use std::cmp::Ordering;

use crate::{
    fn_dag::{EnvFnExt, FnContainerState, FnId},
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::{ReqId, Request},
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::{WithEnvCore, WithEnvHelp},
};

const EPSILON: f32 = 1.0e-6;
const NORMALIZED_CAPACITY: f32 = 1.0;
const MIN_VALUE_DENSITY: f32 = 1.0;
const MAX_VALUE_DENSITY: f32 = 4.0;

#[derive(Clone, Copy, Debug)]
struct CandidateFeature {
    node_id: NodeId,
    warm_affinity: f32,
    data_locality: f32,
}

#[derive(Clone, Debug)]
struct Player {
    req_id: ReqId,
    fn_id: FnId,
    quality_weight: f32,
    /// Every entry comes from `placement_candidate_ids`; OnSocMax-P cannot
    /// create a container or widen the common feasible set.
    candidates: Vec<CandidateFeature>,
}

/// Placement-only adaptation of OnSocMax for indivisible function requests.
///
/// The adaptation retains Algorithm 1's online arrival order, utilization
/// update, and Eq. (22) marginal scarcity price.  Continuous workload
/// splitting and the original time-expanded resource mesh are intentionally
/// outside this shared-HPA placement experiment.
pub struct OnSocMaxScheduler {
    competitive_ratio: f32,
}

impl OnSocMaxScheduler {
    pub fn new() -> Self {
        Self {
            competitive_ratio: solve_competitive_ratio(MIN_VALUE_DENSITY, MAX_VALUE_DENSITY),
        }
    }

    fn collect_players(&self, env: &SimEnvObserve) -> Vec<Player> {
        let requests = env.core().requests();
        let mut players = Vec::new();
        for request in requests.values() {
            for fn_id in schedule_helper::collect_task_to_sche(
                request,
                env,
                schedule_helper::CollectTaskConfig::All,
            ) {
                let candidate_ids = schedule_helper::placement_candidate_ids(request, fn_id, env);
                let candidates = candidate_ids
                    .into_iter()
                    .map(|node_id| CandidateFeature {
                        node_id,
                        warm_affinity: warm_affinity(fn_id, node_id, env),
                        data_locality: data_locality(request, fn_id, node_id, env),
                    })
                    .collect::<Vec<_>>();
                if candidates.is_empty() {
                    continue;
                }
                players.push(Player {
                    req_id: request.req_id,
                    fn_id,
                    quality_weight: if env.help().config().experiment.qos.enabled {
                        env.func(fn_id).quality_weight
                    } else {
                        env.help()
                            .config()
                            .experiment
                            .nash
                            .quality_weight
                            .unwrap_or_else(|| {
                                if env.help().config().request_freq_low() {
                                    0.5
                                } else {
                                    0.6
                                }
                            })
                    }
                    .clamp(0.0, 1.0),
                    candidates,
                });
            }
        }

        // ReqId follows arrival order.  FnId is the deterministic within-job
        // tie-break when several functions become schedulable together.
        players.sort_by_key(|player| (player.req_id, player.fn_id));
        players.dedup_by_key(|player| (player.req_id, player.fn_id));
        players
    }

    fn initial_resource_usage(&self, env: &SimEnvObserve) -> Vec<f32> {
        let mut usage = {
            let nodes = env.nodes();
            nodes
                .iter()
                .map(|node| {
                    safe_ratio(node.cpu, node.rsc_limit.cpu)
                        .max(safe_ratio(node.unready_mem(), node.rsc_limit.mem))
                })
                .collect::<Vec<_>>()
        };

        // CPU is shared rather than reserved in this simulator.  Account for
        // the indivisible active workloads explicitly so queued work is not
        // mistaken for unused capacity when current-frame CPU happens to be 0.
        let mut active_workload = vec![0.0_f32; usage.len()];
        let requests = env.core().requests();
        for request in requests.values() {
            for (&fn_id, &node_id) in &request.fn_node {
                if request.done_fns.contains_key(&fn_id) || node_id >= active_workload.len() {
                    continue;
                }
                active_workload[node_id] += normalized_workload(fn_id, node_id, env);
            }
        }
        for (node_id, workload) in active_workload.into_iter().enumerate() {
            usage[node_id] = usage[node_id].max(workload);
        }
        usage
    }

    fn select_node(
        &self,
        player: &Player,
        resource_usage: &[f32],
        env: &SimEnvObserve,
    ) -> Option<NodeId> {
        let mut best = None;
        for candidate in &player.candidates {
            let demand = normalized_workload(player.fn_id, candidate.node_id, env);
            let after_usage = resource_usage
                .get(candidate.node_id)
                .copied()
                .unwrap_or(f32::INFINITY)
                + demand;
            let price = marginal_cost_eq22(
                after_usage,
                NORMALIZED_CAPACITY,
                MIN_VALUE_DENSITY,
                MAX_VALUE_DENSITY,
                self.competitive_ratio,
            );
            let density = placement_value_density(
                player.quality_weight,
                candidate.warm_affinity,
                candidate.data_locality,
                demand,
            );
            // Binary/non-fractional specialization of the Algorithm 1 choice:
            // select the resource with the largest marginal pseudo-welfare.
            let pseudo_welfare = if price.is_finite() {
                (density - price) * demand
            } else {
                f32::NEG_INFINITY
            };
            let scored_candidate = (candidate.node_id, pseudo_welfare, after_usage);
            if candidate_is_better(scored_candidate, best) {
                best = Some(scored_candidate);
            }
        }
        best.map(|(node_id, _, _)| node_id)
    }
}

impl Default for OnSocMaxScheduler {
    fn default() -> Self {
        Self::new()
    }
}

impl Scheduler for OnSocMaxScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        _mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        let players = self.collect_players(env);
        if players.is_empty() {
            return;
        }
        let mut resource_usage = self.initial_resource_usage(env);

        for player in players {
            let Some(node_id) = self.select_node(&player, &resource_usage, env) else {
                continue;
            };
            let demand = normalized_workload(player.fn_id, node_id, env);
            // Algorithm 1, line 7: update utilization immediately after the
            // irrevocable online placement decision.
            resource_usage[node_id] += demand;
            if let Err(error) =
                cmd_distributor.send(placement_command(node_id, player.req_id, player.fn_id))
            {
                log::warn!(
                    "OnSocMax-P failed to place request {} function {} on node {}: {:?}",
                    player.req_id,
                    player.fn_id,
                    node_id,
                    error
                );
            }
        }
    }
}

fn safe_ratio(numerator: f32, denominator: f32) -> f32 {
    if denominator <= EPSILON {
        1.0
    } else {
        (numerator / denominator).clamp(0.0, 1.0)
    }
}

fn normalized_workload(fn_id: FnId, node_id: NodeId, env: &SimEnvObserve) -> f32 {
    let function = env.func(fn_id);
    let node = env.node(node_id);
    safe_ratio(function.cpu, node.rsc_limit.cpu)
        .max(safe_ratio(function.mem, node.rsc_limit.mem))
        .max(EPSILON)
}

fn warm_affinity(fn_id: FnId, node_id: NodeId, env: &SimEnvObserve) -> f32 {
    let node = env.node(node_id);
    let Some(container) = node.container(fn_id) else {
        return 0.0;
    };
    match container.state() {
        FnContainerState::Starting { .. } => 0.25,
        FnContainerState::Running if container.is_idle() => 1.0,
        FnContainerState::Running => 0.65,
    }
}

fn data_locality(request: &Request, fn_id: FnId, node_id: NodeId, env: &SimEnvObserve) -> f32 {
    let parents = env.func(fn_id).parent_fns(env);
    let mut score_sum = 0.0_f32;
    let mut placed_parents = 0_usize;
    for parent_id in parents {
        let Some(parent_node) = request.fn_node.get(&parent_id).copied() else {
            continue;
        };
        placed_parents += 1;
        if parent_node == node_id {
            score_sum += 1.0;
        } else {
            let bandwidth_mb_s = env.node_get_speed_btwn(parent_node, node_id);
            let delay_ms = if bandwidth_mb_s > EPSILON {
                env.func(parent_id).out_put_size / bandwidth_mb_s * 1000.0
            } else {
                f32::INFINITY
            };
            score_sum += if delay_ms.is_finite() {
                1.0 / (1.0 + delay_ms)
            } else {
                0.0
            };
        }
    }
    if placed_parents == 0 {
        1.0
    } else {
        (score_sum / placed_parents as f32).clamp(0.0, 1.0)
    }
}

/// Stable quality/cost proxy for the paper's marginal value density.  The
/// bounds are the same iota/upsilon used by Eq. (22); demand is a direct
/// resource-cost penalty, while quality, warm execution, and locality provide
/// placement-dependent value.
fn placement_value_density(
    quality_weight: f32,
    warm_affinity: f32,
    data_locality: f32,
    normalized_demand: f32,
) -> f32 {
    let proxy = (0.55 * quality_weight.clamp(0.0, 1.0)
        + 0.25 * warm_affinity.clamp(0.0, 1.0)
        + 0.20 * data_locality.clamp(0.0, 1.0)
        - 0.20 * normalized_demand.clamp(0.0, 1.0))
    .clamp(0.0, 1.0);
    MIN_VALUE_DENSITY + (MAX_VALUE_DENSITY - MIN_VALUE_DENSITY) * proxy
}

/// Solve Eq. (37) for the alpha used by Eq. (22).  The paper establishes
/// alpha >= 2.  Bisection is deterministic and executed only at construction.
fn solve_competitive_ratio(iota: f32, upsilon: f32) -> f32 {
    let ratio = (upsilon / iota.max(EPSILON)).max(1.0 + EPSILON);
    let residual =
        |alpha: f32| alpha - alpha / (alpha - 1.0) - ((alpha * ratio - 1.0) / (alpha - 1.0)).ln();
    let mut low = 2.0_f32;
    let mut high = 8.0_f32;
    while residual(high) < 0.0 && high < 1_024.0 {
        high *= 2.0;
    }
    for _ in 0..80 {
        let middle = (low + high) * 0.5;
        if residual(middle) < 0.0 {
            low = middle;
        } else {
            high = middle;
        }
    }
    (low + high) * 0.5
}

/// Marginal resource cost from OnSocMax Eq. (22), with normalized C_r.
fn marginal_cost_eq22(omega: f32, capacity: f32, iota: f32, upsilon: f32, alpha: f32) -> f32 {
    if !omega.is_finite() || !capacity.is_finite() || capacity <= EPSILON {
        return f32::INFINITY;
    }
    if omega > capacity + EPSILON {
        return f32::INFINITY;
    }
    let bounded_omega = omega.max(0.0);
    let threshold = capacity / (alpha - 1.0);
    if bounded_omega < threshold {
        return iota;
    }
    let denominator = alpha.exp() - (alpha / (alpha - 1.0)).exp();
    if denominator <= EPSILON {
        return f32::INFINITY;
    }
    let increasing =
        (upsilon - iota) / denominator * (alpha * bounded_omega / capacity).exp() + iota / alpha;
    if increasing.is_finite() {
        increasing.max(iota)
    } else {
        f32::INFINITY
    }
}

/// Prefer larger pseudo-welfare.  If Eq. (22) marks every candidate as over
/// capacity (+infinity), the common runtime's queue-by-design semantics do not
/// permit admission rejection, so the least-overflow candidate is selected.
/// Remaining ties use the smaller node id.
fn candidate_is_better(candidate: (NodeId, f32, f32), best: Option<(NodeId, f32, f32)>) -> bool {
    let (node_id, raw_score, after_usage) = candidate;
    let score = if raw_score.is_nan() {
        f32::NEG_INFINITY
    } else {
        raw_score
    };
    match best {
        None => true,
        Some((best_node, raw_best_score, best_after)) => {
            let best_score = if raw_best_score.is_nan() {
                f32::NEG_INFINITY
            } else {
                raw_best_score
            };
            match score.partial_cmp(&best_score).unwrap_or(Ordering::Equal) {
                Ordering::Greater => true,
                Ordering::Less => false,
                Ordering::Equal => {
                    after_usage < best_after - EPSILON
                        || ((after_usage - best_after).abs() <= EPSILON && node_id < best_node)
                }
            }
        }
    }
}

fn placement_command(node_id: NodeId, req_id: ReqId, fn_id: FnId) -> MechScheduleOnceRes {
    MechScheduleOnceRes::ScheCmd(ScheCmd {
        nid: node_id,
        reqid: req_id,
        fnid: fn_id,
        memlimit: None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn select(scored: &[(NodeId, f32, f32)]) -> Option<NodeId> {
        let mut best = None;
        for &candidate in scored {
            if candidate_is_better(candidate, best) {
                best = Some(candidate);
            }
        }
        best.map(|(node_id, _, _)| node_id)
    }

    #[test]
    fn eq37_solver_has_small_residual() {
        let alpha = solve_competitive_ratio(MIN_VALUE_DENSITY, MAX_VALUE_DENSITY);
        let ratio = MAX_VALUE_DENSITY / MIN_VALUE_DENSITY;
        let residual = alpha - alpha / (alpha - 1.0) - ((alpha * ratio - 1.0) / (alpha - 1.0)).ln();
        assert!(alpha >= 2.0);
        assert!(
            residual.abs() < 1.0e-5,
            "alpha={alpha}, residual={residual}"
        );
    }

    #[test]
    fn eq22_price_is_nondecreasing_and_infinite_above_capacity() {
        let alpha = solve_competitive_ratio(MIN_VALUE_DENSITY, MAX_VALUE_DENSITY);
        let samples = [0.0, 0.2, 0.5, 0.8, 1.0].map(|omega| {
            marginal_cost_eq22(
                omega,
                NORMALIZED_CAPACITY,
                MIN_VALUE_DENSITY,
                MAX_VALUE_DENSITY,
                alpha,
            )
        });
        assert!(samples.windows(2).all(|pair| pair[1] + EPSILON >= pair[0]));
        assert!(marginal_cost_eq22(
            1.01,
            NORMALIZED_CAPACITY,
            MIN_VALUE_DENSITY,
            MAX_VALUE_DENSITY,
            alpha,
        )
        .is_infinite());
    }

    #[test]
    fn selection_is_deterministic_and_stays_in_common_candidate_set() {
        let common_candidates = [(9, 0.5, 0.7), (3, 0.5, 0.7), (1, 0.1, 0.2)];
        let selected = select(&common_candidates).expect("candidate selection");
        assert_eq!(selected, 3);
        assert!(common_candidates
            .iter()
            .any(|(node_id, _, _)| *node_id == selected));
    }

    #[test]
    fn overflow_fallback_chooses_least_overflow_then_node_id() {
        let scored = [
            (8, f32::NEG_INFINITY, 1.4),
            (5, f32::NEG_INFINITY, 1.2),
            (2, f32::NEG_INFINITY, 1.2),
        ];
        assert_eq!(select(&scored), Some(2));
    }

    #[test]
    fn command_constructor_emits_only_a_placement_command() {
        match placement_command(3, 5, 7) {
            MechScheduleOnceRes::ScheCmd(command) => {
                assert_eq!((command.nid, command.reqid, command.fnid), (3, 5, 7));
            }
            _ => panic!("OnSocMax-P must emit ScheCmd only"),
        }
    }

    #[test]
    fn quality_proxy_rewards_quality_and_penalizes_demand() {
        let high_quality = placement_value_density(0.9, 1.0, 1.0, 0.1);
        let low_quality = placement_value_density(0.2, 1.0, 1.0, 0.1);
        let high_demand = placement_value_density(0.9, 1.0, 1.0, 0.9);
        assert!(high_quality > low_quality);
        assert!(high_quality > high_demand);
    }
}
