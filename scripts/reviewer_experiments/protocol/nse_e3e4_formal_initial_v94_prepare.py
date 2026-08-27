"""Derive the complete formal E3/E4 initial manifest with frozen V94 profiles.

This preparation step is result blind.  It reuses the already bound formal
E01--E10 tape/SLA/model inputs, changes only the 40 NSESche profile bindings,
and points every method at the same isolated V94 binary.  The prepared source
manifest is never modified.
"""

from __future__ import annotations

import argparse
import copy
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .matrix import (
    _assign_run_identity,
    _reference_build_dependencies,
    _reference_dependency,
)
from .schema import (
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


PLAN_SCHEMA = "NSE_E3E4_FORMAL_INITIAL_V94_PLAN_V1"
OVERLAY_SCHEMA = "NSE_E3E4_FORMAL_INITIAL_V94_OVERLAY_V1"
OVERLAY_MARKER = "nse_e3e4_formal_initial_v94_overlay"
CONFIRMATION_RESULT_SCHEMA = "NSE_E3E4_SRPT_TERMINAL_DUAL_CONFIRMATION_RESULT_V94_V1"
TARGET_METHOD = "sche_nash"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _hash_rows(rows: list[Mapping[str, Any]]) -> str:
    return object_hash(
        sorted((dict(row) for row in rows), key=lambda row: tuple(row.values()))
    )


def _source_identity(run: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cell_id": run["cell_id"],
        "seed": run["seed"],
        "method": run["method"],
        "run_id": run["run_id"],
        "run_spec_hash": run["run_spec_hash"],
        "environment_sha256": object_hash(run["environment"]),
    }


def _verify_self_hash(document: Mapping[str, Any], field: str, label: str) -> None:
    expected = document.get(field)
    payload = copy.deepcopy(dict(document))
    payload.pop(field, None)
    _require(
        isinstance(expected, str) and object_hash(payload) == expected,
        f"{label} {field} does not match its content",
    )


def _load_plan(plan_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = read_json(plan_path)
    _require(isinstance(plan, dict), "V94 formal plan root must be an object")
    _require(
        plan.get("schema_version") == PLAN_SCHEMA, "V94 formal plan schema is invalid"
    )
    _require(
        plan.get("status")
        == "preregistered_before_formal_reference_generation_or_online_execution",
        "V94 formal plan is not in its preregistered state",
    )

    authorization = plan.get("v94_authorization", {})
    confirmation_path = _resolve(authorization.get("confirmation_result_path", ""))
    _require(
        confirmation_path.is_file()
        and file_hash(confirmation_path)
        == authorization.get("confirmation_result_file_sha256"),
        "V94 confirmation result is missing or changed",
    )
    confirmation = read_json(confirmation_path)
    _require(
        confirmation.get("schema_version") == CONFIRMATION_RESULT_SCHEMA
        and confirmation.get("status") == "confirmation_pass"
        and confirmation.get("all_four_confirmation_gates_pass") is True
        and confirmation.get("training_rows_pooled") is False,
        "V94 confirmation result does not authorize formal execution",
    )
    _verify_self_hash(confirmation, "result_hash", "V94 confirmation result")
    _require(
        confirmation["result_hash"] == authorization.get("confirmation_result_hash"),
        "V94 formal plan and confirmation result hash disagree",
    )

    confirmation_plan_path = _resolve(authorization.get("confirmation_plan_path", ""))
    _require(
        confirmation_plan_path.is_file()
        and file_hash(confirmation_plan_path)
        == authorization.get("confirmation_plan_file_sha256"),
        "V94 confirmation plan is missing or changed",
    )

    frozen = plan.get("frozen_candidate", {})
    binary_path = _resolve(frozen.get("binary_path", ""))
    _require(
        binary_path.is_file()
        and file_hash(binary_path) == frozen.get("binary_sha256")
        and binary_path.stat().st_size == frozen.get("binary_bytes"),
        "frozen V94 binary is missing or changed",
    )
    cargo_path = Path("serverless_sim/Cargo.lock").resolve()
    module_conf_path = Path("serverless_sim/module_conf_es.json").resolve()
    _require(
        cargo_path.is_file()
        and file_hash(cargo_path) == frozen.get("cargo_lock_sha256"),
        "frozen V94 Cargo.lock is missing or changed",
    )
    _require(
        module_conf_path.is_file()
        and file_hash(module_conf_path) == frozen.get("module_conf_sha256"),
        "frozen V94 module configuration is missing or changed",
    )
    return plan, confirmation


def _load_source(plan: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    binding = plan.get("immutable_prepared_source", {})
    source_path = _resolve(binding.get("path", ""))
    _require(
        source_path.is_file() and file_hash(source_path) == binding.get("file_sha256"),
        "prepared E3/E4 source manifest is missing or changed",
    )
    source = load_and_validate_manifest(source_path)
    _require(
        source.get("manifest_hash") == binding.get("manifest_hash")
        and source.get("seed_stage") == "initial"
        and source.get("formal_results_eligible") is True,
        "prepared E3/E4 source manifest identity changed",
    )
    _require(
        len(source.get("runs", [])) == 400
        and len(source.get("reference_build_dependencies", [])) == 40
        and source.get("all_tapes_bound") is True
        and source.get("all_sla_targets_bound") is True
        and source.get("all_faasrank_models_bound") is True
        and source.get("all_references_bound") is not True,
        "prepared E3/E4 source is not at the frozen model-bound stage",
    )
    _require(
        "formal_e3_e4_initial_shard" in source and OVERLAY_MARKER not in source,
        "prepared E3/E4 source is not the immutable initial shard",
    )
    return source_path, source


def _frozen_model(source: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    models = {
        object_hash(run["simulator_experiment"]["faasrank_model"]): run[
            "simulator_experiment"
        ]["faasrank_model"]
        for run in source["runs"]
        if run["method"] == "sche_FaaSRank"
    }
    _require(len(models) == 1, "formal FaaSRank rows do not share one frozen model")
    model = copy.deepcopy(next(iter(models.values())))
    frozen = plan["frozen_candidate"]
    _require(
        model.get("state") == "frozen"
        and model.get("model_sha256") == frozen.get("faasrank_model_sha256")
        and model.get("training_tape_sha256")
        == frozen.get("faasrank_training_tape_sha256"),
        "formal FaaSRank model differs from the frozen V94 dependency",
    )
    return model


def _resolve_bound_artifacts(
    source_path: Path, source: Mapping[str, Any], overlay: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Make source-relative SLA/model bindings portable without copying them."""

    sla_bindings = {
        object_hash(run["sla_targets"]): run["sla_targets"]
        for run in source["runs"]
        if isinstance(run.get("sla_targets"), dict)
    }
    model_bindings = {
        object_hash(run["baseline_model"]): run["baseline_model"]
        for run in source["runs"]
        if run.get("baseline_model", {}).get("state") == "frozen"
    }
    _require(len(sla_bindings) == 1, "formal E3/E4 rows do not share one SLA binding")
    _require(
        len(model_bindings) == 1,
        "formal FaaSRank rows do not share one artifact binding",
    )
    source_sla = next(iter(sla_bindings.values()))
    source_model = next(iter(model_bindings.values()))
    sla_path = Path(source_sla["artifact_path"])
    if not sla_path.is_absolute():
        sla_path = source_path.parent / sla_path
    model_path = Path(source_model["artifact_path"])
    if not model_path.is_absolute():
        model_path = source_path.parent / model_path
    sla_path = sla_path.resolve()
    model_path = model_path.resolve()
    _require(
        sla_path.is_file()
        and file_hash(sla_path) == source_sla.get("artifact_sha256")
        and sla_path.stat().st_size == source_sla.get("artifact_bytes"),
        "frozen formal SLA artifact is missing or changed",
    )
    _require(
        model_path.is_file()
        and file_hash(model_path) == source_model.get("artifact_sha256")
        and model_path.stat().st_size == source_model.get("artifact_bytes"),
        "frozen formal FaaSRank artifact is missing or changed",
    )
    for run in overlay["runs"]:
        if isinstance(run.get("sla_targets"), dict):
            run["sla_targets"]["artifact_path"] = str(sla_path)
        if run.get("baseline_model", {}).get("state") == "frozen":
            run["baseline_model"]["artifact_path"] = str(model_path)
    return {
        "sla": {
            "path": str(sla_path),
            "sha256": source_sla["artifact_sha256"],
            "bytes": source_sla["artifact_bytes"],
        },
        "faasrank_model": {
            "path": str(model_path),
            "sha256": source_model["artifact_sha256"],
            "bytes": source_model["artifact_bytes"],
            "training_tape_sha256": source_model["training_tape_sha256"],
        },
    }


def derive_formal_e3_e4_v94_manifest(plan_path: Path) -> dict[str, Any]:
    """Derive the result-blind 400-run formal V94 E3/E4 manifest."""

    plan_path = plan_path.resolve()
    plan, confirmation = _load_plan(plan_path)
    source_path, source = _load_source(plan)
    overlay = copy.deepcopy(source)
    source_runs = {(run["cell_id"], run["seed"]): run for run in source["runs"]}
    frozen_model = _frozen_model(source, plan)
    reused_input_artifacts = _resolve_bound_artifacts(source_path, source, overlay)
    port = str(plan["execution"]["isolated_port"])
    candidate_bindings: list[dict[str, Any]] = []

    for run in overlay["runs"]:
        stable = (run["cell_id"], run["seed"])
        source_run = source_runs[stable]
        run["environment"]["SERVERLESS_SIM_PORT"] = port
        if run["method"] == TARGET_METHOD:
            expected_environment = copy.deepcopy(
                plan[f"{run['experiment_id']}_environment"]
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
    lineage = overlay["formal_e3_e4_initial_shard"]["selected_source_runs"]
    for entry in lineage:
        current = current_by_stable[(entry["source_cell_id"], entry["source_seed"])]
        entry["source_environment_sha256"] = object_hash(current["environment"])

    baseline_source = [
        _source_identity(run)
        for run in source["runs"]
        if run["method"] != TARGET_METHOD
    ]
    baseline_current = [
        _source_identity(run)
        for run in overlay["runs"]
        if run["method"] != TARGET_METHOD
    ]
    all_source = [_source_identity(run) for run in source["runs"]]
    overlay["reference_build_dependencies"] = _reference_build_dependencies(
        overlay["runs"]
    )
    overlay["all_references_bound"] = False
    overlay.pop("reference_catalog_hash", None)
    overlay["execution"]["command_template"] = [
        "{python}",
        "-m",
        "scripts.reviewer_experiments.protocol.serverless_adapter",
        "--run-config",
        "{run_config}",
        "--simulator-exe",
        str(_resolve(plan["frozen_candidate"]["binary_path"])),
    ]
    overlay["created_at"] = utc_now()
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
        "v94_confirmation": {
            "path": str(
                _resolve(plan["v94_authorization"]["confirmation_result_path"])
            ),
            "file_sha256": plan["v94_authorization"]["confirmation_result_file_sha256"],
            "result_hash": confirmation["result_hash"],
        },
        "runtime": {
            "binary_path": str(_resolve(plan["frozen_candidate"]["binary_path"])),
            "binary_sha256": plan["frozen_candidate"]["binary_sha256"],
            "cargo_lock_sha256": plan["frozen_candidate"]["cargo_lock_sha256"],
            "module_conf_sha256": plan["frozen_candidate"]["module_conf_sha256"],
            "serverless_sim_port": port,
        },
        "profiles": {
            "E3": plan["frozen_candidate"]["E3_profile"],
            "E4": plan["frozen_candidate"]["E4_profile"],
        },
        "reused_input_artifacts": reused_input_artifacts,
        "candidate_bindings": sorted(
            candidate_bindings, key=lambda item: (item["cell_id"], item["seed"])
        ),
        "source_run_identity_sha256": _hash_rows(all_source),
        "baseline_source_identity_sha256": _hash_rows(baseline_source),
        "baseline_derived_identity_sha256": _hash_rows(baseline_current),
        "selected_run_count": 400,
        "selected_candidate_run_count": 40,
        "selected_baseline_run_count": 360,
        "selected_reference_build_count": 40,
        "performance_results_consulted": False,
        "training_rows_pooled": False,
        "whole_matrix_required": True,
    }
    overlay.pop("manifest_hash", None)
    overlay["manifest_hash"] = object_hash(overlay)
    validate_manifest(overlay)
    return overlay


def write_formal_e3_e4_v94_manifest(
    plan_path: Path, output_path: Path
) -> dict[str, Any]:
    if plan_path.resolve() == output_path.resolve():
        raise ProtocolValidationError("V94 formal output must differ from its plan")
    output_path = output_path.resolve()
    if output_path.exists():
        raise ProtocolValidationError(
            "refusing to overwrite an existing V94 formal manifest"
        )
    manifest = derive_formal_e3_e4_v94_manifest(plan_path)
    write_json_atomic(output_path, manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive the complete result-blind formal V94 E3/E4 manifest"
    )
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = write_formal_e3_e4_v94_manifest(args.plan, args.output)
    print(
        f"written_formal_v94_e3_e4_manifest={args.output} "
        f"runs={len(manifest['runs'])} "
        f"references={len(manifest['reference_build_dependencies'])} "
        f"manifest_hash={manifest['manifest_hash']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
