use std::{
    cell::{Ref, RefCell, RefMut},
    collections::{BTreeMap, HashMap, HashSet, VecDeque},
    process::Command,
    str,
    sync::mpsc,
    thread::JoinHandle,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use daggy::Walker;
use rand_pcg::Pcg64;
use rand_seeder::Seeder;

use crate::{
    actions::ESActionWrapper,
    config::Config,
    experiment_record::ExperimentRecorder,
    fn_dag::{DagId, EnvFnExt, FnDAG, FnId, Func},
    mechanism::ConfigNewMec,
    mechanism_thread::{self, MechScheduleOnce},
    metric::{MechMetric, OneFrameMetric, Recorder, Records},
    node::{EnvNodeExt, Node, NodeId},
    request::{ReqId, Request},
    scale::{down_exec::DefaultScaleDownExec, num::ScaleNum, up_exec::ScaleUpExec},
    sim_run::Scheduler,
    with_env_sub::WithEnvHelp,
    workload::WorkloadTapeRuntime,
    workload_profile::load_frozen_frequency_profile,
    CONTAINER_BASIC_MEM, NODE_LEFT_MEM_THRESHOLD,
};

// 定义 call_python_script 函数
pub fn call_python_script(arg: &str, rng: f32) -> f64 {
    // 将 f32 转换为 String 以传递给 Python 脚本
    let rng_str = format!("{}", rng);
    // linux use python3
    // windows use python
    // Formal runs pin the helper interpreter explicitly so a system-wide
    // `python` alias cannot silently change the workload calibration.
    #[cfg(target_os = "windows")]
    let default_python = "python";
    #[cfg(not(target_os = "windows"))]
    let default_python = "python3";
    let python_executable =
        std::env::var_os("SERVERLESS_SIM_PYTHON").unwrap_or_else(|| default_python.into());
    let mut python = Command::new(&python_executable);
    let output = python
        .arg("src/real-world-emulation/RealWorldAppEmulation.py")
        .arg(arg)
        .arg(rng_str)
        .output()
        .expect("Failed to execute Python script");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    if output.status.success() {
        stdout
            .trim()
            .parse::<f64>()
            .expect("Failed to parse Python script output")
    } else {
        panic!(
            "Python script error:\nStandard Output: {}\nStandard Error: {}",
            stdout, stderr
        );
    }
}

impl WithEnvHelp for SimEnv {
    fn help(&self) -> &SimEnvHelperState {
        &self.help
    }
}

pub struct SimEnvHelperState {
    config: Config,
    req_next_id: RefCell<ReqId>,
    fn_next_id: RefCell<FnId>,
    cost: RefCell<f32>,
    metric: RefCell<OneFrameMetric>,
    metric_record: RefCell<Option<Recorder>>,
    mech_metric: RefCell<MechMetric>,
    dag_call_frequency: RefCell<BTreeMap<DagId, (f64, f64)>>,
    pub dag_accumulate_call_frequency: RefCell<BTreeMap<DagId, f64>>,
    // key: frame_idx  value: exe_time
    algo_exc_time: RefCell<HashMap<usize, usize>>,
}

impl Clone for SimEnvHelperState {
    fn clone(&self) -> Self {
        Self {
            config: self.config.clone(),
            req_next_id: self.req_next_id.clone(),
            fn_next_id: self.fn_next_id.clone(),
            cost: self.cost.clone(),
            metric: self.metric.clone(),
            metric_record: RefCell::new(None),
            dag_call_frequency: BTreeMap::new().into(),
            mech_metric: self.mech_metric.clone(),
            algo_exc_time: self.algo_exc_time.clone(),
            dag_accumulate_call_frequency: BTreeMap::new().into(),
        }
    }
}

impl SimEnvHelperState {
    pub fn fn_next_id(&self) -> FnId {
        let ret = *self.fn_next_id.borrow_mut();
        *self.fn_next_id.borrow_mut() += 1;
        ret
    }
    pub fn req_next_id(&self) -> ReqId {
        let ret = *self.req_next_id.borrow_mut();
        *self.req_next_id.borrow_mut() += 1;
        ret
    }
    pub fn config<'a>(&'a self) -> &'a Config {
        &self.config
    }
    pub fn cost<'a>(&'a self) -> Ref<'a, f32> {
        self.cost.borrow()
    }
    pub fn metric<'a>(&'a self) -> Ref<'a, OneFrameMetric> {
        self.metric.borrow()
    }
    pub fn metric_record<'a>(&'a self) -> Ref<'a, Option<Recorder>> {
        self.metric_record.borrow()
    }

    pub fn cost_mut<'a>(&'a self) -> RefMut<'a, f32> {
        self.cost.borrow_mut()
    }
    pub fn metric_mut<'a>(&'a self) -> RefMut<'a, OneFrameMetric> {
        self.metric.borrow_mut()
    }
    pub fn metric_record_mut<'a>(&'a self) -> RefMut<'a, Option<Recorder>> {
        self.metric_record.borrow_mut()
    }
    pub fn mech_metric<'a>(&'a self) -> Ref<'a, MechMetric> {
        self.mech_metric.borrow()
    }
    pub fn mech_metric_mut<'a>(&'a self) -> RefMut<'a, MechMetric> {
        self.mech_metric.borrow_mut()
    }
    pub fn fn_call_frequency<'a>(&'a self) -> Ref<'a, BTreeMap<DagId, (f64, f64)>> {
        self.dag_call_frequency.borrow()
    }
    pub fn fn_call_frequency_mut<'a>(&'a self) -> RefMut<'a, BTreeMap<DagId, (f64, f64)>> {
        self.dag_call_frequency.borrow_mut()
    }
    pub fn algo_exc_time<'a>(&'a self) -> Ref<'a, HashMap<usize, usize>> {
        self.algo_exc_time.borrow()
    }
    pub fn algo_exc_time_mut<'a>(&'a self) -> RefMut<'a, HashMap<usize, usize>> {
        self.algo_exc_time.borrow_mut()
    }
    pub fn avg_algo_exc_time(&self) -> f64 {
        let sum = self.algo_exc_time.borrow().values().sum::<usize>();
        let count = self.algo_exc_time.borrow().len();
        if count == 0 {
            0.0
        } else {
            (sum as f64) / (count as f64)
        }
    }
}

pub struct SimEnvCoreState {
    fn_2_nodes: RefCell<HashMap<FnId, HashSet<NodeId>>>,
    dags: RefCell<Vec<FnDAG>>,
    fns: RefCell<Vec<Func>>,
    // 节点间网速图
    node2node_graph: RefCell<Vec<Vec<f32>>>,
    node2node_connection_count: RefCell<Vec<Vec<usize>>>,
    nodes: RefCell<Vec<Node>>,
    current_frame: RefCell<usize>,
    requests: RefCell<BTreeMap<ReqId, Request>>,
    done_requests: RefCell<Vec<Request>>,
    admission_queue: RefCell<VecDeque<Request>>,
}

impl Clone for SimEnvCoreState {
    fn clone(&self) -> Self {
        Self {
            fn_2_nodes: RefCell::new(self.fn_2_nodes.borrow().clone()),
            dags: RefCell::new(self.dags.borrow().clone()),
            fns: RefCell::new(self.fns.borrow().clone()),
            node2node_graph: RefCell::new(self.node2node_graph.borrow().clone()),
            node2node_connection_count: RefCell::new(
                self.node2node_connection_count.borrow().clone(),
            ),
            nodes: RefCell::new(self.nodes.borrow().clone()),
            current_frame: RefCell::new(*self.current_frame.borrow()),
            requests: RefCell::new(self.requests.borrow().clone()),
            done_requests: RefCell::new(self.done_requests.borrow().clone()),
            admission_queue: RefCell::new(self.admission_queue.borrow().clone()),
        }
    }
}

impl SimEnvCoreState {
    pub fn dags<'a>(&'a self) -> Ref<'a, Vec<FnDAG>> {
        self.dags.borrow()
    }
    pub fn dags_mut<'a>(&'a self) -> RefMut<'a, Vec<FnDAG>> {
        self.dags.borrow_mut()
    }
    pub fn fns<'a>(&'a self) -> Ref<'a, Vec<Func>> {
        self.fns.borrow()
    }
    pub fn fns_mut<'a>(&'a self) -> RefMut<'a, Vec<Func>> {
        self.fns.borrow_mut()
    }
    pub fn node2node_graph<'a>(&'a self) -> Ref<'a, Vec<Vec<f32>>> {
        self.node2node_graph.borrow()
    }
    pub fn node2node_graph_mut<'a>(&'a self) -> RefMut<'a, Vec<Vec<f32>>> {
        self.node2node_graph.borrow_mut()
    }

    pub fn fn_2_nodes<'a>(&'a self) -> Ref<'a, HashMap<FnId, HashSet<NodeId>>> {
        self.fn_2_nodes.borrow()
    }
    pub fn node2node_connection_count<'a>(&'a self) -> Ref<'a, Vec<Vec<usize>>> {
        self.node2node_connection_count.borrow()
    }
    pub fn nodes<'a>(&'a self) -> Ref<'a, Vec<Node>> {
        self.nodes.borrow()
    }
    pub fn current_frame<'a>(&'a self) -> usize {
        *self.current_frame.borrow()
    }
    pub fn requests<'a>(&'a self) -> Ref<'a, BTreeMap<ReqId, Request>> {
        self.requests.borrow()
    }
    pub fn done_requests<'a>(&'a self) -> Ref<'a, Vec<Request>> {
        self.done_requests.borrow()
    }
    pub fn admission_queue<'a>(&'a self) -> Ref<'a, VecDeque<Request>> {
        self.admission_queue.borrow()
    }

    pub fn fn_2_nodes_mut<'a>(&'a self) -> RefMut<'a, HashMap<FnId, HashSet<NodeId>>> {
        self.fn_2_nodes.borrow_mut()
    }
    pub fn node2node_connection_count_mut<'a>(&'a self) -> RefMut<'a, Vec<Vec<usize>>> {
        self.node2node_connection_count.borrow_mut()
    }
    pub fn nodes_mut<'a>(&'a self) -> RefMut<'a, Vec<Node>> {
        self.nodes.borrow_mut()
    }
    pub fn current_frame_mut<'a>(&'a self) -> RefMut<'a, usize> {
        self.current_frame.borrow_mut()
    }
    pub fn requests_mut<'a>(&'a self) -> RefMut<'a, BTreeMap<ReqId, Request>> {
        self.requests.borrow_mut()
    }
    pub fn done_requests_mut<'a>(&'a self) -> RefMut<'a, Vec<Request>> {
        self.done_requests.borrow_mut()
    }
    pub fn admission_queue_mut<'a>(&'a self) -> RefMut<'a, VecDeque<Request>> {
        self.admission_queue.borrow_mut()
    }
}

#[derive(Clone, Debug)]
pub struct AdmissionRuntime {
    pub enabled: bool,
    pub policy: String,
    pub active_request_limit: usize,
    pub tape_event_count: usize,
    pub tape_static_cpu_work: f64,
    pub cluster_cpu_per_frame: f64,
    pub static_path_allowance_frames: usize,
    pub minimum_drain_frames: usize,
    pub drain_cpu_work_multiplier: f64,
    pub max_drain_frames: usize,
    pub hard_end_frame: usize,
}

impl AdmissionRuntime {
    fn disabled(config: &Config) -> Self {
        Self {
            enabled: false,
            policy: "disabled".to_string(),
            active_request_limit: usize::MAX,
            tape_event_count: 0,
            tape_static_cpu_work: 0.0,
            cluster_cpu_per_frame: 0.0,
            static_path_allowance_frames: 0,
            minimum_drain_frames: 0,
            drain_cpu_work_multiplier: 0.0,
            max_drain_frames: config
                .total_frame
                .saturating_sub(config.experiment.workload.arrival_horizon_frames),
            hard_end_frame: config.total_frame,
        }
    }

    fn derive(env: &SimEnv) -> Self {
        let config = env.help.config();
        let admission = &config.experiment.admission;
        if !admission.enabled {
            return Self::disabled(config);
        }

        let active_request_limit = {
            let nodes = env.nodes();
            derive_active_request_limit_from_memory(nodes.iter().map(|node| node.rsc_limit.mem))
        };
        let horizon = config.experiment.workload.arrival_horizon_frames;
        let dag_counts = env.workload_tape.replay_dag_counts_before(horizon);
        let tape_event_count = env.workload_tape.replay_event_count_before(horizon);
        let cluster_cpu_per_frame = env
            .nodes()
            .iter()
            .map(|node| node.rsc_limit.cpu as f64)
            .sum::<f64>();
        assert!(
            cluster_cpu_per_frame.is_finite() && cluster_cpu_per_frame > 0.0,
            "admission drain requires positive finite cluster CPU capacity"
        );

        let mut tape_static_cpu_work = 0.0f64;
        let mut static_path_allowance_frames = 0usize;
        for (dag_id, count) in dag_counts {
            assert!(
                dag_id < env.core.dags().len(),
                "tape references missing DAG"
            );
            let dag = env.dag(dag_id);
            let dag_work = dag
                .dag_inner
                .graph()
                .node_weights()
                .map(|fn_id| env.func(*fn_id).cpu as f64)
                .sum::<f64>();
            tape_static_cpu_work += dag_work * count as f64;
            static_path_allowance_frames =
                static_path_allowance_frames.max(static_dag_path_allowance_frames(env, &dag));
        }
        assert!(
            tape_static_cpu_work.is_finite() && tape_static_cpu_work >= 0.0,
            "tape static CPU work must be finite and nonnegative"
        );
        let max_drain_frames = derive_max_drain_frames(
            admission.minimum_drain_frames,
            admission.drain_cpu_work_multiplier,
            tape_static_cpu_work,
            cluster_cpu_per_frame,
            static_path_allowance_frames,
        );
        let hard_end_frame = horizon.saturating_add(max_drain_frames);
        Self {
            enabled: true,
            policy: admission.policy.clone(),
            active_request_limit,
            tape_event_count,
            tape_static_cpu_work,
            cluster_cpu_per_frame,
            static_path_allowance_frames,
            minimum_drain_frames: admission.minimum_drain_frames,
            drain_cpu_work_multiplier: admission.drain_cpu_work_multiplier,
            max_drain_frames,
            hard_end_frame,
        }
    }
}

pub(crate) fn derive_active_request_limit_from_memory(
    memory_capacities: impl IntoIterator<Item = f32>,
) -> usize {
    memory_capacities
        .into_iter()
        .map(|memory| {
            if !memory.is_finite() || memory <= NODE_LEFT_MEM_THRESHOLD {
                0
            } else {
                ((memory - NODE_LEFT_MEM_THRESHOLD) / CONTAINER_BASIC_MEM).floor() as usize
            }
        })
        .sum::<usize>()
        .max(1)
}

pub(crate) fn derive_max_drain_frames(
    minimum_drain_frames: usize,
    cpu_work_multiplier: f64,
    tape_static_cpu_work: f64,
    cluster_cpu_per_frame: f64,
    static_path_allowance_frames: usize,
) -> usize {
    assert!(minimum_drain_frames > 0, "minimum drain must be positive");
    assert!(
        cpu_work_multiplier.is_finite() && cpu_work_multiplier > 0.0,
        "drain CPU-work multiplier must be finite and positive"
    );
    assert!(
        tape_static_cpu_work.is_finite() && tape_static_cpu_work >= 0.0,
        "tape static CPU work must be finite and nonnegative"
    );
    assert!(
        cluster_cpu_per_frame.is_finite() && cluster_cpu_per_frame > 0.0,
        "cluster CPU capacity must be finite and positive"
    );
    let work_drain =
        (cpu_work_multiplier * tape_static_cpu_work / cluster_cpu_per_frame).ceil() as usize;
    minimum_drain_frames.max(work_drain.saturating_add(static_path_allowance_frames))
}

fn static_dag_path_allowance_frames(env: &SimEnv, dag: &FnDAG) -> usize {
    let max_node_cpu = env
        .nodes()
        .iter()
        .map(|node| node.rsc_limit.cpu)
        .filter(|cpu| cpu.is_finite() && *cpu > 0.0)
        .fold(0.0f32, f32::max);
    assert!(
        max_node_cpu > 0.0,
        "static path requires a positive node CPU"
    );
    let min_network_mb_per_second = env
        .core
        .node2node_graph()
        .iter()
        .flat_map(|row| row.iter().copied())
        .filter(|speed| speed.is_finite() && *speed > 0.0)
        .fold(f32::INFINITY, f32::min);
    let mut distance = HashMap::<FnId, usize>::new();
    let mut walker = dag.new_dag_walker();
    while let Some(node_index) = walker.next(&dag.dag_inner) {
        let fn_id = dag.dag_inner[node_index];
        let function = env.func(fn_id);
        let own = function
            .cold_start_time
            .saturating_add((function.cpu / max_node_cpu).ceil().max(1.0) as usize);
        let parent_path = dag
            .dag_inner
            .parents(node_index)
            .iter(&dag.dag_inner)
            .map(|(edge_index, parent_index)| {
                let parent_id = dag.dag_inner[parent_index];
                let edge_mb = *dag.dag_inner.edge_weight(edge_index).unwrap_or(&0.0);
                let transfer_frames = if min_network_mb_per_second.is_finite() {
                    (edge_mb * 1000.0 / min_network_mb_per_second).ceil() as usize
                } else {
                    0
                };
                distance
                    .get(&parent_id)
                    .copied()
                    .unwrap_or(0)
                    .saturating_add(transfer_frames)
            })
            .max()
            .unwrap_or(0);
        distance.insert(fn_id, parent_path.saturating_add(own));
    }
    distance.values().copied().max().unwrap_or(0)
}

pub struct SimEnvMechanisms {
    scale_executor: RefCell<DefaultScaleDownExec>,
    scale_up_exec: RefCell<Box<dyn ScaleUpExec>>,
    spec_scheduler: RefCell<Option<Box<dyn Scheduler + Send>>>,
    spec_scale_num: RefCell<Option<Box<dyn ScaleNum + Send>>>,
}
impl SimEnvMechanisms {
    pub fn scale_executor<'a>(&'a self) -> Ref<'a, DefaultScaleDownExec> {
        self.scale_executor.borrow()
    }
    pub fn scale_up_exec<'a>(&'a self) -> Ref<'a, Box<dyn ScaleUpExec>> {
        self.scale_up_exec.borrow()
    }
    pub fn spec_scheduler<'a>(&'a self) -> Ref<'a, Option<Box<dyn Scheduler + Send>>> {
        self.spec_scheduler.borrow()
    }
    pub fn spec_scale_num<'a>(&'a self) -> Ref<'a, Option<Box<dyn ScaleNum + Send>>> {
        self.spec_scale_num.borrow()
    }

    pub fn scale_executor_mut<'a>(&'a self) -> RefMut<'a, DefaultScaleDownExec> {
        self.scale_executor.borrow_mut()
    }
    pub fn scale_up_exec_mut<'a>(&'a self) -> RefMut<'a, Box<dyn ScaleUpExec>> {
        self.scale_up_exec.borrow_mut()
    }
    pub fn spec_scheduler_mut<'a>(&'a self) -> RefMut<'a, Option<Box<dyn Scheduler + Send>>> {
        self.spec_scheduler.borrow_mut()
    }
    pub fn spec_scale_num_mut<'a>(&'a self) -> RefMut<'a, Option<Box<dyn ScaleNum + Send>>> {
        self.spec_scale_num.borrow_mut()
    }
}

impl SimEnvMechanisms {}

pub struct SimEnv {
    pub recent_use_time: Duration,
    pub rander: RefCell<Pcg64>,
    // end time - tasks
    pub timers: RefCell<HashMap<usize, Vec<Box<dyn FnMut(&SimEnv) + Send>>>>,

    pub help: SimEnvHelperState,
    pub core: SimEnvCoreState,
    // pub mechanisms: SimEnvMechanisms,
    // pub new_mech: MechanismImpl,
    pub master_mech_not_running: bool,
    pub mech_caller: mpsc::Sender<MechScheduleOnce>,
    mech_worker: Option<JoinHandle<()>>,
    pub workload_tape: WorkloadTapeRuntime,
    pub admission_runtime: AdmissionRuntime,
    pub experiment_recorder: ExperimentRecorder,
}

impl SimEnv {
    // 构造函数，接收一个 Config 参数，用于初始化模拟环境的各项属性
    pub fn new(config: Config) -> Self {
        let start = SystemTime::now();
        let recent_use_time = start.duration_since(UNIX_EPOCH).unwrap();

        // let args = parse_arg::get_arg();
        let workload_tape = WorkloadTapeRuntime::new(&config)
            .unwrap_or_else(|error| panic!("invalid workload tape configuration: {error}"));
        let experiment_recorder = ExperimentRecorder::new(&config)
            .unwrap_or_else(|error| panic!("invalid experiment output configuration: {error}"));
        let (mech_caller, mech_worker) =
            mechanism_thread::spawn_joinable(config.new_mec().unwrap());
        let mut newenv = Self {
            help: SimEnvHelperState {
                // nodes: vec![Node::new(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)],
                req_next_id: RefCell::new(0),
                fn_next_id: RefCell::new(0),
                cost: RefCell::new(0.00000001),
                metric: RefCell::new(OneFrameMetric::new()),
                metric_record: RefCell::new(Some(if config.experiment.output.enabled {
                    Recorder::disabled()
                } else {
                    Recorder::new(config.str())
                })),
                config: config.clone(),
                mech_metric: RefCell::new(MechMetric::new()),
                dag_call_frequency: RefCell::new(BTreeMap::new()),
                algo_exc_time: RefCell::new(HashMap::new()),
                dag_accumulate_call_frequency: RefCell::new(BTreeMap::new()),
            },
            core: SimEnvCoreState {
                node2node_graph: RefCell::new(Vec::new()),
                dags: RefCell::new(Vec::new()),
                nodes: RefCell::new(Vec::new()),
                node2node_connection_count: RefCell::new(Vec::new()),
                requests: RefCell::new(BTreeMap::new()),
                done_requests: RefCell::new(Vec::new()),
                admission_queue: RefCell::new(VecDeque::new()),
                current_frame: RefCell::new(0),
                fn_2_nodes: RefCell::new(HashMap::new()),
                fns: RefCell::new(Vec::new()),
            },
            // mechanisms: SimEnvMechanisms {
            //     scale_executor: RefCell::new(DefaultScaleDownExec),
            //     scale_up_exec: RefCell::new(Box::new(LeastTaskScaleUpExec::new())),
            //     spec_scheduler: RefCell::new(sche::prepare_spec_scheduler(&config)),
            //     spec_scale_num: RefCell::new(new_scale_num(&config)),
            // },
            // new_mech: ,
            master_mech_not_running: true,
            recent_use_time,
            rander: RefCell::new(Seeder::from(config.workload_seed()).make_rng()),
            timers: HashMap::new().into(),
            mech_caller,
            mech_worker: Some(mech_worker),
            workload_tape,
            admission_runtime: AdmissionRuntime::disabled(&config),
            experiment_recorder,
        };

        // 为模拟环境创建所有的dag、node、func
        newenv.init();
        newenv.admission_runtime = AdmissionRuntime::derive(&newenv);
        newenv
            .experiment_recorder
            .write_static_environment(&newenv)
            .unwrap_or_else(|error| panic!("failed to record static environment: {error}"));
        // Environment initialization may legitimately take longer than the GC idle
        // threshold when a new workload seed has to build its trace-derived caches.
        // Treat the environment as freshly used after initialization completes so it
        // cannot be collected in the reset-to-step handoff window.
        newenv.avoid_gc();
        newenv
    }
    pub fn reset(&mut self) {
        let config = self.help.config.clone();
        *self = SimEnv::new(config);
    }

    fn shutdown_mechanism(&mut self) {
        // Replacing and dropping the last command sender closes the worker's
        // receive loop.  Joining then guarantees scheduler-owned JSONL and
        // offline-reference writers have atomically published their files.
        let (closed_sender, closed_receiver) = mpsc::channel();
        drop(closed_receiver);
        let sender = std::mem::replace(&mut self.mech_caller, closed_sender);
        drop(sender);
        if let Some(worker) = self.mech_worker.take() {
            if worker.join().is_err() {
                log::error!("mechanism worker panicked during environment shutdown");
            }
        }
    }
    // 初始化方法，进一步设置仿真环境的状态
    fn init(&self) {
        // 创建 NODE_CNT 个节点并初始化网速图和连接图
        self.node_init_node_graph();
        // # # init databases
        // # databases_cnt=5
        // # for i in range(databases_cnt):
        // #     db=DataBase()
        // #     # bind a database to node
        // #     while True:
        // #         rand_node_i=random.randint(0,dim-1)
        // #         if self.nodes[rand_node_i].database==None:
        // #             self.nodes[rand_node_i].database=db
        // #             db.node=self.nodes[rand_node_i]
        // #             break
        // #     self.databases.append(db)

        // 创建 DAG 实例，并将其加入到 dags 列表中
        self.fn_gen_fn_dags(self);

        let cache_req_freq = format!("cache/{}", self.help.config.no_mech_str());
        if self.help.config.experiment.output.enabled {
            let profile = load_frozen_frequency_profile(
                &self.help.config.experiment.workload.frequency_profile,
                &self.help.config.request_freq,
            )
            .unwrap_or_else(|error| panic!("formal workload profile rejected: {error}"));
            *self.help.fn_call_frequency_mut() = profile;
        } else if std::fs::metadata(&cache_req_freq).is_err() {
            //为每个dag生成调用频率和CV
            for dag in self.core.dags().iter() {
                let rng = self.env_rand_f(0.0, 1.0);
                let avg_freq = call_python_script("IAT", rng);
                let cv = call_python_script("CV", rng);
                self.help
                    .fn_call_frequency_mut()
                    .insert(dag.dag_i, (avg_freq, cv));
                log::info!(
                    "gen cv:{}, freq:{} for app:{} by rng{}",
                    cv,
                    avg_freq,
                    dag.dag_i,
                    rng
                );
            }
            // mkdir, allow failure
            let _ = std::fs::create_dir("cache");
            // write to file
            let mut file = std::fs::File::create(cache_req_freq).unwrap();
            serde_json::to_writer(&mut file, &*self.help.fn_call_frequency()).unwrap();
        } else {
            // read frome file
            let mut file = std::fs::File::open(cache_req_freq).unwrap();
            let freq: BTreeMap<DagId, (f64, f64)> = serde_json::from_reader(&mut file).unwrap();
            *self.help.fn_call_frequency_mut() = freq;
        }

        log::info!("env init done");
    }

    // 获取当前模拟帧数
    pub fn current_frame(&self) -> usize {
        *self.core.current_frame.borrow()
    }

    pub fn active_request_limit(&self) -> usize {
        self.admission_runtime.active_request_limit
    }

    pub fn external_arrival_count(&self) -> usize {
        self.core.admission_queue().len()
            + self.core.requests().len()
            + self.core.done_requests().len()
    }

    pub fn admitted_request_count(&self) -> usize {
        self.core.requests().len() + self.core.done_requests().len()
    }

    pub fn cohort_is_drained(&self) -> bool {
        self.core.admission_queue().is_empty() && self.core.requests().is_empty()
    }

    // return scores, next_batch_state
    // pub fn step_batch(&mut self, raw_actions: Vec<Vec<f32>>) -> (Vec<f32>, String) {
    //     let start = SystemTime::now();
    //     self.recent_use_time = start.duration_since(UNIX_EPOCH).unwrap();

    //     let mut state = String::new();
    //     if self.config.scaler_type().is_aief_scaler() {
    //         self.step_aief_batch(raw_actions)
    //     } else {
    //         panic!("not support")
    //     }
    // }

    // 更新最近使用时间，以避免模拟环境被 gc 被清理
    pub fn avoid_gc(&mut self) {
        let start = SystemTime::now();
        self.recent_use_time = start.duration_since(UNIX_EPOCH).unwrap();
    }

    // 根据给定的 raw_action，执行仿真环境的一个时间步，返回 score 和 state
    pub fn step(&mut self, raw_action: u32) -> (f32, String) {
        // update to current time
        self.avoid_gc();
        self.step_es(ESActionWrapper::Int(raw_action), None, None, None, None)
    }

    // 在模拟一帧开始时调用，更新节点状态、清空已完成请求、重置性能指标等
    pub fn on_frame_begin(&self) {
        // 遍历每个节点，更新状态
        for n in self.core.nodes_mut().iter_mut() {
            // 将当前帧的 CPU 使用量保存为上一帧的 CPU 使用量
            n.last_frame_cpu = n.cpu;
            n.last_frame_mem = n.unready_mem();
            // 将当前帧的 CPU 使用量重置为0.0
            n.cpu = 0.0;

            // 更新节点的内存使用量,重新计算
            let container_basic_mem = {
                let containers = n.fn_containers.borrow();
                let mut function_ids = containers.keys().copied().collect::<Vec<_>>();
                function_ids.sort_unstable();
                function_ids.into_iter().fold(0.0f32, |total, fn_id| {
                    total
                        + containers
                            .get(&fn_id)
                            .expect("function ID came from the container map")
                            .container_basic_mem(self)
                })
            };
            *n.unready_mem_mut() = container_basic_mem;

            // 对节点上的每个容器的mem_use和last_frame_mem重设
            let mut containers = n.fn_containers.borrow_mut();
            let mut function_ids = containers.keys().copied().collect::<Vec<_>>();
            function_ids.sort_unstable();
            for fn_id in function_ids {
                let c = containers
                    .get_mut(&fn_id)
                    .expect("function ID came from the container map");
                c.last_frame_mem = c.mem_use;
                c.mem_use = CONTAINER_BASIC_MEM;
            }

            //有些变为运行状态 内存占用变大很正常
            // assert!(
            //     n.unready_mem() <= n.rsc_limit.mem,
            //     "mem {} > limit {}",
            //     n.unready_mem(),
            //     n.rsc_limit.mem
            // );
        }
        // metric，将这一帧已完成的请求数清空
        self.help.metric.borrow_mut().on_frame_begin();

        // timer
        if let Some(timers) = self.timers.borrow_mut().remove(&self.current_frame()) {
            for mut timer in timers {
                timer(self);
            }
        }

        // *self.distance2hpa.borrow_mut() = 0;
    }

    // 在模拟一帧结束时调用，更新节点成本和本帧使用过的容器的使用次数，增加帧数
    pub fn on_frame_end(&self) {
        // 遍历环境中的每个请求，清空该请求的当前帧已完成函数表
        for (_req_i, req) in self.core.requests_mut().iter_mut() {
            req.cur_frame_done.clear();
        }

        // 遍历环境中的每个节点
        for n in self.core.nodes_mut().iter_mut() {
            // 遍历节点上的每个容器
            for (_, c) in n.fn_containers.borrow_mut().iter_mut() {
                // 更新容器的使用情况
                if c.this_frame_used {
                    c.this_frame_used = false;
                    c.used_times += 1;
                }
            }
            // 更新模拟环境的总成本
            let mut cost = self.help.cost_mut();
            *cost += n.cpu * 0.00001 + n.unready_mem() * 0.00001;
        }

        // 将这一帧的数据记录到表中
        self.help
            .metric_record_mut()
            .as_mut()
            .unwrap()
            .add_frame(self);
        self.experiment_recorder.record_frame(self);

        // 自增 frame
        let mut cur_frame = self.core.current_frame.borrow_mut();

        log::info!("frame done: {}", *cur_frame);
        *cur_frame += 1;
    }
}

impl Drop for SimEnv {
    fn drop(&mut self) {
        self.shutdown_mechanism();
    }
}

#[cfg(test)]
mod tests {
    use super::{
        call_python_script, derive_active_request_limit_from_memory, derive_max_drain_frames,
    };

    #[test]
    fn p5_active_request_limit_uses_public_memory_headroom() {
        assert_eq!(
            derive_active_request_limit_from_memory(vec![5_000.0; 20]),
            100
        );
        assert_eq!(
            derive_active_request_limit_from_memory(vec![5_000.0; 100]),
            500
        );
        assert_eq!(
            derive_active_request_limit_from_memory(vec![5_000.0; 500]),
            2_500
        );
        assert_eq!(
            derive_active_request_limit_from_memory(vec![3_400.0, 3_500.0, 3_800.0, 4_100.0]),
            3
        );
        assert_eq!(derive_active_request_limit_from_memory(vec![3_000.0]), 1);
    }

    #[test]
    fn p5_drain_rule_is_exact_and_weak_scaling_invariant() {
        assert_eq!(
            derive_max_drain_frames(1_000, 4.0, 20_000.0, 100.0, 37),
            1_000
        );
        assert_eq!(
            derive_max_drain_frames(1_000, 4.0, 50_000.0, 100.0, 37),
            2_037
        );
        assert_eq!(
            derive_max_drain_frames(1_000, 4.0, 250_000.0, 500.0, 37),
            2_037
        );
    }

    #[test]
    fn test_python_res_consistency() {
        for i in 0..20 {
            let ran = 0.001 * (i as f32);
            let avg_freq = call_python_script("IAT", ran);
            let cv = call_python_script("CV", ran);

            let avg_freq2 = call_python_script("IAT", ran);
            let cv2 = call_python_script("CV", ran);

            assert!(avg_freq - avg_freq2 < 0.0001);
            assert!(cv - cv2 < 0.0001);
        }
    }
}
