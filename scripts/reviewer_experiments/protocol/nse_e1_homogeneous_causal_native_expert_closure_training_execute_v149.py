from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_prepare_v149 import (
    AMENDMENT_SHA256,
    ARM_ID,
    PLAN_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    ROOT,
    RUN_ORDER_SEED,
    paths,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


READY_SCHEDULE_NAME = "frozen-ready-run-order-v149.json"
EXECUTION_RECEIPT_NAME = "execution-receipt-v149.json"


def _assert_hashed(document: dict[str, Any], field: str, label: str) -> str:
    payload = dict(document)
    claimed = payload.pop(field, None)
    if not isinstance(claimed, str) or object_hash(payload) != claimed:
        raise RuntimeError(f"{label} self-hash changed")
    return claimed


def materialize_ready_schedule(root: Path = ROOT) -> dict[str, Any]:
    source_path = paths(root)["schedule"]
    source = read_json(source_path)
    source_hash = _assert_hashed(source, "schedule_hash", "V149 source schedule")
    if (
        source.get("plan_sha256") != PLAN_SHA256
        or source.get("amendment_sha256") != AMENDMENT_SHA256
        or source.get("run_order_seed") != RUN_ORDER_SEED
        or len(source.get("schedule", [])) != 60
    ):
        raise RuntimeError("V149 source schedule boundary changed")
    manifest_path = paths(root)["ready"]
    manifest = load_and_validate_manifest(manifest_path)
    if (
        manifest.get("all_references_bound") is not True
        or len(manifest.get("reference_build_dependencies", [])) != 60
    ):
        raise RuntimeError("V149 ready manifest is not fully reference-bound")
    lookup: dict[tuple[str, str], str] = {}
    for run in manifest["runs"]:
        key = (run["workload"]["request_freq"], run["seed"])
        if key in lookup:
            raise RuntimeError(f"duplicate V149 ready key: {key}")
        lookup[key] = run["run_id"]
    schedule = []
    for item in source["schedule"]:
        key = (item["load"], item["seed"])
        if key not in lookup:
            raise RuntimeError(f"missing V149 ready run: {key}")
        schedule.append({**item, "run_id": lookup[key]})
    if len(schedule) != 60 or len({item["run_id"] for item in schedule}) != 60:
        raise RuntimeError("V149 ready schedule is not an exact 60-run product")
    if set(lookup) != {(item["load"], item["seed"]) for item in schedule}:
        raise RuntimeError("V149 ready manifest contains unscheduled runs")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAUSAL_NATIVE_EXPERT_CLOSURE_READY_RUN_ORDER_V149_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "amendment_sha256": AMENDMENT_SHA256,
        "source_schedule_path": str(source_path),
        "source_schedule_file_sha256": file_hash(source_path),
        "source_schedule_hash": source_hash,
        "run_order_seed": RUN_ORDER_SEED,
        "ready_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "run_count": 60,
        },
        "schedule": schedule,
    }
    document["schedule_hash"] = object_hash(document)
    output = root / READY_SCHEDULE_NAME
    if output.exists():
        existing = read_json(output)
        _assert_hashed(existing, "schedule_hash", "V149 ready schedule")
        left = dict(existing)
        right = dict(document)
        for payload in (left, right):
            payload.pop("created_at", None)
            payload.pop("schedule_hash", None)
        if left != right:
            raise RuntimeError("refusing to replace changed V149 ready schedule")
        return existing
    write_json_atomic(output, document)
    return document


def execute_v149(root: Path = ROOT) -> dict[str, Any]:
    output = root / EXECUTION_RECEIPT_NAME
    if output.exists():
        raise RuntimeError(f"V149 execution receipt already exists: {output}")
    if not PYTHON_PATH.is_file() or file_hash(PYTHON_PATH) != PYTHON_SHA256:
        raise RuntimeError("V149 frozen Python executable is missing or changed")
    schedule = materialize_ready_schedule(root)
    schedule_path = root / READY_SCHEDULE_NAME
    manifest_path = paths(root)["ready"]
    manifest = load_and_validate_manifest(manifest_path)
    run_by_id = {run["run_id"]: run for run in manifest["runs"]}
    workspace = paths(root)["workspace"]
    log_root = root / "execution-logs"
    log_root.mkdir(parents=True, exist_ok=True)
    dispatches = []
    for item in schedule["schedule"]:
        run = run_by_id[item["run_id"]]
        canonical = workspace / "canonical" / item["run_id"]
        action = "executed_frozen_dispatch"
        if canonical.is_dir():
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            action = "validated_preexisting_qc_pass_canonical"
        else:
            command = [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "run",
                str(manifest_path),
                str(workspace),
                "--run-id",
                item["run_id"],
            ]
            stdout_path = log_root / f"{item['ordinal']:02d}.stdout.log"
            stderr_path = log_root / f"{item['ordinal']:02d}.stderr.log"
            with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
                "w", encoding="utf-8"
            ) as stderr:
                completed = subprocess.run(
                    command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
                )
            if completed.returncode != 0:
                failure = {
                    "schema_version": "NSE_E1_HOMOGENEOUS_CAUSAL_NATIVE_EXPERT_CLOSURE_EXECUTION_FAILURE_V149_V1",
                    "created_at": utc_now(),
                    "candidate_performance_summaries_parsed": 0,
                    "plan_sha256": PLAN_SHA256,
                    "amendment_sha256": AMENDMENT_SHA256,
                    "ready_schedule_path": str(schedule_path),
                    "ready_schedule_file_sha256": file_hash(schedule_path),
                    "ready_schedule_hash": schedule["schedule_hash"],
                    "completed_dispatches": dispatches,
                    "failed_ordinal": item["ordinal"],
                    "failed_run_id": item["run_id"],
                    "exit_code": completed.returncode,
                    "stdout_path": str(stdout_path),
                    "stdout_sha256": file_hash(stdout_path),
                    "stderr_path": str(stderr_path),
                    "stderr_sha256": file_hash(stderr_path),
                }
                failure["failure_hash"] = object_hash(failure)
                write_json_atomic(root / "execution-failure-v149.json", failure)
                raise RuntimeError(
                    f"V149 frozen dispatch {item['ordinal']} failed with exit code "
                    f"{completed.returncode}"
                )
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        if not (
            attempt.get("status") == "qc_pass"
            and attempt.get("classification") == "qc_pass"
            and attempt.get("exit_code") == 0
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
        ):
            raise RuntimeError(f"V149 canonical is not a QC pass: {item['run_id']}")
        dispatch = {
            "ordinal": item["ordinal"],
            "load": item["load"],
            "seed": item["seed"],
            "run_id": item["run_id"],
            "action": action,
            "exit_code": 0,
            "attempt": attempt.get("attempt"),
            "attempt_file_sha256": file_hash(canonical / "attempt.json"),
            "qc_report_sha256": file_hash(canonical / "qc_report.json"),
            "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
        }
        if action == "executed_frozen_dispatch":
            dispatch.update(
                {
                    "stdout_path": str(stdout_path),
                    "stdout_sha256": file_hash(stdout_path),
                    "stderr_path": str(stderr_path),
                    "stderr_sha256": file_hash(stderr_path),
                }
            )
        dispatches.append(dispatch)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAUSAL_NATIVE_EXPERT_CLOSURE_EXECUTION_V149_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "amendment_sha256": AMENDMENT_SHA256,
        "ready_schedule_path": str(schedule_path),
        "ready_schedule_file_sha256": file_hash(schedule_path),
        "ready_schedule_hash": schedule["schedule_hash"],
        "run_order_seed": RUN_ORDER_SEED,
        "dispatch_count": len(dispatches),
        "all_exit_codes_zero": all(item["exit_code"] == 0 for item in dispatches),
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output, receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    document = materialize_ready_schedule() if args.materialize_only else execute_v149()
    key = "schedule_hash" if args.materialize_only else "receipt_hash"
    print(json.dumps({key: document[key], "runs": 60}))


if __name__ == "__main__":
    main()
