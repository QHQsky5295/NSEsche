use std::{
    cmp::Ordering,
    collections::{HashMap, HashSet, VecDeque},
};

use crate::{
    config::FaaSRankModelConfig,
    fn_dag::{EnvFnExt, FnContainerState, FnId},
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::{ReqId, Request},
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::{WithEnvCore, WithEnvHelp},
};

const DECISION_HISTORY_LIMIT: usize = 256;

#[derive(Clone, Debug)]
struct ScoringWeights {
    cpu_headroom: f32,
    memory_headroom: f32,
    network_locality: f32,
    warm_affinity: f32,
    load_balance: f32,
    diversity_penalty: f32,
}

impl From<&FaaSRankModelConfig> for ScoringWeights {
    fn from(model: &FaaSRankModelConfig) -> Self {
        Self {
            cpu_headroom: model.cpu_headroom,
            memory_headroom: model.memory_headroom,
            network_locality: model.network_locality,
            warm_affinity: model.warm_affinity,
            load_balance: model.load_balance,
            diversity_penalty: model.diversity_penalty,
        }
    }
}

/// Placement-only FaaSRank adaptation implementing Score-Rank-Select.
///
/// Candidate selection is constrained to workers provisioned by the shared
/// HPA.  Epsilon diversity is deterministic for a fixed simulator seed and
/// request stream; no process-global random source is used.
pub struct FaaSRankScheduler {
    weights: ScoringWeights,
    epsilon: f32,
    decision_history: VecDeque<(FnId, NodeId)>,
    scheduled_pairs: HashSet<(ReqId, FnId)>,
}

impl FaaSRankScheduler {
    pub fn new(model: &FaaSRankModelConfig) -> Self {
        Self {
            weights: ScoringWeights::from(model),
            epsilon: model.epsilon,
            decision_history: VecDeque::with_capacity(DECISION_HISTORY_LIMIT),
            scheduled_pairs: HashSet::new(),
        }
    }

    fn network_locality(
        &self,
        req: &Request,
        fn_id: FnId,
        node_id: NodeId,
        env: &SimEnvObserve,
    ) -> f32 {
        let mut transfer_time = 0.0_f32;
        let mut placed_parents = 0_usize;
        for parent_id in env.func(fn_id).parent_fns(env) {
            let Some(&parent_node) = req.fn_node.get(&parent_id) else {
                continue;
            };
            placed_parents += 1;
            if parent_node != node_id {
                let bandwidth = env
                    .node_get_speed_btwn(parent_node, node_id)
                    .max(f32::EPSILON);
                transfer_time += env.func(parent_id).out_put_size / bandwidth;
            }
        }
        if placed_parents == 0 {
            1.0
        } else {
            1.0 / (1.0 + transfer_time)
        }
    }

    fn recent_selection_fraction(&self, fn_id: FnId, node_id: NodeId) -> f32 {
        let mut function_decisions = 0_usize;
        let mut node_decisions = 0_usize;
        for &(seen_fn, seen_node) in &self.decision_history {
            if seen_fn == fn_id {
                function_decisions += 1;
                if seen_node == node_id {
                    node_decisions += 1;
                }
            }
        }
        if function_decisions == 0 {
            0.0
        } else {
            node_decisions as f32 / function_decisions as f32
        }
    }

    fn calculate_node_score(
        &self,
        req: &Request,
        fn_id: FnId,
        node_id: NodeId,
        projected_assignments: usize,
        env: &SimEnvObserve,
    ) -> f32 {
        let node = env.node(node_id);
        let cpu_headroom = 1.0 - safe_ratio(node.cpu, node.rsc_limit.cpu);
        let memory_headroom = 1.0 - safe_ratio(node.unready_mem(), node.rsc_limit.mem);
        let load_balance = 1.0 / (1.0 + node.all_task_cnt() as f32 + projected_assignments as f32);
        let warm_affinity = node
            .fn_containers
            .borrow()
            .get(&fn_id)
            .map(|container| match container.state() {
                FnContainerState::Running => 1.0,
                FnContainerState::Starting { .. } => 0.2,
            })
            .unwrap_or(0.0);

        self.weights.cpu_headroom * cpu_headroom
            + self.weights.memory_headroom * memory_headroom
            + self.weights.network_locality * self.network_locality(req, fn_id, node_id, env)
            + self.weights.warm_affinity * warm_affinity
            + self.weights.load_balance * load_balance
            - self.weights.diversity_penalty * self.recent_selection_fraction(fn_id, node_id)
    }

    fn score_and_rank(
        &self,
        req: &Request,
        fn_id: FnId,
        projected: &HashMap<NodeId, usize>,
        env: &SimEnvObserve,
    ) -> Vec<(NodeId, f32)> {
        let mut ranked: Vec<(NodeId, f32)> =
            schedule_helper::placement_candidate_ids(req, fn_id, env)
                .into_iter()
                .map(|node_id| {
                    (
                        node_id,
                        self.calculate_node_score(
                            req,
                            fn_id,
                            node_id,
                            projected.get(&node_id).copied().unwrap_or(0),
                            env,
                        ),
                    )
                })
                .collect();
        ranked.sort_by(|left, right| compare_ranked_nodes(*left, *right));
        ranked
    }

    fn select_ranked_node(
        &self,
        ranked: &[(NodeId, f32)],
        req_id: ReqId,
        fn_id: FnId,
        env: &SimEnvObserve,
    ) -> Option<NodeId> {
        if ranked.is_empty() {
            return None;
        }
        let seed = env.help().config().algorithm_seed();
        let frame = env.core().current_frame() as u64;
        let explore_hash = stable_hash(seed, &[frame, req_id as u64, fn_id as u64, 0]);
        let selected_index = if unit_interval(explore_hash) < self.epsilon {
            stable_hash(seed, &[frame, req_id as u64, fn_id as u64, 1]) as usize % ranked.len()
        } else {
            0
        };
        Some(ranked[selected_index].0)
    }

    fn record_decision(&mut self, fn_id: FnId, node_id: NodeId) {
        self.decision_history.push_back((fn_id, node_id));
        while self.decision_history.len() > DECISION_HISTORY_LIMIT {
            self.decision_history.pop_front();
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

/// Descending score, then ascending node id.
fn compare_ranked_nodes(left: (NodeId, f32), right: (NodeId, f32)) -> Ordering {
    right
        .1
        .partial_cmp(&left.1)
        .unwrap_or(Ordering::Equal)
        .then_with(|| left.0.cmp(&right.0))
}

fn stable_hash(seed: &str, values: &[u64]) -> u64 {
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in seed
        .as_bytes()
        .iter()
        .copied()
        .chain(values.iter().flat_map(|value| value.to_le_bytes()))
    {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

fn unit_interval(hash: u64) -> f32 {
    ((hash >> 40) as f32) / ((1_u32 << 24) as f32)
}

impl Scheduler for FaaSRankScheduler {
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
                schedule_helper::CollectTaskConfig::PreAllDone,
            );
            for fn_id in functions {
                let key = (req.req_id, fn_id);
                if self.scheduled_pairs.contains(&key) {
                    continue;
                }

                let ranked = self.score_and_rank(req, fn_id, &projected, env);
                let Some(node_id) = self.select_ranked_node(&ranked, req.req_id, fn_id, env) else {
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
                        self.record_decision(fn_id, node_id);
                        *projected.entry(node_id).or_default() += 1;
                    }
                    Err(error) => log::warn!(
                        "FaaSRank-P failed to place request {} function {} on node {}: {:?}",
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
    fn legacy_model_defaults_preserve_previous_coefficients() {
        let scheduler = FaaSRankScheduler::new(&FaaSRankModelConfig::default());
        assert_eq!(scheduler.weights.cpu_headroom, 0.25);
        assert_eq!(scheduler.weights.memory_headroom, 0.20);
        assert_eq!(scheduler.weights.network_locality, 0.15);
        assert_eq!(scheduler.weights.warm_affinity, 0.25);
        assert_eq!(scheduler.weights.load_balance, 0.15);
        assert_eq!(scheduler.weights.diversity_penalty, 0.05);
        assert_eq!(scheduler.epsilon, 0.1);
    }

    #[test]
    fn configured_frozen_coefficients_are_loaded_without_training_updates() {
        let model = FaaSRankModelConfig {
            state: "frozen".to_string(),
            model_sha256: "a".repeat(64),
            training_tape_sha256: "b".repeat(64),
            cpu_headroom: 1.0,
            memory_headroom: 2.0,
            network_locality: 3.0,
            warm_affinity: 4.0,
            load_balance: 5.0,
            diversity_penalty: 6.0,
            epsilon: 0.2,
        };
        let scheduler = FaaSRankScheduler::new(&model);
        assert_eq!(scheduler.weights.cpu_headroom, 1.0);
        assert_eq!(scheduler.weights.memory_headroom, 2.0);
        assert_eq!(scheduler.weights.network_locality, 3.0);
        assert_eq!(scheduler.weights.warm_affinity, 4.0);
        assert_eq!(scheduler.weights.load_balance, 5.0);
        assert_eq!(scheduler.weights.diversity_penalty, 6.0);
        assert_eq!(scheduler.epsilon, 0.2);
    }

    #[test]
    fn seeded_selection_hash_is_reproducible() {
        let context = [12, 34, 56, 0];
        assert_eq!(
            stable_hash("experiment-7", &context),
            stable_hash("experiment-7", &context)
        );
        assert_ne!(
            stable_hash("experiment-7", &context),
            stable_hash("experiment-8", &context)
        );
    }

    #[test]
    fn ranking_ties_prefer_smaller_node_id() {
        let mut ranked = vec![(9, 0.8), (2, 0.8), (4, 0.9)];
        ranked.sort_by(|left, right| compare_ranked_nodes(*left, *right));
        assert_eq!(ranked, vec![(4, 0.9), (2, 0.8), (9, 0.8)]);
    }

    #[test]
    fn unit_interval_is_bounded() {
        assert!((0.0..1.0).contains(&unit_interval(u64::MAX)));
        assert_eq!(unit_interval(0), 0.0);
    }
}
