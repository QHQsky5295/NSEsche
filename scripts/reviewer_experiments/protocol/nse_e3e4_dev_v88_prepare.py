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


ROOT = Path("tmp/nse_e3e4_operational_dev_20260827_v88")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json"
)
PLAN_SHA256 = "7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab"
DEFAULT_CONFIG = Path("scripts/reviewer_experiments/protocol/default_protocol.json")
DEFAULT_CONFIG_SHA256 = (
    "121d217b4c404c5fbb882c34ed684824b8bd1299d19e92e0f0d82fe8a53b85a2"
)
CONFIG = ROOT / "v88-e3e4-development-config.json"
SOURCE = ROOT / "manifest.v88-e713-e719-full.unbound.json"
CAPTURE = ROOT / "manifest.v88-tape-capture.unbound.json"
CANDIDATE = ROOT / "manifest.v88-pipeline-terminal-ocs.unbound.json"
PREPARED = ROOT / "prepared-manifests-v88.json"
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
BINARY_PATH = Path(
    "C:/Users/99349/Desktop/serverless_sim_game_nse_dev/"
    "tmp/nse_v88_build_10dcb63/release/serverless_sim.exe"
)
BINARY_SHA256 = "9b248c2a80df02fccf60bb934f2befb7216c262212b42beb1b44226348352235"
PYTHON_PATH = Path("D:/Anaconda3/python.exe")
PYTHON_SHA256 = "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
CARGO_LOCK = Path("serverless_sim/Cargo.lock")
CARGO_LOCK_SHA256 = "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
MODULE_INVENTORY = Path("tmp/module_conf_es.json")
MODULE_INVENTORY_INITIAL_FILE_SHA256 = (
    "09daa7a1802ee591e70f843538371f5d1ff827d15ccab14b2136b56e2eb7c75b"
)
MODULE_INVENTORY_SEMANTIC_HASH = (
    "752e521c15ec7a84d2e11a7f73ffd86241a9ad56638964210c30d2c709662877"
)
V87_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v87.json"
)
V87_PLAN_SHA256 = "adde87a33762f68c019543054f9d40cb41ae3da4baa7aaaba96a708adff9e7e9"
V87_BLIND_AUDIT = Path(
    "tmp/nse_e3e4_operational_dev_20260827_v87/joint-blind-audit-v87.json"
)
V87_BLIND_AUDIT_SHA256 = (
    "ecdc4cbaf29aa79e0b69bbf9894d01af3db9c2d22156f3726cb15fd6e951f728"
)
V87_SELECTION = Path(
    "tmp/nse_e3e4_operational_dev_20260827_v87/selection-result-v87.json"
)
V87_SELECTION_SHA256 = (
    "757cb94eefa90ccc220cc8de4973620642bb7b9ea1904e8b3094d9ac9ec77890"
)
SEED_LIST = [f"E{index}" for index in range(713, 720)]
SELECTED_SEED_LIST = SEED_LIST[:3]
SELECTED_SEEDS = set(SELECTED_SEED_LIST)
CI_SEEDS = [f"E{index}" for index in range(720, 730)]
PORT = "3128"
CANDIDATE_ID = "NSESche-E3E4-pipeline-terminal-OCS-V88"
CANDIDATE_VARIANT = "v88-pipeline-terminal-ocs"
CANDIDATE_PROFILE = (
    "faasrank_native_faithful_pipeline_terminal_ocs_dual_window_safe_pareto"
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
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256),
        (SLA_PATH, SLA_SHA256),
        (MODEL_PATH, MODEL_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (PYTHON_PATH, PYTHON_SHA256),
        (CARGO_LOCK, CARGO_LOCK_SHA256),
        (V87_PLAN, V87_PLAN_SHA256),
        (V87_BLIND_AUDIT, V87_BLIND_AUDIT_SHA256),
        (V87_SELECTION, V87_SELECTION_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(f"frozen V88 input is missing or changed: {path}")
    module_inventory = json.loads(MODULE_INVENTORY.read_text(encoding="utf-8"))
    if object_hash(module_inventory) != MODULE_INVENTORY_SEMANTIC_HASH:
        raise RuntimeError("V88 module inventory semantic set changed")


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
        str(BINARY_PATH),
    ]
    write_json_atomic(CONFIG, config)


def _is_e3e4_nsesche(run: dict) -> bool:
    return (
        run["experiment_id"] in {"E3", "E4"}
        and run["seed"] in SELECTED_SEEDS
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
    marker["v88_plan_sha256"] = PLAN_SHA256
    marker["selected_development_seeds"] = SELECTED_SEED_LIST
    marker["formal_results_eligible"] = False
    marker["frozen_v87_baseline_online_runs"] = 60
    marker["new_baseline_online_runs"] = 0
    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata["v88_plan_sha256"] = PLAN_SHA256
        metadata["v88_formal_results_eligible"] = False
        metadata["v88_resource_scaling_excluded"] = True
        if frozen_model_config is not None:
            run["variant"] = CANDIDATE_VARIANT
            run["environment"].update(COMMON_CANDIDATE_ENVIRONMENT)
            run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = CANDIDATE_PROFILE
            run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
                frozen_model_config
            )
            metadata["v88_candidate_id"] = CANDIDATE_ID
            metadata["v88_candidate_profile"] = CANDIDATE_PROFILE
            metadata["v88_faasrank_model_artifact_sha256"] = MODEL_SHA256
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
    ROOT.mkdir(parents=True, exist_ok=True)
    _assert_frozen_inputs()
    outputs = [CONFIG, SOURCE, CAPTURE, CANDIDATE, PREPARED]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise RuntimeError(f"refusing to overwrite V88 inputs: {existing}")

    _write_config()
    write_manifest(SOURCE, CONFIG, seed_stage="initial")

    capture_ids = _selected_ids(
        lambda run: run["experiment_id"] == "E4"
        and run["method"] == "greedy"
        and run["seed"] in SELECTED_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced",
        3,
    )
    capture = derive_integration_smoke_shard(
        SOURCE,
        capture_ids,
        purpose=f"V88 balanced-QoS parent tape capture; plan_sha256={PLAN_SHA256}",
    )
    _write(
        CAPTURE,
        _rewrite(
            capture,
            purpose=(
                "V88 balanced-QoS parent tape capture; " f"plan_sha256={PLAN_SHA256}"
            ),
        ),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    candidate_ids = _selected_ids(_is_e3e4_nsesche, 12)
    candidate_source = derive_integration_smoke_shard(
        SOURCE,
        candidate_ids,
        purpose=f"V88 candidate template; plan_sha256={PLAN_SHA256}",
    )
    _write(
        CANDIDATE,
        _rewrite(
            candidate_source,
            purpose=f"V88 {CANDIDATE_ID}; plan_sha256={PLAN_SHA256}",
            frozen_model_config=frozen_model_config,
        ),
    )

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
        "schema_version": "NSE_E3E4_V88_PREPARED_MANIFESTS_V1",
        "created_at": utc_now(),
        "paper_sections": ["E3 burst recovery", "E4 balanced-QoS and SLA"],
        "resource_scaling_excluded_and_frozen": True,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "binary_path": str(BINARY_PATH),
        "binary_sha256": BINARY_SHA256,
        "binary_implementation_commit": ("10dcb63bc78a6c5e85b667428007c17b306af7e1"),
        "python_path": str(PYTHON_PATH),
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_path": str(CARGO_LOCK),
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_inventory_path": str(MODULE_INVENTORY),
        "module_inventory_initial_file_sha256": (MODULE_INVENTORY_INITIAL_FILE_SHA256),
        "module_inventory_semantic_hash": MODULE_INVENTORY_SEMANTIC_HASH,
        "sla_artifact_path": str(SLA_PATH),
        "sla_artifact_sha256": SLA_SHA256,
        "faasrank_model_path": str(MODEL_PATH),
        "faasrank_model_sha256": MODEL_SHA256,
        "v87_baseline_plan_path": str(V87_PLAN),
        "v87_baseline_plan_sha256": V87_PLAN_SHA256,
        "v87_baseline_blind_audit_path": str(V87_BLIND_AUDIT),
        "v87_baseline_blind_audit_sha256": V87_BLIND_AUDIT_SHA256,
        "v87_baseline_selection_path": str(V87_SELECTION),
        "v87_baseline_selection_sha256": V87_SELECTION_SHA256,
        "frozen_baseline_online_runs": 60,
        "new_baseline_online_runs": 0,
        "candidate_id": CANDIDATE_ID,
        "candidate_variant": CANDIDATE_VARIANT,
        "candidate_profile": CANDIDATE_PROFILE,
        "selected_seeds": SELECTED_SEED_LIST,
        "reserved_unused_seeds": SEED_LIST[3:],
        "base_tape_captures": 3,
        "derived_burst_tapes": 9,
        "candidate_reference_builds": 12,
        "candidate_online_runs": 12,
        "formal_online_runs": 0,
        "performance_results_consulted": False,
        "scientific_summary_files_opened": 0,
        "manifests": manifests,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(PREPARED, receipt)


if __name__ == "__main__":
    main()
