from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_prepare_v143 import (
    CARGO_LOCK,
    CARGO_LOCK_SHA256,
    MODEL_PATH,
    MODEL_SHA256,
    MODULE_CONF,
    MODULE_CONF_SHA256,
    NEW_CONFIRMATION_SEEDS,
    PYTHON_PATH,
    PYTHON_SHA256,
    SCENARIOS,
    SLA_PATH,
    SLA_SHA256,
    TRAINING_SEED_LIST,
    V142_BASELINE_PAIRING,
    V142_BASELINE_READY,
    V142_BASELINE_WORKSPACE,
    V142_BLIND,
    V142_BLIND_HASH,
    V142_BLIND_SHA256,
    V142_EXECUTION,
    V142_EXECUTION_HASH,
    V142_EXECUTION_SHA256,
    V142_PREPARED,
    V142_PREPARED_SHA256,
    V142_RESULT,
    V142_RESULT_HASH,
    V142_RESULT_SHA256,
    V142_TAPE_CATALOG,
    V142_TAPE_CATALOG_SHA256,
    V142_TEMPLATE,
    V142_TEMPLATE_SHA256,
    _assert_hashed,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3_causal_burst_morphology_router_training_20260830_v144")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_causal_burst_morphology_router_training_plan_v144.json"
)
PLAN_SHA256 = "c1cb61ac70bafd080cbf5d9feb1d4579797e6c4ca4c5ab079dc40fbf5263afc0"

V143_ROOT = Path("tmp/nse_e3_random_prefix_ready_tail_training_20260830_v143")
V143_BLIND = V143_ROOT / "joint-blind-audit-v143-training.json"
V143_BLIND_SHA256 = "688206645658ae2ee2784a93de6b907a37a78979f804a0990ac4ef3acd9c2880"
V143_BLIND_HASH = "310e0a22a565fbb572d15725aaa4d37cac0c1f954a7571570627536ab3104cf3"
V143_RESULT = V143_ROOT / "training-result-v143.json"
V143_RESULT_SHA256 = "67ec7e3c65f88d8f5ec861018268f2d25721d44f7c80c5899b8a13ec007ada7e"
V143_RESULT_HASH = "cddc8b012308fc5d424cfe4f3558965285c4b02f31d153c49b7d2c2c94ecd11b"

BINARY_PATH = Path("tmp/nse_v144_build_514224d/release/serverless_sim.exe")
BINARY_SHA256 = "a0b704d795af47d20d003ab7243cabd2426fdc427af0a9ff706c1f7ccb5c1c0c"
BINARY_SOURCE_COMMIT = "514224d7a0b17b20002e694aeef7c92518512a1a"

ARM_ID = "v144-e3-causal-burst-morphology-native-router-nash"
PROFILE = "causal_burst_morphology_hash_greedy_faasrank_loadleast_router_nash"
SELECTION_RULE = "causal_first_seen_arrival_burst_morphology_state_machine"
NATIVE_MEMBERS = ["hash", "greedy", "sche_FaaSRank", "load_least"]
RUNTIME_NATIVE_KINDS = ["hash", "greedy", "faasrank", "load_least"]
RUN_ORDER_SEED = "NSE-V144-CAUSAL-MORPHOLOGY-E1526-E1528"
PORT = "3173"
SHOCK_THRESHOLD_NUMERATOR = 3
SHOCK_THRESHOLD_DENOMINATOR = 2
SHOCK_BASELINE_FRAMES = 80
SHOCK_RECENT_FRAMES = 20
SHOCK_ACTIVE_FRAMES = 50
SERVICE_CERTIFICATE_SCOPE = "all_feasible_players"
V144_SERVICE_STATE_DOMAIN = "runtime_existing_aggregates_and_admitted_work"
V144_WELFARE_STATE_DOMAIN = "empty_current_joint_decision_aggregates_existing_contention_via_pressure_and_eq12_only"
EXPERT_LIFECYCLE = "one_persistent_instance_per_native_expert_advanced_exactly_once_per_scheduling_window"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-manifest-v144.json",
        "schedule": root / "frozen-run-order-v144.json",
    }


def ready_manifest_path(root: Path = ROOT) -> Path:
    return root / f"manifest.{ARM_ID}.ready.json"


def workspace_path(root: Path = ROOT) -> Path:
    return root / "runs" / ARM_ID


def pairing_path(root: Path = ROOT) -> Path:
    return root / f"pairing-audit.{ARM_ID}.json"


def reference_catalog_path(root: Path = ROOT) -> Path:
    return root / f"references.{ARM_ID}.catalog.json"


def _assert_frozen_inputs() -> None:
    frozen = (
        (PLAN, PLAN_SHA256),
        (V142_PREPARED, V142_PREPARED_SHA256),
        (V142_TAPE_CATALOG, V142_TAPE_CATALOG_SHA256),
        (V142_EXECUTION, V142_EXECUTION_SHA256),
        (V142_BLIND, V142_BLIND_SHA256),
        (V142_RESULT, V142_RESULT_SHA256),
        (V142_TEMPLATE, V142_TEMPLATE_SHA256),
        (V143_BLIND, V143_BLIND_SHA256),
        (V143_RESULT, V143_RESULT_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (PYTHON_PATH, PYTHON_SHA256),
        (CARGO_LOCK, CARGO_LOCK_SHA256),
        (MODULE_CONF, MODULE_CONF_SHA256),
        (SLA_PATH, SLA_SHA256),
        (MODEL_PATH, MODEL_SHA256),
    )
    for path, expected in frozen:
        if not path.is_file() or file_hash(path).lower() != expected.lower():
            raise RuntimeError(f"frozen V144 input is missing or changed: {path}")
    _assert_hashed(V142_EXECUTION, "receipt_hash", V142_EXECUTION_HASH)
    _assert_hashed(V142_BLIND, "audit_hash", V142_BLIND_HASH)
    v142_result = _assert_hashed(V142_RESULT, "result_hash", V142_RESULT_HASH)
    _assert_hashed(V143_BLIND, "audit_hash", V143_BLIND_HASH)
    v143_result = _assert_hashed(V143_RESULT, "result_hash", V143_RESULT_HASH)
    for label, result in (("V142", v142_result), ("V143", v143_result)):
        if (
            result.get("family_training_gate_pass") is not False
            or result.get("selected_profile") is not None
            or result.get("passing_candidate_rankings") != []
            or result.get("confirmation_inputs_generated") is not False
        ):
            raise RuntimeError(f"{label} falsification disposition changed")
    if not V142_BASELINE_READY.is_file() or not V142_BASELINE_PAIRING.is_file():
        raise RuntimeError("V142 baseline ready manifest or pairing audit is missing")


def _rewrite_candidate(template: dict[str, Any]) -> dict[str, Any]:
    rewritten = copy.deepcopy(template)
    rewritten["created_at"] = utc_now()
    rewritten["formal_results_eligible"] = False
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    for key in [item for item in marker if item.startswith("v142_")]:
        marker.pop(key)
    marker.update(
        {
            "purpose": f"V144 {ARM_ID} {PLAN_SHA256}",
            "v144_role": "adaptive_training_candidate",
            "v144_training_plan_sha256": PLAN_SHA256,
            "v144_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v144_arm_id": ARM_ID,
            "v144_profile": PROFILE,
            "v144_native_selection_rule": SELECTION_RULE,
            "v144_native_portfolio_members": NATIVE_MEMBERS,
            "v144_runtime_native_kind_order": RUNTIME_NATIVE_KINDS,
            "v144_shock_threshold_numerator": SHOCK_THRESHOLD_NUMERATOR,
            "v144_shock_threshold_denominator": SHOCK_THRESHOLD_DENOMINATOR,
            "v144_shock_baseline_frames": SHOCK_BASELINE_FRAMES,
            "v144_shock_recent_frames": SHOCK_RECENT_FRAMES,
            "v144_shock_active_frames": SHOCK_ACTIVE_FRAMES,
            "v144_expert_lifecycle": EXPERT_LIFECYCLE,
            "v144_expected_run_count": 9,
            "v144_expected_reference_count": 9,
            "v144_reused_v142_baseline_runs": 81,
            "v144_baseline_rerun_count": 0,
            "v144_performance_results_consulted_for_mechanism_design": True,
            "v144_candidate_performance_summaries_parsed": 0,
            "v144_confirmation_inputs_opened": False,
            "sealed_new_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
            "strictly_serial": True,
            "run_order_seed": RUN_ORDER_SEED,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        metadata = run.setdefault("metadata", {})
        for key in [item for item in metadata if item.startswith("v142_")]:
            metadata.pop(key)
        metadata.update(
            {
                "v144_training_plan_sha256": PLAN_SHA256,
                "v144_training_only": True,
                "v144_role": "adaptive_training_candidate",
                "v144_arm_id": ARM_ID,
                "v144_profile": PROFILE,
                "v144_native_selection_rule": SELECTION_RULE,
                "v144_native_portfolio_members": NATIVE_MEMBERS,
                "v144_source_v142_run_id": source_run_id,
                "v144_source_v142_run_spec_hash": source_run_spec_hash,
                "v144_expert_lifecycle": EXPERT_LIFECYCLE,
                "v144_all_four_experts_advanced_every_window": True,
                "v144_shock_detector": "first_seen_arrivals_80_frame_baseline_20_frame_recent_3_over_2_threshold_50_frame_latch",
                "v144_quiet_route": "hash",
                "v144_first_short_route": "greedy",
                "v144_first_sustained_route": "faasrank",
                "v144_recurrent_route": "load_least",
                "v144_complete_native_assignments_required": True,
                "v144_service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
                "v144_service_certificate_state_domain": V144_SERVICE_STATE_DOMAIN,
                "v144_paper_welfare_state_domain": V144_WELFARE_STATE_DOMAIN,
                "v144_no_numeric_tuning": True,
                "v144_outcome_fields_drive_policy": False,
                "v144_scenario_or_burst_label_used_by_policy": False,
                "v144_future_arrivals_used_by_policy": False,
                "v144_adaptive_training_reuses_v142_results": True,
                "v144_confirmation_inputs_opened": False,
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


def _validate_product(manifest: dict[str, Any]) -> None:
    runs = manifest["runs"]
    expected = {
        (scenario, seed) for scenario in SCENARIOS for seed in TRAINING_SEED_LIST
    }
    actual = {(scenario_id(run), run["seed"]) for run in runs}
    if len(runs) != 9 or actual != expected:
        raise RuntimeError("V144 scenario/seed product changed")
    if {run["method"] for run in runs} != {"sche_nash"}:
        raise RuntimeError("V144 method product changed")
    if len(manifest["reference_build_dependencies"]) != 9:
        raise RuntimeError("V144 reference product changed")
    if any(
        run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") != PROFILE
        or run.get("metadata", {}).get("v144_native_portfolio_members")
        != NATIVE_MEMBERS
        or run.get("metadata", {}).get("v144_confirmation_inputs_opened") is not False
        for run in runs
    ):
        raise RuntimeError("V144 candidate contract changed")


def _frozen_schedule(manifest: dict[str, Any]) -> dict[str, Any]:
    cells = [
        {
            "scenario": scenario_id(run),
            "seed": run["seed"],
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
        "schema_version": "NSE_E3_CAUSAL_BURST_MORPHOLOGY_RUN_ORDER_V144_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "performance_results_consulted_for_mechanism_design": True,
        "plan_sha256": PLAN_SHA256,
        "run_order_seed": RUN_ORDER_SEED,
        "randomization_unit": "nine_scenario_by_seed_candidate_cells",
        "schedule": schedule,
    }
    document["schedule_hash"] = object_hash(document)
    return document


def prepare_v144(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V144 training root: {root}")
    root.mkdir(parents=True)
    output = paths(root)
    manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
    _validate_product(manifest)
    write_json_atomic(output["manifest"], manifest)
    schedule = _frozen_schedule(manifest)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E3_CAUSAL_BURST_MORPHOLOGY_PREPARED_V144_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted_for_mechanism_design": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "v142_prepared_path": str(V142_PREPARED),
        "v142_prepared_file_sha256": V142_PREPARED_SHA256,
        "v142_tape_catalog_path": str(V142_TAPE_CATALOG),
        "v142_tape_catalog_file_sha256": V142_TAPE_CATALOG_SHA256,
        "v142_execution_path": str(V142_EXECUTION),
        "v142_execution_file_sha256": V142_EXECUTION_SHA256,
        "v142_execution_hash": V142_EXECUTION_HASH,
        "v142_blind_path": str(V142_BLIND),
        "v142_blind_file_sha256": V142_BLIND_SHA256,
        "v142_blind_hash": V142_BLIND_HASH,
        "v142_result_path": str(V142_RESULT),
        "v142_result_file_sha256": V142_RESULT_SHA256,
        "v142_result_hash": V142_RESULT_HASH,
        "v143_blind_path": str(V143_BLIND),
        "v143_blind_file_sha256": V143_BLIND_SHA256,
        "v143_blind_hash": V143_BLIND_HASH,
        "v143_result_path": str(V143_RESULT),
        "v143_result_file_sha256": V143_RESULT_SHA256,
        "v143_result_hash": V143_RESULT_HASH,
        "parent_disposition": "V142_and_V143_complete_training_falsified_no_confirmation_inputs_generated",
        "v142_baseline_ready_manifest_path": str(V142_BASELINE_READY),
        "v142_baseline_workspace": str(V142_BASELINE_WORKSPACE),
        "v142_baseline_pairing_path": str(V142_BASELINE_PAIRING),
        "reused_frozen_v142_baseline_runs": 81,
        "baseline_reruns": 0,
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
        "sealed_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        "confirmation_inputs_generated": False,
        "candidate_online_runs": 9,
        "candidate_reference_builds": 9,
        "strictly_serial": True,
        "run_order_seed": RUN_ORDER_SEED,
        "frozen_schedule_path": str(output["schedule"]),
        "frozen_schedule_file_sha256": file_hash(output["schedule"]),
        "frozen_schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "arm_id": ARM_ID,
        "profile": PROFILE,
        "native_selection_rule": SELECTION_RULE,
        "native_portfolio_members": NATIVE_MEMBERS,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def main() -> None:
    receipt = prepare_v144()
    print(json.dumps({"receipt_hash": receipt["receipt_hash"], "runs": 9}))


if __name__ == "__main__":
    main()
