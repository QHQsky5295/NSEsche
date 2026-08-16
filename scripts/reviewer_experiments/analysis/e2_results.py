"""Strictly merge formal E2 runs with the audited homogeneous E1 20-node arm."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    FORMAL_E1_METHODS,
    FORMAL_E1_SEEDS_BY_STAGE,
    ProtocolValidationError,
    load_and_validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    utc_now,
    write_json_atomic,
)

from .protocol_results import (
    load_canonical_protocol_results,
    materialize_analysis_reuse_rows,
)
from .summarize_runs import write_csv


def _canonical_root(workspace: Path) -> Path:
    return workspace if workspace.name == "canonical" else workspace / "canonical"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _physical_coverage(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if not row.get("record_kind")]


def _faasrank_artifact_hashes(manifest: Mapping[str, Any]) -> set[str]:
    return {
        str(run.get("baseline_model", {}).get("artifact_sha256"))
        for run in manifest.get("runs", [])
        if run.get("method") == "sche_FaaSRank"
    }


def _validate_merge_contract(
    e2: Mapping[str, Any], e1: Mapping[str, Any]
) -> dict[str, Any]:
    e2_marker = e2.get("formal_e2_weak_scaling_shard")
    e1_marker = e1.get("formal_e1_homogeneous_shard")
    _require(isinstance(e2_marker, Mapping), "E2 manifest is not a formal E2 shard")
    _require(
        isinstance(e1_marker, Mapping),
        "E1 reuse manifest is not a formal homogeneous E1 shard",
    )
    for field in (
        "protocol_id",
        "seed_stage",
        "common_hpa_hash",
        "workload_profile_set_hash",
    ):
        _require(
            e2.get(field) == e1.get(field),
            f"E1/E2 merge contract differs in {field}",
        )
    for label, manifest in (("E1", e1), ("E2", e2)):
        _require(
            manifest.get("formal_results_eligible") is True,
            f"{label} manifest is not eligible for formal results",
        )
        _require(
            manifest.get("all_tapes_bound") is True
            and manifest.get("all_faasrank_models_bound") is True
            and manifest.get("all_references_bound") is True,
            f"{label} manifest is not tape/model/reference ready",
        )
    _require(
        _faasrank_artifact_hashes(e1) == _faasrank_artifact_hashes(e2)
        and len(_faasrank_artifact_hashes(e1)) == 1,
        "E1/E2 do not use the same single frozen FaaSRank model",
    )

    e2_rule = e2_marker.get("sealed_e1_reuse_rule")
    _require(isinstance(e2_rule, Mapping), "E2 sealed E1 reuse rule is missing")
    rules_e1 = {
        entry.get("rule_id"): entry.get("rule_sha256")
        for entry in e1.get("reuse_analyses", [])
    }
    rules_e2 = {
        entry.get("rule_id"): entry.get("rule_sha256")
        for entry in e2.get("reuse_analyses", [])
    }
    rule_id = e2_rule.get("rule_id")
    rule_hash = e2_rule.get("rule_sha256")
    _require(
        rule_id == "E2_FROM_E1_20NODE_HOMOGENEOUS_V1"
        and rules_e1.get(rule_id) == rule_hash
        and rules_e2.get(rule_id) == rule_hash,
        "E1/E2 sealed 20-node reuse rules differ",
    )

    current_by_stable_key = {
        (run["cell_id"], run["seed"]): run for run in e1.get("runs", [])
    }
    lineage = e2_marker.get("e1_reuse_source_runs")
    _require(isinstance(lineage, list), "E2 E1-reuse lineage is missing")
    expected_keys = {
        (method, load, seed)
        for method in FORMAL_E1_METHODS
        for load in FORMAL_E1_LOADS
        for seed in FORMAL_E1_SEEDS_BY_STAGE[str(e2["seed_stage"])]
    }
    observed_keys: set[tuple[str, str, str]] = set()
    for index, entry in enumerate(lineage):
        stable_key = (entry.get("source_cell_id"), entry.get("source_seed"))
        current = current_by_stable_key.get(stable_key)
        _require(
            current is not None, f"E1 reuse lineage[{index}] has no audited E1 run"
        )
        observed_keys.add(
            (
                str(entry.get("source_method")),
                str(entry.get("source_load")),
                str(entry.get("source_seed")),
            )
        )
        _require(
            current.get("method") == entry.get("source_method")
            and current.get("variant", "full") == entry.get("source_variant")
            and current.get("workload_spec_hash")
            == entry.get("source_workload_spec_hash")
            and current.get("workload_tape", {}).get("key")
            == entry.get("source_workload_tape_key")
            and object_hash(current.get("cluster"))
            == entry.get("source_cluster_sha256")
            and object_hash(current.get("simulation"))
            == entry.get("source_simulation_sha256")
            and object_hash(current.get("environment"))
            == entry.get("source_environment_sha256")
            and current.get("common_hpa_hash") == entry.get("source_common_hpa_hash"),
            f"E1 reuse lineage[{index}] differs from the supplied formal E1 manifest",
        )
    _require(observed_keys == expected_keys, "E1 reuse lineage product is incomplete")
    _require(
        set(current_by_stable_key)
        == {(entry["source_cell_id"], entry["source_seed"]) for entry in lineage},
        "supplied E1 shard has runs outside the E2-sealed reuse product",
    )
    return {"reuse_rule_id": rule_id, "reuse_rule_sha256": rule_hash}


def export_e2_with_e1_reuse(
    *,
    e2_manifest_path: Path,
    e2_workspace: Path,
    e1_manifest_path: Path,
    e1_workspace: Path,
    output_csv: Path,
    coverage_csv: Path,
    audit_json: Path,
) -> dict[str, Any]:
    """Export one complete, pairing-audited 20/100/500-node E2 table."""

    e2_manifest_path = e2_manifest_path.resolve()
    e1_manifest_path = e1_manifest_path.resolve()
    e2 = load_and_validate_manifest(e2_manifest_path)
    e1 = load_and_validate_manifest(e1_manifest_path)
    contract = _validate_merge_contract(e2, e1)

    e2_pairing = audit_manifest_pairing(e2, e2_workspace)
    e1_pairing = audit_manifest_pairing(e1, e1_workspace)
    _require(e2_pairing["passed"], "formal E2 pairing/canonical audit failed")
    _require(e1_pairing["passed"], "formal E1 pairing/canonical audit failed")

    e2_rows_all, e2_coverage_all = load_canonical_protocol_results(
        e2_manifest_path, _canonical_root(e2_workspace)
    )
    e1_rows_all, e1_coverage_all = load_canonical_protocol_results(
        e1_manifest_path, _canonical_root(e1_workspace)
    )
    e2_rows = [
        row
        for row in e2_rows_all
        if row.get("experiment_id") == "E2"
        and row.get("analysis_record_kind") == "formal_run"
    ]
    e1_rows = [
        row
        for row in e1_rows_all
        if row.get("experiment_id") == "E1"
        and row.get("analysis_record_kind") == "formal_run"
    ]
    e2_physical_coverage = _physical_coverage(e2_coverage_all)
    e1_physical_coverage = _physical_coverage(e1_coverage_all)
    _require(
        len(e2_rows) == len(e2["runs"])
        and all(row.get("status") == "ok" for row in e2_physical_coverage),
        "formal E2 canonical export is incomplete",
    )
    _require(
        len(e1_rows) == len(e1["runs"])
        and all(row.get("status") == "ok" for row in e1_physical_coverage),
        "formal E1 reuse-source export is incomplete",
    )

    reused_rows, reuse_coverage = materialize_analysis_reuse_rows(
        e2,
        e1_rows,
        source_runs=e1["runs"],
        target_experiment_ids={"E2"},
        source_manifest_hash=str(e1["manifest_hash"]),
    )
    _require(
        len(reused_rows) == len(e1["runs"])
        and all(row.get("status") == "ok" for row in reuse_coverage),
        "E1-to-E2 20-node reuse materialization is incomplete",
    )

    combined = sorted(
        [*e2_rows, *reused_rows],
        key=lambda row: (
            int(row.get("node_count", 0)),
            str(row.get("load", "")),
            str(row.get("algorithm", "")),
            str(row.get("seed", "")),
        ),
    )
    expected_count = len(e2["runs"]) + len(e1["runs"])
    identity_keys = {
        (str(row.get("cell_id")), str(row.get("seed"))) for row in combined
    }
    _require(
        len(combined) == expected_count and len(identity_keys) == expected_count,
        "combined E2 table has missing or duplicate cell/seed rows",
    )
    _require(
        {int(row.get("node_count", 0)) for row in combined} == {20, 100, 500},
        "combined E2 table does not contain exactly 20/100/500 nodes",
    )

    coverage: list[dict[str, Any]] = []
    for scope, rows in (
        ("e2_physical", e2_physical_coverage),
        ("e1_reuse_source", e1_physical_coverage),
        ("e1_to_e2_projection", reuse_coverage),
    ):
        coverage.extend({"coverage_scope": scope, **row} for row in rows)
    write_csv(output_csv, combined)
    write_csv(coverage_csv, coverage)

    row_identities = [
        {
            "cell_id": row.get("cell_id"),
            "seed": row.get("seed"),
            "run_id": row.get("run_id"),
            "analysis_record_kind": row.get("analysis_record_kind"),
            "run_spec_hash": row.get("run_spec_hash"),
            "source_run_id": row.get("source_run_id", ""),
            "reuse_materialization_sha256": row.get("reuse_materialization_sha256", ""),
        }
        for row in combined
    ]
    audit = {
        "schema_version": "NSE_E2_E1_REUSE_MERGE_AUDIT_V1",
        "created_at": utc_now(),
        "status": "complete",
        "e2_manifest": {
            "path": str(e2_manifest_path),
            "manifest_hash": e2["manifest_hash"],
            "file_sha256": file_hash(e2_manifest_path),
            "pairing_audit_sha256": object_hash(e2_pairing),
        },
        "e1_manifest": {
            "path": str(e1_manifest_path),
            "manifest_hash": e1["manifest_hash"],
            "file_sha256": file_hash(e1_manifest_path),
            "pairing_audit_sha256": object_hash(e1_pairing),
        },
        "reuse_contract": contract,
        "seed_stage": e2["seed_stage"],
        "node_counts": [20, 100, 500],
        "physical_e2_row_count": len(e2_rows),
        "e1_reuse_row_count": len(reused_rows),
        "combined_row_count": len(combined),
        "combined_row_identities_sha256": object_hash(row_identities),
        "coverage_row_count": len(coverage),
        "output_csv": {
            "path": str(output_csv.resolve()),
            "sha256": file_hash(output_csv),
        },
        "coverage_csv": {
            "path": str(coverage_csv.resolve()),
            "sha256": file_hash(coverage_csv),
        },
    }
    audit["audit_sha256"] = object_hash(audit)
    write_json_atomic(audit_json, audit)
    return audit
