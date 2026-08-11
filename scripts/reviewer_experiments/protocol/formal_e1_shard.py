"""Derive the complete formal E1 homogeneous execution shard.

Unlike the freely selected integration-smoke shard, this shard has exactly one
legal shape for each seed stage.  It exists to execute and checkpoint the E1
homogeneous block without preparing unrelated E2--E7 inputs.
"""

from __future__ import annotations

import copy
from collections import Counter
from itertools import product
from pathlib import Path
from typing import Any

from .schema import (
    FORMAL_E1_LOADS,
    FORMAL_E1_METHODS,
    FORMAL_E1_SEEDS_BY_STAGE,
    FULL_MATRIX_RUN_COUNTS_BY_STAGE,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


FORMAL_E1_SHARD_SCHEMA = "NSE_FORMAL_E1_HOMOGENEOUS_SHARD_V1"
FULL_MATRIX_CELL_COUNTS = {
    "E1": 60,
    "E2": 60,
    "E3": 30,
    "E4": 10,
    "E5": 12,
    "E6": 4,
    "E7": 12,
}


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


def _expected_e1_keys(
    seed_stage: str, *, topologies: tuple[str, ...]
) -> set[tuple[str, str, str, str]]:
    seeds = FORMAL_E1_SEEDS_BY_STAGE[seed_stage]
    return set(product(FORMAL_E1_METHODS, FORMAL_E1_LOADS, topologies, seeds))


def _e1_key(run: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        run["method"],
        run["workload"]["request_freq"],
        run["cluster"]["topology"],
        run["seed"],
    )


def _assert_complete_full_source(source: dict[str, Any]) -> None:
    if (
        "integration_smoke_shard" in source
        or "formal_e1_homogeneous_shard" in source
        or source.get("formal_results_eligible") is False
    ):
        raise ProtocolValidationError(
            "a derived shard cannot be used as a formal E1 shard source"
        )

    seed_stage = source["seed_stage"]
    expected_counts = FULL_MATRIX_RUN_COUNTS_BY_STAGE[seed_stage]
    observed_counts = Counter(run["experiment_id"] for run in source["runs"])
    observed_formal_counts = {
        experiment_id: observed_counts.get(experiment_id, 0)
        for experiment_id in expected_counts
    }
    unexpected = sorted(set(observed_counts) - set(expected_counts))
    if observed_formal_counts != expected_counts or unexpected:
        raise ProtocolValidationError(
            "formal E1 shard source is not the complete frozen E1-E7 matrix "
            f"for seed_stage={seed_stage}: observed={observed_formal_counts}, "
            f"expected={expected_counts}, unexpected={unexpected}"
        )

    expected_summary_by_experiment: dict[str, dict[str, int]] = {}
    for experiment_id in (f"E{index}" for index in range(1, 10)):
        expected_summary_by_experiment[experiment_id] = {
            "new_cells": FULL_MATRIX_CELL_COUNTS.get(experiment_id, 0),
            "new_runs": expected_counts.get(experiment_id, 0),
            "reuse_entries": sum(
                entry["experiment_id"] == experiment_id
                for entry in source["reuse_analyses"]
            ),
        }
    expected_summary = {
        "new_cells": sum(FULL_MATRIX_CELL_COUNTS.values()),
        "new_runs": sum(expected_counts.values()),
        "by_experiment": expected_summary_by_experiment,
    }
    if source.get("matrix_summary") != expected_summary:
        raise ProtocolValidationError(
            "formal E1 shard source matrix_summary does not match its complete runs"
        )

    expected_dependencies = _reference_build_dependencies(source["runs"])
    if source.get("reference_build_dependencies") != expected_dependencies:
        raise ProtocolValidationError(
            "formal E1 shard source reference dependencies are not complete"
        )

    e1_runs = [run for run in source["runs"] if run["experiment_id"] == "E1"]
    expected_e1 = _expected_e1_keys(
        seed_stage, topologies=("homogeneous", "heterogeneous")
    )
    observed_e1 = [_e1_key(run) for run in e1_runs]
    if len(observed_e1) != len(set(observed_e1)) or set(observed_e1) != expected_e1:
        raise ProtocolValidationError(
            "formal E1 shard source lacks the complete frozen E1 Cartesian product"
        )
    for run in e1_runs:
        if (
            run["cluster"].get("node_count") != 20
            or run["workload"].get("topology") != run["cluster"].get("topology")
            or run["workload"].get("arrival_profile") != "steady"
            or run["workload"].get("qos_profile") != "mixed"
            or run["workload"].get("load_scale") != 1.0
            or run.get("variant") != "full"
        ):
            raise ProtocolValidationError(
                f"formal E1 shard source contains a noncanonical E1 run {run['run_id']}"
            )


def _lineage(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_run_id": run["run_id"],
        "source_run_spec_hash": run["run_spec_hash"],
        "source_cell_id": run["cell_id"],
        "source_method": run["method"],
        "source_variant": run.get("variant", "full"),
        "source_seed": run["seed"],
        "source_workload_spec_hash": run["workload_spec_hash"],
        "source_workload_tape_key": run["workload_tape"]["key"],
        "source_cluster_sha256": object_hash(run["cluster"]),
        "source_simulation_sha256": object_hash(run["simulation"]),
        "source_environment_sha256": object_hash(run["environment"]),
        "source_common_hpa_hash": run["common_hpa_hash"],
    }


def derive_formal_e1_homogeneous_shard(
    source_manifest_path: Path,
) -> dict[str, Any]:
    """Select the only permitted complete E1 homogeneous block."""

    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    _assert_complete_full_source(source)

    seeds = FORMAL_E1_SEEDS_BY_STAGE[source["seed_stage"]]
    expected_keys = _expected_e1_keys(source["seed_stage"], topologies=("homogeneous",))
    runs = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["experiment_id"] == "E1"
        and run["cluster"]["topology"] == "homogeneous"
        and run["cluster"]["node_count"] == 20
    ]
    observed_keys = [_e1_key(run) for run in runs]
    if (
        len(observed_keys) != len(set(observed_keys))
        or set(observed_keys) != expected_keys
    ):
        raise ProtocolValidationError(
            "source does not contain the complete formal E1 homogeneous block"
        )

    reuse_analyses = copy.deepcopy(source["reuse_analyses"])
    dependencies = _reference_build_dependencies(runs)
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["formal_results_eligible"] = True
    shard["runs"] = runs
    shard["reuse_analyses"] = reuse_analyses
    shard["reference_build_dependencies"] = dependencies
    shard["matrix_summary"] = _matrix_summary(runs, reuse_analyses)
    shard["formal_e1_homogeneous_shard"] = {
        "schema_version": FORMAL_E1_SHARD_SCHEMA,
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "protocol_id": source["protocol_id"],
            "run_count": len(source["runs"]),
            "seed_stage": source["seed_stage"],
        },
        "selection": {
            "experiment_id": "E1",
            "cluster_topology": "homogeneous",
            "node_count": 20,
            "methods": list(FORMAL_E1_METHODS),
            "loads": list(FORMAL_E1_LOADS),
            "seeds": list(seeds),
        },
        "selected_source_runs": [_lineage(run) for run in runs],
        "sealed_reuse_rules": [
            {
                "rule_id": entry["rule_id"],
                "rule_sha256": entry["rule_sha256"],
            }
            for entry in reuse_analyses
        ],
        "selected_run_count": len(runs),
        "selected_cell_count": len({run["cell_id"] for run in runs}),
        "selected_reference_build_count": len(dependencies),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_formal_e1_homogeneous_shard(
    source_manifest_path: Path, output_path: Path
) -> dict[str, Any]:
    if source_manifest_path.resolve() == output_path.resolve():
        raise ProtocolValidationError(
            "formal E1 shard output must differ from its source"
        )
    shard = derive_formal_e1_homogeneous_shard(source_manifest_path)
    write_json_atomic(output_path, shard)
    return shard
