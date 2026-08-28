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


ROOT = Path("tmp/nse_e3_causal_horizon_training_20260829_v109")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_causal_horizon_training_plan_v109.json"
)
PLAN_SHA256 = "6466f88075261b147bfa79401c48c4cb51f28d9f7d4e05744a139ffe95e959d2"
V108_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_critical_service_time_training_result_v108.json"
)
V108_RESULT_RECEIPT_SHA256 = (
    "b75563b5e59c1878e14056d3691cb406b21536417f79dcdac61d99db1cbfca44"
)
V108_SOURCE_RESULT = Path(
    "tmp/nse_e3_critical_service_time_training_20260829_v108/"
    "training-result-v108.json"
)
V108_SOURCE_RESULT_SHA256 = (
    "e68c3826c837f572d7f63213ed974d823e9db20f0141faf6a6a7d369bf2ff7b7"
)
FORMAL_RESULT = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_formal_n20_result_v94.json"
)
FORMAL_RESULT_SHA256 = (
    "4b39fb20cf07e5e0850b5f950a36f4461122a2d9940c1c3667568055555e8547"
)
DEFAULT_CONFIG = Path("scripts/reviewer_experiments/protocol/default_protocol.json")
DEFAULT_CONFIG_SHA256 = (
    "121d217b4c404c5fbb882c34ed684824b8bd1299d19e92e0f0d82fe8a53b85a2"
)
SLA_PATH = Path(
    "C:/Users/99349/Desktop/serverless_sim_game/tmp/"
    "formal_e3_e4_reviewer_v3_20260817/frozen-sla.json"
)
SLA_SHA256 = "4a8392bb4f087106716e7d9a801a1dab4377804eef5c3e66df06a5403b100496"
MODEL_PATH = Path(
    "C:/Users/99349/Desktop/serverless_sim_game/tmp/"
    "formal_e1_atomic_hpa_reviewer_v3_20260813/faasrank.frozen.json"
)
MODEL_SHA256 = "7e9e1e63c88a83762fe10af66f6a0fcc6fb457c8087cda848a7c17ddf9f56463"
BINARY_PATH = Path("tmp/nse_v109_build_a9ceba2/release/serverless_sim.exe")
BINARY_SHA256 = "2321acfa65ccc9be8993ea2d1a9edd2b68b981c6a5ab8eaa9e63ded4e53a4e2f"
BINARY_SOURCE_COMMIT = "a9ceba2d536c3b8a5ba297052274acc97fdcc7f6"
PYTHON_PATH = Path("D:/Anaconda3/python.exe")
PYTHON_SHA256 = "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
CARGO_LOCK = Path("serverless_sim/Cargo.lock")
CARGO_LOCK_SHA256 = "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
MODULE_CONF = Path("serverless_sim/module_conf_es.json")
MODULE_CONF_SHA256 = "cc2eaf7f0637f9a7982ff71df661b56a9a9dd7e52f4385b96d25cae48fa216df"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(896, 906)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(906, 916)]
TRAINING_SEED_LIST = ["E896", "E897", "E898"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(1066, 1086)]
PREVIOUS_CONFIRMATION_SEEDS = [f"E{index}" for index in range(926, 1066)]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
    *[f"E{index}" for index in range(899, 926)],
]
PORT = "3142"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_CAUSAL_ARRIVAL_SHOCK15_HORIZON25_CRITICAL_SERVICE10_INITIALIZER_ONLY = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon25_critical_service10_initializer_only_"
    "guard64_dual_window_safe_pareto"
)
E3_CAUSAL_ARRIVAL_SHOCK15_HORIZON50_CRITICAL_SERVICE10_INITIALIZER_ONLY = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "causal_arrival_shock15_horizon50_critical_service10_initializer_only_"
    "guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v109-e3-anchor", "E3", "anchor", E3_ANCHOR, None, 9),
    (
        "v109-e3-causal-shock15-horizon25-critical-service10-initializer-only",
        "E3",
        "candidate",
        E3_CAUSAL_ARRIVAL_SHOCK15_HORIZON25_CRITICAL_SERVICE10_INITIALIZER_ONLY,
        "3/2",
        9,
    ),
    (
        "v109-e3-causal-shock15-horizon50-critical-service10-initializer-only",
        "E3",
        "candidate",
        E3_CAUSAL_ARRIVAL_SHOCK15_HORIZON50_CRITICAL_SERVICE10_INITIALIZER_ONLY,
        "3/2",
        9,
    ),
)
SHOCK_THRESHOLDS = {"3/2": (3, 2)}
CRITICAL_SERVICE_RATIOS = {
    "v109-e3-causal-shock15-horizon25-critical-service10-initializer-only": (9, 10),
    "v109-e3-causal-shock15-horizon50-critical-service10-initializer-only": (9, 10),
}
ACTIVATION_HORIZONS = {
    "v109-e3-causal-shock15-horizon25-critical-service10-initializer-only": 25,
    "v109-e3-causal-shock15-horizon50-critical-service10-initializer-only": 50,
}

COMMON_ENVIRONMENT = {
    "NASH_OPERATIONAL_DIRECT_INITIALIZATION": "1",
    "NASH_OPERATIONAL_INDIFFERENCE_EPSILON": "15.0",
    "NASH_OPERATIONAL_SWITCH_THRESHOLD": "0.0",
    "NASH_OPERATIONAL_ADAPTIVE_PROXY": "0",
    "NASH_OPERATIONAL_STRUCTURAL_PROXY": "0",
    "NASH_OPERATIONAL_HYBRID_PROXY": "1",
    "NASH_OPERATIONAL_BOUNDED_PROXY": "0",
    "NASH_OPERATIONAL_QUEUE_WEIGHT": "0.20",
    "NASH_OPERATIONAL_LOW_DENSITY_QUEUE_WEIGHT": "0.0",
    "NASH_OPERATIONAL_LOW_DENSITY_QUEUE_THRESHOLD": "0.0",
    "NASH_OPERATIONAL_COLD_START_WEIGHT": "0.55",
    "NASH_OPERATIONAL_PROJECTED_LOAD_WEIGHT": "1.0",
    "NASH_OPERATIONAL_RESOURCE_WEIGHT": "0.15",
    "NASH_OPERATIONAL_PARENT_LOCALITY_WEIGHT": "0.0",
    "NASH_OPERATIONAL_SAME_FUNCTION_WEIGHT": "0.10",
    "NASH_OPERATIONAL_FUNCTION_LOAD_WEIGHT": "0.0",
    "NASH_OPERATIONAL_FUNCTION_PROJECTED_LOAD_WEIGHT": "1.0",
    "NASH_OPERATIONAL_UNRESTRICTED_INITIALIZATION": "1",
}


def arm_path(root: Path, arm_id: str) -> Path:
    return root / f"manifest.{arm_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v109-e3-training-config.json",
        "source": root / "manifest.v109-e896-e905-full.unbound.json",
        "capture": root / "manifest.v109-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v109.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V108_RESULT_RECEIPT, V108_RESULT_RECEIPT_SHA256),
        (V108_SOURCE_RESULT, V108_SOURCE_RESULT_SHA256),
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
            raise RuntimeError(f"frozen V109 input is missing or changed: {path}")


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
    arm: tuple[str, str, str, str, str | None, int] | None = None,
    frozen_model_config: dict | None = None,
) -> dict:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": purpose,
            "v109_training_plan_sha256": PLAN_SHA256,
            "v109_training_only": True,
            "v109_binary_source_commit": BINARY_SOURCE_COMMIT,
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
            raise RuntimeError("arm rewrite lacks its frozen model binding")
        (
            arm_id,
            experiment_id,
            role,
            profile,
            shock_rate_ratio,
            expected,
        ) = arm
        shock_threshold = SHOCK_THRESHOLDS.get(shock_rate_ratio)
        critical_service_ratio = CRITICAL_SERVICE_RATIOS.get(arm_id)
        activation_horizon = ACTIVATION_HORIZONS.get(arm_id)
        marker.update(
            {
                "v109_arm_id": arm_id,
                "v109_experiment_id": experiment_id,
                "v109_role": role,
                "v109_profile": profile,
                "v109_shock_rate_ratio": shock_rate_ratio,
                "v109_shock_threshold_numerator": (
                    shock_threshold[0] if shock_threshold else None
                ),
                "v109_shock_threshold_denominator": (
                    shock_threshold[1] if shock_threshold else None
                ),
                "v109_arrival_history_baseline_frames": 80
                if role == "candidate"
                else None,
                "v109_arrival_history_recent_frames": 20
                if role == "candidate"
                else None,
                "v109_arrival_min_requests_per_window": 20
                if role == "candidate"
                else None,
                "v109_shock_activation_horizon_frames": activation_horizon,
                "v109_static_upper_density_gate_bypassed_only_while_shock_active": role
                == "candidate",
                "v109_nonterminal_queue_density_floor": (
                    8.0 if role == "candidate" else None
                ),
                "v109_warm_admissibility": (
                    "preserve_anchor_warmness" if role == "candidate" else None
                ),
                "v109_load_least_window_certificate_mode": (
                    "disabled" if role == "candidate" else "not_applicable"
                ),
                "v109_arrival_signal": "first_seen_request_ids_only"
                if role == "candidate"
                else "not_applicable",
                "v109_cpu_memory_individual_noninferiority": role == "candidate",
                "v109_resource_bottleneck_sum_noninferiority": False,
                "v109_resource_inputs_finite_fail_closed": role == "candidate",
                "v109_critical_service_ratio_numerator": (
                    critical_service_ratio[0] if critical_service_ratio else None
                ),
                "v109_critical_service_ratio_denominator": (
                    critical_service_ratio[1] if critical_service_ratio else None
                ),
                "v109_critical_frontier_substitution": role == "candidate",
                "v109_critical_frontier_rank_source": (
                    "immutable_srpt_remaining_critical_path_rank"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "v109_critical_frontier_tie_rule": (
                    "every_exact_tied_current_request_frontier_maximum"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "v109_noncritical_exact_anchor": role == "candidate",
                "v109_critical_service_proxy_inputs_finite_fail_closed": role
                == "candidate",
                "v109_complete_summed_critical_service_proxy_strictly_lower": role
                == "candidate",
                "v109_expected_run_count": expected,
                "v109_scenario_or_burst_label_used_by_policy": False,
                "v109_completion_or_performance_fields_used_by_policy": False,
                "v109_future_arrivals_used_by_policy": False,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v109_training_plan_sha256": PLAN_SHA256,
                "v109_training_only": True,
                "v109_training_seed_metrics_previously_revealed": False,
                "v109_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v109_confirmation_seeds_opened": False,
                "v109_other_unopened_seeds_opened": False,
                "v109_formal_E01_E20_reexecution": False,
            }
        )
        if arm is not None:
            (
                arm_id,
                experiment_id,
                role,
                profile,
                shock_rate_ratio,
                _,
            ) = arm
            shock_threshold = SHOCK_THRESHOLDS.get(shock_rate_ratio)
            critical_service_ratio = CRITICAL_SERVICE_RATIOS.get(arm_id)
            activation_horizon = ACTIVATION_HORIZONS.get(arm_id)
            certificate_mode = "disabled" if role == "candidate" else "not_applicable"
            if run["experiment_id"] != experiment_id:
                raise RuntimeError(f"{arm_id} contains a non-{experiment_id} run")
            run["variant"] = arm_id
            run["environment"].update(COMMON_ENVIRONMENT)
            run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
            run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
                frozen_model_config
            )
            metadata.update(
                {
                    "v109_arm_id": arm_id,
                    "v109_arm_role": role,
                    "v109_candidate_profile": profile,
                    "v109_candidate_experiment": experiment_id,
                    "v109_shock_rate_ratio": shock_rate_ratio,
                    "v109_shock_threshold_numerator": (
                        shock_threshold[0] if shock_threshold else None
                    ),
                    "v109_shock_threshold_denominator": (
                        shock_threshold[1] if shock_threshold else None
                    ),
                    "v109_arrival_history_baseline_frames": 80
                    if role == "candidate"
                    else None,
                    "v109_arrival_history_recent_frames": 20
                    if role == "candidate"
                    else None,
                    "v109_arrival_min_requests_per_window": 20
                    if role == "candidate"
                    else None,
                    "v109_shock_activation_horizon_frames": activation_horizon,
                    "v109_static_upper_density_gate_bypassed_only_while_shock_active": role
                    == "candidate",
                    "v109_nonterminal_queue_density_floor": (
                        8.0 if role == "candidate" else None
                    ),
                    "v109_warm_admissibility": (
                        "preserve_anchor_warmness" if role == "candidate" else None
                    ),
                    "v109_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v109_native_faithful_initializer": True,
                    "v109_dual_window_safe_pareto": True,
                    "v109_causal_arrival_shock_initializer_guard": role == "candidate",
                    "v109_terminal_players_included_without_lower_floor": role
                    == "candidate",
                    "v109_srpt_critical_path_player_order": "srpt_ready" in profile,
                    "v109_substitution_cap": None,
                    "v109_load_least_window_certificate_mode": certificate_mode,
                    "v109_arrival_signal": "first_seen_request_ids_only"
                    if role == "candidate"
                    else "not_applicable",
                    "v109_cpu_memory_individual_noninferiority": role == "candidate",
                    "v109_resource_bottleneck_sum_noninferiority": False,
                    "v109_resource_inputs_finite_fail_closed": role == "candidate",
                    "v109_critical_service_ratio_numerator": (
                        critical_service_ratio[0] if critical_service_ratio else None
                    ),
                    "v109_critical_service_ratio_denominator": (
                        critical_service_ratio[1] if critical_service_ratio else None
                    ),
                    "v109_critical_service_proxy": (
                        "remote_parent_transfer_plus_cold_start_plus_projected_cpu_service"
                        if role == "candidate"
                        else "not_applicable"
                    ),
                    "v109_critical_service_proxy_inputs_finite_fail_closed": role
                    == "candidate",
                    "v109_scalar_faasrank_noninferiority": role == "candidate",
                    "v109_input_locality_component_noninferiority": role == "candidate",
                    "v109_componentwise_faasrank_noninferiority": False,
                    "v109_per_child_current_warm_downstream_locality_noninferiority": role
                    == "candidate",
                    "v109_downstream_locality_aggregate_compensation_allowed": False,
                    "v109_future_child_placement_or_feasibility_used": False,
                    "v109_critical_frontier_substitution": role == "candidate",
                    "v109_critical_frontier_rank_source": (
                        "immutable_srpt_remaining_critical_path_rank"
                        if role == "candidate"
                        else "not_applicable"
                    ),
                    "v109_critical_frontier_tie_rule": (
                        "every_exact_tied_current_request_frontier_maximum"
                        if role == "candidate"
                        else "not_applicable"
                    ),
                    "v109_noncritical_exact_anchor": role == "candidate",
                    "v109_complete_summed_critical_service_proxy_strictly_lower": role
                    == "candidate",
                    "v109_complete_routed_score_nonworse": role == "candidate",
                    "v109_complete_exact_ocs_score_nonworse": role == "candidate",
                    "v109_complete_immutable_baseline_welfare_nonworse": role
                    == "candidate",
                    "v109_load_least_complete_score_used_as_gate": False,
                    "v109_outcome_fields_drive_policy": False,
                    "v109_scenario_or_burst_label_used_by_policy": False,
                    "v109_completion_or_performance_fields_used_by_policy": False,
                    "v109_future_arrivals_used_by_policy": False,
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
    print(
        f"{path.name}: runs={len(manifest['runs'])} "
        f"refs={len(manifest['reference_build_dependencies'])} "
        f"hash={manifest['manifest_hash']}"
    )


def prepare_v109(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V109 training root: {root}")
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
        paths["source"],
        capture_ids,
        purpose=f"V109 fresh balanced-QoS parent tapes; plan_sha256={PLAN_SHA256}",
    )
    _write(
        paths["capture"],
        _rewrite(
            capture,
            purpose=f"V109 fresh balanced-QoS parent tapes; plan_sha256={PLAN_SHA256}",
        ),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _, _, _, expected = arm
        selected = _selected_ids(paths["source"], _is_training_nash, expected)
        template = derive_integration_smoke_shard(
            paths["source"],
            selected,
            purpose=f"V109 {arm_id} causal-horizon training; plan_sha256={PLAN_SHA256}",
        )
        manifest = _rewrite(
            template,
            purpose=f"V109 {arm_id} causal-horizon training; plan_sha256={PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != expected
            or len(manifest["reference_build_dependencies"]) != expected
        ):
            raise RuntimeError(f"V109 {arm_id} must have {expected} runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V109 {arm_id} escaped E896-E898")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V109 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 27:
        raise RuntimeError("V109 must declare exactly 27 arm-specific references")

    manifest_paths = [paths["source"], paths["capture"]] + [
        arm_path(root, arm_id) for arm_id, _, _, _, _, _ in ARMS
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
        "schema_version": "NSE_E3_CAUSAL_HORIZON_PREPARED_V109_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V108_result_receipt_path": str(V108_RESULT_RECEIPT),
        "V108_result_receipt_sha256": V108_RESULT_RECEIPT_SHA256,
        "V108_source_result_path": str(V108_SOURCE_RESULT),
        "V108_source_result_sha256": V108_SOURCE_RESULT_SHA256,
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
                "experiment_id": experiment_id,
                "role": role,
                "profile": profile,
                "shock_rate_ratio": shock_rate_ratio,
                "shock_threshold_numerator": (
                    SHOCK_THRESHOLDS[shock_rate_ratio][0]
                    if shock_rate_ratio is not None
                    else None
                ),
                "shock_threshold_denominator": (
                    SHOCK_THRESHOLDS[shock_rate_ratio][1]
                    if shock_rate_ratio is not None
                    else None
                ),
                "arrival_history_baseline_frames": 80 if role == "candidate" else None,
                "arrival_history_recent_frames": 20 if role == "candidate" else None,
                "arrival_min_requests_per_window": 20 if role == "candidate" else None,
                "shock_activation_horizon_frames": ACTIVATION_HORIZONS.get(arm_id),
                "static_upper_density_gate_bypassed_only_while_shock_active": role
                == "candidate",
                "resource_headroom_safety_mode": (
                    "cpu_and_memory_headroom_each_nonworse"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "resource_inputs_finite_fail_closed": role == "candidate",
                "maximum_candidate_to_anchor_service_proxy_ratio": (
                    f"{CRITICAL_SERVICE_RATIOS[arm_id][0]}/"
                    f"{CRITICAL_SERVICE_RATIOS[arm_id][1]}"
                    if role == "candidate"
                    else None
                ),
                "critical_service_proxy": (
                    "remote_parent_transfer_plus_cold_start_plus_projected_cpu_service"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "nonterminal_queue_density_floor": (
                    8.0 if role == "candidate" else None
                ),
                "warm_admissibility": (
                    "preserve_anchor_warmness" if role == "candidate" else None
                ),
                "load_least_window_certificate_mode": (
                    "disabled" if role == "candidate" else "not_applicable"
                ),
                "critical_frontier_substitution": role == "candidate",
                "critical_frontier_rank_source": (
                    "immutable_srpt_remaining_critical_path_rank"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "critical_frontier_tie_rule": (
                    "every_exact_tied_current_request_frontier_maximum"
                    if role == "candidate"
                    else "not_applicable"
                ),
                "noncritical_exact_anchor": role == "candidate",
                "complete_summed_critical_service_proxy_strictly_lower": role
                == "candidate",
                "load_least_complete_score_used_as_gate": False,
                "run_count": expected,
                "reference_build_count": expected,
            }
            for arm_id, experiment_id, role, profile, shock_rate_ratio, expected in ARMS
        ],
        "base_tape_captures": 3,
        "derived_burst_tapes": 9,
        "arm_reference_builds": 27,
        "arm_online_runs": 27,
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
    prepare_v109()


if __name__ == "__main__":
    main()
