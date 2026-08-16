"""Derive the frozen initial formal E3/E4 execution shard.

E3 and E4 share the same 20-node heterogeneous, middle-load, balanced-QoS
runtime.  E3 replaces the steady arrival tape with each of the three frozen
event-count-preserving burst transforms and drains the admitted cohort through
frame 4000.  E4 keeps the steady tape and the 1000-frame observation horizon.

The shard is deliberately non-selectable: it contains all ten methods and
E01--E10 for both experiments.  It seals the full-source lineage, common reuse
rules, execution prerequisites, and the exact offline-reference dependency set
without starting any simulator process.
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
from .matrix import BURSTS
from .schema import (
    FORMAL_E1_METHODS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


FORMAL_E3_E4_SHARD_SCHEMA = "NSE_FORMAL_E3_E4_INITIAL_SHARD_V1"
FORMAL_E3_E4_SHARD_MARKER = "formal_e3_e4_initial_shard"
FORMAL_E3_E4_SEEDS = tuple(f"E{index:02d}" for index in range(1, 11))
FORMAL_E3_E4_LOAD = "middle"
FORMAL_E3_E4_CLUSTER = {"node_count": 20, "topology": "heterogeneous"}
FORMAL_E3_E4_PREREQUISITES = {
    "workload_tapes": "required_before_execution",
    "sla_targets": "required_before_execution_from_E1_pilot_artifact",
    "faasrank_model": "required_before_execution",
    "offline_references": "required_before_execution",
}


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
            FORMAL_E1_METHODS, tuple(BURSTS), FORMAL_E3_E4_SEEDS
        )
    }
    e4 = {
        ("E4", method, "steady", seed)
        for method, seed in product(FORMAL_E1_METHODS, FORMAL_E3_E4_SEEDS)
    }
    return e3 | e4


def _expected_selection() -> dict[str, Any]:
    return {
        "experiment_ids": ["E3", "E4"],
        "methods": list(FORMAL_E1_METHODS),
        "seeds": list(FORMAL_E3_E4_SEEDS),
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


def _assert_canonical_e3(run: Mapping[str, Any]) -> None:
    method = str(run.get("method", ""))
    seed = str(run.get("seed", ""))
    burst_name = str(run.get("workload", {}).get("burst_name", ""))
    burst = BURSTS.get(burst_name)
    expected_workload = {
        "request_freq": FORMAL_E3_E4_LOAD,
        "arrival_profile": "burst",
        "topology": "heterogeneous",
        "qos_profile": "balanced",
        "load_scale": 1.0,
        "burst_name": burst_name,
        "burst": copy.deepcopy(burst),
    }
    expected_parent = (
        f"steady.middle.heterogeneous.balanced.{seed}."
        f"{run['workload_profile']['sha256'][:12]}"
    )
    expected_tape = f"burst.{burst_name}.{expected_parent}"
    tape = run.get("workload_tape", {})
    simulation = run.get("simulation", {})
    _require(
        burst is not None
        and run.get("cell_id") == f"E3.{method}.{burst_name}.heterogeneous.n20"
        and run.get("variant") == "full"
        and run.get("workload") == expected_workload
        and run.get("cluster") == FORMAL_E3_E4_CLUSTER
        and simulation.get("total_frame") == 4000
        and simulation.get("expected_final_frame") == 4000
        and simulation.get("expected_frame_count") == 4001
        and simulation.get("arrival_horizon_frames") == 1000
        and simulation.get("observation_horizon_frames") == 1000
        and tape.get("kind") == "derived_burst"
        and tape.get("key") == expected_tape
        and tape.get("parent_key") == expected_parent
        and tape.get("runtime_mode") == "replay"
        and tape.get("runtime_load_scale") == 1.0
        and tape.get("runtime_burst_profile") == "steady"
        and tape.get("transform")
        == {
            "kind": "cdf_burst_remap",
            "scenario": burst_name,
            "event_count_invariant": "exact",
            "dag_order_invariant": "exact",
        },
        f"formal E3/E4 shard contains a noncanonical E3 run {run.get('run_id')}",
    )


def _assert_canonical_e4(run: Mapping[str, Any]) -> None:
    method = str(run.get("method", ""))
    seed = str(run.get("seed", ""))
    expected_workload = {
        "request_freq": FORMAL_E3_E4_LOAD,
        "arrival_profile": "steady",
        "topology": "heterogeneous",
        "qos_profile": "balanced",
        "load_scale": 1.0,
    }
    expected_tape = (
        f"steady.middle.heterogeneous.balanced.{seed}."
        f"{run['workload_profile']['sha256'][:12]}"
    )
    tape = run.get("workload_tape", {})
    simulation = run.get("simulation", {})
    _require(
        run.get("cell_id") == f"E4.{method}.steady.balanced.n20"
        and run.get("variant") == "full"
        and run.get("workload") == expected_workload
        and run.get("cluster") == FORMAL_E3_E4_CLUSTER
        and run.get("metadata", {}).get("per_qos_breakdown_required") is True
        and simulation.get("total_frame") == 1000
        and simulation.get("expected_final_frame") == 1000
        and simulation.get("expected_frame_count") == 1001
        and simulation.get("arrival_horizon_frames") == 1000
        and simulation.get("observation_horizon_frames") == 1000
        and tape.get("kind") == "base_steady"
        and tape.get("key") == expected_tape
        and tape.get("parent_key") is None
        and tape.get("transform") == {"kind": "identity"}
        and tape.get("runtime_mode") == "replay"
        and tape.get("runtime_load_scale") == 1.0
        and tape.get("runtime_burst_profile") == "steady",
        f"formal E3/E4 shard contains a noncanonical E4 run {run.get('run_id')}",
    )


def _validate_physical_shape(shard: Mapping[str, Any]) -> None:
    _require(
        shard.get("seed_stage") == "initial",
        "formal E3/E4 shard requires seed_stage=initial",
    )
    runs = shard.get("runs")
    _require(isinstance(runs, list), "formal E3/E4 runs must be an array")
    _require(len(runs) == 400, "formal E3/E4 shard must contain 400 runs")
    observed_keys = [_physical_key(run) for run in runs]
    _require(
        len(observed_keys) == len(set(observed_keys))
        and set(observed_keys) == _expected_physical_keys(),
        "formal E3/E4 physical Cartesian product is incomplete",
    )

    for run in runs:
        _require(
            run.get("method") in FORMAL_E1_METHODS
            and run.get("seed") in FORMAL_E3_E4_SEEDS,
            f"formal E3/E4 run has an unfrozen method/seed: {run.get('run_id')}",
        )
        qos = run.get("simulator_experiment", {}).get("qos", {})
        _require(
            qos.get("enabled") is True and qos.get("class_assignment") == "balanced",
            f"formal E3/E4 run does not enable balanced QoS: {run.get('run_id')}",
        )
        if run.get("experiment_id") == "E3":
            _assert_canonical_e3(run)
        else:
            _assert_canonical_e4(run)

    dependencies = shard.get("reference_build_dependencies")
    _require(
        isinstance(dependencies, list) and len(dependencies) == 40,
        "formal E3/E4 reference dependency count must be 40",
    )
    expected_dependencies = _reference_build_dependencies(runs)
    _require(
        dependencies == expected_dependencies,
        "formal E3/E4 reference dependencies do not match the selected runs",
    )
    reference_runs = [run for run in runs if run.get("reference_dependency")]
    _require(
        len(reference_runs) == 40
        and all(run.get("method") == "sche_nash" for run in reference_runs),
        "only the 40 formal E3/E4 NSESche runs may require offline references",
    )

    marker = shard.get(FORMAL_E3_E4_SHARD_MARKER)
    _require(isinstance(marker, Mapping), "formal E3/E4 shard marker is missing")
    _require(
        marker.get("schema_version") == FORMAL_E3_E4_SHARD_SCHEMA
        and marker.get("selection") == _expected_selection()
        and marker.get("execution_prerequisites") == FORMAL_E3_E4_PREREQUISITES,
        "formal E3/E4 marker contract is not frozen",
    )
    _require(
        marker.get("selected_run_count") == 400
        and marker.get("selected_cell_count") == 40
        and marker.get("selected_e3_run_count") == 300
        and marker.get("selected_e4_run_count") == 100
        and marker.get("selected_reference_build_count") == 40
        and marker.get("selected_balanced_qos_run_count") == 400
        and marker.get("selected_faasrank_run_count") == 40,
        "formal E3/E4 marker counts are inconsistent",
    )


def derive_formal_e3_e4_initial_shard(source_manifest_path: Path) -> dict[str, Any]:
    """Derive the only legal 400-run initial E3/E4 formal block."""

    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    _assert_complete_full_source(source)
    _require(
        source.get("seed_stage") == "initial",
        "formal E3/E4 shard source must be the initial full matrix",
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
    shard[FORMAL_E3_E4_SHARD_MARKER] = {
        "schema_version": FORMAL_E3_E4_SHARD_SCHEMA,
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


def write_formal_e3_e4_initial_shard(
    source_manifest_path: Path, output_path: Path
) -> dict[str, Any]:
    """Write the initial E3/E4 shard atomically without executing it."""

    if source_manifest_path.resolve() == output_path.resolve():
        raise ProtocolValidationError(
            "formal E3/E4 shard output must differ from its source"
        )
    shard = derive_formal_e3_e4_initial_shard(source_manifest_path)
    write_json_atomic(output_path, shard)
    return shard


__all__ = [
    "FORMAL_E3_E4_SHARD_MARKER",
    "FORMAL_E3_E4_SHARD_SCHEMA",
    "FORMAL_E3_E4_SEEDS",
    "derive_formal_e3_e4_initial_shard",
    "write_formal_e3_e4_initial_shard",
]
