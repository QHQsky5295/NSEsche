"""Build the fixed, non-formal M1 candidate-development boundary.

The paper equations and all formal E01--E20 seeds remain untouched.  This
module creates a disjoint D01--D20 paired bank, three preregistered operational
NSESche candidates, and the fixed D01--D05 candidate screen required by the
frozen resubmission plan.
"""

from __future__ import annotations

import copy
from itertools import product
from pathlib import Path
from typing import Any

from .matrix import (
    _assign_run_identity,
    _base_workload,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    _reference_dependency,
    load_protocol_config,
)
from .schema import (
    FORMAL_E1_METHODS,
    M1_DEVELOPMENT_SAMPLE_POLICY,
    M1_DEVELOPMENT_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


M1_OPERATIONAL_CANDIDATES = (
    "formula",
    "ready_order",
    "ready_finish_tie",
)
M1_SCREEN_SEEDS = M1_DEVELOPMENT_SEEDS[:5]
M1_LOADS = ("low", "middle", "high")
M1_TOPOLOGIES = ("homogeneous", "heterogeneous")
M1_BASELINE_METHODS = tuple(
    method for method in FORMAL_E1_METHODS if method != "sche_nash"
)


def _matrix_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    cells = {(run["experiment_id"], run["cell_id"]) for run in runs}
    by_experiment = {
        f"E{index}": {
            "new_cells": sum(item[0] == f"E{index}" for item in cells),
            "new_runs": sum(run["experiment_id"] == f"E{index}" for run in runs),
            "reuse_entries": 0,
        }
        for index in range(1, 10)
    }
    return {
        "new_cells": len(cells),
        "new_runs": len(runs),
        "by_experiment": by_experiment,
    }


def _candidate_cell(
    candidate: str, load: str, topology: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"M1DEV.sche_nash.{candidate}.{load}.{topology}.n{node_count}",
        "sche_nash",
        _base_workload(load, topology, "mixed"),
        {"node_count": node_count, "topology": topology},
        metadata={
            "m1_operational_candidate": candidate,
            "paper_equations_changed": False,
        },
    )


def _baseline_cell(
    method: str, load: str, topology: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"M1DEV.{method}.{load}.{topology}.n{node_count}",
        method,
        _base_workload(load, topology, "mixed"),
        {"node_count": node_count, "topology": topology},
        metadata={"m1_role": "qualification_baseline"},
    )


def _bind_candidate(run: dict[str, Any], candidate: str) -> None:
    """Bind one candidate before recomputing reference and run identities."""

    experiment = run["simulator_experiment"]
    experiment["nash"]["operational_refinement"] = candidate
    run["environment"]["NASH_OPERATIONAL_REFINEMENT"] = candidate
    experiment["reference"] = {
        "mode": "sa_fallback",
        "table_path": "",
        "build_output_path": "",
    }
    run.pop("reference_dependency", None)
    dependency = _reference_dependency(run)
    run["reference_dependency"] = dependency
    experiment["reference"] = {
        "mode": "offline_required",
        "table_path": dependency["path"],
        "build_output_path": "",
    }
    _assign_run_identity(run)


def build_m1_development_manifest(
    config_path: Path | None = None,
) -> dict[str, Any]:
    config = load_protocol_config(config_path)
    node_count = int(config["matrix_defaults"]["base_node_count"])
    common_hpa_hash = object_hash(config["common_hpa"])
    repository = Path(__file__).resolve().parents[3]
    profiles = load_profile_set(config["workload_profiles"], repository=repository)
    profile_bindings = {load: profile.to_binding() for load, profile in profiles.items()}
    workload_profile_set = {
        "schema_version": config["workload_profiles"]["schema_version"],
        "profile_set_id": config["workload_profiles"]["profile_set_id"],
        "formal_required": True,
        "profiles": profile_bindings,
    }

    cells: list[dict[str, Any]] = []
    for method, load, topology in product(
        M1_BASELINE_METHODS, M1_LOADS, M1_TOPOLOGIES
    ):
        cells.append(_baseline_cell(method, load, topology, node_count))
    for candidate, load, topology in product(
        M1_OPERATIONAL_CANDIDATES, M1_LOADS, M1_TOPOLOGIES
    ):
        cells.append(_candidate_cell(candidate, load, topology, node_count))

    runs: list[dict[str, Any]] = []
    for cell in cells:
        for seed in M1_DEVELOPMENT_SEEDS:
            run = _make_run(
                config,
                cell,
                seed,
                common_hpa_hash,
                profiles[cell["workload"]["request_freq"]],
            )
            candidate = cell.get("metadata", {}).get("m1_operational_candidate")
            if candidate is not None:
                _bind_candidate(run, str(candidate))
            runs.append(run)

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.M1.D01-D20",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": M1_DEVELOPMENT_SAMPLE_POLICY,
            "all_seeds": list(M1_DEVELOPMENT_SEEDS),
            "selected_seeds": list(M1_DEVELOPMENT_SEEDS),
            "paired_across_methods": True,
            "result_conditioned_extension": False,
        },
        "method_versions": copy.deepcopy(
            config["manifest_governance"]["method_versions"]
        ),
        "old_pdf_alignment": copy.deepcopy(
            config["manifest_governance"]["old_pdf_alignment"]
        ),
        "runtime_identity_policy": copy.deepcopy(
            config["manifest_governance"]["runtime_identity"]
        ),
        "seed_stage": "development",
        "ci_extension_requires_trigger": False,
        "common_hpa": copy.deepcopy(config["common_hpa"]),
        "common_hpa_hash": common_hpa_hash,
        "workload_profile_set": workload_profile_set,
        "workload_profile_set_hash": object_hash(workload_profile_set),
        "simulation": copy.deepcopy(config["simulation"]),
        "execution": copy.deepcopy(config["execution"]),
        "qc": copy.deepcopy(config["qc"]),
        "matrix_summary": _matrix_summary(runs),
        "runs": runs,
        "reference_build_dependencies": _reference_build_dependencies(runs),
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": [],
        "m1_development_matrix": {
            "schema_version": "NSE_M1_DEVELOPMENT_MATRIX_V1",
            "purpose": "formula-consistent candidate screening and six-cell qualification",
            "paper_equations_changed": False,
            "formal_seed_overlap": [],
            "candidates": list(M1_OPERATIONAL_CANDIDATES),
            "baseline_methods": list(M1_BASELINE_METHODS),
            "loads": list(M1_LOADS),
            "topologies": list(M1_TOPOLOGIES),
            "node_count": node_count,
            "development_seeds": list(M1_DEVELOPMENT_SEEDS),
            "screen_seeds": list(M1_SCREEN_SEEDS),
            "run_count": len(runs),
            "cell_count": len(cells),
            "reference_build_count": len(_reference_build_dependencies(runs)),
        },
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_m1_development_manifest(
    output_path: Path, config_path: Path | None = None
) -> dict[str, Any]:
    manifest = build_m1_development_manifest(config_path)
    write_json_atomic(output_path, manifest)
    return manifest


def derive_m1_candidate_screen_shard(source_path: Path) -> dict[str, Any]:
    source_path = source_path.resolve()
    source = load_and_validate_manifest(source_path)
    if "m1_development_matrix" not in source:
        raise ProtocolValidationError(
            "M1 candidate screen requires the complete M1 development matrix"
        )
    selected = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["method"] == "sche_nash" and run["seed"] in M1_SCREEN_SEEDS
    ]
    expected = (
        len(M1_OPERATIONAL_CANDIDATES)
        * len(M1_LOADS)
        * len(M1_TOPOLOGIES)
        * len(M1_SCREEN_SEEDS)
    )
    if len(selected) != expected:
        raise ProtocolValidationError(
            f"M1 screen source is incomplete: observed={len(selected)}, expected={expected}"
        )
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["bank_id"] = "TSCv1.development.M1.screen.D01-D05"
    shard["fixed_seed_bank"]["selected_seeds"] = list(M1_SCREEN_SEEDS)
    shard["runs"] = selected
    shard["reference_build_dependencies"] = _reference_build_dependencies(selected)
    shard["matrix_summary"] = _matrix_summary(selected)
    shard.pop("m1_development_matrix", None)
    shard["m1_candidate_screen_shard"] = {
        "schema_version": "NSE_M1_CANDIDATE_SCREEN_SHARD_V1",
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "run_count": len(source["runs"]),
        },
        "selection": {
            "method": "sche_nash",
            "candidates": list(M1_OPERATIONAL_CANDIDATES),
            "loads": list(M1_LOADS),
            "topologies": list(M1_TOPOLOGIES),
            "seeds": list(M1_SCREEN_SEEDS),
        },
        "paper_equations_changed": False,
        "run_count": len(selected),
        "cell_count": len({run["cell_id"] for run in selected}),
        "reference_build_count": len(_reference_build_dependencies(selected)),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_m1_candidate_screen_shard(
    source_path: Path, output_path: Path
) -> dict[str, Any]:
    if source_path.resolve() == output_path.resolve():
        raise ProtocolValidationError("M1 screen output must differ from its source")
    shard = derive_m1_candidate_screen_shard(source_path)
    write_json_atomic(output_path, shard)
    return shard
