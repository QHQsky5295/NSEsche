from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_prepare_v149 import (
    BINARY_PATH,
    BINARY_SHA256,
    BINARY_SOURCE_COMMIT,
    CARGO_LOCK,
    CARGO_LOCK_SHA256,
    LOADS,
    MODULE_CONF,
    MODULE_CONF_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    SEEDS,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_HASH,
    SOURCE_MANIFEST_SHA256,
    SOURCE_PAIRING,
    SOURCE_PAIRING_SHA256,
    SOURCE_ROOT,
    SOURCE_RUNS,
    SOURCE_RUNS_SHA256,
    SOURCE_SUMMARY,
    SOURCE_SUMMARY_SHA256,
    _assert_frozen_inputs as _assert_v149_frozen_inputs,
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
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e1_homogeneous_cross_scenario_anchor_training_20260831_v151")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_cross_scenario_anchor_training_plan_v151.json"
)
PLAN_SHA256 = "d23132e72213b81ff640f8e4554ec852f182cf1232e043e2e7a9b8ac52ae7430"
V150_RESULT = Path(
    "tmp/nse_e1_homogeneous_legacy_profile_training_20260831_v150/"
    "training-result-v150.json"
)
V150_RESULT_SHA256 = "31094458481ed38b4faae961326f2b4900eb3252e3d07de88d1f3c2d6bc5839b"
V150_RESULT_HASH = "d7016463743d8136757d6f92ee42c4daf44349284eb91b1a809e14b64dba4342"
V94_TRAINING_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_training_result_v94.json"
)
V94_TRAINING_RESULT_SHA256 = (
    "85f4c0ba826d0bf0dc1b43f5933f445c58e42480d7c0a8821dd01c84f19a632c"
)
V94_TRAINING_RESULT_HASH = (
    "6d550c6ddac6613df052983a736844b357eed7db0d5dcfc5905dd2ad21d6daa7"
)
V94_CONFIRMATION_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_terminal_dual_confirmation_result_v94.json"
)
V94_CONFIRMATION_RESULT_SHA256 = (
    "bf423f69d89281ccab6afe2140a63fe33b2670f7d46022aa6ab6d8f4663ccd38"
)
V94_CONFIRMATION_RESULT_HASH = (
    "cba45bd87f85094a35d55fdb8cdce455a3b29480141fa8076f6f4111fb48fd38"
)
V97_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_low_density_load_pareto_training_result_v97.json"
)
V97_RESULT_SHA256 = "316492c93a151e256a471cd0e014636b8cf5fd38051e926a9b718e3abb0db8ab"
V97_RESULT_HASH = "d9d6049bce7f5c5e97af6f6f02820dced09712821120a9ec0f78f6882434d640"

ARM_ID = "v151-e1-homogeneous-cross-scenario-anchors"
PROFILES = {
    "low": "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_srpt_ready_load_least_guard64_dual_window_safe_pareto",
    "middle": "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_srpt_ready_dual_window_safe_pareto",
    "high": "faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto",
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
RUN_ORDER_SEED = "NSE-V151-E1-HOMOGENEOUS-CROSS-SCENARIO-ANCHOR-E01-E20"
PORT = "3202"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-manifest-v151.json",
        "schedule": root / "frozen-run-order-v151.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "pairing": root / "pairing-audit-v151.json",
    }


def _assert_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or file_hash(path) != expected_sha256:
        raise RuntimeError(f"{label} is missing or changed: {path}")


def _assert_frozen_inputs() -> dict[str, Any]:
    source = _assert_v149_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V151 plan"),
        (V150_RESULT, V150_RESULT_SHA256, "V150 complete-block result"),
        (
            V94_TRAINING_RESULT,
            V94_TRAINING_RESULT_SHA256,
            "V94 training result",
        ),
        (
            V94_CONFIRMATION_RESULT,
            V94_CONFIRMATION_RESULT_SHA256,
            "V94 confirmation result",
        ),
        (V97_RESULT, V97_RESULT_SHA256, "V97 low-density training result"),
    ):
        _assert_file(path, sha256, label)
    for path, expected_hash in (
        (V150_RESULT, V150_RESULT_HASH),
        (V94_TRAINING_RESULT, V94_TRAINING_RESULT_HASH),
        (V94_CONFIRMATION_RESULT, V94_CONFIRMATION_RESULT_HASH),
    ):
        result = read_json(path)
        payload = dict(result)
        claimed = payload.pop("result_hash", None)
        if claimed != expected_hash or object_hash(payload) != claimed:
            raise RuntimeError(f"frozen result boundary changed: {path}")
    v150 = read_json(V150_RESULT)
    if not (
        v150.get("all_nine_training_gates_pass") is False
        and v150.get("confirmation_inputs_generated") is False
        and v150.get("valid_seed_deletion_replacement_relabeling_or_selective_rerun")
        is False
        and v150.get("candidate_run_count") == 60
    ):
        raise RuntimeError("V150 complete-block retirement boundary changed")
    v97 = read_json(V97_RESULT)
    if v97.get("result_hash") != V97_RESULT_HASH:
        raise RuntimeError("V97 result boundary changed")
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str | None = None
) -> dict[str, Any]:
    if protocol_source_commit is None:
        protocol_source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V151 protocol source commit is invalid")
    source_ids = [
        run["run_id"] for run in source["runs"] if run.get("method") == "sche_nash"
    ]
    if len(source_ids) != 60:
        raise RuntimeError("frozen E1 source no longer has exactly 60 NSESche runs")
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        source_ids,
        purpose=(
            "V151 adaptive in-sample E1 homogeneous cross-scenario-anchor "
            "training only; never a formal result or paper superiority claim"
        ),
    )
    rewritten["created_at"] = utc_now()
    rewritten["execution"]["command_template"] = [
        "{python}",
        "-m",
        "scripts.reviewer_experiments.protocol.serverless_adapter",
        "--run-config",
        "{run_config}",
        "--simulator-exe",
        str(BINARY_PATH.resolve()),
    ]
    rewritten["all_references_bound"] = False
    rewritten.pop("reference_catalog_hash", None)
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": (
                "V151 adaptive in-sample E1 homogeneous cross-scenario-anchor "
                "training only; never a formal result or paper superiority claim"
            ),
            "v151_role": "adaptive_training_candidate",
            "v151_plan_sha256": PLAN_SHA256,
            "v151_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v151_protocol_source_commit": protocol_source_commit,
            "v151_binary_sha256": BINARY_SHA256,
            "v151_arm_id": ARM_ID,
            "v151_profile_map": PROFILES,
            "v151_common_environment": COMMON_ENVIRONMENT,
            "v151_expected_run_count": 60,
            "v151_expected_reference_build_count": 60,
            "v151_reused_frozen_baseline_runs": 540,
            "v151_baseline_rerun_count": 0,
            "v151_performance_results_consulted_for_design": True,
            "v151_candidate_performance_summaries_parsed": 0,
            "v151_confirmation_inputs_generated": False,
            "strictly_serial": True,
            "run_order_seed": RUN_ORDER_SEED,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        load = run["workload"]["request_freq"]
        profile = PROFILES[load]
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"].update(COMMON_ENVIRONMENT)
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
        run["metadata"] = {
            "v151_training_only": True,
            "v151_role": "adaptive_training_candidate",
            "v151_plan_sha256": PLAN_SHA256,
            "v151_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v151_protocol_source_commit": protocol_source_commit,
            "v151_binary_sha256": BINARY_SHA256,
            "v151_arm_id": ARM_ID,
            "v151_profile": profile,
            "v151_profile_selected_from": (
                "V97_E4_low_density_training"
                if load == "low"
                else "V94_E4_independent_training_and_confirmation"
                if load == "middle"
                else "V94_E3_independent_training_and_confirmation"
            ),
            "v151_source_e1_run_id": source_run_id,
            "v151_source_e1_run_spec_hash": source_run_spec_hash,
            "v151_direct_initialization": True,
            "v151_unrestricted_initialization": True,
            "v151_candidate_performance_summaries_parsed_before_run": 0,
            "v151_confirmation_inputs_generated": False,
        }
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
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


def _validate_product(manifest: dict[str, Any]) -> None:
    expected = {(load, seed) for load in LOADS for seed in SEEDS}
    actual = {
        (run["workload"]["request_freq"], run["seed"]) for run in manifest["runs"]
    }
    if len(manifest["runs"]) != 60 or actual != expected:
        raise RuntimeError("V151 load/seed product changed")
    if {run["method"] for run in manifest["runs"]} != {"sche_nash"}:
        raise RuntimeError("V151 method product changed")
    if len(manifest["reference_build_dependencies"]) != 60:
        raise RuntimeError("V151 reference product changed")
    if manifest.get("all_references_bound") is not False:
        raise RuntimeError("V151 unbound manifest claims bound references")
    for run in manifest["runs"]:
        load = run["workload"]["request_freq"]
        expected_environment = {
            **COMMON_ENVIRONMENT,
            "NASH_OPERATIONAL_EXPERT_PROXY": PROFILES[load],
        }
        if (
            run["experiment_id"] != "E1"
            or run["cluster"] != {"node_count": 20, "topology": "homogeneous"}
            or run["workload"]["topology"] != "homogeneous"
            or any(
                run["environment"].get(key) != value
                for key, value in expected_environment.items()
            )
            or run.get("metadata", {}).get("v151_profile") != PROFILES[load]
            or run["reference_dependency"].get("build_required") is not True
        ):
            raise RuntimeError(f"V151 run contract changed: {run.get('run_id')}")


def _frozen_schedule(manifest: dict[str, Any]) -> dict[str, Any]:
    cells = [
        {
            "load": run["workload"]["request_freq"],
            "seed": run["seed"],
            "profile": PROFILES[run["workload"]["request_freq"]],
            "source_unbound_run_id": run["run_id"],
        }
        for run in manifest["runs"]
    ]
    random.Random(RUN_ORDER_SEED).shuffle(cells)
    schedule = [
        {"ordinal": index, "manifest_id": ARM_ID, **cell}
        for index, cell in enumerate(cells, start=1)
    ]
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CROSS_SCENARIO_ANCHOR_RUN_ORDER_V151_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "run_order_seed": RUN_ORDER_SEED,
        "randomization_unit": "sixty_load_by_seed_candidate_cells",
        "schedule": schedule,
    }
    document["schedule_hash"] = object_hash(document)
    return document


def prepare_v151(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V151 training root: {root}")
    root.mkdir(parents=True)
    output = paths(root)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest)
    write_json_atomic(output["manifest"], manifest)
    schedule = _frozen_schedule(manifest)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CROSS_SCENARIO_ANCHOR_PREPARED_V151_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "performance_results_consulted_for_design": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "frozen_design_evidence": {
            "v150_result_sha256": V150_RESULT_SHA256,
            "v150_result_hash": V150_RESULT_HASH,
            "v94_training_result_sha256": V94_TRAINING_RESULT_SHA256,
            "v94_training_result_hash": V94_TRAINING_RESULT_HASH,
            "v94_confirmation_result_sha256": V94_CONFIRMATION_RESULT_SHA256,
            "v94_confirmation_result_hash": V94_CONFIRMATION_RESULT_HASH,
            "v97_result_sha256": V97_RESULT_SHA256,
            "v97_result_hash": V97_RESULT_HASH,
        },
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_path": str(PYTHON_PATH.resolve()),
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_path": str(CARGO_LOCK.resolve()),
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_path": str(MODULE_CONF.resolve()),
        "module_conf_sha256": MODULE_CONF_SHA256,
        "source_manifest_path": str(SOURCE_MANIFEST),
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_runs_file_sha256": SOURCE_RUNS_SHA256,
        "source_summary_file_sha256": SOURCE_SUMMARY_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "reused_frozen_baseline_runs": 540,
        "baseline_reruns": 0,
        "candidate_online_runs": 60,
        "candidate_reference_builds": 60,
        "confirmation_inputs_generated": False,
        "strictly_serial": True,
        "run_order_seed": RUN_ORDER_SEED,
        "frozen_schedule_path": str(output["schedule"]),
        "frozen_schedule_file_sha256": file_hash(output["schedule"]),
        "frozen_schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "arm_id": ARM_ID,
        "profile_map": PROFILES,
        "common_environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def main() -> None:
    receipt = prepare_v151()
    print(json.dumps({"receipt_hash": receipt["receipt_hash"], "runs": 60}))


if __name__ == "__main__":
    main()
