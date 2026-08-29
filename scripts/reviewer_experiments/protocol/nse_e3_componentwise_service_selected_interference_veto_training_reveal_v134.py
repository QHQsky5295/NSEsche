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
from scripts.reviewer_experiments.protocol.nse_e3_componentwise_service_selected_interference_veto_training_blind_audit_v134 import (
    ARMS,
    OUTPUT as BLIND_AUDIT,
)
from scripts.reviewer_experiments.protocol.nse_e3_componentwise_service_selected_interference_veto_training_prepare_v134 import (
    CONFIRMATION_SEEDS,
    FORMAL_RESULT,
    FORMAL_RESULT_SHA256,
    OTHER_UNOPENED_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUS_CONFIRMATION_SEEDS,
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


OUTPUT = ROOT / "training-result-v134.json"
BLIND_AUDIT_FILE_SHA256 = (
    "2feb507f69ec3adb1ba4b28feb167e65a001a847a135551754931c7f0fbc6de6"
)
BLIND_AUDIT_HASH = "e6817deb5473bd5df465895455ec7b8feb24c76838da74eb4c3cd2f7bbef31d5"
EXPECTED_SEEDS = ("E1425", "E1426", "E1427")
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
ANCHOR_ID = "v134-e3-anchor"
CANDIDATE_ID = (
    "v134-e3-causal-shock15-horizon50-admitted-work10-"
    "componentwise-service-selected-interference-veto-initializer-only"
)


def _scenario(run: Mapping[str, Any]) -> str:
    if run.get("experiment_id") != "E3":
        raise ValueError(f"unexpected experiment: {run.get('experiment_id')}")
    return f"E3.{run['workload']['burst_name']}"


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
        (arm_id, scenario) for arm_id in ARMS for scenario in EXPECTED_SCENARIOS
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
                    "used_for_V134_selection": False,
                }
            aggregates[arm_id][scenario] = {
                "profile": arm["profile"],
                "metrics": metric_values,
                "formal_absolute_diagnostics": diagnostics,
            }

    candidate_results: dict[str, dict[str, Any]] = {CANDIDATE_ID: {}}
    all_gates: list[dict[str, Any]] = []
    for scenario in EXPECTED_SCENARIOS:
        gates = {
            metric: _paired_gate(
                grouped[(CANDIDATE_ID, scenario)],
                grouped[(ANCHOR_ID, scenario)],
                metric,
            )
            for metric in METRICS
        }
        all_gates.extend(gates.values())
        candidate_results[CANDIDATE_ID][scenario] = {
            "anchor_arm_id": ANCHOR_ID,
            "gates": gates,
            "all_three_paired_gates_pass": all(
                gate["passed"] for gate in gates.values()
            ),
        }

    candidate_pass = len(all_gates) == 9 and all(gate["passed"] for gate in all_gates)
    relative_qpr_changes = [
        float(gate["relative_mean_change"])
        for gate in all_gates
        if gate["metric"].startswith("qpr_") and _finite(gate["relative_mean_change"])
    ]
    relative_throughput_changes = [
        float(gate["relative_mean_change"])
        for gate in all_gates
        if gate["metric"] == "throughput_requests_per_ms"
        and _finite(gate["relative_mean_change"])
    ]
    score = {
        "arm_id": CANDIDATE_ID,
        "profile": ARMS[CANDIDATE_ID]["profile"],
        "anchor_arm_id": ANCHOR_ID,
        "required_gate_count": 9,
        "all_required_gates_pass": candidate_pass,
        "minimum_relative_mean_qpr_gain": (
            min(relative_qpr_changes) if candidate_pass else None
        ),
        "minimum_relative_mean_throughput_change": (
            min(relative_throughput_changes) if candidate_pass else None
        ),
    }
    return {
        "arm_aggregates": aggregates,
        "paired_candidate_results": candidate_results,
        "candidate_score": score,
        "passing_candidate_rankings": {"E3": [score] if candidate_pass else []},
        "selected_profiles": {"E3": score if candidate_pass else None},
        "joint_training_gate_pass": candidate_pass,
    }


def _validate_blind_audit() -> dict[str, Any]:
    frozen = (BLIND_AUDIT_FILE_SHA256, BLIND_AUDIT_HASH)
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in frozen
    ):
        raise RuntimeError("V134 blind audit has not been frozen into the reveal code")
    if not BLIND_AUDIT.is_file() or file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V134 blind audit is missing or changed")
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
        or blind.get("run_count") != 18
        or blind.get("reference_count") != 18
        or blind.get("tape_count") != 12
        or blind.get("untouched_confirmation_seeds") != CONFIRMATION_SEEDS
        or blind.get("previous_confirmation_seeds_remaining_sealed")
        != PREVIOUS_CONFIRMATION_SEEDS
        or blind.get("other_unopened_seeds_untouched") != OTHER_UNOPENED_SEEDS
        or blind.get("confirmation_inputs_opened") is not False
        or blind.get("other_unopened_inputs_opened") is not False
        or blind.get("reveal_authorized") is not True
    ):
        raise RuntimeError("V134 blind audit does not authorize reveal")
    return blind


def _load_rows(blind: Mapping[str, Any]) -> list[dict[str, Any]]:
    admitted = {item["run_id"]: item["result_sha256"] for item in blind["runs"]}
    if len(admitted) != 18:
        raise RuntimeError("V134 blind audit run evidence is incomplete")
    ready_evidence = blind.get("ready_manifests", {})
    rows = []
    for arm_id, expected in ARMS.items():
        manifest_path = ROOT / f"manifest.{arm_id}.ready.json"
        frozen = ready_evidence.get(arm_id, {})
        if not manifest_path.is_file() or file_hash(manifest_path) != frozen.get(
            "file_sha256"
        ):
            raise RuntimeError(f"V134 frozen manifest changed: {arm_id}")
        manifest = load_and_validate_manifest(manifest_path)
        if manifest.get("manifest_hash") != frozen.get("manifest_hash"):
            raise RuntimeError(f"V134 manifest hash changed: {arm_id}")
        for run in manifest["runs"]:
            metadata = run.get("metadata", {})
            candidate = expected["role"] == "candidate"
            if (
                run["seed"] not in EXPECTED_SEEDS
                or run["method"] != "sche_nash"
                or run["experiment_id"] != "E3"
                or run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
                != expected["profile"]
                or metadata.get("v134_training_plan_sha256") != PLAN_SHA256
                or metadata.get("v134_training_only") is not True
                or metadata.get("v134_training_seed_metrics_previously_revealed")
                is not False
                or metadata.get("v134_confirmation_seeds_opened") is not False
                or metadata.get("v134_other_unopened_seeds_opened") is not False
                or metadata.get("v134_arm_id") != arm_id
                or metadata.get("v134_arm_role") != expected["role"]
                or metadata.get("v134_shock_rate_ratio") != expected["shock_rate_ratio"]
                or metadata.get("v134_shock_threshold_numerator")
                != expected["shock_threshold_numerator"]
                or metadata.get("v134_shock_threshold_denominator")
                != expected["shock_threshold_denominator"]
                or metadata.get("v134_shock_activation_horizon_frames")
                != expected["shock_activation_horizon_frames"]
                or metadata.get("v134_critical_service_ratio_numerator")
                != expected["critical_service_threshold_numerator"]
                or metadata.get("v134_critical_service_ratio_denominator")
                != expected["critical_service_threshold_denominator"]
                or metadata.get("v134_service_proxy_work_source")
                != (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if candidate
                    else "not_applicable"
                )
                or metadata.get("v134_admitted_work_includes_all_blocked_resident")
                is not candidate
                or metadata.get("v134_complete_componentwise_service_pareto")
                is not candidate
                or metadata.get("v134_complete_admitted_interference_pareto")
                is not False
                or metadata.get("v134_componentwise_admitted_interference_pareto")
                is not False
                or metadata.get("v134_selected_choice_interference_veto")
                is not candidate
                or metadata.get("v134_selected_choice_interference_comparison")
                != (
                    "first_otherwise_accepted_player_interference_lte_anchor_plus_epsilon"
                    if candidate
                    else "not_applicable"
                )
                or metadata.get(
                    "v134_selected_choice_interference_inputs_finite_fail_closed"
                )
                is not candidate
                or metadata.get("v134_outcome_fields_drive_policy") is not False
                or metadata.get("v134_scenario_or_burst_label_used_by_policy")
                is not False
                or metadata.get("v134_completion_or_performance_fields_used_by_policy")
                is not False
                or metadata.get("v134_future_arrivals_used_by_policy") is not False
            ):
                raise RuntimeError(f"V134 arm identity changed: {run['run_id']}")
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
                raise RuntimeError(f"V134 summary differs from blind audit: {run_id}")
            summary = read_json(summary_path)
            if (
                summary.get("run_complete") is not True
                or summary.get("run_id") != run_id
            ):
                raise RuntimeError(
                    f"V134 summary identity/completion mismatch: {run_id}"
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
        raise RuntimeError(f"V134 training result already exists: {OUTPUT}")
    if not PLAN.is_file() or file_hash(PLAN) != PLAN_SHA256:
        raise RuntimeError("frozen V134 plan changed before reveal")
    blind = _validate_blind_audit()
    rows = _load_rows(blind)
    if len(rows) != 18:
        raise RuntimeError("V134 revealed row count differs from sealed plan")
    thresholds = _formal_diagnostic_thresholds()
    evaluation = evaluate_training_rows(rows, thresholds)
    joint_pass = evaluation["joint_training_gate_pass"]
    result = {
        "schema_version": "NSE_E3_COMPONENTWISE_SERVICE_SELECTED_INTERFERENCE_VETO_RESULT_V134_V1",
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
        "previous_confirmation_seeds_remaining_sealed": PREVIOUS_CONFIRMATION_SEEDS,
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
            "E3": "the sole candidate must pass all nine paired gates",
            "candidate_ranking_or_tie_break": "not_applicable_one_candidate_only",
            "formal_absolute_gates_used_for_selection": False,
        },
        "frozen_formal_n20_maximum_baseline_means_for_diagnostics": thresholds,
        **evaluation,
        "revealed_rows": rows,
        "decision": {
            "authorize_preregistration_of_E1428_E1447_confirmation": joint_pass,
            "authorize_generation_of_confirmation_inputs_now": False,
            "authorize_formal_all_method_E3_E4": False,
            "close_any_paper_group_from_training": False,
            "seed_deletion_replacement_or_selective_rerun": False,
            "baseline_rerun": False,
            "formal_E01_E20_rerun": False,
            "next_action": (
                "freeze V134 with frozen V97 E4 and separately preregister the "
                "complete E1428-E1447 NSESche confirmation before generating inputs"
                if joint_pass
                else (
                    "freeze the complete V134 training cohort, keep E1428-E1447 and "
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
        description="Reveal the frozen V134 training cohort exactly once after blind audit."
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
        parser.error("V134 reveal requires the explicit command: reveal --execute")
    execute_reveal()


if __name__ == "__main__":
    main()
