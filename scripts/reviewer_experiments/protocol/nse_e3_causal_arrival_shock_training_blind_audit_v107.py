from __future__ import annotations

import gzip
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
from scripts.reviewer_experiments.protocol.nse_e3_causal_arrival_shock_training_prepare_v107 import (
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
    SHOCK_THRESHOLDS,
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


PREPARED = ROOT / "prepared-manifests-v107.json"
TAPES = ROOT / "tapes.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v107-training.json"
RESULT = ROOT / "training-result-v107.json"
CANONICAL_RENAME_RECEIPT = "canonical_rename_receipt_v107.json"
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
        "shock_rate_ratio": shock_rate_ratio,
        "shock_threshold_numerator": (
            SHOCK_THRESHOLDS[shock_rate_ratio][0]
            if shock_rate_ratio is not None
            else None
        ),
        "shock_threshold_denominator": (
            SHOCK_THRESHOLDS[shock_rate_ratio][1]
            if shock_rate_ratio is not None
            else None
        ),
        "arrival_history_baseline_frames": 80 if role == "candidate" else None,
        "arrival_history_recent_frames": 20 if role == "candidate" else None,
        "arrival_min_requests_per_window": 20 if role == "candidate" else None,
        "shock_activation_horizon_frames": 100 if role == "candidate" else None,
        "nonterminal_queue_density_floor": 8.0 if role == "candidate" else None,
        "warm_admissibility": (
            "preserve_anchor_warmness" if role == "candidate" else None
        ),
        "load_least_window_certificate_mode": (
            "disabled" if role == "candidate" else "not_applicable"
        ),
        "arrival_signal": "first_seen_request_ids_only"
        if role == "candidate"
        else "not_applicable",
        "cpu_memory_individual_noninferiority": role == "candidate",
        "resource_bottleneck_sum_noninferiority": False,
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
    for arm_id, experiment_id, role, profile, shock_rate_ratio, count in PREPARED_ARMS
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


def _validate_causal_arrival_shock_diagnostics(
    run: dict[str, Any], canonical: Path, expected: dict[str, Any]
) -> dict[str, Any]:
    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V107 Nash diagnostics: {run['run_id']}")
    candidate = expected["role"] == "candidate"
    window_count = 0
    active_window_count = 0
    threshold_met_window_count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            window_count += 1
            frame = event.get("frame")
            gate = (
                event.get("decision", {})
                .get("load_least_dominance_gate", {})
                .get("causal_arrival_shock")
            )
            _require(
                isinstance(gate, dict),
                f"missing V107 causal diagnostics: {run['run_id']}:{line_number}",
            )
            _require(
                gate.get("gate_enabled") is candidate
                and gate.get("baseline_frames") == 80
                and gate.get("recent_frames") == 20
                and gate.get("min_requests_per_window") == 20
                and gate.get("threshold_numerator")
                == expected["shock_threshold_numerator"]
                and gate.get("threshold_denominator")
                == expected["shock_threshold_denominator"]
                and gate.get("active_frames") == 100
                and gate.get("uses_first_seen_request_ids_only") is True,
                f"V107 causal diagnostic contract changed: {run['run_id']}:{line_number}",
            )
            for field in (
                "first_seen_current_frame",
                "baseline_count",
                "recent_count",
            ):
                value = gate.get(field)
                _require(
                    type(value) is int and value >= 0,
                    f"V107 causal diagnostic {field} changed: "
                    f"{run['run_id']}:{line_number}",
                )
            _require(
                type(frame) is int
                and type(gate.get("history_complete")) is bool
                and type(gate.get("active")) is bool,
                f"V107 causal diagnostic types changed: {run['run_id']}:{line_number}",
            )
            until_frame = gate.get("until_frame")
            _require(
                until_frame is None or (type(until_frame) is int and until_frame >= 0),
                f"V107 causal activation horizon changed: {run['run_id']}:{line_number}",
            )
            _require(
                gate["active"] is (until_frame is not None and frame <= until_frame),
                f"V107 causal active flag changed: {run['run_id']}:{line_number}",
            )
            if not candidate:
                _require(
                    gate["history_complete"] is False
                    and gate["baseline_count"] == 0
                    and gate["recent_count"] == 0
                    and gate["active"] is False
                    and until_frame is None,
                    f"V107 anchor unexpectedly used causal state: "
                    f"{run['run_id']}:{line_number}",
                )
                continue
            if not gate["history_complete"]:
                _require(
                    gate["baseline_count"] == 0 and gate["recent_count"] == 0,
                    f"V107 incomplete causal history leaked counts: "
                    f"{run['run_id']}:{line_number}",
                )
                continue
            sufficient = (
                gate["baseline_count"] >= gate["min_requests_per_window"]
                and gate["recent_count"] >= gate["min_requests_per_window"]
            )
            recent_scaled = (
                gate["recent_count"]
                * gate["baseline_frames"]
                * gate["threshold_denominator"]
            )
            baseline_scaled = (
                gate["baseline_count"]
                * gate["recent_frames"]
                * gate["threshold_numerator"]
            )
            if sufficient and recent_scaled >= baseline_scaled:
                threshold_met_window_count += 1
                _require(
                    gate["active"] is True and until_frame >= frame + 99,
                    f"V107 exact causal threshold did not activate: "
                    f"{run['run_id']}:{line_number}",
                )
            active_window_count += int(gate["active"])
    _require(
        window_count == run["simulation"]["total_frame"],
        f"V107 diagnostic window count changed: {run['run_id']}",
    )
    if candidate:
        _require(
            threshold_met_window_count > 0 and active_window_count > 0,
            f"V107 causal gate never activated: {run['run_id']}",
        )
    return {
        "file_sha256": file_hash(path),
        "window_count": window_count,
        "active_window_count": active_window_count,
        "threshold_met_window_count": threshold_met_window_count,
        "performance_fields_consulted": False,
    }


def _verify_tape_catalog() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(TAPES.is_file(), f"missing V107 tape catalog: {TAPES}")
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V107 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12,
        "V107 tape count changed",
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
        "V107 tape kind boundary changed",
    )
    base_entries = {
        key: entry for key, entry in entries.items() if entry["kind"] == "base_steady"
    }
    capture_root = _stage_root_from_receipts(
        base_entries, "capture_receipt_path", 3, "V107 tape capture"
    )
    rows, last_hash = _read_ledger(capture_root / "ledger.jsonl")
    _assert_ledger_contract(
        rows, Counter({"capture_canonicalized": 3}), "V107 tape capture"
    )
    _require(
        not list((capture_root / "quarantine").glob("**/attempt-*")),
        "V107 tape capture has quarantined attempts",
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
            f"V107 reference {arm_id}",
        )
        arm_roots[arm_id] = root
        expected_by_root[root] += expected["run_count"]
    last_hash_by_root: dict[Path, str] = {}
    for root, expected_count in expected_by_root.items():
        rows, last_hash = _read_ledger(root / "ledger.jsonl")
        _assert_ledger_contract(
            rows,
            Counter({"reference_build_canonicalized": expected_count}),
            f"V107 reference stage {root}",
        )
        _require(
            not list((root / "quarantine").glob("**/attempt-*")),
            f"V107 reference quarantine is nonempty: {root}",
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

    _require(receipt_path.is_file(), "missing V107 canonical rename receipt")
    receipt = read_json(receipt_path)
    receipt_hash = _assert_hashed_object(
        receipt, "receipt_hash", "V107 canonical rename receipt"
    )
    run_id = receipt.get("run_id")
    runs = {run["run_id"]: run for run in manifest["runs"]}
    _require(
        receipt.get("schema_version") == "NSE_V107_CANONICAL_RENAME_RECEIPT_V1"
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
        "V107 canonical rename boundary changed",
    )
    canonical_root = paths["workspace"] / "canonical"
    source = canonical_root / receipt["source_name"]
    target = canonical_root / run_id
    _require(
        not source.exists() and target.is_dir(),
        "V107 canonical rename filesystem state changed",
    )
    declared_files = receipt.get("files_before_after")
    _require(
        isinstance(declared_files, list)
        and receipt.get("content_file_count") == len(declared_files),
        "V107 canonical rename file inventory malformed",
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
        "V107 canonical rename content tree changed",
    )
    _require(
        receipt.get("result_sha256")
        == file_hash(target / "reviewer_records" / run_id / "summary.json")
        and receipt.get("audit_manifest_sha256") == file_hash(target / "manifest.json"),
        "V107 canonical rename terminal hashes changed",
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
    _require(not output.exists(), f"V107 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V107 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V107 plan changed")
    plan = read_json(PLAN)
    _require(plan.get("formal_results_eligible") is False, "V107 eligibility changed")
    _require(PREPARED.is_file(), f"missing V107 prepared receipt: {PREPARED}")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V107 prepared receipt"
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
        "V107 prepared scientific boundary changed",
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
        _require(paths["ready"].is_file(), f"missing V107 ready manifest: {arm_id}")
        manifest = load_and_validate_manifest(paths["ready"])
        _require(
            len(manifest["runs"]) == expected["run_count"],
            f"V107 run count changed: {arm_id}",
        )
        _require(
            manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_references_bound") is True,
            f"V107 ready flags changed: {arm_id}",
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
            references, "catalog_hash", f"V107 references {arm_id}"
        )
        entries = references.get("entries")
        declared_keys = {
            item["key"] for item in manifest["reference_build_dependencies"]
        }
        _require(
            isinstance(entries, dict)
            and set(entries) == declared_keys
            and len(entries) == expected["run_count"],
            f"V107 reference key set changed: {arm_id}",
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
                    f"V107 reference {field} changed: {key}",
                )
            _require(
                file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"],
                f"V107 reference receipt changed: {key}",
            )
            _require(
                file_hash(Path(entry["build_process_observation_path"]))
                == entry["build_process_observation_sha256"],
                f"V107 reference process changed: {key}",
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
            f"V107 pairing changed: {arm_id}",
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
        _require(actual_ids == expected_ids, f"V107 canonical set changed: {arm_id}")
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V107 online quarantine is nonempty: {arm_id}",
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
            f"V107 online {arm_id}",
        )

        for run in manifest["runs"]:
            metadata = run.get("metadata", {})
            _require(
                run["experiment_id"] == expected["experiment_id"]
                and run["seed"] in TRAINING_SEEDS
                and run["seed"] not in set(CONFIRMATION_SEEDS)
                and run["seed"] not in set(PREVIOUS_CONFIRMATION_SEEDS)
                and run["seed"] not in set(OTHER_UNOPENED_SEEDS)
                and metadata.get("v107_arm_id") == arm_id
                and metadata.get("v107_arm_role") == expected["role"]
                and metadata.get("v107_candidate_profile") == expected["profile"]
                and metadata.get("v107_shock_rate_ratio")
                == expected["shock_rate_ratio"]
                and metadata.get("v107_shock_threshold_numerator")
                == expected["shock_threshold_numerator"]
                and metadata.get("v107_shock_threshold_denominator")
                == expected["shock_threshold_denominator"]
                and metadata.get("v107_arrival_history_baseline_frames")
                == expected["arrival_history_baseline_frames"]
                and metadata.get("v107_arrival_history_recent_frames")
                == expected["arrival_history_recent_frames"]
                and metadata.get("v107_arrival_min_requests_per_window")
                == expected["arrival_min_requests_per_window"]
                and metadata.get("v107_shock_activation_horizon_frames")
                == expected["shock_activation_horizon_frames"]
                and metadata.get(
                    "v107_static_upper_density_gate_bypassed_only_while_shock_active"
                )
                is (expected["role"] == "candidate")
                and metadata.get("v107_nonterminal_queue_density_floor")
                == expected["nonterminal_queue_density_floor"]
                and metadata.get("v107_warm_admissibility")
                == expected["warm_admissibility"]
                and metadata.get("v107_load_least_window_certificate_mode")
                == expected["load_least_window_certificate_mode"]
                and metadata.get("v107_arrival_signal") == expected["arrival_signal"]
                and metadata.get("v107_cpu_memory_individual_noninferiority")
                is expected["cpu_memory_individual_noninferiority"]
                and metadata.get("v107_resource_bottleneck_sum_noninferiority")
                is expected["resource_bottleneck_sum_noninferiority"]
                and metadata.get("v107_resource_inputs_finite_fail_closed")
                is (expected["role"] == "candidate")
                and metadata.get("v107_scalar_faasrank_noninferiority")
                is (expected["role"] == "candidate")
                and metadata.get("v107_input_locality_component_noninferiority")
                is (expected["role"] == "candidate")
                and metadata.get("v107_componentwise_faasrank_noninferiority") is False
                and metadata.get(
                    "v107_per_child_current_warm_downstream_locality_noninferiority"
                )
                is (expected["role"] == "candidate")
                and metadata.get(
                    "v107_downstream_locality_aggregate_compensation_allowed"
                )
                is False
                and metadata.get("v107_future_child_placement_or_feasibility_used")
                is False
                and metadata.get("v107_critical_frontier_protection")
                is expected["critical_frontier_protection"]
                and metadata.get("v107_critical_frontier_rank_source")
                == expected["critical_frontier_rank_source"]
                and metadata.get("v107_critical_frontier_tie_rule")
                == expected["critical_frontier_tie_rule"]
                and metadata.get(
                    "v107_only_strictly_lower_rank_parallel_players_may_substitute"
                )
                is expected["critical_frontier_protection"]
                and metadata.get("v107_outcome_fields_drive_policy") is False
                and metadata.get("v107_scenario_or_burst_label_used_by_policy") is False
                and metadata.get("v107_completion_or_performance_fields_used_by_policy")
                is False
                and metadata.get("v107_future_arrivals_used_by_policy") is False
                and metadata.get("v107_training_seed_metrics_previously_revealed")
                is False
                and metadata.get("v107_confirmation_seeds_opened") is False
                and metadata.get("v107_other_unopened_seeds_opened") is False,
                f"V107 run boundary changed: {run['run_id']}",
            )
            canonical = workspace / "canonical" / run["run_id"]
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            causal_diagnostics = _validate_causal_arrival_shock_diagnostics(
                run, canonical, expected
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
                f"V107 canonical status changed: {run['run_id']}",
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
                    "causal_arrival_shock_diagnostics": causal_diagnostics,
                    "ledger_last_hash": ledger_last_hash,
                    "reference_ledger_last_hash": reference_last_hash,
                }
            )

    _require(len(run_evidence) == 27, "V107 run evidence count must be 27")
    _require(len(reference_evidence) == 27, "V107 reference evidence count must be 27")
    _require(len(tape_evidence) == 12, "V107 tape evidence count must be 12")
    _require(
        len(canonical_rename_receipts) <= len(ARMS),
        "V107 canonical rename receipt count exceeds arm count",
    )
    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V107 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V107 runtime git identity is not singular: {git_commits}",
    )
    for (experiment_id, scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 3,
            f"V107 paired arm count changed: {experiment_id}/{scenario}/{seed}",
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
                f"V107 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V107 common HPA changed: {scenario}/{seed}",
        )

    output_payload = {
        "schema_version": "NSE_E3_CAUSAL_ARRIVAL_SHOCK_BLIND_AUDIT_V107_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "mechanism_diagnostic_windows_parsed": sum(
            run["causal_arrival_shock_diagnostics"]["window_count"]
            for run in run_evidence
        ),
        "mechanism_diagnostics_consulted_for_performance_selection": False,
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
