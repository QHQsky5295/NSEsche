from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_prepare_v143 import (
    ARM_ID,
    PLAN_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    ROOT,
    RUN_ORDER_SEED,
    paths,
    ready_manifest_path,
    scenario_id,
    workspace_path,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


READY_SCHEDULE = ROOT / "frozen-ready-run-order-v143.json"
EXECUTION_RECEIPT = ROOT / "execution-receipt-v143.json"


def _assert_hashed(document: dict[str, Any], field: str, label: str) -> str:
    payload = dict(document)
    claimed = payload.pop(field, None)
    if not isinstance(claimed, str) or object_hash(payload) != claimed:
        raise RuntimeError(f"{label} self-hash changed")
    return claimed


def materialize_ready_schedule(root: Path = ROOT) -> dict[str, Any]:
    source_path = paths(root)["schedule"]
    source = read_json(source_path)
    source_hash = _assert_hashed(source, "schedule_hash", "V143 source schedule")
    if (
        source.get("plan_sha256") != PLAN_SHA256
        or source.get("run_order_seed") != RUN_ORDER_SEED
        or len(source.get("schedule", [])) != 9
    ):
        raise RuntimeError("V143 source schedule boundary changed")
    manifest_path = ready_manifest_path(root)
    manifest = load_and_validate_manifest(manifest_path)
    lookup: dict[tuple[str, str], str] = {}
    for run in manifest["runs"]:
        key = (scenario_id(run), run["seed"])
        if key in lookup:
            raise RuntimeError(f"duplicate V143 ready key: {key}")
        lookup[key] = run["run_id"]
    schedule = []
    for item in source["schedule"]:
        key = (item["scenario"], item["seed"])
        if key not in lookup:
            raise RuntimeError(f"missing V143 ready run: {key}")
        schedule.append({**item, "run_id": lookup[key]})
    if len(schedule) != 9 or len({item["run_id"] for item in schedule}) != 9:
        raise RuntimeError("V143 ready schedule is not an exact nine-run product")
    if set(lookup) != {(item["scenario"], item["seed"]) for item in schedule}:
        raise RuntimeError("V143 ready manifest contains unscheduled runs")
    document = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_READY_TAIL_READY_RUN_ORDER_V143_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "performance_results_consulted_for_mechanism_design": True,
        "plan_sha256": PLAN_SHA256,
        "source_schedule_path": str(source_path),
        "source_schedule_file_sha256": file_hash(source_path),
        "source_schedule_hash": source_hash,
        "run_order_seed": RUN_ORDER_SEED,
        "ready_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "run_count": 9,
        },
        "schedule": schedule,
    }
    document["schedule_hash"] = object_hash(document)
    output = root / READY_SCHEDULE.name
    if output.exists():
        existing = read_json(output)
        _assert_hashed(existing, "schedule_hash", "V143 ready schedule")
        left = dict(existing)
        right = dict(document)
        for payload in (left, right):
            payload.pop("created_at", None)
            payload.pop("schedule_hash", None)
        if left != right:
            raise RuntimeError("refusing to replace changed V143 ready schedule")
        return existing
    write_json_atomic(output, document)
    return document


def execute_v143(root: Path = ROOT) -> dict[str, Any]:
    output = root / EXECUTION_RECEIPT.name
    if output.exists():
        raise RuntimeError(f"V143 execution receipt already exists: {output}")
    if not PYTHON_PATH.is_file() or file_hash(PYTHON_PATH) != PYTHON_SHA256:
        raise RuntimeError("V143 frozen Python executable is missing or changed")
    schedule = materialize_ready_schedule(root)
    schedule_path = root / READY_SCHEDULE.name
    manifest_path = ready_manifest_path(root)
    manifest = load_and_validate_manifest(manifest_path)
    run_by_id = {run["run_id"]: run for run in manifest["runs"]}
    workspace = workspace_path(root)
    log_root = root / "execution-logs"
    log_root.mkdir(parents=True, exist_ok=True)
    dispatches = []
    for item in schedule["schedule"]:
        run = run_by_id[item["run_id"]]
        canonical = workspace / "canonical" / item["run_id"]
        if canonical.is_dir():
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            attempt = read_json(canonical / "attempt.json")
            qc = read_json(canonical / "qc_report.json")
            if not (
                attempt.get("attempt") == 1
                and attempt.get("status") == "qc_pass"
                and attempt.get("classification") == "qc_pass"
                and attempt.get("exit_code") == 0
                and attempt.get("timed_out") is False
                and qc.get("passed") is True
                and qc.get("classification") == "qc_pass"
            ):
                raise RuntimeError(
                    f"V143 preexisting canonical is not an attempt-1 QC pass: {item['run_id']}"
                )
            dispatches.append(
                {
                    "ordinal": item["ordinal"],
                    "scenario": item["scenario"],
                    "seed": item["seed"],
                    "run_id": item["run_id"],
                    "action": "validated_preexisting_attempt1_canonical",
                    "exit_code": 0,
                    "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                }
            )
            continue
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
        dispatch = {
            "ordinal": item["ordinal"],
            "scenario": item["scenario"],
            "seed": item["seed"],
            "run_id": item["run_id"],
            "action": "executed_frozen_dispatch",
            "exit_code": completed.returncode,
            "stdout_path": str(stdout_path),
            "stdout_sha256": file_hash(stdout_path),
            "stderr_path": str(stderr_path),
            "stderr_sha256": file_hash(stderr_path),
        }
        dispatches.append(dispatch)
        if completed.returncode != 0:
            failure = {
                "schema_version": "NSE_E3_RANDOM_PREFIX_READY_TAIL_EXECUTION_FAILURE_V143_V1",
                "created_at": utc_now(),
                "candidate_performance_summaries_parsed": 0,
                "plan_sha256": PLAN_SHA256,
                "ready_schedule_path": str(schedule_path),
                "ready_schedule_file_sha256": file_hash(schedule_path),
                "ready_schedule_hash": schedule["schedule_hash"],
                "completed_dispatches": dispatches,
                "failed_ordinal": item["ordinal"],
            }
            failure["failure_hash"] = object_hash(failure)
            write_json_atomic(root / "execution-failure-v143.json", failure)
            raise RuntimeError(
                f"V143 frozen dispatch {item['ordinal']} failed with exit code "
                f"{completed.returncode}"
            )
    receipt = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_READY_TAIL_EXECUTION_V143_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "performance_results_consulted_for_mechanism_design": True,
        "plan_sha256": PLAN_SHA256,
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
    document = materialize_ready_schedule() if args.materialize_only else execute_v143()
    key = "schedule_hash" if args.materialize_only else "receipt_hash"
    print(json.dumps({key: document[key], "runs": 9}))


if __name__ == "__main__":
    main()
