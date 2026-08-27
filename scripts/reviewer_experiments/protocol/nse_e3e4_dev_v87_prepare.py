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


ROOT = Path("tmp/nse_e3e4_operational_dev_20260827_v87")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v87.json"
)
PLAN_SHA256 = "adde87a33762f68c019543054f9d40cb41ae3da4baa7aaaba96a708adff9e7e9"
DEFAULT_CONFIG = Path("scripts/reviewer_experiments/protocol/default_protocol.json")
DEFAULT_CONFIG_SHA256 = (
    "121d217b4c404c5fbb882c34ed684824b8bd1299d19e92e0f0d82fe8a53b85a2"
)
CONFIG = ROOT / "v87-e3e4-development-config.json"
SOURCE = ROOT / "manifest.v87-e710-e719-full.unbound.json"
CAPTURE = ROOT / "manifest.v87-tape-capture.unbound.json"
BASELINES = ROOT / "manifest.v87-advanced-baselines.unbound.json"
PREPARED = ROOT / "prepared-manifests-v87.json"
MODEL_PATH = Path(
    "C:/Users/99349/Desktop/serverless_sim_game/tmp/"
    "formal_e1_atomic_hpa_reviewer_v3_20260813/faasrank.frozen.json"
)
MODEL_SHA256 = "7e9e1e63c88a83762fe10af66f6a0fcc6fb457c8087cda848a7c17ddf9f56463"
BINARY_PATH = Path(
    "C:/Users/99349/Desktop/serverless_sim_game_nse_dev/"
    "tmp/nse_v86_build_f0fb4b2/release/serverless_sim.exe"
)
BINARY_SHA256 = "b16c93b4a964924957e5595c00d0759514001ef911e814ccf2a05b4450aedac4"
MODULE_INVENTORY = Path(
    "C:/Users/99349/Desktop/serverless_sim_game_nse_dev/tmp/module_conf_es.json"
)
MODULE_INVENTORY_SHA256 = (
    "2cdd2601efc96665572b7a72e125de808e806a802efbd2c723671c74e2287fbd"
)
SEED_LIST = [f"E{index}" for index in range(710, 720)]
SELECTED_SEED_LIST = SEED_LIST[:3]
SELECTED_SEEDS = set(SELECTED_SEED_LIST)
CI_SEEDS = [f"E{index}" for index in range(720, 730)]
PORT = "3128"
BASELINE_METHODS = {
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
}
CANDIDATES = (
    (
        "v87a-completion-pareto",
        "faasrank_native_faithful_completion_pareto",
    ),
    (
        "v87b-terminal-ocs",
        "faasrank_native_faithful_terminal_ocs_window_safe_pareto",
    ),
    (
        "v87c-idle-warm-dominance",
        "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_dual_window_safe_pareto",
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


def candidate_path(candidate_id: str) -> Path:
    return ROOT / f"manifest.{candidate_id}.unbound.json"


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256),
        (MODEL_PATH, MODEL_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (MODULE_INVENTORY, MODULE_INVENTORY_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(f"frozen V87 input is missing or changed: {path}")


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


def _is_e3e4(run: dict) -> bool:
    return (
        run["experiment_id"] in {"E3", "E4"}
        and run["seed"] in SELECTED_SEEDS
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
    candidate_id: str | None = None,
    profile: str | None = None,
    frozen_model_config: dict | None = None,
) -> dict:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    marker = rewritten["integration_smoke_shard"]
    marker["purpose"] = purpose
    marker["v87_plan_sha256"] = PLAN_SHA256
    marker["selected_development_seeds"] = SELECTED_SEED_LIST
    marker["formal_results_eligible"] = False
    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        metadata = run.setdefault("metadata", {})
        metadata["v87_plan_sha256"] = PLAN_SHA256
        metadata["v87_formal_results_eligible"] = False
        if candidate_id is not None:
            if profile is None or frozen_model_config is None:
                raise RuntimeError("candidate rewrite lacks profile/model")
            run["variant"] = candidate_id
            run["environment"].update(COMMON_CANDIDATE_ENVIRONMENT)
            run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
            run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
                frozen_model_config
            )
            metadata["v87_candidate_id"] = candidate_id
            metadata["v87_candidate_profile"] = profile
            metadata["v87_faasrank_model_artifact_sha256"] = MODEL_SHA256
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
    outputs = [CONFIG, SOURCE, CAPTURE, BASELINES, PREPARED] + [
        candidate_path(candidate_id) for candidate_id, _ in CANDIDATES
    ]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise RuntimeError(f"refusing to overwrite V87 inputs: {existing}")

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
        purpose=f"V87 balanced-QoS parent tape capture; plan_sha256={PLAN_SHA256}",
    )
    _write(
        CAPTURE,
        _rewrite(
            capture,
            purpose=f"V87 balanced-QoS parent tape capture; plan_sha256={PLAN_SHA256}",
        ),
    )

    baseline_ids = _selected_ids(
        lambda run: _is_e3e4(run) and run["method"] in BASELINE_METHODS,
        60,
    )
    baselines = derive_integration_smoke_shard(
        SOURCE,
        baseline_ids,
        purpose=f"V87 five advanced E3/E4 development baselines; plan_sha256={PLAN_SHA256}",
    )
    _write(
        BASELINES,
        _rewrite(
            baselines,
            purpose=f"V87 five advanced E3/E4 development baselines; plan_sha256={PLAN_SHA256}",
        ),
    )

    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    candidate_ids = _selected_ids(
        lambda run: _is_e3e4(run) and run["method"] == "sche_nash",
        12,
    )
    candidate_source = derive_integration_smoke_shard(
        SOURCE,
        candidate_ids,
        purpose=f"V87 candidate template; plan_sha256={PLAN_SHA256}",
    )
    for candidate_id, profile in CANDIDATES:
        _write(
            candidate_path(candidate_id),
            _rewrite(
                candidate_source,
                purpose=f"V87 {candidate_id}; plan_sha256={PLAN_SHA256}",
                candidate_id=candidate_id,
                profile=profile,
                frozen_model_config=frozen_model_config,
            ),
        )

    manifests = {}
    for path in [SOURCE, CAPTURE, BASELINES] + [
        candidate_path(candidate_id) for candidate_id, _ in CANDIDATES
    ]:
        document = json.loads(path.read_text(encoding="utf-8"))
        manifests[path.name] = {
            "file_sha256": file_hash(path),
            "manifest_hash": document["manifest_hash"],
            "run_count": len(document["runs"]),
            "reference_build_count": len(document["reference_build_dependencies"]),
        }
    receipt = {
        "schema_version": "NSE_E3E4_V87_PREPARED_MANIFESTS_V1",
        "created_at": utc_now(),
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "binary_path": str(BINARY_PATH),
        "binary_sha256": BINARY_SHA256,
        "module_inventory_path": str(MODULE_INVENTORY),
        "module_inventory_sha256": MODULE_INVENTORY_SHA256,
        "faasrank_model_path": str(MODEL_PATH),
        "faasrank_model_sha256": MODEL_SHA256,
        "selected_seeds": SELECTED_SEED_LIST,
        "reserved_initial_seeds": SEED_LIST[3:],
        "baseline_methods": sorted(BASELINE_METHODS),
        "candidate_order": [candidate_id for candidate_id, _ in CANDIDATES],
        "formal_online_runs": 0,
        "performance_results_consulted": False,
        "manifests": manifests,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(PREPARED, receipt)


if __name__ == "__main__":
    main()
