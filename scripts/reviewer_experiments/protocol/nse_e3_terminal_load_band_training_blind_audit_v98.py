from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.nse_e3_terminal_load_band_training_prepare_v98 import (
    ARMS as PREPARED_ARMS,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUSLY_RESERVED_SEEDS,
    PYTHON_SHA256,
    ROOT,
    TRAINING_SEEDS,
)
from scripts.reviewer_experiments.protocol.reference import inspect_reference_table
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.tape import inspect_tape
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


PREPARED = ROOT / "prepared-manifests-v98.json"
TAPES = ROOT / "tapes.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v98-training.json"
RESULT = ROOT / "training-result-v98.json"
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
ARMS = {
    arm_id: {
        "experiment_id": experiment_id,
        "role": role,
        "profile": profile,
        "upper_queue_density_threshold": 64.0 if role == "candidate" else None,
        "nonterminal_queue_density_floor": floor,
        "run_count": count,
    }
    for arm_id, experiment_id, role, profile, floor, count in PREPARED_ARMS
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_hashed_object(value: dict[str, Any], hash_field: str, label: str) -> str:
    claimed = value.get(hash_field)
    unhashed = dict(value)
    unhashed.pop(hash_field, None)
    _require(
        isinstance(claimed, str) and len(claimed) == 64,
        f"{label} lacks a valid claimed hash",
    )
    _require(object_hash(unhashed) == claimed, f"{label} self-hash mismatch")
    return claimed


def _read_ledger(path: Path) -> tuple[list[dict[str, Any]], str]:
    count, last_hash = verify_ledger(path)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
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


def _arm_paths(arm_id: str) -> dict[str, Path]:
    return {
        "ready": ROOT / f"manifest.{arm_id}.ready.json",
        "references": ROOT / f"references.{arm_id}.catalog.json",
        "pairing": ROOT / f"pairing-audit.{arm_id}.json",
        "workspace": ROOT / "runs" / arm_id,
        "reference_workspace": ROOT / "stages" / "references" / arm_id,
    }


def _scenario(run: dict[str, Any]) -> str:
    return f"E3.{run['workload']['burst_name']}"


def _verify_tape_catalog() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(TAPES.is_file(), f"missing V98 tape catalog: {TAPES}")
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V98 tapes")
    entries = catalog.get("entries")
    _require(isinstance(entries, dict) and len(entries) == 12, "V98 tape count changed")
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(info.sha256 == entry["sha256"], f"tape hash changed: {key}")
        _require(info.workload_seed in TRAINING_SEEDS, f"unexpected tape seed: {key}")
        evidence.append(
            {
                "key": key,
                "sha256": info.sha256,
                "event_count": info.event_count,
                "dag_order_sha256": info.dag_order_sha256,
                "kind": entry["kind"],
            }
        )
    _require(
        Counter(item["kind"] for item in evidence)
        == Counter({"base_steady": 3, "derived_burst": 9}),
        "V98 tape kind boundary changed",
    )

    capture_ledger = ROOT / "stages/tape_capture/capture_base_tapes/ledger.jsonl"
    rows, last_hash = _read_ledger(capture_ledger)
    _assert_ledger_contract(
        rows, Counter({"capture_canonicalized": 3}), "V98 tape capture"
    )
    _require(
        not list(
            (ROOT / "stages/tape_capture/capture_base_tapes/quarantine").glob(
                "**/attempt-*"
            )
        ),
        "V98 tape capture has quarantined attempts",
    )
    return evidence, {
        "catalog_path": str(TAPES),
        "catalog_file_sha256": file_hash(TAPES),
        "catalog_hash": catalog_hash,
        "capture_ledger_last_hash": last_hash,
    }


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V98 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V98 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V98 plan changed")
    plan = read_json(PLAN)
    _require(plan.get("formal_results_eligible") is False, "V98 eligibility changed")
    _require(PREPARED.is_file(), f"missing V98 prepared receipt: {PREPARED}")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V98 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("previously_reserved_inputs_generated") is False
        and set(prepared.get("training_seeds", [])) == TRAINING_SEEDS
        and prepared.get("untouched_confirmation_seeds") == CONFIRMATION_SEEDS
        and prepared.get("previously_reserved_seeds_untouched")
        == PREVIOUSLY_RESERVED_SEEDS
        and prepared.get("arm_online_runs") == 27
        and prepared.get("arm_reference_builds") == 27,
        "V98 prepared scientific boundary changed",
    )
    tape_evidence, tape_catalog_evidence = _verify_tape_catalog()

    run_evidence: list[dict[str, Any]] = []
    reference_evidence: list[dict[str, Any]] = []
    pairing_evidence: list[dict[str, Any]] = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    paired_inputs: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    ready_manifests: dict[str, dict[str, Any]] = {}

    for arm_id, expected in ARMS.items():
        paths = _arm_paths(arm_id)
        _require(paths["ready"].is_file(), f"missing V98 ready manifest: {arm_id}")
        manifest = load_and_validate_manifest(paths["ready"])
        _require(
            len(manifest["runs"]) == expected["run_count"],
            f"V98 run count changed: {arm_id}",
        )
        _require(
            manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_references_bound") is True,
            f"V98 ready flags changed: {arm_id}",
        )
        ready_manifests[arm_id] = {
            "path": str(paths["ready"]),
            "file_sha256": file_hash(paths["ready"]),
            "manifest_hash": manifest["manifest_hash"],
        }

        _require(paths["references"].is_file(), f"missing references: {arm_id}")
        references = read_json(paths["references"])
        reference_catalog_hash = _assert_hashed_object(
            references, "catalog_hash", f"V98 references {arm_id}"
        )
        entries = references.get("entries")
        declared_keys = {
            item["key"] for item in manifest["reference_build_dependencies"]
        }
        _require(
            isinstance(entries, dict)
            and set(entries) == declared_keys
            and len(entries) == expected["run_count"],
            f"V98 reference key set changed: {arm_id}",
        )
        for key, entry in sorted(entries.items()):
            info = inspect_reference_table(Path(entry["path"]))
            for field in (
                "sha256",
                "bytes",
                "line_count",
                "state_pair_sequence_sha256",
            ):
                _require(
                    getattr(info, field) == entry[field],
                    f"V98 reference {field} changed: {key}",
                )
            _require(
                file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"],
                f"V98 reference receipt changed: {key}",
            )
            _require(
                file_hash(Path(entry["build_process_observation_path"]))
                == entry["build_process_observation_sha256"],
                f"V98 reference process changed: {key}",
            )
            reference_evidence.append(
                {
                    "arm_id": arm_id,
                    "key": key,
                    "sha256": entry["sha256"],
                    "receipt_sha256": entry["receipt_sha256"],
                    "build_spec_hash": entry["build_spec_hash"],
                    "workload_tape_sha256": entry["workload_tape_sha256"],
                    "catalog_hash": reference_catalog_hash,
                }
            )
        reference_ledger = (
            paths["reference_workspace"] / "reference_builds/ledger.jsonl"
        )
        reference_rows, reference_last_hash = _read_ledger(reference_ledger)
        _assert_ledger_contract(
            reference_rows,
            Counter({"reference_build_canonicalized": expected["run_count"]}),
            f"V98 reference {arm_id}",
        )
        _require(
            not list(
                (paths["reference_workspace"] / "reference_builds/quarantine").glob(
                    "**/attempt-*"
                )
            ),
            f"V98 reference quarantine is nonempty: {arm_id}",
        )

        _require(paths["pairing"].is_file(), f"missing pairing audit: {arm_id}")
        pairing = read_json(paths["pairing"])
        _require(
            pairing.get("passed") is True
            and pairing.get("failed_group_count") == 0
            and pairing.get("run_count") == expected["run_count"]
            and pairing.get("group_count") == expected["run_count"],
            f"V98 pairing changed: {arm_id}",
        )
        pairing_evidence.append(
            {
                "arm_id": arm_id,
                "file_sha256": file_hash(paths["pairing"]),
                "run_count": pairing["run_count"],
                "group_count": pairing["group_count"],
                "passed": True,
            }
        )

        workspace = paths["workspace"]
        expected_ids = {run["run_id"] for run in manifest["runs"]}
        actual_ids = {
            path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
        }
        _require(actual_ids == expected_ids, f"V98 canonical set changed: {arm_id}")
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V98 online quarantine is nonempty: {arm_id}",
        )
        ledger_rows, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
        _assert_ledger_contract(
            ledger_rows,
            Counter(
                {
                    "batch_started": 1,
                    "attempt_started": expected["run_count"],
                    "attempt_canonicalized": expected["run_count"],
                    "batch_finished": 1,
                }
            ),
            f"V98 online {arm_id}",
        )

        for run in manifest["runs"]:
            metadata = run.get("metadata", {})
            _require(
                run["experiment_id"] == expected["experiment_id"]
                and run["seed"] in TRAINING_SEEDS
                and run["seed"] not in set(CONFIRMATION_SEEDS)
                and run["seed"] not in set(PREVIOUSLY_RESERVED_SEEDS)
                and metadata.get("v98_arm_id") == arm_id
                and metadata.get("v98_arm_role") == expected["role"]
                and metadata.get("v98_candidate_profile") == expected["profile"]
                and metadata.get("v98_upper_queue_density_threshold")
                == expected["upper_queue_density_threshold"]
                and metadata.get("v98_nonterminal_queue_density_floor")
                == expected["nonterminal_queue_density_floor"]
                and metadata.get("v98_training_seed_metrics_previously_revealed")
                is False
                and metadata.get("v98_confirmation_seeds_opened") is False
                and metadata.get("v98_previously_reserved_seeds_opened") is False,
                f"V98 run boundary changed: {run['run_id']}",
            )
            canonical = workspace / "canonical" / run["run_id"]
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            attempt = read_json(canonical / "attempt.json")
            qc = read_json(canonical / "qc_report.json")
            audit_manifest = read_json(canonical / "manifest.json")
            _require(
                attempt.get("attempt") == 1
                and attempt.get("status") == "qc_pass"
                and attempt.get("classification") == "qc_pass"
                and attempt.get("timed_out") is False
                and attempt.get("exit_code") == 0
                and qc.get("passed") is True
                and qc.get("classification") == "qc_pass",
                f"V98 canonical status changed: {run['run_id']}",
            )
            runtime = {
                "binary_sha256": audit_manifest["adapter_binary"]["verified_sha256"],
                "git_commit": audit_manifest["software_environment"]["git"]["commit"],
                "python_executable_sha256": audit_manifest["software_environment"][
                    "python"
                ]["executable_sha256"],
                "cargo_lock_sha256": audit_manifest["software_environment"][
                    "cargo_lock"
                ]["sha256"],
            }
            for field, value in runtime.items():
                runtime_values[field].add(str(value))
            scenario = _scenario(run)
            paired_inputs[(run["experiment_id"], scenario, run["seed"])].append(
                {
                    "arm_id": arm_id,
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "workload_tape_key": run["workload_tape"]["key"],
                    "workload_spec_hash": run["workload_spec_hash"],
                    "capture_environment_sha256": run["workload_tape"][
                        "capture_environment"
                    ]["capture_environment_sha256"],
                    "common_hpa_hash": run["common_hpa_hash"],
                    "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
                    "simulation": run["simulation"],
                }
            )
            run_evidence.append(
                {
                    "arm_id": arm_id,
                    "run_id": run["run_id"],
                    "experiment_id": run["experiment_id"],
                    "scenario": scenario,
                    "seed": run["seed"],
                    "run_spec_hash": run["run_spec_hash"],
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "reference_key": run["reference_dependency"]["key"],
                    "result_sha256": attempt["result_sha256"],
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "attempt": 1,
                    "classification": "qc_pass",
                    "ledger_last_hash": ledger_last_hash,
                    "reference_ledger_last_hash": reference_last_hash,
                }
            )

    _require(len(run_evidence) == 27, "V98 run evidence count must be 27")
    _require(len(reference_evidence) == 27, "V98 reference evidence count must be 27")
    _require(len(tape_evidence) == 12, "V98 tape evidence count must be 12")
    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V98 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V98 runtime git identity is not singular: {git_commits}",
    )
    for (experiment_id, scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 3,
            f"V98 paired arm count changed: {experiment_id}/{scenario}/{seed}",
        )
        for field in (
            "workload_tape_sha256",
            "workload_tape_key",
            "workload_spec_hash",
            "capture_environment_sha256",
            "common_hpa_hash",
            "sla_artifact_sha256",
            "simulation",
        ):
            _require(
                len({object_hash(row[field]) for row in rows}) == 1,
                f"V98 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V98 common HPA changed: {scenario}/{seed}",
        )

    runtime_identity = {
        **EXPECTED_RUNTIME,
        "git_commit": next(iter(runtime_values["git_commit"])),
    }
    output_payload = {
        "schema_version": "NSE_E3_TERMINAL_LOAD_BAND_BLIND_AUDIT_V98_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "previously_reserved_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "runtime_identity": runtime_identity,
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "previously_reserved_seeds_untouched": PREVIOUSLY_RESERVED_SEEDS,
        "arm_count": len(ARMS),
        "run_count": len(run_evidence),
        "reference_count": len(reference_evidence),
        "tape_count": len(tape_evidence),
        "ready_manifests": ready_manifests,
        "tape_catalog": tape_catalog_evidence,
        "pairing_audits": pairing_evidence,
        "tapes": tape_evidence,
        "references": reference_evidence,
        "runs": run_evidence,
    }
    output_payload["audit_hash"] = object_hash(output_payload)
    write_json_atomic(output, output_payload)
    return output_payload


def main() -> None:
    audit = run_blind_audit()
    print(OUTPUT)
    print(file_hash(OUTPUT))
    print(audit["audit_hash"])


if __name__ == "__main__":
    main()
