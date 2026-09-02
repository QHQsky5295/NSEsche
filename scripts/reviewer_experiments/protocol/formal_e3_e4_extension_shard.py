"""Derive the frozen E3/E4 second-bank formal execution shard.

The bank-A E01--E10 E3/E4 block remains immutable.  This non-selectable shard
adds exactly the mandatory, disjoint E11--E20 observations for the same burst
and balanced-QoS cells:

* 300 physical E3 runs (ten methods by three bursts by ten seeds);
* 100 physical E4 runs (ten methods by ten seeds); and
* 40 offline-reference dependencies for the NSESche runs.

The source must be the complete, unsharded ``ci_extension`` E1--E7 manifest.
The shard seals source, workload-tape, common-runtime, and reuse-rule lineage;
it does not execute any simulator process.
"""

from __future__ import annotations

import copy
from itertools import product
from pathlib import Path
from typing import Any, Mapping

from .formal_e1_shard import (
    _assert_complete_full_source,
    _lineage,
    _matrix_summary,
    _reference_build_dependencies,
)
from .formal_e3_e4_shard import (
    FORMAL_E3_E4_CLUSTER,
    FORMAL_E3_E4_LOAD,
    FORMAL_E3_E4_PREREQUISITES,
    _assert_canonical_e3,
    _assert_canonical_e4,
)
from .matrix import BURSTS
from .schema import (
    FORMAL_E1_METHODS,
    FORMAL_E1_SEEDS_BY_STAGE,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


FORMAL_E3_E4_EXTENSION_SHARD_SCHEMA = "NSE_FORMAL_E3_E4_CI_EXTENSION_SHARD_V1"
FORMAL_E3_E4_EXTENSION_SHARD_MARKER = "formal_e3_e4_ci_extension_shard"
FORMAL_E3_E4_CI_EXTENSION_SHARD_SCHEMA = FORMAL_E3_E4_EXTENSION_SHARD_SCHEMA
FORMAL_E3_E4_CI_EXTENSION_SHARD_MARKER = FORMAL_E3_E4_EXTENSION_SHARD_MARKER
FORMAL_E3_E4_EXTENSION_SEEDS = tuple(FORMAL_E1_SEEDS_BY_STAGE["ci_extension"])
FORMAL_E3_E4_CI_EXTENSION_SEEDS = FORMAL_E3_E4_EXTENSION_SEEDS
# Kept as a local analogue of the E5/E6 extension constant for callers that
# use the generic precision-stage name.
FORMAL_CI_EXTENSION_SEEDS = FORMAL_E3_E4_EXTENSION_SEEDS


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _physical_key(run: Mapping[str, Any]) -> tuple[str, str, str, str]:
    experiment_id = str(run.get("experiment_id", ""))
    scenario = (
        str(run.get("workload", {}).get("burst_name", ""))
        if experiment_id == "E3"
        else "steady"
    )
    return (
        experiment_id,
        str(run.get("method", "")),
        scenario,
        str(run.get("seed", "")),
    )


def _expected_physical_keys() -> set[tuple[str, str, str, str]]:
    e3 = {
        ("E3", method, burst_name, seed)
        for method, burst_name, seed in product(
            FORMAL_E1_METHODS, tuple(BURSTS), FORMAL_E3_E4_EXTENSION_SEEDS
        )
    }
    e4 = {
        ("E4", method, "steady", seed)
        for method, seed in product(
            FORMAL_E1_METHODS, FORMAL_E3_E4_EXTENSION_SEEDS
        )
    }
    return e3 | e4


def _expected_selection() -> dict[str, Any]:
    return {
        "experiment_ids": ["E3", "E4"],
        "methods": list(FORMAL_E1_METHODS),
        "seeds": list(FORMAL_E3_E4_EXTENSION_SEEDS),
        "common_cluster": copy.deepcopy(FORMAL_E3_E4_CLUSTER),
        "base_load": FORMAL_E3_E4_LOAD,
        "qos_profile": "balanced",
        "E3": {
            "burst_scenarios": [
                {"name": name, **copy.deepcopy(spec)} for name, spec in BURSTS.items()
            ],
            "arrival_horizon_frames": 1000,
            "observation_horizon_frames": 1000,
            "total_frame": 4000,
        },
        "E4": {
            "arrival_profile": "steady",
            "arrival_horizon_frames": 1000,
            "observation_horizon_frames": 1000,
            "total_frame": 1000,
            "per_qos_breakdown_required": True,
        },
    }


def _validate_physical_shape(shard: Mapping[str, Any]) -> None:
    _require(
        shard.get("seed_stage") == "ci_extension",
        "formal E3/E4 extension shard requires seed_stage=ci_extension",
    )
    runs = shard.get("runs")
    _require(isinstance(runs, list), "formal E3/E4 extension runs must be an array")
    _require(
        len(runs) == 400,
        "formal E3/E4 extension shard must contain exactly 400 physical runs",
    )
    observed_keys = [_physical_key(run) for run in runs]
    _require(
        len(observed_keys) == len(set(observed_keys))
        and set(observed_keys) == _expected_physical_keys(),
        "formal E3/E4 extension physical Cartesian product is incomplete",
    )

    e3_count = 0
    e4_count = 0
    for run in runs:
        _require(
            run.get("method") in FORMAL_E1_METHODS
            and run.get("seed") in FORMAL_E3_E4_EXTENSION_SEEDS,
            "formal E3/E4 extension run has an unfrozen method/seed: "
            f"{run.get('run_id')}",
        )
        qos = run.get("simulator_experiment", {}).get("qos", {})
        _require(
            qos.get("enabled") is True and qos.get("class_assignment") == "balanced",
            "formal E3/E4 extension run does not enable balanced QoS: "
            f"{run.get('run_id')}",
        )
        if run.get("experiment_id") == "E3":
            e3_count += 1
            _assert_canonical_e3(run)
        else:
            e4_count += 1
            _assert_canonical_e4(run)
    _require(
        e3_count == 300 and e4_count == 100,
        "formal E3/E4 extension physical counts are not E3=300/E4=100",
    )

    dependencies = shard.get("reference_build_dependencies")
    _require(
        isinstance(dependencies, list) and len(dependencies) == 40,
        "formal E3/E4 extension reference dependency count must be 40",
    )
    _require(
        dependencies == _reference_build_dependencies(runs),
        "formal E3/E4 extension reference dependencies do not match the runs",
    )
    reference_runs = [run for run in runs if run.get("reference_dependency")]
    _require(
        len(reference_runs) == 40
        and all(run.get("method") == "sche_nash" for run in reference_runs),
        "only the 40 formal E3/E4 extension NSESche runs may require references",
    )

    marker = shard.get(FORMAL_E3_E4_EXTENSION_SHARD_MARKER)
    _require(isinstance(marker, Mapping), "formal E3/E4 extension marker is missing")
    _require(
        marker.get("schema_version") == FORMAL_E3_E4_EXTENSION_SHARD_SCHEMA
        and marker.get("selection") == _expected_selection()
        and marker.get("execution_prerequisites") == FORMAL_E3_E4_PREREQUISITES,
        "formal E3/E4 extension marker contract is not frozen",
    )
    _require(
        marker.get("selected_run_count") == 400
        and marker.get("selected_cell_count") == 40
        and marker.get("selected_e3_run_count") == 300
        and marker.get("selected_e4_run_count") == 100
        and marker.get("selected_reference_build_count") == 40
        and marker.get("selected_balanced_qos_run_count") == 400
        and marker.get("selected_faasrank_run_count") == 40,
        "formal E3/E4 extension marker counts are inconsistent",
    )


def derive_formal_e3_e4_ci_extension_shard(
    source_manifest_path: Path,
) -> dict[str, Any]:
    """Derive the only legal 400-run E11--E20 E3/E4 formal block."""

    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    _assert_complete_full_source(source)
    _require(
        source.get("seed_stage") == "ci_extension",
        "formal E3/E4 extension source must be the ci_extension full matrix",
    )

    runs = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run.get("experiment_id") in {"E3", "E4"}
    ]
    dependencies = _reference_build_dependencies(runs)
    reuse_rules = copy.deepcopy(source["reuse_analyses"])
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["formal_results_eligible"] = True
    shard["runs"] = runs
    shard["reuse_analyses"] = reuse_rules
    shard["reference_build_dependencies"] = dependencies
    shard["matrix_summary"] = _matrix_summary(runs, reuse_rules)
    shard[FORMAL_E3_E4_EXTENSION_SHARD_MARKER] = {
        "schema_version": FORMAL_E3_E4_EXTENSION_SHARD_SCHEMA,
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "protocol_id": source["protocol_id"],
            "run_count": len(source["runs"]),
            "seed_stage": source["seed_stage"],
        },
        "selection": _expected_selection(),
        "execution_prerequisites": copy.deepcopy(FORMAL_E3_E4_PREREQUISITES),
        "selected_source_runs": [_lineage(run) for run in runs],
        "sealed_reuse_rules": [
            {"rule_id": entry["rule_id"], "rule_sha256": entry["rule_sha256"]}
            for entry in reuse_rules
        ],
        "selected_run_count": len(runs),
        "selected_cell_count": len({run["cell_id"] for run in runs}),
        "selected_e3_run_count": sum(run["experiment_id"] == "E3" for run in runs),
        "selected_e4_run_count": sum(run["experiment_id"] == "E4" for run in runs),
        "selected_reference_build_count": len(dependencies),
        "selected_balanced_qos_run_count": sum(
            run["workload"].get("qos_profile") == "balanced" for run in runs
        ),
        "selected_faasrank_run_count": sum(
            run["method"] == "sche_FaaSRank" for run in runs
        ),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    _validate_physical_shape(shard)
    validate_manifest(shard)
    return shard


def write_formal_e3_e4_ci_extension_shard(
    source_manifest_path: Path, output_path: Path
) -> dict[str, Any]:
    """Write the formal E3/E4 bank-B shard atomically."""

    if source_manifest_path.resolve() == output_path.resolve():
        raise ProtocolValidationError(
            "formal E3/E4 extension shard output must differ from its source"
        )
    shard = derive_formal_e3_e4_ci_extension_shard(source_manifest_path)
    write_json_atomic(output_path, shard)
    return shard


__all__ = [
    "FORMAL_CI_EXTENSION_SEEDS",
    "FORMAL_E3_E4_CI_EXTENSION_SHARD_MARKER",
    "FORMAL_E3_E4_CI_EXTENSION_SHARD_SCHEMA",
    "FORMAL_E3_E4_CI_EXTENSION_SEEDS",
    "FORMAL_E3_E4_EXTENSION_SEEDS",
    "FORMAL_E3_E4_EXTENSION_SHARD_MARKER",
    "FORMAL_E3_E4_EXTENSION_SHARD_SCHEMA",
    "derive_formal_e3_e4_ci_extension_shard",
    "write_formal_e3_e4_ci_extension_shard",
]
