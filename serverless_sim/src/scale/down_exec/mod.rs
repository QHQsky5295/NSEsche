use crate::{
    config::Config,
    fn_dag::FnId,
    mechanism::{DownCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::NodeId,
    with_env_sub::WithEnvCore,
    with_env_sub::WithEnvHelp,
};

// 原 ScaleExecutor
pub trait ScaleDownExec: Send {
    fn exec_scale_down(
        &mut self,
        sim_env: &SimEnvObserve,
        fnid: FnId,
        scale_cnt: usize,
        cmd_distributor: &MechCmdDistributor,
    ) -> Vec<DownCmd>;

    // /// return success scale up cnt
    // fn scale_up(&mut self, sim_env: &SimEnv, fnid: FnId, scale_cnt: usize) -> usize;
}

pub fn new_scale_down_exec(c: &Config) -> Option<Box<dyn ScaleDownExec>> {
    let es = &c.mech;
    let (scale_down_exec_name, _scale_down_exec_attr) = es.scale_down_exec_conf();

    match &*scale_down_exec_name {
        "default" => {
            return Some(Box::new(DefaultScaleDownExec));
        }
        _ => {
            return None;
        }
    }
}

pub struct DefaultScaleDownExec;

impl DefaultScaleDownExec {
    fn may_remove(container_idle: bool, queued_for_function: usize, common_ready: bool) -> bool {
        container_idle && (!common_ready || queued_for_function == 0)
    }

    fn select_commands(
        mut candidates: Vec<(NodeId, FnId)>,
        fnid: FnId,
        scale_cnt: usize,
        common_ready: bool,
    ) -> Vec<DownCmd> {
        candidates.retain(|&(_, candidate_fn)| candidate_fn == fnid);
        if common_ready {
            candidates.sort_unstable();
        }
        candidates
            .into_iter()
            .take(scale_cnt)
            .map(|(nid, fnid)| DownCmd { nid, fnid })
            .collect()
    }

    fn collect_idle_containers(&self, env: &SimEnvObserve) -> Vec<(NodeId, FnId)> {
        let mut idle_container_node_fn = Vec::new();
        let common_ready = env.help().config().experiment.protocol_version == "reviewer-v5";

        for n in env.core().nodes().iter() {
            for (fnid, fn_ct) in n.fn_containers.borrow().iter() {
                let queued = if common_ready {
                    n.pending_task_cnt_for_fn(*fnid)
                } else {
                    0
                };
                if Self::may_remove(fn_ct.is_idle(), queued, common_ready) {
                    idle_container_node_fn.push((n.node_id(), *fnid));
                }
            }
        }

        idle_container_node_fn
    }

    fn scale_down_for_fn(
        &mut self,
        env: &SimEnvObserve,
        fnid: FnId,
        scale_cnt: usize,
        cmd_distributor: &MechCmdDistributor,
    ) -> Vec<DownCmd> {
        let res = Self::select_commands(
            self.collect_idle_containers(env),
            fnid,
            scale_cnt,
            env.help().config().experiment.protocol_version == "reviewer-v5",
        );
        for cmd in res.iter() {
            cmd_distributor
                .send(MechScheduleOnceRes::ScaleDownCmd(cmd.clone()))
                .unwrap();
        }
        res
    }
}

impl ScaleDownExec for DefaultScaleDownExec {
    fn exec_scale_down(
        &mut self,
        env: &SimEnvObserve,
        fnid: FnId,
        scale_cnt: usize,
        cmd_distributor: &MechCmdDistributor,
    ) -> Vec<DownCmd> {
        self.scale_down_for_fn(env, fnid, scale_cnt, cmd_distributor)
    }
}

#[cfg(test)]
mod tests {
    use super::DefaultScaleDownExec;

    #[test]
    fn p6_scale_down_protects_the_particular_queued_container() {
        assert!(DefaultScaleDownExec::may_remove(true, 1, false));
        assert!(!DefaultScaleDownExec::may_remove(true, 1, true));
        assert!(DefaultScaleDownExec::may_remove(true, 0, true));
        for common_ready in [false, true] {
            assert!(!DefaultScaleDownExec::may_remove(false, 0, common_ready));
            assert!(!DefaultScaleDownExec::may_remove(false, 1, common_ready));
        }
    }

    #[test]
    fn p6_scale_down_is_order_independent_and_function_scoped() {
        let first = vec![(7, 5), (1, 9), (3, 5), (0, 5)];
        let mut reversed = first.clone();
        reversed.reverse();
        for input in [first, reversed] {
            let commands = DefaultScaleDownExec::select_commands(input, 5, 2, true);
            let keys: Vec<_> = commands.iter().map(|c| (c.nid, c.fnid)).collect();
            assert_eq!(keys, vec![(0, 5), (3, 5)]);
        }
    }

    #[test]
    fn p6_scale_down_keeps_legacy_order_and_handles_empty_or_excess_count() {
        let candidates = vec![(7, 5), (1, 9), (3, 5)];
        let legacy = DefaultScaleDownExec::select_commands(candidates.clone(), 5, 1, false);
        assert_eq!(legacy[0].nid, 7);
        assert_eq!(
            DefaultScaleDownExec::select_commands(candidates.clone(), 5, 99, true).len(),
            2
        );
        assert!(DefaultScaleDownExec::select_commands(candidates.clone(), 5, 0, true).is_empty());
        assert!(DefaultScaleDownExec::select_commands(candidates, 4, 1, true).is_empty());
    }
}
