from __future__ import annotations

import argparse
import copy
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.stats import bca_interval
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_disjoint_unpaired_confirmation_v184 as v184,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
    write_manifest,
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
    "tmp/nse_e1_homogeneous_20node_low_relative_load_ocs_training_20260901_v185"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_relative_load_ocs_training_plan_v185.json"
)
PLAN_SHA256 = "e9a1ea38696e60c91129c659cb8b680023eb72d34a871176f4140516b32c5305"
PLAN_HASH = "0eb20ba8915a73bb3d3d53009cb358034cfcb49222ed1d602270e8477e772873"
PLAN_COMMIT = "a4873ec2bdacf873e90003e53fbb9c61803f2057"
IMPLEMENTATION_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_relative_load_ocs_training_implementation_v185.json"
)
GOAL = v184.GOAL
GOAL_SHA256 = v184.GOAL_SHA256
MODULE = Path(__file__)
TEST = Path(
    "scripts/reviewer_experiments/protocol/tests/"
    "test_nse_e1_low_relative_load_ocs_training_v185.py"
)

SOURCE_ROOT = v184.ROOT
SOURCE_READY = SOURCE_ROOT / "manifest.confirmation.ready.json"
SOURCE_READY_SHA256 = "83b00060feeef9b991548e2c6a0a93b9f0f533f3eab40a5345a9ca3b1d06baeb"
SOURCE_TAPE_CATALOG = SOURCE_ROOT / "tapes.catalog.json"
SOURCE_TAPE_CATALOG_SHA256 = (
    "f24f717e5be3e69e0c0636fbd56d0be8e7bf10ee2ba25ccc3588deec8ba53ac3"
)
SOURCE_BLIND = SOURCE_ROOT / "joint-blind-audit-v184.json"
SOURCE_BLIND_SHA256 = "b8656eaa6e9c51046a29ac1e5ea8633d984ad4f463a8acc1ff9babf1e5fd13cc"
SOURCE_RESULT = SOURCE_ROOT / "confirmation-result-v184.json"
SOURCE_RESULT_SHA256 = (
    "f2c94ec84320b5e651de6bc07d051934cebdb39202989734c9faaaae013142d6"
)
SOURCE_RESULT_HASH = "8d66580e81f4bcd14290e1e1d03149c19493deec1592d31fe0ff4dd914fd3202"

SEEDS = tuple(f"E{index}" for index in range(1590, 1610))
PROFILE = (
    "srpt_slack_concurrent2_queue8_cpu_bounded_terminal_short5p5_"
    "pipeline_hiku2_ocs_relative_queue8"
)
FRONTIER = v184.FRONTIER
PORT = "3212"
BINARY_PATH = Path("serverless_sim/target_e1_v185/release/serverless_sim.exe")
BINARY_SHA256 = "c82c5e2533413f563a88553c41296907b2eb4b38e025757c8f3c45c670ee7e48"
BINARY_BYTES = 5_906_432
BINARY_SOURCE_COMMIT = "6983186070b65d483cf96294ec6884e212e53a53"
SCHEDULER_SOURCE = Path("serverless_sim/src/sche/sche_nash.rs")
SCHEDULER_SOURCE_SHA256 = (
    "769140106eded4faef6da86c4f396ace7d7735154f3a4ea90b1f779608725252"
)
PYTHON_PATH = v184.PYTHON_PATH
PYTHON_SHA256 = v184.PYTHON_SHA256
CARGO_LOCK = v184.CARGO_LOCK
CARGO_LOCK_SHA256 = v184.CARGO_LOCK_SHA256
MODULE_CONF = v184.MODULE_CONF
MODULE_CONF_SEMANTIC_HASH = v184.MODULE_CONF_SEMANTIC_HASH

FROZEN_BASELINES = copy.deepcopy(v184.FROZEN_BASELINES)
METRICS = tuple(FROZEN_BASELINES)


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "tapes": root / "manifest.training.tapes.json",
        "prepared": root / "prepared-v185.json",
        "reference_workspace": root / "reference-stage",
        "reference_catalog": root / "references.catalog.json",
        "ready": root / "manifest.training.ready.json",
        "reference_execution": root / "reference-execution-receipt-v185.json",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v185.json",
        "inventory": root / "candidate-inventory-audit-v185.json",
        "blind": root / "joint-blind-audit-v185.json",
        "result": root / "training-result-v185.json",
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


def _assert_source_evidence() -> tuple[dict[str, Any], dict[str, Any]]:
    for path, expected, label in (
        (PLAN, PLAN_SHA256, "V185 plan"),
        (GOAL, GOAL_SHA256, "goal objective"),
        (SOURCE_READY, SOURCE_READY_SHA256, "V184 ready manifest"),
        (SOURCE_TAPE_CATALOG, SOURCE_TAPE_CATALOG_SHA256, "V184 tape catalog"),
        (SOURCE_BLIND, SOURCE_BLIND_SHA256, "V184 blind audit"),
        (SOURCE_RESULT, SOURCE_RESULT_SHA256, "V184 result"),
        (BINARY_PATH, BINARY_SHA256, "V185 binary"),
        (SCHEDULER_SOURCE, SCHEDULER_SOURCE_SHA256, "V185 scheduler source"),
        (PYTHON_PATH, PYTHON_SHA256, "Python executable"),
        (CARGO_LOCK, CARGO_LOCK_SHA256, "Cargo.lock"),
    ):
        _assert_file(path, expected, label)
    _require(BINARY_PATH.stat().st_size == BINARY_BYTES, "V185 binary size changed")
    v184.v182.v181._assert_json_semantic(
        MODULE_CONF, MODULE_CONF_SEMANTIC_HASH, "module_conf_es.json"
    )
    plan = read_json(PLAN)
    _require(
        _assert_hashed(plan, "plan_hash", "V185 plan") == PLAN_HASH
        and plan.get("training_only") is True
        and plan.get("candidate", {}).get("profile") == PROFILE
        and tuple(plan.get("candidate", {}).get("seed_order", [])) == SEEDS
        and plan.get("candidate", {}).get("baseline_online_runs") == 0,
        "V185 plan boundary changed",
    )
    result = read_json(SOURCE_RESULT)
    _require(
        _assert_hashed(result, "result_hash", "V184 result") == SOURCE_RESULT_HASH
        and result.get("status") == "confirmation_fail"
        and tuple(result.get("confirmation_seeds", [])) == SEEDS
        and len(result.get("complete_confirmation_rows", [])) == 20
        and result.get("valid_seed_deletion_replacement_relabeling_or_selective_rerun")
        is False,
        "V184 complete control cohort changed",
    )
    return plan, result


def _assert_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    plan, result = _assert_source_evidence()
    _require(IMPLEMENTATION_RECEIPT.is_file(), "V185 implementation receipt missing")
    implementation = read_json(IMPLEMENTATION_RECEIPT)
    _assert_hashed(implementation, "receipt_hash", "V185 implementation receipt")
    _require(
        implementation.get("plan_sha256") == PLAN_SHA256
        and implementation.get("module_sha256") == file_hash(MODULE)
        and implementation.get("test_sha256") == file_hash(TEST)
        and implementation.get("runtime_binary_sha256") == BINARY_SHA256
        and implementation.get("candidate_online_runs_before_seal") == 0,
        "V185 implementation receipt does not bind this harness",
    )
    return plan, result


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    runs = manifest.get("runs", [])
    _require(
        [(run.get("method"), run.get("seed")) for run in runs]
        == [("sche_nash", seed) for seed in SEEDS],
        "V185 exact ordered 20-run product changed",
    )
    _require(
        manifest.get("all_tapes_bound") is True
        and manifest.get("all_references_bound") is references_bound,
        "V185 binding state changed",
    )
    _require(
        len(manifest.get("reference_build_dependencies", [])) == 20,
        "V185 requires exactly 20 offline references",
    )
    tape_hashes = set()
    for run in runs:
        tape = run.get("workload_tape", {})
        _require(
            run.get("variant") == "homogeneous-20node-low-v185-relative-load-training"
            and run.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == PROFILE
            and run.get("environment", {}).get("SERVERLESS_SIM_PORT") == PORT
            and run.get("metadata", {}).get("v185_training_only") is True
            and run.get("metadata", {}).get("v185_baseline_online_runs") == 0
            and tape.get("runtime_mode") == "replay"
            and isinstance(tape.get("event_count"), int)
            and tape.get("event_count", 0) > 0
            and tape.get("sha256"),
            f"V185 run contract changed: {run.get('run_id')}",
        )
        tape_hashes.add(tape["sha256"])
        reference = run.get("reference_dependency", {})
        _require(
            bool(reference.get("sha256")) is references_bound
            and bool(reference.get("build_required")) is (not references_bound),
            f"V185 reference binding changed: {run.get('run_id')}",
        )
    _require(len(tape_hashes) == 20, "V185 must reuse 20 distinct V184 tapes")


def _rewrite_training(source: Mapping[str, Any]) -> dict[str, Any]:
    rewritten = copy.deepcopy(dict(source))
    source_runs = {
        run["seed"]: run
        for run in source.get("runs", [])
        if run.get("method") == "sche_nash" and run.get("seed") in SEEDS
    }
    _require(set(source_runs) == set(SEEDS), "V184 source Nash product changed")
    rewritten["created_at"] = utc_now()
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    rewritten["runs"] = []
    lineage = []
    for seed in SEEDS:
        source_run = source_runs[seed]
        run = copy.deepcopy(source_run)
        source_run_id = run["run_id"]
        source_spec_hash = run["run_spec_hash"]
        run["variant"] = "homogeneous-20node-low-v185-relative-load-training"
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"].update(v184.v182.v181.COMMON_ENVIRONMENT)
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        metadata = {
            key: value
            for key, value in run.get("metadata", {}).items()
            if not key.startswith("v184_")
        }
        metadata.update(
            {
                "v185_training_only": True,
                "v185_plan_sha256": PLAN_SHA256,
                "v185_plan_commit": PLAN_COMMIT,
                "v185_profile": PROFILE,
                "v185_player_frontier": FRONTIER,
                "v185_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v185_binary_sha256": BINARY_SHA256,
                "v185_source_v184_run_id": source_run_id,
                "v185_source_v184_run_spec_hash": source_spec_hash,
                "v185_source_v184_result_hash": SOURCE_RESULT_HASH,
                "v185_same_tape_control": True,
                "v185_baseline_online_runs": 0,
                "v185_performance_fields_parsed_before_run": 0,
                "v185_seed_deletion_replacement_or_selective_rerun": False,
            }
        )
        run["metadata"] = metadata
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
                "source_v184_run_id": source_run_id,
                "source_v184_run_spec_hash": source_spec_hash,
                "v185_run_id": run["run_id"],
                "v185_run_spec_hash": run["run_spec_hash"],
                "tape_sha256": run["workload_tape"]["sha256"],
            }
        )
    old_marker = rewritten["integration_smoke_shard"]
    marker = {
        key: value for key, value in old_marker.items() if not key.startswith("v184_")
    }
    marker["purpose"] = (
        "V185 same-tape mechanism training against the complete frozen V184 control; "
        "never independent confirmation"
    )
    marker["selected_source_runs"] = [
        item
        for item in old_marker["selected_source_runs"]
        if item.get("source_method") == "sche_nash" and item.get("source_seed") in SEEDS
    ]
    marker.update(
        {
            "v185_training_only": True,
            "v185_plan_sha256": PLAN_SHA256,
            "v185_selected_seeds": list(SEEDS),
            "v185_fixed_run_order": [
                {"method": "sche_nash", "seed": seed} for seed in SEEDS
            ],
            "v185_source_to_training_lineage": lineage,
            "v185_expected_reused_base_tapes": 20,
            "v185_expected_references": 20,
            "v185_expected_online_runs": 20,
            "v185_expected_baseline_online_runs": 0,
            "selected_run_count": 20,
            "selected_reference_build_count": 20,
            "formal_results_eligible": False,
            "paper_superiority_claim_eligible_if_joint_gate_passes": False,
        }
    )
    rewritten["integration_smoke_shard"] = marker
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
    _validate_product(rewritten, references_bound=False)
    return rewritten


def prepare_v185(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    _require(not root.exists(), "V185 root already exists")
    source = load_and_validate_manifest(SOURCE_READY)
    manifest = _rewrite_training(source)
    source_by_seed = {
        run["seed"]: run for run in source["runs"] if run["method"] == "sche_nash"
    }
    tape_evidence = []
    for run in manifest["runs"]:
        source_run = source_by_seed[run["seed"]]
        tape = run["workload_tape"]
        _require(
            tape == source_run["workload_tape"],
            f"V185 tape binding differs from V184: {run['seed']}",
        )
        tape_path = Path(tape["path"])
        _assert_file(tape_path, tape["sha256"], f"V184 tape {run['seed']}")
        tape_evidence.append(
            {
                "seed": run["seed"],
                "path": str(tape_path),
                "sha256": tape["sha256"],
                "bytes": tape_path.stat().st_size,
            }
        )
    root.mkdir(parents=True)
    output = paths(root)
    write_manifest(output["tapes"], manifest)
    receipt = {
        "schema_version": "NSE_E1_LOW_RELATIVE_LOAD_OCS_PREPARED_V185_V1",
        "created_at": utc_now(),
        "training_only": True,
        "performance_fields_parsed": 0,
        "baseline_online_runs": 0,
        "plan_sha256": PLAN_SHA256,
        "source_v184_ready_sha256": SOURCE_READY_SHA256,
        "source_v184_result_hash": SOURCE_RESULT_HASH,
        "source_v184_tape_catalog_sha256": SOURCE_TAPE_CATALOG_SHA256,
        "runtime_binary_sha256": BINARY_SHA256,
        "runtime_binary_source_commit": BINARY_SOURCE_COMMIT,
        "manifest_hash": manifest["manifest_hash"],
        "manifest_file_sha256": file_hash(output["tapes"]),
        "reused_tape_count": len(tape_evidence),
        "new_tape_captures": 0,
        "reference_builds_planned": 20,
        "candidate_online_runs_planned": 20,
        "tape_evidence": tape_evidence,
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


def build_references_v185(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifest = load_and_validate_manifest(output["tapes"])
    _validate_product(manifest, references_bound=False)
    logs = root / "reference-execution-logs"
    dispatches = []
    for ordinal, run in enumerate(manifest["runs"], start=1):
        _reread_goal()
        stdout = logs / f"{ordinal:02d}-{run['seed']}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{run['seed']}.stderr.log"
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "build-references",
                str(output["tapes"]),
                str(output["reference_workspace"]),
                str(output["reference_catalog"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V185 reference {run['seed']}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": run["seed"],
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
            str(output["tapes"]),
            str(output["reference_catalog"]),
            str(output["ready"]),
        ],
        logs / "bind.stdout.log",
        logs / "bind.stderr.log",
        "V185 reference binding",
    )
    ready = load_and_validate_manifest(output["ready"])
    _validate_product(ready, references_bound=True)
    catalog = read_json(output["reference_catalog"])
    _require(len(catalog.get("entries", {})) == 20, "V185 reference catalog is not 20")
    count, last_hash = verify_ledger(
        output["reference_workspace"] / "reference_builds" / "ledger.jsonl"
    )
    receipt = {
        "schema_version": "NSE_E1_LOW_RELATIVE_LOAD_OCS_REFERENCES_V185_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_reference": True,
        "performance_fields_parsed": 0,
        "dispatches": dispatches,
        "catalog_file_sha256": file_hash(output["reference_catalog"]),
        "catalog_entry_count": 20,
        "ledger_event_count": count,
        "ledger_last_hash": last_hash,
        "ready_manifest_hash": ready["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["reference_execution"], receipt)
    return receipt


def execute_v185(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    logs = root / "execution-logs"
    dispatches = []
    for ordinal, run in enumerate(manifest["runs"], start=1):
        _reread_goal()
        stdout = logs / f"{ordinal:02d}-{run['seed']}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{run['seed']}.stderr.log"
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "run",
                str(output["ready"]),
                str(output["workspace"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V185 online {run['seed']}",
        )
        canonical = output["workspace"] / "canonical" / run["run_id"]
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        _require(
            attempt.get("attempt") == 1
            and attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V185 run is not attempt-one QC pass: {run['run_id']}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": run["seed"],
                "run_id": run["run_id"],
                "attempt_sha256": file_hash(canonical / "attempt.json"),
                "qc_sha256": file_hash(canonical / "qc_report.json"),
                "audit_sha256": file_hash(canonical / "manifest.json"),
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_LOW_RELATIVE_LOAD_OCS_EXECUTION_V185_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_online_dispatch": True,
        "performance_fields_parsed": 0,
        "baseline_online_runs": 0,
        "plan_sha256": PLAN_SHA256,
        "fixed_order": [{"method": "sche_nash", "seed": seed} for seed in SEEDS],
        "dispatches": dispatches,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def blind_audit_v185(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    _require(not output["blind"].exists(), "V185 blind audit already exists")
    _require(not output["result"].exists(), "V185 result exists before blind audit")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    prepared = read_json(output["prepared"])
    reference_execution = read_json(output["reference_execution"])
    execution = read_json(output["execution"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V185 prepared receipt")
    reference_hash = _assert_hashed(
        reference_execution, "receipt_hash", "V185 reference receipt"
    )
    execution_hash = _assert_hashed(execution, "receipt_hash", "V185 execution receipt")
    _require(
        [item["seed"] for item in reference_execution["dispatches"]] == list(SEEDS)
        and [item["seed"] for item in execution["dispatches"]] == list(SEEDS)
        and execution.get("baseline_online_runs") == 0
        and prepared.get("new_tape_captures") == 0
        and prepared.get("reused_tape_count") == 20
        and prepared.get("performance_fields_parsed") == 0
        and reference_execution.get("performance_fields_parsed") == 0
        and execution.get("performance_fields_parsed") == 0,
        "V185 result-blind execution receipts changed",
    )
    canonical_root = output["workspace"] / "canonical"
    expected_ids = {run["run_id"] for run in manifest["runs"]}
    actual_ids = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual_ids == expected_ids, "V185 canonical set changed")
    quarantine = output["workspace"] / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.rglob("attempt-*")),
        "V185 quarantine is not empty",
    )
    runner = ProtocolRunner(output["ready"], output["workspace"])
    audits = []
    run_evidence = []
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
            attempt.get("attempt") == 1
            and attempt.get("classification") == "qc_pass"
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V185 non-clean canonical: {run['run_id']}",
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
                "attempt_sha256": file_hash(canonical / "attempt.json"),
                "qc_sha256": file_hash(canonical / "qc_report.json"),
                "audit_sha256": file_hash(canonical / "manifest.json"),
            }
        )
    run_count, run_last_hash = v184._assert_clean_ledger(
        output["workspace"] / "ledger.jsonl", expected_ids
    )
    reference_count, reference_last_hash = verify_ledger(
        output["reference_workspace"] / "reference_builds" / "ledger.jsonl"
    )
    inventory = {
        "schema_version": "NSE_E1_LOW_RELATIVE_LOAD_OCS_INVENTORY_V185_V1",
        "created_at": utc_now(),
        "status": "pass",
        "method": "sche_nash",
        "seeds": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
        "run_count": 20,
        "baseline_online_runs": 0,
        "metrics_consulted": False,
    }
    inventory["inventory_hash"] = object_hash(inventory)
    write_json_atomic(output["inventory"], inventory)
    document = {
        "schema_version": "NSE_E1_LOW_RELATIVE_LOAD_OCS_BLIND_AUDIT_V185_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "formal_results_eligible": False,
        "training_only": True,
        "metrics_consulted": False,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "seeds": list(SEEDS),
        "observed_reused_base_tapes": 20,
        "observed_new_tape_captures": 0,
        "observed_candidate_references": 20,
        "observed_online_runs": 20,
        "attempt_one_qc_passes": 20,
        "zero_quarantine": True,
        "exact_candidate_cohort": True,
        "baseline_online_runs": 0,
        "prepared_receipt_hash": prepared_hash,
        "reference_execution_receipt_hash": reference_hash,
        "execution_receipt_hash": execution_hash,
        "runtime_identity": v184._runtime_identity(audits),
        "ready_manifest": {
            "path": str(output["ready"].resolve()),
            "file_sha256": file_hash(output["ready"]),
            "manifest_hash": manifest["manifest_hash"],
        },
        "candidate_inventory": {
            "path": str(output["inventory"].resolve()),
            "file_sha256": file_hash(output["inventory"]),
            "inventory_hash": inventory["inventory_hash"],
        },
        "source_v184": {
            "ready_file_sha256": SOURCE_READY_SHA256,
            "tape_catalog_file_sha256": SOURCE_TAPE_CATALOG_SHA256,
            "blind_file_sha256": SOURCE_BLIND_SHA256,
            "result_file_sha256": SOURCE_RESULT_SHA256,
            "result_hash": SOURCE_RESULT_HASH,
        },
        "ledgers": {
            "runs": {"events": run_count, "last_hash": run_last_hash},
            "references": {
                "events": reference_count,
                "last_hash": reference_last_hash,
            },
        },
        "run_evidence": run_evidence,
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


def _paired_permutation(differences: Sequence[float], *, seed: int) -> dict[str, Any]:
    values = np.asarray(differences, dtype=float)
    _require(
        values.size == 20 and np.isfinite(values).all(), "invalid paired differences"
    )
    observed = float(values.mean())
    rng = np.random.default_rng(seed)
    extreme = 0
    n_resamples = 100_000
    for start in range(0, n_resamples, 10_000):
        count = min(10_000, n_resamples - start)
        signs = rng.choice(np.asarray([-1.0, 1.0]), size=(count, values.size))
        permuted = (signs * values).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(permuted) >= abs(observed)))
    return {
        "method": "paired_sign_flip_monte_carlo_with_plus_one_correction",
        "seed": seed,
        "resamples": n_resamples,
        "observed_mean_difference": observed,
        "two_sided_p_value": (extreme + 1) / (n_resamples + 1),
        "used_as_gate": False,
    }


def _evaluate_training(
    rows: Sequence[Mapping[str, Any]], control_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    by_seed = {row["seed"]: row for row in rows}
    controls = {row["seed"]: row for row in control_rows}
    _require(
        len(rows) == 20
        and set(by_seed) == set(SEEDS)
        and set(controls) == set(SEEDS)
        and all(row.get("method") == "sche_nash" for row in rows),
        "V185 rows are not the exact paired 20-seed product",
    )
    gates = {}
    for index, metric in enumerate(METRICS):
        candidate = [by_seed[seed].get(metric) for seed in SEEDS]
        control = [controls[seed].get(metric) for seed in SEEDS]
        _require(
            all(_finite(value) for value in candidate + control),
            f"V185 {metric} contains nonfinite values",
        )
        candidate_values = [float(value) for value in candidate]
        control_values = [float(value) for value in control]
        differences = [
            candidate_value - control_value
            for candidate_value, control_value in zip(candidate_values, control_values)
        ]
        candidate_mean = sum(candidate_values) / 20
        control_mean = sum(control_values) / 20
        mean_difference = sum(differences) / 20
        baseline = FROZEN_BASELINES[metric]
        absolute_pass = candidate_mean > float(baseline["mean"])
        paired_pass = mean_difference >= 0.0 if index == 0 else mean_difference > 0.0
        gates[metric] = {
            "frozen_primary_comparator": baseline["method"],
            "frozen_baseline_mean": baseline["mean"],
            "candidate_mean": candidate_mean,
            "V184_same_tape_control_mean": control_mean,
            "candidate_minus_V184_control_mean": mean_difference,
            "candidate_strictly_exceeds_frozen_baseline_mean": absolute_pass,
            "paired_requirement": "nonnegative" if index == 0 else "strictly_positive",
            "paired_requirement_pass": paired_pass,
            "paired_positive_wins": sum(value > 0.0 for value in differences),
            "paired_ties": sum(value == 0.0 for value in differences),
            "paired_n": 20,
            "paired_difference_BCa_95_percent_interval": bca_interval(
                differences, n_resamples=10_000, seed=185_000 + index
            ),
            "two_sided_paired_permutation": _paired_permutation(
                differences, seed=185_100 + index
            ),
            "passed": absolute_pass and paired_pass,
        }
    return {
        "gates": gates,
        "all_twenty_qpr_values_finite": True,
        "all_five_preregistered_performance_requirements_pass": all(
            gate["passed"] for gate in gates.values()
        ),
    }


def reveal_v185(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    _require(not output["result"].exists(), "V185 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V185 blind audit")
    _require(
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("metrics_consulted") is False
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("observed_online_runs") == 20
        and blind.get("attempt_one_qc_passes") == 20
        and blind.get("zero_quarantine") is True
        and blind.get("baseline_online_runs") == 0,
        "V185 blind audit does not authorize reveal",
    )
    _reread_goal()
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    rows = []
    for run in manifest["runs"]:
        summary_path = (
            output["workspace"]
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
                "method": "sche_nash",
                "seed": run["seed"],
                "run_id": run["run_id"],
                **v184._summary_metrics(summary),
                "summary_path": str(summary_path),
                "summary_file_sha256": file_hash(summary_path),
            }
        )
    control = read_json(SOURCE_RESULT)
    control_rows = control["complete_confirmation_rows"]
    evaluation = _evaluate_training(rows, control_rows)
    passed = evaluation["all_five_preregistered_performance_requirements_pass"]
    document = {
        "schema_version": "NSE_E1_LOW_RELATIVE_LOAD_OCS_TRAINING_RESULT_V185_V1",
        "created_at": utc_now(),
        "status": "training_pass" if passed else "training_fail",
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "homogeneous_20node_low_closed": False,
        "middle_load_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "seeds": list(SEEDS),
        "source_V184_result_hash": SOURCE_RESULT_HASH,
        "same_tape_paired_training": True,
        "baseline_online_runs": 0,
        "complete_training_rows": rows,
        "evaluation": evaluation,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
        "decision": (
            "freeze_V185_training_winner_and_preregister_disjoint_low_confirmation"
            if passed
            else "retain_complete_V185_failure_close_axis_and_do_not_advance_to_middle"
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
        "prepare": prepare_v185,
        "build-references": build_references_v185,
        "execute": execute_v185,
        "blind-audit": blind_audit_v185,
        "reveal": reveal_v185,
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
