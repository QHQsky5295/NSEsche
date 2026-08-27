from __future__ import annotations

import json
import re
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


ROOT = Path("tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_confirmation_plan_v94.json"
)
PLAN_SHA256 = "ba11cefa2af67a0347f126104922d3e94c501a9dce043965463719405a5cc90d"
PREPARED = ROOT / "prepared-confirmation-manifests-v94.json"
PREPARED_FILE_SHA256 = (
    "b9d58e190d196bcedab461e9d9bad34b03ac5972fb905f3d8785ccc8e7bc8401"
)
SLA_MANIFEST = ROOT / "manifest.v94-srpt-terminal-dual-confirmation.sla.json"
SLA_MANIFEST_FILE_SHA256 = (
    "2dac626366adb7cf8f5afd5421f40543cb65bd0a100b2c543e3452fd909545cc"
)
SLA_MANIFEST_HASH = "31073048c47cf00016ea27be72259e5121a539be35d0824799e1260a8f3bc570"
READY = ROOT / "manifest.v94-srpt-terminal-dual-confirmation.ready.json"
READY_FILE_SHA256 = "256a8534de3121895760b28e5330093044e6ef0b85873ab7edecc4451e0d4e40"
READY_MANIFEST_HASH = "f68d33b2d3a07e0fcb05337fd88983993d508a0d1fd58ebbceff552bbd0639db"
TAPES = ROOT / "tapes.catalog.json"
TAPES_FILE_SHA256 = "9cb86b2a7b6113a5249e2d1b91d82566894d8dda2672d705abe5d598444a24bd"
REFERENCES = ROOT / "references.v94.catalog.json"
REFERENCES_FILE_SHA256 = (
    "dfca3458b6a8713d11383d16a7d242df44de4a0f26c6ae5dd73cb1b8da20a115"
)
CAPTURE_WORKSPACE = ROOT / "tape-stage"
REFERENCE_WORKSPACE = ROOT / "reference-stage"
WORKSPACE = ROOT / "runs/confirmation-v94"
PAIRING = ROOT / "confirmation-v94-pairing-audit.json"
OUTPUT = ROOT / "joint-blind-audit-v94-confirmation.json"
RESULT = ROOT / "confirmation-result-v94.json"
EXPECTED_BINARY_SHA256 = (
    "9b97746f2785daccd086780c1203d0d3f823cb155350e4befa99b278201edf77"
)
EXPECTED_PYTHON_SHA256 = (
    "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
)
EXPECTED_CARGO_LOCK_SHA256 = (
    "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
)
EXPECTED_PROFILES = {
    "E3": "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto",
    "E4": (
        "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
        "srpt_ready_dual_window_safe_pareto"
    ),
}
EXPECTED_SEEDS = {"E723", "E724", "E725"}
TRAINING_SEEDS = {"E720", "E721", "E722"}
V93_RESERVED_SEEDS = {"E716", "E717", "E718"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected_sha256: str) -> None:
    _require(path.is_file(), f"missing frozen input: {path}")
    _require(file_hash(path) == expected_sha256, f"frozen input changed: {path}")


def _tape_evidence(manifest: dict) -> list[dict]:
    catalog = read_json(TAPES)
    entries = catalog.get("entries")
    expected_keys = {run["workload_tape"]["key"] for run in manifest["runs"]}
    _require(
        isinstance(entries, dict) and set(entries) == expected_keys,
        "tape catalog key set differs from ready manifest",
    )
    kinds = [entry.get("kind") for entry in entries.values()]
    _require(
        kinds.count("base_steady") == 3 and kinds.count("derived_burst") == 9,
        "confirmation requires exactly 3 base and 9 derived tapes",
    )
    quarantine = CAPTURE_WORKSPACE / "capture_base_tapes/quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        "tape-capture quarantine is not empty",
    )
    evidence = []
    for key in sorted(entries):
        entry = entries[key]
        tape = Path(entry["path"])
        _require(
            tape.is_file() and file_hash(tape) == entry["sha256"],
            f"tape artifact changed: {key}",
        )
        if entry["kind"] == "base_steady":
            receipt = Path(entry["capture_receipt_path"])
            attempt = read_json(receipt.parent / "attempt.json")
            _require(
                attempt.get("attempt") == 1 and attempt.get("status") == "pass",
                f"base tape is not attempt-one pass: {key}",
            )
            _require(
                receipt.is_file()
                and file_hash(receipt) == entry["capture_receipt_sha256"],
                f"base tape receipt changed: {key}",
            )
        else:
            transform = entry.get("transform", {})
            _require(
                transform.get("parent_sha256") == entry.get("parent_sha256")
                and transform.get("parent_event_count") == entry.get("event_count")
                and transform.get("event_count_invariant") == "exact"
                and transform.get("dag_order_invariant") == "exact",
                f"derived tape lineage changed: {key}",
            )
        evidence.append(
            {
                "key": key,
                "kind": entry["kind"],
                "sha256": entry["sha256"],
                "event_count": entry["event_count"],
                "workload_seed": entry["workload_seed"],
                "parent_sha256": entry.get("parent_sha256"),
            }
        )
    return evidence


def _reference_evidence(manifest: dict) -> list[dict]:
    catalog = read_json(REFERENCES)
    entries = catalog.get("entries")
    expected_keys = {run["reference_dependency"]["key"] for run in manifest["runs"]}
    _require(
        isinstance(entries, dict) and set(entries) == expected_keys,
        "reference catalog key set differs from ready manifest",
    )
    quarantine = REFERENCE_WORKSPACE / "reference_builds/quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        "reference quarantine is not empty",
    )
    evidence = []
    for key in sorted(entries):
        entry = entries[key]
        table = Path(entry["path"])
        attempt_path = table.parent / "attempt.json"
        attempt = read_json(attempt_path)
        _require(
            attempt.get("status") == "pass" and attempt.get("attempt") == 1,
            f"reference is not attempt-one pass: {key}",
        )
        for path_field, hash_field in (
            ("path", "sha256"),
            ("receipt_path", "receipt_sha256"),
            ("build_process_observation_path", "build_process_observation_sha256"),
        ):
            artifact = Path(entry[path_field])
            _require(
                artifact.is_file() and file_hash(artifact) == entry[hash_field],
                f"reference artifact changed: {key}/{path_field}",
            )
        experiment_id = "E4" if key.startswith("nse-reference.E4") else "E3"
        run_config = read_json(table.parent / "run_config.json")
        _require(
            run_config.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == EXPECTED_PROFILES[experiment_id],
            f"reference profile mismatch: {key}",
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


def _runtime_identity(pairing_runs: list[dict]) -> dict:
    fields = {
        "binary_sha256": "runtime_binary_sha256",
        "git_commit": "runtime_git_commit",
        "python_executable_sha256": "runtime_python_executable_sha256",
        "cargo_lock_sha256": "runtime_cargo_lock_sha256",
    }
    runtime = {}
    for output_field, input_field in fields.items():
        values = {item.get(input_field) for item in pairing_runs}
        _require(
            len(values) == 1 and None not in values,
            f"runtime mismatch: {output_field}",
        )
        runtime[output_field] = next(iter(values))
    _require(runtime["binary_sha256"] == EXPECTED_BINARY_SHA256, "binary SHA mismatch")
    _require(
        runtime["python_executable_sha256"] == EXPECTED_PYTHON_SHA256,
        "Python executable SHA mismatch",
    )
    _require(
        runtime["cargo_lock_sha256"] == EXPECTED_CARGO_LOCK_SHA256,
        "Cargo.lock SHA mismatch",
    )
    _require(
        isinstance(runtime["git_commit"], str)
        and re.fullmatch(r"[0-9a-f]{40}", runtime["git_commit"]) is not None,
        "runtime git commit is malformed",
    )
    return runtime


def _run_evidence(manifest: dict, pairing: dict) -> tuple[list[dict], dict]:
    expected = {run["run_id"] for run in manifest["runs"]}
    canonical_root = WORKSPACE / "canonical"
    actual = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual == expected, "canonical run directory set differs from manifest")
    quarantine = WORKSPACE / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        "confirmation quarantine is not empty",
    )
    _require(
        pairing.get("passed") is True
        and pairing.get("run_count") == 12
        and pairing.get("group_count") == 12
        and pairing.get("failed_group_count") == 0
        and not pairing.get("failures"),
        "confirmation pairing did not pass exactly 12 groups",
    )
    pairing_runs = [
        item for group in pairing.get("groups", []) for item in group.get("runs", [])
    ]
    _require(
        len(pairing_runs) == 12
        and {item.get("run_id") for item in pairing_runs} == expected,
        "pairing run evidence differs from ready manifest",
    )
    runtime = _runtime_identity(pairing_runs)
    runner = ProtocolRunner(READY, WORKSPACE)
    evidence = []
    for run in sorted(manifest["runs"], key=lambda item: item["run_id"]):
        run_id = run["run_id"]
        metadata = run.get("metadata", {})
        _require(run["seed"] in EXPECTED_SEEDS, f"unexpected seed: {run_id}")
        _require(run["method"] == "sche_nash", f"unexpected method: {run_id}")
        _require(
            run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
            == EXPECTED_PROFILES[run["experiment_id"]],
            f"profile mismatch: {run_id}",
        )
        _require(
            metadata.get("v94_confirmation_plan_sha256") == PLAN_SHA256
            and metadata.get("v94_confirmation_only") is True
            and metadata.get("v94_confirmation_metrics_previously_revealed") is False
            and metadata.get("v94_training_rows_excluded") is True
            and metadata.get("v94_v93_reserved_seeds_opened") is False
            and metadata.get("v94_parent_complete_ready_frontier") is True
            and metadata.get("v94_srpt_critical_path_player_order") is True
            and metadata.get("v94_faithful_faasrank_initializer") is True
            and metadata.get("v94_terminal_ocs_router") is True
            and metadata.get("v94_dual_window_safe_pareto_guard") is True
            and metadata.get("v94_idle_warm_dominance_router")
            is (run["experiment_id"] == "E4"),
            f"confirmation boundary missing: {run_id}",
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
            f"run is not attempt-one pass: {run_id}",
        )
        _require(
            qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
            and qc.get("issues") == [],
            f"run QC is not clean: {run_id}",
        )
        _require(
            audit.get("status") == "canonical"
            and audit.get("protocol_manifest", {}).get("manifest_hash")
            == READY_MANIFEST_HASH
            and audit.get("protocol_manifest", {}).get("file_sha256")
            == READY_FILE_SHA256,
            f"run audit does not bind frozen ready manifest: {run_id}",
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
    return evidence, runtime


def main() -> None:
    _require(not OUTPUT.exists(), f"refusing to overwrite blind audit: {OUTPUT}")
    _require(not RESULT.exists(), "confirmation result exists before blind audit")
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (PREPARED, PREPARED_FILE_SHA256),
        (SLA_MANIFEST, SLA_MANIFEST_FILE_SHA256),
        (READY, READY_FILE_SHA256),
        (TAPES, TAPES_FILE_SHA256),
        (REFERENCES, REFERENCES_FILE_SHA256),
    ):
        _assert_file(path, expected)
    sla_manifest = load_and_validate_manifest(SLA_MANIFEST)
    manifest = load_and_validate_manifest(READY)
    _require(
        sla_manifest["manifest_hash"] == SLA_MANIFEST_HASH
        and manifest["manifest_hash"] == READY_MANIFEST_HASH
        and len(manifest["runs"]) == 12
        and len(manifest["reference_build_dependencies"]) == 12
        and manifest.get("all_tapes_bound") is True
        and manifest.get("all_sla_targets_bound") is True
        and manifest.get("all_references_bound") is True
        and manifest.get("formal_results_eligible") is True,
        "ready manifest boundary is invalid",
    )
    manifest_seeds = {run["seed"] for run in manifest["runs"]}
    _require(
        manifest_seeds == EXPECTED_SEEDS
        and not (manifest_seeds & TRAINING_SEEDS)
        and not (manifest_seeds & V93_RESERVED_SEEDS),
        "confirmation seed boundary changed",
    )
    pairing = read_json(PAIRING)
    run_evidence, runtime = _run_evidence(manifest, pairing)
    tape_evidence = _tape_evidence(manifest)
    reference_evidence = _reference_evidence(manifest)
    run_events, run_last_hash = verify_ledger(WORKSPACE / "ledger.jsonl")
    capture_events, capture_last_hash = verify_ledger(
        CAPTURE_WORKSPACE / "capture_base_tapes/ledger.jsonl"
    )
    reference_events, reference_last_hash = verify_ledger(
        REFERENCE_WORKSPACE / "reference_builds/ledger.jsonl"
    )
    _require(run_events == 26, "confirmation ledger must contain 26 events")
    _require(capture_events == 3, "capture ledger must contain 3 events")
    _require(reference_events == 12, "reference ledger must contain 12 events")

    audit = {
        "schema_version": "NSE_E3E4_V94_CONFIRMATION_BLIND_AUDIT_V1",
        "created_at": utc_now(),
        "status": "passed",
        "formal_results_eligible": True,
        "operational_group_closure_eligible": False,
        "confirmation_only": True,
        "plan_path": str(PLAN.resolve()),
        "plan_file_sha256": PLAN_SHA256,
        "metrics_consulted": False,
        "scientific_summary_files_opened": 0,
        "result_files_created_before_audit": 0,
        "observed_online_runs": 12,
        "expected_online_runs": 12,
        "observed_base_tape_captures": 3,
        "observed_derived_burst_tapes": 9,
        "observed_candidate_reference_builds": 12,
        "new_baseline_online_runs": 0,
        "attempt_one_required_and_observed": True,
        "zero_quarantine_required_and_observed": True,
        "exact_run_id_sets": True,
        "training_rows_pooled": False,
        "V93_reserved_seeds_opened": False,
        "runtime_identity": runtime,
        "ready_manifest": {
            "path": str(READY.resolve()),
            "file_sha256": READY_FILE_SHA256,
            "manifest_hash": READY_MANIFEST_HASH,
            "run_count": 12,
            "reference_dependency_count": 12,
        },
        "pairing": {
            "path": str(PAIRING.resolve()),
            "file_sha256": file_hash(PAIRING),
            "passed": True,
            "run_count": 12,
            "group_count": 12,
            "failed_group_count": 0,
        },
        "run_ledger": {
            "path": str((WORKSPACE / "ledger.jsonl").resolve()),
            "file_sha256": file_hash(WORKSPACE / "ledger.jsonl"),
            "events": run_events,
            "last_hash": run_last_hash,
        },
        "capture_ledger": {
            "path": str(
                (CAPTURE_WORKSPACE / "capture_base_tapes/ledger.jsonl").resolve()
            ),
            "file_sha256": file_hash(
                CAPTURE_WORKSPACE / "capture_base_tapes/ledger.jsonl"
            ),
            "events": capture_events,
            "last_hash": capture_last_hash,
        },
        "reference_ledger": {
            "path": str(
                (REFERENCE_WORKSPACE / "reference_builds/ledger.jsonl").resolve()
            ),
            "file_sha256": file_hash(
                REFERENCE_WORKSPACE / "reference_builds/ledger.jsonl"
            ),
            "events": reference_events,
            "last_hash": reference_last_hash,
        },
        "tape_catalog": {
            "path": str(TAPES.resolve()),
            "file_sha256": TAPES_FILE_SHA256,
            "entry_count": 12,
        },
        "reference_catalog": {
            "path": str(REFERENCES.resolve()),
            "file_sha256": REFERENCES_FILE_SHA256,
            "entry_count": 12,
        },
        "run_evidence": run_evidence,
        "tape_evidence": tape_evidence,
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
                "tape_count": 12,
                "reference_count": 12,
                "summary_files_opened": 0,
                "training_rows_pooled": False,
                "V93_reserved_seeds_opened": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
