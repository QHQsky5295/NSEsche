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


ROOT = Path("tmp/nse_e3e4_native_expert_training_20260827_v89")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_native_expert_training_plan_v89.json"
)
PLAN_SHA256 = "e1397e0301e9d94558e281f2d363acd8b5098069ddf6ef558a24304b09f440ef"
BLIND_AUDIT = ROOT / "joint-blind-audit-v89-training.json"
BLIND_AUDIT_FILE_SHA256 = (
    "3e4843dfd259a1a69c524dcf4c5e2cb36b064c1088c6380eec83222d494de341"
)
BLIND_AUDIT_HASH = "dc2907e2850ec54fcc2f3e84946092544974691d29acbadfb63ec84407d1bcf1"
MANIFEST = ROOT / "manifest.v89-native-expert-training.ready.json"
CANONICAL = ROOT / "runs/training-v89/canonical"
OUTPUT = ROOT / "training-result-v89.json"
V88_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json"
)
V88_PLAN_SHA256 = "7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab"
CANDIDATE_ID = "NSESche-E3E4-native-expert-V89-training"
EXPECTED_SEEDS = ("E713", "E714", "E715")
EXPECTED_CONFIRMATION_SEEDS = ("E716", "E717", "E718")
EXPECTED_SCENARIOS = (
    "E3.spike5x50ms",
    "E3.sustained3x200ms",
    "E3.pulse4x4x50ms",
    "E4.steady",
)
EXPECTED_PROFILES = {
    "E3": "ocs_native_faithful_pipeline_dual_window_safe_pareto",
    "E4": "jiagu_native_faithful_window_safe_pareto",
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
    if len(manifest.get("runs", [])) != 12:
        raise RuntimeError("V89 training manifest no longer has exactly 12 runs")
    rows = []
    for run in manifest["runs"]:
        run_id = run["run_id"]
        profile = run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
        if profile != EXPECTED_PROFILES.get(run["experiment_id"]):
            raise RuntimeError(f"V89 profile mismatch: {run_id}")
        summary_path = CANONICAL / run_id / "reviewer_records" / run_id / "summary.json"
        summary = read_json(summary_path)
        if summary.get("run_complete") is not True or summary.get("run_id") != run_id:
            raise RuntimeError(f"summary identity/completion mismatch: {run_id}")
        rows.append(
            {
                "candidate_id": CANDIDATE_ID,
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


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"V89 training result already exists: {OUTPUT}")
    if file_hash(PLAN) != PLAN_SHA256:
        raise RuntimeError("V89 training plan changed before reveal")
    if file_hash(V88_PLAN) != V88_PLAN_SHA256:
        raise RuntimeError("frozen V88 threshold plan changed before reveal")
    if file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V89 training blind audit changed before reveal")
    blind = read_json(BLIND_AUDIT)
    blind_payload = dict(blind)
    claimed_audit_hash = blind_payload.pop("audit_hash", None)
    if (
        claimed_audit_hash != BLIND_AUDIT_HASH
        or object_hash(blind_payload) != claimed_audit_hash
        or blind.get("status") != "passed"
        or blind.get("metrics_consulted") is not False
        or blind.get("scientific_summary_files_opened") != 0
        or blind.get("observed_online_runs") != 12
        or blind.get("observed_candidate_reference_builds") != 12
        or blind.get("new_baseline_online_runs") != 0
        or blind.get("attempt_one_required_and_observed") is not True
        or blind.get("zero_quarantine_required_and_observed") is not True
        or blind.get("training_only") is not True
        or blind.get("confirmation_seeds_opened") is not False
    ):
        raise RuntimeError("V89 training blind audit does not authorize reveal")

    frozen_plan = read_json(V88_PLAN)
    baseline_thresholds = frozen_plan["frozen_prior_evidence"][
        "frozen_maximum_baseline_means"
    ]
    if set(baseline_thresholds) != set(EXPECTED_SCENARIOS):
        raise RuntimeError("V89 frozen baseline scenario set changed")
    rows = _load_rows()
    if len(rows) != 12:
        raise RuntimeError("V89 revealed row count differs from the sealed plan")

    scenario_results = {}
    for scenario_id in EXPECTED_SCENARIOS:
        selected = [row for row in rows if row["scenario_id"] == scenario_id]
        if {row["seed"] for row in selected} != set(EXPECTED_SEEDS):
            raise RuntimeError(f"training seed set mismatch: {scenario_id}")
        metrics = {metric: _aggregate(selected, metric) for metric in METRICS}
        baseline_max = baseline_thresholds[scenario_id]
        scenario_results[scenario_id] = {
            "maximum_frozen_V87_baseline_by_metric": baseline_max,
            "candidate": {
                "candidate_id": CANDIDATE_ID,
                "profiles": sorted({row["profile"] for row in selected}),
                "metrics": metrics,
                **_strict_gate(metrics, baseline_max),
            },
        }
        scenario_results[scenario_id]["training_gate_pass"] = scenario_results[
            scenario_id
        ]["candidate"]["all_three_gates_pass"]

    all_scenarios_pass = all(
        scenario_results[scenario]["training_gate_pass"]
        for scenario in EXPECTED_SCENARIOS
    )
    passing_scenarios = [
        scenario
        for scenario in EXPECTED_SCENARIOS
        if scenario_results[scenario]["training_gate_pass"]
    ]
    payload = {
        "schema_version": "NSE_E3E4_NATIVE_EXPERT_TRAINING_RESULT_V89_V1",
        "created_at": utc_now(),
        "status": "training_pass" if all_scenarios_pass else "training_fail",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_seeds_may_never_close_a_paper_group": True,
        "metrics_revealed_exactly_once_after_joint_blind_audit": True,
        "joint_blind_audit_path": str(BLIND_AUDIT),
        "joint_blind_audit_file_sha256": file_hash(BLIND_AUDIT),
        "joint_blind_audit_hash": blind["audit_hash"],
        "plan_path": str(PLAN),
        "plan_file_sha256": file_hash(PLAN),
        "training_seeds": list(EXPECTED_SEEDS),
        "untouched_confirmation_seeds": list(EXPECTED_CONFIRMATION_SEEDS),
        "required_metrics": list(METRICS),
        "scenario_results": scenario_results,
        "passing_scenarios": passing_scenarios,
        "all_four_training_gates_pass": all_scenarios_pass,
        "decision": {
            "authorize_v89_confirmation_on_E716_E718": all_scenarios_pass,
            "authorize_formal_E3_E4": False,
            "close_any_paper_group_from_training": False,
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "V87_V88_and_V89_training_evidence_retained": True,
            "resource_scaling_reopened": False,
            "next_action": (
                "freeze code and binary, preregister exactly E716-E718 without further tuning, and require a new result-blind confirmation audit"
                if all_scenarios_pass
                else "retain the complete failed training cohort and do not consume E716-E718"
            ),
        },
        "revealed_run_rows": rows,
    }
    payload["result_hash"] = object_hash(payload)
    write_json_atomic(OUTPUT, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "all_four_training_gates_pass": all_scenarios_pass,
                "passing_scenarios": passing_scenarios,
                "confirmation_authorized": all_scenarios_pass,
                "output": str(OUTPUT),
                "file_sha256": file_hash(OUTPUT),
                "result_hash": payload["result_hash"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
