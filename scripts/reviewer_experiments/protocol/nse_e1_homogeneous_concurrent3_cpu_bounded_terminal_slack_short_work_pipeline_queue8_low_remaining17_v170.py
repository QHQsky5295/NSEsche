from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v170 as v170,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_queue8_low_training_v155 as v155,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    _evaluate_load,
    _load_baselines,
    _metrics,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import (
    load_and_validate_manifest,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path(
    "tmp/nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_remaining17_20260901_v170"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_remaining17_plan_v170.json"
)
PLAN_SHA256 = "af0cdd1e69c94d95da35f98751b0d91b1da06d235c5034f5bd53b08441118d96"
DIAGNOSTIC_SUCCESS = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_success_v170.json"
)
DIAGNOSTIC_SUCCESS_SHA256 = (
    "d28b745c309ba36d8b8b33dfc355ab75658602de54ad73d6abeebfc2c5b77fd2"
)
DIAGNOSTIC_SUCCESS_HASH = (
    "ad5efc725381ba3336de6a310b26f18b38b7eb0cb21dae0f2a07287c404dd448"
)
DIAGNOSTIC_ROOT = v170.ROOT
DIAGNOSTIC_SEEDS = tuple(v170.SEEDS)
REMAINING_SEEDS = tuple(seed for seed in v155.SEEDS if seed not in DIAGNOSTIC_SEEDS)
ARM_ID = v170.ARM_ID
PORT = v170.PORT


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.remaining17.unbound.json",
        "prepared": root / "prepared-remaining17-v170.json",
        "schedule": root / "frozen-run-order-remaining17-v170.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.remaining17.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-remaining17-v170.json",
        "pairing": root / "pairing-audit-remaining17-v170.json",
        "blind": root / "joint-blind-audit-remaining17-v170.json",
        "result": root / "complete-training-result-v170.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v170._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V170 remaining17 plan"),
        (
            DIAGNOSTIC_SUCCESS,
            DIAGNOSTIC_SUCCESS_SHA256,
            "V170 diagnostic success receipt",
        ),
    ):
        v170._assert_file(path, sha256, label)
    success = read_json(DIAGNOSTIC_SUCCESS)
    if not (
        v170._assert_hashed(success, "receipt_hash", "V170 diagnostic success receipt")
        == DIAGNOSTIC_SUCCESS_HASH
        and success.get("diagnostic_result", {}).get("joint_diagnostic_pass") is True
        and success.get("disposition", {}).get(
            "remaining_seventeen_v170_runs_authorized"
        )
        is True
        and success.get("disposition", {}).get(
            "delete_replace_relabel_or_selectively_rerun_any_v170_seed"
        )
        is False
    ):
        raise RuntimeError("V170 remaining17 authorization changed")
    diagnostic = v170.paths(DIAGNOSTIC_ROOT)
    for path, sha256, label in (
        (
            diagnostic["ready"],
            success["ready_manifest"]["file_sha256"],
            "V170 diagnostic ready manifest",
        ),
        (
            diagnostic["blind"],
            success["result_blind_audit"]["file_sha256"],
            "V170 diagnostic blind audit",
        ),
        (
            diagnostic["result"],
            success["diagnostic_result"]["file_sha256"],
            "V170 diagnostic result",
        ),
    ):
        v170._assert_file(path, sha256, label)
    diagnostic_manifest = load_and_validate_manifest(diagnostic["ready"])
    v170._validate_product(diagnostic_manifest, references_bound=True)
    if (
        diagnostic_manifest["manifest_hash"]
        != success["ready_manifest"]["manifest_hash"]
    ):
        raise RuntimeError("V170 diagnostic manifest hash changed")
    return source


def _rewrite_remaining17(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = v155._rewrite_candidate(source, protocol_source_commit)
    rewritten["runs"] = [
        run for run in rewritten["runs"] if run["seed"] in REMAINING_SEEDS
    ]
    if [run["seed"] for run in rewritten["runs"]] != list(REMAINING_SEEDS):
        raise RuntimeError("V170 remaining17 source product changed")
    rewritten["execution"]["command_template"][-1] = str(v170.BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    for key in list(marker):
        if key.startswith("v155_"):
            marker.pop(key)
    marker["selected_source_runs"] = [
        item
        for item in marker["selected_source_runs"]
        if item["source_seed"] in REMAINING_SEEDS
    ]
    marker["selected_run_count"] = 17
    marker["selected_reference_build_count"] = 17
    marker.update(
        {
            "purpose": (
                "V170 fixed remaining-seventeen concurrent3 CPU-bounded terminal "
                "training completion; never a formal result or paper superiority claim"
            ),
            "v170_role": "result_blind_remaining17_full_cohort_completion",
            "v170_remaining17_plan_sha256": PLAN_SHA256,
            "v170_diagnostic_success_sha256": DIAGNOSTIC_SUCCESS_SHA256,
            "v170_diagnostic_success_hash": DIAGNOSTIC_SUCCESS_HASH,
            "v170_binary_source_commit": v170.BINARY_SOURCE_COMMIT,
            "v170_protocol_source_commit": protocol_source_commit,
            "v170_binary_sha256": v170.BINARY_SHA256,
            "v170_arm_id": ARM_ID,
            "v170_profile": v170.PROFILE,
            "v170_player_frontier": v170.FRONTIER,
            "v170_single_change_from_v168": v170.SINGLE_CHANGE,
            "v170_cpu_threshold": v170.CPU_THRESHOLD,
            "v170_heavy_player_threshold": v170.HEAVY_PLAYER_THRESHOLD,
            "v170_minimum_active_heavy_players": v170.MINIMUM_ACTIVE_HEAVY_PLAYERS,
            "v170_short_work_threshold": v170.SHORT_WORK_THRESHOLD,
            "v170_queue_density_threshold": v170.QUEUE_THRESHOLD,
            "v170_expected_run_count": 17,
            "v170_expected_reference_build_count": 17,
            "v170_fixed_order": list(REMAINING_SEEDS),
            "v170_diagnostic_seeds_reused_without_rerun": list(DIAGNOSTIC_SEEDS),
            "v170_candidate_performance_summaries_parsed": 0,
        }
    )
    for run in rewritten["runs"]:
        old = run.get("metadata", {})
        source_run_id = old.get("v155_source_e1_run_id")
        source_run_spec_hash = old.get("v155_source_e1_run_spec_hash")
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = v170.PROFILE
        run["metadata"] = {
            "v170_training_only": True,
            "v170_role": "result_blind_remaining17_full_cohort_completion",
            "v170_remaining17_plan_sha256": PLAN_SHA256,
            "v170_diagnostic_success_sha256": DIAGNOSTIC_SUCCESS_SHA256,
            "v170_diagnostic_success_hash": DIAGNOSTIC_SUCCESS_HASH,
            "v170_binary_source_commit": v170.BINARY_SOURCE_COMMIT,
            "v170_protocol_source_commit": protocol_source_commit,
            "v170_binary_sha256": v170.BINARY_SHA256,
            "v170_arm_id": ARM_ID,
            "v170_profile": v170.PROFILE,
            "v170_player_frontier": v170.FRONTIER,
            "v170_single_change_from_v168": v170.SINGLE_CHANGE,
            "v170_cpu_threshold": v170.CPU_THRESHOLD,
            "v170_cpu_boundary": "at_or_below_is_admitted",
            "v170_heavy_player_threshold": v170.HEAVY_PLAYER_THRESHOLD,
            "v170_minimum_active_heavy_players": v170.MINIMUM_ACTIVE_HEAVY_PLAYERS,
            "v170_overload_activation_boundary": "strictly_above_activates",
            "v170_inactive_behavior": "exact_V159_terminal_admission",
            "v170_short_work_threshold": v170.SHORT_WORK_THRESHOLD,
            "v170_queue_density_threshold": v170.QUEUE_THRESHOLD,
            "v170_queue_boundary": "below_is_strict",
            "v170_source_e1_run_id": source_run_id,
            "v170_source_e1_run_spec_hash": source_run_spec_hash,
            "v170_diagnostic_seed": False,
            "v170_candidate_performance_summaries_parsed_before_run": 0,
        }
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
        _assign_run_identity(run)
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == 17
        and [run["seed"] for run in manifest["runs"]] == list(REMAINING_SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and len(manifest.get("reference_build_dependencies", [])) == 17
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V170 exact remaining17 product changed")
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") == v170.PROFILE
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v170_heavy_player_threshold")
            == v170.HEAVY_PLAYER_THRESHOLD
            and metadata.get("v170_minimum_active_heavy_players")
            == v170.MINIMUM_ACTIVE_HEAVY_PLAYERS
            and metadata.get("v170_diagnostic_seed") is False
        ):
            raise RuntimeError(
                f"V170 remaining17 run contract changed: {run['run_id']}"
            )


def prepare_remaining17(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V170 remaining17 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_remaining17(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_LOW_REMAINING17_SCHEDULE_V170_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(REMAINING_SEEDS),
        "diagnostic_seeds_reused_without_rerun": list(DIAGNOSTIC_SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_LOW_REMAINING17_PREPARED_V170_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "diagnostic_success_sha256": DIAGNOSTIC_SUCCESS_SHA256,
        "diagnostic_success_hash": DIAGNOSTIC_SUCCESS_HASH,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(v170.BINARY_PATH.resolve()),
        "binary_sha256": v170.BINARY_SHA256,
        "python_sha256": v170.PYTHON_SHA256,
        "cargo_lock_sha256": v170.CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": v170.MODULE_CONF_SEMANTIC_HASH,
        "candidate_online_runs": 17,
        "candidate_reference_builds": 17,
        "baseline_reruns": 0,
        "diagnostic_seed_reruns": 0,
        "fixed_order": list(REMAINING_SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": v170.PROFILE,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_remaining17(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V170 remaining17 execution receipt already exists")
    prepared = read_json(output["prepared"])
    v170._assert_hashed(prepared, "receipt_hash", "V170 remaining17 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    dispatches = []
    logs = root / "execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
    for ordinal, seed in enumerate(REMAINING_SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = logs / f"{ordinal:02d}-{seed}.stderr.log"
        command = [
            str(v170.PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "run",
            str(output["ready"]),
            str(output["workspace"]),
            "--run-id",
            run["run_id"],
        ]
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(f"V170 remaining17 dispatch {seed} failed")
        canonical = output["workspace"] / "canonical" / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        if not (
            attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
        ):
            raise RuntimeError(f"V170 remaining17 {seed} did not QC-pass")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "attempt": attempt.get("attempt"),
                "classification": attempt.get("classification"),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_LOW_REMAINING17_EXECUTION_V170_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "fixed_order": list(REMAINING_SEEDS),
        "diagnostic_seeds_rerun": 0,
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _remaining17_mechanism_gate(
    audits: Sequence[Mapping[str, Any]], diagnostic_blind: Mapping[str, Any]
) -> dict[str, Any]:
    if {audit["seed"] for audit in audits} != set(REMAINING_SEEDS):
        raise RuntimeError("V170 remaining17 blind seed product changed")
    sum_keys = (
        "admitted_terminal_players_with_incomplete_parents",
        "admitted_slack_short_work_nonterminal_players",
        "rejected_frontier_players_with_incomplete_parents",
        "rejected_short_work_at_or_above_queue_threshold",
        "cpu_guard_admitted_incomplete_parent_terminal_players",
        "cpu_guard_rejected_heavy_incomplete_parent_terminal_players",
        "cpu_guard_parent_completed_heavy_terminal_bypass_players",
        "capacity_overload_heavy_incomplete_parent_terminal_players",
        "capacity_overload_guard_active_windows",
        "capacity_overload_guard_inactive_windows",
        "capacity_overload_guard_inactive_heavy_terminal_admissions",
        "below_threshold_route_windows",
        "at_or_above_threshold_route_windows",
    )
    totals = {key: sum(int(audit[key]) for audit in audits) for key in sum_keys}
    combined_active = totals["capacity_overload_guard_active_windows"] + int(
        diagnostic_blind["capacity_overload_guard_active_windows"]
    )
    combined_inactive = totals["capacity_overload_guard_inactive_windows"] + int(
        diagnostic_blind["capacity_overload_guard_inactive_windows"]
    )
    active_cpu = [
        float(audit["cpu_guard_active_admitted_normalized_cpu_max"])
        for audit in audits
        if audit["cpu_guard_active_admitted_normalized_cpu_max"] is not None
    ] + [float(diagnostic_blind["cpu_guard_active_admitted_normalized_cpu_max"])]
    rejected_cpu = [
        float(audit["cpu_guard_rejected_normalized_cpu_min"])
        for audit in audits
        if audit["cpu_guard_rejected_normalized_cpu_min"] is not None
    ] + [float(diagnostic_blind["cpu_guard_rejected_normalized_cpu_min"])]
    passed = (
        len(audits) == 17
        and sum(audit["windows"] for audit in audits) == 17_000
        and all(audit["performance_outcome_fields_parsed"] == 0 for audit in audits)
        and all(audit["frozen_v159_comparison_applicable"] is False for audit in audits)
        and combined_active > 0
        and combined_inactive > 0
        and min(
            totals["below_threshold_route_windows"],
            totals["at_or_above_threshold_route_windows"],
        )
        > 0
        and max(active_cpu) <= v170.CPU_THRESHOLD
        and min(rejected_cpu) > v170.CPU_THRESHOLD
        and diagnostic_blind.get("pass") is True
        and diagnostic_blind.get("e09_e18_exact_v159_inactive_assignment_sequences")
        is True
        and diagnostic_blind.get("e20_pre_activation_exact_v159_then_diverged") is True
    )
    return {
        **totals,
        "combined_twenty_active_windows": combined_active,
        "combined_twenty_inactive_windows": combined_inactive,
        "combined_active_admitted_normalized_cpu_max": max(active_cpu),
        "combined_rejected_normalized_cpu_min": min(rejected_cpu),
        "diagnostic_blind_audit_reused_without_performance_access": True,
        "pass": passed,
    }


def blind_audit_remaining17(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V170 remaining17 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = v170._assert_hashed(
        prepared, "receipt_hash", "V170 remaining17 prepared receipt"
    )
    execution = read_json(output["execution"])
    execution_hash = v170._assert_hashed(
        execution, "receipt_hash", "V170 remaining17 execution receipt"
    )
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed")
        and pairing.get("run_count") == 17
        and pairing.get("group_count") == 17
    ):
        raise RuntimeError("V170 remaining17 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = v170._validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=17
    )
    if [item["seed"] for item in execution["dispatches"]] != list(REMAINING_SEEDS):
        raise RuntimeError("V170 remaining17 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V170 remaining17 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V170 remaining17 has quarantined attempts")
    audits, identities = [], set()
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
            v170._audit_nash_log(canonical, run, compare_to_frozen_v159=False)
        )
    if len(identities) != 1:
        raise RuntimeError("V170 remaining17 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == v170.BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == v170.PYTHON_SHA256
        and cargo == v170.CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V170 remaining17 runtime identity changed")
    diagnostic_blind = read_json(v170.paths(DIAGNOSTIC_ROOT)["blind"])
    if not (
        v170._assert_hashed(
            diagnostic_blind, "blind_audit_hash", "V170 diagnostic blind audit"
        )
        == "e5c53b37363ac06dfff27bb1ac038ae4e0fb1786669b033a0742e03ccf5d5fe1"
        and diagnostic_blind.get("throughput_completion_latency_cost_qpr_fields_parsed")
        == 0
    ):
        raise RuntimeError("V170 diagnostic blind boundary changed")
    mechanism = _remaining17_mechanism_gate(audits, diagnostic_blind)
    if not mechanism["pass"]:
        raise RuntimeError("V170 combined twenty-run blind mechanism gate failed")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_LOW_REMAINING17_BLIND_AUDIT_V170_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "diagnostic_success_hash": DIAGNOSTIC_SUCCESS_HASH,
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_path": str(output["pairing"]),
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "new_run_count": 17,
        "reused_diagnostic_run_count": 3,
        "new_window_count": 17_000,
        **mechanism,
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": v170.PROFILE,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _load_rows(manifest: Mapping[str, Any], root: Path) -> list[dict[str, Any]]:
    rows = []
    workspace = (
        paths(root)["workspace"] if root == ROOT else v170.paths(root)["workspace"]
    )
    for run in manifest["runs"]:
        summary = (
            workspace
            / "canonical"
            / run["run_id"]
            / "reviewer_records"
            / run["run_id"]
            / "summary.json"
        )
        values = _nse_summary_metrics(read_json(summary))
        rows.append(
            {
                "load": "low",
                "seed": run["seed"],
                "run_id": run["run_id"],
                **_metrics(
                    values.get("throughput"),
                    values.get("latency_mean_ms"),
                    values.get("cost"),
                    values.get("completed"),
                ),
            }
        )
    return rows


def reveal_complete_training(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V170 complete training result already exists")
    blind = read_json(output["blind"])
    blind_hash = v170._assert_hashed(
        blind, "blind_audit_hash", "V170 remaining17 blind audit"
    )
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("pass") is True
    ):
        raise RuntimeError("V170 remaining17 blind audit did not authorize reveal")
    remaining_manifest = load_and_validate_manifest(output["ready"])
    diagnostic_manifest = load_and_validate_manifest(
        v170.paths(DIAGNOSTIC_ROOT)["ready"]
    )
    rows = _load_rows(remaining_manifest, root) + _load_rows(
        diagnostic_manifest, DIAGNOSTIC_ROOT
    )
    if len(rows) != 20 or {row["seed"] for row in rows} != set(v155.SEEDS):
        raise RuntimeError("V170 complete training cohort changed")
    rows.sort(key=lambda row: row["seed"])
    evaluation = _evaluate_load("low", rows, _load_baselines())
    passed = evaluation["all_three_metric_gates_pass"] and blind["pass"]
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_LOW_COMPLETE_TRAINING_RESULT_V170_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "diagnostic_success_hash": DIAGNOSTIC_SUCCESS_HASH,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "new_remaining17_run_count": 17,
        "reused_diagnostic_run_count": 3,
        "baseline_rerun_count": 0,
        "candidate_rows": rows,
        "low_evaluation": evaluation,
        "complete_training_joint_pass": passed,
        "disposition": (
            "freeze_complete_v170_low_cohort_and_authorize_separate_final_data_boundary"
            if passed
            else "retain_all_twenty_valid_v170_runs_and_require_new_causal_plan"
        ),
        "homogeneous_low_training_closed": passed,
        "final_data_boundary_authorized": passed,
        "middle_or_later_execution_authorized": False,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("prepare", "execute", "blind-audit", "reveal")
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    if action == "prepare":
        document, key = prepare_remaining17(), "receipt_hash"
    elif action == "execute":
        document, key = execute_remaining17(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_remaining17(), "blind_audit_hash"
    else:
        document, key = reveal_complete_training(), "result_hash"
    print(
        {
            key: document[key],
            "runs": (
                17 if action != "reveal" else len(document.get("candidate_rows", []))
            ),
        }
    )


if __name__ == "__main__":
    main()
