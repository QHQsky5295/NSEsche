use crate::cache::no_evict::NoEvict;
use crate::cache::InstanceCachePolicy;
use crate::config::Config;
use crate::with_env_sub::WithEnvHelp;
use crate::{
    fn_dag::{EnvFnExt, FnContainer, FnContainerState, FnId, Func},
    mechanism::SimEnvObserve,
    request::ReqId,
    sim_env::SimEnv,
    with_env_sub::WithEnvCore,
    NODE_LEFT_MEM_THRESHOLD, NODE_SCORE_CPU_WEIGHT, NODE_SCORE_MEM_WEIGHT,
};
use rand::Rng;
use rand_distr::{Distribution, Normal};
use rand_pcg::Pcg64;
use rand_seeder::Seeder;
use std::ptr::NonNull;
use std::{
    cell::{Ref, RefCell, RefMut},
    cmp::Ordering,
    collections::{BTreeSet, HashMap, HashSet},
};

pub type NodeId = usize;

#[derive(Clone)]
pub struct NodeRscLimit {
    // 节点cpu上限
    pub cpu: f32,
    // 节点mem上限
    pub mem: f32,
}

/// Exclusive, read-only task states observed at one node.
///
/// `pending` tasks have been assigned to the node but are not resident in a
/// container yet. Resident tasks are classified by the same readiness gates
/// used by the execution loop: the container must be running, all DAG parents
/// must be complete, and all input data must have arrived.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct NodeQueueBreakdown {
    pub pending: usize,
    pub runnable: usize,
    pub parent_blocked: usize,
    pub data_blocked: usize,
    pub starting_resident: usize,
}

/// Exact CPU work for tasks that contribute to the current execution queue.
/// Both the immutable function CPU demand and the current remaining runnable
/// work are retained so preregistered policies can select either observation
/// without changing the queue membership.  This observation deliberately mirrors
/// `NodeQueueBreakdown::pressure_queue_len`: assigned-but-not-resident tasks
/// and currently runnable resident tasks are included exactly once, while
/// tasks blocked by cold start, DAG parents, or input transfer are excluded.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct NodeQueueCpuWork {
    pub pending_cpu: f64,
    pub runnable_cpu: f64,
    pub runnable_remaining_cpu: f64,
    pub pending_cpu_values: Vec<f64>,
    pub runnable_remaining_cpu_values: Vec<f64>,
}

impl NodeQueueCpuWork {
    pub fn total(&self) -> f64 {
        self.pending_cpu + self.runnable_cpu
    }

    pub fn remaining_total(&self) -> f64 {
        self.pending_cpu + self.runnable_remaining_cpu
    }

    /// Exact busy work completed before a newly admitted job of `current_work`
    /// finishes under the simulator's equal-share CPU discipline.  Every
    /// competing job receives at most the service received by the current
    /// job, so its contribution is capped by `current_work`.
    pub fn processor_sharing_competing_work(&self, current_work: f32) -> Option<f64> {
        if !current_work.is_finite() || current_work < 0.0 {
            return None;
        }
        let cap = f64::from(current_work);
        let mut total = 0.0f64;
        for &value in self
            .pending_cpu_values
            .iter()
            .chain(self.runnable_remaining_cpu_values.iter())
        {
            if !value.is_finite() || value < 0.0 {
                return None;
            }
            total += value.min(cap);
            if !total.is_finite() {
                return None;
            }
        }
        Some(total)
    }
}

fn checked_cpu_work_add(total: &mut f64, raw_cpu: f32) -> bool {
    if !raw_cpu.is_finite() || raw_cpu < 0.0 {
        return false;
    }
    *total += f64::from(raw_cpu);
    total.is_finite()
}

impl NodeQueueBreakdown {
    pub fn resident_total(self) -> usize {
        self.runnable
            .saturating_add(self.parent_blocked)
            .saturating_add(self.data_blocked)
            .saturating_add(self.starting_resident)
    }

    pub fn pressure_queue_len(self) -> usize {
        self.pending.saturating_add(self.runnable)
    }

    fn observe_resident(
        &mut self,
        container_running: bool,
        parents_all_done: bool,
        data_recv_done: bool,
    ) {
        if !container_running {
            self.starting_resident += 1;
        } else if !parents_all_done {
            self.parent_blocked += 1;
        } else if !data_recv_done {
            self.data_blocked += 1;
        } else {
            self.runnable += 1;
        }
    }
}

// #[derive(Clone)]
pub struct Node {
    node_id: NodeId,
    // #数据库容器
    // # databases

    // # #函数容器
    // # functions

    // # #serverless总控节点
    // # serverless_controller

    // #资源限制：cpu, mem
    pub rsc_limit: NodeRscLimit,

    // 待处理的任务
    pending_tasks: RefCell<BTreeSet<(ReqId, FnId)>>,

    // 节点上已有的函数容器
    pub fn_containers: RefCell<HashMap<FnId, FnContainer>>,

    // 使用了的cpu
    pub cpu: f32,

    // 使用了的内存
    // 具体函数使用内存在算法执行后才计算, 算法中需要使用last_frame_mem
    mem: RefCell<f32>,

    // 上一帧使用的cpu
    pub last_frame_cpu: f32,

    // 上一帧使用的mem
    pub last_frame_mem: f32,

    pub frame_run_count: usize,

    //缓存置换策略
    instance_cache_policy: RefCell<Box<dyn InstanceCachePolicy<FnId>>>,
}

impl Clone for Node {
    fn clone(&self) -> Self {
        Node {
            node_id: self.node_id,
            rsc_limit: self.rsc_limit.clone(),
            fn_containers: self.fn_containers.clone(),
            pending_tasks: self.pending_tasks.clone(),
            cpu: self.cpu,
            mem: self.mem.clone(),
            last_frame_cpu: self.last_frame_cpu,
            last_frame_mem: self.last_frame_mem,
            frame_run_count: self.frame_run_count,

            // never used, clone is for SimEnvObserve
            instance_cache_policy: RefCell::new(Box::new(NoEvict::new())),
        }
    }
}

impl Node {
    // 具体函数使用内存在算法执行后才计算, 算法中需要使用last_frame_mem
    // 返回已使用的mem量
    pub fn unready_mem_mut<'a>(&'a self) -> RefMut<'a, f32> {
        self.mem.borrow_mut()
    }
    // 具体函数使用内存在算法执行后才计算, 算法中需要使用last_frame_mem
    pub fn unready_mem(&self) -> f32 {
        *self.mem.borrow()
    }
    fn new(node_id: NodeId, config: &Config, cpu_limit: f32, mem_limit: f32) -> Self {
        Self {
            node_id,
            rsc_limit: NodeRscLimit {
                cpu: cpu_limit,
                mem: mem_limit,
            },
            fn_containers: HashMap::new().into(),
            cpu: 0.0,
            mem: (0.0).into(),
            last_frame_cpu: 0.0,
            frame_run_count: 0,
            pending_tasks: BTreeSet::new().into(),
            last_frame_mem: 0.0,
            instance_cache_policy: RefCell::new(config.mech.new_instance_cache_policy()),
        }
    }

    // 增加任务
    pub fn add_task(&self, req_id: ReqId, fn_id: FnId) {
        self.pending_tasks.borrow_mut().insert((req_id, fn_id));
    }

    pub fn unready_left_mem(&self) -> f32 {
        self.rsc_limit.mem - self.unready_mem()
    }

    // 返回剩余的mem量
    pub fn left_mem(&self) -> f32 {
        self.rsc_limit.mem - self.last_frame_mem
    }

    // 返回剩余的可用于部署容器的mem量
    pub fn left_mem_for_place_container(&self) -> f32 {
        self.rsc_limit.mem - self.unready_mem() - NODE_LEFT_MEM_THRESHOLD
    }

    // 判断剩余的可用于部署容器的mem量是否足够部署特定函数的容器
    pub fn mem_enough_for_container(&self, func: &Func) -> bool {
        self.left_mem_for_place_container() > func.cold_start_container_mem_use
            && self.left_mem_for_place_container() > func.container_mem()
    }
    pub fn node_id(&self) -> NodeId {
        self.node_id
    }

    // 比较两个节点的资源使用情况
    // pub enum Ordering {
    //     Less,
    //     Equal,
    //     Greater,
    // }
    pub fn cmp_rsc_used(&self, other: &Self) -> Ordering {
        (self.cpu * NODE_SCORE_CPU_WEIGHT + self.unready_mem() * NODE_SCORE_MEM_WEIGHT)
            .partial_cmp(
                &(other.cpu * NODE_SCORE_CPU_WEIGHT + other.unready_mem() * NODE_SCORE_MEM_WEIGHT),
            )
            .unwrap()
    }

    // 返回节点上所有任务（待处理和正在运行）的总数
    pub fn all_task_cnt(&self) -> usize {
        self.pending_task_cnt() + self.running_task_cnt()
    }

    // 返回节点上待处理任务的数量
    pub fn pending_task_cnt(&self) -> usize {
        self.pending_tasks.borrow().len()
    }

    // 返回节点上正在运行的任务数量
    pub fn running_task_cnt(&self) -> usize {
        self.fn_containers
            .borrow()
            .iter()
            .map(|(_, c)| c.req_fn_state.len())
            .sum()
    }

    /// Classify the node's outstanding work without mutating simulator state.
    /// Iteration is sorted so observation remains deterministic even though
    /// containers and resident tasks are stored in hash maps.
    pub fn queue_breakdown(&self, env: &SimEnvObserve) -> NodeQueueBreakdown {
        let mut breakdown = NodeQueueBreakdown {
            pending: self.pending_task_cnt(),
            ..NodeQueueBreakdown::default()
        };
        let requests = env.core().requests();
        let containers = self.fn_containers.borrow();
        let mut function_ids = containers.keys().copied().collect::<Vec<_>>();
        function_ids.sort_unstable();

        for fn_id in function_ids {
            let container = containers
                .get(&fn_id)
                .expect("function ID came from the container map");
            let container_running = container.is_running();
            if !container_running {
                breakdown.starting_resident = breakdown
                    .starting_resident
                    .saturating_add(container.req_fn_state.len());
                continue;
            }
            let parents = env.func(fn_id).parent_fns(env);
            let mut request_ids = container.req_fn_state.keys().copied().collect::<Vec<_>>();
            request_ids.sort_unstable();

            for req_id in request_ids {
                let task = container
                    .req_fn_state
                    .get(&req_id)
                    .expect("request ID came from the resident-task map");
                let parents_all_done = requests.get(&req_id).is_some_and(|request| {
                    parents
                        .iter()
                        .all(|parent| request.done_fns.contains_key(parent))
                });
                breakdown.observe_resident(true, parents_all_done, task.data_recv_done());
            }
        }

        breakdown
    }

    /// Sum the configured CPU work of the current pending and runnable tasks
    /// without consulting completions or mutating simulator state.  All
    /// hash-backed collections are sorted before floating-point accumulation,
    /// making the result deterministic.  Invalid work values fail closed.
    pub fn queue_cpu_work(&self, env: &SimEnvObserve) -> Option<NodeQueueCpuWork> {
        let mut work = NodeQueueCpuWork::default();
        for &(_req_id, fn_id) in self.pending_tasks.borrow().iter() {
            let cpu = env.func(fn_id).cpu;
            if !checked_cpu_work_add(&mut work.pending_cpu, cpu) {
                return None;
            }
            work.pending_cpu_values.push(f64::from(cpu));
        }

        let requests = env.core().requests();
        let containers = self.fn_containers.borrow();
        let mut function_ids = containers.keys().copied().collect::<Vec<_>>();
        function_ids.sort_unstable();
        for fn_id in function_ids {
            let container = containers
                .get(&fn_id)
                .expect("function ID came from the container map");
            if !container.is_running() {
                continue;
            }
            let parents = env.func(fn_id).parent_fns(env);
            let mut request_ids = container.req_fn_state.keys().copied().collect::<Vec<_>>();
            request_ids.sort_unstable();
            for req_id in request_ids {
                let task = container
                    .req_fn_state
                    .get(&req_id)
                    .expect("request ID came from the resident-task map");
                let runnable = requests.get(&req_id).is_some_and(|request| {
                    parents
                        .iter()
                        .all(|parent| request.done_fns.contains_key(parent))
                }) && task.data_recv_done();
                if runnable {
                    if !checked_cpu_work_add(&mut work.runnable_cpu, env.func(fn_id).cpu)
                        || !checked_cpu_work_add(&mut work.runnable_remaining_cpu, task.left_calc)
                    {
                        return None;
                    }
                    work.runnable_remaining_cpu_values
                        .push(f64::from(task.left_calc));
                }
            }
        }
        (work.total().is_finite() && work.remaining_total().is_finite()).then_some(work)
    }

    // 返回指定函数ID的容器的可变引用
    pub fn container_mut<'a>(&'a self, fnid: FnId) -> Option<RefMut<'a, FnContainer>> {
        let b = self.fn_containers.borrow_mut();
        if !b.contains_key(&fnid) {
            return None;
        }
        let res = RefMut::map(b, |map| {
            map.get_mut(&fnid)
                .unwrap_or_else(|| panic!("container {} not found", fnid))
        });
        Some(res)
        // .get_mut(&fnid)
    }

    // 返回指定函数ID的容器的不可变引用
    pub fn container<'a>(&'a self, fnid: FnId) -> Option<Ref<'a, FnContainer>> {
        let b = self.fn_containers.borrow();
        if !b.contains_key(&fnid) {
            return None;
        }
        let res = Ref::map(b, |map| {
            map.get(&fnid)
                .unwrap_or_else(|| panic!("container {} not found", fnid))
        });
        Some(res)
        // .get_mut(&fnid)
    }
    // pub fn container<'a>(&'a self, fnid: FnId) -> Option<&'a FnContainer> {
    //     self.fn_containers.get(&fnid)
    // }

    pub fn try_unload_container(&self, fnid: FnId, env: &SimEnv, if_down: bool) {
        // log::info!("scale down fn {fnid} from node {}", self.node_id());
        // env.set_scale_down_result(fnid, self.node_id());

        let nodeid = self.node_id();
        let Some(cont) = self.fn_containers.borrow_mut().remove(&fnid) else {
            log::info!("try_unload_container not found {}", fnid);
            return;
        };

        //是主动缩容则要主动移除
        if if_down {
            assert!(self.instance_cache_policy.borrow_mut().remove_all(&fnid));
        }

        env.core
            .fn_2_nodes_mut()
            .get_mut(&fnid)
            .unwrap()
            .remove(&nodeid);
        match cont.state() {
            FnContainerState::Starting { .. } => {
                *self.mem.borrow_mut() -= env.func(fnid).cold_start_container_mem_use;
            }
            FnContainerState::Running => {
                *self.mem.borrow_mut() -= env.func(fnid).container_mem();
            }
        }
        // let fncon = self.fn_containers.borrow_mut().remove(&fnid).unwrap();
        // let con_mem_take = fncon.mem_take(env);
        // // log::info!("unload fn: {fn_id} from node: {node_id}");
        // // 1. 更新 fn 到nodes的map，用于查询fn 对应哪些节点有部署
        // let node_id = self.node_id();
        // env.core.fn_2_nodes_mut().entry(fnid).and_modify(|v| {
        //     v.remove(&node_id);
        // });
        // // will recalc next frame begin
        // // but we need to add mem to node in this frame because it's new container
        // *self.mem.borrow_mut() -= con_mem_take;
        // self.nodes.borrow_mut()[node_id].mem +=
        //     self.func(fn_id).cold_start_container_mem_use;
    }

    pub fn try_load_container(&self, fnid: FnId, env: &SimEnv) {
        if self.container(fnid).is_some() {
            // log::info!("已经添加了{}", fnid);
            return;
        }

        let (old, flag) = unsafe {
            let node = NonNull::new_unchecked(self as *const Node as *mut Node);
            let (old, flag) = self.instance_cache_policy.borrow_mut().put(
                fnid,
                Box::new(move |to_replace| {
                    let node = node.as_ref();
                    // log::info!("节点{}要移除的容器{}", node.node_id, to_replace);
                    for (_k, v) in node.fn_containers.borrow().iter() {
                        // log::info!("{}", v.fn_id);
                    }
                    node.container(*to_replace).unwrap().is_idle()
                }),
            );
            log::info!("old{:?}", old);
            (old, flag)
        };

        // 可以增加该容器
        if flag {
            // 1. 将old unload掉
            if old.is_some() {
                self.try_unload_container(old.unwrap(), env, false);
                log::info!("节点{}移除容器{}", self.node_id, old.unwrap());
            }
            // 2. load 当前fnid
            // try cold start
            // 首先从cache中寻找可用容器
            if self.mem_enough_for_container(&env.func(fnid)) {
                let fncon = FnContainer::new(fnid, self.node_id(), env);
                let con_mem_take = fncon.mem_take(env);
                self.fn_containers.borrow_mut().insert(fnid, fncon);
                let node_id = self.node_id();
                env.core
                    .fn_2_nodes_mut()
                    .entry(fnid)
                    .and_modify(|v| {
                        v.insert(node_id);
                    })
                    .or_insert_with(|| {
                        let mut set: HashSet<usize> = HashSet::new();
                        set.insert(node_id);
                        set
                    });

                // will recalc next frame begin
                // but we need to add mem to node in this frame because it's new container
                *self.mem.borrow_mut() += con_mem_take;
            } else {
                log::info!("内存不够，取消缓存标记{}", fnid);
                let mut node_cache = self.instance_cache_policy.borrow_mut();
                assert!(node_cache.remove_all(&fnid));
            }
        }
    }
    // 尝试加载节点上所有待处理任务的容器
    // 如果内存足够且容器不存在，则创建新容器，将任务状态添加到容器，并从待处理任务集合中移除
    pub fn load_container(&self, env: &SimEnv) {
        // 用于存储已移除的待处理任务
        let mut removed_pending = vec![];

        //let mut tasks = self.pending_tasks.borrow_mut().clone();

        // 遍历该节点上的所有待处理任务
        for &(req_id, fnid) in self.pending_tasks.borrow_mut().iter() {
            // 尝试加载函数容器
            self.try_load_container(fnid, env);

            if let Some(mut fncon) = self.container_mut(fnid) {
                // Maybe it's not the first time to load this container
                // So we need to warm it in the cache
                if fncon.req_fn_state.contains_key(&req_id) {
                    continue;
                }

                self.instance_cache_policy.borrow_mut().get(fnid).unwrap();
                // add to container

                assert!(fncon
                    .req_fn_state
                    .insert(
                        req_id,
                        env.fn_new_fn_running_state(&env.request(req_id), fnid)
                    )
                    .is_none());
                removed_pending.push((req_id, fnid));
            }
        }

        for (req_id, fnid) in removed_pending {
            self.pending_tasks.borrow_mut().remove(&(req_id, fnid));
        }
    }
}

impl SimEnv {
    // 初始化节点之间的图数据结构，包括节点之间的连接数计数和带宽图，并为每个节点设置随机速度
    pub fn node_init_node_graph(&self) {
        let config = self.help().config();
        let profile = &config.experiment.node_profile;
        let mut topology_rng: Pcg64 =
            Seeder::from(&format!("{}:topology", config.topology_seed())).make_rng();
        let cpu_normal = Normal::new(
            profile.cpu_mean as f64,
            (profile.cpu_mean * profile.cpu_cv).max(f32::EPSILON) as f64,
        )
        .expect("valid CPU topology distribution");
        let mem_normal = Normal::new(
            profile.mem_mean as f64,
            (profile.mem_mean * profile.mem_cv).max(f32::EPSILON) as f64,
        )
        .expect("valid memory topology distribution");

        fn sample_capacity(
            heterogeneous: bool,
            mean: f32,
            min_factor: f32,
            max_factor: f32,
            distribution: &Normal<f64>,
            rng: &mut Pcg64,
        ) -> f32 {
            if !heterogeneous {
                return mean;
            }
            (distribution.sample(rng) as f32).clamp(mean * min_factor, mean * max_factor)
        }

        fn center_capacities(values: &mut [f32], mean: f32, min_factor: f32, max_factor: f32) {
            if values.is_empty() {
                return;
            }
            let target_total = mean * values.len() as f32;
            let min_value = mean * min_factor;
            let max_value = mean * max_factor;
            for _ in 0..values.len().saturating_add(2) {
                let residual = target_total - values.iter().sum::<f32>();
                if residual.abs() <= mean.abs().max(1.0) * 1.0e-5 {
                    break;
                }
                let adjustable = values
                    .iter()
                    .enumerate()
                    .filter(|(_, value)| {
                        if residual > 0.0 {
                            **value < max_value
                        } else {
                            **value > min_value
                        }
                    })
                    .map(|(index, _)| index)
                    .collect::<Vec<_>>();
                if adjustable.is_empty() {
                    break;
                }
                let share = residual / adjustable.len() as f32;
                for index in adjustable {
                    values[index] = (values[index] + share).clamp(min_value, max_value);
                }
            }
        }

        fn init_one_node(
            env: &SimEnv,
            node_id: NodeId,
            cpu_limit: f32,
            mem_limit: f32,
            rng: &mut Pcg64,
        ) {
            let node = Node::new(node_id, env.help().config(), cpu_limit, mem_limit);

            // let node_i = nodecnt;
            env.core.nodes_mut().push(node);

            let nodecnt: usize = env.core.nodes().len();

            for i in 0..nodecnt - 1 {
                let network = &env.help().config().experiment.network_profile;
                let randspeed = rng.gen_range(network.min_mbps..network.max_mbps);
                // 设置节点间网速
                env.node_set_speed_btwn(i, nodecnt - 1, randspeed);
            }
        }

        // 初始化节点图
        // # init nodes graph
        let dim = config.experiment.node_count.max(1);
        *self.core.node2node_connection_count_mut() = vec![vec![0; dim]; dim];
        *self.core.node2node_graph_mut() = vec![vec![0.0; dim]; dim];
        let heterogeneous = profile.kind.eq_ignore_ascii_case("heterogeneous");
        let mut cpu_capacities = (0..dim)
            .map(|_| {
                sample_capacity(
                    heterogeneous,
                    profile.cpu_mean,
                    profile.min_factor,
                    profile.max_factor,
                    &cpu_normal,
                    &mut topology_rng,
                )
            })
            .collect::<Vec<_>>();
        let mut mem_capacities = (0..dim)
            .map(|_| {
                sample_capacity(
                    heterogeneous,
                    profile.mem_mean,
                    profile.min_factor,
                    profile.max_factor,
                    &mem_normal,
                    &mut topology_rng,
                )
            })
            .collect::<Vec<_>>();
        if heterogeneous {
            center_capacities(
                &mut cpu_capacities,
                profile.cpu_mean,
                profile.min_factor,
                profile.max_factor,
            );
            center_capacities(
                &mut mem_capacities,
                profile.mem_mean,
                profile.min_factor,
                profile.max_factor,
            );
        }
        for i in 0..dim {
            init_one_node(
                self,
                i,
                cpu_capacities[i],
                mem_capacities[i],
                &mut topology_rng,
            );
        }

        log::info!("node bandwidth graph: {:?}", self.core.node2node_graph());
    }

    /// 设置节点间网速
    /// - speed: MB/s
    fn node_set_speed_btwn(&self, n1: usize, n2: usize, speed: f32) {
        assert!(n1 != n2);
        fn _set_speed_btwn(env: &SimEnv, nbig: usize, nsmall: usize, speed: f32) {
            env.core.node2node_graph_mut()[nbig][nsmall] = speed;
        }
        if n1 > n2 {
            _set_speed_btwn(self, n1, n2, speed);
        } else {
            _set_speed_btwn(self, n2, n1, speed);
        }
    }

    pub fn node_set_connection_count_between(&self, n1: NodeId, n2: NodeId, count: usize) {
        let _set_connection_count_between = |nbig: usize, nsmall: usize, count: usize| {
            self.core.node2node_connection_count_mut()[nbig][nsmall] = count;
        };
        if n1 > n2 {
            _set_connection_count_between(n1, n2, count);
        } else {
            _set_connection_count_between(n2, n1, count);
        }
    }

    pub fn node_get_connection_count_between(&self, n1: NodeId, n2: NodeId) -> usize {
        let _get_connection_count_between =
            |nbig: usize, nsmall: usize| self.core.node2node_connection_count()[nbig][nsmall];
        if n1 > n2 {
            _get_connection_count_between(n1, n2)
        } else {
            _get_connection_count_between(n2, n1)
        }
    }

    pub fn node_get_connection_count_between_by_offerd_graph(
        &self,
        n1: NodeId,
        n2: NodeId,
        offerd: &Vec<Vec<usize>>,
    ) -> usize {
        let _get_connection_count_between = |nbig: usize, nsmall: usize| offerd[nbig][nsmall];
        if n1 > n2 {
            _get_connection_count_between(n1, n2)
        } else {
            _get_connection_count_between(n2, n1)
        }
    }

    pub fn node_set_connection_count_between_by_offerd_graph(
        &self,
        n1: NodeId,
        n2: NodeId,
        count: usize,
        offerd: &mut Vec<Vec<usize>>,
    ) {
        let mut _set_connection_count_between = |nbig: usize, nsmall: usize, count: usize| {
            offerd[nbig][nsmall] = count;
        };
        if n1 > n2 {
            _set_connection_count_between(n1, n2, count);
        } else {
            _set_connection_count_between(n2, n1, count);
        }
    }
}

impl EnvNodeExt for SimEnv {}
impl EnvNodeExt for SimEnvObserve {}
pub trait EnvNodeExt: WithEnvCore {
    // 返回节点数量
    fn node_cnt(&self) -> usize {
        self.core().nodes().len()
    }

    // 返回对节点列表的不可变引用
    fn nodes<'a>(&'a self) -> Ref<'a, Vec<Node>> {
        self.core().nodes()
    }

    // 返回对节点列表的可变引用
    fn nodes_mut<'a>(&'a self) -> RefMut<'a, Vec<Node>> {
        self.core().nodes_mut()
    }

    // 返回对指定节点ID的不可变引用
    fn node<'a>(&'a self, i: NodeId) -> Ref<'a, Node> {
        let b = self.nodes();

        Ref::map(b, |vec| &vec[i])
    }

    // 返回对指定节点ID的可变引用
    fn node_mut<'a>(&'a self, i: NodeId) -> RefMut<'a, Node> {
        let b = self.nodes_mut();

        RefMut::map(b, |vec| &mut vec[i])
    }
    /// 获取节点间网速
    /// - speed: MB/s
    fn node_get_speed_btwn(&self, n1: NodeId, n2: NodeId) -> f32 {
        let _get_speed_btwn =
            |nbig: usize, nsmall: usize| self.core().node2node_graph()[nbig][nsmall];
        if n1 > n2 {
            _get_speed_btwn(n1, n2)
        } else {
            _get_speed_btwn(n2, n1)
        }
    }

    //获取计算速度最慢的节点
    fn node_get_lowest(&self) -> NodeId {
        let nodes = self.core().nodes();
        let res = nodes
            .iter()
            .min_by(|x, y| x.cpu.partial_cmp(&y.cpu).unwrap())
            .unwrap();
        res.node_id
    }

    //获取最低带宽
    fn node_btw_get_lowest(&self) -> f32 {
        let mut low_btw = None;

        for i in 0..self.core().nodes().len() {
            for j in i + 1..self.core().nodes().len() {
                let btw = self.node_get_speed_btwn(i, j);
                if let Some(low_btw_) = low_btw.take() {
                    low_btw = Some(btw.min(low_btw_));
                } else {
                    low_btw = Some(btw);
                }
            }
        }

        low_btw.unwrap()
    }
}

#[cfg(test)]
mod queue_breakdown_tests {
    use super::{checked_cpu_work_add, NodeQueueBreakdown, NodeQueueCpuWork};

    #[test]
    fn blocked_resident_tasks_do_not_enter_runnable_queue() {
        let mut breakdown = NodeQueueBreakdown::default();
        breakdown.observe_resident(true, false, true);
        breakdown.observe_resident(true, true, false);
        breakdown.observe_resident(false, true, true);

        assert_eq!(breakdown.runnable, 0);
        assert_eq!(breakdown.parent_blocked, 1);
        assert_eq!(breakdown.data_blocked, 1);
        assert_eq!(breakdown.starting_resident, 1);
        assert_eq!(breakdown.resident_total(), 3);
        assert_eq!(breakdown.pressure_queue_len(), 0);
    }

    #[test]
    fn ready_task_in_running_container_enters_runnable_queue() {
        let mut breakdown = NodeQueueBreakdown {
            pending: 2,
            ..NodeQueueBreakdown::default()
        };
        breakdown.observe_resident(true, true, true);

        assert_eq!(breakdown.runnable, 1);
        assert_eq!(breakdown.resident_total(), 1);
        assert_eq!(breakdown.pressure_queue_len(), 3);
    }

    #[test]
    fn exact_queue_cpu_work_accumulates_heterogeneous_functions_once() {
        let mut work = NodeQueueCpuWork::default();
        assert!(checked_cpu_work_add(&mut work.pending_cpu, 0.25));
        assert!(checked_cpu_work_add(&mut work.pending_cpu, 1.5));
        assert!(checked_cpu_work_add(&mut work.runnable_cpu, 0.75));
        assert!(checked_cpu_work_add(&mut work.runnable_remaining_cpu, 0.25));

        assert!((work.pending_cpu - 1.75).abs() < f64::EPSILON);
        assert!((work.runnable_cpu - 0.75).abs() < f64::EPSILON);
        assert!((work.runnable_remaining_cpu - 0.25).abs() < f64::EPSILON);
        assert!((work.total() - 2.5).abs() < f64::EPSILON);
        assert!((work.remaining_total() - 2.0).abs() < f64::EPSILON);
    }

    #[test]
    fn exact_queue_cpu_work_rejects_invalid_function_work() {
        let mut total = 1.0;
        assert!(!checked_cpu_work_add(&mut total, f32::NAN));
        assert!(!checked_cpu_work_add(&mut total, -0.5));
        assert_eq!(total, 1.0);
    }

    #[test]
    fn processor_sharing_work_caps_each_competing_job_by_current_work() {
        let work = NodeQueueCpuWork {
            pending_cpu_values: vec![0.25, 2.0],
            runnable_remaining_cpu_values: vec![0.5, 4.0],
            ..NodeQueueCpuWork::default()
        };

        let competing = work.processor_sharing_competing_work(1.0).unwrap();
        assert!((competing - 2.75).abs() < f64::EPSILON);
        assert_eq!(work.processor_sharing_competing_work(f32::NAN), None);
        assert_eq!(work.processor_sharing_competing_work(-1.0), None);
    }
}
