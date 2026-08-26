"""One-time metric reveal for the audited V78 formal E2 overlay."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from scripts.reviewer_experiments.analysis.stats import bca_interval
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


ROOT = Path("tmp/nse_formal_e2_low_n100_overlay_20260826_v78")
MANIFEST_PATH = ROOT / "manifest.ready.json"
BLIND_AUDIT_PATH = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_formal_e2_low_n100_overlay_blind_audit_v78.json"
)
OUTPUT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_formal_e2_low_n100_overlay_result_v78.json"
)
MARKER = "formal_e2_nsesche_profile_overlay"
METHODS = (
    "greedy",
    "random",
    "hash",
    "load_least",
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
    "sche_nash",
)
BASELINES = tuple(method for method in METHODS if method != "sche_nash")
SEEDS = tuple(f"E{index:02d}" for index in range(1, 21))
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)


def finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def summary_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    if summary.get("run_complete") is not True:
        raise RuntimeError("summary is not complete")
    fixed = summary.get("fixed_observation_window")
    if not isinstance(fixed, dict):
        fixed = {}
    cohort = summary.get("drained_arrival_cohort")
    if not isinstance(cohort, dict):
        cohort = {}
    latency = cohort.get("latency_ms", summary.get("latency_ms"))
    if not isinstance(latency, dict):
        latency = {}

    completed = cohort.get("completed", summary.get("completed"))
    throughput_rps = fixed.get(
        "throughput_requests_per_second",
        summary.get("throughput_requests_per_second"),
    )
    latency_mean = latency.get("mean")
    cost = summary.get("simulator_internal_cost_per_completed_request")
    if not isinstance(completed, int) or isinstance(completed, bool) or completed < 0:
        raise RuntimeError("completed count is invalid")
    if not finite_number(throughput_rps) or float(throughput_rps) < 0.0:
        raise RuntimeError("fixed-window throughput is invalid")
    throughput = float(throughput_rps) / 1000.0
    qpr = None
    if (
        completed > 0
        and throughput > 0.0
        and finite_number(latency_mean)
        and float(latency_mean) > 0.0
        and finite_number(cost)
        and float(cost) > 0.0
    ):
        value = throughput / (float(latency_mean) * float(cost))
        if math.isfinite(value) and value >= 0.0:
            qpr = value
    return {
        "completed": completed,
        "throughput_requests_per_ms": throughput,
        "latency_mean_ms": float(latency_mean) if finite_number(latency_mean) else None,
        "cost_per_completed_request": float(cost) if finite_number(cost) else None,
        "qpr_finite_only": qpr,
        "qpr_zero_completed_as_zero": 0.0 if qpr is None else qpr,
    }


def metric_summary(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    values = [float(row[metric]) for row in rows if finite_number(row.get(metric))]
    if not values:
        raise RuntimeError(f"{metric} has no finite values")
    return {
        "n_total": len(rows),
        "n_finite": len(values),
        "n_undefined": len(rows) - len(values),
        "mean": float(np.mean(values)),
        "sample_std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def paired_comparison(
    candidate: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    metric: str,
    bootstrap_seed: int,
) -> dict[str, Any]:
    included: list[str] = []
    excluded: list[str] = []
    candidate_values: list[float] = []
    baseline_values: list[float] = []
    for seed in SEEDS:
        left = baseline[seed].get(metric)
        right = candidate[seed].get(metric)
        if finite_number(left) and finite_number(right):
            included.append(seed)
            baseline_values.append(float(left))
            candidate_values.append(float(right))
        else:
            excluded.append(seed)
    if len(included) < 3:
        raise RuntimeError(f"{metric} has fewer than three finite pairs")
    differences = [
        candidate_value - baseline_value
        for candidate_value, baseline_value in zip(candidate_values, baseline_values)
    ]
    baseline_mean = float(np.mean(baseline_values))
    candidate_mean = float(np.mean(candidate_values))
    difference_mean = float(np.mean(differences))
    return {
        "paired_n": len(included),
        "included_seeds": included,
        "excluded_nonfinite_pair_seeds": excluded,
        "paired_baseline_mean": baseline_mean,
        "paired_candidate_mean": candidate_mean,
        "candidate_minus_baseline_mean": difference_mean,
        "candidate_relative_change_on_paired_means": (
            difference_mean / baseline_mean if baseline_mean != 0.0 else None
        ),
        "paired_difference_sample_std": statistics.stdev(differences),
        "paired_difference_bca_95_ci": bca_interval(
            differences,
            n_resamples=10_000,
            seed=bootstrap_seed,
        ),
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"formal overlay result already exists: {OUTPUT}")

    blind = read_json(BLIND_AUDIT_PATH)
    claimed_audit_hash = blind.get("audit_hash")
    unhashed_blind = dict(blind)
    unhashed_blind.pop("audit_hash", None)
    if (
        blind.get("status") != "passed"
        or blind.get("metrics_consulted") is not False
        or blind.get("scientific_result_files_parsed") != 0
        or blind.get("canonical_count") != 20
        or blind.get("frozen_baseline_count") != 180
        or blind.get("cross_version_pair_equalities_checked") != 180
        or blind.get("errors") != []
        or claimed_audit_hash != object_hash(unhashed_blind)
    ):
        raise RuntimeError("blind audit does not authorize the metric reveal")

    manifest = read_json(MANIFEST_PATH)
    if manifest.get("manifest_hash") != blind.get("manifest_hash") or file_hash(
        MANIFEST_PATH
    ) != blind.get("manifest_file_sha256"):
        raise RuntimeError("formal overlay manifest changed after the blind audit")
    overlay = manifest[MARKER]

    rows: list[dict[str, Any]] = []
    candidate_run_by_seed = {run["seed"]: run for run in manifest["runs"]}
    for seed in SEEDS:
        run = candidate_run_by_seed[seed]
        summary_path = (
            ROOT
            / "formal-runs"
            / "canonical"
            / run["run_id"]
            / manifest["execution"]["result_relative_path"].format(run_id=run["run_id"])
        )
        summary = read_json(summary_path)
        if summary.get("run_id") != run["run_id"]:
            raise RuntimeError(f"candidate summary identity mismatch: {run['run_id']}")
        rows.append(
            {
                "method": "sche_nash",
                "role": "candidate",
                "seed": seed,
                "run_id": run["run_id"],
                "variant": run["variant"],
                "summary_path": str(summary_path),
                "summary_file_sha256": file_hash(summary_path),
                **summary_metrics(summary),
            }
        )

    baseline_entries = overlay["frozen_baseline_runs"]
    source_manifest_cache: dict[str, dict[str, Any]] = {}
    for entry in baseline_entries:
        source_path = entry["source_manifest_path"]
        if source_path not in source_manifest_cache:
            source_manifest_cache[source_path] = read_json(Path(source_path))
        source_manifest = source_manifest_cache[source_path]
        run_id = entry["source_run_id"]
        summary_path = Path(entry["source_canonical_directory"]) / source_manifest[
            "execution"
        ]["result_relative_path"].format(run_id=run_id)
        if file_hash(summary_path) != entry["source_summary_sha256"]:
            raise RuntimeError(f"baseline summary changed after blind audit: {run_id}")
        summary = read_json(summary_path)
        if summary.get("run_id") != run_id:
            raise RuntimeError(f"baseline summary identity mismatch: {run_id}")
        rows.append(
            {
                "method": entry["source_method"],
                "role": "frozen_baseline",
                "seed": entry["source_seed"],
                "run_id": run_id,
                "variant": entry["source_variant"],
                "summary_path": str(summary_path),
                "summary_file_sha256": entry["source_summary_sha256"],
                **summary_metrics(summary),
            }
        )

    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(row)
    if set(by_method) != set(METHODS):
        raise RuntimeError("revealed method set is incomplete")
    if any(
        {row["seed"] for row in values} != set(SEEDS) for values in by_method.values()
    ):
        raise RuntimeError("one or more revealed methods lacks the E01--E20 product")

    method_summaries = {
        method: {
            "method": method,
            "role": "candidate" if method == "sche_nash" else "frozen_baseline",
            "metrics": {
                metric: metric_summary(by_method[method], metric) for metric in METRICS
            },
        }
        for method in METHODS
    }
    rankings = {
        metric: sorted(
            (
                {
                    "rank": 0,
                    "method": method,
                    "mean": method_summaries[method]["metrics"][metric]["mean"],
                    "n_finite": method_summaries[method]["metrics"][metric]["n_finite"],
                }
                for method in METHODS
            ),
            key=lambda item: (-item["mean"], METHODS.index(item["method"])),
        )
        for metric in METRICS
    }
    for metric in METRICS:
        for rank, item in enumerate(rankings[metric], start=1):
            item["rank"] = rank

    strict_mean_gates: dict[str, dict[str, Any]] = {}
    for metric in METRICS:
        candidate_mean = method_summaries["sche_nash"]["metrics"][metric]["mean"]
        best_baseline = max(
            BASELINES,
            key=lambda method: method_summaries[method]["metrics"][metric]["mean"],
        )
        best_baseline_mean = method_summaries[best_baseline]["metrics"][metric]["mean"]
        strict_mean_gates[metric] = {
            "candidate_mean": candidate_mean,
            "best_baseline_method": best_baseline,
            "best_baseline_mean": best_baseline_mean,
            "candidate_minus_best_baseline": candidate_mean - best_baseline_mean,
            "candidate_relative_change_vs_best_baseline": (
                (candidate_mean - best_baseline_mean) / best_baseline_mean
                if best_baseline_mean != 0.0
                else None
            ),
            "candidate_rank": next(
                item["rank"]
                for item in rankings[metric]
                if item["method"] == "sche_nash"
            ),
            "passed": candidate_mean > best_baseline_mean,
        }

    by_method_seed = {
        method: {row["seed"]: row for row in values}
        for method, values in by_method.items()
    }
    pairwise = {
        baseline: {
            metric: paired_comparison(
                by_method_seed["sche_nash"],
                by_method_seed[baseline],
                metric,
                bootstrap_seed=20260827
                + 100 * BASELINES.index(baseline)
                + METRICS.index(metric),
            )
            for metric in METRICS
        }
        for baseline in BASELINES
    }

    all_gates_pass = all(item["passed"] for item in strict_mean_gates.values())
    payload = {
        "schema_version": "NSE_FORMAL_E2_NSESCHE_OVERLAY_RESULT_V78",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "formal_target_cell_superiority_pass"
            if all_gates_pass
            else "formal_target_cell_superiority_fail"
        ),
        "formal_results_eligible": True,
        "metrics_revealed_exactly_once_after_blind_audit": True,
        "blind_audit_path": str(BLIND_AUDIT_PATH),
        "blind_audit_file_sha256": file_hash(BLIND_AUDIT_PATH),
        "blind_audit_hash": claimed_audit_hash,
        "manifest_path": str(MANIFEST_PATH),
        "manifest_file_sha256": file_hash(MANIFEST_PATH),
        "manifest_hash": manifest["manifest_hash"],
        "selection": overlay["selection"],
        "selected_profile": overlay["selected_profile"],
        "candidate_runtime": blind["candidate_runtime_consensus"],
        "frozen_baseline_runtime_values": blind["baseline_runtime_values"],
        "metric_definitions": {
            "throughput_requests_per_ms": "fixed-observation-window throughput in requests/ms",
            "qpr_finite_only": "per-run throughput/(drained-cohort mean latency * cost/completed request), mean over finite positive-completion runs",
            "qpr_zero_completed_as_zero": "the same per-run QPR with undefined/zero-completion runs assigned zero before the mean",
        },
        "method_summaries": method_summaries,
        "rankings": rankings,
        "strict_mean_gates": strict_mean_gates,
        "all_three_strict_mean_gates_pass": all_gates_pass,
        "pairwise_candidate_vs_each_baseline": pairwise,
        "raw_run_table": sorted(
            rows, key=lambda row: (METHODS.index(row["method"]), row["seed"])
        ),
        "decision": {
            "formal_target_cell_superiority_confirmed": all_gates_pass,
            "paired_intervals_overrode_gate": False,
            "seed_deletion_replacement_or_selective_rerun": False,
            "historical_nsesche_runs_used": False,
            "baseline_runs_reexecuted": False,
            "all_artifacts_retained": True,
            "next_action": (
                "freeze_V76_profile_for_additional_preregistered_formal_cells"
                if all_gates_pass
                else "retain_failure_and_stop_without_gate_relaxation"
            ),
        },
        "interpretation_boundary": {
            "claim_scope": "E2 low homogeneous n100 scale5 E01-E20 target cell",
            "all_E2_cells_or_loads_claimed": False,
            "single_runtime_binary_claimed": False,
            "confidence_intervals_are_gate_conditions": False,
        },
    }
    payload["result_hash"] = object_hash(payload)
    write_json_atomic(OUTPUT, payload)
    print(
        {
            "status": payload["status"],
            "all_gates_pass": all_gates_pass,
            "strict_mean_gates": strict_mean_gates,
            "rankings": {metric: rankings[metric][:3] for metric in METRICS},
            "output": str(OUTPUT),
            "file_sha256": file_hash(OUTPUT),
            "result_hash": payload["result_hash"],
        }
    )


if __name__ == "__main__":
    main()
