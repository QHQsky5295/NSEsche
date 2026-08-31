from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_legacy_profile_training_execute_v150 import (
    EXECUTION_RECEIPT_NAME,
    READY_SCHEDULE_NAME,
    _assert_hashed,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_legacy_profile_training_prepare_v150 import (
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    COMMON_ENVIRONMENT,
    LOADS,
    PLAN_SHA256,
    PROFILES,
    PYTHON_SHA256,
    ROOT,
    SEEDS,
    paths,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


OUTPUT_NAME = "joint-blind-audit-v150-training.json"


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    load = run["workload"]["request_freq"]
    expected_profile = PROFILES[load]
    path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    if not path.is_file():
        raise RuntimeError(f"V150 Nash log is missing: {run_id}")
    run_config_count = 0
    window_count = 0
    summary_count = 0
    reference_requested = 0
    reference_available = 0
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for raw in stream:
            event = json.loads(raw)
            kind = event.get("kind")
            if kind == "run_config":
                run_config_count += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == expected_profile
                    and event.get("operational_direct_initialization") is True
                    and event.get("operational_unrestricted_initialization") is True
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                ):
                    raise RuntimeError(
                        "V150 run_config profile/runtime contract changed"
                    )
            elif kind == "window":
                if event.get("frame") != window_count:
                    raise RuntimeError("V150 scheduler window sequence changed")
                solver = event.get("solver")
                decision = event.get("decision")
                if not isinstance(solver, Mapping) or not isinstance(decision, Mapping):
                    raise RuntimeError("V150 scheduler observation is incomplete")
                assignment_hash = decision.get("assignment_hash")
                if not (
                    isinstance(assignment_hash, int)
                    and not isinstance(assignment_hash, bool)
                    and assignment_hash >= 0
                ):
                    raise RuntimeError("V150 final assignment hash is invalid")
                state_key = event.get("reference_state_key")
                if state_key is not None:
                    reference_requested += 1
                    if event.get("reference_source") == "offline_table":
                        reference_available += 1
                window_count += 1
            elif kind == "run_summary":
                summary_count += 1
                if (
                    event.get("scheduler") != "sche_nash"
                    or event.get("windows") != 1000
                    or event.get("observation_writer_error") is not None
                ):
                    raise RuntimeError("V150 Nash terminal marker changed")
            elif kind != "function_profile":
                raise RuntimeError(f"unexpected V150 Nash observation kind: {kind}")
    if run_config_count != 1 or window_count != 1000 or summary_count != 1:
        raise RuntimeError("V150 Nash log cardinality changed")
    if reference_requested == 0 or reference_available != reference_requested:
        raise RuntimeError("V150 offline reference replay coverage changed")
    return {
        "run_id": run_id,
        "load": load,
        "seed": run["seed"],
        "profile": expected_profile,
        "nash_metrics_sha256": file_hash(path),
        "windows": window_count,
        "reference_requested_windows": reference_requested,
        "offline_reference_windows": reference_available,
    }


def _validate_reference_catalog(
    manifest: Mapping[str, Any], catalog_path: Path
) -> dict[str, Any]:
    catalog = read_json(catalog_path)
    payload = dict(catalog)
    claimed = payload.pop("catalog_hash", None)
    if not isinstance(claimed, str) or object_hash(payload) != claimed:
        raise RuntimeError("V150 reference catalog self-hash changed")
    entries = catalog.get("entries")
    if not isinstance(entries, Mapping) or len(entries) != 60:
        raise RuntimeError("V150 reference catalog is not an exact 60-entry product")
    expected_keys = {
        dependency["key"] for dependency in manifest["reference_build_dependencies"]
    }
    if set(entries) != expected_keys:
        raise RuntimeError("V150 reference catalog key set changed")
    for dependency in manifest["reference_build_dependencies"]:
        entry = entries[dependency["key"]]
        for field in (
            "sha256",
            "receipt_sha256",
            "state_pair_sequence_sha256",
            "assignment_sequence_sha256",
            "build_spec_hash",
        ):
            if entry.get(field) != dependency.get(field):
                raise RuntimeError(f"V150 bound reference {field} changed")
        if file_hash(Path(entry["path"])) != entry["sha256"]:
            raise RuntimeError("V150 reference table content hash changed")
        if file_hash(Path(entry["receipt_path"])) != entry["receipt_sha256"]:
            raise RuntimeError("V150 reference receipt content hash changed")
    return {"catalog_hash": claimed, "entry_count": len(entries)}


def _validate_pairing(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    pairing_path = paths(root)["pairing"]
    stored = read_json(pairing_path)
    recomputed = audit_manifest_pairing(
        manifest,
        paths(root)["workspace"],
        expected_methods={"*": ["sche_nash"]},
    )
    for document in (stored, recomputed):
        document.pop("created_at", None)
    if stored != recomputed or recomputed.get("passed") is not True:
        raise RuntimeError("V150 pairing audit is missing, stale, or failed")
    if recomputed.get("run_count") != 60 or recomputed.get("group_count") != 60:
        raise RuntimeError("V150 pairing product changed")
    return recomputed


def run_blind_audit(root: Path = ROOT) -> dict[str, Any]:
    output = root / OUTPUT_NAME
    if output.exists():
        raise RuntimeError(f"V150 blind audit already exists: {output}")
    prepared_path = root / "prepared-manifest-v150.json"
    prepared = read_json(prepared_path)
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V150 prepared receipt")
    execution_path = root / EXECUTION_RECEIPT_NAME
    execution = read_json(execution_path)
    execution_hash = _assert_hashed(execution, "receipt_hash", "V150 execution receipt")
    ready_schedule_path = root / READY_SCHEDULE_NAME
    ready_schedule = read_json(ready_schedule_path)
    schedule_hash = _assert_hashed(
        ready_schedule, "schedule_hash", "V150 ready schedule"
    )
    manifest_path = paths(root)["ready"]
    manifest = load_and_validate_manifest(manifest_path)
    expected_product = {(load, seed) for load in LOADS for seed in SEEDS}
    if not (
        len(manifest["runs"]) == 60
        and manifest.get("all_references_bound") is True
        and manifest.get("all_tapes_bound") is True
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and {(run["workload"]["request_freq"], run["seed"]) for run in manifest["runs"]}
        == expected_product
    ):
        raise RuntimeError("V150 ready product changed")
    for run in manifest["runs"]:
        load = run["workload"]["request_freq"]
        expected_environment = {
            **COMMON_ENVIRONMENT,
            "NASH_OPERATIONAL_EXPERT_PROXY": PROFILES[load],
        }
        if any(
            run["environment"].get(key) != value
            for key, value in expected_environment.items()
        ):
            raise RuntimeError("V150 ready environment changed")
    ledger_path = paths(root)["workspace"] / "ledger.jsonl"
    ledger_count, ledger_hash = verify_ledger(ledger_path)
    pairing = _validate_pairing(manifest, root)
    reference = _validate_reference_catalog(manifest, paths(root)["catalog"])
    by_id = {run["run_id"]: run for run in manifest["runs"]}
    expected_order = [item["run_id"] for item in ready_schedule["schedule"]]
    if [item["run_id"] for item in execution["dispatches"]] != expected_order:
        raise RuntimeError("V150 execution order changed after freezing")
    canonical_root = paths(root)["workspace"] / "canonical"
    actual_dirs = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    if actual_dirs != set(expected_order):
        raise RuntimeError("V150 canonical directory product changed")
    quarantine = paths(root)["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V150 has unexplained quarantined attempts")
    audits = []
    runtime_identity: set[tuple[str, str, str, str]] = set()
    for run_id in expected_order:
        run = by_id[run_id]
        canonical = canonical_root / run_id
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit_manifest = read_json(canonical / "manifest.json")
        software = audit_manifest.get("software_environment", {})
        identity = (
            audit_manifest.get("adapter_binary", {}).get("verified_sha256"),
            software.get("git", {}).get("commit"),
            software.get("python", {}).get("executable_sha256"),
            software.get("cargo_lock", {}).get("sha256"),
        )
        runtime_identity.add(identity)
        audits.append(_audit_nash_log(canonical, run))
    if len(runtime_identity) != 1:
        raise RuntimeError("V150 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(runtime_identity))
    if not (
        binary == BINARY_SHA256
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
        and git_commit == prepared.get("protocol_source_commit")
    ):
        raise RuntimeError("V150 runtime identity changed from frozen preparation")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_LEGACY_PROFILE_BLIND_AUDIT_V150_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "candidate_performance_summaries_parsed": 0,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "prepared_receipt_file_sha256": file_hash(prepared_path),
        "execution_receipt_hash": execution_hash,
        "execution_receipt_file_sha256": file_hash(execution_path),
        "ready_schedule_hash": schedule_hash,
        "ready_schedule_file_sha256": file_hash(ready_schedule_path),
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(manifest_path),
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "ledger_file_sha256": file_hash(ledger_path),
        "pairing_audit_path": str(paths(root)["pairing"]),
        "pairing_audit_file_sha256": file_hash(paths(root)["pairing"]),
        "pairing_passed": pairing["passed"],
        "run_count": len(audits),
        "window_count": sum(item["windows"] for item in audits),
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile_map": PROFILES,
        "all_profile_environment_reference_qc_pairing_invariants_passed": True,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output, document)
    return document


def main() -> None:
    document = run_blind_audit()
    print(json.dumps({"blind_audit_hash": document["blind_audit_hash"], "runs": 60}))


if __name__ == "__main__":
    main()
