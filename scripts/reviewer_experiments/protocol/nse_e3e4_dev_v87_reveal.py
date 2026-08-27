from __future__ import annotations

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


ROOT = Path("tmp/nse_e3e4_operational_dev_20260827_v87")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v87.json"
)
PLAN_SHA256 = "adde87a33762f68c019543054f9d40cb41ae3da4baa7aaaba96a708adff9e7e9"
BLIND_AUDIT = ROOT / "joint-blind-audit-v87.json"
BLIND_AUDIT_FILE_SHA256 = (
    "ecdc4cbaf29aa79e0b69bbf9894d01af3db9c2d22156f3726cb15fd6e951f728"
)
OUTPUT = ROOT / "selection-result-v87.json"
EXPECTED_SEEDS = ("E710", "E711", "E712")
EXPECTED_SCENARIOS = (
    "E3.spike5x50ms",
    "E3.sustained3x200ms",
    "E3.pulse4x4x50ms",
    "E4.steady",
)
BASELINE_METHODS = (
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
)
CANDIDATES = (
    "v87a-completion-pareto",
    "v87b-terminal-ocs",
    "v87c-idle-warm-dominance",
)
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)
ARMS = {
    "advanced_baselines": {
        "manifest": ROOT / "manifest.v87-advanced-baselines.model.json",
        "canonical": ROOT / "runs/advanced-baselines/canonical",
    },
    "v87a-completion-pareto": {
        "manifest": ROOT / "manifest.v87a-completion-pareto.ready.json",
        "canonical": ROOT / "runs/candidate-v87a/canonical",
    },
    "v87b-terminal-ocs": {
        "manifest": ROOT / "manifest.v87b-terminal-ocs.ready.json",
        "canonical": ROOT / "runs/candidate-v87b/canonical",
    },
    "v87c-idle-warm-dominance": {
        "manifest": ROOT / "manifest.v87c-idle-warm-dominance.ready.json",
        "canonical": ROOT / "runs/candidate-v87c/canonical",
    },
}


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
        candidate = throughput / (float(latency_mean) * float(cost))
        if math.isfinite(candidate):
            qpr_finite = candidate
    return {
        "fixed_window_completed": completed,
        "throughput_requests_per_ms": throughput,
        "latency_mean_ms": (float(latency_mean) if _finite(latency_mean) else None),
        "cost_per_completed_request": float(cost) if _finite(cost) else None,
        "qpr_finite_only": qpr_finite,
        "qpr_zero_completed_as_zero": 0.0 if qpr_finite is None else qpr_finite,
    }


def _load_rows(arm: str) -> list[dict]:
    manifest_path = ARMS[arm]["manifest"]
    manifest = read_json(manifest_path)
    rows = []
    for run in manifest["runs"]:
        run_id = run["run_id"]
        summary_path = (
            ARMS[arm]["canonical"]
            / run_id
            / "reviewer_records"
            / run_id
            / "summary.json"
        )
        summary = read_json(summary_path)
        if summary.get("run_complete") is not True or summary.get("run_id") != run_id:
            raise RuntimeError(f"summary identity/completion mismatch: {run_id}")
        rows.append(
            {
                "arm": arm,
                "method": run["method"],
                "variant": run["variant"],
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
        raise RuntimeError(f"V87 selection result already exists: {OUTPUT}")
    if file_hash(PLAN) != PLAN_SHA256:
        raise RuntimeError("V87 plan changed before reveal")
    if file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V87 joint blind audit changed before reveal")
    blind = read_json(BLIND_AUDIT)
    if (
        blind.get("status") != "passed"
        or blind.get("metrics_consulted") is not False
        or blind.get("scientific_summary_files_opened") != 0
        or blind.get("observed_online_runs") != 96
        or blind.get("observed_candidate_reference_builds") != 36
        or blind.get("attempt_one_required_and_observed") is not True
        or blind.get("zero_quarantine_required_and_observed") is not True
    ):
        raise RuntimeError("V87 joint blind audit does not authorize reveal")

    rows_by_arm = {arm: _load_rows(arm) for arm in ARMS}
    if len(rows_by_arm["advanced_baselines"]) != 60 or any(
        len(rows_by_arm[candidate]) != 12 for candidate in CANDIDATES
    ):
        raise RuntimeError("V87 revealed row count differs from the sealed plan")

    scenario_results = {}
    for scenario_id in EXPECTED_SCENARIOS:
        baseline_aggregates = {}
        for method in BASELINE_METHODS:
            selected = [
                row
                for row in rows_by_arm["advanced_baselines"]
                if row["scenario_id"] == scenario_id and row["method"] == method
            ]
            if {row["seed"] for row in selected} != set(EXPECTED_SEEDS):
                raise RuntimeError(
                    f"baseline seed set mismatch: {scenario_id}/{method}"
                )
            baseline_aggregates[method] = {
                metric: _aggregate(selected, metric) for metric in METRICS
            }
        baseline_max = {}
        for metric in METRICS:
            eligible = [
                (method, metrics[metric]["mean"])
                for method, metrics in baseline_aggregates.items()
                if _finite(metrics[metric]["mean"])
            ]
            if len(eligible) != len(BASELINE_METHODS):
                raise RuntimeError(f"nonfinite baseline mean: {scenario_id}/{metric}")
            method, value = max(eligible, key=lambda item: (float(item[1]), item[0]))
            baseline_max[metric] = {"method": method, "mean": float(value)}

        candidate_rows = {}
        for candidate_id in CANDIDATES:
            selected = [
                row
                for row in rows_by_arm[candidate_id]
                if row["scenario_id"] == scenario_id
            ]
            if {row["seed"] for row in selected} != set(EXPECTED_SEEDS):
                raise RuntimeError(
                    f"candidate seed set mismatch: {scenario_id}/{candidate_id}"
                )
            metrics = {metric: _aggregate(selected, metric) for metric in METRICS}
            candidate_rows[candidate_id] = {
                "metrics": metrics,
                **_strict_gate(metrics, baseline_max),
            }
        passers = [
            (candidate_id, result["minimum_relative_margin"])
            for candidate_id, result in candidate_rows.items()
            if result["all_three_gates_pass"]
        ]
        selected_candidate = None
        if passers:
            selected_candidate = sorted(
                passers,
                key=lambda item: (-float(item[1]), item[0]),
            )[0][0]
        scenario_results[scenario_id] = {
            "baseline_aggregates": baseline_aggregates,
            "maximum_baseline_by_metric": baseline_max,
            "candidates": candidate_rows,
            "passing_candidates": [item[0] for item in sorted(passers)],
            "selected_candidate": selected_candidate,
            "scenario_gate_pass": selected_candidate is not None,
        }

    all_scenarios_pass = all(
        scenario_results[scenario]["scenario_gate_pass"]
        for scenario in EXPECTED_SCENARIOS
    )
    payload = {
        "schema_version": "NSE_E3E4_OPERATIONAL_DEVELOPMENT_RESULT_V87",
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
        "selected_profile_by_scenario": {
            scenario: scenario_results[scenario]["selected_candidate"]
            for scenario in EXPECTED_SCENARIOS
        },
        "all_four_scenario_gates_pass": all_scenarios_pass,
        "decision": {
            "freeze_selected_profiles_for_formal_E3_E4": all_scenarios_pass,
            "reason": (
                "each_scenario_has_a_candidate_strictly_above_the_maximum_five_baseline_mean_on_throughput_and_both_qpr_conventions"
                if all_scenarios_pass
                else "one_or_more_scenarios_lacks_a_candidate_passing_all_three_strict_mean_gates"
            ),
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "failed_candidates_retained": True,
            "subgroup_switching_outside_preregistered_per_scenario_selection": False,
            "next_action": (
                "bind_selected_profile_per_scenario_then_build_formal_references"
                if all_scenarios_pass
                else "freeze_V87_evidence_and_preregister_one_new_bounded_NSESche_mechanism_on_E713_E715"
            ),
        },
        "revealed_run_rows": [row for arm in ARMS for row in rows_by_arm[arm]],
    }
    payload["result_hash"] = object_hash(payload)
    write_json_atomic(OUTPUT, payload)
    print(
        {
            "status": payload["status"],
            "all_four_scenario_gates_pass": all_scenarios_pass,
            "selected_profile_by_scenario": payload["selected_profile_by_scenario"],
            "output": str(OUTPUT),
            "file_sha256": file_hash(OUTPUT),
            "result_hash": payload["result_hash"],
        }
    )


if __name__ == "__main__":
    main()
