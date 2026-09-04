"""Read-only G15 diagnosis of first-overflow magnitude in closed G14 evidence."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..protocol.g14_deferral_release_valve import G14_CANDIDATE
from ..protocol.ledger import verify_ledger
from ..protocol.schema import FORMAL_E1_LOADS, G14_DEFERRAL_RELEASE_VALVE_SEEDS
from ..protocol.util import (
    directory_tree_inventory,
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from . import g14_deferral_release_valve as g14
from .formal_inputs import validate_canonical_run
from .observability import load_run_artifacts


REPORT_SCHEMA = "NSE_G15_OVERFLOW_MAGNITUDE_DIAGNOSIS_V1"
EXPECTED_ROOT_FILES = 1092
EXPECTED_ROOT_BYTES = 396182667
EXPECTED_ROOT_HASH = "fdb9706343dd4871e49c75be0cd7a2f81f15e095b9ea7aacf65d4ba04de59b63"
EXPECTED_MANIFEST_FILE = (
    "92eab2178b7a7a69023e8afa19768dcf9b717caed6a18660b64f94fb294dac26"
)
EXPECTED_MANIFEST_DOCUMENT = (
    "6ac843330b50df77d6034de66175be17235ff10a56017cc4e2c9b592116b25f1"
)
EXPECTED_SELECTION_FILE = (
    "887fc413d2de23cd223fcc67775d80cd18509f3b64ffa6a500096c30b7b968b4"
)
EXPECTED_SELECTION_DOCUMENT = (
    "3e750866cde6b11a5ebae84bccdb09846e7e9d9a4eef1787dab64d29e3779169"
)
EXPECTED_GATE_FILE = "aa318b727ab7fb89a5bcee271e0b36200a9235aceaadb8969b739a769c038ebc"
EXPECTED_GATE_DOCUMENT = (
    "737fec07a20b42d1d2a20ee5044643bd717ccaf838d922f0a9779d4a61ab2ea0"
)
EXPECTED_LEDGER_FILE = (
    "57098080c5b2df294720c9ac1082d3b62fa182af3816dcc88b5ad73668e82d44"
)
EXPECTED_LEDGER_EVENTS = 62
EXPECTED_LEDGER_TIP = "0fd4fe2ddbb84bcb7dd9e548ec3b104be09137e2609158b2730af24b36facf5b"
EXPECTED_G14_ANALYZER_FILE = (
    "13997e4f476226acc5b4a5fbf90ca9b0cb8978ffb9fe5a21fa66fd96040aefe3"
)
THRESHOLDS = (1.25, 1.5, 2.0, 4.0)
THRESHOLD_KEYS = tuple(f"{value:g}" for value in THRESHOLDS)
VIOLATION_FIELDS = g14.ALL_TELEMETRY_VIOLATION_FIELDS
TELEMETRY_COMPARE_FIELDS = (
    "longest_positive_deferral_episode_windows",
    "dependency_ready_candidates_total",
    "feasible_ready_candidates_total",
    "admitted_players_total",
    "deferred_feasible_players_total",
    "deferred_positive_window_count",
    "first_overflow_bounded_window_count",
    "persistent_overflow_release_window_count",
    "below_limit_window_count",
    "post_overflow_reset_window_count",
    *VIOLATION_FIELDS,
)
ASSOCIATION_FEATURES = (
    "first_overflow_window_count",
    "persistent_overflow_window_count",
    "overflow_episode_count",
    "persistent_episode_count",
    "episode_length_mean",
    "episode_length_max",
    "first_overflow_ratio_mean",
    "first_overflow_ratio_median",
    "first_overflow_ratio_p90",
    "first_overflow_ratio_p95",
    "first_overflow_ratio_max",
    "deferred_total",
    "queue_total_mean",
    "queue_total_max",
    "first_overflow_queue_total_mean",
    "first_overflow_queue_total_max",
)
ASSOCIATION_OUTCOMES = (
    "log_throughput_ratio",
    "log_qpr_ratio",
    "negative_log_latency_ratio",
    "negative_log_cost_ratio",
    "completion_ratio_difference",
    "persistent_episode_fraction",
)


class DiagnosisError(RuntimeError):
    """Raised when frozen G15 evidence or a diagnostic invariant differs."""


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _finite_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    """Return a deterministic type-7 linear-interpolation quantile."""

    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        average = (cursor + 1 + end) / 2.0
        for position in range(cursor, end):
            ranks[order[position]] = average
        cursor = end
    return ranks


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_rank = _ranks(left)
    right_rank = _ranks(right)
    left_mean = sum(left_rank) / len(left_rank)
    right_mean = sum(right_rank) / len(right_rank)
    numerator = sum(
        (lhs - left_mean) * (rhs - right_mean)
        for lhs, rhs in zip(left_rank, right_rank)
    )
    left_ss = sum((value - left_mean) ** 2 for value in left_rank)
    right_ss = sum((value - right_mean) ** 2 for value in right_rank)
    denominator = math.sqrt(left_ss * right_ss)
    return numerator / denominator if denominator > 0.0 else None


def _queue_summary(values: Sequence[int], selected: Sequence[bool]) -> dict[str, Any]:
    chosen = [value for value, keep in zip(values, selected) if keep]
    return {
        "mean": _mean([float(value) for value in values]),
        "max": max(values) if values else None,
        "selected_mean": _mean([float(value) for value in chosen]),
        "selected_max": max(chosen) if chosen else None,
    }


def _validated_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = directory_tree_inventory(root)
    if (
        len(inventory) != EXPECTED_ROOT_FILES
        or sum(row["bytes"] for row in inventory) != EXPECTED_ROOT_BYTES
        or object_hash(inventory) != EXPECTED_ROOT_HASH
    ):
        raise DiagnosisError("G14 run-root inventory differs from closure")
    if file_hash(Path(g14.__file__).resolve()) != EXPECTED_G14_ANALYZER_FILE:
        raise DiagnosisError("frozen G14 analyzer source differs")

    manifest_path = root / "g14.references.json"
    selection_path = root / "g14.online.selection.json"
    report_path = root / "g14.gate-report.json"
    ledger_path = root / "online" / "ledger.jsonl"
    expected = {
        manifest_path: EXPECTED_MANIFEST_FILE,
        selection_path: EXPECTED_SELECTION_FILE,
        report_path: EXPECTED_GATE_FILE,
        ledger_path: EXPECTED_LEDGER_FILE,
    }
    for path, digest in expected.items():
        if file_hash(path) != digest:
            raise DiagnosisError(f"frozen G14 file hash differs: {path.name}")

    manifest = g14._validate_ready_manifest(manifest_path)
    if manifest.get("manifest_hash") != EXPECTED_MANIFEST_DOCUMENT:
        raise DiagnosisError("G14 manifest document hash differs")
    selection = g14._validate_selection(
        selection_path, manifest_path, root / "online" / "canonical", manifest
    )
    if selection.get("document_sha256") != EXPECTED_SELECTION_DOCUMENT:
        raise DiagnosisError("G14 selection document hash differs")
    report = read_json(report_path)
    if not isinstance(report, dict):
        raise DiagnosisError("G14 gate report is not an object")
    payload = dict(report)
    stored = payload.pop("document_sha256", None)
    gate = report.get("gate_result")
    if (
        stored != EXPECTED_GATE_DOCUMENT
        or object_hash(payload) != stored
        or report.get("status") != "complete_g14_development_gate_failed"
        or not isinstance(gate, Mapping)
        or gate.get("selected_candidate") is not None
        or gate.get("all_valid_runs_retained") is not True
        or len(report.get("run_metrics", ())) != 30
        or len(gate.get("paired_rows", ())) != 15
    ):
        raise DiagnosisError("G14 gate report is not the closed retained product")
    sequence, tip = verify_ledger(ledger_path)
    if sequence != EXPECTED_LEDGER_EVENTS or tip != EXPECTED_LEDGER_TIP:
        raise DiagnosisError("G14 online ledger identity differs")
    return manifest, report


def _feature_row(
    run: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    paired: Mapping[str, Any],
    run_metric: Mapping[str, Any],
    node_count: int,
) -> dict[str, Any]:
    records: list[tuple[int, Mapping[str, Any], int]] = []
    feasible: list[int] = []
    admitted: list[int] = []
    deferred: list[int] = []
    overflow: list[bool] = []
    queue_pending: list[int] = []
    queue_resident: list[int] = []
    queue_total: list[int] = []
    first_ratios: list[float] = []
    first_indices: list[int] = []
    violations = {field: 0 for field in VIOLATION_FIELDS}

    for index, event in enumerate(events):
        telemetry = event.get("global_ready_player_admission")
        decision = event.get("decision")
        cluster = event.get("cluster")
        if (
            not isinstance(telemetry, Mapping)
            or not isinstance(decision, Mapping)
            or not isinstance(cluster, Mapping)
        ):
            raise DiagnosisError(f"candidate window {index} lacks G14 evidence")
        assigned = _finite_int(decision.get("assigned_players"))
        feasible_count = _finite_int(telemetry.get("feasible_ready_candidates"))
        admitted_count = _finite_int(telemetry.get("admitted_players"))
        deferred_count = _finite_int(telemetry.get("deferred_feasible_players"))
        if None in (assigned, feasible_count, admitted_count, deferred_count):
            raise DiagnosisError(f"candidate window {index} has invalid counts")
        pending = _finite_int(cluster.get("queue_pending_total"))
        resident = _finite_int(cluster.get("queue_resident_total"))
        total = _finite_int(cluster.get("queue_total"))
        if None in (pending, resident, total) or total != pending + resident:
            raise DiagnosisError(f"candidate window {index} has invalid queue context")
        for field in VIOLATION_FIELDS:
            value = _finite_int(telemetry.get(field))
            if value is None:
                raise DiagnosisError(f"candidate window {index} has invalid {field}")
            violations[field] += value
        current_overflow = telemetry.get("current_overflow")
        if not isinstance(current_overflow, bool):
            raise DiagnosisError(f"candidate window {index} lacks overflow state")
        mode = telemetry.get("admission_mode")
        if mode == "first_overflow_bounded":
            first_indices.append(index)
            first_ratios.append(float(feasible_count) / node_count)
        records.append((index, telemetry, int(assigned)))
        feasible.append(int(feasible_count))
        admitted.append(int(admitted_count))
        deferred.append(int(deferred_count))
        overflow.append(current_overflow)
        queue_pending.append(int(pending))
        queue_resident.append(int(resident))
        queue_total.append(int(total))

    telemetry_result = g14._release_valve_telemetry(records, node_count)
    if telemetry_result.get("g14_activation_pass") is not True:
        raise DiagnosisError("candidate trace fails frozen G14 state reconstruction")
    for field in TELEMETRY_COMPARE_FIELDS:
        if telemetry_result.get(field) != run_metric.get(field):
            raise DiagnosisError(f"G14 report/raw telemetry mismatch for {field}")

    episodes: list[list[int]] = []
    current: list[int] = []
    for index, active in enumerate(overflow):
        if active:
            current.append(index)
        elif current:
            episodes.append(current)
            current = []
    if current:
        episodes.append(current)
    lengths = [len(episode) for episode in episodes]
    persistent_episode_count = sum(length >= 2 for length in lengths)
    if len(episodes) != len(first_indices):
        raise DiagnosisError("overflow episodes do not match first-overflow modes")
    if sum(max(0, length - 1) for length in lengths) != telemetry_result.get(
        "persistent_overflow_release_window_count"
    ):
        raise DiagnosisError("overflow episodes do not match persistent modes")

    first_selected = [index in set(first_indices) for index in range(len(events))]
    pending_summary = _queue_summary(queue_pending, first_selected)
    resident_summary = _queue_summary(queue_resident, first_selected)
    total_summary = _queue_summary(queue_total, first_selected)
    throughput_ratio = _number(paired.get("throughput_ratio"))
    qpr_ratio = _number(paired.get("qpr_ratio"))
    latency_ratio = _number(paired.get("latency_ratio"))
    cost_ratio = _number(paired.get("cost_ratio"))
    completion_difference = _number(paired.get("completion_ratio_difference"))
    if (
        throughput_ratio is None
        or throughput_ratio <= 0.0
        or qpr_ratio is None
        or qpr_ratio <= 0.0
        or latency_ratio is None
        or latency_ratio <= 0.0
        or cost_ratio is None
        or cost_ratio <= 0.0
        or completion_difference is None
    ):
        raise DiagnosisError("paired G14 outcome is undefined")
    fractions = {
        key: (
            sum(value >= threshold for value in first_ratios) / len(first_ratios)
            if first_ratios
            else 0.0
        )
        for key, threshold in zip(THRESHOLD_KEYS, THRESHOLDS)
    }
    return {
        "run_id": run["run_id"],
        "run_spec_hash": run["run_spec_hash"],
        "load": run["workload"]["request_freq"],
        "seed": run["seed"],
        "workload_tape_sha256": run["workload_tape"]["sha256"],
        "window_count": len(events),
        "first_overflow_window_count": len(first_indices),
        "persistent_overflow_window_count": sum(
            max(0, length - 1) for length in lengths
        ),
        "overflow_episode_count": len(episodes),
        "persistent_episode_count": persistent_episode_count,
        "persistent_episode_fraction": (
            persistent_episode_count / len(episodes) if episodes else 0.0
        ),
        "episode_lengths": lengths,
        "episode_length_mean": _mean([float(length) for length in lengths]),
        "episode_length_max": max(lengths) if lengths else 0,
        "first_overflow_ratios": first_ratios,
        "first_overflow_excess_ratios": [value - 1.0 for value in first_ratios],
        "first_overflow_ratio_mean": _mean(first_ratios),
        "first_overflow_ratio_median": _percentile(first_ratios, 0.50),
        "first_overflow_ratio_p90": _percentile(first_ratios, 0.90),
        "first_overflow_ratio_p95": _percentile(first_ratios, 0.95),
        "first_overflow_ratio_max": max(first_ratios) if first_ratios else None,
        "first_overflow_ratio_fraction_ge": fractions,
        "feasible_ready_total": sum(feasible),
        "admitted_total": sum(admitted),
        "deferred_total": sum(deferred),
        "queue_pending_mean": pending_summary["mean"],
        "queue_pending_max": pending_summary["max"],
        "first_overflow_queue_pending_mean": pending_summary["selected_mean"],
        "first_overflow_queue_pending_max": pending_summary["selected_max"],
        "queue_resident_mean": resident_summary["mean"],
        "queue_resident_max": resident_summary["max"],
        "first_overflow_queue_resident_mean": resident_summary["selected_mean"],
        "first_overflow_queue_resident_max": resident_summary["selected_max"],
        "queue_total_mean": total_summary["mean"],
        "queue_total_max": total_summary["max"],
        "first_overflow_queue_total_mean": total_summary["selected_mean"],
        "first_overflow_queue_total_max": total_summary["selected_max"],
        **violations,
        "g14_activation_pass": run_metric.get("g14_activation_pass"),
        "runtime_identity_pass": run_metric.get("runtime_identity_pass"),
        "nash_runtime_pass": run_metric.get("nash_runtime_pass"),
        "nash_runtime_issues": run_metric.get("nash_runtime_issues"),
        "active_window_count": run_metric.get("active_window_count"),
        "strict_pne_active_windows": run_metric.get("strict_pne_active_windows"),
        "offline_reference_hit_windows": run_metric.get(
            "offline_reference_hit_windows"
        ),
        "throughput_ratio": throughput_ratio,
        "qpr_ratio": qpr_ratio,
        "latency_ratio": latency_ratio,
        "cost_ratio": cost_ratio,
        "completion_ratio_difference": completion_difference,
        "log_throughput_ratio": math.log(throughput_ratio),
        "log_qpr_ratio": math.log(qpr_ratio),
        "negative_log_latency_ratio": -math.log(latency_ratio),
        "negative_log_cost_ratio": -math.log(cost_ratio),
        "joint_win": throughput_ratio > 1.0 and qpr_ratio > 1.0,
    }


def _group_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "loads": sorted({str(row["load"]) for row in rows}),
        "joint_wins": sum(bool(row["joint_win"]) for row in rows),
        "mean_log_throughput_ratio": _mean(
            [float(row["log_throughput_ratio"]) for row in rows]
        ),
        "mean_log_qpr_ratio": _mean([float(row["log_qpr_ratio"]) for row in rows]),
        "run_ids": [row["run_id"] for row in rows],
    }


def _difference(left: Any, right: Any) -> float | None:
    lhs = _number(left)
    rhs = _number(right)
    return lhs - rhs if lhs is not None and rhs is not None else None


def _classifier_core(
    rows: Sequence[Mapping[str, Any]], threshold: float
) -> dict[str, Any]:
    key = f"{threshold:g}"
    predicted = [
        bool(row["first_overflow_window_count"])
        and float(row["first_overflow_ratio_fraction_ge"][key]) >= 0.5
        for row in rows
    ]
    actual = [bool(row["joint_win"]) for row in rows]
    tp = sum(prediction and outcome for prediction, outcome in zip(predicted, actual))
    fp = sum(
        prediction and not outcome for prediction, outcome in zip(predicted, actual)
    )
    tn = sum(
        not prediction and not outcome for prediction, outcome in zip(predicted, actual)
    )
    fn = sum(
        not prediction and outcome for prediction, outcome in zip(predicted, actual)
    )
    sensitivity = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    balanced = (
        (sensitivity + specificity) / 2.0
        if sensitivity is not None and specificity is not None
        else None
    )
    positive = [row for row, flag in zip(rows, predicted) if flag]
    negative = [row for row, flag in zip(rows, predicted) if not flag]
    positive_summary = _group_summary(positive)
    negative_summary = _group_summary(negative)
    return {
        "threshold": threshold,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "sensitivity": sensitivity,
        "specificity": specificity,
        "balanced_accuracy": balanced,
        "predicted_positive": positive_summary,
        "predicted_negative": negative_summary,
        "positive_minus_negative": {
            "mean_log_throughput_ratio_difference": _difference(
                positive_summary["mean_log_throughput_ratio"],
                negative_summary["mean_log_throughput_ratio"],
            ),
            "mean_log_qpr_ratio_difference": _difference(
                positive_summary["mean_log_qpr_ratio"],
                negative_summary["mean_log_qpr_ratio"],
            ),
        },
    }


def _classifier_report(
    rows: Sequence[Mapping[str, Any]], threshold: float
) -> dict[str, Any]:
    report = _classifier_core(rows, threshold)
    report["leave_one_run_out"] = [
        {
            "omitted_run_id": omitted["run_id"],
            **_classifier_core(
                [row for row in rows if row["run_id"] != omitted["run_id"]],
                threshold,
            ),
        }
        for omitted in rows
    ]
    return report


def _select_classifier(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def score(report: Mapping[str, Any]) -> tuple[float, float, float]:
        balanced = _number(report.get("balanced_accuracy"))
        sensitivity = _number(report.get("sensitivity"))
        specificity = _number(report.get("specificity"))
        minimum = (
            min(sensitivity, specificity)
            if sensitivity is not None and specificity is not None
            else -math.inf
        )
        return (
            balanced if balanced is not None else -math.inf,
            minimum,
            -float(report["threshold"]),
        )

    if not reports:
        raise DiagnosisError("no fixed G15 classifiers were evaluated")
    return dict(max(reports, key=score))


def _association_report(
    rows: Sequence[Mapping[str, Any]], feature: str, outcome: str
) -> dict[str, Any]:
    def coefficient(subset: Sequence[Mapping[str, Any]]) -> tuple[int, float | None]:
        pairs = [
            (row.get(feature), row.get(outcome))
            for row in subset
            if _number(row.get(feature)) is not None
            and _number(row.get(outcome)) is not None
        ]
        return len(pairs), _spearman(
            [float(pair[0]) for pair in pairs],
            [float(pair[1]) for pair in pairs],
        )

    n, overall = coefficient(rows)
    return {
        "feature": feature,
        "outcome": outcome,
        "n": n,
        "overall_spearman": overall,
        "by_load": [
            {
                "load": load,
                "n": coefficient([row for row in rows if row["load"] == load])[0],
                "spearman": coefficient([row for row in rows if row["load"] == load])[
                    1
                ],
            }
            for load in FORMAL_E1_LOADS
        ],
        "leave_one_run_out": [
            {
                "omitted_run_id": omitted["run_id"],
                "n": coefficient(
                    [row for row in rows if row["run_id"] != omitted["run_id"]]
                )[0],
                "spearman": coefficient(
                    [row for row in rows if row["run_id"] != omitted["run_id"]]
                )[1],
            }
            for omitted in rows
        ],
    }


def _associations(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        _association_report(rows, feature, outcome)
        for feature in ASSOCIATION_FEATURES
        for outcome in ASSOCIATION_OUTCOMES
        if feature != outcome
    ]


def evaluate_successor(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {
        (load, seed)
        for load in FORMAL_E1_LOADS
        for seed in G14_DEFERRAL_RELEASE_VALVE_SEEDS
    }
    identities = {(str(row.get("load")), str(row.get("seed"))) for row in rows}
    condition_1 = (
        len(rows) == 15
        and len(identities) == 15
        and identities == expected
        and len({str(row.get("run_id", "")) for row in rows}) == 15
        and all(row.get("g14_activation_pass") is True for row in rows)
        and all(row.get("runtime_identity_pass") is True for row in rows)
        and all(
            (_finite_int(row.get(field)) or 0) == 0
            for row in rows
            for field in VIOLATION_FIELDS
        )
    )
    classifiers = [_classifier_report(rows, threshold) for threshold in THRESHOLDS]
    selected = _select_classifier(classifiers)
    positive = selected["predicted_positive"]
    negative = selected["predicted_negative"]
    condition_2 = (
        (_number(selected["balanced_accuracy"]) or -math.inf) >= 0.70
        and (_number(selected["sensitivity"]) or -math.inf) >= 0.60
        and (_number(selected["specificity"]) or -math.inf) >= 0.60
        and positive["n"] >= 3
        and negative["n"] >= 3
        and len(positive["loads"]) >= 2
        and len(negative["loads"]) >= 2
    )
    contrast = selected["positive_minus_negative"]
    condition_3 = all(
        _number(contrast.get(field)) is not None and float(contrast[field]) > 0.0
        for field in (
            "mean_log_throughput_ratio_difference",
            "mean_log_qpr_ratio_difference",
        )
    )
    condition_4 = len(selected["leave_one_run_out"]) == 15 and all(
        (_number(row.get("balanced_accuracy")) or -math.inf) >= 0.65
        and (_number(row.get("sensitivity")) or -math.inf) >= 0.50
        and (_number(row.get("specificity")) or -math.inf) >= 0.50
        and all(
            _number(row["positive_minus_negative"].get(field)) is not None
            and float(row["positive_minus_negative"][field]) > 0.0
            for field in (
                "mean_log_throughput_ratio_difference",
                "mean_log_qpr_ratio_difference",
            )
        )
        for row in selected["leave_one_run_out"]
    )
    associations = _associations(rows)
    gate_associations = [
        next(
            report
            for report in associations
            if report["feature"] == "first_overflow_ratio_p90"
            and report["outcome"] == outcome
        )
        for outcome in ("persistent_episode_fraction", "log_throughput_ratio")
    ]
    condition_5 = all(
        _number(report.get("overall_spearman")) is not None
        and float(report["overall_spearman"]) > 0.0
        and len(report["leave_one_run_out"]) == 15
        and all(
            _number(row.get("spearman")) is not None and float(row["spearman"]) > 0.0
            for row in report["leave_one_run_out"]
        )
        for report in gate_associations
    )
    conditions = {
        "01_exact_15_pair_activation_identity_zero_violation_integrity": condition_1,
        "02_selected_fixed_threshold_meets_classifier_and_group_floors": condition_2,
        "03_predicted_positive_mean_log_primary_effects_are_better": condition_3,
        "04_classifier_and_dual_effect_directions_survive_every_loo": condition_4,
        "05_p90_magnitude_positive_persistence_and_throughput_associations_all_loo": condition_5,
    }
    authorized = all(conditions.values())
    return {
        "status": (
            "complete_magnitude_gated_valve_preregistration_authorized"
            if authorized
            else "complete_no_magnitude_gated_valve_authorized"
        ),
        "magnitude_gated_valve_preregistration_authorized": authorized,
        "implementation_authorized": False,
        "sampling_authorized": False,
        "conditions": conditions,
        "failure_reasons": [name for name, passed in conditions.items() if not passed],
        "threshold_reports": classifiers,
        "selected_threshold_report": selected,
        "gate_associations": gate_associations,
        "all_associations": associations,
    }


def analyze(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest, g14_report = _validated_inputs(root)
    canonical = root / "online" / "canonical"
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    paired_index = {
        (row["load"], row["seed"]): row
        for row in g14_report["gate_result"]["paired_rows"]
    }
    metric_index = {
        row["run_id"]: row
        for row in g14_report["run_metrics"]
        if row["effective_method"] == G14_CANDIDATE
    }
    node_count = int(manifest["g14_deferral_release_valve_development"]["node_count"])
    rows = []
    receipts = []
    for run in manifest["runs"]:
        if run["metadata"]["m1_operational_candidate"] != G14_CANDIDATE:
            continue
        run_dir = canonical / run["run_id"]
        validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        artifacts = load_run_artifacts(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        windows = [
            event for event in artifacts.nse_events if event.get("kind") == "window"
        ]
        key = (run["workload"]["request_freq"], run["seed"])
        paired = paired_index.get(key)
        metric = metric_index.get(run["run_id"])
        if not isinstance(paired, Mapping) or not isinstance(metric, Mapping):
            raise DiagnosisError("G14 report lacks a candidate pair or metric row")
        rows.append(_feature_row(run, windows, paired, metric, node_count))
        receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "tape_sha256": run["workload_tape"]["sha256"],
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
            }
        )
    decision = evaluate_successor(rows)
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": decision["status"],
        "formal_results_eligible": False,
        "paper_claim_eligible": False,
        "source_root": {
            "path": str(root),
            "files": EXPECTED_ROOT_FILES,
            "bytes": EXPECTED_ROOT_BYTES,
            "inventory_sha256": EXPECTED_ROOT_HASH,
        },
        "source_receipts": {
            "manifest_file_sha256": EXPECTED_MANIFEST_FILE,
            "manifest_document_sha256": EXPECTED_MANIFEST_DOCUMENT,
            "selection_file_sha256": EXPECTED_SELECTION_FILE,
            "selection_document_sha256": EXPECTED_SELECTION_DOCUMENT,
            "gate_file_sha256": EXPECTED_GATE_FILE,
            "gate_document_sha256": EXPECTED_GATE_DOCUMENT,
            "ledger_file_sha256": EXPECTED_LEDGER_FILE,
            "ledger_events": EXPECTED_LEDGER_EVENTS,
            "ledger_tip": EXPECTED_LEDGER_TIP,
            "g14_analyzer_sha256": EXPECTED_G14_ANALYZER_FILE,
        },
        "definitions": {
            "independent_unit": "G14 candidate run/seed paired with same-tape C0",
            "first_overflow_ratio": "feasible_ready_candidates/configured_node_count in the first window of an overflow episode",
            "overflow_episode": "maximal consecutive scheduler-window sequence with feasible_ready_candidates>N",
            "quantile": "type-7 linear interpolation on ordered first-overflow ratios",
            "joint_win": "throughput_ratio>1 and qpr_ratio>1",
            "ties_retained_as_nonwins": True,
            "thresholds": list(THRESHOLDS),
            "classifier": "at_least_one_first_overflow_and_fraction_ge_threshold_at_least_0.5",
            "development_fit_not_validation": True,
        },
        "feature_rows": rows,
        "decision": decision,
        "artifact_receipts": receipts,
        "run_count": len(rows),
        "implementation_authorized": False,
        "sampling_authorized": False,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_analysis(root: Path, output: Path) -> dict[str, Any]:
    if output.exists() or output.parent.exists():
        raise DiagnosisError("G15 output workspace must be absent before analysis")
    report = analyze(root)
    output.parent.mkdir(parents=True)
    write_json_atomic(output, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    write_analysis(args.root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
