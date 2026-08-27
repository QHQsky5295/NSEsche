from __future__ import annotations

import copy
import json
import math
import re
from itertools import product
from pathlib import Path
from typing import Any, Iterable

from .faasrank_model import (
    FrozenFaaSRankModel,
    rust_faasrank_model_config,
    verify_frozen_faasrank_model,
)
from .sla import FrozenSlaTargets, load_frozen_sla_targets
from .schema import ProtocolValidationError, validate_manifest, validate_protocol_config
from .tape import TAPE_CATALOG_SCHEMA, TapeFormatError, inspect_tape
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic
from .workload_profile import FrozenWorkloadProfile, load_profile_set


DEFAULT_CONFIG_PATH = Path(__file__).with_name("default_protocol.json")
LOADS = ("low", "middle", "high")
TOPOLOGIES = ("homogeneous", "heterogeneous")
ABLATIONS = ("no_heterogeneity", "no_externality", "no_pricing", "no_coordination")
BURSTS = {
    "spike5x50ms": {
        "kind": "spike",
        "multiplier": 5.0,
        "duration_ms": 50,
        "repetitions": 1,
    },
    "sustained3x200ms": {
        "kind": "sustained",
        "multiplier": 3.0,
        "duration_ms": 200,
        "repetitions": 1,
    },
    "pulse4x4x50ms": {
        "kind": "pulse",
        "multiplier": 4.0,
        "duration_ms": 50,
        "repetitions": 4,
    },
}

LEGACY_FAASRANK_RUST_CONFIG = {
    "state": "legacy_default",
    "model_sha256": "",
    "training_tape_sha256": "",
    "cpu_headroom": 0.25,
    "memory_headroom": 0.20,
    "network_locality": 0.15,
    "warm_affinity": 0.25,
    "load_balance": 0.15,
    "diversity_penalty": 0.05,
    "epsilon": 0.1,
}


def load_protocol_config(path: Path | None = None) -> dict[str, Any]:
    config = read_json(path or DEFAULT_CONFIG_PATH)
    if not isinstance(config, dict):
        raise ProtocolValidationError("protocol config root must be an object")
    validate_protocol_config(config)
    return config


def _slug(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-.")
    return text or "value"


def _cell_id(experiment_id: str, parts: Iterable[Any]) -> str:
    return ".".join([experiment_id, *(_slug(part) for part in parts)])


def _base_workload(
    load: str, topology: str, qos_profile: str, *, load_scale: float = 1.0
) -> dict[str, Any]:
    return {
        "request_freq": load,
        "arrival_profile": "steady",
        "topology": topology,
        "qos_profile": qos_profile,
        "load_scale": load_scale,
    }


def _environment_for(
    method: str, extras: dict[str, Any] | None = None
) -> dict[str, str]:
    environment = {
        "PROTOCOL_SCHEDULER": method,
        "NASH_OBSERVE": "summary",
    }
    if extras:
        environment.update({key: str(value) for key, value in extras.items()})
    return environment


def _make_cell(
    experiment_id: str,
    cell_id: str,
    method: str,
    workload: dict[str, Any],
    cluster: dict[str, Any],
    *,
    environment: dict[str, str] | None = None,
    variant: str = "full",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cell = {
        "experiment_id": experiment_id,
        "cell_id": cell_id,
        "method": method,
        "variant": variant,
        "workload": workload,
        "cluster": cluster,
        "environment": environment or _environment_for(method),
    }
    if metadata:
        cell["metadata"] = metadata
    return cell


def _analysis_reuse_rule(payload: dict[str, Any]) -> dict[str, Any]:
    """Seal one analysis-only reuse rule with a content hash.

    Reused figure points are projections of completed formal runs, not new
    simulator executions.  Keeping the complete selector, identity contract,
    and projection in the manifest makes that distinction machine-auditable.
    """

    rule = {
        "schema_version": "NSE_ANALYSIS_REUSE_RULE_V1",
        **copy.deepcopy(payload),
    }
    rule["rule_sha256"] = object_hash(rule)
    return rule


def expand_cells(
    config: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    methods = config["methods"]
    defaults = config["matrix_defaults"]
    base_nodes = int(defaults["base_node_count"])
    balanced_qos = defaults["qos_profile"]
    base_load = defaults["base_load"]
    cells: list[dict[str, Any]] = []

    # E1: 10 methods x 3 loads x homogeneous/heterogeneous x 20 nodes.
    for method, load, topology in product(methods, LOADS, TOPOLOGIES):
        cells.append(
            _make_cell(
                "E1",
                _cell_id("E1", (method, load, topology, f"n{base_nodes}")),
                method,
                _base_workload(load, topology, "mixed"),
                {"node_count": base_nodes, "topology": topology},
            )
        )

    # E2: only the new 100/500-node homogeneous cells. The 20-node point reuses E1.
    for method, load, (node_count, load_scale) in product(
        methods, LOADS, ((100, 5.0), (500, 25.0))
    ):
        cells.append(
            _make_cell(
                "E2",
                _cell_id(
                    "E2",
                    (
                        method,
                        load,
                        "homogeneous",
                        f"n{node_count}",
                        f"scale{load_scale:g}",
                    ),
                ),
                method,
                _base_workload(load, "homogeneous", "mixed", load_scale=load_scale),
                {"node_count": node_count, "topology": "homogeneous"},
                metadata={"weak_scaling": True, "base_node_count": base_nodes},
            )
        )

    # E3: 10 methods x three predeclared burst processes, 20-node heterogeneous cluster.
    for method, (burst_name, burst) in product(methods, BURSTS.items()):
        workload = _base_workload(base_load, "heterogeneous", balanced_qos)
        workload.update(
            {
                "arrival_profile": "burst",
                "burst_name": burst_name,
                "burst": copy.deepcopy(burst),
            }
        )
        cells.append(
            _make_cell(
                "E3",
                _cell_id("E3", (method, burst_name, "heterogeneous", f"n{base_nodes}")),
                method,
                workload,
                {"node_count": base_nodes, "topology": "heterogeneous"},
            )
        )

    # E4: steady, balanced-QoS comparison; a single predeclared middle-load cell per method.
    for method in methods:
        cells.append(
            _make_cell(
                "E4",
                _cell_id("E4", (method, "steady", balanced_qos, f"n{base_nodes}")),
                method,
                _base_workload(base_load, "heterogeneous", balanced_qos),
                {"node_count": base_nodes, "topology": "heterogeneous"},
                metadata={"per_qos_breakdown_required": True},
            )
        )

    # E5: four NSEsche ablations x three loads.
    for ablation, load in product(ABLATIONS, LOADS):
        cells.append(
            _make_cell(
                "E5",
                _cell_id("E5", ("sche_nash", ablation, load, f"n{base_nodes}")),
                "sche_nash",
                _base_workload(load, "heterogeneous", "mixed"),
                {"node_count": base_nodes, "topology": "heterogeneous"},
                environment=_environment_for(
                    "sche_nash", {"NASH_ABLATION_TYPE": ablation}
                ),
                variant=ablation,
            )
        )

    # E6: two predeclared reference solvers x middle/high heterogeneous workloads.
    for method, load in product(("cp_br", "onsocmax"), ("middle", "high")):
        cells.append(
            _make_cell(
                "E6",
                _cell_id("E6", (method, load, "heterogeneous", f"n{base_nodes}")),
                method,
                _base_workload(load, "heterogeneous", "mixed"),
                {"node_count": base_nodes, "topology": "heterogeneous"},
                metadata={"reference_solver": True},
            )
        )

    # E7: exactly four axial neighbours around each load-specific centre. The centres are reused.
    e7 = defaults["e7"]
    for load in LOADS:
        center = e7["centers"][load]
        price_step = float(e7["steps"]["price_feedback_rate"])
        quality_step = float(e7["steps"]["quality_weight"])
        neighbours = (
            (
                "price_minus",
                center["price_feedback_rate"] - price_step,
                center["quality_weight"],
            ),
            (
                "price_plus",
                center["price_feedback_rate"] + price_step,
                center["quality_weight"],
            ),
            (
                "quality_minus",
                center["price_feedback_rate"],
                center["quality_weight"] - quality_step,
            ),
            (
                "quality_plus",
                center["price_feedback_rate"],
                center["quality_weight"] + quality_step,
            ),
        )
        for label, price, quality in neighbours:
            environment = _environment_for(
                "sche_nash",
                {
                    "NASH_PRICE_FEEDBACK_RATE": f"{price:g}",
                    "NASH_QUALITY_WEIGHT": f"{quality:g}",
                },
            )
            cells.append(
                _make_cell(
                    "E7",
                    _cell_id("E7", (load, label, f"p{price:g}", f"q{quality:g}")),
                    "sche_nash",
                    _base_workload(load, "heterogeneous", "mixed"),
                    {"node_count": base_nodes, "topology": "heterogeneous"},
                    environment=environment,
                    variant=label,
                    metadata={
                        "centre": copy.deepcopy(center),
                        "axial_neighbour": True,
                        "nash_parameters": {
                            "price_feedback_rate": price,
                            "quality_weight": quality,
                        },
                    },
                )
            )

    common_identity = {
        "workload_transform": "identity",
        "cluster_transform": "identity",
        "required_exact": {
            "simulation.frame_duration_seconds": float(
                config["simulation"]["frame_duration_seconds"]
            ),
            "simulation.observation_horizon_frames": int(
                config["simulation"]["observation_horizon_frames"]
            ),
            "workload_tape.runtime_load_scale": 1.0,
            "simulator_experiment.workload.load_scale": 1.0,
            "common_hpa.comparison_scope": "scheduler_plus_common_hpa",
        },
        "required_hash_fields": [
            "run_spec_hash",
            "workload_spec_hash",
            "common_hpa_hash",
        ],
    }
    e7_centres = copy.deepcopy(defaults["e7"]["centers"])
    reuse = [
        _analysis_reuse_rule(
            {
                "rule_id": "E2_FROM_E1_20NODE_HOMOGENEOUS_V1",
                "experiment_id": "E2",
                "kind": "reuse_cells",
                "source_experiment_id": "E1",
                "source_selector": {
                    "method": list(methods),
                    "workload.request_freq": list(LOADS),
                    "workload.arrival_profile": "steady",
                    "workload.topology": "homogeneous",
                    "workload.qos_profile": "mixed",
                    "workload.load_scale": 1.0,
                    "cluster.node_count": base_nodes,
                    "cluster.topology": "homogeneous",
                },
                "compatibility": copy.deepcopy(common_identity),
                "target_projection": {
                    "scenario": "weak_scaling",
                    "variant": "",
                    "cell_id_template": (
                        "E2.reuse-e1-20node.{method}.{load}.homogeneous.n{node_count}"
                    ),
                },
                "purpose": "20-node weak-scaling point",
            }
        ),
        _analysis_reuse_rule(
            {
                "rule_id": "E7_CENTRES_FROM_E1_NSESCHE_V1",
                "experiment_id": "E7",
                "kind": "reuse_cells",
                "source_experiment_id": "E1",
                "source_selector": {
                    "method": "sche_nash",
                    "seed": list(config["seed_policy"]["e7_initial"]),
                    "workload.request_freq": list(LOADS),
                    "workload.arrival_profile": "steady",
                    "workload.topology": "heterogeneous",
                    "workload.qos_profile": "mixed",
                    "workload.load_scale": 1.0,
                    "cluster.node_count": base_nodes,
                    "cluster.topology": "heterogeneous",
                },
                "compatibility": {
                    **copy.deepcopy(common_identity),
                    "required_by_load": {
                        load: {
                            "simulator_experiment.nash.price_feedback_rate": values[
                                "price_feedback_rate"
                            ],
                            "simulator_experiment.nash.quality_weight": values[
                                "quality_weight"
                            ],
                        }
                        for load, values in e7_centres.items()
                    },
                },
                "target_projection": {
                    "scenario": "sensitivity",
                    "variant": "centre",
                    "cell_id_template": "E7.{load}.centre.n{node_count}",
                    "copy_nash_parameters": True,
                },
                "purpose": "load-specific hyperparameter centre points",
            }
        ),
        _analysis_reuse_rule(
            {
                "rule_id": "E5_FULL_FROM_E1_NSESCHE_V1",
                "experiment_id": "E5",
                "kind": "reuse_cells",
                "source_experiment_id": "E1",
                "source_selector": {
                    "method": "sche_nash",
                    "workload.request_freq": list(LOADS),
                    "workload.arrival_profile": "steady",
                    "workload.topology": "heterogeneous",
                    "workload.qos_profile": "mixed",
                    "workload.load_scale": 1.0,
                    "cluster.node_count": base_nodes,
                    "cluster.topology": "heterogeneous",
                },
                "compatibility": {
                    **copy.deepcopy(common_identity),
                    "required_exact": {
                        **copy.deepcopy(common_identity["required_exact"]),
                        **{
                            f"simulator_experiment.ablation.{name}": False
                            for name in ABLATIONS
                        },
                    },
                },
                "target_projection": {
                    "scenario": "ablation",
                    "variant": "full",
                    "cell_id_template": "E5.sche_nash.full.{load}.n{node_count}",
                },
                "purpose": "full NSESche arm for the ablation figure",
            }
        ),
        _analysis_reuse_rule(
            {
                "rule_id": "E6_ORIGINAL_METHODS_FROM_E1_V1",
                "experiment_id": "E6",
                "kind": "reuse_cells",
                "source_experiment_id": "E1",
                "source_selector": {
                    "method": list(methods),
                    "workload.request_freq": ["middle", "high"],
                    "workload.arrival_profile": "steady",
                    "workload.topology": "heterogeneous",
                    "workload.qos_profile": "mixed",
                    "workload.load_scale": 1.0,
                    "cluster.node_count": base_nodes,
                    "cluster.topology": "heterogeneous",
                },
                "compatibility": copy.deepcopy(common_identity),
                "target_projection": {
                    "scenario": "welfare",
                    "variant": "",
                    "cell_id_template": (
                        "E6.reuse-e1.{method}.{load}.heterogeneous.n{node_count}"
                    ),
                },
                "purpose": (
                    "original ten placement methods for the heterogeneous "
                    "middle/high welfare comparison"
                ),
            }
        ),
        _analysis_reuse_rule(
            {
                "rule_id": "E8_POSTHOC_FROM_FORMAL_RUNS_V1",
                "experiment_id": "E8",
                "kind": "analysis_only",
                "source_experiment_ids": ["E1", "E2", "E3", "E4", "E5", "E6", "E7"],
                "produces_runs": False,
            }
        ),
        _analysis_reuse_rule(
            {
                "rule_id": "E9_POSTHOC_FROM_FORMAL_RUNS_V1",
                "experiment_id": "E9",
                "kind": "analysis_only",
                "source_experiment_ids": ["E1", "E2", "E3", "E4", "E5", "E6", "E7"],
                "produces_runs": False,
            }
        ),
    ]
    return cells, reuse


def _seeds_for_cell(
    config: dict[str, Any], cell: dict[str, Any], seed_stage: str
) -> list[str]:
    policy = config["seed_policy"]
    if cell["experiment_id"] == "E7":
        return list(policy["e7_initial"]) if seed_stage in {"initial", "all"} else []
    if seed_stage == "initial":
        return list(policy["initial"])
    if seed_stage == "ci_extension":
        return list(policy["ci_extension"])
    return [*policy["initial"], *policy["ci_extension"]]


def _ablation_payload(variant: str) -> dict[str, bool]:
    payload = {name: False for name in ABLATIONS}
    if variant in payload:
        payload[variant] = True
    return payload


def _simulator_experiment(
    config: dict[str, Any],
    cell: dict[str, Any],
    seed: str,
    tape: dict[str, Any],
    workload_profile: dict[str, Any],
) -> dict[str, Any]:
    """Build the Rust ExperimentConfig payload used by a formal run.

    Environment variables remain in the manifest as compatibility evidence,
    but all E5/E7 choices are authoritative in this payload.
    """
    defaults = config["matrix_defaults"]
    qos = copy.deepcopy(defaults["qos_profiles"][cell["workload"]["qos_profile"]])
    center = defaults["e7"]["centers"][cell["workload"]["request_freq"]]
    nash = {
        "price_feedback_rate": center["price_feedback_rate"],
        "quality_weight": center["quality_weight"],
        **copy.deepcopy(defaults["nash"]),
    }
    if cell["experiment_id"] == "E7":
        nash.update(copy.deepcopy(cell["metadata"]["nash_parameters"]))
    hpa_keys = (
        "target_mem_use_rate",
        "tolerance",
        "check_period_frames",
        "careful_down_history",
        "min_instances",
        "max_instances",
        "min_instances_when_pending",
        "allow_scale_to_zero",
        "scale_up_placement",
    )
    common_hpa = config["common_hpa"]
    return {
        "protocol_version": "reviewer-v3",
        "run_id": "__PROTOCOL_RUN_ID__",
        "workload_seed": seed,
        "topology_seed": seed,
        "algorithm_seed": seed,
        "node_count": int(cell["cluster"]["node_count"]),
        "node_profile": {
            "kind": cell["cluster"]["topology"],
            "cpu_mean": 150.0,
            "mem_mean": 5000.0,
            "cpu_cv": 0.3,
            "mem_cv": 0.25,
            "min_factor": 0.5,
            "max_factor": 1.5,
        },
        "network_profile": {"min_mbps": 8000.0, "max_mbps": 10000.0},
        "hpa": {key: copy.deepcopy(common_hpa[key]) for key in hpa_keys},
        "workload": {
            "mode": tape["runtime_mode"],
            "tape_path": tape["path"],
            "arrival_horizon_frames": int(
                config["simulation"]["arrival_horizon_frames"]
            ),
            "load_scale": tape["runtime_load_scale"],
            "burst_profile": tape["runtime_burst_profile"],
            "frequency_profile": copy.deepcopy(workload_profile),
        },
        "qos": qos,
        # An expanded manifest is deliberately not executable for FaaSRank-P
        # until a separately calibrated immutable model artifact is bound.
        "faasrank_model": copy.deepcopy(LEGACY_FAASRANK_RUST_CONFIG),
        "nash": nash,
        "ablation": _ablation_payload(cell["variant"]),
        "reference": {"mode": "sa_fallback", "table_path": "", "build_output_path": ""},
        "output": {
            "enabled": True,
            "root": "__PROTOCOL_REVIEWER_RECORD_ROOT__",
            "request_events": True,
            "window_events": True,
        },
    }


def _reference_dependency(run: dict[str, Any]) -> dict[str, Any]:
    """Declare a method-state-matched offline NSE welfare reference table.

    For E6 comparators the build pass keeps that comparator's placement policy
    and invokes only the shared read-only NSESche welfare evaluator.  This is
    necessary because each policy creates a different sequence of window
    states; borrowing another policy's reference table would not be valid.
    """
    experiment = copy.deepcopy(run["simulator_experiment"])
    experiment["run_id"] = "__REFERENCE_BUILD_RUN_ID__"
    experiment["reference"] = {
        "mode": "build",
        "table_path": "",
        "build_output_path": "__REFERENCE_BUILD_OUTPUT_PATH__",
    }
    experiment["output"]["root"] = "__REFERENCE_BUILD_OUTPUT_ROOT__"
    # Reference builds inherit the run environment in stages.py.  Scheduler
    # controls such as NASH_OPERATIONAL_EXPERT_PROXY can change the initial
    # assignment and therefore the complete state/hash sequence that the
    # offline table must match.  Bind those controls into the build spec while
    # excluding the adapter's transport-only port.
    reference_environment = {
        key: value
        for key, value in sorted(run.get("environment", {}).items())
        if key != "SERVERLESS_SIM_PORT"
    }
    semantic_hash = object_hash(
        {
            "method": run["method"],
            "environment": reference_environment,
            "workload_tape": run["workload_tape"],
            "cluster": run["cluster"],
            "simulation": run["simulation"],
            "experiment": experiment,
        }
    )
    key = _slug(f"nse-reference.{run['cell_id']}.{run['seed']}.{semantic_hash[:16]}")
    return {
        "schema_version": "NSE_REFERENCE_DEPENDENCY_V1",
        "key": key,
        "path": f"reference_tables/{key}.jsonl",
        "sha256": None,
        "bytes": None,
        "line_count": None,
        "receipt_path": f"reference_receipts/{key}.json",
        "receipt_sha256": None,
        "build_completed": None,
        "state_pair_sequence_sha256": None,
        "assignment_sequence_sha256": None,
        "build_process_observation_path": None,
        "build_process_observation_sha256": None,
        "build_required": True,
        "build_spec_hash": semantic_hash,
        "build_experiment": experiment,
    }


def _assign_run_identity(run: dict[str, Any]) -> None:
    """Assign a deterministic run ID and bind it into ExperimentConfig."""
    run.pop("run_spec_hash", None)
    run.pop("run_id", None)
    experiment = run["simulator_experiment"]
    experiment["run_id"] = "__PROTOCOL_RUN_ID__"
    identity_hash = object_hash(run)[:16]
    run_id = _slug(f"{run['cell_id']}.{run['seed']}.{identity_hash}")
    run["run_id"] = run_id
    experiment["run_id"] = run_id
    run["run_spec_hash"] = object_hash(run)


def _make_run(
    config: dict[str, Any],
    cell: dict[str, Any],
    seed: str,
    common_hpa_hash: str,
    workload_profile: FrozenWorkloadProfile,
) -> dict[str, Any]:
    profile_binding = workload_profile.to_binding()
    workload_spec_hash = object_hash(
        {
            "seed": seed,
            "workload": cell["workload"],
            "workload_profile": profile_binding,
        }
    )
    workload_tape = _workload_tape_plan(cell, seed, profile_binding)
    simulation = copy.deepcopy(config["simulation"])
    if cell["experiment_id"] == "E3":
        simulation.update(
            {
                "total_frame": 4000,
                "expected_final_frame": 4000,
                "expected_frame_count": 4001,
            }
        )
    run_payload = {
        **copy.deepcopy(cell),
        "seed": seed,
        "workload_spec_hash": workload_spec_hash,
        "workload_profile": profile_binding,
        "workload_tape": workload_tape,
        "common_hpa": copy.deepcopy(config["common_hpa"]),
        "common_hpa_hash": common_hpa_hash,
        "simulation": simulation,
    }
    run_payload["simulator_experiment"] = _simulator_experiment(
        config, cell, seed, workload_tape, profile_binding
    )
    if cell["method"] == "sche_FaaSRank":
        run_payload["baseline_model"] = {"state": "unbound"}
    needs_welfare_reference = (
        cell["method"] == "sche_nash" and cell["variant"] != "no_coordination"
    ) or (cell["experiment_id"] == "E6" and cell["method"] in {"cp_br", "onsocmax"})
    if needs_welfare_reference:
        run_payload["reference_dependency"] = _reference_dependency(run_payload)
        run_payload["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run_payload["reference_dependency"]["path"],
            "build_output_path": "",
        }
    elif cell["method"] == "sche_nash":
        # This ablation intentionally removes the Nash-social coordination
        # term, so no social-reference build is scientifically applicable.
        run_payload["reference_policy"] = {
            "status": "not_required",
            "reason": "nash_social_coordination_disabled",
            "build_required": False,
        }
        run_payload["simulator_experiment"]["reference"] = {
            "mode": "not_required",
            "table_path": "",
            "build_output_path": "",
        }
    _assign_run_identity(run_payload)
    return run_payload


def _base_tape_key(
    workload: dict[str, Any], seed: str, workload_profile: dict[str, Any]
) -> str:
    # The tape itself only stores (frame, dag_id), so the key also binds the
    # capture environment that gives each DAG id its function/QoS/network meaning.
    return _slug(
        ".".join(
            (
                "steady",
                workload["request_freq"],
                workload["topology"],
                workload["qos_profile"],
                seed,
                workload_profile["sha256"][:12],
            )
        )
    )


def _workload_provenance(load: str, workload_profile: dict[str, Any]) -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[3]
    relative_files = (
        "serverless_sim/src/real-world-emulation/CDFs/IATCVCDFGenerator.py",
        "serverless_sim/src/real-world-emulation/CDFs/invokesCDF.csv",
        "serverless_sim/src/real-world-emulation/CDFs/CVs.csv",
        "serverless_sim/src/real-world-emulation/RealWorldAppEmulation.py",
    )
    multipliers = {"low": 0.2, "middle": 0.6, "high": 1.4}
    return {
        "schema_version": "NSE_WORKLOAD_PROVENANCE_V1",
        "source_kind": "azure_trace_derived_empirical_cdf",
        "source_statement": (
            "Azure Functions invocation traces were reduced to empirical IAT/CV CDFs; "
            "this is not a direct raw-trace event conversion"
        ),
        "cdf_artifacts": [
            {"path": path, "sha256": file_hash(repository / path)}
            for path in relative_files
        ],
        "load_label": load,
        "load_scale_multiplier": multipliers[load],
        "frequency_profile": copy.deepcopy(workload_profile),
        "rate_unit": "requests/s",
        "measured_arrival_rate_rps": None,
    }


def _workload_tape_plan(
    cell: dict[str, Any], seed: str, workload_profile: dict[str, Any]
) -> dict[str, Any]:
    workload = cell["workload"]
    parent_workload = copy.deepcopy(workload)
    parent_workload["arrival_profile"] = "steady"
    parent_workload.pop("burst_name", None)
    parent_workload.pop("burst", None)
    parent_workload["load_scale"] = 1.0
    parent_key = _base_tape_key(parent_workload, seed, workload_profile)
    if cell["experiment_id"] == "E2":
        factor = int(workload["load_scale"])
        key = _slug(f"weakscale{factor}.{parent_key}")
        kind = "derived_scale"
        transform = {"kind": "same_frame_replication", "factor": factor}
        directory = "derived"
    elif cell["experiment_id"] == "E3":
        scenario = workload["burst_name"]
        key = _slug(f"burst.{scenario}.{parent_key}")
        kind = "derived_burst"
        transform = {
            "kind": "cdf_burst_remap",
            "scenario": scenario,
            "event_count_invariant": "exact",
            "dag_order_invariant": "exact",
        }
        directory = "derived"
    else:
        key = parent_key
        kind = "base_steady"
        transform = {"kind": "identity"}
        parent_key = None
        directory = "base"
    return {
        "key": key,
        "kind": kind,
        "path": f"workload_tapes/{directory}/{key}.json",
        "sha256": None,
        "event_count": None,
        "parent_key": parent_key,
        "parent_sha256": None,
        "transform": transform,
        "runtime_mode": "replay",
        "runtime_load_scale": 1.0,
        "runtime_burst_profile": "steady",
        "workload_profile": copy.deepcopy(workload_profile),
        "provenance": _workload_provenance(workload["request_freq"], workload_profile),
    }


def bind_tape_catalog(
    manifest: dict[str, Any], catalog: dict[str, Any]
) -> dict[str, Any]:
    validate_manifest(manifest)
    if (
        manifest.get("protocol_id")
        != "tsc-reviewer-common-hpa-v3-frozen-workload-profiles"
    ):
        raise ProtocolValidationError(
            "only the frozen workload-profile protocol may bind formal tapes"
        )
    if (
        not isinstance(catalog, dict)
        or catalog.get("schema_version") != TAPE_CATALOG_SCHEMA
    ):
        raise ProtocolValidationError("invalid tape catalog schema")
    catalog_payload = copy.deepcopy(catalog)
    catalog_hash = catalog_payload.pop("catalog_hash", None)
    if (
        not isinstance(catalog_hash, str)
        or object_hash(catalog_payload) != catalog_hash
    ):
        raise ProtocolValidationError("tape catalog hash does not match its content")
    entries = catalog.get("entries")
    if not isinstance(entries, dict):
        raise ProtocolValidationError("tape catalog entries must be an object")
    required_catalog_keys = {
        key
        for run in manifest["runs"]
        for key in (
            run["workload_tape"]["key"],
            run["workload_tape"].get("parent_key"),
        )
        if key is not None
    }
    observed_catalog_keys = set(entries)
    if observed_catalog_keys != required_catalog_keys:
        missing_keys = sorted(required_catalog_keys - observed_catalog_keys)
        extra_keys = sorted(observed_catalog_keys - required_catalog_keys)
        raise ProtocolValidationError(
            "tape catalog key set differs from the manifest: "
            f"missing={missing_keys}, extra={extra_keys}"
        )

    for key in sorted(required_catalog_keys):
        entry = entries[key]
        if not isinstance(entry, dict):
            raise ProtocolValidationError(f"tape catalog entry {key!r} is invalid")
        tape_path = Path(str(entry.get("path", "")))
        try:
            actual = inspect_tape(tape_path, "auto")
        except (OSError, UnicodeError, TapeFormatError, ValueError) as exc:
            raise ProtocolValidationError(
                f"tape catalog entry {key!r} cannot be verified from disk: {exc}"
            ) from exc
        for field in (
            "sha256",
            "version",
            "workload_seed",
            "event_count",
            "dag_order_sha256",
            "first_frame",
            "last_frame",
        ):
            if entry.get(field) != getattr(actual, field):
                raise ProtocolValidationError(
                    f"tape catalog entry {key!r} {field} differs from the actual file"
                )
    bound = copy.deepcopy(manifest)
    for run in bound["runs"]:
        plan = run["workload_tape"]
        entry = entries.get(plan["key"])
        if not isinstance(entry, dict):
            raise ProtocolValidationError(f"tape catalog is missing {plan['key']!r}")
        if entry.get("workload_seed") != run["seed"]:
            raise ProtocolValidationError(f"tape seed mismatch for {plan['key']!r}")
        if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
            raise ProtocolValidationError(f"tape hash is missing for {plan['key']!r}")
        if entry.get("kind") != plan["kind"]:
            raise ProtocolValidationError(f"tape kind mismatch for {plan['key']!r}")
        if not isinstance(entry.get("event_count"), int) or entry["event_count"] <= 0:
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} must contain requests"
            )
        measured_rate = entry.get("measured_arrival_rate_rps")
        if (
            isinstance(measured_rate, bool)
            or not isinstance(measured_rate, (int, float))
            or not math.isfinite(float(measured_rate))
            or measured_rate <= 0
        ):
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} has no measured arrival rate"
            )
        capture_environment = entry.get("capture_environment")
        if not isinstance(capture_environment, dict):
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} has no capture semantic bundle"
            )
        for hash_field in (
            "function_dag_qos_sha256",
            "node_network_sha256",
            "capture_environment_sha256",
            "semantic_bundle_sha256",
        ):
            value = capture_environment.get(hash_field)
            if not isinstance(value, str) or len(value) != 64:
                raise ProtocolValidationError(
                    f"formal tape {plan['key']!r} has invalid {hash_field}"
                )
        receipt_path = Path(str(entry.get("capture_receipt_path", "")))
        receipt_hash = entry.get("capture_receipt_sha256")
        if (
            not isinstance(receipt_hash, str)
            or len(receipt_hash) != 64
            or not receipt_path.is_file()
            or file_hash(receipt_path) != receipt_hash
        ):
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} capture receipt is missing or changed"
            )
        entry_provenance = entry.get("provenance")
        if (
            not isinstance(entry_provenance, dict)
            or entry_provenance.get("source_kind")
            != "azure_trace_derived_empirical_cdf"
        ):
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} source provenance is invalid"
            )
        expected_cdfs = plan["provenance"]["cdf_artifacts"]
        if entry_provenance.get("cdf_artifacts") != expected_cdfs:
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} CDF hashes differ from the frozen protocol"
            )
        expected_profile = plan["workload_profile"]
        if (
            entry.get("workload_profile") != expected_profile
            or entry_provenance.get("frequency_profile") != expected_profile
        ):
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} workload profile differs from the frozen protocol"
            )
        receipt = read_json(receipt_path)
        if (
            not isinstance(receipt, dict)
            or receipt.get("workload_frequency_profile") != expected_profile
        ):
            raise ProtocolValidationError(
                f"formal tape {plan['key']!r} capture receipt has no matching workload profile"
            )
        entry_transform = entry.get("transform")
        if (
            not isinstance(entry_transform, dict)
            or entry_transform.get("kind") != plan["transform"]["kind"]
        ):
            raise ProtocolValidationError(
                f"tape transform mismatch for {plan['key']!r}"
            )
        if (
            plan["kind"] == "derived_scale"
            and entry_transform.get("factor") != plan["transform"]["factor"]
        ):
            raise ProtocolValidationError(
                f"weak-scaling factor mismatch for {plan['key']!r}"
            )
        if (
            plan["kind"] == "derived_burst"
            and entry_transform.get("scenario") != plan["transform"]["scenario"]
        ):
            raise ProtocolValidationError(
                f"burst scenario mismatch for {plan['key']!r}"
            )
        if plan["parent_key"] is not None:
            parent = entries.get(plan["parent_key"])
            if not isinstance(parent, dict) or entry.get("parent_sha256") != parent.get(
                "sha256"
            ):
                raise ProtocolValidationError(
                    f"derived tape parent hash mismatch for {plan['key']!r}"
                )
        plan.update(
            {
                "path": entry["path"],
                "sha256": entry["sha256"],
                "event_count": entry["event_count"],
                "parent_sha256": entry.get("parent_sha256"),
                "transform": copy.deepcopy(entry.get("transform", plan["transform"])),
                "provenance": {
                    **copy.deepcopy(plan["provenance"]),
                    "measured_arrival_rate_rps": entry["measured_arrival_rate_rps"],
                },
                "capture_environment": copy.deepcopy(entry["capture_environment"]),
                "capture_receipt_path": entry["capture_receipt_path"],
                "capture_receipt_sha256": entry["capture_receipt_sha256"],
                "workload_profile": copy.deepcopy(entry["workload_profile"]),
            }
        )
        run["simulator_experiment"]["workload"]["tape_path"] = entry["path"]
        if "reference_dependency" in run:
            # The build task is keyed by the exact immutable tape hash.
            run["reference_dependency"] = _reference_dependency(run)
            run["simulator_experiment"]["reference"]["table_path"] = run[
                "reference_dependency"
            ]["path"]
        _assign_run_identity(run)
    bound["tape_catalog_hash"] = catalog_hash
    bound["all_tapes_bound"] = True
    bound["reference_build_dependencies"] = _reference_build_dependencies(bound["runs"])
    bound.pop("manifest_hash", None)
    bound["manifest_hash"] = object_hash(bound)
    validate_manifest(bound)
    return bound


def bind_faasrank_model(
    manifest: dict[str, Any],
    artifact_path: Path,
    *,
    manifest_artifact_path: str | None = None,
) -> dict[str, Any]:
    """Bind one immutable, training/evaluation-disjoint FaaSRank-P model.

    Tape hashes must already be frozen so the binding can prove that the
    calibration tape is not reused by any formal evaluation run.
    """

    validate_manifest(manifest)
    if manifest.get("all_tapes_bound") is not True:
        raise ProtocolValidationError(
            "bind workload tapes before binding the FaaSRank model"
        )
    evaluation_hashes = {
        run.get("workload_tape", {}).get("sha256") for run in manifest["runs"]
    }
    if any(not isinstance(value, str) for value in evaluation_hashes):
        raise ProtocolValidationError(
            "every evaluation tape must have a frozen SHA-256 before model binding"
        )
    model: FrozenFaaSRankModel = verify_frozen_faasrank_model(
        artifact_path,
        forbidden_test_tape_sha256=sorted(evaluation_hashes),
    )
    stored_path = manifest_artifact_path or str(Path(model.path))
    binding = {
        "schema_version": "NSE_FAASRANK_MODEL_BINDING_V1",
        "state": "frozen",
        "artifact_path": stored_path,
        "artifact_sha256": model.artifact_sha256,
        "artifact_bytes": model.artifact_bytes,
        "training_tape_sha256": model.training_tape_sha256,
        "created_at": model.created_at,
        "provenance": copy.deepcopy(model.provenance),
    }
    rust_config = rust_faasrank_model_config(model)
    bound = copy.deepcopy(manifest)
    faasrank_runs = [run for run in bound["runs"] if run["method"] == "sche_FaaSRank"]
    if not faasrank_runs:
        raise ProtocolValidationError("manifest contains no sche_FaaSRank runs")
    for run in faasrank_runs:
        run["baseline_model"] = copy.deepcopy(binding)
        run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(rust_config)
        _assign_run_identity(run)
    bound["all_faasrank_models_bound"] = True
    bound.pop("manifest_hash", None)
    bound["manifest_hash"] = object_hash(bound)
    validate_manifest(bound)
    return bound


def bind_sla_targets(
    manifest: dict[str, Any],
    artifact_path: Path,
    *,
    manifest_artifact_path: str | None = None,
) -> dict[str, Any]:
    """Bind one immutable three-pilot SLA artifact to every balanced-QoS run."""

    validate_manifest(manifest)
    frozen: FrozenSlaTargets = load_frozen_sla_targets(artifact_path)
    stored_path = manifest_artifact_path or frozen.path
    binding = {
        "schema_version": "NSE_SLA_TARGET_BINDING_V1",
        "state": "frozen",
        "artifact_path": stored_path,
        "artifact_sha256": frozen.artifact_sha256,
        "artifact_bytes": frozen.artifact_bytes,
        "document_sha256": frozen.document_sha256,
        "targets_sha256": frozen.targets_sha256,
        "source_bundle_sha256": frozen.source_bundle_sha256,
        "frozen_at": frozen.frozen_at,
    }
    bound = copy.deepcopy(manifest)
    balanced_runs = [
        run for run in bound["runs"] if run["workload"].get("qos_profile") == "balanced"
    ]
    if not balanced_runs:
        raise ProtocolValidationError("manifest contains no balanced-QoS runs")
    for run in balanced_runs:
        run["simulator_experiment"]["qos"].update(copy.deepcopy(frozen.targets))
        run["sla_targets"] = copy.deepcopy(binding)
        if "reference_dependency" in run:
            run["reference_dependency"] = _reference_dependency(run)
            run["simulator_experiment"]["reference"]["table_path"] = run[
                "reference_dependency"
            ]["path"]
        _assign_run_identity(run)
    bound["all_sla_targets_bound"] = True
    bound["reference_build_dependencies"] = _reference_build_dependencies(bound["runs"])
    bound.pop("manifest_hash", None)
    bound["manifest_hash"] = object_hash(bound)
    validate_manifest(bound)
    return bound


def build_manifest(
    config: dict[str, Any], seed_stage: str = "initial"
) -> dict[str, Any]:
    validate_protocol_config(config)
    if seed_stage not in {"initial", "ci_extension", "all"}:
        raise ProtocolValidationError(
            "seed_stage must be initial, ci_extension, or all"
        )
    cells, reuse = expand_cells(config)
    common_hpa_hash = object_hash(config["common_hpa"])
    profiles = load_profile_set(
        config["workload_profiles"], repository=Path(__file__).resolve().parents[3]
    )
    profile_bindings = {
        load: profile.to_binding() for load, profile in profiles.items()
    }
    workload_profile_set = {
        "schema_version": config["workload_profiles"]["schema_version"],
        "profile_set_id": config["workload_profiles"]["profile_set_id"],
        "formal_required": True,
        "profiles": profile_bindings,
    }
    runs = [
        _make_run(
            config,
            cell,
            seed,
            common_hpa_hash,
            profiles[cell["workload"]["request_freq"]],
        )
        for cell in cells
        for seed in _seeds_for_cell(config, cell, seed_stage)
    ]
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "seed_stage": seed_stage,
        "ci_extension_requires_trigger": bool(
            config["seed_policy"].get("ci_extension_requires_trigger", True)
        ),
        "common_hpa": copy.deepcopy(config["common_hpa"]),
        "common_hpa_hash": common_hpa_hash,
        "workload_profile_set": workload_profile_set,
        "workload_profile_set_hash": object_hash(workload_profile_set),
        "simulation": copy.deepcopy(config["simulation"]),
        "execution": copy.deepcopy(config["execution"]),
        "qc": copy.deepcopy(config["qc"]),
        "matrix_summary": _matrix_summary(cells, runs, reuse),
        "runs": runs,
        "reference_build_dependencies": _reference_build_dependencies(runs),
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": reuse,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def _reference_build_dependencies(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dependencies: dict[str, dict[str, Any]] = {}
    for run in runs:
        dependency = run.get("reference_dependency")
        if dependency is not None:
            dependencies.setdefault(dependency["key"], copy.deepcopy(dependency))
    return [dependencies[key] for key in sorted(dependencies)]


def _matrix_summary(
    cells: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    reuse: list[dict[str, Any]],
) -> dict[str, Any]:
    by_experiment: dict[str, dict[str, int]] = {}
    for experiment_id in [f"E{i}" for i in range(1, 10)]:
        by_experiment[experiment_id] = {
            "new_cells": sum(cell["experiment_id"] == experiment_id for cell in cells),
            "new_runs": sum(run["experiment_id"] == experiment_id for run in runs),
            "reuse_entries": sum(
                entry["experiment_id"] == experiment_id for entry in reuse
            ),
        }
    return {
        "new_cells": len(cells),
        "new_runs": len(runs),
        "by_experiment": by_experiment,
    }


def write_manifest(
    output: Path, config_path: Path | None = None, seed_stage: str = "initial"
) -> dict[str, Any]:
    manifest = build_manifest(load_protocol_config(config_path), seed_stage)
    write_json_atomic(output, manifest)
    return manifest


def dump_default_config(output: Path) -> None:
    config = load_protocol_config()
    write_json_atomic(output, config)
