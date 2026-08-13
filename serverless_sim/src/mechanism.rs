use std::{
    cell::{RefCell, RefMut},
    collections::{HashMap, HashSet},
    sync::mpsc,
    time::Instant,
};

use cpu_time::ThreadTime;

use enum_as_inner::EnumAsInner;

use crate::{
    actions::ESActionWrapper,
    config::Config,
    fn_dag::{EnvFnExt, FnId},
    mechanism_conf::{MechConfig, ModuleMechConf},
    mechanism_thread::MechCmdDistributor,
    node::NodeId,
    request::ReqId,
    scale::{
        down_exec::{new_scale_down_exec, ScaleDownExec},
        num::{
            down_filter::{CarefulScaleDownFilter, ScaleFilter},
            new_scale_num, ScaleNum,
        },
        up_exec::{new_scale_up_exec, ScaleUpExec},
    },
    sche::{prepare_spec_scheduler, sche_nash::PosthocWelfareEvaluator},
    sim_env::{SimEnvCoreState, SimEnvHelperState},
    sim_run::Scheduler,
    util,
    with_env_sub::{WithEnvCore, WithEnvHelp},
};
#[derive(Clone)]
pub struct UpCmd {
    pub nid: NodeId,
    pub fnid: FnId,
}

#[derive(Clone)]
pub struct DownCmd {
    pub nid: NodeId,
    pub fnid: FnId,
}

#[derive(Clone, Debug)]
pub struct ScheCmd {
    pub nid: NodeId,
    pub reqid: ReqId,
    pub fnid: FnId,
    // TODO: memlimit
    pub memlimit: Option<f32>,
}

pub trait SameTarget: Sized {
    fn same_target(&self, other: &Self) -> bool;
}

impl SameTarget for UpCmd {
    fn same_target(&self, other: &Self) -> bool {
        self.fnid == other.fnid && self.nid == other.nid
    }
}
impl SameTarget for DownCmd {
    fn same_target(&self, other: &Self) -> bool {
        self.fnid == other.fnid && self.nid == other.nid
    }
}

impl SameTarget for ScheCmd {
    fn same_target(&self, other: &Self) -> bool {
        self.fnid == other.fnid && self.nid == other.nid && self.reqid == other.reqid
    }
}

pub trait CheckDup {
    fn check_dup(&self) -> bool;
}

impl<S: SameTarget> CheckDup for Vec<S> {
    fn check_dup(&self) -> bool {
        let first = &self[0];
        for v in &self[1..] {
            if !v.same_target(first) {
                return false;
            }
        }
        true
    }
}

pub const SCHE_NAMES: [&'static str; 20] = [
    "rotate",
    "hash",
    "bp_balance",
    "faasflow",
    "pass",
    "pos",
    "fnsche",
    "random",
    "greedy",
    "consistenthash", // "gofs",
    "ensure_scheduler",
    "load_least",
    "sche_nash",
    "sche_orion",
    "sche_jiagu",
    "sche_Hiku",
    "sche_OCS",
    "sche_FaaSRank",
    "cp_br",
    "onsocmax",
    // "load_least",
    // "random",
];
pub const SCALE_NUM_NAMES: [&'static str; 7] = [
    "no",
    "hpa",
    "lass",
    "temp_scaler",
    "full_placement",
    "rela",
    "ensure_scaler",
];
pub const SCALE_DOWN_EXEC_NAMES: [&'static str; 1] = ["default"];
pub const SCALE_UP_EXEC_NAMES: [&'static str; 2] = ["least_task", "no"];
pub const MECH_NAMES: [&'static str; 3] = ["no_scale", "scale_sche_separated", "scale_sche_joint"];
pub const FILTER_NAMES: [&'static str; 1] = ["careful_down"];
pub const INSTANCE_LIVE_NAMES: [&'static str; 3] = ["no_evict", "lru", "fifo"];

pub trait Mechanism: Send {
    fn step(
        &self,
        env: &SimEnvObserve,
        raw_action: ESActionWrapper,
        cmd_distributor: &MechCmdDistributor,
    );
}

pub trait ConfigNewMec {
    fn new_mec(&self) -> Option<MechanismImpl>;
}

impl ConfigNewMec for Config {
    // return none if failed
    fn new_mec(&self) -> Option<MechanismImpl> {
        // read mechanism config
        let module_es = ModuleMechConf::new();
        if !module_es.check_conf_by_module(&self.mech) {
            return None;
        }

        fn check_config(
            conf: &MechConfig,
            allow_sche: &Vec<&'static str>,
            allow_scale_num: &Vec<&'static str>,
            allow_scale_down_exec: &Vec<&'static str>,
            allow_scale_up_exec: &Vec<&'static str>,
        ) -> bool {
            if !allow_sche.contains(&&*conf.sche_conf().0) {
                log::warn!(
                    "mech_type {} not support sche {}",
                    conf.mech_type().0,
                    conf.sche_conf().0
                );
                return false;
            }
            if !allow_scale_num.contains(&&*conf.scale_num_conf().0) {
                log::warn!(
                    "mech_type {} not support scale_num {}",
                    conf.mech_type().0,
                    conf.scale_num_conf().0
                );
                return false;
            }
            if !allow_scale_down_exec.contains(&&*conf.scale_down_exec_conf().0) {
                log::warn!(
                    "mech_type {} not support scale_down_exec {}",
                    conf.mech_type().0,
                    conf.scale_down_exec_conf().0
                );
                return false;
            }
            if !allow_scale_up_exec.contains(&&*conf.scale_up_exec_conf().0) {
                log::warn!(
                    "mech_type {} no_scale not support scale_up_exec {}",
                    conf.mech_type().0,
                    conf.scale_up_exec_conf().0
                );
                return false;
            }
            true
        }

        // check conf relation
        match &*self.mech.mech_type().0 {
            "no_scale" => {
                let allow_sche = vec![
                    "faasflow",
                    "pass",
                    "fnsche",
                    "random",
                    "greedy",
                    "consistenthash",
                    "hash",
                    "rotate",
                    "load_least",
                    "sche_nash",
                ];
                let allow_scale_num = vec!["no"];
                let allow_scale_down_exec = vec!["default"];
                let allow_scale_up_exec = vec!["no"];

                if !check_config(
                    &self.mech,
                    &allow_sche,
                    &allow_scale_num,
                    &allow_scale_down_exec,
                    &allow_scale_up_exec,
                ) {
                    return None;
                }
            }
            "scale_sche_separated" => {
                let allow_sche = vec![
                    "random",
                    "greedy",
                    "hash",
                    "rotate",
                    "load_least",
                    "pass",
                    "sche_nash",
                    "fnsche",
                    "faasflow",
                    "pos",
                    "consistenthash",
                    "bp_balance",
                    "ensure_scheduler",
                    "sche_orion",
                    "sche_jiagu",
                    "sche_Hiku",
                    "sche_OCS",
                    "sche_FaaSRank",
                    "cp_br",
                    "onsocmax",
                ];
                let allow_scale_num = vec!["hpa", "lass", "temp_scaler", "full_placement", "rela"];
                let allow_scale_down_exec = vec!["default"];
                let allow_scale_up_exec = vec!["least_task"];

                if !check_config(
                    &self.mech,
                    &allow_sche,
                    &allow_scale_num,
                    &allow_scale_down_exec,
                    &allow_scale_up_exec,
                ) {
                    return None;
                }
            }
            "scale_sche_joint" => {
                let allow_sche = vec!["pos", "bp_balance", "ensure_scheduler", "sche_nash"];
                let allow_scale_num = vec![
                    "hpa",
                    "lass",
                    "temp_scaler",
                    "full_placement",
                    "rela",
                    "ensure_scaler",
                ];
                let allow_scale_down_exec = vec!["default"];
                let allow_scale_up_exec = vec!["least_task"];
                if !check_config(
                    &self.mech,
                    &allow_sche,
                    &allow_scale_num,
                    &allow_scale_down_exec,
                    &allow_scale_up_exec,
                ) {
                    return None;
                }
            }
            _ => {
                panic!("mech_type not supported {}", self.mech.mech_type().0);
            }
        }

        let Some(sche) = prepare_spec_scheduler(self) else {
            return None;
        };
        let Some(scale_num) = new_scale_num(self) else {
            return None;
        };
        let Some(scale_down_exec) = new_scale_down_exec(self) else {
            return None;
        };
        let Some(scale_up_exec) = new_scale_up_exec(self) else {
            return None;
        };
        let filters = FILTER_NAMES
            .iter()
            .filter(|v| self.mech.filter.get(**v).unwrap().is_some())
            .map(|filters| {
                let filter = match *filters {
                    "careful_down" => CarefulScaleDownFilter::with_history(
                        self.experiment.hpa.careful_down_history,
                    ),
                    _ => {
                        panic!("filter not supported {}", filters);
                    }
                };
                let filter: Box<dyn ScaleFilter> = Box::new(filter);
                RefCell::new(filter)
            })
            .collect();
        let scheduler_name = self.mech.sche_conf().0;
        let posthoc_welfare = if self.experiment.output.enabled && scheduler_name != "sche_nash" {
            Some(PosthocWelfareEvaluator::new(scheduler_name))
        } else {
            None
        };
        Some(MechanismImpl {
            sche: RefCell::new(sche),
            scale_num: RefCell::new(scale_num),
            scale_down_exec: RefCell::new(scale_down_exec),
            scale_up_exec: RefCell::new(scale_up_exec),
            filters,
            fn_scale_num: RefCell::new(HashMap::new()),
            config: self.clone(),
            step_begin: RefCell::new(0),
            posthoc_welfare: RefCell::new(posthoc_welfare),
            placement_timing: RefCell::new(PlacementTiming::default()),
        })
    }
}

pub struct MechanismImpl {
    pub config: Config,
    sche: RefCell<Box<dyn Scheduler>>,
    scale_num: RefCell<Box<dyn ScaleNum>>,
    scale_down_exec: RefCell<Box<dyn ScaleDownExec>>,
    scale_up_exec: RefCell<Box<dyn ScaleUpExec>>,
    filters: Vec<RefCell<Box<dyn ScaleFilter>>>,
    fn_scale_num: RefCell<HashMap<FnId, usize>>,
    pub step_begin: RefCell<u64>,
    posthoc_welfare: RefCell<Option<PosthocWelfareEvaluator>>,
    placement_timing: RefCell<PlacementTiming>,
}

/// Exact timing boundaries for one placement-policy invocation and its
/// read-only post-hoc welfare observer.  These are measured independently;
/// policy time is never obtained by subtracting observer time from a broader
/// mechanism duration.
#[derive(Clone, Copy, Debug, Default)]
pub struct PlacementTiming {
    pub policy_wall_time_ns: u64,
    pub policy_thread_cpu_ns: u64,
    pub welfare_evaluation_wall_time_ns: u64,
    pub welfare_evaluation_thread_cpu_ns: u64,
}

pub struct SimEnvObserve {
    core: SimEnvCoreState,
    help: SimEnvHelperState,
}

impl SimEnvObserve {
    pub fn new(core: SimEnvCoreState, help: SimEnvHelperState) -> Self {
        Self { core, help }
    }
}

impl WithEnvHelp for SimEnvObserve {
    fn help(&self) -> &SimEnvHelperState {
        &self.help
    }
}
impl WithEnvCore for SimEnvObserve {
    fn core(&self) -> &SimEnvCoreState {
        &self.core
    }
}

impl Mechanism for MechanismImpl {
    // 执行步进操作前的准备，根据配置选择调度、扩缩容模式
    fn step(
        &self,
        env: &SimEnvObserve,
        raw_action: ESActionWrapper,
        cmd_distributor: &MechCmdDistributor,
    ) {
        *self.step_begin.borrow_mut() = util::now_ms();
        *self.placement_timing.borrow_mut() = PlacementTiming::default();
        match &*self.config.mech.mech_type().0 {
            "no_scale" => self.step_no_scaler(env, self, cmd_distributor, raw_action),
            "scale_sche_separated" => {
                self.step_scale_sche_separated(env, cmd_distributor, raw_action);
            }

            // 目前只实现了这个
            "scale_sche_joint" => self.step_scale_sche_joint(env, cmd_distributor, raw_action),
            _ => {
                panic!(
                    "mech_type not supported {}",
                    env.help.config().mech.mech_type().0
                )
            }
        }
    }
}

#[derive(EnumAsInner)]
pub enum MechType {
    NoScale,
    ScaleScheSeparated,
    ScaleScheJoint,
}

impl MechanismImpl {
    pub fn placement_timing(&self) -> PlacementTiming {
        *self.placement_timing.borrow()
    }

    pub fn mech_type(&self) -> MechType {
        match &*self.config.mech.mech_type().0 {
            "no_scale" => MechType::NoScale,
            "scale_sche_separated" => MechType::ScaleScheSeparated,
            "scale_sche_joint" => MechType::ScaleScheJoint,
            _ => {
                panic!("mech_type not supported {}", self.config.mech.mech_type().0)
            }
        }
    }
    pub fn scale_down_exec<'a>(&'a self) -> RefMut<'a, Box<dyn ScaleDownExec>> {
        self.scale_down_exec.borrow_mut()
    }
    pub fn scale_up_exec<'a>(&'a self) -> RefMut<'a, Box<dyn ScaleUpExec>> {
        self.scale_up_exec.borrow_mut()
    }
    // pub fn scale_num<'a>(&'a self) -> RefMut<'a, Box<dyn ScaleNum>> {
    //     self.scale_num.borrow_mut()
    // }
    // no scale
    // 表示只进行调度，不主动对容器数量进行干涉
    fn step_no_scaler(
        &self,
        env: &SimEnvObserve,
        mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
        _raw_action: ESActionWrapper,
    ) {
        log::info!("step_no_scaler");
        let sche_cmds = self.run_placement_only_scheduler(env, mech);
        self.send_atomic_commands(cmd_distributor, Vec::new(), sche_cmds, Vec::new());
    }

    fn update_scale_num(&self, env: &SimEnvObserve, fnid: FnId, action: &ESActionWrapper) {
        let mut target = self.scale_num.borrow_mut().scale_for_fn(env, fnid, action);
        for filter in self.filters.iter() {
            target = filter
                .borrow_mut()
                .filter_desired(fnid, target, env.fn_container_cnt(fnid));
        }
        self.fn_scale_num.borrow_mut().insert(fnid, target);
    }

    pub fn scale_num(&self, fnid: FnId) -> usize {
        self.fn_scale_num.borrow().get(&fnid).unwrap().clone()
    }

    // scale and sche separated
    // 先进行扩缩容，再进行调度
    fn step_scale_sche_separated(
        &self,
        env: &SimEnvObserve,
        cmd_distributor: &MechCmdDistributor,
        raw_action: ESActionWrapper,
    ) {
        log::info!("step_separated");

        // Scale and placement decisions must be committed atomically.  The
        // HPA and scheduler both observe the same immutable window snapshot;
        // forwarding scale-down commands immediately would otherwise unload a
        // container before a placement chosen from that snapshot is applied.
        let (hpa_tx, hpa_rx) = mpsc::channel();

        // 遍历每个函数
        let hpa_period = self.config.experiment.hpa.check_period_frames.max(1);
        if env.core.current_frame() % hpa_period == 0 {
            for func in env.core.fns().iter() {
                self.update_scale_num(env, func.fn_id, &raw_action);
                let target = self.scale_num(func.fn_id);

                let cur = env.fn_container_cnt(func.fn_id);

                // 扩容
                if target > cur {
                    self.scale_up_exec
                        .borrow_mut()
                        .exec_scale_up(target, func.fn_id, env, &hpa_tx);
                } else if
                // 缩容
                target < cur {
                    self.scale_down_exec.borrow_mut().exec_scale_down(
                        env,
                        func.fn_id,
                        cur - target,
                        &hpa_tx,
                    );
                }
            }
        }

        drop(hpa_tx);
        let (scale_up_cmds, mut scale_down_cmds) = self.collect_common_hpa_commands(hpa_rx);
        let sche_cmds = self.run_placement_only_scheduler(env, self);
        remove_conflicting_scale_downs(&sche_cmds, &mut scale_down_cmds);
        self.send_atomic_commands(cmd_distributor, scale_up_cmds, sche_cmds, scale_down_cmds);

        // 扩缩容和调度分离，所以要求调度后不能再主动调节容器数量
        // assert!(up.is_empty());
        // assert!(down.is_empty());
    }

    /// Run a placement policy behind a command firewall.  Under the shared
    /// runtime protocol, scale-up/down commands may only be emitted by the
    /// common HPA stages above; a scheduler is allowed to place requests only.
    ///
    /// Historical configurations remain usable: outside an instrumented
    /// reviewer run an invalid scheduler command is logged and ignored.  A
    /// formal run treats it as a protocol violation and fails result-blindly.
    fn run_placement_only_scheduler(
        &self,
        env: &SimEnvObserve,
        mech: &MechanismImpl,
    ) -> Vec<ScheCmd> {
        let (placement_tx, placement_rx) = mpsc::channel();
        let policy_wall_start = Instant::now();
        let policy_cpu_start = ThreadTime::try_now().ok();
        self.sche
            .borrow_mut()
            .schedule_some(env, mech, &placement_tx);
        let policy_wall_time_ns =
            policy_wall_start.elapsed().as_nanos().min(u64::MAX as u128) as u64;
        let policy_thread_cpu_ns = policy_cpu_start
            .as_ref()
            .and_then(|start| start.try_elapsed().ok())
            .map(|duration| duration.as_nanos().min(u64::MAX as u128) as u64)
            .unwrap_or(0);
        drop(placement_tx);

        let mut placement_commands = Vec::new();
        for command in placement_rx {
            match command {
                crate::mechanism_thread::MechScheduleOnceRes::ScheCmd(command) => {
                    placement_commands.push(command);
                }
                crate::mechanism_thread::MechScheduleOnceRes::Cmds {
                    mut sche_cmds,
                    scale_up_cmds,
                    scale_down_cmds,
                } if scale_up_cmds.is_empty() && scale_down_cmds.is_empty() => {
                    placement_commands.append(&mut sche_cmds);
                }
                _ => {
                    let message =
                        "placement policy attempted to emit a non-ScheCmd under common HPA";
                    if self.config.experiment.output.enabled {
                        panic!("{message}");
                    }
                    log::error!("{message}; command ignored");
                }
            }
        }

        let evaluation_wall_start = Instant::now();
        let evaluation_cpu_start = ThreadTime::try_now().ok();
        let evaluation_enabled = self.posthoc_welfare.borrow().is_some();
        if let Some(evaluator) = self.posthoc_welfare.borrow_mut().as_mut() {
            evaluator.evaluate(env, &placement_commands);
        }
        let welfare_evaluation_wall_time_ns = evaluation_wall_start
            .elapsed()
            .as_nanos()
            .min(u64::MAX as u128) as u64;
        let welfare_evaluation_thread_cpu_ns = evaluation_cpu_start
            .as_ref()
            .and_then(|start| start.try_elapsed().ok())
            .map(|duration| duration.as_nanos().min(u64::MAX as u128) as u64)
            .unwrap_or(0);
        *self.placement_timing.borrow_mut() = PlacementTiming {
            policy_wall_time_ns,
            policy_thread_cpu_ns,
            welfare_evaluation_wall_time_ns: if evaluation_enabled {
                welfare_evaluation_wall_time_ns
            } else {
                0
            },
            welfare_evaluation_thread_cpu_ns: if evaluation_enabled {
                welfare_evaluation_thread_cpu_ns
            } else {
                0
            },
        };

        placement_commands
    }

    fn collect_common_hpa_commands(
        &self,
        receiver: mpsc::Receiver<crate::mechanism_thread::MechScheduleOnceRes>,
    ) -> (Vec<UpCmd>, Vec<DownCmd>) {
        let mut scale_up_cmds = Vec::new();
        let mut scale_down_cmds = Vec::new();
        for command in receiver {
            match command {
                crate::mechanism_thread::MechScheduleOnceRes::ScaleUpCmd(command) => {
                    scale_up_cmds.push(command);
                }
                crate::mechanism_thread::MechScheduleOnceRes::ScaleDownCmd(command) => {
                    scale_down_cmds.push(command);
                }
                crate::mechanism_thread::MechScheduleOnceRes::Cmds {
                    sche_cmds,
                    scale_up_cmds: mut batched_up,
                    scale_down_cmds: mut batched_down,
                } if sche_cmds.is_empty() => {
                    scale_up_cmds.append(&mut batched_up);
                    scale_down_cmds.append(&mut batched_down);
                }
                _ => {
                    let message = "common HPA attempted to emit a placement or unsupported command";
                    if self.config.experiment.output.enabled {
                        panic!("{message}");
                    }
                    log::error!("{message}; command ignored");
                }
            }
        }
        (scale_up_cmds, scale_down_cmds)
    }

    fn send_atomic_commands(
        &self,
        cmd_distributor: &MechCmdDistributor,
        scale_up_cmds: Vec<UpCmd>,
        sche_cmds: Vec<ScheCmd>,
        scale_down_cmds: Vec<DownCmd>,
    ) {
        if let Err(error) =
            cmd_distributor.send(crate::mechanism_thread::MechScheduleOnceRes::Cmds {
                sche_cmds,
                scale_up_cmds,
                scale_down_cmds,
            })
        {
            log::warn!("failed to forward atomic common-runtime commands: {error}");
        }
    }

    // scale and sche joint
    fn step_scale_sche_joint(
        &self,
        env: &SimEnvObserve,
        cmd_distributor: &MechCmdDistributor,
        raw_action: ESActionWrapper,
    ) {
        // 遍历每个函数（每一帧都对每个函数进行scale_for_fn，每个函数都进行扩缩容判断）

        for func in env.core.fns().iter() {
            self.update_scale_num(env, func.fn_id, &raw_action);

            // 获取对该函数当前容器数量
            // let cur = env.fn_container_cnt(func.fn_id);
            // let tar = self.scale_num(func.fn_id);

            // log::info!(
            //     "scale fn{} cost {}",
            //     func.fn_id,
            //     util::now_ms() - *self.step_begin.borrow()
            // );
            // log::info!("scale fn {} from {} to {}", func.fn_id, cur, tar);
            // 不进行扩缩容，在调度时候一起进行
            // log::info!("scale fn {} from {} to {}", func.fn_id, cur, tar);
        }

        // 获得扩容、调度、缩容指令
        let mut sche = self.sche.borrow_mut();
        sche.schedule_some(env, self, cmd_distributor);
        // if down_cmds.check_dup() {
        //     log::warn!("down_cmds has dup cmd");
        // }
    }
}

/// A container selected by a placement from the current immutable snapshot
/// cannot also be removed at commit time.  Unrelated scale-down commands keep
/// their original order and remain eligible for the next atomic commit phase.
fn remove_conflicting_scale_downs(sche_cmds: &[ScheCmd], scale_down_cmds: &mut Vec<DownCmd>) {
    let protected_targets: HashSet<(FnId, NodeId)> = sche_cmds
        .iter()
        .map(|command| (command.fnid, command.nid))
        .collect();
    scale_down_cmds.retain(|command| !protected_targets.contains(&(command.fnid, command.nid)));
}

#[cfg(test)]
mod atomic_common_runtime_tests {
    use super::*;

    fn placement(fnid: FnId, nid: NodeId, reqid: ReqId) -> ScheCmd {
        ScheCmd {
            nid,
            reqid,
            fnid,
            memlimit: None,
        }
    }

    #[test]
    fn conflicting_scale_downs_are_removed_without_reordering_unrelated_downs() {
        let placements = vec![placement(7, 3, 11), placement(9, 5, 12)];
        let mut downs = vec![
            DownCmd { fnid: 7, nid: 3 },
            DownCmd { fnid: 7, nid: 4 },
            DownCmd { fnid: 8, nid: 3 },
            DownCmd { fnid: 9, nid: 5 },
            DownCmd { fnid: 7, nid: 3 },
        ];

        remove_conflicting_scale_downs(&placements, &mut downs);

        assert_eq!(downs.len(), 2);
        assert_eq!((downs[0].fnid, downs[0].nid), (7, 4));
        assert_eq!((downs[1].fnid, downs[1].nid), (8, 3));
    }

    #[test]
    fn no_placement_leaves_scale_down_order_unchanged() {
        let mut downs = vec![DownCmd { fnid: 2, nid: 8 }, DownCmd { fnid: 1, nid: 4 }];

        remove_conflicting_scale_downs(&[], &mut downs);

        assert_eq!(downs.len(), 2);
        assert_eq!((downs[0].fnid, downs[0].nid), (2, 8));
        assert_eq!((downs[1].fnid, downs[1].nid), (1, 4));
    }
}
