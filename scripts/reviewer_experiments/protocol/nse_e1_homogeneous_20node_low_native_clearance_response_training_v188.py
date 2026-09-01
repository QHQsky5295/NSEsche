from __future__ import annotations

import argparse
import copy
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_disjoint_unpaired_confirmation_v184 as v184,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_response_time_ocs_training_v187 as v187,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.runner import ProtocolRunner
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
    "tmp/nse_e1_homogeneous_20node_low_native_clearance_response_training_20260901_v188"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_native_clearance_response_training_plan_v188.json"
)
PLAN_SHA256 = "ef13f5d401b01006f656579bfdb71ea21d8ea34f64d2888997f1d5b9641cdcda"
PLAN_HASH = "ae30bcf98b61c9c2650fd3fc6ba333e076a3e99c80622dfb3d6cfc61a2f41955"
PLAN_COMMIT = "ad42bae1ced05f5df1e39bb3ba82ffca517d9e81"
FAILURE_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_response_time_ocs_training_failure_v187.json"
)
FAILURE_RECEIPT_SHA256 = (
    "cc958cbe0c4eee9dfe17fa176b8e6a433f3224fdad7382a337e36616d6dfde3a"
)
FAILURE_RECEIPT_HASH = (
    "cdcad71243b52e4ae4413f6d3776cefa2d67cd9202e80d8e1701f3bff9a657a2"
)
IMPLEMENTATION_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_native_clearance_response_training_implementation_v188.json"
)
MODULE = Path(__file__)
TEST = Path(
    "scripts/reviewer_experiments/protocol/tests/"
    "test_nse_e1_low_native_clearance_response_training_v188.py"
)
GOAL = Path(
    "C:/Users/99349/.codex/attachments/"
    "517fc2e8-82e2-4104-a067-064a7ccd93b0/goal-objective.md"
)
GOAL_SHA256 = "323bd42ffd73299a8ea243d46c93410c8db8d33c07c0efbdd3edc6fe2efdcb0e"

SEEDS = tuple(f"E{index}" for index in range(1610, 1630))
CANDIDATE_PROFILE = (
    "nse_srpt_slack_concurrent2_queue8_cpu_bounded_terminal_short5p5_"
    "pipeline_native_clearance2_response1_queue8"
)
PORT = "3214"
BINARY_PATH = Path("serverless_sim/target_e1_v188/release/serverless_sim.exe")
BINARY_SHA256 = "1e5a4bbf34242c64df9ee4f5139d6cd584a57aa1180635401a18b57eb0cde7cb"
BINARY_BYTES = 5_916_160
BINARY_SOURCE_COMMIT = "ea369809b608c0a2955a7405f1157a5c7fe11344"
SCHEDULER_SOURCE = Path("serverless_sim/src/sche/sche_nash.rs")
SCHEDULER_SOURCE_SHA256 = (
    "9bf4d179d25f4f874ecc0adac2eccd0de40975b5f39561c1725f5f09ec4d61d1"
)
PYTHON_PATH = v184.PYTHON_PATH
PYTHON_SHA256 = v184.PYTHON_SHA256
CARGO_LOCK = v184.CARGO_LOCK
CARGO_LOCK_SHA256 = v184.CARGO_LOCK_SHA256
MODULE_CONF = v184.MODULE_CONF
MODULE_CONF_SEMANTIC_HASH = v184.MODULE_CONF_SEMANTIC_HASH
FROZEN_BASELINES = copy.deepcopy(v184.FROZEN_BASELINES)
METRICS = tuple(FROZEN_BASELINES)

V187_ROOT = v187.ROOT
V187_PATHS = v187.paths(V187_ROOT)
V187_RESULT = V187_PATHS["result"]
V187_RESULT_SHA256 = "5981fbc05a47718b0ba67744e7a0b6377f42e5e50c31811dd2f16670f08c3b04"
V187_RESULT_HASH = "232362007b7f3aa62fc3af0aa4b411f6e1fdf01668d8697d436673fb39907421"
V187_CONTROL_READY_SHA256 = (
    "3d2c8bca0c8a621cfe8184878b445cbc6acd1a10509728a911f8f74b8f0f2487"
)
V187_CANDIDATE_READY_SHA256 = (
    "994ef6f67b8495aad0016e41d3628ad50a7809f02735e02eb9f22085fc06f538"
)
V187_CONTROL_MANIFEST_HASH = (
    "916e9913b03f2310f887dbe00fbe74d6ae2fe6106a89e7bd049b2ad952061e5e"
)
V187_CANDIDATE_MANIFEST_HASH = (
    "46c495278856a89d85e2ec338d1b403259629e6d8c17b0cd1d85c3b8ab4f1112"
)


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "candidate_tapes": root / "manifest.candidate.tapes.json",
        "schedule": root / "schedule-v188.json",
        "prepared": root / "prepared-v188.json",
        "reference_workspace": root / "reference-candidate-stage",
        "reference_catalog": root / "references.candidate.catalog.json",
        "candidate_ready": root / "manifest.candidate.ready.json",
        "reference_execution": root / "reference-execution-receipt-v188.json",
        "candidate_workspace": root / "formal-runs-candidate",
        "execution": root / "execution-receipt-v188.json",
        "inventory": root / "inventory-audit-v188.json",
        "blind": root / "blind-audit-v188.json",
        "result": root / "training-result-v188.json",
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected: str, label: str) -> None:
    _require(path.is_file(), f"missing {label}: {path}")
    _require(file_hash(path) == expected, f"{label} hash changed: {path}")


def _assert_hashed(document: Mapping[str, Any], key: str, label: str) -> str:
    value = document.get(key)
    _require(isinstance(value, str) and len(value) == 64, f"{label} lacks {key}")
    payload = copy.deepcopy(dict(document))
    payload.pop(key, None)
    _require(object_hash(payload) == value, f"{label} self-hash changed")
    return value


def _reread_goal() -> None:
    _assert_file(GOAL, GOAL_SHA256, "goal objective")


def _assert_plan() -> dict[str, Any]:
    _assert_file(PLAN, PLAN_SHA256, "V188 plan")
    _assert_file(FAILURE_RECEIPT, FAILURE_RECEIPT_SHA256, "V187 failure receipt")
    plan = read_json(PLAN)
    failure = read_json(FAILURE_RECEIPT)
    _require(
        _assert_hashed(plan, "plan_hash", "V188 plan") == PLAN_HASH
        and plan.get("latest_goal_sha256") == GOAL_SHA256
        and plan.get("training_only") is True
        and plan.get("formal_results_eligible") is False
        and tuple(plan.get("cohort", {}).get("seed_order", [])) == SEEDS
        and plan.get("cohort", {}).get("new_candidate_runs") == 20
        and plan.get("cohort", {}).get("new_control_runs") == 0
        and plan.get("cohort", {}).get("new_base_tapes") == 0
        and plan.get("candidate", {}).get("profile") == CANDIDATE_PROFILE
        and plan.get("method_identity_boundary", {}).get(
            "external_baseline_expert_scores_allowed"
        )
        is False
        and plan.get("result_blind_execution", {}).get("all_valid_rows_retained")
        is True,
        "V188 plan boundary changed",
    )
    _require(
        _assert_hashed(failure, "receipt_hash", "V187 failure receipt")
        == FAILURE_RECEIPT_HASH
        and failure.get("status")
        == "complete_same_tape_training_failed_throughput_gates"
        and failure.get("technical_integrity", {}).get("all_valid_rows_retained")
        is True,
        "V187 failure evidence changed",
    )
    return plan


def _source_manifests() -> tuple[dict[str, Any], dict[str, Any]]:
    _assert_file(
        V187_PATHS["control_ready"],
        V187_CONTROL_READY_SHA256,
        "V187 control ready manifest",
    )
    _assert_file(
        V187_PATHS["candidate_ready"],
        V187_CANDIDATE_READY_SHA256,
        "V187 candidate ready manifest",
    )
    control = load_and_validate_manifest(V187_PATHS["control_ready"])
    candidate = load_and_validate_manifest(V187_PATHS["candidate_ready"])
    v187._validate_arm(control, "control", tapes_bound=True, references_bound=True)
    v187._validate_arm(candidate, "candidate", tapes_bound=True, references_bound=True)
    _require(
        control["manifest_hash"] == V187_CONTROL_MANIFEST_HASH
        and candidate["manifest_hash"] == V187_CANDIDATE_MANIFEST_HASH,
        "V187 source manifest hash changed",
    )
    return control, candidate


def _assert_frozen_inputs(*, require_implementation: bool) -> dict[str, Any]:
    plan = _assert_plan()
    _reread_goal()
    for path, expected, label in (
        (BINARY_PATH, BINARY_SHA256, "V188 binary"),
        (SCHEDULER_SOURCE, SCHEDULER_SOURCE_SHA256, "V188 scheduler source"),
        (PYTHON_PATH, PYTHON_SHA256, "Python executable"),
        (CARGO_LOCK, CARGO_LOCK_SHA256, "Cargo.lock"),
        (V187_RESULT, V187_RESULT_SHA256, "V187 result"),
    ):
        _assert_file(path, expected, label)
    _require(BINARY_PATH.stat().st_size == BINARY_BYTES, "V188 binary size changed")
    v184.v182.v181._assert_json_semantic(
        MODULE_CONF, MODULE_CONF_SEMANTIC_HASH, "module_conf_es.json"
    )
    result = read_json(V187_RESULT)
    _require(
        _assert_hashed(result, "result_hash", "V187 result") == V187_RESULT_HASH
        and result.get("status") == "training_fail"
        and result.get("valid_seed_deletion_replacement_relabeling_or_selective_rerun")
        is False,
        "V187 result boundary changed",
    )
    _source_manifests()
    if require_implementation:
        _require(
            IMPLEMENTATION_RECEIPT.is_file(), "V188 implementation receipt missing"
        )
        receipt = read_json(IMPLEMENTATION_RECEIPT)
        _assert_hashed(receipt, "receipt_hash", "V188 implementation receipt")
        _require(
            receipt.get("plan_sha256") == PLAN_SHA256
            and receipt.get("module_sha256") == file_hash(MODULE)
            and receipt.get("test_sha256") == file_hash(TEST)
            and receipt.get("runtime_binary_sha256") == BINARY_SHA256
            and receipt.get("scheduler_source_sha256") == SCHEDULER_SOURCE_SHA256
            and receipt.get("online_runs_before_seal") == 0,
            "V188 implementation receipt does not bind this harness",
        )
    return plan


def _build_tape_bound_manifest(protocol_commit: str) -> dict[str, Any]:
    control, source = _source_manifests()
    control_by_seed = {run["seed"]: run for run in control["runs"]}
    rewritten = copy.deepcopy(source)
    source_by_seed = {run["seed"]: run for run in rewritten["runs"]}
    _require(set(source_by_seed) == set(SEEDS), "V188 source product is not exact 20")
    rewritten["created_at"] = utc_now()
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    rewritten["runs"] = []
    lineage = []
    for seed in SEEDS:
        run = copy.deepcopy(source_by_seed[seed])
        source_run_id = run["run_id"]
        source_spec_hash = run["run_spec_hash"]
        control_run = control_by_seed[seed]
        _require(
            run["workload_tape"] == control_run["workload_tape"],
            f"V188 {seed} source arms do not share the frozen tape",
        )
        run["variant"] = "homogeneous-20node-low-v188-native-training"
        run["environment"].update(v184.v182.v181.COMMON_ENVIRONMENT)
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = CANDIDATE_PROFILE
        run["metadata"] = {
            "v188_training_only": True,
            "v188_plan_sha256": PLAN_SHA256,
            "v188_plan_hash": PLAN_HASH,
            "v188_plan_commit": PLAN_COMMIT,
            "v188_protocol_source_commit": protocol_commit,
            "v188_profile": CANDIDATE_PROFILE,
            "v188_player_frontier": v187.FRONTIER,
            "v188_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v188_binary_sha256": BINARY_SHA256,
            "v188_source_v187_candidate_run_id": source_run_id,
            "v188_source_v187_candidate_run_spec_hash": source_spec_hash,
            "v188_source_v187_control_run_id": control_run["run_id"],
            "v188_source_tape_reused": True,
            "v188_external_baseline_scores_allowed": False,
            "v188_new_base_tape_captures": 0,
            "v188_new_control_or_baseline_runs": 0,
            "v188_seed_deletion_replacement_or_selective_result_rerun": False,
        }
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
        _assign_run_identity(run)
        rewritten["runs"].append(run)
        lineage.append(
            {
                "seed": seed,
                "source_v187_candidate_run_id": source_run_id,
                "source_v187_control_run_id": control_run["run_id"],
                "source_tape_sha256": run["workload_tape"]["sha256"],
                "v188_run_id": run["run_id"],
                "v188_run_spec_hash": run["run_spec_hash"],
            }
        )
    marker = rewritten["integration_smoke_shard"]
    for key in tuple(marker):
        if key.startswith("v187_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": "V188 NSESche-native candidate on frozen V187 E1610-E1629 tapes",
            "v188_training_only": True,
            "v188_plan_sha256": PLAN_SHA256,
            "v188_plan_hash": PLAN_HASH,
            "v188_profile": CANDIDATE_PROFILE,
            "v188_source_to_candidate_lineage": lineage,
            "v188_expected_runs": 20,
            "v188_expected_references": 20,
            "v188_new_base_tapes": 0,
            "v188_new_control_or_baseline_runs": 0,
            "selected_run_count": 20,
            "selected_reference_build_count": 20,
        }
    )
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    rewritten["all_tapes_bound"] = True
    rewritten["all_references_bound"] = False
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    _validate_candidate(rewritten, references_bound=False)
    return rewritten


def _validate_candidate(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    runs = manifest.get("runs", [])
    _require(
        [(run.get("method"), run.get("seed")) for run in runs]
        == [("sche_nash", seed) for seed in SEEDS],
        "V188 exact ordered product changed",
    )
    _require(
        manifest.get("formal_results_eligible") is False
        and manifest.get("all_tapes_bound") is True
        and manifest.get("all_references_bound") is references_bound
        and len(manifest.get("reference_build_dependencies", [])) == 20,
        "V188 binding state changed",
    )
    for run in runs:
        reference = run.get("reference_dependency", {})
        _require(
            v187._selected(run)
            and run.get("variant") == "homogeneous-20node-low-v188-native-training"
            and run.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == CANDIDATE_PROFILE
            and run.get("environment", {}).get("SERVERLESS_SIM_PORT") == PORT
            and run.get("metadata", {}).get("v188_external_baseline_scores_allowed")
            is False
            and run.get("metadata", {}).get("v188_new_control_or_baseline_runs") == 0
            and bool(run.get("workload_tape", {}).get("sha256"))
            and bool(reference.get("sha256")) is references_bound
            and bool(reference.get("build_required")) is (not references_bound),
            f"V188 run contract changed: {run.get('run_id')}",
        )


def prepare_v188(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs(require_implementation=True)
    _require(not root.exists(), f"refusing to overwrite V188 root: {root}")
    root.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    manifest = _build_tape_bound_manifest(commit)
    output = paths(root)
    write_json_atomic(output["candidate_tapes"], manifest)
    schedule = {
        "schema_version": "NSE_E1_LOW_NATIVE_SERVICE_SCHEDULE_V188_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "reference_order": list(SEEDS),
        "online_order": list(SEEDS),
        "new_base_tape_captures": 0,
        "new_control_or_baseline_runs": 0,
        "performance_fields_parsed": 0,
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_LOW_NATIVE_SERVICE_PREPARED_V188_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_fields_parsed": 0,
        "goal_sha256": GOAL_SHA256,
        "plan_sha256": PLAN_SHA256,
        "plan_hash": PLAN_HASH,
        "protocol_source_commit": commit,
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "source_v187_control_manifest_sha256": V187_CONTROL_READY_SHA256,
        "source_v187_candidate_manifest_sha256": V187_CANDIDATE_READY_SHA256,
        "candidate_tape_bound_manifest_hash": manifest["manifest_hash"],
        "candidate_tape_bound_manifest_sha256": file_hash(output["candidate_tapes"]),
        "schedule_hash": schedule["schedule_hash"],
        "new_base_tapes": 0,
        "reference_builds_planned": 20,
        "candidate_online_runs_planned": 20,
        "control_or_baseline_online_runs_planned": 0,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def _run_logged(command: Sequence[str], stdout: Path, stderr: Path, label: str) -> None:
    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open("w", encoding="utf-8") as out, stderr.open(
        "w", encoding="utf-8"
    ) as err:
        completed = subprocess.run(command, stdout=out, stderr=err, check=False)
    _require(completed.returncode == 0, f"{label} failed: exit={completed.returncode}")


def build_references_v188(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs(require_implementation=True)
    output = paths(root)
    manifest = load_and_validate_manifest(output["candidate_tapes"])
    _validate_candidate(manifest, references_bound=False)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    logs = root / "reference-execution-logs"
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        _reread_goal()
        stdout = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{seed}.stderr.log"
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "build-references",
                str(output["candidate_tapes"]),
                str(output["reference_workspace"]),
                str(output["reference_catalog"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V188 reference {seed}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    _run_logged(
        [
            str(PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "bind-references",
            str(output["candidate_tapes"]),
            str(output["reference_catalog"]),
            str(output["candidate_ready"]),
        ],
        logs / "bind.stdout.log",
        logs / "bind.stderr.log",
        "V188 reference binding",
    )
    ready = load_and_validate_manifest(output["candidate_ready"])
    _validate_candidate(ready, references_bound=True)
    catalog = read_json(output["reference_catalog"])
    _require(len(catalog.get("entries", {})) == 20, "V188 reference catalog is not 20")
    count, last_hash = verify_ledger(
        output["reference_workspace"] / "reference_builds" / "ledger.jsonl"
    )
    receipt = {
        "schema_version": "NSE_E1_LOW_NATIVE_SERVICE_REFERENCES_V188_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_reference": True,
        "performance_fields_parsed": 0,
        "dispatches": dispatches,
        "catalog_entry_count": 20,
        "catalog_file_sha256": file_hash(output["reference_catalog"]),
        "reference_ledger_events": count,
        "reference_ledger_last_hash": last_hash,
        "ready_manifest_hash": ready["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["candidate_ready"]),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["reference_execution"], receipt)
    return receipt


def execute_v188(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs(require_implementation=True)
    output = paths(root)
    manifest = load_and_validate_manifest(output["candidate_ready"])
    _validate_candidate(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    logs = root / "execution-logs"
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        _reread_goal()
        stdout = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{seed}.stderr.log"
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "run",
                str(output["candidate_ready"]),
                str(output["candidate_workspace"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V188 online {seed}",
        )
        canonical = output["candidate_workspace"] / "canonical" / run["run_id"]
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        _require(
            attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V188 run is not canonical QC pass: {run['run_id']}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "canonical_attempt": attempt["attempt"],
                "attempt_sha256": file_hash(canonical / "attempt.json"),
                "qc_sha256": file_hash(canonical / "qc_report.json"),
                "audit_sha256": file_hash(canonical / "manifest.json"),
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_LOW_NATIVE_SERVICE_EXECUTION_V188_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_online_dispatch": True,
        "performance_fields_parsed": 0,
        "candidate_online_runs": 20,
        "control_or_baseline_online_runs": 0,
        "plan_sha256": PLAN_SHA256,
        "fixed_seed_order": list(SEEDS),
        "dispatches": dispatches,
        "ready_manifest_hash": manifest["manifest_hash"],
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _runtime_identity(
    audits: Sequence[Mapping[str, Any]], expected_commit: str
) -> dict[str, Any]:
    identities = {
        (
            item.get("adapter_binary", {}).get("verified_sha256"),
            item.get("software_environment", {}).get("git", {}).get("commit"),
            item.get("software_environment", {})
            .get("python", {})
            .get("executable_sha256"),
            item.get("software_environment", {}).get("cargo_lock", {}).get("sha256"),
        )
        for item in audits
    }
    _require(len(identities) == 1, "V188 runtime identity is not unanimous")
    binary, git_commit, python_sha, cargo_sha = next(iter(identities))
    _require(
        binary == BINARY_SHA256
        and git_commit == expected_commit
        and python_sha == PYTHON_SHA256
        and cargo_sha == CARGO_LOCK_SHA256,
        "V188 runtime identity changed",
    )
    return {
        "runtime_binary_sha256": binary,
        "runtime_git_commit": git_commit,
        "runtime_python_executable_sha256": python_sha,
        "runtime_cargo_lock_sha256": cargo_sha,
    }


def blind_audit_v188(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs(require_implementation=True)
    output = paths(root)
    _require(not output["blind"].exists(), "V188 blind audit already exists")
    _require(not output["result"].exists(), "V188 result exists before blind audit")
    prepared = read_json(output["prepared"])
    references = read_json(output["reference_execution"])
    execution = read_json(output["execution"])
    receipt_hashes = {
        "prepared": _assert_hashed(prepared, "receipt_hash", "V188 prepared"),
        "references": _assert_hashed(references, "receipt_hash", "V188 references"),
        "execution": _assert_hashed(execution, "receipt_hash", "V188 execution"),
    }
    _require(
        [item["seed"] for item in execution.get("dispatches", [])] == list(SEEDS)
        and execution.get("candidate_online_runs") == 20
        and execution.get("control_or_baseline_online_runs") == 0
        and prepared.get("performance_fields_parsed") == 0
        and references.get("performance_fields_parsed") == 0
        and execution.get("performance_fields_parsed") == 0,
        "V188 result-blind receipts changed",
    )
    manifest = load_and_validate_manifest(output["candidate_ready"])
    _validate_candidate(manifest, references_bound=True)
    canonical_root = output["candidate_workspace"] / "canonical"
    expected_ids = {run["run_id"] for run in manifest["runs"]}
    actual_ids = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual_ids == expected_ids, "V188 canonical set changed")
    audits = []
    run_evidence = []
    candidate_by_seed = {run["seed"]: run for run in manifest["runs"]}
    runner = ProtocolRunner(output["candidate_ready"], output["candidate_workspace"])
    for run in manifest["runs"]:
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        runner._validate_existing_canonical(run, canonical)
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        audit = read_json(canonical / "manifest.json")
        _require(
            attempt.get("classification") == "qc_pass"
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V188 non-clean canonical: {run['run_id']}",
        )
        audits.append(audit)
        run_evidence.append(
            {
                "seed": run["seed"],
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "tape_sha256": run["workload_tape"]["sha256"],
                "reference_sha256": run["reference_dependency"]["sha256"],
                "result_sha256": attempt["result_sha256"],
                "canonical_attempt": attempt["attempt"],
                "attempt_sha256": file_hash(canonical / "attempt.json"),
                "qc_sha256": file_hash(canonical / "qc_report.json"),
                "audit_sha256": file_hash(canonical / "manifest.json"),
            }
        )
    control, _ = _source_manifests()
    control_root = V187_PATHS["control_workspace"] / "canonical"
    control_runner = ProtocolRunner(
        V187_PATHS["control_ready"], V187_PATHS["control_workspace"]
    )
    control_evidence = []
    for run in control["runs"]:
        canonical = control_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=control["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        control_runner._validate_existing_canonical(run, canonical)
        attempt = read_json(canonical / "attempt.json")
        _require(
            candidate_by_seed[run["seed"]]["workload_tape"] == run["workload_tape"],
            f"V188 {run['seed']} candidate/control tape mismatch",
        )
        control_evidence.append(
            {
                "seed": run["seed"],
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "tape_sha256": run["workload_tape"]["sha256"],
                "result_sha256": attempt["result_sha256"],
                "attempt_sha256": file_hash(canonical / "attempt.json"),
                "qc_sha256": file_hash(canonical / "qc_report.json"),
                "audit_sha256": file_hash(canonical / "manifest.json"),
            }
        )
    quarantine_root = output["candidate_workspace"] / "quarantine"
    quarantine_attempts = []
    if quarantine_root.exists():
        for attempt_path in sorted(quarantine_root.rglob("attempt.json")):
            attempt = read_json(attempt_path)
            _require(
                attempt.get("classification") != "qc_pass",
                f"V188 QC-pass attempt incorrectly quarantined: {attempt_path}",
            )
            quarantine_attempts.append(
                {
                    "path": str(attempt_path),
                    "classification": attempt.get("classification"),
                    "file_sha256": file_hash(attempt_path),
                }
            )
    ledger_count, ledger_last_hash = verify_ledger(
        output["candidate_workspace"] / "ledger.jsonl"
    )
    reference_count, reference_last_hash = verify_ledger(
        output["reference_workspace"] / "reference_builds" / "ledger.jsonl"
    )
    inventory = {
        "schema_version": "NSE_E1_LOW_NATIVE_SERVICE_INVENTORY_V188_V1",
        "created_at": utc_now(),
        "status": "pass",
        "seeds": list(SEEDS),
        "candidate_run_count": 20,
        "control_or_baseline_online_run_count": 0,
        "new_base_tape_count": 0,
        "metrics_consulted": False,
        "run_ids": [item["run_id"] for item in run_evidence],
    }
    inventory["inventory_hash"] = object_hash(inventory)
    write_json_atomic(output["inventory"], inventory)
    document = {
        "schema_version": "NSE_E1_LOW_NATIVE_SERVICE_BLIND_AUDIT_V188_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "training_only": True,
        "formal_results_eligible": False,
        "metrics_consulted": False,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "seeds": list(SEEDS),
        "observed_new_base_tapes": 0,
        "observed_references": 20,
        "observed_candidate_online_runs": 20,
        "observed_control_or_baseline_online_runs": 0,
        "canonical_qc_passes": 20,
        "technical_quarantine_attempts": quarantine_attempts,
        "exact_same_tape_frozen_control_cohort": True,
        "receipt_hashes": receipt_hashes,
        "runtime_identity": _runtime_identity(
            audits, prepared["protocol_source_commit"]
        ),
        "ready_manifest": {
            "path": str(output["candidate_ready"].resolve()),
            "file_sha256": file_hash(output["candidate_ready"]),
            "manifest_hash": manifest["manifest_hash"],
        },
        "inventory": {
            "path": str(output["inventory"].resolve()),
            "file_sha256": file_hash(output["inventory"]),
            "inventory_hash": inventory["inventory_hash"],
        },
        "ledgers": {
            "runs": {"events": ledger_count, "last_hash": ledger_last_hash},
            "references": {
                "events": reference_count,
                "last_hash": reference_last_hash,
            },
        },
        "candidate_run_evidence": run_evidence,
        "frozen_v187_control_evidence": control_evidence,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _finite(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _evaluate_training(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evaluation = v187._evaluate_training(rows)
    _require(
        all(_finite(row.get(metric)) for row in rows for metric in METRICS),
        "V188 training rows contain nonfinite values",
    )
    return evaluation


def reveal_v188(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    _require(not output["result"].exists(), "V188 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V188 blind audit")
    _require(
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("metrics_consulted") is False
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("observed_candidate_online_runs") == 20
        and blind.get("observed_control_or_baseline_online_runs") == 0
        and blind.get("canonical_qc_passes") == 20,
        "V188 blind audit does not authorize reveal",
    )
    _reread_goal()
    candidate = load_and_validate_manifest(output["candidate_ready"])
    _validate_candidate(candidate, references_bound=True)
    control, _ = _source_manifests()
    rows = []
    for arm, manifest, workspace in (
        ("candidate", candidate, output["candidate_workspace"]),
        ("control", control, V187_PATHS["control_workspace"]),
    ):
        for run in manifest["runs"]:
            summary_path = (
                workspace
                / "canonical"
                / run["run_id"]
                / "reviewer_records"
                / run["run_id"]
                / "summary.json"
            )
            summary = read_json(summary_path)
            _require(summary.get("run_complete") is True, f"incomplete {run['run_id']}")
            rows.append(
                {
                    "arm": arm,
                    "method": "sche_nash",
                    "seed": run["seed"],
                    "run_id": run["run_id"],
                    **v184._summary_metrics(summary),
                    "summary_path": str(summary_path),
                    "summary_file_sha256": file_hash(summary_path),
                }
            )
    evaluation = _evaluate_training(rows)
    passed = evaluation["all_six_preregistered_performance_requirements_pass"]
    document = {
        "schema_version": "NSE_E1_LOW_NATIVE_SERVICE_TRAINING_RESULT_V188_V1",
        "created_at": utc_now(),
        "status": "training_pass" if passed else "training_fail",
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "homogeneous_20node_low_closed": False,
        "middle_load_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "plan_hash": PLAN_HASH,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "seeds": list(SEEDS),
        "same_tape_frozen_v187_control_training": True,
        "candidate_online_runs": 20,
        "control_or_baseline_online_runs": 0,
        "complete_training_rows": rows,
        "evaluation": evaluation,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
        "decision": (
            "freeze_V188_training_winner_and_preregister_disjoint_low_confirmation"
            if passed
            else "retain_complete_V188_failure_close_axis_and_do_not_advance_to_middle"
        ),
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("prepare", "build-references", "execute", "blind-audit", "reveal"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    functions = {
        "prepare": prepare_v188,
        "build-references": build_references_v188,
        "execute": execute_v188,
        "blind-audit": blind_audit_v188,
        "reveal": reveal_v188,
    }
    document = functions[action]()
    key = next(
        key
        for key in ("receipt_hash", "blind_audit_hash", "result_hash")
        if key in document
    )
    print(json.dumps({"action": action, key: document[key]}, indent=2))


if __name__ == "__main__":
    main()
