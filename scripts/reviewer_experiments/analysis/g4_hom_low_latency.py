"""Read-only homogeneous-low latency-path diagnosis for the frozen G3 product."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy import stats as scipy_stats

from ..protocol.g3_e0_operational import (
    G3_E0_OPERATIONAL_BASELINES,
    G3_E0_OPERATIONAL_SEEDS,
)
from ..protocol.schema import ProtocolValidationError, load_and_validate_manifest
from ..protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from .g3_postfail_diagnosis import (
    CONTROL,
    EXPECTED_SELECTION_DOCUMENT_SHA256,
    EXPECTED_SELECTION_FILE_SHA256,
    _nested,
    _optional_number,
    _required_number,
    _t_summary,
    _validate_selection,
)
from .observability import RunArtifacts, load_run_artifacts


SCHEMA_VERSION = "NSE_G4_HOM_LOW_LATENCY_PATH_DIAGNOSIS_V1"
PRIMARY_BASELINES = (
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
)
STAGES = (
    "schedule_wait_ms",
    "cold_start_wait_ms",
    "data_wait_ms",
    "execution_ms",
)
STAGE_STATS = ("mean", "median", "p95", "p99", "sum")

EXPOSURE_PATHS: dict[str, tuple[str, ...]] = {
    "data_blocked_queue_mean": ("cluster", "queue_data_blocked_total"),
    "parent_blocked_queue_mean": ("cluster", "queue_parent_blocked_total"),
    "runnable_queue_mean": ("cluster", "queue_runnable_total"),
    "resident_queue_mean": ("cluster", "queue_resident_total"),
    "starting_resident_queue_mean": (
        "cluster",
        "queue_starting_resident_total",
    ),
    "pressure_mean": ("cluster", "pressure_mean"),
    "containers_running_mean": ("cluster", "containers_running"),
    "containers_starting_mean": ("cluster", "containers_starting"),
    "cross_node_placement_ratio": ("network", "cross_node_placement_ratio"),
    "co_location_conflict_ratio": (
        "decision",
        "co_location_conflict_pair_ratio_proxy",
    ),
}

EXPECTED_EXPOSURES: dict[str, tuple[tuple[str, int], ...]] = {
    "schedule_wait_ms": (
        ("waiting_share", 1),
        ("no_feasible_share", 1),
        ("parent_blocked_queue_mean", 1),
        ("runnable_queue_mean", 1),
        ("resident_queue_mean", 1),
    ),
    "cold_start_wait_ms": (
        ("selected_starting_share", 1),
        ("selected_cold_or_nonrunning_share", 1),
        ("containers_starting_mean", 1),
        ("selected_running_warm_share", -1),
    ),
    "data_wait_ms": (
        ("cross_node_placement_ratio", 1),
        ("data_blocked_queue_mean", 1),
    ),
    "execution_ms": (
        ("pressure_mean", 1),
        ("node_cpu_utilization_mean", 1),
        ("co_location_conflict_ratio", 1),
    ),
}


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ProtocolValidationError("percentile requires observations")
    return float(
        np.quantile(np.asarray(values, dtype=float), probability, method="linear")
    )


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        raise ProtocolValidationError("stage distribution is empty")
    return {
        "n": len(values),
        "mean": fmean(values),
        "median": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "sum": sum(values),
        "positive_share": sum(value > 0.0 for value in values) / len(values),
    }


def _function_stages(function: Mapping[str, Any]) -> dict[str, float]:
    ready = int(
        _required_number(function.get("ready_schedule_frame"), "function.ready")
    )
    scheduled = int(
        _required_number(function.get("scheduled_frame"), "function.scheduled")
    )
    function_done = int(
        _required_number(function.get("function_done_frame"), "function.done")
    )
    schedule_boundary = max(ready, scheduled)
    cold_raw = function.get("cold_start_done_frame")
    cold_done = (
        schedule_boundary
        if cold_raw is None
        else max(
            int(_required_number(cold_raw, "function.cold_done")), schedule_boundary
        )
    )
    data_raw = function.get("data_received_frame")
    data_done = (
        cold_done
        if data_raw is None
        else max(int(_required_number(data_raw, "function.data_done")), cold_done)
    )
    values = {
        "schedule_wait_ms": float(max(scheduled - ready, 0)),
        "cold_start_wait_ms": float(cold_done - schedule_boundary),
        "data_wait_ms": float(data_done - cold_done),
        "execution_ms": float(function_done - data_done),
    }
    if any(value < 0.0 for value in values.values()):
        raise ProtocolValidationError("negative completed-function stage duration")
    return values


def _request_maps(
    artifacts: RunArtifacts,
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    requests: dict[str, dict[str, Any]] = {}
    functions: dict[tuple[str, str], dict[str, Any]] = {}
    for request in artifacts.requests:
        request_id = str(request.get("request_id", ""))
        if not request_id or request_id in requests:
            raise ProtocolValidationError(
                f"invalid/duplicate request ID in {artifacts.run_id}"
            )
        latency = _required_number(request.get("latency_ms"), "request.latency")
        function_rows = request.get("functions")
        if not isinstance(function_rows, list) or not function_rows:
            raise ProtocolValidationError("completed request lacks functions")
        requests[request_id] = {"latency_ms": latency, "request": request}
        for function in function_rows:
            if not isinstance(function, Mapping):
                raise ProtocolValidationError("function row is not an object")
            function_id = str(function.get("function_id", ""))
            key = (request_id, function_id)
            if not function_id or key in functions:
                raise ProtocolValidationError(
                    "invalid/duplicate completed function key"
                )
            functions[key] = {
                "stages": _function_stages(function),
                "cold_event": function.get("cold_start_done_frame") is not None,
                "qos_class": function.get("qos_class"),
            }
    expected = int(
        _required_number(
            _nested(artifacts.summary, ("fixed_observation_window", "completed")),
            "fixed completed",
        )
    )
    if len(requests) != expected:
        raise ProtocolValidationError(
            f"request stream/summary completion mismatch for {artifacts.run_id}"
        )
    return requests, functions


def _stage_summary(
    functions: Mapping[tuple[str, str], Mapping[str, Any]]
) -> dict[str, Any]:
    if not functions:
        raise ProtocolValidationError("run has no completed functions")
    row: dict[str, Any] = {"completed_function_count": len(functions)}
    mean_sum = 0.0
    for stage in STAGES:
        values = [
            _required_number(function["stages"][stage], stage)
            for function in functions.values()
        ]
        distribution = _distribution(values)
        for statistic in STAGE_STATS:
            row[f"{stage}_{statistic}"] = distribution[statistic]
        row[f"{stage}_positive_share"] = distribution["positive_share"]
        mean_sum += distribution["mean"]
    for stage in STAGES:
        row[f"{stage}_mean_fraction"] = (
            row[f"{stage}_mean"] / mean_sum if mean_sum > 0.0 else None
        )
    cold_count = sum(bool(function["cold_event"]) for function in functions.values())
    row["cold_start_event_count"] = cold_count
    row["cold_start_event_share"] = cold_count / len(functions)
    return row


def _nash_exposures(artifacts: RunArtifacts) -> dict[str, Any]:
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError("NSESche run lacks window metrics")
    totals: defaultdict[str, float] = defaultdict(float)
    active = 0
    complete = 0
    inner_limit = 0
    outer_limit = 0
    dispatch_failures = 0
    exposure_values: defaultdict[str, list[float]] = defaultdict(list)
    for window in windows:
        decision = window.get("decision")
        solver = window.get("solver")
        if not isinstance(decision, Mapping) or not isinstance(solver, Mapping):
            raise ProtocolValidationError("NSESche window lacks decision/solver")
        players = _required_number(
            decision.get("request_function_players"), "decision.players"
        )
        pending = _required_number(
            decision.get("pending_request_function_pairs"), "decision.pending"
        )
        assigned = _required_number(
            decision.get("assigned_players"), "decision.assigned"
        )
        totals["players"] += players
        totals["pending"] += pending
        totals["waiting"] += _required_number(
            decision.get("waiting_for_candidate_nodes"), "decision.waiting"
        )
        totals["no_feasible"] += _required_number(
            decision.get("no_feasible_players"), "decision.no_feasible"
        )
        if assigned <= 0.0:
            continue
        active += 1
        totals["assigned"] += assigned
        totals["candidate_evaluations"] += _required_number(
            decision.get("candidate_evaluations"), "decision.candidates"
        )
        totals["moves"] += _required_number(
            solver.get("assignment_moves"), "solver.moves"
        )
        for name, field in (
            ("selected_running_warm", "selected_running_warm_players"),
            ("selected_starting", "selected_starting_container_players"),
            ("selected_cold", "selected_cold_or_nonrunning_players"),
            ("warm_available", "running_warm_available_players"),
            ("warm_bypassed", "running_warm_bypassed_players"),
        ):
            totals[name] += _required_number(decision.get(field), f"decision.{field}")
        complete += int(bool(decision.get("complete_assignment")))
        inner_limit += int(bool(solver.get("inner_limit_hit")))
        outer_limit += int(bool(solver.get("outer_limit_hit")))
        dispatch_failures += int(bool(decision.get("dispatch_channel_failed")))
        for name, path in EXPOSURE_PATHS.items():
            value = _optional_number(_nested(window, path))
            if value is not None:
                exposure_values[name].append(value)
    assigned_total = totals["assigned"]
    warm_available = totals["warm_available"]
    row: dict[str, Any] = {
        "window_count": len(windows),
        "active_window_count": active,
        "waiting_share": totals["waiting"] / totals["pending"]
        if totals["pending"]
        else 0.0,
        "no_feasible_share": totals["no_feasible"] / totals["players"]
        if totals["players"]
        else 0.0,
        "selected_running_warm_share": totals["selected_running_warm"] / assigned_total,
        "selected_starting_share": totals["selected_starting"] / assigned_total,
        "selected_cold_or_nonrunning_share": totals["selected_cold"] / assigned_total,
        "warm_bypass_share": totals["warm_bypassed"] / warm_available
        if warm_available
        else 0.0,
        "candidates_per_assigned_player": totals["candidate_evaluations"]
        / assigned_total,
        "assignment_moves_per_assigned_player": totals["moves"] / assigned_total,
        "complete_assignment_active_share": complete / active,
        "inner_limit_active_share": inner_limit / active,
        "outer_limit_active_share": outer_limit / active,
        "dispatch_failure_active_share": dispatch_failures / active,
    }
    for name in EXPOSURE_PATHS:
        values = exposure_values[name]
        row[name] = fmean(values) if values else None
    cpu_utilization = [
        _required_number(
            frame.get("node_cpu_utilization_mean"),
            "frame.node_cpu_utilization_mean",
        )
        for frame in artifacts.frames
    ]
    row["node_cpu_utilization_mean"] = fmean(cpu_utilization)
    return row


def _run_row(run: Mapping[str, Any], artifacts: RunArtifacts) -> dict[str, Any]:
    summary = artifacts.summary
    if (
        summary.get("schema") != "NSE_SUMMARY_V1"
        or summary.get("run_id") != run.get("run_id")
        or summary.get("run_complete") is not True
    ):
        raise ProtocolValidationError("invalid latency-diagnosis summary")
    requests, functions = _request_maps(artifacts)
    method = str(run["method"])
    metadata = run.get("metadata")
    candidate = (
        str(metadata.get("m1_operational_candidate"))
        if method == "sche_nash" and isinstance(metadata, Mapping)
        else None
    )
    row: dict[str, Any] = {
        "run_id": str(run["run_id"]),
        "seed": str(run["seed"]),
        "method": method,
        "candidate": candidate,
        "completed_request_count": len(requests),
        "full_cohort_latency_mean_ms": _required_number(
            _nested(summary, ("drained_arrival_cohort", "latency_ms", "mean")),
            "drained latency mean",
        ),
        "full_cohort_latency_p95_ms": _required_number(
            _nested(summary, ("drained_arrival_cohort", "latency_ms", "p95")),
            "drained latency p95",
        ),
    }
    row.update(_stage_summary(functions))
    if method == "sche_nash":
        row.update(_nash_exposures(artifacts))
    row["_requests"] = requests
    row["_functions"] = functions
    return row


def _difference_distribution(values: Sequence[float]) -> dict[str, Any]:
    result = _distribution(values)
    result["negative_share"] = sum(value < 0.0 for value in values) / len(values)
    result["neutral_share"] = sum(value == 0.0 for value in values) / len(values)
    return result


def _match_pair(nash: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    if nash["seed"] != baseline["seed"]:
        raise ProtocolValidationError("latency pair seed mismatch")
    nash_requests = nash["_requests"]
    baseline_requests = baseline["_requests"]
    request_ids = sorted(set(nash_requests).intersection(baseline_requests))
    if not request_ids:
        raise ProtocolValidationError("latency pair has no common completed requests")
    request_differences = [
        nash_requests[key]["latency_ms"] - baseline_requests[key]["latency_ms"]
        for key in request_ids
    ]
    nash_functions = nash["_functions"]
    baseline_functions = baseline["_functions"]
    function_keys = sorted(set(nash_functions).intersection(baseline_functions))
    if not function_keys:
        raise ProtocolValidationError("latency pair has no common completed functions")
    row: dict[str, Any] = {
        "baseline": baseline["method"],
        "seed": nash["seed"],
        "nash_run_id": nash["run_id"],
        "baseline_run_id": baseline["run_id"],
        "nash_completed_requests": len(nash_requests),
        "baseline_completed_requests": len(baseline_requests),
        "common_completed_requests": len(request_ids),
        "nash_only_completed_requests": len(
            set(nash_requests) - set(baseline_requests)
        ),
        "baseline_only_completed_requests": len(
            set(baseline_requests) - set(nash_requests)
        ),
        "common_request_coverage_nash": len(request_ids) / len(nash_requests),
        "common_request_coverage_baseline": len(request_ids) / len(baseline_requests),
        "common_completed_functions": len(function_keys),
        "full_cohort_latency_mean_difference_ms": nash["full_cohort_latency_mean_ms"]
        - baseline["full_cohort_latency_mean_ms"],
    }
    for statistic, value in _difference_distribution(request_differences).items():
        row[f"matched_request_latency_difference_{statistic}"] = value
    for stage in STAGES:
        differences = [
            nash_functions[key]["stages"][stage]
            - baseline_functions[key]["stages"][stage]
            for key in function_keys
        ]
        for statistic, value in _difference_distribution(differences).items():
            row[f"matched_function_{stage}_difference_{statistic}"] = value
        row[f"full_completed_function_{stage}_mean_difference"] = (
            nash[f"{stage}_mean"] - baseline[f"{stage}_mean"]
        )
    return row


def _pair_aggregates(pair_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    aggregates = []
    for baseline in G3_E0_OPERATIONAL_BASELINES:
        group = [row for row in pair_rows if row["baseline"] == baseline]
        if len(group) != 5 or {row["seed"] for row in group} != set(
            G3_E0_OPERATIONAL_SEEDS
        ):
            raise ProtocolValidationError(f"incomplete latency pair group {baseline}")
        stage_summaries = {
            stage: _t_summary(
                [
                    _required_number(
                        row[f"full_completed_function_{stage}_mean_difference"],
                        stage,
                    )
                    for row in group
                ]
            )
            for stage in STAGES
        }
        positive_means = {
            stage: summary["mean"]
            for stage, summary in stage_summaries.items()
            if summary["mean"] > 0.0
        }
        largest = []
        if positive_means:
            maximum = max(positive_means.values())
            largest = sorted(
                stage
                for stage, value in positive_means.items()
                if abs(value - maximum) <= 1e-12
            )
        full_sign_matches = sum(
            _required_number(row["full_cohort_latency_mean_difference_ms"], "full gap")
            * _required_number(
                row["matched_request_latency_difference_mean"], "matched gap"
            )
            > 0.0
            for row in group
        )
        aggregates.append(
            {
                "baseline": baseline,
                "stage_differences": stage_summaries,
                "largest_positive_mean_stages": largest,
                "full_matched_latency_same_sign_count": full_sign_matches,
                "full_cohort_latency_difference": _t_summary(
                    [
                        _required_number(
                            row["full_cohort_latency_mean_difference_ms"], "full gap"
                        )
                        for row in group
                    ]
                ),
                "matched_request_latency_difference": _t_summary(
                    [
                        _required_number(
                            row["matched_request_latency_difference_mean"],
                            "matched gap",
                        )
                        for row in group
                    ]
                ),
            }
        )
    return aggregates


def _spearman_with_loo(
    rows: Sequence[Mapping[str, Any]], x_field: str, y_field: str
) -> dict[str, Any]:
    values = [
        (
            str(row["seed"]),
            _optional_number(row.get(x_field)),
            _optional_number(row.get(y_field)),
        )
        for row in rows
    ]
    if len(values) != 5 or any(
        left is None or right is None for _, left, right in values
    ):
        return {"status": "incomplete", "rho": None, "leave_one_seed_out": []}
    x = [float(left) for _, left, _ in values]
    y = [float(right) for _, _, right in values]
    if len(set(x)) == 1 or len(set(y)) == 1:
        return {"status": "constant_input", "rho": None, "leave_one_seed_out": []}
    rho = float(scipy_stats.spearmanr(x, y).statistic)
    loo = []
    for omitted, _, _ in values:
        kept = [(left, right) for seed, left, right in values if seed != omitted]
        loo_rho = (
            None
            if len({left for left, _ in kept}) == 1
            or len({right for _, right in kept}) == 1
            else float(
                scipy_stats.spearmanr(
                    [left for left, _ in kept], [right for _, right in kept]
                ).statistic
            )
        )
        loo.append({"omitted_seed": omitted, "rho": loo_rho, "n": len(kept)})
    return {"status": "ok", "rho": rho, "leave_one_seed_out": loo}


def _exposure_associations(
    nash_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    associations = []
    for stage, exposures in EXPECTED_EXPOSURES.items():
        for statistic in ("mean", "p95"):
            outcome = f"{stage}_{statistic}"
            for exposure, expected_sign in exposures:
                result = _spearman_with_loo(nash_rows, exposure, outcome)
                result.update(
                    {
                        "stage": stage,
                        "stage_statistic": statistic,
                        "exposure": exposure,
                        "expected_sign": expected_sign,
                    }
                )
                associations.append(result)
    return associations


def _association_passes(row: Mapping[str, Any]) -> bool:
    rho = _optional_number(row.get("rho"))
    if rho is None or abs(rho) < 0.50 or rho * int(row["expected_sign"]) <= 0.0:
        return False
    loo = [
        _optional_number(item.get("rho"))
        for item in row.get("leave_one_seed_out", [])
        if isinstance(item, Mapping)
    ]
    return (
        len(loo) == 5
        and sum(
            value is not None and value * int(row["expected_sign"]) > 0.0
            for value in loo
        )
        >= 4
    )


def _trace_decision(
    aggregates: Sequence[Mapping[str, Any]], associations: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    evidence = {}
    for stage in STAGES:
        consistent = [
            row["baseline"]
            for row in aggregates
            if row["baseline"] in PRIMARY_BASELINES
            and row["stage_differences"][stage]["positive"] >= 4
        ]
        largest = [
            row["baseline"]
            for row in aggregates
            if row["baseline"] in PRIMARY_BASELINES
            and stage in row["largest_positive_mean_stages"]
        ]
        same_comparators = sorted(set(consistent).intersection(largest))
        censoring_confirmed = [
            row["baseline"]
            for row in aggregates
            if row["baseline"] in same_comparators
            and row["full_matched_latency_same_sign_count"] >= 4
            and row["full_cohort_latency_difference"]["positive"] >= 4
            and row["matched_request_latency_difference"]["positive"] >= 4
        ]
        passing_associations = [
            row
            for row in associations
            if row["stage"] == stage and _association_passes(row)
        ]
        evidence[stage] = {
            "consistent_positive_gap_baselines": consistent,
            "largest_positive_gap_baselines": largest,
            "same_comparators": same_comparators,
            "common_completion_confirmed_baselines": censoring_confirmed,
            "passing_expected_direction_associations": passing_associations,
            "criteria_1_2_3_4_pass": len(same_comparators) >= 3
            and len(censoring_confirmed) >= 3
            and bool(passing_associations),
        }
    candidates = [
        stage for stage, row in evidence.items() if row["criteria_1_2_3_4_pass"]
    ]
    return {
        "status": (
            "complete_trace_single_stage_source_inventory_required"
            if len(candidates) == 1
            else "complete_trace_no_unique_latency_stage"
        ),
        "trace_supported_stage": candidates[0] if len(candidates) == 1 else None,
        "candidate_stages": candidates,
        "stage_evidence": evidence,
        "source_inventory_required": len(candidates) == 1,
        "source_change_authorized": False,
        "new_sampling_authorized": False,
    }


def analyze(selection_path: Path, canonical_root: Path) -> dict[str, Any]:
    selection = _validate_selection(selection_path)
    manifest_info = selection.get("development_manifest")
    if not isinstance(manifest_info, Mapping):
        raise ProtocolValidationError("selection lacks manifest binding")
    manifest_path = Path(str(manifest_info["path"])).resolve()
    if file_hash(manifest_path) != manifest_info["file_sha256"]:
        raise ProtocolValidationError("ready manifest hash mismatch")
    manifest = load_and_validate_manifest(manifest_path)
    if manifest["manifest_hash"] != manifest_info["manifest_hash"]:
        raise ProtocolValidationError("ready manifest document mismatch")
    selected_runs = []
    for run in manifest["runs"]:
        if (
            run["workload"]["request_freq"] != "low"
            or run["cluster"]["topology"] != "homogeneous"
        ):
            continue
        if run["method"] == "sche_nash":
            if run.get("metadata", {}).get("m1_operational_candidate") == CONTROL:
                selected_runs.append(run)
        elif run["method"] in G3_E0_OPERATIONAL_BASELINES:
            selected_runs.append(run)
    if len(selected_runs) != 50:
        raise ProtocolValidationError("G4 requires exactly 50 homogeneous-low runs")
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    run_rows = []
    receipts = []
    for run in selected_runs:
        artifacts = load_run_artifacts(
            run,
            canonical_root,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        run_rows.append(_run_row(run, artifacts))
        receipts.append(
            {
                "run_id": run["run_id"],
                "manifest_sha256": file_hash(artifacts.run_directory / "manifest.json"),
                "qc_report_sha256": file_hash(
                    artifacts.run_directory / "qc_report.json"
                ),
            }
        )
    nash_rows = [row for row in run_rows if row.get("candidate") == CONTROL]
    if len(nash_rows) != 5:
        raise ProtocolValidationError("G4 requires five C0 runs")
    nash_by_seed = {row["seed"]: row for row in nash_rows}
    pair_rows = []
    for row in run_rows:
        if row["method"] in G3_E0_OPERATIONAL_BASELINES:
            pair_rows.append(_match_pair(nash_by_seed[row["seed"]], row))
    if len(pair_rows) != 45:
        raise ProtocolValidationError("G4 requires 45 baseline pairs")
    aggregates = _pair_aggregates(pair_rows)
    associations = _exposure_associations(nash_rows)
    decision = _trace_decision(aggregates, associations)

    public_run_rows = [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in run_rows
    ]
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": decision["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "selection_artifact": {
            "path": str(selection_path.resolve()),
            "file_sha256": EXPECTED_SELECTION_FILE_SHA256,
            "document_sha256": EXPECTED_SELECTION_DOCUMENT_SHA256,
        },
        "development_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "definitions": {
            "independent_unit": "run/seed",
            "function_stage_scope": "completed functions; not a causal sum of request latency",
            "common_completion_scope": "censoring diagnostic; does not replace full cohort",
            "all_valid_runs_retained": True,
        },
        "run_stage_metrics": public_run_rows,
        "matched_pair_metrics": pair_rows,
        "baseline_pair_aggregates": aggregates,
        "nash_exposure_stage_associations": associations,
        "trace_decision": decision,
        "artifact_receipts": receipts,
        "run_count": len(run_rows),
        "pair_count": len(pair_rows),
        "source_inventory_complete": False,
        "source_change_authorized": False,
        "new_sampling_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def _csv_value(value: Any) -> Any:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"))
        if isinstance(value, (dict, list, tuple))
        else value
    )


def _write_csv_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ProtocolValidationError(f"empty CSV product {path.name}")
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})
    temporary.replace(path)


def write_outputs(report: Mapping[str, Any], output_dir: Path) -> list[Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    names = (
        "g4_hom_low_latency.json",
        "g4_hom_low_run_stage_metrics.csv",
        "g4_hom_low_matched_pairs.csv",
        "g4_hom_low_pair_aggregates.csv",
        "g4_hom_low_exposure_associations.csv",
    )
    paths = [output_dir / name for name in names]
    if any(path.exists() for path in paths):
        raise FileExistsError("G4 latency output already exists")
    write_json_atomic(paths[0], dict(report))
    try:
        _write_csv_atomic(paths[1], report["run_stage_metrics"])
        _write_csv_atomic(paths[2], report["matched_pair_metrics"])
        _write_csv_atomic(paths[3], report["baseline_pair_aggregates"])
        _write_csv_atomic(paths[4], report["nash_exposure_stage_associations"])
    except Exception:
        for path in paths:
            if path.exists():
                path.unlink()
            temporary = path.with_suffix(path.suffix + ".tmp")
            if temporary.exists():
                temporary.unlink()
        raise
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.selection, args.canonical_root)
    outputs = write_outputs(report, args.output_dir)
    print(
        json.dumps(
            {
                "status": report["status"],
                "document_sha256": report["document_sha256"],
                "run_count": report["run_count"],
                "pair_count": report["pair_count"],
                "outputs": [str(path) for path in outputs],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
