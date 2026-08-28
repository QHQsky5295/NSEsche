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


ROOT = Path("tmp/nse_e3_warm_preserve_density_band_training_20260828_v101")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_warm_preserve_density_band_training_plan_v101.json"
)
PLAN_SHA256 = "7e96db46880e70d0bffe7e4948b51036fd0381cb35c5c71028d9cf71f4b74d9b"
V100_RESULT_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_load_band_warm_admissibility_training_result_v100.json"
)
V100_RESULT_RECEIPT_SHA256 = (
    "9eb17dd2ce8df28e865ce89142e987ecec63b25d4ebd0052d745622511dfa513"
)
V100_SOURCE_RESULT = Path(
    "tmp/nse_e3_load_band_warm_admissibility_training_20260828_v100/"
    "training-result-v100.json"
)
V100_SOURCE_RESULT_SHA256 = (
    "c8ec53c3f593cb505659aedf2956122284180f31a2765d43a034bcfca2b02cd4"
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
BINARY_PATH = Path("tmp/nse_v101_build_f9b74fa/release/serverless_sim.exe")
BINARY_SHA256 = "5f4560a1d3eea62f13fa5a2945a6682281cb9fbb2471e7939387f2566ce4f7e7"
BINARY_SOURCE_COMMIT = "f9b74fa7d2d9a115316bf3c57201608dc39f8a76"
PYTHON_PATH = Path("D:/Anaconda3/python.exe")
PYTHON_SHA256 = "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
CARGO_LOCK = Path("serverless_sim/Cargo.lock")
CARGO_LOCK_SHA256 = "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
MODULE_CONF = Path("serverless_sim/module_conf_es.json")
MODULE_CONF_SHA256 = "cc2eaf7f0637f9a7982ff71df661b56a9a9dd7e52f4385b96d25cae48fa216df"

SOURCE_INITIAL_SEEDS = [f"E{index}" for index in range(872, 882)]
SOURCE_CI_SEEDS = [f"E{index}" for index in range(882, 892)]
TRAINING_SEED_LIST = ["E872", "E873", "E874"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = [f"E{index}" for index in range(926, 946)]
OTHER_UNOPENED_SEEDS = [
    *[f"E{index}" for index in range(766, 786)],
    *[f"E{index}" for index in range(806, 826)],
    *[f"E{index}" for index in range(846, 866)],
    *[f"E{index}" for index in range(875, 926)],
]
PORT = "3136"

E3_ANCHOR = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E3_BAND8_TO24_WARM_PRESERVE = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "terminal_load_band8_24_warm_preserve_guard64_dual_window_safe_pareto"
)
E3_BAND8_TO32_WARM_PRESERVE = (
    "faasrank_native_faithful_terminal_ocs_srpt_ready_"
    "terminal_load_band8_32_warm_preserve_guard64_dual_window_safe_pareto"
)
ARMS = (
    ("v101-e3-anchor", "E3", "anchor", E3_ANCHOR, None, 9),
    (
        "v101-e3-band8-24-warm-preserve",
        "E3",
        "candidate",
        E3_BAND8_TO24_WARM_PRESERVE,
        24.0,
        9,
    ),
    (
        "v101-e3-band8-32-warm-preserve",
        "E3",
        "candidate",
        E3_BAND8_TO32_WARM_PRESERVE,
        32.0,
        9,
    ),
)

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
        "config": root / "v101-e3-training-config.json",
        "source": root / "manifest.v101-e872-e881-full.unbound.json",
        "capture": root / "manifest.v101-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v101.json",
    }


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V100_RESULT_RECEIPT, V100_RESULT_RECEIPT_SHA256),
        (V100_SOURCE_RESULT, V100_SOURCE_RESULT_SHA256),
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
            raise RuntimeError(f"frozen V101 input is missing or changed: {path}")


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
    arm: tuple[str, str, str, str, float | None, int] | None = None,
    frozen_model_config: dict | None = None,
) -> dict:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": purpose,
            "v101_training_plan_sha256": PLAN_SHA256,
            "v101_training_only": True,
            "v101_binary_source_commit": BINARY_SOURCE_COMMIT,
            "selected_development_seeds": TRAINING_SEED_LIST,
            "sealed_confirmation_seeds": CONFIRMATION_SEEDS,
            "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
            "formal_results_eligible": False,
            "new_baseline_online_runs": 0,
            "formal_E01_E20_reexecution": 0,
        }
    )
    if arm is not None:
        if frozen_model_config is None:
            raise RuntimeError("arm rewrite lacks its frozen model binding")
        arm_id, experiment_id, role, profile, upper_density, expected = arm
        marker.update(
            {
                "v101_arm_id": arm_id,
                "v101_experiment_id": experiment_id,
                "v101_role": role,
                "v101_profile": profile,
                "v101_upper_queue_density_threshold": upper_density,
                "v101_nonterminal_queue_density_floor": (
                    8.0 if role == "candidate" else None
                ),
                "v101_warm_admissibility": (
                    "preserve_anchor_warmness" if role == "candidate" else None
                ),
                "v101_expected_run_count": expected,
            }
        )

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata.update(
            {
                "v101_training_plan_sha256": PLAN_SHA256,
                "v101_training_only": True,
                "v101_training_seed_metrics_previously_revealed": False,
                "v101_binary_source_commit": BINARY_SOURCE_COMMIT,
                "v101_confirmation_seeds_opened": False,
                "v101_other_unopened_seeds_opened": False,
                "v101_formal_E01_E20_reexecution": False,
            }
        )
        if arm is not None:
            arm_id, experiment_id, role, profile, upper_density, _ = arm
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
                    "v101_arm_id": arm_id,
                    "v101_arm_role": role,
                    "v101_candidate_profile": profile,
                    "v101_candidate_experiment": experiment_id,
                    "v101_upper_queue_density_threshold": upper_density,
                    "v101_nonterminal_queue_density_floor": (
                        8.0 if role == "candidate" else None
                    ),
                    "v101_warm_admissibility": (
                        "preserve_anchor_warmness" if role == "candidate" else None
                    ),
                    "v101_faasrank_model_artifact_sha256": MODEL_SHA256,
                    "v101_native_faithful_initializer": True,
                    "v101_dual_window_safe_pareto": True,
                    "v101_density_band_warm_preserve_guard": role == "candidate",
                    "v101_terminal_players_included_without_lower_floor": role
                    == "candidate",
                    "v101_srpt_critical_path_player_order": "srpt_ready" in profile,
                    "v101_substitution_cap": None,
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


def prepare_v101(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V101 training root: {root}")
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
        purpose=f"V101 fresh balanced-QoS parent tapes; plan_sha256={PLAN_SHA256}",
    )
    _write(
        paths["capture"],
        _rewrite(
            capture,
            purpose=f"V101 fresh balanced-QoS parent tapes; plan_sha256={PLAN_SHA256}",
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
            purpose=f"V101 {arm_id} density-band training; plan_sha256={PLAN_SHA256}",
        )
        manifest = _rewrite(
            template,
            purpose=f"V101 {arm_id} density-band training; plan_sha256={PLAN_SHA256}",
            arm=arm,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(manifest["runs"]) != expected
            or len(manifest["reference_build_dependencies"]) != expected
        ):
            raise RuntimeError(f"V101 {arm_id} must have {expected} runs/references")
        if {run["seed"] for run in manifest["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V101 {arm_id} escaped E872-E874")
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError("V101 arm-specific reference keys unexpectedly overlap")
        all_reference_keys.update(keys)
        _write(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 27:
        raise RuntimeError("V101 must declare exactly 27 arm-specific references")

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
        "schema_version": "NSE_E3_WARM_PRESERVE_DENSITY_BAND_PREPARED_V101_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V100_result_receipt_path": str(V100_RESULT_RECEIPT),
        "V100_result_receipt_sha256": V100_RESULT_RECEIPT_SHA256,
        "V100_source_result_path": str(V100_SOURCE_RESULT),
        "V100_source_result_sha256": V100_SOURCE_RESULT_SHA256,
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
        "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
        "arms": [
            {
                "arm_id": arm_id,
                "experiment_id": experiment_id,
                "role": role,
                "profile": profile,
                "upper_queue_density_threshold": upper_density,
                "nonterminal_queue_density_floor": (
                    8.0 if role == "candidate" else None
                ),
                "warm_admissibility": (
                    "preserve_anchor_warmness" if role == "candidate" else None
                ),
                "run_count": expected,
                "reference_build_count": expected,
            }
            for arm_id, experiment_id, role, profile, upper_density, expected in ARMS
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
    prepare_v101()


if __name__ == "__main__":
    main()
