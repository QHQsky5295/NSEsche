use std::{
    collections::{HashMap, HashSet, VecDeque},
    env, fs,
    fs::File,
    io::{BufWriter, Write},
    path::{Path, PathBuf},
    time::Instant,
};

use cpu_time::ThreadTime;

use crate::{
    fn_dag::{EnvFnExt, FnId},
    mechanism::{MechType, MechanismImpl, ScheCmd, SimEnvObserve, UpCmd},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::ReqId,
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::{WithEnvCore, WithEnvHelp},
};

const EPSILON: f32 = 1.0e-6;
const DAG_COMPLEXITY_NORMALIZER: f32 = 1.5;
const DIFFERENTIATION_P1: f32 = 31.0;
const DIFFERENTIATION_P2: f32 = 37.0;
const DIFFERENTIATION_MODULUS: f32 = 100.0;
const SOCIAL_REFERENCE_CACHE_CAPACITY: usize = 64;
const SOCIAL_REFERENCE_LOCAL_EVALUATION_LIMIT: usize = 100_000;
// Version 3 fixes Eq. (8)'s state domain to the current-window players.
// Version 4 changes Eq. (6)'s queue observation to pending+runnable work.
// Version 5 makes the social reference independent of the evaluated policy's
// assignment by using a deterministic canonical SA starting allocation.
// Version 6 strengthens that policy-independent search with deterministic
// multi-start social local search and a candidate-scaled SA budget.
const REFERENCE_KEY_SCHEMA_VERSION: u64 = 6;
const REFERENCE_BUILD_RECORD_VERSION: u64 = 1;

fn env_f32(name: &str, default: f32, min: f32, max: f32) -> f32 {
    env::var(name)
        .ok()
        .and_then(|value| value.parse::<f32>().ok())
        .filter(|value| value.is_finite())
        .unwrap_or(default)
        .clamp(min, max)
}

fn env_u32(name: &str, default: u32, min: u32, max: u32) -> u32 {
    env::var(name)
        .ok()
        .and_then(|value| value.parse::<u32>().ok())
        .unwrap_or(default)
        .clamp(min, max)
}

fn load_name(env: &SimEnvObserve) -> &'static str {
    if env.help().config().request_freq_low() {
        "low"
    } else if env.help().config().request_freq_middle() {
        "middle"
    } else {
        "high"
    }
}

fn normalized_queue_pressure(pressure_queue_len: usize, queue_normalizer: f32) -> f32 {
    pressure_queue_len as f32 / queue_normalizer.max(EPSILON)
}

#[derive(Clone, Debug)]
struct NashSettings {
    max_inner_rounds: u32,
    max_outer_rounds: u32,
    price_adjustment_factor: f32,
    quality_weight: f32,
    base_node_price: f32,
    base_utility: f32,
    contribution_coefficient: f32,
    queue_normalizer: f32,
    social_gap_epsilon: f32,
    sa_iterations: u32,
    sa_iterations_per_player: u32,
    sa_initial_temperature: f32,
    sa_cooling_rate: f32,
    network_latency_normalizer_ms: Option<f32>,
    offline_social_reference: Option<f32>,
    offline_reference_file: Option<String>,
    reference_build_output_file: Option<String>,
    reference_mode: String,
    observation_enabled: bool,
    observation_detail: bool,
    ablation_type: String,
    heterogeneity_enabled: bool,
    system_utility_enabled: bool,
    externality_enabled: bool,
    contribution_enabled: bool,
    congestion_pricing_enabled: bool,
    social_coordination_enabled: bool,
}

impl Default for NashSettings {
    fn default() -> Self {
        Self {
            max_inner_rounds: 4,
            max_outer_rounds: 2,
            price_adjustment_factor: 0.6,
            quality_weight: 0.5,
            base_node_price: 0.3,
            base_utility: 25.0,
            contribution_coefficient: 1.0,
            queue_normalizer: 12.0,
            social_gap_epsilon: EPSILON,
            sa_iterations: 64,
            sa_iterations_per_player: 4,
            sa_initial_temperature: 1.0,
            sa_cooling_rate: 0.95,
            network_latency_normalizer_ms: None,
            offline_social_reference: None,
            offline_reference_file: None,
            reference_build_output_file: None,
            reference_mode: "sa_fallback".to_string(),
            observation_enabled: true,
            observation_detail: false,
            ablation_type: "full".to_string(),
            heterogeneity_enabled: true,
            system_utility_enabled: true,
            externality_enabled: true,
            contribution_enabled: true,
            congestion_pricing_enabled: true,
            social_coordination_enabled: true,
        }
    }
}

impl NashSettings {
    fn from_env(env: &SimEnvObserve) -> Self {
        // These defaults reproduce the values reported in Section V-C.
        let (default_r0, default_quality_weight) = if env.help().config().request_freq_low() {
            (0.6, 0.5)
        } else {
            (0.5, 0.6)
        };
        let configured_ablation = &env.help().config().experiment.ablation;
        let nash_config = &env.help().config().experiment.nash;
        let configured_ablation_name = if configured_ablation.no_heterogeneity {
            "no_heterogeneity"
        } else if configured_ablation.no_externality {
            "no_externality"
        } else if configured_ablation.no_pricing {
            "no_pricing"
        } else if configured_ablation.no_coordination {
            "no_coordination"
        } else {
            "full"
        };
        let ablation_type = std::env::var("NASH_ABLATION_TYPE")
            .unwrap_or_else(|_| configured_ablation_name.to_string())
            .to_ascii_lowercase();
        let observation_mode = std::env::var("NASH_OBSERVE")
            .unwrap_or_else(|_| nash_config.observe.clone())
            .to_ascii_lowercase();
        let system_utility_enabled = ablation_type != "no_social";
        let reference_config = &env.help().config().experiment.reference;
        // The experiment manifest is authoritative for formal runs.  The
        // environment variables remain a backwards-compatible fallback only
        // when the corresponding manifest field is empty.
        let reference_mode = if reference_config.mode.trim().is_empty() {
            std::env::var("NASH_REFERENCE_MODE").unwrap_or_else(|_| "sa_fallback".to_string())
        } else {
            reference_config.mode.clone()
        }
        .to_ascii_lowercase();
        let reference_mode = match reference_mode.as_str() {
            "offline_required" | "build" | "sa_fallback" | "not_required" => reference_mode,
            invalid => {
                log::error!(
                    "NSESche invalid experiment.reference.mode={invalid:?}; using fail-closed offline_required mode"
                );
                "offline_required".to_string()
            }
        };

        Self {
            max_inner_rounds: env_u32(
                "NASH_MAX_INNER_ITERATIONS",
                nash_config.max_inner_rounds,
                1,
                128,
            ),
            max_outer_rounds: env_u32(
                "NASH_MAX_OUTER_ITERATIONS",
                nash_config.max_outer_rounds,
                1,
                32,
            ),
            price_adjustment_factor: env_f32(
                "NASH_PRICE_FEEDBACK_RATE",
                nash_config.price_feedback_rate.unwrap_or(default_r0),
                0.0,
                1.0,
            ),
            quality_weight: env_f32(
                "NASH_QUALITY_WEIGHT",
                nash_config.quality_weight.unwrap_or(default_quality_weight),
                0.0,
                10.0,
            ),
            base_node_price: env_f32("NASH_BASE_NODE_PRICE", 0.3, EPSILON, 1_000.0),
            base_utility: env_f32("NASH_BASE_UTILITY", 25.0, 0.0, 1_000_000.0),
            contribution_coefficient: env_f32(
                "NASH_CONTRIBUTION_COEFFICIENT",
                1.0,
                0.0,
                1_000_000.0,
            ),
            queue_normalizer: env_f32("NASH_QUEUE_NORMALIZER", 12.0, EPSILON, 1.0e9),
            social_gap_epsilon: env_f32("NASH_SOCIAL_GAP_EPSILON", EPSILON, 0.0, 1.0),
            sa_iterations: env_u32("NASH_SA_ITERATIONS", nash_config.sa_iterations, 1, 100_000),
            sa_iterations_per_player: env_u32(
                "NASH_SA_ITERATIONS_PER_PLAYER",
                nash_config.sa_iterations_per_player,
                0,
                1_000,
            ),
            sa_initial_temperature: env_f32("NASH_SA_INITIAL_TEMPERATURE", 1.0, EPSILON, 1.0e9),
            sa_cooling_rate: env_f32("NASH_SA_COOLING_RATE", 0.95, 0.01, 0.9999),
            network_latency_normalizer_ms: std::env::var("NASH_NETWORK_LATENCY_NORMALIZER_MS")
                .ok()
                .and_then(|value| value.parse::<f32>().ok())
                .filter(|value| value.is_finite() && *value > EPSILON),
            offline_social_reference: std::env::var("NASH_SOCIAL_REFERENCE")
                .ok()
                .and_then(|value| value.parse::<f32>().ok())
                .filter(|value| value.is_finite() && *value > EPSILON),
            offline_reference_file: std::env::var("NASH_OFFLINE_REFERENCE_FILE")
                .ok()
                .filter(|value| !value.trim().is_empty())
                .filter(|_| reference_config.table_path.trim().is_empty())
                .or_else(|| {
                    (!reference_config.table_path.trim().is_empty())
                        .then(|| reference_config.table_path.clone())
                }),
            reference_build_output_file: if !reference_config.build_output_path.trim().is_empty() {
                Some(reference_config.build_output_path.clone())
            } else if let Ok(path) = std::env::var("NASH_REFERENCE_BUILD_OUTPUT") {
                (!path.trim().is_empty()).then_some(path)
            } else if env.help().config().experiment.output.enabled
                && !env.help().config().experiment.output.root.trim().is_empty()
            {
                let mut path = PathBuf::from(&env.help().config().experiment.output.root);
                if !env.help().config().experiment.run_id.trim().is_empty() {
                    path.push(&env.help().config().experiment.run_id);
                }
                path.push("offline_social_reference_build.jsonl");
                Some(path.to_string_lossy().into_owned())
            } else {
                None
            },
            reference_mode,
            observation_enabled: !matches!(observation_mode.as_str(), "off" | "false" | "0"),
            observation_detail: observation_mode == "detail",
            heterogeneity_enabled: !configured_ablation.no_heterogeneity
                && ablation_type != "no_heterogeneity",
            externality_enabled: system_utility_enabled
                && !configured_ablation.no_externality
                && ablation_type != "no_externality",
            contribution_enabled: system_utility_enabled && ablation_type != "no_contribution",
            congestion_pricing_enabled: !configured_ablation.no_pricing
                && ablation_type != "no_pricing",
            social_coordination_enabled: !configured_ablation.no_coordination
                && ablation_type != "no_coordination"
                && ablation_type != "no_nash_social",
            system_utility_enabled,
            ablation_type,
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct HeterogeneityProfile {
    normalized_cpu: f32,
    normalized_memory: f32,
    resource_intensity: f32,
    function_complexity: f32,
    network_dependency: f32,
    differentiation: f32,
}

impl HeterogeneityProfile {
    fn new(
        normalized_cpu: f32,
        normalized_memory: f32,
        dag_node_count: usize,
        enabled: bool,
    ) -> Self {
        if !enabled {
            return Self {
                normalized_cpu,
                normalized_memory,
                resource_intensity: 0.5,
                function_complexity: 0.5,
                network_dependency: 0.5,
                differentiation: 0.5,
            };
        }

        let cpu = normalized_cpu.max(0.0);
        let memory = normalized_memory.max(0.0);
        let resource_intensity = if cpu + memory > EPSILON {
            (2.0 * (cpu * memory).sqrt() / (cpu + memory)).clamp(0.0, 1.0)
        } else {
            0.0
        };
        let function_complexity = ((dag_node_count.max(1) as f32).ln() / DAG_COMPLEXITY_NORMALIZER)
            .tanh()
            .clamp(0.0, 1.0);
        let network_dependency = (resource_intensity * function_complexity)
            .sqrt()
            .clamp(0.0, 1.0);
        let differentiation = ((cpu * DIFFERENTIATION_P1 + memory * DIFFERENTIATION_P2)
            .rem_euclid(DIFFERENTIATION_MODULUS)
            / DIFFERENTIATION_MODULUS)
            .clamp(0.0, 1.0);

        Self {
            normalized_cpu,
            normalized_memory,
            resource_intensity,
            function_complexity,
            network_dependency,
            differentiation,
        }
    }

    fn impact(self) -> f32 {
        self.function_complexity * self.resource_intensity
    }
}

#[derive(Clone, Copy, Debug)]
struct FunctionProfile {
    fn_id: FnId,
    raw_cpu: f32,
    raw_memory: f32,
    output_mb: f32,
    cold_start_frames: usize,
    dag_node_count: usize,
    required_container_memory: f32,
    quality_weight: f32,
    heterogeneity: HeterogeneityProfile,
}

#[derive(Clone, Copy, Debug, Default)]
struct NodeSnapshot {
    cpu_utilization: f32,
    memory_utilization: f32,
    pending_tasks: usize,
    runnable_tasks: usize,
    parent_blocked_tasks: usize,
    data_blocked_tasks: usize,
    starting_resident_tasks: usize,
    resident_tasks: usize,
    container_count: usize,
    running_containers: usize,
    pressure: f32,
    utilization: f32,
}

#[derive(Clone, Copy, Debug, Default)]
struct NodeAggregate {
    request_count: usize,
    resource_intensity_sum: f32,
    impact_sum: f32,
    reserved_container_memory: f32,
}

#[derive(Clone, Copy, Debug, Default)]
struct PlayerNodeAggregate {
    baseline_feature_sum: f32,
    cost_weight_sum: f32,
    quality_feature_sum: f32,
    resource_intensity_sum: f32,
    resource_impact_sum: f32,
    contribution_feature_sum: f32,
}

#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq, PartialOrd, Ord)]
struct PlayerId {
    req_id: ReqId,
    fn_id: FnId,
}

fn stable_function_assignments(assignments: &HashMap<FnId, NodeId>) -> Vec<(FnId, NodeId)> {
    let mut ordered = assignments
        .iter()
        .map(|(&fn_id, &node_id)| (fn_id, node_id))
        .collect::<Vec<_>>();
    ordered.sort_unstable();
    ordered
}

#[derive(Clone, Debug)]
struct AssignmentState {
    assignments: HashMap<PlayerId, NodeId>,
    node_aggregates: Vec<NodeAggregate>,
    player_node_aggregates: Vec<PlayerNodeAggregate>,
    cold_function_counts: HashMap<(FnId, NodeId), usize>,
    new_container_counts: HashMap<FnId, usize>,
}

impl AssignmentState {
    fn new(base_aggregates: Vec<NodeAggregate>, player_capacity: usize) -> Self {
        Self {
            assignments: HashMap::with_capacity(player_capacity),
            player_node_aggregates: vec![PlayerNodeAggregate::default(); base_aggregates.len()],
            node_aggregates: base_aggregates,
            cold_function_counts: HashMap::new(),
            new_container_counts: HashMap::new(),
        }
    }

    fn can_add(
        &self,
        player: PlayerId,
        node_id: NodeId,
        existing_containers: &HashSet<(FnId, NodeId)>,
        available_container_memory: &[f32],
        profiles: &HashMap<FnId, FunctionProfile>,
        new_container_limits: &HashMap<FnId, usize>,
    ) -> bool {
        if node_id >= self.node_aggregates.len() {
            return false;
        }
        if existing_containers.contains(&(player.fn_id, node_id))
            || self
                .cold_function_counts
                .get(&(player.fn_id, node_id))
                .copied()
                .unwrap_or(0)
                > 0
        {
            return true;
        }
        let new_container_limit = new_container_limits
            .get(&player.fn_id)
            .copied()
            .unwrap_or(usize::MAX);
        if self
            .new_container_counts
            .get(&player.fn_id)
            .copied()
            .unwrap_or(0)
            >= new_container_limit
        {
            return false;
        }
        let required = profiles
            .get(&player.fn_id)
            .map(|profile| profile.required_container_memory)
            .unwrap_or(f32::INFINITY);
        let available = available_container_memory
            .get(node_id)
            .copied()
            .unwrap_or(0.0);
        available - self.node_aggregates[node_id].reserved_container_memory > required
    }

    fn add(
        &mut self,
        player: PlayerId,
        node_id: NodeId,
        existing_containers: &HashSet<(FnId, NodeId)>,
        profiles: &HashMap<FnId, FunctionProfile>,
    ) {
        debug_assert!(!self.assignments.contains_key(&player));
        let profile = &profiles[&player.fn_id];
        self.assignments.insert(player, node_id);
        let aggregate = &mut self.node_aggregates[node_id];
        aggregate.request_count += 1;
        aggregate.resource_intensity_sum += profile.heterogeneity.resource_intensity;
        aggregate.impact_sum += profile.heterogeneity.impact();
        let heterogeneity = profile.heterogeneity;
        let player_aggregate = &mut self.player_node_aggregates[node_id];
        player_aggregate.baseline_feature_sum +=
            heterogeneity.resource_intensity + heterogeneity.function_complexity;
        player_aggregate.cost_weight_sum += 1.0 + heterogeneity.resource_intensity;
        player_aggregate.quality_feature_sum += profile.quality_weight
            * (heterogeneity.function_complexity + heterogeneity.network_dependency);
        player_aggregate.resource_intensity_sum += heterogeneity.resource_intensity;
        player_aggregate.resource_impact_sum +=
            heterogeneity.resource_intensity * heterogeneity.impact();
        player_aggregate.contribution_feature_sum += 1.0 + heterogeneity.differentiation;

        if !existing_containers.contains(&(player.fn_id, node_id)) {
            let count = self
                .cold_function_counts
                .entry((player.fn_id, node_id))
                .or_insert(0);
            if *count == 0 {
                aggregate.reserved_container_memory += profile.required_container_memory;
                *self.new_container_counts.entry(player.fn_id).or_insert(0) += 1;
            }
            *count += 1;
        }
    }

    fn remove(
        &mut self,
        player: PlayerId,
        existing_containers: &HashSet<(FnId, NodeId)>,
        profiles: &HashMap<FnId, FunctionProfile>,
    ) -> Option<NodeId> {
        let node_id = self.assignments.remove(&player)?;
        let profile = &profiles[&player.fn_id];
        let aggregate = &mut self.node_aggregates[node_id];
        aggregate.request_count = aggregate.request_count.saturating_sub(1);
        aggregate.resource_intensity_sum =
            (aggregate.resource_intensity_sum - profile.heterogeneity.resource_intensity).max(0.0);
        aggregate.impact_sum = (aggregate.impact_sum - profile.heterogeneity.impact()).max(0.0);
        let heterogeneity = profile.heterogeneity;
        let player_aggregate = &mut self.player_node_aggregates[node_id];
        player_aggregate.baseline_feature_sum = (player_aggregate.baseline_feature_sum
            - heterogeneity.resource_intensity
            - heterogeneity.function_complexity)
            .max(0.0);
        player_aggregate.cost_weight_sum =
            (player_aggregate.cost_weight_sum - 1.0 - heterogeneity.resource_intensity).max(0.0);
        player_aggregate.quality_feature_sum = (player_aggregate.quality_feature_sum
            - profile.quality_weight
                * (heterogeneity.function_complexity + heterogeneity.network_dependency))
            .max(0.0);
        player_aggregate.resource_intensity_sum =
            (player_aggregate.resource_intensity_sum - heterogeneity.resource_intensity).max(0.0);
        player_aggregate.resource_impact_sum = (player_aggregate.resource_impact_sum
            - heterogeneity.resource_intensity * heterogeneity.impact())
        .max(0.0);
        player_aggregate.contribution_feature_sum =
            (player_aggregate.contribution_feature_sum - 1.0 - heterogeneity.differentiation)
                .max(0.0);

        if !existing_containers.contains(&(player.fn_id, node_id)) {
            let key = (player.fn_id, node_id);
            let remove_entry = if let Some(count) = self.cold_function_counts.get_mut(&key) {
                *count = count.saturating_sub(1);
                *count == 0
            } else {
                false
            };
            if remove_entry {
                self.cold_function_counts.remove(&key);
                let remove_function_entry =
                    if let Some(count) = self.new_container_counts.get_mut(&player.fn_id) {
                        *count = count.saturating_sub(1);
                        *count == 0
                    } else {
                        false
                    };
                if remove_function_entry {
                    self.new_container_counts.remove(&player.fn_id);
                }
                aggregate.reserved_container_memory = (aggregate.reserved_container_memory
                    - profile.required_container_memory)
                    .max(0.0);
            }
        }
        Some(node_id)
    }
}

#[derive(Clone, Debug)]
struct PriceSignal {
    baseline_prices: Vec<f32>,
    adjusted_prices: Vec<f32>,
    node_congestion_premiums: Vec<f32>,
    global_load: f32,
    network_congestion: f32,
}

#[derive(Clone, Copy, Debug, Default)]
struct UtilityBreakdown {
    baseline_reward: f32,
    cost: f32,
    quality: f32,
    externality: f32,
    contribution: f32,
    total: f32,
}

impl std::ops::AddAssign for UtilityBreakdown {
    fn add_assign(&mut self, other: Self) {
        self.baseline_reward += other.baseline_reward;
        self.cost += other.cost;
        self.quality += other.quality;
        self.externality += other.externality;
        self.contribution += other.contribution;
        self.total += other.total;
    }
}

#[derive(Debug)]
struct SolveStats {
    inner_rounds: u32,
    outer_rounds: u32,
    inner_rounds_per_outer: Vec<u32>,
    assignment_moves: usize,
    assignment_moves_per_round: Vec<usize>,
    candidate_evaluations: usize,
    initialization_evaluations: usize,
    no_feasible_players: usize,
    assigned_players: usize,
    oscillation_count: usize,
    inner_stable: bool,
    outer_stable: bool,
    hit_inner_limit: bool,
    hit_outer_limit: bool,
    price_adjustments: u32,
    assignment_hash: u64,
    /// Welfare of the first stable inner-Nash allocation under the immutable
    /// baseline price vector, before Eq. (19) can feed a social gap back into
    /// prices.  This is an observation only and never drives a decision.
    pre_feedback_welfare: UtilityBreakdown,
    /// Welfare of the final proposed assignment re-evaluated under that same
    /// baseline price vector.  This is the method-comparable numerator used by
    /// the post-hoc empirical welfare gap.
    final_assignment_baseline_welfare: UtilityBreakdown,
    welfare: UtilityBreakdown,
    social_reference: Option<f32>,
    reference_key: Option<u64>,
    reference_initial_assignment_hash: Option<u64>,
    social_gap: Option<f32>,
    reference_feedback_eligible: bool,
    reference_below_current: bool,
    gamma: f32,
    reference_source: &'static str,
    reference_cache_hit: bool,
    reference_compute_us: u64,
    reference_lookup_us: u64,
    reference_persist_us: u64,
    reference_persist_ok: bool,
    reference_sa_iterations: u64,
    initialization_us: u64,
    termination_reason: &'static str,
}

impl Default for SolveStats {
    fn default() -> Self {
        Self {
            inner_rounds: 0,
            outer_rounds: 0,
            inner_rounds_per_outer: Vec::new(),
            assignment_moves: 0,
            assignment_moves_per_round: Vec::new(),
            candidate_evaluations: 0,
            initialization_evaluations: 0,
            no_feasible_players: 0,
            assigned_players: 0,
            oscillation_count: 0,
            inner_stable: false,
            outer_stable: false,
            hit_inner_limit: false,
            hit_outer_limit: false,
            price_adjustments: 0,
            assignment_hash: 0,
            pre_feedback_welfare: UtilityBreakdown::default(),
            final_assignment_baseline_welfare: UtilityBreakdown::default(),
            welfare: UtilityBreakdown::default(),
            social_reference: None,
            reference_key: None,
            reference_initial_assignment_hash: None,
            social_gap: None,
            reference_feedback_eligible: false,
            reference_below_current: false,
            gamma: 0.0,
            reference_source: "not_requested",
            reference_cache_hit: false,
            reference_compute_us: 0,
            reference_lookup_us: 0,
            reference_persist_us: 0,
            reference_persist_ok: true,
            reference_sa_iterations: 0,
            initialization_us: 0,
            termination_reason: "not_started",
        }
    }
}

#[derive(Clone, Copy, Debug, Default)]
struct InnerOutcome {
    stable: bool,
    infeasible: bool,
    oscillated: bool,
}

#[derive(Clone, Copy, Debug)]
struct ReferenceResult {
    value: Option<f32>,
    key: Option<u64>,
    source: &'static str,
    cache_hit: bool,
    compute_us: u64,
    lookup_us: u64,
    persist_us: u64,
    persist_ok: bool,
    sa_iterations: u32,
}

#[derive(Clone, Copy, Debug)]
struct ReferenceSearchResult {
    value: f32,
    sa_iterations: u32,
}

impl Default for ReferenceResult {
    fn default() -> Self {
        Self {
            value: None,
            key: None,
            source: "not_requested",
            cache_hit: false,
            compute_us: 0,
            lookup_us: 0,
            persist_us: 0,
            persist_ok: true,
            sa_iterations: 0,
        }
    }
}

#[derive(Debug)]
struct ReferenceBuildWriter {
    final_path: PathBuf,
    partial_path: PathBuf,
    writer: Option<BufWriter<File>>,
    recorded_keys: HashSet<u64>,
    records_written: u64,
    write_errors: u64,
    finalized: bool,
}

impl ReferenceBuildWriter {
    fn partial_path(final_path: &Path) -> PathBuf {
        let mut value = final_path.as_os_str().to_os_string();
        value.push(".partial");
        PathBuf::from(value)
    }

    fn new(final_path: PathBuf) -> Result<Self, String> {
        let partial_path = Self::partial_path(&final_path);
        if let Some(parent) = partial_path.parent() {
            if !parent.as_os_str().is_empty() {
                fs::create_dir_all(parent).map_err(|error| {
                    format!(
                        "failed to create reference build directory {}: {error}",
                        parent.display()
                    )
                })?;
            }
        }
        let writer = File::create(&partial_path)
            .map(BufWriter::new)
            .map_err(|error| {
                format!(
                    "failed to create reference build partial file {}: {error}",
                    partial_path.display()
                )
            })?;
        Ok(Self {
            final_path,
            partial_path,
            writer: Some(writer),
            recorded_keys: HashSet::new(),
            records_written: 0,
            write_errors: 0,
            finalized: false,
        })
    }

    fn record(
        &mut self,
        state_key: u64,
        reference: Option<f32>,
        initial_assignment_hash: u64,
        player_count: usize,
        sa_iterations: u32,
        compute_us: u64,
    ) -> Result<bool, String> {
        if self.recorded_keys.contains(&state_key) {
            return Ok(false);
        }
        let status = match reference {
            Some(value) if value > EPSILON => "positive",
            Some(value) if value < 0.0 => "negative",
            Some(_) => "zero",
            None => "unavailable",
        };
        let event = serde_json::json!({
            "v": REFERENCE_BUILD_RECORD_VERSION,
            "kind": "offline_social_reference_build",
            "state_key": format!("0x{state_key:016x}"),
            "state_key_u64": state_key,
            "reference": reference,
            "status": status,
            "initial_assignment_hash": initial_assignment_hash,
            "players": player_count,
            "sa_iterations": sa_iterations,
            "compute_us": compute_us,
        });
        let Some(writer) = self.writer.as_mut() else {
            self.write_errors += 1;
            return Err("reference build writer is already closed".to_string());
        };
        if let Err(error) = serde_json::to_writer(&mut *writer, &event)
            .and_then(|_| writer.write_all(b"\n").map_err(serde_json::Error::io))
            .and_then(|_| writer.flush().map_err(serde_json::Error::io))
        {
            self.write_errors += 1;
            return Err(format!(
                "failed to append reference build record to {}: {error}",
                self.partial_path.display()
            ));
        }
        self.recorded_keys.insert(state_key);
        self.records_written += 1;
        Ok(true)
    }

    fn flush_partial(&mut self) -> Result<(), String> {
        if let Some(writer) = self.writer.as_mut() {
            writer.flush().map_err(|error| {
                format!(
                    "failed to flush reference build partial file {}: {error}",
                    self.partial_path.display()
                )
            })?;
        }
        Ok(())
    }

    fn finalize(&mut self) -> Result<(), String> {
        if self.finalized {
            return Ok(());
        }
        self.flush_partial()?;
        self.writer.take();
        if self.final_path.exists() {
            fs::remove_file(&self.final_path).map_err(|error| {
                format!(
                    "failed to replace reference build file {}: {error}",
                    self.final_path.display()
                )
            })?;
        }
        fs::rename(&self.partial_path, &self.final_path).map_err(|error| {
            format!(
                "failed to atomically publish reference build file {} -> {}: {error}",
                self.partial_path.display(),
                self.final_path.display()
            )
        })?;
        self.finalized = true;
        Ok(())
    }
}

#[derive(Debug)]
struct NashObservationWriter {
    final_path: PathBuf,
    partial_path: PathBuf,
    writer: Option<BufWriter<File>>,
    finalized: bool,
}

impl NashObservationWriter {
    fn new(final_path: PathBuf) -> Result<Self, String> {
        let partial_path = ReferenceBuildWriter::partial_path(&final_path);
        if let Some(parent) = partial_path.parent() {
            fs::create_dir_all(parent).map_err(|error| {
                format!(
                    "failed to create Nash observation directory {}: {error}",
                    parent.display()
                )
            })?;
        }
        if final_path.exists() || partial_path.exists() {
            return Err(format!(
                "refusing to overwrite Nash observation artifact {}",
                final_path.display()
            ));
        }
        let writer = File::create(&partial_path)
            .map(BufWriter::new)
            .map_err(|error| {
                format!(
                    "failed to create Nash observation partial file {}: {error}",
                    partial_path.display()
                )
            })?;
        Ok(Self {
            final_path,
            partial_path,
            writer: Some(writer),
            finalized: false,
        })
    }

    fn record(&mut self, event: &serde_json::Value) -> Result<(), String> {
        let writer = self
            .writer
            .as_mut()
            .ok_or_else(|| "Nash observation writer is already closed".to_string())?;
        serde_json::to_writer(&mut *writer, event)
            .and_then(|_| writer.write_all(b"\n").map_err(serde_json::Error::io))
            .and_then(|_| writer.flush().map_err(serde_json::Error::io))
            .map_err(|error| {
                format!(
                    "failed to append Nash observation to {}: {error}",
                    self.partial_path.display()
                )
            })
    }

    fn flush_partial(&mut self) -> Result<(), String> {
        if let Some(writer) = self.writer.as_mut() {
            writer.flush().map_err(|error| {
                format!(
                    "failed to flush Nash observation partial file {}: {error}",
                    self.partial_path.display()
                )
            })?;
        }
        Ok(())
    }

    fn finalize(&mut self) -> Result<(), String> {
        if self.finalized {
            return Ok(());
        }
        self.flush_partial()?;
        self.writer.take();
        if self.final_path.exists() {
            return Err(format!(
                "refusing to replace Nash observation artifact {}",
                self.final_path.display()
            ));
        }
        fs::rename(&self.partial_path, &self.final_path).map_err(|error| {
            format!(
                "failed to publish Nash observation file {} -> {}: {error}",
                self.partial_path.display(),
                self.final_path.display()
            )
        })?;
        self.finalized = true;
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Default)]
struct DispatchStats {
    commands_prepared: usize,
    commands_sent: usize,
    scale_ups_prepared: usize,
    scale_ups_sent: usize,
    invalid_assignments: usize,
    channel_failed: bool,
}

#[derive(Clone, Copy, Debug, Default)]
struct WindowTrafficMetrics {
    delta_frames: usize,
    arrivals: usize,
    completions: usize,
    cumulative_arrivals: usize,
    cumulative_completions: usize,
    arrival_rps: f64,
    throughput_rps: f64,
    cumulative_latency_p50_ms: usize,
    cumulative_latency_p95_ms: usize,
    cumulative_latency_p99_ms: usize,
    latency_samples: u64,
}

#[derive(Debug)]
struct TrafficObserver {
    last_frame: usize,
    last_total_seen: usize,
    last_done_count: usize,
    latency_histogram: Vec<u64>,
    latency_samples: u64,
}

impl Default for TrafficObserver {
    fn default() -> Self {
        Self {
            last_frame: 0,
            last_total_seen: 0,
            last_done_count: 0,
            latency_histogram: vec![0; 1024],
            latency_samples: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, Default)]
struct WindowTimings {
    reference_table_refresh_us: u64,
    profile_us: u64,
    collect_players_us: u64,
    snapshot_us: u64,
    pricing_us: u64,
    solve_us: u64,
    dispatch_us: u64,
    scheduler_wall_us: u64,
    scheduler_thread_cpu_us: u64,
}

#[derive(Clone, Copy, Debug, Default)]
struct PlacementDiagnostics {
    assigned_nodes: usize,
    normalized_dispersion: f32,
    co_location_pairs: usize,
    co_location_pair_ratio: f32,
    evaluated_players: usize,
    near_tie_players: usize,
    differentiation_changed_choice_players: usize,
    active_differentiation_mean: f32,
}

#[derive(Debug, Default)]
struct RunAggregate {
    windows: u64,
    solver_windows: u64,
    inner_stable_windows: u64,
    outer_stable_windows: u64,
    inner_limit_windows: u64,
    outer_limit_windows: u64,
    oscillation_windows: u64,
    inner_rounds: Vec<u32>,
    outer_rounds: Vec<u32>,
    wall_us: Vec<u64>,
    thread_cpu_us: Vec<u64>,
    reference_compute_us: u64,
    reference_lookup_us: u64,
    reference_persist_us: u64,
    reference_sa_iterations: u64,
    reference_windows: u64,
    reference_missing_windows: u64,
    reference_zero_windows: u64,
    reference_negative_windows: u64,
    reference_unavailable_windows: u64,
    reference_feedback_eligible_windows: u64,
    reference_below_current_windows: u64,
    reference_persist_failures: u64,
}

impl RunAggregate {
    fn record(&mut self, player_count: usize, stats: &SolveStats, timings: &WindowTimings) {
        self.windows += 1;
        self.wall_us.push(timings.scheduler_wall_us);
        self.thread_cpu_us.push(timings.scheduler_thread_cpu_us);
        self.reference_compute_us += stats.reference_compute_us;
        self.reference_lookup_us += stats.reference_lookup_us;
        self.reference_persist_us += stats.reference_persist_us;
        self.reference_sa_iterations += stats.reference_sa_iterations;
        if stats.reference_key.is_some() {
            self.reference_windows += 1;
        }
        if stats.reference_source == "offline_table_missing" {
            self.reference_missing_windows += 1;
        }
        match stats.social_reference {
            Some(value) if value < 0.0 => self.reference_negative_windows += 1,
            Some(value) if value <= EPSILON => self.reference_zero_windows += 1,
            None if stats.reference_key.is_some()
                && stats.reference_source != "offline_table_missing" =>
            {
                self.reference_unavailable_windows += 1
            }
            _ => {}
        }
        self.reference_feedback_eligible_windows += u64::from(stats.reference_feedback_eligible);
        self.reference_below_current_windows += u64::from(stats.reference_below_current);
        if !stats.reference_persist_ok {
            self.reference_persist_failures += 1;
        }
        if player_count == 0 {
            return;
        }
        self.solver_windows += 1;
        self.inner_rounds.push(stats.inner_rounds);
        self.outer_rounds.push(stats.outer_rounds);
        self.inner_stable_windows += u64::from(stats.inner_stable);
        self.outer_stable_windows += u64::from(stats.outer_stable);
        self.inner_limit_windows += u64::from(stats.hit_inner_limit);
        self.outer_limit_windows += u64::from(stats.hit_outer_limit);
        self.oscillation_windows += u64::from(stats.oscillation_count > 0);
    }
}

pub struct ScheNashScheduler {
    settings: NashSettings,
    function_profiles: HashMap<FnId, FunctionProfile>,
    function_parents: HashMap<FnId, Vec<FnId>>,
    profile_function_count: usize,
    profile_heterogeneity_enabled: bool,
    node_snapshots: Vec<NodeSnapshot>,
    feasible_nodes: HashMap<PlayerId, Vec<NodeId>>,
    new_container_limits: HashMap<FnId, usize>,
    existing_containers: HashSet<(FnId, NodeId)>,
    warm_containers: HashSet<(FnId, NodeId)>,
    available_container_memory: Vec<f32>,
    social_reference_cache: HashMap<u64, f32>,
    social_reference_order: VecDeque<u64>,
    // A build record with `reference: null` is a valid, explicit result: the
    // social reference was unavailable for that state.  Preserve that state
    // separately from a genuinely missing table key so offline replay can
    // retain the inner Nash allocation without reporting a lookup failure.
    offline_reference_table: HashMap<u64, Option<f32>>,
    offline_reference_file_loaded: Option<String>,
    offline_reference_load_error: Option<String>,
    offline_reference_load_wall_us_total: u64,
    offline_reference_load_thread_cpu_us_total: u64,
    offline_reference_load_attempts: u64,
    reference_build_writer: Option<ReferenceBuildWriter>,
    reference_build_writer_error: Option<String>,
    observation_writer: Option<NashObservationWriter>,
    observation_writer_error: Option<String>,
    logged_missing_reference_keys: HashSet<u64>,
    traffic_observer: TrafficObserver,
    run_aggregate: RunAggregate,
    run_config_logged: bool,
    logged_function_profiles: HashSet<FnId>,
    observation_window: u64,
    network_initialized: bool,
    network_node_count: usize,
    network_beta_proxy: f32,
    network_latency_mean_ms: f32,
    network_latency_max_ms: f32,
    active_network_transfers: usize,
    active_network_remaining_mb: f32,
    dynamic_link_delay_mean_ms: f32,
    dynamic_link_delay_max_ms: f32,
    network_latency_normalizer_used_ms: f32,
    saturated_dynamic_links: usize,
    cross_node_placement_ratio: f32,
}

impl ScheNashScheduler {
    pub fn new() -> Self {
        Self {
            settings: NashSettings::default(),
            function_profiles: HashMap::new(),
            function_parents: HashMap::new(),
            profile_function_count: 0,
            profile_heterogeneity_enabled: true,
            node_snapshots: Vec::new(),
            feasible_nodes: HashMap::new(),
            new_container_limits: HashMap::new(),
            existing_containers: HashSet::new(),
            warm_containers: HashSet::new(),
            available_container_memory: Vec::new(),
            social_reference_cache: HashMap::with_capacity(SOCIAL_REFERENCE_CACHE_CAPACITY),
            social_reference_order: VecDeque::with_capacity(SOCIAL_REFERENCE_CACHE_CAPACITY),
            offline_reference_table: HashMap::new(),
            offline_reference_file_loaded: None,
            offline_reference_load_error: None,
            offline_reference_load_wall_us_total: 0,
            offline_reference_load_thread_cpu_us_total: 0,
            offline_reference_load_attempts: 0,
            reference_build_writer: None,
            reference_build_writer_error: None,
            observation_writer: None,
            observation_writer_error: None,
            logged_missing_reference_keys: HashSet::new(),
            traffic_observer: TrafficObserver::default(),
            run_aggregate: RunAggregate::default(),
            run_config_logged: false,
            logged_function_profiles: HashSet::new(),
            observation_window: 0,
            network_initialized: false,
            network_node_count: 0,
            network_beta_proxy: 1.0,
            network_latency_mean_ms: 0.0,
            network_latency_max_ms: 0.0,
            active_network_transfers: 0,
            active_network_remaining_mb: 0.0,
            dynamic_link_delay_mean_ms: 0.0,
            dynamic_link_delay_max_ms: 0.0,
            network_latency_normalizer_used_ms: 0.0,
            saturated_dynamic_links: 0,
            cross_node_placement_ratio: 0.0,
        }
    }

    fn parse_reference_key(value: &str) -> Option<u64> {
        let value = value.trim();
        value
            .strip_prefix("0x")
            .or_else(|| value.strip_prefix("0X"))
            .and_then(|hex| u64::from_str_radix(hex, 16).ok())
            .or_else(|| value.parse::<u64>().ok())
    }

    fn reference_record_key(value: &serde_json::Value) -> Option<u64> {
        value
            .get("state_key_u64")
            .and_then(serde_json::Value::as_u64)
            .or_else(|| {
                value
                    .get("state_key")
                    .and_then(serde_json::Value::as_str)
                    .and_then(Self::parse_reference_key)
            })
    }

    fn insert_reference(
        references: &mut HashMap<u64, Option<f32>>,
        key: u64,
        value: Option<f32>,
    ) -> Result<(), String> {
        if value.is_some_and(|reference| !reference.is_finite()) {
            return Err(format!("reference for state key {key} is not finite"));
        }
        if let Some(previous) = references.insert(key, value) {
            let same = match (previous, value) {
                (Some(previous), Some(value)) => previous.to_bits() == value.to_bits(),
                (None, None) => true,
                _ => false,
            };
            if !same {
                return Err(format!(
                    "conflicting references for state key {key}: {previous:?} vs {value:?}"
                ));
            }
        }
        Ok(())
    }

    fn parse_reference_object(
        value: &serde_json::Value,
        references: &mut HashMap<u64, Option<f32>>,
    ) -> Result<(), String> {
        if value.get("kind").and_then(serde_json::Value::as_str)
            == Some("offline_social_reference_build")
        {
            let Some(key) = Self::reference_record_key(value) else {
                return Err("reference build record is missing a valid state key".to_string());
            };
            let raw_reference = value
                .get("reference")
                .ok_or_else(|| "reference build record is missing reference".to_string())?;
            let reference = if raw_reference.is_null() {
                None
            } else {
                Some(raw_reference.as_f64().ok_or_else(|| {
                    "reference build value is neither numeric nor null".to_string()
                })? as f32)
            };
            Self::insert_reference(references, key, reference)?;
            return Ok(());
        }

        let entries = value.get("references").unwrap_or(value);
        let Some(entries) = entries.as_object() else {
            return Err(
                "reference JSON must be an object, contain a references object, or be JSONL build records"
                    .to_string(),
            );
        };
        for (raw_key, raw_value) in entries {
            let Some(key) = Self::parse_reference_key(raw_key) else {
                continue;
            };
            let raw_reference = raw_value.get("reference").unwrap_or(raw_value);
            let reference = if raw_reference.is_null() {
                None
            } else if let Some(reference) = raw_reference.as_f64().map(|value| value as f32) {
                Some(reference)
            } else {
                continue;
            };
            Self::insert_reference(references, key, reference)?;
        }
        Ok(())
    }

    fn parse_reference_contents(contents: &str) -> Result<HashMap<u64, Option<f32>>, String> {
        let mut references = HashMap::new();
        match serde_json::from_str::<serde_json::Value>(contents) {
            Ok(value) => Self::parse_reference_object(&value, &mut references)?,
            Err(document_error) => {
                let mut parsed_lines = 0usize;
                for (line_index, line) in contents.lines().enumerate() {
                    if line.trim().is_empty() {
                        continue;
                    }
                    let value = serde_json::from_str::<serde_json::Value>(line).map_err(|error| {
                        format!(
                            "reference file is neither JSON ({document_error}) nor valid JSONL at line {}: {error}",
                            line_index + 1
                        )
                    })?;
                    Self::parse_reference_object(&value, &mut references)?;
                    parsed_lines += 1;
                }
                if parsed_lines == 0 {
                    return Err("reference file is empty".to_string());
                }
            }
        }
        if references.is_empty() {
            return Err("no finite reference entries found".to_string());
        }
        Ok(references)
    }

    fn refresh_offline_reference_table(&mut self) {
        let requested_file = self.settings.offline_reference_file.clone();
        if requested_file == self.offline_reference_file_loaded {
            return;
        }
        self.offline_reference_table.clear();
        self.offline_reference_load_error = None;
        self.offline_reference_file_loaded = requested_file.clone();
        let Some(path) = requested_file else {
            return;
        };

        let load_wall_start = Instant::now();
        let load_cpu_start = ThreadTime::try_now().ok();
        let parsed = fs::read_to_string(&path)
            .map_err(|error| error.to_string())
            .and_then(|contents| Self::parse_reference_contents(&contents));
        self.offline_reference_load_attempts += 1;
        self.offline_reference_load_wall_us_total = self
            .offline_reference_load_wall_us_total
            .saturating_add(load_wall_start.elapsed().as_micros().min(u64::MAX as u128) as u64);
        self.offline_reference_load_thread_cpu_us_total = self
            .offline_reference_load_thread_cpu_us_total
            .saturating_add(
                load_cpu_start
                    .as_ref()
                    .and_then(|start| start.try_elapsed().ok())
                    .map(|duration| duration.as_micros().min(u64::MAX as u128) as u64)
                    .unwrap_or(0),
            );
        match parsed {
            Ok(references) => {
                self.offline_reference_table = references;
            }
            Err(error) => {
                log::error!(
                    "NSESche failed to load offline social reference table {}: {}",
                    path,
                    error
                );
                self.offline_reference_load_error = Some(error);
            }
        }
    }

    fn ensure_reference_build_writer(&mut self) {
        if self.settings.reference_mode != "build" {
            return;
        }
        let Some(path) = self.settings.reference_build_output_file.as_ref() else {
            if self.reference_build_writer_error.is_none() {
                let error = "reference mode build requires experiment.reference.build_output_path or an enabled experiment output root".to_string();
                log::error!("NSESche {error}");
                self.reference_build_writer_error = Some(error);
            }
            return;
        };
        let requested = PathBuf::from(path);
        if self
            .reference_build_writer
            .as_ref()
            .is_some_and(|writer| writer.final_path == requested)
        {
            return;
        }
        if let Some(mut previous) = self.reference_build_writer.take() {
            if let Err(error) = previous.finalize() {
                log::error!("NSESche {error}");
                self.reference_build_writer_error = Some(error);
                return;
            }
        }
        match ReferenceBuildWriter::new(requested) {
            Ok(writer) => {
                self.reference_build_writer = Some(writer);
                self.reference_build_writer_error = None;
            }
            Err(error) => {
                log::error!("NSESche {error}");
                self.reference_build_writer_error = Some(error);
            }
        }
    }

    fn persist_reference_build_record(
        &mut self,
        state_key: u64,
        reference: Option<f32>,
        initial_assignment_hash: u64,
        player_count: usize,
        sa_iterations: u32,
        compute_us: u64,
    ) -> (u64, bool) {
        if self.settings.reference_mode != "build" {
            return (0, true);
        }
        let start = Instant::now();
        self.ensure_reference_build_writer();
        let result = self
            .reference_build_writer
            .as_mut()
            .ok_or_else(|| {
                self.reference_build_writer_error
                    .clone()
                    .unwrap_or_else(|| "reference build writer is unavailable".to_string())
            })
            .and_then(|writer| {
                writer.record(
                    state_key,
                    reference,
                    initial_assignment_hash,
                    player_count,
                    sa_iterations,
                    compute_us,
                )
            });
        match result {
            Ok(_) => (start.elapsed().as_micros() as u64, true),
            Err(error) => {
                log::error!("NSESche {error}");
                self.reference_build_writer_error = Some(error);
                (start.elapsed().as_micros() as u64, false)
            }
        }
    }

    fn ensure_observation_writer(&mut self, env: &SimEnvObserve) -> Result<(), String> {
        let config = env.help().config();
        if !self.settings.observation_enabled || !config.experiment.output.enabled {
            return Ok(());
        }
        if self.observation_writer.is_some() {
            return Ok(());
        }
        let final_path = Path::new(&config.experiment.output.root)
            .join(&config.experiment.run_id)
            .join("nash_metrics.jsonl");
        match NashObservationWriter::new(final_path) {
            Ok(writer) => {
                self.observation_writer = Some(writer);
                self.observation_writer_error = None;
                Ok(())
            }
            Err(error) => {
                self.observation_writer_error = Some(error.clone());
                Err(error)
            }
        }
    }

    fn emit_observation(&mut self, event: serde_json::Value) {
        log::info!("NSE_METRIC_V2 {}", event);
        if let Some(writer) = self.observation_writer.as_mut() {
            if let Err(error) = writer.record(&event) {
                self.observation_writer_error = Some(error.clone());
                panic!("NSESche observation output failed: {error}");
            }
        }
    }

    fn ensure_function_profiles(&mut self, env: &SimEnvObserve) {
        let function_count = env.core().fns().len();
        if self.profile_function_count == function_count
            && self.profile_heterogeneity_enabled == self.settings.heterogeneity_enabled
            && self.function_profiles.len() == function_count
        {
            return;
        }

        let functions = {
            let functions = env.core().fns();
            functions
                .iter()
                .map(|function| {
                    (
                        function.fn_id,
                        function.dag_id,
                        function.cpu,
                        function.mem,
                        function.out_put_size,
                        function.cold_start_time,
                        if env.help().config().experiment.qos.enabled {
                            function.quality_weight
                        } else {
                            self.settings.quality_weight
                        },
                        function
                            .cold_start_container_mem_use
                            .max(function.container_mem()),
                    )
                })
                .collect::<Vec<_>>()
        };
        let max_cpu = functions
            .iter()
            .map(|function| function.2)
            .fold(EPSILON, f32::max);
        let max_memory = functions
            .iter()
            .map(|function| function.3)
            .fold(EPSILON, f32::max);
        let dags = env.core().dags();

        self.function_profiles.clear();
        self.function_parents.clear();
        for (
            fn_id,
            dag_id,
            cpu,
            memory,
            output_mb,
            cold_start_frames,
            quality_weight,
            required_memory,
        ) in functions
        {
            let dag_node_count = dags
                .get(dag_id)
                .map(|dag| dag.dag_inner.node_count())
                .unwrap_or(1)
                .max(1);
            let heterogeneity = HeterogeneityProfile::new(
                cpu / max_cpu,
                memory / max_memory,
                dag_node_count,
                self.settings.heterogeneity_enabled,
            );
            let parents = env.func(fn_id).parent_fns(env);
            self.function_parents.insert(fn_id, parents);
            self.function_profiles.insert(
                fn_id,
                FunctionProfile {
                    fn_id,
                    raw_cpu: cpu,
                    raw_memory: memory,
                    output_mb,
                    cold_start_frames,
                    dag_node_count,
                    required_container_memory: required_memory,
                    quality_weight,
                    heterogeneity,
                },
            );
        }
        self.profile_function_count = function_count;
        self.profile_heterogeneity_enabled = self.settings.heterogeneity_enabled;
    }

    fn collect_players(&mut self, env: &SimEnvObserve) -> Vec<PlayerId> {
        let requests = env.core().requests();
        let mut players = Vec::new();
        for request in requests.values() {
            for fn_id in schedule_helper::collect_task_to_sche(
                request,
                env,
                schedule_helper::CollectTaskConfig::All,
            ) {
                let player = PlayerId {
                    req_id: request.req_id,
                    fn_id,
                };
                if !request.fn_node.contains_key(&fn_id)
                    && self.function_profiles.contains_key(&fn_id)
                {
                    players.push(player);
                }
            }
        }
        players.sort_unstable();
        players.dedup();
        players
    }

    fn ensure_network_proxy(&mut self, env: &SimEnvObserve) {
        let node_count = env.node_cnt();
        if self.network_initialized && self.network_node_count == node_count {
            return;
        }
        self.network_initialized = true;
        self.network_node_count = node_count;
        if node_count < 2 {
            self.network_beta_proxy = 1.0;
            self.network_latency_mean_ms = 0.0;
            self.network_latency_max_ms = 0.0;
            return;
        }

        let mut link_latencies = Vec::with_capacity(node_count * (node_count - 1));
        for first in 0..node_count {
            for second in 0..node_count {
                if first == second {
                    continue;
                }
                let speed_mb_s = env.node_get_speed_btwn(first, second);
                if speed_mb_s > EPSILON {
                    // The simulator exposes configured MB/s rather than measured
                    // RTT.  One-MB transfer time is therefore used as an explicit
                    // latency proxy for Eq. (14), never reported as physical RTT.
                    link_latencies.push(1000.0 / speed_mb_s);
                }
            }
        }
        if link_latencies.is_empty() {
            self.network_beta_proxy = 1.0;
            self.network_latency_mean_ms = 0.0;
            self.network_latency_max_ms = 0.0;
            return;
        }
        let latency_sum = link_latencies.iter().sum::<f32>();
        let measured_max = link_latencies.iter().copied().fold(0.0f32, f32::max);
        self.network_latency_mean_ms = latency_sum / link_latencies.len() as f32;
        self.network_latency_max_ms = measured_max;
    }

    fn update_dynamic_network_proxy(
        &mut self,
        env: &SimEnvObserve,
        transfers: &[(NodeId, NodeId, f32)],
    ) {
        let node_count = self.node_snapshots.len();
        self.network_beta_proxy = 1.0;
        self.active_network_transfers = 0;
        self.active_network_remaining_mb = 0.0;
        self.dynamic_link_delay_mean_ms = 0.0;
        self.dynamic_link_delay_max_ms = 0.0;
        self.saturated_dynamic_links = 0;
        if node_count < 2 {
            self.network_latency_normalizer_used_ms =
                self.settings.network_latency_normalizer_ms.unwrap_or(0.0);
            return;
        }

        let mut link_delay_ms = vec![0.0f32; node_count * node_count];
        for &(source, destination, remaining_mb) in transfers {
            if source >= node_count
                || destination >= node_count
                || source == destination
                || remaining_mb <= EPSILON
            {
                continue;
            }
            self.active_network_transfers += 1;
            self.active_network_remaining_mb += remaining_mb;
            let speed_mb_s = env.node_get_speed_btwn(source, destination);
            if speed_mb_s > EPSILON {
                link_delay_ms[source * node_count + destination] +=
                    remaining_mb / speed_mb_s * 1000.0;
            }
        }

        let pair_count = node_count * (node_count - 1);
        let mut delay_sum = 0.0f32;
        let mut delay_max = 0.0f32;
        for source in 0..node_count {
            for destination in 0..node_count {
                if source == destination {
                    continue;
                }
                let delay = link_delay_ms[source * node_count + destination];
                delay_sum += delay;
                delay_max = delay_max.max(delay);
            }
        }
        self.dynamic_link_delay_mean_ms = delay_sum / pair_count as f32;
        self.dynamic_link_delay_max_ms = delay_max;
        let latency_bound = self
            .settings
            .network_latency_normalizer_ms
            .unwrap_or(self.network_latency_max_ms.max(EPSILON));
        self.network_latency_normalizer_used_ms = latency_bound;
        let mut normalized_delay_sum = 0.0f32;
        for source in 0..node_count {
            for destination in 0..node_count {
                if source == destination {
                    continue;
                }
                let delay = link_delay_ms[source * node_count + destination];
                if delay > latency_bound {
                    self.saturated_dynamic_links += 1;
                }
                // Eq. (14) normalizes by the configured l_max; it does not
                // saturate an observed delay that exceeds that bound.  Keep
                // the ratio itself so overload remains visible in beta, and
                // count above-bound links separately for observability.
                normalized_delay_sum += (delay / latency_bound).max(0.0);
            }
        }
        self.network_beta_proxy = 1.0 + normalized_delay_sum / pair_count as f32;
    }

    fn update_node_snapshots(&mut self, env: &SimEnvObserve) {
        self.ensure_network_proxy(env);
        let node_count = env.node_cnt();
        self.node_snapshots = vec![NodeSnapshot::default(); node_count];
        self.available_container_memory = vec![0.0; node_count];
        self.existing_containers.clear();
        self.warm_containers.clear();
        let mut active_transfers = Vec::new();

        let requests = env.core().requests();
        let nodes = env.nodes();
        for node in nodes.iter() {
            let node_id = node.node_id();
            let cpu_utilization = if node.rsc_limit.cpu > EPSILON {
                (node.cpu / node.rsc_limit.cpu).clamp(0.0, 1.0)
            } else {
                0.0
            };
            let memory_utilization = if node.rsc_limit.mem > EPSILON {
                (node.unready_mem() / node.rsc_limit.mem).clamp(0.0, 1.0)
            } else {
                0.0
            };
            let queue = node.queue_breakdown(env);
            let resident_tasks = queue.resident_total();
            debug_assert_eq!(resident_tasks, node.running_task_cnt());
            let (container_count, running_containers) = {
                let containers = node.fn_containers.borrow();
                let mut function_ids = containers.keys().copied().collect::<Vec<_>>();
                function_ids.sort_unstable();
                let mut running_containers = 0usize;
                for fn_id in function_ids {
                    let container = containers
                        .get(&fn_id)
                        .expect("function ID came from the container map");
                    self.existing_containers.insert((fn_id, node_id));
                    if container.is_running() {
                        running_containers += 1;
                        self.warm_containers.insert((fn_id, node_id));
                        let parents = self.function_parents.get(&fn_id);
                        let mut request_ids =
                            container.req_fn_state.keys().copied().collect::<Vec<_>>();
                        request_ids.sort_unstable();
                        for req_id in request_ids {
                            let task = container
                                .req_fn_state
                                .get(&req_id)
                                .expect("request ID came from the running-task map");
                            let parents_all_done = requests
                                .get(&req_id)
                                .map(|request| {
                                    parents.is_none_or(|parents| {
                                        parents
                                            .iter()
                                            .all(|parent| request.done_fns.contains_key(parent))
                                    })
                                })
                                .unwrap_or(false);
                            if !parents_all_done {
                                continue;
                            }
                            let mut source_nodes =
                                task.data_recv.keys().copied().collect::<Vec<_>>();
                            source_nodes.sort_unstable();
                            for source in source_nodes {
                                let &(need_mb, received_mb) = task
                                    .data_recv
                                    .get(&source)
                                    .expect("source node came from the transfer map");
                                let remaining_mb = (need_mb - received_mb).max(0.0);
                                if remaining_mb > EPSILON {
                                    active_transfers.push((source, node_id, remaining_mb));
                                }
                            }
                        }
                    }
                }
                (containers.len(), running_containers)
            };
            // Eq. (6)'s q_n(t) counts work that can contend for execution now.
            // Tasks blocked by a cold-start, unfinished DAG parents, or input
            // transfer remain observable below but do not inflate CPU queue
            // pressure until they become runnable.
            let queue_ratio = normalized_queue_pressure(
                queue.pressure_queue_len(),
                self.settings.queue_normalizer,
            );
            let pressure = cpu_utilization + memory_utilization + queue_ratio;
            let utilization = ((cpu_utilization + memory_utilization) * 0.5).clamp(0.0, 1.0);
            self.node_snapshots[node_id] = NodeSnapshot {
                cpu_utilization,
                memory_utilization,
                pending_tasks: queue.pending,
                runnable_tasks: queue.runnable,
                parent_blocked_tasks: queue.parent_blocked,
                data_blocked_tasks: queue.data_blocked,
                starting_resident_tasks: queue.starting_resident,
                resident_tasks,
                container_count,
                running_containers,
                pressure,
                utilization,
            };
            self.available_container_memory[node_id] = node.left_mem_for_place_container().max(0.0);
        }
        drop(nodes);
        drop(requests);
        self.update_dynamic_network_proxy(env, &active_transfers);
    }

    /// Snapshot the common placement-feasible set for every request/function
    /// player.  The request is deliberately part of the key: two invocations
    /// of the same function can have different feasible paths because their
    /// parent functions may have been placed on different nodes.
    fn update_feasible_nodes(&mut self, env: &SimEnvObserve, players: &[PlayerId]) {
        self.feasible_nodes.clear();
        let requests = env.core().requests();
        for &player in players {
            let candidates = requests
                .get(&player.req_id)
                .map(|request| schedule_helper::placement_candidate_ids(request, player.fn_id, env))
                .unwrap_or_default();
            self.feasible_nodes.insert(player, candidates);
        }
    }

    fn build_existing_aggregates(&mut self, env: &SimEnvObserve) -> Vec<NodeAggregate> {
        let mut aggregates = vec![NodeAggregate::default(); self.node_snapshots.len()];
        let requests = env.core().requests();
        let mut cross_node_assignments = 0usize;
        let mut total_assignments = 0usize;
        // `Request::fn_node` is a `HashMap`.  Its per-process iteration order
        // must not decide the order of floating-point aggregation: otherwise
        // the same tape can produce a one-ULP-different price signal and hence
        // a different bit-exact offline-reference key.  Requests themselves
        // are already held in a `BTreeMap`; make the function order explicit
        // as well so build and replay observe the same state.
        for request in requests.values() {
            let active_assignments = stable_function_assignments(&request.fn_node)
                .into_iter()
                .filter(|(fn_id, _)| !request.done_fns.contains_key(fn_id))
                .collect::<Vec<_>>();
            let distinct_nodes: HashSet<NodeId> = active_assignments
                .iter()
                .map(|&(_, node_id)| node_id)
                .collect();
            let active_assignment_count = active_assignments.len();
            total_assignments += active_assignment_count;
            if distinct_nodes.len() > 1 {
                cross_node_assignments += active_assignment_count.saturating_sub(1);
            }
            for (fn_id, node_id) in active_assignments {
                if node_id >= aggregates.len() {
                    continue;
                }
                let Some(profile) = self.function_profiles.get(&fn_id) else {
                    continue;
                };
                aggregates[node_id].request_count += 1;
                aggregates[node_id].resource_intensity_sum +=
                    profile.heterogeneity.resource_intensity;
                aggregates[node_id].impact_sum += profile.heterogeneity.impact();
            }
        }
        self.cross_node_placement_ratio = if total_assignments == 0 {
            0.0
        } else {
            cross_node_assignments as f32 / total_assignments as f32
        };
        aggregates
    }

    fn build_price_signal(&self, existing: &[NodeAggregate]) -> PriceSignal {
        let node_count = self.node_snapshots.len().max(1);
        let global_load = self
            .node_snapshots
            .iter()
            .map(|node| node.cpu_utilization + node.memory_utilization)
            .sum::<f32>()
            / node_count as f32;
        let mut baseline_prices = Vec::with_capacity(self.node_snapshots.len());
        let mut premiums = Vec::with_capacity(self.node_snapshots.len());

        for (node_id, node) in self.node_snapshots.iter().enumerate() {
            let aggregate = existing.get(node_id).copied().unwrap_or_default();
            let congestion_premium = if aggregate.request_count == 0 {
                0.0
            } else {
                (aggregate.resource_intensity_sum / aggregate.request_count as f32)
                    * node.utilization
            };
            let price = if self.settings.congestion_pricing_enabled {
                // Eqs. (11)-(12).
                self.settings.base_node_price * (1.0 + node.pressure) * (1.0 + congestion_premium)
            } else {
                self.settings.base_node_price
            };
            baseline_prices.push(if price.is_finite() {
                price.max(EPSILON)
            } else {
                self.settings.base_node_price
            });
            premiums.push(congestion_premium);
        }

        PriceSignal {
            adjusted_prices: baseline_prices.clone(),
            baseline_prices,
            node_congestion_premiums: premiums,
            global_load,
            network_congestion: self.network_beta_proxy,
        }
    }

    /// Eq. (8) sums the other functions in the current joint decision `S`.
    /// Already-running functions are represented by `Pressure(t)` and by the
    /// Eq. (12) congestion premium; seeding the game state with them as well
    /// would count the same contention twice and can make the social reference
    /// negative even for a feasible scheduling window.
    fn empty_window_aggregates(&self) -> Vec<NodeAggregate> {
        vec![NodeAggregate::default(); self.node_snapshots.len()]
    }

    fn utility(
        &self,
        player: PlayerId,
        node_id: NodeId,
        other_impact_sum: f32,
        signal: &PriceSignal,
    ) -> Option<UtilityBreakdown> {
        let profile = self.function_profiles.get(&player.fn_id)?;
        let node = self.node_snapshots.get(node_id)?;
        let price = signal.adjusted_prices.get(node_id).copied()?;
        let heterogeneity = profile.heterogeneity;

        // Eqs. (2)-(6).
        let baseline_reward = self.settings.base_utility
            * (heterogeneity.resource_intensity + heterogeneity.function_complexity);
        let cost = price * (1.0 + heterogeneity.resource_intensity);
        let quality = profile.quality_weight
            * (heterogeneity.function_complexity + heterogeneity.network_dependency)
            / (1.0 + node.pressure);

        // Eqs. (7)-(9).  Node impact sums make Eq. (8) O(1).
        let externality = if self.settings.externality_enabled {
            heterogeneity.resource_intensity * node.pressure * other_impact_sum.max(0.0)
        } else {
            0.0
        };
        let contribution = if self.settings.contribution_enabled {
            self.settings.contribution_coefficient
                * (1.0 + heterogeneity.differentiation)
                * (1.0 - node.utilization)
        } else {
            0.0
        };
        let total = baseline_reward - cost + quality - externality + contribution;
        total.is_finite().then_some(UtilityBreakdown {
            baseline_reward,
            cost,
            quality,
            externality,
            contribution,
            total,
        })
    }

    fn candidate_is_better(
        &self,
        player: PlayerId,
        old_node: Option<NodeId>,
        candidate_node: NodeId,
        candidate_utility: f32,
        best: Option<(NodeId, f32)>,
    ) -> bool {
        let Some((best_node, best_utility)) = best else {
            return true;
        };
        if candidate_utility > best_utility + EPSILON {
            return true;
        }
        if (candidate_utility - best_utility).abs() > EPSILON {
            return false;
        }

        let candidate_is_old = old_node == Some(candidate_node);
        let best_is_old = old_node == Some(best_node);
        if candidate_is_old != best_is_old {
            return candidate_is_old;
        }
        let candidate_is_warm = self
            .warm_containers
            .contains(&(player.fn_id, candidate_node));
        let best_is_warm = self.warm_containers.contains(&(player.fn_id, best_node));
        if candidate_is_warm != best_is_warm {
            return candidate_is_warm;
        }
        candidate_node < best_node
    }

    fn best_response(
        &self,
        player: PlayerId,
        old_node: Option<NodeId>,
        state_without_player: &AssignmentState,
        signal: &PriceSignal,
    ) -> (Option<(NodeId, f32)>, usize) {
        let Some(candidates) = self.feasible_nodes.get(&player) else {
            return (None, 0);
        };
        let mut best = None;
        let mut evaluations = 0usize;
        for &node_id in candidates {
            if !state_without_player.can_add(
                player,
                node_id,
                &self.existing_containers,
                &self.available_container_memory,
                &self.function_profiles,
                &self.new_container_limits,
            ) {
                continue;
            }
            let other_impact_sum = state_without_player.node_aggregates[node_id].impact_sum;
            let Some(utility) = self.utility(player, node_id, other_impact_sum, signal) else {
                continue;
            };
            evaluations += 1;
            if self.candidate_is_better(player, old_node, node_id, utility.total, best) {
                best = Some((node_id, utility.total));
            }
        }
        (best, evaluations)
    }

    fn initialize_assignment(
        &self,
        players: &[PlayerId],
        base_aggregates: Vec<NodeAggregate>,
        signal: &PriceSignal,
        stats: &mut SolveStats,
        no_feasible: &mut HashSet<PlayerId>,
    ) -> AssignmentState {
        let start = Instant::now();
        let mut state = AssignmentState::new(base_aggregates, players.len());
        for &player in players {
            let (best, evaluations) = self.best_response(player, None, &state, signal);
            stats.initialization_evaluations += evaluations;
            if let Some((node_id, _)) = best {
                state.add(
                    player,
                    node_id,
                    &self.existing_containers,
                    &self.function_profiles,
                );
            } else {
                no_feasible.insert(player);
            }
        }
        stats.initialization_us = start.elapsed().as_micros() as u64;
        state
    }

    fn assignment_fingerprint(players: &[PlayerId], state: &AssignmentState) -> u64 {
        fn mix(hash: &mut u64, value: u64) {
            *hash ^= value;
            *hash = hash.wrapping_mul(1_099_511_628_211);
        }
        let mut hash = 14_695_981_039_346_656_037u64;
        let mut stable_players = players.to_vec();
        stable_players.sort_unstable();
        stable_players.dedup();
        for player in stable_players {
            mix(&mut hash, player.req_id as u64);
            mix(&mut hash, player.fn_id as u64);
            mix(
                &mut hash,
                state
                    .assignments
                    .get(&player)
                    .copied()
                    .unwrap_or(usize::MAX) as u64,
            );
        }
        hash
    }

    fn node_social_welfare(
        &self,
        node_id: NodeId,
        state: &AssignmentState,
        signal: &PriceSignal,
    ) -> UtilityBreakdown {
        let Some(players) = state.player_node_aggregates.get(node_id).copied() else {
            return UtilityBreakdown::default();
        };
        let Some(all_assignments) = state.node_aggregates.get(node_id).copied() else {
            return UtilityBreakdown::default();
        };
        self.node_social_welfare_from_aggregates(node_id, players, all_assignments, signal)
    }

    fn node_social_welfare_from_aggregates(
        &self,
        node_id: NodeId,
        players: PlayerNodeAggregate,
        all_assignments: NodeAggregate,
        signal: &PriceSignal,
    ) -> UtilityBreakdown {
        let Some(node) = self.node_snapshots.get(node_id) else {
            return UtilityBreakdown::default();
        };
        let Some(price) = signal.adjusted_prices.get(node_id).copied() else {
            return UtilityBreakdown::default();
        };

        let baseline_reward = self.settings.base_utility * players.baseline_feature_sum;
        let cost = price * players.cost_weight_sum;
        let quality = players.quality_feature_sum / (1.0 + node.pressure);
        let externality = if self.settings.externality_enabled {
            node.pressure
                * (players.resource_intensity_sum * all_assignments.impact_sum
                    - players.resource_impact_sum)
                    .max(0.0)
        } else {
            0.0
        };
        let contribution = if self.settings.contribution_enabled {
            self.settings.contribution_coefficient
                * (1.0 - node.utilization)
                * players.contribution_feature_sum
        } else {
            0.0
        };
        UtilityBreakdown {
            baseline_reward,
            cost,
            quality,
            externality,
            contribution,
            total: baseline_reward - cost + quality - externality + contribution,
        }
    }

    fn social_welfare_after_add(
        &self,
        player: PlayerId,
        node_id: NodeId,
        state_without_player: &AssignmentState,
        welfare_without_player: f32,
        signal: &PriceSignal,
    ) -> Option<f32> {
        if !state_without_player.can_add(
            player,
            node_id,
            &self.existing_containers,
            &self.available_container_memory,
            &self.function_profiles,
            &self.new_container_limits,
        ) {
            return None;
        }
        let profile = self.function_profiles.get(&player.fn_id)?;
        let mut all_assignments = state_without_player.node_aggregates.get(node_id).copied()?;
        let mut players = state_without_player
            .player_node_aggregates
            .get(node_id)
            .copied()?;
        let previous = self
            .node_social_welfare_from_aggregates(node_id, players, all_assignments, signal)
            .total;
        let heterogeneity = profile.heterogeneity;
        all_assignments.request_count += 1;
        all_assignments.resource_intensity_sum += heterogeneity.resource_intensity;
        all_assignments.impact_sum += heterogeneity.impact();
        players.baseline_feature_sum +=
            heterogeneity.resource_intensity + heterogeneity.function_complexity;
        players.cost_weight_sum += 1.0 + heterogeneity.resource_intensity;
        players.quality_feature_sum += profile.quality_weight
            * (heterogeneity.function_complexity + heterogeneity.network_dependency);
        players.resource_intensity_sum += heterogeneity.resource_intensity;
        players.resource_impact_sum += heterogeneity.resource_intensity * heterogeneity.impact();
        players.contribution_feature_sum += 1.0 + heterogeneity.differentiation;
        let next = self
            .node_social_welfare_from_aggregates(node_id, players, all_assignments, signal)
            .total;
        let welfare = welfare_without_player - previous + next;
        welfare.is_finite().then_some(welfare)
    }

    fn social_welfare(
        &self,
        _players: &[PlayerId],
        state: &AssignmentState,
        signal: &PriceSignal,
    ) -> UtilityBreakdown {
        let mut total = UtilityBreakdown::default();
        for node_id in 0..state.node_aggregates.len() {
            total += self.node_social_welfare(node_id, state, signal);
        }
        total
    }

    fn placement_diagnostics(
        &self,
        players: &[PlayerId],
        state: &AssignmentState,
        signal: &PriceSignal,
    ) -> PlacementDiagnostics {
        let mut diagnostics = PlacementDiagnostics::default();
        if state.assignments.is_empty() {
            return diagnostics;
        }

        let mut occupancy = HashMap::<NodeId, usize>::new();
        let mut differentiation_sum = 0.0f32;
        let mut differentiation_count = 0usize;
        for node_id in state.assignments.values().copied() {
            *occupancy.entry(node_id).or_insert(0) += 1;
        }
        for player in players {
            if let Some(profile) = self.function_profiles.get(&player.fn_id) {
                differentiation_sum += profile.heterogeneity.differentiation;
                differentiation_count += 1;
            }
        }
        diagnostics.active_differentiation_mean = if differentiation_count == 0 {
            0.0
        } else {
            differentiation_sum / differentiation_count as f32
        };
        diagnostics.assigned_nodes = occupancy.len();
        let assigned = state.assignments.len();
        let hhi = occupancy
            .values()
            .map(|&count| {
                let share = count as f32 / assigned as f32;
                share * share
            })
            .sum::<f32>();
        let maximum_distinct = assigned.min(self.node_snapshots.len());
        diagnostics.normalized_dispersion = if maximum_distinct <= 1 {
            0.0
        } else {
            ((1.0 - hhi) / (1.0 - 1.0 / maximum_distinct as f32)).clamp(0.0, 1.0)
        };
        diagnostics.co_location_pairs = occupancy
            .values()
            .map(|&count| count.saturating_mul(count.saturating_sub(1)) / 2)
            .sum();
        let all_pairs = assigned.saturating_mul(assigned.saturating_sub(1)) / 2;
        diagnostics.co_location_pair_ratio = if all_pairs == 0 {
            0.0
        } else {
            diagnostics.co_location_pairs as f32 / all_pairs as f32
        };

        for &player in players {
            let Some(&assigned_node) = state.assignments.get(&player) else {
                continue;
            };
            let Some(profile) = self.function_profiles.get(&player.fn_id) else {
                continue;
            };
            let Some(candidates) = self.feasible_nodes.get(&player) else {
                continue;
            };
            let mut full_scores = Vec::<(NodeId, f32)>::new();
            let mut without_differentiation_scores = Vec::<(NodeId, f32)>::new();
            for &node_id in candidates {
                let Some(node) = self.node_snapshots.get(node_id) else {
                    continue;
                };
                let mut other_impact = state
                    .node_aggregates
                    .get(node_id)
                    .map(|aggregate| aggregate.impact_sum)
                    .unwrap_or(0.0);
                if node_id == assigned_node {
                    other_impact = (other_impact - profile.heterogeneity.impact()).max(0.0);
                }
                let Some(utility) = self.utility(player, node_id, other_impact, signal) else {
                    continue;
                };
                let contribution_without_differentiation = if self.settings.contribution_enabled {
                    self.settings.contribution_coefficient * (1.0 - node.utilization)
                } else {
                    0.0
                };
                full_scores.push((node_id, utility.total));
                without_differentiation_scores.push((
                    node_id,
                    utility.total - utility.contribution + contribution_without_differentiation,
                ));
            }
            if full_scores.is_empty() {
                continue;
            }
            let rank = |scores: &mut Vec<(NodeId, f32)>| {
                scores.sort_by(|left, right| {
                    right
                        .1
                        .total_cmp(&left.1)
                        .then_with(|| left.0.cmp(&right.0))
                });
            };
            rank(&mut full_scores);
            rank(&mut without_differentiation_scores);
            diagnostics.evaluated_players += 1;
            if full_scores.len() > 1 && (full_scores[0].1 - full_scores[1].1).abs() <= EPSILON {
                diagnostics.near_tie_players += 1;
            }
            if full_scores[0].0 != without_differentiation_scores[0].0 {
                diagnostics.differentiation_changed_choice_players += 1;
            }
        }
        diagnostics
    }

    fn run_inner_loop(
        &self,
        players: &[PlayerId],
        state: &mut AssignmentState,
        signal: &PriceSignal,
        stats: &mut SolveStats,
        no_feasible: &mut HashSet<PlayerId>,
    ) -> InnerOutcome {
        let inner_start_round = stats.inner_rounds;
        let mut seen_assignments = HashSet::new();
        seen_assignments.insert(Self::assignment_fingerprint(players, state));
        let mut best_state = state.clone();
        let mut best_welfare = if state.assignments.len() == players.len() {
            self.social_welfare(players, state, signal).total
        } else {
            f32::NEG_INFINITY
        };

        for _ in 0..self.settings.max_inner_rounds {
            stats.inner_rounds += 1;
            let mut moves = 0usize;
            for &player in players {
                let old_node =
                    state.remove(player, &self.existing_containers, &self.function_profiles);
                let (best, evaluations) = self.best_response(player, old_node, state, signal);
                stats.candidate_evaluations += evaluations;
                if let Some((node_id, _)) = best {
                    state.add(
                        player,
                        node_id,
                        &self.existing_containers,
                        &self.function_profiles,
                    );
                    if old_node != Some(node_id) {
                        moves += 1;
                    }
                    no_feasible.remove(&player);
                } else if let Some(node_id) = old_node {
                    state.add(
                        player,
                        node_id,
                        &self.existing_containers,
                        &self.function_profiles,
                    );
                    no_feasible.insert(player);
                } else {
                    no_feasible.insert(player);
                }
            }

            stats.assignment_moves += moves;
            stats.assignment_moves_per_round.push(moves);
            let complete = state.assignments.len() == players.len() && no_feasible.is_empty();
            if complete {
                let welfare = self.social_welfare(players, state, signal).total;
                if welfare > best_welfare + EPSILON {
                    best_welfare = welfare;
                    best_state = state.clone();
                }
            }
            if moves == 0 && complete {
                stats
                    .inner_rounds_per_outer
                    .push(stats.inner_rounds - inner_start_round);
                return InnerOutcome {
                    stable: true,
                    infeasible: false,
                    oscillated: false,
                };
            }
            if !complete && moves == 0 {
                stats
                    .inner_rounds_per_outer
                    .push(stats.inner_rounds - inner_start_round);
                return InnerOutcome {
                    stable: false,
                    infeasible: true,
                    oscillated: false,
                };
            }
            let fingerprint = Self::assignment_fingerprint(players, state);
            if !seen_assignments.insert(fingerprint) {
                *state = best_state;
                stats.oscillation_count += 1;
                stats
                    .inner_rounds_per_outer
                    .push(stats.inner_rounds - inner_start_round);
                return InnerOutcome {
                    stable: false,
                    infeasible: false,
                    oscillated: true,
                };
            }
        }

        stats.hit_inner_limit = true;
        *state = best_state;
        no_feasible.clear();
        stats
            .inner_rounds_per_outer
            .push(stats.inner_rounds - inner_start_round);
        InnerOutcome {
            stable: false,
            infeasible: state.assignments.len() != players.len(),
            oscillated: false,
        }
    }

    fn deterministic_random(state: &mut u64) -> u64 {
        *state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        *state
    }

    fn reference_neighborhood_size(&self, players: &[PlayerId]) -> usize {
        players
            .iter()
            .map(|player| {
                let mut candidates = self.feasible_nodes.get(player).cloned().unwrap_or_default();
                candidates.sort_unstable();
                candidates.dedup();
                candidates
                    .into_iter()
                    .filter(|&node_id| node_id < self.node_snapshots.len())
                    .count()
            })
            .sum()
    }

    fn effective_sa_iterations(&self, players: &[PlayerId]) -> u32 {
        let player_scaled = self
            .settings
            .sa_iterations_per_player
            .saturating_mul(players.len().min(u32::MAX as usize) as u32);
        let candidate_scaled = self
            .reference_neighborhood_size(players)
            .min(u32::MAX as usize) as u32;
        self.settings
            .sa_iterations
            .max(player_scaled)
            .max(candidate_scaled)
            .min(100_000)
    }

    fn reference_local_evaluation_budget(&self, players: &[PlayerId]) -> usize {
        self.reference_neighborhood_size(players)
            .saturating_mul(players.len().max(4))
            .clamp(1, SOCIAL_REFERENCE_LOCAL_EVALUATION_LIMIT)
    }

    fn social_reference_key(
        &self,
        players: &[PlayerId],
        existing: &[NodeAggregate],
        signal: &PriceSignal,
    ) -> u64 {
        fn mix(hash: &mut u64, value: u64) {
            *hash ^= value;
            *hash = hash.wrapping_mul(1_099_511_628_211);
        }
        let mut multiplicities = HashMap::<FnId, usize>::new();
        for player in players {
            *multiplicities.entry(player.fn_id).or_insert(0) += 1;
        }
        let mut function_ids: Vec<FnId> = multiplicities.keys().copied().collect();
        function_ids.sort_unstable();

        let mut hash = 14_695_981_039_346_656_037u64;
        mix(&mut hash, REFERENCE_KEY_SCHEMA_VERSION);
        mix(&mut hash, self.settings.base_utility.to_bits() as u64);
        mix(&mut hash, self.settings.quality_weight.to_bits() as u64);
        mix(
            &mut hash,
            self.settings.contribution_coefficient.to_bits() as u64,
        );
        mix(&mut hash, self.settings.externality_enabled as u64);
        mix(&mut hash, self.settings.contribution_enabled as u64);
        mix(&mut hash, self.settings.sa_iterations as u64);
        mix(&mut hash, self.settings.sa_iterations_per_player as u64);
        mix(
            &mut hash,
            self.settings.sa_initial_temperature.to_bits() as u64,
        );
        mix(&mut hash, self.settings.sa_cooling_rate.to_bits() as u64);
        for fn_id in function_ids {
            mix(&mut hash, fn_id as u64);
            mix(&mut hash, multiplicities[&fn_id] as u64);
            if let Some(profile) = self.function_profiles.get(&fn_id) {
                mix(&mut hash, profile.quality_weight.to_bits() as u64);
                mix(
                    &mut hash,
                    profile.heterogeneity.resource_intensity.to_bits() as u64,
                );
                mix(
                    &mut hash,
                    profile.heterogeneity.function_complexity.to_bits() as u64,
                );
                mix(
                    &mut hash,
                    profile.heterogeneity.network_dependency.to_bits() as u64,
                );
                mix(
                    &mut hash,
                    profile.heterogeneity.differentiation.to_bits() as u64,
                );
            }
            mix(
                &mut hash,
                self.new_container_limits
                    .get(&fn_id)
                    .copied()
                    .unwrap_or(usize::MAX) as u64,
            );
            mix(&mut hash, u64::MAX);
        }
        let mut stable_players = players.to_vec();
        stable_players.sort_unstable();
        stable_players.dedup();
        for player in stable_players {
            mix(&mut hash, player.req_id as u64);
            mix(&mut hash, player.fn_id as u64);
            if let Some(candidates) = self.feasible_nodes.get(&player) {
                let mut stable_candidates = candidates.clone();
                stable_candidates.sort_unstable();
                stable_candidates.dedup();
                for node_id in stable_candidates {
                    mix(&mut hash, node_id as u64);
                }
            }
            mix(&mut hash, u64::MAX - 1);
        }
        for (node_id, node) in self.node_snapshots.iter().enumerate() {
            mix(&mut hash, node_id as u64);
            mix(&mut hash, node.pressure.to_bits() as u64);
            mix(&mut hash, node.utilization.to_bits() as u64);
            mix(
                &mut hash,
                existing
                    .get(node_id)
                    .map(|value| value.request_count)
                    .unwrap_or(0) as u64,
            );
            mix(
                &mut hash,
                existing
                    .get(node_id)
                    .map(|value| value.resource_intensity_sum.to_bits())
                    .unwrap_or(0) as u64,
            );
            mix(
                &mut hash,
                existing
                    .get(node_id)
                    .map(|value| value.impact_sum.to_bits())
                    .unwrap_or(0) as u64,
            );
            mix(&mut hash, signal.baseline_prices[node_id].to_bits() as u64);
            mix(
                &mut hash,
                self.available_container_memory
                    .get(node_id)
                    .copied()
                    .unwrap_or(0.0)
                    .to_bits() as u64,
            );
        }
        let mut existing_pairs = self
            .existing_containers
            .iter()
            .copied()
            .filter(|(fn_id, _)| multiplicities.contains_key(fn_id))
            .collect::<Vec<_>>();
        existing_pairs.sort_unstable();
        for (fn_id, node_id) in existing_pairs {
            mix(&mut hash, fn_id as u64);
            mix(&mut hash, node_id as u64);
        }
        hash
    }

    fn construct_reference_state(
        &self,
        player_order: &[PlayerId],
        baseline_signal: &PriceSignal,
    ) -> Option<AssignmentState> {
        let mut state = AssignmentState::new(self.empty_window_aggregates(), player_order.len());
        for &player in player_order {
            let mut candidates = self.feasible_nodes.get(&player)?.clone();
            candidates.sort_unstable();
            candidates.dedup();
            let welfare_without = self
                .social_welfare(player_order, &state, baseline_signal)
                .total;
            let mut best: Option<(NodeId, f32)> = None;
            for node_id in candidates {
                let Some(welfare) = self.social_welfare_after_add(
                    player,
                    node_id,
                    &state,
                    welfare_without,
                    baseline_signal,
                ) else {
                    continue;
                };
                let replace = match best {
                    None => true,
                    Some((best_node, best_welfare)) => {
                        welfare > best_welfare + EPSILON
                            || ((welfare - best_welfare).abs() <= EPSILON && node_id < best_node)
                    }
                };
                if replace {
                    best = Some((node_id, welfare));
                }
            }
            let (node_id, _) = best?;
            state.add(
                player,
                node_id,
                &self.existing_containers,
                &self.function_profiles,
            );
        }
        (state.assignments.len() == player_order.len()).then_some(state)
    }

    /// Construct the primary policy-independent starting allocation.  Each
    /// greedy step maximizes the marginal paper social utility, and exact ties
    /// are resolved only by node ID.  Warm state and the evaluated policy's
    /// assignment are deliberately absent from this search.
    fn canonical_reference_state(
        &self,
        players: &[PlayerId],
        baseline_signal: &PriceSignal,
    ) -> Option<AssignmentState> {
        let mut stable_players = players.to_vec();
        stable_players.sort_unstable();
        stable_players.dedup();
        if stable_players.len() != players.len() {
            return None;
        }
        self.construct_reference_state(&stable_players, baseline_signal)
    }

    fn reference_player_orders(&self, players: &[PlayerId], seed: u64) -> Vec<Vec<PlayerId>> {
        let mut stable_players = players.to_vec();
        stable_players.sort_unstable();
        stable_players.dedup();
        if stable_players.len() != players.len() {
            return Vec::new();
        }

        let mut orders = vec![stable_players.clone()];
        let mut reverse = stable_players.clone();
        reverse.reverse();
        if !orders.contains(&reverse) {
            orders.push(reverse);
        }

        let mut constrained_first = stable_players.clone();
        constrained_first.sort_by_key(|player| {
            let mut candidates = self.feasible_nodes.get(player).cloned().unwrap_or_default();
            candidates.sort_unstable();
            candidates.dedup();
            (candidates.len(), *player)
        });
        if !orders.contains(&constrained_first) {
            orders.push(constrained_first);
        }

        let mut shuffled = stable_players;
        let mut random_state = seed.max(1);
        for index in (1..shuffled.len()).rev() {
            let other = Self::deterministic_random(&mut random_state) as usize % (index + 1);
            shuffled.swap(index, other);
        }
        if !orders.contains(&shuffled) {
            orders.push(shuffled);
        }
        orders
    }

    fn improve_reference_state(
        &self,
        players: &[PlayerId],
        initial_state: &AssignmentState,
        baseline_signal: &PriceSignal,
    ) -> Option<(AssignmentState, f32)> {
        if initial_state.assignments.len() != players.len() {
            return None;
        }
        let mut stable_players = players.to_vec();
        stable_players.sort_unstable();
        stable_players.dedup();
        if stable_players.len() != players.len() {
            return None;
        }

        let mut state = initial_state.clone();
        let mut current = self
            .social_welfare(&stable_players, &state, baseline_signal)
            .total;
        if !current.is_finite() {
            return None;
        }
        let evaluation_budget = self.reference_local_evaluation_budget(&stable_players);
        let mut evaluations = 0usize;

        loop {
            let mut improved = false;
            for &player in &stable_players {
                let mut candidates = self.feasible_nodes.get(&player)?.clone();
                candidates.sort_unstable();
                candidates.dedup();
                if evaluations.saturating_add(candidates.len()) > evaluation_budget {
                    return Some((state, current));
                }

                let old_node = state.assignments.get(&player).copied()?;
                let mut state_without = state.clone();
                state_without.remove(player, &self.existing_containers, &self.function_profiles)?;
                let welfare_without = self
                    .social_welfare(&stable_players, &state_without, baseline_signal)
                    .total;
                let mut best_node = old_node;
                let mut best_welfare = current;
                for node_id in candidates {
                    evaluations += 1;
                    let Some(welfare) = self.social_welfare_after_add(
                        player,
                        node_id,
                        &state_without,
                        welfare_without,
                        baseline_signal,
                    ) else {
                        continue;
                    };
                    if welfare > best_welfare + EPSILON
                        || ((welfare - best_welfare).abs() <= EPSILON && node_id < best_node)
                    {
                        best_node = node_id;
                        best_welfare = welfare;
                    }
                }

                if best_welfare > current + EPSILON {
                    state_without.add(
                        player,
                        best_node,
                        &self.existing_containers,
                        &self.function_profiles,
                    );
                    let exact_welfare = self
                        .social_welfare(&stable_players, &state_without, baseline_signal)
                        .total;
                    if exact_welfare.is_finite() && exact_welfare > current + EPSILON {
                        state = state_without;
                        current = exact_welfare;
                        improved = true;
                    }
                }
            }
            if !improved {
                return Some((state, current));
            }
        }
    }

    fn anneal_reference_state(
        &self,
        players: &[PlayerId],
        initial_state: &AssignmentState,
        baseline_signal: &PriceSignal,
        seed: u64,
    ) -> Option<(AssignmentState, f32, u32)> {
        if players.is_empty() || initial_state.assignments.len() != players.len() {
            return None;
        }
        let mut stable_players = players.to_vec();
        stable_players.sort_unstable();
        stable_players.dedup();
        if stable_players.len() != players.len() {
            return None;
        }

        let mut state = initial_state.clone();
        let mut current = self
            .social_welfare(&stable_players, &state, baseline_signal)
            .total;
        if !current.is_finite() {
            return None;
        }
        let mut best_state = state.clone();
        let mut best = current;
        let utility_scale = (current.abs() / stable_players.len().max(1) as f32).max(1.0);
        let mut temperature = self.settings.sa_initial_temperature * utility_scale;
        let mut random_state = seed.max(1);
        let iterations = self.effective_sa_iterations(&stable_players);

        for _ in 0..iterations {
            let iteration_temperature = temperature;
            temperature *= self.settings.sa_cooling_rate;
            let player_index =
                Self::deterministic_random(&mut random_state) as usize % stable_players.len();
            let player = stable_players[player_index];
            let old_node_before = state.assignments.get(&player).copied();
            let old_welfare_before = old_node_before
                .map(|node_id| {
                    self.node_social_welfare(node_id, &state, baseline_signal)
                        .total
                })
                .unwrap_or(0.0);
            let old_node = state.remove(player, &self.existing_containers, &self.function_profiles);
            let old_welfare_after = old_node
                .map(|node_id| {
                    self.node_social_welfare(node_id, &state, baseline_signal)
                        .total
                })
                .unwrap_or(0.0);
            let mut candidates = self.feasible_nodes.get(&player)?.clone();
            candidates.sort_unstable();
            candidates.dedup();
            if candidates.is_empty() {
                if let Some(node_id) = old_node {
                    state.add(
                        player,
                        node_id,
                        &self.existing_containers,
                        &self.function_profiles,
                    );
                }
                continue;
            }
            let candidate_start =
                Self::deterministic_random(&mut random_state) as usize % candidates.len();
            let candidate_node = (0..candidates.len())
                .map(|offset| candidates[(candidate_start + offset) % candidates.len()])
                .find(|&node_id| {
                    state.can_add(
                        player,
                        node_id,
                        &self.existing_containers,
                        &self.available_container_memory,
                        &self.function_profiles,
                        &self.new_container_limits,
                    )
                });
            let Some(candidate_node) = candidate_node else {
                if let Some(node_id) = old_node {
                    state.add(
                        player,
                        node_id,
                        &self.existing_containers,
                        &self.function_profiles,
                    );
                }
                continue;
            };
            let candidate_welfare_before = self
                .node_social_welfare(candidate_node, &state, baseline_signal)
                .total;
            state.add(
                player,
                candidate_node,
                &self.existing_containers,
                &self.function_profiles,
            );
            let candidate_welfare_after = self
                .node_social_welfare(candidate_node, &state, baseline_signal)
                .total;
            let candidate = current + old_welfare_after - old_welfare_before
                + candidate_welfare_after
                - candidate_welfare_before;
            let delta = candidate - current;
            let random_unit = ((Self::deterministic_random(&mut random_state) >> 11) as f64
                / ((1u64 << 53) as f64)) as f32;
            let acceptance_probability = (delta / iteration_temperature.max(EPSILON))
                .exp()
                .clamp(0.0, 1.0);
            let accept =
                candidate.is_finite() && (delta >= 0.0 || random_unit < acceptance_probability);
            if accept {
                current = candidate;
                if current > best + EPSILON {
                    let exact = self
                        .social_welfare(&stable_players, &state, baseline_signal)
                        .total;
                    if exact.is_finite() {
                        current = exact;
                        if exact > best + EPSILON {
                            best = exact;
                            best_state = state.clone();
                        }
                    }
                }
            } else {
                state.remove(player, &self.existing_containers, &self.function_profiles);
                if let Some(node_id) = old_node {
                    state.add(
                        player,
                        node_id,
                        &self.existing_containers,
                        &self.function_profiles,
                    );
                }
            }
        }
        Some((best_state, best, iterations))
    }

    fn compute_social_reference_sa(
        &self,
        players: &[PlayerId],
        initial_state: &AssignmentState,
        baseline_signal: &PriceSignal,
        seed: u64,
    ) -> Option<ReferenceSearchResult> {
        if players.is_empty() || initial_state.assignments.len() != players.len() {
            return None;
        }

        let mut starts = vec![initial_state.clone()];
        let mut fingerprints = HashSet::new();
        fingerprints.insert(Self::assignment_fingerprint(players, initial_state));
        for order in self.reference_player_orders(players, seed) {
            let Some(state) = self.construct_reference_state(&order, baseline_signal) else {
                continue;
            };
            if fingerprints.insert(Self::assignment_fingerprint(players, &state)) {
                starts.push(state);
            }
        }

        let mut best_state = initial_state.clone();
        let mut best = self
            .social_welfare(players, &best_state, baseline_signal)
            .total;
        if !best.is_finite() {
            return None;
        }
        for start in starts {
            let start_welfare = self.social_welfare(players, &start, baseline_signal).total;
            if start_welfare.is_finite() && start_welfare > best + EPSILON {
                best = start_welfare;
                best_state = start.clone();
            }
            let Some((improved_state, improved_welfare)) =
                self.improve_reference_state(players, &start, baseline_signal)
            else {
                continue;
            };
            if improved_welfare > best + EPSILON {
                best = improved_welfare;
                best_state = improved_state;
            }
        }

        let (annealed_state, annealed_welfare, sa_iterations) =
            self.anneal_reference_state(players, &best_state, baseline_signal, seed)?;
        if annealed_welfare > best + EPSILON {
            best = annealed_welfare;
            best_state = annealed_state.clone();
        }
        if let Some((refined_state, refined_welfare)) =
            self.improve_reference_state(players, &annealed_state, baseline_signal)
        {
            if refined_welfare > best + EPSILON {
                best_state = refined_state;
            }
        }

        // A finite non-positive best feasible value is a real observation. It
        // remains in the build artifact for explicit denominator diagnostics;
        // neither the current policy assignment nor a pseudo-constant is used
        // to raise it.
        let exact_best = self
            .social_welfare(players, &best_state, baseline_signal)
            .total;
        exact_best.is_finite().then_some(ReferenceSearchResult {
            value: exact_best,
            sa_iterations,
        })
    }

    fn get_social_reference(
        &mut self,
        players: &[PlayerId],
        _state: &AssignmentState,
        existing: &[NodeAggregate],
        baseline_signal: &PriceSignal,
        _current_welfare: f32,
    ) -> ReferenceResult {
        let lookup_start = Instant::now();
        let canonical_state = self.canonical_reference_state(players, baseline_signal);
        let initial_assignment_hash = canonical_state
            .as_ref()
            .map(|state| Self::assignment_fingerprint(players, state))
            .unwrap_or_else(|| {
                let empty = AssignmentState::new(self.empty_window_aggregates(), players.len());
                Self::assignment_fingerprint(players, &empty)
            });
        let key = self.social_reference_key(players, existing, baseline_signal);
        if self.settings.reference_mode == "sa_fallback" {
            if let Some(value) = self.settings.offline_social_reference {
                return ReferenceResult {
                    value: Some(value),
                    key: Some(key),
                    source: "offline_scalar_debug",
                    cache_hit: false,
                    compute_us: 0,
                    lookup_us: lookup_start.elapsed().as_micros() as u64,
                    persist_us: 0,
                    persist_ok: true,
                    sa_iterations: 0,
                };
            }
        }
        if self.settings.reference_mode != "build" {
            if let Some(value) = self.offline_reference_table.get(&key).copied() {
                return ReferenceResult {
                    value,
                    key: Some(key),
                    source: match value {
                        Some(value) if value > EPSILON => "offline_table",
                        Some(_) => "offline_table_nonpositive",
                        None => "offline_table_unavailable",
                    },
                    cache_hit: true,
                    compute_us: 0,
                    lookup_us: lookup_start.elapsed().as_micros() as u64,
                    persist_us: 0,
                    persist_ok: true,
                    sa_iterations: 0,
                };
            }
        }
        if self.settings.reference_mode == "offline_required" {
            if self.logged_missing_reference_keys.insert(key) {
                log::error!(
                    "NSESche offline_required reference is missing for state key 0x{key:016x}; retaining the inner Nash allocation without price feedback"
                );
            }
            return ReferenceResult {
                value: None,
                key: Some(key),
                source: "offline_table_missing",
                cache_hit: false,
                compute_us: 0,
                lookup_us: lookup_start.elapsed().as_micros() as u64,
                persist_us: 0,
                persist_ok: true,
                sa_iterations: 0,
            };
        }

        if let Some(&cached) = self.social_reference_cache.get(&key) {
            let lookup_us = lookup_start.elapsed().as_micros() as u64;
            let (persist_us, persist_ok) = self.persist_reference_build_record(
                key,
                Some(cached),
                initial_assignment_hash,
                players.len(),
                0,
                0,
            );
            return ReferenceResult {
                value: Some(cached),
                key: Some(key),
                source: if self.settings.reference_mode == "build" {
                    "sa_build_cache"
                } else {
                    "sa_cache"
                },
                cache_hit: true,
                compute_us: 0,
                lookup_us,
                persist_us,
                persist_ok,
                sa_iterations: 0,
            };
        }
        let lookup_us = lookup_start.elapsed().as_micros() as u64;

        let compute_start = Instant::now();
        let search = canonical_state.as_ref().and_then(|state| {
            self.compute_social_reference_sa(players, state, baseline_signal, key)
        });
        let reference = search.map(|result| result.value);
        let sa_iterations = search.map(|result| result.sa_iterations).unwrap_or(0);
        let compute_us = compute_start.elapsed().as_micros() as u64;
        let (persist_us, persist_ok) = self.persist_reference_build_record(
            key,
            reference,
            initial_assignment_hash,
            players.len(),
            sa_iterations,
            compute_us,
        );
        if let Some(value) = reference {
            if !self.social_reference_cache.contains_key(&key)
                && self.social_reference_cache.len() >= SOCIAL_REFERENCE_CACHE_CAPACITY
            {
                if let Some(oldest) = self.social_reference_order.pop_front() {
                    self.social_reference_cache.remove(&oldest);
                }
            }
            if !self.social_reference_cache.contains_key(&key) {
                self.social_reference_order.push_back(key);
            }
            self.social_reference_cache.insert(key, value);
        }
        ReferenceResult {
            value: reference,
            key: Some(key),
            source: if self.settings.reference_mode == "build" {
                match reference {
                    Some(value) if value > EPSILON => "sa_build",
                    Some(value) if value < 0.0 => "sa_build_negative",
                    Some(_) => "sa_build_zero",
                    None => "sa_build_unavailable",
                }
            } else {
                "sa_fallback"
            },
            cache_hit: false,
            compute_us,
            lookup_us,
            persist_us,
            persist_ok,
            sa_iterations,
        }
    }

    fn social_gap(reference: f32, welfare: f32) -> Option<f32> {
        if !reference.is_finite()
            || !welfare.is_finite()
            || reference <= EPSILON
            || welfare > reference + EPSILON
        {
            return None;
        }
        let gap = (reference - welfare) / reference;
        gap.is_finite().then_some(gap.max(0.0))
    }

    fn reference_is_below_current(reference: f32, welfare: f32) -> bool {
        reference.is_finite()
            && welfare.is_finite()
            && reference > EPSILON
            && welfare > reference + EPSILON
    }

    fn apply_price_feedback(&self, signal: &mut PriceSignal, gap: f32) -> f32 {
        // Eqs. (19)-(20).  Eq. (14)'s beta is the network term, not a
        // rolling load average.  Every outer round starts from p_n(t).
        let gamma = self.settings.price_adjustment_factor * signal.global_load.tanh();
        let multiplier = 1.0 + gamma * signal.network_congestion * gap.max(0.0);
        for node_id in 0..signal.adjusted_prices.len() {
            let adjusted = signal.baseline_prices[node_id] * multiplier;
            signal.adjusted_prices[node_id] = if adjusted.is_finite() {
                adjusted.max(EPSILON)
            } else {
                signal.baseline_prices[node_id]
            };
        }
        gamma
    }

    fn solve(
        &mut self,
        players: &[PlayerId],
        existing: Vec<NodeAggregate>,
        mut signal: PriceSignal,
    ) -> (AssignmentState, PriceSignal, SolveStats) {
        let mut stats = SolveStats::default();
        if players.is_empty() {
            stats.termination_reason = "no_players";
            return (AssignmentState::new(existing, 0), signal, stats);
        }
        let baseline_existing = existing.clone();
        let baseline_signal = signal.clone();
        let mut no_feasible = HashSet::new();
        let mut state =
            self.initialize_assignment(players, existing, &signal, &mut stats, &mut no_feasible);
        if state.assignments.len() != players.len() {
            stats.no_feasible_players = no_feasible.len();
            stats.assigned_players = state.assignments.len();
            stats.assignment_hash = Self::assignment_fingerprint(players, &state);
            stats.pre_feedback_welfare = self.social_welfare(players, &state, &baseline_signal);
            stats.final_assignment_baseline_welfare = stats.pre_feedback_welfare;
            stats.welfare = stats.pre_feedback_welfare;
            stats.termination_reason = "infeasible_players";
            return (state, signal, stats);
        }
        stats.pre_feedback_welfare = self.social_welfare(players, &state, &baseline_signal);

        let mut previous_outer_assignment: Option<HashMap<PlayerId, NodeId>> = None;
        let mut window_reference: Option<ReferenceResult> = None;
        for outer_round in 0..self.settings.max_outer_rounds {
            stats.outer_rounds = outer_round + 1;
            let inner =
                self.run_inner_loop(players, &mut state, &signal, &mut stats, &mut no_feasible);
            stats.inner_stable = inner.stable;
            if inner.infeasible {
                stats.termination_reason = "infeasible_players";
                break;
            }
            if inner.oscillated {
                stats.termination_reason = "oscillation_guard";
                break;
            }
            if !inner.stable {
                stats.termination_reason = "inner_iteration_limit";
                break;
            }

            stats.welfare = self.social_welfare(players, &state, &signal);
            if outer_round == 0 {
                stats.pre_feedback_welfare = stats.welfare;
            }
            if !self.settings.social_coordination_enabled {
                stats.termination_reason = "nash_stable_coordination_disabled";
                break;
            }

            if window_reference.is_none() {
                stats.reference_initial_assignment_hash = self
                    .canonical_reference_state(players, &baseline_signal)
                    .map(|reference_state| Self::assignment_fingerprint(players, &reference_state));
                window_reference = Some(self.get_social_reference(
                    players,
                    &state,
                    &baseline_existing,
                    &baseline_signal,
                    stats.welfare.total,
                ));
            }
            let reference = window_reference.unwrap_or_default();
            stats.reference_source = reference.source;
            stats.reference_key = reference.key;
            stats.reference_cache_hit = reference.cache_hit;
            stats.reference_compute_us += reference.compute_us;
            stats.reference_lookup_us += reference.lookup_us;
            stats.reference_persist_us += reference.persist_us;
            stats.reference_persist_ok &= reference.persist_ok;
            stats.reference_sa_iterations += reference.sa_iterations as u64;
            stats.social_reference = reference.value;
            let Some(reference_value) = reference.value else {
                stats.termination_reason = if reference.source == "offline_table_missing" {
                    "social_reference_missing"
                } else {
                    "social_reference_unavailable"
                };
                break;
            };
            let Some(gap) = Self::social_gap(reference_value, stats.welfare.total) else {
                stats.reference_below_current =
                    Self::reference_is_below_current(reference_value, stats.welfare.total);
                stats.termination_reason = if stats.reference_below_current {
                    "social_reference_below_current_welfare"
                } else {
                    "social_reference_invalid"
                };
                break;
            };
            stats.reference_feedback_eligible = true;
            stats.social_gap = Some(gap);

            // The paper's outer-loop stopping rule compares two successive
            // Nash allocations.  Calculate the welfare gap first so the
            // observation belongs to the final allocation, not the preceding
            // price vector.
            if let Some(previous) = previous_outer_assignment.as_ref() {
                if previous == &state.assignments {
                    stats.outer_stable = true;
                    stats.termination_reason = "outer_assignment_unchanged";
                    break;
                }
            }
            if gap <= self.settings.social_gap_epsilon {
                stats.outer_stable = true;
                stats.termination_reason = "social_gap_zero";
                break;
            }
            if !self.settings.congestion_pricing_enabled {
                stats.termination_reason = "nash_stable_pricing_disabled";
                break;
            }
            if outer_round + 1 >= self.settings.max_outer_rounds {
                stats.hit_outer_limit = true;
                stats.termination_reason = "outer_iteration_limit";
                break;
            }

            previous_outer_assignment = Some(state.assignments.clone());
            stats.gamma = self.apply_price_feedback(&mut signal, gap);
            stats.price_adjustments += 1;
        }

        stats.no_feasible_players = no_feasible.len();
        stats.assigned_players = state.assignments.len();
        stats.assignment_hash = Self::assignment_fingerprint(players, &state);
        stats.final_assignment_baseline_welfare =
            self.social_welfare(players, &state, &baseline_signal);
        stats.welfare = self.social_welfare(players, &state, &signal);
        // The common empirical gap compares every policy's final proposed
        // assignment under one immutable pre-feedback price vector.  The
        // loop-local gap above still controls Eq. (19); this reassignment is
        // observation-only and cannot change the selected placement.
        stats.social_gap = stats.social_reference.and_then(|reference| {
            Self::social_gap(reference, stats.final_assignment_baseline_welfare.total)
        });
        if let Some(reference) = stats.social_reference {
            stats.reference_below_current |= Self::reference_is_below_current(
                reference,
                stats.final_assignment_baseline_welfare.total,
            );
        }
        if stats.termination_reason == "not_started" {
            stats.termination_reason = "outer_iteration_limit";
            stats.hit_outer_limit = true;
        }
        (state, signal, stats)
    }

    fn dispatch(
        &mut self,
        players: &[PlayerId],
        state: &AssignmentState,
        node_count: usize,
        emit_scale_up: bool,
        cmd_distributor: &MechCmdDistributor,
    ) -> DispatchStats {
        let mut result = DispatchStats::default();
        let mut keys = Vec::with_capacity(players.len());
        let mut commands = Vec::with_capacity(players.len());
        let mut scale_up_targets = HashSet::new();
        for &player in players {
            let Some(&node_id) = state.assignments.get(&player) else {
                result.invalid_assignments += 1;
                continue;
            };
            if node_id >= node_count {
                result.invalid_assignments += 1;
                continue;
            }
            if !self
                .feasible_nodes
                .get(&player)
                .is_some_and(|candidates| candidates.contains(&node_id))
            {
                result.invalid_assignments += 1;
                continue;
            }
            keys.push(player);
            commands.push(ScheCmd {
                nid: node_id,
                reqid: player.req_id,
                fnid: player.fn_id,
                memlimit: None,
            });
            if emit_scale_up && !self.existing_containers.contains(&(player.fn_id, node_id)) {
                scale_up_targets.insert((player.fn_id, node_id));
            }
        }
        result.commands_prepared = commands.len();
        if commands.is_empty() {
            return result;
        }

        let mut scale_up_targets: Vec<(FnId, NodeId)> = scale_up_targets.into_iter().collect();
        scale_up_targets.sort_unstable();
        let scale_up_commands = scale_up_targets
            .iter()
            .map(|&(fn_id, node_id)| UpCmd {
                nid: node_id,
                fnid: fn_id,
            })
            .collect::<Vec<_>>();
        result.scale_ups_prepared = scale_up_commands.len();

        match cmd_distributor.send(MechScheduleOnceRes::Cmds {
            sche_cmds: commands,
            scale_up_cmds: scale_up_commands,
            scale_down_cmds: Vec::new(),
        }) {
            Ok(()) => {
                result.commands_sent = keys.len();
                result.scale_ups_sent = result.scale_ups_prepared;
            }
            Err(error) => {
                result.channel_failed = true;
                log::warn!("NSESche failed to send schedule command batch: {:?}", error);
            }
        }
        result
    }

    fn histogram_percentile(histogram: &[u64], samples: u64, percentile: f64) -> usize {
        if samples == 0 {
            return 0;
        }
        let target = (samples as f64 * percentile).ceil().max(1.0) as u64;
        let mut cumulative = 0u64;
        for (latency_ms, &count) in histogram.iter().enumerate() {
            cumulative += count;
            if cumulative >= target {
                return latency_ms;
            }
        }
        histogram.len().saturating_sub(1)
    }

    fn observe_traffic(&mut self, env: &SimEnvObserve) -> WindowTrafficMetrics {
        let frame = env.core().current_frame();
        let active_count = env.core().requests().len();
        let done_requests = env.core().done_requests();
        let done_count = done_requests.len();
        let total_seen = active_count + done_count;

        if frame < self.traffic_observer.last_frame
            || done_count < self.traffic_observer.last_done_count
            || total_seen < self.traffic_observer.last_total_seen
        {
            self.traffic_observer = TrafficObserver::default();
        }
        for request in done_requests
            .iter()
            .skip(self.traffic_observer.last_done_count)
        {
            let latency_ms = request.end_frame.saturating_sub(request.begin_frame);
            if latency_ms >= self.traffic_observer.latency_histogram.len() {
                self.traffic_observer
                    .latency_histogram
                    .resize(latency_ms + 1, 0);
            }
            self.traffic_observer.latency_histogram[latency_ms] += 1;
            self.traffic_observer.latency_samples += 1;
        }

        let delta_frames = frame
            .saturating_sub(self.traffic_observer.last_frame)
            .max(1);
        let arrivals = total_seen.saturating_sub(self.traffic_observer.last_total_seen);
        let completions = done_count.saturating_sub(self.traffic_observer.last_done_count);
        let seconds = delta_frames as f64 / 1000.0;
        self.traffic_observer.last_frame = frame;
        self.traffic_observer.last_total_seen = total_seen;
        self.traffic_observer.last_done_count = done_count;

        WindowTrafficMetrics {
            delta_frames,
            arrivals,
            completions,
            cumulative_arrivals: total_seen,
            cumulative_completions: done_count,
            arrival_rps: arrivals as f64 / seconds,
            throughput_rps: completions as f64 / seconds,
            cumulative_latency_p50_ms: Self::histogram_percentile(
                &self.traffic_observer.latency_histogram,
                self.traffic_observer.latency_samples,
                0.50,
            ),
            cumulative_latency_p95_ms: Self::histogram_percentile(
                &self.traffic_observer.latency_histogram,
                self.traffic_observer.latency_samples,
                0.95,
            ),
            cumulative_latency_p99_ms: Self::histogram_percentile(
                &self.traffic_observer.latency_histogram,
                self.traffic_observer.latency_samples,
                0.99,
            ),
            latency_samples: self.traffic_observer.latency_samples,
        }
    }

    fn log_run_config_once(&mut self, env: &SimEnvObserve) {
        if self.run_config_logged || !self.settings.observation_enabled {
            return;
        }
        if let Err(error) = self.ensure_observation_writer(env) {
            panic!("NSESche observation setup failed: {error}");
        }
        self.run_config_logged = true;
        let config = env.help().config();
        let formula_constants = serde_json::json!({
            "social_gap_numerical_epsilon": self.settings.social_gap_epsilon,
            "dag_complexity_normalizer_c_norm": DAG_COMPLEXITY_NORMALIZER,
            "differentiation_p1": DIFFERENTIATION_P1,
            "differentiation_p2": DIFFERENTIATION_P2,
            "differentiation_h_max": DIFFERENTIATION_MODULUS,
        });
        let mechanism = serde_json::json!({
            "type": config.mech.mech_type().0,
            "autoscaler": config.mech.scale_num_conf().0,
            "scale_down_executor": config.mech.scale_down_exec_conf().0,
            "scale_up_executor": config.mech.scale_up_exec_conf().0,
            "scheduler": config.mech.sche_conf().0,
            "instance_cache_policy": config.mech.instance_cache_policy_conf().0,
        });
        let reference = serde_json::json!({
            "mode": self.settings.reference_mode,
            "state_key_schema_version": REFERENCE_KEY_SCHEMA_VERSION,
            "sa_min_iterations": self.settings.sa_iterations,
            "sa_iterations_per_player": self.settings.sa_iterations_per_player,
            "sa_cooling_rate": self.settings.sa_cooling_rate,
            "offline_scalar_debug_configured": self.settings.offline_social_reference.is_some(),
            "offline_file_configured": self.settings.offline_reference_file.is_some(),
            "offline_entries": self.offline_reference_table.len(),
            "offline_load_ok": self.settings.offline_reference_file.is_none()
                || self.offline_reference_load_error.is_none(),
            "offline_load_attempts": self.offline_reference_load_attempts,
            "offline_load_wall_us_total": self.offline_reference_load_wall_us_total,
            "offline_load_thread_cpu_us_total": self.offline_reference_load_thread_cpu_us_total,
            "build_output_file": self.settings.reference_build_output_file,
            "build_writer_ok": self.reference_build_writer_error.is_none(),
        });
        let event = serde_json::json!({
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "formula_alignment": "paper_Eqs_1_20",
            "player_model": "request_function_pair",
            "seed": config.rand_seed,
            "load": config.request_freq,
            "dag_type": config.dag_type,
            "cold_start": config.cold_start,
            "function_type": config.fn_type,
            "total_frames": config.total_frame,
            "nodes": env.node_cnt(),
            "mechanism": mechanism,
            "inner_limit": self.settings.max_inner_rounds,
            "outer_limit": self.settings.max_outer_rounds,
            "inner_convergence_rule": "S_unchanged",
            "outer_convergence_rule": "successive_Nash_assignment_unchanged",
            "r0": self.settings.price_adjustment_factor,
            "quality_weight": self.settings.quality_weight,
            "base_node_price_internal_units": self.settings.base_node_price,
            "base_utility": self.settings.base_utility,
            "contribution_coefficient": self.settings.contribution_coefficient,
            "queue_normalizer": self.settings.queue_normalizer,
            "queue_pressure_source": "node_pending_plus_runnable_resident",
            "queue_breakdown_schema": "exclusive_pending_runnable_parent_blocked_data_blocked_starting_resident_v1",
            "formula_constants": formula_constants,
            "reference": reference,
            "ablation": self.settings.ablation_type,
            "heterogeneity_enabled": self.settings.heterogeneity_enabled,
            "system_utility_enabled": self.settings.system_utility_enabled,
            "externality_enabled": self.settings.externality_enabled,
            "contribution_enabled": self.settings.contribution_enabled,
            "pricing_enabled": self.settings.congestion_pricing_enabled,
            "coordination_enabled": self.settings.social_coordination_enabled,
            "time_unit": "frame=1ms",
            "rate_unit": "requests/s",
            "network_beta_source": "active_transfer_remaining_time_by_directed_link_proxy",
            "network_proxy_is_physical_rtt": false,
            "observation_detail": self.settings.observation_detail,
        });
        self.emit_observation(event);
    }

    fn log_new_function_profiles(&mut self, players: &[PlayerId]) {
        if !self.settings.observation_enabled {
            return;
        }
        let mut multiplicities = HashMap::<FnId, usize>::new();
        for player in players {
            *multiplicities.entry(player.fn_id).or_insert(0) += 1;
        }
        let mut function_ids: Vec<FnId> = multiplicities.keys().copied().collect();
        function_ids.sort_unstable();
        for fn_id in function_ids {
            if self.logged_function_profiles.contains(&fn_id) {
                continue;
            }
            let Some(profile) = self.function_profiles.get(&fn_id).copied() else {
                continue;
            };
            let heterogeneity = profile.heterogeneity;
            let event = serde_json::json!({
                "v": 2,
                "kind": "function_profile",
                "scheduler": "sche_nash",
                "fn_id": profile.fn_id,
                "pending_instances_first_seen": multiplicities[&fn_id],
                "quality_weight_w_i_q": profile.quality_weight,
                "raw": {
                    "cpu": profile.raw_cpu,
                    "memory_mb": profile.raw_memory,
                    "output_mb": profile.output_mb,
                    "cold_start_frames": profile.cold_start_frames,
                    "dag_nodes": profile.dag_node_count,
                    "container_memory_required": profile.required_container_memory,
                },
                "normalized": {
                    "cpu": heterogeneity.normalized_cpu,
                    "memory": heterogeneity.normalized_memory,
                },
                "heterogeneity": {
                    "h_ri": heterogeneity.resource_intensity,
                    "h_fc": heterogeneity.function_complexity,
                    "h_nd": heterogeneity.network_dependency,
                    "h_pi": heterogeneity.differentiation,
                    "impact": heterogeneity.impact(),
                },
            });
            self.emit_observation(event);
            self.logged_function_profiles.insert(fn_id);
        }
    }

    fn vector_stats(values: &[f32]) -> (f32, f32, f32) {
        if values.is_empty() {
            return (0.0, 0.0, 0.0);
        }
        let min = values.iter().copied().fold(f32::INFINITY, f32::min);
        let max = values.iter().copied().fold(f32::NEG_INFINITY, f32::max);
        let mean = values.iter().sum::<f32>() / values.len() as f32;
        (min, mean, max)
    }

    fn log_window(
        &mut self,
        env: &SimEnvObserve,
        traffic: &WindowTrafficMetrics,
        players: &[PlayerId],
        pending_player_count: usize,
        waiting_for_candidate_nodes: usize,
        signal: &PriceSignal,
        state: &AssignmentState,
        stats: &SolveStats,
        dispatch: &DispatchStats,
        timings: &WindowTimings,
    ) {
        if !self.settings.observation_enabled {
            return;
        }
        self.observation_window += 1;
        let node_count = self.node_snapshots.len().max(1);
        let count_stats = |project: fn(&NodeSnapshot) -> usize| {
            let values = self.node_snapshots.iter().map(project);
            (values.clone().sum::<usize>(), values.max().unwrap_or(0))
        };
        let (queue_pending_total, queue_pending_max) = count_stats(|node| node.pending_tasks);
        let (queue_runnable_total, queue_runnable_max) = count_stats(|node| node.runnable_tasks);
        let (queue_parent_blocked_total, queue_parent_blocked_max) =
            count_stats(|node| node.parent_blocked_tasks);
        let (queue_data_blocked_total, queue_data_blocked_max) =
            count_stats(|node| node.data_blocked_tasks);
        let (queue_starting_resident_total, queue_starting_resident_max) =
            count_stats(|node| node.starting_resident_tasks);
        let (queue_resident_total, queue_resident_max) = count_stats(|node| node.resident_tasks);
        let (queue_pressure_count_total, queue_pressure_count_max) =
            count_stats(|node| node.pending_tasks.saturating_add(node.runnable_tasks));
        debug_assert_eq!(
            queue_resident_total,
            queue_runnable_total
                + queue_parent_blocked_total
                + queue_data_blocked_total
                + queue_starting_resident_total
        );
        let container_total: usize = self
            .node_snapshots
            .iter()
            .map(|node| node.container_count)
            .sum();
        let running_containers: usize = self
            .node_snapshots
            .iter()
            .map(|node| node.running_containers)
            .sum();
        let cpu_values: Vec<f32> = self
            .node_snapshots
            .iter()
            .map(|node| node.cpu_utilization)
            .collect();
        let memory_values: Vec<f32> = self
            .node_snapshots
            .iter()
            .map(|node| node.memory_utilization)
            .collect();
        let pressure_values: Vec<f32> = self
            .node_snapshots
            .iter()
            .map(|node| node.pressure)
            .collect();
        let (cpu_min, cpu_mean, cpu_max) = Self::vector_stats(&cpu_values);
        let (memory_min, memory_mean, memory_max) = Self::vector_stats(&memory_values);
        let (pressure_min, pressure_mean, pressure_max) = Self::vector_stats(&pressure_values);
        let (price_min, price_mean, price_max) = Self::vector_stats(&signal.adjusted_prices);
        let (premium_min, premium_mean, premium_max) =
            Self::vector_stats(&signal.node_congestion_premiums);
        let unique_functions = players
            .iter()
            .map(|player| player.fn_id)
            .collect::<HashSet<_>>()
            .len();
        let placement = self.placement_diagnostics(players, state, signal);
        let simulator_cost_units = *env.help().cost();
        let cost_per_completed = if traffic.cumulative_completions == 0 {
            None
        } else {
            Some(simulator_cost_units / traffic.cumulative_completions as f32)
        };

        let event = serde_json::json!({
            "v": 2,
            "kind": "window",
            "scheduler": "sche_nash",
            "window": self.observation_window,
            "frame": env.core().current_frame(),
            "load": load_name(env),
            "traffic": {
                "delta_frames": traffic.delta_frames,
                "arrivals": traffic.arrivals,
                "arrival_rps": traffic.arrival_rps,
                "completions": traffic.completions,
                "throughput_rps": traffic.throughput_rps,
                "cumulative_arrivals": traffic.cumulative_arrivals,
                "cumulative_completions": traffic.cumulative_completions,
                "latency_samples": traffic.latency_samples,
                "latency_cumulative_p50_ms": traffic.cumulative_latency_p50_ms,
                "latency_cumulative_p95_ms": traffic.cumulative_latency_p95_ms,
                "latency_cumulative_p99_ms": traffic.cumulative_latency_p99_ms,
                "per_node_arrival_rps": traffic.arrival_rps / node_count as f64,
            },
            "cluster": {
                "nodes": self.node_snapshots.len(),
                "cpu_min": cpu_min,
                "cpu_mean": cpu_mean,
                "cpu_max": cpu_max,
                "memory_min": memory_min,
                "memory_mean": memory_mean,
                "memory_max": memory_max,
                "pressure_min": pressure_min,
                "pressure_mean": pressure_mean,
                "pressure_max": pressure_max,
                "queue_pending_total": queue_pending_total,
                "queue_pending_max": queue_pending_max,
                "queue_runnable_total": queue_runnable_total,
                "queue_runnable_max": queue_runnable_max,
                "queue_parent_blocked_total": queue_parent_blocked_total,
                "queue_parent_blocked_max": queue_parent_blocked_max,
                "queue_data_blocked_total": queue_data_blocked_total,
                "queue_data_blocked_max": queue_data_blocked_max,
                "queue_starting_resident_total": queue_starting_resident_total,
                "queue_starting_resident_max": queue_starting_resident_max,
                "queue_resident_total": queue_resident_total,
                "queue_resident_max": queue_resident_max,
                "queue_pressure_count_total": queue_pressure_count_total,
                "queue_pressure_count_max": queue_pressure_count_max,
                "queue_running_total": queue_resident_total,
                "queue_running_max": queue_resident_max,
                "queue_total": queue_pending_total + queue_resident_total,
                "containers_total": container_total,
                "containers_running": running_containers,
                "containers_starting": container_total.saturating_sub(running_containers),
            },
            "decision": {
                "pending_request_function_pairs": pending_player_count,
                "waiting_for_candidate_nodes": waiting_for_candidate_nodes,
                "request_function_players": players.len(),
                "unique_functions": unique_functions,
                "assigned_players": stats.assigned_players,
                "complete_assignment": stats.assigned_players == players.len(),
                "candidate_evaluations": stats.candidate_evaluations,
                "initialization_evaluations": stats.initialization_evaluations,
                "no_feasible_players": stats.no_feasible_players,
                "assignment_hash": stats.assignment_hash,
                "initial_assignment_hash": stats.reference_initial_assignment_hash,
                "commands_prepared": dispatch.commands_prepared,
                "commands_sent": dispatch.commands_sent,
                "scale_ups_prepared": dispatch.scale_ups_prepared,
                "scale_ups_sent": dispatch.scale_ups_sent,
                "invalid_assignments": dispatch.invalid_assignments,
                "dispatch_channel_failed": dispatch.channel_failed,
                "placement_dispersion_normalized": placement.normalized_dispersion,
                "assigned_node_count": placement.assigned_nodes,
                "co_location_conflict_pairs_proxy": placement.co_location_pairs,
                "co_location_conflict_pair_ratio_proxy": placement.co_location_pair_ratio,
                "ranking_diagnostic_players": placement.evaluated_players,
                "near_tie_players": placement.near_tie_players,
                "differentiation_changed_top_choice_players": placement.differentiation_changed_choice_players,
                "active_differentiation_mean": placement.active_differentiation_mean,
                "near_tie_player_ratio": if placement.evaluated_players == 0 { 0.0 } else { placement.near_tie_players as f32 / placement.evaluated_players as f32 },
                "differentiation_changed_top_choice_ratio": if placement.evaluated_players == 0 { 0.0 } else { placement.differentiation_changed_choice_players as f32 / placement.evaluated_players as f32 },
                "differentiation_diagnostic_definition": "counterfactual_candidate_ranking_removes_only_h_pi_contribution_term_over_common_candidates",
            },
            "solver": {
                "inner_rounds": stats.inner_rounds,
                "outer_rounds": stats.outer_rounds,
                "inner_rounds_per_outer": stats.inner_rounds_per_outer,
                "assignment_moves": stats.assignment_moves,
                "assignment_moves_per_round": stats.assignment_moves_per_round,
                "inner_stable": stats.inner_stable,
                "outer_stable": stats.outer_stable,
                "inner_limit_hit": stats.hit_inner_limit,
                "outer_limit_hit": stats.hit_outer_limit,
                "oscillations": stats.oscillation_count,
                "termination": stats.termination_reason,
            },
            "social": {
                // `welfare` remains as a backward-compatible alias for the
                // final-price value.  The baseline re-evaluation is the
                // cross-policy comparable quantity used for E6.
                "welfare": stats.welfare.total,
                "pre_feedback_welfare": stats.pre_feedback_welfare.total,
                "final_assignment_baseline_welfare": stats.final_assignment_baseline_welfare.total,
                "final_welfare": stats.welfare.total,
                "reference": stats.social_reference,
                "reference_state_key": stats.reference_key,
                "gap": stats.social_gap,
                "empirical_gap": stats.social_gap,
                "feedback_eligible": stats.reference_feedback_eligible,
                "reference_below_current": stats.reference_below_current,
                "gap_welfare_basis": "final_assignment_evaluated_at_immutable_baseline_prices",
                "reference_source": stats.reference_source,
                "reference_cache_hit": stats.reference_cache_hit,
                "reference_compute_us": stats.reference_compute_us,
                "reference_lookup_us": stats.reference_lookup_us,
                "reference_persist_us": stats.reference_persist_us,
                "reference_persist_ok": stats.reference_persist_ok,
                "reference_sa_iterations": stats.reference_sa_iterations,
                "utility_components": {
                    "baseline_reward": stats.welfare.baseline_reward,
                    "cost": stats.welfare.cost,
                    "quality": stats.welfare.quality,
                    "externality": stats.welfare.externality,
                    "contribution": stats.welfare.contribution,
                },
                "baseline_utility_components": {
                    "baseline_reward": stats.final_assignment_baseline_welfare.baseline_reward,
                    "cost": stats.final_assignment_baseline_welfare.cost,
                    "quality": stats.final_assignment_baseline_welfare.quality,
                    "externality": stats.final_assignment_baseline_welfare.externality,
                    "contribution": stats.final_assignment_baseline_welfare.contribution,
                },
            },
            "pricing": {
                "global_load_g": signal.global_load,
                "network_beta": signal.network_congestion,
                "gamma": stats.gamma,
                "adjustments": stats.price_adjustments,
                "price_min": price_min,
                "price_mean": price_mean,
                "price_max": price_max,
                "node_premium_min": premium_min,
                "node_premium_mean": premium_mean,
                "node_premium_max": premium_max,
            },
            "network": {
                "cross_node_placement_ratio": self.cross_node_placement_ratio,
                "configured_1MB_latency_proxy_mean_ms": self.network_latency_mean_ms,
                "configured_1MB_latency_proxy_max_ms": self.network_latency_max_ms,
                "active_transfer_count": self.active_network_transfers,
                "active_transfer_remaining_mb": self.active_network_remaining_mb,
                "active_link_delay_proxy_mean_ms": self.dynamic_link_delay_mean_ms,
                "active_link_delay_proxy_max_ms": self.dynamic_link_delay_max_ms,
                "latency_normalization_bound_ms": self.network_latency_normalizer_used_ms,
                "links_at_normalization_bound": self.saturated_dynamic_links,
                "physical_rtt_measured": false,
            },
            "cost": {
                "unit": "simulator_internal_units",
                "cumulative": simulator_cost_units,
                "per_completed_request": cost_per_completed,
                "is_currency": false,
            },
            "overhead": {
                "reference_table_refresh_us": timings.reference_table_refresh_us,
                "profile_us": timings.profile_us,
                "collect_players_us": timings.collect_players_us,
                "snapshot_us": timings.snapshot_us,
                "pricing_us": timings.pricing_us,
                "initialization_us": stats.initialization_us,
                "solve_us": timings.solve_us,
                "dispatch_us": timings.dispatch_us,
                "scheduler_wall_us": timings.scheduler_wall_us,
                "scheduler_thread_cpu_us": timings.scheduler_thread_cpu_us,
            },
        });
        self.emit_observation(event);
    }
}

impl Scheduler for ScheNashScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        let traffic = self.observe_traffic(env);
        if env.core().fns().is_empty() || env.core().dags().is_empty() {
            return;
        }

        let scheduler_start = Instant::now();
        let thread_cpu_start = ThreadTime::try_now().ok();
        let mut timings = WindowTimings::default();

        self.settings = NashSettings::from_env(env);
        let phase_start = Instant::now();
        self.refresh_offline_reference_table();
        self.ensure_reference_build_writer();
        timings.reference_table_refresh_us = phase_start.elapsed().as_micros() as u64;

        let phase_start = Instant::now();
        self.ensure_function_profiles(env);
        timings.profile_us = phase_start.elapsed().as_micros() as u64;

        let phase_start = Instant::now();
        let pending_players = self.collect_players(env);
        timings.collect_players_us = phase_start.elapsed().as_micros() as u64;
        let mut active_functions: Vec<FnId> =
            pending_players.iter().map(|player| player.fn_id).collect();
        active_functions.sort_unstable();
        active_functions.dedup();
        let emit_scale_up = match mech.mech_type() {
            MechType::ScaleScheSeparated => false,
            MechType::ScaleScheJoint => true,
            MechType::NoScale => false,
        };
        self.new_container_limits.clear();
        if emit_scale_up {
            for &fn_id in &active_functions {
                let target = mech.scale_num(fn_id);
                let current = env.fn_container_cnt(fn_id);
                self.new_container_limits
                    .insert(fn_id, target.saturating_sub(current));
            }
        }

        let phase_start = Instant::now();
        self.update_node_snapshots(env);
        self.update_feasible_nodes(env, &pending_players);
        let players = pending_players
            .iter()
            .copied()
            .filter(|player| {
                self.feasible_nodes
                    .get(player)
                    .is_some_and(|nodes| !nodes.is_empty())
            })
            .collect::<Vec<_>>();
        let waiting_for_candidate_nodes = pending_players.len().saturating_sub(players.len());
        let existing = self.build_existing_aggregates(env);
        timings.snapshot_us = phase_start.elapsed().as_micros() as u64;

        let phase_start = Instant::now();
        let signal = self.build_price_signal(&existing);
        timings.pricing_us = phase_start.elapsed().as_micros() as u64;

        let phase_start = Instant::now();
        let window_aggregates = self.empty_window_aggregates();
        let (state, final_signal, stats) = self.solve(&players, window_aggregates, signal);
        timings.solve_us = phase_start.elapsed().as_micros() as u64;

        let phase_start = Instant::now();
        let dispatch = self.dispatch(
            &players,
            &state,
            env.node_cnt(),
            emit_scale_up,
            cmd_distributor,
        );
        timings.dispatch_us = phase_start.elapsed().as_micros() as u64;
        timings.scheduler_wall_us = scheduler_start.elapsed().as_micros() as u64;
        timings.scheduler_thread_cpu_us = thread_cpu_start
            .as_ref()
            .and_then(|start| start.try_elapsed().ok())
            .map(|duration| duration.as_micros() as u64)
            .unwrap_or(0);

        self.run_aggregate.record(players.len(), &stats, &timings);
        self.log_run_config_once(env);
        self.log_new_function_profiles(&pending_players);
        self.log_window(
            env,
            &traffic,
            &players,
            pending_players.len(),
            waiting_for_candidate_nodes,
            &final_signal,
            &state,
            &stats,
            &dispatch,
            &timings,
        );
    }
}

fn percentile_u64(values: &[u64], percentile: f64) -> u64 {
    if values.is_empty() {
        return 0;
    }
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    let index = ((sorted.len() as f64 * percentile).ceil() as usize)
        .saturating_sub(1)
        .min(sorted.len() - 1);
    sorted[index]
}

fn percentile_u32(values: &[u32], percentile: f64) -> u32 {
    if values.is_empty() {
        return 0;
    }
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    let index = ((sorted.len() as f64 * percentile).ceil() as usize)
        .saturating_sub(1)
        .min(sorted.len() - 1);
    sorted[index]
}

impl Drop for ScheNashScheduler {
    fn drop(&mut self) {
        let mut build_records_written = 0u64;
        let mut build_write_errors = 0u64;
        let mut build_output_path = None;
        let mut build_published = false;
        if let Some(writer) = self.reference_build_writer.as_mut() {
            build_records_written = writer.records_written;
            build_write_errors = writer.write_errors;
            build_output_path = Some(writer.final_path.to_string_lossy().into_owned());
            let result = if std::thread::panicking() {
                // A failed run must retain the .partial suffix so the result
                // cannot be mistaken for a complete build artifact.
                writer.flush_partial()
            } else {
                writer.finalize()
            };
            match result {
                Ok(()) => build_published = !std::thread::panicking(),
                Err(error) => {
                    log::error!("NSESche {error}");
                    self.reference_build_writer_error = Some(error);
                }
            }
        }
        if !self.settings.observation_enabled || self.run_aggregate.windows == 0 {
            return;
        }
        let solver_windows = self.run_aggregate.solver_windows.max(1) as f64;
        let frame_seconds = self.traffic_observer.last_frame.max(1) as f64 / 1000.0;
        let inner_mean = if self.run_aggregate.inner_rounds.is_empty() {
            0.0
        } else {
            self.run_aggregate
                .inner_rounds
                .iter()
                .map(|value| *value as f64)
                .sum::<f64>()
                / self.run_aggregate.inner_rounds.len() as f64
        };
        let outer_mean = if self.run_aggregate.outer_rounds.is_empty() {
            0.0
        } else {
            self.run_aggregate
                .outer_rounds
                .iter()
                .map(|value| *value as f64)
                .sum::<f64>()
                / self.run_aggregate.outer_rounds.len() as f64
        };
        let reference_windows = self.run_aggregate.reference_windows.max(1) as f64;
        let feedback_eligible_windows = self.run_aggregate.reference_feedback_eligible_windows;
        let event = serde_json::json!({
            "v": 2,
            "kind": "run_summary",
            "scheduler": "sche_nash",
            "windows": self.run_aggregate.windows,
            "solver_windows": self.run_aggregate.solver_windows,
            "arrival_rps": self.traffic_observer.last_total_seen as f64 / frame_seconds,
            "throughput_rps": self.traffic_observer.last_done_count as f64 / frame_seconds,
            "latency_samples": self.traffic_observer.latency_samples,
            "latency_p50_ms": Self::histogram_percentile(
                &self.traffic_observer.latency_histogram,
                self.traffic_observer.latency_samples,
                0.50,
            ),
            "latency_p95_ms": Self::histogram_percentile(
                &self.traffic_observer.latency_histogram,
                self.traffic_observer.latency_samples,
                0.95,
            ),
            "latency_p99_ms": Self::histogram_percentile(
                &self.traffic_observer.latency_histogram,
                self.traffic_observer.latency_samples,
                0.99,
            ),
            "inner_rounds": {
                "mean": inner_mean,
                "median": percentile_u32(&self.run_aggregate.inner_rounds, 0.50),
                "p95": percentile_u32(&self.run_aggregate.inner_rounds, 0.95),
                "max": self.run_aggregate.inner_rounds.iter().copied().max().unwrap_or(0),
            },
            "outer_rounds": {
                "mean": outer_mean,
                "median": percentile_u32(&self.run_aggregate.outer_rounds, 0.50),
                "p95": percentile_u32(&self.run_aggregate.outer_rounds, 0.95),
                "max": self.run_aggregate.outer_rounds.iter().copied().max().unwrap_or(0),
            },
            "convergence": {
                "inner_stable_rate": self.run_aggregate.inner_stable_windows as f64 / solver_windows,
                "outer_stable_rate": self.run_aggregate.outer_stable_windows as f64 / solver_windows,
                "inner_limit_windows": self.run_aggregate.inner_limit_windows,
                "outer_limit_windows": self.run_aggregate.outer_limit_windows,
                "oscillation_windows": self.run_aggregate.oscillation_windows,
            },
            "scheduler_wall_us": {
                "median": percentile_u64(&self.run_aggregate.wall_us, 0.50),
                "p95": percentile_u64(&self.run_aggregate.wall_us, 0.95),
                "max": self.run_aggregate.wall_us.iter().copied().max().unwrap_or(0),
            },
            "scheduler_thread_cpu_us": {
                "median": percentile_u64(&self.run_aggregate.thread_cpu_us, 0.50),
                "p95": percentile_u64(&self.run_aggregate.thread_cpu_us, 0.95),
                "max": self.run_aggregate.thread_cpu_us.iter().copied().max().unwrap_or(0),
            },
            "reference_compute_us_total": self.run_aggregate.reference_compute_us,
            "reference_lookup_us_total": self.run_aggregate.reference_lookup_us,
            "reference_persist_us_total": self.run_aggregate.reference_persist_us,
            "reference_load_us_total": self.offline_reference_load_wall_us_total,
            "reference_load_thread_cpu_us_total": self.offline_reference_load_thread_cpu_us_total,
            "reference_load_attempts": self.offline_reference_load_attempts,
            "reference_sa_iterations_total": self.run_aggregate.reference_sa_iterations,
            "reference_validation": {
                "windows": self.run_aggregate.reference_windows,
                "missing": self.run_aggregate.reference_missing_windows,
                "missing_ratio": self.run_aggregate.reference_missing_windows as f64 / reference_windows,
                "zero": self.run_aggregate.reference_zero_windows,
                "zero_ratio": self.run_aggregate.reference_zero_windows as f64 / reference_windows,
                "negative": self.run_aggregate.reference_negative_windows,
                "negative_ratio": self.run_aggregate.reference_negative_windows as f64 / reference_windows,
                "unavailable": self.run_aggregate.reference_unavailable_windows,
                "unavailable_ratio": self.run_aggregate.reference_unavailable_windows as f64 / reference_windows,
                "feedback_eligible": feedback_eligible_windows,
                "feedback_eligible_ratio": feedback_eligible_windows as f64 / reference_windows,
                "below_current": self.run_aggregate.reference_below_current_windows,
                "below_current_ratio": self.run_aggregate.reference_below_current_windows as f64 / reference_windows,
                "persist_failures": self.run_aggregate.reference_persist_failures,
                "offline_required_ok": self.settings.reference_mode != "offline_required"
                    || (self.offline_reference_load_error.is_none()
                        && self.run_aggregate.reference_missing_windows == 0
                        && self.run_aggregate.reference_unavailable_windows == 0),
            },
            "reference_build": {
                "output": build_output_path,
                "published": build_published,
                "records_written": build_records_written,
                "write_errors": build_write_errors,
                "writer_error": self.reference_build_writer_error,
            },
            "observation_writer_error": self.observation_writer_error.as_deref(),
        });
        log::info!("NSE_METRIC_V2 {}", event);
        if let Some(writer) = self.observation_writer.as_mut() {
            if let Err(error) = writer.record(&event) {
                log::error!("NSESche {error}");
                self.observation_writer_error = Some(error);
            }
            let result = if std::thread::panicking() {
                writer.flush_partial()
            } else {
                writer.finalize()
            };
            if let Err(error) = result {
                log::error!("NSESche {error}");
                self.observation_writer_error = Some(error);
            }
        }
    }
}

/// Read-only, policy-independent evaluation of a scheduler's proposed
/// placement under the NSESche social-welfare equations.
///
/// The evaluator is invoked only after the placement policy has returned its
/// `ScheCmd`s.  It cannot add, remove, or rewrite a command, and it uses the
/// same profile, price, externality, contribution, state-key, and offline-SA
/// implementation as `ScheNashScheduler`.  Keeping the evaluator in this
/// module is intentional: there is one formula implementation, not a second
/// approximation that can drift from the paper or from NSESche.
pub struct PosthocWelfareEvaluator {
    evaluator: ScheNashScheduler,
    scheduler_name: String,
    writer: Option<NashObservationWriter>,
    writer_error: Option<String>,
    window: u64,
    evaluated_windows: u64,
    complete_windows: u64,
    reference_windows: u64,
    valid_gap_windows: u64,
    reference_missing_windows: u64,
    reference_zero_windows: u64,
    reference_negative_windows: u64,
    reference_unavailable_windows: u64,
    reference_feedback_eligible_windows: u64,
    reference_below_current_windows: u64,
    reference_persist_failures: u64,
    evaluation_compute_us: u64,
    evaluation_persist_us: u64,
}

impl PosthocWelfareEvaluator {
    pub fn new(scheduler_name: impl Into<String>) -> Self {
        Self {
            evaluator: ScheNashScheduler::new(),
            scheduler_name: scheduler_name.into(),
            writer: None,
            writer_error: None,
            window: 0,
            evaluated_windows: 0,
            complete_windows: 0,
            reference_windows: 0,
            valid_gap_windows: 0,
            reference_missing_windows: 0,
            reference_zero_windows: 0,
            reference_negative_windows: 0,
            reference_unavailable_windows: 0,
            reference_feedback_eligible_windows: 0,
            reference_below_current_windows: 0,
            reference_persist_failures: 0,
            evaluation_compute_us: 0,
            evaluation_persist_us: 0,
        }
    }

    fn ensure_writer(&mut self, env: &SimEnvObserve) -> Result<(), String> {
        if self.writer.is_some() || !env.help().config().experiment.output.enabled {
            return Ok(());
        }
        let config = env.help().config();
        let final_path = Path::new(&config.experiment.output.root)
            .join(&config.experiment.run_id)
            .join("welfare_metrics.jsonl");
        match NashObservationWriter::new(final_path) {
            Ok(writer) => {
                self.writer = Some(writer);
                self.writer_error = None;
                Ok(())
            }
            Err(error) => {
                self.writer_error = Some(error.clone());
                Err(error)
            }
        }
    }

    fn emit(&mut self, event: &serde_json::Value) {
        log::info!("NSE_METRIC_V2 {}", event);
        if let Some(writer) = self.writer.as_mut() {
            if let Err(error) = writer.record(event) {
                self.writer_error = Some(error.clone());
                panic!("post-hoc welfare observation output failed: {error}");
            }
        }
    }

    /// Evaluate exactly the assignment proposed in `commands`.  The return
    /// value is the complete evaluator duration (formula/reference work plus
    /// persistence) for an independently labelled overhead stream; callers
    /// must not fold it into placement-policy timing.
    pub fn evaluate(&mut self, env: &SimEnvObserve, commands: &[ScheCmd]) {
        if env.core().fns().is_empty() || env.core().dags().is_empty() {
            return;
        }
        if let Err(error) = self.ensure_writer(env) {
            panic!("post-hoc welfare observation setup failed: {error}");
        }

        let compute_start = Instant::now();
        self.evaluator.settings = NashSettings::from_env(env);
        // E1-E5/E7 baselines still receive inexpensive common welfare values,
        // but an online SA reference is not silently introduced.  Only a
        // predeclared E6 build/replay dependency (or an explicit debug scalar)
        // is allowed to request reference work for a non-NSESche policy.
        if self.evaluator.settings.reference_mode == "sa_fallback"
            && self.evaluator.settings.offline_social_reference.is_none()
        {
            self.evaluator.settings.reference_mode = "not_required".to_string();
        }
        self.evaluator.settings.observation_enabled = false;
        self.evaluator.refresh_offline_reference_table();
        self.evaluator.ensure_reference_build_writer();
        self.evaluator.ensure_function_profiles(env);

        let pending_players = self.evaluator.collect_players(env);
        self.evaluator.update_node_snapshots(env);
        self.evaluator.update_feasible_nodes(env, &pending_players);
        let players = pending_players
            .iter()
            .copied()
            .filter(|player| {
                self.evaluator
                    .feasible_nodes
                    .get(player)
                    .is_some_and(|nodes| !nodes.is_empty())
            })
            .collect::<Vec<_>>();
        let existing = self.evaluator.build_existing_aggregates(env);
        let baseline_signal = self.evaluator.build_price_signal(&existing);
        let window_aggregates = self.evaluator.empty_window_aggregates();
        let mut state = AssignmentState::new(window_aggregates.clone(), players.len());
        let player_set = players.iter().copied().collect::<HashSet<_>>();
        let mut invalid_commands = 0usize;
        let mut duplicate_commands = 0usize;

        for command in commands {
            let player = PlayerId {
                req_id: command.reqid,
                fn_id: command.fnid,
            };
            if !player_set.contains(&player)
                || !self
                    .evaluator
                    .feasible_nodes
                    .get(&player)
                    .is_some_and(|nodes| nodes.contains(&command.nid))
                || !state.can_add(
                    player,
                    command.nid,
                    &self.evaluator.existing_containers,
                    &self.evaluator.available_container_memory,
                    &self.evaluator.function_profiles,
                    &self.evaluator.new_container_limits,
                )
            {
                invalid_commands += 1;
                continue;
            }
            if state.assignments.contains_key(&player) {
                duplicate_commands += 1;
                continue;
            }
            state.add(
                player,
                command.nid,
                &self.evaluator.existing_containers,
                &self.evaluator.function_profiles,
            );
        }

        let complete_assignment = state.assignments.len() == players.len();
        let assignment_hash = ScheNashScheduler::assignment_fingerprint(&players, &state);
        let reference_initial_assignment_hash = self
            .evaluator
            .canonical_reference_state(&players, &baseline_signal)
            .map(|reference_state| {
                ScheNashScheduler::assignment_fingerprint(&players, &reference_state)
            });
        let welfare = self
            .evaluator
            .social_welfare(&players, &state, &baseline_signal);
        let reference =
            if complete_assignment && self.evaluator.settings.reference_mode != "not_required" {
                self.evaluator.get_social_reference(
                    &players,
                    &state,
                    &window_aggregates,
                    &baseline_signal,
                    welfare.total,
                )
            } else {
                ReferenceResult::default()
            };
        let empirical_gap = reference
            .value
            .and_then(|value| ScheNashScheduler::social_gap(value, welfare.total));
        let reference_below_current = reference.value.is_some_and(|value| {
            ScheNashScheduler::reference_is_below_current(value, welfare.total)
        });
        let compute_us = compute_start.elapsed().as_micros() as u64;

        self.window += 1;
        self.evaluated_windows += 1;
        self.complete_windows += u64::from(complete_assignment);
        self.reference_windows += u64::from(reference.key.is_some());
        self.valid_gap_windows += u64::from(empirical_gap.is_some());
        self.reference_feedback_eligible_windows += u64::from(empirical_gap.is_some());
        self.reference_below_current_windows += u64::from(reference_below_current);
        self.reference_missing_windows += u64::from(reference.source == "offline_table_missing");
        match reference.value {
            Some(value) if value < 0.0 => self.reference_negative_windows += 1,
            Some(value) if value <= EPSILON => self.reference_zero_windows += 1,
            None if reference.key.is_some() && reference.source != "offline_table_missing" => {
                self.reference_unavailable_windows += 1;
            }
            _ => {}
        }
        self.reference_persist_failures += u64::from(!reference.persist_ok);
        self.evaluation_compute_us += compute_us;

        let event = serde_json::json!({
            "v": 1,
            "kind": "welfare_window",
            "schema": "NSE_POSTHOC_WELFARE_WINDOW_V1",
            "scheduler": self.scheduler_name,
            "window": self.window,
            "frame": env.core().current_frame(),
            "formula_alignment": "paper_Eqs_1_20_shared_implementation",
            "evaluation_scope": "proposed_ScheCmd_assignment_read_only",
            "policy_commands_mutated": false,
            "decision": {
                "request_function_players": players.len(),
                "assigned_players": state.assignments.len(),
                "complete_assignment": complete_assignment,
                "commands_observed": commands.len(),
                "invalid_commands": invalid_commands,
                "duplicate_commands": duplicate_commands,
                // The reference search starts from a policy-independent
                // canonical allocation; the final hash remains the evaluated
                // policy's proposed assignment.
                "initial_assignment_hash": reference_initial_assignment_hash,
                "assignment_hash": assignment_hash,
            },
            "social": {
                "pre_feedback_welfare": welfare.total,
                "final_assignment_baseline_welfare": welfare.total,
                "final_welfare": welfare.total,
                "welfare": welfare.total,
                "feedback_applied": false,
                "reference": reference.value,
                "reference_state_key": reference.key,
                "reference_source": reference.source,
                "reference_cache_hit": reference.cache_hit,
                "reference_compute_us": reference.compute_us,
                "reference_lookup_us": reference.lookup_us,
                "reference_persist_us": reference.persist_us,
                "reference_persist_ok": reference.persist_ok,
                "reference_sa_iterations": reference.sa_iterations,
                "gap": empirical_gap,
                "empirical_gap": empirical_gap,
                "feedback_eligible": empirical_gap.is_some(),
                "reference_below_current": reference_below_current,
                "gap_welfare_basis": "final_assignment_evaluated_at_immutable_baseline_prices",
                "utility_components": {
                    "baseline_reward": welfare.baseline_reward,
                    "cost": welfare.cost,
                    "quality": welfare.quality,
                    "externality": welfare.externality,
                    "contribution": welfare.contribution,
                },
            },
            "overhead": {
                "evaluation_compute_us": compute_us,
                "reference_compute_us": reference.compute_us,
                "reference_lookup_us": reference.lookup_us,
                "reference_persist_us": reference.persist_us,
                "excluded_from_policy_timing": true,
            },
        });
        let persist_start = Instant::now();
        self.emit(&event);
        self.evaluation_persist_us += persist_start.elapsed().as_micros() as u64;
    }
}

impl Drop for PosthocWelfareEvaluator {
    fn drop(&mut self) {
        if self.evaluated_windows > 0 && !std::thread::panicking() {
            let reference_denominator = self.reference_windows.max(1) as f64;
            let feedback_eligible_windows = self.reference_feedback_eligible_windows;
            let event = serde_json::json!({
                "v": 1,
                "kind": "welfare_run_summary",
                "schema": "NSE_POSTHOC_WELFARE_RUN_V1",
                "scheduler": self.scheduler_name,
                "windows": self.evaluated_windows,
                "complete_assignment_windows": self.complete_windows,
                "reference_windows": self.reference_windows,
                "valid_empirical_gap_windows": self.valid_gap_windows,
                "reference_missing_windows": self.reference_missing_windows,
                "reference_validation": {
                    "windows": self.reference_windows,
                    "missing": self.reference_missing_windows,
                    "missing_ratio": self.reference_missing_windows as f64 / reference_denominator,
                    "zero": self.reference_zero_windows,
                    "zero_ratio": self.reference_zero_windows as f64 / reference_denominator,
                    "negative": self.reference_negative_windows,
                    "negative_ratio": self.reference_negative_windows as f64 / reference_denominator,
                    "unavailable": self.reference_unavailable_windows,
                    "unavailable_ratio": self.reference_unavailable_windows as f64 / reference_denominator,
                    "feedback_eligible": feedback_eligible_windows,
                    "feedback_eligible_ratio": feedback_eligible_windows as f64 / reference_denominator,
                    "below_current": self.reference_below_current_windows,
                    "below_current_ratio": self.reference_below_current_windows as f64 / reference_denominator,
                    "persist_failures": self.reference_persist_failures,
                    "offline_required_ok": self.evaluator.settings.reference_mode != "offline_required"
                        || (self.evaluator.offline_reference_load_error.is_none()
                            && self.reference_missing_windows == 0
                            && self.reference_unavailable_windows == 0),
                },
                "evaluation_compute_us_total": self.evaluation_compute_us,
                "evaluation_persist_us_total": self.evaluation_persist_us,
                "reference_load_us_total": self.evaluator.offline_reference_load_wall_us_total,
                "reference_load_thread_cpu_us_total": self.evaluator.offline_reference_load_thread_cpu_us_total,
                "reference_load_attempts": self.evaluator.offline_reference_load_attempts,
                "policy_commands_mutated": false,
                "formula_alignment": "paper_Eqs_1_20_shared_implementation",
                "observation_writer_error": self.writer_error.as_deref(),
            });
            self.emit(&event);
        }
        if let Some(writer) = self.writer.as_mut() {
            let result = if std::thread::panicking() {
                writer.flush_partial()
            } else {
                writer.finalize()
            };
            if let Err(error) = result {
                log::error!("post-hoc welfare {error}");
                self.writer_error = Some(error);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn function_assignment_order_is_invariant_to_hashmap_insertion_order() {
        let mut forward = HashMap::new();
        forward.insert(7, 2);
        forward.insert(3, 9);
        forward.insert(11, 1);

        let mut reverse = HashMap::new();
        reverse.insert(11, 1);
        reverse.insert(3, 9);
        reverse.insert(7, 2);

        let expected = vec![(3, 9), (7, 2), (11, 1)];
        assert_eq!(stable_function_assignments(&forward), expected);
        assert_eq!(stable_function_assignments(&reverse), expected);
    }

    fn assert_close(actual: f32, expected: f32) {
        let tolerance = 1.0e-4 * expected.abs().max(1.0);
        assert!(
            (actual - expected).abs() <= tolerance,
            "actual={actual}, expected={expected}, tolerance={tolerance}"
        );
    }

    #[test]
    fn offline_reference_load_is_timed_once_per_file() {
        let path = std::env::temp_dir().join(format!(
            "nse-reference-load-{}-{}.json",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("system time")
                .as_nanos()
        ));
        std::fs::write(&path, r#"{"references":{"1":2.5}}"#).expect("write reference fixture");
        let mut scheduler = ScheNashScheduler::new();
        scheduler.settings.offline_reference_file = Some(path.to_string_lossy().into_owned());

        scheduler.refresh_offline_reference_table();
        assert_eq!(scheduler.offline_reference_load_attempts, 1);
        assert_eq!(scheduler.offline_reference_table.get(&1), Some(&Some(2.5)));
        let first_wall = scheduler.offline_reference_load_wall_us_total;
        let first_cpu = scheduler.offline_reference_load_thread_cpu_us_total;

        scheduler.refresh_offline_reference_table();
        assert_eq!(scheduler.offline_reference_load_attempts, 1);
        assert_eq!(scheduler.offline_reference_load_wall_us_total, first_wall);
        assert_eq!(
            scheduler.offline_reference_load_thread_cpu_us_total,
            first_cpu
        );
        std::fs::remove_file(path).expect("remove reference fixture");
    }

    fn assert_breakdown_close(actual: UtilityBreakdown, expected: UtilityBreakdown) {
        assert_close(actual.baseline_reward, expected.baseline_reward);
        assert_close(actual.cost, expected.cost);
        assert_close(actual.quality, expected.quality);
        assert_close(actual.externality, expected.externality);
        assert_close(actual.contribution, expected.contribution);
        assert_close(actual.total, expected.total);
    }

    fn function_profile(fn_id: FnId, cpu: f32, memory: f32, dag_nodes: usize) -> FunctionProfile {
        FunctionProfile {
            fn_id,
            raw_cpu: cpu,
            raw_memory: memory,
            output_mb: 1.0,
            cold_start_frames: 10,
            dag_node_count: dag_nodes,
            required_container_memory: 0.1,
            quality_weight: 0.5,
            heterogeneity: HeterogeneityProfile::new(cpu, memory, dag_nodes, true),
        }
    }

    fn direct_social_welfare(
        scheduler: &ScheNashScheduler,
        state: &AssignmentState,
        signal: &PriceSignal,
    ) -> UtilityBreakdown {
        let mut total = UtilityBreakdown::default();
        for (&player, &node_id) in &state.assignments {
            let own_impact = scheduler.function_profiles[&player.fn_id]
                .heterogeneity
                .impact();
            let other_impact = state.node_aggregates[node_id].impact_sum - own_impact;
            total += scheduler
                .utility(player, node_id, other_impact, signal)
                .expect("test player must have a finite utility");
        }
        total
    }

    #[test]
    fn heterogeneity_profile_matches_paper_equations() {
        let profile = HeterogeneityProfile::new(0.25, 1.0, 4, true);
        let expected_resource_intensity = 2.0 * (0.25_f32 * 1.0).sqrt() / 1.25;
        let expected_complexity = (4.0_f32.ln() / DAG_COMPLEXITY_NORMALIZER).tanh();
        let expected_network = (expected_resource_intensity * expected_complexity).sqrt();
        let expected_differentiation = (0.25 * DIFFERENTIATION_P1 + DIFFERENTIATION_P2)
            .rem_euclid(DIFFERENTIATION_MODULUS)
            / DIFFERENTIATION_MODULUS;

        assert_close(profile.resource_intensity, expected_resource_intensity);
        assert_close(profile.function_complexity, expected_complexity);
        assert_close(profile.network_dependency, expected_network);
        assert_close(profile.differentiation, expected_differentiation);
    }

    #[test]
    fn window_externality_does_not_duplicate_runtime_pressure() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.node_snapshots = vec![NodeSnapshot {
            pressure: 2.0,
            utilization: 0.8,
            ..NodeSnapshot::default()
        }];
        scheduler
            .function_profiles
            .insert(0, function_profile(0, 0.5, 0.5, 3));
        scheduler
            .function_profiles
            .insert(1, function_profile(1, 0.6, 0.4, 4));

        // Runtime occupancy affects Eqs. (11)-(12), but Eq. (8) must only
        // sum the other functions participating in this scheduling window.
        let runtime_occupancy = vec![NodeAggregate {
            request_count: 100,
            resource_intensity_sum: 80.0,
            impact_sum: 70.0,
            reserved_container_memory: 0.0,
        }];
        let signal = scheduler.build_price_signal(&runtime_occupancy);
        assert!(signal.node_congestion_premiums[0] > 0.0);

        let first = PlayerId {
            req_id: 1,
            fn_id: 0,
        };
        let second = PlayerId {
            req_id: 2,
            fn_id: 1,
        };
        scheduler.available_container_memory = vec![1.0];
        scheduler.new_container_limits.insert(first.fn_id, 1);
        scheduler.feasible_nodes.insert(first, vec![0]);
        let existing_containers = HashSet::new();

        // This is the pre-fix state: one current player inherits the impact of
        // unrelated runtime assignments, so Eq. (8) alone makes welfare (and
        // therefore its SA reference) negative.
        let mut duplicated_state = AssignmentState::new(runtime_occupancy, 1);
        duplicated_state.add(first, 0, &existing_containers, &scheduler.function_profiles);
        let duplicated = scheduler.social_welfare(&[first], &duplicated_state, &signal);
        assert!(duplicated.externality > 0.0);
        assert!(duplicated.total < 0.0);

        let mut state = AssignmentState::new(scheduler.empty_window_aggregates(), 2);
        state.add(first, 0, &existing_containers, &scheduler.function_profiles);
        let one_player = scheduler.social_welfare(&[first], &state, &signal);
        assert_close(one_player.externality, 0.0);
        assert!(one_player.total > 0.0);
        let reference = scheduler
            .compute_social_reference_sa(&[first], &state, &signal, 1)
            .expect("the feasible one-player window has a finite reference");
        assert_close(reference.value, one_player.total);

        state.add(
            second,
            0,
            &existing_containers,
            &scheduler.function_profiles,
        );
        let two_players = scheduler.social_welfare(&[first, second], &state, &signal);
        let first_heterogeneity = scheduler.function_profiles[&first.fn_id].heterogeneity;
        let second_heterogeneity = scheduler.function_profiles[&second.fn_id].heterogeneity;
        let expected_externality = scheduler.node_snapshots[0].pressure
            * (first_heterogeneity.resource_intensity * second_heterogeneity.impact()
                + second_heterogeneity.resource_intensity * first_heterogeneity.impact());
        assert_close(two_players.externality, expected_externality);
    }

    #[test]
    fn queue_pressure_includes_only_pending_and_runnable_tasks() {
        assert_close(normalized_queue_pressure(24, 12.0), 2.0);
        assert_close(normalized_queue_pressure(6, 12.0), 0.5);
    }

    #[test]
    fn aggregate_social_welfare_matches_player_equations_after_move() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.node_snapshots = vec![
            NodeSnapshot {
                pressure: 1.4,
                utilization: 0.55,
                ..NodeSnapshot::default()
            },
            NodeSnapshot {
                pressure: 0.6,
                utilization: 0.25,
                ..NodeSnapshot::default()
            },
        ];
        scheduler
            .function_profiles
            .insert(0, function_profile(0, 0.35, 0.8, 4));
        scheduler
            .function_profiles
            .insert(1, function_profile(1, 0.75, 0.4, 7));

        let players = [
            PlayerId {
                req_id: 10,
                fn_id: 0,
            },
            PlayerId {
                req_id: 11,
                fn_id: 1,
            },
        ];
        let window_aggregates = vec![NodeAggregate::default(); 2];
        let existing_containers = HashSet::new();
        let mut state = AssignmentState::new(window_aggregates, players.len());
        state.add(
            players[0],
            0,
            &existing_containers,
            &scheduler.function_profiles,
        );
        state.add(
            players[1],
            0,
            &existing_containers,
            &scheduler.function_profiles,
        );
        let signal = PriceSignal {
            baseline_prices: vec![0.25, 0.2],
            adjusted_prices: vec![0.25, 0.2],
            node_congestion_premiums: vec![0.1, 0.0],
            global_load: 0.8,
            network_congestion: 1.2,
        };

        assert_breakdown_close(
            scheduler.social_welfare(&players, &state, &signal),
            direct_social_welfare(&scheduler, &state, &signal),
        );

        assert_eq!(
            state.remove(
                players[1],
                &existing_containers,
                &scheduler.function_profiles
            ),
            Some(0)
        );
        state.add(
            players[1],
            1,
            &existing_containers,
            &scheduler.function_profiles,
        );
        assert_breakdown_close(
            scheduler.social_welfare(&players, &state, &signal),
            direct_social_welfare(&scheduler, &state, &signal),
        );
    }

    #[test]
    fn price_feedback_uses_fixed_window_baseline() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.settings.price_adjustment_factor = 0.6;
        let mut signal = PriceSignal {
            baseline_prices: vec![2.0, 3.0],
            adjusted_prices: vec![2.0, 3.0],
            node_congestion_premiums: vec![0.0, 0.0],
            global_load: 0.7,
            network_congestion: 1.4,
        };
        let gap = 0.2;
        let expected_gamma = 0.6 * 0.7_f32.tanh();
        let expected_multiplier = 1.0 + expected_gamma * 1.4 * gap;

        assert_close(
            scheduler.apply_price_feedback(&mut signal, gap),
            expected_gamma,
        );
        assert_close(signal.adjusted_prices[0], 2.0 * expected_multiplier);
        assert_close(signal.adjusted_prices[1], 3.0 * expected_multiplier);

        signal.adjusted_prices.fill(999.0);
        scheduler.apply_price_feedback(&mut signal, gap);
        assert_close(signal.adjusted_prices[0], 2.0 * expected_multiplier);
        assert_close(signal.adjusted_prices[1], 3.0 * expected_multiplier);
    }

    #[test]
    fn reference_keys_accept_decimal_and_hexadecimal() {
        assert_eq!(ScheNashScheduler::parse_reference_key("42"), Some(42));
        assert_eq!(ScheNashScheduler::parse_reference_key("0x2a"), Some(42));
        assert_eq!(ScheNashScheduler::parse_reference_key(" 0X2A "), Some(42));
        assert_eq!(ScheNashScheduler::parse_reference_key("invalid"), None);
    }

    #[test]
    fn reference_jsonl_preserves_zero_and_negative_values() {
        let contents = concat!(
            "{\"v\":1,\"kind\":\"offline_social_reference_build\",\"state_key\":\"0x2a\",\"reference\":0.0}\n",
            "{\"v\":1,\"kind\":\"offline_social_reference_build\",\"state_key_u64\":43,\"reference\":-2.5}\n",
            "{\"v\":1,\"kind\":\"offline_social_reference_build\",\"state_key_u64\":44,\"reference\":null}\n",
        );
        let references = ScheNashScheduler::parse_reference_contents(contents)
            .expect("valid JSONL build records must load");
        assert_eq!(references.get(&42).copied(), Some(Some(0.0)));
        assert_eq!(references.get(&43).copied(), Some(Some(-2.5)));
        assert_eq!(references.get(&44).copied(), Some(None));
    }

    #[test]
    fn nonpositive_social_reference_is_never_used_as_a_denominator() {
        assert_eq!(ScheNashScheduler::social_gap(0.0, -1.0), None);
        assert_eq!(ScheNashScheduler::social_gap(-2.0, -3.0), None);
        assert_eq!(ScheNashScheduler::social_gap(f32::NAN, 1.0), None);
        assert_eq!(ScheNashScheduler::social_gap(10.0, 10.5), None);
        assert!(ScheNashScheduler::reference_is_below_current(10.0, 10.5));
        assert!(!ScheNashScheduler::reference_is_below_current(0.0, 10.5));
        assert_close(
            ScheNashScheduler::social_gap(10.0, 7.5).expect("positive reference is valid"),
            0.25,
        );
    }

    #[test]
    fn run_reference_applicability_is_not_inferred_from_positive_reference() {
        let mut aggregate = RunAggregate::default();
        let eligible = SolveStats {
            reference_key: Some(1),
            social_reference: Some(10.0),
            reference_feedback_eligible: true,
            ..SolveStats::default()
        };
        aggregate.record(1, &eligible, &WindowTimings::default());

        let below_current = SolveStats {
            reference_key: Some(2),
            social_reference: Some(10.0),
            reference_below_current: true,
            ..SolveStats::default()
        };
        aggregate.record(1, &below_current, &WindowTimings::default());

        assert_eq!(aggregate.reference_windows, 2);
        assert_eq!(aggregate.reference_feedback_eligible_windows, 1);
        assert_eq!(aggregate.reference_below_current_windows, 1);
        assert_eq!(aggregate.reference_zero_windows, 0);
        assert_eq!(aggregate.reference_negative_windows, 0);
    }

    #[test]
    fn offline_required_never_uses_scalar_or_sa_fallback() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.settings.reference_mode = "offline_required".to_string();
        scheduler.settings.offline_social_reference = Some(123.0);
        scheduler
            .function_profiles
            .insert(0, function_profile(0, 0.5, 0.5, 3));
        scheduler.node_snapshots = vec![NodeSnapshot::default()];
        scheduler.available_container_memory = vec![1.0];
        scheduler.new_container_limits.insert(0, 1);
        let player = PlayerId {
            req_id: 1,
            fn_id: 0,
        };
        scheduler.feasible_nodes.insert(player, vec![0]);
        let players = [player];
        let existing = vec![NodeAggregate::default()];
        let mut state = AssignmentState::new(existing.clone(), 1);
        state.add(
            player,
            0,
            &scheduler.existing_containers,
            &scheduler.function_profiles,
        );
        let signal = PriceSignal {
            baseline_prices: vec![0.3],
            adjusted_prices: vec![0.3],
            node_congestion_premiums: vec![0.0],
            global_load: 0.0,
            network_congestion: 1.0,
        };
        let result = scheduler.get_social_reference(&players, &state, &existing, &signal, 1.0);
        assert_eq!(result.value, None);
        assert_eq!(result.source, "offline_table_missing");
        assert_eq!(result.compute_us, 0);
        assert_eq!(result.sa_iterations, 0);
    }

    #[test]
    fn offline_required_distinguishes_unavailable_from_missing_reference() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.settings.reference_mode = "offline_required".to_string();
        scheduler
            .function_profiles
            .insert(0, function_profile(0, 0.5, 0.5, 3));
        scheduler.node_snapshots = vec![NodeSnapshot::default()];
        scheduler.available_container_memory = vec![1.0];
        scheduler.new_container_limits.insert(0, 1);
        let player = PlayerId {
            req_id: 1,
            fn_id: 0,
        };
        scheduler.feasible_nodes.insert(player, vec![0]);
        let players = [player];
        let existing = vec![NodeAggregate::default()];
        let mut state = AssignmentState::new(existing.clone(), 1);
        state.add(
            player,
            0,
            &scheduler.existing_containers,
            &scheduler.function_profiles,
        );
        let signal = PriceSignal {
            baseline_prices: vec![0.3],
            adjusted_prices: vec![0.3],
            node_congestion_premiums: vec![0.0],
            global_load: 0.0,
            network_congestion: 1.0,
        };
        let key = scheduler.social_reference_key(&players, &existing, &signal);
        scheduler.offline_reference_table.insert(key, None);

        let result = scheduler.get_social_reference(&players, &state, &existing, &signal, 1.0);
        assert_eq!(result.value, None);
        assert_eq!(result.source, "offline_table_unavailable");
        assert!(result.cache_hit);
        assert_eq!(result.compute_us, 0);
        assert_eq!(result.sa_iterations, 0);
    }

    #[test]
    fn assignment_hash_is_independent_of_player_input_order() {
        let first = PlayerId {
            req_id: 7,
            fn_id: 1,
        };
        let second = PlayerId {
            req_id: 3,
            fn_id: 2,
        };
        let mut state = AssignmentState::new(vec![NodeAggregate::default(); 2], 2);
        state.assignments.insert(first, 0);
        state.assignments.insert(second, 1);
        assert_eq!(
            ScheNashScheduler::assignment_fingerprint(&[first, second], &state),
            ScheNashScheduler::assignment_fingerprint(&[second, first], &state),
        );
    }

    #[test]
    fn reference_state_key_is_independent_of_candidate_order() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler
            .function_profiles
            .insert(0, function_profile(0, 0.5, 0.5, 3));
        scheduler.node_snapshots = vec![NodeSnapshot::default(); 2];
        scheduler.available_container_memory = vec![1.0, 1.0];
        scheduler.new_container_limits.insert(0, 1);
        let players = [PlayerId {
            req_id: 1,
            fn_id: 0,
        }];
        scheduler.feasible_nodes.insert(players[0], vec![1, 0]);
        let existing = vec![NodeAggregate::default(); 2];
        let signal = PriceSignal {
            baseline_prices: vec![0.3, 0.3],
            adjusted_prices: vec![0.3, 0.3],
            node_congestion_premiums: vec![0.0, 0.0],
            global_load: 0.0,
            network_congestion: 1.0,
        };
        let first = scheduler.social_reference_key(&players, &existing, &signal);
        scheduler.feasible_nodes.insert(players[0], vec![0, 1]);
        let second = scheduler.social_reference_key(&players, &existing, &signal);
        assert_eq!(first, second);
    }

    #[test]
    fn social_reference_state_is_independent_of_policy_assignment() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler
            .function_profiles
            .insert(0, function_profile(0, 0.5, 0.5, 3));
        scheduler.node_snapshots = vec![NodeSnapshot::default(); 2];
        scheduler.available_container_memory = vec![1.0, 1.0];
        scheduler.new_container_limits.insert(0, 1);
        let player = PlayerId {
            req_id: 1,
            fn_id: 0,
        };
        let players = [player];
        scheduler.feasible_nodes.insert(player, vec![1, 0]);
        let signal = PriceSignal {
            baseline_prices: vec![0.3, 0.3],
            adjusted_prices: vec![0.3, 0.3],
            node_congestion_premiums: vec![0.0, 0.0],
            global_load: 0.0,
            network_congestion: 1.0,
        };
        let canonical = scheduler
            .canonical_reference_state(&players, &signal)
            .expect("canonical reference assignment");
        assert_eq!(canonical.assignments.get(&player), Some(&0));

        let mut first_policy = AssignmentState::new(vec![NodeAggregate::default(); 2], 1);
        first_policy.add(
            player,
            0,
            &scheduler.existing_containers,
            &scheduler.function_profiles,
        );
        let mut second_policy = AssignmentState::new(vec![NodeAggregate::default(); 2], 1);
        second_policy.add(
            player,
            1,
            &scheduler.existing_containers,
            &scheduler.function_profiles,
        );
        assert_ne!(
            ScheNashScheduler::assignment_fingerprint(&players, &first_policy),
            ScheNashScheduler::assignment_fingerprint(&players, &second_policy)
        );
        assert_eq!(
            scheduler.social_reference_key(&players, &vec![NodeAggregate::default(); 2], &signal,),
            scheduler.social_reference_key(&players, &vec![NodeAggregate::default(); 2], &signal,)
        );
    }

    #[test]
    fn policy_independent_reference_matches_exact_small_optimum_deterministically() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.node_snapshots = vec![
            NodeSnapshot {
                pressure: 1.8,
                utilization: 0.65,
                ..NodeSnapshot::default()
            },
            NodeSnapshot {
                pressure: 0.7,
                utilization: 0.25,
                ..NodeSnapshot::default()
            },
            NodeSnapshot {
                pressure: 1.1,
                utilization: 0.4,
                ..NodeSnapshot::default()
            },
        ];
        scheduler.available_container_memory = vec![10.0; 3];
        let players = [
            PlayerId {
                req_id: 3,
                fn_id: 0,
            },
            PlayerId {
                req_id: 1,
                fn_id: 1,
            },
            PlayerId {
                req_id: 2,
                fn_id: 2,
            },
        ];
        for (fn_id, cpu, memory, dag_nodes) in
            [(0, 0.3, 0.8, 3), (1, 0.7, 0.4, 5), (2, 0.9, 0.6, 7)]
        {
            scheduler
                .function_profiles
                .insert(fn_id, function_profile(fn_id, cpu, memory, dag_nodes));
            for node_id in 0..3 {
                scheduler.existing_containers.insert((fn_id, node_id));
            }
        }
        for player in players {
            scheduler.feasible_nodes.insert(player, vec![2, 0, 1]);
        }
        let signal = PriceSignal {
            baseline_prices: vec![0.45, 0.25, 0.35],
            adjusted_prices: vec![0.45, 0.25, 0.35],
            node_congestion_premiums: vec![0.0; 3],
            global_load: 0.8,
            network_congestion: 1.0,
        };

        let mut exact = f32::NEG_INFINITY;
        for first_node in 0..3 {
            for second_node in 0..3 {
                for third_node in 0..3 {
                    let mut state =
                        AssignmentState::new(vec![NodeAggregate::default(); 3], players.len());
                    for (player, node_id) in
                        players
                            .iter()
                            .copied()
                            .zip([first_node, second_node, third_node])
                    {
                        state.add(
                            player,
                            node_id,
                            &scheduler.existing_containers,
                            &scheduler.function_profiles,
                        );
                    }
                    exact = exact.max(scheduler.social_welfare(&players, &state, &signal).total);
                }
            }
        }

        let canonical = scheduler
            .canonical_reference_state(&players, &signal)
            .expect("small instance has a complete canonical assignment");
        let first = scheduler
            .compute_social_reference_sa(&players, &canonical, &signal, 0x1234)
            .expect("small instance reference");
        let second = scheduler
            .compute_social_reference_sa(&players, &canonical, &signal, 0x1234)
            .expect("deterministic repeat");
        assert_close(first.value, exact);
        assert_close(second.value, exact);
        assert_eq!(first.sa_iterations, second.sa_iterations);
        assert!(
            first.sa_iterations as usize >= scheduler.reference_neighborhood_size(&players),
            "SA budget must cover at least one candidate-scaled neighborhood"
        );

        for candidates in scheduler.feasible_nodes.values_mut() {
            candidates.reverse();
        }
        let reordered = scheduler
            .canonical_reference_state(&players, &signal)
            .expect("candidate order must not affect feasibility");
        let reordered_reference = scheduler
            .compute_social_reference_sa(
                &[players[2], players[0], players[1]],
                &reordered,
                &signal,
                0x1234,
            )
            .expect("reordered reference");
        assert_close(reordered_reference.value, exact);
    }

    #[test]
    fn reference_search_preserves_legitimate_negative_optimum() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.node_snapshots = vec![NodeSnapshot {
            pressure: 1_000.0,
            utilization: 1.0,
            ..NodeSnapshot::default()
        }];
        scheduler.available_container_memory = vec![10.0];
        let players = [
            PlayerId {
                req_id: 1,
                fn_id: 0,
            },
            PlayerId {
                req_id: 2,
                fn_id: 1,
            },
        ];
        for (fn_id, cpu, memory) in [(0, 0.8, 0.7), (1, 0.9, 0.6)] {
            scheduler
                .function_profiles
                .insert(fn_id, function_profile(fn_id, cpu, memory, 5));
            scheduler.existing_containers.insert((fn_id, 0));
        }
        for player in players {
            scheduler.feasible_nodes.insert(player, vec![0]);
        }
        let signal = PriceSignal {
            baseline_prices: vec![0.3],
            adjusted_prices: vec![0.3],
            node_congestion_premiums: vec![0.0],
            global_load: 1.0,
            network_congestion: 1.0,
        };
        let canonical = scheduler
            .canonical_reference_state(&players, &signal)
            .expect("single-node instance is feasible");
        let exact = scheduler
            .social_welfare(&players, &canonical, &signal)
            .total;
        assert!(exact < 0.0);
        let reference = scheduler
            .compute_social_reference_sa(&players, &canonical, &signal, 7)
            .expect("negative feasible reference remains observable");
        assert_close(reference.value, exact);
        assert!(reference.value < 0.0);
    }

    #[test]
    fn same_function_players_use_request_specific_candidate_sets() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler
            .function_profiles
            .insert(0, function_profile(0, 0.5, 0.5, 3));
        scheduler.node_snapshots = vec![NodeSnapshot::default(); 2];
        scheduler.available_container_memory = vec![1.0, 1.0];
        scheduler.existing_containers.insert((0, 0));
        scheduler.existing_containers.insert((0, 1));
        let first = PlayerId {
            req_id: 1,
            fn_id: 0,
        };
        let second = PlayerId {
            req_id: 2,
            fn_id: 0,
        };
        scheduler.feasible_nodes.insert(first, vec![0]);
        scheduler.feasible_nodes.insert(second, vec![1]);
        let signal = PriceSignal {
            baseline_prices: vec![0.3, 0.3],
            adjusted_prices: vec![0.3, 0.3],
            node_congestion_premiums: vec![0.0, 0.0],
            global_load: 0.0,
            network_congestion: 1.0,
        };
        let mut stats = SolveStats::default();
        let mut no_feasible = HashSet::new();
        let state = scheduler.initialize_assignment(
            &[first, second],
            vec![NodeAggregate::default(); 2],
            &signal,
            &mut stats,
            &mut no_feasible,
        );

        assert_eq!(state.assignments.get(&first), Some(&0));
        assert_eq!(state.assignments.get(&second), Some(&1));
        assert!(no_feasible.is_empty());
    }

    #[test]
    fn utility_uses_function_level_quality_weight() {
        let mut scheduler = ScheNashScheduler::new();
        scheduler.node_snapshots = vec![NodeSnapshot {
            pressure: 0.5,
            utilization: 0.25,
            ..NodeSnapshot::default()
        }];
        let mut low_weight = function_profile(0, 0.5, 0.5, 3);
        low_weight.quality_weight = 0.2;
        let mut high_weight = function_profile(1, 0.5, 0.5, 3);
        high_weight.quality_weight = 0.9;
        scheduler.function_profiles.insert(0, low_weight);
        scheduler.function_profiles.insert(1, high_weight);
        let signal = PriceSignal {
            baseline_prices: vec![0.3],
            adjusted_prices: vec![0.3],
            node_congestion_premiums: vec![0.0],
            global_load: 0.0,
            network_congestion: 1.0,
        };
        let low = scheduler
            .utility(
                PlayerId {
                    req_id: 1,
                    fn_id: 0,
                },
                0,
                0.0,
                &signal,
            )
            .expect("low-weight utility");
        let high = scheduler
            .utility(
                PlayerId {
                    req_id: 2,
                    fn_id: 1,
                },
                0,
                0.0,
                &signal,
            )
            .expect("high-weight utility");
        assert!(high.quality > low.quality);
        assert_close(
            high.quality / low.quality,
            high_weight.quality_weight / low_weight.quality_weight,
        );
    }

    #[test]
    fn build_writer_keeps_partial_until_atomic_finalize() {
        let unique = format!(
            "nsesche_reference_test_{}_{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("system clock")
                .as_nanos()
        );
        let directory = std::env::temp_dir().join(unique);
        fs::create_dir(&directory).expect("create test directory");
        let final_path = directory.join("references.jsonl");
        let partial_path = ReferenceBuildWriter::partial_path(&final_path);
        let mut writer = ReferenceBuildWriter::new(final_path.clone()).expect("create writer");
        assert!(writer
            .record(42, Some(-1.25), 99, 4, 64, 12)
            .expect("write record"));
        assert!(!writer
            .record(42, Some(-1.25), 99, 4, 64, 12)
            .expect("deduplicate record"));
        assert!(partial_path.exists());
        assert!(!final_path.exists());
        writer.finalize().expect("publish build artifact");
        assert!(!partial_path.exists());
        assert!(final_path.exists());
        let references = ScheNashScheduler::parse_reference_contents(
            &fs::read_to_string(&final_path).expect("read build artifact"),
        )
        .expect("replay build artifact");
        assert_eq!(references.get(&42).copied(), Some(Some(-1.25)));
        fs::remove_file(&final_path).expect("remove test artifact");
        fs::remove_dir(&directory).expect("remove test directory");
    }

    #[test]
    fn observation_writer_keeps_partial_until_atomic_finalize() {
        let unique = format!(
            "nsesche_observation_test_{}_{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("system clock")
                .as_nanos()
        );
        let directory = std::env::temp_dir().join(unique);
        fs::create_dir(&directory).expect("create test directory");
        let final_path = directory.join("nash_metrics.jsonl");
        let partial_path = ReferenceBuildWriter::partial_path(&final_path);
        let mut writer = NashObservationWriter::new(final_path.clone()).expect("create writer");
        writer
            .record(&serde_json::json!({"kind": "window", "frame": 7}))
            .expect("write event");
        assert!(partial_path.exists());
        assert!(!final_path.exists());
        writer.finalize().expect("publish observation artifact");
        assert!(!partial_path.exists());
        assert!(final_path.exists());
        let line = fs::read_to_string(&final_path).expect("read observation artifact");
        let event: serde_json::Value = serde_json::from_str(line.trim()).expect("valid JSONL");
        assert_eq!(event["frame"], 7);
        fs::remove_file(&final_path).expect("remove test artifact");
        fs::remove_dir(&directory).expect("remove test directory");
    }
}
