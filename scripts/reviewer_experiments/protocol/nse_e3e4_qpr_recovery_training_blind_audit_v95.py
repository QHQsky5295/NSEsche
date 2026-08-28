from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.analysis.formal_inputs import (
    validate_canonical_run,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3e4_qpr_recovery_training_20260828_v95")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_qpr_recovery_training_plan_v95.json"
)
PLAN_FILE_SHA256 = "8d25706e4adda849e06b334eacd73117dd52b49797f1755e47ab8491844e545d"
PREPARED = ROOT / "prepared-manifests-v95.json"
PREPARED_FILE_SHA256 = (
    "bb265d2ea5d4098540554c6fbd37cdebd1b871852245f8095b3a44b5839435a0"
)
PREPARED_RECEIPT_HASH = (
    "77c49dc4e24574c26aabd17a9b1d21a2cd39491226bf0c84ebc1c123931108af"
)
TAPES = ROOT / "tapes.catalog.json"
TAPES_FILE_SHA256 = "11b6331853defbbf37ba8054d04d5b770771a5086ba14d01618516a46417b989"
TAPES_CATALOG_HASH = "4b0d62c1dc55ce9d123a0d4a811599980f386b940e5b3bc332629edbb91315a5"
CAPTURE_WORKSPACE = ROOT / "stages/tape_capture"
OUTPUT = ROOT / "joint-blind-audit-v95-training.json"
TRAINING_SEEDS = {"E726", "E727", "E728"}
CONFIRMATION_SEEDS = {"E729", "E730", "E731"}
EXPECTED_RUNTIME = {
    "binary_sha256": (
        "9b97746f2785daccd086780c1203d0d3f823cb155350e4befa99b278201edf77"
    ),
    "git_commit": "76fb198adda47b59d5314fe918e1bd5e3e8380b9",
    "python_executable_sha256": (
        "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
    ),
    "cargo_lock_sha256": (
        "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
    ),
}
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
CANDIDATES = {
    "v95a-hiku-load": {
        "E3_profile": "srpt_ready_hiku_load_faithful",
        "E4_profile": "srpt_ready_load_least_current_demand",
        "ready_file_sha256": (
            "3ae2a49ef0378229dc2fa9ec607fdba64fe89e8d9233a7f71ba48efa1cc7f573"
        ),
        "ready_manifest_hash": (
            "6c1ad31d2530a0da7a3628ca9b1b36cc7f81b523db5e5a24602aceeb21eb4c30"
        ),
        "reference_file_sha256": (
            "2d9f125ec7e024f74d43e9ff97aa6a4aef6eaa84ac309fc26bf4d7855f71f794"
        ),
        "reference_catalog_hash": (
            "75963e13510d33425b97884b449cfa00ab73f85b636ddb3df97eafbc04af6f2c"
        ),
        "pairing_file_sha256": (
            "b310cde12c19dd7bff8b973a1d967258ea83753bf6935408521c92add7c2ba5d"
        ),
    },
    "v95b-hiku2-ocs-faasrank-load": {
        "E3_profile": "srpt_ready_hiku2_ocs_borda",
        "E4_profile": "srpt_ready_faasrank_load_least_borda",
        "ready_file_sha256": (
            "a807d40ef16be3bdbdbf2bceca4a75e8118c69c68e3800124eb6c6a229e3967e"
        ),
        "ready_manifest_hash": (
            "2e4aef234c744148bdf911816f75f2f824841f021836b87f54e769c61b6734b3"
        ),
        "reference_file_sha256": (
            "7ac052f854d58d04e6fa255422bb9bdd410ca71a1adb6bb48e68d8ad80621b65"
        ),
        "reference_catalog_hash": (
            "f4b9069acd4af90faf489d6766987443bef28dc03e4fba03a30ea4e2772985ed"
        ),
        "pairing_file_sha256": (
            "cafb0ed2c94323042835844c19f747224b59341d366825dd51021dfe69021493"
        ),
    },
    "v95c-hiku-ocs3-hiku2-ocs": {
        "E3_profile": "srpt_ready_hiku_ocs3_borda",
        "E4_profile": "srpt_ready_hiku2_ocs_borda",
        "ready_file_sha256": (
            "1f73754d60ced526f9755930cb2ae6d209b5166339827ddd8ef4eba262006375"
        ),
        "ready_manifest_hash": (
            "0831e1f5402891658b1d34baf14b528bfb78f23e3b8a8a26673965248316be31"
        ),
        "reference_file_sha256": (
            "063dcabca8bf25c1197aafae74d5c97d3f4279b6ca54d4367e66b43c44a0a737"
        ),
        "reference_catalog_hash": (
            "5b78d7b78bbf0b6e3be95a97c20af3bf225f57956d050d4a4db972a9bd17bf2a"
        ),
        "pairing_file_sha256": (
            "223eb4bc4e61eac11ea087c17d5b018629d580a34354c035c07939e6683091fe"
        ),
    },
}
RENAME_RECEIPT = (
    ROOT / "runs/v95b-hiku2-ocs-faasrank-load/canonical_rename_receipt_v95.json"
)
RENAME_RECEIPT_FILE_SHA256 = (
    "7b2eedb3812b1a926223d8b55ed782733db1ec20e2b4ff5740b9143532298632"
)
RENAME_RECEIPT_HASH = "13e4c2a31490194a30217fbe46614e5b18cc15a65420941ae4bd83f5e2d7197b"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected_sha256: str) -> None:
    _require(path.is_file(), f"missing frozen input: {path}")
    _require(file_hash(path) == expected_sha256, f"frozen input changed: {path}")


def _assert_hashed_object(
    value: dict[str, Any], hash_field: str, expected_hash: str, label: str
) -> None:
    claimed = value.get(hash_field)
    unhashed = dict(value)
    unhashed.pop(hash_field, None)
    _require(claimed == expected_hash, f"{label} claimed hash changed")
    _require(object_hash(unhashed) == expected_hash, f"{label} self-hash mismatch")


def _read_ledger(path: Path) -> tuple[list[dict[str, Any]], str]:
    count, last_hash = verify_ledger(path)
    with path.open("r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    _require(len(rows) == count, f"ledger line count changed: {path}")
    _require(
        rows and rows[-1].get("event_hash") == last_hash,
        f"ledger tail hash changed: {path}",
    )
    return rows, last_hash


def _assert_ledger_contract(
    rows: list[dict[str, Any]], expected_types: Counter[str], label: str
) -> None:
    observed = Counter(str(row.get("event_type")) for row in rows)
    _require(observed == expected_types, f"{label} event contract changed: {observed}")


def _candidate_paths(candidate_id: str) -> dict[str, Path]:
    return {
        "ready": ROOT / f"manifest.{candidate_id}.ready.json",
        "references": ROOT / f"references.{candidate_id}.catalog.json",
        "pairing": ROOT / f"pairing-audit.{candidate_id}.json",
        "workspace": ROOT / "runs" / candidate_id,
        "reference_workspace": ROOT / "stages" / f"references-{candidate_id}",
    }


def _scenario(run: dict[str, Any]) -> str:
    if run["experiment_id"] == "E4":
        return "E4.steady"
    return f"E3.{run['workload']['burst_name']}"


def _tape_evidence(expected_keys: set[str]) -> tuple[list[dict[str, Any]], dict]:
    _assert_file(TAPES, TAPES_FILE_SHA256)
    catalog = read_json(TAPES)
    _assert_hashed_object(catalog, "catalog_hash", TAPES_CATALOG_HASH, "tape catalog")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and set(entries) == expected_keys,
        "tape catalog key set differs from candidate manifests",
    )
    kinds = Counter(entry.get("kind") for entry in entries.values())
    _require(
        kinds == Counter({"base_steady": 3, "derived_burst": 9}),
        f"V95 tape-kind counts changed: {kinds}",
    )
    seeds = {entry.get("workload_seed") for entry in entries.values()}
    _require(seeds == TRAINING_SEEDS, "tape catalog includes non-training seeds")

    capture_root = CAPTURE_WORKSPACE / "capture_base_tapes"
    quarantine = capture_root / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        "tape-capture quarantine is not empty",
    )
    rows, last_hash = _read_ledger(capture_root / "ledger.jsonl")
    _assert_ledger_contract(rows, Counter({"capture_canonicalized": 3}), "capture")
    _require(
        all(row.get("payload", {}).get("attempt") == 1 for row in rows),
        "base tape capture was not attempt one",
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
                and transform.get("event_count_invariant") == "exact"
                and transform.get("dag_order_invariant") == "exact",
                f"derived tape lineage changed: {key}",
            )
        evidence.append(
            {
                "key": key,
                "kind": entry["kind"],
                "workload_seed": entry["workload_seed"],
                "sha256": entry["sha256"],
                "event_count": entry["event_count"],
                "parent_sha256": entry.get("parent_sha256"),
            }
        )
    return evidence, {
        "path": str((capture_root / "ledger.jsonl").resolve()),
        "file_sha256": file_hash(capture_root / "ledger.jsonl"),
        "events": len(rows),
        "last_hash": last_hash,
    }


def _reference_evidence(
    manifest: dict[str, Any], candidate_id: str, expected: dict[str, str]
) -> tuple[list[dict[str, Any]], dict]:
    paths = _candidate_paths(candidate_id)
    _assert_file(paths["references"], expected["reference_file_sha256"])
    catalog = read_json(paths["references"])
    _assert_hashed_object(
        catalog,
        "catalog_hash",
        expected["reference_catalog_hash"],
        f"{candidate_id} reference catalog",
    )
    entries = catalog.get("entries")
    expected_keys = {run["reference_dependency"]["key"] for run in manifest["runs"]}
    _require(
        isinstance(entries, dict) and set(entries) == expected_keys,
        f"{candidate_id} reference catalog key set mismatch",
    )
    reference_root = paths["reference_workspace"] / "reference_builds"
    canonical = reference_root / "canonical"
    actual_dirs = {path.name for path in canonical.iterdir() if path.is_dir()}
    _require(
        actual_dirs == expected_keys, f"{candidate_id} reference directory mismatch"
    )
    quarantine = reference_root / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        f"{candidate_id} reference quarantine is not empty",
    )
    rows, last_hash = _read_ledger(reference_root / "ledger.jsonl")
    _assert_ledger_contract(
        rows, Counter({"reference_build_canonicalized": 12}), candidate_id
    )
    _require(
        all(row.get("payload", {}).get("attempt") == 1 for row in rows),
        f"{candidate_id} reference ledger contains non-first attempts",
    )

    evidence = []
    for key in sorted(entries):
        entry = entries[key]
        table = Path(entry["path"])
        attempt_path = table.parent / "attempt.json"
        attempt = read_json(attempt_path)
        _require(
            attempt.get("status") == "pass" and attempt.get("attempt") == 1,
            f"{candidate_id} reference is not attempt-one pass: {key}",
        )
        for path_field, hash_field in (
            ("path", "sha256"),
            ("receipt_path", "receipt_sha256"),
            ("build_process_observation_path", "build_process_observation_sha256"),
        ):
            artifact = Path(entry[path_field])
            _require(
                artifact.is_file() and file_hash(artifact) == entry[hash_field],
                f"{candidate_id} reference artifact changed: {key}/{path_field}",
            )
        run_config = read_json(table.parent / "run_config.json")
        experiment_id = "E4" if key.startswith("nse-reference.E4") else "E3"
        _require(
            run_config.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == expected[f"{experiment_id}_profile"],
            f"{candidate_id} reference profile mismatch: {key}",
        )
        evidence.append(
            {
                "candidate_id": candidate_id,
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
    return evidence, {
        "path": str((reference_root / "ledger.jsonl").resolve()),
        "file_sha256": file_hash(reference_root / "ledger.jsonl"),
        "events": len(rows),
        "last_hash": last_hash,
    }


def _runtime_identity(pairing_runs: list[dict[str, Any]]) -> dict[str, str]:
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
            f"pairing runtime mismatch: {output_field}",
        )
        runtime[output_field] = next(iter(values))
    _require(runtime == EXPECTED_RUNTIME, "pairing runtime identity changed")
    _require(
        re.fullmatch(r"[0-9a-f]{40}", runtime["git_commit"]) is not None,
        "runtime Git commit is malformed",
    )
    return runtime


def _run_evidence(
    manifest: dict[str, Any], candidate_id: str, expected: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    paths = _candidate_paths(candidate_id)
    expected_ids = {run["run_id"] for run in manifest["runs"]}
    canonical_root = paths["workspace"] / "canonical"
    actual_ids = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual_ids == expected_ids, f"{candidate_id} canonical run set mismatch")
    quarantine = paths["workspace"] / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        f"{candidate_id} run quarantine is not empty",
    )

    _assert_file(paths["pairing"], expected["pairing_file_sha256"])
    pairing = read_json(paths["pairing"])
    _require(
        pairing.get("passed") is True
        and pairing.get("run_count") == 12
        and pairing.get("group_count") == 12
        and pairing.get("passed_group_count") == 12
        and pairing.get("failed_group_count") == 0
        and pairing.get("failures") == [],
        f"{candidate_id} pairing audit did not pass exactly 12 groups",
    )
    _require(
        pairing.get("protocol_manifest_sha256") == expected["ready_manifest_hash"],
        f"{candidate_id} pairing manifest binding changed",
    )
    _require(
        Path(pairing.get("canonical_root", "")).resolve() == canonical_root.resolve(),
        f"{candidate_id} pairing canonical root changed",
    )
    pairing_runs = [
        item for group in pairing.get("groups", []) for item in group.get("runs", [])
    ]
    _require(
        len(pairing_runs) == 12
        and {item.get("run_id") for item in pairing_runs} == expected_ids,
        f"{candidate_id} pairing run evidence differs from manifest",
    )
    runtime = _runtime_identity(pairing_runs)
    _require(
        {item.get("common_hpa_sha256") for item in pairing_runs}
        == {EXPECTED_COMMON_HPA_SHA256},
        f"{candidate_id} common HPA identity changed",
    )

    rows, last_hash = _read_ledger(paths["workspace"] / "ledger.jsonl")
    _assert_ledger_contract(
        rows,
        Counter(
            {
                "batch_started": 1,
                "attempt_started": 12,
                "attempt_canonicalized": 12,
                "batch_finished": 1,
            }
        ),
        f"{candidate_id} run ledger",
    )
    started = [row for row in rows if row.get("event_type") == "attempt_started"]
    canonicalized = [
        row for row in rows if row.get("event_type") == "attempt_canonicalized"
    ]
    _require(
        all(row.get("payload", {}).get("attempt") == 1 for row in started),
        f"{candidate_id} run ledger contains non-first starts",
    )
    _require(
        {row.get("payload", {}).get("run_id") for row in started} == expected_ids
        and {row.get("payload", {}).get("run_id") for row in canonicalized}
        == expected_ids,
        f"{candidate_id} run ledger coverage changed",
    )

    evidence = []
    for run in sorted(manifest["runs"], key=lambda item: item["run_id"]):
        run_id = run["run_id"]
        experiment_id = run["experiment_id"]
        metadata = run.get("metadata", {})
        _require(run["seed"] in TRAINING_SEEDS, f"unexpected seed: {run_id}")
        _require(run["method"] == "sche_nash", f"unexpected method: {run_id}")
        _require(
            run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
            == expected[f"{experiment_id}_profile"],
            f"{candidate_id} online profile mismatch: {run_id}",
        )
        _require(
            metadata.get("v95_training_plan_sha256") == PLAN_FILE_SHA256
            and metadata.get("v95_training_only") is True
            and metadata.get("v95_training_seed_metrics_previously_revealed") is False
            and metadata.get("v95_confirmation_seeds_opened") is False
            and metadata.get("v95_formal_E01_E20_reexecution") is False
            and metadata.get("v95_candidate_id") == candidate_id
            and metadata.get("v95_candidate_profile")
            == expected[f"{experiment_id}_profile"]
            and metadata.get("v95_candidate_experiment") == experiment_id
            and metadata.get("v95_parent_complete_ready_frontier") is True
            and metadata.get("v95_srpt_critical_path_player_order") is True,
            f"{candidate_id} scientific boundary missing: {run_id}",
        )
        canonical = canonical_root / run_id
        qc = validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=expected["ready_manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt_path = canonical / "attempt.json"
        audit_path = canonical / "manifest.json"
        qc_path = canonical / "qc_report.json"
        attempt = read_json(attempt_path)
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
        protocol = audit.get("protocol_manifest", {})
        _require(
            audit.get("status") == "canonical"
            and protocol.get("manifest_hash") == expected["ready_manifest_hash"]
            and protocol.get("file_sha256") == expected["ready_file_sha256"],
            f"run audit manifest binding mismatch: {run_id}",
        )
        evidence.append(
            {
                "candidate_id": candidate_id,
                "run_id": run_id,
                "seed": run["seed"],
                "scenario": _scenario(run),
                "expert_profile": expected[f"{experiment_id}_profile"],
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
    return (
        evidence,
        runtime,
        {
            "path": str((paths["workspace"] / "ledger.jsonl").resolve()),
            "file_sha256": file_hash(paths["workspace"] / "ledger.jsonl"),
            "events": len(rows),
            "last_hash": last_hash,
        },
    )


def _assert_rename_receipt() -> dict[str, Any]:
    _assert_file(RENAME_RECEIPT, RENAME_RECEIPT_FILE_SHA256)
    receipt = read_json(RENAME_RECEIPT)
    _assert_hashed_object(
        receipt, "receipt_hash", RENAME_RECEIPT_HASH, "V95 canonical rename receipt"
    )
    _require(
        receipt.get("schema") == "NSE_ONLINE_CANONICAL_RENAME_RECEIPT_V95_V1"
        and receipt.get("candidate_id") == "v95b-hiku2-ocs-faasrank-load"
        and receipt.get("source_name") == "attempt-01"
        and receipt.get("target_name") == receipt.get("run_id")
        and receipt.get("operation") == "same_parent_os_replace_directory_only"
        and receipt.get("performance_metrics_consulted") is False
        and receipt.get("content_file_count") == 15
        and receipt.get("content_tree_hash")
        == "6b9d26352a6649380999eb1eb0aca34d400f7d2be8abe6ae8be10001d5d6e8ff",
        "V95 canonical rename boundary changed",
    )
    target = ROOT / "runs/v95b-hiku2-ocs-faasrank-load/canonical" / receipt["run_id"]
    source = target.parent / receipt["source_name"]
    _require(
        target.is_dir() and not source.exists(), "V95 canonical rename not applied"
    )
    actual_files = []
    for path in sorted(target.rglob("*")):
        if path.is_file():
            actual_files.append(
                {
                    "path": path.relative_to(target).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": file_hash(path),
                }
            )
    _require(actual_files == receipt.get("files"), "renamed canonical tree changed")
    return {
        "path": str(RENAME_RECEIPT.resolve()),
        "file_sha256": RENAME_RECEIPT_FILE_SHA256,
        "receipt_hash": RENAME_RECEIPT_HASH,
        "content_tree_hash": receipt["content_tree_hash"],
        "performance_metrics_consulted": False,
    }


def audit_training_artifacts(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"refusing to overwrite blind audit: {output}")
    _assert_file(PLAN, PLAN_FILE_SHA256)
    _assert_file(PREPARED, PREPARED_FILE_SHA256)
    _require(
        not (ROOT / "training-result-v95.json").exists(),
        "V95 reveal exists before blind audit",
    )
    plan = read_json(PLAN)
    prepared = read_json(PREPARED)
    _assert_hashed_object(
        prepared, "receipt_hash", PREPARED_RECEIPT_HASH, "V95 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and set(prepared.get("training_seeds", [])) == TRAINING_SEEDS
        and set(prepared.get("untouched_confirmation_seeds", [])) == CONFIRMATION_SEEDS
        and prepared.get("confirmation_seeds_opened") is False,
        "V95 prepared scientific boundary changed",
    )
    plan_pairs = {
        item["candidate_id"]: {
            "E3_profile": item["E3_profile"],
            "E4_profile": item["E4_profile"],
        }
        for item in plan["candidate_pairs"]
    }
    _require(
        plan_pairs
        == {
            candidate_id: {
                "E3_profile": expected["E3_profile"],
                "E4_profile": expected["E4_profile"],
            }
            for candidate_id, expected in CANDIDATES.items()
        },
        "V95 candidate pairs differ from preregistration",
    )

    manifests: dict[str, dict[str, Any]] = {}
    all_tape_keys: set[str] = set()
    all_reference_keys: set[str] = set()
    run_evidence = []
    reference_evidence = []
    groups = {}
    runtime_identity = None
    for candidate_id, expected in CANDIDATES.items():
        paths = _candidate_paths(candidate_id)
        _assert_file(paths["ready"], expected["ready_file_sha256"])
        manifest = load_and_validate_manifest(paths["ready"])
        manifests[candidate_id] = manifest
        _require(
            manifest["manifest_hash"] == expected["ready_manifest_hash"]
            and len(manifest["runs"]) == 12
            and len(manifest["reference_build_dependencies"]) == 12
            and manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_references_bound") is True
            and manifest.get("formal_results_eligible") is False,
            f"{candidate_id} ready manifest boundary is invalid",
        )
        _require(
            {run["seed"] for run in manifest["runs"]} == TRAINING_SEEDS,
            f"{candidate_id} seed boundary changed",
        )
        all_tape_keys.update(run["workload_tape"]["key"] for run in manifest["runs"])

        candidate_references, reference_ledger = _reference_evidence(
            manifest, candidate_id, expected
        )
        candidate_reference_keys = {
            item["reference_key"] for item in candidate_references
        }
        _require(
            not all_reference_keys.intersection(candidate_reference_keys),
            "candidate-specific reference key sets overlap",
        )
        all_reference_keys.update(candidate_reference_keys)
        candidate_runs, candidate_runtime, run_ledger = _run_evidence(
            manifest, candidate_id, expected
        )
        if runtime_identity is None:
            runtime_identity = candidate_runtime
        _require(
            runtime_identity == candidate_runtime,
            "runtime identity differs between candidate workspaces",
        )
        run_evidence.extend(candidate_runs)
        reference_evidence.extend(candidate_references)
        groups[candidate_id] = {
            "E3_profile": expected["E3_profile"],
            "E4_profile": expected["E4_profile"],
            "ready_manifest": {
                "path": str(paths["ready"].resolve()),
                "file_sha256": expected["ready_file_sha256"],
                "manifest_hash": expected["ready_manifest_hash"],
                "run_count": 12,
                "reference_dependency_count": 12,
            },
            "reference_catalog": {
                "path": str(paths["references"].resolve()),
                "file_sha256": expected["reference_file_sha256"],
                "catalog_hash": expected["reference_catalog_hash"],
                "entry_count": 12,
            },
            "pairing": {
                "path": str(paths["pairing"].resolve()),
                "file_sha256": expected["pairing_file_sha256"],
                "passed": True,
                "run_count": 12,
                "group_count": 12,
            },
            "run_ledger": run_ledger,
            "reference_ledger": reference_ledger,
        }

    tape_evidence, capture_ledger = _tape_evidence(all_tape_keys)
    rename_receipt = _assert_rename_receipt()
    _require(len(run_evidence) == 36, "V95 run evidence count must be 36")
    _require(
        len(reference_evidence) == len(all_reference_keys) == 36,
        "V95 reference evidence must contain 36 unique keys",
    )
    _require(len(tape_evidence) == 12, "V95 tape evidence count must be 12")
    _require(
        not any(
            seed in item["run_id"]
            for seed in CONFIRMATION_SEEDS
            for item in run_evidence
        )
        and not any(
            seed in item["reference_key"]
            for seed in CONFIRMATION_SEEDS
            for item in reference_evidence
        )
        and not any(
            seed in item["key"] for seed in CONFIRMATION_SEEDS for item in tape_evidence
        ),
        "confirmation seed artifacts exist before the training reveal",
    )

    audit = {
        "schema_version": "NSE_E3E4_QPR_RECOVERY_TRAINING_BLIND_AUDIT_V95_V1",
        "created_at": utc_now(),
        "status": "passed",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_only": True,
        "plan_path": str(PLAN.resolve()),
        "plan_file_sha256": PLAN_FILE_SHA256,
        "prepared_receipt": {
            "path": str(PREPARED.resolve()),
            "file_sha256": PREPARED_FILE_SHA256,
            "receipt_hash": PREPARED_RECEIPT_HASH,
        },
        "performance_results_consulted": False,
        "scientific_summary_files_parsed": 0,
        "result_files_created_before_audit": 0,
        "expected_candidate_pairs": 3,
        "observed_candidate_pairs": 3,
        "expected_online_runs": 36,
        "observed_online_runs": 36,
        "expected_base_tape_captures": 3,
        "observed_base_tape_captures": 3,
        "expected_derived_burst_tapes": 9,
        "observed_derived_burst_tapes": 9,
        "expected_candidate_reference_builds": 36,
        "observed_candidate_reference_builds": 36,
        "new_baseline_online_runs": 0,
        "attempt_one_required_and_observed": True,
        "zero_quarantine_required_and_observed": True,
        "exact_run_id_sets": True,
        "candidate_reference_key_sets_disjoint": True,
        "confirmation_seeds_opened": False,
        "confirmation_artifacts_observed": 0,
        "runtime_identity": runtime_identity,
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "groups": groups,
        "tape_catalog": {
            "path": str(TAPES.resolve()),
            "file_sha256": TAPES_FILE_SHA256,
            "catalog_hash": TAPES_CATALOG_HASH,
            "entry_count": 12,
        },
        "capture_ledger": capture_ledger,
        "canonical_rename_receipt": rename_receipt,
        "run_evidence": run_evidence,
        "tape_evidence": tape_evidence,
        "reference_evidence": reference_evidence,
        "reveal_authorized": True,
    }
    audit["audit_hash"] = object_hash(audit)
    write_json_atomic(output, audit)
    return audit


def main() -> None:
    audit = audit_training_artifacts()
    print(
        json.dumps(
            {
                "status": audit["status"],
                "output": str(OUTPUT),
                "file_sha256": file_hash(OUTPUT),
                "audit_hash": audit["audit_hash"],
                "run_count": audit["observed_online_runs"],
                "tape_count": len(audit["tape_evidence"]),
                "reference_count": audit["observed_candidate_reference_builds"],
                "summary_files_parsed": 0,
                "confirmation_seeds_opened": False,
                "reveal_authorized": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
