"""Five-run G6 parent-scheduled lookahead development protocol."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Mapping, Sequence

from scipy import stats as scipy_stats

from ..analysis.feedback_trace import validate_runtime_contract_config
from ..analysis.formal_inputs import validate_canonical_run
from ..analysis.observability import RunArtifacts, load_run_artifacts
from .g1_corrected_runtime import _runtime_execution
from .g3_e0_operational import G3_E0_OPERATIONAL_BASELINES
from .m1_completion_guard import _runtime_receipt
from .m1_development import _bind_candidate, _matrix_summary
from .m1_qualification import _canonical_summary_path, _screen_metrics
from .matrix import (
    _base_workload,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    load_protocol_config,
)
from .schema import (
    G6_LOOKAHEAD_SAMPLE_POLICY,
    G6_LOOKAHEAD_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G6_CANDIDATE = "lookahead_preall_sched"
G6_SELECTION_SCHEMA = "NSE_G6_LOOKAHEAD_SELECTION_V1"
G6_MANIFEST_SCHEMA = "NSE_G6_LOOKAHEAD_DEVELOPMENT_V1"
EXPECTED_G3_READY_MANIFEST_HASH = (
    "c7beed33f706333833e4aca7b66a3e0508761c1babf40f70a2e75d4de6c5a657"
)
EXPECTED_G3_READY_FILE_SHA256 = (
    "a54f0fbbbe02d0b1559b1b094eeefe77f1860b522a6c26b9c69b03262ced02f4"
)
EXPECTED_G3_SELECTION_FILE_SHA256 = (
    "22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7"
)
EXPECTED_G3_SELECTION_DOCUMENT_SHA256 = (
    "4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34"
)
FROZEN_BEST_THROUGHPUT = 1.1514
FROZEN_BEST_QPR = 0.040391615
METRICS = (
    "throughput_requests_per_ms",
    "qpr",
    "latency_mean_ms",
    "cost_per_completed_request",
    "completion_ratio",
)


def _finite(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"G6 {label} is not numeric")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise ProtocolValidationError(f"G6 {label} is invalid")
    return result


def _nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProtocolValidationError(f"G6 {label} is not a nonnegative integer")
    return value


def _load_g3_source(
    manifest_path: Path, selection_path: Path
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    manifest_path = manifest_path.resolve()
    selection_path = selection_path.resolve()
    if file_hash(manifest_path) != EXPECTED_G3_READY_FILE_SHA256:
        raise ProtocolValidationError("G6 source G3 ready-manifest file hash mismatch")
    source = load_and_validate_manifest(manifest_path)
    if source["manifest_hash"] != EXPECTED_G3_READY_MANIFEST_HASH:
        raise ProtocolValidationError("G6 source G3 ready-manifest document mismatch")
    if file_hash(selection_path) != EXPECTED_G3_SELECTION_FILE_SHA256:
        raise ProtocolValidationError("G6 source G3 selection file hash mismatch")
    selection = read_json(selection_path)
    if not isinstance(selection, dict):
        raise ProtocolValidationError("G6 source G3 selection is not an object")
    stored = selection.get("document_sha256")
    payload = copy.deepcopy(selection)
    payload.pop("document_sha256", None)
    binding = selection.get("development_manifest")
    if (
        stored != EXPECTED_G3_SELECTION_DOCUMENT_SHA256
        or object_hash(payload) != stored
        or selection.get("status") != "complete_g3_e0_development_gate_failed"
        or selection.get("run_count") != 135
        or selection.get("formal_confirmation_authorized") is not False
        or not isinstance(binding, dict)
        or binding.get("manifest_hash") != source["manifest_hash"]
        or binding.get("file_sha256") != EXPECTED_G3_READY_FILE_SHA256
        or Path(str(binding.get("path", ""))).resolve() != manifest_path
    ):
        raise ProtocolValidationError("G6 source G3 selection binding is invalid")
    baseline_aggregates = selection.get("baseline_low_aggregates")
    if not isinstance(baseline_aggregates, list) or len(baseline_aggregates) != 9:
        raise ProtocolValidationError("G6 source G3 baseline aggregates are incomplete")
    aggregate_by_method = {
        str(row.get("method")): row
        for row in baseline_aggregates
        if isinstance(row, Mapping)
    }
    throughput_values = {
        method: _finite(
            row.get("mean_throughput_requests_per_ms"),
            f"{method} frozen throughput",
        )
        for method, row in aggregate_by_method.items()
    }
    qpr_values = {
        method: _finite(row.get("mean_qpr"), f"{method} frozen QPR")
        for method, row in aggregate_by_method.items()
    }
    if (
        set(aggregate_by_method) != set(G3_E0_OPERATIONAL_BASELINES)
        or not math.isclose(
            throughput_values.get("sche_Hiku", math.nan),
            FROZEN_BEST_THROUGHPUT,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or not math.isclose(
            qpr_values.get("sche_jiagu", math.nan),
            FROZEN_BEST_QPR,
            rel_tol=0.0,
            abs_tol=5.0e-10,
        )
        or max(throughput_values, key=throughput_values.get) != "sche_Hiku"
        or max(qpr_values, key=qpr_values.get) != "sche_jiagu"
    ):
        raise ProtocolValidationError("G6 frozen best-baseline thresholds are invalid")
    selected = []
    for run in source["runs"]:
        if (
            run["workload"].get("request_freq") != "low"
            or run["cluster"].get("topology") != "homogeneous"
        ):
            continue
        if run["method"] == "sche_nash":
            if run.get("metadata", {}).get("m1_operational_candidate") == "ready_order":
                selected.append(run)
        elif run["method"] in G3_E0_OPERATIONAL_BASELINES:
            selected.append(run)
    if (
        len(selected) != 50
        or sum(run["method"] == "sche_nash" for run in selected) != 5
        or {run["seed"] for run in selected} != set(G6_LOOKAHEAD_SEEDS)
    ):
        raise ProtocolValidationError("G6 source G3 control product is not exact")
    return source, selection, selected


def _source_binding(
    manifest_path: Path,
    selection_path: Path,
    canonical_root: Path,
    source: Mapping[str, Any],
    selection: Mapping[str, Any],
    runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "manifest_path": str(manifest_path.resolve()),
        "manifest_hash": source["manifest_hash"],
        "manifest_file_sha256": file_hash(manifest_path),
        "selection_path": str(selection_path.resolve()),
        "selection_file_sha256": file_hash(selection_path),
        "selection_document_sha256": selection["document_sha256"],
        "canonical_root": str(canonical_root.resolve()),
        "run_count": 135,
        "reused_control_run_count": 50,
        "reused_c0_run_count": 5,
        "reused_baseline_run_count": 45,
        "run_bindings": [
            {"run_id": run["run_id"], "run_spec_hash": run["run_spec_hash"]}
            for run in sorted(runs, key=lambda row: str(row["run_id"]))
        ],
    }


def _candidate_cell(node_count: int) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G6.sche_nash.{G6_CANDIDATE}.low.homogeneous.n{node_count}",
        "sche_nash",
        _base_workload("low", "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={
            "m1_operational_candidate": G6_CANDIDATE,
            "g6_lookahead_role": "parent_scheduled_strict_eq15_candidate",
            "paper_equations_changed": False,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
            "player_collection": "parents_scheduled",
        },
    )


def build_g6_lookahead_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    g3_manifest_path: Path,
    g3_selection_path: Path,
    g3_canonical_root: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact five-run candidate-only, non-formal G6 manifest."""

    source, selection, source_runs = _load_g3_source(
        g3_manifest_path, g3_selection_path
    )
    config = load_protocol_config(config_path)
    runtime = _runtime_receipt(simulator_exe, source_git_commit)
    node_count = int(config["matrix_defaults"]["base_node_count"])
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
    if (
        source["common_hpa_hash"] != common_hpa_hash
        or source["workload_profile_set_hash"] != object_hash(workload_profile_set)
        or source["simulation"] != config["simulation"]
    ):
        raise ProtocolValidationError(
            "G6 current protocol differs from frozen G3 inputs"
        )

    cell = _candidate_cell(node_count)
    source_c0 = {
        run["seed"]: run for run in source_runs if run["method"] == "sche_nash"
    }
    runs = []
    for seed in G6_LOOKAHEAD_SEEDS:
        run = _make_run(config, cell, seed, common_hpa_hash, profiles["low"])
        _bind_candidate(run, G6_CANDIDATE)
        control = source_c0.get(seed)
        if control is None or any(
            run[field] != control[field]
            for field in (
                "workload",
                "cluster",
                "workload_spec_hash",
                "workload_profile",
                "common_hpa",
                "common_hpa_hash",
                "simulation",
            )
        ):
            raise ProtocolValidationError(f"G6 input mismatch against G3 C0 for {seed}")
        if run["workload_tape"]["key"] != control["workload_tape"]["key"]:
            raise ProtocolValidationError(f"G6 workload-tape key mismatch for {seed}")
        runs.append(run)

    activation_gate = {
        "completed_functions_only": True,
        "per_seed_pre_ready_bound_share_at_least": 0.10,
        "per_seed_mean_startup_overlap_ms_strictly_above": 0.0,
        "complete_dispatch_accounting": True,
        "offline_reference_required": True,
    }
    performance_gate = {
        "mean_throughput_strictly_above": FROZEN_BEST_THROUGHPUT,
        "mean_qpr_strictly_above": FROZEN_BEST_QPR,
        "paired_throughput_improvements_at_least": 3,
        "paired_qpr_improvements_at_least": 4,
        "paired_joint_improvements_at_least": 3,
        "per_seed_throughput_control_floor_ratio": 0.80,
        "per_seed_qpr_control_floor_ratio": 0.80,
        "mean_completion_not_below_control": True,
        "mean_latency_strictly_below_control": True,
        "mean_solve_time_ratio_at_most": 3.0,
    }
    marker = {
        "schema_version": G6_MANIFEST_SCHEMA,
        "purpose": "parent-scheduled strict-Eq15 homogeneous-low development gate",
        "candidate": G6_CANDIDATE,
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "utility_guard_relative_regret": 0.0,
        "player_collection": "parents_scheduled",
        "player_order": "arrival_frame_req_id_dag_topological_rank_fn_id",
        "development_seeds": list(G6_LOOKAHEAD_SEEDS),
        "all_valid_runs_retained": True,
        "result_conditioned_extension": False,
        "first_valid_canonical_result_retained": True,
        "source_g3_product": _source_binding(
            g3_manifest_path,
            g3_selection_path,
            g3_canonical_root,
            source,
            selection,
            source_runs,
        ),
        "activation_gate": activation_gate,
        "performance_gate": performance_gate,
        "runtime_binary": runtime,
        "workload_tape_count": 5,
        "candidate_run_count": 5,
        "reference_build_count": len(_reference_build_dependencies(runs)),
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.G6.lookahead.D71-D75",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G6_LOOKAHEAD_SAMPLE_POLICY,
            "all_seeds": list(G6_LOOKAHEAD_SEEDS),
            "selected_seeds": list(G6_LOOKAHEAD_SEEDS),
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
        "g6_lookahead_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g6_lookahead_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    g3_manifest_path: Path,
    g3_selection_path: Path,
    g3_canonical_root: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G6 lookahead manifest")
    manifest = build_g6_lookahead_manifest(
        simulator_exe,
        source_git_commit,
        g3_manifest_path,
        g3_selection_path,
        g3_canonical_root,
        config_path,
    )
    write_json_atomic(output_path, manifest)
    return manifest


def _metric_row(run: Mapping[str, Any], summary: Mapping[str, Any]) -> dict[str, Any]:
    throughput, qpr, latency, cost = _screen_metrics(dict(summary))
    completion = _finite(summary.get("completion_ratio"), "completion ratio")
    return {
        "run_id": str(run["run_id"]),
        "seed": str(run["seed"]),
        "method": str(run["method"]),
        "candidate": run.get("metadata", {}).get("m1_operational_candidate"),
        "throughput_requests_per_ms": throughput,
        "qpr": qpr,
        "latency_mean_ms": latency,
        "cost_per_completed_request": cost,
        "completion_ratio": completion,
    }


def _activation_metrics(artifacts: RunArtifacts) -> dict[str, Any]:
    completed_requests = set()
    completed_functions = 0
    early_bound = 0
    overlap_sum = 0.0
    for request in artifacts.requests:
        request_id = str(request.get("request_id", ""))
        functions = request.get("functions")
        if not request_id or request_id in completed_requests:
            raise ProtocolValidationError("G6 request stream has invalid request IDs")
        if not isinstance(functions, list) or not functions:
            raise ProtocolValidationError("G6 completed request has no functions")
        completed_requests.add(request_id)
        seen_functions = set()
        for function in functions:
            if not isinstance(function, Mapping):
                raise ProtocolValidationError("G6 function timing row is invalid")
            function_id = str(function.get("function_id", ""))
            if not function_id or function_id in seen_functions:
                raise ProtocolValidationError("G6 function timing identity is invalid")
            seen_functions.add(function_id)
            ready = _nonnegative_int(
                function.get("ready_schedule_frame"), "ready_schedule_frame"
            )
            scheduled = _nonnegative_int(
                function.get("scheduled_frame"), "scheduled_frame"
            )
            cold_raw = function.get("cold_start_done_frame")
            cold_done = (
                None
                if cold_raw is None
                else _nonnegative_int(cold_raw, "cold_start_done_frame")
            )
            completed_functions += 1
            early_bound += int(scheduled < ready)
            if cold_done is not None:
                overlap_sum += max(min(cold_done, ready) - scheduled, 0)
    expected = _nonnegative_int(
        artifacts.summary.get("fixed_observation_window", {}).get("completed"),
        "fixed completed requests",
    )
    if len(completed_requests) != expected or completed_functions == 0:
        raise ProtocolValidationError("G6 request stream/summary completion mismatch")
    return {
        "completed_request_count": len(completed_requests),
        "completed_function_count": completed_functions,
        "pre_ready_bound_count": early_bound,
        "pre_ready_bound_share": early_bound / completed_functions,
        "startup_overlap_ms_sum": overlap_sum,
        "mean_startup_overlap_ms": overlap_sum / completed_functions,
    }


def _candidate_runtime(
    run: Mapping[str, Any], artifacts: RunArtifacts
) -> dict[str, Any]:
    configs = [
        event for event in artifacts.nse_events if event.get("kind") == "run_config"
    ]
    if len(configs) != 1:
        raise ProtocolValidationError("G6 candidate lacks exactly one run_config")
    config = configs[0]
    errors = validate_runtime_contract_config(
        config,
        expected_candidate=G6_CANDIDATE,
        expected_r0=float(run["simulator_experiment"]["nash"]["price_feedback_rate"]),
    )
    expected_selector = {
        "schema": None,
        "semantics": "single_ready_order_path",
        "orders": None,
        "eligibility": None,
        "ranking": None,
        "welfare_tolerance": None,
        "dispatch_feedback": False,
    }
    reference = config.get("reference")
    if (
        errors
        or config.get("operational_refinement_schema_version") != 6
        or config.get("player_collection") != "parents_scheduled"
        or config.get("operational_equilibrium_selection") != expected_selector
        or config.get("decision_neutral_diagnostics", {}).get(
            "order_counterfactual_enabled"
        )
        is not False
        or not isinstance(reference, Mapping)
        or reference.get("mode") != "offline_required"
        or reference.get("offline_load_ok") is not True
        or _nonnegative_int(reference.get("offline_entries"), "offline entries") <= 0
    ):
        raise ProtocolValidationError(f"G6 runtime contract failed: {errors}")

    active_windows = 0
    assigned_total = 0
    solve_us = 0
    reference_hits = 0
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError("G6 candidate has no policy windows")
    for window in windows:
        decision = window.get("decision")
        overhead = window.get("overhead")
        if not isinstance(decision, Mapping) or not isinstance(overhead, Mapping):
            raise ProtocolValidationError("G6 candidate window is incomplete")
        assigned = _nonnegative_int(
            decision.get("assigned_players"), "assigned players"
        )
        if assigned == 0:
            continue
        active_windows += 1
        assigned_total += assigned
        solve_us += _nonnegative_int(overhead.get("solve_us"), "solve time")
        social = window.get("social")
        if not isinstance(social, Mapping):
            raise ProtocolValidationError("G6 active window has no social object")
        _nonnegative_int(social.get("reference_state_key"), "reference state key")
        _finite(social.get("reference"), "offline reference")
        if (
            decision.get("complete_assignment") is not True
            or _nonnegative_int(decision.get("commands_prepared"), "commands prepared")
            != assigned
            or _nonnegative_int(decision.get("commands_sent"), "commands sent")
            != assigned
            or _nonnegative_int(
                decision.get("invalid_assignments"), "invalid assignments"
            )
            != 0
            or decision.get("dispatch_channel_failed") is not False
            or window.get("operational_equilibrium_selection") is not None
            or window.get("order_counterfactual") is not None
            or social.get("reference_source") != "offline_table"
        ):
            raise ProtocolValidationError("G6 dispatch/reference accounting failed")
        reference_hits += 1
    if active_windows == 0 or assigned_total == 0 or solve_us <= 0:
        raise ProtocolValidationError("G6 candidate has no active scheduling work")
    return {
        "active_window_count": active_windows,
        "assigned_players": assigned_total,
        "commands_prepared": assigned_total,
        "commands_sent": assigned_total,
        "invalid_assignments": 0,
        "dispatch_channel_failures": 0,
        "offline_reference_hit_windows": reference_hits,
        "aggregate_active_window_solve_us": solve_us,
    }


def _summary(values: Sequence[float], seeds: Sequence[str]) -> dict[str, Any]:
    sample = [_finite(value, "summary value") for value in values]
    if len(sample) != 5 or len(seeds) != 5:
        raise ProtocolValidationError("G6 summaries require exactly five seeds")
    mean = fmean(sample)
    sd = stdev(sample)
    half_width = (
        float(scipy_stats.t.ppf(0.975, len(sample) - 1)) * sd / math.sqrt(len(sample))
    )
    return {
        "n": len(sample),
        "mean": mean,
        "sample_sd": sd,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "positive": sum(value > 1.0e-15 for value in sample),
        "neutral": sum(abs(value) <= 1.0e-15 for value in sample),
        "negative": sum(value < -1.0e-15 for value in sample),
        "values": sample,
        "leave_one_seed_out": [
            {
                "omitted_seed": seed,
                "mean": fmean(
                    value for index, value in enumerate(sample) if index != omitted
                ),
            }
            for omitted, seed in enumerate(seeds)
        ],
    }


def _absolute_summaries(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: G6_LOOKAHEAD_SEEDS.index(str(row["seed"])))
    seeds = [str(row["seed"]) for row in ordered]
    return {
        metric: _summary([float(row[metric]) for row in ordered], seeds)
        for metric in METRICS
    }


def _evaluate_gate(
    candidate_rows: Sequence[Mapping[str, Any]],
    control_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected_seeds = set(G6_LOOKAHEAD_SEEDS)
    if (
        len(candidate_rows) != 5
        or len(control_rows) != 5
        or len(baseline_rows) != 45
        or {str(row["seed"]) for row in candidate_rows} != expected_seeds
        or {str(row["seed"]) for row in control_rows} != expected_seeds
        or {str(row["method"]) for row in baseline_rows}
        != set(G3_E0_OPERATIONAL_BASELINES)
    ):
        raise ProtocolValidationError("G6 gate inputs are incomplete")
    candidates = {str(row["seed"]): row for row in candidate_rows}
    controls = {str(row["seed"]): row for row in control_rows}
    pairs = []
    for seed in G6_LOOKAHEAD_SEEDS:
        candidate = candidates[seed]
        control = controls[seed]
        candidate_solve = _finite(
            candidate.get("aggregate_active_window_solve_us"),
            "candidate solve time",
            positive=True,
        )
        control_solve = _finite(
            control.get("aggregate_active_window_solve_us"),
            "control solve time",
            positive=True,
        )
        throughput_diff = float(candidate["throughput_requests_per_ms"]) - float(
            control["throughput_requests_per_ms"]
        )
        qpr_diff = float(candidate["qpr"]) - float(control["qpr"])
        pairs.append(
            {
                "seed": seed,
                "candidate_run_id": candidate["run_id"],
                "control_run_id": control["run_id"],
                "throughput_difference": throughput_diff,
                "qpr_difference": qpr_diff,
                "latency_improvement_ms": float(control["latency_mean_ms"])
                - float(candidate["latency_mean_ms"]),
                "cost_improvement_per_completed_request": float(
                    control["cost_per_completed_request"]
                )
                - float(candidate["cost_per_completed_request"]),
                "completion_ratio_difference": float(candidate["completion_ratio"])
                - float(control["completion_ratio"]),
                "throughput_control_ratio": float(
                    candidate["throughput_requests_per_ms"]
                )
                / _finite(
                    control["throughput_requests_per_ms"],
                    "control throughput",
                    positive=True,
                ),
                "qpr_control_ratio": float(candidate["qpr"])
                / _finite(control["qpr"], "control QPR", positive=True),
                "solve_time_ratio": candidate_solve / control_solve,
                "throughput_improved": throughput_diff > 0.0,
                "qpr_improved": qpr_diff > 0.0,
                "jointly_improved": throughput_diff > 0.0 and qpr_diff > 0.0,
            }
        )
    seeds = list(G6_LOOKAHEAD_SEEDS)
    paired_metrics = {
        metric: _summary([float(row[metric]) for row in pairs], seeds)
        for metric in (
            "throughput_difference",
            "qpr_difference",
            "latency_improvement_ms",
            "cost_improvement_per_completed_request",
            "completion_ratio_difference",
            "throughput_control_ratio",
            "qpr_control_ratio",
            "solve_time_ratio",
        )
    }
    candidate_summary = _absolute_summaries(candidate_rows)
    control_summary = _absolute_summaries(control_rows)
    baseline_summaries = {}
    for method in G3_E0_OPERATIONAL_BASELINES:
        group = [row for row in baseline_rows if row["method"] == method]
        if len(group) != 5 or {str(row["seed"]) for row in group} != expected_seeds:
            raise ProtocolValidationError(f"G6 baseline {method} is incomplete")
        baseline_summaries[method] = _absolute_summaries(group)
    activation_rows = [
        {
            "seed": row["seed"],
            "pre_ready_bound_share": row["pre_ready_bound_share"],
            "mean_startup_overlap_ms": row["mean_startup_overlap_ms"],
            "passed": row["pre_ready_bound_share"] >= 0.10
            and row["mean_startup_overlap_ms"] > 0.0,
        }
        for row in sorted(
            candidate_rows,
            key=lambda item: G6_LOOKAHEAD_SEEDS.index(str(item["seed"])),
        )
    ]
    throughput_wins = sum(bool(row["throughput_improved"]) for row in pairs)
    qpr_wins = sum(bool(row["qpr_improved"]) for row in pairs)
    joint_wins = sum(bool(row["jointly_improved"]) for row in pairs)
    conditions = {
        "activation_all_seeds": all(row["passed"] for row in activation_rows),
        "mean_throughput_above_frozen_best": (
            candidate_summary["throughput_requests_per_ms"]["mean"]
            > FROZEN_BEST_THROUGHPUT
        ),
        "mean_qpr_above_frozen_best": candidate_summary["qpr"]["mean"]
        > FROZEN_BEST_QPR,
        "paired_throughput_wins_at_least_3": throughput_wins >= 3,
        "paired_qpr_wins_at_least_4": qpr_wins >= 4,
        "paired_joint_wins_at_least_3": joint_wins >= 3,
        "per_seed_throughput_floor": all(
            row["throughput_control_ratio"] >= 0.80 for row in pairs
        ),
        "per_seed_qpr_floor": all(row["qpr_control_ratio"] >= 0.80 for row in pairs),
        "mean_completion_not_below_control": (
            candidate_summary["completion_ratio"]["mean"]
            >= control_summary["completion_ratio"]["mean"]
        ),
        "mean_latency_below_control": candidate_summary["latency_mean_ms"]["mean"]
        < control_summary["latency_mean_ms"]["mean"],
        "mean_solve_time_ratio_at_most_3": paired_metrics["solve_time_ratio"]["mean"]
        <= 3.0,
    }
    passed = all(conditions.values())
    return {
        "status": (
            "complete_g6_development_confirmation_preregistration_authorized"
            if passed
            else "complete_g6_development_gate_failed"
        ),
        "candidate_development_qualified": passed,
        "confirmation_preregistration_authorized": passed,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
        "all_valid_runs_retained": True,
        "conditions": conditions,
        "paired_win_counts": {
            "throughput": throughput_wins,
            "qpr": qpr_wins,
            "joint": joint_wins,
        },
        "activation_rows": activation_rows,
        "candidate_metric_summaries": candidate_summary,
        "control_metric_summaries": control_summary,
        "baseline_metric_summaries": baseline_summaries,
        "paired_rows": pairs,
        "paired_metric_summaries": paired_metrics,
        "frozen_best_thresholds": {
            "throughput_method": "sche_Hiku",
            "throughput_requests_per_ms": FROZEN_BEST_THROUGHPUT,
            "qpr_method": "sche_jiagu",
            "qpr": FROZEN_BEST_QPR,
        },
    }


def _source_rows(
    source: Mapping[str, Any],
    selection: Mapping[str, Any],
    source_runs: Sequence[Mapping[str, Any]],
    canonical_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stored_metrics = {
        str(row["run_id"]): row for row in selection.get("run_metrics", [])
    }
    stored_receipts = {
        str(row["run_id"]): row for row in selection.get("artifact_receipts", [])
    }
    if len(stored_metrics) != 135 or len(stored_receipts) != 135:
        raise ProtocolValidationError("G6 source selection lacks complete G3 receipts")
    result_relative_path = source["execution"].get(
        "result_relative_path", "result.json"
    )
    rows = []
    receipts = []
    for run in source_runs:
        run_dir = canonical_root / run["run_id"]
        validate_canonical_run(
            dict(run),
            run_dir,
            expected_manifest_hash=str(source["manifest_hash"]),
            result_relative_path=result_relative_path,
        )
        summary_path = _canonical_summary_path(canonical_root, run["run_id"])
        summary = read_json(summary_path)
        if not isinstance(summary, dict):
            raise ProtocolValidationError(
                f"G6 source run {run['run_id']} lacks summary"
            )
        row = _metric_row(run, summary)
        stored = stored_metrics.get(str(run["run_id"]))
        if not isinstance(stored, Mapping):
            raise ProtocolValidationError("G6 source metric receipt is missing")
        for metric in METRICS:
            stored_key = metric
            if metric == "throughput_requests_per_ms":
                stored_key = "throughput_requests_per_ms"
            if not math.isclose(
                float(row[metric]),
                _finite(stored.get(stored_key), f"stored {metric}"),
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise ProtocolValidationError(
                    "G6 source metric differs from G3 receipt"
                )
        receipt = {
            "run_id": run["run_id"],
            "run_spec_hash": run["run_spec_hash"],
            "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
            "summary_sha256": file_hash(summary_path),
            "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
        }
        if receipt != stored_receipts.get(str(run["run_id"])):
            raise ProtocolValidationError("G6 source artifact receipt differs from G3")
        if run["method"] == "sche_nash":
            stored_runtime = stored.get("runtime")
            if not isinstance(stored_runtime, Mapping):
                raise ProtocolValidationError("G6 C0 source lacks solve-time receipt")
            row["aggregate_active_window_solve_us"] = _finite(
                stored_runtime.get("aggregate_active_window_solve_us"),
                "stored C0 solve time",
                positive=True,
            )
        rows.append(row)
        receipts.append(receipt)
    return rows, receipts


def analyze_g6_lookahead(
    manifest_path: Path, candidate_canonical_root: Path
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    candidate_canonical_root = candidate_canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("g6_lookahead_development")
    if (
        not isinstance(marker, dict)
        or manifest.get("all_tapes_bound") is not True
        or manifest.get("all_references_bound") is not True
        or len(manifest["runs"]) != 5
    ):
        raise ProtocolValidationError(
            "G6 analysis requires the complete ready manifest"
        )
    source_info = marker["source_g3_product"]
    source, selection, source_runs = _load_g3_source(
        Path(source_info["manifest_path"]), Path(source_info["selection_path"])
    )
    expected_binding = _source_binding(
        Path(source_info["manifest_path"]),
        Path(source_info["selection_path"]),
        Path(source_info["canonical_root"]),
        source,
        selection,
        source_runs,
    )
    if source_info != expected_binding:
        raise ProtocolValidationError("G6 source G3 binding changed after freeze")
    source_rows, source_receipts = _source_rows(
        source,
        selection,
        source_runs,
        Path(source_info["canonical_root"]).resolve(),
    )
    source_c0 = {
        row["seed"]: row for row in source_rows if row["method"] == "sche_nash"
    }
    source_runs_c0 = {
        run["seed"]: run for run in source_runs if run["method"] == "sche_nash"
    }

    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    candidate_rows = []
    candidate_receipts = []
    for run in manifest["runs"]:
        control_run = source_runs_c0.get(run["seed"])
        if control_run is None or run["workload_tape"].get("sha256") != control_run[
            "workload_tape"
        ].get("sha256"):
            raise ProtocolValidationError("G6 candidate/control tape pairing failed")
        run_dir = candidate_canonical_root / run["run_id"]
        qc = validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        contract = qc.get("observations", {}).get("nash_runtime_contract")
        if (
            not isinstance(contract, Mapping)
            or contract.get("strict_eq15_ready") is not True
            or contract.get("stream_contract_ready") is not True
        ):
            raise ProtocolValidationError("G6 candidate failed strict runtime QC")
        artifacts = load_run_artifacts(
            run,
            candidate_canonical_root,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        row = _metric_row(run, artifacts.summary)
        row.update(_candidate_runtime(run, artifacts))
        row.update(_activation_metrics(artifacts))
        candidate_rows.append(row)
        summary_path = _canonical_summary_path(candidate_canonical_root, run["run_id"])
        candidate_receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": run["reference_dependency"]["sha256"],
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "summary_sha256": file_hash(summary_path),
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
            }
        )
    gate = _evaluate_gate(
        candidate_rows,
        list(source_c0.values()),
        [row for row in source_rows if row["method"] != "sche_nash"],
    )
    report: dict[str, Any] = {
        "schema_version": G6_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": gate["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "development_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "runtime_binary": copy.deepcopy(marker["runtime_binary"]),
        "source_g3_product": copy.deepcopy(source_info),
        "definitions": {
            "independent_unit": "run/seed",
            "all_valid_runs_retained": True,
            "completed_functions_only_for_activation": True,
            "paired_by_identical_workload_tape": True,
            "development_results_are_paper_evidence": False,
        },
        "activation_gate": copy.deepcopy(marker["activation_gate"]),
        "performance_gate": copy.deepcopy(marker["performance_gate"]),
        "candidate_run_metrics": candidate_rows,
        "source_control_run_metrics": source_rows,
        "gate_result": gate,
        "candidate_artifact_receipts": candidate_receipts,
        "source_artifact_receipts": source_receipts,
        "candidate_run_count": len(candidate_rows),
        "source_control_run_count": len(source_rows),
        "confirmation_preregistration_authorized": gate[
            "confirmation_preregistration_authorized"
        ],
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_g6_lookahead_selection(
    manifest_path: Path, candidate_canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G6 lookahead selection")
    report = analyze_g6_lookahead(manifest_path, candidate_canonical_root)
    write_json_atomic(output_path, report)
    return report
