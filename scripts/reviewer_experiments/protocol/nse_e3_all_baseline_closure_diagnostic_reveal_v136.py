from __future__ import annotations

import argparse
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_blind_audit_v136 import (
    OUTPUT as BLIND_AUDIT,
)
from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_prepare_v136 import (
    BASELINE_METHODS,
    PLAN,
    PLAN_SHA256,
    ROOT,
    SCENARIOS,
    SEED_LIST,
    V135_ANCHOR_MANIFEST,
    V135_ANCHOR_WORKSPACE,
    paths,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_reveal_v100 import (
    _finite,
    summary_metrics,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


OUTPUT = ROOT / "all-baseline-closure-result-v136.json"
BLIND_AUDIT_FILE_SHA256 = "__FROZEN_AFTER_V136_BLIND_AUDIT__"
BLIND_AUDIT_HASH = "__FROZEN_AFTER_V136_BLIND_AUDIT__"
METHODS = [*BASELINE_METHODS, "sche_nash"]
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)


def _aggregate(rows: Sequence[Mapping[str, Any]], metric: str) -> dict[str, Any]:
    values = [row.get(metric) for row in rows]
    finite_values = [float(value) for value in values if _finite(value)]
    complete = len(rows) == len(SEED_LIST) and len(finite_values) == len(rows)
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


def _paired_comparison(
    anchor_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    metric: str,
) -> dict[str, Any]:
    anchor = {str(row["seed"]): row.get(metric) for row in anchor_rows}
    baseline = {str(row["seed"]): row.get(metric) for row in baseline_rows}
    complete = (
        set(anchor) == set(SEED_LIST)
        and set(baseline) == set(SEED_LIST)
        and all(_finite(value) for value in anchor.values())
        and all(_finite(value) for value in baseline.values())
    )
    deltas = (
        {seed: float(anchor[seed]) - float(baseline[seed]) for seed in SEED_LIST}
        if complete
        else {}
    )
    positive = sum(delta > 0.0 for delta in deltas.values())
    return {
        "complete_paired_finite_cohort": complete,
        "NSESche_minus_baseline_by_seed": deltas,
        "strictly_positive_seed_count": positive,
        "required_strictly_positive_seed_count": 2,
        "passed": complete and positive >= 2,
    }


def evaluate_closure_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    expected_product = {
        (method, scenario, seed)
        for method in METHODS
        for scenario in SCENARIOS
        for seed in SEED_LIST
    }
    actual_product = set()
    for row in rows:
        run_id = str(row.get("run_id"))
        if run_id in seen_ids:
            raise ValueError(f"duplicate V136 run_id: {run_id}")
        seen_ids.add(run_id)
        method = str(row.get("method"))
        scenario = str(row.get("scenario"))
        seed = str(row.get("seed"))
        actual_product.add((method, scenario, seed))
        grouped[(method, scenario)].append(row)
    if len(rows) != 90 or actual_product != expected_product:
        raise ValueError(
            "V136 revealed product mismatch: "
            f"count={len(rows)}, missing={sorted(expected_product-actual_product)}, "
            f"extra={sorted(actual_product-expected_product)}"
        )

    aggregates: dict[str, dict[str, Any]] = {}
    for method in METHODS:
        aggregates[method] = {}
        for scenario in SCENARIOS:
            selected = grouped[(method, scenario)]
            aggregates[method][scenario] = {
                metric: _aggregate(selected, metric) for metric in METRICS
            }

    gates: dict[str, dict[str, Any]] = {}
    all_gate_rows = []
    for scenario in SCENARIOS:
        gates[scenario] = {}
        anchor_rows = grouped[("sche_nash", scenario)]
        for metric in METRICS:
            anchor_aggregate = aggregates["sche_nash"][scenario][metric]
            anchor_mean = anchor_aggregate["mean"]
            baseline_means = {
                method: aggregates[method][scenario][metric]["mean"]
                for method in BASELINE_METHODS
            }
            complete_means = _finite(anchor_mean) and all(
                _finite(value) for value in baseline_means.values()
            )
            maximum = (
                max(float(value) for value in baseline_means.values())
                if complete_means
                else None
            )
            maximum_methods = (
                sorted(
                    method
                    for method, value in baseline_means.items()
                    if float(value) == maximum
                )
                if complete_means and maximum is not None
                else []
            )
            strict_mean_pass = (
                complete_means and maximum is not None and float(anchor_mean) > maximum
            )
            comparisons = {
                method: _paired_comparison(
                    anchor_rows, grouped[(method, scenario)], metric
                )
                for method in BASELINE_METHODS
            }
            direction_pass = all(item["passed"] for item in comparisons.values())
            gate = {
                "metric": metric,
                "NSESche_mean": anchor_mean,
                "baseline_means": baseline_means,
                "maximum_baseline_mean": maximum,
                "maximum_baseline_methods": maximum_methods,
                "NSESche_minus_maximum_baseline_mean": (
                    float(anchor_mean) - maximum
                    if complete_means and maximum is not None
                    else None
                ),
                "strict_mean_rule_pass": strict_mean_pass,
                "paired_direction_comparisons": comparisons,
                "all_nine_paired_direction_rules_pass": direction_pass,
                "no_tie_counts_as_first": True,
                "passed": strict_mean_pass and direction_pass,
            }
            gates[scenario][metric] = gate
            all_gate_rows.append(gate)
    joint_pass = len(all_gate_rows) == 9 and all(
        gate["passed"] for gate in all_gate_rows
    )
    failures = [
        {
            "scenario": scenario,
            "metric": metric,
            "maximum_baseline_methods": gate["maximum_baseline_methods"],
            "NSESche_minus_maximum_baseline_mean": gate[
                "NSESche_minus_maximum_baseline_mean"
            ],
            "strict_mean_rule_pass": gate["strict_mean_rule_pass"],
            "failed_paired_baselines": [
                method
                for method, comparison in gate["paired_direction_comparisons"].items()
                if not comparison["passed"]
            ],
        }
        for scenario, scenario_gates in gates.items()
        for metric, gate in scenario_gates.items()
        if not gate["passed"]
    ]
    return {
        "method_scenario_aggregates": aggregates,
        "closure_gates": gates,
        "required_gate_count": 9,
        "passed_gate_count": sum(gate["passed"] for gate in all_gate_rows),
        "joint_all_baseline_closure_pass": joint_pass,
        "failing_gaps": failures,
    }


def _validate_blind_audit() -> dict[str, Any]:
    frozen = (BLIND_AUDIT_FILE_SHA256, BLIND_AUDIT_HASH)
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in frozen
    ):
        raise RuntimeError("V136 blind audit has not been frozen into reveal code")
    if not BLIND_AUDIT.is_file() or file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V136 blind audit is missing or changed")
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
        or blind.get("baseline_run_count") != 81
        or blind.get("reused_NSESche_run_count") != 9
        or blind.get("combined_run_count") != 90
        or blind.get("NSESche_rerun_count") != 0
        or blind.get("confirmation_inputs_opened") is not False
        or blind.get("reveal_authorized") is not True
    ):
        raise RuntimeError("V136 blind audit does not authorize reveal")
    return blind


def _load_manifest_rows(
    manifest_path: Path,
    workspace: Path,
    evidence: Mapping[str, str],
    expected_manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not manifest_path.is_file() or file_hash(manifest_path) != expected_manifest.get(
        "file_sha256"
    ):
        raise RuntimeError(f"V136 frozen manifest changed: {manifest_path}")
    manifest = load_and_validate_manifest(manifest_path)
    if manifest.get("manifest_hash") != expected_manifest.get("manifest_hash"):
        raise RuntimeError(f"V136 manifest hash changed: {manifest_path}")
    rows = []
    for run in manifest["runs"]:
        run_id = run["run_id"]
        summary_path = (
            workspace
            / "canonical"
            / run_id
            / "reviewer_records"
            / run_id
            / "summary.json"
        )
        admitted = evidence.get(run_id)
        if not summary_path.is_file() or file_hash(summary_path) != admitted:
            raise RuntimeError(f"V136 summary differs from blind audit: {run_id}")
        summary = read_json(summary_path)
        if summary.get("run_complete") is not True or summary.get("run_id") != run_id:
            raise RuntimeError(f"V136 summary identity is invalid: {run_id}")
        rows.append(
            {
                "role": "frozen_NSESche_anchor"
                if run["method"] == "sche_nash"
                else "paper_baseline",
                "method": run["method"],
                "scenario": scenario_id(run),
                "seed": run["seed"],
                "run_id": run_id,
                **summary_metrics(summary, run_id),
                "summary_path": str(summary_path),
                "summary_file_sha256": admitted,
            }
        )
    return rows


def _load_rows(blind: Mapping[str, Any]) -> list[dict[str, Any]]:
    baseline_evidence = {
        str(row["run_id"]): str(row["result_sha256"]) for row in blind["baseline_runs"]
    }
    anchor_evidence = {
        str(row["run_id"]): str(row["result_sha256"]) for row in blind["anchor_runs"]
    }
    if len(baseline_evidence) != 81 or len(anchor_evidence) != 9:
        raise RuntimeError("V136 blind run evidence is incomplete")
    output_paths = paths(ROOT)
    rows = _load_manifest_rows(
        output_paths["ready"],
        output_paths["workspace"],
        baseline_evidence,
        blind["ready_manifest"],
    )
    rows.extend(
        _load_manifest_rows(
            V135_ANCHOR_MANIFEST,
            V135_ANCHOR_WORKSPACE,
            anchor_evidence,
            blind["anchor_manifest"],
        )
    )
    return rows


def execute_reveal() -> dict[str, Any]:
    if OUTPUT.exists():
        raise RuntimeError(f"V136 result already exists: {OUTPUT}")
    if not PLAN.is_file() or file_hash(PLAN) != PLAN_SHA256:
        raise RuntimeError("frozen V136 plan changed before reveal")
    blind = _validate_blind_audit()
    rows = _load_rows(blind)
    evaluation = evaluate_closure_rows(rows)
    joint_pass = evaluation["joint_all_baseline_closure_pass"]
    result = {
        "schema_version": "NSE_E3_ALL_BASELINE_CLOSURE_RESULT_V136_V1",
        "created_at": utc_now(),
        "status": "diagnostic_pass" if joint_pass else "diagnostic_fail",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "diagnostic_alone_may_not_close_a_paper_group": True,
        "metrics_revealed_exactly_once_after_joint_blind_audit": True,
        "joint_blind_audit_path": str(BLIND_AUDIT),
        "joint_blind_audit_file_sha256": BLIND_AUDIT_FILE_SHA256,
        "joint_blind_audit_hash": BLIND_AUDIT_HASH,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "seeds": list(SEED_LIST),
        "scenarios": list(SCENARIOS),
        "baseline_methods": list(BASELINE_METHODS),
        "selection_metrics": list(METRICS),
        "closure_rule": {
            "mean": "NSESche mean strictly exceeds every baseline mean per scenario and metric",
            "paired_direction": "NSESche-minus-baseline is strictly positive on at least two of three paired seeds for every baseline",
            "winner": "all nine scenario-metric gates pass; ties fail",
        },
        **evaluation,
        "revealed_rows": rows,
        "decision": {
            "authorize_preregistration_of_all_method_E1451_E1470_confirmation": joint_pass,
            "authorize_generation_of_confirmation_inputs_now": False,
            "close_any_paper_group_from_this_diagnostic": False,
            "delete_replace_or_select_unfavorable_seed_method_or_result": False,
            "rerun_NSESche_on_E1448_E1450": False,
            "next_action": (
                "preregister the complete all-method E1451-E1470 confirmation before generating any confirmation input"
                if joint_pass
                else "retain the complete V136 cohort and target the revealed paired baseline gaps only through a separately preregistered mechanism change on fresh training seeds"
            ),
        },
    }
    result["result_hash"] = object_hash(result)
    write_json_atomic(OUTPUT, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reveal the frozen V136 all-baseline closure diagnostic exactly once."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    reveal = subparsers.add_parser("reveal", help="perform the one-time reveal")
    reveal.add_argument(
        "--execute",
        action="store_true",
        help="required explicit acknowledgement that all baseline performance will be opened",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "reveal" or not args.execute:
        parser.error("V136 reveal requires the explicit command: reveal --execute")
    execute_reveal()


if __name__ == "__main__":
    main()
