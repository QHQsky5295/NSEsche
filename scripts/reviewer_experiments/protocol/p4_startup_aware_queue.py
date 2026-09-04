"""Frozen zero-result D126--D130 startup-aware queue-pressure protocol."""

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
    P4_STARTUP_AWARE_QUEUE_SAMPLE_POLICY,
    P4_STARTUP_AWARE_QUEUE_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from .util import object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


P4_CONTROL = "execution_ready"
P4_CANDIDATE = "startup_aware"
P4_OPERATIONAL_REFINEMENT = "ready_order"
P4_MANIFEST_SCHEMA = "NSE_P4_STARTUP_AWARE_QUEUE_V1"
P4_REFERENCE_KEY_SCHEMA_VERSION = 15
P4_SETTINGS: tuple[tuple[str, str, str], ...] = (
    (P4_CONTROL, "execution_ready", "control"),
    (P4_CANDIDATE, "startup_aware", "candidate"),
)
P4_SETTING_LABELS = tuple(row[0] for row in P4_SETTINGS)


def _queue_cell(
    label: str, semantics: str, role: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E7",
        f"P4STARTUPQ.sche_nash.{label}.low.homogeneous.n{node_count}",
        "sche_nash",
        _base_workload("low", "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        environment=_environment_for(
            "sche_nash",
            {
                "NASH_OPERATIONAL_REFINEMENT": P4_OPERATIONAL_REFINEMENT,
                "NASH_PRICE_FEEDBACK_RATE": "0.6",
                "NASH_QUALITY_WEIGHT": "0.5",
                "NASH_QUEUE_PRESSURE_SEMANTICS": semantics,
            },
        ),
        variant=label,
        metadata={
            "p4_queue_role": role,
            "queue_pressure_setting": label,
            "queue_pressure_semantics": semantics,
            "m1_operational_candidate": P4_OPERATIONAL_REFINEMENT,
            "paper_equations_changed": False,
            "strict_best_response": True,
            "reference_key_schema_version": P4_REFERENCE_KEY_SCHEMA_VERSION,
            "queue_pressure_reference_key_tag": 0 if role == "control" else 1,
            "nash_parameters": {
                "price_feedback_rate": 0.60,
                "quality_weight": 0.50,
            },
        },
    )


def _bind_queue_semantics(run: dict[str, Any], semantics: str) -> None:
    """Bind queue semantics before recomputing reference and run identities."""

    _bind_candidate(run, P4_OPERATIONAL_REFINEMENT)
    run["simulator_experiment"]["nash"]["queue_pressure_semantics"] = semantics
    run["environment"]["NASH_QUEUE_PRESSURE_SEMANTICS"] = semantics
    _bind_candidate(run, P4_OPERATIONAL_REFINEMENT)


def _settings_payload() -> list[dict[str, Any]]:
    return [
        {
            "ordinal": ordinal,
            "label": label,
            "queue_pressure_semantics": semantics,
            "role": role,
        }
        for ordinal, (label, semantics, role) in enumerate(P4_SETTINGS, start=1)
    ]


def _gate() -> dict[str, Any]:
    return {
        "complete_online_run_count": 10,
        "same_tape_within_seed": True,
        "startup_backlog_positive_active_window_share_at_least": 0.10,
        "activation_seed_count_at_least": 4,
        "assignment_change_seed_count_at_least": 4,
        "mean_throughput_ratio_at_least": 1.015,
        "mean_qpr_ratio_at_least": 1.11,
        "paired_joint_wins_at_least": 3,
        "paired_joint_nonlosses_at_least": 4,
        "per_seed_control_floor_ratio_each_metric": 0.80,
        "every_leave_one_seed_out_mean_difference_nonnegative": True,
        "strictly_positive_leave_one_seed_out_values_at_least_each_metric": 4,
        "completion_ratio_mean_not_below_control": True,
        "request_latency_mean_ratio_at_most": 1.05,
        "runtime_reference_integrity_required": True,
        "mean_policy_wall_time_ratio_at_most": 1.50,
        "all_ten_conditions_required": True,
    }


def _selection_rule() -> dict[str, Any]:
    return {
        "eligible_set": "startup_aware_only_if_all_ten_conditions_pass",
        "pass_action": "authorize_separate_low_baseline_compatibility_preregistration",
        "no_pass_action": "retain_execution_ready_and_close_startup_aware_family",
        "one_shot": True,
        "gate_edit_after_outcome_exposure": False,
    }


def build_p4_startup_aware_queue_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact zero-result two-setting by five-seed P4 product."""

    config = load_protocol_config(config_path)
    node_count = int(config["matrix_defaults"]["base_node_count"])
    if node_count != 20:
        raise ProtocolValidationError(
            "P4 startup-aware queue requires the frozen 20-node cluster"
        )
    configured = config["matrix_defaults"]["e7"]["centers"]["low"]
    if configured != {"price_feedback_rate": 0.6, "quality_weight": 0.5}:
        raise ProtocolValidationError("P4 low-load paper parameters drifted")
    if config["matrix_defaults"]["nash"]["queue_pressure_semantics"] != P4_CONTROL:
        raise ProtocolValidationError(
            "P4 requires execution_ready as the unchanged protocol default"
        )

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
        _queue_cell(label, semantics, role, node_count)
        for label, semantics, role in P4_SETTINGS
    ]
    runs: list[dict[str, Any]] = []
    for seed in P4_STARTUP_AWARE_QUEUE_SEEDS:
        for cell in cells:
            run = _make_run(config, cell, seed, common_hpa_hash, profiles["low"])
            _bind_queue_semantics(run, cell["metadata"]["queue_pressure_semantics"])
            runs.append(run)

    marker = {
        "schema_version": P4_MANIFEST_SCHEMA,
        "purpose": "low-load startup-aware Eq. (6) queue-pressure development screen",
        "load": "low",
        "topology": "homogeneous",
        "node_count": node_count,
        "method": "sche_nash",
        "operational_refinement": P4_OPERATIONAL_REFINEMENT,
        "control_setting": P4_CONTROL,
        "candidate_setting": P4_CANDIDATE,
        "queue_pressure_semantics_schema": "execution_ready_or_startup_aware_v1",
        "reference_key_schema_version": P4_REFERENCE_KEY_SCHEMA_VERSION,
        "settings": _settings_payload(),
        "development_seeds": list(P4_STARTUP_AWARE_QUEUE_SEEDS),
        "execution_order": "seed_major_then_setting_ordinal",
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "all_valid_runs_retained": True,
        "first_qc_valid_canonical_result_retained": True,
        "result_conditioned_seed_setting_or_run_selection": False,
        "strong_baselines_in_screen": False,
        "gate": _gate(),
        "selection_rule": _selection_rule(),
        "runtime_binary": runtime,
        "workload_tape_count": 5,
        "reference_build_count": 10,
        "online_run_count": 10,
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.P4.startup-aware-queue.D126-D130",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": P4_STARTUP_AWARE_QUEUE_SAMPLE_POLICY,
            "all_seeds": list(P4_STARTUP_AWARE_QUEUE_SEEDS),
            "selected_seeds": list(P4_STARTUP_AWARE_QUEUE_SEEDS),
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
        "p4_startup_aware_queue_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_p4_startup_aware_queue_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite P4 startup-aware manifest")
    manifest = build_p4_startup_aware_queue_manifest(
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
    write_p4_startup_aware_queue_manifest(
        args.output, args.simulator_exe, args.source_git_commit, args.config
    )


if __name__ == "__main__":
    main()
