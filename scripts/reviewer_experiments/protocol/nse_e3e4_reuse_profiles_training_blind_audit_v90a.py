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


ROOT = Path("tmp/nse_e3e4_reuse_profiles_training_20260828_v90a")
AMENDMENT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_reuse_profiles_training_amendment_v90a.json"
)
AMENDMENT_SHA256 = "ac7e9a292b0545c8d5e435461c07cb4d5632875df431e62257537453264b79b7"
FAILURE_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_reuse_profiles_technical_failure_v90.json"
)
FAILURE_RECEIPT_SHA256 = (
    "e08e0d8c6082ce8e7bdb492f7decacb4a8ff8a3076b3913823a5c9743c35dd9a"
)
OUTPUT = ROOT / "joint-blind-audit-v90a-training.json"
GROUPS = {
    "v90-e3-middle-transfer": {
        "profile": "stable_faasrank_load_least_borda",
        "runs": 9,
        "ready_file_sha256": "3ca3d0918588e028224f4eb0a2a26f958c59ed08f9e01670d4424e9b8e3ccd27",
        "ready_manifest_hash": "b8ab397990604bb21e0f88a0af2fa9506edba3f501a7935fb2493a0d5262312b",
        "pairing_file_sha256": "6b0884e6a4b955f5dcdb59e3628e558331f8d9ce059936e840d0f5637d4892c2",
        "catalog_file_sha256": "1b23e30ffe46c6bdb2c1fdf15991249ba12d64b232bfcd9aafb5c80aea150061",
    },
    "v90-e3-high-transfer": {
        "profile": "stable_ocs",
        "runs": 9,
        "ready_file_sha256": "283093970dc9dc714efd75527479df31f2b51aa5bc8a2ce59473d59d06f1411a",
        "ready_manifest_hash": "25c01bb109bc19729acb6f596f8bf60b0a5bd46ac02bf1f8ec5edd3a5eca415f",
        "pairing_file_sha256": "2c42770ba3ff8bacda7e5c1bebedd07951ec6c855f0b57c6dd8e7ef73042c527",
        "catalog_file_sha256": "6a56308aecbce209de897feecfd36bc9ba99fa9e487fb363ca975c23bfba4f06",
    },
    "v90-e4-middle-transfer": {
        "profile": "stable_faasrank_load_least_borda",
        "runs": 3,
        "ready_file_sha256": "476a156e6bc489a33ad704a2d741633331fc48ab6be5df0429a1df276123c475",
        "ready_manifest_hash": "19135dbf816d59817b9631a0971ef92f17b1f537f9cb46e6faf3a0d4e0b7d53e",
        "pairing_file_sha256": "89bd76d3a6229de6f365dd29b1245fc91d262b2290a47b68af8d9773e4b69e4a",
        "catalog_file_sha256": "87a5d1077128dac140becd12bb099eeffcf8807418235fae30ee147c09631c15",
    },
}
EXPECTED_RUNTIME = {
    "binary_sha256": "42d42a9587eecf80b5cb258a1645d032defed7e80a8fb3d29c3765cc1e1649d4",
    "git_commit": "85a536a357920cafd9a3d9c474d8e5ab749be23e",
    "python_executable_sha256": (
        "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
    ),
    "cargo_lock_sha256": (
        "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
    ),
}
EXPECTED_SEEDS = {"E713", "E714", "E715"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _paths(candidate_id: str) -> dict[str, Path]:
    return {
        "ready": ROOT / f"manifest.{candidate_id}.ready.json",
        "pairing": ROOT / f"pairing.{candidate_id}.json",
        "catalog": ROOT / f"references.{candidate_id}.catalog.json",
        "workspace": ROOT / "runs" / candidate_id,
        "reference_workspace": ROOT / "reference-builds" / candidate_id,
    }


def _reference_evidence(
    manifest: dict, candidate_id: str, paths: dict[str, Path]
) -> list[dict]:
    catalog = read_json(paths["catalog"])
    entries = catalog.get("entries")
    expected_keys = {run["reference_dependency"]["key"] for run in manifest["runs"]}
    _require(
        isinstance(entries, dict) and set(entries) == expected_keys,
        f"{candidate_id} reference catalog key set mismatch",
    )
    quarantine = paths["reference_workspace"] / "reference_builds/quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        f"{candidate_id} reference quarantine is not empty",
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
                f"{candidate_id} reference artifact changed: {key}",
            )
        run_config = read_json(table.parent / "run_config.json")
        _require(
            run_config.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == GROUPS[candidate_id]["profile"],
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
    return evidence


def _run_evidence(
    manifest: dict, candidate_id: str, paths: dict[str, Path]
) -> tuple[list[dict], dict]:
    expected = {run["run_id"] for run in manifest["runs"]}
    canonical_root = paths["workspace"] / "canonical"
    actual = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual == expected, f"{candidate_id} canonical set mismatch")
    quarantine = paths["workspace"] / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.iterdir()),
        f"{candidate_id} online quarantine is not empty",
    )
    pairing = read_json(paths["pairing"])
    expected_count = GROUPS[candidate_id]["runs"]
    _require(
        pairing.get("passed") is True
        and pairing.get("run_count") == expected_count
        and pairing.get("group_count") == expected_count
        and pairing.get("failed_group_count") == 0
        and not pairing.get("failures"),
        f"{candidate_id} pairing audit failed",
    )
    pairing_runs = [
        item for group in pairing.get("groups", []) for item in group.get("runs", [])
    ]
    _require(
        len(pairing_runs) == expected_count
        and {item.get("run_id") for item in pairing_runs} == expected,
        f"{candidate_id} pairing evidence differs from manifest",
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

    runner = ProtocolRunner(paths["ready"], paths["workspace"])
    evidence = []
    for run in sorted(manifest["runs"], key=lambda item: item["run_id"]):
        run_id = run["run_id"]
        _require(run["seed"] in EXPECTED_SEEDS, f"unexpected seed: {run_id}")
        _require(run["method"] == "sche_nash", f"unexpected method: {run_id}")
        _require(
            run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
            == GROUPS[candidate_id]["profile"],
            f"online profile mismatch: {run_id}",
        )
        metadata = run.get("metadata", {})
        _require(
            metadata.get("v90a_amendment_sha256") == AMENDMENT_SHA256
            and metadata.get("v90a_training_only") is True
            and metadata.get("v90a_confirmation_seeds_untouched") is True,
            f"V90A boundary missing: {run_id}",
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
            audit.get("protocol_manifest", {}).get("manifest_hash")
            == GROUPS[candidate_id]["ready_manifest_hash"]
            and audit.get("protocol_manifest", {}).get("file_sha256")
            == GROUPS[candidate_id]["ready_file_sha256"],
            f"run audit manifest binding mismatch: {run_id}",
        )
        evidence.append(
            {
                "candidate_id": candidate_id,
                "run_id": run_id,
                "seed": run["seed"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": run["reference_dependency"]["sha256"],
                "result_sha256": attempt["result_sha256"],
                "attempt_sha256": file_hash(attempt_path),
                "qc_report_sha256": file_hash(qc_path),
                "audit_manifest_sha256": file_hash(audit_path),
            }
        )
    return evidence, {
        field: next(iter(values)) for field, values in runtime_sets.items()
    }


def main() -> None:
    _require(not OUTPUT.exists(), f"refusing to overwrite blind audit: {OUTPUT}")
    _require(
        file_hash(AMENDMENT) == AMENDMENT_SHA256,
        "V90A amendment changed before audit",
    )
    _require(
        file_hash(FAILURE_RECEIPT) == FAILURE_RECEIPT_SHA256,
        "V90 technical-failure receipt changed before audit",
    )
    _require(
        not (ROOT / "training-result-v90a.json").exists(),
        "V90A reveal exists before blind audit",
    )

    run_evidence = []
    reference_evidence = []
    group_evidence = {}
    runtime_identity = None
    all_reference_keys = set()
    for candidate_id, expected in GROUPS.items():
        paths = _paths(candidate_id)
        for name, expected_hash in (
            ("ready", expected["ready_file_sha256"]),
            ("pairing", expected["pairing_file_sha256"]),
            ("catalog", expected["catalog_file_sha256"]),
        ):
            _require(
                paths[name].is_file() and file_hash(paths[name]) == expected_hash,
                f"{candidate_id} frozen {name} changed",
            )
        manifest = load_and_validate_manifest(paths["ready"])
        _require(
            manifest["manifest_hash"] == expected["ready_manifest_hash"]
            and len(manifest["runs"]) == expected["runs"]
            and manifest.get("formal_results_eligible") is False,
            f"{candidate_id} ready boundary is invalid",
        )
        candidate_runs, candidate_runtime = _run_evidence(manifest, candidate_id, paths)
        candidate_references = _reference_evidence(manifest, candidate_id, paths)
        keys = {item["reference_key"] for item in candidate_references}
        _require(
            not all_reference_keys.intersection(keys),
            "candidate reference key sets overlap",
        )
        all_reference_keys.update(keys)
        run_events, run_last_hash = verify_ledger(paths["workspace"] / "ledger.jsonl")
        reference_ledger = (
            paths["reference_workspace"] / "reference_builds/ledger.jsonl"
        )
        ref_events, ref_last_hash = verify_ledger(reference_ledger)
        if runtime_identity is None:
            runtime_identity = candidate_runtime
        _require(
            runtime_identity == candidate_runtime,
            "runtime identity differs between candidates",
        )
        run_evidence.extend(candidate_runs)
        reference_evidence.extend(candidate_references)
        group_evidence[candidate_id] = {
            "ready_manifest_file_sha256": expected["ready_file_sha256"],
            "ready_manifest_hash": expected["ready_manifest_hash"],
            "pairing_file_sha256": expected["pairing_file_sha256"],
            "reference_catalog_file_sha256": expected["catalog_file_sha256"],
            "run_count": expected["runs"],
            "reference_count": len(candidate_references),
            "run_ledger_events": run_events,
            "run_ledger_last_hash": run_last_hash,
            "reference_ledger_events": ref_events,
            "reference_ledger_last_hash": ref_last_hash,
        }

    _require(len(run_evidence) == 21, "V90A online evidence count must be 21")
    _require(
        len(reference_evidence) == len(all_reference_keys) == 21,
        "V90A reference evidence count must be 21 unique keys",
    )
    audit = {
        "schema_version": "NSE_E3E4_V90A_TRAINING_BLIND_AUDIT_V1",
        "created_at": utc_now(),
        "status": "passed",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_only": True,
        "parent_plan_sha256": (
            "980452abb659e0c9c2cae0dc2e58ebdbe8516a061d325297d5e84380dff0ec9a"
        ),
        "amendment_path": str(AMENDMENT.resolve()),
        "amendment_file_sha256": AMENDMENT_SHA256,
        "technical_failure_receipt_file_sha256": FAILURE_RECEIPT_SHA256,
        "metrics_consulted": False,
        "scientific_summary_files_opened": 0,
        "observed_online_runs": 21,
        "expected_online_runs": 21,
        "observed_candidate_reference_builds": 21,
        "expected_candidate_reference_builds": 21,
        "new_baseline_online_runs": 0,
        "attempt_one_required_and_observed": True,
        "zero_quarantine_required_and_observed": True,
        "exact_run_id_sets": True,
        "candidate_reference_key_sets_disjoint": True,
        "failed_V90_attempts_retained": True,
        "confirmation_seeds_opened": False,
        "runtime_identity": runtime_identity,
        "groups": group_evidence,
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
                "runs": len(run_evidence),
                "references": len(reference_evidence),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
