"""Frozen zero-result D121--D125 low-load parameter recovery protocol."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

from .g1_corrected_runtime import _runtime_execution
from .m1_completion_guard import _runtime_receipt
from .m1_development import _bind_candidate, _matrix_summary
from .matrix import (
    _base_workload,
    _environment_for,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    load_protocol_config,
)
from .schema import (
    P2_LOW_HYPERPARAMETER_RECOVERY_SAMPLE_POLICY,
    P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from .util import object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


P2_LOW_CONTROL = "centre"
P2_LOW_OPERATIONAL_REFINEMENT = "ready_order"
P2_LOW_MANIFEST_SCHEMA = "NSE_P2_LOW_HYPERPARAMETER_RECOVERY_V1"
P2_LOW_SETTINGS: tuple[tuple[str, float, float], ...] = (
    ("centre", 0.60, 0.50),
    ("r0_minus", 0.55, 0.50),
    ("r0_plus", 0.65, 0.50),
    ("wq_minus", 0.60, 0.40),
    ("wq_plus", 0.60, 0.60),
)
P2_LOW_SETTING_LABELS = tuple(row[0] for row in P2_LOW_SETTINGS)


def _parameter_cell(
    label: str, price_feedback_rate: float, quality_weight: float, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E7",
        (
            f"P2LOWHP.sche_nash.{label}.low.homogeneous.n{node_count}."
            f"p{price_feedback_rate:g}.q{quality_weight:g}"
        ),
        "sche_nash",
        _base_workload("low", "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        environment=_environment_for(
            "sche_nash",
            {
                "NASH_OPERATIONAL_REFINEMENT": P2_LOW_OPERATIONAL_REFINEMENT,
                "NASH_PRICE_FEEDBACK_RATE": f"{price_feedback_rate:g}",
                "NASH_QUALITY_WEIGHT": f"{quality_weight:g}",
            },
        ),
        variant=label,
        metadata={
            "p2_low_parameter_role": (
                "submitted_centre" if label == P2_LOW_CONTROL else "axial_neighbour"
            ),
            "parameter_setting": label,
            "m1_operational_candidate": P2_LOW_OPERATIONAL_REFINEMENT,
            "paper_equations_changed": False,
            "strict_best_response": True,
            "reference_key_tag": 1,
            "nash_parameters": {
                "price_feedback_rate": price_feedback_rate,
                "quality_weight": quality_weight,
            },
        },
    )


def _settings_payload() -> list[dict[str, Any]]:
    return [
        {
            "ordinal": ordinal,
            "label": label,
            "price_feedback_rate": price_feedback_rate,
            "quality_weight": quality_weight,
            "role": "control" if label == P2_LOW_CONTROL else "neighbour",
        }
        for ordinal, (label, price_feedback_rate, quality_weight) in enumerate(
            P2_LOW_SETTINGS, start=1
        )
    ]


def build_p2_low_hyperparameter_recovery_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact zero-result 5-setting by 5-seed development product."""

    config = load_protocol_config(config_path)
    node_count = int(config["matrix_defaults"]["base_node_count"])
    if node_count != 20:
        raise ProtocolValidationError(
            "P2 low parameter recovery requires the frozen 20-node cluster"
        )
    configured = config["matrix_defaults"]["e7"]
    if configured["centers"]["low"] != {
        "price_feedback_rate": 0.6,
        "quality_weight": 0.5,
    } or configured["steps"] != {"price_feedback_rate": 0.05, "quality_weight": 0.1}:
        raise ProtocolValidationError("P2 low E7 centre or axial steps drifted")

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
        _parameter_cell(label, price, quality, node_count)
        for label, price, quality in P2_LOW_SETTINGS
    ]
    runs: list[dict[str, Any]] = []
    for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS:
        for cell in cells:
            run = _make_run(config, cell, seed, common_hpa_hash, profiles["low"])
            _bind_candidate(run, P2_LOW_OPERATIONAL_REFINEMENT)
            runs.append(run)

    marker = {
        "schema_version": P2_LOW_MANIFEST_SCHEMA,
        "purpose": "low-load E7 axial-neighbour recovery screen",
        "load": "low",
        "topology": "homogeneous",
        "node_count": node_count,
        "method": "sche_nash",
        "operational_refinement": P2_LOW_OPERATIONAL_REFINEMENT,
        "control_setting": P2_LOW_CONTROL,
        "settings": _settings_payload(),
        "development_seeds": list(P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS),
        "execution_order": "seed_major_then_setting_ordinal",
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "all_valid_runs_retained": True,
        "first_qc_valid_canonical_result_retained": True,
        "result_conditioned_seed_setting_or_run_selection": False,
        "strong_baselines_in_screen": False,
        "gate": {
            "complete_online_run_count": 25,
            "same_tape_within_seed": True,
            "mean_throughput_ratio_at_least": 1.015,
            "mean_qpr_ratio_at_least": 1.11,
            "paired_joint_wins_at_least": 3,
            "paired_joint_nonlosses_at_least": 4,
            "per_seed_centre_floor_ratio_each_metric": 0.80,
            "every_leave_one_seed_out_mean_difference_nonnegative": True,
            "strictly_positive_leave_one_seed_out_values_at_least_each_metric": 4,
            "completion_ratio_mean_not_below_centre": True,
            "request_latency_mean_ratio_at_most": 1.05,
            "runtime_reference_integrity_required": True,
            "mean_policy_wall_time_ratio_at_most": 1.50,
            "all_conditions_required": True,
        },
        "selection_rule": {
            "eligible_set": "neighbours_passing_every_gate_condition",
            "primary": "descending_minimum_of_mean_throughput_and_qpr_ratios",
            "secondary": "descending_geometric_mean_of_the_two_mean_ratios",
            "final_label_order": ["r0_minus", "r0_plus", "wq_minus", "wq_plus"],
            "no_pass_action": "retain_centre_and_block_fresh_formal_bank",
            "one_shot": True,
            "gate_edit_after_outcome_exposure": False,
        },
        "runtime_binary": runtime,
        "workload_tape_count": 5,
        "reference_build_count": 25,
        "online_run_count": 25,
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.P2.low-hyperparameter-recovery.D121-D125",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": P2_LOW_HYPERPARAMETER_RECOVERY_SAMPLE_POLICY,
            "all_seeds": list(P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS),
            "selected_seeds": list(P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS),
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
        "p2_low_hyperparameter_recovery_screen": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_p2_low_hyperparameter_recovery_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite P2 low parameter manifest")
    manifest = build_p2_low_hyperparameter_recovery_manifest(
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
    write_p2_low_hyperparameter_recovery_manifest(
        args.output, args.simulator_exe, args.source_git_commit, args.config
    )


if __name__ == "__main__":
    main()
