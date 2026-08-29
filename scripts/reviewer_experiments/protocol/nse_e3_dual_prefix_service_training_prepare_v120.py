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


ROOT = Path("tmp/nse_e3_dual_prefix_service_training_20260829_v120")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_dual_prefix_service_training_plan_v120.json"
)
PLAN_SHA256 = "e9c70086196812b605d7a8c0bf41f7726d1755cf6eb2edf3a90a89b7d6c0c642"
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
V119_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_all_player_service_construction_training_result_v119.json"
)
V119_RESULT_RECEIPT_SHA256 = (
    "a64a9d3b5a2ecb89854cbc47b9ec4ab1f38d437ec16756a4d6d3507b41866734"
)
V119_RESULT_RECEIPT_HASH = (
    "c2d2a4d19573280cbc288621f2cf7aea69ca8a02b5d8df3a667fe09c2a5582fa"
)
V119_RESULT_RECEIPT_COMMIT = "c46671b64f2e3b68afa15d27fb363b01fd88a2de"
BINARY_PATH = Path("tmp/nse_v120_build_b77f3fb/release/serverless_sim.exe")
BINARY_SHA256 = "8690a3a6daa2a1c512f3ad566a41331b79c0a7e7f2672a8f7ce6bd6d44509cb6"
BINARY_SOURCE_COMMIT = "b77f3fb416df79c4f3e04b409b1f5fdd851ec6ea"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(929, 939)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(939, 949)]
TRAINING_SEED_LIST = ["E929", "E930", "E931"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1106, 1126)]
PREVIOUS_CONFIRMATION_SEEDS = [f"E{index}" for index in range(932, 1106)]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
]
PORT = "3153"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_DUAL_PREFIX_SERVICE = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_admitted_work10_"
    "all_player_service_directed_dual_prefix_componentwise_pareto_initializer_only_guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v120-e3-anchor", "anchor", E3_ANCHOR, 9),
    (
        "v120-e3-causal-shock15-horizon50-admitted-work10-all-player-dual-prefix-service-directed-initializer-only",
        "candidate",
        E3_DUAL_PREFIX_SERVICE,
        9,
    ),
)


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v120-e3-training-config.json",
        "source": root / "manifest.v120-e929-e938-full.unbound.json",
        "capture": root / "manifest.v120-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v120.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V113_RESULT_RECEIPT, V113_RESULT_RECEIPT_SHA256),
        (V113_SOURCE_RESULT, V113_SOURCE_RESULT_SHA256),
        (V119_RESULT_RECEIPT, V119_RESULT_RECEIPT_SHA256),
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
            raise RuntimeError(f"frozen V120 input is missing or changed: {path}")
    parent = json.loads(V119_RESULT_RECEIPT.read_text(encoding="utf-8"))
    if parent.get("receipt_hash") != V119_RESULT_RECEIPT_HASH:
        raise RuntimeError("frozen V119 receipt object hash changed")


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
            "v120_training_plan_sha256": PLAN_SHA256,
            "v120_training_only": True,
            "v120_binary_source_commit": BINARY_SOURCE_COMMIT,
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
            raise RuntimeError("V120 arm rewrite lacks frozen model binding")
        arm_id, role, profile, expected = arm
        candidate = role == "candidate"
        marker.update(
            {
                "v120_arm_id": arm_id,
                "v120_experiment_id": "E3",
                "v120_role": role,
                "v120_profile": profile,
                "v120_shock_threshold_numerator": 3 if candidate else None,
                "v120_shock_threshold_denominator": 2 if candidate else None,
                "v120_shock_activation_horizon_frames": 50 if candidate else None,
                "v120_critical_service_ratio_numerator": 9 if candidate else None,
                "v120_critical_service_ratio_denominator": 10 if candidate else None,
                "v120_service_proxy_work_source": (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if candidate
                    else "not_applicable"
                ),
                "v120_complete_componentwise_service_pareto": candidate,
                "v120_componentwise_service_scope": (
                    "all_current_players" if candidate else "not_applicable"
                ),
                "v120_componentwise_service_comparison": (
                    "every_current_player_alternative_proxy_lte_anchor_plus_epsilon"
                    if candidate
                    else "not_applicable"
                ),
                "v120_componentwise_service_replay_order": (
                    "native_player_order" if candidate else "not_applicable"
                ),
                "v120_interference_constraints": False,
                "v120_arrival_phase_guard": False,
                "v120_critical_frontier_substitution": candidate,
                "v120_service_directed_construction": candidate,
                "v120_service_choice_scope": (
                    "all_current_players" if candidate else "not_applicable"
                ),
                "v120_dual_prefix_anchor_enabled": candidate,
                "v120_anchor_service_baseline_state": (
                    "independent_exact_anchor_native_order_prefix"
                    if candidate
                    else "not_applicable"
                ),
                "v120_candidate_service_state": (
                    "evolving_alternative_native_order_prefix"
                    if candidate
                    else "not_applicable"
                ),
                "v120_noncritical_exact_anchor": False,
                "v120_expected_run_count": expected,
                "v120_scenario_or_burst_label_used_by_policy": False,
                "v120_completion_or_performance_fields_used_by_policy": False,
                "v120_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v120_training_plan_sha256": PLAN_SHA256,
                "v120_training_only": True,
                "v120_training_seed_metrics_previously_revealed": False,
                "v120_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v120_confirmation_seeds_opened": False,
                "v120_other_unopened_seeds_opened": False,
                "v120_formal_E01_E20_reexecution": False,
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
                    "v120_arm_id": arm_id,
                    "v120_arm_role": role,
                    "v120_candidate_profile": profile,
                    "v120_candidate_experiment": "E3",
                    "v120_shock_rate_ratio": "3/2" if candidate else None,
                    "v120_shock_threshold_numerator": 3 if candidate else None,
                    "v120_shock_threshold_denominator": 2 if candidate else None,
                    "v120_arrival_history_baseline_frames": 80 if candidate else None,
                    "v120_arrival_history_recent_frames": 20 if candidate else None,
                    "v120_arrival_min_requests_per_window": 20 if candidate else None,
                    "v120_shock_activation_horizon_frames": 50 if candidate else None,
                    "v120_nonterminal_queue_density_floor": 8.0 if candidate else None,
                    "v120_warm_admissibility": (
                        "preserve_anchor_warmness" if candidate else None
                    ),
                    "v120_load_least_window_certificate_mode": (
                        "disabled" if candidate else "not_applicable"
                    ),
                    "v120_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v120_critical_service_ratio_numerator": 9 if candidate else None,
                    "v120_critical_service_ratio_denominator": 10
                    if candidate
                    else None,
                    "v120_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
                        if candidate
                        else "not_applicable"
                    ),
                    "v120_service_proxy_work_source": (
                        "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                    "v120_admitted_work_includes_all_blocked_resident": candidate,
                    "v120_admitted_work_deterministic_f64_sum": candidate,
                    "v120_complete_componentwise_service_pareto": candidate,
                    "v120_componentwise_service_scope": (
                        "all_current_players" if candidate else "not_applicable"
                    ),
                    "v120_componentwise_service_comparison": (
                        "every_current_player_alternative_proxy_lte_anchor_plus_epsilon"
                        if candidate
                        else "not_applicable"
                    ),
                    "v120_componentwise_service_replay_order": (
                        "native_player_order" if candidate else "not_applicable"
                    ),
                    "v120_componentwise_service_inputs_finite_fail_closed": candidate,
                    "v120_componentwise_service_coverage_mismatch_fail_closed": candidate,
                    "v120_interference_constraints": False,
                    "v120_arrival_phase_guard": False,
                    "v120_critical_service_proxy_inputs_finite_fail_closed": candidate,
                    "v120_cpu_memory_individual_noninferiority": candidate,
                    "v120_scalar_faasrank_noninferiority": candidate,
                    "v120_input_locality_component_noninferiority": candidate,
                    "v120_per_child_current_warm_downstream_locality_noninferiority": candidate,
                    "v120_critical_frontier_substitution": candidate,
                    "v120_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if candidate
                        else "not_applicable"
                    ),
                    "v120_service_directed_construction": candidate,
                    "v120_service_choice_scope": (
                        "all_current_players" if candidate else "not_applicable"
                    ),
                    "v120_dual_prefix_anchor_enabled": candidate,
                    "v120_anchor_service_baseline_state": (
                        "independent_exact_anchor_native_order_prefix"
                        if candidate
                        else "not_applicable"
                    ),
                    "v120_candidate_service_state": (
                        "evolving_alternative_native_order_prefix"
                        if candidate
                        else "not_applicable"
                    ),
                    "v120_dual_prefix_inputs_finite_fail_closed": candidate,
                    "v120_noncritical_exact_anchor": False,
                    "v120_complete_summed_critical_service_proxy_strictly_lower": candidate,
                    "v120_complete_routed_score_nonworse": candidate,
                    "v120_complete_exact_ocs_score_nonworse": candidate,
                    "v120_complete_immutable_baseline_welfare_nonworse": candidate,
                    "v120_outcome_fields_drive_policy": False,
                    "v120_scenario_or_burst_label_used_by_policy": False,
                    "v120_completion_or_performance_fields_used_by_policy": False,
                    "v120_future_arrivals_used_by_policy": False,
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


def prepare_v120(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V120 training root: {root}")
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
        paths["source"], capture_ids, purpose=f"V120 fresh parent tapes {PLAN_SHA256}"
    )
    _write(
        paths["capture"],
        _rewrite(capture, purpose=f"V120 fresh parent tapes {PLAN_SHA256}"),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"], selected, purpose=f"V120 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite(
            template,
            purpose=f"V120 {arm_id} {PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != 9
            or len(manifest["reference_build_dependencies"]) != 9
        ):
            raise RuntimeError(f"V120 {arm_id} must have 9 runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V120 {arm_id} escaped E929-E931")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V120 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 18:
        raise RuntimeError("V120 must declare exactly 18 arm-specific references")

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
        "schema_version": "NSE_E3_DUAL_PREFIX_SERVICE_PREPARED_V120_V1",
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
        "V119_result_receipt_path": str(V119_RESULT_RECEIPT),
        "V119_result_receipt_sha256": V119_RESULT_RECEIPT_SHA256,
        "V119_result_receipt_hash": V119_RESULT_RECEIPT_HASH,
        "V119_result_receipt_commit": V119_RESULT_RECEIPT_COMMIT,
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
                "dual_prefix_anchor_enabled": role == "candidate",
                "anchor_service_baseline_state": (
                    "independent_exact_anchor_native_order_prefix"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "candidate_service_state": (
                    "evolving_alternative_native_order_prefix"
                    if role == "candidate"
                    else "not_applicable"
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
    prepare_v120()


if __name__ == "__main__":
    main()
