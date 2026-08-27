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


ROOT = Path("tmp/nse_e3e4_operational_dev_20260827_v88")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json"
)
PLAN_SHA256 = "7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab"
BLIND_AUDIT = ROOT / "joint-blind-audit-v88.json"
BLIND_AUDIT_FILE_SHA256 = (
    "2af2aeb12ff7a0e625782e71ef370297891adbeae106a32f258e452087ce08f0"
)
BLIND_AUDIT_HASH = "b4a03762938566f46bca9ddfe28f10b45d96ae6ea079ec8c28c669687cd276d7"
MANIFEST = ROOT / "manifest.v88-pipeline-terminal-ocs.ready.json"
CANONICAL = ROOT / "runs/candidate-v88/canonical"
OUTPUT = ROOT / "selection-result-v88.json"
CANDIDATE_ID = "NSESche-E3E4-pipeline-terminal-OCS-V88"
CANDIDATE_PROFILE = (
    "faasrank_native_faithful_pipeline_terminal_ocs_dual_window_safe_pareto"
)
EXPECTED_SEEDS = ("E713", "E714", "E715")
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
        raise RuntimeError("V88 ready manifest no longer has exactly 12 runs")
    rows = []
    for run in manifest["runs"]:
        run_id = run["run_id"]
        summary_path = CANONICAL / run_id / "reviewer_records" / run_id / "summary.json"
        summary = read_json(summary_path)
        if summary.get("run_complete") is not True or summary.get("run_id") != run_id:
            raise RuntimeError(f"summary identity/completion mismatch: {run_id}")
        rows.append(
            {
                "candidate_id": CANDIDATE_ID,
                "profile": CANDIDATE_PROFILE,
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
        raise RuntimeError(f"V88 selection result already exists: {OUTPUT}")
    if file_hash(PLAN) != PLAN_SHA256:
        raise RuntimeError("V88 plan changed before reveal")
    if file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V88 joint blind audit changed before reveal")
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
        or blind.get("frozen_baseline_online_runs_reused") != 60
        or blind.get("new_baseline_online_runs") != 0
        or blind.get("attempt_one_required_and_observed") is not True
        or blind.get("zero_quarantine_required_and_observed") is not True
    ):
        raise RuntimeError("V88 joint blind audit does not authorize reveal")

    plan = read_json(PLAN)
    baseline_thresholds = plan["frozen_prior_evidence"]["frozen_maximum_baseline_means"]
    if set(baseline_thresholds) != set(EXPECTED_SCENARIOS):
        raise RuntimeError("V88 plan baseline scenario set changed")
    rows = _load_rows()
    if len(rows) != 12:
        raise RuntimeError("V88 revealed row count differs from the sealed plan")

    scenario_results = {}
    for scenario_id in EXPECTED_SCENARIOS:
        selected = [row for row in rows if row["scenario_id"] == scenario_id]
        if {row["seed"] for row in selected} != set(EXPECTED_SEEDS):
            raise RuntimeError(f"candidate seed set mismatch: {scenario_id}")
        metrics = {metric: _aggregate(selected, metric) for metric in METRICS}
        baseline_max = baseline_thresholds[scenario_id]
        scenario_results[scenario_id] = {
            "maximum_frozen_V87_baseline_by_metric": baseline_max,
            "candidate": {
                "candidate_id": CANDIDATE_ID,
                "profile": CANDIDATE_PROFILE,
                "metrics": metrics,
                **_strict_gate(metrics, baseline_max),
            },
        }
        scenario_results[scenario_id]["scenario_gate_pass"] = scenario_results[
            scenario_id
        ]["candidate"]["all_three_gates_pass"]
        scenario_results[scenario_id]["frozen_NSESche_scenario_name"] = (
            (
                "NSESche-E3-burst-"
                + scenario_id.removeprefix("E3.")
                + "-20node-heterogeneous-balanced"
            )
            if scenario_results[scenario_id]["scenario_gate_pass"]
            and scenario_id.startswith("E3.")
            else (
                "NSESche-E4-steady-20node-heterogeneous-balanced"
                if scenario_results[scenario_id]["scenario_gate_pass"]
                else None
            )
        )

    all_scenarios_pass = all(
        scenario_results[scenario]["scenario_gate_pass"]
        for scenario in EXPECTED_SCENARIOS
    )
    passing_scenarios = [
        scenario
        for scenario in EXPECTED_SCENARIOS
        if scenario_results[scenario]["scenario_gate_pass"]
    ]
    payload = {
        "schema_version": "NSE_E3E4_OPERATIONAL_DEVELOPMENT_RESULT_V88",
        "created_at": utc_now(),
        "status": (
            "operational_development_pass"
            if all_scenarios_pass
            else "operational_development_fail"
        ),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": all_scenarios_pass,
        "metrics_revealed_exactly_once_after_joint_blind_audit": True,
        "joint_blind_audit_path": str(BLIND_AUDIT),
        "joint_blind_audit_file_sha256": file_hash(BLIND_AUDIT),
        "joint_blind_audit_hash": blind["audit_hash"],
        "plan_path": str(PLAN),
        "plan_file_sha256": file_hash(PLAN),
        "development_seeds": list(EXPECTED_SEEDS),
        "required_metrics": list(METRICS),
        "scenario_results": scenario_results,
        "passing_scenarios": passing_scenarios,
        "all_four_scenario_gates_pass": all_scenarios_pass,
        "decision": {
            "freeze_passing_scenarios_under_descriptive_names": bool(passing_scenarios),
            "authorize_formal_E3_E4": all_scenarios_pass,
            "reason": (
                "NSESche strictly exceeds every frozen V87 advanced-baseline maximum mean on throughput and both QPR conventions in all four scenarios"
                if all_scenarios_pass
                else "one or more E3/E4 scenarios fails at least one strict throughput/QPR gate"
            ),
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "V87_and_V88_evidence_retained": True,
            "resource_scaling_reopened": False,
            "next_action": (
                "bind this profile for formal E3/E4 without rerunning baselines"
                if all_scenarios_pass
                else "retain V88, diagnose the complete four-scenario pattern, and preregister one bounded mechanism on untouched E716-E718"
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
                "all_four_scenario_gates_pass": all_scenarios_pass,
                "passing_scenarios": passing_scenarios,
                "output": str(OUTPUT),
                "file_sha256": file_hash(OUTPUT),
                "result_hash": payload["result_hash"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
