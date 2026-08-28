"""Prepare the complete E11--E20 formal E3/E4 extension with frozen V94.

The initial E01--E10 reveal is used only to authorize the already-preregistered
all-method precision extension.  This module refuses any candidate or baseline
parameter change: it overlays the exact V94 environments/runtime used by the
completed initial block onto the disjoint formal CI-extension shard before
tape capture, reference generation, or online execution.
"""

from __future__ import annotations

import argparse
import copy
import csv
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import (
    validate_pairing_audit,
)

from .matrix import (
    _assign_run_identity,
    _reference_build_dependencies,
    _reference_dependency,
)
from .nse_e3e4_formal_initial_v94_prepare import (
    OVERLAY_MARKER as INITIAL_OVERLAY_MARKER,
    _frozen_model,
    _hash_rows,
    _load_plan as _load_initial_v94_plan,
    _resolve,
    _source_identity,
)
from .schema import (
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


PLAN_SCHEMA = "NSE_E3E4_FORMAL_EXTENSION_V94_PLAN_V1"
OVERLAY_SCHEMA = "NSE_E3E4_FORMAL_EXTENSION_V94_OVERLAY_V1"
OVERLAY_MARKER = "nse_e3e4_formal_extension_v94_overlay"
TARGET_METHOD = "sche_nash"
EXPECTED_SEEDS = tuple(f"E{index:02d}" for index in range(11, 21))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _stable_policy_identity(run: Mapping[str, Any]) -> dict[str, Any]:
    """Return the policy/config identity that legitimate bindings cannot change."""

    return {
        "cell_id": run["cell_id"],
        "seed": run["seed"],
        "experiment_id": run["experiment_id"],
        "method": run["method"],
        "variant": run.get("variant", "full"),
        "workload_sha256": object_hash(run["workload"]),
        "cluster_sha256": object_hash(run["cluster"]),
        "environment_sha256": object_hash(run["environment"]),
    }


def _bound_file(binding: Mapping[str, Any], path_field: str, hash_field: str) -> Path:
    path = _resolve(str(binding.get(path_field, "")))
    _require(
        path.is_file() and file_hash(path) == binding.get(hash_field),
        f"extension authorization artifact is missing or changed: {path}",
    )
    return path


def _validate_extension_decision(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {
        ("E3", "pulse4x4x50ms"),
        ("E3", "spike5x50ms"),
        ("E3", "sustained3x200ms"),
        ("E4", ""),
    }
    observed = {
        (row.get("experiment_id", ""), row.get("burst_pattern", "")) for row in rows
    }
    _require(
        len(rows) == 4
        and observed == expected
        and all(row.get("decision") == "extend_all_methods_to_n20" for row in rows)
        and all(
            row.get("first_n") == "10" and row.get("max_n") == "20" for row in rows
        ),
        "initial precision report does not authorize the complete E3/E4 extension",
    )


def _load_extension_plan(
    plan_path: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
]:
    plan = read_json(plan_path)
    _require(isinstance(plan, dict), "V94 extension plan root must be an object")
    _require(
        plan.get("schema_version") == PLAN_SCHEMA
        and plan.get("status")
        == "preregistered_before_extension_tape_capture_reference_generation_or_online_execution",
        "V94 extension plan schema or state is invalid",
    )

    initial_plan_binding = plan.get("frozen_initial_v94_plan", {})
    initial_plan_path = _bound_file(initial_plan_binding, "path", "file_sha256")
    initial_plan, confirmation = _load_initial_v94_plan(initial_plan_path)
    _require(
        initial_plan_binding.get("reuse_candidate_profile_and_runtime_without_change")
        is True
        and initial_plan_binding.get("post_initial_tuning") is False
        and initial_plan_binding.get("training_rows_pooled") is False,
        "V94 extension plan does not freeze the initial candidate boundary",
    )

    authorization = plan.get("initial_precision_authorization", {})
    initial_ready_path = _bound_file(
        authorization,
        "initial_ready_manifest_path",
        "initial_ready_manifest_file_sha256",
    )
    initial_ready = load_and_validate_manifest(initial_ready_path)
    _require(
        initial_ready.get("manifest_hash")
        == authorization.get("initial_ready_manifest_hash")
        and initial_ready.get("seed_stage") == "initial"
        and initial_ready.get("formal_results_eligible") is True
        and INITIAL_OVERLAY_MARKER in initial_ready
        and len(initial_ready.get("runs", [])) == 400
        and initial_ready.get("all_references_bound") is True,
        "completed V94 initial formal manifest identity changed",
    )
    pairing_path = _bound_file(
        authorization, "initial_pairing_path", "initial_pairing_file_sha256"
    )
    canonical_root = _resolve(authorization.get("initial_canonical_root", ""))
    pairing = validate_pairing_audit(pairing_path, initial_ready, canonical_root)
    _require(
        pairing.get("run_count") == 400
        and pairing.get("group_count") == 40
        and pairing.get("failed_group_count") == 0,
        "completed V94 initial pairing audit is not the exact 400-run product",
    )
    decision_path = _bound_file(
        authorization,
        "extension_decisions_path",
        "extension_decisions_file_sha256",
    )
    _bound_file(
        authorization, "analysis_manifest_path", "analysis_manifest_file_sha256"
    )
    _validate_extension_decision(decision_path)
    _require(
        authorization.get("required_decision") == "extend_all_methods_to_n20"
        and authorization.get("initial_run_count") == 400
        and authorization.get("initial_pairing_group_count") == 40
        and authorization.get("initial_quarantine_count") == 0
        and authorization.get("initial_blocked_count") == 0
        and authorization.get("performance_results_consulted_after_blind_reveal")
        is True
        and authorization.get(
            "extension_selection_depended_only_on_frozen_precision_rule"
        )
        is True,
        "V94 extension authorization boundary changed",
    )

    source_binding = plan.get("immutable_extension_source", {})
    source_path = _bound_file(source_binding, "path", "file_sha256")
    source = load_and_validate_manifest(source_path)
    _require(
        source.get("manifest_hash") == source_binding.get("manifest_hash")
        and source.get("seed_stage") == "ci_extension"
        and source.get("formal_results_eligible") is True
        and "formal_e3_e4_ci_extension_shard" in source
        and OVERLAY_MARKER not in source
        and len(source.get("runs", [])) == 400
        and len(source.get("reference_build_dependencies", [])) == 40
        and source.get("all_tapes_bound") is not True
        and source.get("all_sla_targets_bound") is not True
        and source.get("all_faasrank_models_bound") is not True
        and source.get("all_references_bound") is not True,
        "prepared E3/E4 extension source is not the immutable unbound shard",
    )
    _require(
        {run["seed"] for run in source["runs"]} == set(EXPECTED_SEEDS),
        "prepared E3/E4 extension source does not contain exactly E11-E20",
    )

    artifacts = plan.get("frozen_input_artifacts", {})
    for name in ("sla", "faasrank_model"):
        binding = artifacts.get(name, {})
        artifact_path = _resolve(binding.get("path", ""))
        _require(
            artifact_path.is_file()
            and artifact_path.is_absolute()
            and file_hash(artifact_path) == binding.get("sha256")
            and artifact_path.stat().st_size == binding.get("bytes"),
            f"frozen extension {name} artifact is missing or changed",
        )
    _require(
        artifacts["faasrank_model"].get("training_tape_sha256")
        == initial_plan["frozen_candidate"]["faasrank_training_tape_sha256"],
        "extension FaaSRank training tape differs from V94",
    )
    return (
        plan,
        initial_plan,
        confirmation,
        source_path,
        source,
        initial_ready_path,
        initial_ready,
    )


def derive_formal_e3_e4_v94_extension_manifest(plan_path: Path) -> dict[str, Any]:
    """Derive the result-blind 400-run E11--E20 V94 extension overlay."""

    plan_path = plan_path.resolve()
    (
        plan,
        initial_plan,
        confirmation,
        source_path,
        source,
        initial_ready_path,
        initial_ready,
    ) = _load_extension_plan(plan_path)
    overlay = copy.deepcopy(source)
    source_runs = {(run["cell_id"], run["seed"]): run for run in source["runs"]}
    frozen_model = _frozen_model(initial_ready, initial_plan)
    port = str(plan["execution"]["isolated_port"])
    candidate_bindings: list[dict[str, Any]] = []

    for run in overlay["runs"]:
        stable = (run["cell_id"], run["seed"])
        source_run = source_runs[stable]
        run["environment"]["SERVERLESS_SIM_PORT"] = port
        if run["method"] == TARGET_METHOD:
            expected_environment = copy.deepcopy(
                initial_plan[f"{run['experiment_id']}_environment"]
            )
            expected_environment["SERVERLESS_SIM_PORT"] = port
            run["environment"] = expected_environment
            run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(frozen_model)
            run.setdefault("metadata", {}).update(
                {
                    "formal_v94_profile_overlay": OVERLAY_SCHEMA,
                    "v94_candidate_profile": expected_environment[
                        "NASH_OPERATIONAL_EXPERT_PROXY"
                    ],
                    "source_formal_run_id": source_run["run_id"],
                    "source_formal_run_spec_hash": source_run["run_spec_hash"],
                }
            )
            run["reference_dependency"] = _reference_dependency(run)
            run["simulator_experiment"]["reference"] = {
                "mode": "offline_required",
                "table_path": run["reference_dependency"]["path"],
                "build_output_path": "",
            }
            candidate_bindings.append(
                {
                    "cell_id": run["cell_id"],
                    "seed": run["seed"],
                    "experiment_id": run["experiment_id"],
                    "source_run_id": source_run["run_id"],
                    "source_run_spec_hash": source_run["run_spec_hash"],
                    "source_environment_sha256": object_hash(source_run["environment"]),
                    "derived_environment_sha256": object_hash(run["environment"]),
                    "profile": expected_environment["NASH_OPERATIONAL_EXPERT_PROXY"],
                    "reference_key": run["reference_dependency"]["key"],
                    "reference_build_spec_hash": run["reference_dependency"][
                        "build_spec_hash"
                    ],
                }
            )
        _assign_run_identity(run)

    current_by_stable = {(run["cell_id"], run["seed"]): run for run in overlay["runs"]}
    lineage = overlay["formal_e3_e4_ci_extension_shard"]["selected_source_runs"]
    for entry in lineage:
        current = current_by_stable[(entry["source_cell_id"], entry["source_seed"])]
        entry["source_environment_sha256"] = object_hash(current["environment"])

    baselines_source = [
        _stable_policy_identity(run)
        for run in source["runs"]
        if run["method"] != TARGET_METHOD
    ]
    baselines_current = [
        _stable_policy_identity(run)
        for run in overlay["runs"]
        if run["method"] != TARGET_METHOD
    ]
    all_source = [_source_identity(run) for run in source["runs"]]
    overlay["reference_build_dependencies"] = _reference_build_dependencies(
        overlay["runs"]
    )
    overlay["all_tapes_bound"] = False
    overlay["all_sla_targets_bound"] = False
    overlay["all_faasrank_models_bound"] = False
    overlay["all_references_bound"] = False
    overlay.pop("reference_catalog_hash", None)
    binary_path = str(_resolve(initial_plan["frozen_candidate"]["binary_path"]))
    overlay["execution"]["command_template"] = [
        "{python}",
        "-m",
        "scripts.reviewer_experiments.protocol.serverless_adapter",
        "--run-config",
        "{run_config}",
        "--simulator-exe",
        binary_path,
    ]
    overlay["created_at"] = utc_now()
    artifacts = copy.deepcopy(plan["frozen_input_artifacts"])
    for binding in artifacts.values():
        binding["path"] = str(_resolve(binding["path"]))
    authorization = plan["initial_precision_authorization"]
    overlay[OVERLAY_MARKER] = {
        "schema_version": OVERLAY_SCHEMA,
        "plan": {
            "path": str(plan_path),
            "file_sha256": file_hash(plan_path),
            "schema_version": plan["schema_version"],
        },
        "prepared_source": {
            "path": str(source_path),
            "file_sha256": file_hash(source_path),
            "manifest_hash": source["manifest_hash"],
        },
        "initial_formal_block": {
            "manifest_path": str(initial_ready_path),
            "manifest_file_sha256": file_hash(initial_ready_path),
            "manifest_hash": initial_ready["manifest_hash"],
            "pairing_file_sha256": authorization["initial_pairing_file_sha256"],
            "extension_decisions_file_sha256": authorization[
                "extension_decisions_file_sha256"
            ],
        },
        "v94_confirmation": {
            "path": str(
                _resolve(initial_plan["v94_authorization"]["confirmation_result_path"])
            ),
            "file_sha256": initial_plan["v94_authorization"][
                "confirmation_result_file_sha256"
            ],
            "result_hash": confirmation["result_hash"],
        },
        "runtime": {
            "binary_path": binary_path,
            "binary_sha256": initial_plan["frozen_candidate"]["binary_sha256"],
            "cargo_lock_sha256": initial_plan["frozen_candidate"]["cargo_lock_sha256"],
            "module_conf_sha256": initial_plan["frozen_candidate"][
                "module_conf_sha256"
            ],
            "serverless_sim_port": port,
        },
        "profiles": {
            "E3": initial_plan["frozen_candidate"]["E3_profile"],
            "E4": initial_plan["frozen_candidate"]["E4_profile"],
        },
        "frozen_input_artifacts": artifacts,
        "candidate_bindings": sorted(
            candidate_bindings, key=lambda item: (item["cell_id"], item["seed"])
        ),
        "source_run_identity_sha256": _hash_rows(all_source),
        "baseline_source_identity_sha256": _hash_rows(baselines_source),
        "baseline_derived_identity_sha256": _hash_rows(baselines_current),
        "selected_run_count": 400,
        "selected_candidate_run_count": 40,
        "selected_baseline_run_count": 360,
        "selected_reference_build_count": 40,
        "initial_performance_results_consulted_after_blind_reveal": True,
        "extension_selection_result_driven": False,
        "candidate_or_baseline_parameters_changed_after_initial_reveal": False,
        "training_rows_pooled": False,
        "whole_matrix_required": True,
    }
    overlay.pop("manifest_hash", None)
    overlay["manifest_hash"] = object_hash(overlay)
    validate_manifest(overlay)
    return overlay


def write_formal_e3_e4_v94_extension_manifest(
    plan_path: Path, output_path: Path
) -> dict[str, Any]:
    if plan_path.resolve() == output_path.resolve():
        raise ProtocolValidationError("V94 extension output must differ from its plan")
    output_path = output_path.resolve()
    if output_path.exists():
        raise ProtocolValidationError(
            "refusing to overwrite an existing V94 extension manifest"
        )
    manifest = derive_formal_e3_e4_v94_extension_manifest(plan_path)
    write_json_atomic(output_path, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive the complete result-blind E11-E20 V94 E3/E4 manifest"
    )
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    manifest = write_formal_e3_e4_v94_extension_manifest(args.plan, args.output)
    print(
        f"written_formal_v94_e3_e4_extension_manifest={args.output} "
        f"runs={len(manifest['runs'])} "
        f"references={len(manifest['reference_build_dependencies'])} "
        f"manifest_hash={manifest['manifest_hash']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
