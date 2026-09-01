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
    nse_e1_homogeneous_concurrent2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v176 as v176,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_severe_queue32_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v177 as v177,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_requestcohort1_shortest_request_least_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v175 as v175,
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
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    PYTHON_PATH,
    PYTHON_SHA256,
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


ROOT = Path("tmp/nse_e1_homogeneous_v177_equivalence_complete_training_20260901_v181")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_v177_equivalence_complete_training_plan_v181.json"
)
PLAN_SHA256 = "049702f20fc1bd251f2bed1fce24a7e8ab0324c817e6c39d3990b1fc4406a71c"
PLAN_COMMIT = "0a41a29dd125d4a1b734b8644894b6c3b699cbfd"
GOAL = Path(
    "C:/Users/99349/.codex/attachments/"
    "1c803696-1748-4de8-9db0-ac3c738d6591/goal-objective.md"
)
GOAL_SHA256 = "95684b3a7073d6e99ea63132010a3b2627081dfb0d74e708cb2be4418932b878"
V178_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_v177_matched_v176_control_result_blind_audit_failure_v178.json"
)
V178_FAILURE_SHA256 = "e34eb8ddb75cc53f7073fa06f02a1f4f2fb599270d64bbe7fa0de14e8c1bdc03"
V178_FAILURE_HASH = "1dd368e373da69ddc2963a3e0a0370f2f2a6ee9126e53d84bd404b2c9dceb2cb"
V180_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_v179_all_nine_preunblinding_analysis_failure_v180.json"
)
V180_FAILURE_SHA256 = "6c321dd592036024201ac78708816ae61d29d56b61df314138ac326ac6027804"
V180_FAILURE_HASH = "b42dd60204045e85a9c4ec81eaf087bb636028ffa6b88fd4e5328d77bfac75ec"

SEEDS = ("E02", "E03", "E13", "E16", "E20")
V177_EXISTING = ("E06", "E10", "E11", "E12", "E15", "E18")
V176_EQUIVALENT = ("E01", "E05", "E07", "E08", "E14")
V170_EQUIVALENT = ("E04", "E09", "E17", "E19")
ARM_ID = "v181-low-v177-equivalence-complete-training"
PROFILE = v177.PROFILE
FRONTIER = v177.FRONTIER
PORT = v177.PORT
BINARY_PATH = v177.BINARY_PATH
BINARY_SHA256 = v177.BINARY_SHA256
BINARY_SOURCE_COMMIT = v177.BINARY_SOURCE_COMMIT
RECORDS_ROOT = Path("serverless_sim/records")


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v181.json",
        "schedule": root / "frozen-run-order-v181.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v181.json",
        "pairing": root / "pairing-audit-v181.json",
        "blind": root / "joint-blind-audit-v181.json",
        "result": root / "complete-training-result-v181.json",
    }


def _reread_goal() -> None:
    if hashlib.sha256(GOAL.read_bytes()).hexdigest() != GOAL_SHA256:
        raise RuntimeError("goal objective changed")


def _records_snapshot() -> dict[str, Any]:
    entries = []
    for path in sorted(item for item in RECORDS_ROOT.rglob("*") if item.is_file()):
        entries.append(
            {
                "path": path.relative_to(RECORDS_ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_hash(path),
            }
        )
    return {
        "file_count": len(entries),
        "bytes": sum(item["bytes"] for item in entries),
        "manifest_hash": object_hash(entries),
    }


def _source_products() -> list[tuple[Mapping[str, Any], Path]]:
    products = []
    for manifest_path, canonical_root in (
        (v177.paths()["ready"], v177.paths()["workspace"] / "canonical"),
        (v176.paths()["ready"], v176.paths()["workspace"] / "canonical"),
        (v175.v170.paths()["ready"], v175.v170.paths()["workspace"] / "canonical"),
        (
            v175.v170remaining.paths()["ready"],
            v175.v170remaining.paths()["workspace"] / "canonical",
        ),
    ):
        products.append((load_and_validate_manifest(manifest_path), canonical_root))
    return products


def _scan_branch_log(log: Path) -> dict[str, Any]:
    exact_one = 0
    severe_exact_one = 0
    exact_two = 0
    first_exact_two = None
    max_exact_one_density = None
    assignments = []
    windows = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            windows += 1
            decision = event["decision"]
            activation = decision["terminal_pipeline_frontier"][
                "cpu_bounded_terminal_guard"
            ]["capacity_overload_activation"]
            heavy = int(activation["heavy_incomplete_parent_terminal_players"])
            density = float(decision["srpt_hiku2_ocs_queue_router"]["queue_density"])
            assignment = decision.get("assignment_hash")
            if isinstance(assignment, bool) or not isinstance(assignment, int):
                raise RuntimeError("assignment hash is malformed")
            assignments.append(assignment)
            if heavy == 1:
                exact_one += 1
                severe_exact_one += density >= v177.SEVERE_QUEUE_THRESHOLD
                max_exact_one_density = (
                    density
                    if max_exact_one_density is None
                    else max(max_exact_one_density, density)
                )
            if heavy == 2:
                exact_two += 1
                if first_exact_two is None:
                    first_exact_two = int(event["frame"])
    if windows != 1000:
        raise RuntimeError("branch evidence window count changed")
    return {
        "windows": windows,
        "exact_one": exact_one,
        "severe_exact_one_ge32": severe_exact_one,
        "max_exact_one_queue_density": max_exact_one_density,
        "exact_two": exact_two,
        "first_exact_two_frame": first_exact_two,
        "assignments": tuple(assignments),
        "assignment_sequence_sha256": v177._assignment_sequence_sha256(assignments),
    }


def _verify_branch_partition(plan: Mapping[str, Any]) -> dict[str, Any]:
    evidence = plan["result_blind_branch_evidence"]["per_seed"]
    if [item["seed"] for item in evidence] != [f"E{i:02d}" for i in range(1, 21)]:
        raise RuntimeError("V181 branch evidence seed product changed")
    index: dict[str, tuple[Mapping[str, Any], Path]] = {}
    for manifest, canonical_root in _source_products():
        for run in manifest["runs"]:
            index[run["run_id"]] = (run, canonical_root / run["run_id"])
    role_counts: dict[str, int] = {}
    for item in evidence:
        run_id = item["run_id"]
        if run_id not in index:
            raise RuntimeError(f"V181 source run disappeared: {run_id}")
        run, canonical = index[run_id]
        manifest = next(
            manifest
            for manifest, canonical_root in _source_products()
            if canonical.parent == canonical_root
        )
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
        _assert_file(log, item["nash_sha256"], f"V181 {item['seed']} branch log")
        scanned = _scan_branch_log(log)
        for key in ("exact_one", "severe_exact_one_ge32", "exact_two"):
            if scanned[key] != item[key]:
                raise RuntimeError(f"V181 {item['seed']} {key} changed")
        if "max_exact_one_queue_density" in item and not (
            scanned["max_exact_one_queue_density"]
            == item["max_exact_one_queue_density"]
        ):
            raise RuntimeError(f"V181 {item['seed']} exact-one density changed")
        if "first_exact_two_frame" in item and not (
            scanned["first_exact_two_frame"] == item["first_exact_two_frame"]
        ):
            raise RuntimeError(f"V181 {item['seed']} first exact-two changed")
        role = item["role"]
        role_counts[role] = role_counts.get(role, 0) + 1
        if role == "v176_branch_equivalent" and scanned["severe_exact_one_ge32"]:
            raise RuntimeError("V176 reuse reaches the only V177-changing branch")
        if role == "v170_branch_equivalent" and (
            scanned["severe_exact_one_ge32"] or scanned["exact_two"]
        ):
            raise RuntimeError("V170 reuse reaches a V177-changing branch")
        if role == "new_v181_v177_required" and scanned["exact_two"] <= 0:
            raise RuntimeError("V181 required seed no longer reaches exact-two")
    expected = {
        "actual_v177_existing": 6,
        "v176_branch_equivalent": 5,
        "v170_branch_equivalent": 4,
        "new_v181_v177_required": 5,
    }
    if role_counts != expected:
        raise RuntimeError("V181 equivalence partition counts changed")
    return {
        "source_window_count": 20000,
        "performance_fields_parsed": 0,
        "role_counts": role_counts,
        "partition_pass": True,
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v177._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V181 plan"),
        (GOAL, GOAL_SHA256, "goal objective"),
        (V178_FAILURE, V178_FAILURE_SHA256, "V178 failure receipt"),
        (V180_FAILURE, V180_FAILURE_SHA256, "V180 failure receipt"),
        (BINARY_PATH, BINARY_SHA256, "V177 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    if (
        _assert_hashed(read_json(V178_FAILURE), "receipt_hash", "V178 failure")
        != V178_FAILURE_HASH
    ):
        raise RuntimeError("V178 failure receipt changed")
    if (
        _assert_hashed(read_json(V180_FAILURE), "receipt_hash", "V180 failure")
        != V180_FAILURE_HASH
    ):
        raise RuntimeError("V180 failure receipt changed")
    plan = read_json(PLAN)
    partition = plan["fixed_twenty_seed_partition"]
    if not (
        plan["training_only"] is True
        and plan["formal_results_eligible"] is False
        and plan["scientific_status"]["result_informed_reassessment_disclosed"] is True
        and plan["scientific_status"][
            "performance_values_used_to_choose_the_five_new_seeds"
        ]
        is False
        and plan["scientific_status"][
            "branch_telemetry_only_used_to_choose_the_five_new_seeds"
        ]
        is True
        and tuple(partition["actual_v177_existing"]) == V177_EXISTING
        and tuple(partition["v176_branch_equivalent"]) == V176_EQUIVALENT
        and tuple(partition["v170_branch_equivalent"]) == V170_EQUIVALENT
        and tuple(partition["new_v181_v177_required"]) == SEEDS
        and tuple(partition["new_run_order"]) == SEEDS
        and plan["execution_contract"]["new_online_runs"] == len(SEEDS)
        and plan["execution_contract"]["new_reference_builds"] == len(SEEDS)
        and plan["execution_contract"]["baseline_reruns"] == 0
        and plan["execution_contract"][
            "no_seed_deletion_replacement_relabeling_or_selective_rerun"
        ]
        is True
    ):
        raise RuntimeError("V181 plan contract changed")
    _verify_branch_partition(plan)
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    snapshot = _records_snapshot()
    if snapshot["file_count"] != 6 or snapshot["bytes"] != 254320:
        raise RuntimeError("shared serverless_sim/records changed")
    return source


def _metadata(commit: str, source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "v181_training_only": True,
        "v181_role": "fixed_complement_for_complete_v177_equivalent_profile",
        "v181_plan_sha256": PLAN_SHA256,
        "v181_plan_commit": PLAN_COMMIT,
        "v181_protocol_source_commit": commit,
        "v181_binary_source_commit": BINARY_SOURCE_COMMIT,
        "v181_binary_sha256": BINARY_SHA256,
        "v181_profile": PROFILE,
        "v181_player_frontier": FRONTIER,
        "v181_source_e1_run_id": source.get("v155_source_e1_run_id"),
        "v181_source_e1_run_spec_hash": source.get("v155_source_e1_run_spec_hash"),
        "v181_performance_summaries_parsed_before_run": 0,
        "v181_seed_selection_uses_branch_telemetry_only": True,
        "v181_valid_seed_deletion_replacement_or_selective_rerun": False,
    }


def _rewrite_candidate(source: dict[str, Any], commit: str) -> dict[str, Any]:
    rewritten = v155._rewrite_candidate(source, commit)
    by_seed = {run["seed"]: run for run in rewritten["runs"]}
    if set(by_seed) != {f"E{i:02d}" for i in range(1, 21)}:
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
            "purpose": "V181 fixed five-run complement for one complete V177-equivalent training profile",
            "v181_role": "fixed_complement_for_complete_v177_equivalent_profile",
            "v181_plan_sha256": PLAN_SHA256,
            "v181_plan_commit": PLAN_COMMIT,
            "v181_protocol_source_commit": commit,
            "v181_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v181_binary_sha256": BINARY_SHA256,
            "v181_profile": PROFILE,
            "v181_player_frontier": FRONTIER,
            "v181_expected_run_count": len(SEEDS),
            "v181_expected_reference_build_count": len(SEEDS),
            "v181_fixed_order": list(SEEDS),
            "v181_performance_summaries_parsed": 0,
            "v181_seed_selection_uses_branch_telemetry_only": True,
            "v181_environment": COMMON_ENVIRONMENT,
        }
    )
    for run in rewritten["runs"]:
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = _metadata(commit, run.get("metadata", {}))
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


def _validate_product(manifest: Mapping[str, Any], *, bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == len(SEEDS)
        and [run["seed"] for run in manifest["runs"]] == list(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and len(manifest.get("reference_build_dependencies", [])) == len(SEEDS)
        and manifest.get("all_references_bound") is bound
    ):
        raise RuntimeError("V181 exact five-run product changed")
    expected_env = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and all(run["environment"].get(k) == v for k, v in expected_env.items())
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v181_profile") == PROFILE
            and metadata.get("v181_player_frontier") == FRONTIER
            and metadata.get("v181_seed_selection_uses_branch_telemetry_only") is True
        ):
            raise RuntimeError(f"V181 run contract changed: {run.get('run_id')}")


def prepare_v181(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V181 root: {root}")
    root.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    manifest = _rewrite_candidate(source, commit)
    _validate_product(manifest, bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_EQUIVALENCE_COMPLETE_TRAINING_SCHEDULE_V181_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_EQUIVALENCE_COMPLETE_TRAINING_PREPARED_V181_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "candidate_performance_summaries_parsed": 0,
        "goal_objective_sha256": GOAL_SHA256,
        "plan_sha256": PLAN_SHA256,
        "plan_commit": PLAN_COMMIT,
        "protocol_source_commit": commit,
        "binary_source_commit": BINARY_SOURCE_COMMIT,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": MODULE_CONF_SEMANTIC_HASH,
        "new_online_runs": len(SEEDS),
        "new_reference_builds": len(SEEDS),
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "branch_partition": _verify_branch_partition(read_json(PLAN)),
        "shared_records_snapshot": _records_snapshot(),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v181(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V181 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V181 prepared receipt")
    if _records_snapshot() != prepared["shared_records_snapshot"]:
        raise RuntimeError("shared records changed before V181 execution")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, bound=True)
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
        _reread_goal()
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(f"V181 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V181 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    if _records_snapshot() != prepared["shared_records_snapshot"]:
        raise RuntimeError("shared records changed during V181 execution")
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_EQUIVALENCE_COMPLETE_TRAINING_EXECUTION_V181_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "goal_reread_before_every_dispatch": True,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": len(SEEDS),
        "dispatches": dispatches,
        "shared_records_snapshot": _records_snapshot(),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _audit_new_run(
    canonical: Path, run: Mapping[str, Any], expected_first_exact_two: int
) -> dict[str, Any]:
    telemetry = v177._audit_nash_log(canonical, run, frozen_base=None)
    current_log = (
        canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    )
    current = _scan_branch_log(current_log)
    frozen = v175._frozen_v170_assignment_hashes(run["seed"])
    mismatch = [
        index
        for index, (candidate, control) in enumerate(
            zip(current["assignments"], frozen)
        )
        if candidate != control
    ]
    first_mismatch = mismatch[0] if mismatch else None
    prefix_pass = tuple(current["assignments"][:expected_first_exact_two]) == tuple(
        frozen[:expected_first_exact_two]
    )
    first_differs = (
        current["assignments"][expected_first_exact_two]
        != frozen[expected_first_exact_two]
    )
    exact_two_contract = (
        telemetry["capacity_overload_exact_two_windows"] > 0
        and telemetry["capacity_overload_exact_two_heavy_terminal_rejections"]
        == 2 * telemetry["capacity_overload_exact_two_windows"]
    )
    return {
        **telemetry,
        "frozen_v170_assignment_sequence_sha256": v177._assignment_sequence_sha256(
            frozen
        ),
        "first_exact_two_frame": current["first_exact_two_frame"],
        "expected_first_exact_two_frame": expected_first_exact_two,
        "first_assignment_mismatch_frame_vs_v170": first_mismatch,
        "pre_first_exact_two_assignment_prefix_matches_v170": prefix_pass,
        "first_exact_two_frame_assignment_differs_from_v170": first_differs,
        "first_divergence_is_first_exact_two": first_mismatch
        == expected_first_exact_two
        == current["first_exact_two_frame"],
        "exact_two_guard_rejects_both_heavy_players": exact_two_contract,
    }


def blind_audit_v181(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V181 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V181 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V181 execution receipt")
    if _records_snapshot() != prepared["shared_records_snapshot"]:
        raise RuntimeError("shared records changed before V181 blind audit")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed")
        and pairing.get("run_count") == len(SEEDS)
        and pairing.get("group_count") == len(SEEDS)
    ):
        raise RuntimeError("V181 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=len(SEEDS)
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V181 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {item.name for item in canonical_root.iterdir() if item.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V181 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V181 has quarantined attempts")
    expected_frames = read_json(PLAN)["pre_unblinding_mechanism_gate"][
        "all_five_first_exact_two_frames_must_equal"
    ]
    audits = []
    identities = set()
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
        audits.append(_audit_new_run(canonical, run, int(expected_frames[run["seed"]])))
    if len(identities) != 1:
        raise RuntimeError("V181 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V181 runtime identity changed")
    mechanism_pass = all(
        item["first_divergence_is_first_exact_two"]
        and item["exact_two_guard_rejects_both_heavy_players"]
        and item["performance_outcome_fields_parsed"] == 0
        for item in audits
    )
    if not mechanism_pass:
        raise RuntimeError("V181 pre-unblinding mechanism gate failed")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_EQUIVALENCE_COMPLETE_TRAINING_BLIND_AUDIT_V181_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
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
        "branch_partition": _verify_branch_partition(read_json(PLAN)),
        "all_five_first_diverge_at_first_exact_two": True,
        "all_five_exact_two_guard_rejects_both_heavy_players": True,
        "mechanism_gate_pass": mechanism_pass,
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "per_run_result_blind_audits": audits,
        "shared_records_snapshot": _records_snapshot(),
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _load_rows(
    manifest: Mapping[str, Any], root: Path, expected_seeds: Sequence[str]
) -> list[dict[str, Any]]:
    rows = []
    for run in manifest["runs"]:
        if run["seed"] not in expected_seeds:
            continue
        summary_path = (
            root
            / "formal-runs"
            / "canonical"
            / run["run_id"]
            / "reviewer_records"
            / run["run_id"]
            / "summary.json"
        )
        values = _nse_summary_metrics(read_json(summary_path))
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
    rows.sort(key=lambda item: item["seed"])
    if [row["seed"] for row in rows] != sorted(expected_seeds):
        raise RuntimeError("candidate result seed product changed")
    return rows


def _compose_complete_profile(
    v170_rows: Sequence[Mapping[str, Any]],
    v176_rows: Sequence[Mapping[str, Any]],
    v177_rows: Sequence[Mapping[str, Any]],
    v181_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources = {
        "v170_branch_equivalent": {row["seed"]: dict(row) for row in v170_rows},
        "v176_branch_equivalent": {row["seed"]: dict(row) for row in v176_rows},
        "actual_v177_existing": {row["seed"]: dict(row) for row in v177_rows},
        "new_v181_v177_required": {row["seed"]: dict(row) for row in v181_rows},
    }
    partition = {
        "actual_v177_existing": V177_EXISTING,
        "v176_branch_equivalent": V176_EQUIVALENT,
        "v170_branch_equivalent": V170_EQUIVALENT,
        "new_v181_v177_required": SEEDS,
    }
    rows = []
    lineage = []
    for seed in (f"E{i:02d}" for i in range(1, 21)):
        roles = [role for role, seeds in partition.items() if seed in seeds]
        if len(roles) != 1 or seed not in sources[roles[0]]:
            raise RuntimeError(f"V181 complete profile lineage changed: {seed}")
        role = roles[0]
        row = dict(sources[role][seed])
        rows.append(row)
        lineage.append({"seed": seed, "source_role": role, "run_id": row["run_id"]})
    return rows, lineage


def reveal_v181(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V181 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V181 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("all_five_first_diverge_at_first_exact_two") is True
        and blind.get("all_five_exact_two_guard_rejects_both_heavy_players") is True
        and blind.get("mechanism_gate_pass") is True
    ):
        raise RuntimeError("V181 blind audit did not authorize reveal")
    _reread_goal()
    manifest = load_and_validate_manifest(output["ready"])
    v181_rows = _load_rows(manifest, root, SEEDS)
    v170_all = v175._load_v170_candidate()
    v176_manifest = load_and_validate_manifest(v176.paths()["ready"])
    v176_rows = _load_rows(v176_manifest, v176.ROOT, V176_EQUIVALENT)
    v177_manifest = load_and_validate_manifest(v177.paths()["ready"])
    v177_rows = _load_rows(v177_manifest, v177.ROOT, V177_EXISTING)
    complete, lineage = _compose_complete_profile(
        [row for row in v170_all if row["seed"] in V170_EQUIVALENT],
        v176_rows,
        v177_rows,
        v181_rows,
    )
    evaluation = _evaluate_load("low", complete, _load_baselines())
    throughput = evaluation["gates"]["throughput"]
    qpr_finite = evaluation["gates"]["qpr_finite_only"]
    qpr_zero = evaluation["gates"]["qpr_zero_completed_as_zero"]
    if not (
        throughput["ceiling_algorithm"] == "Orion"
        and throughput["ceiling_mean"] == 1.4741
        and qpr_finite["ceiling_algorithm"] == "OCS"
        and qpr_finite["ceiling_mean"] == 0.055577160345697
        and qpr_zero["ceiling_algorithm"] == "OCS"
        and qpr_zero["ceiling_mean"] == 0.055577160345697
    ):
        raise RuntimeError("V181 frozen baseline ceilings changed")
    passed = bool(evaluation["all_three_metric_gates_pass"])
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_EQUIVALENCE_COMPLETE_TRAINING_RESULT_V181_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "new_online_run_count": len(SEEDS),
        "new_reference_build_count": len(SEEDS),
        "baseline_rerun_count": 0,
        "complete_profile_run_count": len(complete),
        "all_twenty_seeds_included": True,
        "profile": PROFILE,
        "complete_profile_lineage": lineage,
        "complete_profile_rows": complete,
        "hybrid_low_evaluation": evaluation,
        "joint_training_pass": passed,
        "homogeneous_low_training_closed": passed,
        "homogeneous_low_paper_claim_closed": False,
        "confirmation_inputs_generated": False,
        "disposition": (
            "freeze_complete_twenty_seed_V177_equivalent_training_result_and_require_a_separately_committed_fresh_seed_confirmation_plan"
            if passed
            else "retain_all_five_valid_V181_runs_and_retire_V181_without_subset_reporting"
        ),
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
        "middle_high_or_later_section_authorized": False,
        "shared_records_snapshot": _records_snapshot(),
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
        document, key = prepare_v181(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v181(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v181(), "blind_audit_hash"
    else:
        document, key = reveal_v181(), "result_hash"
    print(json.dumps({key: document[key], "runs": len(SEEDS)}))


if __name__ == "__main__":
    main()
