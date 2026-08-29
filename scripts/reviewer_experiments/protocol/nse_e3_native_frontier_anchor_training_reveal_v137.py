from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_reveal_v100 import (
    _finite,
    summary_metrics,
)
from scripts.reviewer_experiments.protocol.nse_e3_native_frontier_anchor_training_blind_audit_v137 import (
    ARMS,
    OUTPUT as BLIND_AUDIT,
)
from scripts.reviewer_experiments.protocol.nse_e3_native_frontier_anchor_training_execute_v137 import (
    ready_manifest_path,
    workspace_path,
)
from scripts.reviewer_experiments.protocol.nse_e3_native_frontier_anchor_training_prepare_v137 import (
    ARM_IDS,
    BASELINE_METHODS,
    NEW_CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUS_CONFIRMATION_SEEDS,
    ROOT,
    SCENARIOS,
    TRAINING_SEED_LIST,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


OUTPUT = ROOT / "training-result-v137.json"
BLIND_AUDIT_FILE_SHA256 = (
    "2bdc4e71a423e712fa668e3f0afdcc958030b9a49eb21e00c1320f9365ea1633"
)
BLIND_AUDIT_HASH = "85823dbb4c9081d9787a353aac35b09432f9ac29a4ef7c0283d98c7647ce859c"
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)


def _aggregate(rows: Sequence[Mapping[str, Any]], metric: str) -> dict[str, Any]:
    values = [row.get(metric) for row in rows]
    finite = [float(value) for value in values if _finite(value)]
    complete = len(rows) == 3 and len(finite) == 3
    return {
        "n_total": len(rows),
        "n_finite": len(finite),
        "n_zero_completed": sum(row.get("fixed_window_completed") == 0 for row in rows),
        "complete_three_seed_finite_cohort": complete,
        "mean": statistics.fmean(finite) if complete else None,
        "sample_std": statistics.stdev(finite) if complete else None,
        "values_by_seed": {
            str(row["seed"]): row.get(metric)
            for row in sorted(rows, key=lambda item: str(item["seed"]))
        },
    }


def _paired_comparison(
    candidate_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    metric: str,
) -> dict[str, Any]:
    candidate = {str(row["seed"]): row.get(metric) for row in candidate_rows}
    baseline = {str(row["seed"]): row.get(metric) for row in baseline_rows}
    complete = (
        set(candidate) == set(TRAINING_SEED_LIST)
        and set(baseline) == set(TRAINING_SEED_LIST)
        and all(_finite(value) for value in candidate.values())
        and all(_finite(value) for value in baseline.values())
    )
    deltas = (
        {
            seed: float(candidate[seed]) - float(baseline[seed])
            for seed in TRAINING_SEED_LIST
        }
        if complete
        else {}
    )
    positive = sum(delta > 0.0 for delta in deltas.values())
    return {
        "metric": metric,
        "complete_paired_finite_cohort": complete,
        "candidate_minus_baseline_by_seed": deltas,
        "strictly_positive_seed_count": positive,
        "required_strictly_positive_seed_count": 2,
        "passed": complete and positive >= 2,
    }


def evaluate_training_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    labels = [*BASELINE_METHODS, *ARM_IDS]
    expected = {
        (label, scenario, seed)
        for label in labels
        for scenario in SCENARIOS
        for seed in TRAINING_SEED_LIST
    }
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    actual = set()
    run_ids = set()
    for row in rows:
        run_id = str(row.get("run_id"))
        if run_id in run_ids:
            raise ValueError(f"duplicate V137 run_id: {run_id}")
        run_ids.add(run_id)
        key = (str(row.get("method_label")), str(row.get("scenario")))
        grouped[key].append(row)
        actual.add((key[0], key[1], str(row.get("seed"))))
    if len(rows) != 108 or actual != expected:
        raise ValueError(
            "V137 revealed product mismatch: "
            f"count={len(rows)}, missing={sorted(expected-actual)}, "
            f"extra={sorted(actual-expected)}"
        )

    aggregates: dict[str, dict[str, Any]] = {}
    for label in labels:
        aggregates[label] = {}
        for scenario in SCENARIOS:
            selected = grouped[(label, scenario)]
            aggregates[label][scenario] = {
                metric: _aggregate(selected, metric) for metric in METRICS
            }

    arm_results = {}
    passing = []
    for arm_id in ARM_IDS:
        arm_gates = {}
        relative_margins = []
        all_gates = []
        for scenario in SCENARIOS:
            scenario_gates = {}
            for metric in METRICS:
                candidate_mean = aggregates[arm_id][scenario][metric]["mean"]
                baseline_means = {
                    method: aggregates[method][scenario][metric]["mean"]
                    for method in BASELINE_METHODS
                }
                complete = _finite(candidate_mean) and all(
                    _finite(value) for value in baseline_means.values()
                )
                maximum = (
                    max(float(value) for value in baseline_means.values())
                    if complete
                    else None
                )
                strict_mean = (
                    complete and maximum is not None and float(candidate_mean) > maximum
                )
                comparisons = {
                    method: _paired_comparison(
                        grouped[(arm_id, scenario)],
                        grouped[(method, scenario)],
                        metric,
                    )
                    for method in BASELINE_METHODS
                }
                paired_pass = all(item["passed"] for item in comparisons.values())
                relative_margin = (
                    (float(candidate_mean) - maximum) / maximum
                    if strict_mean and maximum is not None and maximum > 0.0
                    else None
                )
                gate = {
                    "metric": metric,
                    "candidate_mean": candidate_mean,
                    "baseline_means": baseline_means,
                    "maximum_baseline_mean": maximum,
                    "maximum_baseline_methods": (
                        sorted(
                            method
                            for method, value in baseline_means.items()
                            if complete and float(value) == maximum
                        )
                        if complete
                        else []
                    ),
                    "candidate_minus_maximum_baseline_mean": (
                        float(candidate_mean) - maximum
                        if complete and maximum is not None
                        else None
                    ),
                    "relative_mean_margin": relative_margin,
                    "strict_mean_rule_pass": strict_mean,
                    "paired_direction_comparisons": comparisons,
                    "all_nine_paired_direction_rules_pass": paired_pass,
                    "passed": strict_mean and paired_pass,
                }
                scenario_gates[metric] = gate
                all_gates.append(gate)
                if relative_margin is not None:
                    relative_margins.append(relative_margin)
            arm_gates[scenario] = scenario_gates
        arm_pass = len(all_gates) == 9 and all(gate["passed"] for gate in all_gates)
        score = {
            "arm_id": arm_id,
            "profile": ARMS[arm_id]["profile"],
            "required_gate_count": 9,
            "passed_gate_count": sum(gate["passed"] for gate in all_gates),
            "all_required_gates_pass": arm_pass,
            "minimum_relative_mean_margin": (
                min(relative_margins)
                if arm_pass and len(relative_margins) == 9
                else None
            ),
        }
        arm_results[arm_id] = {"gates": arm_gates, "score": score}
        if arm_pass:
            passing.append(score)
    passing.sort(
        key=lambda item: (
            -float(item["minimum_relative_mean_margin"]),
            str(item["arm_id"]),
        )
    )
    selected = passing[0] if passing else None
    return {
        "method_scenario_aggregates": aggregates,
        "arm_results": arm_results,
        "passing_candidate_rankings": passing,
        "selected_profile": selected,
        "family_training_gate_pass": selected is not None,
        "paper_claim_authorized": False,
        "confirmation_required_for_any_claim": selected is not None,
    }


def _validate_blind_audit() -> dict[str, Any]:
    frozen = (BLIND_AUDIT_FILE_SHA256, BLIND_AUDIT_HASH)
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in frozen
    ):
        raise RuntimeError("V137 blind audit has not been frozen into reveal code")
    if not BLIND_AUDIT.is_file() or file_hash(BLIND_AUDIT) != BLIND_AUDIT_FILE_SHA256:
        raise RuntimeError("V137 blind audit is missing or changed")
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
        or blind.get("run_count") != 108
        or blind.get("reference_count") != 27
        or blind.get("tape_count") != 12
        or blind.get("block_count") != 9
        or blind.get("sealed_previous_confirmation_seeds")
        != PREVIOUS_CONFIRMATION_SEEDS
        or blind.get("sealed_new_confirmation_seeds") != NEW_CONFIRMATION_SEEDS
        or blind.get("confirmation_inputs_opened") is not False
        or blind.get("reveal_authorized") is not True
    ):
        raise RuntimeError("V137 blind audit does not authorize reveal")
    return blind


def _load_rows(blind: Mapping[str, Any]) -> list[dict[str, Any]]:
    admitted = {item["run_id"]: item for item in blind["runs"]}
    if len(admitted) != 108:
        raise RuntimeError("V137 blind audit run evidence is incomplete")
    rows = []
    for manifest_id in ["v137-baselines", *ARM_IDS]:
        manifest_path = ready_manifest_path(ROOT, manifest_id)
        frozen = blind["ready_manifests"].get(manifest_id, {})
        if not manifest_path.is_file() or file_hash(manifest_path) != frozen.get(
            "file_sha256"
        ):
            raise RuntimeError(f"V137 frozen manifest changed: {manifest_id}")
        manifest = load_and_validate_manifest(manifest_path)
        if manifest.get("manifest_hash") != frozen.get("manifest_hash"):
            raise RuntimeError(f"V137 manifest hash changed: {manifest_id}")
        candidate = manifest_id in ARM_IDS
        for run in manifest["runs"]:
            run_id = run["run_id"]
            evidence = admitted.get(run_id)
            if evidence is None or evidence.get("manifest_id") != manifest_id:
                raise RuntimeError(f"V137 run not admitted by blind audit: {run_id}")
            summary_path = (
                workspace_path(ROOT, manifest_id)
                / "canonical"
                / run_id
                / "reviewer_records"
                / run_id
                / "summary.json"
            )
            if not summary_path.is_file() or file_hash(summary_path) != evidence.get(
                "result_sha256"
            ):
                raise RuntimeError(f"V137 summary differs from blind audit: {run_id}")
            summary = read_json(summary_path)
            if (
                summary.get("run_complete") is not True
                or summary.get("run_id") != run_id
            ):
                raise RuntimeError(f"V137 summary identity changed: {run_id}")
            rows.append(
                {
                    "method_label": manifest_id if candidate else run["method"],
                    "role": "candidate" if candidate else "paper_baseline",
                    "scenario": scenario_id(run),
                    "seed": run["seed"],
                    "run_id": run_id,
                    **summary_metrics(summary, run_id),
                    "summary_path": str(summary_path),
                    "summary_file_sha256": evidence["result_sha256"],
                }
            )
    return rows


def execute_reveal() -> dict[str, Any]:
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite V137 result: {OUTPUT}")
    if not PLAN.is_file() or file_hash(PLAN) != PLAN_SHA256:
        raise RuntimeError("V137 plan changed before reveal")
    blind = _validate_blind_audit()
    rows = _load_rows(blind)
    evaluation = evaluate_training_rows(rows)
    result = {
        "schema_version": "NSE_E3_NATIVE_FRONTIER_ANCHOR_TRAINING_RESULT_V137_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_only": True,
        "performance_results_consulted": True,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "blind_audit_path": str(BLIND_AUDIT),
        "blind_audit_file_sha256": BLIND_AUDIT_FILE_SHA256,
        "blind_audit_hash": BLIND_AUDIT_HASH,
        "training_seeds": TRAINING_SEED_LIST,
        "sealed_previous_confirmation_seeds": PREVIOUS_CONFIRMATION_SEEDS,
        "sealed_new_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        "confirmation_inputs_generated": False,
        "run_count": len(rows),
        "metrics": list(METRICS),
        **evaluation,
        "rows": rows,
    }
    result["result_hash"] = object_hash(result)
    write_json_atomic(OUTPUT, result)
    return result


def main() -> None:
    result = execute_reveal()
    selected = result["selected_profile"]
    print(
        json.dumps(
            {
                "family_training_gate_pass": result["family_training_gate_pass"],
                "selected_arm_id": selected["arm_id"] if selected else None,
                "result_hash": result["result_hash"],
            }
        )
    )


if __name__ == "__main__":
    main()
