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
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
    CARGO_LOCK,
    CARGO_LOCK_SHA256,
    MODEL_PATH,
    MODEL_SHA256,
    MODULE_CONF,
    MODULE_CONF_SHA256,
    NEW_CONFIRMATION_SEEDS,
    PAPER_WELFARE_STATE_DOMAIN,
    PYTHON_PATH,
    PYTHON_SHA256,
    RANDOM_SHADOW_LIFECYCLE,
    SCENARIOS,
    SERVICE_CERTIFICATE_STATE_DOMAIN,
    SLA_PATH,
    SLA_SHA256,
    TRAINING_SEED_LIST,
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


ROOT = Path("tmp/nse_e3_random_prefix_ready_tail_training_20260830_v143")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_random_prefix_ready_tail_training_plan_v143.json"
)
PLAN_SHA256 = "887456e3e9dc0a3b36e80d515c4e0bc3ad8b86b9ae34cf0ae5355c4a73d52ff9"

V142_ROOT = Path("tmp/nse_e3_random_prefix_training_20260830_v142")
V142_PREPARED = V142_ROOT / "prepared-manifests-v142.json"
V142_PREPARED_SHA256 = (
    "0c1c7f4f9732e4af19974c980024dca13499c082c0769750db8a152bf1c29ca0"
)
V142_TAPE_CATALOG = V142_ROOT / "tapes.catalog.json"
V142_TAPE_CATALOG_SHA256 = (
    "8e6b43d4b3e45eebe1450f344ed45d52242ffd5a8e09bcd46b24571a926324ca"
)
V142_EXECUTION = V142_ROOT / "execution-receipt-v142.json"
V142_EXECUTION_SHA256 = (
    "3fb10613f586488b19e7b7c542843099a8751ab6be7894adbfee89ded26bb1c0"
)
V142_EXECUTION_HASH = "82f65cc36d5f775c47a07acbc860e6cd9585fd1e1c5e21c822cab5fd9c84557a"
V142_BLIND = V142_ROOT / "joint-blind-audit-v142-training.json"
V142_BLIND_SHA256 = "d30551d98cca78681f165c60991354d7950c7dbe5ce8352a54f641434591fabc"
V142_BLIND_HASH = "23d6e417f067fa75296d92b61b85dfafdf3ff2f979dbea9774a2bd7a3ae3df15"
V142_RESULT = V142_ROOT / "training-result-v142.json"
V142_RESULT_SHA256 = "49682bed2e245018dd789f7f8afd1929dbc6e5688f4fdf0105e5554f77b4c452"
V142_RESULT_HASH = "aa41930ef4a73ab2eb427183a19fe2ed71309d50172b37054c7235ff6021553e"
V142_TEMPLATE = (
    V142_ROOT
    / "manifest.v142-e3-random-prefix-service-pareto-portfolio-nash.unbound.json"
)
V142_TEMPLATE_SHA256 = (
    "06f2b52aed714125fe086350b8060b59ba5ad4793244723ee86ea8053a1b0cb3"
)
V142_BASELINE_READY = V142_ROOT / "manifest.v142-baselines.ready.json"
V142_BASELINE_WORKSPACE = V142_ROOT / "runs" / "v142-baselines"
V142_BASELINE_PAIRING = V142_ROOT / "pairing-audit.v142-baselines.json"

BINARY_PATH = Path("tmp/nse_v143_build_2430446/release/serverless_sim.exe")
BINARY_SHA256 = "4863d34118730dc531cc47be8dc42d18ab1fa0dded10f3e38d1d6b5ba1e77d50"
BINARY_SOURCE_COMMIT = "243044683133d56976d7d4ac4e04f87a6099063d"

ARM_ID = (
    "v143-e3-random-prefix-ready-tail-faasrank-default-service-pareto-portfolio-nash"
)
PROFILE = "random_prefix_ready_tail_faasrank_default_service_pareto_portfolio_nash"
SELECTION_RULE = "faasrank_default_service_pareto"
NATIVE_MEMBERS = [
    "sche_FaaSRank",
    "greedy",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
    "load_least",
    "sche_OCS",
]
RUNTIME_NATIVE_KINDS = [
    "faasrank",
    "greedy",
    "hiku",
    "jiagu",
    "orion",
    "load_least",
    "ocs",
]
RUN_ORDER_SEED = "NSE-V143-READY-TAIL-E1526-E1528"
PORT = "3172"
COHORT_SOURCE = (
    "exact_random_prefix_union_current_parents_completed_common_feasible_tail"
)
READY_TAIL_PREDICATE = (
    "all_parent_functions_complete_at_window_start_and_common_placement_feasible"
)
SERVICE_CERTIFICATE_SCOPE = (
    "exact_random_prefix_union_current_parents_completed_feasible_tail"
)
V143_SERVICE_STATE_DOMAIN = "runtime_existing_aggregates_and_admitted_work_projected_to_exact_random_prefix_union_ready_tail"
V143_WELFARE_STATE_DOMAIN = (
    "empty_current_joint_decision_aggregates_existing_contention_via_pressure_and_eq12_only_"
    "projected_to_exact_random_prefix_union_ready_tail"
)


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-manifest-v143.json",
        "schedule": root / "frozen-run-order-v143.json",
    }


def ready_manifest_path(root: Path = ROOT) -> Path:
    return root / f"manifest.{ARM_ID}.ready.json"


def workspace_path(root: Path = ROOT) -> Path:
    return root / "runs" / ARM_ID


def pairing_path(root: Path = ROOT) -> Path:
    return root / f"pairing-audit.{ARM_ID}.json"


def reference_catalog_path(root: Path = ROOT) -> Path:
    return root / f"references.{ARM_ID}.catalog.json"


def _assert_hashed(path: Path, field: str, expected_hash: str) -> dict[str, Any]:
    document = read_json(path)
    payload = dict(document)
    claimed = payload.pop(field, None)
    if claimed != expected_hash or object_hash(payload) != claimed:
        raise RuntimeError(f"frozen hashed object changed: {path}")
    return document


def _assert_frozen_inputs() -> None:
    frozen = (
        (PLAN, PLAN_SHA256),
        (V142_PREPARED, V142_PREPARED_SHA256),
        (V142_TAPE_CATALOG, V142_TAPE_CATALOG_SHA256),
        (V142_EXECUTION, V142_EXECUTION_SHA256),
        (V142_BLIND, V142_BLIND_SHA256),
        (V142_RESULT, V142_RESULT_SHA256),
        (V142_TEMPLATE, V142_TEMPLATE_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (PYTHON_PATH, PYTHON_SHA256),
        (CARGO_LOCK, CARGO_LOCK_SHA256),
        (MODULE_CONF, MODULE_CONF_SHA256),
        (SLA_PATH, SLA_SHA256),
        (MODEL_PATH, MODEL_SHA256),
    )
    for path, expected in frozen:
        if not path.is_file() or file_hash(path).lower() != expected.lower():
            raise RuntimeError(f"frozen V143 input is missing or changed: {path}")
    _assert_hashed(
        V142_PREPARED, "receipt_hash", read_json(V142_PREPARED)["receipt_hash"]
    )
    _assert_hashed(
        V142_TAPE_CATALOG, "catalog_hash", read_json(V142_TAPE_CATALOG)["catalog_hash"]
    )
    _assert_hashed(V142_EXECUTION, "receipt_hash", V142_EXECUTION_HASH)
    _assert_hashed(V142_BLIND, "audit_hash", V142_BLIND_HASH)
    result = _assert_hashed(V142_RESULT, "result_hash", V142_RESULT_HASH)
    if (
        result.get("family_training_gate_pass") is not False
        or result.get("selected_profile") is not None
        or result.get("passing_candidate_rankings") != []
        or result.get("confirmation_inputs_generated") is not False
    ):
        raise RuntimeError("V142 falsification disposition changed")
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
            "purpose": f"V143 {ARM_ID} {PLAN_SHA256}",
            "v143_role": "adaptive_training_candidate",
            "v143_training_plan_sha256": PLAN_SHA256,
            "v143_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v143_arm_id": ARM_ID,
            "v143_profile": PROFILE,
            "v143_native_selection_rule": SELECTION_RULE,
            "v143_native_portfolio_members": NATIVE_MEMBERS,
            "v143_runtime_native_kind_order": RUNTIME_NATIVE_KINDS,
            "v143_random_prefix_ready_tail_cohort_required": True,
            "v143_cohort_source": COHORT_SOURCE,
            "v143_ready_tail_predicate": READY_TAIL_PREDICATE,
            "v143_expected_run_count": 9,
            "v143_expected_reference_count": 9,
            "v143_reused_v142_baseline_runs": 81,
            "v143_baseline_rerun_count": 0,
            "v143_performance_results_consulted_for_mechanism_design": True,
            "v143_candidate_performance_summaries_parsed": 0,
            "v143_confirmation_inputs_opened": False,
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
                "v143_training_plan_sha256": PLAN_SHA256,
                "v143_training_only": True,
                "v143_role": "adaptive_training_candidate",
                "v143_arm_id": ARM_ID,
                "v143_profile": PROFILE,
                "v143_native_selection_rule": SELECTION_RULE,
                "v143_native_portfolio_members": NATIVE_MEMBERS,
                "v143_source_v142_run_id": source_run_id,
                "v143_source_v142_run_spec_hash": source_run_spec_hash,
                "v143_random_shadow_seed_source": "algorithm_seed",
                "v143_random_shadow_lifecycle": RANDOM_SHADOW_LIFECYCLE,
                "v143_random_prefix_preserved": True,
                "v143_random_prefix_node_ids_preserved": True,
                "v143_ready_tail_predicate": READY_TAIL_PREDICATE,
                "v143_ready_tail_stable_all_frontier_order": True,
                "v143_prefix_ready_overlap_removed": True,
                "v143_common_cohort_required": True,
                "v143_faasrank_default_required": True,
                "v143_complete_hybrid_assignments_required": True,
                "v143_service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
                "v143_service_certificate_state_domain": V143_SERVICE_STATE_DOMAIN,
                "v143_paper_welfare_state_domain": V143_WELFARE_STATE_DOMAIN,
                "v143_no_numeric_tuning": True,
                "v143_outcome_fields_drive_policy": False,
                "v143_scenario_or_burst_label_used_by_policy": False,
                "v143_future_arrivals_used_by_policy": False,
                "v143_adaptive_training_reuses_v142_results": True,
                "v143_confirmation_inputs_opened": False,
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
        raise RuntimeError("V143 scenario/seed product changed")
    if {run["method"] for run in runs} != {"sche_nash"}:
        raise RuntimeError("V143 method product changed")
    if len(manifest["reference_build_dependencies"]) != 9:
        raise RuntimeError("V143 reference product changed")
    if any(
        run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") != PROFILE
        or run.get("metadata", {}).get("v143_native_portfolio_members")
        != NATIVE_MEMBERS
        or run.get("metadata", {}).get("v143_confirmation_inputs_opened") is not False
        for run in runs
    ):
        raise RuntimeError("V143 candidate contract changed")


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
        "schema_version": "NSE_E3_RANDOM_PREFIX_READY_TAIL_RUN_ORDER_V143_V1",
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


def prepare_v143(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V143 training root: {root}")
    root.mkdir(parents=True)
    output = paths(root)
    manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
    _validate_product(manifest)
    write_json_atomic(output["manifest"], manifest)
    schedule = _frozen_schedule(manifest)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_READY_TAIL_PREPARED_V143_V1",
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
        "v142_disposition": "complete_training_family_falsified_no_candidate_selected_no_confirmation_inputs_generated",
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
    receipt = prepare_v143()
    print(json.dumps({"receipt_hash": receipt["receipt_hash"], "runs": 9}))


if __name__ == "__main__":
    main()
