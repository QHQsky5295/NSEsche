use std::{
    cmp::Ordering,
    collections::{HashMap, HashSet},
};

use crate::{
    fn_dag::{EnvFnExt, FnContainerState, FnId},
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::{ReqId, Request},
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::WithEnvCore,
};

/// ORION-inspired placement weights.  These weights affect request placement
/// only; scaling, prewarming, and container lifecycle are owned by the common
/// mechanism used by every evaluated scheduler.
#[derive(Clone, Debug)]
pub struct OrionConfig {
    pub resource_headroom_weight: f32,
    pub warm_affinity_weight: f32,
    pub load_balance_weight: f32,
    pub network_locality_weight: f32,
}

impl Default for OrionConfig {
    fn default() -> Self {
        Self {
            resource_headroom_weight: 0.4,
            warm_affinity_weight: 0.3,
            load_balance_weight: 0.2,
            network_locality_weight: 0.1,
        }
    }
}

/// Placement-only adaptation of ORION.
///
/// The scheduler retains critical-path ordering and data-locality-aware node
/// ranking.  It deliberately emits `ScheCmd` only: the shared HPA is the sole
/// owner of instance counts, prewarming, cold starts, and eviction.
pub struct OrionScheduler {
    config: OrionConfig,
    critical_path_rank: HashMap<ReqId, HashMap<FnId, f32>>,
    scheduled_pairs: HashSet<(ReqId, FnId)>,
}

impl OrionScheduler {
    pub fn new() -> Self {
        Self {
            config: OrionConfig::default(),
            critical_path_rank: HashMap::new(),
            scheduled_pairs: HashSet::new(),
        }
    }

    fn build_critical_path_rank(&self, req: &Request, env: &SimEnvObserve) -> HashMap<FnId, f32> {
        let dag = env.dag(req.dag_i);
        let mut walker = dag.new_dag_walker();
        let mut topological_order = Vec::new();
        while let Some(index) = walker.next(&dag.dag_inner) {
            topological_order.push(dag.dag_inner[index]);
        }

        let node_count = env.node_cnt().max(1) as f32;
        let average_cpu = (env
            .nodes()
            .iter()
            .map(|node| node.rsc_limit.cpu)
            .sum::<f32>()
            / node_count)
            .max(f32::EPSILON);

        let mut ranks = HashMap::new();
        for fn_id in topological_order.into_iter().rev() {
            let function = env.func(fn_id);
            let execution_cost = function.cpu / average_cpu;
            // Retain the simulator's legacy 1000 MB/s reference used by the
            // original adaptation.  Runtime node ranking below uses the
            // simulator's actual node-to-node bandwidth matrix.
            let transfer_cost = function.out_put_size / 1000.0;
            let largest_child_rank = function
                .sub_fns(env)
                .into_iter()
                .filter_map(|child| ranks.get(&child).copied())
                .fold(0.0_f32, f32::max);
            ranks.insert(fn_id, execution_cost + transfer_cost + largest_child_rank);
        }
        ranks
    }

    fn network_locality_score(
        &self,
        req: &Request,
        fn_id: FnId,
        node_id: NodeId,
        planned_placements: &HashMap<(ReqId, FnId), NodeId>,
        env: &SimEnvObserve,
    ) -> f32 {
        let mut transfer_time = 0.0_f32;
        let mut placed_parent_count = 0_usize;
        for parent_id in env.func(fn_id).parent_fns(env) {
            let parent_node = req
                .fn_node
                .get(&parent_id)
                .copied()
                .or_else(|| planned_placements.get(&(req.req_id, parent_id)).copied());
            let Some(parent_node) = parent_node else {
                continue;
            };
            placed_parent_count += 1;
            if parent_node != node_id {
                let bandwidth = env
                    .node_get_speed_btwn(parent_node, node_id)
                    .max(f32::EPSILON);
                transfer_time += env.func(parent_id).out_put_size / bandwidth;
            }
        }

        if placed_parent_count == 0 {
            1.0
        } else {
            1.0 / (1.0 + transfer_time)
        }
    }

    fn node_score(
        &self,
        req: &Request,
        fn_id: FnId,
        node_id: NodeId,
        projected_assignments: usize,
        planned_placements: &HashMap<(ReqId, FnId), NodeId>,
        env: &SimEnvObserve,
    ) -> f32 {
        let node = env.node(node_id);
        let cpu_utilization = safe_ratio(node.cpu, node.rsc_limit.cpu);
        let memory_utilization = safe_ratio(node.unready_mem(), node.rsc_limit.mem);
        let resource_headroom = 1.0 - (cpu_utilization + memory_utilization) / 2.0;
        let load_score = 1.0 / (1.0 + node.all_task_cnt() as f32 + projected_assignments as f32);

        let warm_affinity = node
            .fn_containers
            .borrow()
            .get(&fn_id)
            .map(|container| match container.state() {
                FnContainerState::Running => 1.0,
                FnContainerState::Starting { .. } => 0.25,
            })
            .unwrap_or(0.0);

        self.config.resource_headroom_weight * resource_headroom
            + self.config.warm_affinity_weight * warm_affinity
            + self.config.load_balance_weight * load_score
            + self.config.network_locality_weight
                * self.network_locality_score(req, fn_id, node_id, planned_placements, env)
    }

    fn select_best_node(
        &self,
        req: &Request,
        fn_id: FnId,
        projected: &HashMap<NodeId, usize>,
        planned_placements: &HashMap<(ReqId, FnId), NodeId>,
        env: &SimEnvObserve,
    ) -> Option<NodeId> {
        schedule_helper::placement_candidate_ids(req, fn_id, env)
            .into_iter()
            .map(|node_id| {
                let score = self.node_score(
                    req,
                    fn_id,
                    node_id,
                    projected.get(&node_id).copied().unwrap_or(0),
                    planned_placements,
                    env,
                );
                (node_id, score)
            })
            .max_by(|left, right| compare_scored_nodes(*left, *right))
            .map(|(node_id, _)| node_id)
    }

    fn prune_request_state(&mut self, env: &SimEnvObserve) {
        let active: HashSet<ReqId> = env.core().requests().keys().copied().collect();
        self.critical_path_rank
            .retain(|req_id, _| active.contains(req_id));
        // Commands are drained before the next scheduler step.  Clear the
        // in-flight guard so a placement rejected after a concurrent HPA
        // scale-down can be retried against the next snapshot.
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

fn compare_scored_nodes(left: (NodeId, f32), right: (NodeId, f32)) -> Ordering {
    left.1
        .partial_cmp(&right.1)
        .unwrap_or(Ordering::Equal)
        // `max_by` should choose the smaller node id on an exact score tie.
        .then_with(|| right.0.cmp(&left.0))
}

impl Scheduler for OrionScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        _mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        self.prune_request_state(env);
        let mut projected_assignments: HashMap<NodeId, usize> = HashMap::new();
        let mut planned_placements: HashMap<(ReqId, FnId), NodeId> = HashMap::new();

        for (_, req) in env.core().requests().iter() {
            if !self.critical_path_rank.contains_key(&req.req_id) {
                let ranks = self.build_critical_path_rank(req, env);
                self.critical_path_rank.insert(req.req_id, ranks);
            }

            let mut functions = schedule_helper::collect_task_to_sche(
                req,
                env,
                schedule_helper::CollectTaskConfig::All,
            );
            let ranks = self
                .critical_path_rank
                .get(&req.req_id)
                .expect("ORION critical-path rank must exist");
            functions.sort_by(|left, right| {
                ranks
                    .get(right)
                    .unwrap_or(&0.0)
                    .partial_cmp(ranks.get(left).unwrap_or(&0.0))
                    .unwrap_or(Ordering::Equal)
                    .then_with(|| left.cmp(right))
            });

            for fn_id in functions {
                let key = (req.req_id, fn_id);
                if self.scheduled_pairs.contains(&key) {
                    continue;
                }
                let Some(node_id) = self.select_best_node(
                    req,
                    fn_id,
                    &projected_assignments,
                    &planned_placements,
                    env,
                ) else {
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
                        *projected_assignments.entry(node_id).or_default() += 1;
                        planned_placements.insert(key, node_id);
                    }
                    Err(error) => log::warn!(
                        "ORION-P failed to place request {} function {} on node {}: {:?}",
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
    fn score_ties_prefer_smaller_node_id() {
        let selected = [(7, 0.5), (2, 0.5)]
            .into_iter()
            .max_by(|left, right| compare_scored_nodes(*left, *right));
        assert_eq!(selected, Some((2, 0.5)));
    }

    #[test]
    fn safe_ratio_handles_zero_capacity() {
        assert_eq!(safe_ratio(0.0, 0.0), 1.0);
        assert_eq!(safe_ratio(5.0, 10.0), 0.5);
    }
}
