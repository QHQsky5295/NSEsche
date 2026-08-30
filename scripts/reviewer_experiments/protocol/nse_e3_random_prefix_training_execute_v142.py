from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    ARM_IDS,
    METHOD_LABELS,
    PLAN_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    ROOT,
    RUN_ORDER_SEED,
    paths,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


READY_SCHEDULE = ROOT / "frozen-ready-run-order-v142.json"
EXECUTION_RECEIPT = ROOT / "execution-receipt-v142.json"


def ready_manifest_path(root: Path, manifest_id: str) -> Path:
    return root / f"manifest.{manifest_id}.ready.json"


def workspace_path(root: Path, manifest_id: str) -> Path:
    return root / "runs" / manifest_id


def _assert_hashed_object(document: dict[str, Any], field: str, label: str) -> str:
    payload = dict(document)
    claimed = payload.pop(field, None)
    if not isinstance(claimed, str) or object_hash(payload) != claimed:
        raise RuntimeError(f"{label} self-hash changed")
    return claimed


def _manifest_ids() -> list[str]:
    return ["v142-baselines", *ARM_IDS]


def materialize_ready_schedule(root: Path = ROOT) -> dict[str, Any]:
    base_path = paths(root)["schedule"]
    if not base_path.is_file():
        raise RuntimeError(f"missing V142 base schedule: {base_path}")
    base = read_json(base_path)
    base_hash = _assert_hashed_object(base, "schedule_hash", "V142 base schedule")
    if (
        base.get("run_order_seed") != RUN_ORDER_SEED
        or base.get("method_labels") != METHOD_LABELS
        or len(base.get("schedule", [])) != 108
    ):
        raise RuntimeError("V142 base schedule boundary changed")

    manifests: dict[str, dict[str, Any]] = {}
    ready_evidence: dict[str, dict[str, Any]] = {}
    lookup: dict[tuple[str, str, str], str] = {}
    for manifest_id in _manifest_ids():
        path = ready_manifest_path(root, manifest_id)
        manifest = load_and_validate_manifest(path)
        manifests[manifest_id] = manifest
        ready_evidence[manifest_id] = {
            "path": str(path),
            "file_sha256": file_hash(path),
            "manifest_hash": manifest["manifest_hash"],
            "run_count": len(manifest["runs"]),
        }
        label_override = None if manifest_id == "v142-baselines" else manifest_id
        for run in manifest["runs"]:
            label = label_override or run["method"]
            key = (scenario_id(run), run["seed"], label)
            if key in lookup:
                raise RuntimeError(f"duplicate V142 ready schedule key: {key}")
            lookup[key] = run["run_id"]

    schedule = []
    for item in base["schedule"]:
        key = (item["scenario"], item["seed"], item["method_label"])
        try:
            run_id = lookup[key]
        except KeyError as exc:
            raise RuntimeError(
                f"missing V142 ready run for schedule key: {key}"
            ) from exc
        manifest_id = (
            "v142-baselines"
            if item["manifest_id"] == "baselines"
            else item["manifest_id"]
        )
        schedule.append(
            {
                **item,
                "manifest_id": manifest_id,
                "source_unbound_run_id": item["run_id"],
                "run_id": run_id,
            }
        )
    if len(schedule) != 108 or len({item["run_id"] for item in schedule}) != 108:
        raise RuntimeError("V142 ready schedule is not an exact 108-run product")
    if set(lookup) != {
        (item["scenario"], item["seed"], item["method_label"]) for item in schedule
    }:
        raise RuntimeError("V142 ready manifests contain unscheduled runs")

    document = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_READY_RUN_ORDER_V142_V1",
        "created_at": utc_now(),
        "performance_results_consulted": False,
        "plan_sha256": PLAN_SHA256,
        "source_schedule_path": str(base_path),
        "source_schedule_file_sha256": file_hash(base_path),
        "source_schedule_hash": base_hash,
        "run_order_seed": RUN_ORDER_SEED,
        "ready_manifests": ready_evidence,
        "schedule": schedule,
    }
    document["schedule_hash"] = object_hash(document)
    output = root / READY_SCHEDULE.name
    if output.exists():
        existing = read_json(output)
        existing_hash = _assert_hashed_object(
            existing, "schedule_hash", "V142 ready schedule"
        )
        comparable_existing = dict(existing)
        comparable_document = dict(document)
        comparable_existing.pop("created_at", None)
        comparable_existing.pop("schedule_hash", None)
        comparable_document.pop("created_at", None)
        comparable_document.pop("schedule_hash", None)
        if comparable_existing != comparable_document:
            raise RuntimeError("refusing to replace changed V142 ready schedule")
        existing["schedule_hash"] = existing_hash
        return existing
    write_json_atomic(output, document)
    return document


def execute_v142(root: Path = ROOT) -> dict[str, Any]:
    if EXECUTION_RECEIPT.exists() and root == ROOT:
        raise RuntimeError(
            f"V142 execution receipt already exists: {EXECUTION_RECEIPT}"
        )
    if not PYTHON_PATH.is_file() or file_hash(PYTHON_PATH) != PYTHON_SHA256:
        raise RuntimeError("V142 frozen Python executable is missing or changed")
    schedule = materialize_ready_schedule(root)
    schedule_path = root / READY_SCHEDULE.name
    log_root = root / "execution-logs"
    log_root.mkdir(parents=True, exist_ok=True)
    dispatches = []
    for item in schedule["schedule"]:
        manifest_id = item["manifest_id"]
        manifest = ready_manifest_path(root, manifest_id)
        workspace = workspace_path(root, manifest_id)
        command = [
            str(PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "run",
            str(manifest),
            str(workspace),
            "--run-id",
            item["run_id"],
        ]
        manifest_document = load_and_validate_manifest(manifest)
        run_by_id = {run["run_id"]: run for run in manifest_document["runs"]}
        run = run_by_id[item["run_id"]]
        canonical = workspace / "canonical" / item["run_id"]
        if canonical.is_dir():
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest_document["manifest_hash"],
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
                    f"V142 preexisting canonical is not an attempt-1 QC pass: "
                    f"{item['run_id']}"
                )
            dispatches.append(
                {
                    "ordinal": item["ordinal"],
                    "block_id": item["block_id"],
                    "within_block_index": item["within_block_index"],
                    "method_label": item["method_label"],
                    "manifest_id": manifest_id,
                    "run_id": item["run_id"],
                    "action": "validated_preexisting_attempt1_canonical",
                    "exit_code": 0,
                    "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                }
            )
            continue
        stdout_path = log_root / f"{item['ordinal']:03d}.stdout.log"
        stderr_path = log_root / f"{item['ordinal']:03d}.stderr.log"
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command,
                cwd=Path.cwd(),
                stdout=stdout,
                stderr=stderr,
                check=False,
            )
        dispatch = {
            "ordinal": item["ordinal"],
            "block_id": item["block_id"],
            "within_block_index": item["within_block_index"],
            "method_label": item["method_label"],
            "manifest_id": manifest_id,
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
                "schema_version": "NSE_E3_RANDOM_PREFIX_EXECUTION_FAILURE_V142_V1",
                "created_at": utc_now(),
                "performance_results_consulted": False,
                "plan_sha256": PLAN_SHA256,
                "ready_schedule_path": str(schedule_path),
                "ready_schedule_file_sha256": file_hash(schedule_path),
                "ready_schedule_hash": schedule["schedule_hash"],
                "completed_dispatches": dispatches,
                "failed_ordinal": item["ordinal"],
            }
            failure["failure_hash"] = object_hash(failure)
            write_json_atomic(root / "execution-failure-v142.json", failure)
            raise RuntimeError(
                f"V142 frozen dispatch {item['ordinal']} failed with "
                f"exit code {completed.returncode}"
            )

    receipt = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_EXECUTION_V142_V1",
        "created_at": utc_now(),
        "performance_results_consulted": False,
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
    output = root / EXECUTION_RECEIPT.name
    if output.exists():
        raise RuntimeError(f"refusing to overwrite V142 execution receipt: {output}")
    write_json_atomic(output, receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--materialize-only",
        action="store_true",
        help="freeze the ready run IDs without executing any simulator process",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.materialize_only:
        document = materialize_ready_schedule()
        print(json.dumps({"schedule_hash": document["schedule_hash"], "runs": 108}))
    else:
        receipt = execute_v142()
        print(json.dumps({"receipt_hash": receipt["receipt_hash"], "runs": 108}))


if __name__ == "__main__":
    main()
