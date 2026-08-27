from __future__ import annotations

import json
from pathlib import Path

from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.runner import ProtocolRunner
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3e4_native_expert_training_20260827_v89")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_native_expert_training_plan_v89.json"
)
PLAN_SHA256 = "e1397e0301e9d94558e281f2d363acd8b5098069ddf6ef558a24304b09f440ef"
READY = ROOT / "manifest.v89-native-expert-training.ready.json"
READY_FILE_SHA256 = "e96272803366ed00bac518ac15d440ebb88255846add13165854600c1a240b03"
READY_MANIFEST_HASH = "f8ec21ccdbe75ea4e7d2434821f5ca3b108e5b7c18b38198c03055de70b414fc"
WORKSPACE = ROOT / "runs/training-v89"
PAIRING = ROOT / "training-v89-pairing-audit.json"
REFERENCES = ROOT / "references.v89.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v89-training.json"
V88_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json"
)
V88_PLAN_SHA256 = "7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab"
V88_RESULT = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_result_v88.json"
)
V88_RESULT_SHA256 = "ddbc9d92316a27a036def3282194aa6b46b789026ea678f9a443d76d44d56842"
EXPECTED_RUNTIME = {
    "binary_sha256": "42d42a9587eecf80b5cb258a1645d032defed7e80a8fb3d29c3765cc1e1649d4",
    "git_commit": "63c668341db6c6e7595d86e679bf8dffedacfa52",
    "python_executable_sha256": (
        "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
    ),
    "cargo_lock_sha256": (
        "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
    ),
}
EXPECTED_PROFILES = {
    "E3": "ocs_native_faithful_pipeline_dual_window_safe_pareto",
    "E4": "jiagu_native_faithful_window_safe_pareto",
}
EXPECTED_SEEDS = {"E713", "E714", "E715"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected_sha256: str) -> None:
    _require(path.is_file(), f"missing frozen input: {path}")
    _require(file_hash(path) == expected_sha256, f"frozen input changed: {path}")


def _reference_evidence(manifest: dict) -> list[dict]:
    catalog = read_json(REFERENCES)
    entries = catalog.get("entries")
    _require(isinstance(entries, dict) and len(entries) == 12, "reference count != 12")
    _require(
        {run["reference_dependency"]["key"] for run in manifest["runs"]}
        == set(entries),
        "ready manifest and reference catalog key sets differ",
    )
    quarantine = ROOT / "reference-builds-v89/reference_builds/quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        "reference quarantine is not empty",
    )
    evidence = []
    for key in sorted(entries):
        entry = entries[key]
        table = Path(entry["path"])
        receipt = Path(entry["receipt_path"])
        process = Path(entry["build_process_observation_path"])
        attempt_path = table.parent / "attempt.json"
        attempt = read_json(attempt_path)
        _require(
            attempt.get("status") == "pass" and attempt.get("attempt") == 1,
            f"reference is not attempt-one pass: {key}",
        )
        _require(
            table.is_file()
            and file_hash(table) == entry["sha256"]
            and receipt.is_file()
            and file_hash(receipt) == entry["receipt_sha256"]
            and process.is_file()
            and file_hash(process) == entry["build_process_observation_sha256"],
            f"reference artifact hash mismatch: {key}",
        )
        evidence.append(
            {
                "reference_key": key,
                "build_spec_hash": entry["build_spec_hash"],
                "table_sha256": entry["sha256"],
                "receipt_sha256": entry["receipt_sha256"],
                "process_observation_sha256": entry["build_process_observation_sha256"],
                "attempt_sha256": file_hash(attempt_path),
                "attempt": 1,
                "status": "pass",
            }
        )
    return evidence


def _run_evidence(manifest: dict, pairing: dict) -> tuple[list[dict], dict]:
    expected = {run["run_id"] for run in manifest["runs"]}
    canonical_root = WORKSPACE / "canonical"
    actual = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual == expected, "canonical run directory set differs from manifest")
    quarantine = WORKSPACE / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        "training quarantine is not empty",
    )
    _require(
        pairing.get("passed") is True
        and pairing.get("run_count") == 12
        and pairing.get("group_count") == 12
        and pairing.get("failed_group_count") == 0
        and not pairing.get("failures"),
        "training pairing audit did not pass exactly 12 groups",
    )
    pairing_runs = [
        item for group in pairing.get("groups", []) for item in group.get("runs", [])
    ]
    _require(
        len(pairing_runs) == 12
        and {item.get("run_id") for item in pairing_runs} == expected,
        "pairing run evidence differs from ready manifest",
    )
    runtime_sets = {
        "binary_sha256": {item.get("runtime_binary_sha256") for item in pairing_runs},
        "git_commit": {item.get("runtime_git_commit") for item in pairing_runs},
        "python_executable_sha256": {
            item.get("runtime_python_executable_sha256") for item in pairing_runs
        },
        "cargo_lock_sha256": {
            item.get("runtime_cargo_lock_sha256") for item in pairing_runs
        },
    }
    for field, values in runtime_sets.items():
        _require(values == {EXPECTED_RUNTIME[field]}, f"runtime mismatch: {field}")

    runner = ProtocolRunner(READY, WORKSPACE)
    by_id = {run["run_id"]: run for run in manifest["runs"]}
    evidence = []
    for run_id in sorted(expected):
        run = by_id[run_id]
        metadata = run.get("metadata", {})
        _require(run["seed"] in EXPECTED_SEEDS, f"unexpected seed: {run_id}")
        _require(run["method"] == "sche_nash", f"unexpected method: {run_id}")
        _require(
            run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
            == EXPECTED_PROFILES[run["experiment_id"]],
            f"profile mismatch: {run_id}",
        )
        _require(
            metadata.get("v89_training_only") is True
            and metadata.get("v89_resource_scaling_excluded") is True
            and metadata.get("v89_training_plan_sha256") == PLAN_SHA256,
            f"V89 training boundary missing: {run_id}",
        )
        canonical = canonical_root / run_id
        runner._validate_existing_canonical(run, canonical)
        attempt_path = canonical / "attempt.json"
        qc_path = canonical / "qc_report.json"
        audit_path = canonical / "manifest.json"
        attempt = read_json(attempt_path)
        qc = read_json(qc_path)
        audit = read_json(audit_path)
        _require(
            attempt.get("attempt") == 1
            and attempt.get("status") == "qc_pass"
            and attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and attempt.get("exit_code") == 0
            and attempt.get("failure_signature") is None,
            f"run is not attempt-one technical pass: {run_id}",
        )
        _require(
            qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
            and qc.get("issues") == [],
            f"run QC is not a clean pass: {run_id}",
        )
        _require(
            audit.get("status") == "canonical"
            and audit.get("protocol_manifest", {}).get("manifest_hash")
            == READY_MANIFEST_HASH
            and audit.get("protocol_manifest", {}).get("file_sha256")
            == READY_FILE_SHA256,
            f"run audit does not bind ready manifest: {run_id}",
        )
        evidence.append(
            {
                "run_id": run_id,
                "seed": run["seed"],
                "scenario": (
                    "E4.steady"
                    if run["experiment_id"] == "E4"
                    else f"E3.{run['workload']['burst_name']}"
                ),
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": run["reference_dependency"]["sha256"],
                "result_sha256": attempt["result_sha256"],
                "attempt_sha256": file_hash(attempt_path),
                "qc_report_sha256": file_hash(qc_path),
                "audit_manifest_sha256": file_hash(audit_path),
                "audit_manifest_hash": audit["audit_manifest_hash"],
            }
        )
    return evidence, {
        field: next(iter(values)) for field, values in runtime_sets.items()
    }


def main() -> None:
    _require(not OUTPUT.exists(), f"refusing to overwrite blind audit: {OUTPUT}")
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (READY, READY_FILE_SHA256),
        (V88_PLAN, V88_PLAN_SHA256),
        (V88_RESULT, V88_RESULT_SHA256),
    ):
        _assert_file(path, expected)
    _require(not (ROOT / "training-result-v89.json").exists(), "V89 reveal exists")
    manifest = load_and_validate_manifest(READY)
    _require(
        manifest["manifest_hash"] == READY_MANIFEST_HASH
        and len(manifest["runs"]) == 12
        and len(manifest["reference_build_dependencies"]) == 12
        and manifest.get("formal_results_eligible") is False,
        "ready manifest boundary is invalid",
    )
    pairing = read_json(PAIRING)
    run_evidence, runtime_identity = _run_evidence(manifest, pairing)
    reference_evidence = _reference_evidence(manifest)
    ledger_path = WORKSPACE / "ledger.jsonl"
    ledger_events, ledger_last_hash = verify_ledger(ledger_path)
    _require(ledger_events == 26, "training ledger must contain exactly 26 events")

    audit = {
        "schema_version": "NSE_E3E4_V89_TRAINING_BLIND_AUDIT_V1",
        "created_at": utc_now(),
        "status": "passed",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_only": True,
        "plan_path": str(PLAN.resolve()),
        "plan_file_sha256": PLAN_SHA256,
        "metrics_consulted": False,
        "scientific_summary_files_opened": 0,
        "result_files_created_before_audit": 0,
        "observed_online_runs": 12,
        "expected_online_runs": 12,
        "observed_candidate_reference_builds": 12,
        "expected_candidate_reference_builds": 12,
        "frozen_baseline_online_runs_reused": 60,
        "new_baseline_online_runs": 0,
        "resource_scaling_runs": 0,
        "attempt_one_required_and_observed": True,
        "zero_quarantine_required_and_observed": True,
        "exact_run_id_sets": True,
        "confirmation_seeds_opened": False,
        "runtime_identity": runtime_identity,
        "ready_manifest": {
            "path": str(READY.resolve()),
            "file_sha256": READY_FILE_SHA256,
            "manifest_hash": READY_MANIFEST_HASH,
            "run_count": 12,
            "reference_dependency_count": 12,
        },
        "frozen_prior_evidence": {
            "v88_plan_path": str(V88_PLAN.resolve()),
            "v88_plan_file_sha256": V88_PLAN_SHA256,
            "v88_result_path": str(V88_RESULT.resolve()),
            "v88_result_file_sha256": V88_RESULT_SHA256,
        },
        "pairing": {
            "path": str(PAIRING.resolve()),
            "file_sha256": file_hash(PAIRING),
            "passed": True,
            "run_count": 12,
            "group_count": 12,
            "failed_group_count": 0,
        },
        "ledger": {
            "path": str(ledger_path.resolve()),
            "file_sha256": file_hash(ledger_path),
            "events": ledger_events,
            "last_hash": ledger_last_hash,
        },
        "reference_catalog": {
            "path": str(REFERENCES.resolve()),
            "file_sha256": file_hash(REFERENCES),
            "entry_count": 12,
        },
        "run_evidence": run_evidence,
        "reference_evidence": reference_evidence,
    }
    audit["audit_hash"] = object_hash(audit)
    write_json_atomic(OUTPUT, audit)
    print(
        json.dumps(
            {
                "status": "passed",
                "output": str(OUTPUT),
                "file_sha256": file_hash(OUTPUT),
                "audit_hash": audit["audit_hash"],
                "run_count": 12,
                "reference_count": 12,
                "summary_files_opened": 0,
                "confirmation_seeds_opened": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
