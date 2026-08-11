from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Any

from .util import object_hash, read_json


class ProtocolValidationError(ValueError):
    """Raised when a protocol configuration or manifest violates an invariant."""


SEED_RE = re.compile(r"^E\d{2}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

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
FULL_MATRIX_RUN_COUNTS_BY_STAGE = {
    "initial": {
        "E1": 600,
        "E2": 600,
        "E3": 300,
        "E4": 100,
        "E5": 120,
        "E6": 40,
        "E7": 60,
    },
    "ci_extension": {
        "E1": 600,
        "E2": 600,
        "E3": 300,
        "E4": 100,
        "E5": 120,
        "E6": 40,
        "E7": 0,
    },
    "all": {
        "E1": 1200,
        "E2": 1200,
        "E3": 600,
        "E4": 200,
        "E5": 240,
        "E6": 80,
        "E7": 60,
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _validate_analysis_reuse_rules(value: Any) -> None:
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
        "methods",
        "seed_policy",
        "common_hpa",
        "simulation",
        "matrix_defaults",
        "execution",
        "qc",
    }
    missing = sorted(required - config.keys())
    _require(not missing, f"protocol config is missing: {', '.join(missing)}")
    methods = config["methods"]
    _require(
        isinstance(methods, list) and len(methods) == 10,
        "exactly 10 methods are required",
    )
    _require(len(set(methods)) == len(methods), "methods must be unique")
    _require("sche_nash" in methods, "sche_nash must be one of the methods")

    policy = config["seed_policy"]
    for stage, expected in (("initial", 10), ("ci_extension", 10), ("e7_initial", 5)):
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
        not (set(policy["initial"]) & set(policy["ci_extension"])),
        "initial and CI-extension seeds must be disjoint",
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
        "observe",
    ):
        _require(
            field in nash, f"matrix_defaults.nash.{field} must be explicitly frozen"
        )
    _require(
        nash["queue_normalization_mode"] in {"window_max", "fixed"},
        "matrix_defaults.nash.queue_normalization_mode must be window_max or fixed",
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
    formal_e1_marker_present = "formal_e1_homogeneous_shard" in manifest
    eligibility_present = "formal_results_eligible" in manifest
    _require(
        not (marker_present and formal_e1_marker_present),
        "a manifest cannot be both an integration smoke and a formal E1 shard",
    )
    if formal_e1_marker_present:
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


def _validate_formal_e1_homogeneous_shard(manifest: dict[str, Any]) -> None:
    marker = manifest.get("formal_e1_homogeneous_shard")
    if marker is None:
        return

    prefix = "formal_e1_homogeneous_shard"
    _require(
        isinstance(marker, dict),
        f"{prefix} must be an object",
    )
    _require(
        marker.get("schema_version") == "NSE_FORMAL_E1_HOMOGENEOUS_SHARD_V1",
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
        "cluster_topology": "homogeneous",
        "node_count": 20,
        "methods": list(FORMAL_E1_METHODS),
        "loads": list(FORMAL_E1_LOADS),
        "seeds": list(expected_seeds),
    }
    _require(
        selection == expected_selection,
        f"{prefix}.selection is not the frozen E1 homogeneous Cartesian product",
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
            f"E1.{run['method']}.{run['workload']['request_freq']}.homogeneous.n20"
        )
        expected_tape_key = (
            "steady."
            f"{run['workload']['request_freq']}.homogeneous.mixed.{run['seed']}"
        )
        _require(
            run["experiment_id"] == "E1"
            and run["cell_id"] == expected_cell_id
            and run["cluster"].get("topology") == "homogeneous"
            and run["cluster"].get("node_count") == 20
            and run["workload"].get("topology") == "homogeneous"
            and run["workload"].get("arrival_profile") == "steady"
            and run["workload"].get("qos_profile") == "mixed"
            and run["workload"].get("load_scale") == 1.0
            and run.get("variant") == "full"
            and run["workload_tape"].get("key") == expected_tape_key,
            f"{prefix} contains a noncanonical run {run['run_id']}",
        )
    _require(
        set(current_by_product) == expected_product,
        f"{prefix} does not contain the complete E1 homogeneous Cartesian product",
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


def validate_manifest(manifest: dict[str, Any], *, check_hash: bool = True) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "created_at",
        "seed_stage",
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
        manifest["seed_stage"] in {"initial", "ci_extension", "all"},
        "invalid seed_stage",
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
    _validate_analysis_reuse_rules(manifest["reuse_analyses"])
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
            "seed",
            "workload",
            "workload_spec_hash",
            "workload_tape",
            "cluster",
            "common_hpa",
            "common_hpa_hash",
            "simulation",
            "simulator_experiment",
            "environment",
        ):
            _require(key in run, f"{prefix} missing {key}")
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
        _require(
            object_hash({"seed": run["seed"], "workload": run["workload"]})
            == run["workload_spec_hash"],
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
        _validate_simulation(run["simulation"], f"{prefix}.simulation")
        _require(
            experiment.get("run_id") == run["run_id"],
            f"{prefix} simulator run_id mismatch",
        )
        experiment_workload = experiment.get("workload", {})
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
        run_key = (run["cell_id"], run["seed"])
        _require(run_key not in run_keys, f"duplicate cell/seed pair {run_key}")
        run_keys.add(run_key)
        expected_run_hash = _hash_without(run, "run_spec_hash")
        _require(
            expected_run_hash == run["run_spec_hash"],
            f"{prefix} has invalid run_spec_hash",
        )

    _validate_formal_e1_homogeneous_shard(manifest)

    analysis_ids = {entry.get("experiment_id") for entry in manifest["reuse_analyses"]}
    _require(
        {"E8", "E9"}.issubset(analysis_ids), "E8 and E9 must be reuse-only analyses"
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


def _expected_ablation(variant: str) -> dict[str, bool]:
    names = ("no_heterogeneity", "no_externality", "no_pricing", "no_coordination")
    return {name: name == variant for name in names}


def load_and_validate_manifest(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    _require(isinstance(manifest, dict), "manifest root must be an object")
    validate_manifest(manifest)
    return manifest
