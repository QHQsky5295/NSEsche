"""Build the frozen E5/E6 CI-extension formal execution shard.

The initial E5/E6/E7 block is immutable and remains the authoritative E01--E10
artifact.  When the frozen precision rule requests ``n=20``, this shard adds
only the disjoint E11--E20 observations required for E5 and E6:

* 120 physical E5 ablation runs;
* 40 physical E6 welfare-comparator runs; and
* 230 role projections of 210 unique E1 heterogeneous source runs.

E7 is intentionally absent because its protocol-fixed five-seed sensitivity
check has no CI-extension stage.  The source must be the complete, unsharded
``ci_extension`` E1--E7 manifest, so this entry point cannot selectively add
methods, loads, variants, or seeds after seeing the initial results.
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
from .formal_e5_e6_e7_shard import (
    FORMAL_E5_FULL_REUSE_RULE,
    FORMAL_E6_METHODS,
    FORMAL_E6_ORIGINAL_METHODS,
    FORMAL_E6_ORIGINAL_REUSE_RULE,
)
from .matrix import ABLATIONS, LOADS
from .schema import (
    FORMAL_E1_METHODS,
    FORMAL_E1_SEEDS_BY_STAGE,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


FORMAL_E5_E6_EXTENSION_SHARD_SCHEMA = "NSE_FORMAL_E5_E6_CI_EXTENSION_SHARD_V1"
FORMAL_E5_E6_EXTENSION_SHARD_MARKER = "formal_e5_e6_ci_extension_shard"
FORMAL_CI_EXTENSION_SEEDS = tuple(FORMAL_E1_SEEDS_BY_STAGE["ci_extension"])


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _run_key(run: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(run.get("experiment_id", "")),
        str(run.get("method", "")),
        str(run.get("variant", "full")),
        str(run.get("workload", {}).get("request_freq", "")),
        str(run.get("seed", "")),
    )


def _e1_key(run: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(run.get("method", "")),
        str(run.get("workload", {}).get("request_freq", "")),
        str(run.get("seed", "")),
    )


def _e1_lineage(run: Mapping[str, Any], *, target: str, rule_id: str) -> dict[str, Any]:
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
    return {"rule_id": rules[0]["rule_id"], "rule_sha256": rules[0]["rule_sha256"]}


def _select_e1_heterogeneous(
    source: Mapping[str, Any],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    selected = {
        _e1_key(run): run
        for run in source["runs"]
        if run.get("experiment_id") == "E1"
        and run.get("cluster", {}).get("topology") == "heterogeneous"
        and int(run.get("cluster", {}).get("node_count", -1)) == 20
    }
    expected = set(product(FORMAL_E1_METHODS, LOADS, FORMAL_CI_EXTENSION_SEEDS))
    _require(
        set(selected) == expected and len(selected) == 300,
        "source lacks the complete CI-extension heterogeneous E1 product",
    )
    return selected


def _select_reuse_lineage(
    source: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    e1 = _select_e1_heterogeneous(source)
    selections = {
        "E5": [
            ("sche_nash", load, seed)
            for load in LOADS
            for seed in FORMAL_CI_EXTENSION_SEEDS
        ],
        "E6": [
            (method, load, seed)
            for method in FORMAL_E6_ORIGINAL_METHODS
            for load in ("middle", "high")
            for seed in FORMAL_CI_EXTENSION_SEEDS
        ],
    }
    rule_ids = {
        "E5": FORMAL_E5_FULL_REUSE_RULE,
        "E6": FORMAL_E6_ORIGINAL_REUSE_RULE,
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
        len(lineage["E6"]) == 200,
        "E6 original reuse lineage must contain 200 runs",
    )
    return lineage


def _validate_physical_shape(shard: Mapping[str, Any]) -> None:
    _require(
        shard.get("seed_stage") == "ci_extension",
        "E5/E6 extension shard requires seed_stage=ci_extension",
    )
    runs = shard.get("runs")
    _require(isinstance(runs, list), "E5/E6 extension runs must be an array")
    _require(len(runs) == 160, "E5/E6 extension must contain 160 physical runs")
    keys = [_run_key(run) for run in runs]
    _require(len(keys) == len(set(keys)), "E5/E6 extension repeats a physical run")

    e5 = [run for run in runs if run.get("experiment_id") == "E5"]
    e6 = [run for run in runs if run.get("experiment_id") == "E6"]
    _require(
        len(e5) == 120 and len(e6) == 40,
        "E5/E6 extension physical counts are not 120/40",
    )
    _require(
        not any(run.get("experiment_id") == "E7" for run in runs),
        "E7 must not appear in the CI-extension shard",
    )
    expected_e5 = {
        ("E5", "sche_nash", ablation, load, seed)
        for ablation in ABLATIONS
        for load in LOADS
        for seed in FORMAL_CI_EXTENSION_SEEDS
    }
    expected_e6 = {
        ("E6", method, "full", load, seed)
        for method in FORMAL_E6_METHODS
        for load in ("middle", "high")
        for seed in FORMAL_CI_EXTENSION_SEEDS
    }
    _require(
        {_run_key(run) for run in e5} == expected_e5,
        "E5 CI-extension Cartesian product is incomplete",
    )
    _require(
        {_run_key(run) for run in e6} == expected_e6,
        "E6 CI-extension Cartesian product is incomplete",
    )
    for run in runs:
        _require(
            run.get("cluster") == {"node_count": 20, "topology": "heterogeneous"}
            and run.get("workload", {}).get("topology") == "heterogeneous"
            and run.get("workload", {}).get("arrival_profile") == "steady"
            and run.get("workload", {}).get("qos_profile") == "mixed"
            and float(run.get("workload", {}).get("load_scale", -1.0)) == 1.0,
            f"physical {run.get('experiment_id')} run changes the common heterogeneous steady contract: {run.get('run_id')}",
        )

    dependencies = shard.get("reference_build_dependencies")
    _require(
        isinstance(dependencies, list) and len(dependencies) == 130,
        "E5/E6 extension reference dependency count must be 130",
    )
    expected_dependency_keys = {
        run["reference_dependency"]["key"]
        for run in runs
        if run.get("reference_dependency") is not None
    }
    _require(
        {dependency.get("key") for dependency in dependencies}
        == expected_dependency_keys
        and len(expected_dependency_keys) == 130,
        "reference dependencies do not match the physical E5/E6 extension runs",
    )
    no_coordination = [run for run in e5 if run.get("variant") == "no_coordination"]
    _require(len(no_coordination) == 30, "E5 no_coordination must contain 30 runs")
    _require(
        all(
            run.get("reference_policy", {}).get("status") == "not_required"
            for run in no_coordination
        ),
        "E5 no_coordination must not request references",
    )

    marker = shard.get(FORMAL_E5_E6_EXTENSION_SHARD_MARKER)
    _require(isinstance(marker, Mapping), "E5/E6 extension marker is missing")
    _require(
        marker.get("selected_physical_run_count") == 160,
        "extension marker physical count mismatch",
    )
    _require(
        marker.get("reference_build_count") == 130,
        "extension marker reference count mismatch",
    )
    reuse = marker.get("e1_reuse_lineage")
    _require(isinstance(reuse, Mapping), "E1 extension reuse lineage is missing")
    _require(len(reuse.get("E5", [])) == 30, "marker E5 reuse count mismatch")
    _require(len(reuse.get("E6", [])) == 200, "marker E6 reuse count mismatch")
    _require(set(reuse) == {"E5", "E6"}, "extension reuse roles must be E5/E6 only")
    _require(
        marker.get("e1_reuse_projection_count") == 230,
        "extension marker projection count mismatch",
    )
    _require(
        marker.get("e1_reuse_unique_source_run_count") == 210,
        "extension marker unique E1 source count mismatch",
    )


def validate_e1_ci_extension_reuse_lineage(
    shard: Mapping[str, Any], e1_heterogeneous_manifest: Mapping[str, Any]
) -> None:
    """Match the sealed E11--E20 role projections to an E1 hetero shard."""

    marker = shard.get(FORMAL_E5_E6_EXTENSION_SHARD_MARKER)
    _require(isinstance(marker, Mapping), "E5/E6 extension marker is missing")
    e1_marker = e1_heterogeneous_manifest.get("formal_e1_heterogeneous_shard")
    _require(
        isinstance(e1_marker, Mapping),
        "supplied E1 manifest is not a formal heterogeneous shard",
    )
    _require(
        e1_heterogeneous_manifest.get("seed_stage") == "ci_extension",
        "supplied E1 manifest is not the CI-extension stage",
    )
    current: dict[tuple[str, str, str], dict[str, Any]] = {}
    for run in e1_heterogeneous_manifest.get("runs", []):
        if (
            run.get("experiment_id") != "E1"
            or run.get("cluster", {}).get("topology") != "heterogeneous"
            or int(run.get("cluster", {}).get("node_count", -1)) != 20
        ):
            continue
        key = _e1_key(run)
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
    expected = set(product(FORMAL_E1_METHODS, LOADS, FORMAL_CI_EXTENSION_SEEDS))
    _require(
        set(current) == expected,
        "supplied E1 heterogeneous manifest lacks the CI-extension reuse product",
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
                f"E1 extension reuse lineage {role}[{index}] has no supplied source",
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
                    f"E1 extension reuse lineage {role}[{index}] differs in {field}",
                )
            _require(
                existing.get("source_topology") == "heterogeneous",
                f"E1 extension reuse lineage {role}[{index}] is not heterogeneous",
            )


def derive_formal_e5_e6_ci_extension_shard(
    source_manifest_path: Path,
) -> dict[str, Any]:
    """Derive the result-blind 160-run E11--E20 E5/E6 block."""

    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    _assert_complete_full_source(source)
    _require(
        source.get("seed_stage") == "ci_extension",
        "E5/E6 extension source must be the ci_extension full matrix",
    )

    runs = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run.get("experiment_id") in {"E5", "E6"}
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

    unique_source_ids = {
        entry["source_run_id"] for rows in reuse_lineage.values() for entry in rows
    }
    marker = {
        "schema_version": FORMAL_E5_E6_EXTENSION_SHARD_SCHEMA,
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "protocol_id": source["protocol_id"],
            "run_count": len(source["runs"]),
            "seed_stage": source["seed_stage"],
        },
        "selection": {
            "experiment_ids": ["E5", "E6"],
            "physical_runs": {
                "E5": {
                    "variants": list(ABLATIONS),
                    "loads": list(LOADS),
                    "seeds": list(FORMAL_CI_EXTENSION_SEEDS),
                },
                "E6": {
                    "methods": list(FORMAL_E6_METHODS),
                    "loads": ["middle", "high"],
                    "seeds": list(FORMAL_CI_EXTENSION_SEEDS),
                },
            },
            "common_cluster": {"node_count": 20, "topology": "heterogeneous"},
            "e7_extension_run_count": 0,
        },
        "selected_source_runs": [_lineage(run) for run in runs],
        "e1_reuse_lineage": reuse_lineage,
        "sealed_reuse_rules": [
            {"rule_id": entry["rule_id"], "rule_sha256": entry["rule_sha256"]}
            for entry in reuse_rules
        ],
        "sealed_e1_reuse_rules": {
            "E5": _source_rule(source, FORMAL_E5_FULL_REUSE_RULE),
            "E6": _source_rule(source, FORMAL_E6_ORIGINAL_REUSE_RULE),
        },
        "selected_physical_run_count": len(runs),
        "selected_physical_cell_count": len({run["cell_id"] for run in runs}),
        "reference_build_count": len(dependencies),
        "e1_reuse_projection_count": sum(len(rows) for rows in reuse_lineage.values()),
        "e1_reuse_unique_source_run_count": len(unique_source_ids),
    }
    shard[FORMAL_E5_E6_EXTENSION_SHARD_MARKER] = marker
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    _validate_physical_shape(shard)
    validate_manifest(shard)
    return shard


def write_formal_e5_e6_ci_extension_shard(
    source_manifest_path: Path, output_path: Path
) -> dict[str, Any]:
    """Write the formal E5/E6 CI-extension shard atomically."""

    if source_manifest_path.resolve() == output_path.resolve():
        raise ProtocolValidationError(
            "E5/E6 extension shard output must differ from its source"
        )
    shard = derive_formal_e5_e6_ci_extension_shard(source_manifest_path)
    write_json_atomic(output_path, shard)
    return shard


__all__ = [
    "FORMAL_E5_E6_EXTENSION_SHARD_SCHEMA",
    "FORMAL_E5_E6_EXTENSION_SHARD_MARKER",
    "FORMAL_CI_EXTENSION_SEEDS",
    "derive_formal_e5_e6_ci_extension_shard",
    "write_formal_e5_e6_ci_extension_shard",
    "validate_e1_ci_extension_reuse_lineage",
]
