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


ROOT = Path("tmp/nse_e3_remaining_queue_work_training_20260829_v111")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_remaining_queue_work_training_plan_v111.json"
)
PLAN_SHA256 = "cba67e8c76db6ebfc2e84010177b585b0d9645b7589582f0e47448e0c43e438b"
V110_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_exact_queue_work_training_result_v110.json"
)
V110_RESULT_RECEIPT_SHA256 = (
    "d4fa765922d5483178b8d89f7fe96260a22fd76cada33e14a2dec1a49305aaa4"
)
V110_SOURCE_RESULT = Path(
    "tmp/nse_e3_exact_queue_work_training_20260829_v110/training-result-v110.json"
)
V110_SOURCE_RESULT_SHA256 = (
    "c62db82a56b9f55c3b2930ee18d630fef61b2ab8f43c72e8196f0ebbae3a8d74"
)
BINARY_PATH = Path("tmp/nse_v111_build_51b0053/release/serverless_sim.exe")
BINARY_SHA256 = "5c68e9cc35d0293740980c1c85c42f9fe9bb8673ef3c0a9eeaa0e649d1271fee"
BINARY_SOURCE_COMMIT = "51b005338a9a2a13a7b39681b063feff28f71816"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(902, 912)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(912, 922)]
TRAINING_SEED_LIST = ["E902", "E903", "E904"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1066, 1086)]
PREVIOUS_CONFIRMATION_SEEDS = [f"E{index}" for index in range(926, 1066)]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
    *[f"E{index}" for index in range(905, 926)],
]
PORT = "3144"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_REMAINING_QUEUE_WORK = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_remaining_queue_work10_initializer_only_"
    "guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v111-e3-anchor", "anchor", E3_ANCHOR, 9),
    (
        "v111-e3-causal-shock15-horizon50-remaining-queue-work10-initializer-only",
        "candidate",
        E3_REMAINING_QUEUE_WORK,
        9,
    ),
)


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v111-e3-training-config.json",
        "source": root / "manifest.v111-e902-e911-full.unbound.json",
        "capture": root / "manifest.v111-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v111.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V110_RESULT_RECEIPT, V110_RESULT_RECEIPT_SHA256),
        (V110_SOURCE_RESULT, V110_SOURCE_RESULT_SHA256),
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
            raise RuntimeError(f"frozen V111 input is missing or changed: {path}")


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
            "v111_training_plan_sha256": PLAN_SHA256,
            "v111_training_only": True,
            "v111_binary_source_commit": BINARY_SOURCE_COMMIT,
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
            raise RuntimeError("V111 arm rewrite lacks frozen model binding")
        arm_id, role, profile, expected = arm
        candidate = role == "candidate"
        marker.update(
            {
                "v111_arm_id": arm_id,
                "v111_experiment_id": "E3",
                "v111_role": role,
                "v111_profile": profile,
                "v111_shock_threshold_numerator": 3 if candidate else None,
                "v111_shock_threshold_denominator": 2 if candidate else None,
                "v111_shock_activation_horizon_frames": 50 if candidate else None,
                "v111_critical_service_ratio_numerator": 9 if candidate else None,
                "v111_critical_service_ratio_denominator": 10 if candidate else None,
                "v111_service_proxy_work_source": (
                    "immutable_pending_plus_current_runnable_remaining_and_same_window_projected_function_cpu_v1"
                    if candidate
                    else "not_applicable"
                ),
                "v111_critical_frontier_substitution": candidate,
                "v111_noncritical_exact_anchor": candidate,
                "v111_expected_run_count": expected,
                "v111_scenario_or_burst_label_used_by_policy": False,
                "v111_completion_or_performance_fields_used_by_policy": False,
                "v111_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v111_training_plan_sha256": PLAN_SHA256,
                "v111_training_only": True,
                "v111_training_seed_metrics_previously_revealed": False,
                "v111_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v111_confirmation_seeds_opened": False,
                "v111_other_unopened_seeds_opened": False,
                "v111_formal_E01_E20_reexecution": False,
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
                    "v111_arm_id": arm_id,
                    "v111_arm_role": role,
                    "v111_candidate_profile": profile,
                    "v111_candidate_experiment": "E3",
                    "v111_shock_rate_ratio": "3/2" if candidate else None,
                    "v111_shock_threshold_numerator": 3 if candidate else None,
                    "v111_shock_threshold_denominator": 2 if candidate else None,
                    "v111_arrival_history_baseline_frames": 80 if candidate else None,
                    "v111_arrival_history_recent_frames": 20 if candidate else None,
                    "v111_arrival_min_requests_per_window": 20 if candidate else None,
                    "v111_shock_activation_horizon_frames": 50 if candidate else None,
                    "v111_nonterminal_queue_density_floor": 8.0 if candidate else None,
                    "v111_warm_admissibility": (
                        "preserve_anchor_warmness" if candidate else None
                    ),
                    "v111_load_least_window_certificate_mode": (
                        "disabled" if candidate else "not_applicable"
                    ),
                    "v111_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v111_critical_service_ratio_numerator": 9 if candidate else None,
                    "v111_critical_service_ratio_denominator": 10
                    if candidate
                    else None,
                    "v111_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_remaining_queue_cpu_work"
                        if candidate
                        else "not_applicable"
                    ),
                    "v111_service_proxy_work_source": (
                        "immutable_pending_plus_current_runnable_remaining_and_same_window_projected_function_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                    "v111_remaining_queue_work_excludes_blocked_resident": candidate,
                    "v111_remaining_queue_work_deterministic_f64_sum": candidate,
                    "v111_critical_service_proxy_inputs_finite_fail_closed": candidate,
                    "v111_cpu_memory_individual_noninferiority": candidate,
                    "v111_scalar_faasrank_noninferiority": candidate,
                    "v111_input_locality_component_noninferiority": candidate,
                    "v111_per_child_current_warm_downstream_locality_noninferiority": candidate,
                    "v111_critical_frontier_substitution": candidate,
                    "v111_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if candidate
                        else "not_applicable"
                    ),
                    "v111_noncritical_exact_anchor": candidate,
                    "v111_complete_summed_critical_service_proxy_strictly_lower": candidate,
                    "v111_complete_routed_score_nonworse": candidate,
                    "v111_complete_exact_ocs_score_nonworse": candidate,
                    "v111_complete_immutable_baseline_welfare_nonworse": candidate,
                    "v111_outcome_fields_drive_policy": False,
                    "v111_scenario_or_burst_label_used_by_policy": False,
                    "v111_completion_or_performance_fields_used_by_policy": False,
                    "v111_future_arrivals_used_by_policy": False,
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


def prepare_v111(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V111 training root: {root}")
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
        paths["source"], capture_ids, purpose=f"V111 fresh parent tapes {PLAN_SHA256}"
    )
    _write(
        paths["capture"],
        _rewrite(capture, purpose=f"V111 fresh parent tapes {PLAN_SHA256}"),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"], selected, purpose=f"V111 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite(
            template,
            purpose=f"V111 {arm_id} {PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != 9
            or len(manifest["reference_build_dependencies"]) != 9
        ):
            raise RuntimeError(f"V111 {arm_id} must have 9 runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V111 {arm_id} escaped E902-E904")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V111 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 18:
        raise RuntimeError("V111 must declare exactly 18 arm-specific references")

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
        "schema_version": "NSE_E3_REMAINING_QUEUE_WORK_PREPARED_V111_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V110_result_receipt_path": str(V110_RESULT_RECEIPT),
        "V110_result_receipt_sha256": V110_RESULT_RECEIPT_SHA256,
        "V110_source_result_path": str(V110_SOURCE_RESULT),
        "V110_source_result_sha256": V110_SOURCE_RESULT_SHA256,
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
                    "immutable_pending_plus_current_runnable_remaining_and_same_window_projected_function_cpu_v1"
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
    prepare_v111()


if __name__ == "__main__":
    main()
