from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_blind_audit_v149 import (
    OUTPUT_NAME as BLIND_AUDIT_NAME,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_prepare_v149 import (
    AMENDMENT_SHA256,
    LOADS,
    PLAN_SHA256,
    ROOT,
    SEEDS,
    SOURCE_RUNS,
    SOURCE_RUNS_SHA256,
    paths,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


OUTPUT_NAME = "training-result-v149.json"
BASELINE_LABELS = {
    "Greedy",
    "Random",
    "Hash",
    "Load Balance",
    "FaaSRank",
    "OCS",
    "Hiku",
    "Jiagu",
    "Orion",
}
COMPARATORS = {
    "low": {"throughput": "Orion", "qpr": "OCS"},
    "middle": {"throughput": "FaaSRank", "qpr": "FaaSRank"},
    "high": {"throughput": "Jiagu", "qpr": "Jiagu"},
}


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _metrics(
    throughput: Any, latency: Any, cost: Any, completed: Any
) -> dict[str, float | None]:
    throughput_value = _float(throughput)
    latency_value = _float(latency)
    cost_value = _float(cost)
    completed_value = _float(completed)
    finite_qpr = None
    if (
        throughput_value is not None
        and throughput_value >= 0.0
        and latency_value is not None
        and latency_value > 0.0
        and cost_value is not None
        and cost_value > 0.0
    ):
        finite_qpr = throughput_value / (latency_value * cost_value)
    zero_qpr = 0.0 if completed_value == 0.0 else finite_qpr
    return {
        "throughput": throughput_value,
        "qpr_finite_only": finite_qpr,
        "qpr_zero_completed_as_zero": zero_qpr,
    }


def _load_baselines() -> list[dict[str, Any]]:
    if not SOURCE_RUNS.is_file() or file_hash(SOURCE_RUNS) != SOURCE_RUNS_SHA256:
        raise RuntimeError("frozen E1 baseline rows are missing or changed")
    rows = []
    with SOURCE_RUNS.open("r", encoding="utf-8-sig", newline="") as stream:
        for raw in csv.DictReader(stream):
            if raw.get("algorithm") not in BASELINE_LABELS:
                continue
            metric = _metrics(
                raw.get("throughput"),
                raw.get("latency"),
                raw.get("cost"),
                raw.get("completed"),
            )
            rows.append(
                {
                    "load": raw["load"],
                    "seed": raw["seed"],
                    "algorithm": raw["algorithm"],
                    **metric,
                }
            )
    expected = {
        (load, seed, algorithm)
        for load in LOADS
        for seed in SEEDS
        for algorithm in BASELINE_LABELS
    }
    if (
        len(rows) != 540
        or {(row["load"], row["seed"], row["algorithm"]) for row in rows} != expected
    ):
        raise RuntimeError("frozen nine-baseline E1 product changed")
    return rows


def _load_candidate(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for run in manifest["runs"]:
        summary_path = (
            paths()["workspace"]
            / "canonical"
            / run["run_id"]
            / "reviewer_records"
            / run["run_id"]
            / "summary.json"
        )
        summary = read_json(summary_path)
        values = _nse_summary_metrics(summary)
        rows.append(
            {
                "load": run["workload"]["request_freq"],
                "seed": run["seed"],
                "run_id": run["run_id"],
                **_metrics(
                    values.get("throughput"),
                    values.get("latency_mean_ms"),
                    values.get("cost"),
                    values.get("completed"),
                ),
            }
        )
    expected = {(load, seed) for load in LOADS for seed in SEEDS}
    if len(rows) != 60 or {(row["load"], row["seed"]) for row in rows} != expected:
        raise RuntimeError("V149 candidate result product changed")
    return rows


def _mean(rows: Sequence[Mapping[str, Any]], metric: str) -> tuple[float | None, int]:
    values = [row.get(metric) for row in rows]
    finite = [float(value) for value in values if _float(value) is not None]
    return (statistics.fmean(finite), len(finite)) if finite else (None, 0)


def _evaluate_load(
    load: str,
    candidate: list[dict[str, Any]],
    baselines: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_load = [row for row in candidate if row["load"] == load]
    baseline_load = [row for row in baselines if row["load"] == load]
    baseline_by_algorithm = {
        algorithm: [row for row in baseline_load if row["algorithm"] == algorithm]
        for algorithm in sorted(BASELINE_LABELS)
    }
    metrics = ("throughput", "qpr_finite_only", "qpr_zero_completed_as_zero")
    gates = {}
    for metric in metrics:
        candidate_mean, candidate_n = _mean(candidate_load, metric)
        baseline_means = {}
        for algorithm, rows in baseline_by_algorithm.items():
            mean, n = _mean(rows, metric)
            baseline_means[algorithm] = {"mean": mean, "n_finite": n}
        finite_baselines = {
            algorithm: payload["mean"]
            for algorithm, payload in baseline_means.items()
            if payload["mean"] is not None
        }
        ceiling_algorithm = max(finite_baselines, key=finite_baselines.get)
        ceiling_mean = finite_baselines[ceiling_algorithm]
        preregistered = COMPARATORS[load][
            "throughput" if metric == "throughput" else "qpr"
        ]
        if ceiling_algorithm != preregistered:
            raise RuntimeError(
                f"frozen {load}/{metric} ceiling identity changed: {ceiling_algorithm}"
            )
        candidate_by_seed = {row["seed"]: row for row in candidate_load}
        comparator_by_seed = {
            row["seed"]: row for row in baseline_by_algorithm[preregistered]
        }
        paired = []
        for seed in SEEDS:
            left = _float(candidate_by_seed[seed].get(metric))
            right = _float(comparator_by_seed[seed].get(metric))
            if left is not None and right is not None:
                paired.append(
                    {
                        "seed": seed,
                        "candidate": left,
                        "comparator": right,
                        "difference": left - right,
                    }
                )
        wins = sum(item["difference"] > 0.0 for item in paired)
        finite_complete = metric != "qpr_finite_only" or candidate_n == 20
        mean_pass = (
            candidate_mean is not None
            and candidate_mean > ceiling_mean
            and finite_complete
        )
        paired_pass = wins >= 12 and finite_complete
        gates[metric] = {
            "candidate_mean": candidate_mean,
            "candidate_n_finite": candidate_n,
            "baseline_means": baseline_means,
            "ceiling_algorithm": ceiling_algorithm,
            "ceiling_mean": ceiling_mean,
            "mean_difference": (
                None if candidate_mean is None else candidate_mean - ceiling_mean
            ),
            "mean_gate_pass": mean_pass,
            "paired_comparator": preregistered,
            "paired_n": len(paired),
            "paired_positive_wins": wins,
            "paired_gate_pass": paired_pass,
            "candidate_finite_qpr_all20_required": metric == "qpr_finite_only",
            "candidate_finite_qpr_all20_pass": finite_complete,
            "gate_pass": mean_pass and paired_pass,
            "paired_rows": paired,
        }
    return {
        "load": load,
        "candidate_run_count": len(candidate_load),
        "gates": gates,
        "all_three_metric_gates_pass": all(
            payload["gate_pass"] for payload in gates.values()
        ),
    }


def execute_reveal(root: Path = ROOT) -> dict[str, Any]:
    output = root / OUTPUT_NAME
    if output.exists():
        raise RuntimeError(f"V149 training result already exists: {output}")
    blind_path = root / BLIND_AUDIT_NAME
    blind = read_json(blind_path)
    payload = dict(blind)
    blind_hash = payload.pop("blind_audit_hash", None)
    if (
        not isinstance(blind_hash, str)
        or object_hash(payload) != blind_hash
        or blind.get("status") != "pass"
        or blind.get("performance_reveal_authorized") is not True
        or blind.get("throughput_completion_latency_cost_qpr_fields_parsed") != 0
    ):
        raise RuntimeError(
            "V149 blind audit is absent, changed, or did not authorize reveal"
        )
    manifest = load_and_validate_manifest(paths(root)["ready"])
    candidate = _load_candidate(manifest)
    baselines = _load_baselines()
    loads = [_evaluate_load(load, candidate, baselines) for load in LOADS]
    passed = all(item["all_three_metric_gates_pass"] for item in loads)
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAUSAL_NATIVE_EXPERT_CLOSURE_TRAINING_RESULT_V149_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "amendment_sha256": AMENDMENT_SHA256,
        "blind_audit_path": str(blind_path),
        "blind_audit_file_sha256": file_hash(blind_path),
        "blind_audit_hash": blind_hash,
        "candidate_run_count": len(candidate),
        "reused_frozen_baseline_run_count": len(baselines),
        "baseline_rerun_count": 0,
        "loads": loads,
        "all_nine_training_gates_pass": passed,
        "disposition": (
            "training_pass_requires_separate_confirmation_plan_and_unopened_inputs"
            if passed
            else "retire_v149_unchanged_no_confirmation_inputs_generated"
        ),
        "confirmation_inputs_generated": False,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output, document)
    return document


def main() -> None:
    document = execute_reveal()
    print(
        json.dumps(
            {
                "result_hash": document["result_hash"],
                "all_nine_training_gates_pass": document[
                    "all_nine_training_gates_pass"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
