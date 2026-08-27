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


ROOT = Path("tmp/nse_e3e4_strict_native_per_player_training_20260828_v92")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_strict_native_per_player_training_plan_v92.json"
)
PLAN_SHA256 = "0df36e5321bcf3bfa6cca2653c3ba0a206ff2b9e498cc91e3175c5dd3a05a79c"
PREPARED = ROOT / "manifest.v92-strict-native-per-player-training.sla.json"
PREPARED_FILE_SHA256 = (
    "86cf2ca213427c08cec1c43b7b44d764dbe4b0d49368cf962da2f2dc0ee1c2f1"
)
PREPARED_MANIFEST_HASH = (
    "b00ff2dd25c34cf81933ae773599cbf3c49f8967b6aaa1d1fefb175f1942ad41"
)
READY = ROOT / "manifest.v92-strict-native-per-player-training.ready.json"
READY_FILE_SHA256 = "a97fcfe5ff0f7d2572900574b88392de97b29ba0c5f189d5640611c34fa41dee"
READY_MANIFEST_HASH = "9791659d07a17231c43820a7b2d1c7324b8a5ffe0038169725b4521f9f929015"
WORKSPACE = ROOT / "runs/training-v92"
PAIRING = ROOT / "training-v92-pairing-audit.json"
REFERENCES = ROOT / "references.v92.catalog.json"
REFERENCES_FILE_SHA256 = (
    "82d35d00a76fc4c19904d1ff3a4e953799e2da987cdac1dcc538dab2b42e7012"
)
REFERENCE_WORKSPACE = ROOT / "reference-builds-v92"
OUTPUT = ROOT / "joint-blind-audit-v92-training.json"
EXPECTED_BINARY_SHA256 = (
    "a2be2019e5875719a03d1a6aa72bfc202865a473605850f02680aded3c41d671"
)
EXPECTED_PYTHON_SHA256 = (
    "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
)
EXPECTED_CARGO_LOCK_SHA256 = (
    "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
)
EXPECTED_PROFILES = {
    "E3": "ocs_native_exact_pipeline_per_player_strict_pareto",
    "E4": "jiagu_native_exact_per_player_strict_pareto",
}
EXPECTED_SEEDS = {"E713", "E714", "E715"}
CONFIRMATION_SEEDS = {"E716", "E717", "E718"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected_sha256: str) -> None:
    _require(path.is_file(), f"missing frozen input: {path}")
    _require(file_hash(path) == expected_sha256, f"frozen input changed: {path}")


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
        run_config = read_json(table.parent / "run_config.json")
        experiment_id = run_config.get("experiment_id")
        if experiment_id is None:
            experiment_id = (
                "E4"
                if ".E4." in f".{key}." or key.startswith("nse-reference.E4")
                else "E3"
            )
        _require(
            run_config.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == EXPECTED_PROFILES[experiment_id],
            f"reference expert profile mismatch: {key}",
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
            len(values) == 1 and None not in values, f"runtime mismatch: {output_field}"
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
            f"expert profile mismatch: {run_id}",
        )
        _require(
            metadata.get("v92_training_plan_sha256") == PLAN_SHA256
            and metadata.get("v92_training_only") is True
            and metadata.get("v92_training_seed_metrics_previously_revealed") is True
            and metadata.get("v92_exact_native_initializer") is True
            and metadata.get("v92_every_player_expert_nonworsening_certificate") is True
            and metadata.get("v92_at_least_one_player_strict_expert_improvement")
            is True
            and metadata.get("v92_resource_scaling_excluded") is True
            and metadata.get("v92_complete_v91_cohort_retained") is True,
            f"V92 scientific boundary missing: {run_id}",
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
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (PREPARED, PREPARED_FILE_SHA256),
        (READY, READY_FILE_SHA256),
        (REFERENCES, REFERENCES_FILE_SHA256),
    ):
        _assert_file(path, expected)
    _require(
        not (ROOT / "training-result-v92.json").exists(),
        "V92 reveal exists before blind audit",
    )
    prepared = load_and_validate_manifest(PREPARED)
    manifest = load_and_validate_manifest(READY)
    _require(
        prepared["manifest_hash"] == PREPARED_MANIFEST_HASH
        and manifest["manifest_hash"] == READY_MANIFEST_HASH
        and len(manifest["runs"]) == 12
        and len(manifest["reference_build_dependencies"]) == 12
        and manifest.get("all_references_bound") is True
        and manifest.get("formal_results_eligible") is False,
        "ready manifest boundary is invalid",
    )
    _require(
        {run["seed"] for run in manifest["runs"]} == EXPECTED_SEEDS
        and not ({run["seed"] for run in manifest["runs"]} & CONFIRMATION_SEEDS),
        "training/confirmation seed boundary changed",
    )
    pairing = read_json(PAIRING)
    run_evidence, runtime = _run_evidence(manifest, pairing)
    reference_evidence = _reference_evidence(manifest)
    run_events, run_last_hash = verify_ledger(WORKSPACE / "ledger.jsonl")
    reference_events, reference_last_hash = verify_ledger(
        REFERENCE_WORKSPACE / "reference_builds/ledger.jsonl"
    )
    _require(run_events == 26, "training ledger must contain exactly 26 events")
    _require(reference_events == 12, "reference ledger must contain exactly 12 events")

    audit = {
        "schema_version": "NSE_E3E4_V92_TRAINING_BLIND_AUDIT_V1",
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
        "new_baseline_online_runs": 0,
        "attempt_one_required_and_observed": True,
        "zero_quarantine_required_and_observed": True,
        "exact_run_id_sets": True,
        "confirmation_seeds_opened": False,
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
        "reference_catalog": {
            "path": str(REFERENCES.resolve()),
            "file_sha256": REFERENCES_FILE_SHA256,
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
