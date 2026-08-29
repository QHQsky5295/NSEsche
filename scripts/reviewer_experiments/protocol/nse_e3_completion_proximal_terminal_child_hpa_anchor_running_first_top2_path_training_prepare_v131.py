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
    "tmp/nse_e3_completion_proximal_terminal_child_hpa_anchor_running_first_top2_path_training_20260829_v131"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_completion_proximal_terminal_child_hpa_anchor_running_first_top2_path_training_plan_v131.json"
)
PLAN_SHA256 = "45510e542b0c8a97301d4f301b65a93935e3e2c09d904efd109ed05580d63805"
V130_RESULT = Path(
    "tmp/nse_e3_completion_proximal_terminal_child_hpa_anchor_top2_path_training_20260829_v130/"
    "training-result-v130.json"
)
V130_RESULT_SHA256 = "85ca56273e76518c9c4216f6904c4b480792829f73727e4017f8c0ddb53954de"
V130_RESULT_HASH = "1cb1bb802a8aa0abd4b2d92d7e6d24131ba1d435fa816935dfd0d7082c8d9237"
V130_RESULT_COMMIT = "29356467addeeb58ebc413b5e6842c6b1b19cc8a"
V130_BLIND_AUDIT = Path(
    "tmp/nse_e3_completion_proximal_terminal_child_hpa_anchor_top2_path_training_20260829_v130/"
    "joint-blind-audit-v130-training.json"
)
V130_BLIND_AUDIT_SHA256 = (
    "1b8877a396510918f4eef999d2b2d8548d1f12ded5f66403c5490667cdfafa24"
)
V130_BLIND_AUDIT_HASH = (
    "5cf8fe5e1a5ac6b8ee153533cea2ad75007dea7f4df4ee05c8ee01a866e0d103"
)
V130_BLIND_AUDIT_COMMIT = "68b883d7334f36e29103d3fe6011af3ba41d4d95"
V129_RESULT = Path(
    "tmp/nse_e3_completion_proximal_terminal_child_hpa_anchor_argmin_path_training_20260829_v129/"
    "training-result-v129.json"
)
V129_RESULT_SHA256 = "46c916dc4c621a197bb4e0b94d6f6ae403a76202945f64cbba57483ae1af39f2"
V129_RESULT_HASH = "8f8f095bda8ae5b0e8aeb8c239e131526c5025e543d8b3abd4e79849dc03e0ab"
V129_RESULT_COMMIT = "d28cd51064b86843f5a47091799992bbe1a449aa"
V129_BLIND_AUDIT = Path(
    "tmp/nse_e3_completion_proximal_terminal_child_hpa_anchor_argmin_path_training_20260829_v129/"
    "joint-blind-audit-v129-training.json"
)
V129_BLIND_AUDIT_SHA256 = (
    "5e748f21b3fa43b8af248a6e610daefb73d9e852502c9f5bab78d95d97e03f41"
)
V129_BLIND_AUDIT_HASH = (
    "c30f38084027583323df43ba1a356bc4312a358c61e64f2147830f6ac2d12c12"
)
V129_BLIND_AUDIT_COMMIT = "5e325842e9eb6bcd0e49d5db32e31e44d27ff8d3"
V127_RESULT = Path(
    "tmp/nse_e3_completion_proximal_terminal_child_hpa_path_training_20260829_v127/"
    "training-result-v127.json"
)
V127_RESULT_SHA256 = "0314620c9752a06d703d66b24983b2180467cf693260c9f5dc07541ffff84231"
V127_RESULT_HASH = "2f7ee278f25ae051e4c330e1bf0681151b603fd5ca345504105aa521a0291514"
V127_RESULT_COMMIT = "6267c4d75da3ddc552e7c43ff06891aeb99b1760"
V124_RESULT = Path(
    "tmp/nse_e3_completion_proximal_componentwise_training_20260829_v124/"
    "training-result-v124.json"
)
V124_RESULT_SHA256 = "c3a8853ed4f949e3cd6be6c0388ec4118e9283e3f3f851637bc7ff54b92f5bd2"
V124_RESULT_HASH = "ce90080618070dfc54291b88f91a374ed01053e44011d327f944a95ae3ed3c40"
V124_RESULT_COMMIT = "2332cccf33470356169f2ad2847214372ab3c33b"
V125_INVALIDATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_completion_proximal_changed_player_training_plan_v125_invalidated.json"
)
V125_INVALIDATION_SHA256 = (
    "a9dfc19bf353063d9f1363ec6689596e799094810527b4d430e76b5290bcdfac"
)
V126_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_completion_proximal_terminal_child_path_training_blind_failure_v126.json"
)
V126_FAILURE_SHA256 = "fe0f22e8599b66af60e005a246bc715e271dc4fc33b81670805833713dd637b2"
V126_FAILURE_HASH = "c4ffa1bd7c461dd957c0d1f09d9c58c2f43ac638b246b36041acf19f7fa59053"
V126_FAILURE_COMMIT = "3894f86f3b78efb80268ba569774b48d4cb8e7ca"
V123_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_completion_proximal_training_result_v123.json"
)
V123_RESULT_RECEIPT_SHA256 = (
    "0c7347259243655171910dfb7d1ad8c2a86d50e9830784384cfd0bd124ef190a"
)
V123_RESULT_RECEIPT_HASH = (
    "a6b644690714d4a85daa266c337cae3e18abe3cbd3d7b1bf1a62e593166e31f0"
)
V123_RESULT_RECEIPT_COMMIT = "d41ba055682c3145d48f91f967c37d391972e37e"
V113_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_admitted_work_training_result_v113.json"
)
V113_RESULT_RECEIPT_SHA256 = (
    "a51866155d4c7858dcc4c1eb6bf18b943533858422ba3fe98652f3ffb6915004"
)
V113_RESULT_RECEIPT_HASH = (
    "8ca06251384dadffbd3ec1d724396eb556dd4d3948e3dadbd5485926ebc702da"
)
V113_SOURCE_RESULT = Path(
    "tmp/nse_e3_admitted_work_training_20260829_v113/training-result-v113.json"
)
V113_SOURCE_RESULT_SHA256 = (
    "a1228fedc1e9e050cb98db1b9bfdfc7bc027b6ae3ac1457d124448b0851df2d7"
)
BINARY_PATH = Path("tmp/nse_v131_build_13b5c78/release/serverless_sim.exe")
BINARY_SHA256 = "196fd6f5b5c5bbc04105f3d4cb07143946aa7b9de2fba18aef1b1b02797f68e5"
BINARY_SOURCE_COMMIT = "13b5c78f6a15e9576246238e0d3cbc4069a89a39"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(1356, 1366)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(1366, 1376)]
TRAINING_SEED_LIST = ["E1356", "E1357", "E1358"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1359, 1379)]
PREVIOUS_CONFIRMATION_SEEDS = [
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
PORT = "3162"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_ADMITTED_WORK = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_admitted_work10_completion_proximal_depth1_componentwise_service_terminal_child_hpa_anchor_running_first_top2_path_pareto_initializer_only_"
    "guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v131-e3-anchor", "anchor", E3_ANCHOR, 9),
    (
        "v131-e3-causal-shock15-horizon50-admitted-work10-completion-proximal-depth1-componentwise-service-terminal-child-hpa-anchor-running-first-top2-path-pareto-initializer-only",
        "candidate",
        E3_ADMITTED_WORK,
        9,
    ),
)


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v131-e3-training-config.json",
        "source": root / "manifest.v131-e1356-e1365-full.unbound.json",
        "capture": root / "manifest.v131-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v131.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V130_RESULT, V130_RESULT_SHA256),
        (V130_BLIND_AUDIT, V130_BLIND_AUDIT_SHA256),
        (V129_RESULT, V129_RESULT_SHA256),
        (V129_BLIND_AUDIT, V129_BLIND_AUDIT_SHA256),
        (V127_RESULT, V127_RESULT_SHA256),
        (V126_FAILURE, V126_FAILURE_SHA256),
        (V124_RESULT, V124_RESULT_SHA256),
        (V125_INVALIDATION, V125_INVALIDATION_SHA256),
        (V123_RESULT_RECEIPT, V123_RESULT_RECEIPT_SHA256),
        (V113_RESULT_RECEIPT, V113_RESULT_RECEIPT_SHA256),
        (V113_SOURCE_RESULT, V113_SOURCE_RESULT_SHA256),
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
            raise RuntimeError(f"frozen V131 input is missing or changed: {path}")
    v130 = json.loads(V130_RESULT.read_text(encoding="utf-8"))
    if (
        v130.get("result_hash") != V130_RESULT_HASH
        or v130.get("status") != "training_fail"
        or v130.get("joint_training_gate_pass") is not False
        or v130.get("decision", {}).get(
            "authorize_generation_of_confirmation_inputs_now"
        )
        is not False
    ):
        raise RuntimeError("frozen V130 parent result identity changed")
    v130_blind = json.loads(V130_BLIND_AUDIT.read_text(encoding="utf-8"))
    if (
        v130_blind.get("audit_hash") != V130_BLIND_AUDIT_HASH
        or v130_blind.get("performance_summaries_parsed") != 0
        or v130_blind.get("performance_results_consulted") is not False
    ):
        raise RuntimeError("frozen V130 parent blind-audit identity changed")
    v129 = json.loads(V129_RESULT.read_text(encoding="utf-8"))
    if (
        v129.get("result_hash") != V129_RESULT_HASH
        or v129.get("status") != "training_fail"
        or v129.get("joint_training_gate_pass") is not False
        or v129.get("decision", {}).get(
            "authorize_generation_of_confirmation_inputs_now"
        )
        is not False
    ):
        raise RuntimeError("frozen V129 parent result identity changed")
    v129_blind = json.loads(V129_BLIND_AUDIT.read_text(encoding="utf-8"))
    if (
        v129_blind.get("audit_hash") != V129_BLIND_AUDIT_HASH
        or v129_blind.get("performance_summaries_parsed") != 0
        or v129_blind.get("performance_results_consulted") is not False
    ):
        raise RuntimeError("frozen V129 parent blind-audit identity changed")
    v127 = json.loads(V127_RESULT.read_text(encoding="utf-8"))
    if (
        v127.get("result_hash") != V127_RESULT_HASH
        or v127.get("status") != "training_fail"
        or v127.get("joint_training_gate_pass") is not False
        or v127.get("decision", {}).get(
            "authorize_generation_of_confirmation_inputs_now"
        )
        is not False
    ):
        raise RuntimeError("frozen V127 parent result identity changed")
    v126 = json.loads(V126_FAILURE.read_text(encoding="utf-8"))
    if v126.get("receipt_hash") != V126_FAILURE_HASH:
        raise RuntimeError("frozen V126 blind-failure receipt object hash changed")
    if (
        v126.get("scientific_boundary", {}).get("performance_results_consulted")
        is not False
    ):
        raise RuntimeError("V126 parent receipt crossed the result-blind boundary")
    v124 = json.loads(V124_RESULT.read_text(encoding="utf-8"))
    if v124.get("result_hash") != V124_RESULT_HASH:
        raise RuntimeError("frozen V124 result object hash changed")
    v123 = json.loads(V123_RESULT_RECEIPT.read_text(encoding="utf-8"))
    if v123.get("receipt_hash") != V123_RESULT_RECEIPT_HASH:
        raise RuntimeError("frozen V123 receipt object hash changed")
    v113 = json.loads(V113_RESULT_RECEIPT.read_text(encoding="utf-8"))
    if v113.get("receipt_hash") != V113_RESULT_RECEIPT_HASH:
        raise RuntimeError("frozen V113 receipt object hash changed")


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
            "v131_training_plan_sha256": PLAN_SHA256,
            "v131_training_only": True,
            "v131_binary_source_commit": BINARY_SOURCE_COMMIT,
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
            raise RuntimeError("V131 arm rewrite lacks frozen model binding")
        arm_id, role, profile, expected = arm
        candidate = role == "candidate"
        marker.update(
            {
                "v131_arm_id": arm_id,
                "v131_experiment_id": "E3",
                "v131_role": role,
                "v131_profile": profile,
                "v131_shock_threshold_numerator": 3 if candidate else None,
                "v131_shock_threshold_denominator": 2 if candidate else None,
                "v131_shock_activation_horizon_frames": 50 if candidate else None,
                "v131_critical_service_ratio_numerator": 9 if candidate else None,
                "v131_critical_service_ratio_denominator": 10 if candidate else None,
                "v131_service_proxy_work_source": (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if candidate
                    else "not_applicable"
                ),
                "v131_critical_frontier_substitution": candidate,
                "v131_completion_proximal_depth1_substitution_scope": candidate,
                "v131_completion_proximal_definition": (
                    "terminal_function_or_nonterminal_function_whose_immutable_DAG_children_are_all_terminal"
                    if candidate
                    else "not_applicable"
                ),
                "v131_maximum_remaining_child_depth": 1 if candidate else None,
                "v131_deeper_player_exact_anchor": candidate,
                "v131_complete_componentwise_service_pareto": candidate,
                "v131_componentwise_service_scope": (
                    "all_current_critical_frontier_players"
                    if candidate
                    else "not_applicable"
                ),
                "v131_componentwise_service_comparison": (
                    "every_current_critical_player_alternative_less_than_or_equal_to_anchor"
                    if candidate
                    else "not_applicable"
                ),
                "v131_complete_terminal_child_hpa_anchor_running_first_top2_path_service_pareto": candidate,
                "v131_terminal_child_hpa_anchor_running_first_top2_path_pairing": (
                    "same_first_two_running_first_deterministic_anchor_ranked_child_container_nodes"
                    if candidate
                    else "not_applicable"
                ),
                "v131_terminal_child_hpa_anchor_running_first_top2_path_aggregation": (
                    "complete_per_child_pareto_on_up_to_two_running_first_deterministic_anchor_ranked_witnesses"
                    if candidate
                    else "not_applicable"
                ),
                "v131_terminal_child_hpa_anchor_running_first_top2_path_scope": (
                    "every_immutable_immediate_child_of_each_actually_changed_completion_proximal_player"
                    if candidate
                    else "not_applicable"
                ),
                "v131_terminal_child_hpa_anchor_running_first_top2_path_proxy": (
                    "parent_output_transfer_plus_full_cold_start_if_starting_plus_child_node_admitted_cpu_service"
                    if candidate
                    else "not_applicable"
                ),
                "v131_terminal_child_hpa_container_node_scope": (
                    "all_current_HPA_owned_child_containers_running_or_starting"
                    if candidate
                    else "not_applicable"
                ),
                "v131_terminal_child_hpa_anchor_running_first_top2_path_comparison": (
                    "every_terminal_child_alternative_path_to_each_of_the_first_two_running_first_deterministic_anchor_ranked_hpa_containers_less_than_or_equal_to_anchor"
                    if candidate
                    else "not_applicable"
                ),
                "v131_terminal_child_hpa_anchor_running_first_top2_selection": (
                    "running_before_starting_then_ascending_finite_anchor_path_then_lowest_node_id_take_first_two"
                    if candidate
                    else "not_applicable"
                ),
                "v131_terminal_child_hpa_anchor_running_first_top2_path_input_fail_closed": candidate,
                "v131_expected_run_count": expected,
                "v131_scenario_or_burst_label_used_by_policy": False,
                "v131_completion_or_performance_fields_used_by_policy": False,
                "v131_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v131_training_plan_sha256": PLAN_SHA256,
                "v131_training_only": True,
                "v131_training_seed_metrics_previously_revealed": False,
                "v131_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v131_confirmation_seeds_opened": False,
                "v131_other_unopened_seeds_opened": False,
                "v131_formal_E01_E20_reexecution": False,
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
                    "v131_arm_id": arm_id,
                    "v131_arm_role": role,
                    "v131_candidate_profile": profile,
                    "v131_candidate_experiment": "E3",
                    "v131_shock_rate_ratio": "3/2" if candidate else None,
                    "v131_shock_threshold_numerator": 3 if candidate else None,
                    "v131_shock_threshold_denominator": 2 if candidate else None,
                    "v131_arrival_history_baseline_frames": 80 if candidate else None,
                    "v131_arrival_history_recent_frames": 20 if candidate else None,
                    "v131_arrival_min_requests_per_window": 20 if candidate else None,
                    "v131_shock_activation_horizon_frames": 50 if candidate else None,
                    "v131_nonterminal_queue_density_floor": 8.0 if candidate else None,
                    "v131_warm_admissibility": (
                        "preserve_anchor_warmness" if candidate else None
                    ),
                    "v131_load_least_window_certificate_mode": (
                        "disabled" if candidate else "not_applicable"
                    ),
                    "v131_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v131_critical_service_ratio_numerator": 9 if candidate else None,
                    "v131_critical_service_ratio_denominator": 10
                    if candidate
                    else None,
                    "v131_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_service_proxy_work_source": (
                        "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_admitted_work_includes_all_blocked_resident": candidate,
                    "v131_admitted_work_deterministic_f64_sum": candidate,
                    "v131_critical_service_proxy_inputs_finite_fail_closed": candidate,
                    "v131_cpu_memory_individual_noninferiority": candidate,
                    "v131_scalar_faasrank_noninferiority": candidate,
                    "v131_input_locality_component_noninferiority": candidate,
                    "v131_per_child_current_warm_downstream_locality_noninferiority": candidate,
                    "v131_critical_frontier_substitution": candidate,
                    "v131_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_completion_proximal_depth1_substitution_scope": candidate,
                    "v131_completion_proximal_definition": (
                        "terminal_function_or_nonterminal_function_whose_immutable_DAG_children_are_all_terminal"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_maximum_remaining_child_depth": 1 if candidate else None,
                    "v131_completion_proximal_critical_frontier_substitution": candidate,
                    "v131_deeper_player_exact_anchor": candidate,
                    "v131_complete_componentwise_service_pareto": candidate,
                    "v131_componentwise_service_scope": (
                        "all_current_critical_frontier_players"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_componentwise_service_comparison": (
                        "every_current_critical_player_alternative_less_than_or_equal_to_anchor"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_componentwise_service_replay_order": (
                        "frozen_native_player_order_with_independent_assignment_prefixes"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_complete_terminal_child_hpa_anchor_running_first_top2_path_service_pareto": candidate,
                    "v131_terminal_child_hpa_anchor_running_first_top2_path_scope": (
                        "every_immutable_immediate_child_of_each_actually_changed_completion_proximal_player"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_terminal_child_hpa_anchor_running_first_top2_path_proxy": (
                        "parent_output_transfer_plus_full_cold_start_if_starting_plus_child_node_admitted_cpu_service"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_terminal_child_hpa_container_node_scope": (
                        "all_current_HPA_owned_child_containers_running_or_starting"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_terminal_child_hpa_anchor_running_first_top2_path_comparison": (
                        "every_terminal_child_alternative_path_to_each_of_the_first_two_running_first_deterministic_anchor_ranked_hpa_containers_less_than_or_equal_to_anchor"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_terminal_child_hpa_anchor_running_first_top2_path_pairing": (
                        "same_first_two_running_first_deterministic_anchor_ranked_child_container_nodes"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_terminal_child_hpa_anchor_running_first_top2_path_aggregation": (
                        "complete_per_child_pareto_on_up_to_two_running_first_deterministic_anchor_ranked_witnesses"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_terminal_child_hpa_anchor_running_first_top2_selection": (
                        "running_before_starting_then_ascending_finite_anchor_path_then_lowest_node_id_take_first_two"
                        if candidate
                        else "not_applicable"
                    ),
                    "v131_terminal_child_hpa_anchor_running_first_top2_path_input_fail_closed": candidate,
                    "v131_complete_summed_critical_service_proxy_strictly_lower": candidate,
                    "v131_complete_routed_score_nonworse": candidate,
                    "v131_complete_exact_ocs_score_nonworse": candidate,
                    "v131_complete_immutable_baseline_welfare_nonworse": candidate,
                    "v131_outcome_fields_drive_policy": False,
                    "v131_scenario_or_burst_label_used_by_policy": False,
                    "v131_completion_or_performance_fields_used_by_policy": False,
                    "v131_future_arrivals_used_by_policy": False,
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


def prepare_v131(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V131 training root: {root}")
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
        paths["source"], capture_ids, purpose=f"V131 fresh parent tapes {PLAN_SHA256}"
    )
    _write(
        paths["capture"],
        _rewrite(capture, purpose=f"V131 fresh parent tapes {PLAN_SHA256}"),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"], selected, purpose=f"V131 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite(
            template,
            purpose=f"V131 {arm_id} {PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != 9
            or len(manifest["reference_build_dependencies"]) != 9
        ):
            raise RuntimeError(f"V131 {arm_id} must have 9 runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V131 {arm_id} escaped E1356-E1358")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V131 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 18:
        raise RuntimeError("V131 must declare exactly 18 arm-specific references")

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
        "schema_version": "NSE_E3_COMPLETION_PROXIMAL_TERMINAL_CHILD_HPA_ANCHOR_RUNNING_FIRST_TOP2_PATH_PREPARED_V131_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V130_result_path": str(V130_RESULT),
        "V130_result_sha256": V130_RESULT_SHA256,
        "V130_result_hash": V130_RESULT_HASH,
        "V130_result_commit": V130_RESULT_COMMIT,
        "V130_blind_audit_path": str(V130_BLIND_AUDIT),
        "V130_blind_audit_sha256": V130_BLIND_AUDIT_SHA256,
        "V130_blind_audit_hash": V130_BLIND_AUDIT_HASH,
        "V130_blind_audit_commit": V130_BLIND_AUDIT_COMMIT,
        "V130_performance_results_consulted": True,
        "V129_result_path": str(V129_RESULT),
        "V129_result_sha256": V129_RESULT_SHA256,
        "V129_result_hash": V129_RESULT_HASH,
        "V129_result_commit": V129_RESULT_COMMIT,
        "V129_blind_audit_path": str(V129_BLIND_AUDIT),
        "V129_blind_audit_sha256": V129_BLIND_AUDIT_SHA256,
        "V129_blind_audit_hash": V129_BLIND_AUDIT_HASH,
        "V129_blind_audit_commit": V129_BLIND_AUDIT_COMMIT,
        "V129_performance_results_consulted": True,
        "V127_result_path": str(V127_RESULT),
        "V127_result_sha256": V127_RESULT_SHA256,
        "V127_result_hash": V127_RESULT_HASH,
        "V127_result_commit": V127_RESULT_COMMIT,
        "V127_performance_results_consulted": True,
        "V126_blind_failure_path": str(V126_FAILURE),
        "V126_blind_failure_sha256": V126_FAILURE_SHA256,
        "V126_blind_failure_hash": V126_FAILURE_HASH,
        "V126_blind_failure_commit": V126_FAILURE_COMMIT,
        "V126_performance_results_consulted": False,
        "V124_result_path": str(V124_RESULT),
        "V124_result_sha256": V124_RESULT_SHA256,
        "V124_result_hash": V124_RESULT_HASH,
        "V124_result_commit": V124_RESULT_COMMIT,
        "V125_invalidation_path": str(V125_INVALIDATION),
        "V125_invalidation_sha256": V125_INVALIDATION_SHA256,
        "V123_result_receipt_path": str(V123_RESULT_RECEIPT),
        "V123_result_receipt_sha256": V123_RESULT_RECEIPT_SHA256,
        "V123_result_receipt_hash": V123_RESULT_RECEIPT_HASH,
        "V123_result_receipt_commit": V123_RESULT_RECEIPT_COMMIT,
        "V113_result_receipt_path": str(V113_RESULT_RECEIPT),
        "V113_result_receipt_sha256": V113_RESULT_RECEIPT_SHA256,
        "V113_result_receipt_hash": V113_RESULT_RECEIPT_HASH,
        "V113_source_result_path": str(V113_SOURCE_RESULT),
        "V113_source_result_sha256": V113_SOURCE_RESULT_SHA256,
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
                "completion_proximal_depth1_substitution_scope": role == "candidate",
                "completion_proximal_definition": (
                    "terminal_function_or_nonterminal_function_whose_immutable_DAG_children_are_all_terminal"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "maximum_remaining_child_depth": 1 if role == "candidate" else None,
                "deeper_player_exact_anchor": role == "candidate",
                "complete_componentwise_service_pareto": role == "candidate",
                "componentwise_service_scope": (
                    "all_current_critical_frontier_players"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "complete_terminal_child_hpa_anchor_running_first_top2_path_service_pareto": role
                == "candidate",
                "terminal_child_hpa_anchor_running_first_top2_path_pairing": (
                    "same_first_two_running_first_deterministic_anchor_ranked_child_container_nodes"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "terminal_child_hpa_anchor_running_first_top2_path_aggregation": (
                    "complete_per_child_pareto_on_up_to_two_running_first_deterministic_anchor_ranked_witnesses"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "terminal_child_hpa_anchor_running_first_top2_selection": (
                    "running_before_starting_then_ascending_finite_anchor_path_then_lowest_node_id_take_first_two"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "terminal_child_hpa_anchor_running_first_top2_path_scope": (
                    "every_immutable_immediate_child_of_each_actually_changed_completion_proximal_player"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "terminal_child_hpa_container_node_scope": (
                    "all_current_HPA_owned_child_containers_running_or_starting"
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
    prepare_v131()


if __name__ == "__main__":
    main()
