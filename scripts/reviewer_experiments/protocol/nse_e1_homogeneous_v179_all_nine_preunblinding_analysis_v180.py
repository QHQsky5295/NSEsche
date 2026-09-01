from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_queue8_cpu2_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v179 as v179,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v176 as v176,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_requestcohort1_shortest_request_least_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v175 as v175,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    _evaluate_load,
    _load_baselines,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    _assert_file,
    _assert_hashed,
    _validate_reference_catalog,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_v179_all_nine_preunblinding_analysis_plan_v180.json"
)
PLAN_SHA256 = "aec02b7a640e587438c3e133dd83c1ad99d61eb9211c63c4613bb6a53abfae38"
V179_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_queue8_cpu2_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_failure_v179.json"
)
V179_FAILURE_SHA256 = "85ffc5ec7f84b15fb05026643b08a5f1a14de4aabe198f525cc993c52173b931"
V179_FAILURE_HASH = "41d224c57fd708d1f901f5836be00ce313acdec547ba67a3d043f1fe32cfbb8b"
V179_BLIND_SHA256 = "c499fea40f9ecaa60b40492a7e8f3785b692b504856f5b28da7390690ab806ac"
V179_BLIND_HASH = "cb73cf232b3af26a05a6fb6b758982e72884e4b8d4fd5ac2f293698028d9e74a"
REACHABLE_SEEDS = ("E01", "E05", "E06", "E12", "E15", "E17")
NO_ACTIVATION_SEEDS = ("E09", "E10", "E18")
SELECTED_THROUGHPUT_SUM_GATE = 12.581000000000001
SELECTED_QPR_SUM_GATE = 0.40358639189433965
SELECTED_THROUGHPUT_WIN_GATE = 5
SELECTED_QPR_WIN_GATE = 7


def paths() -> dict[str, Path]:
    output = v179.paths()
    return {
        **output,
        "blind_v180": v179.ROOT / "joint-blind-audit-v180.json",
        "result_v180": v179.ROOT / "diagnostic-result-v180.json",
    }


def _assert_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    v179._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V180 pre-unblinding plan"),
        (V179_FAILURE, V179_FAILURE_SHA256, "V179 failure receipt"),
        (v179.paths()["blind"], V179_BLIND_SHA256, "V179 blind audit"),
    ):
        _assert_file(path, sha256, label)
    failure = read_json(V179_FAILURE)
    blind = read_json(v179.paths()["blind"])
    if not (
        _assert_hashed(failure, "receipt_hash", "V179 failure receipt")
        == V179_FAILURE_HASH
        and failure.get("disposition", {}).get("retain_all_nine_valid_v179_runs")
        is True
        and failure.get("disposition", {}).get("performance_reveal_or_gate_evaluation")
        is False
        and _assert_hashed(blind, "blind_audit_hash", "V179 blind audit")
        == V179_BLIND_HASH
        and blind.get("performance_reveal_authorized") is False
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("run_count") == len(v179.SEEDS)
    ):
        raise RuntimeError("V179 pre-unblinding boundary changed")
    plan = read_json(PLAN)
    if not (
        plan.get("performance_results_consulted_for_this_analysis_plan") is False
        and plan.get("all_nine_fixed_cohort") == list(v179.SEEDS)
        and plan.get("execution_policy", {}).get("new_online_runs") == 0
        and plan.get("execution_policy", {}).get("new_reference_builds") == 0
        and plan.get("execution_policy", {}).get(
            "delete_replace_relabel_or_selectively_rerun_any_seed"
        )
        is False
    ):
        raise RuntimeError("V180 analysis plan changed")
    return failure, blind


def _mechanism_gate(audits: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_seed = {item["seed"]: item for item in audits}
    if set(by_seed) != set(v179.SEEDS):
        raise RuntimeError("V180 audit cohort changed")
    reachable = all(
        by_seed[seed]["bounded_single_activation_windows"] > 0
        and by_seed[seed]["first_assignment_mismatch_frame_vs_frozen_base"]
        == by_seed[seed]["first_bounded_single_activation_frame"]
        for seed in REACHABLE_SEEDS
    )
    no_activation = all(
        by_seed[seed]["bounded_single_activation_windows"] == 0
        and by_seed[seed]["first_assignment_mismatch_frame_vs_frozen_base"] is None
        and by_seed[seed]["exact_one_unbounded_windows"] > 0
        for seed in NO_ACTIVATION_SEEDS
    )
    other = (
        sum(item["exact_two_windows"] for item in audits) > 0
        and sum(item["parents_completed_heavy_bypass_players"] for item in audits) > 0
        and sum(item["low_route_windows"] for item in audits) > 0
        and sum(item["high_route_windows"] for item in audits) > 0
        and sum(item["reference_available_windows"] for item in audits) > 0
    )
    return {
        "reachable_seed_set": list(REACHABLE_SEEDS),
        "no_activation_control_seed_set": list(NO_ACTIVATION_SEEDS),
        "reachable_seeds_activate_and_first_diverge_at_activation": reachable,
        "no_activation_controls_equal_nearest_parent_for_all_windows": no_activation,
        "primary_bypass_route_and_reference_breadth": other,
        "pass": reachable and no_activation and other,
    }


def blind_audit_v180() -> dict[str, Any]:
    output = paths()
    if output["blind_v180"].exists():
        raise RuntimeError("V180 blind audit already exists")
    failure, old_blind = _assert_inputs()
    manifest = load_and_validate_manifest(output["ready"])
    v179._validate_product(manifest, bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed")
        and pairing.get("run_count") == len(v179.SEEDS)
        and pairing.get("group_count") == len(v179.SEEDS)
    ):
        raise RuntimeError("V180 exact pairing failed")
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    references = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=len(v179.SEEDS)
    )
    audits = []
    identities = set()
    canonical_root = output["workspace"] / "canonical"
    for run in manifest["runs"]:
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit_manifest = read_json(canonical / "manifest.json")
        software = audit_manifest.get("software_environment", {})
        identities.add(
            (
                audit_manifest.get("adapter_binary", {}).get("verified_sha256"),
                software.get("git", {}).get("commit"),
                software.get("python", {}).get("executable_sha256"),
                software.get("cargo_lock", {}).get("sha256"),
            )
        )
        audits.append(
            v179._audit_nash_log(
                canonical, run, v179._frozen_assignment_hashes(run["seed"])
            )
        )
    if len(identities) != 1:
        raise RuntimeError("V180 runtime identity is not unanimous")
    identity = next(iter(identities))
    expected = old_blind["runtime_identity"]
    if identity != (
        expected["runtime_binary_sha256"],
        expected["runtime_git_commit"],
        expected["runtime_python_executable_sha256"],
        expected["runtime_cargo_lock_sha256"],
    ):
        raise RuntimeError("V180 runtime identity changed")
    mechanism = _mechanism_gate(audits)
    if not mechanism["pass"]:
        raise RuntimeError("V180 result-blind mechanism gate failed")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V179_ALL_NINE_PREUNBLINDING_AUDIT_V180_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "post_collection_pre_unblinding_analysis": True,
        "plan_file_sha256": PLAN_SHA256,
        "audit_source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "v179_failure_receipt_hash": failure["receipt_hash"],
        "v179_blind_audit_hash": old_blind["blind_audit_hash"],
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": references,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_passed": True,
        "run_count": len(v179.SEEDS),
        "window_count": sum(item["windows"] for item in audits),
        "runtime_identity": {
            "runtime_binary_sha256": identity[0],
            "runtime_git_commit": identity[1],
            "runtime_python_executable_sha256": identity[2],
            "runtime_cargo_lock_sha256": identity[3],
        },
        "mechanism_gate": mechanism,
        "per_run_result_blind_audits": audits,
        "all_nine_runs_included": True,
        "new_online_runs": 0,
        "new_reference_builds": 0,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind_v180"], document)
    return document


def reveal_v180() -> dict[str, Any]:
    output = paths()
    if output["result_v180"].exists():
        raise RuntimeError("V180 result already exists")
    _assert_inputs()
    blind = read_json(output["blind_v180"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V180 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("mechanism_gate", {}).get("pass") is True
        and blind.get("all_nine_runs_included") is True
    ):
        raise RuntimeError("V180 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = v179._load_candidate(manifest, v179.ROOT)
    v170_rows = v175._load_v170_candidate()
    v176_manifest = load_and_validate_manifest(v176.paths()["ready"])
    v176_rows = v176._load_candidate(v176_manifest, v176.ROOT)
    hybrid = v179._hybrid_rows(v170_rows, v176_rows, candidate)
    evaluation = _evaluate_load("low", hybrid, _load_baselines())
    throughput_sum = sum(float(row["throughput"]) for row in candidate)
    qpr_values = [float(row["qpr_finite_only"]) for row in candidate]
    throughput_wins = sum(
        row["difference"] > 0
        for row in evaluation["gates"]["throughput"]["paired_rows"]
        if row["seed"] in v179.SEEDS
    )
    qpr_wins = sum(
        row["difference"] > 0
        for row in evaluation["gates"]["qpr_finite_only"]["paired_rows"]
        if row["seed"] in v179.SEEDS
    )
    gates = {
        "throughput_selected_nine_sum": throughput_sum,
        "throughput_selected_nine_sum_gate": SELECTED_THROUGHPUT_SUM_GATE,
        "throughput_selected_nine_sum_pass": throughput_sum
        > SELECTED_THROUGHPUT_SUM_GATE,
        "throughput_selected_nine_paired_wins": throughput_wins,
        "throughput_selected_nine_paired_wins_required": SELECTED_THROUGHPUT_WIN_GATE,
        "throughput_selected_nine_paired_wins_pass": throughput_wins
        >= SELECTED_THROUGHPUT_WIN_GATE,
        "qpr_selected_nine_sum": sum(qpr_values),
        "qpr_selected_nine_sum_gate": SELECTED_QPR_SUM_GATE,
        "qpr_selected_nine_sum_pass": sum(qpr_values) > SELECTED_QPR_SUM_GATE,
        "qpr_selected_nine_paired_wins": qpr_wins,
        "qpr_selected_nine_paired_wins_required": SELECTED_QPR_WIN_GATE,
        "qpr_selected_nine_paired_wins_pass": qpr_wins >= SELECTED_QPR_WIN_GATE,
        "qpr_selected_nine_all_finite": all(
            math.isfinite(value) for value in qpr_values
        ),
    }
    passed = evaluation["all_three_metric_gates_pass"] and all(
        value
        for key, value in gates.items()
        if key.endswith("_pass") or key.endswith("_all_finite")
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V179_ALL_NINE_PREUNBLINDING_RESULT_V180_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "post_collection_pre_unblinding_analysis": True,
        "plan_file_sha256": PLAN_SHA256,
        "blind_audit_file_sha256": file_hash(output["blind_v180"]),
        "blind_audit_hash": blind_hash,
        "all_nine_runs_included": True,
        "new_online_runs": 0,
        "new_reference_builds": 0,
        "baseline_reruns": 0,
        "hybrid_low_evaluation": evaluation,
        "selected_nine_gates": gates,
        "mechanism_gate": blind["mechanism_gate"],
        "joint_diagnostic_pass": passed,
        "disposition": (
            "close_homogeneous_low_training_and_authorize_a_separately_committed_confirmation_plan"
            if passed
            else "retain_all_nine_valid_V179_runs_and_retire_V180_without_subset_reporting"
        ),
        "homogeneous_low_claim_closed": passed,
        "confirmation_inputs_generated": False,
        "middle_or_later_execution_authorized": False,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result_v180"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("blind-audit", "reveal"))
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    if action == "blind-audit":
        document, key = blind_audit_v180(), "blind_audit_hash"
    else:
        document, key = reveal_v180(), "result_hash"
    print(json.dumps({key: document[key], "runs": len(v179.SEEDS)}))


if __name__ == "__main__":
    main()
