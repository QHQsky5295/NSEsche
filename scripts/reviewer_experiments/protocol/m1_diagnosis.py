"""Derive the fixed decision-neutral M1 warm-path diagnosis shard."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .m1_development import (
    M1_LOADS,
    M1_SCREEN_SEEDS,
    M1_TOPOLOGIES,
    _matrix_summary,
)
from .matrix import _assign_run_identity, _reference_build_dependencies
from .schema import (
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


DIAGNOSIS_SCHEMA = "NSE_M1_MECHANISM_DIAGNOSIS_SHARD_V1"
DIAGNOSIS_NAME = "warm_path_v1"
DIAGNOSIS_CANDIDATE = "ready_order"


def derive_m1_mechanism_diagnosis_shard(source_path: Path) -> dict[str, Any]:
    """Select the preregistered 30 runs from a completed-ready qualification manifest.

    The workload tape and offline reference bindings are copied exactly.  Only
    decision-neutral provenance metadata is added before the run identity is
    recomputed, so diagnostic artifacts cannot overwrite qualification artifacts.
    """

    source_path = source_path.resolve()
    source = load_and_validate_manifest(source_path)
    qualification = source.get("m1_qualification_shard")
    if not isinstance(qualification, dict):
        raise ProtocolValidationError(
            "M1 mechanism diagnosis requires an M1 qualification shard"
        )
    selection = qualification.get("selection")
    if (
        not isinstance(selection, dict)
        or selection.get("selected_candidate") != DIAGNOSIS_CANDIDATE
    ):
        raise ProtocolValidationError(
            "M1 warm-path diagnosis is preregistered for ready_order only"
        )
    selected = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["method"] == "sche_nash" and run["seed"] in M1_SCREEN_SEEDS
    ]
    expected = len(M1_LOADS) * len(M1_TOPOLOGIES) * len(M1_SCREEN_SEEDS)
    if len(selected) != expected:
        raise ProtocolValidationError(
            f"M1 diagnosis source is incomplete: observed={len(selected)}, expected={expected}"
        )

    for run in selected:
        metadata = run.setdefault("metadata", {})
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        metadata.update(
            {
                "m1_mechanism_diagnosis": DIAGNOSIS_NAME,
                "decision_neutral_observation": "warm_path_schema_1",
                "source_qualification_run_id": source_run_id,
                "source_qualification_run_spec_hash": source_run_spec_hash,
            }
        )
        _assign_run_identity(run)

    dependencies = _reference_build_dependencies(selected)
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["phase"] = "development"
    shard["bank_id"] = "TSCv1.development.M1.diagnosis.D01-D05"
    shard["fixed_seed_bank"]["selected_seeds"] = list(M1_SCREEN_SEEDS)
    shard["runs"] = selected
    shard["reference_build_dependencies"] = dependencies
    shard["matrix_summary"] = _matrix_summary(selected)
    shard.pop("m1_qualification_shard", None)
    shard["m1_mechanism_diagnosis_shard"] = {
        "schema_version": DIAGNOSIS_SCHEMA,
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "run_count": len(source["runs"]),
        },
        "selection": {
            "method": "sche_nash",
            "selected_candidate": DIAGNOSIS_CANDIDATE,
            "loads": list(M1_LOADS),
            "topologies": list(M1_TOPOLOGIES),
            "seeds": list(M1_SCREEN_SEEDS),
        },
        "decision_neutral_observation": {
            "name": DIAGNOSIS_NAME,
            "warm_path_schema": 1,
            "changes_scheduler_decision": False,
        },
        "paper_equations_changed": False,
        "formal_results_eligible": False,
        "run_count": len(selected),
        "cell_count": len({run["cell_id"] for run in selected}),
        "reference_build_count": len(dependencies),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_m1_mechanism_diagnosis_shard(
    source_path: Path, output_path: Path
) -> dict[str, Any]:
    if source_path.resolve() == output_path.resolve():
        raise ProtocolValidationError("M1 diagnosis output must differ from its source")
    source = load_and_validate_manifest(source_path.resolve())
    if source.get("all_tapes_bound") is not True or source.get(
        "all_references_bound"
    ) is not True:
        raise ProtocolValidationError(
            "an executable M1 diagnosis requires fully bound tapes and references"
        )
    shard = derive_m1_mechanism_diagnosis_shard(source_path)
    write_json_atomic(output_path, shard)
    return shard
