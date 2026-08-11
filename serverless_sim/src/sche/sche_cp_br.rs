use std::collections::HashMap;

use crate::{
    fn_dag::FnId,
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::ReqId,
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::{WithEnvCore, WithEnvHelp},
};

const EPSILON: f32 = 1.0e-6;
const BASE_NODE_PRICE: f32 = 0.3;
const BASE_UTILITY: f32 = 10.0;
const QUEUE_NORMALIZER: f32 = 12.0;
const MAX_BEST_RESPONSE_ROUNDS: usize = 4;
const DAG_COMPLEXITY_NORMALIZER: f32 = 4.605_170_2; // ln(100)

#[derive(Clone, Copy, Debug)]
struct FunctionProfile {
    resource_intensity: f32,
    function_complexity: f32,
    network_dependency: f32,
    quality_weight: f32,
}

#[derive(Clone, Copy, Debug, Default)]
struct NodeSignal {
    pressure: f32,
    utilization: f32,
    existing_count: usize,
    existing_intensity_sum: f32,
}

#[derive(Clone, Copy, Debug, Default)]
struct ProvisionalLoad {
    count: usize,
    intensity_sum: f32,
}

#[derive(Clone, Debug)]
struct Player {
    req_id: ReqId,
    fn_id: FnId,
    profile: FunctionProfile,
    /// This list is obtained exclusively from the shared candidate filter.
    candidates: Vec<NodeId>,
}

/// Congestion-pricing best-response comparator constructed for this study.
///
/// CP-BR deliberately contains no social-welfare reference and no outer price
/// feedback loop.  It reuses the pressure and baseline congestion-price signal
/// of NSESche and runs only the individual best-response stage.  It is a
/// mechanism-matched reference, not a reproduction of a separately published
/// end-to-end system.
pub struct CPBRScheduler {
    function_profiles: HashMap<FnId, FunctionProfile>,
}

impl CPBRScheduler {
    pub fn new() -> Self {
        Self {
            function_profiles: HashMap::new(),
        }
    }

    fn ensure_function_profiles(&mut self, env: &SimEnvObserve) {
        let functions = env.core().fns();
        if self.function_profiles.len() == functions.len() {
            return;
        }
        let dags = env.core().dags();
        let max_cpu = functions
            .iter()
            .map(|function| function.cpu)
            .fold(EPSILON, f32::max);
        let max_memory = functions
            .iter()
            .map(|function| function.mem)
            .fold(EPSILON, f32::max);

        self.function_profiles = functions
            .iter()
            .map(|function| {
                let normalized_cpu = (function.cpu / max_cpu).max(0.0);
                let normalized_memory = (function.mem / max_memory).max(0.0);
                let resource_intensity = resource_intensity(normalized_cpu, normalized_memory);
                let dag_size = dags
                    .get(function.dag_id)
                    .map(|dag| dag.dag_inner.node_count())
                    .unwrap_or(1)
                    .max(1);
                let function_complexity = ((dag_size as f32).ln() / DAG_COMPLEXITY_NORMALIZER)
                    .tanh()
                    .clamp(0.0, 1.0);
                let network_dependency = (resource_intensity * function_complexity)
                    .sqrt()
                    .clamp(0.0, 1.0);
                (
                    function.fn_id,
                    FunctionProfile {
                        resource_intensity,
                        function_complexity,
                        network_dependency,
                        quality_weight: if env.help().config().experiment.qos.enabled {
                            function.quality_weight.max(0.0)
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
                                .max(0.0)
                        },
                    },
                )
            })
            .collect();
    }

    fn collect_players(
        &self,
        env: &SimEnvObserve,
        profiles: &HashMap<FnId, FunctionProfile>,
    ) -> Vec<Player> {
        let requests = env.core().requests();
        let mut players = Vec::new();
        for request in requests.values() {
            for fn_id in schedule_helper::collect_task_to_sche(
                request,
                env,
                schedule_helper::CollectTaskConfig::All,
            ) {
                let Some(profile) = profiles.get(&fn_id).copied() else {
                    continue;
                };
                let candidates = schedule_helper::placement_candidate_ids(request, fn_id, env);
                if !candidates.is_empty() {
                    players.push(Player {
                        req_id: request.req_id,
                        fn_id,
                        profile,
                        candidates,
                    });
                }
            }
        }
        players.sort_by_key(|player| (player.req_id, player.fn_id));
        players.dedup_by_key(|player| (player.req_id, player.fn_id));
        players
    }

    fn node_signals(
        &self,
        env: &SimEnvObserve,
        profiles: &HashMap<FnId, FunctionProfile>,
    ) -> Vec<NodeSignal> {
        let mut signals = env
            .nodes()
            .iter()
            .map(|node| {
                let cpu_utilization = safe_ratio(node.cpu, node.rsc_limit.cpu);
                let memory_utilization = safe_ratio(node.unready_mem(), node.rsc_limit.mem);
                NodeSignal {
                    pressure: cpu_utilization
                        + memory_utilization
                        + node.pending_task_cnt() as f32 / QUEUE_NORMALIZER,
                    utilization: ((cpu_utilization + memory_utilization) * 0.5).clamp(0.0, 1.0),
                    ..NodeSignal::default()
                }
            })
            .collect::<Vec<_>>();

        let requests = env.core().requests();
        for request in requests.values() {
            for (&fn_id, &node_id) in &request.fn_node {
                if request.done_fns.contains_key(&fn_id) || node_id >= signals.len() {
                    continue;
                }
                let Some(profile) = profiles.get(&fn_id) else {
                    continue;
                };
                signals[node_id].existing_count += 1;
                signals[node_id].existing_intensity_sum += profile.resource_intensity;
            }
        }
        signals
    }

    fn best_response_assignments(
        &self,
        players: &[Player],
        signals: &[NodeSignal],
    ) -> HashMap<(ReqId, FnId), NodeId> {
        let mut assignments = HashMap::with_capacity(players.len());
        let mut provisional = vec![ProvisionalLoad::default(); signals.len()];

        for _ in 0..MAX_BEST_RESPONSE_ROUNDS {
            let mut changes = 0_usize;
            for player in players {
                let key = (player.req_id, player.fn_id);
                let old_node = assignments.remove(&key);
                if let Some(node_id) = old_node {
                    remove_provisional(
                        &mut provisional[node_id],
                        player.profile.resource_intensity,
                    );
                }

                let mut best = None;
                for &node_id in &player.candidates {
                    let Some(node) = signals.get(node_id) else {
                        continue;
                    };
                    let projected = provisional[node_id];
                    let (price, pressure) =
                        congestion_price(*node, projected, player.profile.resource_intensity);
                    let utility = individual_utility(player.profile, price, pressure);
                    if candidate_is_better((node_id, utility), best) {
                        best = Some((node_id, utility));
                    }
                }

                let selected = best.map(|(node_id, _)| node_id);
                if let Some(node_id) = selected {
                    assignments.insert(key, node_id);
                    add_provisional(&mut provisional[node_id], player.profile.resource_intensity);
                }
                if selected != old_node {
                    changes += 1;
                }
            }
            if changes == 0 {
                break;
            }
        }
        assignments
    }
}

impl Default for CPBRScheduler {
    fn default() -> Self {
        Self::new()
    }
}

impl Scheduler for CPBRScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        _mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        self.ensure_function_profiles(env);
        let players = self.collect_players(env, &self.function_profiles);
        if players.is_empty() {
            return;
        }
        let signals = self.node_signals(env, &self.function_profiles);
        let assignments = self.best_response_assignments(&players, &signals);

        // Players are already in a fixed order, so command emission is stable
        // across runs with the same snapshot and seed.
        for player in players {
            let Some(&node_id) = assignments.get(&(player.req_id, player.fn_id)) else {
                continue;
            };
            if let Err(error) =
                cmd_distributor.send(placement_command(node_id, player.req_id, player.fn_id))
            {
                log::warn!(
                    "CP-BR failed to place request {} function {} on node {}: {:?}",
                    player.req_id,
                    player.fn_id,
                    node_id,
                    error
                );
            }
        }
    }
}

fn resource_intensity(normalized_cpu: f32, normalized_memory: f32) -> f32 {
    let total = normalized_cpu + normalized_memory;
    if total <= EPSILON {
        0.0
    } else {
        (2.0 * (normalized_cpu * normalized_memory).max(0.0).sqrt() / total).clamp(0.0, 1.0)
    }
}

fn safe_ratio(numerator: f32, denominator: f32) -> f32 {
    if denominator <= EPSILON {
        1.0
    } else {
        (numerator / denominator).clamp(0.0, 1.0)
    }
}

/// NSESche's fixed-window baseline price signal, without its social feedback.
fn congestion_price(
    node: NodeSignal,
    provisional: ProvisionalLoad,
    candidate_intensity: f32,
) -> (f32, f32) {
    let pressure = node.pressure + (provisional.count + 1) as f32 / QUEUE_NORMALIZER;
    let count = node.existing_count + provisional.count + 1;
    let intensity_sum =
        node.existing_intensity_sum + provisional.intensity_sum + candidate_intensity;
    let congestion_premium = if count == 0 {
        0.0
    } else {
        intensity_sum / count as f32 * node.utilization
    };
    let price = BASE_NODE_PRICE * (1.0 + pressure) * (1.0 + congestion_premium);
    (price.max(EPSILON), pressure)
}

/// Individual utility used by the best-response-only comparator.  These are
/// the NSESche individual reward/cost/quality terms; externality,
/// contribution, offline reference, and outer-loop feedback are absent.
fn individual_utility(profile: FunctionProfile, price: f32, pressure: f32) -> f32 {
    let baseline_reward = BASE_UTILITY * (profile.resource_intensity + profile.function_complexity);
    let cost = price * (1.0 + profile.resource_intensity);
    let quality = profile.quality_weight
        * (profile.function_complexity + profile.network_dependency)
        / (1.0 + pressure.max(0.0));
    baseline_reward - cost + quality
}

fn add_provisional(load: &mut ProvisionalLoad, intensity: f32) {
    load.count += 1;
    load.intensity_sum += intensity;
}

fn remove_provisional(load: &mut ProvisionalLoad, intensity: f32) {
    load.count = load.count.saturating_sub(1);
    load.intensity_sum = (load.intensity_sum - intensity).max(0.0);
}

/// Compare strictly within the supplied common candidate stream. Larger
/// utility wins; exact ties are resolved by the smaller node id.
fn candidate_is_better(candidate: (NodeId, f32), best: Option<(NodeId, f32)>) -> bool {
    let (node_id, raw_score) = candidate;
    let score = if raw_score.is_finite() {
        raw_score
    } else {
        f32::NEG_INFINITY
    };
    match best {
        None => true,
        Some((best_node, raw_best_score)) => {
            let best_score = if raw_best_score.is_finite() {
                raw_best_score
            } else {
                f32::NEG_INFINITY
            };
            score > best_score + EPSILON
                || ((score == best_score
                    || (score.is_finite()
                        && best_score.is_finite()
                        && (score - best_score).abs() <= EPSILON))
                    && node_id < best_node)
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

    #[test]
    fn congestion_price_does_not_fall_as_pressure_rises() {
        let low = NodeSignal {
            pressure: 0.2,
            utilization: 0.4,
            existing_count: 2,
            existing_intensity_sum: 1.0,
        };
        let high = NodeSignal {
            pressure: 0.9,
            ..low
        };
        let projected = ProvisionalLoad {
            count: 1,
            intensity_sum: 0.5,
        };
        assert!(
            congestion_price(high, projected, 0.5).0 >= congestion_price(low, projected, 0.5).0
        );
    }

    #[test]
    fn selection_is_deterministic_and_cannot_escape_common_candidates() {
        let common_candidates = [(7, 1.0), (2, 1.0), (11, 0.5)];
        let mut best = None;
        for candidate in common_candidates {
            if candidate_is_better(candidate, best) {
                best = Some(candidate);
            }
        }
        let selected = best
            .map(|(node_id, _)| node_id)
            .expect("a candidate must win");
        assert_eq!(selected, 2);
        assert!(common_candidates
            .iter()
            .any(|(node_id, _)| *node_id == selected));
    }

    #[test]
    fn command_constructor_emits_only_a_placement_command() {
        match placement_command(3, 5, 7) {
            MechScheduleOnceRes::ScheCmd(command) => {
                assert_eq!((command.nid, command.reqid, command.fnid), (3, 5, 7));
            }
            _ => panic!("CP-BR must emit ScheCmd only"),
        }
    }

    #[test]
    fn resource_intensity_is_bounded() {
        assert_eq!(resource_intensity(0.0, 0.0), 0.0);
        assert!((resource_intensity(0.25, 1.0) - 0.8).abs() <= EPSILON);
        assert!((0.0..=1.0).contains(&resource_intensity(3.0, 4.0)));
    }
}
