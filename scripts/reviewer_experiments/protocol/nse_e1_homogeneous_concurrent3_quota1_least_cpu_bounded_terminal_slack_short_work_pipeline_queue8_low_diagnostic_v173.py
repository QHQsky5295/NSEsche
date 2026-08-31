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
    nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v159 as v159,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v170 as v170,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_remaining17_v170 as v170remaining,
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
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_queue8_low_training_v155 as v155base,
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
    "tmp/nse_e1_homogeneous_concurrent3_quota1_least_cpu_bounded_terminal_low_diagnostic_20260901_v173"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent3_quota1_least_cpu_bounded_terminal_low_diagnostic_plan_v173.json"
)
PLAN_SHA256 = "f7b082f06957214a234f1c5f10083a103de8eef8a7c3396318258124ce6f19c2"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent3_quota1_least_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_implementation_v173.json"
)
IMPLEMENTATION_SHA256 = (
    "9381bb43dead446e5478c500ef0fdb9c3336e02322bdc6b5dff7093ae8619581"
)
V170_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_complete_training_failure_v170.json"
)
V170_FAILURE_SHA256 = "8a131dcc21c3a95d227d18c640e90d26877fa4c15da5f2387145dff24c576a92"
V170_FAILURE_HASH = "f0806f37783cfb5091f8ec48f465c9b3d74c29c53a6075c5c7c1114051195c10"
V171_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent3_quota2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_complete_training_failure_v171.json"
)
V171_FAILURE_SHA256 = "8b76ecd2dd472ffedc3f104cff635d3bf55017a9b41bb46ce9f099507518d83c"
V171_FAILURE_HASH = "cf1c6ea3ccfb5fcd4ed55d9773e57abebed0fd75be6172881f3d649f5de8e175"
V170_COMPLETE_RESULT = v170remaining.paths()["result"]
V170_COMPLETE_RESULT_SHA256 = (
    "7b790463c8938a4a687eff7aa4090f149c0b1b9543bd94b6a8645b05fa66b45e"
)
V170_COMPLETE_RESULT_HASH = (
    "d7a1b35fe817733608d0725bf1dc7fa110ee78e96601d429745febe010218da7"
)

SEEDS = ("E01", "E02", "E13", "E15", "E16", "E20")
THROUGHPUT_SIX_SEED_SUM_GATE = 8.808999999999997
QPR_SIX_SEED_SUM_GATE = 0.32606219215094256
THROUGHPUT_SIX_SEED_PAIRED_WIN_GATE = 3
QPR_SIX_SEED_PAIRED_WIN_GATE = 1

ARM_ID = "v173-low-srpt-slack-concurrent3-quota1-least-cpu-bounded-terminal-short5p5-pipeline-hiku2-ocs-queue8"
PROFILE = "srpt_slack_concurrent3_quota1_least_cpu_bounded_terminal_short5p5_pipeline_hiku2_ocs_queue8"
FRONTIER = "parents_completed_or_concurrent3_quota1_least_cpu_bounded_terminal_or_slack_short_work_parents_scheduled"
SINGLE_CHANGE = (
    "V172_quota_one_selection_changed_from_request_id_first_to_least_immutable_"
    "function_cpu_work_then_request_id_then_function_id"
)
TERMINAL_DEFINITION = (
    "admit_all_parents-completed_players;when_current_heavy_terminal_player_count_"
    "strictly_exceeds_two_admit_the_one_heavy_incomplete-parent-terminal-player_"
    "with_least_immutable_function_cpu_work_tied_by_request-id-then-function-id_"
    "and_apply_the_V168_CPU_bound_to_the_excess;otherwise_retain_V159_terminal_"
    "admission;retain_V159_nonterminal_short-work_frontier"
)
CPU_THRESHOLD = 1.0
HEAVY_PLAYER_THRESHOLD = 2
MINIMUM_ACTIVE_HEAVY_PLAYERS = 3
ACTIVE_HEAVY_QUOTA = 1
QUOTA_SELECTION_ORDER = (
    "ascending_immutable_function_cpu_work_then_request_id_then_function_id"
)
SHORT_WORK_THRESHOLD = v159.SHORT_WORK_THRESHOLD
QUEUE_THRESHOLD = v159.QUEUE_THRESHOLD
LOW_EXPERT = v159.LOW_EXPERT
HIGH_EXPERT = v159.HIGH_EXPERT
WORK_DEFINITION = v159.WORK_DEFINITION
PORT = v159.PORT

BINARY_SOURCE_COMMIT = "db8ba0b965e6c9d3c5bba661394e9fb7a69251ff"
BINARY_PATH = Path("serverless_sim/target_e1_v173/release/serverless_sim.exe")
BINARY_SHA256 = "9cc2705f97585a2e8a54dd85fe0bf8963bc3982dcdcf39dc38b26529af1b729b"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v173.json",
        "schedule": root / "frozen-run-order-v173.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v173.json",
        "pairing": root / "pairing-audit-v173.json",
        "blind": root / "joint-blind-audit-v173.json",
        "result": root / "diagnostic-result-v173.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v159._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V173 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V173 implementation receipt"),
        (V170_FAILURE, V170_FAILURE_SHA256, "V170 sealed complete failure receipt"),
        (V171_FAILURE, V171_FAILURE_SHA256, "V171 sealed complete failure receipt"),
        (
            V170_COMPLETE_RESULT,
            V170_COMPLETE_RESULT_SHA256,
            "V170 sealed complete result",
        ),
        (BINARY_PATH, BINARY_SHA256, "V173 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    implementation = read_json(IMPLEMENTATION)
    change = implementation.get("single_scientific_change", {})
    if not (
        implementation.get("implementation_commit") == BINARY_SOURCE_COMMIT
        and implementation.get("plan_file_sha256") == PLAN_SHA256
        and implementation.get("isolated_release", {}).get("sha256") == BINARY_SHA256
        and change.get("to_profile") == PROFILE
        and change.get("activation_boundary") == "strictly_above_activates"
        and change.get("activation_threshold") == HEAVY_PLAYER_THRESHOLD
        and change.get("minimum_active_count") == MINIMUM_ACTIVE_HEAVY_PLAYERS
        and change.get("inactive_behavior") == "exact_V159_terminal_admission"
        and change.get("active_heavy_quota") == ACTIVE_HEAVY_QUOTA
        and change.get("old_quota_selection_order")
        == "ascending_request_id_then_function_id"
        and change.get("new_quota_selection_order") == QUOTA_SELECTION_ORDER
        and change.get("old_active_heavy_behavior")
        == "admit_the_first_heavy_incomplete_parent_terminal_player_in_request_id_then_function_id_order"
        and change.get("new_active_heavy_behavior")
        == "admit_the_heavy_incomplete_parent_terminal_player_with_least_immutable_function_cpu_work"
        and change.get("excess_active_heavy_behavior")
        == "exact_V168_closed_CPU_guard_rejection"
        and change.get("cpu_ratio_threshold") == CPU_THRESHOLD
        and change.get("uses_seed_load_dag_function_or_performance_labels") is False
        and change.get("uses_completion_or_performance_outcomes") is False
    ):
        raise RuntimeError("V173 implementation boundary changed")
    failure = read_json(V170_FAILURE)
    if not (
        _assert_hashed(failure, "receipt_hash", "V170 complete failure receipt")
        == V170_FAILURE_HASH
        and failure.get("complete_training_result", {}).get("joint_pass") is False
        and failure.get("complete_training_result", {}).get("throughput_gate_pass")
        is True
        and failure.get("complete_training_result", {}).get("qpr_gate_pass") is False
        and failure.get("complete_training_result", {}).get("file_sha256")
        == V170_COMPLETE_RESULT_SHA256
        and failure.get("complete_training_result", {}).get("result_hash")
        == V170_COMPLETE_RESULT_HASH
        and failure.get("disposition", {}).get("retain_all_twenty_valid_v170_runs")
        is True
        and failure.get("disposition", {}).get(
            "delete_replace_relabel_or_selectively_rerun_any_v170_seed"
        )
        is False
    ):
        raise RuntimeError("V170 complete failure boundary changed")
    failure = read_json(V171_FAILURE)
    if not (
        _assert_hashed(failure, "receipt_hash", "V171 complete failure receipt")
        == V171_FAILURE_HASH
        and failure.get("complete_training_result", {}).get("joint_pass") is False
        and failure.get("complete_training_result", {}).get("throughput_gate_pass")
        is False
        and failure.get("complete_training_result", {}).get("qpr_gate_pass") is False
        and failure.get("complete_training_result", {}).get("result_hash")
        == "7aa522786cdc32997f37f5f52618de8caaf5a50dd9b50bf46b91bc86f8fe0b6b"
        and failure.get("disposition", {}).get("retain_all_twenty_valid_v171_runs")
        is True
        and failure.get("disposition", {}).get(
            "delete_replace_relabel_or_selectively_rerun_any_v171_seed"
        )
        is False
    ):
        raise RuntimeError("V171 complete failure boundary changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


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
    lineage_by_seed = {
        entry["source_seed"]: entry for entry in marker["selected_source_runs"]
    }
    marker["selected_source_runs"] = [lineage_by_seed[seed] for seed in SEEDS]
    for key in list(marker):
        if key.startswith("v155_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": (
                "V173 outcome-disclosed six-seed concurrent3 quota1 CPU-bounded "
                "terminal-starvation diagnostic; "
                "never a formal result or paper superiority claim"
            ),
            "v173_role": "result_blind_concurrent3_quota1_least_cpu_bounded_terminal_falsification",
            "v173_plan_sha256": PLAN_SHA256,
            "v173_implementation_sha256": IMPLEMENTATION_SHA256,
            "v173_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v173_protocol_source_commit": protocol_source_commit,
            "v173_binary_sha256": BINARY_SHA256,
            "v173_arm_id": ARM_ID,
            "v173_profile": PROFILE,
            "v173_player_frontier": FRONTIER,
            "v173_single_change_from_v172": SINGLE_CHANGE,
            "v173_cpu_threshold": CPU_THRESHOLD,
            "v173_cpu_boundary": "at_or_below_is_admitted",
            "v173_heavy_player_threshold": HEAVY_PLAYER_THRESHOLD,
            "v173_minimum_active_heavy_players": MINIMUM_ACTIVE_HEAVY_PLAYERS,
            "v173_overload_activation_boundary": "strictly_above_activates",
            "v173_inactive_behavior": "exact_V159_terminal_admission",
            "v173_active_heavy_admission_policy": "deterministic_least_cpu_quota_one",
            "v173_active_heavy_admission_quota": ACTIVE_HEAVY_QUOTA,
            "v173_quota_selection_order": QUOTA_SELECTION_ORDER,
            "v173_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v173_queue_density_threshold": QUEUE_THRESHOLD,
            "v173_queue_boundary": "below_is_strict",
            "v173_environment": COMMON_ENVIRONMENT,
            "v173_expected_run_count": len(SEEDS),
            "v173_expected_reference_build_count": len(SEEDS),
            "v173_fixed_order": list(SEEDS),
            "v173_candidate_performance_summaries_parsed": 0,
            "v173_remaining_fourteen_authorized": False,
            "v173_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        old = run.get("metadata", {})
        source_run_id = old.get("v155_source_e1_run_id")
        source_run_spec_hash = old.get("v155_source_e1_run_spec_hash")
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v173_training_only": True,
            "v173_role": "result_blind_concurrent3_quota1_least_cpu_bounded_terminal_falsification",
            "v173_plan_sha256": PLAN_SHA256,
            "v173_implementation_sha256": IMPLEMENTATION_SHA256,
            "v173_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v173_protocol_source_commit": protocol_source_commit,
            "v173_binary_sha256": BINARY_SHA256,
            "v173_arm_id": ARM_ID,
            "v173_profile": PROFILE,
            "v173_player_frontier": FRONTIER,
            "v173_single_change_from_v172": SINGLE_CHANGE,
            "v173_cpu_threshold": CPU_THRESHOLD,
            "v173_cpu_boundary": "at_or_below_is_admitted",
            "v173_heavy_player_threshold": HEAVY_PLAYER_THRESHOLD,
            "v173_minimum_active_heavy_players": MINIMUM_ACTIVE_HEAVY_PLAYERS,
            "v173_overload_activation_boundary": "strictly_above_activates",
            "v173_inactive_behavior": "exact_V159_terminal_admission",
            "v173_active_heavy_admission_policy": "deterministic_least_cpu_quota_one",
            "v173_active_heavy_admission_quota": ACTIVE_HEAVY_QUOTA,
            "v173_quota_selection_order": QUOTA_SELECTION_ORDER,
            "v173_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v173_queue_density_threshold": QUEUE_THRESHOLD,
            "v173_queue_boundary": "below_is_strict",
            "v173_source_e1_run_id": source_run_id,
            "v173_source_e1_run_spec_hash": source_run_spec_hash,
            "v173_candidate_performance_summaries_parsed_before_run": 0,
            "v173_remaining_fourteen_authorized": False,
            "v173_confirmation_inputs_generated": False,
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
        raise RuntimeError("V173 exact E01/E02/E13/E15/E16/E20 product changed")
    expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and all(
                run["environment"].get(key) == value for key, value in expected.items()
            )
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v173_profile") == PROFILE
            and metadata.get("v173_player_frontier") == FRONTIER
            and metadata.get("v173_cpu_threshold") == CPU_THRESHOLD
            and metadata.get("v173_cpu_boundary") == "at_or_below_is_admitted"
            and metadata.get("v173_heavy_player_threshold") == HEAVY_PLAYER_THRESHOLD
            and metadata.get("v173_minimum_active_heavy_players")
            == MINIMUM_ACTIVE_HEAVY_PLAYERS
            and metadata.get("v173_overload_activation_boundary")
            == "strictly_above_activates"
            and metadata.get("v173_inactive_behavior")
            == "exact_V159_terminal_admission"
            and metadata.get("v173_active_heavy_admission_policy")
            == "deterministic_least_cpu_quota_one"
            and metadata.get("v173_active_heavy_admission_quota") == ACTIVE_HEAVY_QUOTA
            and metadata.get("v173_quota_selection_order") == QUOTA_SELECTION_ORDER
            and metadata.get("v173_short_work_threshold") == SHORT_WORK_THRESHOLD
            and metadata.get("v173_queue_density_threshold") == QUEUE_THRESHOLD
            and metadata.get("v173_queue_boundary") == "below_is_strict"
        ):
            raise RuntimeError(f"V173 run contract changed: {run.get('run_id')}")


def prepare_v173(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V173 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_CPU_BOUNDED_TERMINAL_LOW_SCHEDULE_V173_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_CPU_BOUNDED_TERMINAL_LOW_PREPARED_V173_V1",
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
        "v170_complete_failure_file_sha256": V170_FAILURE_SHA256,
        "v170_complete_failure_hash": V170_FAILURE_HASH,
        "v171_complete_failure_file_sha256": V171_FAILURE_SHA256,
        "v171_complete_failure_hash": V171_FAILURE_HASH,
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
        "cpu_boundary": "at_or_below_is_admitted",
        "heavy_player_threshold": HEAVY_PLAYER_THRESHOLD,
        "minimum_active_heavy_players": MINIMUM_ACTIVE_HEAVY_PLAYERS,
        "overload_activation_boundary": "strictly_above_activates",
        "inactive_behavior": "exact_V159_terminal_admission",
        "active_heavy_admission_policy": "deterministic_least_cpu_quota_one",
        "active_heavy_admission_quota": ACTIVE_HEAVY_QUOTA,
        "quota_selection_order": QUOTA_SELECTION_ORDER,
        "short_work_threshold": SHORT_WORK_THRESHOLD,
        "queue_density_threshold": QUEUE_THRESHOLD,
        "queue_boundary": "below_is_strict",
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v173(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V173 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V173 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    dispatches = []
    logs = root / "execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
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
            raise RuntimeError(f"V173 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V173 canonical is not a QC pass: {run['run_id']}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_CAPACITY_OVERLOAD_CPU_BOUNDED_TERMINAL_LOW_EXECUTION_V173_V1",
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


def _frozen_v170_assignment_hashes(seed: str) -> tuple[int, ...]:
    diagnostic_source = seed in v170.SEEDS
    output = v170.paths() if diagnostic_source else v170remaining.paths()
    failure = read_json(V170_FAILURE)
    if diagnostic_source:
        success = read_json(v170remaining.DIAGNOSTIC_SUCCESS)
        _assert_file(
            v170remaining.DIAGNOSTIC_SUCCESS,
            v170remaining.DIAGNOSTIC_SUCCESS_SHA256,
            "frozen V170 diagnostic success receipt",
        )
        if (
            _assert_hashed(
                success,
                "receipt_hash",
                "frozen V170 diagnostic success receipt",
            )
            != v170remaining.DIAGNOSTIC_SUCCESS_HASH
        ):
            raise RuntimeError("frozen V170 diagnostic success receipt changed")
        expected_ready = success["ready_manifest"]
    else:
        expected_ready = failure["ready_manifest"]
    _assert_file(
        output["ready"],
        expected_ready["file_sha256"],
        f"frozen V170 {seed} ready manifest",
    )
    manifest = load_and_validate_manifest(output["ready"])
    if manifest["manifest_hash"] != expected_ready["manifest_hash"]:
        raise RuntimeError(f"frozen V170 {seed} manifest hash changed")
    matching = [item for item in manifest["runs"] if item["seed"] == seed]
    if len(matching) != 1:
        raise RuntimeError(f"frozen V170 assignment source is not unique for {seed}")
    run = matching[0]
    run_id = run["run_id"]
    canonical = output["workspace"] / "canonical" / run_id
    validate_canonical_run(
        run,
        canonical,
        expected_manifest_hash=manifest["manifest_hash"],
        result_relative_path="reviewer_records/{run_id}/summary.json",
    )
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    values = []
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("kind") == "window":
                if event.get("frame") != len(values):
                    raise RuntimeError("frozen V170 assignment sequence changed")
                value = event.get("decision", {}).get("assignment_hash")
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise RuntimeError("frozen V170 assignment hash changed")
                values.append(value)
    if len(values) != 1000:
        raise RuntimeError("frozen V170 assignment sequence cardinality changed")
    return tuple(values)


def _audit_nash_log(
    canonical: Path,
    run: Mapping[str, Any],
    *,
    compare_to_frozen_v170: bool = True,
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
        "capacity_overload_heavy": 0,
        "capacity_overload_active_windows": 0,
        "capacity_overload_inactive_windows": 0,
        "capacity_overload_inactive_heavy_admissions": 0,
        "active_heavy_quota_selected": 0,
        "active_heavy_quota_admitted": 0,
        "active_heavy_quota_rejected": 0,
        "least_cpu_order_certified_active_windows": 0,
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
    active_frames: list[int] = []

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
                raise RuntimeError(f"unexpected V173 Nash observation kind: {kind}")
            counts[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                guard = contract.get("cpu_bounded_terminal_guard", {})
                activation = guard.get("capacity_overload_activation", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V173"
                    and contract.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and contract.get("below_threshold_expert") == LOW_EXPERT
                    and contract.get("at_or_above_threshold_expert") == HIGH_EXPERT
                    and contract.get("player_frontier") == FRONTIER
                    and contract.get("single_change_from_v155") == SINGLE_CHANGE
                    and contract.get("terminal_pipeline_definition")
                    == TERMINAL_DEFINITION
                    and contract.get("short_work_pipeline_remaining_work_threshold")
                    == SHORT_WORK_THRESHOLD
                    and contract.get("short_work_pipeline_queue_density_threshold")
                    == QUEUE_THRESHOLD
                    and contract.get("short_work_pipeline_queue_boundary")
                    == "below_is_strict"
                    and contract.get("short_work_definition") == WORK_DEFINITION
                    and guard.get("normalized_cpu_threshold") == CPU_THRESHOLD
                    and guard.get("boundary") == "at_or_below_is_admitted"
                    and guard.get("numerator") == "immutable_function_cpu_work"
                    and guard.get("denominator")
                    == "current_cluster_mean_node_cpu_capacity"
                    and guard.get("parents_completed_bypass") is True
                    and guard.get("uses_completion_or_performance_outcomes") is False
                    and activation.get("heavy_player_definition")
                    == "collectable_incomplete-parent_terminal_player_with_immutable_function_cpu_work_over_current_cluster_mean_node_cpu_capacity_strictly_above_one"
                    and activation.get("capacity_threshold")
                    == "fixed_two_current_heavy_players"
                    and activation.get("fixed_heavy_player_count_threshold")
                    == HEAVY_PLAYER_THRESHOLD
                    and activation.get("minimum_active_heavy_player_count")
                    == MINIMUM_ACTIVE_HEAVY_PLAYERS
                    and activation.get("activation_boundary")
                    == "heavy_player_count_strictly_above_two"
                    and activation.get("inactive_behavior") == "V159_terminal_admission"
                    and activation.get("active_heavy_admission_policy")
                    == "deterministic_least_cpu_quota_one"
                    and activation.get("active_heavy_admission_quota")
                    == ACTIVE_HEAVY_QUOTA
                    and activation.get("quota_selection_order") == QUOTA_SELECTION_ORDER
                    and activation.get(
                        "uses_seed_load_dag_function_or_performance_labels"
                    )
                    is False
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V173 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != counts["window"] - 1:
                    raise RuntimeError("V173 scheduler window sequence changed")
                decision = event.get("decision", {})
                decision_hash = decision.get("assignment_hash")
                if (
                    isinstance(decision_hash, bool)
                    or not isinstance(decision_hash, int)
                    or decision_hash < 0
                    or decision.get("player_frontier") != FRONTIER
                ):
                    raise RuntimeError("V173 decision frontier/hash changed")
                frontier = decision.get("terminal_pipeline_frontier", {})
                terminal_now = v159._count(
                    frontier.get("admitted_terminal_players_with_incomplete_parents"),
                    "terminal admission count",
                )
                short_now = v159._count(
                    frontier.get(
                        "admitted_short_work_nonterminal_players_with_incomplete_parents"
                    ),
                    "short-work admission count",
                )
                rejected_now = v159._count(
                    frontier.get(
                        "rejected_nonterminal_players_with_incomplete_parents"
                    ),
                    "frontier rejection count",
                )
                incomplete_now = v159._count(
                    decision.get("pipeline_players_with_incomplete_parents"),
                    "pipeline incomplete-parent count",
                )
                work_max_now = v159._finite_optional(
                    frontier.get("admitted_short_work_remaining_work_max"),
                    "admitted work maximum",
                )
                work_min_now = v159._finite_optional(
                    frontier.get("rejected_nonterminal_remaining_work_min"),
                    "rejected work minimum",
                )
                queue_gate = frontier.get("short_work_queue_gate", {})
                queue_rejected_now = v159._count(
                    queue_gate.get("rejected_short_work_at_or_above_threshold"),
                    "queue-gated rejection count",
                )
                admitted_density_now = v159._finite_optional(
                    queue_gate.get("admitted_short_work_queue_density_max"),
                    "admitted queue-density maximum",
                )
                rejected_density_now = v159._finite_optional(
                    queue_gate.get("rejected_short_work_queue_density_min"),
                    "rejected queue-density minimum",
                )
                guard = frontier.get("cpu_bounded_terminal_guard", {})
                guard_admitted_now = v159._count(
                    guard.get("admitted_incomplete_parent_terminal_players"),
                    "CPU-guard admitted count",
                )
                guard_rejected_now = v159._count(
                    guard.get("rejected_heavy_incomplete_parent_terminal_players"),
                    "CPU-guard rejected count",
                )
                guard_bypass_now = v159._count(
                    guard.get("parents_completed_heavy_terminal_bypass_players"),
                    "CPU-guard parent-completed bypass count",
                )
                guard_admitted_ratio_now = v159._finite_optional(
                    guard.get("admitted_normalized_cpu_max"),
                    "CPU-guard admitted ratio maximum",
                )
                guard_rejected_ratio_now = v159._finite_optional(
                    guard.get("rejected_normalized_cpu_min"),
                    "CPU-guard rejected ratio minimum",
                )
                activation = guard.get("capacity_overload_activation", {})
                heavy_now = v159._count(
                    activation.get("heavy_incomplete_parent_terminal_players"),
                    "capacity-overload heavy player count",
                )
                node_count_now = v159._count(
                    activation.get("node_count_threshold"),
                    "concurrent3 node count observation",
                )
                heavy_threshold_now = v159._count(
                    activation.get("heavy_player_count_threshold"),
                    "concurrent3 heavy player threshold",
                )
                minimum_active_now = v159._count(
                    activation.get("minimum_active_heavy_player_count"),
                    "concurrent3 minimum active player count",
                )
                inactive_heavy_admissions_now = v159._count(
                    activation.get("guard_inactive_heavy_terminal_admissions"),
                    "capacity-overload inactive heavy admission count",
                )
                quota_selected_now = v159._count(
                    activation.get("active_heavy_quota_selected_players"),
                    "active heavy quota selected count",
                )
                quota_admitted_now = v159._count(
                    activation.get("active_heavy_quota_admitted_players"),
                    "active heavy quota admitted count",
                )
                quota_rejected_now = v159._count(
                    activation.get("active_heavy_quota_rejected_excess_players"),
                    "active heavy quota rejected count",
                )
                guard_active_now = activation.get("guard_active")
                guard_inactive_now = activation.get("guard_inactive")
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
                    and guard.get("denominator")
                    == "current_cluster_mean_node_cpu_capacity"
                    and guard.get("uses_completion_or_performance_outcomes") is False
                    and activation.get("enabled") is True
                    and node_count_now == 20
                    and heavy_threshold_now == HEAVY_PLAYER_THRESHOLD
                    and minimum_active_now == MINIMUM_ACTIVE_HEAVY_PLAYERS
                    and activation.get("threshold_kind")
                    == "fixed_two_current_heavy_players"
                    and activation.get("activation_boundary")
                    == "strictly_above_activates"
                    and activation.get("active_heavy_admission_policy")
                    == "deterministic_least_cpu_quota_one"
                    and activation.get("active_heavy_admission_quota")
                    == ACTIVE_HEAVY_QUOTA
                    and activation.get("quota_selection_order") == QUOTA_SELECTION_ORDER
                    and isinstance(guard_active_now, bool)
                    and isinstance(guard_inactive_now, bool)
                    and guard_inactive_now is (not guard_active_now)
                    and guard_active_now is (heavy_now > heavy_threshold_now)
                    and activation.get(
                        "uses_seed_load_dag_function_or_performance_labels"
                    )
                    is False
                    and guard_admitted_now == terminal_now
                    and (guard_admitted_now == 0) == (guard_admitted_ratio_now is None)
                    and (guard_rejected_now == 0) == (guard_rejected_ratio_now is None)
                    and (
                        guard_rejected_ratio_now is None
                        or guard_rejected_ratio_now > CPU_THRESHOLD
                    )
                    and (
                        guard_active_now
                        and quota_selected_now == min(heavy_now, ACTIVE_HEAVY_QUOTA)
                        and quota_admitted_now == quota_selected_now
                        and quota_admitted_now <= ACTIVE_HEAVY_QUOTA
                        and quota_rejected_now == heavy_now - quota_admitted_now
                        and guard_rejected_now == quota_rejected_now
                        and guard_admitted_now >= quota_admitted_now
                        and guard_admitted_ratio_now is not None
                        and guard_rejected_ratio_now is not None
                        and guard_admitted_ratio_now <= guard_rejected_ratio_now
                        and inactive_heavy_admissions_now == 0
                        or guard_inactive_now
                        and guard_rejected_now == 0
                        and inactive_heavy_admissions_now == heavy_now
                        and quota_selected_now == 0
                        and quota_admitted_now == 0
                        and quota_rejected_now == 0
                    )
                    and queue_gate.get("enabled") is True
                    and queue_gate.get("threshold") == QUEUE_THRESHOLD
                    and queue_gate.get("boundary") == "below_is_strict"
                    and incomplete_now <= terminal_now + short_now
                    and queue_rejected_now <= rejected_now
                    and (short_now == 0)
                    == (work_max_now is None and admitted_density_now is None)
                    and (queue_rejected_now == 0) == (rejected_density_now is None)
                    and (work_max_now is None or work_max_now <= SHORT_WORK_THRESHOLD)
                    and (
                        admitted_density_now is None
                        or admitted_density_now < QUEUE_THRESHOLD
                    )
                    and (work_min_now is None or work_min_now > SHORT_WORK_THRESHOLD)
                    and (
                        rejected_density_now is None
                        or rejected_density_now >= QUEUE_THRESHOLD
                    )
                    and decision.get("pipeline_observation_fields_drive_future_windows")
                    is False
                ):
                    raise RuntimeError("V173 CPU/slack/queue frontier evidence changed")
                decision_hashes.append(decision_hash)
                if guard_active_now:
                    active_frames.append(counts["window"] - 1)
                totals["terminal"] += terminal_now
                totals["short"] += short_now
                totals["rejected"] += rejected_now
                totals["queue_rejected"] += queue_rejected_now
                totals["incomplete"] += incomplete_now
                totals["guard_admitted"] += guard_admitted_now
                totals["guard_rejected"] += guard_rejected_now
                totals["guard_bypass"] += guard_bypass_now
                totals["capacity_overload_heavy"] += heavy_now
                totals["capacity_overload_active_windows"] += int(guard_active_now)
                totals["capacity_overload_inactive_windows"] += int(guard_inactive_now)
                totals[
                    "capacity_overload_inactive_heavy_admissions"
                ] += inactive_heavy_admissions_now
                totals["active_heavy_quota_selected"] += quota_selected_now
                totals["active_heavy_quota_admitted"] += quota_admitted_now
                totals["active_heavy_quota_rejected"] += quota_rejected_now
                totals["least_cpu_order_certified_active_windows"] += int(
                    guard_active_now
                    and guard_admitted_ratio_now is not None
                    and guard_rejected_ratio_now is not None
                    and guard_admitted_ratio_now <= guard_rejected_ratio_now
                )
                update_max("admitted_work_max", work_max_now)
                update_min("rejected_work_min", work_min_now)
                update_max("admitted_density_max", admitted_density_now)
                update_min("rejected_density_min", rejected_density_now)
                update_max("guard_admitted_ratio_max", guard_admitted_ratio_now)
                if guard_active_now:
                    update_max(
                        "guard_active_admitted_ratio_max", guard_admitted_ratio_now
                    )
                else:
                    update_max(
                        "guard_inactive_admitted_ratio_max", guard_admitted_ratio_now
                    )
                update_min("guard_rejected_ratio_min", guard_rejected_ratio_now)
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
                    raise RuntimeError("V173 route telemetry is incomplete")
                expected = (
                    LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
                )
                if route.get("selected_expert") != expected:
                    raise RuntimeError("V173 route does not match queue density")
                totals["low_routes"] += expected == LOW_EXPERT
                totals["high_routes"] += expected == HIGH_EXPERT
                social = event.get("social", {})
                key, source = social.get("reference_state_key"), social.get(
                    "reference_source"
                )
                if key is None:
                    if source != "not_requested":
                        raise RuntimeError("V173 unrequested reference reason changed")
                    totals["reference_not_requested"] += 1
                elif source in ("offline_table", "offline_table_nonpositive"):
                    totals["reference_available"] += 1
                else:
                    raise RuntimeError("V173 bound reference source changed")
            elif kind == "run_summary":
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V173 Nash terminal marker changed")
            # Function-profile payloads are deliberately not inspected.
    if (
        counts["run_config"] != 1
        or counts["window"] != 1000
        or counts["run_summary"] != 1
    ):
        raise RuntimeError("V173 Nash log cardinality changed")
    if (
        totals["reference_available"] + totals["reference_not_requested"]
        != counts["window"]
    ):
        raise RuntimeError("V173 reference replay coverage changed")
    first_active_frame = active_frames[0] if active_frames else None
    frozen_v170 = (
        _frozen_v170_assignment_hashes(run["seed"]) if compare_to_frozen_v170 else None
    )
    if frozen_v170 is None:
        frozen_sequence_sha256 = None
        full_mismatch_count = None
        prefix_matches = None
        post_activation_mismatch_count = None
    else:
        prefix_end = (
            first_active_frame
            if first_active_frame is not None
            else len(decision_hashes)
        )
        frozen_sequence_sha256 = _assignment_sequence_sha256(frozen_v170)
        full_mismatch_count = sum(
            current != frozen for current, frozen in zip(decision_hashes, frozen_v170)
        )
        prefix_matches = tuple(decision_hashes[:prefix_end]) == frozen_v170[:prefix_end]
        post_activation_mismatch_count = (
            sum(
                current != frozen
                for current, frozen in zip(
                    decision_hashes[first_active_frame:],
                    frozen_v170[first_active_frame:],
                )
            )
            if first_active_frame is not None
            else 0
        )
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": counts["window"],
        "assignment_sequence_sha256": _assignment_sequence_sha256(decision_hashes),
        "frozen_v170_comparison_applicable": compare_to_frozen_v170,
        "frozen_v170_assignment_sequence_sha256": frozen_sequence_sha256,
        "assignment_mismatch_count_vs_v170": full_mismatch_count,
        "first_guard_active_frame": first_active_frame,
        "pre_activation_assignment_prefix_matches_v170": prefix_matches,
        "post_activation_assignment_mismatch_count_vs_v170": post_activation_mismatch_count,
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
        "capacity_overload_heavy_incomplete_parent_terminal_players": totals[
            "capacity_overload_heavy"
        ],
        "capacity_overload_guard_active_windows": totals[
            "capacity_overload_active_windows"
        ],
        "capacity_overload_guard_inactive_windows": totals[
            "capacity_overload_inactive_windows"
        ],
        "capacity_overload_guard_inactive_heavy_terminal_admissions": totals[
            "capacity_overload_inactive_heavy_admissions"
        ],
        "active_heavy_quota_selected_players": totals["active_heavy_quota_selected"],
        "active_heavy_quota_admitted_players": totals["active_heavy_quota_admitted"],
        "active_heavy_quota_rejected_excess_players": totals[
            "active_heavy_quota_rejected"
        ],
        "least_cpu_order_certified_active_windows": totals[
            "least_cpu_order_certified_active_windows"
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
    audits: Sequence[Mapping[str, Any]]
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
        "capacity_overload_guard_inactive_heavy_terminal_admissions",
        "active_heavy_quota_selected_players",
        "active_heavy_quota_admitted_players",
        "active_heavy_quota_rejected_excess_players",
        "least_cpu_order_certified_active_windows",
        "below_threshold_route_windows",
        "at_or_above_threshold_route_windows",
    )
    totals = {key: sum(int(audit[key]) for audit in audits) for key in sum_keys}
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
        values = [float(a[key]) for a in audits if a[key] is not None]
        extrema[key] = max(values) if values else None
    for key in min_keys:
        values = [float(a[key]) for a in audits if a[key] is not None]
        extrema[key] = min(values) if values else None
    by_seed = {str(audit["seed"]): audit for audit in audits}
    if set(by_seed) != set(SEEDS):
        raise RuntimeError("V173 blind audit seed product changed")
    selected_activation = all(
        by_seed[seed]["capacity_overload_guard_active_windows"] > 0
        and by_seed[seed]["capacity_overload_guard_inactive_windows"] > 0
        and by_seed[seed]["first_guard_active_frame"] is not None
        and by_seed[seed]["pre_activation_assignment_prefix_matches_v170"] is True
        and by_seed[seed]["post_activation_assignment_mismatch_count_vs_v170"] > 0
        for seed in SEEDS
    )
    quota_exercised = (
        totals["active_heavy_quota_selected_players"] > 0
        and totals["active_heavy_quota_selected_players"]
        == totals["active_heavy_quota_admitted_players"]
        == ACTIVE_HEAVY_QUOTA * totals["capacity_overload_guard_active_windows"]
        and totals["active_heavy_quota_rejected_excess_players"] > 0
        and totals["least_cpu_order_certified_active_windows"]
        == totals["capacity_overload_guard_active_windows"]
    )
    passed = (
        all(value > 0 for value in totals.values())
        and all(extrema[key] is not None for key in extrema)
        and selected_activation
        and quota_exercised
        and extrema["cpu_guard_active_admitted_normalized_cpu_max"] > CPU_THRESHOLD
        and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"] > CPU_THRESHOLD
        and extrema["cpu_guard_rejected_normalized_cpu_min"] > CPU_THRESHOLD
        and extrema["admitted_short_work_remaining_work_max"] <= SHORT_WORK_THRESHOLD
        and extrema["rejected_over_threshold_remaining_work_min"] > SHORT_WORK_THRESHOLD
        and extrema["admitted_short_work_queue_density_max"] < QUEUE_THRESHOLD
        and extrema["rejected_short_work_queue_density_min"] >= QUEUE_THRESHOLD
    )
    return {
        **totals,
        **extrema,
        "cpu_guard_light_admission_heavy_rejection_and_parent_completed_bypass_exercised": (
            totals["cpu_guard_admitted_incomplete_parent_terminal_players"] > 0
            and totals["cpu_guard_rejected_heavy_incomplete_parent_terminal_players"]
            > 0
            and totals["cpu_guard_parent_completed_heavy_terminal_bypass_players"] > 0
        ),
        "cpu_guard_boundary_invariants_passed": (
            extrema["cpu_guard_active_admitted_normalized_cpu_max"] is not None
            and extrema["cpu_guard_active_admitted_normalized_cpu_max"] > CPU_THRESHOLD
            and extrema["cpu_guard_rejected_normalized_cpu_min"] is not None
            and extrema["cpu_guard_rejected_normalized_cpu_min"] > CPU_THRESHOLD
        ),
        "capacity_overload_activation_and_v159_inactive_admission_exercised": (
            totals["capacity_overload_guard_active_windows"] > 0
            and totals["capacity_overload_guard_inactive_windows"] > 0
            and totals["capacity_overload_guard_inactive_heavy_terminal_admissions"] > 0
            and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"] is not None
            and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"]
            > CPU_THRESHOLD
        ),
        "deterministic_active_heavy_quota_exercised_and_bounded": quota_exercised,
        "least_cpu_quota_selection_order_certified_in_every_active_window": (
            totals["least_cpu_order_certified_active_windows"]
            == totals["capacity_overload_guard_active_windows"]
        ),
        "selected_seeds_pre_activation_exact_v170_then_diverged": selected_activation,
        "selected_seed_first_guard_active_frames": {
            seed: by_seed[seed]["first_guard_active_frame"] for seed in SEEDS
        },
        "selected_seed_post_activation_assignment_mismatches_vs_v170": {
            seed: by_seed[seed]["post_activation_assignment_mismatch_count_vs_v170"]
            for seed in SEEDS
        },
        "work_and_queue_threshold_invariants_passed": (
            extrema["admitted_short_work_remaining_work_max"] is not None
            and extrema["admitted_short_work_remaining_work_max"]
            <= SHORT_WORK_THRESHOLD
            and extrema["rejected_over_threshold_remaining_work_min"] is not None
            and extrema["rejected_over_threshold_remaining_work_min"]
            > SHORT_WORK_THRESHOLD
            and extrema["admitted_short_work_queue_density_max"] is not None
            and extrema["admitted_short_work_queue_density_max"] < QUEUE_THRESHOLD
            and extrema["rejected_short_work_queue_density_min"] is not None
            and extrema["rejected_short_work_queue_density_min"] >= QUEUE_THRESHOLD
        ),
        "both_routes_exercised": (
            totals["below_threshold_route_windows"] > 0
            and totals["at_or_above_threshold_route_windows"] > 0
        ),
        "pass": passed,
    }


def blind_audit_v173(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V173 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V173 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V173 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if (
        not pairing.get("passed")
        or pairing.get("run_count") != len(SEEDS)
        or pairing.get("group_count") != len(SEEDS)
    ):
        raise RuntimeError("V173 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=len(SEEDS)
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V173 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V173 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V173 has unexplained quarantined attempts")
    audits, identities = [], set()
    for run in manifest["runs"]:
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit = read_json(canonical / "manifest.json")
        software = audit.get("software_environment", {})
        identities.add(
            (
                audit.get("adapter_binary", {}).get("verified_sha256"),
                software.get("git", {}).get("commit"),
                software.get("python", {}).get("executable_sha256"),
                software.get("cargo_lock", {}).get("sha256"),
            )
        )
        audits.append(_audit_nash_log(canonical, run))
    if len(identities) != 1:
        raise RuntimeError("V173 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V173 runtime identity changed")
    mechanism = _mechanism_falsification_gate(audits)
    if not mechanism["pass"]:
        raise RuntimeError("V173 mechanism falsification breadth is insufficient")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_CPU_BOUNDED_TERMINAL_LOW_BLIND_AUDIT_V173_V1",
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
        "window_count": sum(x["windows"] for x in audits),
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
        raise RuntimeError("V173 candidate result product changed")
    return rows


def _hybrid_rows_v173(
    v170_rows: Sequence[Mapping[str, Any]],
    v173_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(v170_rows) != 20 or {row["seed"] for row in v170_rows} != {
        f"E{index:02d}" for index in range(1, 21)
    }:
        raise RuntimeError("V170 complete candidate cohort changed")
    if len(v173_rows) != len(SEEDS) or {row["seed"] for row in v173_rows} != set(SEEDS):
        raise RuntimeError("V173 diagnostic candidate cohort changed")
    replacements = {row["seed"]: dict(row) for row in v173_rows}
    return [
        replacements.get(row["seed"], dict(row))
        for row in sorted(v170_rows, key=lambda item: item["seed"])
    ]


def _load_v170_candidate() -> list[dict[str, Any]]:
    _assert_file(
        V170_COMPLETE_RESULT,
        V170_COMPLETE_RESULT_SHA256,
        "V170 sealed complete result",
    )
    document = read_json(V170_COMPLETE_RESULT)
    if (
        _assert_hashed(document, "result_hash", "V170 sealed complete result")
        != V170_COMPLETE_RESULT_HASH
    ):
        raise RuntimeError("V170 sealed complete result hash changed")
    rows = [dict(row) for row in document.get("candidate_rows", [])]
    expected_seeds = {f"E{index:02d}" for index in range(1, 21)}
    if (
        len(rows) != 20
        or {row.get("seed") for row in rows} != expected_seeds
        or any(row.get("load") != "low" for row in rows)
    ):
        raise RuntimeError("V170 sealed complete candidate cohort changed")
    return rows


def reveal_v173(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V173 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V173 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get(
            "cpu_guard_light_admission_heavy_rejection_and_parent_completed_bypass_exercised"
        )
        is True
        and blind.get("cpu_guard_boundary_invariants_passed") is True
        and blind.get(
            "capacity_overload_activation_and_v159_inactive_admission_exercised"
        )
        is True
        and blind.get("deterministic_active_heavy_quota_exercised_and_bounded") is True
        and blind.get(
            "least_cpu_quota_selection_order_certified_in_every_active_window"
        )
        is True
        and blind.get("selected_seeds_pre_activation_exact_v170_then_diverged") is True
        and blind.get("work_and_queue_threshold_invariants_passed") is True
        and blind.get("both_routes_exercised") is True
        and blind.get("pass") is True
    ):
        raise RuntimeError("V173 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = _load_candidate(manifest, root)
    v170_rows = _load_v170_candidate()
    hybrid = _hybrid_rows_v173(v170_rows, candidate)
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
    mechanism = {
        key: blind[key]
        for key in (
            "cpu_guard_admitted_incomplete_parent_terminal_players",
            "cpu_guard_rejected_heavy_incomplete_parent_terminal_players",
            "cpu_guard_parent_completed_heavy_terminal_bypass_players",
            "cpu_guard_admitted_normalized_cpu_max",
            "cpu_guard_active_admitted_normalized_cpu_max",
            "cpu_guard_inactive_admitted_normalized_cpu_max",
            "cpu_guard_rejected_normalized_cpu_min",
            "capacity_overload_heavy_incomplete_parent_terminal_players",
            "capacity_overload_guard_active_windows",
            "capacity_overload_guard_inactive_windows",
            "capacity_overload_guard_inactive_heavy_terminal_admissions",
            "active_heavy_quota_selected_players",
            "active_heavy_quota_admitted_players",
            "active_heavy_quota_rejected_excess_players",
            "least_cpu_order_certified_active_windows",
            "deterministic_active_heavy_quota_exercised_and_bounded",
            "least_cpu_quota_selection_order_certified_in_every_active_window",
            "selected_seeds_pre_activation_exact_v170_then_diverged",
            "selected_seed_first_guard_active_frames",
            "selected_seed_post_activation_assignment_mismatches_vs_v170",
            "admitted_slack_short_work_nonterminal_players",
            "rejected_short_work_at_or_above_queue_threshold",
            "admitted_short_work_remaining_work_max",
            "rejected_over_threshold_remaining_work_min",
            "admitted_short_work_queue_density_max",
            "rejected_short_work_queue_density_min",
        )
    }
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
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT3_CPU_BOUNDED_TERMINAL_LOW_DIAGNOSTIC_RESULT_V173_V1",
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
        "reused_v170_candidate_run_count": 20 - len(SEEDS),
        "reused_frozen_baseline_run_count": 180,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "hybrid_low_evaluation": evaluation,
        "diagnostic_six_seed_gates": diagnostic,
        "mechanism_gate": mechanism,
        "joint_diagnostic_pass": passed,
        "disposition": (
            "authorize_separately_committed_remaining_fourteen_training_plan_without_rerunning_E01_E02_E13_E15_E16_E20"
            if passed
            else "retain_all_six_valid_diagnostic_runs_and_retire_concurrent3_quota1_least_cpu_bounded_terminal_candidate"
        ),
        "remaining_fourteen_training_runs_authorized": passed,
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
        document, key = prepare_v173(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v173(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v173(), "blind_audit_hash"
    else:
        document, key = reveal_v173(), "result_hash"
    print(json.dumps({key: document[key], "runs": len(SEEDS)}))


if __name__ == "__main__":
    main()
