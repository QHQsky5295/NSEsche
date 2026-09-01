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
    nse_e1_homogeneous_v177_matched_v176_control_result_blind_audit_v178 as v178,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_requestcohort1_shortest_request_least_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v175 as v175,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v159 as v159,
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
    "tmp/nse_e1_homogeneous_concurrent2_queue8_cpu2_bounded_terminal_low_diagnostic_20260901_v179"
)
GOAL = Path(
    "C:/Users/99349/.codex/attachments/1c803696-1748-4de8-9db0-ac3c738d6591/goal-objective.md"
)
GOAL_SHA256 = "95684b3a7073d6e99ea63132010a3b2627081dfb0d74e708cb2be4418932b878"
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_queue8_cpu2_bounded_terminal_low_diagnostic_plan_v179.json"
)
PLAN_SHA256 = "c95d654d9fc4de3c6dcf586cea25bcff5b5f39df6daf2a50fed9ac0148e50f68"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_queue8_cpu2_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_implementation_v179.json"
)
IMPLEMENTATION_SHA256 = (
    "ff0e01060f263e180215adfe8956f1e4abe5c0f1bfda16057f1a456814b4f087"
)
BLIND_AUDIT_AMENDMENT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_v179_result_blind_control_mapping_amendment_v179a.json"
)
BLIND_AUDIT_AMENDMENT_SHA256 = (
    "ef3129e486bf872252d86e318946e24eedabd71cc7a3e8b270284ac4d1b94c6c"
)
V170_RESULT = v175.V170_COMPLETE_RESULT
V170_RESULT_SHA256 = v175.V170_COMPLETE_RESULT_SHA256
V170_RESULT_HASH = v175.V170_COMPLETE_RESULT_HASH
V176_RESULT = v176.ROOT / "diagnostic-result-v176.json"
V176_RESULT_SHA256 = "a84a89faa95d82129ebbef2619ea9cd2b7d6bf0fbfc93aca689b6d3ceb24a9c2"
V176_RESULT_HASH = "faac945e6b3dcc937e37d64e7a0c64cde3305950ce1da9bf733710c02aab8199"
V178_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_v177_matched_v176_control_result_blind_audit_failure_v178.json"
)
V178_FAILURE_SHA256 = "e34eb8ddb75cc53f7073fa06f02a1f4f2fb599270d64bbe7fa0de14e8c1bdc03"
V178_FAILURE_HASH = "1dd368e373da69ddc2963a3e0a0370f2f2a6ee9126e53d84bd404b2c9dceb2cb"

SEEDS = ("E01", "E05", "E06", "E09", "E10", "E12", "E15", "E17", "E18")
POSITIVE_SEEDS = ("E01", "E05", "E06", "E10", "E12", "E15", "E17")
NEGATIVE_CONTROL_SEEDS = ("E09", "E18")
FIRST_DIVERGENCE_SEEDS = ("E01", "E05", "E06", "E10", "E12", "E15")
V176_REUSE_SEEDS = ("E07", "E08", "E14")
V170_REUSE_SEEDS = ("E02", "E03", "E04", "E11", "E13", "E16", "E19", "E20")

PROFILE = "srpt_slack_concurrent2_queue8_cpu2_bounded_terminal_short5p5_pipeline_hiku2_ocs_queue8"
ARM_ID = "v179-low-srpt-slack-concurrent2-queue8-cpu2-bounded-terminal-short5p5-pipeline-hiku2-ocs-queue8"
FRONTIER = (
    "parents_completed_or_concurrent2_queue8_cpu2_bounded_terminal_or_slack_short_work_"
    "parents_scheduled"
)
BINARY_SOURCE_COMMIT = "614461bb4b3ec408fb27bed0ed4dfbf39f300444"
BINARY_PATH = Path("serverless_sim/target_e1_v179/release/serverless_sim.exe")
BINARY_SHA256 = "82ecbb4bc23d49c5f6b3e80ad66befe7361c93a88d19b0864ebe21a58463de00"
PORT = v159.PORT
CPU_THRESHOLD = 1.0
CPU_UPPER_THRESHOLD = 2.0
HEAVY_PLAYER_THRESHOLD = 1
QUEUE_THRESHOLD = v159.QUEUE_THRESHOLD
SHORT_WORK_THRESHOLD = v159.SHORT_WORK_THRESHOLD
LOW_EXPERT = v159.LOW_EXPERT
HIGH_EXPERT = v159.HIGH_EXPERT
SELECTED_THROUGHPUT_SUM_GATE = 12.581000000000001
SELECTED_QPR_SUM_GATE = 0.40358639189433965
SELECTED_THROUGHPUT_WIN_GATE = 5
SELECTED_QPR_WIN_GATE = 7


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v179.json",
        "schedule": root / "frozen-run-order-v179.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v179.json",
        "pairing": root / "pairing-audit-v179.json",
        "blind": root / "joint-blind-audit-v179.json",
        "result": root / "diagnostic-result-v179.json",
    }


def _reread_goal() -> None:
    payload = GOAL.read_bytes()
    if hashlib.sha256(payload).hexdigest() != GOAL_SHA256:
        raise RuntimeError("goal objective changed")
    print(payload.decode("utf-8"), flush=True)


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v159._assert_frozen_inputs()
    for path, sha256, label in (
        (GOAL, GOAL_SHA256, "goal objective"),
        (PLAN, PLAN_SHA256, "V179 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V179 implementation"),
        (
            BLIND_AUDIT_AMENDMENT,
            BLIND_AUDIT_AMENDMENT_SHA256,
            "V179 result-blind amendment",
        ),
        (V170_RESULT, V170_RESULT_SHA256, "V170 complete result"),
        (V176_RESULT, V176_RESULT_SHA256, "V176 result"),
        (V178_FAILURE, V178_FAILURE_SHA256, "V178 failure receipt"),
        (BINARY_PATH, BINARY_SHA256, "V179 binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    implementation = read_json(IMPLEMENTATION)
    change = implementation.get("single_scientific_change", {})
    telemetry = implementation.get("telemetry_contract", {})
    if not (
        _assert_hashed(implementation, "receipt_hash", "V179 implementation")
        == "a04825154ef41e455552026986db6bd9a6bd8b151f6e09d4643a8ed03993bf10"
        and implementation.get("implementation_commit") == BINARY_SOURCE_COMMIT
        and implementation.get("plan_file_sha256") == PLAN_SHA256
        and implementation.get("isolated_release", {}).get("sha256") == BINARY_SHA256
        and change.get("to_profile") == PROFILE
        and change.get("bounded_single_queue_density_threshold") == QUEUE_THRESHOLD
        and change.get("bounded_single_normalized_cpu_upper_threshold")
        == CPU_UPPER_THRESHOLD
        and change.get("uses_seed_load_dag_function_or_performance_labels") is False
        and telemetry.get("version") == "V179"
        and telemetry.get("player_frontier") == FRONTIER
    ):
        raise RuntimeError("V179 implementation boundary changed")
    amendment = read_json(BLIND_AUDIT_AMENDMENT)
    if not (
        _assert_hashed(amendment, "receipt_hash", "V179 result-blind amendment")
        == "b7aedeb199dc1feb58162297ca5b76d206e00c1c6fcd0204e878142c6595478a"
        and amendment.get("performance_fields_parsed") == 0
        and amendment.get("additional_online_runs_or_reference_builds_authorized") == 0
    ):
        raise RuntimeError("V179 result-blind amendment changed")
    if (
        _assert_hashed(read_json(V170_RESULT), "result_hash", "V170 result")
        != V170_RESULT_HASH
    ):
        raise RuntimeError("V170 result changed")
    if (
        _assert_hashed(read_json(V176_RESULT), "result_hash", "V176 result")
        != V176_RESULT_HASH
    ):
        raise RuntimeError("V176 result changed")
    failure = read_json(V178_FAILURE)
    if not (
        _assert_hashed(failure, "receipt_hash", "V178 failure") == V178_FAILURE_HASH
        and failure.get("diagnostic_result", {}).get("joint_pass") is False
    ):
        raise RuntimeError("V178 result-blind audit boundary changed")
    plan = read_json(PLAN)
    if not (
        plan.get("goal_objective_sha256") == GOAL_SHA256
        and plan.get("diagnostic_design", {}).get("seeds") == list(SEEDS)
        and plan.get("diagnostic_design", {}).get("positive_mechanism_seeds")
        == list(POSITIVE_SEEDS)
        and plan.get("diagnostic_design", {}).get("negative_control_seeds")
        == list(NEGATIVE_CONTROL_SEEDS)
    ):
        raise RuntimeError("V179 plan product changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "module_conf_es.json",
    )
    return source


def _metadata(commit: str, source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "v179_training_only": True,
        "v179_role": "result_blind_queue8_cpu2_bounded_lone_terminal_falsification",
        "v179_plan_sha256": PLAN_SHA256,
        "v179_implementation_sha256": IMPLEMENTATION_SHA256,
        "v179_binary_source_commit": BINARY_SOURCE_COMMIT,
        "v179_protocol_source_commit": commit,
        "v179_binary_sha256": BINARY_SHA256,
        "v179_arm_id": ARM_ID,
        "v179_profile": PROFILE,
        "v179_player_frontier": FRONTIER,
        "v179_queue_density_threshold": QUEUE_THRESHOLD,
        "v179_lone_heavy_cpu_upper_threshold": CPU_UPPER_THRESHOLD,
        "v179_source_e1_run_id": source.get("v155_source_e1_run_id"),
        "v179_source_e1_run_spec_hash": source.get("v155_source_e1_run_spec_hash"),
        "v179_candidate_performance_summaries_parsed_before_run": 0,
    }


def _rewrite_candidate(source: dict[str, Any], commit: str) -> dict[str, Any]:
    rewritten = v155._rewrite_candidate(source, commit)
    by_seed = {run["seed"]: run for run in rewritten["runs"]}
    if set(by_seed) != {f"E{index:02d}" for index in range(1, 21)}:
        raise RuntimeError("V155 complete source product changed")
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
            "purpose": "V179 outcome-disclosed nine-seed training diagnosis; never a formal result or paper claim",
            "v179_role": "result_blind_queue8_cpu2_bounded_lone_terminal_falsification",
            "v179_plan_sha256": PLAN_SHA256,
            "v179_implementation_sha256": IMPLEMENTATION_SHA256,
            "v179_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v179_protocol_source_commit": commit,
            "v179_binary_sha256": BINARY_SHA256,
            "v179_arm_id": ARM_ID,
            "v179_profile": PROFILE,
            "v179_player_frontier": FRONTIER,
            "v179_queue_density_threshold": QUEUE_THRESHOLD,
            "v179_lone_heavy_cpu_upper_threshold": CPU_UPPER_THRESHOLD,
            "v179_environment": COMMON_ENVIRONMENT,
            "v179_expected_run_count": len(SEEDS),
            "v179_expected_reference_build_count": len(SEEDS),
            "v179_fixed_order": list(SEEDS),
            "v179_candidate_performance_summaries_parsed": 0,
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
        and [run.get("seed") for run in manifest["runs"]] == list(SEEDS)
        and {run.get("method") for run in manifest["runs"]} == {"sche_nash"}
        and len(manifest.get("reference_build_dependencies", [])) == len(SEEDS)
        and manifest.get("all_references_bound") is bound
    ):
        raise RuntimeError("V179 exact product changed")
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run.get("experiment_id") == "E1"
            and run.get("workload", {}).get("request_freq") == "low"
            and run.get("cluster") == {"node_count": 20, "topology": "homogeneous"}
            and run.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == PROFILE
            and run.get("environment", {}).get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v179_profile") == PROFILE
            and metadata.get("v179_player_frontier") == FRONTIER
            and metadata.get("v179_queue_density_threshold") == QUEUE_THRESHOLD
            and metadata.get("v179_lone_heavy_cpu_upper_threshold")
            == CPU_UPPER_THRESHOLD
        ):
            raise RuntimeError(f"V179 run contract changed: {run.get('run_id')}")


def prepare_v179(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V179 root: {root}")
    root.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    manifest = _rewrite_candidate(source, commit)
    _validate_product(manifest, bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_QUEUE8_CPU2_BOUNDED_TERMINAL_LOW_SCHEDULE_V179_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_QUEUE8_CPU2_BOUNDED_TERMINAL_LOW_PREPARED_V179_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "candidate_performance_summaries_parsed": 0,
        "goal_objective_sha256": GOAL_SHA256,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": MODULE_CONF_SEMANTIC_HASH,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "candidate_online_runs": len(SEEDS),
        "candidate_reference_builds": len(SEEDS),
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "queue_density_threshold": QUEUE_THRESHOLD,
        "lone_heavy_cpu_upper_threshold": CPU_UPPER_THRESHOLD,
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v179(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V179 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V179 prepared receipt")
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
            raise RuntimeError(f"V179 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V179 canonical is not a QC pass: {run['run_id']}")
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
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_QUEUE8_CPU2_BOUNDED_TERMINAL_LOW_EXECUTION_V179_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "goal_reread_before_every_dispatch": True,
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


def _frozen_assignment_hashes(seed: str) -> tuple[int, ...]:
    if seed in v178.CONTROL_SEEDS:
        manifest = load_and_validate_manifest(v178.paths()["ready"])
        run = next(item for item in manifest["runs"] if item.get("seed") == seed)
        canonical = v178.paths()["workspace"] / "canonical" / run["run_id"]
        return v178._assignment_hashes(canonical, run["run_id"])
    if seed not in {"E01", "E05", "E10"}:
        return v175._frozen_v170_assignment_hashes(seed)
    manifest = load_and_validate_manifest(v176.paths()["ready"])
    run = next(item for item in manifest["runs"] if item.get("seed") == seed)
    log = (
        v176.paths()["workspace"]
        / "canonical"
        / run["run_id"]
        / "reviewer_records"
        / run["run_id"]
        / "nash_metrics.jsonl.gz"
    )
    hashes = []
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("kind") == "window":
                hashes.append(event["decision"]["assignment_hash"])
    if len(hashes) != 1000:
        raise RuntimeError("V176 assignment cardinality changed")
    return tuple(hashes)


def _audit_nash_log(
    canonical: Path, run: Mapping[str, Any], frozen: Sequence[int]
) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    kinds = {"run_config": 0, "window": 0, "run_summary": 0}
    assignments: list[int] = []
    bounded_frames: list[int] = []
    exact_one_unbounded = 0
    exact_two = 0
    bypass = 0
    low_routes = 0
    high_routes = 0
    reference_available = 0
    reference_not_requested = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind == "function_profile":
                continue
            if kind not in kinds:
                raise RuntimeError(f"unexpected V179 Nash event: {kind}")
            kinds[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                activation = contract.get("cpu_bounded_terminal_guard", {}).get(
                    "capacity_overload_activation", {}
                )
                if not (
                    event.get("operational_expert_proxy") == PROFILE
                    and event.get("operational_player_frontier") == FRONTIER
                    and contract.get("version") == "V179"
                    and contract.get("player_frontier") == FRONTIER
                    and activation.get("bounded_single_queue_density_threshold")
                    == QUEUE_THRESHOLD
                    and activation.get("bounded_single_normalized_cpu_upper_threshold")
                    == CPU_UPPER_THRESHOLD
                    and activation.get(
                        "uses_seed_load_dag_function_or_performance_labels"
                    )
                    is False
                ):
                    raise RuntimeError("V179 run_config contract changed")
                continue
            if kind == "run_summary":
                if event.get("observation_writer_error") is not None:
                    raise RuntimeError("V179 Nash writer failed")
                continue
            frame = event.get("frame")
            decision = event.get("decision", {})
            assignment = decision.get("assignment_hash")
            if (
                isinstance(frame, bool)
                or not isinstance(frame, int)
                or isinstance(assignment, bool)
                or not isinstance(assignment, int)
                or assignment < 0
            ):
                raise RuntimeError("V179 window identity changed")
            assignments.append(assignment)
            frontier = decision.get("terminal_pipeline_frontier", {})
            guard = frontier.get("cpu_bounded_terminal_guard", {})
            activation = guard.get("capacity_overload_activation", {})
            heavy = v159._count(
                activation.get("heavy_incomplete_parent_terminal_players"), "heavy"
            )
            rejected = v159._count(
                guard.get("rejected_heavy_incomplete_parent_terminal_players"),
                "rejected heavy",
            )
            inactive_admissions = v159._count(
                activation.get("guard_inactive_heavy_terminal_admissions"),
                "inactive heavy admissions",
            )
            q = v159._finite_optional(
                activation.get("operational_queue_density"), "queue density"
            )
            lone_cpu = v159._finite_optional(
                activation.get("lone_heavy_normalized_cpu"), "lone heavy CPU"
            )
            expected_primary = heavy > HEAVY_PLAYER_THRESHOLD
            expected_bounded = (
                heavy == 1
                and q is not None
                and q >= QUEUE_THRESHOLD
                and lone_cpu is not None
                and lone_cpu > CPU_THRESHOLD
                and lone_cpu <= CPU_UPPER_THRESHOLD
            )
            expected_active = expected_primary or expected_bounded
            if not (
                frontier.get("enabled") is True
                and frontier.get("definition") == FRONTIER
                and frontier.get("short_work_remaining_work_threshold")
                == SHORT_WORK_THRESHOLD
                and guard.get("enabled") is True
                and guard.get("normalized_cpu_threshold") == CPU_THRESHOLD
                and guard.get("uses_completion_or_performance_outcomes") is False
                and activation.get("enabled") is True
                and activation.get("node_count_threshold") == 20
                and activation.get("heavy_player_count_threshold") == 1
                and activation.get("minimum_active_heavy_player_count") == 1
                and activation.get("threshold_kind") == "fixed_one_current_heavy_player"
                and activation.get("operational_queue_density_source")
                == "current_pending_plus_runnable_tasks_per_node"
                and activation.get("bounded_single_queue_density_threshold")
                == QUEUE_THRESHOLD
                and activation.get("bounded_single_queue_boundary")
                == "at_or_above_is_eligible"
                and activation.get("bounded_single_normalized_cpu_upper_threshold")
                == CPU_UPPER_THRESHOLD
                and activation.get("bounded_single_normalized_cpu_upper_boundary")
                == "at_or_below_is_eligible"
                and activation.get("primary_heavy_count_activation") is expected_primary
                and activation.get("bounded_single_activation") is expected_bounded
                and activation.get("guard_active") is expected_active
                and activation.get("guard_inactive") is (not expected_active)
                and activation.get("uses_seed_load_dag_function_or_performance_labels")
                is False
                and (
                    expected_active
                    and rejected == heavy
                    and inactive_admissions == 0
                    or not expected_active
                    and rejected == 0
                    and inactive_admissions == heavy
                )
            ):
                raise RuntimeError("V179 bounded guard invariant changed")
            if heavy == 1:
                if lone_cpu is None or lone_cpu <= CPU_THRESHOLD:
                    raise RuntimeError("V179 lone-heavy telemetry changed")
                if expected_bounded:
                    bounded_frames.append(frame)
                else:
                    exact_one_unbounded += 1
            if heavy == 2:
                exact_two += 1
            bypass += v159._count(
                guard.get("parents_completed_heavy_terminal_bypass_players"), "bypass"
            )
            queue_gate = frontier.get("short_work_queue_gate", {})
            admitted_work = v159._finite_optional(
                frontier.get("admitted_short_work_remaining_work_max"), "short work"
            )
            rejected_work = v159._finite_optional(
                frontier.get("rejected_nonterminal_remaining_work_min"), "rejected work"
            )
            admitted_density = v159._finite_optional(
                queue_gate.get("admitted_short_work_queue_density_max"),
                "admitted density",
            )
            rejected_density = v159._finite_optional(
                queue_gate.get("rejected_short_work_queue_density_min"),
                "rejected density",
            )
            if not (
                queue_gate.get("enabled") is True
                and queue_gate.get("threshold") == QUEUE_THRESHOLD
                and queue_gate.get("boundary") == "below_is_strict"
                and (admitted_work is None or admitted_work <= SHORT_WORK_THRESHOLD)
                and (rejected_work is None or rejected_work > SHORT_WORK_THRESHOLD)
                and (admitted_density is None or admitted_density < QUEUE_THRESHOLD)
                and (rejected_density is None or rejected_density >= QUEUE_THRESHOLD)
            ):
                raise RuntimeError("V179 short-work invariant changed")
            route = decision.get("srpt_hiku2_ocs_queue_router", {})
            density = v159._finite_optional(route.get("queue_density"), "route density")
            expected_expert = LOW_EXPERT if density < QUEUE_THRESHOLD else HIGH_EXPERT
            if not (
                route.get("enabled") is True
                and route.get("queue_density_threshold") == QUEUE_THRESHOLD
                and route.get("player_frontier") == FRONTIER
                and route.get("selected_expert") == expected_expert
                and route.get("uses_completion_outcomes") is False
            ):
                raise RuntimeError("V179 route invariant changed")
            low_routes += expected_expert == LOW_EXPERT
            high_routes += expected_expert == HIGH_EXPERT
            social = event.get("social", {})
            if social.get("reference_state_key") is None:
                if social.get("reference_source") != "not_requested":
                    raise RuntimeError("V179 reference reason changed")
                reference_not_requested += 1
            elif social.get("reference_source") in (
                "offline_table",
                "offline_table_nonpositive",
            ):
                reference_available += 1
            else:
                raise RuntimeError("V179 reference source changed")
    if kinds != {"run_config": 1, "window": 1000, "run_summary": 1}:
        raise RuntimeError("V179 Nash log cardinality changed")
    if len(frozen) != len(assignments):
        raise RuntimeError("V179 frozen assignment cardinality changed")
    mismatches = [
        i for i, pair in enumerate(zip(assignments, frozen)) if pair[0] != pair[1]
    ]
    first_activation = bounded_frames[0] if bounded_frames else None
    first_mismatch = mismatches[0] if mismatches else None
    if first_activation is not None and assignments[:first_activation] != list(
        frozen[:first_activation]
    ):
        raise RuntimeError("V179 diverged before bounded activation")
    return {
        "seed": run["seed"],
        "run_id": run_id,
        "windows": len(assignments),
        "bounded_single_activation_windows": len(bounded_frames),
        "first_bounded_single_activation_frame": first_activation,
        "exact_one_unbounded_windows": exact_one_unbounded,
        "exact_two_windows": exact_two,
        "parents_completed_heavy_bypass_players": bypass,
        "low_route_windows": low_routes,
        "high_route_windows": high_routes,
        "reference_available_windows": reference_available,
        "reference_not_requested_windows": reference_not_requested,
        "first_assignment_mismatch_frame_vs_frozen_base": first_mismatch,
        "assignment_sequence_sha256": hashlib.sha256(
            "\n".join(map(str, assignments)).encode("utf-8")
        ).hexdigest(),
        "frozen_assignment_sequence_sha256": hashlib.sha256(
            "\n".join(map(str, frozen)).encode("utf-8")
        ).hexdigest(),
    }


def blind_audit_v179(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V179 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V179 prepared")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V179 execution")
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
        raise RuntimeError("V179 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=len(SEEDS)
    )
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V179 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V179 has unexplained quarantine")
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
        audits.append(
            _audit_nash_log(canonical, run, _frozen_assignment_hashes(run["seed"]))
        )
    if len(identities) != 1:
        raise RuntimeError("V179 runtime identity is not unanimous")
    binary, commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V179 runtime identity changed")
    by_seed = {item["seed"]: item for item in audits}
    positive_exercised = all(
        by_seed[seed]["bounded_single_activation_windows"] > 0
        for seed in POSITIVE_SEEDS
    )
    negative_controls = all(
        by_seed[seed]["bounded_single_activation_windows"] == 0
        and by_seed[seed]["first_assignment_mismatch_frame_vs_frozen_base"] is None
        and by_seed[seed]["exact_one_unbounded_windows"] > 0
        for seed in NEGATIVE_CONTROL_SEEDS
    )
    exact_first_divergence = all(
        by_seed[seed]["first_assignment_mismatch_frame_vs_frozen_base"]
        == by_seed[seed]["first_bounded_single_activation_frame"]
        for seed in FIRST_DIVERGENCE_SEEDS
    )
    e17_pre_activation_match = (
        by_seed["E17"]["first_assignment_mismatch_frame_vs_frozen_base"] is None
        or by_seed["E17"]["first_assignment_mismatch_frame_vs_frozen_base"]
        >= by_seed["E17"]["first_bounded_single_activation_frame"]
    )
    breadth = (
        positive_exercised
        and negative_controls
        and exact_first_divergence
        and e17_pre_activation_match
        and sum(item["exact_two_windows"] for item in audits) > 0
        and sum(item["parents_completed_heavy_bypass_players"] for item in audits) > 0
        and sum(item["low_route_windows"] for item in audits) > 0
        and sum(item["high_route_windows"] for item in audits) > 0
    )
    amendment = read_json(BLIND_AUDIT_AMENDMENT)
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_QUEUE8_CPU2_BOUNDED_TERMINAL_LOW_BLIND_AUDIT_V179_V1",
        "created_at": utc_now(),
        "status": "pass" if breadth else "failed_mechanism_falsification",
        "performance_reveal_authorized": breadth,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "result_blind_amendment_file_sha256": BLIND_AUDIT_AMENDMENT_SHA256,
        "result_blind_amendment_receipt_hash": amendment["receipt_hash"],
        "blind_audit_source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "run_count": len(SEEDS),
        "window_count": sum(item["windows"] for item in audits),
        "positive_mechanism_seeds_exercised": positive_exercised,
        "negative_controls_remain_frozen_exactly": negative_controls,
        "matched_controls_first_diverge_at_activation": exact_first_divergence,
        "e17_matches_until_first_activation": e17_pre_activation_match,
        "parents_completed_bypass_exercised": sum(
            item["parents_completed_heavy_bypass_players"] for item in audits
        )
        > 0,
        "short_work_and_both_routes_invariants_passed": True,
        "pass": breadth,
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
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
    if [row["seed"] for row in rows] != list(SEEDS):
        raise RuntimeError("V179 candidate result product changed")
    return rows


def _hybrid_rows(
    v170_rows: Sequence[Mapping[str, Any]],
    v176_rows: Sequence[Mapping[str, Any]],
    v179_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    expected = {f"E{index:02d}" for index in range(1, 21)}
    if len(v170_rows) != 20 or {row.get("seed") for row in v170_rows} != expected:
        raise RuntimeError("V170 candidate cohort changed")
    if {row.get("seed") for row in v176_rows} != set(v176.SEEDS):
        raise RuntimeError("V176 candidate cohort changed")
    if {row.get("seed") for row in v179_rows} != set(SEEDS):
        raise RuntimeError("V179 candidate cohort changed")
    if set(SEEDS) | set(V176_REUSE_SEEDS) | set(V170_REUSE_SEEDS) != expected:
        raise RuntimeError("V179 hybrid partition changed")
    replacements = {row["seed"]: dict(row) for row in v179_rows}
    frozen_v176 = {row["seed"]: dict(row) for row in v176_rows}
    replacements.update({seed: frozen_v176[seed] for seed in V176_REUSE_SEEDS})
    return [
        replacements.get(row["seed"], dict(row))
        for row in sorted(v170_rows, key=lambda item: item["seed"])
    ]


def reveal_v179(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V179 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V179 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("pass") is True
    ):
        raise RuntimeError("V179 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = _load_candidate(manifest, root)
    v170_rows = v175._load_v170_candidate()
    v176_manifest = load_and_validate_manifest(v176.paths()["ready"])
    v176_rows = v176._load_candidate(v176_manifest, v176.ROOT)
    hybrid = _hybrid_rows(v170_rows, v176_rows, candidate)
    evaluation = _evaluate_load("low", hybrid, _load_baselines())
    throughput_sum = sum(float(row["throughput"]) for row in candidate)
    qpr_values = [float(row["qpr_finite_only"]) for row in candidate]
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
        "throughput_selected_nine_sum": throughput_sum,
        "throughput_selected_nine_sum_pass": throughput_sum
        > SELECTED_THROUGHPUT_SUM_GATE,
        "throughput_selected_nine_paired_wins": throughput_wins,
        "throughput_selected_nine_paired_wins_pass": throughput_wins
        >= SELECTED_THROUGHPUT_WIN_GATE,
        "qpr_selected_nine_sum": sum(qpr_values),
        "qpr_selected_nine_sum_pass": sum(qpr_values) > SELECTED_QPR_SUM_GATE,
        "qpr_selected_nine_paired_wins": qpr_wins,
        "qpr_selected_nine_paired_wins_pass": qpr_wins >= SELECTED_QPR_WIN_GATE,
        "qpr_selected_nine_all_finite": all(math.isfinite(v) for v in qpr_values),
    }
    passed = evaluation["all_three_metric_gates_pass"] and all(
        value
        for key, value in diagnostic.items()
        if key.endswith("_pass") or key.endswith("_all_finite")
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CONCURRENT2_QUEUE8_CPU2_BOUNDED_TERMINAL_LOW_DIAGNOSTIC_RESULT_V179_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "new_candidate_run_count": len(SEEDS),
        "reused_v176_candidate_run_count": len(V176_REUSE_SEEDS),
        "reused_v170_candidate_run_count": len(V170_REUSE_SEEDS),
        "reused_frozen_baseline_run_count": 180,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "hybrid_low_evaluation": evaluation,
        "diagnostic_selected_nine_gates": diagnostic,
        "mechanism_gate": {"pass": blind["pass"]},
        "joint_diagnostic_pass": passed,
        "disposition": (
            "close_homogeneous_low_training_and_authorize_a_separately_committed_confirmation_plan"
            if passed
            else "retain_all_nine_valid_diagnostic_runs_and_retire_V179_without_unplanned_seed_execution"
        ),
        "homogeneous_low_claim_closed": passed,
        "confirmation_inputs_generated": False,
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
        document, key = prepare_v179(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v179(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v179(), "blind_audit_hash"
    else:
        document, key = reveal_v179(), "result_hash"
    print(json.dumps({key: document[key], "runs": len(SEEDS)}))


if __name__ == "__main__":
    main()
