"""Read-only, run-level G10 state-regime diagnosis for a possible G11 successor."""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping, Sequence

from ..protocol.g10_work_conserving import (
    G10_CANDIDATES,
    G10_CONTROL,
    G10_EFFECTIVE_METHODS,
)
from ..protocol.m1_qualification import _canonical_summary_path
from ..protocol.schema import (
    FORMAL_E1_LOADS,
    G10_WORK_CONSERVING_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
)
from ..protocol.util import (
    directory_tree_inventory,
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from .formal_inputs import validate_canonical_run
from .g10_work_conserving import _metric_row
from .g4_hom_low_latency import _write_csv_atomic
from .observability import load_run_artifacts, stage_wait_run_metrics


REPORT_SCHEMA = "NSE_G11_STATE_REGIME_DIAGNOSIS_V1"
EXPECTED_G10_ROOT_FILES = 1527
EXPECTED_G10_ROOT_BYTES = 566_678_494
EXPECTED_G10_ROOT_HASH = (
    "aed84ef942171c77d6ed340b9f2cfabb062a0b57b09b8cf02111443499704ff9"
)
EXPECTED_G10_GATE_HASH = (
    "e0581b60b64382d886e219ab4b73d8f36c33f1dce5723c1f27da8607ae3a0870"
)
SATURATION_THRESHOLDS = (1, 2, 4, 8)
RUN_LEVEL_STATE_FIELDS = (
    "queue_area_per_fixed_arrival",
    "cpu_utilization_mean",
    "memory_utilization_mean",
    "cold_start_wait_mean_ms",
    "schedule_wait_mean_ms",
    "completion_ratio",
    "latency_mean_ms",
    "cost_per_completed_request",
    "placement_policy_wall_mean_ns",
)
REPRODUCED_G10_FIELDS = (
    "fixed_arrival_count",
    "fixed_completion_count",
    "completion_ratio",
    "throughput_requests_per_ms",
    "latency_mean_ms",
    "cost_per_completed_request",
    "qpr",
    "queue_area_request_frames",
    "cpu_utilization_mean",
    "memory_utilization_mean",
    "cold_start_wait_mean_ms",
    "schedule_wait_mean_ms",
    "placement_policy_wall_mean_ns",
)
OUTCOME_FIELDS = (
    "log_throughput_ratio",
    "log_qpr_ratio",
    "negative_log_latency_ratio",
    "negative_log_cost_ratio",
    "completion_ratio_difference",
)


def _finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"expected a finite number, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise ProtocolValidationError(f"expected a finite number, got {value!r}")
    return result


def _count(value: Any) -> int:
    result = _finite(value)
    if result < 0.0 or result != int(result):
        raise ProtocolValidationError(f"expected a nonnegative integer, got {value!r}")
    return int(result)


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ProtocolValidationError("percentile input is empty")
    if not 0.0 <= probability <= 1.0:
        raise ProtocolValidationError("percentile probability is outside [0,1]")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _distribution(prefix: str, values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ProtocolValidationError(f"{prefix} distribution is empty")
    return {
        f"{prefix}_mean": fmean(values),
        f"{prefix}_median": _percentile(values, 0.50),
        f"{prefix}_p90": _percentile(values, 0.90),
        f"{prefix}_p95": _percentile(values, 0.95),
        f"{prefix}_max": max(values),
        **{
            f"{prefix}_ge_{threshold}x_fraction": sum(
                value >= threshold for value in values
            )
            / len(values)
            for threshold in SATURATION_THRESHOLDS
        },
    }


def _ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        for position in range(index, end):
            result[ordered[position][0]] = average_rank
        index = end
    return result


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = fmean(left)
    right_mean = fmean(right)
    numerator = sum(
        (lhs - left_mean) * (rhs - right_mean) for lhs, rhs in zip(left, right)
    )
    left_ss = sum((value - left_mean) ** 2 for value in left)
    right_ss = sum((value - right_mean) ** 2 for value in right)
    if left_ss <= 0.0 or right_ss <= 0.0:
        return None
    return numerator / math.sqrt(left_ss * right_ss)


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    return _pearson(_ranks(left), _ranks(right))


def _confusion(rows: Sequence[Mapping[str, Any]], threshold: int) -> dict[str, Any]:
    feature = f"active_ready_ge_{threshold}x_fraction"
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    predictions = []
    for row in rows:
        predicted = _finite(row[feature]) >= 0.50
        observed = bool(row["joint_favorable"])
        key = (
            "tp"
            if predicted and observed
            else "fp"
            if predicted
            else "fn"
            if observed
            else "tn"
        )
        counts[key] += 1
        predictions.append(
            {
                "load": row["load"],
                "seed": row["seed"],
                "predicted_frontier_favorable": predicted,
                "joint_favorable": observed,
            }
        )
    positive = counts["tp"] + counts["fn"]
    negative = counts["tn"] + counts["fp"]
    sensitivity = counts["tp"] / positive if positive else None
    specificity = counts["tn"] / negative if negative else None
    balanced = (
        (sensitivity + specificity) / 2.0
        if sensitivity is not None and specificity is not None
        else None
    )
    return {
        "threshold_ready_per_node": threshold,
        "prediction_rule": f"{feature}>=0.50",
        **counts,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "balanced_accuracy": balanced,
        "passed_full_threshold": balanced is not None
        and balanced >= 0.70
        and sensitivity is not None
        and sensitivity >= 0.60
        and specificity is not None
        and specificity >= 0.60,
        "predictions": predictions,
    }


def _threshold_diagnostics(
    rows: Sequence[Mapping[str, Any]], threshold: int
) -> dict[str, Any]:
    full = _confusion(rows, threshold)
    leave_one_seed_out = []
    for seed in G10_WORK_CONSERVING_SEEDS:
        retained = [row for row in rows if row["seed"] != seed]
        result = _confusion(retained, threshold)
        result["omitted_seed"] = seed
        leave_one_seed_out.append(result)
    full["leave_one_seed_out"] = leave_one_seed_out
    full["all_leave_one_seed_out_pass"] = all(
        row["passed_full_threshold"] for row in leave_one_seed_out
    )
    return full


def _effective_method(run: Mapping[str, Any]) -> str:
    metadata = run.get("metadata")
    if run.get("method") != "sche_nash" or not isinstance(metadata, Mapping):
        raise ProtocolValidationError("G10 diagnosis requires sche_nash metadata")
    method = str(metadata.get("m1_operational_candidate", ""))
    if method not in G10_EFFECTIVE_METHODS:
        raise ProtocolValidationError(f"unexpected G10 method: {method}")
    return method


def _run_state_features(
    run: Mapping[str, Any], artifacts: Any, node_count: int
) -> dict[str, Any]:
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError(f"{run['run_id']} has no policy windows")
    ready: list[float] = []
    pending: list[float] = []
    waiting: list[float] = []
    active_ready: list[float] = []
    frontier_candidates: list[float] = []
    outstanding_frontier: list[float] = []
    frontier_budget: list[float] = []
    frontier_admitted: list[float] = []
    active = 0
    violations = defaultdict(int)
    for index, window in enumerate(windows):
        decision = window.get("decision")
        telemetry = window.get("work_conserving_remaining_work")
        if not isinstance(decision, Mapping) or not isinstance(telemetry, Mapping):
            raise ProtocolValidationError(
                f"{run['run_id']} window {index} lacks decision/G10 telemetry"
            )
        ready_count = _count(telemetry.get("ready_candidates"))
        assigned = _count(decision.get("assigned_players"))
        ready_ratio = ready_count / node_count
        ready.append(ready_ratio)
        pending.append(
            _count(decision.get("pending_request_function_pairs")) / node_count
        )
        waiting.append(_count(decision.get("waiting_for_candidate_nodes")) / node_count)
        if assigned > 0:
            active += 1
            active_ready.append(ready_ratio)
        for field in (
            "ready_omissions",
            "frontier_bound_violations",
            "frontier_one_hop_violations",
            "dispatch_class_violations",
        ):
            violations[field] += _count(telemetry.get(field))
        if _effective_method(run) == G10_CANDIDATES[1]:
            frontier_candidates.append(
                _count(telemetry.get("frontier_candidates")) / node_count
            )
            outstanding_frontier.append(
                _count(telemetry.get("outstanding_frontier")) / node_count
            )
            frontier_budget.append(
                _count(telemetry.get("frontier_budget")) / node_count
            )
            frontier_admitted.append(
                _count(telemetry.get("frontier_admitted")) / node_count
            )
    if not active_ready:
        raise ProtocolValidationError(f"{run['run_id']} has no active policy windows")
    result: dict[str, Any] = {
        "run_id": run["run_id"],
        "load": run["workload"]["request_freq"],
        "seed": run["seed"],
        "effective_method": _effective_method(run),
        "node_count": node_count,
        "policy_window_count": len(windows),
        "active_window_count": active,
        "zero_ready_window_fraction": sum(value == 0.0 for value in ready) / len(ready),
        "nonzero_ready_window_fraction": sum(value > 0.0 for value in ready)
        / len(ready),
        **_distribution("ready_per_node", ready),
        **_distribution("pending_per_node", pending),
        **_distribution("waiting_per_node", waiting),
        **{
            f"active_ready_ge_{threshold}x_fraction": sum(
                value >= threshold for value in active_ready
            )
            / len(active_ready)
            for threshold in SATURATION_THRESHOLDS
        },
        **violations,
    }
    if frontier_admitted:
        result.update(
            {
                **_distribution("frontier_candidates_per_node", frontier_candidates),
                **_distribution("outstanding_frontier_per_node", outstanding_frontier),
                **_distribution("frontier_budget_per_node", frontier_budget),
                **_distribution("frontier_admitted_per_node", frontier_admitted),
                "frontier_positive_admission_window_fraction": sum(
                    value > 0.0 for value in frontier_admitted
                )
                / len(frontier_admitted),
                "frontier_admissions_per_active_window": sum(frontier_admitted)
                * node_count
                / active,
            }
        )
    return result


def _paired_outcomes(
    run_features: Sequence[Mapping[str, Any]], candidate: str
) -> list[dict[str, Any]]:
    index = {
        (row["load"], row["seed"], row["effective_method"]): row for row in run_features
    }
    rows = []
    for load in FORMAL_E1_LOADS:
        for seed in G10_WORK_CONSERVING_SEEDS:
            current = index[(load, seed, candidate)]
            control = index[(load, seed, G10_CONTROL)]
            throughput_ratio = _finite(current["throughput_requests_per_ms"]) / _finite(
                control["throughput_requests_per_ms"]
            )
            qpr_ratio = _finite(current["qpr"]) / _finite(control["qpr"])
            latency_ratio = _finite(current["latency_mean_ms"]) / _finite(
                control["latency_mean_ms"]
            )
            cost_ratio = _finite(current["cost_per_completed_request"]) / _finite(
                control["cost_per_completed_request"]
            )
            completion_difference = _finite(current["completion_ratio"]) - _finite(
                control["completion_ratio"]
            )
            rows.append(
                {
                    "candidate": candidate,
                    "load": load,
                    "seed": seed,
                    "candidate_run_id": current["run_id"],
                    "control_run_id": control["run_id"],
                    "throughput_ratio": throughput_ratio,
                    "qpr_ratio": qpr_ratio,
                    "latency_ratio": latency_ratio,
                    "cost_ratio": cost_ratio,
                    "completion_ratio_difference": completion_difference,
                    "log_throughput_ratio": math.log(throughput_ratio),
                    "log_qpr_ratio": math.log(qpr_ratio),
                    "negative_log_latency_ratio": -math.log(latency_ratio),
                    "negative_log_cost_ratio": -math.log(cost_ratio),
                    "joint_favorable": throughput_ratio > 1.0
                    and qpr_ratio > 1.0
                    and completion_difference >= 0.0
                    and latency_ratio < 1.0,
                    **{
                        key: value
                        for key, value in current.items()
                        if key in RUN_LEVEL_STATE_FIELDS
                        or key.startswith(
                            (
                                "ready_per_node_",
                                "pending_per_node_",
                                "waiting_per_node_",
                                "active_ready_ge_",
                                "frontier_",
                                "outstanding_frontier_",
                                "zero_ready_",
                                "nonzero_ready_",
                            )
                        )
                    },
                }
            )
    return rows


def _state_feature_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    excluded = {
        "candidate",
        "load",
        "seed",
        "candidate_run_id",
        "control_run_id",
        "throughput_ratio",
        "qpr_ratio",
        "latency_ratio",
        "cost_ratio",
        "completion_ratio_difference",
        "log_throughput_ratio",
        "log_qpr_ratio",
        "negative_log_latency_ratio",
        "negative_log_cost_ratio",
        "joint_favorable",
    }
    common = set(rows[0]) - excluded
    for row in rows[1:]:
        common &= set(row)
    return sorted(
        key
        for key in common
        if all(
            isinstance(row.get(key), (int, float))
            and not isinstance(row.get(key), bool)
            and math.isfinite(float(row[key]))
            for row in rows
        )
    )


def _correlations(
    rows: Sequence[Mapping[str, Any]], features: Sequence[str]
) -> list[dict[str, Any]]:
    output = []
    for feature in features:
        left = [_finite(row[feature]) for row in rows]
        for outcome in OUTCOME_FIELDS:
            right = [_finite(row[outcome]) for row in rows]
            output.append(
                {
                    "feature": feature,
                    "outcome": outcome,
                    "n": len(rows),
                    "spearman_rho": _spearman(left, right),
                }
            )
    return output


def _load_feature_summaries(
    rows: Sequence[Mapping[str, Any]], features: Sequence[str]
) -> list[dict[str, Any]]:
    output = []
    for load in FORMAL_E1_LOADS:
        group = [row for row in rows if row["load"] == load]
        for feature in features:
            output.append(
                {
                    "load": load,
                    "feature": feature,
                    "n": len(group),
                    "mean": fmean(_finite(row[feature]) for row in group),
                    "minimum": min(_finite(row[feature]) for row in group),
                    "maximum": max(_finite(row[feature]) for row in group),
                }
            )
    return output


def _coherence(rows: Sequence[Mapping[str, Any]], threshold: int) -> dict[str, Any]:
    feature = f"active_ready_ge_{threshold}x_fraction"

    def correlations(group: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
        values = [_finite(row[feature]) for row in group]
        return {
            outcome: _spearman(values, [_finite(row[outcome]) for row in group])
            for outcome in ("log_throughput_ratio", "log_qpr_ratio")
        }

    full = correlations(rows)
    leave_one_seed_out = []
    for seed in G10_WORK_CONSERVING_SEEDS:
        result = correlations([row for row in rows if row["seed"] != seed])
        leave_one_seed_out.append({"omitted_seed": seed, **result})
    passed = all(value is not None and value > 0.0 for value in full.values()) and all(
        value is not None and value > 0.0
        for row in leave_one_seed_out
        for key, value in row.items()
        if key != "omitted_seed"
    )
    return {
        "feature": feature,
        "full": full,
        "leave_one_seed_out": leave_one_seed_out,
        "positive_for_both_outcomes_full_and_every_leave_one_seed_out": passed,
    }


def build_report(g10_root: Path) -> dict[str, Any]:
    g10_root = g10_root.resolve()
    gate_path = g10_root / "g10.gate.report.json"
    if file_hash(gate_path) != EXPECTED_G10_GATE_HASH:
        raise ProtocolValidationError("G10 gate report differs from preregistration")
    root_inventory = directory_tree_inventory(g10_root)
    if (
        len(root_inventory) != EXPECTED_G10_ROOT_FILES
        or sum(row["bytes"] for row in root_inventory) != EXPECTED_G10_ROOT_BYTES
        or object_hash(root_inventory) != EXPECTED_G10_ROOT_HASH
    ):
        raise ProtocolValidationError("G10 run-root inventory differs from closure")
    manifest_path = g10_root / "g10.references.json"
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("g10_work_conserving_development")
    if not isinstance(marker, Mapping) or int(marker.get("node_count", 0)) != 20:
        raise ProtocolValidationError("G10 marker/node count is invalid")
    gate = read_json(gate_path)
    if (
        not isinstance(gate, Mapping)
        or gate.get("status") != "complete_g10_development_gate_failed"
        or gate.get("selected_candidate") is not None
        or len(gate.get("run_metrics", ())) != 45
    ):
        raise ProtocolValidationError("G10 gate report is not the closed failure")
    gate_rows = {str(row["run_id"]): row for row in gate["run_metrics"]}
    canonical = g10_root / "online" / "canonical"
    run_features = []
    for run in manifest["runs"]:
        validate_canonical_run(
            run,
            canonical / str(run["run_id"]),
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=manifest["execution"].get(
                "result_relative_path", "result.json"
            ),
        )
        artifacts = load_run_artifacts(
            run,
            canonical,
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=manifest["execution"].get(
                "result_relative_path", "result.json"
            ),
        )
        summary = read_json(_canonical_summary_path(canonical, str(run["run_id"])))
        if not isinstance(summary, Mapping):
            raise ProtocolValidationError("canonical summary is invalid")
        state = _run_state_features(run, artifacts, 20)
        recomputed = _metric_row(run, summary, stage_wait_run_metrics(artifacts))
        frozen = gate_rows[str(run["run_id"])]
        for key in REPRODUCED_G10_FIELDS:
            canonical_value = _finite(recomputed.get(key))
            frozen_value = _finite(frozen.get(key))
            if not math.isclose(
                canonical_value, frozen_value, rel_tol=1e-15, abs_tol=1e-12
            ):
                raise ProtocolValidationError(
                    f"canonical recomputation differs from frozen G10 field {key}"
                )
            state[key] = canonical_value
        arrivals = _count(state["fixed_arrival_count"])
        if arrivals == 0:
            raise ProtocolValidationError("queue-area normalization has zero arrivals")
        state["queue_area_per_fixed_arrival"] = (
            _finite(state["queue_area_request_frames"]) / arrivals
        )
        if not math.isclose(
            _finite(state["qpr"]),
            _finite(state["throughput_requests_per_ms"])
            / (
                _finite(state["latency_mean_ms"])
                * _finite(state["cost_per_completed_request"])
            ),
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ProtocolValidationError("canonical QPR factorization differs")
        run_features.append(state)
    expected_product = {
        (load, seed, method)
        for load in FORMAL_E1_LOADS
        for seed in G10_WORK_CONSERVING_SEEDS
        for method in G10_EFFECTIVE_METHODS
    }
    observed_product = {
        (row["load"], row["seed"], row["effective_method"]) for row in run_features
    }
    if len(run_features) != 45 or observed_product != expected_product:
        raise ProtocolValidationError("run feature product is incomplete")
    paired = [
        *_paired_outcomes(run_features, G10_CANDIDATES[0]),
        *_paired_outcomes(run_features, G10_CANDIDATES[1]),
    ]
    c2 = [row for row in paired if row["candidate"] == G10_CANDIDATES[1]]
    c2_features = _state_feature_names(c2)
    correlations = _correlations(c2, c2_features)
    thresholds = [_threshold_diagnostics(c2, value) for value in SATURATION_THRESHOLDS]
    selected_threshold = max(
        thresholds,
        key=lambda row: (
            row["balanced_accuracy"]
            if row["balanced_accuracy"] is not None
            else -math.inf,
            -int(row["threshold_ready_per_node"]),
        ),
    )
    chosen = int(selected_threshold["threshold_ready_per_node"])
    coherence = _coherence(c2, chosen)
    integrity_pass = all(
        _count(row[field]) == 0
        for row in run_features
        if row["effective_method"] == G10_CANDIDATES[1]
        for field in (
            "ready_omissions",
            "frontier_bound_violations",
            "frontier_one_hop_violations",
            "dispatch_class_violations",
        )
    )
    conditions = {
        "01_complete_reproducible_g10_population_and_features": True,
        "02_all_c2_activation_integrity_valid": integrity_pass,
        "03_fixed_threshold_classification_gate": bool(
            selected_threshold["passed_full_threshold"]
            and selected_threshold["all_leave_one_seed_out_pass"]
        ),
        "04_positive_throughput_qpr_saturation_coherence_and_loo": bool(
            coherence["positive_for_both_outcomes_full_and_every_leave_one_seed_out"]
        ),
    }
    admitted = all(conditions.values())
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": (
            "complete_g11_state_regime_successor_preregistration_authorized"
            if admitted
            else "complete_g11_state_regime_path_not_admitted"
        ),
        "input_receipts": {
            "g10_root": str(g10_root),
            "g10_root_files": len(root_inventory),
            "g10_root_bytes": sum(row["bytes"] for row in root_inventory),
            "g10_root_inventory_sha256": object_hash(root_inventory),
            "g10_gate_report": str(gate_path),
            "g10_gate_report_sha256": file_hash(gate_path),
            "g10_manifest_hash": manifest["manifest_hash"],
        },
        "definitions": {
            "independent_unit": "run/seed",
            "window_use": "pre_decision_features_aggregated_within_run",
            "joint_favorable": "throughput_ratio>1 and qpr_ratio>1 and completion_difference>=0 and latency_ratio<1",
            "classifier": "at_least_half_of_active_windows_have_ready_players_per_node_at_or_above_threshold",
            "fixed_thresholds": list(SATURATION_THRESHOLDS),
            "load_label_available_to_future_mechanism": False,
            "diagnosis_is_validation": False,
        },
        "run_state_features": run_features,
        "paired_outcomes": paired,
        "c2_state_features": c2_features,
        "c2_feature_outcome_correlations": correlations,
        "c2_load_feature_summaries": _load_feature_summaries(c2, c2_features),
        "threshold_diagnostics": thresholds,
        "selected_training_threshold_ready_per_node": chosen,
        "selected_threshold_coherence": coherence,
        "admission_conditions": conditions,
        "g11_successor_preregistration_authorized": admitted,
        "g11_implementation_authorized": False,
        "g11_sampling_authorized": False,
        "strong_baseline_addendum_authorized": False,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
        "paper_claim_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def _flatten_thresholds(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in row.items()
            if key not in {"predictions", "leave_one_seed_out"}
        }
        for row in rows
    ]


def write_report(g10_root: Path, output_directory: Path) -> dict[str, Any]:
    output_directory = output_directory.resolve()
    if output_directory.exists():
        raise ProtocolValidationError("refusing to overwrite G11 diagnosis output")
    report = build_report(g10_root)
    output_directory.mkdir(parents=True)
    paths = {
        "report": output_directory / "g11.diagnosis.json",
        "features": output_directory / "g11.run_state_features.csv",
        "pairs": output_directory / "g11.paired_outcomes.csv",
        "correlations": output_directory / "g11.correlations.csv",
        "thresholds": output_directory / "g11.thresholds.csv",
    }
    write_json_atomic(paths["report"], report)
    _write_csv_atomic(paths["features"], report["run_state_features"])
    _write_csv_atomic(paths["pairs"], report["paired_outcomes"])
    _write_csv_atomic(paths["correlations"], report["c2_feature_outcome_correlations"])
    _write_csv_atomic(
        paths["thresholds"], _flatten_thresholds(report["threshold_diagnostics"])
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("g10_root", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args(argv)
    write_report(args.g10_root, args.output_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
