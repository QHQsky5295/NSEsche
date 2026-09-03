"""Read-only G5 diagnosis of proactive DAG binding and warm-node bypass."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping, Sequence

import numpy as np

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
    _required_number,
    _t_summary,
    _validate_selection,
)
from .g4_hom_low_latency import _write_csv_atomic
from .observability import RunArtifacts, load_run_artifacts


SCHEMA_VERSION = "NSE_G5_LOOKAHEAD_WARM_PATH_DIAGNOSIS_V1"
EXPECTED_G4_FILE_SHA256 = (
    "1f58e404f39f3aa03cd4c2e03865800caa95e0a687f3a00c335bd0d8798556c5"
)
EXPECTED_G4_DOCUMENT_SHA256 = (
    "d65feedbd8894df12a38f583b23ee319f008507188671985c9ad8621b3e1749e"
)
EXPECTED_MANIFEST_HASH = (
    "c7beed33f706333833e4aca7b66a3e0508761c1babf40f70a2e75d4de6c5a657"
)
LOOKAHEAD_BASELINES = ("sche_OCS", "sche_Hiku", "sche_jiagu", "sche_orion")
CONTROL_BASELINE = "sche_FaaSRank"
SOURCE_CONTRACT = {
    "serverless_sim/src/sche/sche_nash.rs": "35dcce5ea95da12800ff662d17cb69f125d752bbe1a3fb0b6e662b1ecd99aa46",
    "serverless_sim/src/sche/sche_FaaSRank.rs": "88165558a2415e4b25b733ff873ed0ca14983e4c8c44befb55dadde82c64fbac",
    "serverless_sim/src/sche/sche_ocs.rs": "f5a10d0d84c4ff7e3371bfdb1dd725cba1a4920082eaffd9a5423ff5c16be715",
    "serverless_sim/src/sche/sche_hiku.rs": "47ab2703983ba97aba8a82763d78b2a81a74d831b0df25fd0ed3648f6437fbef",
    "serverless_sim/src/sche/sche_jiagu.rs": "e81230a8602ea9cbd7d12793660105ee1cda110f939c7236b9b114b951f833f3",
    "serverless_sim/src/sche/sche_orion.rs": "0a1fe41bc734d9539bbdbb9df17142a66250abadecaccda6e6a4ac73b1bb1dfc",
    "serverless_sim/src/sim_run.rs": "8226f8c66a7f26c641a07a3802f4440e51bd26c61ea02d2e6e46296fdeda3cb7",
}
SOURCE_MODES = {
    "sche_nash": "PreAllDone",
    "sche_FaaSRank": "PreAllDone",
    "sche_OCS": "PreAllSched",
    "sche_Hiku": "All",
    "sche_jiagu": "All",
    "sche_orion": "All",
}
SOURCE_PATH_MODES = {
    "serverless_sim/src/sche/sche_nash.rs": "PreAllDone",
    "serverless_sim/src/sche/sche_FaaSRank.rs": "PreAllDone",
    "serverless_sim/src/sche/sche_ocs.rs": "PreAllSched",
    "serverless_sim/src/sche/sche_hiku.rs": "All",
    "serverless_sim/src/sche/sche_jiagu.rs": "All",
    "serverless_sim/src/sche/sche_orion.rs": "All",
    "serverless_sim/src/sim_run.rs": "definition",
}
TIMING_METRICS = (
    "pre_ready_bound",
    "pre_ready_lead_ms",
    "startup_overlap_ms",
    "post_ready_cold_wait_ms",
)


def _required_int(value: Any, label: str) -> int:
    number = _required_number(value, label)
    integer = int(number)
    if number != integer or integer < 0:
        raise ProtocolValidationError(f"{label} must be a nonnegative integer")
    return integer


def _validate_g4(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if file_hash(path) != EXPECTED_G4_FILE_SHA256:
        raise ProtocolValidationError("unexpected G4 report file hash")
    report = read_json(path)
    if not isinstance(report, dict):
        raise ProtocolValidationError("G4 report is not an object")
    stored = report.get("document_sha256")
    payload = dict(report)
    payload.pop("document_sha256", None)
    if stored != EXPECTED_G4_DOCUMENT_SHA256 or object_hash(payload) != stored:
        raise ProtocolValidationError("G4 report document hash mismatch")
    if (
        report.get("status") != "complete_trace_no_unique_latency_stage"
        or report.get("run_count") != 50
        or report.get("pair_count") != 45
        or report.get("new_sampling_authorized") is not False
    ):
        raise ProtocolValidationError("G4 report does not bind the closed diagnosis")
    return report


def _validate_sources(repo_root: Path) -> list[dict[str, str]]:
    receipts = []
    for relative, expected in SOURCE_CONTRACT.items():
        path = repo_root / relative
        actual = file_hash(path)
        if expected and actual != expected:
            raise ProtocolValidationError(f"source hash mismatch: {relative}")
        receipts.append(
            {
                "path": relative,
                "file_sha256": actual,
                "collection_mode": SOURCE_PATH_MODES[relative],
            }
        )
    return receipts


def _function_timing(function: Mapping[str, Any]) -> dict[str, float]:
    ready = _required_int(function.get("ready_schedule_frame"), "function.ready")
    scheduled = _required_int(function.get("scheduled_frame"), "function.scheduled")
    cold_raw = function.get("cold_start_done_frame")
    cold_done = (
        None if cold_raw is None else _required_int(cold_raw, "function.cold_done")
    )
    lead = max(ready - scheduled, 0)
    overlap = 0 if cold_done is None else max(min(cold_done, ready) - scheduled, 0)
    cold_wait = 0 if cold_done is None else max(cold_done - max(ready, scheduled), 0)
    return {
        "pre_ready_bound": float(scheduled < ready),
        "pre_ready_lead_ms": float(lead),
        "startup_overlap_ms": float(overlap),
        "post_ready_cold_wait_ms": float(cold_wait),
        "scheduled_frame": float(scheduled),
        "cold_event": float(cold_done is not None),
    }


def _function_map(artifacts: RunArtifacts) -> dict[tuple[str, str], dict[str, float]]:
    functions: dict[tuple[str, str], dict[str, float]] = {}
    request_ids = set()
    for request in artifacts.requests:
        request_id = str(request.get("request_id", ""))
        if not request_id or request_id in request_ids:
            raise ProtocolValidationError("invalid/duplicate completed request ID")
        request_ids.add(request_id)
        rows = request.get("functions")
        if not isinstance(rows, list) or not rows:
            raise ProtocolValidationError("completed request lacks functions")
        for function in rows:
            if not isinstance(function, Mapping):
                raise ProtocolValidationError("function row is not an object")
            function_id = str(function.get("function_id", ""))
            key = (request_id, function_id)
            if not function_id or key in functions:
                raise ProtocolValidationError(
                    "invalid/duplicate completed function key"
                )
            functions[key] = _function_timing(function)
    expected = _required_int(
        artifacts.summary.get("fixed_observation_window", {}).get("completed"),
        "fixed completed",
    )
    if len(request_ids) != expected:
        raise ProtocolValidationError("request stream/summary completion mismatch")
    if not functions:
        raise ProtocolValidationError("run has no completed functions")
    return functions


def _percentile(values: Sequence[float], probability: float) -> float:
    return float(
        np.quantile(np.asarray(values, dtype=float), probability, method="linear")
    )


def _distribution(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise ProtocolValidationError("empty timing distribution")
    return {
        "n": len(values),
        "mean": fmean(values),
        "median": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "sum": sum(values),
        "positive_share": sum(value > 0.0 for value in values) / len(values),
    }


def _timing_summary(
    functions: Mapping[tuple[str, str], Mapping[str, float]]
) -> dict[str, Any]:
    row: dict[str, Any] = {"completed_function_count": len(functions)}
    for metric in TIMING_METRICS:
        values = [float(function[metric]) for function in functions.values()]
        for statistic, value in _distribution(values).items():
            row[f"{metric}_{statistic}"] = value
    return row


def _pair_row(nash: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    if nash["seed"] != baseline["seed"]:
        raise ProtocolValidationError("G5 pair seed mismatch")
    nash_functions = nash["_functions"]
    baseline_functions = baseline["_functions"]
    common = sorted(set(nash_functions).intersection(baseline_functions))
    if not common:
        raise ProtocolValidationError("G5 pair has no common completed functions")

    def full_advantage(metric: str) -> float:
        suffix = "mean"
        if metric == "pre_ready_bound":
            suffix = "mean"
        return float(baseline[f"{metric}_{suffix}"]) - float(nash[f"{metric}_{suffix}"])

    row: dict[str, Any] = {
        "baseline": baseline["method"],
        "seed": nash["seed"],
        "nash_run_id": nash["run_id"],
        "baseline_run_id": baseline["run_id"],
        "nash_completed_functions": len(nash_functions),
        "baseline_completed_functions": len(baseline_functions),
        "common_completed_functions": len(common),
        "full_pre_ready_bound_share_advantage": full_advantage("pre_ready_bound"),
        "full_pre_ready_lead_ms_advantage": full_advantage("pre_ready_lead_ms"),
        "full_startup_overlap_ms_advantage": full_advantage("startup_overlap_ms"),
        "full_nash_post_ready_cold_disadvantage_ms": float(
            nash["post_ready_cold_wait_ms_mean"]
        )
        - float(baseline["post_ready_cold_wait_ms_mean"]),
    }
    for metric in ("pre_ready_bound", "pre_ready_lead_ms", "startup_overlap_ms"):
        values = [
            float(baseline_functions[key][metric]) - float(nash_functions[key][metric])
            for key in common
        ]
        row[f"common_{metric}_advantage"] = fmean(values)
    cold_values = [
        float(nash_functions[key]["post_ready_cold_wait_ms"])
        - float(baseline_functions[key]["post_ready_cold_wait_ms"])
        for key in common
    ]
    row["common_nash_post_ready_cold_disadvantage_ms"] = fmean(cold_values)
    row["full_overlap_cold_cooccurrence"] = bool(
        row["full_startup_overlap_ms_advantage"] > 0.0
        and row["full_nash_post_ready_cold_disadvantage_ms"] > 0.0
    )
    return row


def _loo_means(values: Sequence[float], seeds: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "omitted_seed": seed,
            "mean": fmean(
                value for index, value in enumerate(values) if index != omitted
            ),
        }
        for omitted, seed in enumerate(seeds)
    ]


def _pair_aggregates(pairs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    metrics = (
        "full_pre_ready_bound_share_advantage",
        "full_pre_ready_lead_ms_advantage",
        "full_startup_overlap_ms_advantage",
        "full_nash_post_ready_cold_disadvantage_ms",
        "common_pre_ready_bound_advantage",
        "common_pre_ready_lead_ms_advantage",
        "common_startup_overlap_ms_advantage",
        "common_nash_post_ready_cold_disadvantage_ms",
    )
    rows = []
    for baseline in (*G3_E0_OPERATIONAL_BASELINES,):
        selected = sorted(
            (row for row in pairs if row["baseline"] == baseline),
            key=lambda row: G3_E0_OPERATIONAL_SEEDS.index(row["seed"]),
        )
        if len(selected) != 5:
            raise ProtocolValidationError(
                f"G5 baseline pair count mismatch: {baseline}"
            )
        summaries = {}
        for metric in metrics:
            values = [float(row[metric]) for row in selected]
            summary = _t_summary(values)
            summary["leave_one_seed_out"] = _loo_means(
                values, [str(row["seed"]) for row in selected]
            )
            summaries[metric] = summary
        rows.append(
            {
                "baseline": baseline,
                "metrics": summaries,
                "full_overlap_cold_cooccurrence_count": sum(
                    bool(row["full_overlap_cold_cooccurrence"]) for row in selected
                ),
            }
        )
    return rows


def _window_int(decision: Mapping[str, Any], field: str) -> int:
    return _required_int(decision.get(field), f"decision.{field}")


def _warm_accounting(
    artifacts: RunArtifacts,
    functions: Mapping[tuple[str, str], Mapping[str, float]],
) -> dict[str, Any]:
    by_frame: defaultdict[int, list[Mapping[str, float]]] = defaultdict(list)
    for function in functions.values():
        by_frame[int(function["scheduled_frame"])].append(function)
    totals: defaultdict[str, int] = defaultdict(int)
    utility_sum = 0.0
    finish_sum = 0.0
    bypass_joined = bypass_cold = 0
    inactive_joined = inactive_cold = 0
    active_windows = 0
    for window in artifacts.nse_events:
        if window.get("kind") != "window":
            continue
        decision = window.get("decision")
        if not isinstance(decision, Mapping):
            raise ProtocolValidationError("C0 window lacks decision object")
        assigned = _window_int(decision, "assigned_players")
        if assigned == 0:
            continue
        active_windows += 1
        running = _window_int(decision, "selected_running_warm_players")
        starting = _window_int(decision, "selected_starting_container_players")
        cold = _window_int(decision, "selected_cold_or_nonrunning_players")
        available = _window_int(decision, "running_warm_available_players")
        bypassed = _window_int(decision, "running_warm_bypassed_players")
        lower = _window_int(decision, "selected_lower_utility_than_warm_players")
        nonwarm = starting + cold
        if (
            assigned != running + nonwarm
            or not (0 <= bypassed <= available <= assigned)
            or bypassed > nonwarm
            or lower != 0
            or decision.get("complete_assignment") is not True
            or _window_int(decision, "commands_prepared") != assigned
            or _window_int(decision, "commands_sent") != assigned
            or _window_int(decision, "invalid_assignments") != 0
            or decision.get("dispatch_channel_failed") is not False
        ):
            raise ProtocolValidationError(
                "C0 warm/dispatch accounting invariant failed"
            )
        frame = _required_int(window.get("frame"), "window.frame")
        joined = by_frame.get(frame, [])
        joined_cold = sum(bool(function["cold_event"]) for function in joined)
        if nonwarm > 0 and bypassed > 0:
            bypass_joined += len(joined)
            bypass_cold += joined_cold
        elif nonwarm > 0:
            inactive_joined += len(joined)
            inactive_cold += joined_cold
        totals["assigned"] += assigned
        totals["running"] += running
        totals["starting"] += starting
        totals["cold"] += cold
        totals["available"] += available
        totals["bypassed"] += bypassed
        totals["nonwarm"] += nonwarm
        totals["absence"] += nonwarm - bypassed
        totals["joined"] += len(joined)
        utility_sum += _required_number(
            decision.get("warm_bypass_utility_advantage_sum"),
            "decision.warm_bypass_utility_advantage_sum",
        )
        finish_sum += _required_number(
            decision.get("warm_bypass_finish_score_delta_sum"),
            "decision.warm_bypass_finish_score_delta_sum",
        )
    if active_windows == 0 or totals["assigned"] == 0:
        raise ProtocolValidationError("C0 run has no active assigned window")
    if totals["joined"] > totals["assigned"]:
        raise ProtocolValidationError(
            "completed-only frame join exceeds dispatched players"
        )
    bypass_rate = bypass_cold / bypass_joined if bypass_joined else None
    inactive_rate = inactive_cold / inactive_joined if inactive_joined else None
    return {
        "run_id": artifacts.run_id,
        "seed": artifacts.seed,
        "active_window_count": active_windows,
        "assigned_players": totals["assigned"],
        "selected_running_warm_players": totals["running"],
        "selected_starting_container_players": totals["starting"],
        "selected_cold_or_nonrunning_players": totals["cold"],
        "running_warm_available_players": totals["available"],
        "running_warm_bypassed_players": totals["bypassed"],
        "selected_nonwarm_players": totals["nonwarm"],
        "capacity_absence_nonwarm_players": totals["absence"],
        "conditional_warm_bypass_share": (
            totals["bypassed"] / totals["available"] if totals["available"] else 0.0
        ),
        "nonwarm_bypass_contribution": (
            totals["bypassed"] / totals["nonwarm"] if totals["nonwarm"] else 0.0
        ),
        "warm_bypass_utility_advantage_mean": (
            utility_sum / totals["bypassed"] if totals["bypassed"] else None
        ),
        "warm_bypass_finish_score_delta_mean": (
            finish_sum / totals["bypassed"] if totals["bypassed"] else None
        ),
        "same_frame_completed_functions": totals["joined"],
        "completed_only_command_coverage": totals["joined"] / totals["assigned"],
        "bypass_active_completed_functions": bypass_joined,
        "bypass_active_cold_events": bypass_cold,
        "bypass_active_cold_event_rate": bypass_rate,
        "bypass_inactive_nonwarm_completed_functions": inactive_joined,
        "bypass_inactive_nonwarm_cold_events": inactive_cold,
        "bypass_inactive_nonwarm_cold_event_rate": inactive_rate,
        "bypass_active_rate_higher": (
            bypass_rate > inactive_rate
            if bypass_rate is not None and inactive_rate is not None
            else None
        ),
    }


def _lookahead_condition(row: Mapping[str, Any]) -> dict[str, bool]:
    metrics = row["metrics"]
    condition_2 = (
        metrics["full_pre_ready_bound_share_advantage"]["positive"] >= 4
        and metrics["full_pre_ready_lead_ms_advantage"]["positive"] >= 4
        and metrics["common_pre_ready_bound_advantage"]["positive"] >= 3
        and metrics["common_pre_ready_lead_ms_advantage"]["positive"] >= 3
    )
    condition_3 = (
        metrics["full_startup_overlap_ms_advantage"]["positive"] >= 4
        and metrics["common_startup_overlap_ms_advantage"]["positive"] >= 3
    )
    condition_4 = row["full_overlap_cold_cooccurrence_count"] >= 3
    return {
        "condition_2_lead": condition_2,
        "condition_3_overlap": condition_3,
        "condition_4_overlap_cold": condition_4,
        "qualifies": condition_2 and condition_3 and condition_4,
    }


def _decision(
    run_rows: Sequence[Mapping[str, Any]],
    aggregates: Sequence[Mapping[str, Any]],
    warm_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    nash_rows = [row for row in run_rows if row["method"] == "sche_nash"]
    condition_1 = all(row["pre_ready_bound_mean"] <= 0.01 for row in nash_rows)
    evidence = {}
    for row in aggregates:
        if row["baseline"] in (*LOOKAHEAD_BASELINES, CONTROL_BASELINE):
            evidence[row["baseline"]] = _lookahead_condition(row)
    qualifying = [
        baseline for baseline in LOOKAHEAD_BASELINES if evidence[baseline]["qualifies"]
    ]
    control_fails = not (
        evidence[CONTROL_BASELINE]["condition_2_lead"]
        and evidence[CONTROL_BASELINE]["condition_3_overlap"]
    )
    lookahead_supported = condition_1 and len(qualifying) >= 3 and control_fails

    nonzero = all(
        row["selected_nonwarm_players"] > 0 and row["running_warm_bypassed_players"] > 0
        for row in warm_rows
    )
    seed_majority = sum(row["nonwarm_bypass_contribution"] >= 0.50 for row in warm_rows)
    total_bypass = sum(row["running_warm_bypassed_players"] for row in warm_rows)
    total_nonwarm = sum(row["selected_nonwarm_players"] for row in warm_rows)
    pooled_share = total_bypass / total_nonwarm if total_nonwarm else 0.0
    utility_positive = all(
        row["warm_bypass_utility_advantage_mean"] is not None
        and row["warm_bypass_utility_advantage_mean"] > 0.0
        for row in warm_rows
    )
    coverage_ok = all(
        row["completed_only_command_coverage"] >= 0.80 for row in warm_rows
    )
    rate_higher = sum(row["bypass_active_rate_higher"] is True for row in warm_rows)
    warm_bypass_dominant = (
        nonzero
        and seed_majority >= 4
        and pooled_share >= 0.50
        and utility_positive
        and coverage_ok
        and rate_higher >= 4
    )
    if lookahead_supported and not warm_bypass_dominant:
        status = "complete_lookahead_candidate_preregistration_authorized"
        authorized = "pre_all_scheduled_strict_eq15"
    elif warm_bypass_dominant and not lookahead_supported:
        status = "complete_warm_bypass_family_preregistration_authorized"
        authorized = "warm_bypass_family"
    else:
        status = "complete_no_single_operational_path"
        authorized = None
    return {
        "status": status,
        "lookahead_supported": lookahead_supported,
        "lookahead_condition_1_c0_no_preready_binding": condition_1,
        "lookahead_qualifying_baselines": qualifying,
        "lookahead_same_admission_control_fails": control_fails,
        "lookahead_evidence": evidence,
        "warm_bypass_dominant": warm_bypass_dominant,
        "warm_nonzero_all_seeds": nonzero,
        "warm_seed_majority_count": seed_majority,
        "warm_pooled_nonwarm_bypass_contribution": pooled_share,
        "warm_utility_advantage_positive_all_seeds": utility_positive,
        "warm_completed_only_coverage_ok_all_seeds": coverage_ok,
        "warm_bypass_active_rate_higher_count": rate_higher,
        "candidate_preregistration_authorized": authorized,
        "source_change_authorized": False,
        "new_sampling_authorized": False,
        "formal_progression_authorized": False,
    }


def analyze(
    g4_path: Path,
    selection_path: Path,
    canonical_root: Path,
    repo_root: Path,
) -> dict[str, Any]:
    g4 = _validate_g4(g4_path)
    source_receipts = _validate_sources(repo_root.resolve())
    selection = _validate_selection(selection_path)
    manifest_info = selection.get("development_manifest")
    if not isinstance(manifest_info, Mapping):
        raise ProtocolValidationError("selection lacks manifest binding")
    manifest_path = Path(str(manifest_info["path"])).resolve()
    if file_hash(manifest_path) != manifest_info["file_sha256"]:
        raise ProtocolValidationError("ready manifest file hash mismatch")
    manifest = load_and_validate_manifest(manifest_path)
    if (
        manifest["manifest_hash"] != EXPECTED_MANIFEST_HASH
        or manifest["manifest_hash"] != manifest_info["manifest_hash"]
    ):
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
        raise ProtocolValidationError("G5 requires exactly 50 homogeneous-low runs")
    g4_run_ids = {str(row["run_id"]) for row in g4["run_stage_metrics"]}
    if {str(run["run_id"]) for run in selected_runs} != g4_run_ids:
        raise ProtocolValidationError("G5/G4 run-set mismatch")
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    g4_receipts = {row["run_id"]: row for row in g4["artifact_receipts"]}
    rows = []
    artifacts_by_run = {}
    receipts = []
    for run in selected_runs:
        artifacts = load_run_artifacts(
            run,
            canonical_root,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        functions = _function_map(artifacts)
        row = {
            "run_id": str(run["run_id"]),
            "seed": str(run["seed"]),
            "method": str(run["method"]),
            "candidate": (
                run.get("metadata", {}).get("m1_operational_candidate")
                if run["method"] == "sche_nash"
                else None
            ),
            "collection_mode": SOURCE_MODES.get(str(run["method"])),
        }
        row.update(_timing_summary(functions))
        row["_functions"] = functions
        rows.append(row)
        artifacts_by_run[str(run["run_id"])] = artifacts
        receipt = {
            "run_id": str(run["run_id"]),
            "manifest_sha256": file_hash(artifacts.run_directory / "manifest.json"),
            "qc_report_sha256": file_hash(artifacts.run_directory / "qc_report.json"),
        }
        if receipt != g4_receipts.get(str(run["run_id"])):
            raise ProtocolValidationError("G5/G4 artifact receipt mismatch")
        receipts.append(receipt)
    nash_rows = [row for row in rows if row["candidate"] == CONTROL]
    if len(nash_rows) != 5:
        raise ProtocolValidationError("G5 requires exactly five C0 runs")
    nash_by_seed = {row["seed"]: row for row in nash_rows}
    pairs = [
        _pair_row(nash_by_seed[row["seed"]], row)
        for row in rows
        if row["method"] in G3_E0_OPERATIONAL_BASELINES
    ]
    if len(pairs) != 45:
        raise ProtocolValidationError("G5 requires exactly 45 baseline pairs")
    aggregates = _pair_aggregates(pairs)
    warm_rows = [
        _warm_accounting(artifacts_by_run[row["run_id"]], row["_functions"])
        for row in nash_rows
    ]
    decision = _decision(rows, aggregates, warm_rows)
    public_rows = [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in rows
    ]
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": decision["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "definitions": {
            "independent_unit": "run/seed",
            "all_valid_runs_retained": True,
            "completed_functions_only": True,
            "startup_overlap_is_saved_latency": False,
            "same_frame_join_is_per_invocation_causality": False,
        },
        "g4_parent": {
            "path": str(g4_path.resolve()),
            "file_sha256": EXPECTED_G4_FILE_SHA256,
            "document_sha256": EXPECTED_G4_DOCUMENT_SHA256,
        },
        "selection_artifact": {
            "path": str(selection_path.resolve()),
            "file_sha256": file_hash(selection_path),
            "document_sha256": selection["document_sha256"],
        },
        "development_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "source_receipts": source_receipts,
        "function_timing_runs": public_rows,
        "function_timing_pairs": pairs,
        "function_timing_aggregates": aggregates,
        "nash_warm_accounting": warm_rows,
        "decision": decision,
        "artifact_receipts": receipts,
        "run_count": len(rows),
        "pair_count": len(pairs),
        "source_change_authorized": False,
        "new_sampling_authorized": False,
        "formal_progression_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_outputs(report: Mapping[str, Any], output_dir: Path) -> list[Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        output_dir / "g5_lookahead_warm_path.json",
        output_dir / "g5_function_timing_runs.csv",
        output_dir / "g5_function_timing_pairs.csv",
        output_dir / "g5_function_timing_aggregates.csv",
        output_dir / "g5_nash_warm_accounting.csv",
    ]
    if any(path.exists() for path in paths):
        raise FileExistsError("G5 output already exists")
    write_json_atomic(paths[0], dict(report))
    try:
        _write_csv_atomic(paths[1], report["function_timing_runs"])
        _write_csv_atomic(paths[2], report["function_timing_pairs"])
        _write_csv_atomic(paths[3], report["function_timing_aggregates"])
        _write_csv_atomic(paths[4], report["nash_warm_accounting"])
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
    parser.add_argument("--g4-report", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(
        args.g4_report,
        args.selection,
        args.canonical_root,
        args.repo_root,
    )
    paths = write_outputs(report, args.output_dir)
    print(
        json.dumps(
            {
                "status": report["status"],
                "document_sha256": report["document_sha256"],
                "outputs": [str(path) for path in paths],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
