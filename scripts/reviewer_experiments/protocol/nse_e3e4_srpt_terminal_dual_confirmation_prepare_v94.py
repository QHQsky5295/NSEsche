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


ROOT = Path("tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_confirmation_plan_v94.json"
)
PLAN_SHA256 = "ba11cefa2af67a0347f126104922d3e94c501a9dce043965463719405a5cc90d"
TRAINING_DESIGN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_training_design_v94.json"
)
TRAINING_DESIGN_SHA256 = (
    "9e109ad029356d916fcdb1671c02ffd6bb08de0e46c3dfb6ca7d2caf54707371"
)
TRAINING_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_training_result_v94.json"
)
TRAINING_RESULT_SHA256 = (
    "c4d82d46fbd5fa703322bbe4dc58aa744985d8489dad52f58aa54efa47daf2b1"
)
TRAINING_RESULT_HASH = (
    "6d550c6ddac6613df052983a736844b357eed7db0d5dcfc5905dd2ad21d6daa7"
)
V88_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json"
)
V88_PLAN_SHA256 = "7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab"
DEFAULT_CONFIG = Path("scripts/reviewer_experiments/protocol/default_protocol.json")
DEFAULT_CONFIG_SHA256 = (
    "121d217b4c404c5fbb882c34ed684824b8bd1299d19e92e0f0d82fe8a53b85a2"
)
CONFIG = ROOT / "v94-e3e4-confirmation-config.json"
SOURCE = ROOT / "manifest.v94-e723-e732-full.unbound.json"
CAPTURE = ROOT / "manifest.v94-confirmation-tape-capture.unbound.json"
CANDIDATE = ROOT / "manifest.v94-srpt-terminal-dual-confirmation.unbound.json"
PREPARED = ROOT / "prepared-confirmation-manifests-v94.json"
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
SEED_LIST = [f"E{index}" for index in range(723, 733)]
CONFIRMATION_SEED_LIST = ["E723", "E724", "E725"]
CONFIRMATION_SEEDS = set(CONFIRMATION_SEED_LIST)
TRAINING_SEEDS = ["E720", "E721", "E722"]
V93_RESERVED_SEEDS = ["E716", "E717", "E718"]
CI_SEEDS = [f"E{index}" for index in range(733, 743)]
PORT = "3129"
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
        (TRAINING_DESIGN, TRAINING_DESIGN_SHA256),
        (TRAINING_RESULT, TRAINING_RESULT_SHA256),
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
                f"frozen V94 confirmation input is missing or changed: {path}"
            )
    result = json.loads(TRAINING_RESULT.read_text(encoding="utf-8"))
    claimed_hash = result.pop("result_hash", None)
    if claimed_hash != TRAINING_RESULT_HASH or object_hash(result) != claimed_hash:
        raise RuntimeError("V94 training result self-hash is invalid")
    if (
        result.get("status") != "training_pass"
        or result.get("all_four_training_gates_pass") is not True
        or result.get("decision", {}).get("authorize_v94_confirmation_on_E723_E725")
        is not True
    ):
        raise RuntimeError("V94 training result does not authorize confirmation")


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


def _is_confirmation_candidate(run: dict) -> bool:
    return (
        run["experiment_id"] in {"E3", "E4"}
        and run["seed"] in CONFIRMATION_SEEDS
        and run["method"] == "sche_nash"
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced"
        and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
    )


def _selected_source_runs(predicate, expected: int) -> list[dict]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    selected = [copy.deepcopy(run) for run in source["runs"] if predicate(run)]
    if len(selected) != expected:
        raise RuntimeError(f"expected {expected} selected runs, got {len(selected)}")
    return selected


def _rewrite_capture(shard: dict) -> dict:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    marker = rewritten["integration_smoke_shard"]
    marker["purpose"] = (
        "V94 fresh E723-E725 confirmation parent tape capture; "
        f"confirmation_plan_sha256={PLAN_SHA256}"
    )
    marker["v94_confirmation_plan_sha256"] = PLAN_SHA256
    marker["v94_confirmation_capture_only"] = True
    marker["selected_confirmation_seeds"] = CONFIRMATION_SEED_LIST
    marker["sealed_training_seeds"] = TRAINING_SEEDS
    marker["sealed_v93_reserved_seeds"] = V93_RESERVED_SEEDS
    marker["formal_results_eligible"] = False
    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata["v94_confirmation_plan_sha256"] = PLAN_SHA256
        metadata["v94_confirmation_capture_only"] = True
        metadata["v94_confirmation_metrics_previously_revealed"] = False
        metadata["v94_training_rows_excluded"] = True
        metadata["v94_v93_reserved_seeds_opened"] = False
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


def _confirmation_manifest(frozen_model_config: dict) -> dict:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    selected = _selected_source_runs(_is_confirmation_candidate, 12)
    source_by_id = {run["run_id"]: run for run in selected}
    rewritten = copy.deepcopy(source)
    rewritten["created_at"] = utc_now()
    rewritten["formal_results_eligible"] = True
    rewritten.pop("integration_smoke_shard", None)
    rewritten["runs"] = selected
    lineage = []
    for run in rewritten["runs"]:
        source_run = source_by_id[run["run_id"]]
        original_run_id = source_run["run_id"]
        original_run_spec_hash = source_run["run_spec_hash"]
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        profile = E3_PROFILE if run["experiment_id"] == "E3" else E4_PROFILE
        variant = (
            "v94-confirmation-srpt-terminal-ocs-dual"
            if run["experiment_id"] == "E3"
            else "v94-confirmation-srpt-terminal-ocs-idle-warm-dual"
        )
        run["variant"] = variant
        run["environment"].update(COMMON_CANDIDATE_ENVIRONMENT)
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
        run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
            frozen_model_config
        )
        metadata = run.setdefault("metadata", {})
        metadata["v94_confirmation_plan_sha256"] = PLAN_SHA256
        metadata["v94_training_result_sha256"] = TRAINING_RESULT_SHA256
        metadata["v94_confirmation_only"] = True
        metadata["v94_confirmation_metrics_previously_revealed"] = False
        metadata["v94_binary_source_commit"] = BINARY_SOURCE_COMMIT
        metadata["v94_training_rows_excluded"] = True
        metadata["v94_v93_reserved_seeds_opened"] = False
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
        scenario_name = run["workload"].get("burst_name") or "steady"
        lineage.append(
            {
                "source_run_id": original_run_id,
                "source_run_spec_hash": original_run_spec_hash,
                "confirmation_run_id": run["run_id"],
                "confirmation_run_spec_hash": run["run_spec_hash"],
                "experiment_id": run["experiment_id"],
                "scenario_id": f"{run['experiment_id']}.{scenario_name}",
                "seed": run["seed"],
                "profile": profile,
            }
        )
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    rewritten["nse_v94_confirmation_shard"] = {
        "schema_version": "NSE_E3E4_V94_CONFIRMATION_SHARD_V1",
        "purpose": "unchanged-profile E723-E725 independent confirmation",
        "confirmation_plan_path": str(PLAN),
        "confirmation_plan_sha256": PLAN_SHA256,
        "training_result_path": str(TRAINING_RESULT),
        "training_result_sha256": TRAINING_RESULT_SHA256,
        "training_result_hash": TRAINING_RESULT_HASH,
        "source_manifest_path": str(SOURCE),
        "source_manifest_file_sha256": file_hash(SOURCE),
        "source_manifest_hash": source["manifest_hash"],
        "selected_confirmation_seeds": CONFIRMATION_SEED_LIST,
        "sealed_training_seeds": TRAINING_SEEDS,
        "sealed_v93_reserved_seeds": V93_RESERVED_SEEDS,
        "selected_run_count": 12,
        "selected_reference_build_count": 12,
        "new_baseline_online_runs": 0,
        "formal_results_eligible": True,
        "operational_group_closure_eligible_if_joint_gate_passes": True,
        "source_lineage": lineage,
    }
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
        raise RuntimeError(f"refusing to overwrite V94 confirmation root: {ROOT}")
    ROOT.mkdir(parents=True)
    _write_config()
    write_manifest(SOURCE, CONFIG, seed_stage="initial")

    capture_source_runs = _selected_source_runs(
        lambda run: run["experiment_id"] == "E4"
        and run["method"] == "greedy"
        and run["seed"] in CONFIRMATION_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced",
        3,
    )
    capture = derive_integration_smoke_shard(
        SOURCE,
        [run["run_id"] for run in capture_source_runs],
        purpose=(
            "V94 fresh E723-E725 confirmation parent tape capture; "
            f"confirmation_plan_sha256={PLAN_SHA256}"
        ),
    )
    _write(CAPTURE, _rewrite_capture(capture))

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    candidate = _confirmation_manifest(frozen_model_config)
    if {run["seed"] for run in candidate["runs"]} != CONFIRMATION_SEEDS:
        raise RuntimeError("V94 confirmation escaped the E723-E725 boundary")
    if len(candidate["reference_build_dependencies"]) != 12:
        raise RuntimeError("V94 confirmation must have exactly 12 references")
    _write(CANDIDATE, candidate)

    manifests = {}
    for path in (SOURCE, CAPTURE, CANDIDATE):
        document = json.loads(path.read_text(encoding="utf-8"))
        manifests[path.name] = {
            "file_sha256": file_hash(path),
            "manifest_hash": document["manifest_hash"],
            "run_count": len(document["runs"]),
            "reference_build_count": len(document["reference_build_dependencies"]),
            "formal_results_eligible": document.get("formal_results_eligible"),
        }
    receipt = {
        "schema_version": "NSE_E3E4_SRPT_TERMINAL_DUAL_CONFIRMATION_PREPARED_V94_V1",
        "created_at": utc_now(),
        "formal_results_eligible": True,
        "operational_group_closure_eligible_if_joint_gate_passes": True,
        "confirmation_metrics_previously_revealed": False,
        "confirmation_plan_path": str(PLAN),
        "confirmation_plan_sha256": PLAN_SHA256,
        "training_design_path": str(TRAINING_DESIGN),
        "training_design_sha256": TRAINING_DESIGN_SHA256,
        "training_result_path": str(TRAINING_RESULT),
        "training_result_sha256": TRAINING_RESULT_SHA256,
        "training_result_hash": TRAINING_RESULT_HASH,
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
        "confirmation_seeds": CONFIRMATION_SEED_LIST,
        "closed_training_seeds": TRAINING_SEEDS,
        "sealed_v93_reserved_seeds": V93_RESERVED_SEEDS,
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
        "V93_reserved_seeds_opened": False,
        "manifests": manifests,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(PREPARED, receipt)


if __name__ == "__main__":
    main()
