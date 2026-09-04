"""Read-only G17 threshold-safety diagnosis of the closed G16 evidence."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..protocol.g16_overflow_magnitude_valve import G16_CANDIDATE
from ..protocol.ledger import verify_ledger
from ..protocol.schema import FORMAL_E1_LOADS, G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS
from ..protocol.util import (
    directory_tree_inventory,
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from . import g16_overflow_magnitude_valve as g16
from .formal_inputs import validate_canonical_run
from .observability import load_run_artifacts


REPORT_SCHEMA = "NSE_G17_THRESHOLD_SAFETY_DIAGNOSIS_V1"
EXPECTED_ROOT_FILES = 1092
EXPECTED_ROOT_BYTES = 395532897
EXPECTED_ROOT_HASH = "28a7d5a16592e928e4c63d11901f76629c75d8a5041d69955baec12e36f04c9f"
EXPECTED_MANIFEST_FILE = (
    "bdda8e7b8f790c692760e1eb5eb7369d0e4f078bb3140883e6db514fae63eb65"
)
EXPECTED_MANIFEST_DOCUMENT = (
    "fbea597e13a10d032b5c9483c2b754d061d6d19062389e41ae02ffd7588cb50e"
)
EXPECTED_SELECTION_FILE = (
    "0c9eb944bc015047de3503ad017ce24e0aa729f9d88e9188f0a5bcad1174bdd4"
)
EXPECTED_SELECTION_DOCUMENT = (
    "94fc4f533731c479a2297b21a0b4ac281c4997f7b964a03acd6e45ba71c21458"
)
EXPECTED_GATE_FILE = "7fdf5456cdb68d12dd738658813729065669d9ed5f57c57e658414ca695000e3"
EXPECTED_GATE_DOCUMENT = (
    "c1856ac8748412b303ee8f131533267c1041c346893624fff21a11e5bc3aea37"
)
EXPECTED_LEDGER_FILE = (
    "9e36a4f171ae8d394480c13eb9e09c2fea12a2991a26536cb31c4fb3db264f2a"
)
EXPECTED_LEDGER_EVENTS = 62
EXPECTED_LEDGER_TIP = "5ef27a3a6a4e57a7dc1949ff4c68b12d53d98c3eb540921a3312f891028d57fa"
EXPECTED_G16_ANALYZER_FILE = (
    "0c3721113dbb3dc2abfe6465a66398c1a797504ecdc95eb4f773fd3098c6f8e4"
)
THRESHOLDS = (1.25, 1.5, 2.0, 4.0)
THRESHOLD_KEYS = tuple(f"{value:g}" for value in THRESHOLDS)
THRESHOLD_FRACTIONS = {
    "1.25": (5, 4),
    "1.5": (3, 2),
    "2": (2, 1),
    "4": (4, 1),
}
DOSE_BUDGETS = (1, 4, 16, 64)
VIOLATION_FIELDS = g16.ZERO_VIOLATION_FIELDS
FIRST_OVERFLOW_MODES = (
    "first_overflow_below_magnitude_release",
    "first_overflow_magnitude_bounded",
)
ALL_MODES = (
    *FIRST_OVERFLOW_MODES,
    "persistent_overflow_release",
    "below_limit",
    "post_overflow_reset",
)
TELEMETRY_COMPARE_FIELDS = (
    "longest_positive_deferral_episode_windows",
    "dependency_ready_candidates_total",
    "feasible_ready_candidates_total",
    "admitted_players_total",
    "deferred_feasible_players_total",
    "deferred_positive_window_count",
    "magnitude_gate_applicable_window_count",
    "magnitude_gate_pass_window_count",
    "first_overflow_below_magnitude_release_window_count",
    "first_overflow_magnitude_bounded_window_count",
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
    "reset_interval_mean",
    "first_overflow_ratio_mean",
    "first_overflow_ratio_median",
    "first_overflow_ratio_p75",
    "first_overflow_ratio_p90",
    "first_overflow_ratio_p95",
    "first_overflow_ratio_max",
    "actual_bounded_window_count",
    "actual_deferred_player_total",
    "actual_bounded_density_per_active_window",
    "actual_deferred_mass_per_assigned_player",
    "feasible_ready_mean",
    "first_overflow_feasible_ready_mean",
    "material_bounded_feasible_ready_mean",
    "queue_pending_mean",
    "first_overflow_queue_pending_mean",
    "material_bounded_queue_pending_mean",
    "queue_resident_mean",
    "first_overflow_queue_resident_mean",
    "material_bounded_queue_resident_mean",
    "queue_total_mean",
    "first_overflow_queue_total_mean",
    "material_bounded_queue_total_mean",
)
ASSOCIATION_OUTCOMES = (
    "log_throughput_ratio",
    "log_qpr_ratio",
    "negative_log_latency_ratio",
    "negative_log_cost_ratio",
    "completion_ratio_difference",
)
PRIMARY_METRICS = (
    ("throughput", "throughput_requests_per_ms"),
    ("qpr", "qpr"),
)


class DiagnosisError(RuntimeError):
    """Raised when frozen G16 evidence or a diagnostic invariant differs."""


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


def _ratio(numerator: Any, denominator: Any) -> float | None:
    left = _number(numerator)
    right = _number(denominator)
    if left is None or right is None or right <= 0.0:
        return None
    return left / right


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


def _summary(values: Sequence[int | float], selected: Sequence[bool]) -> dict[str, Any]:
    all_values = [float(value) for value in values]
    chosen = [value for value, keep in zip(all_values, selected) if keep]
    return {
        "mean": _mean(all_values),
        "p95": _percentile(all_values, 0.95),
        "max": max(all_values) if all_values else None,
        "selected_mean": _mean(chosen),
        "selected_p95": _percentile(chosen, 0.95),
        "selected_max": max(chosen) if chosen else None,
    }


def _validated_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = directory_tree_inventory(root)
    if (
        len(inventory) != EXPECTED_ROOT_FILES
        or sum(row["bytes"] for row in inventory) != EXPECTED_ROOT_BYTES
        or object_hash(inventory) != EXPECTED_ROOT_HASH
    ):
        raise DiagnosisError("G16 run-root inventory differs from closure")
    if file_hash(Path(g16.__file__).resolve()) != EXPECTED_G16_ANALYZER_FILE:
        raise DiagnosisError("frozen G16 analyzer source differs")

    manifest_path = root / "g16.references.json"
    selection_path = root / "g16.online.selection.json"
    report_path = root / "g16.gate-report.json"
    ledger_path = root / "online" / "ledger.jsonl"
    expected = {
        manifest_path: EXPECTED_MANIFEST_FILE,
        selection_path: EXPECTED_SELECTION_FILE,
        report_path: EXPECTED_GATE_FILE,
        ledger_path: EXPECTED_LEDGER_FILE,
    }
    for path, digest in expected.items():
        if file_hash(path) != digest:
            raise DiagnosisError(f"frozen G16 file hash differs: {path.name}")

    manifest = g16._validate_ready_manifest(manifest_path)
    if manifest.get("manifest_hash") != EXPECTED_MANIFEST_DOCUMENT:
        raise DiagnosisError("G16 manifest document hash differs")
    selection = g16._validate_selection(
        selection_path, manifest_path, root / "online" / "canonical", manifest
    )
    if selection.get("document_sha256") != EXPECTED_SELECTION_DOCUMENT:
        raise DiagnosisError("G16 selection document hash differs")
    report = read_json(report_path)
    if not isinstance(report, dict):
        raise DiagnosisError("G16 gate report is not an object")
    payload = dict(report)
    stored = payload.pop("document_sha256", None)
    gate = report.get("gate_result")
    if (
        stored != EXPECTED_GATE_DOCUMENT
        or object_hash(payload) != stored
        or report.get("status") != "complete_g16_development_gate_failed"
        or not isinstance(gate, Mapping)
        or gate.get("selected_candidate") is not None
        or gate.get("all_valid_runs_retained") is not True
        or len(report.get("run_metrics", ())) != 30
        or len(gate.get("paired_rows", ())) != 15
    ):
        raise DiagnosisError("G16 gate report is not the closed retained product")
    sequence, tip = verify_ledger(ledger_path)
    if sequence != EXPECTED_LEDGER_EVENTS or tip != EXPECTED_LEDGER_TIP:
        raise DiagnosisError("G16 online ledger identity differs")
    return manifest, report


def _intervals(indices: Sequence[int]) -> list[int]:
    return [right - left for left, right in zip(indices, indices[1:])]


def _put_scope_summaries(
    target: dict[str, Any],
    name: str,
    values: Sequence[int],
    first_selected: Sequence[bool],
    bounded_selected: Sequence[bool],
) -> None:
    first = _summary(values, first_selected)
    bounded = _summary(values, bounded_selected)
    target[f"{name}_mean"] = first["mean"]
    target[f"{name}_p95"] = first["p95"]
    target[f"{name}_max"] = first["max"]
    target[f"first_overflow_{name}_mean"] = first["selected_mean"]
    target[f"first_overflow_{name}_p95"] = first["selected_p95"]
    target[f"first_overflow_{name}_max"] = first["selected_max"]
    target[f"material_bounded_{name}_mean"] = bounded["selected_mean"]
    target[f"material_bounded_{name}_p95"] = bounded["selected_p95"]
    target[f"material_bounded_{name}_max"] = bounded["selected_max"]


def _positive_metric(metric: Mapping[str, Any], field: str) -> float:
    value = _number(metric.get(field))
    if value is None or value <= 0.0:
        raise DiagnosisError(f"G16/C0 raw metric is not positive: {field}")
    return value


def _feature_row(
    run: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    paired: Mapping[str, Any],
    run_metric: Mapping[str, Any],
    control_metric: Mapping[str, Any],
    node_count: int,
) -> dict[str, Any]:
    records: list[tuple[int, Mapping[str, Any], int]] = []
    dependency_ready: list[int] = []
    feasible: list[int] = []
    admitted: list[int] = []
    deferred: list[int] = []
    overflow: list[bool] = []
    queue_pending: list[int] = []
    queue_resident: list[int] = []
    queue_total: list[int] = []
    first_indices: list[int] = []
    first_feasible: list[int] = []
    bounded_indices: list[int] = []
    mode_counts = {mode: 0 for mode in ALL_MODES}
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
            raise DiagnosisError(f"candidate window {index} lacks G16 evidence")
        assigned = _finite_int(decision.get("assigned_players"))
        dependency_count = _finite_int(telemetry.get("dependency_ready_candidates"))
        feasible_count = _finite_int(telemetry.get("feasible_ready_candidates"))
        admitted_count = _finite_int(telemetry.get("admitted_players"))
        deferred_count = _finite_int(telemetry.get("deferred_feasible_players"))
        if None in (
            assigned,
            dependency_count,
            feasible_count,
            admitted_count,
            deferred_count,
        ):
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
        mode = telemetry.get("admission_mode")
        if not isinstance(current_overflow, bool) or mode not in mode_counts:
            raise DiagnosisError(f"candidate window {index} has invalid G16 state")
        mode_counts[str(mode)] += 1
        if mode in FIRST_OVERFLOW_MODES:
            first_indices.append(index)
            first_feasible.append(int(feasible_count))
        if mode == "first_overflow_magnitude_bounded":
            bounded_indices.append(index)
        records.append((index, telemetry, int(assigned)))
        dependency_ready.append(int(dependency_count))
        feasible.append(int(feasible_count))
        admitted.append(int(admitted_count))
        deferred.append(int(deferred_count))
        overflow.append(current_overflow)
        queue_pending.append(int(pending))
        queue_resident.append(int(resident))
        queue_total.append(int(total))

    telemetry_result = g16._overflow_magnitude_telemetry(records, node_count)
    if telemetry_result.get("g16_activation_pass") is not True:
        raise DiagnosisError("candidate trace fails frozen G16 state reconstruction")
    for field in TELEMETRY_COMPARE_FIELDS:
        if telemetry_result.get(field) != run_metric.get(field):
            raise DiagnosisError(f"G16 report/raw telemetry mismatch for {field}")

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
    for episode in episodes:
        first_mode = events[episode[0]]["global_ready_player_admission"][
            "admission_mode"
        ]
        later_modes = [
            events[index]["global_ready_player_admission"]["admission_mode"]
            for index in episode[1:]
        ]
        if first_mode not in FIRST_OVERFLOW_MODES or any(
            mode != "persistent_overflow_release" for mode in later_modes
        ):
            raise DiagnosisError("overflow episode has invalid G16 mode sequence")
    if len(episodes) != len(first_indices):
        raise DiagnosisError("overflow episodes do not match first-overflow modes")
    if sum(max(0, length - 1) for length in lengths) != telemetry_result.get(
        "persistent_overflow_release_window_count"
    ):
        raise DiagnosisError("overflow episodes do not match persistent modes")
    if len(bounded_indices) != telemetry_result.get("magnitude_gate_pass_window_count"):
        raise DiagnosisError("material bounded modes do not match G16 magnitude passes")

    first_set = set(first_indices)
    bounded_set = set(bounded_indices)
    first_selected = [index in first_set for index in range(len(events))]
    bounded_selected = [index in bounded_set for index in range(len(events))]
    first_ratios = [value / node_count for value in first_feasible]
    threshold_counts: dict[str, int] = {}
    threshold_fractions: dict[str, float] = {}
    threshold_mass: dict[str, int] = {}
    for key in THRESHOLD_KEYS:
        numerator, denominator = THRESHOLD_FRACTIONS[key]
        selected = [
            denominator * value >= numerator * node_count for value in first_feasible
        ]
        threshold_counts[key] = sum(selected)
        threshold_fractions[key] = (
            threshold_counts[key] / len(first_feasible) if first_feasible else 0.0
        )
        threshold_mass[key] = sum(
            max(0, value - node_count)
            for value, keep in zip(first_feasible, selected)
            if keep
        )

    candidate_throughput = _positive_metric(run_metric, "throughput_requests_per_ms")
    candidate_qpr = _positive_metric(run_metric, "qpr")
    control_throughput = _positive_metric(control_metric, "throughput_requests_per_ms")
    control_qpr = _positive_metric(control_metric, "qpr")
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
        or not math.isclose(
            throughput_ratio,
            candidate_throughput / control_throughput,
            rel_tol=1e-12,
            abs_tol=1e-15,
        )
        or not math.isclose(
            qpr_ratio,
            candidate_qpr / control_qpr,
            rel_tol=1e-12,
            abs_tol=1e-15,
        )
    ):
        raise DiagnosisError("paired G16 outcome is undefined or inconsistent")

    active_windows = _finite_int(run_metric.get("active_window_count"))
    assigned_total = _finite_int(run_metric.get("assigned_players"))
    if active_windows is None or assigned_total is None:
        raise DiagnosisError("G16 runtime coverage is invalid")
    dose_budgets = {}
    for budget in DOSE_BUDGETS:
        retained = bounded_indices[:budget]
        retained_mass = sum(deferred[index] for index in retained)
        dose_budgets[str(budget)] = {
            "retained_bounded_events": len(retained),
            "retained_deferred_players": retained_mass,
            "bounded_event_coverage": (
                len(retained) / len(bounded_indices) if bounded_indices else 1.0
            ),
            "deferred_player_coverage": (
                retained_mass / sum(deferred[index] for index in bounded_indices)
                if sum(deferred[index] for index in bounded_indices)
                else 1.0
            ),
        }

    row: dict[str, Any] = {
        "run_id": run["run_id"],
        "run_spec_hash": run["run_spec_hash"],
        "load": run["workload"]["request_freq"],
        "seed": run["seed"],
        "workload_tape_sha256": run["workload_tape"]["sha256"],
        "window_count": len(events),
        "mode_counts": mode_counts,
        "first_overflow_window_count": len(first_indices),
        "persistent_overflow_window_count": sum(
            max(0, length - 1) for length in lengths
        ),
        "overflow_episode_count": len(episodes),
        "persistent_episode_count": sum(length >= 2 for length in lengths),
        "episode_lengths": lengths,
        "episode_length_mean": _mean([float(length) for length in lengths]),
        "episode_length_max": max(lengths) if lengths else 0,
        "reset_intervals": _intervals(first_indices),
        "reset_interval_mean": _mean(
            [float(value) for value in _intervals(first_indices)]
        ),
        "material_bounded_intervals": _intervals(bounded_indices),
        "first_overflow_ratios": first_ratios,
        "first_overflow_ratio_mean": _mean(first_ratios),
        "first_overflow_ratio_median": _percentile(first_ratios, 0.50),
        "first_overflow_ratio_p75": _percentile(first_ratios, 0.75),
        "first_overflow_ratio_p90": _percentile(first_ratios, 0.90),
        "first_overflow_ratio_p95": _percentile(first_ratios, 0.95),
        "first_overflow_ratio_max": max(first_ratios) if first_ratios else None,
        "first_overflow_count_ge": threshold_counts,
        "first_overflow_ratio_fraction_ge": threshold_fractions,
        "first_overflow_deferred_player_mass_ge": threshold_mass,
        "actual_bounded_window_count": len(bounded_indices),
        "actual_deferred_player_total": sum(
            deferred[index] for index in bounded_indices
        ),
        "actual_bounded_density_per_active_window": (
            len(bounded_indices) / active_windows if active_windows else 0.0
        ),
        "actual_deferred_mass_per_assigned_player": (
            sum(deferred[index] for index in bounded_indices) / assigned_total
            if assigned_total
            else 0.0
        ),
        "dose_budget_trace_coverage": dose_budgets,
        **violations,
        "g16_activation_pass": run_metric.get("g16_activation_pass"),
        "runtime_identity_pass": run_metric.get("runtime_identity_pass"),
        "nash_runtime_pass": run_metric.get("nash_runtime_pass"),
        "nash_runtime_issues": run_metric.get("nash_runtime_issues"),
        "active_window_count": active_windows,
        "strict_pne_active_windows": run_metric.get("strict_pne_active_windows"),
        "offline_reference_hit_windows": run_metric.get(
            "offline_reference_hit_windows"
        ),
        "candidate_throughput": candidate_throughput,
        "control_throughput": control_throughput,
        "candidate_qpr": candidate_qpr,
        "control_qpr": control_qpr,
        "throughput_ratio": throughput_ratio,
        "qpr_ratio": qpr_ratio,
        "latency_ratio": latency_ratio,
        "cost_ratio": cost_ratio,
        "completion_ratio_difference": completion_difference,
        "log_throughput_ratio": math.log(throughput_ratio),
        "log_qpr_ratio": math.log(qpr_ratio),
        "negative_log_latency_ratio": -math.log(latency_ratio),
        "negative_log_cost_ratio": -math.log(cost_ratio),
        "joint_nonloss": throughput_ratio >= 1.0 and qpr_ratio >= 1.0,
        "joint_win": throughput_ratio > 1.0 and qpr_ratio > 1.0,
    }
    for name, values in (
        ("dependency_ready", dependency_ready),
        ("feasible_ready", feasible),
        ("admitted", admitted),
        ("queue_pending", queue_pending),
        ("queue_resident", queue_resident),
        ("queue_total", queue_total),
    ):
        _put_scope_summaries(row, name, values, first_selected, bounded_selected)
    return row


def _group_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "loads": sorted({str(row["load"]) for row in rows}),
        "joint_nonlosses": sum(bool(row["joint_nonloss"]) for row in rows),
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


def _confusion(predicted: Sequence[bool], actual: Sequence[bool]) -> dict[str, Any]:
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
    return {
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "sensitivity": sensitivity,
        "specificity": specificity,
        "balanced_accuracy": balanced,
    }


def _envelope_core(
    rows: Sequence[Mapping[str, Any]], predicted: Sequence[bool]
) -> dict[str, Any]:
    load_rows = []
    leave_one_seed_out = []
    for load in FORMAL_E1_LOADS:
        group = [
            (row, keep) for row, keep in zip(rows, predicted) if row["load"] == load
        ]
        proxy_rows = []
        for row, keep in group:
            throughput = (
                float(row["candidate_throughput"])
                if keep
                else float(row["control_throughput"])
            )
            qpr = float(row["candidate_qpr"]) if keep else float(row["control_qpr"])
            throughput_ratio = throughput / float(row["control_throughput"])
            qpr_ratio = qpr / float(row["control_qpr"])
            proxy_rows.append(
                {
                    "run_id": row["run_id"],
                    "seed": row["seed"],
                    "predicted_safe": keep,
                    "proxy_throughput": throughput,
                    "control_throughput": row["control_throughput"],
                    "proxy_qpr": qpr,
                    "control_qpr": row["control_qpr"],
                    "throughput_ratio": throughput_ratio,
                    "qpr_ratio": qpr_ratio,
                    "joint_win": throughput_ratio > 1.0 and qpr_ratio > 1.0,
                    "joint_nonloss": throughput_ratio >= 1.0 and qpr_ratio >= 1.0,
                }
            )
        throughput_mean_ratio = _ratio(
            _mean([float(row["proxy_throughput"]) for row in proxy_rows]),
            _mean([float(row["control_throughput"]) for row in proxy_rows]),
        )
        qpr_mean_ratio = _ratio(
            _mean([float(row["proxy_qpr"]) for row in proxy_rows]),
            _mean([float(row["control_qpr"]) for row in proxy_rows]),
        )
        load_rows.append(
            {
                "load": load,
                "n": len(proxy_rows),
                "throughput_mean_ratio": throughput_mean_ratio,
                "qpr_mean_ratio": qpr_mean_ratio,
                "joint_wins": sum(bool(row["joint_win"]) for row in proxy_rows),
                "joint_nonlosses": sum(
                    bool(row["joint_nonloss"]) for row in proxy_rows
                ),
                "minimum_primary_ratio": min(
                    [
                        float(row[metric])
                        for row in proxy_rows
                        for metric in ("throughput_ratio", "qpr_ratio")
                    ],
                    default=None,
                ),
                "proxy_rows": proxy_rows,
            }
        )
        for metric_name, metric_field in PRIMARY_METRICS:
            for omitted, _ in group:
                retained = [
                    (row, keep) for row, keep in group if row["seed"] != omitted["seed"]
                ]
                differences = [
                    (
                        float(row[f"candidate_{metric_name}"])
                        - float(row[f"control_{metric_name}"])
                        if keep
                        else 0.0
                    )
                    for row, keep in retained
                ]
                leave_one_seed_out.append(
                    {
                        "load": load,
                        "metric": metric_field,
                        "omitted_seed": omitted["seed"],
                        "mean_difference": _mean(differences),
                    }
                )
    minimum_mean_ratio = min(
        [
            float(row[field])
            for row in load_rows
            for field in ("throughput_mean_ratio", "qpr_mean_ratio")
            if _number(row[field]) is not None
        ],
        default=None,
    )
    return {
        "by_load": load_rows,
        "minimum_six_load_metric_mean_ratio": minimum_mean_ratio,
        "leave_one_seed_out_mean_differences": leave_one_seed_out,
        "noncausal_optimistic_screening_only": True,
    }


def _classifier_core(
    rows: Sequence[Mapping[str, Any]], threshold: float
) -> dict[str, Any]:
    key = f"{threshold:g}"
    predicted = [
        bool(row["first_overflow_window_count"])
        and float(row["first_overflow_ratio_fraction_ge"][key]) >= 0.5
        for row in rows
    ]
    nonloss = _confusion(predicted, [bool(row["joint_nonloss"]) for row in rows])
    win = _confusion(predicted, [bool(row["joint_win"]) for row in rows])
    positive = [row for row, flag in zip(rows, predicted) if flag]
    negative = [row for row, flag in zip(rows, predicted) if not flag]
    positive_summary = _group_summary(positive)
    negative_summary = _group_summary(negative)
    return {
        "threshold": threshold,
        "predicted_safe_by_run_id": {
            str(row["run_id"]): flag for row, flag in zip(rows, predicted)
        },
        "joint_nonloss_classifier": nonloss,
        "joint_win_classifier": win,
        "balanced_accuracy": nonloss["balanced_accuracy"],
        "sensitivity": nonloss["sensitivity"],
        "specificity": nonloss["specificity"],
        "predicted_safe": positive_summary,
        "predicted_unsafe": negative_summary,
        "safe_minus_unsafe": {
            "mean_log_throughput_ratio_difference": _difference(
                positive_summary["mean_log_throughput_ratio"],
                negative_summary["mean_log_throughput_ratio"],
            ),
            "mean_log_qpr_ratio_difference": _difference(
                positive_summary["mean_log_qpr_ratio"],
                negative_summary["mean_log_qpr_ratio"],
            ),
        },
        "optimistic_screening_envelope": _envelope_core(rows, predicted),
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


def _select_threshold(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def score(report: Mapping[str, Any]) -> tuple[float, float, float, float]:
        envelope = report["optimistic_screening_envelope"]
        minimum_ratio = _number(envelope["minimum_six_load_metric_mean_ratio"])
        balanced = _number(report.get("balanced_accuracy"))
        sensitivity = _number(report.get("sensitivity"))
        specificity = _number(report.get("specificity"))
        minimum_class = (
            min(sensitivity, specificity)
            if sensitivity is not None and specificity is not None
            else -math.inf
        )
        return (
            minimum_ratio if minimum_ratio is not None else -math.inf,
            balanced if balanced is not None else -math.inf,
            minimum_class,
            float(report["threshold"]),
        )

    if not reports:
        raise DiagnosisError("no fixed G17 thresholds were evaluated")
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
    activated = [row for row in rows if int(row["actual_bounded_window_count"]) > 0]
    activated_n, activated_value = coefficient(activated)
    by_load = []
    for load in FORMAL_E1_LOADS:
        load_n, value = coefficient([row for row in rows if row["load"] == load])
        by_load.append({"load": load, "n": load_n, "spearman": value})
    leave_one_out = []
    for omitted in rows:
        loo_n, value = coefficient(
            [row for row in rows if row["run_id"] != omitted["run_id"]]
        )
        leave_one_out.append(
            {"omitted_run_id": omitted["run_id"], "n": loo_n, "spearman": value}
        )
    return {
        "feature": feature,
        "outcome": outcome,
        "n": n,
        "overall_spearman": overall,
        "by_load": by_load,
        "activated_runs_only": {"n": activated_n, "spearman": activated_value},
        "leave_one_run_out": leave_one_out,
    }


def _associations(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        _association_report(rows, feature, outcome)
        for feature in ASSOCIATION_FEATURES
        for outcome in ASSOCIATION_OUTCOMES
    ]


def _dose_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        str(budget): {
            "budget": budget,
            "retained_bounded_events": sum(
                int(
                    row["dose_budget_trace_coverage"][str(budget)][
                        "retained_bounded_events"
                    ]
                )
                for row in rows
            ),
            "retained_deferred_players": sum(
                int(
                    row["dose_budget_trace_coverage"][str(budget)][
                        "retained_deferred_players"
                    ]
                )
                for row in rows
            ),
            "by_load": [
                {
                    "load": load,
                    "retained_bounded_events": sum(
                        int(
                            row["dose_budget_trace_coverage"][str(budget)][
                                "retained_bounded_events"
                            ]
                        )
                        for row in rows
                        if row["load"] == load
                    ),
                    "retained_deferred_players": sum(
                        int(
                            row["dose_budget_trace_coverage"][str(budget)][
                                "retained_deferred_players"
                            ]
                        )
                        for row in rows
                        if row["load"] == load
                    ),
                }
                for load in FORMAL_E1_LOADS
            ],
        }
        for budget in DOSE_BUDGETS
    }


def evaluate_successor(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {
        (load, seed)
        for load in FORMAL_E1_LOADS
        for seed in G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS
    }
    identities = {(str(row.get("load")), str(row.get("seed"))) for row in rows}
    condition_1 = (
        len(rows) == 15
        and len(identities) == 15
        and identities == expected
        and len({str(row.get("run_id", "")) for row in rows}) == 15
        and all(row.get("g16_activation_pass") is True for row in rows)
        and all(row.get("runtime_identity_pass") is True for row in rows)
        and all(
            (_finite_int(row.get(field)) or 0) == 0
            for row in rows
            for field in VIOLATION_FIELDS
        )
    )
    threshold_reports = [
        _classifier_report(rows, threshold) for threshold in THRESHOLDS
    ]
    selected = _select_threshold(threshold_reports)
    safe = selected["predicted_safe"]
    unsafe = selected["predicted_unsafe"]
    condition_2 = (
        float(selected["threshold"]) > 1.25
        and (_number(selected["balanced_accuracy"]) or -math.inf) >= 0.70
        and (_number(selected["sensitivity"]) or -math.inf) >= 0.60
        and (_number(selected["specificity"]) or -math.inf) >= 0.60
        and safe["n"] >= 3
        and unsafe["n"] >= 3
        and len(safe["loads"]) >= 2
        and len(unsafe["loads"]) >= 2
    )
    contrast = selected["safe_minus_unsafe"]
    contrast_fields = (
        "mean_log_throughput_ratio_difference",
        "mean_log_qpr_ratio_difference",
    )
    condition_3 = all(
        _number(contrast.get(field)) is not None and float(contrast[field]) > 0.0
        for field in contrast_fields
    )
    envelope = selected["optimistic_screening_envelope"]
    condition_4 = len(envelope["by_load"]) == 3 and all(
        row["n"] == 5
        and (_number(row["throughput_mean_ratio"]) or -math.inf) > 1.0
        and (_number(row["qpr_mean_ratio"]) or -math.inf) > 1.0
        and row["joint_wins"] >= 1
        and row["joint_nonlosses"] >= 4
        and (_number(row["minimum_primary_ratio"]) or -math.inf) >= 0.80
        for row in envelope["by_load"]
    )
    condition_5 = True
    for load in FORMAL_E1_LOADS:
        for _, metric_field in PRIMARY_METRICS:
            values = [
                row
                for row in envelope["leave_one_seed_out_mean_differences"]
                if row["load"] == load and row["metric"] == metric_field
            ]
            nonnegative = sum(
                _number(row["mean_difference"]) is not None
                and float(row["mean_difference"]) >= 0.0
                for row in values
            )
            positive = sum(
                _number(row["mean_difference"]) is not None
                and float(row["mean_difference"]) > 0.0
                for row in values
            )
            condition_5 = condition_5 and (
                len(values) == 5 and nonnegative == 5 and positive >= 4
            )
    condition_6 = len(selected["leave_one_run_out"]) == 15 and all(
        (_number(row.get("balanced_accuracy")) or -math.inf) >= 0.65
        and (_number(row.get("sensitivity")) or -math.inf) >= 0.50
        and (_number(row.get("specificity")) or -math.inf) >= 0.50
        and all(
            _number(row["safe_minus_unsafe"].get(field)) is not None
            and float(row["safe_minus_unsafe"][field]) > 0.0
            for field in contrast_fields
        )
        for row in selected["leave_one_run_out"]
    )
    conditions = {
        "01_exact_15_pair_activation_identity_zero_violation_integrity": condition_1,
        "02_selected_stricter_threshold_classifier_and_group_floors": condition_2,
        "03_predicted_safe_mean_log_primary_effects_are_better": condition_3,
        "04_all_load_optimistic_envelope_primary_and_pair_floors": condition_4,
        "05_all_envelope_loo_means_nonnegative_and_four_positive": condition_5,
        "06_classifier_and_dual_effect_floors_survive_every_loo": condition_6,
    }
    authorized = all(conditions.values())
    return {
        "status": (
            "complete_stricter_threshold_successor_preregistration_eligible"
            if authorized
            else "complete_fixed_threshold_valve_family_closed"
        ),
        "stricter_threshold_successor_preregistration_eligible": authorized,
        "implementation_authorized": False,
        "sampling_authorized": False,
        "conditions": conditions,
        "failure_reasons": [name for name, passed in conditions.items() if not passed],
        "threshold_reports": threshold_reports,
        "selected_threshold_report": selected,
        "all_associations": _associations(rows),
        "dose_budget_trace_summary": _dose_summary(rows),
    }


def analyze(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest, g16_report = _validated_inputs(root)
    canonical = root / "online" / "canonical"
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    paired_index = {
        (row["load"], row["seed"]): row
        for row in g16_report["gate_result"]["paired_rows"]
    }
    metric_index = {row["run_id"]: row for row in g16_report["run_metrics"]}
    node_count = int(manifest["g16_overflow_magnitude_valve_development"]["node_count"])
    rows = []
    receipts = []
    for run in manifest["runs"]:
        if run["metadata"]["m1_operational_candidate"] != G16_CANDIDATE:
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
        control_metric = (
            metric_index.get(str(paired.get("control_run_id")))
            if isinstance(paired, Mapping)
            else None
        )
        if (
            not isinstance(paired, Mapping)
            or not isinstance(metric, Mapping)
            or not isinstance(control_metric, Mapping)
        ):
            raise DiagnosisError("G16 report lacks a candidate pair or metric row")
        rows.append(
            _feature_row(run, windows, paired, metric, control_metric, node_count)
        )
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
            "g16_analyzer_sha256": EXPECTED_G16_ANALYZER_FILE,
        },
        "definitions": {
            "independent_unit": "G16 candidate run/seed paired with same-tape C0",
            "first_overflow_ratio": "F/N in the first window of an overflow episode",
            "overflow_episode": "maximal consecutive scheduler-window sequence with feasible_ready_candidates>N",
            "quantile": "type-7 linear interpolation on ordered first-overflow ratios",
            "joint_nonloss": "throughput_ratio>=1 and qpr_ratio>=1",
            "joint_win": "throughput_ratio>1 and qpr_ratio>1",
            "exact_ties_retained": True,
            "thresholds": list(THRESHOLDS),
            "classifier": "at_least_one_first_overflow_and_fraction_ge_threshold_at_least_0.5",
            "optimistic_envelope": "predicted-safe uses observed G16; predicted-unsafe uses paired C0",
            "optimistic_envelope_is_noncausal": True,
            "dose_budgets_are_trace_coverage_not_counterfactuals": True,
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
        raise DiagnosisError("G17 output workspace must be absent before analysis")
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
