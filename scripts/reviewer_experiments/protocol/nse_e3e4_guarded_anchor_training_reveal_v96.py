from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3e4_guarded_anchor_training_20260828_v96")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_guarded_anchor_training_plan_v96.json"
)
PLAN_FILE_SHA256 = "5fc758ad2ce1a90aa26884d94d5338d4739277c9d75f12c0f37eaf07788747ab"
BLIND_AUDIT = ROOT / "joint-blind-audit-v96-training.json"
BLIND_AUDIT_FILE_SHA256 = (
    "660346dee18441a64adec11338b5875dc9789c10bec2631130875a2a0b49ffa7"
)
BLIND_AUDIT_HASH = "06b27f3f81ac22c1217b8ecc8ea0f238534c15aaa537a4d61c031260b28ae8b5"
OUTPUT = ROOT / "training-result-v96.json"
EXPECTED_SEEDS = ("E746", "E747", "E748")
EXPECTED_CONFIRMATION_SEEDS = tuple(f"E{index}" for index in range(766, 786))
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
ARMS = {
    "v96-e3-anchor": {
        "experiment_id": "E3",
        "role": "anchor",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_"
            "srpt_ready_dual_window_safe_pareto"
        ),
        "manifest_file_sha256": (
            "583833d44ed19f471620fea3d7e09f61cfef40198b9195b861a303195bd1672a"
        ),
        "manifest_hash": (
            "8b4a92f3cbc6d6acfc22ee43abe0dab204ecdbf981dbae7224958b35e19e5505"
        ),
    },
    "v96-e3-idle-warm-srpt": {
        "experiment_id": "E3",
        "role": "candidate",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "srpt_ready_dual_window_safe_pareto"
        ),
        "manifest_file_sha256": (
            "5df97f92a1e90f3b1bb8885b438071065613cfdde62e0b06b1ab61d6b191965a"
        ),
        "manifest_hash": (
            "515ac6007f58f2f6c4dbb4c3c4e4db275d683c0014d4d79a971d454dc40c9a36"
        ),
    },
    "v96-e3-idle-warm-no-srpt": {
        "experiment_id": "E3",
        "role": "candidate",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "dual_window_safe_pareto"
        ),
        "manifest_file_sha256": (
            "237bc1d5d7fcddcf723fecb1b17da88029a2b4e2178fb96a4df5af3404f9a2fc"
        ),
        "manifest_hash": (
            "94f89dd36125898debd8a430eccb938cb05a100b9ca05cd7db257a413959dc41"
        ),
    },
    "v96-e4-anchor": {
        "experiment_id": "E4",
        "role": "anchor",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "srpt_ready_dual_window_safe_pareto"
        ),
        "manifest_file_sha256": (
            "8d434beea2c1c1d89d1c3ee6eb81c18b7a41e9a1109d7daac6ec17f6764903d8"
        ),
        "manifest_hash": (
            "bed0eba71dc04206cdf402fa41d7fb4a9fd3288b6009a41bf486d9a0f2ba15a4"
        ),
    },
    "v96-e4-idle-warm-no-srpt": {
        "experiment_id": "E4",
        "role": "candidate",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "dual_window_safe_pareto"
        ),
        "manifest_file_sha256": (
            "61e715ac95b007e8c4923c02d7ab89564b396cdb67c1fc1bb2728f301f9a8e4b"
        ),
        "manifest_hash": (
            "66a050f9bc21b06626aef07858ca6c1e40236892afe6151d96f446eba108a88e"
        ),
    },
}
ANCHORS = {"E3": "v96-e3-anchor", "E4": "v96-e4-anchor"}


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
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
    complete = len(rows) == len(EXPECTED_SEEDS) and len(finite_values) == len(rows)
    return {
        "n_total": len(rows),
        "n_finite": len(finite_values),
        "n_zero_completed": sum(row.get("fixed_window_completed") == 0 for row in rows),
        "complete_three_seed_finite_cohort": complete,
        "mean": statistics.fmean(finite_values) if complete else None,
        "sample_std": statistics.stdev(finite_values) if complete else None,
        "values_by_seed": {
            str(row["seed"]): row.get(metric)
            for row in sorted(rows, key=lambda item: str(item["seed"]))
        },
    }


def _paired_gate(
    candidate_rows: Sequence[Mapping[str, Any]],
    anchor_rows: Sequence[Mapping[str, Any]],
    metric: str,
) -> dict[str, Any]:
    candidate = {str(row["seed"]): row.get(metric) for row in candidate_rows}
    anchor = {str(row["seed"]): row.get(metric) for row in anchor_rows}
    complete = (
        set(candidate) == set(EXPECTED_SEEDS)
        and set(anchor) == set(EXPECTED_SEEDS)
        and all(_finite(value) for value in candidate.values())
        and all(_finite(value) for value in anchor.values())
    )
    deltas = (
        {seed: float(candidate[seed]) - float(anchor[seed]) for seed in EXPECTED_SEEDS}
        if complete
        else {}
    )
    candidate_mean = (
        statistics.fmean(float(candidate[seed]) for seed in EXPECTED_SEEDS)
        if complete
        else None
    )
    anchor_mean = (
        statistics.fmean(float(anchor[seed]) for seed in EXPECTED_SEEDS)
        if complete
        else None
    )
    mean_delta = candidate_mean - anchor_mean if complete else None
    relative_mean_change = (
        mean_delta / anchor_mean
        if complete and anchor_mean is not None and anchor_mean > 0.0
        else None
    )
    if metric == "throughput_requests_per_ms":
        direction_count = sum(delta >= 0.0 for delta in deltas.values())
        mean_rule = complete and mean_delta is not None and mean_delta >= 0.0
        direction_rule = complete and direction_count >= 2
        rule = "mean_noninferior_and_at_least_two_of_three_nonnegative"
    else:
        direction_count = sum(delta > 0.0 for delta in deltas.values())
        mean_rule = complete and mean_delta is not None and mean_delta > 0.0
        direction_rule = complete and direction_count >= 2
        rule = "mean_strictly_greater_and_at_least_two_of_three_strictly_positive"
    return {
        "metric": metric,
        "complete_paired_finite_cohort": complete,
        "candidate_mean": candidate_mean,
        "anchor_mean": anchor_mean,
        "candidate_minus_anchor_mean": mean_delta,
        "relative_mean_change": relative_mean_change,
        "paired_deltas_by_seed": deltas,
        "direction_consistent_seed_count": direction_count,
        "mean_rule_pass": mean_rule,
        "direction_rule_pass": direction_rule,
        "rule": rule,
        "passed": mean_rule and direction_rule,
    }


def evaluate_training_rows(
    rows: Sequence[Mapping[str, Any]],
    absolute_thresholds: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for row in rows:
        run_id = str(row.get("run_id"))
        if run_id in seen_ids:
            raise ValueError(f"duplicate run_id: {run_id}")
        seen_ids.add(run_id)
        arm_id = str(row.get("arm_id"))
        scenario = str(row.get("scenario_id"))
        if arm_id not in ARMS or scenario not in EXPECTED_SCENARIOS:
            raise ValueError(f"unexpected arm/scenario: {arm_id}/{scenario}")
        grouped[(arm_id, scenario)].append(row)

    expected_keys = {
        (arm_id, scenario)
        for arm_id, arm in ARMS.items()
        for scenario in EXPECTED_SCENARIOS
        if scenario.startswith(arm["experiment_id"] + ".")
    }
    if set(grouped) != expected_keys:
        raise ValueError(
            "arm/scenario product mismatch: "
            f"missing={sorted(expected_keys-set(grouped))}, "
            f"extra={sorted(set(grouped)-expected_keys)}"
        )
    if set(absolute_thresholds) != set(EXPECTED_SCENARIOS):
        raise ValueError("absolute diagnostic threshold scenario set changed")

    aggregates: dict[str, dict[str, Any]] = {}
    for arm_id, arm in ARMS.items():
        aggregates[arm_id] = {}
        scenarios = [
            scenario
            for scenario in EXPECTED_SCENARIOS
            if scenario.startswith(arm["experiment_id"] + ".")
        ]
        for scenario in scenarios:
            selected = sorted(
                grouped[(arm_id, scenario)], key=lambda row: str(row["seed"])
            )
            if [str(row["seed"]) for row in selected] != sorted(EXPECTED_SEEDS):
                raise ValueError(f"seed set mismatch: {arm_id}/{scenario}")
            metric_values = {metric: _aggregate(selected, metric) for metric in METRICS}
            diagnostics = {}
            for metric in METRICS:
                mean = metric_values[metric]["mean"]
                threshold = float(absolute_thresholds[scenario][metric])
                diagnostics[metric] = {
                    "candidate_mean": mean,
                    "frozen_formal_n20_maximum_baseline_mean": threshold,
                    "candidate_minus_maximum_baseline": (
                        float(mean) - threshold if _finite(mean) else None
                    ),
                    "strictly_greater_diagnostic": (
                        _finite(mean) and float(mean) > threshold
                    ),
                    "used_for_V96_selection": False,
                }
            aggregates[arm_id][scenario] = {
                "profile": arm["profile"],
                "metrics": metric_values,
                "formal_absolute_diagnostics": diagnostics,
            }

    candidate_results: dict[str, dict[str, Any]] = {}
    dimension_scores: dict[str, dict[str, Any]] = {"E3": {}, "E4": {}}
    for arm_id, arm in ARMS.items():
        if arm["role"] != "candidate":
            continue
        dimension = arm["experiment_id"]
        anchor_id = ANCHORS[dimension]
        scenarios = [
            scenario
            for scenario in EXPECTED_SCENARIOS
            if scenario.startswith(dimension + ".")
        ]
        candidate_results[arm_id] = {}
        all_gates = []
        for scenario in scenarios:
            candidate_rows = grouped[(arm_id, scenario)]
            anchor_rows = grouped[(anchor_id, scenario)]
            gates = {
                metric: _paired_gate(candidate_rows, anchor_rows, metric)
                for metric in METRICS
            }
            scenario_pass = all(gate["passed"] for gate in gates.values())
            all_gates.extend(gates.values())
            candidate_results[arm_id][scenario] = {
                "anchor_arm_id": anchor_id,
                "gates": gates,
                "all_three_paired_gates_pass": scenario_pass,
            }
        arm_pass = all(gate["passed"] for gate in all_gates)
        qpr_changes = [
            float(gate["relative_mean_change"])
            for gate in all_gates
            if gate["metric"].startswith("qpr_")
            and _finite(gate["relative_mean_change"])
        ]
        throughput_changes = [
            float(gate["relative_mean_change"])
            for gate in all_gates
            if gate["metric"] == "throughput_requests_per_ms"
            and _finite(gate["relative_mean_change"])
        ]
        dimension_scores[dimension][arm_id] = {
            "profile": arm["profile"],
            "anchor_arm_id": anchor_id,
            "required_gate_count": len(all_gates),
            "all_required_gates_pass": arm_pass,
            "minimum_relative_mean_qpr_gain": min(qpr_changes) if arm_pass else None,
            "minimum_relative_mean_throughput_change": (
                min(throughput_changes) if arm_pass else None
            ),
        }

    rankings: dict[str, list[dict[str, Any]]] = {}
    winners: dict[str, dict[str, Any] | None] = {}
    for dimension in ("E3", "E4"):
        passers = [
            (arm_id, score)
            for arm_id, score in dimension_scores[dimension].items()
            if score["all_required_gates_pass"]
        ]
        ranked = sorted(
            passers,
            key=lambda item: (
                -float(item[1]["minimum_relative_mean_qpr_gain"]),
                -float(item[1]["minimum_relative_mean_throughput_change"]),
                item[0],
            ),
        )
        rankings[dimension] = [{"arm_id": arm_id, **score} for arm_id, score in ranked]
        winners[dimension] = rankings[dimension][0] if rankings[dimension] else None

    return {
        "arm_aggregates": aggregates,
        "paired_candidate_results": candidate_results,
        "dimension_scores": dimension_scores,
        "passing_candidate_rankings": rankings,
        "selected_profiles": winners,
        "joint_training_gate_pass": (
            winners["E3"] is not None and winners["E4"] is not None
        ),
    }


def _validate_blind_audit() -> dict[str, Any]:
    if not BLIND_AUDIT.is_file() or file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V96 blind audit is missing or changed")
    blind = read_json(BLIND_AUDIT)
    payload = dict(blind)
    claimed = payload.pop("audit_hash", None)
    if (
        claimed != BLIND_AUDIT_HASH
        or object_hash(payload) != claimed
        or blind.get("status") != "pass"
        or blind.get("plan_file_sha256") != PLAN_FILE_SHA256
        or blind.get("performance_results_consulted") is not False
        or blind.get("performance_summaries_parsed") != 0
        or blind.get("run_count") != 33
        or blind.get("reference_count") != 33
        or blind.get("tape_count") != 12
        or blind.get("confirmation_inputs_opened") is not False
        or blind.get("reveal_authorized") is not True
    ):
        raise RuntimeError("V96 blind audit does not authorize reveal")
    return blind


def _load_rows(blind: Mapping[str, Any]) -> list[dict[str, Any]]:
    admitted = {item["run_id"]: item["result_sha256"] for item in blind["runs"]}
    if len(admitted) != 33:
        raise RuntimeError("V96 blind audit run evidence is incomplete")
    rows = []
    for arm_id, expected in ARMS.items():
        manifest_path = ROOT / f"manifest.{arm_id}.ready.json"
        if (
            not manifest_path.is_file()
            or file_hash(manifest_path) != expected["manifest_file_sha256"]
        ):
            raise RuntimeError(f"V96 frozen manifest changed: {arm_id}")
        manifest = load_and_validate_manifest(manifest_path)
        if manifest.get("manifest_hash") != expected["manifest_hash"]:
            raise RuntimeError(f"V96 manifest hash changed: {arm_id}")
        for run in manifest["runs"]:
            metadata = run.get("metadata", {})
            if (
                run["seed"] not in EXPECTED_SEEDS
                or run["method"] != "sche_nash"
                or run["experiment_id"] != expected["experiment_id"]
                or run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
                != expected["profile"]
                or metadata.get("v96_training_plan_sha256") != PLAN_FILE_SHA256
                or metadata.get("v96_training_only") is not True
                or metadata.get("v96_training_seed_metrics_previously_revealed")
                is not False
                or metadata.get("v96_confirmation_seeds_opened") is not False
                or metadata.get("v96_arm_id") != arm_id
                or metadata.get("v96_arm_role") != expected["role"]
            ):
                raise RuntimeError(f"V96 arm identity changed: {run['run_id']}")
            run_id = run["run_id"]
            summary_path = (
                ROOT
                / "runs"
                / arm_id
                / "canonical"
                / run_id
                / "reviewer_records"
                / run_id
                / "summary.json"
            )
            if not summary_path.is_file() or file_hash(summary_path) != admitted.get(
                run_id
            ):
                raise RuntimeError(f"V96 summary differs from blind audit: {run_id}")
            summary = read_json(summary_path)
            if (
                summary.get("run_complete") is not True
                or summary.get("run_id") != run_id
            ):
                raise RuntimeError(
                    f"V96 summary identity/completion mismatch: {run_id}"
                )
            rows.append(
                {
                    "arm_id": arm_id,
                    "role": expected["role"],
                    "profile": expected["profile"],
                    "scenario_id": _scenario(run),
                    "seed": run["seed"],
                    "run_id": run_id,
                    **summary_metrics(summary, run_id),
                    "summary_path": str(summary_path),
                    "summary_file_sha256": admitted[run_id],
                }
            )
    return rows


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"V96 training result already exists: {OUTPUT}")
    if not PLAN.is_file() or file_hash(PLAN) != PLAN_FILE_SHA256:
        raise RuntimeError("frozen V96 plan changed before reveal")
    plan = read_json(PLAN)
    blind = _validate_blind_audit()
    rows = _load_rows(blind)
    if len(rows) != 33:
        raise RuntimeError("V96 revealed row count differs from sealed plan")
    thresholds = plan["frozen_formal_n20_maximum_baseline_means_for_diagnostics"]
    evaluation = evaluate_training_rows(rows, thresholds)
    joint_pass = evaluation["joint_training_gate_pass"]
    result = {
        "schema_version": "NSE_E3E4_GUARDED_ANCHOR_TRAINING_RESULT_V96_V1",
        "created_at": utc_now(),
        "status": "training_pass" if joint_pass else "training_fail",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_rows_may_never_close_a_paper_group": True,
        "metrics_revealed_exactly_once_after_joint_blind_audit": True,
        "joint_blind_audit_path": str(BLIND_AUDIT),
        "joint_blind_audit_file_sha256": BLIND_AUDIT_FILE_SHA256,
        "joint_blind_audit_hash": BLIND_AUDIT_HASH,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_FILE_SHA256,
        "training_seeds": list(EXPECTED_SEEDS),
        "untouched_confirmation_seeds": list(EXPECTED_CONFIRMATION_SEEDS),
        "selection_metrics": list(METRICS),
        "selection_rule": {
            "throughput": (
                "candidate mean >= paired anchor mean and at least two of three "
                "paired seed deltas >= 0 in every scenario"
            ),
            "each_qpr_convention": (
                "candidate mean > paired anchor mean and at least two of three "
                "paired seed deltas > 0 in every scenario"
            ),
            "E3": "pass all nine paired scenario-by-metric gates",
            "E4": "pass all three paired steady gates",
            "formal_absolute_gates_used_for_selection": False,
        },
        "frozen_formal_n20_maximum_baseline_means_for_diagnostics": thresholds,
        **evaluation,
        "revealed_rows": rows,
        "decision": {
            "authorize_preregistration_of_E766_E785_confirmation": joint_pass,
            "authorize_generation_of_confirmation_inputs_now": False,
            "authorize_formal_all_method_E3_E4": False,
            "close_any_paper_group_from_training": False,
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "formal_E01_E20_rerun": False,
            "next_action": (
                "freeze the selected E3/E4 profiles and preregister the complete "
                "E766-E785 NSESche confirmation before generating those inputs"
                if joint_pass
                else (
                    "freeze the complete V96 training cohort, keep E766-E785 "
                    "untouched, and return to guarded-mechanism diagnosis"
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
                "confirmation_preregistration_authorized": joint_pass,
                "confirmation_inputs_generated": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
