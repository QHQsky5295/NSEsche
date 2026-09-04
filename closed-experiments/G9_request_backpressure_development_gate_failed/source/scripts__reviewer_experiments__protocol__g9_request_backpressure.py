"""Frozen D81--D85 request-level backpressure development protocol."""

from __future__ import annotations

import argparse
import copy
from itertools import product
from pathlib import Path
from typing import Any

from .g1_corrected_runtime import _runtime_execution
from .m1_completion_guard import _runtime_receipt
from .m1_development import _bind_candidate, _matrix_summary
from .matrix import (
    _base_workload,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    load_protocol_config,
)
from .schema import (
    FORMAL_E1_LOADS,
    G9_REQUEST_BACKPRESSURE_SAMPLE_POLICY,
    G9_REQUEST_BACKPRESSURE_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from .util import object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G9_CANDIDATE = "ready_request_backpressure"
G9_CONTROL = "ready_order"
G9_BASELINES = ("load_least", "sche_FaaSRank", "sche_Hiku")
G9_EFFECTIVE_METHODS = (G9_CONTROL, G9_CANDIDATE, *G9_BASELINES)
G9_MANIFEST_SCHEMA = "NSE_G9_REQUEST_BACKPRESSURE_DEVELOPMENT_V1"


def _nash_cell(candidate: str, load: str, node_count: int) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G9.sche_nash.{candidate}.{load}.homogeneous.n{node_count}",
        "sche_nash",
        _base_workload(load, "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={
            "m1_operational_candidate": candidate,
            "g9_role": (
                "request_backpressure_candidate"
                if candidate == G9_CANDIDATE
                else "strict_ready_order_control"
            ),
            "paper_equations_changed": False,
            "new_compound_method": candidate == G9_CANDIDATE,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
        },
    )


def _baseline_cell(method: str, load: str, node_count: int) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G9.{method}.{load}.homogeneous.n{node_count}",
        method,
        _base_workload(load, "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={"g9_role": "independent_baseline"},
    )


def build_g9_request_backpressure_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact zero-result 75-run G9 development product."""

    config = load_protocol_config(config_path)
    node_count = int(config["matrix_defaults"]["base_node_count"])
    if node_count != 20:
        raise ProtocolValidationError("G9 requires the frozen 20-node base cluster")
    runtime = _runtime_receipt(simulator_exe, source_git_commit)
    common_hpa_hash = object_hash(config["common_hpa"])
    repository = Path(__file__).resolve().parents[3]
    profiles = load_profile_set(config["workload_profiles"], repository=repository)
    profile_bindings = {
        load: profile.to_binding() for load, profile in profiles.items()
    }
    workload_profile_set = {
        "schema_version": config["workload_profiles"]["schema_version"],
        "profile_set_id": config["workload_profiles"]["profile_set_id"],
        "formal_required": True,
        "profiles": profile_bindings,
    }

    cells = []
    for load in FORMAL_E1_LOADS:
        cells.extend(
            _nash_cell(candidate, load, node_count)
            for candidate in (G9_CONTROL, G9_CANDIDATE)
        )
        cells.extend(
            _baseline_cell(method, load, node_count) for method in G9_BASELINES
        )
    runs = []
    for cell, seed in product(cells, G9_REQUEST_BACKPRESSURE_SEEDS):
        load = str(cell["workload"]["request_freq"])
        run = _make_run(config, cell, seed, common_hpa_hash, profiles[load])
        if run["method"] == "sche_nash":
            _bind_candidate(run, str(run["metadata"]["m1_operational_candidate"]))
        runs.append(run)

    marker = {
        "schema_version": G9_MANIFEST_SCHEMA,
        "purpose": "three-load request-level bounded-concurrency development gate",
        "candidate": G9_CANDIDATE,
        "control": G9_CONTROL,
        "baseline_methods": list(G9_BASELINES),
        "loads": list(FORMAL_E1_LOADS),
        "topology": "homogeneous",
        "node_count": node_count,
        "development_seeds": list(G9_REQUEST_BACKPRESSURE_SEEDS),
        "paper_equations_changed": False,
        "new_compound_method": True,
        "strict_eq15_required": True,
        "operational_refinement_schema_version": 8,
        "reference_key_tag": 13,
        "request_backpressure_rule": {
            "cohort_order": "arrival_frame_then_request_id",
            "cohort_limit": "configured_node_count",
            "player_scope": "dependency_ready_not_yet_placed_request_function_players",
            "request_rejection_or_deletion": False,
            "load_specific_parameter": False,
        },
        "all_valid_runs_retained": True,
        "first_qc_valid_canonical_result_retained": True,
        "result_conditioned_seed_or_run_selection": False,
        "integrity_gate": {
            "online_run_count": 75,
            "all_runs_present_unique_paired_qc_valid": True,
            "all_runs_positive_completion_and_defined_qpr": True,
            "same_tape_within_load_seed": True,
            "technical_retry_only": True,
            "scientific_outcome_retryable": False,
        },
        "activation_gate": {
            "deferred_positive_when_live_exceeds_limit": True,
            "admitted_requests_at_most_node_count": True,
            "every_dispatched_player_in_cohort": True,
            "cohort_retention_violations_at_most": 0,
            "strict_eq15_and_reference_stream_required": True,
        },
        "performance_gate": {
            "rank_first_throughput_each_load": True,
            "rank_first_qpr_each_load": True,
            "paired_control_throughput_wins_at_least_each_load": 4,
            "paired_control_qpr_wins_at_least_each_load": 4,
            "paired_mean_above_each_baseline_each_metric_each_load": True,
            "per_seed_control_floor_ratio_each_metric": 0.80,
            "mean_policy_wall_time_ratio_at_most_each_load": 1.25,
        },
        "runtime_binary": runtime,
        "workload_tape_count": 15,
        "reference_build_count": 30,
        "online_run_count": 75,
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.G9.request-backpressure.D81-D85",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G9_REQUEST_BACKPRESSURE_SAMPLE_POLICY,
            "all_seeds": list(G9_REQUEST_BACKPRESSURE_SEEDS),
            "selected_seeds": list(G9_REQUEST_BACKPRESSURE_SEEDS),
            "paired_across_methods": True,
            "result_conditioned_extension": False,
        },
        "method_versions": copy.deepcopy(
            config["manifest_governance"]["method_versions"]
        ),
        "old_pdf_alignment": copy.deepcopy(
            config["manifest_governance"]["old_pdf_alignment"]
        ),
        "runtime_identity_policy": copy.deepcopy(
            config["manifest_governance"]["runtime_identity"]
        ),
        "seed_stage": "development",
        "ci_extension_requires_trigger": False,
        "common_hpa": copy.deepcopy(config["common_hpa"]),
        "common_hpa_hash": common_hpa_hash,
        "workload_profile_set": workload_profile_set,
        "workload_profile_set_hash": object_hash(workload_profile_set),
        "simulation": copy.deepcopy(config["simulation"]),
        "execution": _runtime_execution(config["execution"], runtime),
        "qc": copy.deepcopy(config["qc"]),
        "matrix_summary": _matrix_summary(runs),
        "runs": runs,
        "reference_build_dependencies": _reference_build_dependencies(runs),
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": [],
        "g9_request_backpressure_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g9_request_backpressure_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G9 manifest")
    manifest = build_g9_request_backpressure_manifest(
        simulator_exe, source_git_commit, config_path
    )
    write_json_atomic(output_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("simulator_exe", type=Path)
    parser.add_argument("source_git_commit")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    write_g9_request_backpressure_manifest(
        args.output, args.simulator_exe, args.source_git_commit, args.config
    )


if __name__ == "__main__":
    main()
