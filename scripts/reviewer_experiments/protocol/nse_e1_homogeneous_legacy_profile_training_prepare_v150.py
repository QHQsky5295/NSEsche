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


ROOT = Path("tmp/nse_e1_homogeneous_legacy_profile_training_20260831_v150")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_legacy_profile_training_plan_v150.json"
)
PLAN_SHA256 = "6148e7cd8e4b5d368c07c766f7d771eb1031a790b64c86cdff3a4667fd7dd1e8"
V58_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_operational_dev_plan_v58.json"
)
V58_PLAN_SHA256 = "530bf976d776c58996b624ea48a77299db9999f3822dca78bc5779da2ce5712c"
V59_PLAN = Path(
    "scripts/reviewer_experiments/protocol/nse_operational_dev_plan_v59.json"
)
V59_PLAN_SHA256 = "90c9baca83259ef43c98abf56ea038dbeeaa3faa2941759ed8c35221a1b0dbfa"
LEGACY_CATALOG = Path(
    "scripts/reviewer_experiments/protocol/NSESche_E1_homogeneous_n20_final_v1.json"
)
LEGACY_CATALOG_SHA256 = (
    "21f89a7ff21f9fc68d13e15a51d0587bfc55715a6a52931e6c35af54eb6d8fec"
)
V149_RESULT = Path(
    "tmp/nse_e1_homogeneous_causal_native_expert_closure_training_20260831_v149/"
    "training-result-v149.json"
)
V149_RESULT_SHA256 = "2475d88765c130963de86873dfa857b4b1426e2ea1af06793aa240d41491bb59"
V149_RESULT_HASH = "c1a34310c187e9b22c635599469de270c4e8d7bafecd545055ccf0161d9467c4"

ARM_ID = "v150-e1-homogeneous-load-specific-legacy-winners"
PROFILES = {
    "low": "srpt_ready_hiku2_ocs_borda",
    "middle": "srpt_ready_hiku_ocs3_borda",
    "high": "srpt_ready_ocs_current_demand",
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
RUN_ORDER_SEED = "NSE-V150-E1-HOMOGENEOUS-LEGACY-PROFILE-E01-E20"
PORT = "3201"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-manifest-v150.json",
        "schedule": root / "frozen-run-order-v150.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "pairing": root / "pairing-audit-v150.json",
    }


def _assert_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or file_hash(path) != expected_sha256:
        raise RuntimeError(f"{label} is missing or changed: {path}")


def _assert_frozen_inputs() -> dict[str, Any]:
    source = _assert_v149_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V150 plan"),
        (V58_PLAN, V58_PLAN_SHA256, "V58 prior-training plan"),
        (V59_PLAN, V59_PLAN_SHA256, "V59 prior-training plan"),
        (LEGACY_CATALOG, LEGACY_CATALOG_SHA256, "legacy winner catalog"),
        (V149_RESULT, V149_RESULT_SHA256, "V149 retirement result"),
    ):
        _assert_file(path, sha256, label)
    result = read_json(V149_RESULT)
    payload = dict(result)
    claimed = payload.pop("result_hash", None)
    if (
        claimed != V149_RESULT_HASH
        or object_hash(payload) != claimed
        or result.get("all_nine_training_gates_pass") is not False
        or result.get("confirmation_inputs_generated") is not False
    ):
        raise RuntimeError("V149 retirement boundary changed")
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str | None = None
) -> dict[str, Any]:
    if protocol_source_commit is None:
        protocol_source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V150 protocol source commit is invalid")
    source_ids = [
        run["run_id"] for run in source["runs"] if run.get("method") == "sche_nash"
    ]
    if len(source_ids) != 60:
        raise RuntimeError("frozen E1 source no longer has exactly 60 NSESche runs")
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        source_ids,
        purpose=(
            "V150 adaptive in-sample E1 homogeneous load-specific-profile training "
            "only; never a formal result or paper superiority claim"
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
                "V150 adaptive in-sample E1 homogeneous load-specific-profile "
                "training only; never a formal result or paper superiority claim"
            ),
            "v150_role": "adaptive_training_candidate",
            "v150_plan_sha256": PLAN_SHA256,
            "v150_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v150_protocol_source_commit": protocol_source_commit,
            "v150_binary_sha256": BINARY_SHA256,
            "v150_arm_id": ARM_ID,
            "v150_profile_map": PROFILES,
            "v150_common_environment": COMMON_ENVIRONMENT,
            "v150_expected_run_count": 60,
            "v150_expected_reference_build_count": 60,
            "v150_reused_frozen_baseline_runs": 540,
            "v150_baseline_rerun_count": 0,
            "v150_performance_results_consulted_for_design": True,
            "v150_candidate_performance_summaries_parsed": 0,
            "v150_confirmation_inputs_generated": False,
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
            "v150_training_only": True,
            "v150_role": "adaptive_training_candidate",
            "v150_plan_sha256": PLAN_SHA256,
            "v150_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v150_protocol_source_commit": protocol_source_commit,
            "v150_binary_sha256": BINARY_SHA256,
            "v150_arm_id": ARM_ID,
            "v150_profile": profile,
            "v150_profile_selected_from": (
                "V58_E220_E224" if load == "high" else "V59_E230_E234"
            ),
            "v150_source_e1_run_id": source_run_id,
            "v150_source_e1_run_spec_hash": source_run_spec_hash,
            "v150_direct_initialization": True,
            "v150_unrestricted_initialization": True,
            "v150_candidate_performance_summaries_parsed_before_run": 0,
            "v150_confirmation_inputs_generated": False,
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
        raise RuntimeError("V150 load/seed product changed")
    if {run["method"] for run in manifest["runs"]} != {"sche_nash"}:
        raise RuntimeError("V150 method product changed")
    if len(manifest["reference_build_dependencies"]) != 60:
        raise RuntimeError("V150 reference product changed")
    if manifest.get("all_references_bound") is not False:
        raise RuntimeError("V150 unbound manifest claims bound references")
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
            or run.get("metadata", {}).get("v150_profile") != PROFILES[load]
            or run["reference_dependency"].get("build_required") is not True
        ):
            raise RuntimeError(f"V150 run contract changed: {run.get('run_id')}")


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
        "schema_version": "NSE_E1_HOMOGENEOUS_LEGACY_PROFILE_RUN_ORDER_V150_V1",
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


def prepare_v150(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V150 training root: {root}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_LEGACY_PROFILE_PREPARED_V150_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "performance_results_consulted_for_design": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "prior_training_files": {
            "v58_plan_sha256": V58_PLAN_SHA256,
            "v59_plan_sha256": V59_PLAN_SHA256,
            "legacy_catalog_sha256": LEGACY_CATALOG_SHA256,
            "v149_result_sha256": V149_RESULT_SHA256,
            "v149_result_hash": V149_RESULT_HASH,
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
    receipt = prepare_v150()
    print(json.dumps({"receipt_hash": receipt["receipt_hash"], "runs": 60}))


if __name__ == "__main__":
    main()
