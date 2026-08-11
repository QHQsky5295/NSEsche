use std::{
    cmp::Ordering,
    collections::{HashMap, HashSet, VecDeque},
};

use crate::{
    fn_dag::{FnContainerState, FnId},
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::{ReqId, Request},
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::WithEnvCore,
};

const HISTORY_LIMIT: usize = 64;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum PlacementContainerState {
    Missing,
    Starting,
    RunningBusy,
    RunningIdle,
}

/// Placement-only OCS adaptation.
///
/// OCS retains container-state-aware invocation distribution and bounded
/// placement history.  Cache admission/eviction is intentionally absent: the
/// common cache and HPA protocol is shared by every scheduler in the study.
pub struct OCSScheduler {
    invocation_history: HashMap<FnId, VecDeque<NodeId>>,
    scheduled_pairs: HashSet<(ReqId, FnId)>,
}

impl Default for OCSScheduler {
    fn default() -> Self {
        Self::new()
    }
}

impl OCSScheduler {
    pub fn new() -> Self {
        Self {
            invocation_history: HashMap::new(),
            scheduled_pairs: HashSet::new(),
        }
    }

    fn container_state(
        &self,
        fn_id: FnId,
        node_id: NodeId,
        env: &SimEnvObserve,
    ) -> PlacementContainerState {
        env.node(node_id)
            .fn_containers
            .borrow()
            .get(&fn_id)
            .map(|container| match container.state() {
                FnContainerState::Starting { .. } => PlacementContainerState::Starting,
                FnContainerState::Running if container.req_fn_state.is_empty() => {
                    PlacementContainerState::RunningIdle
                }
                FnContainerState::Running => PlacementContainerState::RunningBusy,
            })
            .unwrap_or(PlacementContainerState::Missing)
    }

    fn recent_affinity(&self, fn_id: FnId, node_id: NodeId) -> f32 {
        let Some(history) = self.invocation_history.get(&fn_id) else {
            return 0.0;
        };
        if history.is_empty() {
            return 0.0;
        }
        history.iter().filter(|&&seen| seen == node_id).count() as f32 / history.len() as f32
    }

    fn node_score(
        &self,
        fn_id: FnId,
        node_id: NodeId,
        projected_assignments: usize,
        env: &SimEnvObserve,
    ) -> f32 {
        let node = env.node(node_id);
        let memory_utilization = safe_ratio(node.unready_mem(), node.rsc_limit.mem);
        let task_load = (node.all_task_cnt() + projected_assignments) as f32;
        let normalized_load = task_load / (1.0 + task_load);
        ocs_placement_score(
            self.container_state(fn_id, node_id, env),
            memory_utilization,
            normalized_load,
            self.recent_affinity(fn_id, node_id),
        )
    }

    fn select_node(
        &self,
        req: &Request,
        fn_id: FnId,
        projected: &HashMap<NodeId, usize>,
        env: &SimEnvObserve,
    ) -> Option<NodeId> {
        schedule_helper::placement_candidate_ids(req, fn_id, env)
            .into_iter()
            .map(|node_id| {
                let score = self.node_score(
                    fn_id,
                    node_id,
                    projected.get(&node_id).copied().unwrap_or(0),
                    env,
                );
                (node_id, score)
            })
            .max_by(|left, right| compare_scored_nodes(*left, *right))
            .map(|(node_id, _)| node_id)
    }

    fn record_placement(&mut self, fn_id: FnId, node_id: NodeId) {
        let history = self
            .invocation_history
            .entry(fn_id)
            .or_insert_with(|| VecDeque::with_capacity(HISTORY_LIMIT));
        history.push_back(node_id);
        while history.len() > HISTORY_LIMIT {
            history.pop_front();
        }
    }

    fn prune_request_state(&mut self, _env: &SimEnvObserve) {
        self.scheduled_pairs.clear();
    }
}

fn safe_ratio(numerator: f32, denominator: f32) -> f32 {
    if denominator <= f32::EPSILON {
        1.0
    } else {
        (numerator / denominator).clamp(0.0, 1.0)
    }
}

/// Higher is better.  In particular, a warm idle container must outrank a
/// busy warm container, which must outrank starting/missing containers under
/// otherwise identical conditions.  This fixes the old inverted minimization.
fn ocs_placement_score(
    state: PlacementContainerState,
    memory_utilization: f32,
    normalized_load: f32,
    recent_affinity: f32,
) -> f32 {
    let warm_score = match state {
        PlacementContainerState::Missing => 0.0,
        PlacementContainerState::Starting => 0.2,
        PlacementContainerState::RunningBusy => 0.65,
        PlacementContainerState::RunningIdle => 1.0,
    };
    0.55 * warm_score
        + 0.20 * (1.0 - memory_utilization.clamp(0.0, 1.0))
        + 0.15 * (1.0 - normalized_load.clamp(0.0, 1.0))
        + 0.10 * recent_affinity.clamp(0.0, 1.0)
}

fn compare_scored_nodes(left: (NodeId, f32), right: (NodeId, f32)) -> Ordering {
    left.1
        .partial_cmp(&right.1)
        .unwrap_or(Ordering::Equal)
        .then_with(|| right.0.cmp(&left.0))
}

impl Scheduler for OCSScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        _mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        self.prune_request_state(env);
        let mut projected: HashMap<NodeId, usize> = HashMap::new();

        for (_, req) in env.core().requests().iter() {
            let functions = schedule_helper::collect_task_to_sche(
                req,
                env,
                schedule_helper::CollectTaskConfig::PreAllSched,
            );
            for fn_id in functions {
                let key = (req.req_id, fn_id);
                if self.scheduled_pairs.contains(&key) {
                    continue;
                }
                let Some(node_id) = self.select_node(req, fn_id, &projected, env) else {
                    continue;
                };

                match cmd_distributor.send(MechScheduleOnceRes::ScheCmd(ScheCmd {
                    nid: node_id,
                    reqid: req.req_id,
                    fnid: fn_id,
                    memlimit: None,
                })) {
                    Ok(()) => {
                        self.scheduled_pairs.insert(key);
                        self.record_placement(fn_id, node_id);
                        *projected.entry(node_id).or_default() += 1;
                    }
                    Err(error) => log::warn!(
                        "OCS-P failed to place request {} function {} on node {}: {:?}",
                        req.req_id,
                        fn_id,
                        node_id,
                        error
                    ),
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn warm_score_direction_is_not_inverted() {
        let missing = ocs_placement_score(PlacementContainerState::Missing, 0.2, 0.2, 0.0);
        let starting = ocs_placement_score(PlacementContainerState::Starting, 0.2, 0.2, 0.0);
        let busy = ocs_placement_score(PlacementContainerState::RunningBusy, 0.2, 0.2, 0.0);
        let idle = ocs_placement_score(PlacementContainerState::RunningIdle, 0.2, 0.2, 0.0);
        assert!(idle > busy && busy > starting && starting > missing);
    }

    #[test]
    fn lower_load_wins_when_container_state_matches() {
        let low = ocs_placement_score(PlacementContainerState::RunningIdle, 0.2, 0.1, 0.0);
        let high = ocs_placement_score(PlacementContainerState::RunningIdle, 0.2, 0.9, 0.0);
        assert!(low > high);
    }
}
