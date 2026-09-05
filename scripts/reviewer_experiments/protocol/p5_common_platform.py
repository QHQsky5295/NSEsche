"""Build the frozen, zero-result P5 common-platform protocol pilot."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

from .g1_corrected_runtime import _runtime_execution
from .m1_completion_guard import _runtime_receipt
from .m1_development import _matrix_summary
from .matrix import (
    _assign_run_identity,
    _base_workload,
    _environment_for,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    _reference_dependency,
    load_protocol_config,
)
from .schema import (
    FORMAL_E1_METHODS,
    P5_COMMON_PLATFORM_MARKER,
    P5_COMMON_PLATFORM_SAMPLE_POLICY,
    P5_COMMON_PLATFORM_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


P5_MANIFEST_SCHEMA = "NSE_P5_COMMON_PLATFORM_PILOT_V1"
P5_LOADS = ("low", "middle", "high")
P5_NODE_COUNT = 20
P5_ACTIVE_REQUEST_LIMIT = 100
P5_ARRIVAL_HORIZON = 1_000
P5_ADMISSION = {
    "enabled": True,
    "policy": "fcfs_capacity",
    "drain_cpu_work_multiplier": 4.0,
    "minimum_drain_frames": 1_000,
    "stop_when_drained": True,
}
P5_SIMULATION = {
    "dag_type": "mix",
    "cold_start": "high",
    "fn_type": "cpu",
    "total_frame": 1_000,
    "expected_final_frame": None,
    "expected_frame_count": None,
    "arrival_horizon_frames": 1_000,
    "observation_horizon_frames": 1_000,
    "frame_duration_seconds": 0.001,
    "terminal_mode": "early_drained_or_derived_hard_deadline",
    "minimum_final_frame": 1_000,
    "hard_end_frame_source": (
        "1000+max(1000,ceil(4*tape_static_cpu_work/cluster_cpu_per_frame)"
        "+static_path_allowance_frames)"
    ),
}


def _p5_cell(method: str, load: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "p5_common_platform": True,
        "paper_equations_changed": False,
        "method_ordinal": FORMAL_E1_METHODS.index(method) + 1,
        "load_ordinal": P5_LOADS.index(load) + 1,
    }
    environment = _environment_for(method)
    if method == "sche_nash":
        parameters = (
            {"price_feedback_rate": 0.6, "quality_weight": 0.5}
            if load == "low"
            else {"price_feedback_rate": 0.5, "quality_weight": 0.6}
        )
        metadata.update(
            {
                "m1_operational_candidate": "ready_order",
                "strict_best_response": True,
                "utility_guard_relative_regret": 0.0,
                "nash_parameters": parameters,
            }
        )
        environment.update(
            {
                "NASH_OPERATIONAL_REFINEMENT": "ready_order",
                "NASH_PRICE_FEEDBACK_RATE": f"{parameters['price_feedback_rate']:g}",
                "NASH_QUALITY_WEIGHT": f"{parameters['quality_weight']:g}",
            }
        )
    return _make_cell(
        "E1",
        f"P5.{method}.{load}.homogeneous.n{P5_NODE_COUNT}",
        method,
        _base_workload(load, "homogeneous", "mixed"),
        {"node_count": P5_NODE_COUNT, "topology": "homogeneous"},
        environment=environment,
        metadata=metadata,
    )


def _bind_p5_contract(run: dict[str, Any]) -> None:
    experiment = run["simulator_experiment"]
    run["simulation"] = copy.deepcopy(P5_SIMULATION)
    experiment["protocol_version"] = "reviewer-v4"
    experiment["admission"] = copy.deepcopy(P5_ADMISSION)
    experiment["workload"]["arrival_horizon_frames"] = P5_ARRIVAL_HORIZON

    if run["method"] == "sche_nash":
        parameters = run["metadata"]["nash_parameters"]
        experiment["nash"].update(parameters)
        experiment["nash"]["operational_refinement"] = "ready_order"

    # P5 deliberately builds one method-state-matched read-only welfare table
    # for every method, including baseline post-hoc evaluator streams.
    experiment["reference"] = {
        "mode": "sa_fallback",
        "table_path": "",
        "build_output_path": "",
    }
    run.pop("reference_dependency", None)
    dependency = _reference_dependency(run)
    run["reference_dependency"] = dependency
    experiment["reference"] = {
        "mode": "offline_required",
        "table_path": dependency["path"],
        "build_output_path": "",
    }
    _assign_run_identity(run)


def _gate() -> dict[str, Any]:
    return {
        "population_and_identity": "90_unique_first_qc_valid_one_runtime_nine_tapes_90_references",
        "arrival_identity": "ordered_tape_arrival_and_static_drain_inputs_identical_within_pair",
        "conservation": "censored=waiting+active=arrivals-completed_and_zero_drop_reject_timeout",
        "fcfs": "admitted_sequence_is_every_frame_prefix_of_external_sequence",
        "capacity": "active_limit_100_no_over_cap_and_next_frame_work_conserving_refill",
        "timing": "no_arrival_at_or_after_1000_and_valid_early_or_hard_terminal",
        "metric_identity_absolute_tolerance": 1e-9,
        "usable_cohort": {
            "fixed_window_completions_at_least": 1,
            "terminal_completion_ratio_at_least": 0.95,
        },
        "traffic_interpretation": "report_request_and_static_work_distributions_without_selection",
        "reference_and_nash_integrity": True,
        "determinism_duplicate": "P5P01-low-sche_nash",
        "result_blindness": True,
    }


def build_p5_common_platform_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact 3-load x 3-seed x 10-method zero-result pilot."""

    config = load_protocol_config(config_path)
    if int(config["matrix_defaults"]["base_node_count"]) != P5_NODE_COUNT:
        raise ProtocolValidationError("P5 requires the frozen homogeneous-20 cluster")
    if int(config["simulation"]["arrival_horizon_frames"]) != P5_ARRIVAL_HORIZON:
        raise ProtocolValidationError("P5 requires the 1,000-frame arrival horizon")

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
        _p5_cell(method, load) for load in P5_LOADS for method in FORMAL_E1_METHODS
    ]
    cells_by_load_method = {
        (cell["workload"]["request_freq"], cell["method"]): cell for cell in cells
    }
    runs: list[dict[str, Any]] = []
    for load in P5_LOADS:
        for seed in P5_COMMON_PLATFORM_SEEDS:
            for method in FORMAL_E1_METHODS:
                run = _make_run(
                    config,
                    cells_by_load_method[(load, method)],
                    seed,
                    common_hpa_hash,
                    profiles[load],
                )
                _bind_p5_contract(run)
                runs.append(run)

    qc = copy.deepcopy(config["qc"])
    qc["p5_common_platform"] = {
        "scientific_zero_or_low_completion_is_qc_valid": True,
        "scientific_rank_or_old_pdf_drift_is_qc_valid": True,
        "admission_event_stream_required": True,
        "metric_identity_absolute_tolerance": 1e-9,
    }
    analyzer_path = (
        Path(__file__).resolve().parents[1] / "analysis" / "p5_common_platform.py"
    )
    if not analyzer_path.is_file():
        raise ProtocolValidationError("P5 frozen analyzer source is missing")
    addendum_path = (
        Path(__file__).resolve().parents[3]
        / "refine-logs"
        / "P5_COMMON_PLATFORM_PRERESULT_ADDENDUM.md"
    )
    if not addendum_path.is_file():
        raise ProtocolValidationError("P5 pre-result addendum is missing")
    marker = {
        "schema_version": P5_MANIFEST_SCHEMA,
        "purpose": "method-neutral FCFS active-cohort and bounded-drain protocol pilot",
        "pilot_seeds": list(P5_COMMON_PLATFORM_SEEDS),
        "loads": list(P5_LOADS),
        "methods": list(FORMAL_E1_METHODS),
        "topology": "homogeneous",
        "node_count": P5_NODE_COUNT,
        "execution_order": "load_major_then_seed_then_method_ordinal",
        "paper_equations_changed": False,
        "all_valid_runs_retained": True,
        "first_qc_valid_canonical_result_retained": True,
        "result_conditioned_seed_method_or_run_selection": False,
        "admission": {
            **copy.deepcopy(P5_ADMISSION),
            "active_limit_formula": "max(1,sum(floor(max(0,node_mem-3500)/300)))",
            "expected_active_limit": P5_ACTIVE_REQUEST_LIMIT,
            "fcfs_key": ["arrival_frame", "tape_sequence"],
        },
        "simulation": copy.deepcopy(P5_SIMULATION),
        "gate": _gate(),
        "runtime_binary": runtime,
        "workload_tape_count": 9,
        "reference_build_count": 90,
        "online_run_count": 90,
        "analysis_contract": {
            "path": "scripts/reviewer_experiments/analysis/p5_common_platform.py",
            "sha256": file_hash(analyzer_path),
            "gate_condition_count": 12,
            "relative_outcomes_sealed_after_conditions_1_to_11": True,
            "relative_outcomes_excluded_from_pass_fail": True,
        },
        "preresult_addendum": {
            "path": "refine-logs/P5_COMMON_PLATFORM_PRERESULT_ADDENDUM.md",
            "sha256": file_hash(addendum_path),
            "faasrank_model_binding_after_tapes": True,
            "faasrank_retraining_or_reselection": False,
            "determinism_uses_timing_free_semantic_hashes": True,
        },
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "pilot",
        "bank_id": "TSCv1.pilot.P5.common-platform.P5P01-P5P03",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": P5_COMMON_PLATFORM_SAMPLE_POLICY,
            "all_seeds": list(P5_COMMON_PLATFORM_SEEDS),
            "selected_seeds": list(P5_COMMON_PLATFORM_SEEDS),
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
        "simulation": copy.deepcopy(P5_SIMULATION),
        "execution": _runtime_execution(config["execution"], runtime),
        "qc": qc,
        "matrix_summary": _matrix_summary(runs),
        "runs": runs,
        "reference_build_dependencies": _reference_build_dependencies(runs),
        "all_tapes_bound": False,
        "all_references_bound": False,
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": [],
        P5_COMMON_PLATFORM_MARKER: marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_p5_common_platform_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite P5 zero-result manifest")
    manifest = build_p5_common_platform_manifest(
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
    write_p5_common_platform_manifest(
        args.output, args.simulator_exe, args.source_git_commit, args.config
    )


if __name__ == "__main__":
    main()
