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


ROOT = Path(
    "tmp/nse_e3_componentwise_service_componentwise_interference_training_20260830_v133"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_componentwise_service_componentwise_interference_training_plan_v133.json"
)
PLAN_SHA256 = "6cee0e71f268d0ec947f257c5a79223d5662d5ed7e5dc3888c1d7aba69177283"
V117_PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_componentwise_service_training_plan_v117.json"
)
V117_PLAN_SHA256 = "b67c44f83d04141258f59ef0886a81e72ae83187059ce6e5d776290fab50126f"
V117_RESULT = Path(
    "tmp/nse_e3_componentwise_service_training_20260829_v117/"
    "training-result-v117.json"
)
V117_RESULT_SHA256 = "e59d4f3d308fc87206307620edb83091a91c218b4a6e205cf2324a2db5b91c5f"
V132_PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_componentwise_service_complete_interference_training_plan_v132.json"
)
V132_PLAN_SHA256 = "27619d4ebd8217334ed078f0f72315d49c295ae69cf082f068609b46c0444b34"
V132_BLIND_AUDIT = Path(
    "tmp/nse_e3_componentwise_service_complete_interference_training_20260830_v132/"
    "joint-blind-audit-v132-training.json"
)
V132_BLIND_AUDIT_SHA256 = (
    "e6ed1e3ac069f9090f5b987fac63ed42ed9f7b9c6ac9e0f4b9b034a23fbf48dd"
)
BINARY_PATH = Path("tmp/nse_v133_build_5c263a6/release/serverless_sim.exe")
BINARY_SHA256 = "e895ade1a0bc6f78b1b02a1273593f191ac268f60f878d6d9baf0d879edeb546"
BINARY_SOURCE_COMMIT = "5c263a667b20e6a131e106baac7bc01d4ca40bec"

TRAINING_SEED_LIST = ["E1402", "E1403", "E1404"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
SOURCE_INITIAL_SEEDS = [
    *TRAINING_SEED_LIST,
    "E1379",
    "E1380",
    "E1381",
    "E1356",
    "E1357",
    "E1358",
    "E1333",
]
SOURCE_CI_SEEDS = [
    "E1334",
    "E1335",
    "E1310",
    "E1311",
    "E1312",
    "E1287",
    "E1288",
    "E1289",
    "E1264",
    "E1265",
]
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1405, 1425)]
PREVIOUS_CONFIRMATION_SEEDS = [
    *[f"E{index}" for index in range(1382, 1402)],
    *[f"E{index}" for index in range(1359, 1379)],
    *[f"E{index}" for index in range(1336, 1356)],
    *[f"E{index}" for index in range(1313, 1333)],
    *[f"E{index}" for index in range(1290, 1310)],
    *[f"E{index}" for index in range(1267, 1287)],
]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(1198, 1241)],
    *[f"E{index}" for index in range(1244, 1264)],
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
]
PORT = "3164"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_COMPONENTWISE_SERVICE_COMPONENTWISE_INTERFERENCE = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_admitted_work10_"
    "componentwise_service_componentwise_interference_pareto_initializer_only_guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v133-e3-anchor", "anchor", E3_ANCHOR, 9),
    (
        "v133-e3-causal-shock15-horizon50-admitted-work10-componentwise-service-complete-interference-initializer-only",
        "candidate",
        E3_COMPONENTWISE_SERVICE_COMPONENTWISE_INTERFERENCE,
        9,
    ),
)


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v133-e3-training-config.json",
        "source": root / "manifest.v133-training-source-full.unbound.json",
        "capture": root / "manifest.v133-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v133.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V117_PLAN, V117_PLAN_SHA256),
        (V117_RESULT, V117_RESULT_SHA256),
        (V132_PLAN, V132_PLAN_SHA256),
        (V132_BLIND_AUDIT, V132_BLIND_AUDIT_SHA256),
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
            raise RuntimeError(f"frozen V133 input is missing or changed: {path}")


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
            "v133_training_plan_sha256": PLAN_SHA256,
            "v133_training_only": True,
            "v133_binary_source_commit": BINARY_SOURCE_COMMIT,
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
            raise RuntimeError("V133 arm rewrite lacks frozen model binding")
        arm_id, role, profile, expected = arm
        candidate = role == "candidate"
        marker.update(
            {
                "v133_arm_id": arm_id,
                "v133_experiment_id": "E3",
                "v133_role": role,
                "v133_profile": profile,
                "v133_shock_threshold_numerator": 3 if candidate else None,
                "v133_shock_threshold_denominator": 2 if candidate else None,
                "v133_shock_activation_horizon_frames": 50 if candidate else None,
                "v133_critical_service_ratio_numerator": 9 if candidate else None,
                "v133_critical_service_ratio_denominator": 10 if candidate else None,
                "v133_service_proxy_work_source": (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if candidate
                    else "not_applicable"
                ),
                "v133_complete_componentwise_service_pareto": candidate,
                "v133_componentwise_service_comparison": (
                    "every_current_critical_frontier_alternative_proxy_lte_anchor_plus_epsilon"
                    if candidate
                    else "not_applicable"
                ),
                "v133_componentwise_service_replay_order": (
                    "native_player_order" if candidate else "not_applicable"
                ),
                "v133_complete_admitted_interference_pareto": False,
                "v133_componentwise_admitted_interference_pareto": candidate,
                "v133_componentwise_interference_comparison": (
                    "candidate_player_interference_lte_anchor_plus_epsilon"
                    if candidate
                    else "not_applicable"
                ),
                "v133_arrival_phase_guard": False,
                "v133_critical_frontier_substitution": candidate,
                "v133_noncritical_exact_anchor": candidate,
                "v133_expected_run_count": expected,
                "v133_scenario_or_burst_label_used_by_policy": False,
                "v133_completion_or_performance_fields_used_by_policy": False,
                "v133_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v133_training_plan_sha256": PLAN_SHA256,
                "v133_training_only": True,
                "v133_training_seed_metrics_previously_revealed": False,
                "v133_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v133_confirmation_seeds_opened": False,
                "v133_other_unopened_seeds_opened": False,
                "v133_formal_E01_E20_reexecution": False,
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
                    "v133_arm_id": arm_id,
                    "v133_arm_role": role,
                    "v133_candidate_profile": profile,
                    "v133_candidate_experiment": "E3",
                    "v133_shock_rate_ratio": "3/2" if candidate else None,
                    "v133_shock_threshold_numerator": 3 if candidate else None,
                    "v133_shock_threshold_denominator": 2 if candidate else None,
                    "v133_arrival_history_baseline_frames": 80 if candidate else None,
                    "v133_arrival_history_recent_frames": 20 if candidate else None,
                    "v133_arrival_min_requests_per_window": 20 if candidate else None,
                    "v133_shock_activation_horizon_frames": 50 if candidate else None,
                    "v133_nonterminal_queue_density_floor": 8.0 if candidate else None,
                    "v133_warm_admissibility": (
                        "preserve_anchor_warmness" if candidate else None
                    ),
                    "v133_load_least_window_certificate_mode": (
                        "disabled" if candidate else "not_applicable"
                    ),
                    "v133_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v133_critical_service_ratio_numerator": 9 if candidate else None,
                    "v133_critical_service_ratio_denominator": 10
                    if candidate
                    else None,
                    "v133_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
                        if candidate
                        else "not_applicable"
                    ),
                    "v133_service_proxy_work_source": (
                        "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                    "v133_admitted_work_includes_all_blocked_resident": candidate,
                    "v133_admitted_work_deterministic_f64_sum": candidate,
                    "v133_complete_componentwise_service_pareto": candidate,
                    "v133_componentwise_service_comparison": (
                        "every_current_critical_frontier_alternative_proxy_lte_anchor_plus_epsilon"
                        if candidate
                        else "not_applicable"
                    ),
                    "v133_componentwise_service_replay_order": (
                        "native_player_order" if candidate else "not_applicable"
                    ),
                    "v133_componentwise_service_inputs_finite_fail_closed": candidate,
                    "v133_componentwise_service_coverage_mismatch_fail_closed": candidate,
                    "v133_complete_admitted_interference_pareto": False,
                    "v133_componentwise_admitted_interference_pareto": candidate,
                    "v133_componentwise_interference_definition": (
                        "current_player_sum_of_min_admitted_work_and_player_work_over_node_capacity"
                        if candidate
                        else "not_applicable"
                    ),
                    "v133_componentwise_interference_comparison": (
                        "candidate_player_interference_lte_anchor_plus_epsilon"
                        if candidate
                        else "not_applicable"
                    ),
                    "v133_componentwise_interference_inputs_finite_fail_closed": candidate,
                    "v133_arrival_phase_guard": False,
                    "v133_critical_service_proxy_inputs_finite_fail_closed": candidate,
                    "v133_cpu_memory_individual_noninferiority": candidate,
                    "v133_scalar_faasrank_noninferiority": candidate,
                    "v133_input_locality_component_noninferiority": candidate,
                    "v133_per_child_current_warm_downstream_locality_noninferiority": candidate,
                    "v133_critical_frontier_substitution": candidate,
                    "v133_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if candidate
                        else "not_applicable"
                    ),
                    "v133_noncritical_exact_anchor": candidate,
                    "v133_complete_summed_critical_service_proxy_strictly_lower": candidate,
                    "v133_complete_routed_score_nonworse": candidate,
                    "v133_complete_exact_ocs_score_nonworse": candidate,
                    "v133_complete_immutable_baseline_welfare_nonworse": candidate,
                    "v133_outcome_fields_drive_policy": False,
                    "v133_scenario_or_burst_label_used_by_policy": False,
                    "v133_completion_or_performance_fields_used_by_policy": False,
                    "v133_future_arrivals_used_by_policy": False,
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


def prepare_v133(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V133 training root: {root}")
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
        paths["source"], capture_ids, purpose=f"V133 fresh parent tapes {PLAN_SHA256}"
    )
    _write(
        paths["capture"],
        _rewrite(capture, purpose=f"V133 fresh parent tapes {PLAN_SHA256}"),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"], selected, purpose=f"V133 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite(
            template,
            purpose=f"V133 {arm_id} {PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != 9
            or len(manifest["reference_build_dependencies"]) != 9
        ):
            raise RuntimeError(f"V133 {arm_id} must have 9 runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V133 {arm_id} escaped E1402-E1404")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V133 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 18:
        raise RuntimeError("V133 must declare exactly 18 arm-specific references")

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
        "schema_version": "NSE_E3_COMPONENTWISE_SERVICE_COMPONENTWISE_INTERFERENCE_PREPARED_V133_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V117_plan_path": str(V117_PLAN),
        "V117_plan_sha256": V117_PLAN_SHA256,
        "V117_result_path": str(V117_RESULT),
        "V117_result_sha256": V117_RESULT_SHA256,
        "V132_plan_path": str(V132_PLAN),
        "V132_plan_sha256": V132_PLAN_SHA256,
        "V132_blind_audit_path": str(V132_BLIND_AUDIT),
        "V132_blind_audit_sha256": V132_BLIND_AUDIT_SHA256,
        "V132_performance_result_reopened": False,
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
                "complete_componentwise_service_rule": (
                    "every_current_critical_frontier_alternative_proxy_lte_anchor_plus_epsilon"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "componentwise_service_replay_order": (
                    "native_player_order" if role == "candidate" else "not_applicable"
                ),
                "componentwise_interference_rule": (
                    "candidate_player_interference_lte_anchor_plus_epsilon"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "componentwise_per_choice_interference": role == "candidate",
                "complete_aggregate_interference": False,
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
    prepare_v133()


if __name__ == "__main__":
    main()
