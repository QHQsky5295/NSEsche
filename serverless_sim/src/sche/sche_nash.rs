use std::{
    collections::{HashMap, HashSet, VecDeque},
    env, fs,
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
            base_utility: 10.0,
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
        let ablation_type = std::env::var("NASH_ABLATION_TYPE")
            .unwrap_or_else(|_| "full".to_string())
            .to_ascii_lowercase();
        let observation_mode = std::env::var("NASH_OBSERVE")
            .unwrap_or_else(|_| "summary".to_string())
            .to_ascii_lowercase();
        let system_utility_enabled = ablation_type != "no_social";
        let reference_mode = std::env::var("NASH_REFERENCE_MODE")
            .unwrap_or_else(|_| "sa_fallback".to_string())
            .to_ascii_lowercase();
        let reference_mode = match reference_mode.as_str() {
            "offline_required" | "build" | "sa_fallback" => reference_mode,
            _ => "sa_fallback".to_string(),
        };

        Self {
            max_inner_rounds: env_u32("NASH_MAX_INNER_ITERATIONS", 4, 1, 128),
            max_outer_rounds: env_u32("NASH_MAX_OUTER_ITERATIONS", 2, 1, 32),
            price_adjustment_factor: env_f32("NASH_PRICE_FEEDBACK_RATE", default_r0, 0.0, 1.0),
            quality_weight: env_f32("NASH_QUALITY_WEIGHT", default_quality_weight, 0.0, 10.0),
            base_node_price: env_f32("NASH_BASE_NODE_PRICE", 0.3, EPSILON, 1_000.0),
            base_utility: env_f32("NASH_BASE_UTILITY", 10.0, 0.0, 1_000_000.0),
            contribution_coefficient: env_f32(
                "NASH_CONTRIBUTION_COEFFICIENT",
                1.0,
                0.0,
                1_000_000.0,
            ),
            queue_normalizer: env_f32("NASH_QUEUE_NORMALIZER", 12.0, EPSILON, 1.0e9),
            social_gap_epsilon: env_f32("NASH_SOCIAL_GAP_EPSILON", EPSILON, 0.0, 1.0),
            sa_iterations: env_u32("NASH_SA_ITERATIONS", 64, 1, 100_000),
            sa_iterations_per_player: env_u32("NASH_SA_ITERATIONS_PER_PLAYER", 4, 0, 1_000),
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
                .filter(|value| !value.trim().is_empty()),
            reference_mode,
            observation_enabled: !matches!(observation_mode.as_str(), "off" | "false" | "0"),
            observation_detail: observation_mode == "detail",
            heterogeneity_enabled: ablation_type != "no_heterogeneity",
            externality_enabled: system_utility_enabled && ablation_type != "no_externality",
            contribution_enabled: system_utility_enabled && ablation_type != "no_contribution",
            congestion_pricing_enabled: ablation_type != "no_pricing",
            social_coordination_enabled: ablation_type != "no_coordination"
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
    heterogeneity: HeterogeneityProfile,
}

#[derive(Clone, Copy, Debug, Default)]
struct NodeSnapshot {
    cpu_utilization: f32,
    memory_utilization: f32,
    pending_tasks: usize,
    running_tasks: usize,
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
        player_aggregate.quality_feature_sum +=
            heterogeneity.function_complexity + heterogeneity.network_dependency;
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
            - heterogeneity.function_complexity
            - heterogeneity.network_dependency)
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
    welfare: UtilityBreakdown,
    social_reference: Option<f32>,
    reference_key: Option<u64>,
    social_gap: Option<f32>,
    gamma: f32,
    reference_source: &'static str,
    reference_cache_hit: bool,
    reference_compute_us: u64,
    reference_lookup_us: u64,
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
            welfare: UtilityBreakdown::default(),
            social_reference: None,
            reference_key: None,
            social_gap: None,
            gamma: 0.0,
            reference_source: "not_requested",
            reference_cache_hit: false,
            reference_compute_us: 0,
            reference_lookup_us: 0,
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

#[derive(Clone, Copy, Debug, Default)]
struct ReferenceResult {
    value: Option<f32>,
    key: Option<u64>,
    source: &'static str,
    cache_hit: bool,
    compute_us: u64,
    lookup_us: u64,
    sa_iterations: u32,
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
    reference_sa_iterations: u64,
}

impl RunAggregate {
    fn record(&mut self, player_count: usize, stats: &SolveStats, timings: &WindowTimings) {
        self.windows += 1;
        self.wall_us.push(timings.scheduler_wall_us);
        self.thread_cpu_us.push(timings.scheduler_thread_cpu_us);
        self.reference_compute_us += stats.reference_compute_us;
        self.reference_lookup_us += stats.reference_lookup_us;
        self.reference_sa_iterations += stats.reference_sa_iterations;
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
    feasible_nodes: HashMap<FnId, Vec<NodeId>>,
    new_container_limits: HashMap<FnId, usize>,
    existing_containers: HashSet<(FnId, NodeId)>,
    warm_containers: HashSet<(FnId, NodeId)>,
    available_container_memory: Vec<f32>,
    scheduled_pairs: HashSet<PlayerId>,
    social_reference_cache: HashMap<u64, f32>,
    social_reference_order: VecDeque<u64>,
    offline_reference_table: HashMap<u64, f32>,
    offline_reference_file_loaded: Option<String>,
    offline_reference_load_error: Option<String>,
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
            scheduled_pairs: HashSet::new(),
            social_reference_cache: HashMap::with_capacity(SOCIAL_REFERENCE_CACHE_CAPACITY),
            social_reference_order: VecDeque::with_capacity(SOCIAL_REFERENCE_CACHE_CAPACITY),
            offline_reference_table: HashMap::new(),
            offline_reference_file_loaded: None,
            offline_reference_load_error: None,
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

        let parsed = fs::read_to_string(&path)
            .map_err(|error| error.to_string())
            .and_then(|contents| {
                serde_json::from_str::<serde_json::Value>(&contents)
                    .map_err(|error| error.to_string())
            });
        let value = match parsed {
            Ok(value) => value,
            Err(error) => {
                self.offline_reference_load_error = Some(error);
                return;
            }
        };
        let references = value.get("references").unwrap_or(&value);
        let Some(entries) = references.as_object() else {
            self.offline_reference_load_error =
                Some("reference JSON must be an object or contain a references object".to_string());
            return;
        };
        for (raw_key, raw_value) in entries {
            let Some(key) = Self::parse_reference_key(raw_key) else {
                continue;
            };
            let Some(reference) = raw_value.as_f64().map(|value| value as f32) else {
                continue;
            };
            if reference.is_finite() && reference > EPSILON {
                self.offline_reference_table.insert(key, reference);
            }
        }
        if self.offline_reference_table.is_empty() {
            self.offline_reference_load_error =
                Some("no valid reference entries found".to_string());
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
        for (fn_id, dag_id, cpu, memory, output_mb, cold_start_frames, required_memory) in functions
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
                    heterogeneity,
                },
            );
        }
        self.profile_function_count = function_count;
        self.profile_heterogeneity_enabled = self.settings.heterogeneity_enabled;
    }

    fn collect_players(&mut self, env: &SimEnvObserve) -> Vec<PlayerId> {
        let requests = env.core().requests();
        let active_request_ids: HashSet<ReqId> = requests.keys().copied().collect();
        self.scheduled_pairs
            .retain(|player| active_request_ids.contains(&player.req_id));

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
                    && !self.scheduled_pairs.contains(&player)
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
                // l_max is a configured upper bound in Eq. (14); cap the
                // remaining-time proxy at that bound before normalization.
                normalized_delay_sum += (delay / latency_bound).clamp(0.0, 1.0);
            }
        }
        self.network_beta_proxy = 1.0 + normalized_delay_sum / pair_count as f32;
    }

    fn update_node_snapshots(
        &mut self,
        env: &SimEnvObserve,
        active_functions: &[FnId],
        require_existing_container: bool,
    ) {
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
            let pending_tasks = node.pending_task_cnt();
            let running_tasks = node.running_task_cnt();
            let (container_count, running_containers) = {
                let containers = node.fn_containers.borrow();
                for (&fn_id, container) in containers.iter() {
                    self.existing_containers.insert((fn_id, node_id));
                    if container.is_running() {
                        self.warm_containers.insert((fn_id, node_id));
                        let parents = self.function_parents.get(&fn_id);
                        for (&req_id, task) in &container.req_fn_state {
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
                            for (&source, &(need_mb, received_mb)) in &task.data_recv {
                                let remaining_mb = (need_mb - received_mb).max(0.0);
                                if remaining_mb > EPSILON {
                                    active_transfers.push((source, node_id, remaining_mb));
                                }
                            }
                        }
                    }
                }
                (
                    containers.len(),
                    containers
                        .values()
                        .filter(|container| container.is_running())
                        .count(),
                )
            };
            let queue_ratio = pending_tasks as f32 / self.settings.queue_normalizer;
            let pressure = cpu_utilization + memory_utilization + queue_ratio;
            let utilization = ((cpu_utilization + memory_utilization) * 0.5).clamp(0.0, 1.0);
            self.node_snapshots[node_id] = NodeSnapshot {
                cpu_utilization,
                memory_utilization,
                pending_tasks,
                running_tasks,
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

        self.feasible_nodes.clear();
        for &fn_id in active_functions {
            let Some(profile) = self.function_profiles.get(&fn_id) else {
                continue;
            };
            let mut candidates = Vec::with_capacity(node_count);
            for node_id in 0..node_count {
                let has_container = self.existing_containers.contains(&(fn_id, node_id));
                let can_create_container =
                    self.available_container_memory[node_id] > profile.required_container_memory;
                if has_container || (!require_existing_container && can_create_container) {
                    candidates.push(node_id);
                }
            }
            self.feasible_nodes.insert(fn_id, candidates);
        }
    }

    fn build_existing_aggregates(&mut self, env: &SimEnvObserve) -> Vec<NodeAggregate> {
        let mut aggregates = vec![NodeAggregate::default(); self.node_snapshots.len()];
        let requests = env.core().requests();
        let mut cross_node_assignments = 0usize;
        let mut total_assignments = 0usize;
        for request in requests.values() {
            let active_assignments = request
                .fn_node
                .iter()
                .filter(|(fn_id, _)| !request.done_fns.contains_key(fn_id));
            let distinct_nodes: HashSet<NodeId> = active_assignments
                .clone()
                .map(|(_, &node_id)| node_id)
                .collect();
            let active_assignment_count = active_assignments.clone().count();
            total_assignments += active_assignment_count;
            if distinct_nodes.len() > 1 {
                cross_node_assignments += active_assignment_count.saturating_sub(1);
            }
            for (&fn_id, &node_id) in active_assignments {
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
        let quality = self.settings.quality_weight
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
        let Some(candidates) = self.feasible_nodes.get(&player.fn_id) else {
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
        for &player in players {
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
        let Some(node) = self.node_snapshots.get(node_id) else {
            return UtilityBreakdown::default();
        };
        let Some(players) = state.player_node_aggregates.get(node_id).copied() else {
            return UtilityBreakdown::default();
        };
        let Some(all_assignments) = state.node_aggregates.get(node_id).copied() else {
            return UtilityBreakdown::default();
        };
        let Some(price) = signal.adjusted_prices.get(node_id).copied() else {
            return UtilityBreakdown::default();
        };

        let baseline_reward = self.settings.base_utility * players.baseline_feature_sum;
        let cost = price * players.cost_weight_sum;
        let quality =
            self.settings.quality_weight * players.quality_feature_sum / (1.0 + node.pressure);
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

    fn effective_sa_iterations(&self, player_count: usize) -> u32 {
        let scaled = self
            .settings
            .sa_iterations_per_player
            .saturating_mul(player_count.min(u32::MAX as usize) as u32);
        self.settings.sa_iterations.max(scaled).min(100_000)
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
            if let Some(candidates) = self.feasible_nodes.get(&fn_id) {
                for &node_id in candidates {
                    mix(&mut hash, node_id as u64);
                }
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

    fn compute_social_reference_sa(
        &self,
        players: &[PlayerId],
        initial_state: &AssignmentState,
        baseline_signal: &PriceSignal,
        seed: u64,
    ) -> Option<f32> {
        if players.is_empty() || initial_state.assignments.len() != players.len() {
            return None;
        }
        let mut state = initial_state.clone();
        let mut current = self.social_welfare(players, &state, baseline_signal).total;
        if !current.is_finite() {
            return None;
        }
        let mut best = current;
        let utility_scale = (current.abs() / players.len().max(1) as f32).max(1.0);
        let mut temperature = self.settings.sa_initial_temperature * utility_scale;
        let mut random_state = seed.max(1);

        for _ in 0..self.effective_sa_iterations(players.len()) {
            let iteration_temperature = temperature;
            temperature *= self.settings.sa_cooling_rate;
            let player_index =
                Self::deterministic_random(&mut random_state) as usize % players.len();
            let player = players[player_index];
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
            let Some(candidates) = self.feasible_nodes.get(&player.fn_id) else {
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
                best = best.max(candidate);
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
        (best.is_finite() && best > EPSILON).then_some(best)
    }

    fn get_social_reference(
        &mut self,
        players: &[PlayerId],
        state: &AssignmentState,
        existing: &[NodeAggregate],
        baseline_signal: &PriceSignal,
        current_welfare: f32,
    ) -> ReferenceResult {
        let lookup_start = Instant::now();
        let key = self.social_reference_key(players, existing, baseline_signal);
        if let Some(value) = self.settings.offline_social_reference {
            return ReferenceResult {
                value: Some(value),
                key: Some(key),
                source: "offline_scalar_debug",
                cache_hit: false,
                compute_us: 0,
                lookup_us: lookup_start.elapsed().as_micros() as u64,
                sa_iterations: 0,
            };
        }
        if let Some(&value) = self.offline_reference_table.get(&key) {
            return ReferenceResult {
                value: Some(value),
                key: Some(key),
                source: "offline_table",
                cache_hit: true,
                compute_us: 0,
                lookup_us: lookup_start.elapsed().as_micros() as u64,
                sa_iterations: 0,
            };
        }
        if self.settings.reference_mode == "offline_required" {
            return ReferenceResult {
                value: None,
                key: Some(key),
                source: "offline_table_missing",
                cache_hit: false,
                compute_us: 0,
                lookup_us: lookup_start.elapsed().as_micros() as u64,
                sa_iterations: 0,
            };
        }

        if let Some(&cached) = self.social_reference_cache.get(&key) {
            let lookup_us = lookup_start.elapsed().as_micros() as u64;
            if cached + EPSILON >= current_welfare {
                return ReferenceResult {
                    value: Some(cached),
                    key: Some(key),
                    source: "sa_cache",
                    cache_hit: true,
                    compute_us: 0,
                    lookup_us,
                    sa_iterations: 0,
                };
            }
        }
        let lookup_us = lookup_start.elapsed().as_micros() as u64;

        let compute_start = Instant::now();
        let sa_iterations = self.effective_sa_iterations(players.len());
        let reference = self.compute_social_reference_sa(players, state, baseline_signal, key);
        let compute_us = compute_start.elapsed().as_micros() as u64;
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
                "sa_build"
            } else {
                "sa_fallback"
            },
            cache_hit: false,
            compute_us,
            lookup_us,
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
            stats.termination_reason = "infeasible_players";
            return (state, signal, stats);
        }

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
            if !self.settings.social_coordination_enabled {
                stats.termination_reason = "nash_stable_coordination_disabled";
                break;
            }

            if window_reference.is_none() {
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
            stats.reference_sa_iterations += reference.sa_iterations as u64;
            stats.social_reference = reference.value;
            let Some(reference_value) = reference.value else {
                stats.termination_reason = "social_reference_missing";
                break;
            };
            let Some(gap) = Self::social_gap(reference_value, stats.welfare.total) else {
                stats.termination_reason = "social_reference_invalid";
                break;
            };
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
        stats.welfare = self.social_welfare(players, &state, &signal);
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
            if self.scheduled_pairs.contains(&player) {
                continue;
            }
            let Some(&node_id) = state.assignments.get(&player) else {
                result.invalid_assignments += 1;
                continue;
            };
            if node_id >= node_count {
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
                self.scheduled_pairs.extend(keys);
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
            "sa_min_iterations": self.settings.sa_iterations,
            "sa_iterations_per_player": self.settings.sa_iterations_per_player,
            "sa_cooling_rate": self.settings.sa_cooling_rate,
            "offline_scalar_debug_configured": self.settings.offline_social_reference.is_some(),
            "offline_file_configured": self.settings.offline_reference_file.is_some(),
            "offline_entries": self.offline_reference_table.len(),
            "offline_load_ok": self.settings.offline_reference_file.is_none()
                || self.offline_reference_load_error.is_none(),
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
            "queue_pressure_source": "node_pre_container_admission_queue",
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
        log::info!("NSE_METRIC_V2 {}", event);
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
            log::info!("NSE_METRIC_V2 {}", event);
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
        stats: &SolveStats,
        dispatch: &DispatchStats,
        timings: &WindowTimings,
    ) {
        if !self.settings.observation_enabled {
            return;
        }
        self.observation_window += 1;
        let node_count = self.node_snapshots.len().max(1);
        let queue_pending_total: usize = self
            .node_snapshots
            .iter()
            .map(|node| node.pending_tasks)
            .sum();
        let queue_running_total: usize = self
            .node_snapshots
            .iter()
            .map(|node| node.running_tasks)
            .sum();
        let queue_pending_max = self
            .node_snapshots
            .iter()
            .map(|node| node.pending_tasks)
            .max()
            .unwrap_or(0);
        let queue_running_max = self
            .node_snapshots
            .iter()
            .map(|node| node.running_tasks)
            .max()
            .unwrap_or(0);
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
                "queue_running_total": queue_running_total,
                "queue_running_max": queue_running_max,
                "queue_total": queue_pending_total + queue_running_total,
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
                "commands_prepared": dispatch.commands_prepared,
                "commands_sent": dispatch.commands_sent,
                "scale_ups_prepared": dispatch.scale_ups_prepared,
                "scale_ups_sent": dispatch.scale_ups_sent,
                "invalid_assignments": dispatch.invalid_assignments,
                "dispatch_channel_failed": dispatch.channel_failed,
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
                "welfare": stats.welfare.total,
                "reference": stats.social_reference,
                "reference_state_key": stats.reference_key,
                "gap": stats.social_gap,
                "reference_source": stats.reference_source,
                "reference_cache_hit": stats.reference_cache_hit,
                "reference_compute_us": stats.reference_compute_us,
                "reference_lookup_us": stats.reference_lookup_us,
                "reference_sa_iterations": stats.reference_sa_iterations,
                "utility_components": {
                    "baseline_reward": stats.welfare.baseline_reward,
                    "cost": stats.welfare.cost,
                    "quality": stats.welfare.quality,
                    "externality": stats.welfare.externality,
                    "contribution": stats.welfare.contribution,
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
        log::info!("NSE_METRIC_V2 {}", event);
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
        let (require_existing_container, emit_scale_up) = match mech.mech_type() {
            MechType::ScaleScheSeparated => (true, false),
            MechType::ScaleScheJoint => (false, true),
            MechType::NoScale => (false, false),
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
        self.update_node_snapshots(env, &active_functions, require_existing_container);
        let players = pending_players
            .iter()
            .copied()
            .filter(|player| {
                self.feasible_nodes.get(&player.fn_id).is_some_and(|nodes| {
                    nodes.iter().any(|&node_id| {
                        self.existing_containers.contains(&(player.fn_id, node_id))
                            || self
                                .new_container_limits
                                .get(&player.fn_id)
                                .copied()
                                .unwrap_or(usize::MAX)
                                > 0
                    })
                })
            })
            .collect::<Vec<_>>();
        let waiting_for_candidate_nodes = pending_players.len().saturating_sub(players.len());
        let existing = self.build_existing_aggregates(env);
        timings.snapshot_us = phase_start.elapsed().as_micros() as u64;

        let phase_start = Instant::now();
        let signal = self.build_price_signal(&existing);
        timings.pricing_us = phase_start.elapsed().as_micros() as u64;

        let phase_start = Instant::now();
        let (state, final_signal, stats) = self.solve(&players, existing, signal);
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
            "reference_sa_iterations_total": self.run_aggregate.reference_sa_iterations,
        });
        log::info!("NSE_METRIC_V2 {}", event);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_close(actual: f32, expected: f32) {
        let tolerance = 1.0e-4 * expected.abs().max(1.0);
        assert!(
            (actual - expected).abs() <= tolerance,
            "actual={actual}, expected={expected}, tolerance={tolerance}"
        );
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
        let base = vec![
            NodeAggregate {
                request_count: 1,
                resource_intensity_sum: 0.3,
                impact_sum: 0.2,
                reserved_container_memory: 0.0,
            },
            NodeAggregate::default(),
        ];
        let existing_containers = HashSet::new();
        let mut state = AssignmentState::new(base, players.len());
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
}
