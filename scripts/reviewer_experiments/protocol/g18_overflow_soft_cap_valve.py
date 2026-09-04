"""Frozen zero-result D116--D120 G18 overflow soft-cap valve protocol."""

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
    G18_OVERFLOW_SOFT_CAP_VALVE_SAMPLE_POLICY,
    G18_OVERFLOW_SOFT_CAP_VALVE_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from .util import object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G18_CONTROL = "ready_order"
G18_CANDIDATE = "ready_global_overflow_soft_cap_release_valve"
G18_EFFECTIVE_METHODS = (G18_CONTROL, G18_CANDIDATE)
G18_MANIFEST_SCHEMA = "NSE_G18_OVERFLOW_SOFT_CAP_VALVE_DEVELOPMENT_V1"
G18_REFERENCE_KEY_TAGS = {G18_CONTROL: 1, G18_CANDIDATE: 19}


def _nash_cell(candidate: str, load: str, node_count: int) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G18.sche_nash.{candidate}.{load}.homogeneous.n{node_count}",
        "sche_nash",
        _base_workload(load, "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={
            "m1_operational_candidate": candidate,
            "g18_role": (
                "overflow_soft_cap_valve_candidate"
                if candidate == G18_CANDIDATE
                else "strict_ready_order_control"
            ),
            "paper_equations_changed": False,
            "new_compound_method": candidate == G18_CANDIDATE,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
            "reference_key_tag": G18_REFERENCE_KEY_TAGS[candidate],
        },
    )


def _candidate_rule() -> dict[str, Any]:
    return {
        "candidate_sequence": (
            "global_dependency_ready_not_yet_placed_after_individual_"
            "feasibility_filter"
        ),
        "candidate_order": "arrival_frame_req_id_dag_topological_rank_fn_id",
        "initial_valve_state": "closed",
        "current_overflow": "feasible_ready_count_greater_than_configured_node_count",
        "soft_cap_numerator": 5,
        "soft_cap_denominator": 4,
        "soft_cap_rounding": (
            "ceil_5_times_configured_node_count_over_4_using_checked_widened_"
            "integer_arithmetic"
        ),
        "material_comparison": (
            "feasible_ready_count_strictly_greater_than_rounded_soft_cap"
        ),
        "admission_rule": (
            "first_rounded_soft_cap_prefix_only_if_valve_closed_current_overflow_"
            "and_material_comparison_passes_else_all_feasible_ready"
        ),
        "state_update": "next_valve_state_equals_current_overflow",
        "equivalence": {
            "no_current_overflow": "same_active_set_as_c0",
            "at_or_below_cap_first_overflow": "same_active_set_as_c0",
            "material_first_overflow": "first_ceil_5n_over_4_legacy_order_prefix",
            "later_adjacent_overflow_window": "same_active_set_as_c0",
        },
        "longest_actual_positive_deferral_episode_at_most": 1,
        "forbidden": {
            "request_cohort": False,
            "frontier_or_preready_player": False,
            "remaining_work_key": False,
            "warm_override": False,
            "utility_regret_guard": False,
            "load_or_seed_or_outcome_branch": False,
            "baseline_expert": False,
            "cap_search_or_runtime_tuning": False,
            "fixed_threshold_classifier": False,
        },
    }


def build_g18_overflow_soft_cap_valve_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact zero-result 30-run G18 candidate/control product."""

    config = load_protocol_config(config_path)
    node_count = int(config["matrix_defaults"]["base_node_count"])
    if node_count != 20:
        raise ProtocolValidationError("G18 requires the frozen 20-node base cluster")
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
        for load, candidate in product(FORMAL_E1_LOADS, G18_EFFECTIVE_METHODS)
    ]
    runs = []
    for cell, seed in product(cells, G18_OVERFLOW_SOFT_CAP_VALVE_SEEDS):
        load = str(cell["workload"]["request_freq"])
        run = _make_run(config, cell, seed, common_hpa_hash, profiles[load])
        _bind_candidate(run, str(run["metadata"]["m1_operational_candidate"]))
        runs.append(run)

    marker = {
        "schema_version": G18_MANIFEST_SCHEMA,
        "purpose": "three-load overflow soft-cap release-valve control gate",
        "control": G18_CONTROL,
        "candidate": G18_CANDIDATE,
        "loads": list(FORMAL_E1_LOADS),
        "topology": "homogeneous",
        "node_count": node_count,
        "development_seeds": list(G18_OVERFLOW_SOFT_CAP_VALVE_SEEDS),
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "operational_refinement_schema_version": 13,
        "reference_key_schema_version": 14,
        "reference_key_tags": copy.deepcopy(G18_REFERENCE_KEY_TAGS),
        "candidate_rule": _candidate_rule(),
        "all_valid_runs_retained": True,
        "first_qc_valid_canonical_result_retained": True,
        "result_conditioned_seed_or_run_selection": False,
        "strong_baselines_in_initial_stage": False,
        "integrity_gate": {
            "online_run_count": 30,
            "all_runs_present_unique_paired_qc_valid": True,
            "all_runs_positive_completion_and_defined_qpr": True,
            "same_tape_within_load_seed": True,
            "one_registered_runtime_identity": True,
            "technical_retry_only": True,
            "scientific_outcome_retryable": False,
        },
        "activation_gate": {
            "material_soft_cap_deferral_seeds_at_least_each_load": 1,
            "at_or_below_cap_first_overflow_release_runs_at_least_total": 3,
            "at_or_below_cap_first_overflow_release_loads_at_least": 2,
            "persistent_overflow_release_runs_at_least_total": 3,
            "persistent_overflow_release_loads_at_least": 2,
            "longest_actual_positive_deferral_episode_at_most": 1,
            "readiness_violations_at_most": 0,
            "feasibility_violations_at_most": 0,
            "legacy_order_violations_at_most": 0,
            "prefix_violations_at_most": 0,
            "bound_violations_at_most": 0,
            "soft_cap_arithmetic_violations_at_most": 0,
            "admission_rule_violations_at_most": 0,
            "state_transition_violations_at_most": 0,
            "dispatch_set_violations_at_most": 0,
            "strict_pne_reference_runtime_dispatch_required": True,
        },
        "performance_gate": {
            "mean_throughput_ratio_above_control_each_load": 1.0,
            "mean_qpr_ratio_above_control_each_load": 1.0,
            "paired_joint_wins_at_least_each_load": 1,
            "paired_joint_nonlosses_at_least_each_load": 4,
            "per_seed_control_floor_ratio_each_metric": 0.80,
            "every_leave_one_seed_out_mean_difference_nonnegative": True,
            "strictly_positive_leave_one_seed_out_values_at_least_each_metric_load": 4,
            "completion_ratio_mean_not_below_control_each_load": True,
            "request_latency_mean_ratio_at_most_each_load": 1.05,
            "mean_policy_wall_time_ratio_at_most_each_load": 1.50,
        },
        "decision_rule": {
            "qualify_only_if_every_gate_passes": True,
            "strong_baseline_addendum_required_after_pass": True,
            "failure_closes_candidate_before_confirmation": True,
            "gate_edit_after_outcome_exposure": False,
        },
        "runtime_binary": runtime,
        "workload_tape_count": 15,
        "reference_build_count": 30,
        "online_run_count": 30,
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.G18.overflow-soft-cap-valve.D116-D120",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G18_OVERFLOW_SOFT_CAP_VALVE_SAMPLE_POLICY,
            "all_seeds": list(G18_OVERFLOW_SOFT_CAP_VALVE_SEEDS),
            "selected_seeds": list(G18_OVERFLOW_SOFT_CAP_VALVE_SEEDS),
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
        "g18_overflow_soft_cap_valve_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g18_overflow_soft_cap_valve_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G18 manifest")
    manifest = build_g18_overflow_soft_cap_valve_manifest(
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
    write_g18_overflow_soft_cap_valve_manifest(
        args.output, args.simulator_exe, args.source_git_commit, args.config
    )


if __name__ == "__main__":
    main()
