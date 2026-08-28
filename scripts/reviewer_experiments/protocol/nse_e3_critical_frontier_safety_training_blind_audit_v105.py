from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_blind_audit_v100 import (
    _assert_hashed_object,
    _assert_ledger_contract,
    _read_ledger,
    _require,
    _stage_root_from_receipts,
)
from scripts.reviewer_experiments.protocol.nse_e3_critical_frontier_safety_training_prepare_v105 import (
    ARMS as PREPARED_ARMS,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    CONFIRMATION_SEEDS,
    OTHER_UNOPENED_SEEDS,
    PREVIOUS_CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
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


PREPARED = ROOT / "prepared-manifests-v105.json"
TAPES = ROOT / "tapes.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v105-training.json"
RESULT = ROOT / "training-result-v105.json"
CANONICAL_RENAME_RECEIPT = "canonical_rename_receipt_v105.json"
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
        "upper_queue_density_threshold": upper_density,
        "nonterminal_queue_density_floor": 8.0 if role == "candidate" else None,
        "warm_admissibility": (
            "preserve_anchor_warmness" if role == "candidate" else None
        ),
        "load_least_window_certificate_mode": (
            "disabled" if role == "candidate" else "not_applicable"
        ),
        "component_safety_mode": component_safety_mode,
        "critical_frontier_protection": role == "candidate",
        "critical_frontier_rank_source": (
            "immutable_srpt_remaining_critical_path_rank"
            if role == "candidate"
            else "not_applicable"
        ),
        "critical_frontier_tie_rule": (
            "protect_missing_nonfinite_singleton_or_rank_plus_epsilon_ge_request_frontier_maximum"
            if role == "candidate"
            else "not_applicable"
        ),
        "run_count": count,
    }
    for arm_id, experiment_id, role, profile, upper_density, component_safety_mode, count in PREPARED_ARMS
}


def _arm_paths(arm_id: str) -> dict[str, Path]:
    workspace = ROOT / "runs" / arm_id
    return {
        "ready": ROOT / f"manifest.{arm_id}.ready.json",
        "references": ROOT / f"references.{arm_id}.catalog.json",
        "pairing": ROOT / f"pairing-audit.{arm_id}.json",
        "workspace": workspace,
        "rename_receipt": workspace / CANONICAL_RENAME_RECEIPT,
    }


def _scenario(run: dict[str, Any]) -> str:
    return f"E3.{run['workload']['burst_name']}"


def _verify_tape_catalog() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(TAPES.is_file(), f"missing V105 tape catalog: {TAPES}")
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V105 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12,
        "V105 tape count changed",
    )
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
        "V105 tape kind boundary changed",
    )
    base_entries = {
        key: entry for key, entry in entries.items() if entry["kind"] == "base_steady"
    }
    capture_root = _stage_root_from_receipts(
        base_entries, "capture_receipt_path", 3, "V105 tape capture"
    )
    rows, last_hash = _read_ledger(capture_root / "ledger.jsonl")
    _assert_ledger_contract(
        rows, Counter({"capture_canonicalized": 3}), "V105 tape capture"
    )
    _require(
        not list((capture_root / "quarantine").glob("**/attempt-*")),
        "V105 tape capture has quarantined attempts",
    )
    return evidence, {
        "catalog_path": str(TAPES),
        "catalog_file_sha256": file_hash(TAPES),
        "catalog_hash": catalog_hash,
        "capture_stage_root": str(capture_root),
        "capture_ledger_last_hash": last_hash,
    }


def _verify_reference_stage_ledgers() -> tuple[dict[str, Path], dict[Path, str]]:
    arm_roots: dict[str, Path] = {}
    expected_by_root: Counter[Path] = Counter()
    for arm_id, expected in ARMS.items():
        catalog_path = ROOT / f"references.{arm_id}.catalog.json"
        _require(catalog_path.is_file(), f"missing reference catalog: {arm_id}")
        entries = read_json(catalog_path).get("entries")
        _require(isinstance(entries, dict), f"reference catalog malformed: {arm_id}")
        root = _stage_root_from_receipts(
            entries,
            "receipt_path",
            expected["run_count"],
            f"V105 reference {arm_id}",
        )
        arm_roots[arm_id] = root
        expected_by_root[root] += expected["run_count"]
    last_hash_by_root: dict[Path, str] = {}
    for root, expected_count in expected_by_root.items():
        rows, last_hash = _read_ledger(root / "ledger.jsonl")
        _assert_ledger_contract(
            rows,
            Counter({"reference_build_canonicalized": expected_count}),
            f"V105 reference stage {root}",
        )
        _require(
            not list((root / "quarantine").glob("**/attempt-*")),
            f"V105 reference quarantine is nonempty: {root}",
        )
        last_hash_by_root[root] = last_hash
    return arm_roots, last_hash_by_root


def _verify_canonical_rename_receipt(
    arm_id: str,
    paths: dict[str, Path],
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    receipt_path = paths["rename_receipt"]
    if not receipt_path.exists():
        return None

    _require(receipt_path.is_file(), "missing V105 canonical rename receipt")
    receipt = read_json(receipt_path)
    receipt_hash = _assert_hashed_object(
        receipt, "receipt_hash", "V105 canonical rename receipt"
    )
    run_id = receipt.get("run_id")
    runs = {run["run_id"]: run for run in manifest["runs"]}
    _require(
        receipt.get("schema_version") == "NSE_V105_CANONICAL_RENAME_RECEIPT_V1"
        and receipt.get("performance_metrics_consulted") is False
        and receipt.get("scientific_run_reexecuted") is False
        and receipt.get("file_content_modified") is False
        and receipt.get("arm_id") == arm_id
        and receipt.get("operation") == "same_parent_os_replace_directory_only"
        and isinstance(run_id, str)
        and run_id in runs
        and receipt.get("run_spec_hash") == runs[run_id]["run_spec_hash"]
        and receipt.get("target_name") == run_id
        and isinstance(receipt.get("source_name"), str)
        and receipt["source_name"].startswith("attempt-01")
        and receipt.get("ready_manifest_file_sha256") == file_hash(paths["ready"])
        and receipt.get("ready_manifest_hash") == manifest["manifest_hash"]
        and receipt.get("ledger_file_sha256_before_after")
        == file_hash(paths["workspace"] / "ledger.jsonl"),
        "V105 canonical rename boundary changed",
    )
    canonical_root = paths["workspace"] / "canonical"
    source = canonical_root / receipt["source_name"]
    target = canonical_root / run_id
    _require(
        not source.exists() and target.is_dir(),
        "V105 canonical rename filesystem state changed",
    )
    declared_files = receipt.get("files_before_after")
    _require(
        isinstance(declared_files, list)
        and receipt.get("content_file_count") == len(declared_files),
        "V105 canonical rename file inventory malformed",
    )
    expected_files = {
        item["path"]: (item["bytes"], item["sha256"])
        for item in declared_files
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and isinstance(item.get("bytes"), int)
        and isinstance(item.get("sha256"), str)
    }
    actual_files = {
        str(path.relative_to(target)).replace("\\", "/"): (
            path.stat().st_size,
            file_hash(path),
        )
        for path in target.rglob("*")
        if path.is_file()
    }
    _require(
        len(expected_files) == len(declared_files) and actual_files == expected_files,
        "V105 canonical rename content tree changed",
    )
    _require(
        receipt.get("result_sha256")
        == file_hash(target / "reviewer_records" / run_id / "summary.json")
        and receipt.get("audit_manifest_sha256") == file_hash(target / "manifest.json"),
        "V105 canonical rename terminal hashes changed",
    )
    return {
        "arm_id": arm_id,
        "run_id": run_id,
        "path": str(receipt_path),
        "file_sha256": file_hash(receipt_path),
        "receipt_hash": receipt_hash,
        "content_file_count": len(actual_files),
        "scientific_run_reexecuted": False,
        "file_content_modified": False,
        "performance_metrics_consulted": False,
    }


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V105 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V105 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V105 plan changed")
    plan = read_json(PLAN)
    _require(plan.get("formal_results_eligible") is False, "V105 eligibility changed")
    _require(PREPARED.is_file(), f"missing V105 prepared receipt: {PREPARED}")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V105 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("other_unopened_inputs_generated") is False
        and set(prepared.get("training_seeds", [])) == TRAINING_SEEDS
        and prepared.get("untouched_confirmation_seeds") == CONFIRMATION_SEEDS
        and prepared.get("previous_confirmation_seeds_remaining_sealed")
        == PREVIOUS_CONFIRMATION_SEEDS
        and prepared.get("other_unopened_seeds_untouched") == OTHER_UNOPENED_SEEDS
        and prepared.get("arm_online_runs") == 27
        and prepared.get("arm_reference_builds") == 27,
        "V105 prepared scientific boundary changed",
    )
    tape_evidence, tape_catalog_evidence = _verify_tape_catalog()
    reference_stage_roots, reference_ledger_hashes = _verify_reference_stage_ledgers()

    run_evidence: list[dict[str, Any]] = []
    reference_evidence: list[dict[str, Any]] = []
    pairing_evidence: list[dict[str, Any]] = []
    canonical_rename_receipts: list[dict[str, Any]] = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    paired_inputs: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    ready_manifests: dict[str, dict[str, Any]] = {}

    for arm_id, expected in ARMS.items():
        paths = _arm_paths(arm_id)
        _require(paths["ready"].is_file(), f"missing V105 ready manifest: {arm_id}")
        manifest = load_and_validate_manifest(paths["ready"])
        _require(
            len(manifest["runs"]) == expected["run_count"],
            f"V105 run count changed: {arm_id}",
        )
        _require(
            manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_references_bound") is True,
            f"V105 ready flags changed: {arm_id}",
        )
        ready_manifests[arm_id] = {
            "path": str(paths["ready"]),
            "file_sha256": file_hash(paths["ready"]),
            "manifest_hash": manifest["manifest_hash"],
        }
        rename_receipt = _verify_canonical_rename_receipt(arm_id, paths, manifest)
        if rename_receipt is not None:
            canonical_rename_receipts.append(rename_receipt)

        _require(paths["references"].is_file(), f"missing references: {arm_id}")
        references = read_json(paths["references"])
        reference_catalog_hash = _assert_hashed_object(
            references, "catalog_hash", f"V105 references {arm_id}"
        )
        entries = references.get("entries")
        declared_keys = {
            item["key"] for item in manifest["reference_build_dependencies"]
        }
        _require(
            isinstance(entries, dict)
            and set(entries) == declared_keys
            and len(entries) == expected["run_count"],
            f"V105 reference key set changed: {arm_id}",
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
                    f"V105 reference {field} changed: {key}",
                )
            _require(
                file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"],
                f"V105 reference receipt changed: {key}",
            )
            _require(
                file_hash(Path(entry["build_process_observation_path"]))
                == entry["build_process_observation_sha256"],
                f"V105 reference process changed: {key}",
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
        reference_last_hash = reference_ledger_hashes[reference_stage_roots[arm_id]]

        _require(paths["pairing"].is_file(), f"missing pairing audit: {arm_id}")
        pairing = read_json(paths["pairing"])
        _require(
            pairing.get("passed") is True
            and pairing.get("failed_group_count") == 0
            and pairing.get("run_count") == expected["run_count"]
            and pairing.get("group_count") == expected["run_count"],
            f"V105 pairing changed: {arm_id}",
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
        _require(actual_ids == expected_ids, f"V105 canonical set changed: {arm_id}")
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V105 online quarantine is nonempty: {arm_id}",
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
            f"V105 online {arm_id}",
        )

        for run in manifest["runs"]:
            metadata = run.get("metadata", {})
            _require(
                run["experiment_id"] == expected["experiment_id"]
                and run["seed"] in TRAINING_SEEDS
                and run["seed"] not in set(CONFIRMATION_SEEDS)
                and run["seed"] not in set(PREVIOUS_CONFIRMATION_SEEDS)
                and run["seed"] not in set(OTHER_UNOPENED_SEEDS)
                and metadata.get("v105_arm_id") == arm_id
                and metadata.get("v105_arm_role") == expected["role"]
                and metadata.get("v105_candidate_profile") == expected["profile"]
                and metadata.get("v105_upper_queue_density_threshold")
                == expected["upper_queue_density_threshold"]
                and metadata.get("v105_nonterminal_queue_density_floor")
                == expected["nonterminal_queue_density_floor"]
                and metadata.get("v105_warm_admissibility")
                == expected["warm_admissibility"]
                and metadata.get("v105_load_least_window_certificate_mode")
                == expected["load_least_window_certificate_mode"]
                and metadata.get("v105_component_safety_mode")
                == expected["component_safety_mode"]
                and metadata.get("v105_scalar_faasrank_noninferiority")
                is (expected["role"] == "candidate")
                and metadata.get("v105_input_locality_component_noninferiority")
                is (expected["role"] == "candidate")
                and metadata.get("v105_componentwise_faasrank_noninferiority")
                is expected["component_safety_mode"].startswith("componentwise_")
                and metadata.get(
                    "v105_per_child_current_warm_downstream_locality_noninferiority"
                )
                is (expected["role"] == "candidate")
                and metadata.get(
                    "v105_downstream_locality_aggregate_compensation_allowed"
                )
                is False
                and metadata.get("v105_future_child_placement_or_feasibility_used")
                is False
                and metadata.get("v105_critical_frontier_protection")
                is expected["critical_frontier_protection"]
                and metadata.get("v105_critical_frontier_rank_source")
                == expected["critical_frontier_rank_source"]
                and metadata.get("v105_critical_frontier_tie_rule")
                == expected["critical_frontier_tie_rule"]
                and metadata.get(
                    "v105_only_strictly_lower_rank_parallel_players_may_substitute"
                )
                is expected["critical_frontier_protection"]
                and metadata.get("v105_outcome_fields_drive_policy") is False
                and metadata.get("v105_training_seed_metrics_previously_revealed")
                is False
                and metadata.get("v105_confirmation_seeds_opened") is False
                and metadata.get("v105_other_unopened_seeds_opened") is False,
                f"V105 run boundary changed: {run['run_id']}",
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
                f"V105 canonical status changed: {run['run_id']}",
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

    _require(len(run_evidence) == 27, "V105 run evidence count must be 27")
    _require(len(reference_evidence) == 27, "V105 reference evidence count must be 27")
    _require(len(tape_evidence) == 12, "V105 tape evidence count must be 12")
    _require(
        len(canonical_rename_receipts) <= len(ARMS),
        "V105 canonical rename receipt count exceeds arm count",
    )
    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V105 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V105 runtime git identity is not singular: {git_commits}",
    )
    for (experiment_id, scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 3,
            f"V105 paired arm count changed: {experiment_id}/{scenario}/{seed}",
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
                f"V105 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V105 common HPA changed: {scenario}/{seed}",
        )

    output_payload = {
        "schema_version": "NSE_E3_CRITICAL_FRONTIER_SAFETY_BLIND_AUDIT_V105_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "other_unopened_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "runtime_identity": {
            **EXPECTED_RUNTIME,
            "git_commit": next(iter(runtime_values["git_commit"])),
        },
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "previous_confirmation_seeds_remaining_sealed": PREVIOUS_CONFIRMATION_SEEDS,
        "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
        "arm_count": len(ARMS),
        "run_count": len(run_evidence),
        "reference_count": len(reference_evidence),
        "tape_count": len(tape_evidence),
        "ready_manifests": ready_manifests,
        "tape_catalog": tape_catalog_evidence,
        "pairing_audits": pairing_evidence,
        "canonical_rename_receipts": canonical_rename_receipts,
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
