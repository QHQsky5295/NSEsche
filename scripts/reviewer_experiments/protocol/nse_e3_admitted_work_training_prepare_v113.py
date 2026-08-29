from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.reviewer_experiments.protocol.faasrank_model import (
    rust_faasrank_model_config,
    verify_frozen_faasrank_model,
)
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
    write_manifest,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_horizon_training_prepare_v109 import (
    CARGO_LOCK,
    CARGO_LOCK_SHA256,
    COMMON_ENVIRONMENT,
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_SHA256,
    FORMAL_RESULT,
    FORMAL_RESULT_SHA256,
    MODEL_PATH,
    MODEL_SHA256,
    MODULE_CONF,
    MODULE_CONF_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    SLA_PATH,
    SLA_SHA256,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
    derive_integration_smoke_shard,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3_admitted_work_training_20260829_v113")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_admitted_work_training_plan_v113.json"
)
PLAN_SHA256 = "139f528355360c0c1d783b19f3d1de10bd95849d5d61174670392839dee8c634"
V112_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_processor_sharing_work_training_result_v112.json"
)
V112_RESULT_RECEIPT_SHA256 = (
    "7f59b5b6fe0bb6c2321e26a7df88f5a5e44e473caa44a1feaa2f7a349a88c377"
)
V112_SOURCE_RESULT = Path(
    "tmp/nse_e3_processor_sharing_work_training_20260829_v112/training-result-v112.json"
)
V112_SOURCE_RESULT_SHA256 = (
    "b034bd9b0e58f4e21da044d6cd84d6502e3a21a33750c559435075575809bbd6"
)
BINARY_PATH = Path("tmp/nse_v113_build_e56a233/release/serverless_sim.exe")
BINARY_SHA256 = "ffe2aef6fd1cbaf9fa555b612a7b8d7748832cd21aacf54bb60f2959765c91b7"
BINARY_SOURCE_COMMIT = "e56a2337707ca8eb985ff570dc8396138a58e80f"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(908, 918)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(918, 928)]
TRAINING_SEED_LIST = ["E908", "E909", "E910"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1066, 1086)]
PREVIOUS_CONFIRMATION_SEEDS = [f"E{index}" for index in range(926, 1066)]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
    *[f"E{index}" for index in range(911, 926)],
]
PORT = "3146"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_ADMITTED_WORK = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_admitted_work10_initializer_only_"
    "guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v113-e3-anchor", "anchor", E3_ANCHOR, 9),
    (
        "v113-e3-causal-shock15-horizon50-admitted-work10-initializer-only",
        "candidate",
        E3_ADMITTED_WORK,
        9,
    ),
)


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v113-e3-training-config.json",
        "source": root / "manifest.v113-e908-e917-full.unbound.json",
        "capture": root / "manifest.v113-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v113.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V112_RESULT_RECEIPT, V112_RESULT_RECEIPT_SHA256),
        (V112_SOURCE_RESULT, V112_SOURCE_RESULT_SHA256),
        (FORMAL_RESULT, FORMAL_RESULT_SHA256),
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256),
        (SLA_PATH, SLA_SHA256),
        (MODEL_PATH, MODEL_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (PYTHON_PATH, PYTHON_SHA256),
        (CARGO_LOCK, CARGO_LOCK_SHA256),
        (MODULE_CONF, MODULE_CONF_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(f"frozen V113 input is missing or changed: {path}")


def _write_config(path: Path) -> None:
    config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    config["seed_policy"] = {
        "initial": SOURCE_INITIAL_SEEDS,
        "ci_extension": SOURCE_CI_SEEDS,
        "ci_extension_requires_trigger": True,
        "e7_initial": SOURCE_INITIAL_SEEDS[:5],
    }
    config["execution"]["command_template"] = [
        "{python}",
        "-m",
        "scripts.reviewer_experiments.protocol.serverless_adapter",
        "--run-config",
        "{run_config}",
        "--simulator-exe",
        str(BINARY_PATH.resolve()),
    ]
    write_json_atomic(path, config)


def _is_training_nash(run: dict) -> bool:
    return (
        run["experiment_id"] == "E3"
        and run["seed"] in TRAINING_SEEDS
        and run["method"] == "sche_nash"
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced"
        and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
    )


def _selected_ids(source_path: Path, predicate, expected: int) -> list[str]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    selected = [run["run_id"] for run in source["runs"] if predicate(run)]
    if len(selected) != expected:
        raise RuntimeError(f"expected {expected} selected runs, got {len(selected)}")
    return selected


def _rewrite(
    shard: dict,
    *,
    purpose: str,
    arm: tuple[str, str, str, int] | None = None,
    frozen_model_config: dict | None = None,
) -> dict:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": purpose,
            "v113_training_plan_sha256": PLAN_SHA256,
            "v113_training_only": True,
            "v113_binary_source_commit": BINARY_SOURCE_COMMIT,
            "selected_development_seeds": TRAINING_SEED_LIST,
            "sealed_confirmation_seeds": CONFIRMATION_SEEDS,
            "previous_confirmation_seeds_remaining_sealed": PREVIOUS_CONFIRMATION_SEEDS,
            "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
            "formal_results_eligible": False,
            "new_baseline_online_runs": 0,
            "formal_E01_E20_reexecution": 0,
        }
    )
    if arm is not None:
        if frozen_model_config is None:
            raise RuntimeError("V113 arm rewrite lacks frozen model binding")
        arm_id, role, profile, expected = arm
        candidate = role == "candidate"
        marker.update(
            {
                "v113_arm_id": arm_id,
                "v113_experiment_id": "E3",
                "v113_role": role,
                "v113_profile": profile,
                "v113_shock_threshold_numerator": 3 if candidate else None,
                "v113_shock_threshold_denominator": 2 if candidate else None,
                "v113_shock_activation_horizon_frames": 50 if candidate else None,
                "v113_critical_service_ratio_numerator": 9 if candidate else None,
                "v113_critical_service_ratio_denominator": 10 if candidate else None,
                "v113_service_proxy_work_source": (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if candidate
                    else "not_applicable"
                ),
                "v113_critical_frontier_substitution": candidate,
                "v113_noncritical_exact_anchor": candidate,
                "v113_expected_run_count": expected,
                "v113_scenario_or_burst_label_used_by_policy": False,
                "v113_completion_or_performance_fields_used_by_policy": False,
                "v113_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v113_training_plan_sha256": PLAN_SHA256,
                "v113_training_only": True,
                "v113_training_seed_metrics_previously_revealed": False,
                "v113_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v113_confirmation_seeds_opened": False,
                "v113_other_unopened_seeds_opened": False,
                "v113_formal_E01_E20_reexecution": False,
            }
        )
        if arm is not None:
            arm_id, role, profile, _ = arm
            candidate = role == "candidate"
            run["variant"] = arm_id
            run["environment"].update(COMMON_ENVIRONMENT)
            run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
            run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
                frozen_model_config
            )
            metadata.update(
                {
                    "v113_arm_id": arm_id,
                    "v113_arm_role": role,
                    "v113_candidate_profile": profile,
                    "v113_candidate_experiment": "E3",
                    "v113_shock_rate_ratio": "3/2" if candidate else None,
                    "v113_shock_threshold_numerator": 3 if candidate else None,
                    "v113_shock_threshold_denominator": 2 if candidate else None,
                    "v113_arrival_history_baseline_frames": 80 if candidate else None,
                    "v113_arrival_history_recent_frames": 20 if candidate else None,
                    "v113_arrival_min_requests_per_window": 20 if candidate else None,
                    "v113_shock_activation_horizon_frames": 50 if candidate else None,
                    "v113_nonterminal_queue_density_floor": 8.0 if candidate else None,
                    "v113_warm_admissibility": (
                        "preserve_anchor_warmness" if candidate else None
                    ),
                    "v113_load_least_window_certificate_mode": (
                        "disabled" if candidate else "not_applicable"
                    ),
                    "v113_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v113_critical_service_ratio_numerator": 9 if candidate else None,
                    "v113_critical_service_ratio_denominator": 10
                    if candidate
                    else None,
                    "v113_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
                        if candidate
                        else "not_applicable"
                    ),
                    "v113_service_proxy_work_source": (
                        "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                    "v113_admitted_work_includes_all_blocked_resident": candidate,
                    "v113_admitted_work_deterministic_f64_sum": candidate,
                    "v113_critical_service_proxy_inputs_finite_fail_closed": candidate,
                    "v113_cpu_memory_individual_noninferiority": candidate,
                    "v113_scalar_faasrank_noninferiority": candidate,
                    "v113_input_locality_component_noninferiority": candidate,
                    "v113_per_child_current_warm_downstream_locality_noninferiority": candidate,
                    "v113_critical_frontier_substitution": candidate,
                    "v113_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if candidate
                        else "not_applicable"
                    ),
                    "v113_noncritical_exact_anchor": candidate,
                    "v113_complete_summed_critical_service_proxy_strictly_lower": candidate,
                    "v113_complete_routed_score_nonworse": candidate,
                    "v113_complete_exact_ocs_score_nonworse": candidate,
                    "v113_complete_immutable_baseline_welfare_nonworse": candidate,
                    "v113_outcome_fields_drive_policy": False,
                    "v113_scenario_or_burst_label_used_by_policy": False,
                    "v113_completion_or_performance_fields_used_by_policy": False,
                    "v113_future_arrivals_used_by_policy": False,
                }
            )
            run["reference_dependency"] = _reference_dependency(run)
            run["simulator_experiment"]["reference"]["table_path"] = run[
                "reference_dependency"
            ]["path"]
        _assign_run_identity(run)

    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    marker["selected_run_count"] = len(rewritten["runs"])
    marker["selected_reference_build_count"] = len(
        rewritten["reference_build_dependencies"]
    )
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _write(path: Path, manifest: dict) -> None:
    write_json_atomic(path, manifest)


def prepare_v113(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V113 training root: {root}")
    root.mkdir(parents=True)
    paths = _paths(root)
    _write_config(paths["config"])
    write_manifest(paths["source"], paths["config"], seed_stage="initial")

    capture_ids = _selected_ids(
        paths["source"],
        lambda run: run["experiment_id"] == "E4"
        and run["method"] == "greedy"
        and run["seed"] in TRAINING_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced",
        3,
    )
    capture = derive_integration_smoke_shard(
        paths["source"], capture_ids, purpose=f"V113 fresh parent tapes {PLAN_SHA256}"
    )
    _write(
        paths["capture"],
        _rewrite(capture, purpose=f"V113 fresh parent tapes {PLAN_SHA256}"),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"], selected, purpose=f"V113 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite(
            template,
            purpose=f"V113 {arm_id} {PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != 9
            or len(manifest["reference_build_dependencies"]) != 9
        ):
            raise RuntimeError(f"V113 {arm_id} must have 9 runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V113 {arm_id} escaped E908-E910")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V113 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 18:
        raise RuntimeError("V113 must declare exactly 18 arm-specific references")

    manifest_paths = [paths["source"], paths["capture"]] + [
        arm_path(root, arm_id) for arm_id, _, _, _ in ARMS
    ]
    manifests = {}
    for path in manifest_paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        manifests[path.name] = {
            "file_sha256": file_hash(path),
            "manifest_hash": document["manifest_hash"],
            "run_count": len(document["runs"]),
            "reference_build_count": len(document["reference_build_dependencies"]),
        }
    receipt = {
        "schema_version": "NSE_E3_ADMITTED_WORK_PREPARED_V113_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V112_result_receipt_path": str(V112_RESULT_RECEIPT),
        "V112_result_receipt_sha256": V112_RESULT_RECEIPT_SHA256,
        "V112_source_result_path": str(V112_SOURCE_RESULT),
        "V112_source_result_sha256": V112_SOURCE_RESULT_SHA256,
        "formal_result_path": str(FORMAL_RESULT),
        "formal_result_sha256": FORMAL_RESULT_SHA256,
        "binary_path": str(BINARY_PATH),
        "binary_sha256": BINARY_SHA256,
        "binary_source_commit": BINARY_SOURCE_COMMIT,
        "python_path": str(PYTHON_PATH),
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_path": str(CARGO_LOCK),
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_path": str(MODULE_CONF),
        "module_conf_sha256": MODULE_CONF_SHA256,
        "sla_artifact_path": str(SLA_PATH),
        "sla_artifact_sha256": SLA_SHA256,
        "faasrank_model_path": str(MODEL_PATH),
        "faasrank_model_sha256": MODEL_SHA256,
        "training_seeds": TRAINING_SEED_LIST,
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "previous_confirmation_seeds_remaining_sealed": PREVIOUS_CONFIRMATION_SEEDS,
        "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
        "arms": [
            {
                "arm_id": arm_id,
                "experiment_id": "E3",
                "role": role,
                "profile": profile,
                "shock_rate_ratio": "3/2" if role == "candidate" else None,
                "shock_activation_horizon_frames": 50 if role == "candidate" else None,
                "maximum_candidate_to_anchor_service_proxy_ratio": (
                    "9/10" if role == "candidate" else None
                ),
                "service_proxy_work_source": (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "run_count": expected,
                "reference_build_count": expected,
            }
            for arm_id, role, profile, expected in ARMS
        ],
        "base_tape_captures": 3,
        "derived_burst_tapes": 9,
        "arm_reference_builds": 18,
        "arm_online_runs": 18,
        "new_baseline_method_runs": 0,
        "formal_E01_E20_reexecution": 0,
        "strictly_serial": True,
        "confirmation_inputs_generated": False,
        "other_unopened_inputs_generated": False,
        "manifests": manifests,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(paths["prepared"], receipt)
    return receipt


def main() -> None:
    prepare_v113()


if __name__ == "__main__":
    main()
