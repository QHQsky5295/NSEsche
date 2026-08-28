from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3e4_qpr_recovery_training_20260828_v95")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_qpr_recovery_training_plan_v95.json"
)
PLAN_FILE_SHA256 = "8d25706e4adda849e06b334eacd73117dd52b49797f1755e47ab8491844e545d"
BLIND_AUDIT = ROOT / "joint-blind-audit-v95-training.json"
BLIND_AUDIT_FILE_SHA256 = (
    "2f32e91fdc01e1bcb2e17ad6acbf6cec5061eaf65d05ecf40566218f5232d45c"
)
BLIND_AUDIT_HASH = "b10d7f3a7ad4689270f0aa0e74833d0bc785adca72f4ce05ee7404d3d59c5a32"
OUTPUT = ROOT / "training-result-v95.json"
EXPECTED_SEEDS = ("E726", "E727", "E728")
EXPECTED_CONFIRMATION_SEEDS = ("E729", "E730", "E731")
EXPECTED_SCENARIOS = (
    "E3.spike5x50ms",
    "E3.sustained3x200ms",
    "E3.pulse4x4x50ms",
    "E4.steady",
)
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)
CANDIDATES = {
    "v95a-hiku-load": {
        "E3_profile": "srpt_ready_hiku_load_faithful",
        "E4_profile": "srpt_ready_load_least_current_demand",
        "manifest_file_sha256": (
            "3ae2a49ef0378229dc2fa9ec607fdba64fe89e8d9233a7f71ba48efa1cc7f573"
        ),
        "manifest_hash": (
            "6c1ad31d2530a0da7a3628ca9b1b36cc7f81b523db5e5a24602aceeb21eb4c30"
        ),
    },
    "v95b-hiku2-ocs-faasrank-load": {
        "E3_profile": "srpt_ready_hiku2_ocs_borda",
        "E4_profile": "srpt_ready_faasrank_load_least_borda",
        "manifest_file_sha256": (
            "a807d40ef16be3bdbdbf2bceca4a75e8118c69c68e3800124eb6c6a229e3967e"
        ),
        "manifest_hash": (
            "2e4aef234c744148bdf911816f75f2f824841f021836b87f54e769c61b6734b3"
        ),
    },
    "v95c-hiku-ocs3-hiku2-ocs": {
        "E3_profile": "srpt_ready_hiku_ocs3_borda",
        "E4_profile": "srpt_ready_hiku2_ocs_borda",
        "manifest_file_sha256": (
            "1f73754d60ced526f9755930cb2ae6d209b5166339827ddd8ef4eba262006375"
        ),
        "manifest_hash": (
            "0831e1f5402891658b1d34baf14b528bfb78f23e3b8a8a26673965248316be31"
        ),
    },
}


def _finite(value: object) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _scenario(run: Mapping[str, Any]) -> str:
    if run.get("experiment_id") == "E3":
        return f"E3.{run['workload']['burst_name']}"
    if run.get("experiment_id") == "E4":
        return "E4.steady"
    raise ValueError(f"unexpected experiment: {run.get('experiment_id')}")


def summary_metrics(summary: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    fixed = summary.get("fixed_observation_window")
    latency = summary.get("latency_ms")
    if not isinstance(fixed, Mapping) or not isinstance(latency, Mapping):
        raise ValueError(f"summary lacks fixed-window or latency objects: {run_id}")
    completed = fixed.get("completed")
    throughput_rps = fixed.get("throughput_requests_per_second")
    latency_mean = latency.get("mean")
    cost = summary.get("simulator_internal_cost_per_completed_request")
    if not isinstance(completed, int) or isinstance(completed, bool) or completed < 0:
        raise ValueError(f"summary completed count is invalid: {run_id}")
    if not _finite(throughput_rps) or float(throughput_rps) < 0.0:
        raise ValueError(f"summary fixed-window throughput is invalid: {run_id}")
    throughput = float(throughput_rps) / 1000.0
    qpr_finite = None
    if completed > 0:
        if (
            not _finite(latency_mean)
            or float(latency_mean) <= 0.0
            or not _finite(cost)
            or float(cost) <= 0.0
        ):
            raise ValueError(
                f"positive-completion run lacks a finite QPR denominator: {run_id}"
            )
        qpr_finite = throughput / (float(latency_mean) * float(cost))
        if not math.isfinite(qpr_finite):
            raise ValueError(f"non-finite recomputed QPR: {run_id}")
    return {
        "fixed_window_completed": completed,
        "throughput_requests_per_ms": throughput,
        "latency_mean_ms": float(latency_mean) if _finite(latency_mean) else None,
        "cost_per_completed_request": float(cost) if _finite(cost) else None,
        "qpr_finite_only": qpr_finite,
        "qpr_zero_completed_as_zero": 0.0 if completed == 0 else qpr_finite,
    }


def _aggregate(rows: Sequence[Mapping[str, Any]], metric: str) -> dict[str, Any]:
    values = [row.get(metric) for row in rows]
    finite_values = [float(value) for value in values if _finite(value)]
    complete_cohort = len(rows) == len(EXPECTED_SEEDS)
    return {
        "n_total": len(rows),
        "n_finite": len(finite_values),
        "n_zero_completed": sum(row.get("fixed_window_completed") == 0 for row in rows),
        "complete_three_seed_cohort": complete_cohort,
        "mean": (
            statistics.fmean(finite_values)
            if complete_cohort and finite_values
            else None
        ),
        "sample_std": (
            statistics.stdev(finite_values)
            if complete_cohort and len(finite_values) >= 2
            else None
        ),
        "values_by_seed": {
            str(row["seed"]): row.get(metric)
            for row in sorted(rows, key=lambda item: str(item["seed"]))
        },
    }


def _metric_gate(aggregate: Mapping[str, Any], threshold: float) -> dict[str, Any]:
    mean = aggregate.get("mean")
    passed = (
        aggregate.get("complete_three_seed_cohort") is True
        and _finite(mean)
        and _finite(threshold)
        and float(mean) > float(threshold)
    )
    margin = float(mean) - float(threshold) if _finite(mean) else None
    relative = (
        margin / float(threshold) if margin is not None and threshold > 0 else None
    )
    return {
        "candidate_mean": mean,
        "frozen_formal_n20_maximum_baseline_mean": threshold,
        "candidate_minus_maximum_baseline": margin,
        "relative_margin": relative,
        "complete_three_seed_cohort": (
            aggregate.get("complete_three_seed_cohort") is True
        ),
        "strictly_greater": passed,
    }


def evaluate_training_rows(
    rows: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, Mapping[str, float]],
    *,
    candidate_profiles: Mapping[str, Mapping[str, str]] | None = None,
    expected_seeds: Sequence[str] = EXPECTED_SEEDS,
) -> dict[str, Any]:
    profiles = candidate_profiles or CANDIDATES
    expected_scenarios = set(EXPECTED_SCENARIOS)
    if set(thresholds) != expected_scenarios:
        raise ValueError("frozen threshold scenario set changed")
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    seen_run_ids: set[str] = set()
    for row in rows:
        run_id = str(row.get("run_id"))
        if run_id in seen_run_ids:
            raise ValueError(f"duplicate run_id: {run_id}")
        seen_run_ids.add(run_id)
        candidate_id = str(row.get("candidate_id"))
        scenario_id = str(row.get("scenario_id"))
        if candidate_id not in profiles or scenario_id not in expected_scenarios:
            raise ValueError(
                f"unexpected candidate/scenario: {candidate_id}/{scenario_id}"
            )
        grouped[(candidate_id, scenario_id)].append(row)
    expected_keys = {
        (candidate_id, scenario_id)
        for candidate_id in profiles
        for scenario_id in EXPECTED_SCENARIOS
    }
    if set(grouped) != expected_keys:
        raise ValueError(
            "candidate/scenario product mismatch: "
            f"missing={sorted(expected_keys-set(grouped))}, "
            f"extra={sorted(set(grouped)-expected_keys)}"
        )

    scenario_results: dict[str, dict[str, Any]] = {}
    dimension_scores: dict[str, dict[str, Any]] = {"E3": {}, "E4": {}}
    for candidate_id, candidate in profiles.items():
        scenario_results[candidate_id] = {}
        for scenario_id in EXPECTED_SCENARIOS:
            selected = sorted(
                grouped[(candidate_id, scenario_id)], key=lambda row: str(row["seed"])
            )
            if [str(row["seed"]) for row in selected] != sorted(expected_seeds):
                raise ValueError(f"seed set mismatch: {candidate_id}/{scenario_id}")
            metrics = {metric: _aggregate(selected, metric) for metric in METRICS}
            gates = {
                metric: _metric_gate(
                    metrics[metric], float(thresholds[scenario_id][metric])
                )
                for metric in METRICS
            }
            scenario_results[candidate_id][scenario_id] = {
                "profile": candidate[
                    "E4_profile" if scenario_id == "E4.steady" else "E3_profile"
                ],
                "metrics": metrics,
                "gates": gates,
                "all_three_gates_pass": all(
                    gates[metric]["strictly_greater"] for metric in METRICS
                ),
            }

        for dimension, scenarios in {
            "E3": EXPECTED_SCENARIOS[:3],
            "E4": EXPECTED_SCENARIOS[3:],
        }.items():
            gates = [
                scenario_results[candidate_id][scenario_id]["gates"][metric]
                for scenario_id in scenarios
                for metric in METRICS
            ]
            passed = all(gate["strictly_greater"] for gate in gates)
            margins = [float(gate["relative_margin"]) for gate in gates if passed]
            dimension_scores[dimension][candidate_id] = {
                "profile": candidate[f"{dimension}_profile"],
                "required_gate_count": 9 if dimension == "E3" else 3,
                "all_required_gates_pass": passed,
                "minimum_relative_margin": min(margins) if passed else None,
                "mean_relative_margin": statistics.fmean(margins) if passed else None,
            }

    winners: dict[str, dict[str, Any] | None] = {}
    rankings: dict[str, list[dict[str, Any]]] = {}
    for dimension in ("E3", "E4"):
        passers = [
            (candidate_id, score)
            for candidate_id, score in dimension_scores[dimension].items()
            if score["all_required_gates_pass"]
        ]
        ranked = sorted(
            passers,
            key=lambda item: (
                -float(item[1]["minimum_relative_margin"]),
                -float(item[1]["mean_relative_margin"]),
                item[0],
            ),
        )
        rankings[dimension] = [
            {"candidate_id": candidate_id, **score} for candidate_id, score in ranked
        ]
        winners[dimension] = rankings[dimension][0] if rankings[dimension] else None

    joint_pass = winners["E3"] is not None and winners["E4"] is not None
    return {
        "scenario_results": scenario_results,
        "dimension_scores": dimension_scores,
        "passing_candidate_rankings": rankings,
        "selected_profiles": winners,
        "joint_training_gate_pass": joint_pass,
    }


def _validate_blind_audit() -> dict[str, Any]:
    if not BLIND_AUDIT.is_file() or file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V95 blind audit is missing or changed")
    blind = read_json(BLIND_AUDIT)
    payload = dict(blind)
    claimed = payload.pop("audit_hash", None)
    if (
        claimed != BLIND_AUDIT_HASH
        or object_hash(payload) != claimed
        or blind.get("status") != "passed"
        or blind.get("plan_file_sha256") != PLAN_FILE_SHA256
        or blind.get("performance_results_consulted") is not False
        or blind.get("scientific_summary_files_parsed") != 0
        or blind.get("observed_candidate_pairs") != 3
        or blind.get("observed_online_runs") != 36
        or blind.get("observed_base_tape_captures") != 3
        or blind.get("observed_derived_burst_tapes") != 9
        or blind.get("observed_candidate_reference_builds") != 36
        or blind.get("new_baseline_online_runs") != 0
        or blind.get("attempt_one_required_and_observed") is not True
        or blind.get("zero_quarantine_required_and_observed") is not True
        or blind.get("confirmation_seeds_opened") is not False
        or blind.get("confirmation_artifacts_observed") != 0
        or blind.get("reveal_authorized") is not True
    ):
        raise RuntimeError("V95 blind audit does not authorize reveal")
    for candidate_id, expected in CANDIDATES.items():
        admitted = (
            blind.get("groups", {}).get(candidate_id, {}).get("ready_manifest", {})
        )
        if (
            admitted.get("file_sha256") != expected["manifest_file_sha256"]
            or admitted.get("manifest_hash") != expected["manifest_hash"]
            or admitted.get("run_count") != 12
        ):
            raise RuntimeError(
                f"V95 blind audit candidate binding changed: {candidate_id}"
            )
    return blind


def _load_rows(blind: Mapping[str, Any]) -> list[dict[str, Any]]:
    admitted_results = {
        item["run_id"]: item["result_sha256"] for item in blind["run_evidence"]
    }
    if len(admitted_results) != 36:
        raise RuntimeError("blind audit run evidence is incomplete")
    rows = []
    for candidate_id, expected in CANDIDATES.items():
        manifest_path = ROOT / f"manifest.{candidate_id}.ready.json"
        if (
            not manifest_path.is_file()
            or file_hash(manifest_path) != expected["manifest_file_sha256"]
        ):
            raise RuntimeError(f"frozen candidate manifest changed: {candidate_id}")
        manifest = load_and_validate_manifest(manifest_path)
        if manifest.get("manifest_hash") != expected["manifest_hash"]:
            raise RuntimeError(f"candidate manifest hash changed: {candidate_id}")
        for run in manifest["runs"]:
            run_id = run["run_id"]
            experiment_id = run["experiment_id"]
            profile = expected[f"{experiment_id}_profile"]
            metadata = run.get("metadata", {})
            if (
                run["seed"] not in EXPECTED_SEEDS
                or run["method"] != "sche_nash"
                or run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") != profile
                or metadata.get("v95_training_plan_sha256") != PLAN_FILE_SHA256
                or metadata.get("v95_training_only") is not True
                or metadata.get("v95_training_seed_metrics_previously_revealed")
                is not False
                or metadata.get("v95_confirmation_seeds_opened") is not False
                or metadata.get("v95_candidate_id") != candidate_id
                or metadata.get("v95_candidate_profile") != profile
            ):
                raise RuntimeError(f"candidate identity changed: {run_id}")
            summary_path = (
                ROOT
                / "runs"
                / candidate_id
                / "canonical"
                / run_id
                / "reviewer_records"
                / run_id
                / "summary.json"
            )
            if not summary_path.is_file() or file_hash(
                summary_path
            ) != admitted_results.get(run_id):
                raise RuntimeError(f"summary differs from blind audit: {run_id}")
            summary = read_json(summary_path)
            if (
                summary.get("run_complete") is not True
                or summary.get("run_id") != run_id
            ):
                raise RuntimeError(f"summary identity/completion mismatch: {run_id}")
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "profile": profile,
                    "scenario_id": _scenario(run),
                    "seed": run["seed"],
                    "run_id": run_id,
                    **summary_metrics(summary, run_id),
                    "summary_path": str(summary_path),
                    "summary_file_sha256": admitted_results[run_id],
                }
            )
    return rows


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"V95 training result already exists: {OUTPUT}")
    if not PLAN.is_file() or file_hash(PLAN) != PLAN_FILE_SHA256:
        raise RuntimeError("frozen V95 plan changed before reveal")
    plan = read_json(PLAN)
    blind = _validate_blind_audit()
    thresholds = plan["frozen_formal_n20_maximum_baseline_means"]
    rows = _load_rows(blind)
    if len(rows) != 36:
        raise RuntimeError("V95 revealed row count differs from sealed plan")
    evaluation = evaluate_training_rows(rows, thresholds)
    joint_pass = evaluation["joint_training_gate_pass"]
    result = {
        "schema_version": "NSE_E3E4_QPR_RECOVERY_TRAINING_RESULT_V95_V1",
        "created_at": utc_now(),
        "status": "training_pass" if joint_pass else "training_fail",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_seeds_may_never_close_a_paper_group": True,
        "metrics_revealed_exactly_once_after_joint_blind_audit": True,
        "joint_blind_audit_path": str(BLIND_AUDIT),
        "joint_blind_audit_file_sha256": BLIND_AUDIT_FILE_SHA256,
        "joint_blind_audit_hash": BLIND_AUDIT_HASH,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_FILE_SHA256,
        "training_seeds": list(EXPECTED_SEEDS),
        "untouched_confirmation_seeds": list(EXPECTED_CONFIRMATION_SEEDS),
        "required_metrics": list(METRICS),
        "selection_rule": {
            "E3": "pass all nine E3 scenario-by-metric gates",
            "E4": "pass all three E4 metric gates",
            "multiple_passers": (
                "largest minimum relative margin, then largest mean relative margin, "
                "then lexicographically smallest candidate_id"
            ),
            "strict_ties_to_baseline_fail": True,
            "independent_E3_E4_selection": True,
        },
        "metric_definitions": {
            "throughput_requests_per_ms": (
                "per-run fixed-observation-window completed requests divided by 1000 ms"
            ),
            "qpr_finite_only": (
                "per-run QPR=throughput/(cost*latency) for completed>0; all three "
                "training values must be finite for this training gate"
            ),
            "qpr_zero_completed_as_zero": (
                "same per-run QPR, with exactly zero-completion runs contributing 0; "
                "positive-completion invalid denominators fail closed"
            ),
        },
        "frozen_formal_n20_maximum_baseline_means": thresholds,
        **evaluation,
        "revealed_rows": rows,
        "decision": {
            "authorize_v95_confirmation_on_E729_E731": joint_pass,
            "authorize_formal_E3_E4": False,
            "close_any_paper_group_from_training": False,
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "formal_E01_E20_rerun": False,
            "next_action": (
                "freeze selected E3/E4 mapping and preregister exactly E729-E731"
                if joint_pass
                else (
                    "freeze the complete V95 training cohort, keep E729-E731 sealed, "
                    "and return to mechanism diagnosis"
                )
            ),
        },
    }
    result["result_hash"] = object_hash(result)
    write_json_atomic(OUTPUT, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(OUTPUT),
                "file_sha256": file_hash(OUTPUT),
                "result_hash": result["result_hash"],
                "selected_profiles": result["selected_profiles"],
                "joint_training_gate_pass": joint_pass,
                "confirmation_authorized": joint_pass,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
