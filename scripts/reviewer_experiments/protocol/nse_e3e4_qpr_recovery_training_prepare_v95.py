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


ROOT = Path("tmp/nse_e3e4_qpr_recovery_training_20260828_v95")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_qpr_recovery_training_plan_v95.json"
)
PLAN_SHA256 = "8d25706e4adda849e06b334eacd73117dd52b49797f1755e47ab8491844e545d"
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
BINARY_PATH = Path("tmp/nse_v94_build_66d4a86/release/serverless_sim.exe")
BINARY_SHA256 = "9b97746f2785daccd086780c1203d0d3f823cb155350e4befa99b278201edf77"
BINARY_SOURCE_COMMIT = "66d4a867ca50fae29a030d0ddd9d88300ec09c61"
PYTHON_PATH = Path("D:/Anaconda3/python.exe")
PYTHON_SHA256 = "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
CARGO_LOCK = Path("serverless_sim/Cargo.lock")
CARGO_LOCK_SHA256 = "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
MODULE_CONF = Path("serverless_sim/module_conf_es.json")
MODULE_CONF_SHA256 = "cc2eaf7f0637f9a7982ff71df661b56a9a9dd7e52f4385b96d25cae48fa216df"
MECHANISM_INPUTS = (
    (
        Path(
            "scripts/reviewer_experiments/protocol/"
            "NSESche_E1_homogeneous_n20_final_v1.json"
        ),
        "102aaa046c0427f25cbffe78d4390deadbb31132bf7bcb68a32c7e47b6b61e53",
    ),
    (
        Path(
            "scripts/reviewer_experiments/protocol/"
            "NSESche_E1_heterogeneous_n20_final_v1.json"
        ),
        "f87f6ec3f2da8146ece3951ddd6ba3f868daa10d5208b63c7cd0d2960d0c2609",
    ),
    (
        Path("scripts/reviewer_experiments/protocol/nse_operational_dev_plan_v58.json"),
        "000844d820e0a2dbda6fca6182d8806454c1b36e7490f14a983bda66c659c723",
    ),
    (
        Path("scripts/reviewer_experiments/protocol/nse_operational_dev_plan_v59.json"),
        "6c6f8ecb09ac2cc8a2c4c1e667143f2c1d5fd46ad69cb48b42cbab2a7390f85d",
    ),
    (
        Path("scripts/reviewer_experiments/protocol/nse_operational_dev_plan_v60.json"),
        "e0dd661bb472e1bfdf8e1ec77e4a438c902584e25d505b2ea3c42d930c911ccc",
    ),
)

SEED_LIST = [f"E{index}" for index in range(726, 736)]
TRAINING_SEED_LIST = ["E726", "E727", "E728"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
CONFIRMATION_SEEDS = ["E729", "E730", "E731"]
CI_SEEDS = [f"E{index}" for index in range(736, 746)]
PORT = "3131"
CANDIDATE_PAIRS = (
    (
        "v95a-hiku-load",
        "srpt_ready_hiku_load_faithful",
        "srpt_ready_load_least_current_demand",
    ),
    (
        "v95b-hiku2-ocs-faasrank-load",
        "srpt_ready_hiku2_ocs_borda",
        "srpt_ready_faasrank_load_least_borda",
    ),
    (
        "v95c-hiku-ocs3-hiku2-ocs",
        "srpt_ready_hiku_ocs3_borda",
        "srpt_ready_hiku2_ocs_borda",
    ),
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


def candidate_path(root: Path, candidate_id: str) -> Path:
    return root / f"manifest.{candidate_id}.unbound.json"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "v95-e3e4-training-config.json",
        "source": root / "manifest.v95-e726-e735-full.unbound.json",
        "capture": root / "manifest.v95-tape-capture.unbound.json",
        "prepared": root / "prepared-manifests-v95.json",
    }


def _assert_frozen_inputs() -> None:
    inputs = (
        (PLAN, PLAN_SHA256),
        (FORMAL_RESULT, FORMAL_RESULT_SHA256),
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256),
        (SLA_PATH, SLA_SHA256),
        (MODEL_PATH, MODEL_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (PYTHON_PATH, PYTHON_SHA256),
        (CARGO_LOCK, CARGO_LOCK_SHA256),
        (MODULE_CONF, MODULE_CONF_SHA256),
        *MECHANISM_INPUTS,
    )
    for path, expected in inputs:
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(f"frozen V95 input is missing or changed: {path}")


def _write_config(path: Path) -> None:
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
    write_json_atomic(path, config)


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
    candidate_id: str | None = None,
    E3_profile: str | None = None,
    E4_profile: str | None = None,
    frozen_model_config: dict | None = None,
) -> dict:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    marker = rewritten["integration_smoke_shard"]
    marker["purpose"] = purpose
    marker["v95_training_plan_sha256"] = PLAN_SHA256
    marker["v95_training_only"] = True
    marker["v95_binary_source_commit"] = BINARY_SOURCE_COMMIT
    marker["selected_development_seeds"] = TRAINING_SEED_LIST
    marker["sealed_confirmation_seeds"] = CONFIRMATION_SEEDS
    marker["formal_results_eligible"] = False
    marker["new_baseline_online_runs"] = 0
    marker["formal_E01_E20_reexecution"] = 0
    if candidate_id is not None:
        if not E3_profile or not E4_profile or frozen_model_config is None:
            raise RuntimeError(
                "candidate rewrite lacks its frozen profile/model binding"
            )
        marker["v95_candidate_id"] = candidate_id
        marker["v95_E3_profile"] = E3_profile
        marker["v95_E4_profile"] = E4_profile

    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata["v95_training_plan_sha256"] = PLAN_SHA256
        metadata["v95_training_only"] = True
        metadata["v95_training_seed_metrics_previously_revealed"] = False
        metadata["v95_binary_source_commit"] = BINARY_SOURCE_COMMIT
        metadata["v95_confirmation_seeds_opened"] = False
        metadata["v95_formal_E01_E20_reexecution"] = False
        if candidate_id is not None:
            profile = E3_profile if run["experiment_id"] == "E3" else E4_profile
            run["variant"] = f"{candidate_id}-{run['experiment_id'].lower()}"
            run["environment"].update(COMMON_CANDIDATE_ENVIRONMENT)
            run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
            run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
                frozen_model_config
            )
            metadata["v95_candidate_id"] = candidate_id
            metadata["v95_candidate_profile"] = profile
            metadata["v95_candidate_experiment"] = run["experiment_id"]
            metadata["v95_faasrank_model_artifact_sha256"] = MODEL_SHA256
            metadata["v95_parent_complete_ready_frontier"] = True
            metadata["v95_srpt_critical_path_player_order"] = True
            # Environment controls alter the initial assignment/state sequence,
            # so bind them into the unbound build declaration immediately.
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


def prepare_v95(root: Path = ROOT) -> dict:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V95 training root: {root}")
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
        purpose=f"V95 fresh balanced-QoS parent tape capture; plan_sha256={PLAN_SHA256}",
    )
    _write(
        paths["capture"],
        _rewrite(
            capture,
            purpose=(
                "V95 fresh balanced-QoS parent tape capture; "
                f"plan_sha256={PLAN_SHA256}"
            ),
        ),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    candidate_ids = _selected_ids(paths["source"], _is_training_candidate, 12)
    candidate_source = derive_integration_smoke_shard(
        paths["source"],
        candidate_ids,
        purpose=f"V95 candidate template; plan_sha256={PLAN_SHA256}",
    )
    candidate_manifests: dict[str, dict] = {}
    all_reference_keys: set[str] = set()
    for candidate_id, E3_profile, E4_profile in CANDIDATE_PAIRS:
        candidate = _rewrite(
            candidate_source,
            purpose=f"V95 {candidate_id} QPR recovery training; plan_sha256={PLAN_SHA256}",
            candidate_id=candidate_id,
            E3_profile=E3_profile,
            E4_profile=E4_profile,
            frozen_model_config=frozen_model_config,
        )
        if (
            len(candidate["runs"]) != 12
            or len(candidate["reference_build_dependencies"]) != 12
        ):
            raise RuntimeError(f"V95 {candidate_id} must have 12 runs and references")
        if {run["seed"] for run in candidate["runs"]} != TRAINING_SEEDS:
            raise RuntimeError(f"V95 {candidate_id} escaped E726-E728")
        keys = {item["key"] for item in candidate["reference_build_dependencies"]}
        if all_reference_keys & keys:
            raise RuntimeError(
                "V95 candidate-specific reference keys unexpectedly overlap"
            )
        all_reference_keys.update(keys)
        path = candidate_path(root, candidate_id)
        _write(path, candidate)
        candidate_manifests[candidate_id] = candidate
    if len(all_reference_keys) != 36:
        raise RuntimeError("V95 must declare exactly 36 candidate-specific references")

    manifests: dict[str, dict] = {}
    manifest_paths = [paths["source"], paths["capture"]] + [
        candidate_path(root, candidate_id) for candidate_id, _, _ in CANDIDATE_PAIRS
    ]
    for path in manifest_paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        manifests[path.name] = {
            "file_sha256": file_hash(path),
            "manifest_hash": document["manifest_hash"],
            "run_count": len(document["runs"]),
            "reference_build_count": len(document["reference_build_dependencies"]),
        }
    receipt = {
        "schema_version": "NSE_E3E4_QPR_RECOVERY_TRAINING_PREPARED_V95_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
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
        "candidate_pairs": [
            {
                "candidate_id": candidate_id,
                "E3_profile": E3_profile,
                "E4_profile": E4_profile,
            }
            for candidate_id, E3_profile, E4_profile in CANDIDATE_PAIRS
        ],
        "base_tape_captures": 3,
        "derived_burst_tapes": 9,
        "candidate_reference_builds": 36,
        "candidate_online_runs": 36,
        "new_baseline_online_runs": 0,
        "formal_E01_E20_reexecution": 0,
        "strictly_serial": True,
        "confirmation_seeds_opened": False,
        "manifests": manifests,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(paths["prepared"], receipt)
    return receipt


def main() -> None:
    prepare_v95()


if __name__ == "__main__":
    main()
