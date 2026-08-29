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


ROOT = Path("tmp/nse_e3_componentwise_service_training_20260829_v117")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_componentwise_service_training_plan_v117.json"
)
PLAN_SHA256 = "b67c44f83d04141258f59ef0886a81e72ae83187059ce6e5d776290fab50126f"
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
V116_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_arrival_phase_training_result_v116.json"
)
V116_RESULT_RECEIPT_SHA256 = (
    "30922d8d0404d5c6a270b5edf80b3b65325e35991a1c505a410db7acb9890ed3"
)
V116_SOURCE_RESULT = Path(
    "tmp/nse_e3_arrival_phase_training_20260829_v116/training-result-v116.json"
)
V116_SOURCE_RESULT_SHA256 = (
    "d9a670a5c834f5905f5ad785e8f6d51d10f6f87cc2c8705954a44b335b92602d"
)
BINARY_PATH = Path("tmp/nse_v117_build_3ca87ef/release/serverless_sim.exe")
BINARY_SHA256 = "4c15a3069c02aa9cc9e044d42cf9b1b516d0450aa19cc7e79b59d40fe9b492db"
BINARY_SOURCE_COMMIT = "3ca87efa6662449a47d4e8eb41a4b16104c0d8f5"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(920, 930)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(930, 940)]
TRAINING_SEED_LIST = ["E920", "E921", "E922"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1106, 1126)]
PREVIOUS_CONFIRMATION_SEEDS = [f"E{index}" for index in range(926, 1106)]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
    *[f"E{index}" for index in range(923, 926)],
]
PORT = "3150"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_COMPONENTWISE_SERVICE = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_admitted_work10_"
    "componentwise_service_pareto_initializer_only_guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v117-e3-anchor", "anchor", E3_ANCHOR, 9),
    (
        "v117-e3-causal-shock15-horizon50-admitted-work10-componentwise-service-initializer-only",
        "candidate",
        E3_COMPONENTWISE_SERVICE,
        9,
    ),
)


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v117-e3-training-config.json",
        "source": root / "manifest.v117-e920-e929-full.unbound.json",
        "capture": root / "manifest.v117-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v117.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V113_RESULT_RECEIPT, V113_RESULT_RECEIPT_SHA256),
        (V113_SOURCE_RESULT, V113_SOURCE_RESULT_SHA256),
        (V116_RESULT_RECEIPT, V116_RESULT_RECEIPT_SHA256),
        (V116_SOURCE_RESULT, V116_SOURCE_RESULT_SHA256),
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
            raise RuntimeError(f"frozen V117 input is missing or changed: {path}")


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
            "v117_training_plan_sha256": PLAN_SHA256,
            "v117_training_only": True,
            "v117_binary_source_commit": BINARY_SOURCE_COMMIT,
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
            raise RuntimeError("V117 arm rewrite lacks frozen model binding")
        arm_id, role, profile, expected = arm
        candidate = role == "candidate"
        marker.update(
            {
                "v117_arm_id": arm_id,
                "v117_experiment_id": "E3",
                "v117_role": role,
                "v117_profile": profile,
                "v117_shock_threshold_numerator": 3 if candidate else None,
                "v117_shock_threshold_denominator": 2 if candidate else None,
                "v117_shock_activation_horizon_frames": 50 if candidate else None,
                "v117_critical_service_ratio_numerator": 9 if candidate else None,
                "v117_critical_service_ratio_denominator": 10 if candidate else None,
                "v117_service_proxy_work_source": (
                    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                    if candidate
                    else "not_applicable"
                ),
                "v117_complete_componentwise_service_pareto": candidate,
                "v117_componentwise_service_comparison": (
                    "every_current_critical_frontier_alternative_proxy_lte_anchor_plus_epsilon"
                    if candidate
                    else "not_applicable"
                ),
                "v117_componentwise_service_replay_order": (
                    "native_player_order" if candidate else "not_applicable"
                ),
                "v117_interference_constraints": False,
                "v117_arrival_phase_guard": False,
                "v117_critical_frontier_substitution": candidate,
                "v117_noncritical_exact_anchor": candidate,
                "v117_expected_run_count": expected,
                "v117_scenario_or_burst_label_used_by_policy": False,
                "v117_completion_or_performance_fields_used_by_policy": False,
                "v117_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v117_training_plan_sha256": PLAN_SHA256,
                "v117_training_only": True,
                "v117_training_seed_metrics_previously_revealed": False,
                "v117_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v117_confirmation_seeds_opened": False,
                "v117_other_unopened_seeds_opened": False,
                "v117_formal_E01_E20_reexecution": False,
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
                    "v117_arm_id": arm_id,
                    "v117_arm_role": role,
                    "v117_candidate_profile": profile,
                    "v117_candidate_experiment": "E3",
                    "v117_shock_rate_ratio": "3/2" if candidate else None,
                    "v117_shock_threshold_numerator": 3 if candidate else None,
                    "v117_shock_threshold_denominator": 2 if candidate else None,
                    "v117_arrival_history_baseline_frames": 80 if candidate else None,
                    "v117_arrival_history_recent_frames": 20 if candidate else None,
                    "v117_arrival_min_requests_per_window": 20 if candidate else None,
                    "v117_shock_activation_horizon_frames": 50 if candidate else None,
                    "v117_nonterminal_queue_density_floor": 8.0 if candidate else None,
                    "v117_warm_admissibility": (
                        "preserve_anchor_warmness" if candidate else None
                    ),
                    "v117_load_least_window_certificate_mode": (
                        "disabled" if candidate else "not_applicable"
                    ),
                    "v117_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v117_critical_service_ratio_numerator": 9 if candidate else None,
                    "v117_critical_service_ratio_denominator": 10
                    if candidate
                    else None,
                    "v117_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
                        if candidate
                        else "not_applicable"
                    ),
                    "v117_service_proxy_work_source": (
                        "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                    "v117_admitted_work_includes_all_blocked_resident": candidate,
                    "v117_admitted_work_deterministic_f64_sum": candidate,
                    "v117_complete_componentwise_service_pareto": candidate,
                    "v117_componentwise_service_comparison": (
                        "every_current_critical_frontier_alternative_proxy_lte_anchor_plus_epsilon"
                        if candidate
                        else "not_applicable"
                    ),
                    "v117_componentwise_service_replay_order": (
                        "native_player_order" if candidate else "not_applicable"
                    ),
                    "v117_componentwise_service_inputs_finite_fail_closed": candidate,
                    "v117_componentwise_service_coverage_mismatch_fail_closed": candidate,
                    "v117_interference_constraints": False,
                    "v117_arrival_phase_guard": False,
                    "v117_critical_service_proxy_inputs_finite_fail_closed": candidate,
                    "v117_cpu_memory_individual_noninferiority": candidate,
                    "v117_scalar_faasrank_noninferiority": candidate,
                    "v117_input_locality_component_noninferiority": candidate,
                    "v117_per_child_current_warm_downstream_locality_noninferiority": candidate,
                    "v117_critical_frontier_substitution": candidate,
                    "v117_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if candidate
                        else "not_applicable"
                    ),
                    "v117_noncritical_exact_anchor": candidate,
                    "v117_complete_summed_critical_service_proxy_strictly_lower": candidate,
                    "v117_complete_routed_score_nonworse": candidate,
                    "v117_complete_exact_ocs_score_nonworse": candidate,
                    "v117_complete_immutable_baseline_welfare_nonworse": candidate,
                    "v117_outcome_fields_drive_policy": False,
                    "v117_scenario_or_burst_label_used_by_policy": False,
                    "v117_completion_or_performance_fields_used_by_policy": False,
                    "v117_future_arrivals_used_by_policy": False,
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


def prepare_v117(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V117 training root: {root}")
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
        paths["source"], capture_ids, purpose=f"V117 fresh parent tapes {PLAN_SHA256}"
    )
    _write(
        paths["capture"],
        _rewrite(capture, purpose=f"V117 fresh parent tapes {PLAN_SHA256}"),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"], selected, purpose=f"V117 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite(
            template,
            purpose=f"V117 {arm_id} {PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != 9
            or len(manifest["reference_build_dependencies"]) != 9
        ):
            raise RuntimeError(f"V117 {arm_id} must have 9 runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V117 {arm_id} escaped E920-E922")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V117 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 18:
        raise RuntimeError("V117 must declare exactly 18 arm-specific references")

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
        "schema_version": "NSE_E3_COMPONENTWISE_SERVICE_PREPARED_V117_V1",
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
        "V116_result_receipt_path": str(V116_RESULT_RECEIPT),
        "V116_result_receipt_sha256": V116_RESULT_RECEIPT_SHA256,
        "V116_source_result_path": str(V116_SOURCE_RESULT),
        "V116_source_result_sha256": V116_SOURCE_RESULT_SHA256,
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
    prepare_v117()


if __name__ == "__main__":
    main()
