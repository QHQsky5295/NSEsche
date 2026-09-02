use serde::{Deserialize, Serialize};

use crate::mechanism_conf::MechConfig;

fn default_protocol_version() -> String {
    "reviewer-v1".to_string()
}

#[cfg(test)]
mod experiment_config_tests {
    use super::Config;

    fn select_faasrank(config: &mut Config) {
        for selected in config.mech.sche.values_mut() {
            *selected = None;
        }
        config
            .mech
            .sche
            .insert("sche_FaaSRank".to_string(), Some(String::new()));
    }

    fn formal_faasrank_config() -> Config {
        let mut config = Config::new_test();
        config.total_frame = 1_000;
        config.experiment.output.enabled = true;
        config.experiment.run_id = "faasrank-formal-e1".to_string();
        config.experiment.workload_seed = "workload-1".to_string();
        config.experiment.topology_seed = "topology-1".to_string();
        config.experiment.algorithm_seed = "algorithm-1".to_string();
        config.experiment.protocol_version = "reviewer-v3".to_string();
        config.experiment.workload.frequency_profile.schema_version =
            "NSE_WORKLOAD_FREQUENCY_PROFILE_V1".to_string();
        config.experiment.workload.frequency_profile.profile_set_id =
            "submission-era-azure-cdf-v1".to_string();
        config.experiment.workload.frequency_profile.profile_id =
            "submission-era-azure-cdf-low-v1".to_string();
        config.experiment.workload.frequency_profile.load = "low".to_string();
        config.experiment.workload.frequency_profile.path = "profile.json".to_string();
        config.experiment.workload.frequency_profile.sha256 = "c".repeat(64);
        config
            .experiment
            .workload
            .frequency_profile
            .dag_call_frequency_sha256 = "d".repeat(64);
        config.experiment.workload.frequency_profile.dag_count = 50;
        config
            .experiment
            .workload
            .frequency_profile
            .expected_arrival_rate_rps = 1_934.66;
        config
            .experiment
            .workload
            .frequency_profile
            .submission_actual_arrival_rate_rps = 1_923.0;
        config
            .experiment
            .workload
            .frequency_profile
            .request_frequency_scale = 0.2;
        config.experiment.workload.frequency_profile.source = serde_json::json!({"kind": "test"});
        for selected in config.mech.instance_cache_policy.values_mut() {
            *selected = None;
        }
        config
            .mech
            .instance_cache_policy
            .insert("no_evict".to_string(), Some(String::new()));
        select_faasrank(&mut config);
        config
    }

    #[test]
    fn legacy_defaults_remain_valid() {
        let config = Config::new_test();
        assert_eq!(config.experiment.qos.class_assignment, "balanced");
        config
            .validate_experiment()
            .expect("legacy-compatible defaults");
    }

    #[test]
    fn legacy_serialized_payload_may_omit_new_model_and_qos_fields() {
        let mut payload = serde_json::to_value(Config::new_test()).expect("serialize test config");
        let experiment = payload
            .get_mut("experiment")
            .and_then(serde_json::Value::as_object_mut)
            .expect("experiment object");
        experiment.remove("faasrank_model");
        experiment
            .get_mut("qos")
            .and_then(serde_json::Value::as_object_mut)
            .expect("QoS object")
            .remove("class_assignment");

        let config: Config = serde_json::from_value(payload).expect("read legacy payload");
        assert_eq!(config.experiment.faasrank_model.state, "legacy_default");
        assert_eq!(config.experiment.faasrank_model.cpu_headroom, 0.25);
        assert_eq!(config.experiment.qos.class_assignment, "balanced");
    }

    #[test]
    fn unsupported_qos_class_assignment_is_rejected() {
        let mut config = Config::new_test();
        config.experiment.qos.class_assignment = "mixed_without_protocol".to_string();
        let error = config
            .validate_experiment()
            .expect_err("unknown QoS assignment must fail");
        assert!(error.contains("qos.class_assignment"));
    }

    #[test]
    fn formal_output_requires_explicit_provenance() {
        let mut config = Config::new_test();
        config.total_frame = 1_000;
        config.experiment.output.enabled = true;
        let error = config
            .validate_experiment()
            .expect_err("missing formal provenance must fail");
        assert!(error.contains("run_id"));
    }

    #[test]
    fn reference_not_required_is_limited_to_coordination_ablation() {
        let mut config = Config::new_test();
        config.experiment.reference.mode = "not_required".to_string();
        let error = config
            .validate_experiment()
            .expect_err("full NSESche cannot omit its offline reference");
        assert!(error.contains("coordination"));

        config.experiment.ablation.no_coordination = true;
        config
            .validate_experiment()
            .expect("coordination ablation does not evaluate the reference");
    }

    #[test]
    fn legacy_faasrank_uses_backward_compatible_defaults() {
        let mut config = Config::new_test();
        select_faasrank(&mut config);
        config
            .validate_experiment()
            .expect("non-formal legacy FaaSRank payload remains valid");
        assert_eq!(config.experiment.faasrank_model.state, "legacy_default");
        assert_eq!(config.experiment.faasrank_model.epsilon, 0.1);
    }

    #[test]
    fn formal_faasrank_requires_frozen_model_provenance() {
        let mut config = formal_faasrank_config();
        let error = config
            .validate_experiment()
            .expect_err("legacy model state must not enter formal results");
        assert!(error.contains("state=frozen"));

        config.experiment.faasrank_model.state = "frozen".to_string();
        config.experiment.faasrank_model.model_sha256 = "a".repeat(64);
        let error = config
            .validate_experiment()
            .expect_err("training provenance is mandatory");
        assert!(error.contains("non-empty training_tape_sha256"));

        config.experiment.faasrank_model.training_tape_sha256 = "b".repeat(64);
        config
            .validate_experiment()
            .expect("complete frozen model provenance is valid");
    }

    #[test]
    fn formal_faasrank_rejects_bad_hashes_and_nonfinite_parameters() {
        let mut config = formal_faasrank_config();
        config.experiment.faasrank_model.state = "frozen".to_string();
        config.experiment.faasrank_model.model_sha256 = "not-a-sha256".to_string();
        config.experiment.faasrank_model.training_tape_sha256 = "b".repeat(64);
        let error = config
            .validate_experiment()
            .expect_err("malformed model hash must fail");
        assert!(error.contains("model_sha256"));

        config.experiment.faasrank_model.model_sha256 = "a".repeat(64);
        config.experiment.faasrank_model.training_tape_sha256 = "g".repeat(64);
        let error = config
            .validate_experiment()
            .expect_err("non-hex training hash must fail");
        assert!(error.contains("training_tape_sha256"));

        config.experiment.faasrank_model.training_tape_sha256 = "b".repeat(64);
        config.experiment.faasrank_model.cpu_headroom = f32::NAN;
        let error = config
            .validate_experiment()
            .expect_err("nonfinite model coefficient must fail");
        assert!(error.contains("cpu_headroom"));

        config.experiment.faasrank_model.cpu_headroom = 0.25;
        config.experiment.faasrank_model.epsilon = f32::INFINITY;
        let error = config
            .validate_experiment()
            .expect_err("nonfinite epsilon must fail");
        assert!(error.contains("epsilon"));
    }

    #[test]
    fn queue_normalization_is_explicit_and_mode_consistent() {
        let mut config = Config::new_test();
        config
            .validate_experiment()
            .expect("window-max queue normalization is the default");

        config.experiment.nash.queue_normalization_mode = "fixed".to_string();
        let error = config
            .validate_experiment()
            .expect_err("fixed mode needs an explicit normalizer");
        assert!(error.contains("queue_normalizer"));

        config.experiment.nash.queue_normalizer = Some(1024.0);
        config
            .validate_experiment()
            .expect("positive fixed queue normalizer is valid");

        config.experiment.nash.queue_normalization_mode = "window_max".to_string();
        let error = config
            .validate_experiment()
            .expect_err("window-max mode must not carry a hidden fixed value");
        assert!(error.contains("must be null"));
    }
}

fn default_node_count() -> usize {
    20
}

fn default_node_cpu() -> f32 {
    150.0
}

fn default_node_mem() -> f32 {
    5_000.0
}

fn default_network_min_mbps() -> f32 {
    8_000.0
}

fn default_network_max_mbps() -> f32 {
    10_000.0
}

fn default_arrival_horizon() -> usize {
    1_000
}

fn default_load_scale() -> f32 {
    1.0
}

fn default_hpa_target() -> f32 {
    0.5
}

fn default_hpa_tolerance() -> f32 {
    0.1
}

fn default_hpa_history() -> usize {
    100
}

fn default_hpa_period() -> usize {
    1
}

fn default_qos_latency_weight() -> f32 {
    0.9
}

fn default_qos_throughput_weight() -> f32 {
    0.6
}

fn default_qos_cost_weight() -> f32 {
    0.2
}

fn default_qos_class_assignment() -> String {
    "balanced".to_string()
}

fn default_faasrank_state() -> String {
    "legacy_default".to_string()
}

fn default_faasrank_cpu_headroom() -> f32 {
    0.25
}

fn default_faasrank_memory_headroom() -> f32 {
    0.20
}

fn default_faasrank_network_locality() -> f32 {
    0.15
}

fn default_faasrank_warm_affinity() -> f32 {
    0.25
}

fn default_faasrank_load_balance() -> f32 {
    0.15
}

fn default_faasrank_diversity_penalty() -> f32 {
    0.05
}

fn default_faasrank_epsilon() -> f32 {
    0.1
}

fn is_sha256_hex(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

/// Runtime experiment settings.  Every field has a default so historical
/// reset payloads remain readable; formal reviewer runs must populate these
/// fields explicitly and persist the resulting config in their manifest.
#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct ExperimentConfig {
    #[serde(default = "default_protocol_version")]
    pub protocol_version: String,
    pub run_id: String,
    pub workload_seed: String,
    pub topology_seed: String,
    pub algorithm_seed: String,
    #[serde(default = "default_node_count")]
    pub node_count: usize,
    pub node_profile: NodeProfileConfig,
    pub network_profile: NetworkProfileConfig,
    pub hpa: HpaProtocolConfig,
    pub workload: WorkloadConfig,
    pub qos: QosConfig,
    pub faasrank_model: FaaSRankModelConfig,
    pub nash: NashProtocolConfig,
    pub ablation: AblationConfig,
    pub reference: ReferenceConfig,
    pub output: ExperimentOutputConfig,
}

impl Default for ExperimentConfig {
    fn default() -> Self {
        Self {
            protocol_version: default_protocol_version(),
            run_id: String::new(),
            workload_seed: String::new(),
            topology_seed: String::new(),
            algorithm_seed: String::new(),
            node_count: default_node_count(),
            node_profile: NodeProfileConfig::default(),
            network_profile: NetworkProfileConfig::default(),
            hpa: HpaProtocolConfig::default(),
            workload: WorkloadConfig::default(),
            qos: QosConfig::default(),
            faasrank_model: FaaSRankModelConfig::default(),
            nash: NashProtocolConfig::default(),
            ablation: AblationConfig::default(),
            reference: ReferenceConfig::default(),
            output: ExperimentOutputConfig::default(),
        }
    }
}

/// Frozen coefficients used by the placement-only FaaSRank-P adaptation.
///
/// Historical, non-formal payloads omit this object and therefore retain the
/// previous hard-coded coefficients through `Default`.  A formal FaaSRank-P
/// run must explicitly declare `state="frozen"` and bind both the serialized
/// model and its disjoint training tape with SHA-256 provenance.
#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct FaaSRankModelConfig {
    #[serde(default = "default_faasrank_state")]
    pub state: String,
    pub model_sha256: String,
    pub training_tape_sha256: String,
    #[serde(default = "default_faasrank_cpu_headroom")]
    pub cpu_headroom: f32,
    #[serde(default = "default_faasrank_memory_headroom")]
    pub memory_headroom: f32,
    #[serde(default = "default_faasrank_network_locality")]
    pub network_locality: f32,
    #[serde(default = "default_faasrank_warm_affinity")]
    pub warm_affinity: f32,
    #[serde(default = "default_faasrank_load_balance")]
    pub load_balance: f32,
    #[serde(default = "default_faasrank_diversity_penalty")]
    pub diversity_penalty: f32,
    #[serde(default = "default_faasrank_epsilon")]
    pub epsilon: f32,
}

impl Default for FaaSRankModelConfig {
    fn default() -> Self {
        Self {
            state: default_faasrank_state(),
            model_sha256: String::new(),
            training_tape_sha256: String::new(),
            cpu_headroom: default_faasrank_cpu_headroom(),
            memory_headroom: default_faasrank_memory_headroom(),
            network_locality: default_faasrank_network_locality(),
            warm_affinity: default_faasrank_warm_affinity(),
            load_balance: default_faasrank_load_balance(),
            diversity_penalty: default_faasrank_diversity_penalty(),
            epsilon: default_faasrank_epsilon(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct NashProtocolConfig {
    /// `None` retains the paper's load-specific defaults.
    pub price_feedback_rate: Option<f32>,
    pub quality_weight: Option<f32>,
    pub max_inner_rounds: u32,
    pub max_outer_rounds: u32,
    pub sa_iterations: u32,
    pub sa_iterations_per_player: u32,
    /// Eq. (6) queue normalization. `window_max` defines q_max(t) from the
    /// current scheduling window; `fixed` requires `queue_normalizer`.
    pub queue_normalization_mode: String,
    pub queue_normalizer: Option<f32>,
    /// Formula-consistent operational candidate used during development and
    /// frozen before formal execution. This field changes neither the paper
    /// utility nor the best-response acceptance rule.
    pub operational_refinement: String,
    pub observe: String,
}

impl Default for NashProtocolConfig {
    fn default() -> Self {
        Self {
            price_feedback_rate: None,
            quality_weight: None,
            max_inner_rounds: 4,
            max_outer_rounds: 2,
            sa_iterations: 64,
            sa_iterations_per_player: 4,
            queue_normalization_mode: "window_max".to_string(),
            queue_normalizer: None,
            operational_refinement: "ready_finish_tie".to_string(),
            observe: "summary".to_string(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct HpaProtocolConfig {
    #[serde(default = "default_hpa_target")]
    pub target_mem_use_rate: f32,
    #[serde(default = "default_hpa_tolerance")]
    pub tolerance: f32,
    #[serde(default = "default_hpa_period")]
    pub check_period_frames: usize,
    #[serde(default = "default_hpa_history")]
    pub careful_down_history: usize,
    pub min_instances: usize,
    /// `None` means one instance per node, i.e. the same capacity-relative
    /// upper-bound rule at every cluster size.
    pub max_instances: Option<usize>,
    pub min_instances_when_pending: usize,
    pub allow_scale_to_zero: bool,
    pub scale_up_placement: String,
}

impl Default for HpaProtocolConfig {
    fn default() -> Self {
        Self {
            target_mem_use_rate: default_hpa_target(),
            tolerance: default_hpa_tolerance(),
            check_period_frames: default_hpa_period(),
            careful_down_history: default_hpa_history(),
            min_instances: 0,
            max_instances: None,
            min_instances_when_pending: 1,
            allow_scale_to_zero: true,
            scale_up_placement: "least_task".to_string(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct NodeProfileConfig {
    /// "homogeneous" or "heterogeneous".
    pub kind: String,
    #[serde(default = "default_node_cpu")]
    pub cpu_mean: f32,
    #[serde(default = "default_node_mem")]
    pub mem_mean: f32,
    /// Coefficients of variation used by the heterogeneous profile.
    pub cpu_cv: f32,
    pub mem_cv: f32,
    /// Clamp sampled capacities to these multiples of their means.
    pub min_factor: f32,
    pub max_factor: f32,
}

impl Default for NodeProfileConfig {
    fn default() -> Self {
        Self {
            kind: "homogeneous".to_string(),
            cpu_mean: default_node_cpu(),
            mem_mean: default_node_mem(),
            cpu_cv: 0.30,
            mem_cv: 0.25,
            min_factor: 0.5,
            max_factor: 1.5,
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct NetworkProfileConfig {
    /// The simulator transfer code interprets this field as MB/s.
    #[serde(default = "default_network_min_mbps")]
    pub min_mbps: f32,
    #[serde(default = "default_network_max_mbps")]
    pub max_mbps: f32,
}

impl Default for NetworkProfileConfig {
    fn default() -> Self {
        Self {
            min_mbps: default_network_min_mbps(),
            max_mbps: default_network_max_mbps(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct WorkloadFrequencyProfileConfig {
    pub schema_version: String,
    pub profile_set_id: String,
    pub profile_id: String,
    pub load: String,
    pub path: String,
    pub sha256: String,
    pub dag_call_frequency_sha256: String,
    pub dag_count: usize,
    pub expected_arrival_rate_rps: f64,
    pub submission_actual_arrival_rate_rps: f64,
    pub request_frequency_scale: f64,
    pub source: serde_json::Value,
}

impl Default for WorkloadFrequencyProfileConfig {
    fn default() -> Self {
        Self {
            schema_version: String::new(),
            profile_set_id: String::new(),
            profile_id: String::new(),
            load: String::new(),
            path: String::new(),
            sha256: String::new(),
            dag_call_frequency_sha256: String::new(),
            dag_count: 0,
            expected_arrival_rate_rps: 0.0,
            submission_actual_arrival_rate_rps: 0.0,
            request_frequency_scale: 0.0,
            source: serde_json::Value::Null,
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct WorkloadConfig {
    /// "generated", "capture", or "replay".
    pub mode: String,
    pub tape_path: String,
    #[serde(default = "default_arrival_horizon")]
    pub arrival_horizon_frames: usize,
    #[serde(default = "default_load_scale")]
    pub load_scale: f32,
    /// "steady", "spike_5x_50ms", "sustained_3x_200ms", or
    /// "pulse_4x_4_50ms".
    pub burst_profile: String,
    pub frequency_profile: WorkloadFrequencyProfileConfig,
}

impl Default for WorkloadConfig {
    fn default() -> Self {
        Self {
            mode: "generated".to_string(),
            tape_path: String::new(),
            arrival_horizon_frames: default_arrival_horizon(),
            load_scale: default_load_scale(),
            burst_profile: "steady".to_string(),
            frequency_profile: WorkloadFrequencyProfileConfig::default(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct QosConfig {
    pub enabled: bool,
    /// `balanced` assigns the three classes evenly.  The `all_*` variants
    /// support isolated SLA-calibration pilots.
    #[serde(default = "default_qos_class_assignment")]
    pub class_assignment: String,
    #[serde(default = "default_qos_latency_weight")]
    pub latency_weight: f32,
    #[serde(default = "default_qos_throughput_weight")]
    pub throughput_weight: f32,
    #[serde(default = "default_qos_cost_weight")]
    pub cost_weight: f32,
    /// Frozen by the pre-registered pilot; `None` means that the corresponding
    /// SLA is not claimed for this run.
    pub latency_deadline_ms: Option<f32>,
    pub throughput_target_rps: Option<f32>,
    pub cost_budget_per_request: Option<f32>,
}

impl Default for QosConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            class_assignment: default_qos_class_assignment(),
            latency_weight: default_qos_latency_weight(),
            throughput_weight: default_qos_throughput_weight(),
            cost_weight: default_qos_cost_weight(),
            latency_deadline_ms: None,
            throughput_target_rps: None,
            cost_budget_per_request: None,
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug, Default)]
#[serde(default)]
pub struct AblationConfig {
    pub no_heterogeneity: bool,
    pub no_externality: bool,
    pub no_pricing: bool,
    pub no_coordination: bool,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct ReferenceConfig {
    /// "sa_fallback" is retained for smoke/debug; formal coordinated runs use
    /// "build" followed by "offline_required".  The `no_coordination`
    /// ablation uses "not_required" because it never evaluates Eq. (19).
    pub mode: String,
    pub table_path: String,
    pub build_output_path: String,
}

impl Default for ReferenceConfig {
    fn default() -> Self {
        Self {
            mode: "sa_fallback".to_string(),
            table_path: String::new(),
            build_output_path: String::new(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
pub struct ExperimentOutputConfig {
    pub enabled: bool,
    pub root: String,
    pub request_events: bool,
    pub window_events: bool,
}

impl Default for ExperimentOutputConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            root: "reviewer_records".to_string(),
            request_events: true,
            window_events: true,
        }
    }
}

// 存储应用配置信息
#[derive(Serialize, Deserialize, Clone)]
pub struct APPConfig {
    // 应用的数量
    pub app_cnt: usize,
    // 表示请求频率
    pub request_freq: String,
    /// dag type: single, chain, dag
    pub dag_type: String,
    /// cold start: high, low, mix
    /// 冷启动情况
    pub cold_start: String,
    /// cpu, memory,datasize
    // pub fn_cpu: String,
    // pub fn_mem: String,
    // pub fn_data: String,
    // 函数的CPU、内存和数据大小需求
    pub fn_cpu: f32,
    pub fn_mem: f32,
    pub fn_data: f32,
    /// is time sensitive app=1
    pub app_is_sens: bool,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct Config {
    /// for the different algos, should use the same seed
    pub rand_seed: String,
    pub total_frame: usize,
    /// low middle high
    pub request_freq: String,
    /// dag type: single, chain, dag, mix
    pub dag_type: String,
    /// cold start: high, low, mix
    pub cold_start: String,
    /// cpu, data, mix
    pub fn_type: String,
    /// each stage control algorithm settings
    pub no_mech_latency: bool,
    // pub app_types: Vec<APPConfig>,
    pub mech: MechConfig,
    /// whether to log the resultz
    pub no_log: bool,
    #[serde(default)]
    pub experiment: ExperimentConfig,
}

impl Config {
    pub fn new_test() -> Config {
        Config {
            total_frame: 100,
            rand_seed: "test".to_string(),
            request_freq: "low".to_string(),
            dag_type: "single".to_string(),
            cold_start: "high".to_string(),
            fn_type: "cpu".to_string(),
            mech: MechConfig::new_test(),
            no_mech_latency: true,
            no_log: true,
            experiment: ExperimentConfig::default(),
        }
    }

    pub fn workload_seed(&self) -> &str {
        if self.experiment.workload_seed.is_empty() {
            &self.rand_seed
        } else {
            &self.experiment.workload_seed
        }
    }

    pub fn topology_seed(&self) -> &str {
        if self.experiment.topology_seed.is_empty() {
            self.workload_seed()
        } else {
            &self.experiment.topology_seed
        }
    }

    pub fn algorithm_seed(&self) -> &str {
        if self.experiment.algorithm_seed.is_empty() {
            self.workload_seed()
        } else {
            &self.experiment.algorithm_seed
        }
    }

    pub fn validate_experiment(&self) -> Result<(), String> {
        let experiment = &self.experiment;
        let finite_positive = |name: &str, value: f32| {
            if value.is_finite() && value > 0.0 {
                Ok(())
            } else {
                Err(format!("{name} must be finite and positive"))
            }
        };
        if experiment.node_count == 0 {
            return Err("experiment.node_count must be positive".to_string());
        }
        if !matches!(
            experiment.node_profile.kind.as_str(),
            "homogeneous" | "heterogeneous"
        ) {
            return Err("node_profile.kind must be homogeneous or heterogeneous".to_string());
        }
        finite_positive("node_profile.cpu_mean", experiment.node_profile.cpu_mean)?;
        finite_positive("node_profile.mem_mean", experiment.node_profile.mem_mean)?;
        if !experiment.node_profile.cpu_cv.is_finite()
            || experiment.node_profile.cpu_cv < 0.0
            || !experiment.node_profile.mem_cv.is_finite()
            || experiment.node_profile.mem_cv < 0.0
        {
            return Err(
                "node profile coefficients of variation must be finite and nonnegative".to_string(),
            );
        }
        if !(experiment.node_profile.min_factor.is_finite()
            && experiment.node_profile.max_factor.is_finite()
            && experiment.node_profile.min_factor > 0.0
            && experiment.node_profile.max_factor >= experiment.node_profile.min_factor)
        {
            return Err("node profile clamp factors are invalid".to_string());
        }
        finite_positive(
            "network_profile.min_mbps",
            experiment.network_profile.min_mbps,
        )?;
        if !(experiment.network_profile.max_mbps.is_finite()
            && experiment.network_profile.max_mbps > experiment.network_profile.min_mbps)
        {
            return Err("network_profile.max_mbps must exceed min_mbps".to_string());
        }
        if !(experiment.hpa.target_mem_use_rate.is_finite()
            && experiment.hpa.target_mem_use_rate > 0.0
            && experiment.hpa.target_mem_use_rate <= 1.0)
        {
            return Err("hpa.target_mem_use_rate must be in (0, 1]".to_string());
        }
        if !(experiment.hpa.tolerance.is_finite()
            && experiment.hpa.tolerance >= 0.0
            && experiment.hpa.tolerance < 1.0)
        {
            return Err("hpa.tolerance must be in [0, 1)".to_string());
        }
        if experiment.hpa.check_period_frames == 0 || experiment.hpa.careful_down_history == 0 {
            return Err("HPA periods/history must be positive".to_string());
        }
        if experiment.hpa.max_instances == Some(0) {
            return Err("hpa.max_instances must be positive when specified".to_string());
        }
        if experiment.hpa.max_instances.is_some_and(|maximum| {
            experiment.hpa.min_instances > maximum
                || experiment.hpa.min_instances_when_pending > maximum
        }) {
            return Err("HPA minimum instances exceed the configured maximum".to_string());
        }
        if experiment.hpa.allow_scale_to_zero && experiment.hpa.min_instances > 0 {
            return Err("allow_scale_to_zero conflicts with hpa.min_instances > 0".to_string());
        }
        if experiment.hpa.scale_up_placement != "least_task" {
            return Err(
                "the reviewer protocol requires HPA scale_up_placement=least_task".to_string(),
            );
        }
        if experiment.workload.arrival_horizon_frames == 0
            || !experiment.workload.load_scale.is_finite()
            || experiment.workload.load_scale <= 0.0
        {
            return Err("workload horizon and scale are invalid".to_string());
        }
        if !matches!(
            experiment.workload.burst_profile.as_str(),
            "steady" | "spike_5x_50ms" | "sustained_3x_200ms" | "pulse_4x_4_50ms"
        ) {
            return Err("unsupported workload burst_profile".to_string());
        }
        if !matches!(
            experiment.workload.mode.as_str(),
            "generated" | "capture" | "replay"
        ) {
            return Err("workload.mode must be generated, capture, or replay".to_string());
        }
        if experiment.workload.mode == "replay" && experiment.workload.tape_path.is_empty() {
            return Err("workload replay requires tape_path".to_string());
        }
        for (name, weight) in [
            ("latency", experiment.qos.latency_weight),
            ("throughput", experiment.qos.throughput_weight),
            ("cost", experiment.qos.cost_weight),
        ] {
            if !weight.is_finite() || !(0.0..=1.0).contains(&weight) {
                return Err(format!("QoS {name} weight must be in [0, 1]"));
            }
        }
        if !matches!(
            experiment.qos.class_assignment.as_str(),
            "balanced" | "all_latency" | "all_throughput" | "all_cost"
        ) {
            return Err(
                "qos.class_assignment must be balanced, all_latency, all_throughput, or all_cost"
                    .to_string(),
            );
        }
        for (name, value) in [
            ("latency_deadline_ms", experiment.qos.latency_deadline_ms),
            (
                "throughput_target_rps",
                experiment.qos.throughput_target_rps,
            ),
            (
                "cost_budget_per_request",
                experiment.qos.cost_budget_per_request,
            ),
        ] {
            if let Some(value) = value {
                if !value.is_finite() || value <= 0.0 {
                    return Err(format!("QoS {name} must be finite and positive"));
                }
            }
        }
        if let Some(value) = experiment.nash.price_feedback_rate {
            if !value.is_finite() || !(0.0..=1.0).contains(&value) {
                return Err("nash.price_feedback_rate must be in [0, 1]".to_string());
            }
        }
        if let Some(value) = experiment.nash.quality_weight {
            if !value.is_finite() || !(0.0..=10.0).contains(&value) {
                return Err("nash.quality_weight must be in [0, 10]".to_string());
            }
        }
        if experiment.nash.max_inner_rounds == 0
            || experiment.nash.max_outer_rounds == 0
            || experiment.nash.sa_iterations == 0
        {
            return Err("NSESche iteration budgets must be positive".to_string());
        }
        match experiment.nash.queue_normalization_mode.as_str() {
            "window_max" => {
                if experiment.nash.queue_normalizer.is_some() {
                    return Err(
                        "nash.queue_normalizer must be null when queue_normalization_mode=window_max"
                            .to_string(),
                    );
                }
            }
            "fixed" => {
                if !experiment
                    .nash
                    .queue_normalizer
                    .is_some_and(|value| value.is_finite() && value > 0.0)
                {
                    return Err(
                        "nash.queue_normalizer must be finite and positive when queue_normalization_mode=fixed"
                            .to_string(),
                    );
                }
            }
            _ => {
                return Err("nash.queue_normalization_mode must be window_max or fixed".to_string());
            }
        }
        if !matches!(
            experiment.nash.operational_refinement.as_str(),
            "formula"
                | "ready_order"
                | "ready_finish_tie"
                | "guarded_finish_05"
                | "guarded_finish_15"
                | "guarded_dynamic_finish_05"
                | "guarded_dynamic_finish_15"
        ) {
            return Err(
                "nash.operational_refinement must be formula, ready_order, ready_finish_tie, guarded_finish_05, guarded_finish_15, guarded_dynamic_finish_05, or guarded_dynamic_finish_15".to_string(),
            );
        }
        if !matches!(
            experiment.nash.observe.as_str(),
            "off" | "summary" | "detail"
        ) {
            return Err("nash.observe must be off, summary, or detail".to_string());
        }
        if !matches!(
            experiment.reference.mode.as_str(),
            "sa_fallback" | "build" | "offline_required" | "not_required"
        ) {
            return Err(
                "reference.mode must be sa_fallback, build, offline_required, or not_required"
                    .to_string(),
            );
        }
        if experiment.reference.mode == "not_required" && !experiment.ablation.no_coordination {
            return Err(
                "reference.mode=not_required is only valid when Nash-social coordination is disabled"
                    .to_string(),
            );
        }
        if experiment.reference.mode == "offline_required"
            && experiment.reference.table_path.is_empty()
        {
            return Err("offline_required reference mode needs table_path".to_string());
        }
        if experiment.output.enabled {
            if self.total_frame < experiment.workload.arrival_horizon_frames {
                return Err("total_frame must cover the workload arrival horizon".to_string());
            }
            if experiment.run_id.is_empty()
                || experiment.workload_seed.is_empty()
                || experiment.topology_seed.is_empty()
                || experiment.algorithm_seed.is_empty()
            {
                return Err(
                    "formal output requires run_id and all three explicit seeds".to_string()
                );
            }
            if experiment.protocol_version != "reviewer-v3" {
                return Err(
                    "formal output requires experiment.protocol_version=reviewer-v3".to_string(),
                );
            }
            let profile = &experiment.workload.frequency_profile;
            if profile.schema_version != "NSE_WORKLOAD_FREQUENCY_PROFILE_V1"
                || profile.profile_set_id != "submission-era-azure-cdf-v1"
                || profile.profile_id.is_empty()
                || profile.path.is_empty()
                || profile.load != self.request_freq
                || profile.dag_count != 50
                || !is_sha256_hex(&profile.sha256)
                || !is_sha256_hex(&profile.dag_call_frequency_sha256)
                || !profile.expected_arrival_rate_rps.is_finite()
                || profile.expected_arrival_rate_rps <= 0.0
                || !profile.submission_actual_arrival_rate_rps.is_finite()
                || profile.submission_actual_arrival_rate_rps <= 0.0
                || !profile.request_frequency_scale.is_finite()
                || profile.request_frequency_scale <= 0.0
                || !profile.source.is_object()
            {
                return Err(
                    "formal output requires a complete frozen workload frequency profile"
                        .to_string(),
                );
            }
            let expected_scale = if self.request_freq_low() {
                0.2
            } else if self.request_freq_middle() {
                0.6
            } else if self.request_freq_high() {
                1.4
            } else {
                return Err("formal request_freq must be low, middle, or high".to_string());
            };
            if (profile.request_frequency_scale - expected_scale).abs() > f64::EPSILON {
                return Err("frozen workload profile scale does not match request_freq".to_string());
            }
            if !experiment
                .run_id
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || "-_.".contains(character))
            {
                return Err(
                    "run_id may contain only ASCII letters, digits, '-', '_' and '.'".to_string(),
                );
            }
            if experiment.output.root.trim().is_empty() {
                return Err("experiment.output.root cannot be empty".to_string());
            }
            if !self.no_mech_latency {
                return Err("formal common-runtime runs require no_mech_latency=true".to_string());
            }
            if self.mech.mech_type().0 != "scale_sche_separated"
                || self.mech.scale_num_conf().0 != "hpa"
                || self.mech.scale_down_exec_conf().0 != "default"
                || self.mech.scale_up_exec_conf().0 != "least_task"
                || self.mech.instance_cache_policy_conf().0 != "no_evict"
                || self
                    .mech
                    .filter
                    .get("careful_down")
                    .and_then(|value| value.as_ref())
                    .is_none()
            {
                return Err(
                    "formal runs require separated scheduling with common HPA/default/least_task/careful_down/no_evict"
                        .to_string(),
                );
            }
            if self.mech.sche_conf().0 == "sche_FaaSRank" {
                let model = &experiment.faasrank_model;
                if model.state != "frozen" {
                    return Err(
                        "formal FaaSRank-P runs require faasrank_model.state=frozen".to_string()
                    );
                }
                if !is_sha256_hex(&model.model_sha256) {
                    return Err(
                        "formal FaaSRank-P runs require a 64-character hexadecimal model_sha256"
                            .to_string(),
                    );
                }
                if model.training_tape_sha256.is_empty() {
                    return Err(
                        "formal FaaSRank-P runs require a non-empty training_tape_sha256"
                            .to_string(),
                    );
                }
                if !is_sha256_hex(&model.training_tape_sha256) {
                    return Err(
                        "formal FaaSRank-P runs require a 64-character hexadecimal training_tape_sha256"
                            .to_string(),
                    );
                }
                for (name, value) in [
                    ("cpu_headroom", model.cpu_headroom),
                    ("memory_headroom", model.memory_headroom),
                    ("network_locality", model.network_locality),
                    ("warm_affinity", model.warm_affinity),
                    ("load_balance", model.load_balance),
                    ("diversity_penalty", model.diversity_penalty),
                ] {
                    if !value.is_finite() {
                        return Err(format!(
                            "formal FaaSRank-P coefficient {name} must be finite"
                        ));
                    }
                }
                if !model.epsilon.is_finite() || !(0.0..=1.0).contains(&model.epsilon) {
                    return Err(
                        "formal FaaSRank-P epsilon must be finite and in [0, 1]".to_string()
                    );
                }
            }
        }
        Ok(())
    }

    pub fn request_freq_low(&self) -> bool {
        if &*self.request_freq == "low" {
            return true;
        }
        false
    }
    pub fn request_freq_middle(&self) -> bool {
        if &*self.request_freq == "middle" {
            return true;
        }
        false
    }
    pub fn request_freq_high(&self) -> bool {
        if &*self.request_freq == "high" {
            return true;
        }
        false
    }

    pub fn dag_type_single(&self) -> bool {
        if &*self.dag_type == "single" {
            return true;
        }
        false
    }

    pub fn dag_type_dag(&self) -> bool {
        if &*self.dag_type == "dag" {
            return true;
        }
        false
    }

    pub fn dag_type_mix(&self) -> bool {
        if &*self.dag_type == "mix" {
            return true;
        }
        false
    }

    pub fn fntype_cpu(&self) -> bool {
        if &*self.fn_type == "cpu" {
            return true;
        }
        false
    }

    pub fn fntype_data(&self) -> bool {
        if &*self.fn_type == "data" {
            return true;
        }
        false
    }

    // pub fn check_valid(&self) {
    //     match &*self.request_freq {
    //         "low" | "middle" | "high" => {}
    //         _ => panic!("request_freq should be low, middle or high"),
    //     }
    //     match &*self.dag_type {
    //         "single" | "chain" | "dag" | "mix" => {}
    //         _ => panic!("dag_type should be single, chain, dag or mix"),
    //     }
    //     match &*self.cold_start {
    //         "high" | "low" | "mix" => {}
    //         _ => panic!("cold_start should be high, low or mix"),
    //     }
    //     match &*self.fn_type {
    //         "cpu" | "data" | "mix" => {}
    //         _ => panic!("fn_type should be cpu, data or mix"),
    //     }
    //     match &*self.es.up {
    //         // "ai","lass","fnsche","hpa","faasflow"
    //         "lass" | "ai" | "fnsche" | "hpa" | "faasflow" => {}
    //         _ => panic!("ef.up should be lass, ai, fnsche, hpa or faasflow"),
    //     }
    //     match &*self.es.down {
    //         // "ai","lass","fnsche","hpa","faasflow"
    //         "lass" | "ai" | "fnsche" | "hpa" | "faasflow" => {}
    //         _ => panic!("ef.down should be lass, ai, fnsche, hpa or faasflow"),
    //     }
    //     match &*self.es.sche {
    //         "rule" | "ai" | "faasflow" | "fnsche" | "rule_prewarm_succ" | "random"
    //         | "round_robin" | "load_least" | "gofs" | "pass" => {}
    //         _ => panic!("ef.sche should be rule, ai, faasflow or fnsche"),
    //     }
    //     match &*self.es.down_smooth {
    //         "direct" | "smooth_30" | "smooth_100" => {}
    //         _ => panic!("ef.down_smooth should be direct, smooth_30 or smooth_100"),
    //     }
    //     if self.es.sche_ai() {
    //         match &**self.es.ai_type.as_ref().unwrap() {
    //             "sac" | "ppo" | "mat" => {}
    //             _ => panic!("ef.ai_type should be sac, ppo or mat"),
    //         }
    //     }
    // }
    pub fn no_mech_str(&self) -> String {
        format!(
            "sd{}.rf{}.dt{}.cs{}.ft{}",
            self.workload_seed(),
            self.request_freq,
            self.dag_type,
            self.cold_start,
            self.fn_type
        )
    }
    pub fn str(&self) -> String {
        let scnum = self.mech.scale_num_conf();
        let scdown = self.mech.scale_down_exec_conf();
        let scup = self.mech.scale_up_exec_conf();
        let sche = self.mech.sche_conf();
        let ins_cache = self.mech.instance_cache_policy_conf();
        let mut some_filter = self
            .mech
            .filter
            .iter()
            .filter(|v| v.1.is_some())
            .map(|v| (v.0, v.1.clone().unwrap()))
            .collect::<Vec<_>>();
        some_filter.sort();
        let some_filter = some_filter
            .iter()
            .map(|v| format!("({}.{})", v.0, v.1))
            .collect::<String>();
        // .join(",");
        let legacy_key = format!(
            "sd{}.rf{}.dt{}.cs{}.ft{}.nml{}.mt{}.scl({}.{})({}.{})({}.{})[{}].scd({}.{}).ic({}.{})",
            self.rand_seed,
            self.request_freq,
            self.dag_type,
            self.cold_start,
            self.fn_type,
            if self.no_mech_latency { 1 } else { 0 },
            self.mech.mech_type().0,
            scnum.0,
            scnum.1,
            scdown.0,
            scdown.1,
            scup.0,
            scup.1,
            some_filter,
            sche.0,
            sche.1,
            ins_cache.0,
            ins_cache.1
        );
        if self.experiment.run_id.is_empty() {
            legacy_key
        } else {
            format!("{legacy_key}.run{}", self.experiment.run_id)
        }
    }
}
