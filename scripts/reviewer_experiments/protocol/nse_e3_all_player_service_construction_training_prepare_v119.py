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


ROOT = Path("tmp/nse_e3_all_player_service_construction_training_20260829_v119")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_all_player_service_construction_training_plan_v119.json"
)
PLAN_SHA256 = "c749422361e143be475f43e810fa2fc31b1d102671d42c91e8629bca72a784ec"
V113_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_admitted_work_training_result_v113.json"
)
V113_RESULT_RECEIPT_SHA256 = (
    "a51866155d4c7858dcc4c1eb6bf18b943533858422ba3fe98652f3ffb6915004"
)
V113_SOURCE_RESULT = Path(
    "tmp/nse_e3_admitted_work_training_20260829_v113/training-result-v113.json"
)
V113_SOURCE_RESULT_SHA256 = (
    "a1228fedc1e9e050cb98db1b9bfdfc7bc027b6ae3ac1457d124448b0851df2d7"
)
V118_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_all_player_service_training_result_v118.json"
)
V118_RESULT_RECEIPT_SHA256 = (
    "8a02fd79087bfd96095363bfcc8e5ae3644410ccbe66729e550eb96bacf2a091"
)
V118_RESULT_RECEIPT_HASH = (
    "89344255e84bf708f532d4683956ae050b8ae5b34e5eb0f3c8abbab7fba56539"
)
V118_RESULT_RECEIPT_COMMIT = "68d1603520b6b3910463f815a4afec569263a3ac"
BINARY_PATH = Path("tmp/nse_v119_build_9a377c3/release/serverless_sim.exe")
BINARY_SHA256 = "39e6fd80da3e89e45b074ae7af4fb0ae3474def3ad754073f13e8e521b089ebb"
BINARY_SOURCE_COMMIT = "9a377c3ef88a0f4f0fc6c446a9221e0460dff97b"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(926, 936)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(936, 946)]
TRAINING_SEED_LIST = ["E926", "E927", "E928"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1106, 1126)]
PREVIOUS_CONFIRMATION_SEEDS = [f"E{index}" for index in range(929, 1106)]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
]
PORT = "3152"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_ALL_PLAYER_SERVICE = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_admitted_work10_"
    "all_player_service_directed_componentwise_pareto_initializer_only_guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v119-e3-anchor", "anchor", E3_ANCHOR, 9),
    (
        "v119-e3-causal-shock15-horizon50-admitted-work10-all-player-service-directed-initializer-only",
        "candidate",
        E3_ALL_PLAYER_SERVICE,
        9,
    ),
)


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v119-e3-training-config.json",
        "source": root / "manifest.v119-e926-e935-full.unbound.json",
        "capture": root / "manifest.v119-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v119.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V113_RESULT_RECEIPT, V113_RESULT_RECEIPT_SHA256),
        (V113_SOURCE_RESULT, V113_SOURCE_RESULT_SHA256),
        (V118_RESULT_RECEIPT, V118_RESULT_RECEIPT_SHA256),
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
            raise RuntimeError(f"frozen V119 input is missing or changed: {path}")
    parent = json.loads(V118_RESULT_RECEIPT.read_text(encoding="utf-8"))
    if parent.get("receipt_hash") != V118_RESULT_RECEIPT_HASH:
        raise RuntimeError("frozen V118 receipt object hash changed")


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
            "v119_training_plan_sha256": PLAN_SHA256,
            "v119_training_only": True,
            "v119_binary_source_commit": BINARY_SOURCE_COMMIT,
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
            raise RuntimeError("V119 arm rewrite lacks frozen model binding")
        arm_id, role, profile, expected = arm
        candidate = role == "candidate"
        marker.update(
            {
                "v119_arm_id": arm_id,
                "v119_experiment_id": "E3",
                "v119_role": role,
                "v119_profile": profile,
                "v119_shock_threshold_numerator": 3 if candidate else None,
                "v119_shock_threshold_denominator": 2 if candidate else None,
                "v119_shock_activation_horizon_frames": 50 if candidate else None,
                "v119_critical_service_ratio_numerator": 9 if candidate else None,
                "v119_critical_service_ratio_denominator": 10 if candidate else None,
                "v119_service_proxy_work_source": (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if candidate
                    else "not_applicable"
                ),
                "v119_complete_componentwise_service_pareto": candidate,
                "v119_componentwise_service_scope": (
                    "all_current_players" if candidate else "not_applicable"
                ),
                "v119_componentwise_service_comparison": (
                    "every_current_player_alternative_proxy_lte_anchor_plus_epsilon"
                    if candidate
                    else "not_applicable"
                ),
                "v119_componentwise_service_replay_order": (
                    "native_player_order" if candidate else "not_applicable"
                ),
                "v119_interference_constraints": False,
                "v119_arrival_phase_guard": False,
                "v119_critical_frontier_substitution": candidate,
                "v119_service_directed_construction": candidate,
                "v119_service_choice_scope": (
                    "all_current_players" if candidate else "not_applicable"
                ),
                "v119_noncritical_exact_anchor": False,
                "v119_expected_run_count": expected,
                "v119_scenario_or_burst_label_used_by_policy": False,
                "v119_completion_or_performance_fields_used_by_policy": False,
                "v119_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v119_training_plan_sha256": PLAN_SHA256,
                "v119_training_only": True,
                "v119_training_seed_metrics_previously_revealed": False,
                "v119_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v119_confirmation_seeds_opened": False,
                "v119_other_unopened_seeds_opened": False,
                "v119_formal_E01_E20_reexecution": False,
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
                    "v119_arm_id": arm_id,
                    "v119_arm_role": role,
                    "v119_candidate_profile": profile,
                    "v119_candidate_experiment": "E3",
                    "v119_shock_rate_ratio": "3/2" if candidate else None,
                    "v119_shock_threshold_numerator": 3 if candidate else None,
                    "v119_shock_threshold_denominator": 2 if candidate else None,
                    "v119_arrival_history_baseline_frames": 80 if candidate else None,
                    "v119_arrival_history_recent_frames": 20 if candidate else None,
                    "v119_arrival_min_requests_per_window": 20 if candidate else None,
                    "v119_shock_activation_horizon_frames": 50 if candidate else None,
                    "v119_nonterminal_queue_density_floor": 8.0 if candidate else None,
                    "v119_warm_admissibility": (
                        "preserve_anchor_warmness" if candidate else None
                    ),
                    "v119_load_least_window_certificate_mode": (
                        "disabled" if candidate else "not_applicable"
                    ),
                    "v119_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v119_critical_service_ratio_numerator": 9 if candidate else None,
                    "v119_critical_service_ratio_denominator": 10
                    if candidate
                    else None,
                    "v119_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
                        if candidate
                        else "not_applicable"
                    ),
                    "v119_service_proxy_work_source": (
                        "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                    "v119_admitted_work_includes_all_blocked_resident": candidate,
                    "v119_admitted_work_deterministic_f64_sum": candidate,
                    "v119_complete_componentwise_service_pareto": candidate,
                    "v119_componentwise_service_scope": (
                        "all_current_players" if candidate else "not_applicable"
                    ),
                    "v119_componentwise_service_comparison": (
                        "every_current_player_alternative_proxy_lte_anchor_plus_epsilon"
                        if candidate
                        else "not_applicable"
                    ),
                    "v119_componentwise_service_replay_order": (
                        "native_player_order" if candidate else "not_applicable"
                    ),
                    "v119_componentwise_service_inputs_finite_fail_closed": candidate,
                    "v119_componentwise_service_coverage_mismatch_fail_closed": candidate,
                    "v119_interference_constraints": False,
                    "v119_arrival_phase_guard": False,
                    "v119_critical_service_proxy_inputs_finite_fail_closed": candidate,
                    "v119_cpu_memory_individual_noninferiority": candidate,
                    "v119_scalar_faasrank_noninferiority": candidate,
                    "v119_input_locality_component_noninferiority": candidate,
                    "v119_per_child_current_warm_downstream_locality_noninferiority": candidate,
                    "v119_critical_frontier_substitution": candidate,
                    "v119_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if candidate
                        else "not_applicable"
                    ),
                    "v119_service_directed_construction": candidate,
                    "v119_service_choice_scope": (
                        "all_current_players" if candidate else "not_applicable"
                    ),
                    "v119_noncritical_exact_anchor": False,
                    "v119_complete_summed_critical_service_proxy_strictly_lower": candidate,
                    "v119_complete_routed_score_nonworse": candidate,
                    "v119_complete_exact_ocs_score_nonworse": candidate,
                    "v119_complete_immutable_baseline_welfare_nonworse": candidate,
                    "v119_outcome_fields_drive_policy": False,
                    "v119_scenario_or_burst_label_used_by_policy": False,
                    "v119_completion_or_performance_fields_used_by_policy": False,
                    "v119_future_arrivals_used_by_policy": False,
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


def prepare_v119(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V119 training root: {root}")
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
        paths["source"], capture_ids, purpose=f"V119 fresh parent tapes {PLAN_SHA256}"
    )
    _write(
        paths["capture"],
        _rewrite(capture, purpose=f"V119 fresh parent tapes {PLAN_SHA256}"),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"], selected, purpose=f"V119 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite(
            template,
            purpose=f"V119 {arm_id} {PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != 9
            or len(manifest["reference_build_dependencies"]) != 9
        ):
            raise RuntimeError(f"V119 {arm_id} must have 9 runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V119 {arm_id} escaped E926-E928")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V119 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 18:
        raise RuntimeError("V119 must declare exactly 18 arm-specific references")

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
        "schema_version": "NSE_E3_ALL_PLAYER_SERVICE_PREPARED_V119_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V113_result_receipt_path": str(V113_RESULT_RECEIPT),
        "V113_result_receipt_sha256": V113_RESULT_RECEIPT_SHA256,
        "V113_source_result_path": str(V113_SOURCE_RESULT),
        "V113_source_result_sha256": V113_SOURCE_RESULT_SHA256,
        "V118_result_receipt_path": str(V118_RESULT_RECEIPT),
        "V118_result_receipt_sha256": V118_RESULT_RECEIPT_SHA256,
        "V118_result_receipt_hash": V118_RESULT_RECEIPT_HASH,
        "V118_result_receipt_commit": V118_RESULT_RECEIPT_COMMIT,
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
                "service_directed_construction": role == "candidate",
                "service_choice_scope": (
                    "all_current_players" if role == "candidate" else "not_applicable"
                ),
                "complete_componentwise_service_rule": (
                    "every_current_player_alternative_proxy_lte_anchor_plus_epsilon"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "componentwise_service_replay_order": (
                    "native_player_order" if role == "candidate" else "not_applicable"
                ),
                "componentwise_service_scope": (
                    "all_current_players" if role == "candidate" else "not_applicable"
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
    prepare_v119()


if __name__ == "__main__":
    main()
