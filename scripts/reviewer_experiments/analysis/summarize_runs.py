"""Canonicalize experiment CSVs and produce reviewer-ready run-level statistics.

The input may contain one row per run or repeated observations belonging to the
same run.  Repeated rows are collapsed using documented, metric-name-based rules;
the resulting ``run_level.csv`` is the sole input to confidence intervals and
paired tests.  QPR is always recomputed for each run before any across-run mean:

    QPR_i = throughput_i [requests/ms] /
            (cost_i [simulator cost/completed request] * latency_i [ms])

No run is selected according to its performance or its agreement with an older
figure.  Invalid numerical values remain auditable through count/status columns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

try:  # ``python -m ...``
    from .stats import (
        bca_interval,
        holm_adjust,
        paired_effect_sizes,
        paired_permutation_test,
        precision_assessment,
    )
except ImportError:  # direct script execution
    from stats import (  # type: ignore
        bca_interval,
        holm_adjust,
        paired_effect_sizes,
        paired_permutation_test,
        precision_assessment,
    )


IDENTIFIER_COLUMNS = {
    "run_id",
    "seed",
    "pair_id",
    "algorithm",
    "variant",
    "scenario",
    "load",
    "node_count",
    "burst_pattern",
    "qos_class",
}

ALIASES = {
    "rand_seed": "seed",
    "random_seed": "seed",
    "scheduler": "algorithm",
    "sche": "algorithm",
    "method": "algorithm",
    "workload": "load",
    "workload_intensity": "load",
    "request_freq": "load",
    "nodes": "node_count",
    "cluster_size": "node_count",
    "cost_per_req": "cost",
    "average_cost": "cost",
    "avg_cost": "cost",
    "time_per_req": "latency",
    "latency_ms": "latency",
    "latency_mean_ms": "latency",
    "average_latency": "latency",
    "avg_latency": "latency",
    "rps": "throughput",
    "throughput_rps": "throughput",
    "cost_performance_ratio": "reported_qpr",
    "quality_price_ratio": "reported_qpr",
    "coldstart_time_per_req": "cold_start_latency",
    "cold_start_time_per_req": "cold_start_latency",
    "waitsche_time_per_req": "queue_latency",
    "wait_time_per_req": "queue_latency",
    "exe_time_per_req": "execution_latency",
    "execution_time_per_req": "execution_latency",
    "algo_exec_time": "scheduler_latency",
    "algorithm_execution_latency": "scheduler_latency",
    "scheduler_wall_ms": "scheduler_latency",
    "scheduler_latency_ms": "scheduler_latency",
    "scheduler_cpu_ms": "scheduler_cpu",
    "scheduler_peak_memory_mb": "scheduler_peak_memory",
    "cpu_util": "cpu_utilization",
    "memory_util": "memory_utilization",
    "mem_utilization": "memory_utilization",
}

ALGORITHM_NAMES = {
    "greedy": "Greedy",
    "random": "Random",
    "hash": "Hash",
    "load_least": "Load Balance",
    "load_balance": "Load Balance",
    "load balance": "Load Balance",
    "sche_faasrank": "FaaSRank",
    "faasrank": "FaaSRank",
    "sche_ocs": "OCS",
    "ocs": "OCS",
    "sche_hiku": "Hiku",
    "hiku": "Hiku",
    "sche_jiagu": "Jiagu",
    "jiagu": "Jiagu",
    "sche_orion": "Orion",
    "orion": "Orion",
    "sche_nash": "NSESche",
    "nash": "NSESche",
    "nsesche": "NSESche",
}

PREFERRED_METRICS = [
    "cost",
    "latency",
    "throughput",
    "qpr",
    "cold_start_latency",
    "queue_latency",
    "execution_latency",
    "scheduler_latency",
    "scheduler_cpu",
    "scheduler_peak_memory",
    "cpu_utilization",
    "memory_utilization",
    "fairness",
    "sla_violation_rate",
    "direct_cost_mean",
    "completion_rate",
    "recovery_time",
]

LOWER_IS_BETTER = {
    "cost",
    "latency",
    "cold_start_latency",
    "queue_latency",
    "execution_latency",
    "scheduler_latency",
    "scheduler_cpu",
    "scheduler_peak_memory",
    "sla_violation_rate",
    "recovery_time",
    "recovery_time_ms",
    "restricted_recovery_time_ms",
    "peak_queue",
    "latency_p95_ms",
    "latency_p99_ms",
    "stage_latency_p95_ms",
    "stage_latency_p99_ms",
    "admission_drop",
    "admission_reject",
    "timeout",
    "process_peak_rss_mib",
    "scheduler_wall_mean_us",
    "scheduler_cpu_mean_us",
    "solve_mean_us",
    "inner_rounds_mean",
    "outer_rounds_mean",
    "inner_limit_hit_rate",
    "outer_limit_hit_rate",
    "oscillation_window_rate",
    "nonconvergence_rate",
    "offline_build_wall_ms",
    "offline_build_cpu_ms",
    "offline_build_peak_rss_mib",
    "reference_table_size_mib",
    "reference_table_bytes",
    "reference_table_load_us",
    "reference_lookup_mean_us",
    "reference_missing_ratio",
    "reference_zero_ratio",
    "reference_negative_ratio",
    "welfare_gap_mean",
    "welfare_gap_p95",
    "timeout_rate",
    "drop_rate",
    "rejection_rate",
}

# Frozen n=10 -> n=20 rule from the reviewer-response protocol.  Metrics not
# listed (or matched by the tail/overhead rules below) remain descriptive and
# cannot trigger additional seeds.
PRECISION_TRIGGER_THRESHOLDS = {
    "throughput": 0.05,
    "cost": 0.05,
    "qpr": 0.05,
}


def _precision_trigger_threshold(metric: str) -> float | None:
    normalized = metric.strip().lower()
    if normalized in PRECISION_TRIGGER_THRESHOLDS:
        return PRECISION_TRIGGER_THRESHOLDS[normalized]
    if "p95" in normalized or "p99" in normalized:
        return 0.10
    if normalized.startswith("scheduler_") or normalized == "scheduler_latency":
        return 0.10
    return None


def _snake_case(value: str) -> str:
    value = value.strip().replace("%", "percent")
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_").lower()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, np.number)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _canonical_algorithm(value: Any) -> str:
    text = str(value or "").strip().rstrip(".")
    return ALGORITHM_NAMES.get(text.lower(), text)


def _canonical_load(value: Any) -> str:
    text = str(value or "").strip()
    lowered = text.lower()
    return {
        "rflow": "low",
        "low load": "low",
        "rfmiddle": "middle",
        "mid": "middle",
        "medium": "middle",
        "middle load": "middle",
        "rfhigh": "high",
        "high load": "high",
    }.get(lowered, lowered or "unspecified")


def read_csv_rows(path: str | Path) -> list[dict[str, Any]]:
    """Read and canonicalize headers without altering the source CSV."""

    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {source}")
        normalized = [_snake_case(name) for name in reader.fieldnames]
        rows: list[dict[str, Any]] = []
        for source_row, raw in enumerate(reader, start=2):
            row: dict[str, Any] = {"_source_row": source_row}
            for old_name, normalized_name in zip(reader.fieldnames, normalized):
                canonical = ALIASES.get(normalized_name, normalized_name)
                value = raw.get(old_name, "")
                # An explicitly named canonical column takes precedence over an alias.
                if canonical not in row or normalized_name == canonical:
                    row[canonical] = value
            if "algorithm" in row:
                row["algorithm"] = _canonical_algorithm(row["algorithm"])
            if "load" in row:
                row["load"] = _canonical_load(row["load"])
            rows.append(row)
    return rows


def _aggregation_kind(metric: str) -> str:
    lowered = metric.lower()
    if "peak" in lowered or lowered.endswith("_max") or lowered.startswith("max_"):
        return "max"
    if (
        lowered.endswith("_count")
        or lowered.endswith("_requests")
        or lowered
        in {
            "arrivals",
            "completed",
            "timeouts",
            "dropped",
            "rejected",
            "cold_starts",
        }
    ):
        return "sum"
    return "mean"


def collapse_to_run_level(
    rows: Sequence[Mapping[str, Any]],
    *,
    run_keys: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Collapse repeated observations to one auditable row per independent run."""

    if not rows:
        return []
    run_keys = tuple(
        run_keys
        or (
            "scenario",
            "load",
            "node_count",
            "burst_pattern",
            "qos_class",
            "algorithm",
            "variant",
            "seed",
            "run_id",
        )
    )
    prepared: list[dict[str, Any]] = []
    for index, source_row in enumerate(rows, start=1):
        row = dict(source_row)
        row.setdefault("scenario", "unspecified")
        row["scenario"] = str(row["scenario"] or "unspecified").strip().lower()
        row["load"] = _canonical_load(row.get("load", "unspecified"))
        row["algorithm"] = _canonical_algorithm(row.get("algorithm", ""))
        if not str(row.get("seed", "")).strip():
            row["seed"] = str(row.get("run_id", "")).strip()
        if not str(row.get("run_id", "")).strip():
            row["run_id"] = str(row.get("seed", "")).strip() or f"row-{index}"
        row["pair_id"] = str(row.get("pair_id", "")).strip() or str(
            row["seed"] or row["run_id"]
        )
        prepared.append(row)

    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in prepared:
        key = tuple(str(row.get(name, "")).strip() for name in run_keys)
        groups[key].append(row)

    run_level: list[dict[str, Any]] = []
    for key in sorted(groups):
        members = groups[key]
        result: dict[str, Any] = {name: value for name, value in zip(run_keys, key)}
        result["pair_id"] = str(members[0].get("pair_id", result.get("seed", "")))
        result["source_rows"] = len(members)
        warnings: list[str] = []
        columns = sorted(set().union(*(member.keys() for member in members)))
        for column in columns:
            if (
                column.startswith("_")
                or column in result
                or column in {"pair_id", "source_rows"}
            ):
                continue
            raw_values = [member.get(column) for member in members]
            numeric = [_as_float(value) for value in raw_values]
            present_numeric = [value for value in numeric if value is not None]
            nonempty = [
                str(value).strip() for value in raw_values if str(value or "").strip()
            ]
            if present_numeric and len(present_numeric) == len(nonempty):
                kind = _aggregation_kind(column)
                if kind == "sum":
                    result[column] = float(np.sum(present_numeric))
                elif kind == "max":
                    result[column] = float(np.max(present_numeric))
                else:
                    result[column] = float(np.mean(present_numeric))
            elif nonempty:
                result[column] = nonempty[0]
                if any(value != nonempty[0] for value in nonempty[1:]):
                    warnings.append(f"conflicting_{column}")

        reported = _as_float(result.get("reported_qpr"))
        if reported is not None:
            result["reported_qpr"] = reported
        throughput = _as_float(result.get("throughput"))
        cost = _as_float(result.get("cost"))
        latency = _as_float(result.get("latency"))
        result["qpr"] = math.nan
        result["qpr_valid"] = 0
        if throughput is None or cost is None or latency is None:
            result["qpr_status"] = "missing_input"
        elif not all(math.isfinite(value) for value in (throughput, cost, latency)):
            result["qpr_status"] = "nonfinite_input"
        elif throughput < 0.0:
            result["qpr_status"] = "negative_throughput"
        elif cost <= 0.0:
            result["qpr_status"] = "nonpositive_cost"
        elif latency <= 0.0:
            result["qpr_status"] = "nonpositive_latency"
        else:
            result["qpr"] = throughput / (cost * latency)
            result["qpr_valid"] = 1
            result["qpr_status"] = "ok"
        result["aggregation_warnings"] = ";".join(warnings)
        run_level.append(result)
    return run_level


def infer_metrics(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    candidates: set[str] = set()
    for row in rows:
        for key, value in row.items():
            if (
                key.startswith("_")
                or key in IDENTIFIER_COLUMNS
                or key
                in {
                    "source_rows",
                    "qpr_valid",
                    "qpr_status",
                    "aggregation_warnings",
                    "reported_qpr",
                }
            ):
                continue
            if _as_float(value) is not None:
                candidates.add(key)
    ordered = [metric for metric in PREFERRED_METRICS if metric in candidates]
    ordered.extend(sorted(candidates - set(ordered)))
    return ordered


def _stable_seed(base_seed: int, *parts: Any) -> int:
    payload = "|".join(str(part) for part in (base_seed, *parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "little") % (2**32)


def _group_rows(
    rows: Sequence[Mapping[str, Any]], group_columns: Sequence[str]
) -> dict[tuple[str, ...], list[Mapping[str, Any]]]:
    grouped: dict[tuple[str, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(column, "")) for column in group_columns)].append(row)
    return grouped


def summarize_run_level(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_columns: Sequence[str],
    metrics: Sequence[str] | None = None,
    confidence: float = 0.95,
    bootstrap_resamples: int = 10_000,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    """Compute one mean/BCa-CI row per experimental cell and metric."""

    metrics = list(metrics or infer_metrics(rows))
    output: list[dict[str, Any]] = []
    for key, members in sorted(_group_rows(rows, group_columns).items()):
        group_values = {name: value for name, value in zip(group_columns, key)}
        for metric in metrics:
            raw = [_as_float(member.get(metric)) for member in members]
            present = [value for value in raw if value is not None]
            finite = np.asarray(
                [value for value in present if math.isfinite(value)], dtype=float
            )
            nonfinite_n = len(present) - int(finite.size)
            result: dict[str, Any] = {
                **group_values,
                "metric": metric,
                "n_total": len(members),
                "n_present": len(present),
                "n_finite": int(finite.size),
                "n_missing": len(members) - len(present),
                "n_nonfinite": nonfinite_n,
                "n_zero": int(np.count_nonzero(finite == 0.0)),
                "n_negative": int(np.count_nonzero(finite < 0.0)),
                "mean": math.nan,
                "median": math.nan,
                "std": math.nan,
                "bca_low": math.nan,
                "bca_high": math.nan,
                "ci_half_width": math.nan,
                "relative_ci_half_width": math.nan,
                "confidence": confidence,
                "analysis_status": "no_finite_values",
            }
            if finite.size:
                mean = float(np.mean(finite))
                result.update(
                    {
                        "mean": mean,
                        "median": float(np.median(finite)),
                        "std": float(np.std(finite, ddof=1))
                        if finite.size >= 2
                        else math.nan,
                        "analysis_status": "insufficient_for_bca"
                        if finite.size < 3
                        else "ok",
                    }
                )
                if finite.size >= 3:
                    ci = bca_interval(
                        finite,
                        confidence=confidence,
                        n_resamples=bootstrap_resamples,
                        seed=_stable_seed(seed, *key, metric, "summary"),
                    )
                    low = float(ci["low"])
                    high = float(ci["high"])
                    half_width = (high - low) / 2.0
                    relative = half_width / abs(mean) if abs(mean) > 1e-12 else math.inf
                    result.update(
                        {
                            "bca_low": low,
                            "bca_high": high,
                            "ci_half_width": half_width,
                            "relative_ci_half_width": relative,
                        }
                    )
                if nonfinite_n or result["n_missing"]:
                    result[
                        "analysis_status"
                    ] = f"{result['analysis_status']};invalid_values_present"
            output.append(result)
    return output


def _seed_sort_key(value: Any) -> tuple[int, float | str]:
    number = _as_float(value)
    if number is not None and math.isfinite(number):
        return (0, number)
    return (1, str(value))


def _paired_relative_statistics(
    reference_values: np.ndarray,
    comparator_values: np.ndarray,
    *,
    direction: float,
    confidence: float,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    """Return paired ratio and relative-change statistics without fake epsilons.

    The denominator is the comparator value for the same seed.  A zero
    comparator makes that pair's ratio undefined; in that case the complete
    relative analysis is marked unavailable rather than silently dropping the
    seed or injecting a pseudo-constant.
    """

    denominator_zero = int(np.count_nonzero(comparator_values == 0.0))
    result: dict[str, Any] = {
        "paired_ratio_reference_over_comparator": math.nan,
        "paired_ratio_ci_low": math.nan,
        "paired_ratio_ci_high": math.nan,
        "relative_change_reference_minus_comparator": math.nan,
        "relative_change_ci_low": math.nan,
        "relative_change_ci_high": math.nan,
        "oriented_relative_improvement": math.nan,
        "oriented_relative_improvement_ci_low": math.nan,
        "oriented_relative_improvement_ci_high": math.nan,
        "relative_change_n": 0,
        "relative_change_denominator_zero_n": denominator_zero,
        "relative_change_nonfinite_n": 0,
        "relative_change_status": (
            "undefined_zero_comparator" if denominator_zero else "insufficient_for_bca"
        ),
    }
    if denominator_zero:
        return result

    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        ratios = reference_values / comparator_values
    nonfinite_ratio = int(np.count_nonzero(~np.isfinite(ratios)))
    if nonfinite_ratio:
        result.update(
            {
                "relative_change_nonfinite_n": nonfinite_ratio,
                "relative_change_status": "undefined_nonfinite_ratio",
            }
        )
        return result
    relative = ratios - 1.0
    oriented = direction * relative
    result.update(
        {
            "paired_ratio_reference_over_comparator": float(np.mean(ratios)),
            "relative_change_reference_minus_comparator": float(np.mean(relative)),
            "oriented_relative_improvement": float(np.mean(oriented)),
            "relative_change_n": int(relative.size),
            "relative_change_status": "ok"
            if relative.size >= 3
            else "insufficient_for_bca",
        }
    )
    if relative.size < 3:
        return result

    ratio_ci = bca_interval(
        ratios,
        confidence=confidence,
        n_resamples=bootstrap_resamples,
        seed=seed,
    )
    relative_ci = bca_interval(
        relative,
        confidence=confidence,
        n_resamples=bootstrap_resamples,
        seed=(seed + 1) % (2**32 - 1),
    )
    oriented_ci = bca_interval(
        oriented,
        confidence=confidence,
        n_resamples=bootstrap_resamples,
        seed=(seed + 2) % (2**32 - 1),
    )
    result.update(
        {
            "paired_ratio_ci_low": float(ratio_ci["low"]),
            "paired_ratio_ci_high": float(ratio_ci["high"]),
            "relative_change_ci_low": float(relative_ci["low"]),
            "relative_change_ci_high": float(relative_ci["high"]),
            "oriented_relative_improvement_ci_low": float(oriented_ci["low"]),
            "oriented_relative_improvement_ci_high": float(oriented_ci["high"]),
        }
    )
    return result


def build_precision_table(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_columns: Sequence[str],
    metrics: Sequence[str],
    first_n: int = 10,
    max_n: int = 20,
    target_relative_half_width: float = 0.10,
    confidence: float = 0.95,
    bootstrap_resamples: int = 10_000,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for key, members in sorted(_group_rows(rows, group_columns).items()):
        ordered = sorted(
            members,
            key=lambda row: (
                _seed_sort_key(row.get("seed")),
                str(row.get("run_id", "")),
            ),
        )
        group_values = {name: value for name, value in zip(group_columns, key)}
        for metric in metrics:
            values = [
                value
                for value in (_as_float(member.get(metric)) for member in ordered)
                if value is not None and math.isfinite(value)
            ]
            n_total = len(ordered)
            n_finite = len(values)
            frozen_threshold = _precision_trigger_threshold(metric)
            assessment = precision_assessment(
                values,
                first_n=first_n,
                max_n=max_n,
                target_relative_half_width=(
                    frozen_threshold
                    if frozen_threshold is not None
                    else target_relative_half_width
                ),
                confidence=confidence,
                n_resamples=bootstrap_resamples,
                seed=_stable_seed(seed, *key, metric, "precision"),
            )
            # ``available_n`` is retained as the finite-value count for backward
            # compatibility.  A completed run may legitimately have an undefined
            # derived metric (for example, QPR when no request completes), so the
            # run cap must be evaluated from the number of completed runs instead.
            assessment["n_total"] = n_total
            assessment["n_finite"] = n_finite
            # Formal execution is fixed at 20 paired seeds.  These widths are
            # descriptive diagnostics only and can never stop bank B or request
            # a result-dependent retry.
            assessment["controls_ci_extension"] = False
            assessment["predeclared_precision_diagnostic"] = (
                frozen_threshold is not None
            )
            assessment["formal_sample_policy"] = "fixed_paired_n20"
            assessment["recommended_n"] = max_n
            if n_total < max_n:
                assessment["decision"] = "fixed_n20_bank_incomplete"
            elif n_finite < max_n:
                assessment[
                    "decision"
                ] = "fixed_n20_complete_with_insufficient_finite_values"
            elif bool(assessment.get("precision_met_n20")):
                assessment["decision"] = "fixed_n20_complete_precision_met"
            else:
                assessment["decision"] = "fixed_n20_complete_precision_not_met"
            output.append({**group_values, "metric": metric, **assessment})
    return output


def build_extension_decisions(
    precision_rows: Sequence[Mapping[str, Any]],
    *,
    context_columns: Sequence[str],
    treatment_column: str,
    first_n: int = 10,
    max_n: int = 20,
) -> list[dict[str, Any]]:
    """Report fixed-bank completion plus result-blind precision diagnostics.

    The historical function/output name is retained for compatibility.  It no
    longer makes an adaptive sample-size decision: every formal scenario uses
    the same preregistered E01--E20 paired bank.
    """

    output: list[dict[str, Any]] = []
    for key, members in sorted(_group_rows(precision_rows, context_columns).items()):
        context = {name: value for name, value in zip(context_columns, key)}
        diagnostics = [
            row
            for row in members
            if bool(row.get("predeclared_precision_diagnostic"))
        ]
        methods = sorted(
            {
                str(row.get(treatment_column, ""))
                for row in members
                if str(row.get(treatment_column, ""))
            }
        )
        decision = (
            "fixed_n20_bank_complete"
            if members
            and all(int(row.get("n_total", 0) or 0) >= max_n for row in members)
            else "fixed_n20_bank_required"
        )
        output.append(
            {
                **context,
                "decision": decision,
                "first_n": first_n,
                "max_n": max_n,
                "method_count": len(methods),
                "methods": ";".join(methods),
                "trigger_check_count": 0,
                "precision_diagnostic_count": len(diagnostics),
                "failed_n10_trigger_count": 0,
                "failed_n10_precision_diagnostic_count": sum(
                    int(row.get("available_n", 0) or 0) >= first_n
                    and not bool(row.get("precision_met_n10"))
                    for row in diagnostics
                ),
                "extension_scope": "fixed_paired_n20_all_methods",
            }
        )
    return output


def paired_comparisons(
    rows: Sequence[Mapping[str, Any]],
    *,
    context_columns: Sequence[str],
    treatment_column: str,
    reference: str,
    pair_column: str,
    metrics: Sequence[str],
    confidence: float = 0.95,
    bootstrap_resamples: int = 10_000,
    permutation_resamples: int = 100_000,
    alpha: float = 0.05,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    """Compute paired reference-vs-comparator tests and Holm correction by cell/metric."""

    grouped = _group_rows(rows, context_columns)
    comparisons: list[dict[str, Any]] = []
    for key, members in sorted(grouped.items()):
        context = {name: value for name, value in zip(context_columns, key)}
        treatments = sorted(
            {str(member.get(treatment_column, "")) for member in members}
        )
        if reference not in treatments:
            continue
        for metric in metrics:
            maps: dict[str, dict[str, float]] = {}
            duplicate_pairs: set[str] = set()
            for treatment in treatments:
                pair_map: dict[str, float] = {}
                for member in members:
                    if str(member.get(treatment_column, "")) != treatment:
                        continue
                    pair = str(member.get(pair_column, ""))
                    value = _as_float(member.get(metric))
                    if value is None or not math.isfinite(value):
                        continue
                    if pair in pair_map:
                        duplicate_pairs.add(f"{treatment}:{pair}")
                    pair_map[pair] = value
                maps[treatment] = pair_map
            if duplicate_pairs:
                raise ValueError(
                    "duplicate pair identifiers within an experimental cell: "
                    + ", ".join(sorted(duplicate_pairs)[:5])
                )

            reference_map = maps[reference]
            for comparator in treatments:
                if comparator == reference:
                    continue
                comparator_map = maps[comparator]
                pairs = sorted(
                    set(reference_map) & set(comparator_map), key=_seed_sort_key
                )
                result: dict[str, Any] = {
                    **context,
                    "metric": metric,
                    "treatment_column": treatment_column,
                    "reference": reference,
                    "comparator": comparator,
                    "n_reference": len(reference_map),
                    "n_comparator": len(comparator_map),
                    "n_pairs": len(pairs),
                    "missing_reference_pairs": len(
                        set(comparator_map) - set(reference_map)
                    ),
                    "missing_comparator_pairs": len(
                        set(reference_map) - set(comparator_map)
                    ),
                    "mean_reference": math.nan,
                    "mean_comparator": math.nan,
                    "raw_difference_reference_minus_comparator": math.nan,
                    "oriented_improvement": math.nan,
                    "improvement_ci_low": math.nan,
                    "improvement_ci_high": math.nan,
                    "higher_is_better": metric not in LOWER_IS_BETTER,
                    "permutation_p_raw": math.nan,
                    "permutation_exact": False,
                    "cohen_dz": math.nan,
                    "rank_biserial": math.nan,
                    "paired_ratio_reference_over_comparator": math.nan,
                    "paired_ratio_ci_low": math.nan,
                    "paired_ratio_ci_high": math.nan,
                    "relative_change_reference_minus_comparator": math.nan,
                    "relative_change_ci_low": math.nan,
                    "relative_change_ci_high": math.nan,
                    "oriented_relative_improvement": math.nan,
                    "oriented_relative_improvement_ci_low": math.nan,
                    "oriented_relative_improvement_ci_high": math.nan,
                    "relative_change_n": 0,
                    "relative_change_denominator_zero_n": 0,
                    "relative_change_nonfinite_n": 0,
                    "relative_change_status": "insufficient_pairs",
                    "p_holm": math.nan,
                    "reject_holm": False,
                    "alpha": alpha,
                    "analysis_status": "insufficient_pairs",
                }
                if not pairs:
                    comparisons.append(result)
                    continue
                reference_values = np.asarray(
                    [reference_map[pair] for pair in pairs], dtype=float
                )
                comparator_values = np.asarray(
                    [comparator_map[pair] for pair in pairs], dtype=float
                )
                direction = 1.0 if metric not in LOWER_IS_BETTER else -1.0
                oriented_reference = direction * reference_values
                oriented_comparator = direction * comparator_values
                improvement = oriented_reference - oriented_comparator
                effect = paired_effect_sizes(oriented_reference, oriented_comparator)
                test = paired_permutation_test(
                    oriented_reference,
                    oriented_comparator,
                    alternative="two-sided",
                    n_resamples=permutation_resamples,
                    seed=_stable_seed(seed, *key, metric, comparator, "permutation"),
                )
                result.update(
                    {
                        "mean_reference": float(np.mean(reference_values)),
                        "mean_comparator": float(np.mean(comparator_values)),
                        "raw_difference_reference_minus_comparator": float(
                            np.mean(reference_values - comparator_values)
                        ),
                        "oriented_improvement": float(np.mean(improvement)),
                        "permutation_p_raw": float(test["p_value"]),
                        "permutation_exact": bool(test["exact"]),
                        "cohen_dz": effect["cohen_dz"],
                        "rank_biserial": effect["rank_biserial"],
                        "analysis_status": "ok"
                        if len(pairs) >= 3
                        else "insufficient_for_bca",
                    }
                )
                result.update(
                    _paired_relative_statistics(
                        reference_values,
                        comparator_values,
                        direction=direction,
                        confidence=confidence,
                        bootstrap_resamples=bootstrap_resamples,
                        seed=_stable_seed(
                            seed, *key, metric, comparator, "paired_relative"
                        ),
                    )
                )
                if len(pairs) >= 3:
                    ci = bca_interval(
                        improvement,
                        confidence=confidence,
                        n_resamples=bootstrap_resamples,
                        seed=_stable_seed(seed, *key, metric, comparator, "paired_bca"),
                    )
                    result["improvement_ci_low"] = ci["low"]
                    result["improvement_ci_high"] = ci["high"]
                comparisons.append(result)

    # Each context/metric is a declared family: NSESche versus every comparator.
    families: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(comparisons):
        p_value = _as_float(row.get("permutation_p_raw"))
        if p_value is None or not math.isfinite(p_value):
            continue
        family = tuple(str(row.get(column, "")) for column in context_columns) + (
            str(row["metric"]),
        )
        families[family].append(index)
    for indices in families.values():
        adjusted, rejected = holm_adjust(
            [float(comparisons[index]["permutation_p_raw"]) for index in indices],
            alpha=alpha,
        )
        for index, p_adjusted, reject in zip(indices, adjusted, rejected):
            comparisons[index]["p_holm"] = p_adjusted
            comparisons[index]["reject_holm"] = reject
    return comparisons


def write_csv(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        destination.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_pipeline(
    *,
    input_csv: str | Path,
    output_dir: str | Path,
    group_columns: Sequence[str],
    metrics: Sequence[str] | None = None,
    treatment_column: str = "algorithm",
    reference: str = "NSESche",
    pair_column: str = "pair_id",
    confidence: float = 0.95,
    bootstrap_resamples: int = 10_000,
    permutation_resamples: int = 100_000,
    alpha: float = 0.05,
    first_n: int = 10,
    max_n: int = 20,
    target_relative_half_width: float = 0.10,
    seed: int = 20260809,
) -> dict[str, Path]:
    source = Path(input_csv).resolve()
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    source_rows = read_csv_rows(source)
    run_rows = collapse_to_run_level(source_rows)
    selected_metrics = list(metrics or infer_metrics(run_rows))
    active_group_columns = [
        column for column in group_columns if any(column in row for row in run_rows)
    ]
    if treatment_column not in active_group_columns:
        active_group_columns.append(treatment_column)
    summaries = summarize_run_level(
        run_rows,
        group_columns=active_group_columns,
        metrics=selected_metrics,
        confidence=confidence,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    precision = build_precision_table(
        run_rows,
        group_columns=active_group_columns,
        metrics=selected_metrics,
        first_n=first_n,
        max_n=max_n,
        target_relative_half_width=target_relative_half_width,
        confidence=confidence,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    context_columns = [
        column for column in active_group_columns if column != treatment_column
    ]
    extension_decisions = build_extension_decisions(
        precision,
        context_columns=context_columns,
        treatment_column=treatment_column,
        first_n=first_n,
        max_n=max_n,
    )
    comparisons = paired_comparisons(
        run_rows,
        context_columns=context_columns,
        treatment_column=treatment_column,
        reference=reference,
        pair_column=pair_column,
        metrics=selected_metrics,
        confidence=confidence,
        bootstrap_resamples=bootstrap_resamples,
        permutation_resamples=permutation_resamples,
        alpha=alpha,
        seed=seed,
    )

    outputs = {
        "run_level": destination / "run_level.csv",
        "summary": destination / "summary.csv",
        "comparisons": destination / "comparisons.csv",
        "precision": destination / "precision.csv",
        "extension_decisions": destination / "extension_decisions.csv",
        "manifest": destination / "analysis_manifest.json",
    }
    write_csv(outputs["run_level"], run_rows)
    write_csv(outputs["summary"], summaries)
    write_csv(outputs["comparisons"], comparisons)
    write_csv(outputs["precision"], precision)
    write_csv(outputs["extension_decisions"], extension_decisions)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(source),
        "input_sha256": _source_sha256(source),
        "source_rows": len(source_rows),
        "run_level_rows": len(run_rows),
        "group_columns": active_group_columns,
        "metrics": selected_metrics,
        "qpr_formula": (
            "throughput [requests/ms = 10^3 requests/s] / "
            "(cost [simulator internal cost/completed request] * latency [ms]), "
            "computed per run"
        ),
        "treatment_column": treatment_column,
        "reference": reference,
        "pair_column": pair_column,
        "confidence": confidence,
        "bootstrap_resamples": bootstrap_resamples,
        "permutation_resamples": permutation_resamples,
        "holm_alpha": alpha,
        "precision_rule": {
            "first_n": first_n,
            "max_n": max_n,
            "formal_sample_policy": "fixed paired E01--E20 for every method/cell",
            "precision_diagnostic_relative_ci_half_width": {
                "throughput": 0.05,
                "cost": 0.05,
                "qpr": 0.05,
                "p95_p99": 0.10,
                "scheduler_overhead": 0.10,
            },
            "other_metric_descriptive_threshold": target_relative_half_width,
            "execution_scope": "all ten methods in both fixed paired banks",
            "result_conditioned_extension": False,
        },
        "random_seed": seed,
        "integrity_policy": (
            "No performance-based run selection; non-finite values are counted and flagged."
        ),
    }
    outputs["manifest"].write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return outputs


def _comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw or run-level CSV")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--group-by",
        default="scenario,load,node_count,burst_pattern,qos_class,algorithm,variant",
    )
    parser.add_argument(
        "--metrics", default="", help="Comma-separated; empty means infer"
    )
    parser.add_argument("--treatment-column", default="algorithm")
    parser.add_argument("--reference", default="NSESche")
    parser.add_argument("--pair-column", default="pair_id")
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--bootstrap-resamples", type=int, default=10_000)
    parser.add_argument("--permutation-resamples", type=int, default=100_000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--first-n", type=int, default=10)
    parser.add_argument("--max-n", type=int, default=20)
    parser.add_argument(
        "--target-relative-half-width",
        type=float,
        default=0.10,
        help="descriptive fallback for non-trigger metrics; frozen trigger thresholds remain 5%%/10%%",
    )
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args(argv)

    outputs = run_pipeline(
        input_csv=args.input,
        output_dir=args.output_dir,
        group_columns=_comma_list(args.group_by),
        metrics=_comma_list(args.metrics) or None,
        treatment_column=args.treatment_column,
        reference=_canonical_algorithm(args.reference)
        if args.treatment_column == "algorithm"
        else args.reference,
        pair_column=args.pair_column,
        confidence=args.confidence,
        bootstrap_resamples=args.bootstrap_resamples,
        permutation_resamples=args.permutation_resamples,
        alpha=args.alpha,
        first_n=args.first_n,
        max_n=args.max_n,
        target_relative_half_width=args.target_relative_half_width,
        seed=args.seed,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
