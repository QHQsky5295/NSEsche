from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_confirmation_plan_v94.json"
)
PLAN_SHA256 = "ba11cefa2af67a0347f126104922d3e94c501a9dce043965463719405a5cc90d"
TRAINING_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_training_result_v94.json"
)
TRAINING_RESULT_SHA256 = (
    "c4d82d46fbd5fa703322bbe4dc58aa744985d8489dad52f58aa54efa47daf2b1"
)
V88_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json"
)
V88_PLAN_SHA256 = "7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab"
BLIND_AUDIT = ROOT / "joint-blind-audit-v94-confirmation.json"
MANIFEST = ROOT / "manifest.v94-srpt-terminal-dual-confirmation.ready.json"
MANIFEST_FILE_SHA256 = (
    "256a8534de3121895760b28e5330093044e6ef0b85873ab7edecc4451e0d4e40"
)
MANIFEST_HASH = "f68d33b2d3a07e0fcb05337fd88983993d508a0d1fd58ebbceff552bbd0639db"
CANONICAL = ROOT / "runs/confirmation-v94/canonical"
OUTPUT = ROOT / "confirmation-result-v94.json"
EXPECTED_SEEDS = ("E723", "E724", "E725")
CLOSED_TRAINING_SEEDS = ("E720", "E721", "E722")
V93_RESERVED_SEEDS = ("E716", "E717", "E718")
EXPECTED_SCENARIOS = (
    "E3.spike5x50ms",
    "E3.sustained3x200ms",
    "E3.pulse4x4x50ms",
    "E4.steady",
)
EXPECTED_PROFILES = {
    "E3": "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto",
    "E4": (
        "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
        "srpt_ready_dual_window_safe_pareto"
    ),
}
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)


def _finite(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _scenario(run: dict) -> str:
    if run["experiment_id"] == "E3":
        return f"E3.{run['workload']['burst_name']}"
    if run["experiment_id"] == "E4":
        return "E4.steady"
    raise RuntimeError(f"unexpected experiment: {run['experiment_id']}")


def _summary_metrics(summary: dict) -> dict:
    fixed = summary.get("fixed_observation_window")
    latency = summary.get("latency_ms")
    if not isinstance(fixed, dict) or not isinstance(latency, dict):
        raise RuntimeError("summary lacks fixed-window or latency objects")
    completed = fixed.get("completed")
    throughput_rps = fixed.get("throughput_requests_per_second")
    latency_mean = latency.get("mean")
    cost = summary.get("simulator_internal_cost_per_completed_request")
    if not isinstance(completed, int) or isinstance(completed, bool) or completed < 0:
        raise RuntimeError("summary completed count is invalid")
    if not _finite(throughput_rps) or float(throughput_rps) < 0.0:
        raise RuntimeError("summary fixed-window throughput is invalid")
    throughput = float(throughput_rps) / 1000.0
    qpr_finite = None
    if (
        completed > 0
        and throughput > 0.0
        and _finite(latency_mean)
        and float(latency_mean) > 0.0
        and _finite(cost)
        and float(cost) > 0.0
    ):
        value = throughput / (float(latency_mean) * float(cost))
        if math.isfinite(value):
            qpr_finite = value
    return {
        "fixed_window_completed": completed,
        "throughput_requests_per_ms": throughput,
        "latency_mean_ms": float(latency_mean) if _finite(latency_mean) else None,
        "cost_per_completed_request": float(cost) if _finite(cost) else None,
        "qpr_finite_only": qpr_finite,
        "qpr_zero_completed_as_zero": 0.0 if qpr_finite is None else qpr_finite,
    }


def _load_rows() -> list[dict]:
    manifest = read_json(MANIFEST)
    if (
        manifest.get("manifest_hash") != MANIFEST_HASH
        or len(manifest.get("runs", [])) != 12
        or manifest.get("formal_results_eligible") is not True
    ):
        raise RuntimeError("ready manifest changed before reveal")
    rows = []
    for run in manifest["runs"]:
        run_id = run["run_id"]
        profile = EXPECTED_PROFILES.get(run["experiment_id"])
        metadata = run.get("metadata", {})
        if (
            run["seed"] not in EXPECTED_SEEDS
            or run["method"] != "sche_nash"
            or run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") != profile
            or metadata.get("v94_confirmation_plan_sha256") != PLAN_SHA256
            or metadata.get("v94_confirmation_only") is not True
            or metadata.get("v94_confirmation_metrics_previously_revealed") is not False
            or metadata.get("v94_training_rows_excluded") is not True
            or metadata.get("v94_v93_reserved_seeds_opened") is not False
            or metadata.get("v94_parent_complete_ready_frontier") is not True
            or metadata.get("v94_srpt_critical_path_player_order") is not True
            or metadata.get("v94_faithful_faasrank_initializer") is not True
            or metadata.get("v94_terminal_ocs_router") is not True
            or metadata.get("v94_dual_window_safe_pareto_guard") is not True
            or metadata.get("v94_idle_warm_dominance_router")
            is not (run["experiment_id"] == "E4")
        ):
            raise RuntimeError(f"candidate identity changed: {run_id}")
        summary_path = CANONICAL / run_id / "reviewer_records" / run_id / "summary.json"
        summary = read_json(summary_path)
        if summary.get("run_complete") is not True or summary.get("run_id") != run_id:
            raise RuntimeError(f"summary identity/completion mismatch: {run_id}")
        rows.append(
            {
                "profile": profile,
                "scenario_id": _scenario(run),
                "seed": run["seed"],
                "run_id": run_id,
                **_summary_metrics(summary),
                "summary_path": str(summary_path),
                "summary_file_sha256": file_hash(summary_path),
            }
        )
    return rows


def _aggregate(rows: list[dict], metric: str) -> dict:
    values = [float(row[metric]) for row in rows if _finite(row.get(metric))]
    mean = statistics.fmean(values) if len(values) == len(EXPECTED_SEEDS) else None
    return {
        "n_total": len(rows),
        "n_finite": len(values),
        "mean": mean,
        "sample_std": statistics.stdev(values) if len(values) >= 2 else None,
        "values_by_seed": {row["seed"]: row.get(metric) for row in rows},
    }


def _strict_gate(candidate: dict, baseline_max: dict) -> dict:
    gates = {}
    relative_margins = []
    for metric in METRICS:
        candidate_mean = candidate[metric]["mean"]
        comparator_mean = baseline_max[metric]["mean"]
        passed = (
            _finite(candidate_mean)
            and _finite(comparator_mean)
            and float(candidate_mean) > float(comparator_mean)
        )
        relative_margin = None
        if _finite(candidate_mean) and _finite(comparator_mean):
            if float(comparator_mean) > 0.0:
                relative_margin = (
                    float(candidate_mean) - float(comparator_mean)
                ) / float(comparator_mean)
            elif float(candidate_mean) > float(comparator_mean):
                relative_margin = math.inf
        gates[metric] = {
            "candidate_mean": candidate_mean,
            "maximum_baseline_mean": comparator_mean,
            "maximum_baseline_method": baseline_max[metric]["method"],
            "candidate_minus_maximum_baseline": (
                float(candidate_mean) - float(comparator_mean)
                if _finite(candidate_mean) and _finite(comparator_mean)
                else None
            ),
            "relative_margin": relative_margin,
            "strictly_greater": passed,
        }
        if passed and relative_margin is not None:
            relative_margins.append(relative_margin)
    all_pass = all(gates[metric]["strictly_greater"] for metric in METRICS)
    return {
        "gates": gates,
        "all_three_gates_pass": all_pass,
        "minimum_relative_margin": min(relative_margins) if all_pass else None,
    }


def _validate_blind_audit() -> dict:
    if not BLIND_AUDIT.is_file():
        raise RuntimeError("V94 confirmation blind audit is missing")
    blind = read_json(BLIND_AUDIT)
    payload = dict(blind)
    claimed_hash = payload.pop("audit_hash", None)
    if (
        not isinstance(claimed_hash, str)
        or object_hash(payload) != claimed_hash
        or blind.get("status") != "passed"
        or blind.get("plan_file_sha256") != PLAN_SHA256
        or blind.get("metrics_consulted") is not False
        or blind.get("scientific_summary_files_opened") != 0
        or blind.get("observed_online_runs") != 12
        or blind.get("observed_base_tape_captures") != 3
        or blind.get("observed_derived_burst_tapes") != 9
        or blind.get("observed_candidate_reference_builds") != 12
        or blind.get("new_baseline_online_runs") != 0
        or blind.get("attempt_one_required_and_observed") is not True
        or blind.get("zero_quarantine_required_and_observed") is not True
        or blind.get("training_rows_pooled") is not False
        or blind.get("V93_reserved_seeds_opened") is not False
        or blind.get("ready_manifest", {}).get("file_sha256") != MANIFEST_FILE_SHA256
        or blind.get("ready_manifest", {}).get("manifest_hash") != MANIFEST_HASH
    ):
        raise RuntimeError("V94 confirmation blind audit does not authorize reveal")
    return blind


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"V94 confirmation result already exists: {OUTPUT}")
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (TRAINING_RESULT, TRAINING_RESULT_SHA256),
        (V88_PLAN, V88_PLAN_SHA256),
        (MANIFEST, MANIFEST_FILE_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(f"frozen reveal input changed: {path}")
    blind = _validate_blind_audit()
    frozen_plan = read_json(V88_PLAN)
    thresholds = frozen_plan["frozen_prior_evidence"]["frozen_maximum_baseline_means"]
    if set(thresholds) != set(EXPECTED_SCENARIOS):
        raise RuntimeError("frozen baseline scenario set changed")
    rows = _load_rows()
    if len(rows) != 12:
        raise RuntimeError("V94 confirmation row count differs from sealed plan")

    scenario_results = {}
    for scenario_id in EXPECTED_SCENARIOS:
        selected = [row for row in rows if row["scenario_id"] == scenario_id]
        if {row["seed"] for row in selected} != set(EXPECTED_SEEDS):
            raise RuntimeError(f"confirmation seed set mismatch: {scenario_id}")
        metrics = {metric: _aggregate(selected, metric) for metric in METRICS}
        scenario_results[scenario_id] = {
            "profile": sorted({row["profile"] for row in selected})[0],
            "maximum_frozen_V87_baseline_by_metric": thresholds[scenario_id],
            "metrics": metrics,
            **_strict_gate(metrics, thresholds[scenario_id]),
            "selection_rule": "single frozen candidate; independent confirmation",
        }

    all_pass = all(
        scenario_results[scenario]["all_three_gates_pass"]
        for scenario in EXPECTED_SCENARIOS
    )
    result = {
        "schema_version": "NSE_E3E4_SRPT_TERMINAL_DUAL_CONFIRMATION_RESULT_V94_V1",
        "created_at": utc_now(),
        "status": "confirmation_pass" if all_pass else "confirmation_fail",
        "formal_results_eligible": True,
        "operational_group_closure_eligible": all_pass,
        "metrics_revealed_exactly_once_after_joint_blind_audit": True,
        "joint_blind_audit_path": str(BLIND_AUDIT),
        "joint_blind_audit_file_sha256": file_hash(BLIND_AUDIT),
        "joint_blind_audit_hash": blind["audit_hash"],
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "training_result_path": str(TRAINING_RESULT),
        "training_result_file_sha256": TRAINING_RESULT_SHA256,
        "confirmation_seeds": list(EXPECTED_SEEDS),
        "closed_training_seeds": list(CLOSED_TRAINING_SEEDS),
        "sealed_V93_reserved_seeds": list(V93_RESERVED_SEEDS),
        "training_rows_pooled": False,
        "required_metrics": list(METRICS),
        "scenario_results": scenario_results,
        "passing_scenarios": [
            scenario
            for scenario in EXPECTED_SCENARIOS
            if scenario_results[scenario]["all_three_gates_pass"]
        ],
        "all_four_confirmation_gates_pass": all_pass,
        "revealed_rows": rows,
        "interpretation": (
            "Independent n=3 confirmation of the preregistered operational gate; "
            "training and confirmation are not pooled, and this is not represented "
            "as a high-powered population estimate."
        ),
        "decision": {
            "close_v94_operational_E3_E4_gate": all_pass,
            "authorize_opening_V93_E716_E718": False,
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "training_confirmation_pooling": False,
            "resource_scaling_reopened": False,
            "next_action": (
                "freeze V94 confirmation result and write immutable closure handoff"
                if all_pass
                else (
                    "retain E723-E725, report every failure, and close V94 without "
                    "further tuning or another confirmation attempt"
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
                "all_four_confirmation_gates_pass": all_pass,
                "passing_scenarios": result["passing_scenarios"],
                "training_rows_pooled": False,
                "V93_reserved_seeds_opened": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
