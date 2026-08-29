from __future__ import annotations

import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_blind_audit_v100 import (
    _assert_hashed_object,
    _read_ledger,
    _require,
    _stage_root_from_receipts,
)
from scripts.reviewer_experiments.protocol.nse_e3_native_frontier_anchor_training_execute_v137 import (
    EXECUTION_RECEIPT,
    READY_SCHEDULE,
    ready_manifest_path,
    workspace_path,
)
from scripts.reviewer_experiments.protocol.nse_e3_native_frontier_anchor_training_prepare_v137 import (
    ARMS as PREPARED_ARMS,
    ARM_IDS,
    BASELINE_METHODS,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    METHOD_LABELS,
    NEW_CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUS_CONFIRMATION_SEEDS,
    PYTHON_SHA256,
    ROOT,
    SCENARIOS,
    TRAINING_SEED_LIST,
    TRAINING_SEEDS,
    paths,
    scenario_id,
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


PREPARED = ROOT / "prepared-manifests-v137.json"
TAPES = ROOT / "tapes.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v137-training.json"
RESULT = ROOT / "training-result-v137.json"
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
ARMS = {
    arm_id: {"profile": profile, "native_kind": native_kind, "run_count": 9}
    for arm_id, profile, native_kind in PREPARED_ARMS
}


def pairing_path(root: Path, manifest_id: str) -> Path:
    return root / f"pairing-audit.{manifest_id}.json"


def reference_catalog_path(root: Path, arm_id: str) -> Path:
    return root / f"references.{arm_id}.catalog.json"


def _finite(value: Any) -> bool:
    return (
        type(value) in (int, float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _verify_tapes() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(TAPES.is_file(), f"missing V137 tape catalog: {TAPES}")
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V137 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12, "V137 tape count changed"
    )
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(info.sha256 == entry["sha256"], f"V137 tape hash changed: {key}")
        _require(info.workload_seed in TRAINING_SEEDS, f"V137 tape seed changed: {key}")
        evidence.append(
            {
                "key": key,
                "sha256": info.sha256,
                "event_count": info.event_count,
                "dag_order_sha256": info.dag_order_sha256,
                "workload_seed": info.workload_seed,
                "kind": entry["kind"],
            }
        )
    _require(
        Counter(item["kind"] for item in evidence)
        == Counter({"base_steady": 3, "derived_burst": 9}),
        "V137 tape kinds changed",
    )
    _require(
        Counter(item["workload_seed"] for item in evidence)
        == Counter({seed: 4 for seed in TRAINING_SEEDS}),
        "V137 tape seed product changed",
    )
    base = {
        key: value for key, value in entries.items() if value["kind"] == "base_steady"
    }
    capture_root = _stage_root_from_receipts(
        base, "capture_receipt_path", 3, "V137 tape capture"
    )
    rows, last_hash = _read_ledger(capture_root / "ledger.jsonl")
    counts = Counter(row["event"] for row in rows)
    _require(
        counts == Counter({"capture_canonicalized": 3}),
        f"V137 capture ledger changed: {counts}",
    )
    _require(
        not list((capture_root / "quarantine").glob("**/attempt-*")),
        "V137 tape capture quarantine is nonempty",
    )
    return evidence, {
        "catalog_path": str(TAPES),
        "catalog_file_sha256": file_hash(TAPES),
        "catalog_hash": catalog_hash,
        "capture_stage_root": str(capture_root),
        "capture_ledger_last_hash": last_hash,
    }


def _verify_references() -> tuple[list[dict[str, Any]], dict[str, str]]:
    evidence = []
    ledger_hashes = {}
    for arm_id in ARM_IDS:
        path = reference_catalog_path(ROOT, arm_id)
        _require(path.is_file(), f"missing V137 reference catalog: {arm_id}")
        catalog = read_json(path)
        catalog_hash = _assert_hashed_object(
            catalog, "catalog_hash", f"V137 references {arm_id}"
        )
        entries = catalog.get("entries")
        _require(
            isinstance(entries, dict) and len(entries) == 9,
            f"V137 reference count changed: {arm_id}",
        )
        root = _stage_root_from_receipts(
            entries, "receipt_path", 9, f"V137 references {arm_id}"
        )
        rows, last_hash = _read_ledger(root / "ledger.jsonl")
        counts = Counter(row["event"] for row in rows)
        _require(
            counts == Counter({"reference_build_canonicalized": 9}),
            f"V137 reference ledger changed: {arm_id}/{counts}",
        )
        _require(
            not list((root / "quarantine").glob("**/attempt-*")),
            f"V137 reference quarantine is nonempty: {arm_id}",
        )
        ledger_hashes[arm_id] = last_hash
        for key, entry in sorted(entries.items()):
            info = inspect_reference_table(Path(entry["path"]))
            _require(
                all(
                    getattr(info, field) == entry[field]
                    for field in (
                        "sha256",
                        "bytes",
                        "line_count",
                        "state_pair_sequence_sha256",
                    )
                )
                and file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"]
                and file_hash(Path(entry["build_process_observation_path"]))
                == entry["build_process_observation_sha256"],
                f"V137 reference evidence changed: {key}",
            )
            evidence.append(
                {
                    "arm_id": arm_id,
                    "key": key,
                    "sha256": entry["sha256"],
                    "receipt_sha256": entry["receipt_sha256"],
                    "build_spec_hash": entry["build_spec_hash"],
                    "workload_tape_sha256": entry["workload_tape_sha256"],
                    "catalog_hash": catalog_hash,
                }
            )
    _require(len(evidence) == 27, "V137 reference evidence count changed")
    return evidence, ledger_hashes


def _validate_native_diagnostics(
    run: dict[str, Any], canonical: Path, native_kind: str
) -> dict[str, Any]:
    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V137 Nash diagnostics: {run['run_id']}")
    counts = Counter()
    reasons = Counter()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            counts["windows"] += 1
            decision = event.get("decision")
            _require(isinstance(decision, dict), "missing V137 decision diagnostics")
            native = decision.get("native_shadow_anchor")
            _require(isinstance(native, dict), "missing V137 native shadow diagnostics")
            players = decision.get("request_function_players")
            _require(
                type(players) is int and players >= 0,
                f"invalid V137 player count: {run['run_id']}:{line_number}",
            )
            if players > 0:
                counts["player_windows"] += 1
                _require(
                    native.get("kind") == native_kind
                    and native.get("valid") is True
                    and native.get("commands") == players
                    and native.get("duplicate_commands") == 0
                    and native.get("unexpected_messages") == 0
                    and native.get("missing_players") == 0
                    and native.get("extra_players") == 0
                    and native.get("infeasible_commands") == 0
                    and type(native.get("anchor_assignment_hash")) is int
                    and type(native.get("ordered_command_hash")) is int,
                    f"V137 native anchor mismatch: {run['run_id']}:{line_number}",
                )
            _require(
                native.get("certificate_uses_completion_outcomes") is False,
                f"V137 native certificate consulted outcomes: {run['run_id']}",
            )
            initializer_players = native.get("initializer_readiness_service_players")
            proposal_players = native.get("proposal_readiness_service_players")
            _require(
                type(initializer_players) is int
                and initializer_players >= 0
                and initializer_players == proposal_players,
                f"V137 native service cohort mismatch: {run['run_id']}:{line_number}",
            )
            if initializer_players > 0:
                counts["service_windows"] += 1
                _require(
                    native.get("initializer_readiness_service_complete") is True
                    and native.get("proposal_readiness_service_complete") is True
                    and all(
                        _finite(native.get(field))
                        for field in (
                            "initializer_readiness_service_sum",
                            "proposal_readiness_service_sum",
                            "initializer_readiness_service_max",
                            "proposal_readiness_service_max",
                            "readiness_service_sum_delta",
                            "readiness_service_max_delta",
                        )
                    ),
                    f"V137 native service certificate incomplete: {run['run_id']}:{line_number}",
                )
            guard = decision.get("window_safe_guard")
            _require(isinstance(guard, dict), "missing V137 native guard diagnostics")
            reason = guard.get("reason")
            _require(isinstance(reason, str), "invalid V137 native guard reason")
            reasons[reason] += 1
            if guard.get("accepted") is True:
                counts["accepted_windows"] += 1
                _require(
                    initializer_players > 0
                    and float(native["readiness_service_sum_delta"]) < 0.0
                    and float(native["readiness_service_max_delta"]) <= 1.0e-9
                    and _finite(guard.get("baseline_welfare_delta"))
                    and float(guard["baseline_welfare_delta"]) >= -1.0e-9,
                    f"V137 native accepted window violated certificate: {run['run_id']}:{line_number}",
                )
    _require(counts["windows"] == 4000, f"V137 window count changed: {run['run_id']}")
    _require(
        counts["player_windows"] > 0,
        f"V137 has no native player windows: {run['run_id']}",
    )
    return {
        "window_count": counts["windows"],
        "native_player_window_count": counts["player_windows"],
        "service_certificate_window_count": counts["service_windows"],
        "accepted_proposal_window_count": counts["accepted_windows"],
        "guard_reasons": dict(sorted(reasons.items())),
        "native_kind": native_kind,
        "performance_fields_consulted": False,
    }


def _runtime_evidence(audit: Mapping[str, Any]) -> dict[str, str]:
    return {
        "binary_sha256": str(audit["adapter_binary"]["verified_sha256"]),
        "git_commit": str(audit["software_environment"]["git"]["commit"]),
        "python_executable_sha256": str(
            audit["software_environment"]["python"]["executable_sha256"]
        ),
        "cargo_lock_sha256": str(audit["software_environment"]["cargo_lock"]["sha256"]),
    }


def _validate_execution_receipt() -> dict[str, Any]:
    ready_schedule_path = ROOT / READY_SCHEDULE.name
    execution_path = ROOT / EXECUTION_RECEIPT.name
    _require(ready_schedule_path.is_file(), "missing V137 ready schedule")
    _require(execution_path.is_file(), "missing V137 execution receipt")
    schedule = read_json(ready_schedule_path)
    schedule_hash = _assert_hashed_object(
        schedule, "schedule_hash", "V137 ready schedule"
    )
    receipt = read_json(execution_path)
    receipt_hash = _assert_hashed_object(
        receipt, "receipt_hash", "V137 execution receipt"
    )
    _require(
        receipt.get("performance_results_consulted") is False
        and receipt.get("plan_sha256") == PLAN_SHA256
        and receipt.get("ready_schedule_hash") == schedule_hash
        and receipt.get("dispatch_count") == 108
        and receipt.get("all_exit_codes_zero") is True
        and len(receipt.get("dispatches", [])) == 108,
        "V137 execution receipt boundary changed",
    )
    for scheduled, dispatched in zip(schedule["schedule"], receipt["dispatches"]):
        _require(
            all(
                scheduled[field] == dispatched[field]
                for field in (
                    "ordinal",
                    "block_id",
                    "within_block_index",
                    "method_label",
                    "manifest_id",
                    "run_id",
                )
            )
            and dispatched["exit_code"] == 0
            and file_hash(Path(dispatched["stdout_path"]))
            == dispatched["stdout_sha256"]
            and file_hash(Path(dispatched["stderr_path"]))
            == dispatched["stderr_sha256"],
            f"V137 frozen dispatch changed: {scheduled['ordinal']}",
        )
    return {
        "ready_schedule_path": str(ready_schedule_path),
        "ready_schedule_file_sha256": file_hash(ready_schedule_path),
        "ready_schedule_hash": schedule_hash,
        "execution_receipt_path": str(execution_path),
        "execution_receipt_file_sha256": file_hash(execution_path),
        "execution_receipt_hash": receipt_hash,
    }


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V137 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V137 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V137 plan changed")
    _require(PREPARED.is_file(), "missing V137 prepared receipt")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V137 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("training_seeds") == TRAINING_SEED_LIST
        and prepared.get("sealed_previous_confirmation_seeds")
        == PREVIOUS_CONFIRMATION_SEEDS
        and prepared.get("sealed_new_confirmation_seeds") == NEW_CONFIRMATION_SEEDS
        and prepared.get("total_online_runs") == 108
        and prepared.get("candidate_reference_builds") == 27,
        "V137 prepared scientific boundary changed",
    )
    execution = _validate_execution_receipt()
    tapes, tape_catalog = _verify_tapes()
    references, reference_ledger_hashes = _verify_references()

    run_evidence = []
    pairing_evidence = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    paired_inputs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    ready_manifests = {}
    products = [
        ("v137-baselines", 81, None),
        *[(arm_id, 9, ARMS[arm_id]) for arm_id in ARM_IDS],
    ]
    for manifest_id, expected_count, arm in products:
        manifest_path = ready_manifest_path(ROOT, manifest_id)
        manifest = load_and_validate_manifest(manifest_path)
        candidate = arm is not None
        _require(
            len(manifest["runs"]) == expected_count
            and manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_references_bound") is True
            and manifest.get("all_faasrank_models_bound") is (not candidate),
            f"V137 ready boundary changed: {manifest_id}",
        )
        ready_manifests[manifest_id] = {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "run_count": expected_count,
        }
        pairing_file = pairing_path(ROOT, manifest_id)
        pairing = read_json(pairing_file)
        _require(
            pairing.get("passed") is True
            and pairing.get("failed_group_count") == 0
            and pairing.get("run_count") == expected_count,
            f"V137 pairing changed: {manifest_id}",
        )
        pairing_evidence.append(
            {
                "manifest_id": manifest_id,
                "path": str(pairing_file),
                "file_sha256": file_hash(pairing_file),
                "run_count": pairing["run_count"],
                "group_count": pairing["group_count"],
            }
        )
        workspace = workspace_path(ROOT, manifest_id)
        expected_ids = {run["run_id"] for run in manifest["runs"]}
        actual_ids = {
            path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
        }
        _require(
            actual_ids == expected_ids, f"V137 canonical set changed: {manifest_id}"
        )
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V137 online quarantine is nonempty: {manifest_id}",
        )
        ledger_rows, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
        counts = Counter(row["event"] for row in ledger_rows)
        _require(
            counts["attempt_started"] == expected_count
            and counts["attempt_canonicalized"] == expected_count
            and not any(
                counts[event]
                for event in (
                    "attempt_failed",
                    "attempt_quarantined",
                    "run_blocked",
                    "partial_abandoned",
                )
            ),
            f"V137 online ledger changed: {manifest_id}/{counts}",
        )
        for run in manifest["runs"]:
            canonical = workspace / "canonical" / run["run_id"]
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            attempt = read_json(canonical / "attempt.json")
            qc = read_json(canonical / "qc_report.json")
            audit = read_json(canonical / "manifest.json")
            _require(
                attempt.get("attempt") == 1
                and attempt.get("status") == "qc_pass"
                and attempt.get("classification") == "qc_pass"
                and attempt.get("timed_out") is False
                and attempt.get("exit_code") == 0
                and qc.get("passed") is True
                and qc.get("classification") == "qc_pass",
                f"V137 canonical status changed: {run['run_id']}",
            )
            runtime = _runtime_evidence(audit)
            for field, value in runtime.items():
                runtime_values[field].add(value)
            scenario = scenario_id(run)
            label = manifest_id if candidate else run["method"]
            diagnostics = (
                _validate_native_diagnostics(
                    run, canonical, str(arm["native_kind"]).replace("sche_", "").lower()
                )
                if candidate
                else None
            )
            paired_inputs[(scenario, run["seed"])].append(
                {
                    "method_label": label,
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
                    "manifest_id": manifest_id,
                    "method_label": label,
                    "run_id": run["run_id"],
                    "scenario": scenario,
                    "seed": run["seed"],
                    "run_spec_hash": run["run_spec_hash"],
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "reference_key": (
                        run["reference_dependency"]["key"] if candidate else None
                    ),
                    "result_sha256": attempt["result_sha256"],
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "attempt": 1,
                    "classification": "qc_pass",
                    "native_diagnostics": diagnostics,
                    "ledger_last_hash": ledger_last_hash,
                    "reference_ledger_last_hash": (
                        reference_ledger_hashes[manifest_id] if candidate else None
                    ),
                }
            )

    _require(len(run_evidence) == 108, "V137 run evidence count changed")
    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V137 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(c in "0123456789abcdef" for c in next(iter(git_commits))),
        f"V137 runtime git identity changed: {git_commits}",
    )
    _require(len(paired_inputs) == 9, "V137 paired block count changed")
    for (scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 12
            and {row["method_label"] for row in rows} == set(METHOD_LABELS),
            f"V137 block product changed: {scenario}/{seed}",
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
                f"V137 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V137 common HPA changed: {scenario}/{seed}",
        )

    payload = {
        "schema_version": "NSE_E3_NATIVE_FRONTIER_ANCHOR_BLIND_AUDIT_V137_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "runtime_identity": {**EXPECTED_RUNTIME, "git_commit": next(iter(git_commits))},
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": TRAINING_SEED_LIST,
        "sealed_previous_confirmation_seeds": PREVIOUS_CONFIRMATION_SEEDS,
        "sealed_new_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        "manifest_count": 4,
        "baseline_run_count": 81,
        "candidate_run_count": 27,
        "run_count": 108,
        "reference_count": 27,
        "tape_count": 12,
        "block_count": 9,
        "execution": execution,
        "tape_catalog": tape_catalog,
        "ready_manifests": ready_manifests,
        "pairing": pairing_evidence,
        "tapes": tapes,
        "references": references,
        "runs": run_evidence,
    }
    payload["audit_hash"] = object_hash(payload)
    write_json_atomic(output, payload)
    return payload


def main() -> None:
    audit = run_blind_audit()
    print(json.dumps({"status": audit["status"], "audit_hash": audit["audit_hash"]}))


if __name__ == "__main__":
    main()
