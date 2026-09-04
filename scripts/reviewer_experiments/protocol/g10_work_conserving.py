"""Frozen zero-result D96--D100 G10 work-conserving protocol."""

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
    G10_WORK_CONSERVING_SAMPLE_POLICY,
    G10_WORK_CONSERVING_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from .util import object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G10_CONTROL = "ready_order"
G10_CANDIDATES = (
    "ready_remaining_work",
    "ready_remaining_work_bounded_frontier",
)
G10_EFFECTIVE_METHODS = (G10_CONTROL, *G10_CANDIDATES)
G10_MANIFEST_SCHEMA = "NSE_G10_WORK_CONSERVING_DEVELOPMENT_V1"
G10_REFERENCE_KEY_TAGS = {
    G10_CONTROL: 1,
    G10_CANDIDATES[0]: 14,
    G10_CANDIDATES[1]: 15,
}


def _nash_cell(candidate: str, load: str, node_count: int) -> dict[str, Any]:
    roles = {
        G10_CONTROL: "strict_ready_order_control",
        G10_CANDIDATES[0]: "remaining_work_candidate",
        G10_CANDIDATES[1]: "bounded_frontier_candidate",
    }
    return _make_cell(
        "E1",
        f"G10.sche_nash.{candidate}.{load}.homogeneous.n{node_count}",
        "sche_nash",
        _base_workload(load, "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={
            "m1_operational_candidate": candidate,
            "g10_role": roles[candidate],
            "paper_equations_changed": False,
            "new_compound_method": candidate != G10_CONTROL,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
            "reference_key_tag": G10_REFERENCE_KEY_TAGS[candidate],
        },
    )


def _candidate_rules() -> dict[str, Any]:
    return {
        "ready_remaining_work": {
            "candidate_set": "dependency_ready_identical_to_control",
            "order": (
                "unfinished_functions_then_arrival_frame_req_id_"
                "dag_topological_rank_fn_id"
            ),
            "remaining_work_definition": (
                "dag_function_count_minus_completed_function_count"
            ),
            "initialization": "sequential_existing_candidate_selection",
        },
        "ready_remaining_work_bounded_frontier": {
            "all_ready_players_first_and_uncapped": True,
            "frontier_eligibility": (
                "unplaced_not_ready_all_incomplete_direct_parents_placed_and_"
                "their_parents_complete"
            ),
            "frontier_budget": "max_zero_node_count_minus_outstanding_parent_blocked",
            "frontier_bound": (
                "outstanding_parent_blocked_plus_new_frontier_at_most_"
                "configured_node_count"
            ),
        },
        "forbidden": {
            "warm_or_finish_override": False,
            "bounded_regret": False,
            "baseline_expert": False,
            "load_specific_branch": False,
        },
    }


def build_g10_work_conserving_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact zero-result 45-run G10 candidate/control product."""

    config = load_protocol_config(config_path)
    node_count = int(config["matrix_defaults"]["base_node_count"])
    if node_count != 20:
        raise ProtocolValidationError("G10 requires the frozen 20-node base cluster")
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

    cells = [
        _nash_cell(candidate, load, node_count)
        for load, candidate in product(FORMAL_E1_LOADS, G10_EFFECTIVE_METHODS)
    ]
    runs = []
    for cell, seed in product(cells, G10_WORK_CONSERVING_SEEDS):
        load = str(cell["workload"]["request_freq"])
        run = _make_run(config, cell, seed, common_hpa_hash, profiles[load])
        _bind_candidate(run, str(run["metadata"]["m1_operational_candidate"]))
        runs.append(run)

    marker = {
        "schema_version": G10_MANIFEST_SCHEMA,
        "purpose": "three-load work-conserving remaining-work control gate",
        "control": G10_CONTROL,
        "candidates": list(G10_CANDIDATES),
        "loads": list(FORMAL_E1_LOADS),
        "topology": "homogeneous",
        "node_count": node_count,
        "development_seeds": list(G10_WORK_CONSERVING_SEEDS),
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "operational_refinement_schema_version": 9,
        "reference_key_tags": copy.deepcopy(G10_REFERENCE_KEY_TAGS),
        "candidate_rules": _candidate_rules(),
        "all_valid_runs_retained": True,
        "first_qc_valid_canonical_result_retained": True,
        "result_conditioned_seed_or_run_selection": False,
        "strong_baselines_in_initial_stage": False,
        "integrity_gate": {
            "online_run_count": 45,
            "all_runs_present_unique_paired_qc_valid": True,
            "all_runs_positive_completion_and_defined_qpr": True,
            "same_tape_within_load_seed": True,
            "technical_retry_only": True,
            "scientific_outcome_retryable": False,
        },
        "activation_gate": {
            "c1_ready_set_identical_to_control": True,
            "c2_ready_omissions_at_most": 0,
            "c2_frontier_bound_violations_at_most": 0,
            "c2_frontier_one_hop_violations_at_most": 0,
            "c2_dispatch_class_violations_at_most": 0,
            "c2_positive_frontier_admission_seeds_at_least_each_load": 3,
            "strict_pne_reference_runtime_dispatch_required": True,
        },
        "performance_gate": {
            "mean_throughput_ratio_above_control_each_load": 1.0,
            "mean_qpr_ratio_above_control_each_load": 1.0,
            "paired_throughput_wins_at_least_each_load": 3,
            "paired_qpr_wins_at_least_each_load": 3,
            "paired_joint_wins_at_least_each_load": 3,
            "per_seed_control_floor_ratio_each_metric": 0.80,
            "every_leave_one_seed_out_mean_difference_positive": True,
            "completion_ratio_mean_not_below_control_each_load": True,
            "request_latency_mean_below_control_each_load": True,
            "mean_policy_wall_time_ratio_at_most_each_load": 1.50,
        },
        "selection_rule": [
            "maximum_minimum_of_six_primary_ratios",
            "maximum_mean_of_six_primary_ratios",
            "maximum_joint_paired_wins",
            "exact_tie_selects_ready_remaining_work",
        ],
        "runtime_binary": runtime,
        "workload_tape_count": 15,
        "reference_build_count": 45,
        "online_run_count": 45,
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.G10.work-conserving.D96-D100",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G10_WORK_CONSERVING_SAMPLE_POLICY,
            "all_seeds": list(G10_WORK_CONSERVING_SEEDS),
            "selected_seeds": list(G10_WORK_CONSERVING_SEEDS),
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
        "g10_work_conserving_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g10_work_conserving_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G10 manifest")
    manifest = build_g10_work_conserving_manifest(
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
    write_g10_work_conserving_manifest(
        args.output, args.simulator_exe, args.source_git_commit, args.config
    )


if __name__ == "__main__":
    main()
