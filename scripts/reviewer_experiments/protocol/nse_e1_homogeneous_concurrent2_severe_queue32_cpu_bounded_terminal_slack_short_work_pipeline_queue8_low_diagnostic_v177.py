from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_requestcohort1_shortest_request_least_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v175 as v175,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v176 as v176base,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v159 as v159,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_queue8_low_training_v155 as v155base,
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
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    PYTHON_PATH,
    PYTHON_SHA256,
    SOURCE_MANIFEST_HASH,
    SOURCE_MANIFEST_SHA256,
    SOURCE_PAIRING_SHA256,
    _assert_file,
    _assert_hashed,
    _validate_reference_catalog,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_legacy_profile_training_prepare_v150 import (
    COMMON_ENVIRONMENT,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_queue8_low_training_v155 import (
    CARGO_LOCK_SHA256,
    MODULE_CONF_SEMANTIC_HASH,
    _assert_json_semantic,
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
    "tmp/nse_e1_homogeneous_concurrent2_severe_queue32_cpu_bounded_terminal_low_diagnostic_20260901_v177"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_severe_queue32_cpu_bounded_terminal_low_diagnostic_plan_v177.json"
)
PLAN_SHA256 = "085b3456041fcc2ac52f4e8aedc6d61d02b65dc51de881a9790221ff10f6e223"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_severe_queue32_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_implementation_v177.json"
)
IMPLEMENTATION_SHA256 = (
    "86debcb8220c96c7bdfd40caa111bd31e9d52eb8ea8eb2c9b2f6d1a49f73c00b"
)
V170_COMPLETE_RESULT = v175.V170_COMPLETE_RESULT
V170_COMPLETE_RESULT_SHA256 = v175.V170_COMPLETE_RESULT_SHA256
V170_COMPLETE_RESULT_HASH = v175.V170_COMPLETE_RESULT_HASH
V176_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_failure_v176.json"
)
V176_FAILURE_SHA256 = "1c36ed8890a5a402def2691fbbd7f75152a3ae3025fb04b83022b5dade900638"
V176_FAILURE_HASH = "7e4a3c05b73dd5bc6d366980b48201172bde77e3765faf9abaf8ad624f152e04"
V176_RESULT = v176base.ROOT / "diagnostic-result-v176.json"
V176_RESULT_SHA256 = "a84a89faa95d82129ebbef2619ea9cd2b7d6bf0fbfc93aca689b6d3ceb24a9c2"
V176_RESULT_HASH = "faac945e6b3dcc937e37d64e7a0c64cde3305950ce1da9bf733710c02aab8199"

SEEDS = ("E06", "E10", "E11", "E12", "E15", "E18")
V176_REUSE_SEEDS = ("E01", "E05", "E07", "E08", "E14")
V170_REUSE_SEEDS = ("E02", "E03", "E04", "E09", "E13", "E16", "E17", "E19", "E20")
THROUGHPUT_SIX_SEED_SUM_GATE = 5.845999999999999
QPR_SIX_SEED_SUM_GATE = 0.12377280163791829
THROUGHPUT_SIX_SEED_PAIRED_WIN_GATE = 3
QPR_SIX_SEED_PAIRED_WIN_GATE = 2

ARM_ID = "v177-low-srpt-slack-concurrent2-severe-queue32-cpu-bounded-terminal-short5p5-pipeline-hiku2-ocs-queue8"
PROFILE = "srpt_slack_concurrent2_severe_queue32_cpu_bounded_terminal_short5p5_pipeline_hiku2_ocs_queue8"
FRONTIER = (
    "parents_completed_or_concurrent2_severe_queue32_cpu_bounded_terminal_or_slack_short_work_"
    "parents_scheduled"
)
SINGLE_CHANGE = (
    "V176_all_or_none_guard_plus_the_same_guard_for_exactly_one_heavy_player_"
    "only_when_current_operational_queue_density_is_at_least_32"
)
TERMINAL_DEFINITION = (
    "admit_all_parents-completed_players;activate_the_V168_incomplete-parent-terminal_"
    "CPU_bound_when_current_heavy_terminal_player_count_strictly_exceeds_one_or_when_"
    "it_equals_one_and_current_operational_queue_density_is_at_least_32;"
    "otherwise_retain_V159_terminal_admission;retain_V159_nonterminal_short-work_"
    "frontier"
)
CPU_THRESHOLD = 1.0
HEAVY_PLAYER_THRESHOLD = 1
MINIMUM_ACTIVE_HEAVY_PLAYERS = 1
SEVERE_QUEUE_THRESHOLD = 32.0
SHORT_WORK_THRESHOLD = v159.SHORT_WORK_THRESHOLD
QUEUE_THRESHOLD = v159.QUEUE_THRESHOLD
LOW_EXPERT = v159.LOW_EXPERT
HIGH_EXPERT = v159.HIGH_EXPERT
WORK_DEFINITION = v159.WORK_DEFINITION
PORT = v159.PORT

BINARY_SOURCE_COMMIT = "93337de31c3a83bf29706bad55698acc810d6571"
BINARY_PATH = Path("serverless_sim/target_e1_v177/release/serverless_sim.exe")
BINARY_SHA256 = "96cfb67f34309c2d3e2619c342187ae535ba1b601af2b605a18d2c3181cf187b"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v177.json",
        "schedule": root / "frozen-run-order-v177.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v177.json",
        "pairing": root / "pairing-audit-v177.json",
        "blind": root / "joint-blind-audit-v177.json",
        "result": root / "diagnostic-result-v177.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v159._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V177 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V177 implementation receipt"),
        (V170_COMPLETE_RESULT, V170_COMPLETE_RESULT_SHA256, "V170 complete result"),
        (V176_FAILURE, V176_FAILURE_SHA256, "V176 failure receipt"),
        (V176_RESULT, V176_RESULT_SHA256, "V176 diagnostic result"),
        (BINARY_PATH, BINARY_SHA256, "V177 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    implementation = read_json(IMPLEMENTATION)
    change = implementation.get("single_scientific_change", {})
    telemetry = implementation.get("telemetry_contract", {})
    if not (
        _assert_hashed(implementation, "receipt_hash", "V177 implementation receipt")
        == "28ecf2108dc3562e8e2167efac7d5bb2b1b2227f7c5730d7ba3eb7c4956af5bb"
        and implementation.get("implementation_commit") == BINARY_SOURCE_COMMIT
        and implementation.get("plan_file_sha256") == PLAN_SHA256
        and implementation.get("isolated_release", {}).get("sha256") == BINARY_SHA256
        and change.get("to_profile") == PROFILE
        and change.get("severe_queue_density_threshold") == SEVERE_QUEUE_THRESHOLD
        and change.get("severe_queue_density_derivation")
        == "4_times_frozen_queue_routing_threshold_8"
        and change.get("severe_queue_boundary") == "at_or_above_activates"
        and change.get("ordinary_single_behavior") == "exact_V159_terminal_admission"
        and change.get("active_heavy_behavior")
        == "exact_V168_all_or_none_CPU_guard_rejection"
        and change.get("active_heavy_admissions") == 0
        and change.get("cpu_ratio_threshold") == CPU_THRESHOLD
        and change.get("uses_seed_load_dag_function_or_performance_labels") is False
        and change.get("uses_completion_or_performance_outcomes") is False
        and telemetry.get("version") == "V177"
        and telemetry.get("player_frontier") == FRONTIER
        and telemetry.get("run_config_capacity_threshold")
        == "fixed_one_current_heavy_player"
        and telemetry.get("run_config_minimum_active_heavy_player_count") == 1
        and telemetry.get("run_config_severe_single_queue_density_threshold")
        == SEVERE_QUEUE_THRESHOLD
        and telemetry.get("run_config_active_heavy_admission_policy") is None
        and telemetry.get("run_config_active_heavy_admission_quota") is None
    ):
        raise RuntimeError("V177 implementation boundary changed")
    failure = read_json(V176_FAILURE)
    if not (
        _assert_hashed(failure, "receipt_hash", "V176 failure receipt")
        == V176_FAILURE_HASH
        and failure.get("diagnostic_result", {}).get("joint_pass") is False
        and failure.get("diagnostic_result", {}).get(
            "hybrid_twenty_throughput_gate_pass"
        )
        is True
        and failure.get("diagnostic_result", {}).get("hybrid_twenty_qpr_gate_pass")
        is False
        and failure.get("disposition", {}).get("retain_all_six_valid_v176_runs") is True
        and failure.get("disposition", {}).get(
            "delete_replace_relabel_or_selectively_rerun_any_v176_seed"
        )
        is False
    ):
        raise RuntimeError("V176 frozen failure boundary changed")
    complete = read_json(V170_COMPLETE_RESULT)
    if (
        _assert_hashed(complete, "result_hash", "V170 complete result")
        != V170_COMPLETE_RESULT_HASH
    ):
        raise RuntimeError("V170 complete result changed")
    v176_result = read_json(V176_RESULT)
    if (
        _assert_hashed(v176_result, "result_hash", "V176 diagnostic result")
        != V176_RESULT_HASH
        or v176_result.get("joint_diagnostic_pass") is not False
    ):
        raise RuntimeError("V176 diagnostic result changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _metadata(protocol_source_commit: str, source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "v177_training_only": True,
        "v177_role": "result_blind_concurrent2_severe_queue32_cpu_bounded_terminal_falsification",
        "v177_plan_sha256": PLAN_SHA256,
        "v177_implementation_sha256": IMPLEMENTATION_SHA256,
        "v177_binary_source_commit": BINARY_SOURCE_COMMIT,
        "v177_protocol_source_commit": protocol_source_commit,
        "v177_binary_sha256": BINARY_SHA256,
        "v177_arm_id": ARM_ID,
        "v177_profile": PROFILE,
        "v177_player_frontier": FRONTIER,
        "v177_single_change_from_v176": SINGLE_CHANGE,
        "v177_cpu_threshold": CPU_THRESHOLD,
        "v177_cpu_boundary": "at_or_below_is_admitted",
        "v177_heavy_player_threshold": HEAVY_PLAYER_THRESHOLD,
        "v177_minimum_active_heavy_players": MINIMUM_ACTIVE_HEAVY_PLAYERS,
        "v177_overload_activation_boundary": "heavy_count_strictly_above_one_or_exactly_one_with_queue_density_at_or_above_32_activates",
        "v177_severe_queue_density_threshold": SEVERE_QUEUE_THRESHOLD,
        "v177_severe_queue_density_source": "current_pending_plus_runnable_tasks_per_node",
        "v177_severe_queue_boundary": "at_or_above_activates",
        "v177_inactive_behavior": "exact_V159_terminal_admission",
        "v177_active_heavy_admission_policy": "all_current_heavy_incomplete_parent_terminal_players_rejected",
        "v177_active_heavy_admission_quota": None,
        "v177_short_work_threshold": SHORT_WORK_THRESHOLD,
        "v177_queue_density_threshold": QUEUE_THRESHOLD,
        "v177_queue_boundary": "below_is_strict",
        "v177_source_e1_run_id": source.get("v155_source_e1_run_id"),
        "v177_source_e1_run_spec_hash": source.get("v155_source_e1_run_spec_hash"),
        "v177_candidate_performance_summaries_parsed_before_run": 0,
        "v177_remaining_nine_authorized": False,
        "v177_confirmation_inputs_generated": False,
    }


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = v155base._rewrite_candidate(source, protocol_source_commit)
    by_seed = {run["seed"]: run for run in rewritten["runs"]}
    if set(by_seed) != {f"E{index:02d}" for index in range(1, 21)}:
        raise RuntimeError("V155 complete low source product changed")
    rewritten["runs"] = [by_seed[seed] for seed in SEEDS]
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    lineage = {item["source_seed"]: item for item in marker["selected_source_runs"]}
    marker["selected_source_runs"] = [lineage[seed] for seed in SEEDS]
    for key in list(marker):
        if key.startswith("v155_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": "V177 outcome-disclosed six-seed training diagnosis; never a formal result or paper superiority claim",
            "v177_role": "result_blind_concurrent2_severe_queue32_cpu_bounded_terminal_falsification",
            "v177_plan_sha256": PLAN_SHA256,
            "v177_implementation_sha256": IMPLEMENTATION_SHA256,
            "v177_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v177_protocol_source_commit": protocol_source_commit,
            "v177_binary_sha256": BINARY_SHA256,
            "v177_arm_id": ARM_ID,
            "v177_profile": PROFILE,
            "v177_player_frontier": FRONTIER,
            "v177_single_change_from_v176": SINGLE_CHANGE,
            "v177_cpu_threshold": CPU_THRESHOLD,
            "v177_heavy_player_threshold": HEAVY_PLAYER_THRESHOLD,
            "v177_minimum_active_heavy_players": MINIMUM_ACTIVE_HEAVY_PLAYERS,
            "v177_overload_activation_boundary": "heavy_count_strictly_above_one_or_exactly_one_with_queue_density_at_or_above_32_activates",
            "v177_severe_queue_density_threshold": SEVERE_QUEUE_THRESHOLD,
            "v177_severe_queue_density_source": "current_pending_plus_runnable_tasks_per_node",
            "v177_severe_queue_boundary": "at_or_above_activates",
            "v177_inactive_behavior": "exact_V159_terminal_admission",
            "v177_active_heavy_admission_policy": "all_current_heavy_incomplete_parent_terminal_players_rejected",
            "v177_active_heavy_admission_quota": None,
            "v177_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v177_queue_density_threshold": QUEUE_THRESHOLD,
            "v177_queue_boundary": "below_is_strict",
            "v177_environment": COMMON_ENVIRONMENT,
            "v177_expected_run_count": len(SEEDS),
            "v177_expected_reference_build_count": len(SEEDS),
            "v177_fixed_order": list(SEEDS),
            "v177_candidate_performance_summaries_parsed": 0,
            "v177_remaining_nine_authorized": False,
            "v177_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = _metadata(protocol_source_commit, run.get("metadata", {}))
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
    marker["selected_run_count"] = len(SEEDS)
    marker["selected_reference_build_count"] = len(SEEDS)
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == len(SEEDS)
        and [run["seed"] for run in manifest["runs"]] == list(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and len(manifest.get("reference_build_dependencies", [])) == len(SEEDS)
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V177 exact E06/E10/E11/E12/E15/E18 product changed")
    expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and all(run["environment"].get(k) == v for k, v in expected.items())
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v177_profile") == PROFILE
            and metadata.get("v177_player_frontier") == FRONTIER
            and metadata.get("v177_cpu_threshold") == CPU_THRESHOLD
            and metadata.get("v177_heavy_player_threshold") == HEAVY_PLAYER_THRESHOLD
            and metadata.get("v177_minimum_active_heavy_players")
            == MINIMUM_ACTIVE_HEAVY_PLAYERS
            and metadata.get("v177_overload_activation_boundary")
            == "heavy_count_strictly_above_one_or_exactly_one_with_queue_density_at_or_above_32_activates"
            and metadata.get("v177_severe_queue_density_threshold")
            == SEVERE_QUEUE_THRESHOLD
            and metadata.get("v177_severe_queue_density_source")
            == "current_pending_plus_runnable_tasks_per_node"
            and metadata.get("v177_severe_queue_boundary") == "at_or_above_activates"
            and metadata.get("v177_inactive_behavior")
            == "exact_V159_terminal_admission"
            and metadata.get("v177_active_heavy_admission_policy")
            == "all_current_heavy_incomplete_parent_terminal_players_rejected"
            and metadata.get("v177_active_heavy_admission_quota") is None
            and metadata.get("v177_short_work_threshold") == SHORT_WORK_THRESHOLD
            and metadata.get("v177_queue_density_threshold") == QUEUE_THRESHOLD
        ):
            raise RuntimeError(f"V177 run contract changed: {run.get('run_id')}")


def prepare_v177(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V177 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_SEVERE_QUEUE32_CPU_BOUNDED_TERMINAL_LOW_SCHEDULE_V177_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_SEVERE_QUEUE32_CPU_BOUNDED_TERMINAL_LOW_PREPARED_V177_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": MODULE_CONF_SEMANTIC_HASH,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "v176_diagnostic_failure_file_sha256": V176_FAILURE_SHA256,
        "v176_diagnostic_failure_hash": V176_FAILURE_HASH,
        "v176_diagnostic_result_file_sha256": V176_RESULT_SHA256,
        "v176_diagnostic_result_hash": V176_RESULT_HASH,
        "candidate_online_runs": len(SEEDS),
        "candidate_reference_builds": len(SEEDS),
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "cpu_threshold": CPU_THRESHOLD,
        "heavy_player_threshold": HEAVY_PLAYER_THRESHOLD,
        "minimum_active_heavy_players": MINIMUM_ACTIVE_HEAVY_PLAYERS,
        "overload_activation_boundary": "heavy_count_strictly_above_one_or_exactly_one_with_queue_density_at_or_above_32_activates",
        "severe_queue_density_threshold": SEVERE_QUEUE_THRESHOLD,
        "severe_queue_density_source": "current_pending_plus_runnable_tasks_per_node",
        "severe_queue_boundary": "at_or_above_activates",
        "inactive_behavior": "exact_V159_terminal_admission",
        "active_heavy_admission_policy": "all_current_heavy_incomplete_parent_terminal_players_rejected",
        "active_heavy_admission_quota": None,
        "short_work_threshold": SHORT_WORK_THRESHOLD,
        "queue_density_threshold": QUEUE_THRESHOLD,
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v177(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V177 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V177 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    logs = root / "execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = logs / f"{ordinal:02d}-{seed}.stderr.log"
        command = [
            str(PYTHON_PATH),
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
            raise RuntimeError(f"V177 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V177 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "stdout_path": str(stdout_path),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_path": str(stderr_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_SEVERE_QUEUE32_CPU_BOUNDED_TERMINAL_LOW_EXECUTION_V177_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": len(SEEDS),
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _assignment_sequence_sha256(values: Sequence[int]) -> str:
    return hashlib.sha256("\n".join(map(str, values)).encode("utf-8")).hexdigest()


def _finite_optional(value: Any, label: str) -> float | None:
    return v159._finite_optional(value, label)


def _frozen_base_assignment_hashes(seed: str) -> tuple[int, ...]:
    if seed != "E10":
        return v175._frozen_v170_assignment_hashes(seed)
    manifest = load_and_validate_manifest(v176base.paths()["ready"])
    run = next((item for item in manifest["runs"] if item.get("seed") == seed), None)
    if run is None:
        raise RuntimeError("frozen V176 E10 run is missing")
    log = (
        v176base.paths()["workspace"]
        / "canonical"
        / run["run_id"]
        / "reviewer_records"
        / run["run_id"]
        / "nash_metrics.jsonl.gz"
    )
    hashes: list[int] = []
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            value = event.get("decision", {}).get("assignment_hash")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise RuntimeError("frozen V176 E10 assignment hash changed")
            hashes.append(value)
    if len(hashes) != 1000:
        raise RuntimeError("frozen V176 E10 assignment cardinality changed")
    return tuple(hashes)


def _audit_nash_log(
    canonical: Path,
    run: Mapping[str, Any],
    *,
    frozen_base: Sequence[int] | None = None,
) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    counts = {"run_config": 0, "window": 0, "run_summary": 0, "function_profile": 0}
    totals = {
        "terminal": 0,
        "short": 0,
        "rejected": 0,
        "queue_rejected": 0,
        "incomplete": 0,
        "guard_admitted": 0,
        "guard_rejected": 0,
        "guard_bypass": 0,
        "heavy": 0,
        "active_windows": 0,
        "inactive_windows": 0,
        "exact_one_windows": 0,
        "severe_exact_one_windows": 0,
        "severe_exact_one_heavy_rejections": 0,
        "ordinary_exact_one_windows": 0,
        "ordinary_exact_one_heavy_admissions": 0,
        "exact_two_windows": 0,
        "exact_two_heavy_rejections": 0,
        "inactive_heavy_admissions": 0,
        "low_routes": 0,
        "high_routes": 0,
        "reference_available": 0,
        "reference_not_requested": 0,
    }
    extrema: dict[str, float | None] = {
        "admitted_work_max": None,
        "rejected_work_min": None,
        "admitted_density_max": None,
        "rejected_density_min": None,
        "guard_admitted_ratio_max": None,
        "guard_active_admitted_ratio_max": None,
        "guard_inactive_admitted_ratio_max": None,
        "guard_rejected_ratio_min": None,
    }
    decision_hashes: list[int] = []
    first_severe_exact_one_frame: int | None = None

    def update_max(key: str, value: float | None) -> None:
        if value is not None:
            extrema[key] = value if extrema[key] is None else max(extrema[key], value)

    def update_min(key: str, value: float | None) -> None:
        if value is not None:
            extrema[key] = value if extrema[key] is None else min(extrema[key], value)

    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind not in counts:
                raise RuntimeError(f"unexpected V177 Nash observation kind: {kind}")
            counts[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                guard = contract.get("cpu_bounded_terminal_guard", {})
                activation = guard.get("capacity_overload_activation", {})
                checks = (
                    ("scheduler", event.get("scheduler"), "sche_nash"),
                    ("profile", event.get("operational_expert_proxy"), PROFILE),
                    (
                        "reference_mode",
                        event.get("reference", {}).get("mode"),
                        "offline_required",
                    ),
                    (
                        "reference_loaded",
                        event.get("reference", {}).get("offline_load_ok"),
                        True,
                    ),
                    ("version", contract.get("version"), "V177"),
                    (
                        "queue_threshold",
                        contract.get("queue_density_threshold"),
                        QUEUE_THRESHOLD,
                    ),
                    ("low_expert", contract.get("below_threshold_expert"), LOW_EXPERT),
                    (
                        "high_expert",
                        contract.get("at_or_above_threshold_expert"),
                        HIGH_EXPERT,
                    ),
                    ("frontier", contract.get("player_frontier"), FRONTIER),
                    (
                        "single_change",
                        contract.get("single_change_from_v155"),
                        SINGLE_CHANGE,
                    ),
                    (
                        "terminal_definition",
                        contract.get("terminal_pipeline_definition"),
                        TERMINAL_DEFINITION,
                    ),
                    (
                        "short_threshold",
                        contract.get("short_work_pipeline_remaining_work_threshold"),
                        SHORT_WORK_THRESHOLD,
                    ),
                    (
                        "short_queue_threshold",
                        contract.get("short_work_pipeline_queue_density_threshold"),
                        QUEUE_THRESHOLD,
                    ),
                    (
                        "short_queue_boundary",
                        contract.get("short_work_pipeline_queue_boundary"),
                        "below_is_strict",
                    ),
                    (
                        "work_definition",
                        contract.get("short_work_definition"),
                        WORK_DEFINITION,
                    ),
                    (
                        "cpu_threshold",
                        guard.get("normalized_cpu_threshold"),
                        CPU_THRESHOLD,
                    ),
                    ("cpu_boundary", guard.get("boundary"), "at_or_below_is_admitted"),
                    (
                        "cpu_numerator",
                        guard.get("numerator"),
                        "immutable_function_cpu_work",
                    ),
                    (
                        "cpu_denominator",
                        guard.get("denominator"),
                        "current_cluster_mean_node_cpu_capacity",
                    ),
                    ("parent_bypass", guard.get("parents_completed_bypass"), True),
                    (
                        "guard_outcome_free",
                        guard.get("uses_completion_or_performance_outcomes"),
                        False,
                    ),
                    (
                        "heavy_definition",
                        activation.get("heavy_player_definition"),
                        "collectable_incomplete-parent_terminal_player_with_immutable_function_cpu_work_over_current_cluster_mean_node_cpu_capacity_strictly_above_one",
                    ),
                    (
                        "capacity_threshold",
                        activation.get("capacity_threshold"),
                        "fixed_one_current_heavy_player",
                    ),
                    (
                        "fixed_threshold",
                        activation.get("fixed_heavy_player_count_threshold"),
                        HEAVY_PLAYER_THRESHOLD,
                    ),
                    (
                        "minimum_active",
                        activation.get("minimum_active_heavy_player_count"),
                        MINIMUM_ACTIVE_HEAVY_PLAYERS,
                    ),
                    (
                        "activation_boundary",
                        activation.get("activation_boundary"),
                        "heavy_player_count_strictly_above_one_or_exactly_one_with_operational_queue_density_at_least_32",
                    ),
                    (
                        "severe_queue_threshold",
                        activation.get("severe_single_queue_density_threshold"),
                        SEVERE_QUEUE_THRESHOLD,
                    ),
                    (
                        "severe_queue_source",
                        activation.get("severe_single_queue_density_source"),
                        "current_pending_plus_runnable_tasks_per_node",
                    ),
                    (
                        "severe_queue_boundary",
                        activation.get("severe_single_queue_boundary"),
                        "at_or_above_activates",
                    ),
                    (
                        "inactive_behavior",
                        activation.get("inactive_behavior"),
                        "V159_terminal_admission",
                    ),
                    (
                        "active_policy",
                        activation.get("active_heavy_admission_policy"),
                        None,
                    ),
                    (
                        "active_quota",
                        activation.get("active_heavy_admission_quota"),
                        None,
                    ),
                    (
                        "active_quota_unit",
                        activation.get("active_heavy_admission_quota_unit"),
                        None,
                    ),
                    ("quota_order", activation.get("quota_selection_order"), None),
                    (
                        "label_free",
                        activation.get(
                            "uses_seed_load_dag_function_or_performance_labels"
                        ),
                        False,
                    ),
                    (
                        "contract_outcome_free",
                        contract.get("uses_completed_request_outcomes"),
                        False,
                    ),
                    (
                        "reference_policy_independent",
                        contract.get("reference_policy_independent"),
                        True,
                    ),
                )
                mismatches = [
                    label for label, actual, expected in checks if actual != expected
                ]
                if mismatches:
                    raise RuntimeError(
                        "V177 run_config contract changed: " + ",".join(mismatches)
                    )
                continue
            if kind == "run_summary":
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V177 Nash terminal marker changed")
                continue
            if kind == "function_profile":
                continue

            frame = counts["window"] - 1
            if event.get("frame") != frame:
                raise RuntimeError("V177 scheduler window sequence changed")
            decision = event.get("decision", {})
            decision_hash = decision.get("assignment_hash")
            if (
                isinstance(decision_hash, bool)
                or not isinstance(decision_hash, int)
                or decision_hash < 0
                or decision.get("player_frontier") != FRONTIER
            ):
                raise RuntimeError("V177 decision frontier/hash changed")
            decision_hashes.append(decision_hash)
            frontier = decision.get("terminal_pipeline_frontier", {})
            terminal = v159._count(
                frontier.get("admitted_terminal_players_with_incomplete_parents"),
                "terminal admission count",
            )
            short = v159._count(
                frontier.get(
                    "admitted_short_work_nonterminal_players_with_incomplete_parents"
                ),
                "short-work admission count",
            )
            rejected = v159._count(
                frontier.get("rejected_nonterminal_players_with_incomplete_parents"),
                "frontier rejection count",
            )
            incomplete = v159._count(
                decision.get("pipeline_players_with_incomplete_parents"),
                "pipeline incomplete-parent count",
            )
            admitted_work = _finite_optional(
                frontier.get("admitted_short_work_remaining_work_max"),
                "admitted work maximum",
            )
            rejected_work = _finite_optional(
                frontier.get("rejected_nonterminal_remaining_work_min"),
                "rejected work minimum",
            )
            queue_gate = frontier.get("short_work_queue_gate", {})
            queue_rejected = v159._count(
                queue_gate.get("rejected_short_work_at_or_above_threshold"),
                "queue-gated rejection count",
            )
            admitted_density = _finite_optional(
                queue_gate.get("admitted_short_work_queue_density_max"),
                "admitted queue-density maximum",
            )
            rejected_density = _finite_optional(
                queue_gate.get("rejected_short_work_queue_density_min"),
                "rejected queue-density minimum",
            )
            guard = frontier.get("cpu_bounded_terminal_guard", {})
            guard_admitted = v159._count(
                guard.get("admitted_incomplete_parent_terminal_players"),
                "CPU-guard admitted count",
            )
            guard_rejected = v159._count(
                guard.get("rejected_heavy_incomplete_parent_terminal_players"),
                "CPU-guard rejected count",
            )
            guard_bypass = v159._count(
                guard.get("parents_completed_heavy_terminal_bypass_players"),
                "CPU-guard parent-completed bypass count",
            )
            admitted_ratio = _finite_optional(
                guard.get("admitted_normalized_cpu_max"),
                "CPU-guard admitted ratio maximum",
            )
            rejected_ratio = _finite_optional(
                guard.get("rejected_normalized_cpu_min"),
                "CPU-guard rejected ratio minimum",
            )
            activation = guard.get("capacity_overload_activation", {})
            heavy = v159._count(
                activation.get("heavy_incomplete_parent_terminal_players"),
                "capacity-overload heavy player count",
            )
            inactive_admissions = v159._count(
                activation.get("guard_inactive_heavy_terminal_admissions"),
                "capacity-overload inactive heavy admission count",
            )
            active = activation.get("guard_active")
            inactive = activation.get("guard_inactive")
            activation_density = _finite_optional(
                activation.get("operational_queue_density"),
                "capacity-overload operational queue density",
            )
            primary_active = activation.get("primary_heavy_count_activation")
            severe_single_active = activation.get("severe_single_activation")
            expected_primary_active = heavy > HEAVY_PLAYER_THRESHOLD
            expected_severe_single_active = (
                heavy == 1
                and activation_density is not None
                and activation_density >= SEVERE_QUEUE_THRESHOLD
            )
            expected_active = expected_primary_active or expected_severe_single_active
            if not (
                frontier.get("enabled") is True
                and frontier.get("definition") == FRONTIER
                and frontier.get("short_work_remaining_work_threshold")
                == SHORT_WORK_THRESHOLD
                and frontier.get("terminal_topology_source")
                == "immutable_function_children_is_empty"
                and frontier.get("uses_completion_or_performance_outcomes") is False
                and guard.get("enabled") is True
                and guard.get("normalized_cpu_threshold") == CPU_THRESHOLD
                and guard.get("boundary") == "at_or_below_is_admitted"
                and guard.get("numerator") == "immutable_function_cpu_work"
                and guard.get("denominator") == "current_cluster_mean_node_cpu_capacity"
                and guard.get("uses_completion_or_performance_outcomes") is False
                and activation.get("enabled") is True
                and activation.get("node_count_threshold") == 20
                and activation.get("heavy_player_count_threshold")
                == HEAVY_PLAYER_THRESHOLD
                and activation.get("minimum_active_heavy_player_count")
                == MINIMUM_ACTIVE_HEAVY_PLAYERS
                and activation.get("threshold_kind") == "fixed_one_current_heavy_player"
                and activation.get("activation_boundary")
                == "heavy_count_strictly_above_one_or_exactly_one_with_queue_density_at_or_above_32_activates"
                and activation.get("operational_queue_density_source")
                == "current_pending_plus_runnable_tasks_per_node"
                and activation.get("severe_single_queue_density_threshold")
                == SEVERE_QUEUE_THRESHOLD
                and activation.get("severe_single_queue_boundary")
                == "at_or_above_activates"
                and activation.get("active_heavy_admission_policy") is None
                and activation.get("active_heavy_admission_quota") is None
                and activation.get("active_heavy_admission_quota_unit") is None
                and activation.get("quota_selection_order") is None
                and activation.get("active_heavy_quota_selected_players") is None
                and activation.get("active_heavy_quota_admitted_players") is None
                and activation.get("active_heavy_quota_rejected_excess_players") is None
                and activation.get("active_heavy_selected_request_count") is None
                and activation.get("active_heavy_selected_request_candidate_players")
                is None
                and isinstance(active, bool)
                and isinstance(inactive, bool)
                and isinstance(primary_active, bool)
                and isinstance(severe_single_active, bool)
                and inactive is (not active)
                and primary_active is expected_primary_active
                and severe_single_active is expected_severe_single_active
                and active is expected_active
                and activation.get("uses_seed_load_dag_function_or_performance_labels")
                is False
                and guard_admitted == terminal
                and (guard_admitted == 0) == (admitted_ratio is None)
                and (guard_rejected == 0) == (rejected_ratio is None)
                and (
                    not active
                    or admitted_ratio is None
                    or admitted_ratio <= CPU_THRESHOLD
                )
                and (rejected_ratio is None or rejected_ratio > CPU_THRESHOLD)
                and (
                    active
                    and guard_rejected == heavy
                    and inactive_admissions == 0
                    or inactive
                    and guard_rejected == 0
                    and inactive_admissions == heavy
                )
                and queue_gate.get("enabled") is True
                and queue_gate.get("threshold") == QUEUE_THRESHOLD
                and queue_gate.get("boundary") == "below_is_strict"
                and incomplete <= terminal + short
                and queue_rejected <= rejected
                and (short == 0) == (admitted_work is None and admitted_density is None)
                and (queue_rejected == 0) == (rejected_density is None)
                and (admitted_work is None or admitted_work <= SHORT_WORK_THRESHOLD)
                and (admitted_density is None or admitted_density < QUEUE_THRESHOLD)
                and (rejected_work is None or rejected_work > SHORT_WORK_THRESHOLD)
                and (rejected_density is None or rejected_density >= QUEUE_THRESHOLD)
                and decision.get("pipeline_observation_fields_drive_future_windows")
                is False
            ):
                raise RuntimeError("V177 CPU/slack/queue frontier evidence changed")
            if heavy == 2:
                totals["exact_two_windows"] += 1
                totals["exact_two_heavy_rejections"] += guard_rejected
            if heavy == 1:
                totals["exact_one_windows"] += 1
                if severe_single_active:
                    totals["severe_exact_one_windows"] += 1
                    totals["severe_exact_one_heavy_rejections"] += guard_rejected
                    if first_severe_exact_one_frame is None:
                        first_severe_exact_one_frame = frame
                else:
                    totals["ordinary_exact_one_windows"] += 1
                    totals["ordinary_exact_one_heavy_admissions"] += inactive_admissions
            totals["terminal"] += terminal
            totals["short"] += short
            totals["rejected"] += rejected
            totals["queue_rejected"] += queue_rejected
            totals["incomplete"] += incomplete
            totals["guard_admitted"] += guard_admitted
            totals["guard_rejected"] += guard_rejected
            totals["guard_bypass"] += guard_bypass
            totals["heavy"] += heavy
            totals["active_windows"] += int(active)
            totals["inactive_windows"] += int(inactive)
            totals["inactive_heavy_admissions"] += inactive_admissions
            update_max("admitted_work_max", admitted_work)
            update_min("rejected_work_min", rejected_work)
            update_max("admitted_density_max", admitted_density)
            update_min("rejected_density_min", rejected_density)
            update_max("guard_admitted_ratio_max", admitted_ratio)
            update_max(
                "guard_active_admitted_ratio_max"
                if active
                else "guard_inactive_admitted_ratio_max",
                admitted_ratio,
            )
            update_min("guard_rejected_ratio_min", rejected_ratio)
            route = decision.get("srpt_hiku2_ocs_queue_router", {})
            density = route.get("queue_density")
            if not (
                route.get("enabled") is True
                and isinstance(density, (int, float))
                and not isinstance(density, bool)
                and math.isfinite(float(density))
                and route.get("queue_density_threshold") == QUEUE_THRESHOLD
                and route.get("player_frontier") == FRONTIER
                and route.get("dependency_pipeline_frontier") is True
                and route.get("uses_completion_outcomes") is False
            ):
                raise RuntimeError("V177 route telemetry is incomplete")
            if activation_density is None or float(density) != activation_density:
                raise RuntimeError("V177 guard/router queue-density telemetry diverged")
            expected = LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
            if route.get("selected_expert") != expected:
                raise RuntimeError("V177 route does not match queue density")
            totals["low_routes"] += expected == LOW_EXPERT
            totals["high_routes"] += expected == HIGH_EXPERT
            social = event.get("social", {})
            key = social.get("reference_state_key")
            source = social.get("reference_source")
            if key is None:
                if source != "not_requested":
                    raise RuntimeError("V177 unrequested reference reason changed")
                totals["reference_not_requested"] += 1
            elif source in ("offline_table", "offline_table_nonpositive"):
                totals["reference_available"] += 1
            else:
                raise RuntimeError("V177 bound reference source changed")

    if (
        counts["run_config"] != 1
        or counts["window"] != 1000
        or counts["run_summary"] != 1
    ):
        raise RuntimeError("V177 Nash log cardinality changed")
    if totals["reference_available"] + totals["reference_not_requested"] != 1000:
        raise RuntimeError("V177 reference replay coverage changed")
    if frozen_base is None:
        frozen_hash = None
        prefix_matches = None
        first_severe_exact_one_differs = None
        first_mismatch = None
        mismatch_count = None
    else:
        if len(frozen_base) != 1000:
            raise RuntimeError("frozen base assignment cardinality changed")
        frozen_hash = _assignment_sequence_sha256(frozen_base)
        mismatch_frames = [
            index
            for index, (current, frozen) in enumerate(zip(decision_hashes, frozen_base))
            if current != frozen
        ]
        first_mismatch = mismatch_frames[0] if mismatch_frames else None
        mismatch_count = len(mismatch_frames)
        prefix_matches = first_severe_exact_one_frame is not None and tuple(
            decision_hashes[:first_severe_exact_one_frame]
        ) == tuple(frozen_base[:first_severe_exact_one_frame])
        first_severe_exact_one_differs = (
            first_severe_exact_one_frame is not None
            and decision_hashes[first_severe_exact_one_frame]
            != frozen_base[first_severe_exact_one_frame]
            and first_mismatch == first_severe_exact_one_frame
        )
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": counts["window"],
        "assignment_sequence_sha256": _assignment_sequence_sha256(decision_hashes),
        "frozen_base_assignment_sequence_sha256": frozen_hash,
        "assignment_mismatch_count_vs_base": mismatch_count,
        "first_assignment_mismatch_frame_vs_base": first_mismatch,
        "first_severe_exact_one_frame": first_severe_exact_one_frame,
        "pre_first_severe_exact_one_assignment_prefix_matches_base": prefix_matches,
        "first_severe_exact_one_frame_assignment_differs_from_base": first_severe_exact_one_differs,
        "admitted_terminal_players_with_incomplete_parents": totals["terminal"],
        "admitted_slack_short_work_nonterminal_players": totals["short"],
        "rejected_frontier_players_with_incomplete_parents": totals["rejected"],
        "rejected_short_work_at_or_above_queue_threshold": totals["queue_rejected"],
        "cpu_guard_admitted_incomplete_parent_terminal_players": totals[
            "guard_admitted"
        ],
        "cpu_guard_rejected_heavy_incomplete_parent_terminal_players": totals[
            "guard_rejected"
        ],
        "cpu_guard_parent_completed_heavy_terminal_bypass_players": totals[
            "guard_bypass"
        ],
        "cpu_guard_admitted_normalized_cpu_max": extrema["guard_admitted_ratio_max"],
        "cpu_guard_active_admitted_normalized_cpu_max": extrema[
            "guard_active_admitted_ratio_max"
        ],
        "cpu_guard_inactive_admitted_normalized_cpu_max": extrema[
            "guard_inactive_admitted_ratio_max"
        ],
        "cpu_guard_rejected_normalized_cpu_min": extrema["guard_rejected_ratio_min"],
        "capacity_overload_heavy_incomplete_parent_terminal_players": totals["heavy"],
        "capacity_overload_guard_active_windows": totals["active_windows"],
        "capacity_overload_guard_inactive_windows": totals["inactive_windows"],
        "capacity_overload_exact_one_windows": totals["exact_one_windows"],
        "capacity_overload_severe_exact_one_windows": totals[
            "severe_exact_one_windows"
        ],
        "capacity_overload_severe_exact_one_heavy_terminal_rejections": totals[
            "severe_exact_one_heavy_rejections"
        ],
        "capacity_overload_ordinary_exact_one_windows": totals[
            "ordinary_exact_one_windows"
        ],
        "capacity_overload_ordinary_exact_one_heavy_terminal_admissions": totals[
            "ordinary_exact_one_heavy_admissions"
        ],
        "capacity_overload_exact_two_windows": totals["exact_two_windows"],
        "capacity_overload_exact_two_heavy_terminal_rejections": totals[
            "exact_two_heavy_rejections"
        ],
        "capacity_overload_guard_inactive_heavy_terminal_admissions": totals[
            "inactive_heavy_admissions"
        ],
        "admitted_short_work_remaining_work_max": extrema["admitted_work_max"],
        "rejected_over_threshold_remaining_work_min": extrema["rejected_work_min"],
        "admitted_short_work_queue_density_max": extrema["admitted_density_max"],
        "rejected_short_work_queue_density_min": extrema["rejected_density_min"],
        "feasible_pipeline_players_with_incomplete_parents": totals["incomplete"],
        "below_threshold_route_windows": totals["low_routes"],
        "at_or_above_threshold_route_windows": totals["high_routes"],
        "offline_reference_windows": totals["reference_available"],
        "legitimate_not_requested_windows": totals["reference_not_requested"],
        "function_profile_records_seen_without_payload_access": counts[
            "function_profile"
        ],
        "performance_outcome_fields_parsed": 0,
    }


def _mechanism_falsification_gate(
    audits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
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
        "capacity_overload_exact_one_windows",
        "capacity_overload_severe_exact_one_windows",
        "capacity_overload_severe_exact_one_heavy_terminal_rejections",
        "capacity_overload_ordinary_exact_one_windows",
        "capacity_overload_ordinary_exact_one_heavy_terminal_admissions",
        "capacity_overload_exact_two_windows",
        "capacity_overload_exact_two_heavy_terminal_rejections",
        "capacity_overload_guard_inactive_heavy_terminal_admissions",
        "below_threshold_route_windows",
        "at_or_above_threshold_route_windows",
    )
    totals = {key: sum(int(item[key]) for item in audits) for key in sum_keys}
    max_keys = (
        "cpu_guard_admitted_normalized_cpu_max",
        "cpu_guard_active_admitted_normalized_cpu_max",
        "cpu_guard_inactive_admitted_normalized_cpu_max",
        "admitted_short_work_remaining_work_max",
        "admitted_short_work_queue_density_max",
    )
    min_keys = (
        "cpu_guard_rejected_normalized_cpu_min",
        "rejected_over_threshold_remaining_work_min",
        "rejected_short_work_queue_density_min",
    )
    extrema: dict[str, float | None] = {}
    for key in max_keys:
        values = [float(item[key]) for item in audits if item[key] is not None]
        extrema[key] = max(values) if values else None
    for key in min_keys:
        values = [float(item[key]) for item in audits if item[key] is not None]
        extrema[key] = min(values) if values else None
    by_seed = {str(item["seed"]): item for item in audits}
    if set(by_seed) != set(SEEDS):
        raise RuntimeError("V177 blind audit seed product changed")
    selected_severe_single = all(
        by_seed[seed]["capacity_overload_severe_exact_one_windows"] > 0
        and by_seed[seed]["first_severe_exact_one_frame"] is not None
        and by_seed[seed]["pre_first_severe_exact_one_assignment_prefix_matches_base"]
        is True
        and by_seed[seed]["first_severe_exact_one_frame_assignment_differs_from_base"]
        is True
        and by_seed[seed]["first_assignment_mismatch_frame_vs_base"]
        == by_seed[seed]["first_severe_exact_one_frame"]
        for seed in SEEDS
    )
    boundary_exact = (
        totals["capacity_overload_exact_one_windows"] > 0
        and totals["capacity_overload_severe_exact_one_windows"] > 0
        and totals["capacity_overload_severe_exact_one_heavy_terminal_rejections"]
        == totals["capacity_overload_severe_exact_one_windows"]
        and totals["capacity_overload_ordinary_exact_one_windows"] > 0
        and totals["capacity_overload_ordinary_exact_one_heavy_terminal_admissions"]
        == totals["capacity_overload_ordinary_exact_one_windows"]
        and totals["capacity_overload_exact_one_windows"]
        == totals["capacity_overload_severe_exact_one_windows"]
        + totals["capacity_overload_ordinary_exact_one_windows"]
        and totals["capacity_overload_exact_two_windows"] > 0
        and totals["capacity_overload_exact_two_heavy_terminal_rejections"]
        == 2 * totals["capacity_overload_exact_two_windows"]
    )
    work_queue = (
        extrema["admitted_short_work_remaining_work_max"] is not None
        and extrema["admitted_short_work_remaining_work_max"] <= SHORT_WORK_THRESHOLD
        and extrema["rejected_over_threshold_remaining_work_min"] is not None
        and extrema["rejected_over_threshold_remaining_work_min"] > SHORT_WORK_THRESHOLD
        and extrema["admitted_short_work_queue_density_max"] is not None
        and extrema["admitted_short_work_queue_density_max"] < QUEUE_THRESHOLD
        and extrema["rejected_short_work_queue_density_min"] is not None
        and extrema["rejected_short_work_queue_density_min"] >= QUEUE_THRESHOLD
    )
    guard_boundary = (
        extrema["cpu_guard_active_admitted_normalized_cpu_max"] is not None
        and extrema["cpu_guard_active_admitted_normalized_cpu_max"] <= CPU_THRESHOLD
        and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"] is not None
        and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"] > CPU_THRESHOLD
        and extrema["cpu_guard_rejected_normalized_cpu_min"] is not None
        and extrema["cpu_guard_rejected_normalized_cpu_min"] > CPU_THRESHOLD
    )
    both_routes = (
        totals["below_threshold_route_windows"] > 0
        and totals["at_or_above_threshold_route_windows"] > 0
    )
    exercised = (
        totals["cpu_guard_admitted_incomplete_parent_terminal_players"] > 0
        and totals["cpu_guard_rejected_heavy_incomplete_parent_terminal_players"] > 0
        and totals["cpu_guard_parent_completed_heavy_terminal_bypass_players"] > 0
        and totals["capacity_overload_guard_active_windows"] > 0
        and totals["capacity_overload_guard_inactive_windows"] > 0
        and totals["admitted_slack_short_work_nonterminal_players"] > 0
        and totals["rejected_short_work_at_or_above_queue_threshold"] > 0
    )
    passed = (
        selected_severe_single
        and boundary_exact
        and work_queue
        and guard_boundary
        and both_routes
        and exercised
    )
    return {
        **totals,
        **extrema,
        "every_selected_seed_exercised_severe_exact_one_boundary": all(
            by_seed[seed]["capacity_overload_severe_exact_one_windows"] > 0
            for seed in SEEDS
        ),
        "selected_seeds_match_frozen_base_until_first_severe_exact_one_then_diverge": selected_severe_single,
        "selected_seed_first_severe_exact_one_frames": {
            seed: by_seed[seed]["first_severe_exact_one_frame"] for seed in SEEDS
        },
        "selected_seed_first_assignment_mismatch_frames_vs_base": {
            seed: by_seed[seed]["first_assignment_mismatch_frame_vs_base"]
            for seed in SEEDS
        },
        "severe_exact_one_and_exact_two_rejected_ordinary_exact_one_admitted": boundary_exact,
        "cpu_guard_light_admission_heavy_rejection_and_parent_completed_bypass_exercised": exercised,
        "cpu_guard_boundary_invariants_passed": guard_boundary,
        "work_and_queue_threshold_invariants_passed": work_queue,
        "both_routes_exercised": both_routes,
        "no_active_heavy_quota_or_request_cohort_admission": True,
        "pass": passed,
    }


def blind_audit_v177(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V177 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V177 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V177 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed")
        and pairing.get("run_count") == len(SEEDS)
        and pairing.get("group_count") == len(SEEDS)
    ):
        raise RuntimeError("V177 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=len(SEEDS)
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V177 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V177 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V177 has unexplained quarantined attempts")
    audits: list[dict[str, Any]] = []
    identities: set[tuple[Any, ...]] = set()
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
            _audit_nash_log(
                canonical,
                run,
                frozen_base=_frozen_base_assignment_hashes(run["seed"]),
            )
        )
    if len(identities) != 1:
        raise RuntimeError("V177 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V177 runtime identity changed")
    mechanism = _mechanism_falsification_gate(audits)
    if not mechanism["pass"]:
        raise RuntimeError("V177 mechanism falsification breadth is insufficient")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_SEVERE_QUEUE32_CPU_BOUNDED_TERMINAL_LOW_BLIND_AUDIT_V177_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "aggregate_runtime_breadth_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_path": str(output["pairing"]),
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "run_count": len(SEEDS),
        "window_count": sum(item["windows"] for item in audits),
        **mechanism,
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _load_candidate(
    manifest: Mapping[str, Any], root: Path = ROOT
) -> list[dict[str, Any]]:
    rows = []
    for run in manifest["runs"]:
        summary = (
            paths(root)["workspace"]
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
    if len(rows) != len(SEEDS) or [row["seed"] for row in rows] != list(SEEDS):
        raise RuntimeError("V177 candidate result product changed")
    return rows


def _hybrid_rows(
    v170_rows: Sequence[Mapping[str, Any]],
    v176_rows: Sequence[Mapping[str, Any]],
    v177_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    expected = {f"E{index:02d}" for index in range(1, 21)}
    if len(v170_rows) != 20 or {row.get("seed") for row in v170_rows} != expected:
        raise RuntimeError("V170 complete candidate cohort changed")
    if len(v176_rows) != len(v176base.SEEDS) or {
        row.get("seed") for row in v176_rows
    } != set(v176base.SEEDS):
        raise RuntimeError("V176 diagnostic candidate cohort changed")
    if len(v177_rows) != len(SEEDS) or {row.get("seed") for row in v177_rows} != set(
        SEEDS
    ):
        raise RuntimeError("V177 diagnostic candidate cohort changed")
    if not (
        set(V176_REUSE_SEEDS).isdisjoint(SEEDS)
        and set(V170_REUSE_SEEDS).isdisjoint(SEEDS)
        and set(V170_REUSE_SEEDS).isdisjoint(V176_REUSE_SEEDS)
        and set(V176_REUSE_SEEDS) | set(V170_REUSE_SEEDS) | set(SEEDS) == expected
    ):
        raise RuntimeError("V177 frozen hybrid partition changed")
    frozen_v176 = {row["seed"]: dict(row) for row in v176_rows}
    current_v177 = {row["seed"]: dict(row) for row in v177_rows}
    replacements = {seed: frozen_v176[seed] for seed in V176_REUSE_SEEDS}
    replacements.update(current_v177)
    return [
        replacements.get(row["seed"], dict(row))
        for row in sorted(v170_rows, key=lambda item: item["seed"])
    ]


def reveal_v177(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V177 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V177 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get(
            "selected_seeds_match_frozen_base_until_first_severe_exact_one_then_diverge"
        )
        is True
        and blind.get(
            "severe_exact_one_and_exact_two_rejected_ordinary_exact_one_admitted"
        )
        is True
        and blind.get("cpu_guard_boundary_invariants_passed") is True
        and blind.get("work_and_queue_threshold_invariants_passed") is True
        and blind.get("both_routes_exercised") is True
        and blind.get("pass") is True
    ):
        raise RuntimeError("V177 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = _load_candidate(manifest, root)
    v170_rows = v175._load_v170_candidate()
    v176_manifest = load_and_validate_manifest(v176base.paths()["ready"])
    v176_rows = v176base._load_candidate(v176_manifest, v176base.ROOT)
    hybrid = _hybrid_rows(v170_rows, v176_rows, candidate)
    evaluation = _evaluate_load("low", hybrid, _load_baselines())
    throughput_sum = sum(float(row["throughput"]) for row in candidate)
    qpr_values = [float(row["qpr_finite_only"]) for row in candidate]
    qpr_sum = sum(qpr_values)
    throughput_wins = sum(
        row["difference"] > 0
        for row in evaluation["gates"]["throughput"]["paired_rows"]
        if row["seed"] in SEEDS
    )
    qpr_wins = sum(
        row["difference"] > 0
        for row in evaluation["gates"]["qpr_finite_only"]["paired_rows"]
        if row["seed"] in SEEDS
    )
    diagnostic = {
        "throughput_six_seed_sum": throughput_sum,
        "throughput_six_seed_sum_pass": throughput_sum > THROUGHPUT_SIX_SEED_SUM_GATE,
        "throughput_six_seed_paired_wins": throughput_wins,
        "throughput_six_seed_paired_wins_pass": throughput_wins
        >= THROUGHPUT_SIX_SEED_PAIRED_WIN_GATE,
        "qpr_six_seed_sum": qpr_sum,
        "qpr_six_seed_sum_pass": qpr_sum > QPR_SIX_SEED_SUM_GATE,
        "qpr_six_seed_paired_wins": qpr_wins,
        "qpr_six_seed_paired_wins_pass": qpr_wins >= QPR_SIX_SEED_PAIRED_WIN_GATE,
        "qpr_six_seed_all_finite": all(math.isfinite(value) for value in qpr_values),
    }
    mechanism_keys = (
        "cpu_guard_admitted_incomplete_parent_terminal_players",
        "cpu_guard_rejected_heavy_incomplete_parent_terminal_players",
        "cpu_guard_parent_completed_heavy_terminal_bypass_players",
        "capacity_overload_guard_active_windows",
        "capacity_overload_guard_inactive_windows",
        "capacity_overload_exact_one_windows",
        "capacity_overload_severe_exact_one_windows",
        "capacity_overload_severe_exact_one_heavy_terminal_rejections",
        "capacity_overload_ordinary_exact_one_windows",
        "capacity_overload_ordinary_exact_one_heavy_terminal_admissions",
        "capacity_overload_exact_two_windows",
        "capacity_overload_exact_two_heavy_terminal_rejections",
        "selected_seeds_match_frozen_base_until_first_severe_exact_one_then_diverge",
        "selected_seed_first_severe_exact_one_frames",
        "selected_seed_first_assignment_mismatch_frames_vs_base",
        "severe_exact_one_and_exact_two_rejected_ordinary_exact_one_admitted",
        "work_and_queue_threshold_invariants_passed",
        "both_routes_exercised",
    )
    mechanism = {key: blind[key] for key in mechanism_keys}
    mechanism["pass"] = blind["pass"]
    passed = (
        evaluation["all_three_metric_gates_pass"]
        and mechanism["pass"]
        and diagnostic["throughput_six_seed_sum_pass"]
        and diagnostic["throughput_six_seed_paired_wins_pass"]
        and diagnostic["qpr_six_seed_sum_pass"]
        and diagnostic["qpr_six_seed_paired_wins_pass"]
        and diagnostic["qpr_six_seed_all_finite"]
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_SEVERE_QUEUE32_CPU_BOUNDED_TERMINAL_LOW_DIAGNOSTIC_RESULT_V177_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "new_candidate_run_count": len(SEEDS),
        "reused_v176_candidate_run_count": len(V176_REUSE_SEEDS),
        "reused_v170_candidate_run_count": len(V170_REUSE_SEEDS),
        "reused_frozen_baseline_run_count": 180,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "hybrid_low_evaluation": evaluation,
        "diagnostic_six_seed_gates": diagnostic,
        "mechanism_gate": mechanism,
        "joint_diagnostic_pass": passed,
        "disposition": (
            "authorize_separately_committed_remaining_nine_training_plan_without_rerunning_the_six_V177_diagnostic_or_five_frozen_V176_reuse_seeds"
            if passed
            else "retain_all_six_valid_diagnostic_runs_and_retire_concurrent2_severe_queue32_cpu_bounded_terminal_candidate"
        ),
        "remaining_nine_training_runs": list(V170_REUSE_SEEDS),
        "remaining_nine_training_runs_authorized": passed,
        "confirmation_inputs_generated": False,
        "homogeneous_low_claim_closed": False,
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
        document, key = prepare_v177(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v177(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v177(), "blind_audit_hash"
    else:
        document, key = reveal_v177(), "result_hash"
    print(json.dumps({key: document[key], "runs": len(SEEDS)}))


if __name__ == "__main__":
    main()
