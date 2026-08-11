"""Derive a small, non-formal integration-smoke manifest from a full manifest.

The shard keeps the selected run specifications byte-for-byte, so it exercises
the real capture/bind/reference/runner/QC path.  Its manifest-level provenance
and explicit ineligibility marker prevent its outputs from being confused with
the preregistered formal experiment matrix.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Iterable

from .schema import (
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


DEFAULT_SMOKE_PURPOSE = (
    "end-to-end protocol integration smoke only; never a formal scientific result"
)


def _reference_build_dependencies(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dependencies: dict[str, dict[str, Any]] = {}
    for run in runs:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], copy.deepcopy(dependency))
    return [dependencies[key] for key in sorted(dependencies)]


def _matrix_summary(
    runs: list[dict[str, Any]], reuse_analyses: list[dict[str, Any]]
) -> dict[str, Any]:
    cells = {(run["experiment_id"], run["cell_id"]) for run in runs}
    by_experiment: dict[str, dict[str, int]] = {}
    for experiment_id in (f"E{index}" for index in range(1, 10)):
        by_experiment[experiment_id] = {
            "new_cells": sum(item[0] == experiment_id for item in cells),
            "new_runs": sum(run["experiment_id"] == experiment_id for run in runs),
            "reuse_entries": sum(
                entry["experiment_id"] == experiment_id for entry in reuse_analyses
            ),
        }
    return {
        "new_cells": len(cells),
        "new_runs": len(runs),
        "by_experiment": by_experiment,
    }


def derive_integration_smoke_shard(
    source_manifest_path: Path,
    run_ids: Iterable[str],
    *,
    purpose: str = DEFAULT_SMOKE_PURPOSE,
) -> dict[str, Any]:
    """Select runs from one validated formal manifest and seal their lineage."""

    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    if (
        "integration_smoke_shard" in source
        or source.get("formal_results_eligible") is False
    ):
        raise ProtocolValidationError(
            "an integration-smoke shard cannot be used as a shard source"
        )
    if not isinstance(purpose, str) or not purpose.strip():
        raise ProtocolValidationError("smoke-shard purpose must be non-empty")

    requested = list(run_ids)
    if not requested:
        raise ProtocolValidationError(
            "select at least one --run-id for the smoke shard"
        )
    if len(requested) != len(set(requested)):
        raise ProtocolValidationError("smoke-shard run IDs must not be repeated")

    requested_set = set(requested)
    source_by_id = {run["run_id"]: run for run in source["runs"]}
    missing = sorted(requested_set - source_by_id.keys())
    if missing:
        raise ProtocolValidationError(
            "source manifest has no selected run IDs: " + ", ".join(missing)
        )

    # Preserve source-manifest order so selection is deterministic and paired
    # run order remains identical to the complete declaration.
    runs = [
        copy.deepcopy(run) for run in source["runs"] if run["run_id"] in requested_set
    ]
    reuse_analyses = copy.deepcopy(source["reuse_analyses"])
    selected_source_runs = [
        {
            "source_run_id": run["run_id"],
            "source_run_spec_hash": run["run_spec_hash"],
            "source_cell_id": run["cell_id"],
            "source_method": run["method"],
            "source_seed": run["seed"],
            "source_workload_spec_hash": run["workload_spec_hash"],
            "source_common_hpa_hash": run["common_hpa_hash"],
        }
        for run in runs
    ]
    sealed_reuse_rules = [
        {
            "rule_id": entry["rule_id"],
            "rule_sha256": entry["rule_sha256"],
        }
        for entry in reuse_analyses
    ]

    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["formal_results_eligible"] = False
    shard["runs"] = runs
    shard["reuse_analyses"] = reuse_analyses
    shard["reference_build_dependencies"] = _reference_build_dependencies(runs)
    shard["matrix_summary"] = _matrix_summary(runs, reuse_analyses)
    shard["integration_smoke_shard"] = {
        "schema_version": "NSE_INTEGRATION_SMOKE_SHARD_V1",
        "purpose": purpose.strip(),
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "run_count": len(source["runs"]),
            "seed_stage": source["seed_stage"],
        },
        "selected_source_runs": selected_source_runs,
        "sealed_reuse_rules": sealed_reuse_rules,
        "selected_run_count": len(runs),
        "selected_reference_build_count": len(shard["reference_build_dependencies"]),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_integration_smoke_shard(
    source_manifest_path: Path,
    output_path: Path,
    run_ids: Iterable[str],
    *,
    purpose: str = DEFAULT_SMOKE_PURPOSE,
) -> dict[str, Any]:
    """Derive, validate, and atomically write one non-formal smoke shard."""

    if source_manifest_path.resolve() == output_path.resolve():
        raise ProtocolValidationError("smoke shard output must differ from its source")
    shard = derive_integration_smoke_shard(
        source_manifest_path, run_ids, purpose=purpose
    )
    write_json_atomic(output_path, shard)
    return shard
