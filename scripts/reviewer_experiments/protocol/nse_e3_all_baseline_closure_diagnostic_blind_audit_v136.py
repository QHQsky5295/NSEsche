from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import (
    validate_canonical_run,
    validate_pairing_audit,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_prepare_v136 import (
    BASELINE_METHODS,
    BINARY_SHA256,
    PLAN,
    PLAN_SHA256,
    ROOT,
    SCENARIOS,
    SEED_LIST,
    SEEDS,
    TAPES,
    TAPES_FILE_SHA256,
    V135_ANCHOR_MANIFEST,
    V135_ANCHOR_MANIFEST_FILE_SHA256,
    V135_ANCHOR_WORKSPACE,
    paths,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.tape import inspect_tape
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


PREPARED = ROOT / "prepared-v136.json"
OUTPUT = ROOT / "joint-blind-audit-v136.json"
RESULT = ROOT / "all-baseline-closure-result-v136.json"
ANCHOR_PAIRING = V135_ANCHOR_MANIFEST.parent / "pairing-audit.v135-e3-anchor.json"
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_hashed_object(value: Mapping[str, Any], hash_field: str, label: str) -> str:
    claimed = value.get(hash_field)
    payload = dict(value)
    payload.pop(hash_field, None)
    _require(
        isinstance(claimed, str) and len(claimed) == 64,
        f"{label} lacks a valid claimed hash",
    )
    _require(object_hash(payload) == claimed, f"{label} self-hash mismatch")
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
        bool(rows) and rows[-1].get("event_hash") == last_hash,
        f"ledger tail hash changed: {path}",
    )
    return rows, last_hash


def _assert_clean_ledger(
    rows: list[dict[str, Any]], expected_runs: int, label: str
) -> None:
    expected = Counter(
        {
            "batch_started": 1,
            "attempt_started": expected_runs,
            "attempt_canonicalized": expected_runs,
            "batch_finished": 1,
        }
    )
    actual = Counter(str(row.get("event_type")) for row in rows)
    _require(actual == expected, f"{label} ledger contract changed: {actual}")


def _validate_declared_product(runs: list[dict[str, Any]]) -> None:
    expected = {
        (method, scenario, seed)
        for method in BASELINE_METHODS
        for scenario in SCENARIOS
        for seed in SEED_LIST
    }
    actual = {(run["method"], scenario_id(run), run["seed"]) for run in runs}
    _require(
        len(runs) == 81 and actual == expected,
        "V136 declared baseline product is incomplete or contains extras",
    )
    _require(
        all(run.get("reference_dependency") is None for run in runs),
        "V136 baseline manifest unexpectedly carries a Nash reference",
    )
    for run in runs:
        metadata = run.get("metadata", {})
        _require(
            run["experiment_id"] == "E3"
            and run["workload"]["request_freq"] == "middle"
            and run["workload"]["topology"] == "heterogeneous"
            and run["workload"]["qos_profile"] == "balanced"
            and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
            and run["simulation"]["arrival_horizon_frames"] == 1000
            and run["simulation"]["observation_horizon_frames"] == 1000
            and run["simulation"]["total_frame"] == 4000
            and metadata.get("v136_plan_sha256") == PLAN_SHA256
            and metadata.get("v136_diagnostic_only") is True
            and metadata.get("v136_role") == "paper_baseline"
            and metadata.get("v136_complete_method_seed_scenario_product") is True
            and metadata.get("v136_baseline_performance_consulted_before_execution")
            is False
            and metadata.get("v136_NSESche_reused_not_rerun") is True
            and metadata.get("v136_confirmation_inputs_opened") is False
            and metadata.get("v136_seed_or_scenario_label_used_by_policy") is False
            and metadata.get("v136_outcome_fields_used_by_policy") is False,
            f"V136 run boundary changed: {run['run_id']}",
        )


def _verify_tapes() -> dict[str, Any]:
    _require(
        TAPES.is_file() and file_hash(TAPES) == TAPES_FILE_SHA256,
        "V136 tape catalog changed",
    )
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V136 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12, "V136 tape count changed"
    )
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(info.sha256 == entry.get("sha256"), f"V136 tape changed: {key}")
        _require(info.workload_seed in SEEDS, f"V136 tape seed changed: {key}")
        evidence.append(
            {
                "key": key,
                "sha256": info.sha256,
                "event_count": info.event_count,
                "dag_order_sha256": info.dag_order_sha256,
                "workload_seed": info.workload_seed,
                "kind": entry.get("kind"),
            }
        )
    _require(
        Counter(item["kind"] for item in evidence)
        == Counter({"base_steady": 3, "derived_burst": 9}),
        "V136 tape kind product changed",
    )
    return {
        "path": str(TAPES),
        "file_sha256": TAPES_FILE_SHA256,
        "catalog_hash": catalog_hash,
        "entries": evidence,
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


def _canonical_evidence(
    run: dict[str, Any],
    canonical: Path,
    manifest_hash: str,
    role: str,
    ledger_last_hash: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    validate_canonical_run(
        run,
        canonical,
        expected_manifest_hash=manifest_hash,
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
        f"V136 canonical status changed: {run['run_id']}",
    )
    result_sha256 = attempt.get("result_sha256")
    _require(
        isinstance(result_sha256, str) and len(result_sha256) == 64,
        f"V136 result hash missing: {run['run_id']}",
    )
    evidence = {
        "role": role,
        "run_id": run["run_id"],
        "method": run["method"],
        "scenario": scenario_id(run),
        "seed": run["seed"],
        "run_spec_hash": run["run_spec_hash"],
        "workload_spec_hash": run["workload_spec_hash"],
        "common_hpa_hash": run["common_hpa_hash"],
        "workload_tape_key": run["workload_tape"]["key"],
        "workload_tape_sha256": run["workload_tape"]["sha256"],
        "capture_environment_sha256": run["workload_tape"]["capture_environment"][
            "capture_environment_sha256"
        ],
        "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
        "result_sha256": result_sha256,
        "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
        "qc_report_sha256": file_hash(canonical / "qc_report.json"),
        "ledger_last_hash": ledger_last_hash,
        "performance_fields_consulted": False,
    }
    return evidence, _runtime_evidence(audit)


def _verify_workspace(
    manifest: dict[str, Any],
    workspace: Path,
    pairing_path: Path,
    role: str,
) -> tuple[list[dict[str, Any]], dict[str, set[str]], dict[str, Any]]:
    expected_ids = {run["run_id"] for run in manifest["runs"]}
    canonical_root = workspace / "canonical"
    actual_ids = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual_ids == expected_ids, f"V136 {role} canonical set changed")
    quarantine = workspace / "quarantine"
    _require(
        not quarantine.exists() or not list(quarantine.glob("**/attempt-*")),
        f"V136 {role} contains quarantined attempts",
    )
    ledger_rows, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
    _assert_clean_ledger(ledger_rows, len(manifest["runs"]), f"V136 {role}")
    pairing = validate_pairing_audit(pairing_path, manifest, canonical_root)
    _require(
        pairing.get("run_count") == len(manifest["runs"])
        and pairing.get("group_count") == 9
        and pairing.get("failed_group_count") == 0,
        f"V136 {role} pairing product changed",
    )
    evidence = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    for run in manifest["runs"]:
        row, runtime = _canonical_evidence(
            run,
            canonical_root / run["run_id"],
            manifest["manifest_hash"],
            role,
            ledger_last_hash,
        )
        evidence.append(row)
        for field, value in runtime.items():
            runtime_values[field].add(value)
    return (
        evidence,
        runtime_values,
        {
            "path": str(pairing_path),
            "file_sha256": file_hash(pairing_path),
            "run_count": pairing["run_count"],
            "group_count": pairing["group_count"],
            "passed": True,
        },
    )


def _assert_paired_inputs(
    baseline_runs: list[dict[str, Any]], anchor_runs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in [*baseline_runs, *anchor_runs]:
        grouped[(row["scenario"], row["seed"])].append(row)
    _require(len(grouped) == 9, "V136 paired input group count changed")
    output = []
    exact_fields = (
        "workload_spec_hash",
        "common_hpa_hash",
        "workload_tape_key",
        "workload_tape_sha256",
        "capture_environment_sha256",
        "sla_artifact_sha256",
    )
    for (scenario, seed), rows in sorted(grouped.items()):
        methods = {row["method"] for row in rows}
        _require(
            len(rows) == 10 and methods == {"sche_nash", *BASELINE_METHODS},
            f"V136 paired method product changed: {scenario}/{seed}",
        )
        for field in exact_fields:
            _require(
                len({str(row[field]) for row in rows}) == 1,
                f"V136 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V136 common-HPA hash changed: {scenario}/{seed}",
        )
        output.append(
            {
                "scenario": scenario,
                "seed": seed,
                "method_count": 10,
                **{field: rows[0][field] for field in exact_fields},
            }
        )
    return output


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    output_paths = paths(ROOT)
    _require(not output.exists(), f"V136 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V136 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V136 plan changed")
    _require(PREPARED.is_file(), "V136 prepared receipt is missing")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(prepared, "receipt_hash", "V136 prepared")
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("baseline_performance_summaries_parsed") == 0
        and prepared.get("new_baseline_run_count") == 81
        and prepared.get("reused_NSESche_run_count") == 9
        and prepared.get("NSESche_rerun_count") == 0
        and prepared.get("confirmation_inputs_generated") is False,
        "V136 prepared information boundary changed",
    )
    tape_evidence = _verify_tapes()

    ready = load_and_validate_manifest(output_paths["ready"])
    _validate_declared_product(ready["runs"])
    _require(
        ready.get("formal_results_eligible") is False
        and ready.get("all_tapes_bound") is True
        and ready.get("all_sla_targets_bound") is True
        and ready.get("all_faasrank_models_bound") is True
        and ready.get("all_references_bound") is True
        and not ready["reference_build_dependencies"],
        "V136 ready manifest boundary changed",
    )
    baseline_runs, baseline_runtime, baseline_pairing = _verify_workspace(
        ready,
        output_paths["workspace"],
        output_paths["pairing"],
        "paper_baseline",
    )
    _require(len(baseline_runs) == 81, "V136 baseline evidence count changed")
    for field, values in baseline_runtime.items():
        _require(len(values) == 1, f"V136 baseline runtime {field} is not singular")
    _require(
        baseline_runtime["binary_sha256"] == {BINARY_SHA256},
        "V136 baseline binary changed",
    )

    _require(
        V135_ANCHOR_MANIFEST.is_file()
        and file_hash(V135_ANCHOR_MANIFEST) == V135_ANCHOR_MANIFEST_FILE_SHA256,
        "V136 frozen V135 anchor manifest changed",
    )
    anchor = load_and_validate_manifest(V135_ANCHOR_MANIFEST)
    _require(
        len(anchor["runs"]) == 9
        and {run["method"] for run in anchor["runs"]} == {"sche_nash"}
        and {run["seed"] for run in anchor["runs"]} == SEEDS,
        "V136 frozen NSESche anchor product changed",
    )
    anchor_runs, anchor_runtime, anchor_pairing = _verify_workspace(
        anchor, V135_ANCHOR_WORKSPACE, ANCHOR_PAIRING, "frozen_NSESche_anchor"
    )
    _require(len(anchor_runs) == 9, "V136 anchor evidence count changed")
    _require(
        anchor_runtime["binary_sha256"] == {BINARY_SHA256},
        "V136 anchor binary differs from frozen baseline binary",
    )
    paired_inputs = _assert_paired_inputs(baseline_runs, anchor_runs)

    audit = {
        "schema_version": "NSE_E3_ALL_BASELINE_CLOSURE_BLIND_AUDIT_V136_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "ready_manifest": {
            "path": str(output_paths["ready"]),
            "file_sha256": file_hash(output_paths["ready"]),
            "manifest_hash": ready["manifest_hash"],
        },
        "anchor_manifest": {
            "path": str(V135_ANCHOR_MANIFEST),
            "file_sha256": V135_ANCHOR_MANIFEST_FILE_SHA256,
            "manifest_hash": anchor["manifest_hash"],
        },
        "tape_catalog": tape_evidence,
        "baseline_pairing": baseline_pairing,
        "anchor_pairing": anchor_pairing,
        "baseline_runtime_consensus": {
            field: next(iter(values)) for field, values in baseline_runtime.items()
        },
        "anchor_runtime_consensus": {
            field: next(iter(values)) for field, values in anchor_runtime.items()
        },
        "baseline_runs": sorted(baseline_runs, key=lambda row: row["run_id"]),
        "anchor_runs": sorted(anchor_runs, key=lambda row: row["run_id"]),
        "paired_inputs": paired_inputs,
        "baseline_run_count": 81,
        "reused_NSESche_run_count": 9,
        "combined_run_count": 90,
        "paired_input_group_count": 9,
        "new_reference_build_count": 0,
        "NSESche_rerun_count": 0,
        "confirmation_inputs_opened": False,
        "reveal_authorized": True,
    }
    audit["audit_hash"] = object_hash(audit)
    write_json_atomic(output, audit)
    return audit


def main() -> None:
    run_blind_audit()


if __name__ == "__main__":
    main()
