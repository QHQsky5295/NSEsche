"""Build the formal V77 E2 NSESche-only versioned-method overlay.

The overlay never rewrites the completed E2 products.  It derives twenty new
NSESche run specifications from the exact E01--E20 low/n100 source runs and
seals the 180 immutable baseline artifacts used by the later comparison.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import (
    validate_canonical_run,
)

from .matrix import (
    _assign_run_identity,
    _reference_build_dependencies,
    _reference_dependency,
)
from .schema import (
    FORMAL_E1_METHODS,
    FORMAL_E1_SEEDS_BY_STAGE,
    FORMAL_SHARD_MARKERS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


FORMAL_E2_NSESCHE_OVERLAY_SCHEMA = "NSE_FORMAL_E2_NSESCHE_PROFILE_OVERLAY_V1"
FORMAL_E2_NSESCHE_OVERLAY_MARKER = "formal_e2_nsesche_profile_overlay"
PLAN_SCHEMA = "NSE_FORMAL_E2_NSESCHE_OVERLAY_PLAN_V77"
PROFILE_SCHEMA = "NSE_OPERATIONAL_SELECTED_PROFILE_V76"
TARGET_METHOD = "sche_nash"
TARGET_VARIANT = "v77-formal-v76-selected-profile"
TARGET_CELL = "E2.sche_nash.low.homogeneous.n100.scale5"
TARGET_LOAD = "low"
TARGET_NODE_COUNT = 100
TARGET_LOAD_SCALE = 5.0
BASELINE_METHODS = tuple(
    method for method in FORMAL_E1_METHODS if method != TARGET_METHOD
)
ALL_SEEDS = FORMAL_E1_SEEDS_BY_STAGE["all"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _is_target(run: Mapping[str, Any]) -> bool:
    workload = run.get("workload", {})
    cluster = run.get("cluster", {})
    return (
        run.get("experiment_id") == "E2"
        and workload.get("request_freq") == TARGET_LOAD
        and workload.get("arrival_profile") == "steady"
        and workload.get("topology") == "homogeneous"
        and workload.get("qos_profile") == "mixed"
        and workload.get("load_scale") == TARGET_LOAD_SCALE
        and cluster.get("node_count") == TARGET_NODE_COUNT
        and cluster.get("topology") == "homogeneous"
    )


def _source_descriptor(
    path: Path, manifest: Mapping[str, Any], canonical_root: Path
) -> dict[str, Any]:
    return {
        "path": str(path),
        "manifest_hash": manifest["manifest_hash"],
        "file_sha256": file_hash(path),
        "seed_stage": manifest["seed_stage"],
        "canonical_root": str(canonical_root),
    }


def _runtime_identity(directory: Path) -> dict[str, Any]:
    adapter = read_json(directory / "adapter_observation.json")
    audit = read_json(directory / "manifest.json")
    software = audit.get("software_environment", {})
    return {
        "binary_sha256": adapter.get("server_executable_sha256"),
        "python_sha256": adapter.get("python_helper_interpreter_sha256"),
        "git_commit": software.get("git", {}).get("commit"),
        "cargo_lock_sha256": software.get("cargo_lock", {}).get("sha256"),
    }


def _artifact_lineage(
    run: Mapping[str, Any],
    *,
    stage: str,
    source_manifest_path: Path,
    source_manifest_hash: str,
    source_manifest_file_sha256: str,
    canonical_root: Path,
    result_relative_path: str,
) -> dict[str, Any]:
    directory = canonical_root / str(run["run_id"])
    validate_canonical_run(
        run,
        directory,
        expected_manifest_hash=source_manifest_hash,
        result_relative_path=result_relative_path,
    )
    summary_relative = result_relative_path.format(run_id=str(run["run_id"]))
    return {
        "source_stage": stage,
        "source_manifest_path": str(source_manifest_path),
        "source_manifest_hash": source_manifest_hash,
        "source_manifest_file_sha256": source_manifest_file_sha256,
        "source_run_id": run["run_id"],
        "source_run_spec_hash": run["run_spec_hash"],
        "source_cell_id": run["cell_id"],
        "source_method": run["method"],
        "source_variant": run.get("variant", "full"),
        "source_seed": run["seed"],
        "source_workload_spec_hash": run["workload_spec_hash"],
        "source_workload_tape_key": run["workload_tape"]["key"],
        "source_workload_tape_sha256": run["workload_tape"]["sha256"],
        "source_common_hpa_hash": run["common_hpa_hash"],
        "source_cluster_sha256": object_hash(run["cluster"]),
        "source_simulation_sha256": object_hash(run["simulation"]),
        "source_canonical_directory": str(directory),
        "source_audit_manifest_sha256": file_hash(directory / "manifest.json"),
        "source_qc_report_sha256": file_hash(directory / "qc_report.json"),
        "source_summary_sha256": file_hash(directory / summary_relative),
        "source_runtime_identity": _runtime_identity(directory),
    }


def _candidate_source_lineage(
    source_run: Mapping[str, Any], candidate_run: Mapping[str, Any], stage: str
) -> dict[str, Any]:
    return {
        "source_stage": stage,
        "source_run_id": source_run["run_id"],
        "source_run_spec_hash": source_run["run_spec_hash"],
        "source_cell_id": source_run["cell_id"],
        "source_seed": source_run["seed"],
        "source_workload_spec_hash": source_run["workload_spec_hash"],
        "source_workload_tape_key": source_run["workload_tape"]["key"],
        "source_workload_tape_sha256": source_run["workload_tape"]["sha256"],
        "source_common_hpa_hash": source_run["common_hpa_hash"],
        "source_cluster_sha256": object_hash(source_run["cluster"]),
        "source_simulation_sha256": object_hash(source_run["simulation"]),
        "derived_run_id": candidate_run["run_id"],
        "derived_run_spec_hash": candidate_run["run_spec_hash"],
    }


def _matrix_summary(
    runs: list[dict[str, Any]], reuse: list[dict[str, Any]]
) -> dict[str, Any]:
    cells = {(run["experiment_id"], run["cell_id"]) for run in runs}
    by_experiment: dict[str, dict[str, int]] = {}
    for experiment_id in (f"E{index}" for index in range(1, 10)):
        by_experiment[experiment_id] = {
            "new_cells": sum(cell[0] == experiment_id for cell in cells),
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


def _verify_plan(plan_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = read_json(plan_path)
    _require(plan.get("schema_version") == PLAN_SCHEMA, "V77 plan schema is invalid")
    _require(
        plan.get("status")
        == "preregistered_before_overlay_manifest_or_reference_generation",
        "V77 plan is not in its preregistered state",
    )
    profile_binding = plan.get("frozen_candidate", {})
    profile_path = _resolve(profile_binding.get("selected_profile_path", ""))
    _require(profile_path.is_file(), "frozen V76 selected-profile file is missing")
    _require(
        file_hash(profile_path) == profile_binding.get("selected_profile_file_sha256"),
        "frozen V76 selected-profile hash changed",
    )
    profile = read_json(profile_path)
    _require(
        profile.get("schema_version") == PROFILE_SCHEMA
        and profile.get("eligible_for_future_formal_nsesche_manifest_binding") is True,
        "V76 profile is not eligible for formal binding",
    )
    _require(
        profile.get("profile_id") == profile_binding.get("profile_id"),
        "V77 plan and V76 selected profile disagree",
    )
    binary_path = _resolve(profile_binding.get("binary_path", ""))
    model_path = _resolve(profile_binding.get("faasrank_model_path", ""))
    _require(
        binary_path.is_file()
        and file_hash(binary_path) == profile_binding.get("binary_sha256"),
        "frozen V77 candidate binary is missing or changed",
    )
    _require(
        model_path.is_file()
        and file_hash(model_path) == profile_binding.get("faasrank_model_sha256"),
        "frozen V77 FaaSRank model is missing or changed",
    )
    selected_environment = profile.get("environment")
    planned_environment = profile_binding.get("environment")
    _require(
        isinstance(selected_environment, dict)
        and isinstance(planned_environment, dict)
        and all(
            planned_environment.get(key) == value
            for key, value in selected_environment.items()
        ),
        "V77 plan changed a frozen V76 environment value",
    )
    return plan, profile


def derive_formal_e2_nsesche_overlay(plan_path: Path) -> dict[str, Any]:
    """Derive the result-blind V77 twenty-run formal overlay manifest."""

    plan_path = plan_path.resolve()
    plan, profile = _verify_plan(plan_path)
    source_specs = plan["frozen_baseline_sources"]
    stage_inputs: list[tuple[str, Path, dict[str, Any], Path]] = []
    for stage in ("initial", "ci_extension"):
        spec = source_specs[stage]
        source_path = _resolve(spec["manifest_path"])
        canonical_root = _resolve(spec["canonical_root"])
        _require(source_path.is_file(), f"{stage} source manifest is missing")
        _require(
            file_hash(source_path) == spec["manifest_file_sha256"],
            f"{stage} source manifest file hash changed",
        )
        source = load_and_validate_manifest(source_path)
        _require(
            source["manifest_hash"] == spec["manifest_hash"]
            and source["seed_stage"] == stage,
            f"{stage} source manifest identity changed",
        )
        stage_inputs.append((stage, source_path, source, canonical_root))

    candidate_runs: list[dict[str, Any]] = []
    candidate_lineage: list[dict[str, Any]] = []
    baseline_lineage: list[dict[str, Any]] = []
    historical_lineage: list[dict[str, Any]] = []
    profile_binding = plan["frozen_candidate"]
    profile_environment = copy.deepcopy(profile_binding["environment"])
    expected_model_sha = profile_binding["faasrank_model_sha256"]
    base_manifest = copy.deepcopy(stage_inputs[0][2])

    for stage, source_path, source, canonical_root in stage_inputs:
        seeds = set(FORMAL_E1_SEEDS_BY_STAGE[stage])
        target_runs = [run for run in source["runs"] if _is_target(run)]
        expected_keys = {
            (method, seed) for method in FORMAL_E1_METHODS for seed in seeds
        }
        observed_keys = {(run["method"], run["seed"]) for run in target_runs}
        _require(
            len(target_runs) == len(expected_keys) and observed_keys == expected_keys,
            f"{stage} source does not contain the complete target cell",
        )
        source_sha = file_hash(source_path)
        result_relative_path = source["execution"]["result_relative_path"]
        for run in target_runs:
            lineage = _artifact_lineage(
                run,
                stage=stage,
                source_manifest_path=source_path,
                source_manifest_hash=source["manifest_hash"],
                source_manifest_file_sha256=source_sha,
                canonical_root=canonical_root,
                result_relative_path=result_relative_path,
            )
            if run["method"] == TARGET_METHOD:
                historical_lineage.append(lineage)
                candidate = copy.deepcopy(run)
                candidate["variant"] = TARGET_VARIANT
                candidate["environment"].update(profile_environment)
                candidate.setdefault("metadata", {}).update(
                    {
                        "formal_overlay": FORMAL_E2_NSESCHE_OVERLAY_SCHEMA,
                        "selected_profile_id": profile["profile_id"],
                        "selected_profile_sha256": file_hash(
                            _resolve(profile_binding["selected_profile_path"])
                        ),
                        "source_formal_run_id": run["run_id"],
                        "source_formal_run_spec_hash": run["run_spec_hash"],
                    }
                )
                model = candidate["simulator_experiment"].get("faasrank_model", {})
                model.update(
                    {
                        "state": "frozen",
                        "model_sha256": expected_model_sha,
                        "training_tape_sha256": profile["frozen_dependencies"][
                            "faasrank_rust_model_payload_hash"
                        ],
                    }
                )
                # The Rust payload hash is separately sealed; preserve the actual
                # disjoint training-tape hash from the frozen formal artifact.
                source_model = read_json(
                    _resolve(profile_binding["faasrank_model_path"])
                )
                training_sha = source_model.get("training_tape", {}).get("sha256")
                if training_sha is None:
                    training_sha = source_model.get("training_tape_sha256")
                _require(
                    isinstance(training_sha, str) and len(training_sha) == 64,
                    "frozen FaaSRank training-tape hash is missing",
                )
                model["training_tape_sha256"] = training_sha
                candidate["simulator_experiment"]["faasrank_model"] = model
                candidate["reference_dependency"] = _reference_dependency(candidate)
                candidate["simulator_experiment"]["reference"] = {
                    "mode": "offline_required",
                    "table_path": candidate["reference_dependency"]["path"],
                    "build_output_path": "",
                }
                _assign_run_identity(candidate)
                candidate_runs.append(candidate)
                candidate_lineage.append(
                    _candidate_source_lineage(run, candidate, stage)
                )
            else:
                baseline_lineage.append(lineage)

    _require(
        {(run["method"], run["seed"]) for run in candidate_runs}
        == {(TARGET_METHOD, seed) for seed in ALL_SEEDS},
        "candidate overlay is not the complete E01-E20 NSESche product",
    )
    _require(len(baseline_lineage) == 180, "baseline lineage must contain 180 runs")
    _require(len(historical_lineage) == 20, "historical lineage must contain 20 runs")

    overlay = base_manifest
    for marker in FORMAL_SHARD_MARKERS:
        overlay.pop(marker, None)
    overlay.pop("integration_smoke_shard", None)
    overlay["created_at"] = utc_now()
    overlay["seed_stage"] = "all"
    overlay["formal_results_eligible"] = True
    overlay["runs"] = sorted(candidate_runs, key=lambda run: run["seed"])
    overlay["reference_build_dependencies"] = _reference_build_dependencies(
        overlay["runs"]
    )
    overlay["all_tapes_bound"] = True
    overlay["all_faasrank_models_bound"] = True
    overlay["all_sla_targets_bound"] = False
    overlay["all_references_bound"] = False
    overlay.pop("reference_catalog_hash", None)
    overlay["execution"]["command_template"][-1] = str(
        _resolve(profile_binding["binary_path"])
    )
    overlay["matrix_summary"] = _matrix_summary(
        overlay["runs"], overlay["reuse_analyses"]
    )
    source_descriptors = [
        _source_descriptor(path, source, canonical_root)
        for _, path, source, canonical_root in stage_inputs
    ]
    overlay[FORMAL_E2_NSESCHE_OVERLAY_MARKER] = {
        "schema_version": FORMAL_E2_NSESCHE_OVERLAY_SCHEMA,
        "plan": {
            "path": str(plan_path),
            "file_sha256": file_hash(plan_path),
            "schema_version": plan["schema_version"],
        },
        "source_manifests": source_descriptors,
        "selection": copy.deepcopy(plan["matrix"]),
        "selected_profile": {
            "path": str(_resolve(profile_binding["selected_profile_path"])),
            "file_sha256": profile_binding["selected_profile_file_sha256"],
            "profile_id": profile["profile_id"],
            "environment": profile_environment,
            "binary_path": str(_resolve(profile_binding["binary_path"])),
            "binary_sha256": profile_binding["binary_sha256"],
            "faasrank_model_path": str(
                _resolve(profile_binding["faasrank_model_path"])
            ),
            "faasrank_model_sha256": expected_model_sha,
            "faasrank_rust_model_payload_hash": profile_binding[
                "faasrank_rust_model_payload_hash"
            ],
            "faasrank_training_tape_sha256": training_sha,
        },
        "selected_source_runs": sorted(
            candidate_lineage, key=lambda item: item["source_seed"]
        ),
        "frozen_baseline_runs": sorted(
            baseline_lineage,
            key=lambda item: (item["source_method"], item["source_seed"]),
        ),
        "historical_nsesche_runs": sorted(
            historical_lineage, key=lambda item: item["source_seed"]
        ),
        "versioned_runtime_contract": copy.deepcopy(plan["versioned_runtime_contract"]),
        "frozen_baseline_runtime": {
            "binary_sha256": source_specs["baseline_binary_sha256"],
            "python_sha256": source_specs["baseline_python_sha256"],
            "cargo_lock_sha256": source_specs["baseline_cargo_lock_sha256"],
            "common_hpa_hash": source_specs["baseline_common_hpa_hash"],
        },
        "selected_run_count": 20,
        "selected_cell_count": 1,
        "selected_reference_build_count": 20,
        "frozen_baseline_run_count": 180,
        "historical_nsesche_run_count": 20,
        "performance_results_consulted": False,
    }
    overlay.pop("manifest_hash", None)
    overlay["manifest_hash"] = object_hash(overlay)
    validate_manifest(overlay)
    return overlay


def write_formal_e2_nsesche_overlay(
    plan_path: Path, output_path: Path
) -> dict[str, Any]:
    if plan_path.resolve() == output_path.resolve():
        raise ProtocolValidationError("V77 overlay output must differ from its plan")
    overlay = derive_formal_e2_nsesche_overlay(plan_path)
    write_json_atomic(output_path, overlay)
    return overlay
