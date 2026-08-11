use std::{
    cmp::Ordering,
    collections::{HashMap, HashSet, VecDeque},
};

use crate::{
    fn_dag::{FnContainerState, FnId},
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::ReqId,
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::WithEnvCore,
};

const DEMAND_WINDOW: usize = 20;

/// Placement-only Jiagu adaptation.
///
/// Demand prediction is used to make and spread placement pre-decisions.  It
/// never changes instance counts: the experiment-wide HPA remains the sole
/// scaler and container-lifecycle owner.
pub struct JiaguScheduler {
    demand_history: HashMap<FnId, VecDeque<f64>>,
    predicted_demand: HashMap<FnId, f64>,
    pre_decisions: HashMap<(ReqId, FnId), Vec<NodeId>>,
    scheduled_pairs: HashSet<(ReqId, FnId)>,
    last_observed_frame: Option<usize>,
}

impl JiaguScheduler {
    pub fn new() -> Self {
        Self {
            demand_history: HashMap::new(),
            predicted_demand: HashMap::new(),
            pre_decisions: HashMap::new(),
            scheduled_pairs: HashSet::new(),
            last_observed_frame: None,
        }
    }

    fn collect_pending(&self, env: &SimEnvObserve) -> Vec<(ReqId, FnId)> {
        let mut pending = Vec::new();
        for (_, req) in env.core().requests().iter() {
            for fn_id in schedule_helper::collect_task_to_sche(
                req,
                env,
                schedule_helper::CollectTaskConfig::All,
            ) {
                if !self.scheduled_pairs.contains(&(req.req_id, fn_id)) {
                    pending.push((req.req_id, fn_id));
                }
            }
        }
        pending
    }

    fn update_prediction(&mut self, pending: &[(ReqId, FnId)], env: &SimEnvObserve) {
        let frame = env.core().current_frame();
        if self.last_observed_frame == Some(frame) {
            return;
        }
        self.last_observed_frame = Some(frame);

        let mut frame_counts: HashMap<FnId, usize> = HashMap::new();
        for (_, fn_id) in pending {
            *frame_counts.entry(*fn_id).or_default() += 1;
        }

        for function in env.core().fns().iter() {
            let history = self
                .demand_history
                .entry(function.fn_id)
                .or_insert_with(|| VecDeque::with_capacity(DEMAND_WINDOW));
            history.push_back(frame_counts.get(&function.fn_id).copied().unwrap_or(0) as f64);
            while history.len() > DEMAND_WINDOW {
                history.pop_front();
            }
            self.predicted_demand
                .insert(function.fn_id, forecast_demand(history));
        }
    }

    fn node_rank_key(
        &self,
        fn_id: FnId,
        node_id: NodeId,
        env: &SimEnvObserve,
    ) -> (u8, f32, usize, NodeId) {
        let node = env.node(node_id);
        let container_rank = node
            .fn_containers
            .borrow()
            .get(&fn_id)
            .map(|container| match container.state() {
                FnContainerState::Running if container.req_fn_state.is_empty() => 0,
                FnContainerState::Running => 1,
                FnContainerState::Starting { .. } => 2,
            })
            .unwrap_or(3);
        let utilization = (safe_ratio(node.cpu, node.rsc_limit.cpu)
            + safe_ratio(node.unready_mem(), node.rsc_limit.mem))
            / 2.0;
        (container_rank, utilization, node.all_task_cnt(), node_id)
    }

    fn generate_pre_decisions(&mut self, pending: &[(ReqId, FnId)], env: &SimEnvObserve) {
        let active_pairs: HashSet<(ReqId, FnId)> = pending.iter().copied().collect();
        self.pre_decisions
            .retain(|pair, _| active_pairs.contains(pair));

        let requests = env.core().requests();
        for &(req_id, fn_id) in pending {
            let Some(req) = requests.get(&req_id) else {
                continue;
            };
            let mut candidates = schedule_helper::placement_candidate_ids(req, fn_id, env);
            candidates.sort_by(|left, right| {
                let left_key = self.node_rank_key(fn_id, *left, env);
                let right_key = self.node_rank_key(fn_id, *right, env);
                compare_rank_keys(left_key, right_key)
            });
            self.pre_decisions.insert((req_id, fn_id), candidates);
        }
    }

    fn select_pre_decided_node(
        &self,
        req_id: ReqId,
        fn_id: FnId,
        projected: &HashMap<NodeId, usize>,
        env: &SimEnvObserve,
    ) -> Option<NodeId> {
        let ranked = self.pre_decisions.get(&(req_id, fn_id))?;
        if ranked.is_empty() {
            return None;
        }

        // A higher forecast widens placement across more HPA-provisioned
        // workers; it never asks HPA to create those workers.
        let active_width = self
            .predicted_demand
            .get(&fn_id)
            .copied()
            .unwrap_or(1.0)
            .ceil()
            .max(1.0) as usize;
        ranked
            .iter()
            .take(active_width.min(ranked.len()))
            .enumerate()
            .min_by_key(|(rank, node_id)| {
                (
                    env.node(**node_id).all_task_cnt()
                        + projected.get(node_id).copied().unwrap_or(0),
                    *rank,
                    **node_id,
                )
            })
            .map(|(_, node_id)| *node_id)
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

fn forecast_demand(history: &VecDeque<f64>) -> f64 {
    if history.is_empty() {
        return 0.0;
    }
    let mean = history.iter().sum::<f64>() / history.len() as f64;
    let trend = if history.len() > 1 {
        (history.back().copied().unwrap_or(0.0) - history.front().copied().unwrap_or(0.0))
            / (history.len() - 1) as f64
    } else {
        0.0
    };
    (mean + 0.5 * trend).max(0.0)
}

fn compare_rank_keys(left: (u8, f32, usize, NodeId), right: (u8, f32, usize, NodeId)) -> Ordering {
    left.0
        .cmp(&right.0)
        .then_with(|| left.1.partial_cmp(&right.1).unwrap_or(Ordering::Equal))
        .then_with(|| left.2.cmp(&right.2))
        .then_with(|| left.3.cmp(&right.3))
}

impl Scheduler for JiaguScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        _mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        self.prune_request_state(env);
        let mut pending = self.collect_pending(env);
        self.update_prediction(&pending, env);
        self.generate_pre_decisions(&pending, env);

        pending.sort_by(|left, right| {
            self.predicted_demand
                .get(&right.1)
                .unwrap_or(&0.0)
                .partial_cmp(self.predicted_demand.get(&left.1).unwrap_or(&0.0))
                .unwrap_or(Ordering::Equal)
                .then_with(|| left.cmp(right))
        });

        let mut projected: HashMap<NodeId, usize> = HashMap::new();
        for (req_id, fn_id) in pending {
            let Some(node_id) = self.select_pre_decided_node(req_id, fn_id, &projected, env) else {
                continue;
            };
            match cmd_distributor.send(MechScheduleOnceRes::ScheCmd(ScheCmd {
                nid: node_id,
                reqid: req_id,
                fnid: fn_id,
                memlimit: None,
            })) {
                Ok(()) => {
                    self.scheduled_pairs.insert((req_id, fn_id));
                    *projected.entry(node_id).or_default() += 1;
                }
                Err(error) => log::warn!(
                    "Jiagu-P failed to place request {} function {} on node {}: {:?}",
                    req_id,
                    fn_id,
                    node_id,
                    error
                ),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn forecast_uses_mean_and_nonnegative_trend() {
        let increasing = VecDeque::from([1.0, 2.0, 3.0]);
        let flat = VecDeque::from([2.0, 2.0, 2.0]);
        assert!(forecast_demand(&increasing) > forecast_demand(&flat));
        assert_eq!(forecast_demand(&VecDeque::new()), 0.0);
    }

    #[test]
    fn rank_ties_are_resolved_by_node_id() {
        let left = (0, 0.2, 1, 3);
        let right = (0, 0.2, 1, 8);
        assert_eq!(compare_rank_keys(left, right), Ordering::Less);
    }
}
