"""Derive the complete formal E2 weak-scaling execution shard.

E2 has only two physical execution sizes (100 and 500 nodes).  Its 20-node
point is an identity projection of the already completed homogeneous E1 block.
This module seals both sets at shard-creation time so analysis cannot silently
substitute a different E1 run set later.
"""

from __future__ import annotations

import copy
from itertools import product
from pathlib import Path
from typing import Any

from .formal_e1_shard import (
    _assert_complete_full_source,
    _lineage,
    _matrix_summary,
    _reference_build_dependencies,
)
from .schema import (
    FORMAL_E1_LOADS,
    FORMAL_E1_METHODS,
    FORMAL_E1_SEEDS_BY_STAGE,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


FORMAL_E2_SHARD_SCHEMA = "NSE_FORMAL_E2_WEAK_SCALING_SHARD_V1"
FORMAL_E2_SHARD_MARKER = "formal_e2_weak_scaling_shard"
FORMAL_E2_NODE_SCALES = ((100, 5.0), (500, 25.0))
E2_REUSE_RULE_ID = "E2_FROM_E1_20NODE_HOMOGENEOUS_V1"


def _e2_key(run: dict[str, Any]) -> tuple[str, str, int, str]:
    return (
        run["method"],
        run["workload"]["request_freq"],
        int(run["cluster"]["node_count"]),
        run["seed"],
    )


def _expected_e2_keys(seed_stage: str) -> set[tuple[str, str, int, str]]:
    return set(
        product(
            FORMAL_E1_METHODS,
            FORMAL_E1_LOADS,
            (100, 500),
            FORMAL_E1_SEEDS_BY_STAGE[seed_stage],
        )
    )


def _e1_reuse_lineage(run: dict[str, Any]) -> dict[str, Any]:
    return {
        **_lineage(run),
        "source_experiment_id": run["experiment_id"],
        "source_load": run["workload"]["request_freq"],
        "source_topology": run["cluster"]["topology"],
        "source_node_count": run["cluster"]["node_count"],
        "source_load_scale": run["workload"]["load_scale"],
    }


def derive_formal_e2_weak_scaling_shard(
    source_manifest_path: Path,
) -> dict[str, Any]:
    """Select the one legal E2 physical block and seal its E1 reuse source."""

    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    _assert_complete_full_source(source)
    seed_stage = source["seed_stage"]
    seeds = FORMAL_E1_SEEDS_BY_STAGE[seed_stage]

    runs = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["experiment_id"] == "E2"
    ]
    observed = [_e2_key(run) for run in runs]
    expected = _expected_e2_keys(seed_stage)
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ProtocolValidationError(
            "source does not contain the complete formal E2 weak-scaling block"
        )

    e1_reuse_runs = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["experiment_id"] == "E1"
        and run["cluster"]["topology"] == "homogeneous"
        and run["cluster"]["node_count"] == 20
    ]
    expected_e1_reuse = set(
        product(FORMAL_E1_METHODS, FORMAL_E1_LOADS, seeds)
    )
    observed_e1_reuse = {
        (run["method"], run["workload"]["request_freq"], run["seed"])
        for run in e1_reuse_runs
    }
    if len(e1_reuse_runs) != len(expected_e1_reuse) or observed_e1_reuse != expected_e1_reuse:
        raise ProtocolValidationError(
            "source lacks the complete homogeneous E1 20-node reuse block for E2"
        )

    reuse_rules = copy.deepcopy(source["reuse_analyses"])
    matching_rules = [
        entry for entry in reuse_rules if entry.get("rule_id") == E2_REUSE_RULE_ID
    ]
    if len(matching_rules) != 1:
        raise ProtocolValidationError("source lacks the unique sealed E2 reuse rule")
    reuse_rule = matching_rules[0]

    dependencies = _reference_build_dependencies(runs)
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["formal_results_eligible"] = True
    shard["runs"] = runs
    shard["reuse_analyses"] = reuse_rules
    shard["reference_build_dependencies"] = dependencies
    shard["matrix_summary"] = _matrix_summary(runs, reuse_rules)
    shard[FORMAL_E2_SHARD_MARKER] = {
        "schema_version": FORMAL_E2_SHARD_SCHEMA,
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "protocol_id": source["protocol_id"],
            "run_count": len(source["runs"]),
            "seed_stage": seed_stage,
        },
        "selection": {
            "experiment_id": "E2",
            "cluster_topology": "homogeneous",
            "node_scales": [
                {"node_count": node_count, "load_scale": load_scale}
                for node_count, load_scale in FORMAL_E2_NODE_SCALES
            ],
            "methods": list(FORMAL_E1_METHODS),
            "loads": list(FORMAL_E1_LOADS),
            "seeds": list(seeds),
        },
        "selected_source_runs": [_lineage(run) for run in runs],
        "e1_reuse_source_runs": [
            _e1_reuse_lineage(run) for run in e1_reuse_runs
        ],
        "sealed_e1_reuse_rule": {
            "rule_id": reuse_rule["rule_id"],
            "rule_sha256": reuse_rule["rule_sha256"],
        },
        "sealed_reuse_rules": [
            {"rule_id": entry["rule_id"], "rule_sha256": entry["rule_sha256"]}
            for entry in reuse_rules
        ],
        "selected_run_count": len(runs),
        "selected_cell_count": len({run["cell_id"] for run in runs}),
        "selected_reference_build_count": len(dependencies),
        "e1_reuse_source_run_count": len(e1_reuse_runs),
        "e1_reuse_source_cell_count": len(
            {run["cell_id"] for run in e1_reuse_runs}
        ),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_formal_e2_weak_scaling_shard(
    source_manifest_path: Path, output_path: Path
) -> dict[str, Any]:
    if source_manifest_path.resolve() == output_path.resolve():
        raise ProtocolValidationError(
            "formal E2 shard output must differ from its source"
        )
    shard = derive_formal_e2_weak_scaling_shard(source_manifest_path)
    write_json_atomic(output_path, shard)
    return shard
