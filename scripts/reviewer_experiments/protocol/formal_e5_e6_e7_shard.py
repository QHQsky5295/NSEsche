"""Build the frozen initial E5/E6/E7 formal execution shard.

The combined shard deliberately contains only the *physical* initial runs for
the three experiments.  Points which are already available from the completed
20-node heterogeneous E1 comparison are represented by sealed, role-specific
lineage lists instead of being executed again:

* E5 full NSESche: 30 source runs (three loads, E01--E10);
* E6 original placement methods: 200 source runs (ten methods, middle/high,
  E01--E10); and
* E7 load-specific centre points: 30 source runs (three loads, E01--E10).

The source is the immutable complete initial E1--E7 manifest.  The shard does
not invent a second workload or runtime contract.  A later merge/export step
can compare the sealed stable keys and hashes with the completed E1
heterogeneous ready manifest and canonical records.

This module intentionally does not register a CLI command or modify the shared
schema.  The protocol integration agent adds the marker to the common entry
points after this core has been reviewed.
"""

from __future__ import annotations

import copy
from collections import Counter
from itertools import product
from pathlib import Path
from typing import Any, Mapping

from .formal_e1_shard import (
    _assert_complete_full_source,
    _lineage,
    _matrix_summary,
    _reference_build_dependencies,
)
from .matrix import ABLATIONS, LOADS
from .schema import (
    FORMAL_E1_METHODS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


FORMAL_E5_E6_E7_SHARD_SCHEMA = "NSE_FORMAL_E5_E6_E7_INITIAL_SHARD_V1"
FORMAL_E5_E6_E7_SHARD_MARKER = "formal_e5_e6_e7_initial_shard"
FORMAL_INITIAL_SEEDS = tuple(f"E{index:02d}" for index in range(1, 11))
FORMAL_E7_CENTRE_SEEDS = FORMAL_INITIAL_SEEDS
FORMAL_E6_METHODS = ("cp_br", "onsocmax")
FORMAL_E6_ORIGINAL_METHODS = tuple(FORMAL_E1_METHODS)
FORMAL_E7_AXIAL_VARIANTS = (
    "price_minus",
    "price_plus",
    "quality_minus",
    "quality_plus",
)
FORMAL_E5_FULL_REUSE_RULE = "E5_FULL_FROM_E1_NSESCHE_V1"
FORMAL_E6_ORIGINAL_REUSE_RULE = "E6_ORIGINAL_METHODS_FROM_E1_V1"
FORMAL_E7_CENTRE_REUSE_RULE = "E7_CENTRES_FROM_E1_NSESCHE_V1"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _run_key(run: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    """Return the stable physical key used by the frozen matrix."""

    return (
        str(run.get("experiment_id", "")),
        str(run.get("method", "")),
        str(run.get("variant", "full")),
        str(run.get("workload", {}).get("request_freq", "")),
        str(run.get("seed", "")),
    )


def _e1_heterogeneous_key(run: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(run.get("method", "")),
        str(run.get("workload", {}).get("request_freq", "")),
        str(run.get("seed", "")),
    )


def _e1_lineage(run: Mapping[str, Any], *, target: str, rule_id: str) -> dict[str, Any]:
    """Add stable workload/load fields to the shared E1 lineage shape."""

    return {
        **_lineage(dict(run)),
        "source_experiment_id": "E1",
        "source_load": run["workload"]["request_freq"],
        "source_topology": run["cluster"]["topology"],
        "source_node_count": int(run["cluster"]["node_count"]),
        "source_load_scale": float(run["workload"]["load_scale"]),
        "target_experiment_id": target,
        "reuse_rule_id": rule_id,
    }


def _source_rule(source: Mapping[str, Any], rule_id: str) -> dict[str, Any]:
    rules = [
        entry
        for entry in source.get("reuse_analyses", [])
        if entry.get("rule_id") == rule_id
    ]
    _require(len(rules) == 1, f"source lacks unique sealed reuse rule {rule_id}")
    rule = rules[0]
    return {"rule_id": rule["rule_id"], "rule_sha256": rule["rule_sha256"]}


def _select_e1_heterogeneous(
    source: Mapping[str, Any]
) -> dict[tuple[str, str, str], dict[str, Any]]:
    selected = {
        _e1_heterogeneous_key(run): run
        for run in source["runs"]
        if run.get("experiment_id") == "E1"
        and run.get("cluster", {}).get("topology") == "heterogeneous"
        and int(run.get("cluster", {}).get("node_count", -1)) == 20
    }
    expected = {
        (method, load, seed)
        for method in FORMAL_E1_METHODS
        for load in LOADS
        for seed in FORMAL_INITIAL_SEEDS
    }
    _require(
        set(selected) == expected and len(selected) == 300,
        "source lacks the complete initial heterogeneous E1 product",
    )
    return selected


def _select_reuse_lineage(
    source: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    e1 = _select_e1_heterogeneous(source)
    selections = {
        "E5": [
            ("sche_nash", load, seed) for load in LOADS for seed in FORMAL_INITIAL_SEEDS
        ],
        "E6": [
            (method, load, seed)
            for method in FORMAL_E6_ORIGINAL_METHODS
            for load in ("middle", "high")
            for seed in FORMAL_INITIAL_SEEDS
        ],
        "E7": [
            ("sche_nash", load, seed)
            for load in LOADS
            for seed in FORMAL_E7_CENTRE_SEEDS
        ],
    }
    rule_ids = {
        "E5": FORMAL_E5_FULL_REUSE_RULE,
        "E6": FORMAL_E6_ORIGINAL_REUSE_RULE,
        "E7": FORMAL_E7_CENTRE_REUSE_RULE,
    }
    lineage: dict[str, list[dict[str, Any]]] = {}
    for target, keys in selections.items():
        rows: list[dict[str, Any]] = []
        for key in keys:
            run = e1.get(key)
            _require(run is not None, f"missing E1 reuse source {target}:{key}")
            rows.append(_e1_lineage(run, target=target, rule_id=rule_ids[target]))
        lineage[target] = rows
    _require(len(lineage["E5"]) == 30, "E5 full reuse lineage must contain 30 runs")
    _require(
        len(lineage["E6"]) == 200, "E6 original reuse lineage must contain 200 runs"
    )
    _require(len(lineage["E7"]) == 30, "E7 centre reuse lineage must contain 30 runs")
    return lineage


def _validate_physical_shape(shard: Mapping[str, Any]) -> None:
    """Validate the combined shard without depending on shared schema edits."""

    _require(
        shard.get("seed_stage") == "initial",
        "combined E5/E6/E7 shard requires seed_stage=initial",
    )
    runs = shard.get("runs")
    _require(isinstance(runs, list), "combined shard runs must be an array")
    _require(len(runs) == 280, "combined shard must contain exactly 280 physical runs")
    keys = [_run_key(run) for run in runs]
    _require(
        len(keys) == len(set(keys)),
        "combined shard contains duplicate physical run keys",
    )

    e5 = [run for run in runs if run.get("experiment_id") == "E5"]
    e6 = [run for run in runs if run.get("experiment_id") == "E6"]
    e7 = [run for run in runs if run.get("experiment_id") == "E7"]
    _require(
        len(e5) == 120 and len(e6) == 40 and len(e7) == 120,
        "E5/E6/E7 physical counts are not 120/40/120",
    )

    expected_e5 = {
        ("E5", "sche_nash", ablation, load, seed)
        for ablation in ABLATIONS
        for load in LOADS
        for seed in FORMAL_INITIAL_SEEDS
    }
    expected_e6 = {
        ("E6", method, "full", load, seed)
        for method in FORMAL_E6_METHODS
        for load in ("middle", "high")
        for seed in FORMAL_INITIAL_SEEDS
    }
    expected_e7 = {
        ("E7", "sche_nash", variant, load, seed)
        for variant in FORMAL_E7_AXIAL_VARIANTS
        for load in LOADS
        for seed in FORMAL_E7_CENTRE_SEEDS
    }
    _require(
        {_run_key(run) for run in e5} == expected_e5,
        "E5 physical Cartesian product is incomplete",
    )
    _require(
        {_run_key(run) for run in e6} == expected_e6,
        "E6 physical Cartesian product is incomplete",
    )
    _require(
        len(expected_e7) == 120, "E7 physical axial-neighbour product is incomplete"
    )
    _require(
        {_run_key(run) for run in e7} == expected_e7,
        "E7 physical product contains duplicate or malformed cells",
    )
    for run in [*e5, *e6, *e7]:
        _require(
            run.get("cluster") == {"node_count": 20, "topology": "heterogeneous"}
            and run.get("workload", {}).get("topology") == "heterogeneous"
            and run.get("workload", {}).get("arrival_profile") == "steady"
            and run.get("workload", {}).get("qos_profile") == "mixed"
            and float(run.get("workload", {}).get("load_scale", -1.0)) == 1.0,
            f"physical {run.get('experiment_id')} run does not use the common heterogeneous steady contract: {run.get('run_id')}",
        )

    dependencies = shard.get("reference_build_dependencies")
    _require(
        isinstance(dependencies, list) and len(dependencies) == 250,
        "reference dependency count must be 250",
    )
    expected_dependency_keys = {
        run["reference_dependency"]["key"]
        for run in runs
        if run.get("reference_dependency") is not None
    }
    _require(
        {dependency.get("key") for dependency in dependencies}
        == expected_dependency_keys
        and len(expected_dependency_keys) == 250,
        "reference dependencies do not match the physical E5/E6/E7 runs",
    )
    policies = [run for run in e5 if run.get("variant") == "no_coordination"]
    _require(len(policies) == 30, "E5 no_coordination must contain 30 runs")
    _require(
        all(
            run.get("reference_policy", {}).get("status") == "not_required"
            for run in policies
        ),
        "E5 no_coordination must not request references",
    )

    marker = shard.get(FORMAL_E5_E6_E7_SHARD_MARKER)
    _require(isinstance(marker, Mapping), "combined shard marker is missing")
    _require(
        marker.get("selected_physical_run_count") == 280,
        "marker physical count mismatch",
    )
    _require(
        marker.get("reference_build_count") == 250, "marker reference count mismatch"
    )
    reuse = marker.get("e1_reuse_lineage")
    _require(isinstance(reuse, Mapping), "E1 reuse lineage map is missing")
    _require(len(reuse.get("E5", [])) == 30, "marker E5 reuse count mismatch")
    _require(len(reuse.get("E6", [])) == 200, "marker E6 reuse count mismatch")
    _require(len(reuse.get("E7", [])) == 30, "marker E7 reuse count mismatch")
    _require(
        marker.get("e1_reuse_projection_count") == 260,
        "marker projection count mismatch",
    )
    _require(
        marker.get("e1_reuse_unique_source_run_count") == 210,
        "marker unique E1 source count mismatch",
    )


def _validate_with_available_schema(shard: dict[str, Any]) -> None:
    """Use common schema validation once the integration marker is registered."""

    _validate_physical_shape(shard)
    # During the isolated-core phase the common schema intentionally does not
    # know this marker yet.  The integration agent adds it to FORMAL_SHARD_MARKERS
    # and the normal validator then becomes authoritative automatically.
    try:
        from .schema import FORMAL_SHARD_MARKERS

        if FORMAL_E5_E6_E7_SHARD_MARKER in FORMAL_SHARD_MARKERS:
            validate_manifest(shard)
    except ImportError:
        pass


def validate_e1_reuse_lineage(
    shard: Mapping[str, Any], e1_heterogeneous_manifest: Mapping[str, Any]
) -> None:
    """Check the sealed reuse roles against a completed formal E1 hetero shard.

    E1 run IDs and run-spec hashes may change when tapes, frozen models, and
    offline references are bound.  The stable source cell/seed identity and
    the immutable workload, tape, cluster, simulation, environment, and HPA
    hashes must not change.  This is the core-side merge contract; a future
    exporter can additionally verify canonical result/QC files.
    """

    marker = shard.get(FORMAL_E5_E6_E7_SHARD_MARKER)
    _require(isinstance(marker, Mapping), "combined shard marker is missing")
    e1_marker = e1_heterogeneous_manifest.get("formal_e1_heterogeneous_shard")
    _require(
        isinstance(e1_marker, Mapping),
        "supplied E1 manifest is not a formal heterogeneous shard",
    )
    current: dict[tuple[str, str, str], dict[str, Any]] = {}
    for run in e1_heterogeneous_manifest.get("runs", []):
        if (
            run.get("experiment_id") != "E1"
            or run.get("cluster", {}).get("topology") != "heterogeneous"
            or int(run.get("cluster", {}).get("node_count", -1)) != 20
        ):
            continue
        key = (
            str(run.get("method", "")),
            str(run.get("workload", {}).get("request_freq", "")),
            str(run.get("seed", "")),
        )
        _require(key not in current, f"duplicate E1 heterogeneous lineage key {key}")
        current[key] = {
            "source_variant": run.get("variant", "full"),
            "source_workload_spec_hash": run.get("workload_spec_hash"),
            "source_workload_tape_key": run.get("workload_tape", {}).get("key"),
            "source_cluster_sha256": object_hash(run.get("cluster")),
            "source_simulation_sha256": object_hash(run.get("simulation")),
            "source_environment_sha256": object_hash(run.get("environment")),
            "source_common_hpa_hash": run.get("common_hpa_hash"),
            "source_topology": run.get("cluster", {}).get("topology"),
        }
    _require(
        set(current)
        >= {
            (method, load, seed)
            for method in FORMAL_E1_METHODS
            for load in LOADS
            for seed in FORMAL_INITIAL_SEEDS
        },
        "supplied E1 heterogeneous manifest lacks initial reuse product",
    )
    for role, rows in marker["e1_reuse_lineage"].items():
        for index, row in enumerate(rows):
            key = (
                str(row.get("source_method", "")),
                str(row.get("source_load", "")),
                str(row.get("source_seed", "")),
            )
            existing = current.get(key)
            _require(
                existing is not None,
                f"E1 reuse lineage {role}[{index}] has no supplied E1 source",
            )
            for field in (
                "source_variant",
                "source_workload_spec_hash",
                "source_workload_tape_key",
                "source_cluster_sha256",
                "source_simulation_sha256",
                "source_environment_sha256",
                "source_common_hpa_hash",
            ):
                _require(
                    row.get(field) == existing.get(field),
                    f"E1 reuse lineage {role}[{index}] differs in {field}",
                )
            _require(
                existing.get("source_topology") == "heterogeneous",
                f"E1 reuse lineage {role}[{index}] is not heterogeneous",
            )


def derive_formal_e5_e6_e7_initial_shard(source_manifest_path: Path) -> dict[str, Any]:
    """Derive the frozen 280-run initial E5/E6/E7 block."""

    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    _assert_complete_full_source(source)
    _require(
        source.get("seed_stage") == "initial",
        "combined shard source must be the initial full matrix",
    )

    runs = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run.get("experiment_id") in {"E5", "E6", "E7"}
    ]
    reuse_lineage = _select_reuse_lineage(source)
    dependencies = _reference_build_dependencies(runs)
    reuse_rules = copy.deepcopy(source["reuse_analyses"])
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["formal_results_eligible"] = True
    shard["runs"] = runs
    shard["reuse_analyses"] = reuse_rules
    shard["reference_build_dependencies"] = dependencies
    shard["matrix_summary"] = _matrix_summary(runs, reuse_rules)

    source_lineage = {target: rows for target, rows in reuse_lineage.items()}
    unique_source_ids = {
        entry["source_run_id"] for rows in source_lineage.values() for entry in rows
    }
    marker = {
        "schema_version": FORMAL_E5_E6_E7_SHARD_SCHEMA,
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "protocol_id": source["protocol_id"],
            "run_count": len(source["runs"]),
            "seed_stage": source["seed_stage"],
        },
        "selection": {
            "experiment_ids": ["E5", "E6", "E7"],
            "physical_runs": {
                "E5": {
                    "variants": list(ABLATIONS),
                    "loads": list(LOADS),
                    "seeds": list(FORMAL_INITIAL_SEEDS),
                },
                "E6": {
                    "methods": list(FORMAL_E6_METHODS),
                    "loads": ["middle", "high"],
                    "seeds": list(FORMAL_INITIAL_SEEDS),
                },
                "E7": {
                    "axial_neighbours_per_load": 4,
                    "loads": list(LOADS),
                    "seeds": list(FORMAL_E7_CENTRE_SEEDS),
                },
            },
            "common_cluster": {"node_count": 20, "topology": "heterogeneous"},
        },
        "selected_source_runs": [_lineage(run) for run in runs],
        "e1_reuse_lineage": source_lineage,
        "sealed_reuse_rules": [
            {"rule_id": entry["rule_id"], "rule_sha256": entry["rule_sha256"]}
            for entry in reuse_rules
        ],
        "sealed_e1_reuse_rules": {
            "E5": _source_rule(source, FORMAL_E5_FULL_REUSE_RULE),
            "E6": _source_rule(source, FORMAL_E6_ORIGINAL_REUSE_RULE),
            "E7": _source_rule(source, FORMAL_E7_CENTRE_REUSE_RULE),
        },
        "selected_physical_run_count": len(runs),
        "selected_physical_cell_count": len({run["cell_id"] for run in runs}),
        "reference_build_count": len(dependencies),
        "e1_reuse_projection_count": sum(len(rows) for rows in source_lineage.values()),
        "e1_reuse_unique_source_run_count": len(unique_source_ids),
    }
    shard[FORMAL_E5_E6_E7_SHARD_MARKER] = marker
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    _validate_with_available_schema(shard)
    return shard


def write_formal_e5_e6_e7_initial_shard(
    source_manifest_path: Path, output_path: Path
) -> dict[str, Any]:
    """Write the combined initial shard atomically."""

    if source_manifest_path.resolve() == output_path.resolve():
        raise ProtocolValidationError(
            "combined E5/E6/E7 shard output must differ from its source"
        )
    shard = derive_formal_e5_e6_e7_initial_shard(source_manifest_path)
    write_json_atomic(output_path, shard)
    return shard


__all__ = [
    "FORMAL_E5_E6_E7_SHARD_SCHEMA",
    "FORMAL_E5_E6_E7_SHARD_MARKER",
    "FORMAL_INITIAL_SEEDS",
    "FORMAL_E7_CENTRE_SEEDS",
    "FORMAL_E7_AXIAL_VARIANTS",
    "FORMAL_E6_METHODS",
    "derive_formal_e5_e6_e7_initial_shard",
    "write_formal_e5_e6_e7_initial_shard",
    "validate_e1_reuse_lineage",
]
