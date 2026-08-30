use crate::config::Config;
use crate::mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes};
use crate::with_env_sub::WithEnvCore;
use crate::{
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    sim_run::{schedule_helper, Scheduler},
};
use rand::prelude::SliceRandom;
use rand_pcg::Pcg64;
use rand_seeder::Seeder;

pub struct RandomScheduler {
    rng: Pcg64,
}

impl RandomScheduler {
    pub fn new(config: &Config) -> Self {
        Self::from_algorithm_seed(config.algorithm_seed())
    }

    pub(crate) fn from_algorithm_seed(algorithm_seed: &str) -> Self {
        Self {
            rng: Seeder::from(&format!("random-placement:{algorithm_seed}")).make_rng(),
        }
    }
}

impl Scheduler for RandomScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        for (_req_id, req) in env.core().requests().iter() {
            let fns = schedule_helper::collect_task_to_sche(
                req,
                env,
                schedule_helper::CollectTaskConfig::All,
            );

            for fnid in fns {
                let nodesid = schedule_helper::placement_candidate_ids(req, fnid, env);

                let nodeid = if let Some(node) = nodesid.choose(&mut self.rng) {
                    node
                } else {
                    // 处理没有可用节点的情况，例如记录日志或返回错误
                    eprintln!("No available nodes for scheduling");
                    return;
                };

                // 创建调度命令，使用 match 进行错误处理
                match cmd_distributor.send(MechScheduleOnceRes::ScheCmd(ScheCmd {
                    nid: *nodeid,
                    reqid: req.req_id,
                    fnid,
                    memlimit: None,
                })) {
                    Ok(_) => {
                        // 发送成功，继续处理
                    }
                    Err(e) => {
                        // 发送失败，记录错误但不崩溃
                        log::warn!(
                            "Failed to send schedule command for fn {} to node {}: {:?}",
                            fnid,
                            nodeid,
                            e
                        );
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn multi_window_trace(scheduler: &mut RandomScheduler) -> Vec<(usize, usize, usize, usize)> {
        let windows = [
            vec![(11, 7, vec![0, 1, 2]), (11, 8, vec![1, 3])],
            vec![(12, 3, vec![0, 2]), (13, 9, vec![1, 2, 3])],
            vec![(14, 4, vec![0, 1, 2, 3])],
        ];
        let mut trace = Vec::new();
        for (window, tasks) in windows.into_iter().enumerate() {
            for (req_id, fn_id, candidates) in tasks {
                let node_id = *candidates
                    .choose(&mut scheduler.rng)
                    .expect("test candidate set is nonempty");
                trace.push((window, req_id, fn_id, node_id));
            }
        }
        trace
    }

    fn multi_window_early_stop_trace(
        scheduler: &mut RandomScheduler,
    ) -> Vec<(usize, usize, usize, usize)> {
        let windows = [
            vec![
                (21, 1, vec![0, 1, 2]),
                (21, 2, Vec::new()),
                (21, 3, vec![0, 2]),
            ],
            vec![(22, 4, vec![1, 2]), (22, 5, vec![0, 1, 2])],
            vec![(23, 6, Vec::new()), (23, 7, vec![0, 1])],
        ];
        let mut trace = Vec::new();
        for (window, tasks) in windows.into_iter().enumerate() {
            for (req_id, fn_id, candidates) in tasks {
                let Some(&node_id) = candidates.choose(&mut scheduler.rng) else {
                    // Model RandomScheduler::schedule_some returning from this
                    // scheduling window without advancing its persistent RNG.
                    break;
                };
                trace.push((window, req_id, fn_id, node_id));
            }
        }
        trace
    }

    fn ordered_trace_hash(trace: &[(usize, usize, usize, usize)]) -> u64 {
        let mut hash = 14_695_981_039_346_656_037u64;
        for &(window, req_id, fn_id, node_id) in trace {
            for value in [window, req_id, fn_id, node_id] {
                hash ^= value as u64;
                hash = hash.wrapping_mul(1_099_511_628_211);
            }
        }
        hash
    }

    fn assignment_trace_hash(trace: &[(usize, usize, usize, usize)]) -> u64 {
        let mut assignments = trace.to_vec();
        assignments.sort_unstable_by_key(|&(window, req_id, fn_id, _)| (window, req_id, fn_id));
        ordered_trace_hash(&assignments)
    }

    #[test]
    fn same_algorithm_seed_preserves_random_multi_window_command_and_assignment_traces() {
        let mut standalone = RandomScheduler::from_algorithm_seed("E1523");
        let mut native_shadow = RandomScheduler::from_algorithm_seed("E1523");

        let standalone_trace = multi_window_trace(&mut standalone);
        let native_shadow_trace = multi_window_trace(&mut native_shadow);

        assert_eq!(native_shadow_trace, standalone_trace);
        assert_eq!(
            ordered_trace_hash(&native_shadow_trace),
            ordered_trace_hash(&standalone_trace)
        );
        assert_eq!(
            assignment_trace_hash(&native_shadow_trace),
            assignment_trace_hash(&standalone_trace)
        );

        let mut different_seed = RandomScheduler::from_algorithm_seed("E1524");
        assert_ne!(multi_window_trace(&mut different_seed), standalone_trace);
    }

    #[test]
    fn same_seed_random_shadow_preserves_early_stop_prefixes_across_windows() {
        let mut standalone = RandomScheduler::from_algorithm_seed("E1526");
        let mut native_shadow = RandomScheduler::from_algorithm_seed("E1526");

        let standalone_trace = multi_window_early_stop_trace(&mut standalone);
        let shadow_trace = multi_window_early_stop_trace(&mut native_shadow);

        assert_eq!(shadow_trace, standalone_trace);
        assert_eq!(
            ordered_trace_hash(&shadow_trace),
            ordered_trace_hash(&standalone_trace)
        );
        assert_eq!(shadow_trace.len(), 3);
        assert_eq!(
            shadow_trace
                .iter()
                .map(|&(window, _, fn_id, _)| (window, fn_id))
                .collect::<Vec<_>>(),
            vec![(0, 1), (1, 4), (1, 5)]
        );
        assert!(!shadow_trace.iter().any(|&(_, _, fn_id, _)| fn_id == 3));
        assert!(!shadow_trace.iter().any(|&(_, _, fn_id, _)| fn_id == 7));
    }
}
