from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_reveal_v100 import (
    _finite,
    summary_metrics,
)
from scripts.reviewer_experiments.protocol.nse_e3_load_initializer_certificate_factorial_training_blind_audit_v102 import (
    ARMS,
    OUTPUT as BLIND_AUDIT,
)
from scripts.reviewer_experiments.protocol.nse_e3_load_initializer_certificate_factorial_training_prepare_v102 import (
    CONFIRMATION_SEEDS,
    FORMAL_RESULT,
    FORMAL_RESULT_SHA256,
    OTHER_UNOPENED_SEEDS,
    PLAN,
    PLAN_SHA256,
    ROOT,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


OUTPUT = ROOT / "training-result-v102.json"
BLIND_AUDIT_FILE_SHA256 = (
    "9d79584cb474e299bd57d3639296f19d63fd43279fa282cfa0556da0888b52f5"
)
BLIND_AUDIT_HASH = "8bf216ceeeb499853bdbc3f05e7839245c524a0444db6712898d8ad89bc61a82"
EXPECTED_SEEDS = ("E875", "E876", "E877")
EXPECTED_SCENARIOS = (
    "E3.spike5x50ms",
    "E3.sustained3x200ms",
    "E3.pulse4x4x50ms",
)
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)
ANCHORS = {"E3": "v102-e3-anchor"}
CERTIFICATE_PREFERENCE = {
    "v102-e3-band8-24-warm-preserve-conditional-certificate": 0,
    "v102-e3-band8-24-warm-preserve-initializer-only": 1,
}


def _scenario(run: Mapping[str, Any]) -> str:
    if run.get("experiment_id") == "E3":
        return f"E3.{run['workload']['burst_name']}"
    raise ValueError(f"unexpected experiment: {run.get('experiment_id')}")


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
        for scenario in EXPECTED_SCENARIOS:
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
                    "used_for_V102_selection": False,
                }
            aggregates[arm_id][scenario] = {
                "profile": arm["profile"],
                "metrics": metric_values,
                "formal_absolute_diagnostics": diagnostics,
            }

    candidate_results: dict[str, dict[str, Any]] = {}
    dimension_scores: dict[str, dict[str, Any]] = {"E3": {}}
    for arm_id, arm in ARMS.items():
        if arm["role"] != "candidate":
            continue
        anchor_id = ANCHORS[arm["experiment_id"]]
        candidate_results[arm_id] = {}
        all_gates = []
        for scenario in EXPECTED_SCENARIOS:
            gates = {
                metric: _paired_gate(
                    grouped[(arm_id, scenario)], grouped[(anchor_id, scenario)], metric
                )
                for metric in METRICS
            }
            all_gates.extend(gates.values())
            candidate_results[arm_id][scenario] = {
                "anchor_arm_id": anchor_id,
                "gates": gates,
                "all_three_paired_gates_pass": all(
                    gate["passed"] for gate in gates.values()
                ),
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
        dimension_scores["E3"][arm_id] = {
            "profile": arm["profile"],
            "upper_queue_density_threshold": arm["upper_queue_density_threshold"],
            "anchor_arm_id": anchor_id,
            "required_gate_count": len(all_gates),
            "all_required_gates_pass": arm_pass,
            "minimum_relative_mean_qpr_gain": min(qpr_changes) if arm_pass else None,
            "minimum_relative_mean_throughput_change": (
                min(throughput_changes) if arm_pass else None
            ),
        }

    passers = [
        (arm_id, score)
        for arm_id, score in dimension_scores["E3"].items()
        if score["all_required_gates_pass"]
    ]
    ranked = sorted(
        passers,
        key=lambda item: (
            -float(item[1]["minimum_relative_mean_qpr_gain"]),
            -float(item[1]["minimum_relative_mean_throughput_change"]),
            CERTIFICATE_PREFERENCE[item[0]],
            item[0],
        ),
    )
    rankings = {"E3": [{"arm_id": arm_id, **score} for arm_id, score in ranked]}
    winners = {"E3": rankings["E3"][0] if rankings["E3"] else None}
    return {
        "arm_aggregates": aggregates,
        "paired_candidate_results": candidate_results,
        "dimension_scores": dimension_scores,
        "passing_candidate_rankings": rankings,
        "selected_profiles": winners,
        "joint_training_gate_pass": winners["E3"] is not None,
    }


def _validate_blind_audit() -> dict[str, Any]:
    if not BLIND_AUDIT.is_file() or file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V102 blind audit is missing or changed")
    blind = read_json(BLIND_AUDIT)
    payload = dict(blind)
    claimed = payload.pop("audit_hash", None)
    if (
        claimed != BLIND_AUDIT_HASH
        or object_hash(payload) != claimed
        or blind.get("status") != "pass"
        or blind.get("plan_file_sha256") != PLAN_SHA256
        or blind.get("performance_results_consulted") is not False
        or blind.get("performance_summaries_parsed") != 0
        or blind.get("run_count") != 27
        or blind.get("reference_count") != 27
        or blind.get("tape_count") != 12
        or blind.get("confirmation_inputs_opened") is not False
        or blind.get("other_unopened_inputs_opened") is not False
        or blind.get("reveal_authorized") is not True
    ):
        raise RuntimeError("V102 blind audit does not authorize reveal")
    return blind


def _load_rows(blind: Mapping[str, Any]) -> list[dict[str, Any]]:
    admitted = {item["run_id"]: item["result_sha256"] for item in blind["runs"]}
    if len(admitted) != 27:
        raise RuntimeError("V102 blind audit run evidence is incomplete")
    ready_evidence = blind.get("ready_manifests", {})
    rows = []
    for arm_id, expected in ARMS.items():
        manifest_path = ROOT / f"manifest.{arm_id}.ready.json"
        frozen = ready_evidence.get(arm_id, {})
        if not manifest_path.is_file() or file_hash(manifest_path) != frozen.get(
            "file_sha256"
        ):
            raise RuntimeError(f"V102 frozen manifest changed: {arm_id}")
        manifest = load_and_validate_manifest(manifest_path)
        if manifest.get("manifest_hash") != frozen.get("manifest_hash"):
            raise RuntimeError(f"V102 manifest hash changed: {arm_id}")
        for run in manifest["runs"]:
            metadata = run.get("metadata", {})
            if (
                run["seed"] not in EXPECTED_SEEDS
                or run["method"] != "sche_nash"
                or run["experiment_id"] != expected["experiment_id"]
                or run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
                != expected["profile"]
                or metadata.get("v102_training_plan_sha256") != PLAN_SHA256
                or metadata.get("v102_training_only") is not True
                or metadata.get("v102_training_seed_metrics_previously_revealed")
                is not False
                or metadata.get("v102_confirmation_seeds_opened") is not False
                or metadata.get("v102_other_unopened_seeds_opened") is not False
                or metadata.get("v102_arm_id") != arm_id
                or metadata.get("v102_arm_role") != expected["role"]
                or metadata.get("v102_upper_queue_density_threshold")
                != expected["upper_queue_density_threshold"]
                or metadata.get("v102_nonterminal_queue_density_floor")
                != expected["nonterminal_queue_density_floor"]
                or metadata.get("v102_warm_admissibility")
                != expected["warm_admissibility"]
                or metadata.get("v102_load_least_window_certificate_mode")
                != expected["load_least_window_certificate_mode"]
            ):
                raise RuntimeError(f"V102 arm identity changed: {run['run_id']}")
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
                raise RuntimeError(f"V102 summary differs from blind audit: {run_id}")
            summary = read_json(summary_path)
            if (
                summary.get("run_complete") is not True
                or summary.get("run_id") != run_id
            ):
                raise RuntimeError(
                    f"V102 summary identity/completion mismatch: {run_id}"
                )
            rows.append(
                {
                    "arm_id": arm_id,
                    "role": expected["role"],
                    "profile": expected["profile"],
                    "upper_queue_density_threshold": expected[
                        "upper_queue_density_threshold"
                    ],
                    "nonterminal_queue_density_floor": expected[
                        "nonterminal_queue_density_floor"
                    ],
                    "warm_admissibility": expected["warm_admissibility"],
                    "load_least_window_certificate_mode": expected[
                        "load_least_window_certificate_mode"
                    ],
                    "scenario_id": _scenario(run),
                    "seed": run["seed"],
                    "run_id": run_id,
                    **summary_metrics(summary, run_id),
                    "summary_path": str(summary_path),
                    "summary_file_sha256": admitted[run_id],
                }
            )
    return rows


def _formal_diagnostic_thresholds() -> dict[str, dict[str, float]]:
    if not FORMAL_RESULT.is_file() or file_hash(FORMAL_RESULT) != FORMAL_RESULT_SHA256:
        raise RuntimeError("frozen V94 formal diagnostic result changed")
    formal = read_json(FORMAL_RESULT)
    scenarios = formal.get("scenario_results", {})
    if not set(EXPECTED_SCENARIOS).issubset(scenarios):
        raise RuntimeError("frozen V94 E3 scenario set changed")
    return {
        scenario: {
            metric: float(scenarios[scenario]["gates"][metric]["maximum_baseline_mean"])
            for metric in METRICS
        }
        for scenario in EXPECTED_SCENARIOS
    }


def execute_reveal() -> dict[str, Any]:
    if OUTPUT.exists():
        raise RuntimeError(f"V102 training result already exists: {OUTPUT}")
    if not PLAN.is_file() or file_hash(PLAN) != PLAN_SHA256:
        raise RuntimeError("frozen V102 plan changed before reveal")
    blind = _validate_blind_audit()
    rows = _load_rows(blind)
    if len(rows) != 27:
        raise RuntimeError("V102 revealed row count differs from sealed plan")
    thresholds = _formal_diagnostic_thresholds()
    evaluation = evaluate_training_rows(rows, thresholds)
    joint_pass = evaluation["joint_training_gate_pass"]
    result = {
        "schema_version": "NSE_E3_LOAD_INITIALIZER_CERTIFICATE_FACTORIAL_RESULT_V102_V1",
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
        "plan_file_sha256": PLAN_SHA256,
        "training_seeds": list(EXPECTED_SEEDS),
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
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
            "E3": "one candidate must pass all nine paired scenario-by-metric gates",
            "multiple_passers": (
                "maximize minimum relative mean QPR gain, then minimum relative "
                "throughput change, then prefer conditional certificate over initializer-only, then arm_id"
            ),
            "frozen_E4": (
                "retain V97 v97-e4-load-guard64 without V102 result-dependent reselection"
            ),
            "formal_absolute_gates_used_for_selection": False,
        },
        "frozen_formal_n20_maximum_baseline_means_for_diagnostics": thresholds,
        **evaluation,
        "revealed_rows": rows,
        "decision": {
            "authorize_preregistration_of_E926_E945_confirmation": joint_pass,
            "authorize_generation_of_confirmation_inputs_now": False,
            "authorize_formal_all_method_E3_E4": False,
            "close_any_paper_group_from_training": False,
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "formal_E01_E20_rerun": False,
            "next_action": (
                "freeze the selected E3 profile with the frozen V97 E4 profile and "
                "separately preregister the complete E926-E945 NSESche confirmation "
                "before generating inputs"
                if joint_pass
                else (
                    "freeze the complete V102 training cohort, keep E926-E945 and "
                    "every other unopened seed untouched, and return to mechanism diagnosis"
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
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reveal the frozen V102 training cohort exactly once after blind audit."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    reveal = subparsers.add_parser("reveal", help="perform the one-time reveal")
    reveal.add_argument(
        "--execute",
        action="store_true",
        help="required explicit acknowledgement that performance will be opened",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "reveal" or not args.execute:
        parser.error("V102 reveal requires the explicit command: reveal --execute")
    execute_reveal()


if __name__ == "__main__":
    main()
