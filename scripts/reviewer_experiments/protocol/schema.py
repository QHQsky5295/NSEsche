from __future__ import annotations

import copy
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .util import object_hash, read_json


class ProtocolValidationError(ValueError):
    """Raised when a protocol configuration or manifest violates an invariant."""


SEED_RE = re.compile(r"^(?:E|D)\d{2}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
FORMAL_PROTOCOL_ID = "tsc-reviewer-common-hpa-v4-tscv1-fixed20"
FIXED_SAMPLE_POLICY = "paired_fixed_n20_split_into_two_execution_banks_only"
M1_DEVELOPMENT_SAMPLE_POLICY = "paired_fixed_m1_development_n20_no_formal_reuse"
M1_DEVELOPMENT_SEEDS = tuple(f"D{index:02d}" for index in range(1, 21))
M1_GUARD_SAMPLE_POLICY = (
    "paired_fixed_m1_guard_n20_no_formal_or_prior_development_reuse"
)
M1_GUARD_SEEDS = tuple(f"D{index:02d}" for index in range(21, 41))
M1_GUARD_MARKERS = (
    "m1_completion_guard_matrix",
    "m1_completion_guard_screen_shard",
    "m1_completion_guard_qualification_shard",
)
M1_DYNAMIC_SAMPLE_POLICY = (
    "paired_fixed_m1_dynamic_contention_n20_no_prior_or_formal_reuse"
)
M1_DYNAMIC_SEEDS = tuple(f"D{index:02d}" for index in range(41, 61))
M1_DYNAMIC_MARKERS = (
    "m1_dynamic_contention_matrix",
    "m1_dynamic_contention_screen_shard",
    "m1_dynamic_contention_qualification_shard",
)
G1_CORRECTED_TECHNICAL_SAMPLE_POLICY = (
    "fixed_g1_corrected_runtime_technical_d44_no_selection_or_formal_use"
)
G1_CORRECTED_TECHNICAL_SEEDS = ("D44",)
G1_CORRECTED_SCREEN_SAMPLE_POLICY = (
    "paired_fixed_g1_corrected_runtime_screen_d61_d65_no_formal_reuse"
)
G1_CORRECTED_SCREEN_SEEDS = tuple(f"D{index:02d}" for index in range(61, 66))
G1_CORRECTED_MARKERS = (
    "g1_corrected_runtime_technical_replay",
    "g1_corrected_runtime_screen",
)
M1_RUNTIME_BOUND_MARKERS = (
    *M1_GUARD_MARKERS,
    *M1_DYNAMIC_MARKERS,
    *G1_CORRECTED_MARKERS,
)
M1_NONFORMAL_MARKERS = (
    "m1_development_matrix",
    "m1_candidate_screen_shard",
    "m1_qualification_shard",
    "m1_mechanism_diagnosis_shard",
    *M1_GUARD_MARKERS,
    *M1_DYNAMIC_MARKERS,
    *G1_CORRECTED_MARKERS,
)
FORMAL_BANK_IDS = {
    "initial": "TSCv1.formal.bank-A.E01-E10",
    "ci_extension": "TSCv1.formal.bank-B.E11-E20",
    "all": "TSCv1.formal.bank-AB.E01-E20",
}
FORMAL_METHOD_VERSIONS = {
    "greedy": "baseline-implementation-v1",
    "random": "baseline-implementation-v1",
    "hash": "baseline-implementation-v1",
    "load_least": "baseline-implementation-v1",
    "sche_FaaSRank": "frozen-model-baseline-v1",
    "sche_OCS": "baseline-implementation-v1",
    "sche_Hiku": "baseline-implementation-v1",
    "sche_jiagu": "baseline-implementation-v1",
    "sche_orion": "baseline-implementation-v1",
    "sche_nash": "formula-consistent-operational-v2-reference-key-v10",
    "cp_br": "welfare-comparator-v1",
    "onsocmax": "welfare-comparator-v1",
}
OLD_PDF_ALIGNMENT = {
    "version": "5-12V2-TSC-NSESche-Complete-IEEE",
    "filename": "（5-12V2）TSC_NSESche_Complete_IEEE_.pdf",
    "sha256": "03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18",
}
RUNTIME_IDENTITY_POLICY = {
    "git_commit": "bound_and_verified_in_each_run_audit_manifest",
    "binary_sha256": "bound_and_verified_in_each_run_audit_manifest",
}

FORMAL_E1_METHODS = (
    "greedy",
    "random",
    "hash",
    "load_least",
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
    "sche_nash",
)
FORMAL_E1_LOADS = ("low", "middle", "high")
FORMAL_E1_SEEDS_BY_STAGE = {
    "initial": tuple(f"E{index:02d}" for index in range(1, 11)),
    "ci_extension": tuple(f"E{index:02d}" for index in range(11, 21)),
    "all": tuple(f"E{index:02d}" for index in range(1, 21)),
}
FORMAL_SHARD_MARKERS = (
    "formal_e1_homogeneous_shard",
    "formal_e1_heterogeneous_shard",
    "formal_e2_weak_scaling_shard",
    "formal_e3_e4_initial_shard",
    "formal_e3_e4_ci_extension_shard",
    "formal_e5_e6_e7_initial_shard",
    "formal_e5_e6_ci_extension_shard",
)
FULL_MATRIX_RUN_COUNTS_BY_STAGE = {
    "initial": {
        "E1": 600,
        "E2": 600,
        "E3": 300,
        "E4": 100,
        "E5": 120,
        "E6": 40,
        "E7": 120,
    },
    "ci_extension": {
        "E1": 600,
        "E2": 600,
        "E3": 300,
        "E4": 100,
        "E5": 120,
        "E6": 40,
        "E7": 120,
    },
    "all": {
        "E1": 1200,
        "E2": 1200,
        "E3": 600,
        "E4": 200,
        "E5": 240,
        "E6": 80,
        "E7": 240,
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _validate_analysis_reuse_rules(value: Any, *, formal_required: bool = True) -> None:
    """Validate the sealed, executable contract for analysis-only reuse."""

    _require(isinstance(value, list), "reuse_analyses must be an array")
    rule_ids: set[str] = set()
    reuse_targets: set[str] = set()
    for index, entry in enumerate(value):
        prefix = f"reuse_analyses[{index}]"
        _require(isinstance(entry, dict), f"{prefix} must be an object")
        _require(
            entry.get("schema_version") == "NSE_ANALYSIS_REUSE_RULE_V1",
            f"{prefix} has unsupported schema_version",
        )
        rule_id = entry.get("rule_id")
        _require(
            isinstance(rule_id, str) and bool(rule_id),
            f"{prefix}.rule_id must be a non-empty string",
        )
        _require(rule_id not in rule_ids, f"duplicate reuse rule_id {rule_id}")
        rule_ids.add(rule_id)
        rule_sha256 = entry.get("rule_sha256")
        _require(
            isinstance(rule_sha256, str) and HASH_RE.fullmatch(rule_sha256) is not None,
            f"{prefix}.rule_sha256 must be a SHA-256 digest",
        )
        _require(
            _hash_without(entry, "rule_sha256") == rule_sha256,
            f"{prefix}.rule_sha256 does not match rule content",
        )

        kind = entry.get("kind")
        experiment_id = entry.get("experiment_id")
        _require(
            kind in {"reuse_cells", "analysis_only"},
            f"{prefix}.kind is unsupported",
        )
        if kind == "reuse_cells":
            _require(
                experiment_id in {"E2", "E5", "E6", "E7"},
                f"{prefix} has unsupported reuse target",
            )
            _require(
                entry.get("source_experiment_id") == "E1",
                f"{prefix} must reuse a formal E1 source",
            )
            _require(
                isinstance(entry.get("source_selector"), dict)
                and bool(entry["source_selector"]),
                f"{prefix}.source_selector must be a non-empty object",
            )
            compatibility = entry.get("compatibility")
            _require(
                isinstance(compatibility, dict),
                f"{prefix}.compatibility must be an object",
            )
            _require(
                compatibility.get("workload_transform") == "identity"
                and compatibility.get("cluster_transform") == "identity",
                f"{prefix} may only project identity workload/cluster specifications",
            )
            _require(
                isinstance(compatibility.get("required_exact"), dict),
                f"{prefix}.compatibility.required_exact must be an object",
            )
            required_hashes = compatibility.get("required_hash_fields")
            _require(
                isinstance(required_hashes, list)
                and {
                    "run_spec_hash",
                    "workload_spec_hash",
                    "common_hpa_hash",
                }.issubset(set(required_hashes)),
                f"{prefix} must preserve all source provenance hashes",
            )
            projection = entry.get("target_projection")
            _require(
                isinstance(projection, dict)
                and isinstance(projection.get("cell_id_template"), str)
                and bool(projection["cell_id_template"])
                and isinstance(projection.get("scenario"), str),
                f"{prefix}.target_projection is incomplete",
            )
            reuse_targets.add(str(experiment_id))
        else:
            _require(
                experiment_id in {"E8", "E9"},
                f"{prefix} has unsupported analysis-only target",
            )
            _require(
                entry.get("produces_runs") is False,
                f"{prefix} must declare produces_runs=false",
            )
            _require(
                isinstance(entry.get("source_experiment_ids"), list),
                f"{prefix}.source_experiment_ids must be an array",
            )

    if formal_required:
        _require(
            reuse_targets == {"E2", "E5", "E6", "E7"},
            "reuse_analyses must declare E2/E5/E6/E7 materialization rules",
        )


def _validate_simulation(simulation: Any, prefix: str) -> None:
    _require(isinstance(simulation, dict), f"{prefix} must be an object")
    total_frame = simulation.get("total_frame")
    expected_final_frame = simulation.get("expected_final_frame")
    expected_frame_count = simulation.get("expected_frame_count")
    arrival_horizon = simulation.get("arrival_horizon_frames")
    observation_horizon = simulation.get("observation_horizon_frames")
    for name, value in (
        ("total_frame", total_frame),
        ("expected_final_frame", expected_final_frame),
        ("expected_frame_count", expected_frame_count),
        ("arrival_horizon_frames", arrival_horizon),
        ("observation_horizon_frames", observation_horizon),
    ):
        _require(
            isinstance(value, int) and not isinstance(value, bool),
            f"{prefix}.{name} must be an integer",
        )
    _require(total_frame >= 0, f"{prefix}.total_frame must not be negative")
    _require(
        expected_final_frame == total_frame,
        f"{prefix}.expected_final_frame must equal total_frame",
    )
    _require(
        expected_frame_count == total_frame + 1,
        f"{prefix}.expected_frame_count must equal total_frame + 1",
    )
    _require(
        0 <= arrival_horizon <= total_frame,
        f"{prefix}.arrival_horizon_frames must be between zero and total_frame",
    )
    _require(
        0 < observation_horizon <= total_frame,
        f"{prefix}.observation_horizon_frames must be positive and no greater than total_frame",
    )
    _require(
        arrival_horizon == observation_horizon,
        f"{prefix}.arrival_horizon_frames must equal observation_horizon_frames for the fixed arrival cohort",
    )
    duration = simulation.get("frame_duration_seconds")
    _require(
        isinstance(duration, (int, float))
        and not isinstance(duration, bool)
        and float(duration) == 0.001,
        f"{prefix}.frame_duration_seconds must equal 0.001",
    )


def _validate_workload_profile_set(value: Any, expected_hash: Any) -> dict[str, Any]:
    from .workload_profile import (
        CANONICAL_PROFILES,
        CANONICAL_PROFILE_SET_ID,
        PROFILE_LOADS,
        PROFILE_SCHEMA,
        PROFILE_SET_SCHEMA,
        load_frozen_workload_profile,
    )

    _require(isinstance(value, dict), "workload_profile_set must be an object")
    _require(
        value.get("schema_version") == PROFILE_SET_SCHEMA,
        "workload_profile_set schema is unsupported",
    )
    _require(
        value.get("profile_set_id") == CANONICAL_PROFILE_SET_ID,
        "workload_profile_set id is invalid",
    )
    _require(
        value.get("formal_required") is True,
        "workload_profile_set must be required for formal runs",
    )
    _require(
        isinstance(expected_hash, str)
        and HASH_RE.fullmatch(expected_hash) is not None
        and object_hash(value) == expected_hash,
        "workload_profile_set_hash does not match its content",
    )
    profiles = value.get("profiles")
    _require(
        isinstance(profiles, dict) and set(profiles) == set(PROFILE_LOADS),
        "workload_profile_set must contain low/middle/high exactly",
    )
    for load in PROFILE_LOADS:
        binding = profiles[load]
        prefix = f"workload_profile_set.profiles.{load}"
        _require(isinstance(binding, dict), f"{prefix} must be an object")
        _require(
            binding.get("schema_version") == PROFILE_SCHEMA,
            f"{prefix} schema is invalid",
        )
        _require(
            binding.get("load") == load,
            f"{prefix} load does not match its key",
        )
        for field in (
            "profile_set_id",
            "profile_id",
            "path",
            "sha256",
            "dag_call_frequency_sha256",
            "dag_count",
            "expected_arrival_rate_rps",
            "submission_actual_arrival_rate_rps",
            "request_frequency_scale",
            "source",
        ):
            _require(field in binding, f"{prefix} is missing {field}")
        _require(
            binding["profile_set_id"] == value["profile_set_id"],
            f"{prefix} profile_set_id mismatch",
        )
        loaded = load_frozen_workload_profile(
            Path(binding["path"]),
            expected_sha256=binding["sha256"],
            expected_load=load,
            expected_profile_id=binding["profile_id"],
            expected_profile_set_id=binding["profile_set_id"],
            expected_frequency_sha256=binding["dag_call_frequency_sha256"],
        )
        _require(
            loaded.to_binding() == binding,
            f"{prefix} differs from its immutable artifact",
        )
        canonical = CANONICAL_PROFILES[load]
        _require(
            binding["sha256"] == canonical["sha256"]
            and binding["profile_id"] == canonical["profile_id"]
            and binding["dag_call_frequency_sha256"]
            == canonical["dag_call_frequency_sha256"]
            and binding["expected_arrival_rate_rps"]
            == canonical["expected_arrival_rate_rps"]
            and binding["submission_actual_arrival_rate_rps"]
            == canonical["submission_actual_arrival_rate_rps"],
            f"{prefix} is not the frozen canonical artifact",
        )
    return profiles


def _validate_qc_policy(qc: Any, prefix: str) -> None:
    """Freeze technical QC without introducing outcome-based acceptance gates."""

    _require(isinstance(qc, dict), f"{prefix} must be an object")
    _require(
        qc.get("format") == "nse_reviewer_v1",
        f"{prefix}.format must be nse_reviewer_v1",
    )
    _require(
        qc.get("require_provenance") is True,
        f"{prefix}.require_provenance must be true",
    )
    for field in (
        "required_finite_metrics",
        "required_positive_metrics",
        "allowed_null_metrics",
        "allowed_zero_metrics",
        "stderr_failure_patterns",
    ):
        values = qc.get(field)
        _require(
            isinstance(values, list)
            and all(isinstance(value, str) and value for value in values),
            f"{prefix}.{field} must be a string array",
        )
        _require(
            len(values) == len(set(values)),
            f"{prefix}.{field} must not contain duplicates",
        )
    _require(
        qc["required_finite_metrics"] == [],
        f"{prefix}.required_finite_metrics must stay empty; NSE_SUMMARY_V1 fields are validated conditionally",
    )
    _require(
        qc["required_positive_metrics"] == [],
        f"{prefix}.required_positive_metrics must stay empty so scientific zero outcomes remain valid",
    )

    artifacts = qc.get("jsonl_artifacts")
    _require(isinstance(artifacts, dict), f"{prefix}.jsonl_artifacts must be an object")
    _require(
        artifacts.get("required") is True,
        f"{prefix}.jsonl_artifacts.required must be true",
    )
    _require(
        artifacts.get("require_completed_event") is False,
        f"{prefix}.jsonl_artifacts.require_completed_event must be false; completion is bound by summary.run_complete",
    )
    maximum_line_bytes = artifacts.get("max_line_bytes")
    _require(
        isinstance(maximum_line_bytes, int)
        and not isinstance(maximum_line_bytes, bool)
        and maximum_line_bytes > 0,
        f"{prefix}.jsonl_artifacts.max_line_bytes must be a positive integer",
    )

    contract = qc.get("nse_summary_contract")
    _require(
        isinstance(contract, dict), f"{prefix}.nse_summary_contract must be an object"
    )
    _require(
        contract.get("schema") == "NSE_SUMMARY_V1",
        f"{prefix}.nse_summary_contract.schema must be NSE_SUMMARY_V1",
    )
    expected_cohort_metric_contract = {
        "fixed_observation_window": "throughput counts cohort completions at or before observation_horizon_frames and divides by that fixed duration",
        "drained_arrival_cohort": "completion ratio and latency use requests arriving before observation_horizon_frames, observed through total_frame",
        "throughput_unit": "requests/s",
        "latency_unit": "ms",
    }
    _require(
        contract.get("cohort_metric_contract") == expected_cohort_metric_contract,
        f"{prefix}.nse_summary_contract.cohort_metric_contract is invalid",
    )
    _require(
        contract.get("scientific_zero_completions_are_valid") is True,
        f"{prefix} must preserve zero completions as a valid scientific outcome",
    )
    expected_zero_completion_nulls = {
        "latency_ms.mean",
        "latency_ms.p50",
        "latency_ms.p95",
        "latency_ms.p99",
        "drained_arrival_cohort.latency_ms.mean",
        "drained_arrival_cohort.latency_ms.p50",
        "drained_arrival_cohort.latency_ms.p95",
        "drained_arrival_cohort.latency_ms.p99",
        "simulator_internal_cost_per_completed_request",
    }
    zero_completion_nulls = contract.get("nullable_when_zero_completions")
    _require(
        isinstance(zero_completion_nulls, list)
        and len(zero_completion_nulls) == len(set(zero_completion_nulls))
        and set(zero_completion_nulls) == expected_zero_completion_nulls,
        f"{prefix}.nse_summary_contract has an invalid zero-completion null policy",
    )
    expected_zero_window_nulls = {
        "scheduler_wall_ns",
        "scheduler_thread_cpu_ns",
        "placement_policy_wall_ns",
        "placement_policy_thread_cpu_ns",
        "posthoc_welfare_evaluation_wall_ns",
        "posthoc_welfare_evaluation_thread_cpu_ns",
    }
    zero_window_nulls = contract.get("nullable_when_zero_scheduler_windows")
    _require(
        isinstance(zero_window_nulls, list)
        and len(zero_window_nulls) == len(set(zero_window_nulls))
        and set(zero_window_nulls) == expected_zero_window_nulls,
        f"{prefix}.nse_summary_contract has an invalid zero-window null policy",
    )
    expected_qos_classes = {
        "mixed": ["shared"],
        "balanced": ["latency", "throughput", "cost"],
    }
    _require(
        contract.get("qos_classes_by_profile") == expected_qos_classes,
        f"{prefix}.nse_summary_contract.qos_classes_by_profile is not the frozen Rust class mapping",
    )
    _require(
        contract.get("node_utilization_unit") == "fraction_of_node_capacity",
        f"{prefix}.nse_summary_contract.node_utilization_unit is invalid",
    )
    expected_utilization_definition = {
        "sampling": "one_sample_per_node_per_recorded_frame",
        "cpu_numerator": "node.cpu",
        "cpu_denominator": "node.rsc_limit.cpu",
        "memory_numerator": "node.unready_mem()",
        "memory_denominator": "node.rsc_limit.mem",
        "clipping": "none",
        "invalid_sample_policy": "exclude_non_finite_usage_or_capacity_negative_usage_or_non_positive_capacity",
    }
    _require(
        contract.get("node_utilization_definition") == expected_utilization_definition,
        f"{prefix}.nse_summary_contract.node_utilization_definition is invalid",
    )
    expected_scheduler_timing_definition = {
        "primary_policy_metric": "placement_policy_wall_ns",
        "mechanism_total_metric": "scheduler_wall_ns",
        "posthoc_welfare_excluded_from_policy_boundary": True,
        "policy_time_derived_by_subtraction": False,
    }
    _require(
        contract.get("scheduler_timing_definition")
        == expected_scheduler_timing_definition,
        f"{prefix}.nse_summary_contract.scheduler_timing_definition is invalid",
    )


def validate_protocol_config(config: dict[str, Any]) -> None:
    required = {
        "protocol_id",
        "manifest_governance",
        "methods",
        "seed_policy",
        "common_hpa",
        "simulation",
        "workload_profiles",
        "matrix_defaults",
        "execution",
        "qc",
    }
    missing = sorted(required - config.keys())
    _require(not missing, f"protocol config is missing: {', '.join(missing)}")
    _require(
        config["protocol_id"] == FORMAL_PROTOCOL_ID,
        "protocol_id must identify the frozen workload-profile protocol",
    )
    methods = config["methods"]
    _require(
        isinstance(methods, list) and len(methods) == 10,
        "exactly 10 methods are required",
    )
    _require(len(set(methods)) == len(methods), "methods must be unique")
    _require("sche_nash" in methods, "sche_nash must be one of the methods")

    policy = config["seed_policy"]
    for stage, expected in (
        ("initial", 10),
        ("ci_extension", 10),
        ("e7_initial", 10),
        ("e7_ci_extension", 10),
    ):
        seeds = policy.get(stage)
        _require(
            isinstance(seeds, list) and len(seeds) == expected,
            f"{stage} must contain {expected} seeds",
        )
        _require(len(set(seeds)) == len(seeds), f"{stage} seeds must be unique")
        _require(
            all(isinstance(seed, str) and SEED_RE.fullmatch(seed) for seed in seeds),
            f"invalid {stage} seed",
        )
    _require(
        tuple(policy["initial"]) == FORMAL_E1_SEEDS_BY_STAGE["initial"]
        and tuple(policy["ci_extension"]) == FORMAL_E1_SEEDS_BY_STAGE["ci_extension"],
        "formal seed banks must be exactly E01--E10 and E11--E20",
    )
    _require(
        policy["e7_initial"] == policy["initial"]
        and policy["e7_ci_extension"] == policy["ci_extension"],
        "E7 must use the same fixed 20 paired seeds as every other experiment",
    )
    _require(
        policy.get("ci_extension_requires_trigger") is False,
        "the E11-E20 bank is fixed and must not depend on an observed CI trigger",
    )

    governance = config["manifest_governance"]
    _require(
        isinstance(governance, dict)
        and governance.get("schema_version") == "NSE_TSC_RESUBMISSION_GOVERNANCE_V1",
        "manifest_governance is missing or unsupported",
    )
    _require(governance.get("phase") == "formal", "default phase must be formal")
    _require(
        governance.get("fixed_sample_policy") == FIXED_SAMPLE_POLICY,
        "fixed sample policy must preregister 20 paired observations",
    )
    bank_ids = governance.get("bank_ids")
    _require(
        bank_ids == FORMAL_BANK_IDS,
        "manifest_governance.bank_ids must bind all execution stages",
    )
    method_versions = governance.get("method_versions")
    _require(
        method_versions == FORMAL_METHOD_VERSIONS,
        "manifest_governance.method_versions does not match the frozen methods",
    )
    alignment = governance.get("old_pdf_alignment")
    _require(
        alignment == OLD_PDF_ALIGNMENT,
        "manifest_governance.old_pdf_alignment does not match the frozen manuscript",
    )
    _require(
        governance.get("runtime_identity") == RUNTIME_IDENTITY_POLICY,
        "runtime Git/binary identity policy is not fail-closed",
    )

    execution = config["execution"]
    _require(execution.get("max_attempts") == 3, "max_attempts is fixed at 3")
    _require(
        float(execution.get("timeout_seconds", 0)) > 0,
        "timeout_seconds must be positive",
    )
    command = execution.get("command_template")
    _require(
        isinstance(command, list) and all(isinstance(item, str) for item in command),
        "command_template must be a string array",
    )

    simulation = config["simulation"]
    _validate_simulation(simulation, "simulation")

    # Import locally to avoid a module cycle: workload_profile raises this
    # module's ProtocolValidationError for one consistent validation surface.
    from .workload_profile import load_profile_set

    load_profile_set(
        config["workload_profiles"], repository=Path(__file__).resolve().parents[3]
    )

    common_hpa = config["common_hpa"]
    _require(
        common_hpa.get("scale_num") == "hpa", "formal protocol requires common HPA"
    )
    _require(
        common_hpa.get("comparison_scope") == "scheduler_plus_common_hpa",
        "comparison_scope must be scheduler_plus_common_hpa",
    )
    for field in (
        "target_mem_use_rate",
        "tolerance",
        "check_period_frames",
        "careful_down_history",
        "min_instances",
        "max_instances",
        "min_instances_when_pending",
        "allow_scale_to_zero",
        "scale_up_placement",
    ):
        _require(field in common_hpa, f"common_hpa.{field} must be explicitly frozen")

    defaults = config["matrix_defaults"]
    qos_profiles = defaults.get("qos_profiles")
    _require(
        isinstance(qos_profiles, dict), "matrix_defaults.qos_profiles must be an object"
    )
    for profile in ("mixed", "balanced"):
        qos = qos_profiles.get(profile)
        _require(isinstance(qos, dict), f"QoS profile {profile} is missing")
        for field in (
            "enabled",
            "class_assignment",
            "latency_weight",
            "throughput_weight",
            "cost_weight",
            "latency_deadline_ms",
            "throughput_target_rps",
            "cost_budget_per_request",
        ):
            _require(field in qos, f"QoS profile {profile} is missing {field}")
        _require(
            qos["class_assignment"] == "balanced",
            f"QoS profile {profile} must use balanced class assignment",
        )
    nash = defaults.get("nash")
    _require(isinstance(nash, dict), "matrix_defaults.nash must be an object")
    for field in (
        "max_inner_rounds",
        "max_outer_rounds",
        "sa_iterations",
        "sa_iterations_per_player",
        "queue_normalization_mode",
        "queue_normalizer",
        "operational_refinement",
        "observe",
    ):
        _require(
            field in nash, f"matrix_defaults.nash.{field} must be explicitly frozen"
        )
    _require(
        nash["queue_normalization_mode"] in {"window_max", "fixed"},
        "matrix_defaults.nash.queue_normalization_mode must be window_max or fixed",
    )
    _require(
        nash["operational_refinement"]
        in {
            "formula",
            "ready_order",
            "ready_finish_tie",
            "guarded_finish_05",
            "guarded_finish_15",
            "guarded_dynamic_finish_05",
            "guarded_dynamic_finish_15",
        },
        "matrix_defaults.nash.operational_refinement is invalid",
    )
    if nash["queue_normalization_mode"] == "window_max":
        _require(
            nash["queue_normalizer"] is None,
            "matrix_defaults.nash.queue_normalizer must be null for window_max",
        )
    else:
        normalizer = nash["queue_normalizer"]
        _require(
            isinstance(normalizer, (int, float))
            and not isinstance(normalizer, bool)
            and math.isfinite(float(normalizer))
            and float(normalizer) > 0.0,
            "matrix_defaults.nash.queue_normalizer must be finite and positive for fixed mode",
        )
    faasrank = defaults.get("faasrank_model")
    _require(
        isinstance(faasrank, dict) and faasrank == {"state": "unbound"},
        "matrix_defaults.faasrank_model must be the explicit unbound placeholder; "
        "bind the immutable artifact to the expanded tape-bound manifest",
    )
    _validate_qc_policy(config["qc"], "qc")


def _hash_without(document: dict[str, Any], field: str) -> str:
    payload = copy.deepcopy(document)
    payload.pop(field, None)
    return object_hash(payload)


def _validate_integration_smoke_shard(manifest: dict[str, Any]) -> None:
    """Validate the permanent, non-formal lineage marker on a smoke shard."""

    marker_present = "integration_smoke_shard" in manifest
    formal_markers = {marker for marker in FORMAL_SHARD_MARKERS if marker in manifest}
    m1_markers = {marker for marker in M1_NONFORMAL_MARKERS if marker in manifest}
    _require(
        len(formal_markers) <= 1,
        "a manifest cannot contain multiple formal E1 shard markers or other formal shard markers",
    )
    formal_marker_present = bool(formal_markers)
    m1_marker_present = bool(m1_markers)
    _require(len(m1_markers) <= 1, "a manifest cannot contain multiple M1 markers")
    eligibility_present = "formal_results_eligible" in manifest
    _require(
        sum((marker_present, formal_marker_present, m1_marker_present)) <= 1,
        "a manifest cannot combine smoke, formal, and M1 shard markers",
    )
    if formal_marker_present:
        return
    if m1_marker_present:
        _require(
            manifest.get("formal_results_eligible") is False,
            "M1 development and qualification manifests must be non-formal",
        )
        return
    if not marker_present:
        # Existing full formal manifests predate the explicit eligibility field;
        # an explicit true marker is also accepted for future schema writers.
        _require(
            not eligibility_present or manifest.get("formal_results_eligible") is True,
            "formal_results_eligible=false requires an integration smoke marker",
        )
        return
    _require(
        marker_present and manifest.get("formal_results_eligible") is False,
        "integration smoke shards must declare formal_results_eligible=false",
    )
    marker = manifest.get("integration_smoke_shard")
    _require(isinstance(marker, dict), "integration_smoke_shard must be an object")
    _require(
        marker.get("schema_version") == "NSE_INTEGRATION_SMOKE_SHARD_V1",
        "integration_smoke_shard has an unsupported schema_version",
    )
    _require(
        isinstance(marker.get("purpose"), str) and bool(marker["purpose"].strip()),
        "integration_smoke_shard.purpose must be non-empty",
    )
    source = marker.get("source_manifest")
    _require(
        isinstance(source, dict),
        "integration_smoke_shard.source_manifest must be an object",
    )
    _require(
        isinstance(source.get("path"), str) and bool(source["path"]),
        "integration_smoke_shard source path is missing",
    )
    for field in ("manifest_hash", "file_sha256"):
        _require(
            HASH_RE.fullmatch(str(source.get(field))) is not None,
            f"integration_smoke_shard source {field} is invalid",
        )
    _require(
        isinstance(source.get("run_count"), int)
        and not isinstance(source.get("run_count"), bool)
        and source["run_count"] >= len(manifest["runs"]),
        "integration_smoke_shard source run_count is invalid",
    )
    _require(
        source.get("seed_stage") in {"initial", "ci_extension", "all"},
        "integration_smoke_shard source seed_stage is invalid",
    )

    lineage = marker.get("selected_source_runs")
    _require(
        isinstance(lineage, list) and bool(lineage),
        "integration_smoke_shard must select at least one source run",
    )
    _require(
        marker.get("selected_run_count") == len(lineage) == len(manifest["runs"]),
        "integration_smoke_shard selected run count is inconsistent",
    )
    current_by_stable_key = {
        (run.get("cell_id"), run.get("seed")): run for run in manifest["runs"]
    }
    source_run_ids: set[str] = set()
    lineage_keys: set[tuple[Any, Any]] = set()
    for index, entry in enumerate(lineage):
        prefix = f"integration_smoke_shard.selected_source_runs[{index}]"
        _require(isinstance(entry, dict), f"{prefix} must be an object")
        source_run_id = entry.get("source_run_id")
        _require(
            isinstance(source_run_id, str)
            and RUN_ID_RE.fullmatch(source_run_id) is not None
            and source_run_id not in source_run_ids,
            f"{prefix}.source_run_id is invalid or duplicated",
        )
        source_run_ids.add(source_run_id)
        for field in (
            "source_run_spec_hash",
            "source_workload_spec_hash",
            "source_common_hpa_hash",
        ):
            _require(
                HASH_RE.fullmatch(str(entry.get(field))) is not None,
                f"{prefix}.{field} is invalid",
            )
        _require(
            isinstance(entry.get("source_cell_id"), str)
            and bool(entry["source_cell_id"]),
            f"{prefix}.source_cell_id is invalid",
        )
        _require(
            isinstance(entry.get("source_method"), str)
            and bool(entry["source_method"]),
            f"{prefix}.source_method is invalid",
        )
        _require(
            isinstance(entry.get("source_seed"), str)
            and SEED_RE.fullmatch(entry["source_seed"]) is not None,
            f"{prefix}.source_seed is invalid",
        )
        stable_key = (entry["source_cell_id"], entry["source_seed"])
        _require(
            stable_key not in lineage_keys,
            f"{prefix} repeats a source cell/seed pair",
        )
        lineage_keys.add(stable_key)
        current = current_by_stable_key.get(stable_key)
        _require(current is not None, f"{prefix} has no current derived run")
        _require(
            current.get("method") == entry["source_method"]
            and current.get("workload_spec_hash") == entry["source_workload_spec_hash"]
            and current.get("common_hpa_hash") == entry["source_common_hpa_hash"],
            f"{prefix} does not match the current derived run",
        )
    _require(
        set(current_by_stable_key) == lineage_keys,
        "integration_smoke_shard lineage does not cover exactly its current runs",
    )

    sealed_rules = marker.get("sealed_reuse_rules")
    _require(
        isinstance(sealed_rules, list),
        "integration_smoke_shard.sealed_reuse_rules must be an array",
    )
    expected_rules = [
        {"rule_id": entry.get("rule_id"), "rule_sha256": entry.get("rule_sha256")}
        for entry in manifest["reuse_analyses"]
    ]
    _require(
        sealed_rules == expected_rules,
        "integration_smoke_shard did not preserve the sealed reuse rules",
    )

    dependencies: dict[str, dict[str, Any]] = {}
    for run in manifest["runs"]:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], dependency)
    expected_dependencies = [dependencies[key] for key in sorted(dependencies)]
    _require(
        manifest.get("reference_build_dependencies") == expected_dependencies,
        "integration_smoke_shard reference dependencies were not recomputed",
    )
    _require(
        marker.get("selected_reference_build_count") == len(expected_dependencies),
        "integration_smoke_shard selected reference-build count is inconsistent",
    )


def _validate_formal_e1_shard(manifest: dict[str, Any], *, topology: str) -> None:
    _require(
        topology in {"homogeneous", "heterogeneous"},
        f"unsupported formal E1 shard topology: {topology}",
    )
    marker_name = f"formal_e1_{topology}_shard"
    marker = manifest.get(marker_name)
    if marker is None:
        return

    prefix = marker_name
    schema_version = f"NSE_FORMAL_E1_{topology.upper()}_SHARD_V1"
    _require(
        isinstance(marker, dict),
        f"{prefix} must be an object",
    )
    _require(
        marker.get("schema_version") == schema_version,
        f"{prefix} has an unsupported schema_version",
    )
    _require(
        manifest.get("formal_results_eligible") is True,
        "a formal E1 shard must declare formal_results_eligible=true",
    )
    _require(
        "integration_smoke_shard" not in manifest,
        "a formal E1 shard cannot contain an integration smoke marker",
    )

    source = marker.get("source_manifest")
    _require(isinstance(source, dict), f"{prefix}.source_manifest must be an object")
    _require(
        isinstance(source.get("path"), str) and bool(source["path"]),
        f"{prefix} source path is missing",
    )
    for field in ("manifest_hash", "file_sha256"):
        _require(
            HASH_RE.fullmatch(str(source.get(field))) is not None,
            f"{prefix} source {field} is invalid",
        )
    seed_stage = manifest["seed_stage"]
    expected_seeds = FORMAL_E1_SEEDS_BY_STAGE[seed_stage]
    expected_source_count = sum(FULL_MATRIX_RUN_COUNTS_BY_STAGE[seed_stage].values())
    _require(
        source.get("seed_stage") == seed_stage,
        f"{prefix} source seed_stage differs from the shard",
    )
    _require(
        source.get("protocol_id") == manifest["protocol_id"],
        f"{prefix} source protocol_id differs from the shard",
    )
    _require(
        source.get("run_count") == expected_source_count,
        f"{prefix} source run_count is not the complete frozen matrix",
    )

    selection = marker.get("selection")
    expected_selection = {
        "experiment_id": "E1",
        "cluster_topology": topology,
        "node_count": 20,
        "methods": list(FORMAL_E1_METHODS),
        "loads": list(FORMAL_E1_LOADS),
        "seeds": list(expected_seeds),
    }
    _require(
        selection == expected_selection,
        f"{prefix}.selection is not the frozen E1 {topology} Cartesian product",
    )

    expected_product = {
        (method, load, seed)
        for method in FORMAL_E1_METHODS
        for load in FORMAL_E1_LOADS
        for seed in expected_seeds
    }
    current_by_product: dict[tuple[str, str, str], dict[str, Any]] = {}
    current_by_stable_key: dict[tuple[str, str], dict[str, Any]] = {}
    for run in manifest["runs"]:
        key = (run["method"], run["workload"]["request_freq"], run["seed"])
        stable_key = (run["cell_id"], run["seed"])
        _require(
            key not in current_by_product,
            f"{prefix} repeats product member {key}",
        )
        _require(
            stable_key not in current_by_stable_key,
            f"{prefix} repeats cell/seed {stable_key}",
        )
        current_by_product[key] = run
        current_by_stable_key[stable_key] = run
        expected_cell_id = (
            f"E1.{run['method']}.{run['workload']['request_freq']}.{topology}.n20"
        )
        expected_tape_key = (
            "steady."
            f"{run['workload']['request_freq']}.{topology}.mixed.{run['seed']}."
            f"{run['workload_profile']['sha256'][:12]}"
        )
        _require(
            run["experiment_id"] == "E1"
            and run["cell_id"] == expected_cell_id
            and run["cluster"].get("topology") == topology
            and run["cluster"].get("node_count") == 20
            and run["workload"].get("topology") == topology
            and run["workload"].get("arrival_profile") == "steady"
            and run["workload"].get("qos_profile") == "mixed"
            and run["workload"].get("load_scale") == 1.0
            and run.get("variant") == "full"
            and run["workload_tape"].get("key") == expected_tape_key,
            f"{prefix} contains a noncanonical run {run['run_id']}",
        )
    _require(
        set(current_by_product) == expected_product,
        f"{prefix} does not contain the complete E1 {topology} Cartesian product",
    )

    lineage = marker.get("selected_source_runs")
    _require(
        isinstance(lineage, list) and len(lineage) == len(expected_product),
        f"{prefix} lineage does not cover every selected run",
    )
    source_run_ids: set[str] = set()
    lineage_keys: set[tuple[str, str]] = set()
    for index, entry in enumerate(lineage):
        entry_prefix = f"{prefix}.selected_source_runs[{index}]"
        _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
        source_run_id = entry.get("source_run_id")
        _require(
            isinstance(source_run_id, str)
            and RUN_ID_RE.fullmatch(source_run_id) is not None
            and source_run_id not in source_run_ids,
            f"{entry_prefix}.source_run_id is invalid or duplicated",
        )
        source_run_ids.add(source_run_id)
        for field in (
            "source_run_spec_hash",
            "source_workload_spec_hash",
            "source_cluster_sha256",
            "source_simulation_sha256",
            "source_environment_sha256",
            "source_common_hpa_hash",
        ):
            _require(
                HASH_RE.fullmatch(str(entry.get(field))) is not None,
                f"{entry_prefix}.{field} is invalid",
            )
        for field in (
            "source_cell_id",
            "source_method",
            "source_variant",
            "source_seed",
            "source_workload_tape_key",
        ):
            _require(
                isinstance(entry.get(field), str) and bool(entry[field]),
                f"{entry_prefix}.{field} is invalid",
            )
        stable_key = (entry["source_cell_id"], entry["source_seed"])
        _require(
            stable_key not in lineage_keys,
            f"{entry_prefix} repeats a source cell/seed pair",
        )
        lineage_keys.add(stable_key)
        current = current_by_stable_key.get(stable_key)
        _require(current is not None, f"{entry_prefix} has no current derived run")
        _require(
            current["method"] == entry["source_method"]
            and current.get("variant", "full") == entry["source_variant"]
            and current["workload_spec_hash"] == entry["source_workload_spec_hash"]
            and current["workload_tape"]["key"] == entry["source_workload_tape_key"]
            and object_hash(current["cluster"]) == entry["source_cluster_sha256"]
            and object_hash(current["simulation"]) == entry["source_simulation_sha256"]
            and object_hash(current["environment"])
            == entry["source_environment_sha256"]
            and current["common_hpa_hash"] == entry["source_common_hpa_hash"],
            f"{entry_prefix} differs from the current run after binding",
        )
    _require(
        set(current_by_stable_key) == lineage_keys,
        f"{prefix} lineage does not cover exactly its current runs",
    )

    sealed_rules = marker.get("sealed_reuse_rules")
    expected_rules = [
        {"rule_id": entry.get("rule_id"), "rule_sha256": entry.get("rule_sha256")}
        for entry in manifest["reuse_analyses"]
    ]
    _require(
        sealed_rules == expected_rules,
        f"{prefix} did not preserve the sealed reuse rules",
    )

    dependencies: dict[str, dict[str, Any]] = {}
    for run in manifest["runs"]:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], dependency)
    expected_dependencies = [dependencies[key] for key in sorted(dependencies)]
    _require(
        manifest.get("reference_build_dependencies") == expected_dependencies,
        f"{prefix} reference dependencies were not recomputed",
    )
    _require(
        marker.get("selected_run_count") == len(expected_product),
        f"{prefix} selected_run_count is inconsistent",
    )
    _require(
        marker.get("selected_cell_count")
        == len(FORMAL_E1_METHODS) * len(FORMAL_E1_LOADS),
        f"{prefix} selected_cell_count is inconsistent",
    )
    _require(
        marker.get("selected_reference_build_count") == len(expected_dependencies),
        f"{prefix} selected_reference_build_count is inconsistent",
    )

    cells = {(run["experiment_id"], run["cell_id"]) for run in manifest["runs"]}
    by_experiment: dict[str, dict[str, int]] = {}
    for experiment_id in (f"E{index}" for index in range(1, 10)):
        by_experiment[experiment_id] = {
            "new_cells": sum(item[0] == experiment_id for item in cells),
            "new_runs": sum(
                run["experiment_id"] == experiment_id for run in manifest["runs"]
            ),
            "reuse_entries": sum(
                entry["experiment_id"] == experiment_id
                for entry in manifest["reuse_analyses"]
            ),
        }
    expected_summary = {
        "new_cells": len(cells),
        "new_runs": len(manifest["runs"]),
        "by_experiment": by_experiment,
    }
    _require(
        manifest.get("matrix_summary") == expected_summary,
        f"{prefix} matrix_summary does not match the selected runs",
    )


def _validate_formal_e2_shard(manifest: dict[str, Any]) -> None:
    """Validate the complete physical E2 block and its sealed E1 reuse source."""

    marker_name = "formal_e2_weak_scaling_shard"
    marker = manifest.get(marker_name)
    if marker is None:
        return
    prefix = marker_name
    _require(isinstance(marker, dict), f"{prefix} must be an object")
    _require(
        marker.get("schema_version") == "NSE_FORMAL_E2_WEAK_SCALING_SHARD_V1",
        f"{prefix} has an unsupported schema_version",
    )
    _require(
        manifest.get("formal_results_eligible") is True,
        "a formal E2 shard must declare formal_results_eligible=true",
    )
    _require(
        "integration_smoke_shard" not in manifest,
        "a formal E2 shard cannot contain an integration smoke marker",
    )

    source = marker.get("source_manifest")
    _require(isinstance(source, dict), f"{prefix}.source_manifest must be an object")
    _require(
        isinstance(source.get("path"), str) and bool(source["path"]),
        f"{prefix} source path is missing",
    )
    for field in ("manifest_hash", "file_sha256"):
        _require(
            HASH_RE.fullmatch(str(source.get(field))) is not None,
            f"{prefix} source {field} is invalid",
        )
    seed_stage = manifest["seed_stage"]
    seeds = FORMAL_E1_SEEDS_BY_STAGE[seed_stage]
    expected_source_count = sum(FULL_MATRIX_RUN_COUNTS_BY_STAGE[seed_stage].values())
    _require(
        source.get("seed_stage") == seed_stage
        and source.get("protocol_id") == manifest["protocol_id"]
        and source.get("run_count") == expected_source_count,
        f"{prefix} source is not the complete matching frozen matrix",
    )

    expected_selection = {
        "experiment_id": "E2",
        "cluster_topology": "homogeneous",
        "node_scales": [
            {"node_count": 100, "load_scale": 5.0},
            {"node_count": 500, "load_scale": 25.0},
        ],
        "methods": list(FORMAL_E1_METHODS),
        "loads": list(FORMAL_E1_LOADS),
        "seeds": list(seeds),
    }
    _require(
        marker.get("selection") == expected_selection,
        f"{prefix}.selection is not the frozen E2 Cartesian product",
    )

    expected_product = {
        (method, load, node_count, seed)
        for method in FORMAL_E1_METHODS
        for load in FORMAL_E1_LOADS
        for node_count in (100, 500)
        for seed in seeds
    }
    current_by_product: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    current_by_stable_key: dict[tuple[str, str], dict[str, Any]] = {}
    for run in manifest["runs"]:
        method = run["method"]
        load = run["workload"]["request_freq"]
        node_count = run["cluster"].get("node_count")
        seed = run["seed"]
        key = (method, load, node_count, seed)
        stable_key = (run["cell_id"], seed)
        _require(
            key not in current_by_product, f"{prefix} repeats product member {key}"
        )
        _require(
            stable_key not in current_by_stable_key,
            f"{prefix} repeats cell/seed {stable_key}",
        )
        current_by_product[key] = run
        current_by_stable_key[stable_key] = run
        factor = {100: 5.0, 500: 25.0}.get(node_count)
        factor_slug = "" if factor is None else f"{factor:g}"
        expected_cell = (
            f"E2.{method}.{load}.homogeneous.n{node_count}.scale{factor_slug}"
        )
        expected_parent = (
            f"steady.{load}.homogeneous.mixed.{seed}."
            f"{run['workload_profile']['sha256'][:12]}"
        )
        expected_tape = f"weakscale{factor_slug}.{expected_parent}"
        tape = run["workload_tape"]
        _require(
            run["experiment_id"] == "E2"
            and factor is not None
            and run["cell_id"] == expected_cell
            and run["cluster"].get("topology") == "homogeneous"
            and run["workload"].get("topology") == "homogeneous"
            and run["workload"].get("arrival_profile") == "steady"
            and run["workload"].get("qos_profile") == "mixed"
            and run["workload"].get("load_scale") == factor
            and run.get("variant") == "full"
            and tape.get("kind") == "derived_scale"
            and tape.get("key") == expected_tape
            and tape.get("parent_key") == expected_parent
            and isinstance(tape.get("transform"), dict)
            and tape["transform"].get("kind") == "same_frame_replication"
            and tape["transform"].get("factor") == int(factor),
            f"{prefix} contains a noncanonical run {run['run_id']}",
        )
    _require(
        set(current_by_product) == expected_product,
        f"{prefix} does not contain the complete E2 weak-scaling Cartesian product",
    )

    lineage = marker.get("selected_source_runs")
    _require(
        isinstance(lineage, list) and len(lineage) == len(expected_product),
        f"{prefix} lineage does not cover every physical E2 run",
    )
    lineage_keys: set[tuple[str, str]] = set()
    source_run_ids: set[str] = set()
    for index, entry in enumerate(lineage):
        entry_prefix = f"{prefix}.selected_source_runs[{index}]"
        _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
        source_run_id = entry.get("source_run_id")
        _require(
            isinstance(source_run_id, str)
            and RUN_ID_RE.fullmatch(source_run_id) is not None
            and source_run_id not in source_run_ids,
            f"{entry_prefix}.source_run_id is invalid or duplicated",
        )
        source_run_ids.add(source_run_id)
        for field in (
            "source_run_spec_hash",
            "source_workload_spec_hash",
            "source_cluster_sha256",
            "source_simulation_sha256",
            "source_environment_sha256",
            "source_common_hpa_hash",
        ):
            _require(
                HASH_RE.fullmatch(str(entry.get(field))) is not None,
                f"{entry_prefix}.{field} is invalid",
            )
        for field in (
            "source_cell_id",
            "source_method",
            "source_variant",
            "source_seed",
            "source_workload_tape_key",
        ):
            _require(
                isinstance(entry.get(field), str) and bool(entry[field]),
                f"{entry_prefix}.{field} is invalid",
            )
        stable_key = (entry["source_cell_id"], entry["source_seed"])
        _require(stable_key not in lineage_keys, f"{entry_prefix} is duplicated")
        lineage_keys.add(stable_key)
        current = current_by_stable_key.get(stable_key)
        _require(current is not None, f"{entry_prefix} has no current derived run")
        _require(
            current["method"] == entry["source_method"]
            and current.get("variant", "full") == entry["source_variant"]
            and current["workload_spec_hash"] == entry["source_workload_spec_hash"]
            and current["workload_tape"]["key"] == entry["source_workload_tape_key"]
            and object_hash(current["cluster"]) == entry["source_cluster_sha256"]
            and object_hash(current["simulation"]) == entry["source_simulation_sha256"]
            and object_hash(current["environment"])
            == entry["source_environment_sha256"]
            and current["common_hpa_hash"] == entry["source_common_hpa_hash"],
            f"{entry_prefix} differs from the current run after binding",
        )
    _require(
        set(current_by_stable_key) == lineage_keys,
        f"{prefix} lineage does not cover exactly its current physical runs",
    )

    expected_e1_product = {
        (method, load, seed)
        for method in FORMAL_E1_METHODS
        for load in FORMAL_E1_LOADS
        for seed in seeds
    }
    e1_lineage = marker.get("e1_reuse_source_runs")
    _require(
        isinstance(e1_lineage, list) and len(e1_lineage) == len(expected_e1_product),
        f"{prefix} E1 reuse lineage is incomplete",
    )
    observed_e1: set[tuple[str, str, str]] = set()
    e1_source_ids: set[str] = set()
    for index, entry in enumerate(e1_lineage):
        entry_prefix = f"{prefix}.e1_reuse_source_runs[{index}]"
        _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
        for field in (
            "source_run_spec_hash",
            "source_workload_spec_hash",
            "source_cluster_sha256",
            "source_simulation_sha256",
            "source_environment_sha256",
            "source_common_hpa_hash",
        ):
            _require(
                HASH_RE.fullmatch(str(entry.get(field))) is not None,
                f"{entry_prefix}.{field} is invalid",
            )
        source_run_id = entry.get("source_run_id")
        _require(
            isinstance(source_run_id, str)
            and RUN_ID_RE.fullmatch(source_run_id) is not None
            and source_run_id not in e1_source_ids,
            f"{entry_prefix}.source_run_id is invalid or duplicated",
        )
        e1_source_ids.add(source_run_id)
        method = entry.get("source_method")
        load = entry.get("source_load")
        seed = entry.get("source_seed")
        key = (method, load, seed)
        _require(key not in observed_e1, f"{entry_prefix} repeats E1 source {key}")
        observed_e1.add(key)
        expected_cell = f"E1.{method}.{load}.homogeneous.n20"
        _require(
            entry.get("source_experiment_id") == "E1"
            and entry.get("source_cell_id") == expected_cell
            and entry.get("source_variant") == "full"
            and entry.get("source_topology") == "homogeneous"
            and entry.get("source_node_count") == 20
            and entry.get("source_load_scale") == 1.0
            and isinstance(entry.get("source_workload_tape_key"), str)
            and entry["source_workload_tape_key"].startswith(
                f"steady.{load}.homogeneous.mixed.{seed}."
            ),
            f"{entry_prefix} is not a canonical E1 homogeneous reuse source",
        )
    _require(
        observed_e1 == expected_e1_product,
        f"{prefix} E1 reuse lineage is not the complete 20-node product",
    )

    expected_rules = [
        {"rule_id": entry.get("rule_id"), "rule_sha256": entry.get("rule_sha256")}
        for entry in manifest["reuse_analyses"]
    ]
    _require(
        marker.get("sealed_reuse_rules") == expected_rules,
        f"{prefix} did not preserve all sealed reuse rules",
    )
    e2_rules = [
        item
        for item in expected_rules
        if item["rule_id"] == "E2_FROM_E1_20NODE_HOMOGENEOUS_V1"
    ]
    _require(
        len(e2_rules) == 1 and marker.get("sealed_e1_reuse_rule") == e2_rules[0],
        f"{prefix} E1 reuse rule is absent or changed",
    )

    dependencies: dict[str, dict[str, Any]] = {}
    for run in manifest["runs"]:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], dependency)
    expected_dependencies = [dependencies[key] for key in sorted(dependencies)]
    _require(
        manifest.get("reference_build_dependencies") == expected_dependencies,
        f"{prefix} reference dependencies were not recomputed",
    )
    _require(
        marker.get("selected_run_count") == len(expected_product)
        and marker.get("selected_cell_count") == 60
        and marker.get("selected_reference_build_count") == len(expected_dependencies)
        and marker.get("e1_reuse_source_run_count") == len(expected_e1_product)
        and marker.get("e1_reuse_source_cell_count") == 30,
        f"{prefix} selected counts are inconsistent",
    )

    cells = {(run["experiment_id"], run["cell_id"]) for run in manifest["runs"]}
    by_experiment: dict[str, dict[str, int]] = {}
    for experiment_id in (f"E{index}" for index in range(1, 10)):
        by_experiment[experiment_id] = {
            "new_cells": sum(item[0] == experiment_id for item in cells),
            "new_runs": sum(
                run["experiment_id"] == experiment_id for run in manifest["runs"]
            ),
            "reuse_entries": sum(
                entry["experiment_id"] == experiment_id
                for entry in manifest["reuse_analyses"]
            ),
        }
    _require(
        manifest.get("matrix_summary")
        == {
            "new_cells": len(cells),
            "new_runs": len(manifest["runs"]),
            "by_experiment": by_experiment,
        },
        f"{prefix} matrix_summary does not match the selected runs",
    )


def _validate_formal_e3_e4_shard_contract(
    manifest: dict[str, Any],
    *,
    marker_name: str,
    schema_version: str,
    seed_stage: str,
) -> None:
    """Validate a complete stage-specific burst and balanced-QoS block."""

    marker = manifest.get(marker_name)
    if marker is None:
        return
    prefix = marker_name
    _require(isinstance(marker, dict), f"{prefix} must be an object")
    _require(
        marker.get("schema_version") == schema_version,
        f"{prefix} has an unsupported schema_version",
    )
    _require(
        manifest.get("formal_results_eligible") is True
        and manifest.get("seed_stage") == seed_stage,
        f"{prefix} requires an eligible {seed_stage} manifest",
    )
    _require(
        "integration_smoke_shard" not in manifest,
        f"{prefix} cannot contain an integration smoke marker",
    )

    source = marker.get("source_manifest")
    _require(isinstance(source, dict), f"{prefix}.source_manifest must be an object")
    _require(
        isinstance(source.get("path"), str) and bool(source["path"]),
        f"{prefix} source path is missing",
    )
    for field in ("manifest_hash", "file_sha256"):
        _require(
            HASH_RE.fullmatch(str(source.get(field))) is not None,
            f"{prefix} source {field} is invalid",
        )
    _require(
        source.get("seed_stage") == seed_stage
        and source.get("protocol_id") == manifest["protocol_id"]
        and source.get("run_count")
        == sum(FULL_MATRIX_RUN_COUNTS_BY_STAGE[seed_stage].values()),
        f"{prefix} source is not the complete {seed_stage} frozen matrix",
    )

    methods = list(FORMAL_E1_METHODS)
    seeds = list(FORMAL_E1_SEEDS_BY_STAGE[seed_stage])
    bursts = [
        {
            "name": "spike5x50ms",
            "kind": "spike",
            "multiplier": 5.0,
            "duration_ms": 50,
            "repetitions": 1,
        },
        {
            "name": "sustained3x200ms",
            "kind": "sustained",
            "multiplier": 3.0,
            "duration_ms": 200,
            "repetitions": 1,
        },
        {
            "name": "pulse4x4x50ms",
            "kind": "pulse",
            "multiplier": 4.0,
            "duration_ms": 50,
            "repetitions": 4,
        },
    ]
    expected_selection = {
        "experiment_ids": ["E3", "E4"],
        "methods": methods,
        "seeds": seeds,
        "common_cluster": {"node_count": 20, "topology": "heterogeneous"},
        "base_load": "middle",
        "qos_profile": "balanced",
        "E3": {
            "burst_scenarios": bursts,
            "arrival_horizon_frames": 1000,
            "observation_horizon_frames": 1000,
            "total_frame": 4000,
        },
        "E4": {
            "arrival_profile": "steady",
            "arrival_horizon_frames": 1000,
            "observation_horizon_frames": 1000,
            "total_frame": 1000,
            "per_qos_breakdown_required": True,
        },
    }
    _require(
        marker.get("selection") == expected_selection,
        f"{prefix}.selection is not the frozen {seed_stage} E3/E4 product",
    )
    _require(
        marker.get("execution_prerequisites")
        == {
            "workload_tapes": "required_before_execution",
            "sla_targets": "required_before_execution_from_E1_pilot_artifact",
            "faasrank_model": "required_before_execution",
            "offline_references": "required_before_execution",
        },
        f"{prefix} execution prerequisites are not frozen",
    )

    burst_by_name = {entry["name"]: entry for entry in bursts}
    expected_product = {
        ("E3", method, burst_name, seed)
        for method in methods
        for burst_name in burst_by_name
        for seed in seeds
    } | {("E4", method, "steady", seed) for method in methods for seed in seeds}
    runs = manifest["runs"]
    _require(len(runs) == 400, f"{prefix} must contain exactly 400 runs")
    observed_product: set[tuple[str, str, str, str]] = set()
    current_by_stable: dict[tuple[str, str], dict[str, Any]] = {}
    for run in runs:
        experiment_id = run["experiment_id"]
        scenario = (
            run["workload"].get("burst_name") if experiment_id == "E3" else "steady"
        )
        product_key = (experiment_id, run["method"], scenario, run["seed"])
        _require(
            product_key not in observed_product,
            f"{prefix} repeats physical product member {product_key}",
        )
        observed_product.add(product_key)
        stable = (run["cell_id"], run["seed"])
        _require(stable not in current_by_stable, f"{prefix} repeats {stable}")
        current_by_stable[stable] = run

        workload = run["workload"]
        simulation = run["simulation"]
        tape = run["workload_tape"]
        qos = run["simulator_experiment"]["qos"]
        _require(
            run["method"] in FORMAL_E1_METHODS
            and run["seed"] in seeds
            and run.get("variant") == "full"
            and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
            and workload.get("request_freq") == "middle"
            and workload.get("topology") == "heterogeneous"
            and workload.get("qos_profile") == "balanced"
            and workload.get("load_scale") == 1.0
            and qos.get("enabled") is True
            and qos.get("class_assignment") == "balanced"
            and simulation.get("arrival_horizon_frames") == 1000
            and simulation.get("observation_horizon_frames") == 1000
            and tape.get("runtime_mode") == "replay"
            and tape.get("runtime_load_scale") == 1.0
            and tape.get("runtime_burst_profile") == "steady",
            f"{prefix} run {run['run_id']} changes the common balanced-QoS runtime",
        )

        tape_suffix = (
            f"steady.middle.heterogeneous.balanced.{run['seed']}."
            f"{run['workload_profile']['sha256'][:12]}"
        )
        if experiment_id == "E3":
            burst = burst_by_name.get(str(scenario))
            _require(burst is not None, f"{prefix} has an unknown burst {scenario}")
            expected_burst = {
                key: value for key, value in burst.items() if key != "name"
            }
            transform = tape.get("transform")
            expected_unbound_transform = {
                "kind": "cdf_burst_remap",
                "scenario": scenario,
                "event_count_invariant": "exact",
                "dag_order_invariant": "exact",
            }
            transform_is_valid = transform == expected_unbound_transform
            if manifest.get("all_tapes_bound") is True:
                bound_shapes = {
                    "spike5x50ms": (5.0, [[475, 525]]),
                    "sustained3x200ms": (3.0, [[400, 600]]),
                    "pulse4x4x50ms": (
                        4.0,
                        [[200, 250], [400, 450], [600, 650], [800, 850]],
                    ),
                }
                multiplier, intervals = bound_shapes[str(scenario)]
                transform_is_valid = (
                    isinstance(transform, dict)
                    and transform.get("schema") == "NSE_TAPE_DERIVATION_V1"
                    and transform.get("kind") == "cdf_burst_remap"
                    and transform.get("scenario") == scenario
                    and transform.get("horizon_frames") == 1000
                    and transform.get("multiplier") == multiplier
                    and transform.get("intervals") == intervals
                    and transform.get("event_count_invariant") == "exact"
                    and transform.get("dag_order_invariant") == "exact"
                    and transform.get("parent_sha256") == tape.get("parent_sha256")
                    and transform.get("parent_event_count") == tape.get("event_count")
                )
            _require(
                run["cell_id"] == f"E3.{run['method']}.{scenario}.heterogeneous.n20"
                and workload.get("arrival_profile") == "burst"
                and workload.get("burst") == expected_burst
                and simulation.get("total_frame") == 4000
                and simulation.get("expected_final_frame") == 4000
                and simulation.get("expected_frame_count") == 4001
                and tape.get("kind") == "derived_burst"
                and tape.get("parent_key") == tape_suffix
                and tape.get("key") == f"burst.{scenario}.{tape_suffix}"
                and transform_is_valid,
                f"{prefix} contains a noncanonical E3 run {run['run_id']}",
            )
        else:
            _require(
                experiment_id == "E4"
                and run["cell_id"] == f"E4.{run['method']}.steady.balanced.n20"
                and workload.get("arrival_profile") == "steady"
                and "burst_name" not in workload
                and "burst" not in workload
                and run.get("metadata", {}).get("per_qos_breakdown_required") is True
                and simulation.get("total_frame") == 1000
                and simulation.get("expected_final_frame") == 1000
                and simulation.get("expected_frame_count") == 1001
                and tape.get("kind") == "base_steady"
                and tape.get("key") == tape_suffix
                and tape.get("parent_key") is None
                and tape.get("transform") == {"kind": "identity"},
                f"{prefix} contains a noncanonical E4 run {run['run_id']}",
            )
    _require(
        observed_product == expected_product,
        f"{prefix} physical Cartesian product is incomplete",
    )

    lineage = marker.get("selected_source_runs")
    _require(
        isinstance(lineage, list) and len(lineage) == 400,
        f"{prefix} physical lineage is incomplete",
    )
    lineage_stable: set[tuple[str, str]] = set()
    lineage_ids: set[str] = set()
    for index, entry in enumerate(lineage):
        entry_prefix = f"{prefix}.selected_source_runs[{index}]"
        _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
        source_id = entry.get("source_run_id")
        _require(
            isinstance(source_id, str)
            and RUN_ID_RE.fullmatch(source_id) is not None
            and source_id not in lineage_ids,
            f"{entry_prefix}.source_run_id is invalid or duplicated",
        )
        lineage_ids.add(source_id)
        for field in (
            "source_run_spec_hash",
            "source_workload_spec_hash",
            "source_cluster_sha256",
            "source_simulation_sha256",
            "source_environment_sha256",
            "source_common_hpa_hash",
        ):
            _require(
                HASH_RE.fullmatch(str(entry.get(field))) is not None,
                f"{entry_prefix}.{field} is invalid",
            )
        stable = (entry.get("source_cell_id"), entry.get("source_seed"))
        _require(
            stable not in lineage_stable,
            f"{entry_prefix} repeats a source cell/seed",
        )
        lineage_stable.add(stable)
        current = current_by_stable.get(stable)
        _require(current is not None, f"{entry_prefix} has no current physical run")
        _require(
            current.get("method") == entry.get("source_method")
            and current.get("variant", "full") == entry.get("source_variant")
            and current.get("workload_spec_hash")
            == entry.get("source_workload_spec_hash")
            and current.get("workload_tape", {}).get("key")
            == entry.get("source_workload_tape_key")
            and object_hash(current.get("cluster"))
            == entry.get("source_cluster_sha256")
            and object_hash(current.get("simulation"))
            == entry.get("source_simulation_sha256")
            and object_hash(current.get("environment"))
            == entry.get("source_environment_sha256")
            and current.get("common_hpa_hash") == entry.get("source_common_hpa_hash"),
            f"{entry_prefix} differs from the current run after binding",
        )
    _require(
        lineage_stable == set(current_by_stable),
        f"{prefix} lineage does not cover exactly its current runs",
    )

    expected_rules = [
        {"rule_id": entry.get("rule_id"), "rule_sha256": entry.get("rule_sha256")}
        for entry in manifest["reuse_analyses"]
    ]
    _require(
        marker.get("sealed_reuse_rules") == expected_rules,
        f"{prefix} did not preserve all sealed reuse rules",
    )
    dependencies: dict[str, dict[str, Any]] = {}
    reference_runs = []
    for run in runs:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], dependency)
            reference_runs.append(run)
    expected_dependencies = [dependencies[key] for key in sorted(dependencies)]
    _require(
        manifest.get("reference_build_dependencies") == expected_dependencies
        and len(expected_dependencies) == 40
        and len(reference_runs) == 40
        and all(run["method"] == "sche_nash" for run in reference_runs),
        f"{prefix} reference dependencies are not the 40 NSESche runs",
    )
    _require(
        marker.get("selected_run_count") == 400
        and marker.get("selected_cell_count") == 40
        and marker.get("selected_e3_run_count") == 300
        and marker.get("selected_e4_run_count") == 100
        and marker.get("selected_reference_build_count") == 40
        and marker.get("selected_balanced_qos_run_count") == 400
        and marker.get("selected_faasrank_run_count") == 40,
        f"{prefix} selected counts are inconsistent",
    )

    cells = {(run["experiment_id"], run["cell_id"]) for run in runs}
    by_experiment = {
        f"E{index}": {
            "new_cells": sum(item[0] == f"E{index}" for item in cells),
            "new_runs": sum(run["experiment_id"] == f"E{index}" for run in runs),
            "reuse_entries": sum(
                entry["experiment_id"] == f"E{index}"
                for entry in manifest["reuse_analyses"]
            ),
        }
        for index in range(1, 10)
    }
    _require(
        manifest.get("matrix_summary")
        == {
            "new_cells": 40,
            "new_runs": 400,
            "by_experiment": by_experiment,
        },
        f"{prefix} matrix_summary does not match selected runs",
    )


def _validate_formal_e3_e4_shard(manifest: dict[str, Any]) -> None:
    """Validate the complete initial E3/E4 execution block."""

    _validate_formal_e3_e4_shard_contract(
        manifest,
        marker_name="formal_e3_e4_initial_shard",
        schema_version="NSE_FORMAL_E3_E4_INITIAL_SHARD_V1",
        seed_stage="initial",
    )


def _validate_formal_e3_e4_extension_shard(manifest: dict[str, Any]) -> None:
    """Validate the mandatory, disjoint E11--E20 E3/E4 second bank."""

    _validate_formal_e3_e4_shard_contract(
        manifest,
        marker_name="formal_e3_e4_ci_extension_shard",
        schema_version="NSE_FORMAL_E3_E4_CI_EXTENSION_SHARD_V1",
        seed_stage="ci_extension",
    )


def _validate_formal_e5_e6_e7_shard(manifest: dict[str, Any]) -> None:
    """Validate the frozen initial physical E5/E6/E7 shard.

    The marker carries role-specific E1 heterogeneous reuse lineage.  Physical
    runs are checked against the current bound manifest; reuse entries are
    checked structurally here and against an E1 ready manifest by the merge
    audit before analysis.
    """

    marker_name = "formal_e5_e6_e7_initial_shard"
    marker = manifest.get(marker_name)
    if marker is None:
        return
    prefix = marker_name
    _require(isinstance(marker, dict), f"{prefix} must be an object")
    _require(
        marker.get("schema_version") == "NSE_FORMAL_E5_E6_E7_INITIAL_SHARD_V1",
        f"{prefix} has an unsupported schema_version",
    )
    _require(
        manifest.get("formal_results_eligible") is True
        and manifest.get("seed_stage") == "initial",
        f"{prefix} requires an eligible initial manifest",
    )
    _require(
        "integration_smoke_shard" not in manifest,
        f"{prefix} cannot contain an integration smoke marker",
    )
    source = marker.get("source_manifest")
    _require(isinstance(source, dict), f"{prefix}.source_manifest must be an object")
    for field in ("manifest_hash", "file_sha256"):
        _require(
            HASH_RE.fullmatch(str(source.get(field))) is not None,
            f"{prefix} source {field} is invalid",
        )
    _require(
        source.get("seed_stage") == "initial"
        and source.get("protocol_id") == manifest["protocol_id"]
        and source.get("run_count")
        == sum(FULL_MATRIX_RUN_COUNTS_BY_STAGE["initial"].values()),
        f"{prefix} source is not the complete initial frozen matrix",
    )

    expected_physical = {
        "E5": 120,
        "E6": 40,
        "E7": 120,
    }
    runs = manifest["runs"]
    observed_counts = Counter(run["experiment_id"] for run in runs)
    _require(
        {key: observed_counts.get(key, 0) for key in expected_physical}
        == expected_physical
        and len(runs) == 280,
        f"{prefix} physical run counts are not 120/40/120",
    )
    current_by_stable: dict[tuple[str, str], dict[str, Any]] = {}
    physical_keys: set[tuple[str, str, str, str, str]] = set()
    ablations = {
        "no_heterogeneity",
        "no_externality",
        "no_pricing",
        "no_coordination",
    }
    e6_methods = {"cp_br", "onsocmax"}
    e7_variants = {"price_minus", "price_plus", "quality_minus", "quality_plus"}
    for run in runs:
        experiment = run["experiment_id"]
        key = (
            experiment,
            run["method"],
            run.get("variant", "full"),
            run["workload"]["request_freq"],
            run["seed"],
        )
        _require(key not in physical_keys, f"{prefix} repeats physical run {key}")
        physical_keys.add(key)
        stable = (run["cell_id"], run["seed"])
        _require(
            stable not in current_by_stable, f"{prefix} repeats cell/seed {stable}"
        )
        current_by_stable[stable] = run
        _require(
            run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
            and run["workload"].get("topology") == "heterogeneous"
            and run["workload"].get("arrival_profile") == "steady"
            and run["workload"].get("qos_profile") == "mixed"
            and run["workload"].get("load_scale") == 1.0,
            f"{prefix} run {run['run_id']} changes the common E5/E6/E7 runtime",
        )
        if experiment == "E5":
            _require(
                run["method"] == "sche_nash" and run.get("variant") in ablations,
                f"{prefix} has malformed E5 run",
            )
        elif experiment == "E6":
            _require(
                run["method"] in e6_methods
                and run.get("variant") == "full"
                and run["workload"]["request_freq"] in {"middle", "high"},
                f"{prefix} has malformed E6 run",
            )
        else:
            _require(
                run["method"] == "sche_nash" and run.get("variant") in e7_variants,
                f"{prefix} has malformed E7 run",
            )

    expected_rules = [
        {"rule_id": entry.get("rule_id"), "rule_sha256": entry.get("rule_sha256")}
        for entry in manifest["reuse_analyses"]
    ]
    _require(
        marker.get("sealed_reuse_rules") == expected_rules,
        f"{prefix} did not preserve all sealed reuse rules",
    )
    expected_role_rules = {
        "E5": "E5_FULL_FROM_E1_NSESCHE_V1",
        "E6": "E6_ORIGINAL_METHODS_FROM_E1_V1",
        "E7": "E7_CENTRES_FROM_E1_NSESCHE_V1",
    }
    sealed_role_rules = marker.get("sealed_e1_reuse_rules")
    _require(
        isinstance(sealed_role_rules, dict), f"{prefix} role reuse rules are missing"
    )
    for role, rule_id in expected_role_rules.items():
        matching = [item for item in expected_rules if item["rule_id"] == rule_id]
        _require(
            len(matching) == 1 and sealed_role_rules.get(role) == matching[0],
            f"{prefix} sealed {role} reuse rule is missing or changed",
        )

    lineage = marker.get("selected_source_runs")
    _require(
        isinstance(lineage, list) and len(lineage) == 280,
        f"{prefix} physical lineage is incomplete",
    )
    lineage_stable: set[tuple[str, str]] = set()
    lineage_ids: set[str] = set()
    for index, entry in enumerate(lineage):
        entry_prefix = f"{prefix}.selected_source_runs[{index}]"
        _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
        source_id = entry.get("source_run_id")
        _require(
            isinstance(source_id, str)
            and RUN_ID_RE.fullmatch(source_id) is not None
            and source_id not in lineage_ids,
            f"{entry_prefix}.source_run_id is invalid or duplicated",
        )
        lineage_ids.add(source_id)
        for field in (
            "source_run_spec_hash",
            "source_workload_spec_hash",
            "source_cluster_sha256",
            "source_simulation_sha256",
            "source_environment_sha256",
            "source_common_hpa_hash",
        ):
            _require(
                HASH_RE.fullmatch(str(entry.get(field))) is not None,
                f"{entry_prefix}.{field} is invalid",
            )
        stable = (entry.get("source_cell_id"), entry.get("source_seed"))
        _require(
            stable not in lineage_stable, f"{entry_prefix} repeats a source cell/seed"
        )
        lineage_stable.add(stable)
        current = current_by_stable.get(stable)
        _require(current is not None, f"{entry_prefix} has no current physical run")
        _require(
            current.get("method") == entry.get("source_method")
            and current.get("variant", "full") == entry.get("source_variant")
            and current.get("workload_spec_hash")
            == entry.get("source_workload_spec_hash")
            and current.get("workload_tape", {}).get("key")
            == entry.get("source_workload_tape_key")
            and object_hash(current.get("cluster"))
            == entry.get("source_cluster_sha256")
            and object_hash(current.get("simulation"))
            == entry.get("source_simulation_sha256")
            and object_hash(current.get("environment"))
            == entry.get("source_environment_sha256")
            and current.get("common_hpa_hash") == entry.get("source_common_hpa_hash"),
            f"{entry_prefix} differs from the current physical run after binding",
        )
    _require(
        lineage_stable == set(current_by_stable),
        f"{prefix} physical lineage coverage differs",
    )

    expected_reuse_counts = {"E5": 30, "E6": 200, "E7": 30}
    reuse = marker.get("e1_reuse_lineage")
    _require(isinstance(reuse, dict), f"{prefix} E1 reuse lineage map is missing")
    all_reuse_ids: set[str] = set()
    for role, expected_count in expected_reuse_counts.items():
        rows = reuse.get(role)
        _require(
            isinstance(rows, list) and len(rows) == expected_count,
            f"{prefix} {role} reuse lineage count mismatch",
        )
        role_ids: set[str] = set()
        for index, entry in enumerate(rows):
            entry_prefix = f"{prefix}.e1_reuse_lineage.{role}[{index}]"
            _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
            source_id = entry.get("source_run_id")
            _require(
                isinstance(source_id, str)
                and RUN_ID_RE.fullmatch(source_id) is not None
                and source_id not in role_ids,
                f"{entry_prefix}.source_run_id is invalid or duplicated",
            )
            role_ids.add(source_id)
            all_reuse_ids.add(source_id)
            for field in (
                "source_run_spec_hash",
                "source_workload_spec_hash",
                "source_cluster_sha256",
                "source_simulation_sha256",
                "source_environment_sha256",
                "source_common_hpa_hash",
            ):
                _require(
                    HASH_RE.fullmatch(str(entry.get(field))) is not None,
                    f"{entry_prefix}.{field} is invalid",
                )
            _require(
                entry.get("source_experiment_id") == "E1"
                and entry.get("source_topology") == "heterogeneous"
                and entry.get("source_node_count") == 20
                and entry.get("source_load_scale") == 1.0
                and entry.get("target_experiment_id") == role
                and entry.get("reuse_rule_id") == expected_role_rules[role]
                and entry.get("source_method")
                and entry.get("source_load") in {"low", "middle", "high"}
                and SEED_RE.fullmatch(str(entry.get("source_seed"))) is not None,
                f"{entry_prefix} is not a canonical E1 heterogeneous reuse source",
            )
    _require(
        marker.get("e1_reuse_projection_count") == 260
        and marker.get("e1_reuse_unique_source_run_count") == 210,
        f"{prefix} E1 reuse projection counts are inconsistent",
    )
    _require(
        len(all_reuse_ids) == 210,
        f"{prefix} E1 reuse source identity count is inconsistent",
    )

    dependencies: dict[str, dict[str, Any]] = {}
    for run in runs:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], dependency)
    expected_dependencies = [dependencies[key] for key in sorted(dependencies)]
    _require(
        manifest.get("reference_build_dependencies") == expected_dependencies,
        f"{prefix} reference dependencies were not recomputed",
    )
    _require(
        marker.get("selected_physical_run_count") == 280
        and marker.get("selected_physical_cell_count") == 28
        and marker.get("reference_build_count") == len(expected_dependencies),
        f"{prefix} selected counts are inconsistent",
    )
    cells = {(run["experiment_id"], run["cell_id"]) for run in runs}
    by_experiment = {
        f"E{index}": {
            "new_cells": sum(item[0] == f"E{index}" for item in cells),
            "new_runs": sum(run["experiment_id"] == f"E{index}" for run in runs),
            "reuse_entries": sum(
                entry["experiment_id"] == f"E{index}"
                for entry in manifest["reuse_analyses"]
            ),
        }
        for index in range(1, 10)
    }
    _require(
        manifest.get("matrix_summary")
        == {
            "new_cells": len(cells),
            "new_runs": len(runs),
            "by_experiment": by_experiment,
        },
        f"{prefix} matrix_summary does not match selected runs",
    )


def _validate_formal_e5_e6_extension_shard(manifest: dict[str, Any]) -> None:
    """Validate the preregistered E11--E20 E5/E6/E7 second bank."""

    marker_name = "formal_e5_e6_ci_extension_shard"
    marker = manifest.get(marker_name)
    if marker is None:
        return
    prefix = marker_name
    _require(isinstance(marker, dict), f"{prefix} must be an object")
    _require(
        marker.get("schema_version") == "NSE_FORMAL_E5_E6_E7_CI_EXTENSION_SHARD_V1",
        f"{prefix} has an unsupported schema_version",
    )
    _require(
        manifest.get("formal_results_eligible") is True
        and manifest.get("seed_stage") == "ci_extension",
        f"{prefix} requires an eligible ci_extension manifest",
    )
    _require(
        "integration_smoke_shard" not in manifest,
        f"{prefix} cannot contain an integration smoke marker",
    )
    source = marker.get("source_manifest")
    _require(isinstance(source, dict), f"{prefix}.source_manifest must be an object")
    for field in ("manifest_hash", "file_sha256"):
        _require(
            HASH_RE.fullmatch(str(source.get(field))) is not None,
            f"{prefix} source {field} is invalid",
        )
    _require(
        source.get("seed_stage") == "ci_extension"
        and source.get("protocol_id") == manifest["protocol_id"]
        and source.get("run_count")
        == sum(FULL_MATRIX_RUN_COUNTS_BY_STAGE["ci_extension"].values()),
        f"{prefix} source is not the complete ci_extension frozen matrix",
    )

    runs = manifest["runs"]
    observed_counts = Counter(run["experiment_id"] for run in runs)
    _require(
        observed_counts == {"E5": 120, "E6": 40, "E7": 120} and len(runs) == 280,
        f"{prefix} physical run counts are not E5=120/E6=40/E7=120",
    )
    expected_seeds = FORMAL_E1_SEEDS_BY_STAGE["ci_extension"]
    ablations = {
        "no_heterogeneity",
        "no_externality",
        "no_pricing",
        "no_coordination",
    }
    e6_methods = {"cp_br", "onsocmax"}
    e7_variants = {"price_minus", "price_plus", "quality_minus", "quality_plus"}
    expected_physical = (
        {
            ("E5", "sche_nash", variant, load, seed)
            for variant in ablations
            for load in FORMAL_E1_LOADS
            for seed in expected_seeds
        }
        | {
            ("E6", method, "full", load, seed)
            for method in e6_methods
            for load in ("middle", "high")
            for seed in expected_seeds
        }
        | {
            ("E7", "sche_nash", variant, load, seed)
            for variant in e7_variants
            for load in FORMAL_E1_LOADS
            for seed in expected_seeds
        }
    )
    current_by_stable: dict[tuple[str, str], dict[str, Any]] = {}
    physical_keys: set[tuple[str, str, str, str, str]] = set()
    for run in runs:
        experiment = run["experiment_id"]
        key = (
            experiment,
            run["method"],
            run.get("variant", "full"),
            run["workload"]["request_freq"],
            run["seed"],
        )
        _require(key not in physical_keys, f"{prefix} repeats physical run {key}")
        physical_keys.add(key)
        stable = (run["cell_id"], run["seed"])
        _require(
            stable not in current_by_stable, f"{prefix} repeats cell/seed {stable}"
        )
        current_by_stable[stable] = run
        _require(
            run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
            and run["workload"].get("topology") == "heterogeneous"
            and run["workload"].get("arrival_profile") == "steady"
            and run["workload"].get("qos_profile") == "mixed"
            and run["workload"].get("load_scale") == 1.0,
            f"{prefix} run {run['run_id']} changes the common E5/E6/E7 runtime",
        )
        if experiment == "E5":
            _require(
                run["method"] == "sche_nash"
                and run.get("variant") in ablations
                and run["workload"]["request_freq"] in FORMAL_E1_LOADS,
                f"{prefix} has malformed E5 run",
            )
        elif experiment == "E6":
            _require(
                run["method"] in e6_methods
                and run.get("variant") == "full"
                and run["workload"]["request_freq"] in {"middle", "high"},
                f"{prefix} has malformed E6 run",
            )
        else:
            _require(
                run["method"] == "sche_nash"
                and run.get("variant") in e7_variants
                and run["workload"]["request_freq"] in FORMAL_E1_LOADS,
                f"{prefix} has malformed E7 run",
            )
    _require(
        physical_keys == expected_physical,
        f"{prefix} does not contain the exact E11--E20 Cartesian product",
    )

    expected_selection = {
        "experiment_ids": ["E5", "E6", "E7"],
        "physical_runs": {
            "E5": {
                "variants": [
                    "no_heterogeneity",
                    "no_externality",
                    "no_pricing",
                    "no_coordination",
                ],
                "loads": list(FORMAL_E1_LOADS),
                "seeds": list(expected_seeds),
            },
            "E6": {
                "methods": ["cp_br", "onsocmax"],
                "loads": ["middle", "high"],
                "seeds": list(expected_seeds),
            },
            "E7": {
                "axial_neighbours_per_load": 4,
                "loads": list(FORMAL_E1_LOADS),
                "seeds": list(expected_seeds),
            },
        },
        "common_cluster": {"node_count": 20, "topology": "heterogeneous"},
        "e7_extension_run_count": 120,
    }
    _require(
        marker.get("selection") == expected_selection,
        f"{prefix}.selection is not the frozen E5/E6/E7 second-bank product",
    )

    expected_rules = [
        {"rule_id": entry.get("rule_id"), "rule_sha256": entry.get("rule_sha256")}
        for entry in manifest["reuse_analyses"]
    ]
    _require(
        marker.get("sealed_reuse_rules") == expected_rules,
        f"{prefix} did not preserve all sealed reuse rules",
    )
    expected_role_rules = {
        "E5": "E5_FULL_FROM_E1_NSESCHE_V1",
        "E6": "E6_ORIGINAL_METHODS_FROM_E1_V1",
        "E7": "E7_CENTRES_FROM_E1_NSESCHE_V1",
    }
    sealed_role_rules = marker.get("sealed_e1_reuse_rules")
    _require(
        isinstance(sealed_role_rules, dict)
        and set(sealed_role_rules) == set(expected_role_rules),
        f"{prefix} role reuse rules are missing or contain extra roles",
    )
    for role, rule_id in expected_role_rules.items():
        matching = [item for item in expected_rules if item["rule_id"] == rule_id]
        _require(
            len(matching) == 1 and sealed_role_rules.get(role) == matching[0],
            f"{prefix} sealed {role} reuse rule is missing or changed",
        )

    lineage = marker.get("selected_source_runs")
    _require(
        isinstance(lineage, list) and len(lineage) == 280,
        f"{prefix} physical lineage is incomplete",
    )
    lineage_stable: set[tuple[str, str]] = set()
    lineage_ids: set[str] = set()
    for index, entry in enumerate(lineage):
        entry_prefix = f"{prefix}.selected_source_runs[{index}]"
        _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
        source_id = entry.get("source_run_id")
        _require(
            isinstance(source_id, str)
            and RUN_ID_RE.fullmatch(source_id) is not None
            and source_id not in lineage_ids,
            f"{entry_prefix}.source_run_id is invalid or duplicated",
        )
        lineage_ids.add(source_id)
        for field in (
            "source_run_spec_hash",
            "source_workload_spec_hash",
            "source_cluster_sha256",
            "source_simulation_sha256",
            "source_environment_sha256",
            "source_common_hpa_hash",
        ):
            _require(
                HASH_RE.fullmatch(str(entry.get(field))) is not None,
                f"{entry_prefix}.{field} is invalid",
            )
        stable = (entry.get("source_cell_id"), entry.get("source_seed"))
        _require(
            stable not in lineage_stable, f"{entry_prefix} repeats a source cell/seed"
        )
        lineage_stable.add(stable)
        current = current_by_stable.get(stable)
        _require(current is not None, f"{entry_prefix} has no current physical run")
        _require(
            current.get("method") == entry.get("source_method")
            and current.get("variant", "full") == entry.get("source_variant")
            and current.get("workload_spec_hash")
            == entry.get("source_workload_spec_hash")
            and current.get("workload_tape", {}).get("key")
            == entry.get("source_workload_tape_key")
            and object_hash(current.get("cluster"))
            == entry.get("source_cluster_sha256")
            and object_hash(current.get("simulation"))
            == entry.get("source_simulation_sha256")
            and object_hash(current.get("environment"))
            == entry.get("source_environment_sha256")
            and current.get("common_hpa_hash") == entry.get("source_common_hpa_hash"),
            f"{entry_prefix} differs from the current physical run after binding",
        )
    _require(
        lineage_stable == set(current_by_stable),
        f"{prefix} physical lineage coverage differs",
    )

    expected_reuse_counts = {"E5": 30, "E6": 200, "E7": 30}
    reuse = marker.get("e1_reuse_lineage")
    _require(
        isinstance(reuse, dict) and set(reuse) == set(expected_reuse_counts),
        f"{prefix} E1 reuse lineage roles differ",
    )
    expected_reuse_keys = {
        "E5": {
            ("sche_nash", load, seed)
            for load in FORMAL_E1_LOADS
            for seed in expected_seeds
        },
        "E6": {
            (method, load, seed)
            for method in FORMAL_E1_METHODS
            for load in ("middle", "high")
            for seed in expected_seeds
        },
        "E7": {
            ("sche_nash", load, seed)
            for load in FORMAL_E1_LOADS
            for seed in expected_seeds
        },
    }
    all_reuse_ids: set[str] = set()
    for role, expected_count in expected_reuse_counts.items():
        rows = reuse.get(role)
        _require(
            isinstance(rows, list) and len(rows) == expected_count,
            f"{prefix} {role} reuse lineage count mismatch",
        )
        role_ids: set[str] = set()
        role_keys: set[tuple[str, str, str]] = set()
        for index, entry in enumerate(rows):
            entry_prefix = f"{prefix}.e1_reuse_lineage.{role}[{index}]"
            _require(isinstance(entry, dict), f"{entry_prefix} must be an object")
            source_id = entry.get("source_run_id")
            _require(
                isinstance(source_id, str)
                and RUN_ID_RE.fullmatch(source_id) is not None
                and source_id not in role_ids,
                f"{entry_prefix}.source_run_id is invalid or duplicated",
            )
            role_ids.add(source_id)
            all_reuse_ids.add(source_id)
            for field in (
                "source_run_spec_hash",
                "source_workload_spec_hash",
                "source_cluster_sha256",
                "source_simulation_sha256",
                "source_environment_sha256",
                "source_common_hpa_hash",
            ):
                _require(
                    HASH_RE.fullmatch(str(entry.get(field))) is not None,
                    f"{entry_prefix}.{field} is invalid",
                )
            key = (
                str(entry.get("source_method", "")),
                str(entry.get("source_load", "")),
                str(entry.get("source_seed", "")),
            )
            _require(key not in role_keys, f"{entry_prefix} repeats a source key")
            role_keys.add(key)
            _require(
                entry.get("source_experiment_id") == "E1"
                and entry.get("source_topology") == "heterogeneous"
                and entry.get("source_node_count") == 20
                and entry.get("source_load_scale") == 1.0
                and entry.get("target_experiment_id") == role
                and entry.get("reuse_rule_id") == expected_role_rules[role]
                and entry.get("source_variant") == "full"
                and entry.get("source_seed") in expected_seeds,
                f"{entry_prefix} is not a canonical E1 heterogeneous extension source",
            )
        _require(
            role_keys == expected_reuse_keys[role],
            f"{prefix} {role} reuse lineage is not the exact E11--E20 product",
        )
    _require(
        marker.get("e1_reuse_projection_count") == 260
        and marker.get("e1_reuse_unique_source_run_count") == 210,
        f"{prefix} E1 reuse projection counts are inconsistent",
    )
    _require(
        len(all_reuse_ids) == 210,
        f"{prefix} E1 reuse source identity count is inconsistent",
    )

    dependencies: dict[str, dict[str, Any]] = {}
    for run in runs:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], dependency)
    expected_dependencies = [dependencies[key] for key in sorted(dependencies)]
    _require(
        len(expected_dependencies) == 250
        and manifest.get("reference_build_dependencies") == expected_dependencies,
        f"{prefix} reference dependencies were not recomputed",
    )
    no_coordination = [
        run
        for run in runs
        if run["experiment_id"] == "E5" and run.get("variant") == "no_coordination"
    ]
    _require(
        len(no_coordination) == 30
        and all(
            run.get("reference_policy", {}).get("status") == "not_required"
            and run.get("reference_dependency") is None
            for run in no_coordination
        ),
        f"{prefix} no_coordination runs must not request references",
    )
    _require(
        marker.get("selected_physical_run_count") == 280
        and marker.get("selected_physical_cell_count") == 28
        and marker.get("reference_build_count") == 250,
        f"{prefix} selected counts are inconsistent",
    )
    cells = {(run["experiment_id"], run["cell_id"]) for run in runs}
    by_experiment = {
        f"E{index}": {
            "new_cells": sum(item[0] == f"E{index}" for item in cells),
            "new_runs": sum(run["experiment_id"] == f"E{index}" for run in runs),
            "reuse_entries": sum(
                entry["experiment_id"] == f"E{index}"
                for entry in manifest["reuse_analyses"]
            ),
        }
        for index in range(1, 10)
    }
    _require(
        manifest.get("matrix_summary")
        == {
            "new_cells": 28,
            "new_runs": 280,
            "by_experiment": by_experiment,
        },
        f"{prefix} matrix_summary does not match selected runs",
    )


def validate_manifest(manifest: dict[str, Any], *, check_hash: bool = True) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "created_at",
        "phase",
        "bank_id",
        "fixed_seed_bank",
        "method_versions",
        "old_pdf_alignment",
        "runtime_identity_policy",
        "seed_stage",
        "ci_extension_requires_trigger",
        "common_hpa",
        "common_hpa_hash",
        "execution",
        "qc",
        "runs",
        "reference_build_dependencies",
        "all_faasrank_models_bound",
        "all_sla_targets_bound",
        "reuse_analyses",
        "manifest_hash",
    }
    missing = sorted(required - manifest.keys())
    _require(not missing, f"manifest is missing: {', '.join(missing)}")
    _require(manifest["schema_version"] == "1.0", "unsupported manifest schema_version")
    _require(
        manifest["protocol_id"] == FORMAL_PROTOCOL_ID,
        "unsupported protocol_id; regenerate the manifest with the frozen workload-profile protocol",
    )
    formal_profile_protocol = True
    workload_profiles: dict[str, Any] = {}
    if formal_profile_protocol:
        _require(
            "workload_profile_set" in manifest
            and "workload_profile_set_hash" in manifest,
            "frozen-profile protocol manifest lacks workload_profile_set binding",
        )
        workload_profiles = _validate_workload_profile_set(
            manifest["workload_profile_set"], manifest["workload_profile_set_hash"]
        )
    _require(
        manifest["seed_stage"] in {"initial", "ci_extension", "all", "development"},
        "invalid seed_stage",
    )
    _require(
        manifest["ci_extension_requires_trigger"] is False,
        "formal execution may not depend on a result-conditioned extension trigger",
    )
    _require(
        manifest["phase"] in {"pilot", "development", "qualification", "formal"},
        "invalid experiment phase",
    )
    _require(
        isinstance(manifest["bank_id"], str) and bool(manifest["bank_id"]),
        "bank_id must be a non-empty string",
    )
    if manifest.get("formal_results_eligible") is True:
        _require(
            manifest["phase"] == "formal",
            "only phase=formal may be formal-results eligible",
        )
    if manifest["phase"] == "formal":
        _require(
            manifest["bank_id"] == FORMAL_BANK_IDS[manifest["seed_stage"]],
            "formal bank_id does not match seed_stage",
        )
    if "integration_smoke_shard" in manifest:
        _require(
            manifest["phase"] == "pilot"
            and manifest["bank_id"] == "TSCv1.pilot.integration-smoke"
            and manifest.get("formal_results_eligible") is False,
            "integration smoke manifests must remain pilot-only",
        )
    fixed_bank = manifest["fixed_seed_bank"]
    if manifest["seed_stage"] == "development":
        is_guard_bank = any(marker in manifest for marker in M1_GUARD_MARKERS)
        is_dynamic_bank = any(marker in manifest for marker in M1_DYNAMIC_MARKERS)
        is_g1_technical = "g1_corrected_runtime_technical_replay" in manifest
        is_g1_screen = "g1_corrected_runtime_screen" in manifest
        if is_g1_technical:
            expected_policy = G1_CORRECTED_TECHNICAL_SAMPLE_POLICY
            expected_all_seeds = G1_CORRECTED_TECHNICAL_SEEDS
        elif is_g1_screen:
            expected_policy = G1_CORRECTED_SCREEN_SAMPLE_POLICY
            expected_all_seeds = G1_CORRECTED_SCREEN_SEEDS
        elif is_dynamic_bank:
            expected_policy = M1_DYNAMIC_SAMPLE_POLICY
            expected_all_seeds = M1_DYNAMIC_SEEDS
        elif is_guard_bank:
            expected_policy = M1_GUARD_SAMPLE_POLICY
            expected_all_seeds = M1_GUARD_SEEDS
        else:
            expected_policy = M1_DEVELOPMENT_SAMPLE_POLICY
            expected_all_seeds = M1_DEVELOPMENT_SEEDS
        selected_seeds = (
            fixed_bank.get("selected_seeds") if isinstance(fixed_bank, dict) else None
        )
        _require(
            isinstance(fixed_bank, dict)
            and fixed_bank.get("policy") == expected_policy
            and fixed_bank.get("all_seeds") == list(expected_all_seeds)
            and isinstance(selected_seeds, list)
            and bool(selected_seeds)
            and len(selected_seeds) == len(set(selected_seeds))
            and set(selected_seeds).issubset(expected_all_seeds)
            and fixed_bank.get("paired_across_methods") is True
            and fixed_bank.get("result_conditioned_extension") is False,
            "fixed_seed_bank does not bind the M1 development seed policy",
        )
    else:
        all_seeds = list(FORMAL_E1_SEEDS_BY_STAGE["all"])
        selected_seeds = list(FORMAL_E1_SEEDS_BY_STAGE[manifest["seed_stage"]])
        _require(
            isinstance(fixed_bank, dict)
            and fixed_bank.get("policy") == FIXED_SAMPLE_POLICY
            and fixed_bank.get("all_seeds") == all_seeds
            and fixed_bank.get("selected_seeds") == selected_seeds
            and fixed_bank.get("paired_across_methods") is True
            and fixed_bank.get("result_conditioned_extension") is False,
            "fixed_seed_bank does not bind the preregistered paired n=20 policy",
        )
    _require(
        manifest["method_versions"] == FORMAL_METHOD_VERSIONS,
        "method_versions do not match the frozen method implementations",
    )
    alignment = manifest["old_pdf_alignment"]
    _require(
        alignment == OLD_PDF_ALIGNMENT,
        "old_pdf_alignment does not match the frozen manuscript",
    )
    _require(
        manifest["runtime_identity_policy"] == RUNTIME_IDENTITY_POLICY,
        "runtime_identity_policy is invalid",
    )
    _require(
        manifest["execution"].get("max_attempts") == 3,
        "manifest max_attempts must equal 3",
    )
    _require(
        HASH_RE.fullmatch(str(manifest["common_hpa_hash"])) is not None,
        "invalid common_hpa_hash",
    )
    _require(
        object_hash(manifest["common_hpa"]) == manifest["common_hpa_hash"],
        "common_hpa_hash does not match common_hpa",
    )
    _require(isinstance(manifest["runs"], list), "runs must be an array")
    _validate_analysis_reuse_rules(
        manifest["reuse_analyses"], formal_required=manifest["phase"] == "formal"
    )
    _validate_qc_policy(manifest["qc"], "qc")
    _validate_integration_smoke_shard(manifest)

    run_ids: set[str] = set()
    run_keys: set[tuple[str, str]] = set()
    for index, run in enumerate(manifest["runs"]):
        prefix = f"runs[{index}]"
        for key in (
            "run_id",
            "run_spec_hash",
            "cell_id",
            "experiment_id",
            "method",
            "method_version",
            "seed",
            "seeds",
            "workload",
            "workload_spec_hash",
            "workload_tape",
            "cluster",
            "common_hpa",
            "common_hpa_hash",
            "simulation",
            "simulator_experiment",
            "environment",
            "artifact_hashes",
        ):
            _require(key in run, f"{prefix} missing {key}")
        if formal_profile_protocol:
            _require("workload_profile" in run, f"{prefix} missing workload_profile")
        _require(
            RUN_ID_RE.fullmatch(run["run_id"]) is not None,
            f"{prefix} has invalid run_id",
        )
        _require(run["run_id"] not in run_ids, f"duplicate run_id {run['run_id']}")
        run_ids.add(run["run_id"])
        _require(
            run["experiment_id"] in {f"E{i}" for i in range(1, 8)},
            f"{prefix} has invalid experiment_id",
        )
        _require(
            SEED_RE.fullmatch(run["seed"]) is not None, f"{prefix} has invalid seed"
        )
        _require(
            run["method_version"] == manifest["method_versions"].get(run["method"]),
            f"{prefix} method_version does not match the manifest",
        )
        _require(
            run["common_hpa_hash"] == manifest["common_hpa_hash"],
            f"{prefix} changes common HPA",
        )
        _require(
            run["common_hpa"] == manifest["common_hpa"],
            f"{prefix} embeds a different common HPA",
        )
        _require(
            object_hash(run["common_hpa"]) == run["common_hpa_hash"],
            f"{prefix} has invalid common HPA content",
        )
        workload_hash_payload = {"seed": run["seed"], "workload": run["workload"]}
        if formal_profile_protocol:
            load = run["workload"].get("request_freq")
            _require(
                load in workload_profiles
                and run["workload_profile"] == workload_profiles[load],
                f"{prefix} workload profile does not match its load binding",
            )
            workload_hash_payload["workload_profile"] = run["workload_profile"]
        _require(
            object_hash(workload_hash_payload) == run["workload_spec_hash"],
            f"{prefix} has invalid workload_spec_hash",
        )
        tape = run["workload_tape"]
        _require(
            isinstance(tape, dict) and isinstance(tape.get("key"), str),
            f"{prefix} has invalid workload_tape",
        )
        for field in (
            "kind",
            "path",
            "sha256",
            "event_count",
            "parent_key",
            "parent_sha256",
            "transform",
            "runtime_mode",
            "runtime_load_scale",
            "runtime_burst_profile",
            "provenance",
        ):
            _require(field in tape, f"{prefix} workload_tape is missing {field}")
        if formal_profile_protocol:
            _require(
                tape.get("workload_profile") == run["workload_profile"],
                f"{prefix} workload tape profile binding mismatch",
            )
        _require(
            tape["runtime_mode"] == "replay",
            f"{prefix} tape runtime mode must be replay",
        )
        _require(
            tape["runtime_load_scale"] == 1.0,
            f"{prefix} tape runtime load_scale must be 1",
        )
        _require(
            tape["runtime_burst_profile"] == "steady",
            f"{prefix} Rust burst generator must be disabled",
        )
        provenance = tape["provenance"]
        _require(
            isinstance(provenance, dict)
            and provenance.get("source_kind") == "azure_trace_derived_empirical_cdf",
            f"{prefix} workload source provenance is invalid",
        )
        _require(
            "not a direct raw-trace event conversion"
            in str(provenance.get("source_statement")),
            f"{prefix} workload provenance must not claim raw-trace replay",
        )
        artifacts = provenance.get("cdf_artifacts")
        _require(
            isinstance(artifacts, list) and len(artifacts) >= 3,
            f"{prefix} CDF hashes are missing",
        )
        _require(
            all(
                isinstance(item, dict) and HASH_RE.fullmatch(str(item.get("sha256")))
                for item in artifacts
            ),
            f"{prefix} contains an invalid CDF hash",
        )
        if formal_profile_protocol:
            _require(
                provenance.get("frequency_profile") == run["workload_profile"],
                f"{prefix} workload provenance profile binding mismatch",
            )
        if tape.get("sha256") is not None:
            _require(
                HASH_RE.fullmatch(str(tape["sha256"])) is not None,
                f"{prefix} has invalid tape sha256",
            )
        if manifest.get("all_tapes_bound") is True:
            _require(
                HASH_RE.fullmatch(str(tape.get("sha256"))) is not None,
                f"{prefix} bound tape hash is missing",
            )
            _require(
                isinstance(tape.get("event_count"), int) and tape["event_count"] > 0,
                f"{prefix} bound tape is empty",
            )
            measured_rate = provenance.get("measured_arrival_rate_rps")
            _require(
                isinstance(measured_rate, (int, float))
                and not isinstance(measured_rate, bool)
                and measured_rate > 0,
                f"{prefix} bound tape measured rate is missing",
            )
            capture = tape.get("capture_environment")
            _require(
                isinstance(capture, dict),
                f"{prefix} bound tape capture bundle is missing",
            )
            for field in (
                "function_dag_qos_sha256",
                "node_network_sha256",
                "capture_environment_sha256",
                "semantic_bundle_sha256",
            ):
                _require(
                    HASH_RE.fullmatch(str(capture.get(field))) is not None,
                    f"{prefix} capture {field} is invalid",
                )
            for field in ("function_count", "node_count"):
                _require(
                    isinstance(capture.get(field), int)
                    and not isinstance(capture.get(field), bool)
                    and capture[field] > 0,
                    f"{prefix} capture {field} must be a positive integer",
                )
            semantic_payload = {
                field: capture[field]
                for field in (
                    "function_dag_qos_sha256",
                    "node_network_sha256",
                    "capture_environment_sha256",
                    "function_count",
                    "node_count",
                )
            }
            _require(
                object_hash(semantic_payload) == capture["semantic_bundle_sha256"],
                f"{prefix} capture semantic_bundle_sha256 does not bind its environment fields",
            )
            _require(
                isinstance(tape.get("capture_receipt_path"), str)
                and bool(tape["capture_receipt_path"]),
                f"{prefix} capture receipt path is missing",
            )
            _require(
                HASH_RE.fullmatch(str(tape.get("capture_receipt_sha256"))) is not None,
                f"{prefix} capture receipt hash is invalid",
            )
        experiment = run["simulator_experiment"]
        _require(
            isinstance(experiment, dict), f"{prefix} has invalid simulator_experiment"
        )
        if formal_profile_protocol:
            _require(
                experiment.get("protocol_version") == "reviewer-v3",
                f"{prefix} has an obsolete Rust protocol_version",
            )
        _validate_simulation(run["simulation"], f"{prefix}.simulation")
        _require(
            experiment.get("run_id") == run["run_id"],
            f"{prefix} simulator run_id mismatch",
        )
        _require(
            run["seeds"]
            == {
                "workload_seed": experiment.get("workload_seed"),
                "topology_seed": experiment.get("topology_seed"),
                "algorithm_seed": experiment.get("algorithm_seed"),
            }
            == {
                "workload_seed": run["seed"],
                "topology_seed": run["seed"],
                "algorithm_seed": run["seed"],
            },
            f"{prefix} three-seed binding is inconsistent",
        )
        experiment_workload = experiment.get("workload", {})
        if formal_profile_protocol:
            _require(
                experiment_workload.get("frequency_profile") == run["workload_profile"],
                f"{prefix} Rust workload profile binding mismatch",
            )
        _require(
            experiment_workload.get("mode") == "replay", f"{prefix} must replay a tape"
        )
        _require(
            experiment_workload.get("load_scale") == 1.0,
            f"{prefix} runtime load_scale must be 1",
        )
        _require(
            experiment_workload.get("burst_profile") == "steady",
            f"{prefix} runtime burst generation must be disabled",
        )
        _require(
            experiment_workload.get("tape_path") == tape.get("path"),
            f"{prefix} ExperimentConfig tape path mismatch",
        )
        _require(
            experiment_workload.get("arrival_horizon_frames")
            == run["simulation"]["arrival_horizon_frames"],
            f"{prefix} ExperimentConfig arrival_horizon_frames must match run simulation",
        )
        _require(
            isinstance(experiment_workload.get("arrival_horizon_frames"), int)
            and not isinstance(experiment_workload.get("arrival_horizon_frames"), bool)
            and experiment_workload["arrival_horizon_frames"]
            <= run["simulation"]["total_frame"],
            f"{prefix} ExperimentConfig arrival_horizon_frames exceeds total_frame",
        )
        _require(
            experiment.get("ablation")
            == _expected_ablation(run.get("variant", "full")),
            f"{prefix} ablation payload mismatch",
        )
        qos = experiment.get("qos")
        _require(isinstance(qos, dict), f"{prefix} QoS payload is missing")
        qos_targets = (
            "latency_deadline_ms",
            "throughput_target_rps",
            "cost_budget_per_request",
        )
        if run["workload"].get("qos_profile") == "balanced":
            _require(
                qos.get("enabled") is True, f"{prefix} balanced QoS must be enabled"
            )
            _require(
                qos.get("class_assignment") == "balanced",
                f"{prefix} balanced QoS class assignment is invalid",
            )
            if manifest.get("all_sla_targets_bound") is True:
                for field in qos_targets:
                    value = qos.get(field)
                    _require(
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(float(value))
                        and value > 0,
                        f"{prefix} frozen QoS target {field} is invalid",
                    )
                sla_binding = run.get("sla_targets")
                _require(
                    isinstance(sla_binding, dict)
                    and sla_binding.get("schema_version") == "NSE_SLA_TARGET_BINDING_V1"
                    and sla_binding.get("state") == "frozen",
                    f"{prefix} SLA target binding is missing",
                )
                for field in (
                    "artifact_sha256",
                    "document_sha256",
                    "targets_sha256",
                    "source_bundle_sha256",
                ):
                    _require(
                        HASH_RE.fullmatch(str(sla_binding.get(field))) is not None,
                        f"{prefix} SLA binding {field} is invalid",
                    )
                _require(
                    isinstance(sla_binding.get("artifact_path"), str)
                    and bool(sla_binding["artifact_path"])
                    and isinstance(sla_binding.get("artifact_bytes"), int)
                    and not isinstance(sla_binding.get("artifact_bytes"), bool)
                    and sla_binding["artifact_bytes"] > 0,
                    f"{prefix} SLA artifact path/size is invalid",
                )
            else:
                _require(
                    all(qos.get(field) is None for field in qos_targets)
                    and "sla_targets" not in run,
                    f"{prefix} has SLA values that were not bound through a frozen artifact",
                )
        else:
            _require(
                qos.get("enabled") is False,
                f"{prefix} mixed legacy QoS must be disabled",
            )
        if run["experiment_id"] == "E7":
            parameters = run.get("metadata", {}).get("nash_parameters")
            _require(
                isinstance(parameters, dict), f"{prefix} E7 nash parameters are missing"
            )
            _require(
                experiment.get("nash", {}).get("price_feedback_rate")
                == parameters.get("price_feedback_rate"),
                f"{prefix} E7 price field mismatch",
            )
            _require(
                experiment.get("nash", {}).get("quality_weight")
                == parameters.get("quality_weight"),
                f"{prefix} E7 quality field mismatch",
            )
        nash_without_coordination = (
            run["method"] == "sche_nash" and run.get("variant") == "no_coordination"
        )
        e6_welfare_comparator = run["experiment_id"] == "E6" and run["method"] in {
            "cp_br",
            "onsocmax",
        }
        reference_required = (
            run["method"] == "sche_nash" and not nash_without_coordination
        ) or e6_welfare_comparator
        if nash_without_coordination:
            policy = run.get("reference_policy")
            _require(
                isinstance(policy, dict)
                and policy.get("status") == "not_required"
                and policy.get("build_required") is False,
                f"{prefix} no_coordination must explicitly declare that no reference build applies",
            )
            _require(
                experiment.get("reference", {}).get("mode") == "not_required",
                f"{prefix} no_coordination must use Rust reference.mode=not_required",
            )
        if reference_required:
            dependency = run.get("reference_dependency")
            _require(
                isinstance(dependency, dict),
                f"{prefix} welfare reference dependency is missing",
            )
            _require(
                experiment.get("reference", {}).get("mode") == "offline_required",
                f"{prefix} welfare evaluation must fail closed on offline reference",
            )
            _require(
                experiment.get("reference", {}).get("table_path")
                == dependency.get("path"),
                f"{prefix} reference path mismatch",
            )
            if manifest.get("all_references_bound") is True:
                for field in (
                    "sha256",
                    "receipt_sha256",
                    "state_pair_sequence_sha256",
                    "assignment_sequence_sha256",
                    "build_process_observation_sha256",
                ):
                    _require(
                        HASH_RE.fullmatch(str(dependency.get(field))) is not None,
                        f"{prefix} bound reference {field} is invalid",
                    )
                _require(
                    dependency.get("build_required") is False,
                    f"{prefix} bound reference still requires a build",
                )
                _require(
                    isinstance(dependency.get("build_completed"), int)
                    and dependency["build_completed"] >= 0,
                    f"{prefix} build completed counter is invalid",
                )
        if run["method"] == "sche_FaaSRank":
            binding = run.get("baseline_model")
            _require(
                isinstance(binding, dict), f"{prefix} FaaSRank model binding is missing"
            )
            if manifest.get("all_faasrank_models_bound") is True:
                for field in (
                    "artifact_path",
                    "artifact_sha256",
                    "artifact_bytes",
                    "training_tape_sha256",
                    "created_at",
                    "provenance",
                ):
                    _require(
                        field in binding,
                        f"{prefix} frozen FaaSRank binding is missing {field}",
                    )
                _require(
                    binding.get("schema_version") == "NSE_FAASRANK_MODEL_BINDING_V1"
                    and binding.get("state") == "frozen",
                    f"{prefix} FaaSRank binding is not frozen",
                )
                _require(
                    isinstance(binding.get("artifact_path"), str)
                    and bool(binding["artifact_path"]),
                    f"{prefix} FaaSRank artifact_path is invalid",
                )
                _require(
                    HASH_RE.fullmatch(str(binding.get("artifact_sha256"))) is not None,
                    f"{prefix} FaaSRank artifact SHA-256 is invalid",
                )
                _require(
                    HASH_RE.fullmatch(str(binding.get("training_tape_sha256")))
                    is not None,
                    f"{prefix} FaaSRank training-tape SHA-256 is invalid",
                )
                _require(
                    isinstance(binding.get("artifact_bytes"), int)
                    and not isinstance(binding.get("artifact_bytes"), bool)
                    and binding["artifact_bytes"] > 0,
                    f"{prefix} FaaSRank artifact size is invalid",
                )
                _require(
                    binding["training_tape_sha256"] != tape.get("sha256"),
                    f"{prefix} FaaSRank training and evaluation tapes are not disjoint",
                )
                rust_model = experiment.get("faasrank_model")
                _require(
                    isinstance(rust_model, dict)
                    and rust_model.get("state") == "frozen"
                    and rust_model.get("model_sha256") == binding["artifact_sha256"]
                    and rust_model.get("training_tape_sha256")
                    == binding["training_tape_sha256"],
                    f"{prefix} Rust FaaSRank model payload differs from its binding",
                )
            else:
                _require(
                    binding == {"state": "unbound"},
                    f"{prefix} unbound FaaSRank run has an unexpected model payload",
                )
                _require(
                    experiment.get("faasrank_model", {}).get("state")
                    == "legacy_default",
                    f"{prefix} unbound FaaSRank run must remain fail-closed for formal execution",
                )
        reference = run.get("reference_dependency")
        _require(
            run["artifact_hashes"]
            == {
                "workload_tape_sha256": tape.get("sha256"),
                "simulator_config_sha256": object_hash(experiment),
                "offline_reference_sha256": (
                    reference.get("sha256") if isinstance(reference, dict) else None
                ),
            },
            f"{prefix} artifact_hashes do not match the frozen inputs",
        )
        run_key = (run["cell_id"], run["seed"])
        _require(run_key not in run_keys, f"duplicate cell/seed pair {run_key}")
        run_keys.add(run_key)
        expected_run_hash = _hash_without(run, "run_spec_hash")
        _require(
            expected_run_hash == run["run_spec_hash"],
            f"{prefix} has invalid run_spec_hash",
        )

    _validate_m1_nonformal_manifest(manifest)
    _validate_formal_e1_shard(manifest, topology="homogeneous")
    _validate_formal_e1_shard(manifest, topology="heterogeneous")
    _validate_formal_e2_shard(manifest)
    _validate_formal_e3_e4_shard(manifest)
    _validate_formal_e3_e4_extension_shard(manifest)
    _validate_formal_e5_e6_e7_shard(manifest)
    _validate_formal_e5_e6_extension_shard(manifest)

    analysis_ids = {entry.get("experiment_id") for entry in manifest["reuse_analyses"]}
    if manifest["phase"] == "formal":
        _require(
            {"E8", "E9"}.issubset(analysis_ids),
            "E8 and E9 must be reuse-only analyses",
        )
    _require(
        not any(run["experiment_id"] in {"E8", "E9"} for run in manifest["runs"]),
        "E8/E9 must not create runs",
    )
    if check_hash:
        _require(
            HASH_RE.fullmatch(str(manifest["manifest_hash"])) is not None,
            "invalid manifest_hash",
        )
        _require(
            _hash_without(manifest, "manifest_hash") == manifest["manifest_hash"],
            "manifest_hash does not match content",
        )


def _validate_m1_nonformal_manifest(manifest: dict[str, Any]) -> None:
    present = [marker for marker in M1_NONFORMAL_MARKERS if marker in manifest]
    if not present:
        return
    _require(len(present) == 1, "exactly one M1 non-formal marker is required")
    marker_name = present[0]
    marker = manifest[marker_name]
    _require(isinstance(marker, dict), f"{marker_name} must be an object")
    _require(
        manifest["seed_stage"] == "development"
        and manifest.get("formal_results_eligible") is False,
        f"{marker_name} must use the non-formal development seed stage",
    )
    expected_phase = (
        "qualification"
        if marker_name
        in {
            "m1_qualification_shard",
            "m1_completion_guard_qualification_shard",
            "m1_dynamic_contention_qualification_shard",
        }
        else "development"
    )
    _require(
        manifest["phase"] == expected_phase,
        f"{marker_name} has the wrong experiment phase",
    )
    schema_versions = {
        "m1_development_matrix": "NSE_M1_DEVELOPMENT_MATRIX_V1",
        "m1_candidate_screen_shard": "NSE_M1_CANDIDATE_SCREEN_SHARD_V1",
        "m1_qualification_shard": "NSE_M1_QUALIFICATION_SHARD_V1",
        "m1_mechanism_diagnosis_shard": "NSE_M1_MECHANISM_DIAGNOSIS_SHARD_V1",
        "m1_completion_guard_matrix": "NSE_M1_COMPLETION_GUARD_MATRIX_V1",
        "m1_completion_guard_screen_shard": ("NSE_M1_COMPLETION_GUARD_SCREEN_SHARD_V1"),
        "m1_completion_guard_qualification_shard": (
            "NSE_M1_COMPLETION_GUARD_QUALIFICATION_SHARD_V1"
        ),
        "m1_dynamic_contention_matrix": "NSE_M1_DYNAMIC_CONTENTION_MATRIX_V1",
        "m1_dynamic_contention_screen_shard": (
            "NSE_M1_DYNAMIC_CONTENTION_SCREEN_SHARD_V1"
        ),
        "m1_dynamic_contention_qualification_shard": (
            "NSE_M1_DYNAMIC_CONTENTION_QUALIFICATION_SHARD_V1"
        ),
        "g1_corrected_runtime_technical_replay": (
            "NSE_G1_CORRECTED_RUNTIME_TECHNICAL_REPLAY_V1"
        ),
        "g1_corrected_runtime_screen": "NSE_G1_CORRECTED_RUNTIME_SCREEN_V1",
    }
    _require(
        marker.get("schema_version") == schema_versions[marker_name],
        f"{marker_name} has an unsupported schema_version",
    )

    guard_candidates = ["ready_order", "guarded_finish_05", "guarded_finish_15"]
    dynamic_candidates = [
        "ready_order",
        "guarded_dynamic_finish_05",
        "guarded_dynamic_finish_15",
    ]
    strict_candidates = ["ready_order", "ready_finish_tie", "formula"]
    if marker_name == "g1_corrected_runtime_technical_replay":
        source = marker.get("source_manifest")
        source_run = marker.get("source_run")
        _require(
            marker.get("technical_only") is True
            and marker.get("selection_eligible") is False
            and marker.get("formal_results_eligible") is False
            and marker.get("candidate") == "ready_order"
            and marker.get("seed") == "D44"
            and marker.get("strict_eq15_required") is True
            and marker.get("utility_guard_relative_regret") == 0.0,
            "G1 technical replay does not preserve its technical-only strict-Eq.15 boundary",
        )
        _require(
            isinstance(source, dict)
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None
            and isinstance(source.get("run_count"), int)
            and source["run_count"] > 0
            and isinstance(source_run, dict)
            and RUN_ID_RE.fullmatch(str(source_run.get("run_id"))) is not None
            and HASH_RE.fullmatch(str(source_run.get("run_spec_hash"))) is not None
            and HASH_RE.fullmatch(str(source_run.get("workload_tape_sha256")))
            is not None,
            "G1 technical replay source provenance is invalid",
        )
        expected_seeds = list(G1_CORRECTED_TECHNICAL_SEEDS)
        expected_run_count = 1
        expected_cell_count = 1
        expected_reference_count = 1
    elif marker_name == "g1_corrected_runtime_screen":
        gate = marker.get("technical_gate")
        rule = marker.get("selection_rule")
        _require(
            marker.get("candidates") == strict_candidates
            and marker.get("control_candidate") == "ready_order"
            and marker.get("loads") == list(FORMAL_E1_LOADS)
            and marker.get("topologies") == ["homogeneous", "heterogeneous"]
            and marker.get("screen_seeds") == list(G1_CORRECTED_SCREEN_SEEDS)
            and marker.get("strict_eq15_required") is True
            and marker.get("utility_guard_relative_regret") == 0.0
            and marker.get("paper_equations_changed") is False,
            "G1 corrected-runtime screen does not bind the frozen strict candidates",
        )
        _require(
            isinstance(gate, dict)
            and isinstance(gate.get("path"), str)
            and bool(gate["path"])
            and HASH_RE.fullmatch(str(gate.get("file_sha256"))) is not None
            and HASH_RE.fullmatch(str(gate.get("document_sha256"))) is not None
            and HASH_RE.fullmatch(str(gate.get("technical_manifest_hash"))) is not None,
            "G1 corrected-runtime screen lacks a frozen technical gate",
        )
        _require(
            isinstance(rule, dict)
            and rule.get("result_conditioned_seed_removal_or_replacement") is False,
            "G1 corrected-runtime selection rule permits result-conditioned seeds",
        )
        expected_seeds = list(G1_CORRECTED_SCREEN_SEEDS)
        expected_run_count = 90
        expected_cell_count = 18
        expected_reference_count = 90
    elif marker_name == "m1_dynamic_contention_matrix":
        expected_seeds = list(M1_DYNAMIC_SEEDS)
        _require(
            marker.get("candidates") == dynamic_candidates
            and marker.get("screen_seeds") == expected_seeds[:5]
            and marker.get("development_seeds") == expected_seeds
            and marker.get("baseline_methods")
            == [method for method in FORMAL_E1_METHODS if method != "sche_nash"]
            and marker.get("control_candidate") == "ready_order"
            and marker.get("qualification_requires_dynamic_winner") is True
            and marker.get("dynamic_contention_term")
            == "state_without_player_assigned_request_count",
            "m1_dynamic_contention_matrix does not bind the frozen family",
        )
        expected_run_count = 1440
        expected_cell_count = 72
        expected_reference_count = 360
    elif marker_name == "m1_dynamic_contention_screen_shard":
        selection = marker.get("selection")
        _require(
            isinstance(selection, dict)
            and selection.get("method") == "sche_nash"
            and selection.get("candidates") == dynamic_candidates
            and selection.get("loads") == list(FORMAL_E1_LOADS)
            and selection.get("topologies") == ["homogeneous", "heterogeneous"]
            and selection.get("seeds") == list(M1_DYNAMIC_SEEDS[:5]),
            "dynamic-contention screen is not the frozen 3x6x5 product",
        )
        source = marker.get("source_manifest")
        _require(
            isinstance(source, dict)
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None
            and source.get("run_count") == 1440,
            "dynamic-contention screen source provenance is invalid",
        )
        expected_seeds = list(M1_DYNAMIC_SEEDS[:5])
        expected_run_count = 90
        expected_cell_count = 18
        expected_reference_count = 90
    elif marker_name == "m1_dynamic_contention_qualification_shard":
        selection = marker.get("selection")
        _require(
            isinstance(selection, dict)
            and selection.get("selected_candidate")
            in {"guarded_dynamic_finish_05", "guarded_dynamic_finish_15"}
            and selection.get("methods") == list(FORMAL_E1_METHODS)
            and selection.get("loads") == list(FORMAL_E1_LOADS)
            and selection.get("topologies") == ["homogeneous", "heterogeneous"]
            and selection.get("seeds") == list(M1_DYNAMIC_SEEDS),
            "dynamic-contention qualification is not the authorized product",
        )
        source = marker.get("source_manifest")
        receipt = marker.get("candidate_selection")
        _require(
            isinstance(source, dict)
            and source.get("run_count") == 1440
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None,
            "dynamic-contention qualification source provenance is invalid",
        )
        _require(
            isinstance(receipt, dict)
            and HASH_RE.fullmatch(str(receipt.get("file_sha256"))) is not None
            and HASH_RE.fullmatch(str(receipt.get("document_sha256"))) is not None,
            "dynamic-contention selection provenance is invalid",
        )
        expected_seeds = list(M1_DYNAMIC_SEEDS)
        expected_run_count = 1200
        expected_cell_count = 60
        expected_reference_count = 120
    elif marker_name == "m1_completion_guard_matrix":
        expected_seeds = list(M1_GUARD_SEEDS)
        _require(
            marker.get("candidates") == guard_candidates
            and marker.get("screen_seeds") == expected_seeds[:5]
            and marker.get("development_seeds") == expected_seeds
            and marker.get("baseline_methods")
            == [method for method in FORMAL_E1_METHODS if method != "sche_nash"]
            and marker.get("control_candidate") == "ready_order"
            and marker.get("qualification_requires_guard_winner") is True,
            "m1_completion_guard_matrix does not bind the frozen family and seeds",
        )
        expected_run_count = 1440
        expected_cell_count = 72
        expected_reference_count = 360
    elif marker_name == "m1_completion_guard_screen_shard":
        selection = marker.get("selection")
        _require(
            isinstance(selection, dict)
            and selection.get("method") == "sche_nash"
            and selection.get("candidates") == guard_candidates
            and selection.get("loads") == list(FORMAL_E1_LOADS)
            and selection.get("topologies") == ["homogeneous", "heterogeneous"]
            and selection.get("seeds") == list(M1_GUARD_SEEDS[:5]),
            "guard screen selection is not the frozen 3x6x5 product",
        )
        source = marker.get("source_manifest")
        _require(
            isinstance(source, dict)
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None
            and source.get("run_count") == 1440,
            "guard screen source provenance is invalid",
        )
        expected_seeds = list(M1_GUARD_SEEDS[:5])
        expected_run_count = 90
        expected_cell_count = 18
        expected_reference_count = 90
    elif marker_name == "m1_completion_guard_qualification_shard":
        selection = marker.get("selection")
        _require(
            isinstance(selection, dict)
            and selection.get("selected_candidate")
            in {"guarded_finish_05", "guarded_finish_15"}
            and selection.get("methods") == list(FORMAL_E1_METHODS)
            and selection.get("loads") == list(FORMAL_E1_LOADS)
            and selection.get("topologies") == ["homogeneous", "heterogeneous"]
            and selection.get("seeds") == list(M1_GUARD_SEEDS),
            "guard qualification is not the authorized ten-method product",
        )
        source = marker.get("source_manifest")
        receipt = marker.get("candidate_selection")
        _require(
            isinstance(source, dict)
            and source.get("run_count") == 1440
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None,
            "guard qualification source provenance is invalid",
        )
        _require(
            isinstance(receipt, dict)
            and HASH_RE.fullmatch(str(receipt.get("file_sha256"))) is not None
            and HASH_RE.fullmatch(str(receipt.get("document_sha256"))) is not None,
            "guard qualification selection provenance is invalid",
        )
        expected_seeds = list(M1_GUARD_SEEDS)
        expected_run_count = 1200
        expected_cell_count = 60
        expected_reference_count = 120
    elif marker_name == "m1_development_matrix":
        expected_seeds = list(M1_DEVELOPMENT_SEEDS)
        expected_candidates = ["formula", "ready_order", "ready_finish_tie"]
        _require(
            marker.get("candidates") == expected_candidates
            and marker.get("screen_seeds") == expected_seeds[:5]
            and marker.get("development_seeds") == expected_seeds
            and marker.get("baseline_methods")
            == [method for method in FORMAL_E1_METHODS if method != "sche_nash"],
            "m1_development_matrix does not bind the frozen candidates and seeds",
        )
        expected_run_count = 1440
        expected_cell_count = 72
        expected_reference_count = 360
    elif marker_name == "m1_candidate_screen_shard":
        selection = marker.get("selection")
        _require(
            isinstance(selection, dict)
            and selection.get("method") == "sche_nash"
            and selection.get("candidates")
            == ["formula", "ready_order", "ready_finish_tie"]
            and selection.get("loads") == list(FORMAL_E1_LOADS)
            and selection.get("topologies") == ["homogeneous", "heterogeneous"]
            and selection.get("seeds") == list(M1_DEVELOPMENT_SEEDS[:5]),
            "m1_candidate_screen_shard selection is not the frozen 3x6x5 product",
        )
        source = marker.get("source_manifest")
        _require(
            isinstance(source, dict)
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None
            and source.get("run_count") == 1440,
            "m1_candidate_screen_shard source provenance is invalid",
        )
        expected_seeds = list(M1_DEVELOPMENT_SEEDS[:5])
        expected_run_count = 90
        expected_cell_count = 18
        expected_reference_count = 90
    elif marker_name == "m1_qualification_shard":
        selection = marker.get("selection")
        _require(
            isinstance(selection, dict)
            and selection.get("selected_candidate")
            in {"formula", "ready_order", "ready_finish_tie"}
            and selection.get("methods") == list(FORMAL_E1_METHODS)
            and selection.get("loads") == list(FORMAL_E1_LOADS)
            and selection.get("topologies") == ["homogeneous", "heterogeneous"]
            and selection.get("seeds") == list(M1_DEVELOPMENT_SEEDS),
            "m1_qualification_shard selection is not the fixed ten-method product",
        )
        source = marker.get("source_manifest")
        receipt = marker.get("candidate_selection")
        _require(
            isinstance(source, dict)
            and source.get("run_count") == 1440
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None,
            "m1_qualification_shard source provenance is invalid",
        )
        _require(
            isinstance(receipt, dict)
            and HASH_RE.fullmatch(str(receipt.get("file_sha256"))) is not None
            and HASH_RE.fullmatch(str(receipt.get("document_sha256"))) is not None,
            "m1_qualification_shard selection provenance is invalid",
        )
        expected_seeds = list(M1_DEVELOPMENT_SEEDS)
        expected_run_count = 1200
        expected_cell_count = 60
        expected_reference_count = 120
    else:
        selection = marker.get("selection")
        _require(
            isinstance(selection, dict)
            and selection.get("method") == "sche_nash"
            and selection.get("selected_candidate") == "ready_order"
            and selection.get("loads") == list(FORMAL_E1_LOADS)
            and selection.get("topologies") == ["homogeneous", "heterogeneous"]
            and selection.get("seeds") == list(M1_DEVELOPMENT_SEEDS[:5]),
            "m1_mechanism_diagnosis_shard selection is not the frozen 1x6x5 product",
        )
        source = marker.get("source_manifest")
        _require(
            isinstance(source, dict)
            and source.get("run_count") == 1200
            and HASH_RE.fullmatch(str(source.get("manifest_hash"))) is not None
            and HASH_RE.fullmatch(str(source.get("file_sha256"))) is not None,
            "m1_mechanism_diagnosis_shard source provenance is invalid",
        )
        _require(
            marker.get("decision_neutral_observation")
            == {
                "name": "warm_path_v1",
                "warm_path_schema": 1,
                "changes_scheduler_decision": False,
            }
            and marker.get("paper_equations_changed") is False
            and marker.get("formal_results_eligible") is False,
            "m1_mechanism_diagnosis_shard observation boundary is invalid",
        )
        expected_seeds = list(M1_DEVELOPMENT_SEEDS[:5])
        expected_run_count = 30
        expected_cell_count = 6
        expected_reference_count = 30

    if marker_name in M1_RUNTIME_BOUND_MARKERS:
        runtime = marker.get("runtime_binary")
        command = manifest.get("execution", {}).get("command_template", [])
        _require(
            isinstance(runtime, dict)
            and isinstance(runtime.get("path"), str)
            and bool(runtime["path"])
            and HASH_RE.fullmatch(str(runtime.get("sha256"))) is not None
            and isinstance(runtime.get("bytes"), int)
            and not isinstance(runtime.get("bytes"), bool)
            and runtime["bytes"] > 0
            and re.fullmatch(r"[0-9a-f]{40}", str(runtime.get("source_git_commit")))
            is not None
            and isinstance(command, list)
            and len(command) >= 2
            and command[-2:] == ["--simulator-exe", runtime["path"]],
            f"{marker_name} does not bind the frozen guard runtime binary",
        )

    _require(
        manifest["fixed_seed_bank"].get("selected_seeds") == expected_seeds,
        f"{marker_name} selected seed bank is inconsistent",
    )
    runs = manifest["runs"]
    _require(
        len(runs) == expected_run_count
        and len({run["cell_id"] for run in runs}) == expected_cell_count
        and {run["seed"] for run in runs} == set(expected_seeds),
        f"{marker_name} run product is incomplete",
    )
    _require(
        len(manifest["reference_build_dependencies"]) == expected_reference_count,
        f"{marker_name} reference dependency count is incomplete",
    )
    _require(
        marker.get("run_count") == expected_run_count
        and marker.get("cell_count") == expected_cell_count
        and marker.get("reference_build_count") == expected_reference_count,
        f"{marker_name} declared counts are inconsistent",
    )
    for run in runs:
        _require(
            run["experiment_id"] == "E1"
            and run["cluster"].get("node_count") == 20
            and run["cluster"].get("topology") in {"homogeneous", "heterogeneous"}
            and run["workload"].get("request_freq") in set(FORMAL_E1_LOADS)
            and run["workload"].get("qos_profile") == "mixed",
            f"{marker_name} contains a noncanonical M1 E1 run",
        )
        candidate = run.get("metadata", {}).get("m1_operational_candidate")
        if run["method"] == "sche_nash":
            if marker_name in M1_DYNAMIC_MARKERS:
                allowed_candidates = set(dynamic_candidates)
            elif marker_name in M1_GUARD_MARKERS:
                allowed_candidates = set(guard_candidates)
            elif marker_name in G1_CORRECTED_MARKERS:
                allowed_candidates = set(strict_candidates)
            else:
                allowed_candidates = {"formula", "ready_order", "ready_finish_tie"}
            _require(
                candidate in allowed_candidates
                and run["simulator_experiment"]["nash"].get("operational_refinement")
                == candidate
                and run["environment"].get("NASH_OPERATIONAL_REFINEMENT") == candidate,
                f"{marker_name} NSESche candidate binding is invalid",
            )
            if marker_name in G1_CORRECTED_MARKERS:
                metadata = run.get("metadata", {})
                _require(
                    metadata.get("strict_best_response") is True
                    and metadata.get("utility_guard_relative_regret") == 0.0
                    and metadata.get("paper_equations_changed") is False,
                    f"{marker_name} contains a non-strict Eq.15 run",
                )
            if marker_name == "m1_qualification_shard":
                _require(
                    candidate == marker["selection"]["selected_candidate"],
                    "m1_qualification_shard contains an unselected NSESche candidate",
                )
            if marker_name == "m1_completion_guard_qualification_shard":
                _require(
                    candidate == marker["selection"]["selected_candidate"],
                    "guard qualification contains an unselected candidate",
                )
            if marker_name == "m1_dynamic_contention_qualification_shard":
                _require(
                    candidate == marker["selection"]["selected_candidate"],
                    "dynamic-contention qualification contains an unselected candidate",
                )
            if marker_name == "m1_mechanism_diagnosis_shard":
                metadata = run.get("metadata", {})
                _require(
                    candidate == "ready_order"
                    and metadata.get("m1_mechanism_diagnosis") == "warm_path_v1"
                    and metadata.get("decision_neutral_observation")
                    == "warm_path_schema_1"
                    and RUN_ID_RE.fullmatch(
                        str(metadata.get("source_qualification_run_id"))
                    )
                    is not None
                    and HASH_RE.fullmatch(
                        str(metadata.get("source_qualification_run_spec_hash"))
                    )
                    is not None,
                    "m1_mechanism_diagnosis_shard run provenance is invalid",
                )
        else:
            _require(
                marker_name
                not in {
                    "m1_candidate_screen_shard",
                    "m1_completion_guard_screen_shard",
                    "m1_dynamic_contention_screen_shard",
                    "g1_corrected_runtime_technical_replay",
                    "g1_corrected_runtime_screen",
                }
                and candidate is None,
                f"{marker_name} contains an unexpected baseline run",
            )


def _expected_ablation(variant: str) -> dict[str, bool]:
    names = ("no_heterogeneity", "no_externality", "no_pricing", "no_coordination")
    return {name: name == variant for name in names}


def load_and_validate_manifest(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    _require(isinstance(manifest, dict), "manifest root must be an object")
    validate_manifest(manifest)
    return manifest
