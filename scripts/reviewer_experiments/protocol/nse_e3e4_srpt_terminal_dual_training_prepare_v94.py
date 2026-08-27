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


ROOT = Path("tmp/nse_e3e4_srpt_terminal_dual_training_20260828_v94")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_training_design_v94.json"
)
PLAN_SHA256 = "9e109ad029356d916fcdb1671c02ffd6bb08de0e46c3dfb6ca7d2caf54707371"
V93_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_ready_native_training_result_v93.json"
)
V93_RESULT_SHA256 = "3d3fb549bf6f6a72b1ad03ce9eeb3132601aec716e7e5d69d44b33efff1620e6"
V87_RESULT = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_result_v87.json"
)
V87_RESULT_SHA256 = "4a53fcad06ace6f91915f5ed0a05acf1b10b863db5d5af6cd55788996a463c79"
V88_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json"
)
V88_PLAN_SHA256 = "7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab"
DEFAULT_CONFIG = Path("scripts/reviewer_experiments/protocol/default_protocol.json")
DEFAULT_CONFIG_SHA256 = (
    "121d217b4c404c5fbb882c34ed684824b8bd1299d19e92e0f0d82fe8a53b85a2"
)
CONFIG = ROOT / "v94-e3e4-training-config.json"
SOURCE = ROOT / "manifest.v94-e720-e729-full.unbound.json"
CAPTURE = ROOT / "manifest.v94-tape-capture.unbound.json"
CANDIDATE = ROOT / "manifest.v94-srpt-terminal-dual-training.unbound.json"
PREPARED = ROOT / "prepared-manifests-v94.json"
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
BINARY_PATH = Path("tmp/nse_v94_build_66d4a86/release/serverless_sim.exe")
BINARY_SHA256 = "9b97746f2785daccd086780c1203d0d3f823cb155350e4befa99b278201edf77"
BINARY_SOURCE_COMMIT = "66d4a867ca50fae29a030d0ddd9d88300ec09c61"
PYTHON_PATH = Path("D:/Anaconda3/python.exe")
PYTHON_SHA256 = "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
CARGO_LOCK = Path("serverless_sim/Cargo.lock")
CARGO_LOCK_SHA256 = "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
MODULE_CONF = Path("serverless_sim/module_conf_es.json")
MODULE_CONF_SHA256 = "cc2eaf7f0637f9a7982ff71df661b56a9a9dd7e52f4385b96d25cae48fa216df"
SEED_LIST = [f"E{index}" for index in range(720, 730)]
TRAINING_SEED_LIST = ["E720", "E721", "E722"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = ["E723", "E724", "E725"]
V93_RESERVED_SEEDS = ["E716", "E717", "E718"]
CI_SEEDS = [f"E{index}" for index in range(730, 740)]
PORT = "3128"
E3_PROFILE = "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto"
E4_PROFILE = (
    "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
    "srpt_ready_dual_window_safe_pareto"
)
COMMON_CANDIDATE_ENVIRONMENT = {
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


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V93_RESULT, V93_RESULT_SHA256),
        (V87_RESULT, V87_RESULT_SHA256),
        (V88_PLAN, V88_PLAN_SHA256),
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256),
        (SLA_PATH, SLA_SHA256),
        (MODEL_PATH, MODEL_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (PYTHON_PATH, PYTHON_SHA256),
        (CARGO_LOCK, CARGO_LOCK_SHA256),
        (MODULE_CONF, MODULE_CONF_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(
                f"frozen V94 training input is missing or changed: {path}"
            )


def _write_config() -> None:
    config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    config["seed_policy"] = {
        "initial": SEED_LIST,
        "ci_extension": CI_SEEDS,
        "ci_extension_requires_trigger": True,
        "e7_initial": SEED_LIST[:5],
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
    write_json_atomic(CONFIG, config)


def _is_training_candidate(run: dict) -> bool:
    return (
        run["experiment_id"] in {"E3", "E4"}
        and run["seed"] in TRAINING_SEEDS
        and run["method"] == "sche_nash"
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced"
        and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
    )


def _selected_ids(predicate, expected: int) -> list[str]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    selected = [run["run_id"] for run in source["runs"] if predicate(run)]
    if len(selected) != expected:
        raise RuntimeError(f"expected {expected} selected runs, got {len(selected)}")
    return selected


def _rewrite(
    shard: dict,
    *,
    purpose: str,
    frozen_model_config: dict | None = None,
) -> dict:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    marker = rewritten["integration_smoke_shard"]
    marker["purpose"] = purpose
    marker["v94_training_plan_sha256"] = PLAN_SHA256
    marker["v94_training_only"] = True
    marker["v94_binary_source_commit"] = BINARY_SOURCE_COMMIT
    marker["selected_development_seeds"] = TRAINING_SEED_LIST
    marker["sealed_confirmation_seeds"] = CONFIRMATION_SEEDS
    marker["sealed_v93_reserved_seeds"] = V93_RESERVED_SEEDS
    marker["formal_results_eligible"] = False
    marker["new_baseline_online_runs"] = 0
    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata["v94_training_plan_sha256"] = PLAN_SHA256
        metadata["v94_training_only"] = True
        metadata["v94_training_seed_metrics_previously_revealed"] = False
        metadata["v94_binary_source_commit"] = BINARY_SOURCE_COMMIT
        metadata["v94_resource_scaling_excluded"] = True
        metadata["v94_confirmation_seeds_opened"] = False
        metadata["v94_v93_reserved_seeds_opened"] = False
        if frozen_model_config is not None:
            profile = E3_PROFILE if run["experiment_id"] == "E3" else E4_PROFILE
            variant = (
                "v94-training-srpt-terminal-ocs-dual"
                if run["experiment_id"] == "E3"
                else "v94-training-srpt-terminal-ocs-idle-warm-dual"
            )
            run["variant"] = variant
            run["environment"].update(COMMON_CANDIDATE_ENVIRONMENT)
            run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
            run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
                frozen_model_config
            )
            metadata["v94_candidate_profile"] = profile
            metadata["v94_candidate_variant"] = variant
            metadata["v94_faasrank_model_artifact_sha256"] = MODEL_SHA256
            metadata["v94_parent_complete_ready_frontier"] = True
            metadata["v94_srpt_critical_path_player_order"] = True
            metadata["v94_faithful_faasrank_initializer"] = True
            metadata["v94_terminal_ocs_router"] = True
            metadata["v94_dual_window_safe_pareto_guard"] = True
            metadata["v94_idle_warm_dominance_router"] = run["experiment_id"] == "E4"
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


def main() -> None:
    _assert_frozen_inputs()
    if ROOT.exists():
        raise RuntimeError(f"refusing to overwrite V94 training root: {ROOT}")
    ROOT.mkdir(parents=True)
    _write_config()
    write_manifest(SOURCE, CONFIG, seed_stage="initial")

    capture_ids = _selected_ids(
        lambda run: run["experiment_id"] == "E4"
        and run["method"] == "greedy"
        and run["seed"] in TRAINING_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced",
        3,
    )
    capture = derive_integration_smoke_shard(
        SOURCE,
        capture_ids,
        purpose=f"V94 fresh balanced-QoS parent tape capture; plan_sha256={PLAN_SHA256}",
    )
    _write(
        CAPTURE,
        _rewrite(
            capture,
            purpose=(
                "V94 fresh balanced-QoS parent tape capture; "
                f"plan_sha256={PLAN_SHA256}"
            ),
        ),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    candidate_ids = _selected_ids(_is_training_candidate, 12)
    candidate_source = derive_integration_smoke_shard(
        SOURCE,
        candidate_ids,
        purpose=f"V94 single-candidate training template; plan_sha256={PLAN_SHA256}",
    )
    candidate = _rewrite(
        candidate_source,
        purpose=(
            "V94 SRPT-ready terminal-OCS dual training cohort; "
            f"plan_sha256={PLAN_SHA256}"
        ),
        frozen_model_config=frozen_model_config,
    )
    if {run["seed"] for run in candidate["runs"]} != TRAINING_SEEDS:
        raise RuntimeError("V94 candidate escaped the E720-E722 training boundary")
    if len(candidate["reference_build_dependencies"]) != 12:
        raise RuntimeError("V94 must have exactly 12 candidate-specific references")
    _write(CANDIDATE, candidate)

    manifests = {}
    for path in (SOURCE, CAPTURE, CANDIDATE):
        document = json.loads(path.read_text(encoding="utf-8"))
        manifests[path.name] = {
            "file_sha256": file_hash(path),
            "manifest_hash": document["manifest_hash"],
            "run_count": len(document["runs"]),
            "reference_build_count": len(document["reference_build_dependencies"]),
        }
    receipt = {
        "schema_version": "NSE_E3E4_SRPT_TERMINAL_DUAL_TRAINING_PREPARED_V94_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_metrics_previously_revealed": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V93_result_path": str(V93_RESULT),
        "V93_result_sha256": V93_RESULT_SHA256,
        "V87_result_path": str(V87_RESULT),
        "V87_result_sha256": V87_RESULT_SHA256,
        "frozen_threshold_plan_path": str(V88_PLAN),
        "frozen_threshold_plan_sha256": V88_PLAN_SHA256,
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
        "untouched_v93_reserved_seeds": V93_RESERVED_SEEDS,
        "E3_profile": E3_PROFILE,
        "E4_profile": E4_PROFILE,
        "base_tape_captures": 3,
        "derived_burst_tapes": 9,
        "candidate_reference_builds": 12,
        "candidate_online_runs": 12,
        "new_baseline_online_runs": 0,
        "strictly_serial": True,
        "performance_results_consulted": False,
        "scientific_summary_files_opened_during_preparation": 0,
        "confirmation_seeds_opened": False,
        "V93_reserved_seeds_opened": False,
        "manifests": manifests,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(PREPARED, receipt)


if __name__ == "__main__":
    main()
