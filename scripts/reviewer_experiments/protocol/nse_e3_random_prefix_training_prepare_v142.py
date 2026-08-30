from __future__ import annotations

import copy
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from scripts.reviewer_experiments.protocol.faasrank_model import (
    rust_faasrank_model_config,
    verify_frozen_faasrank_model,
)
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
    write_manifest,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_horizon_training_prepare_v109 import (
    CARGO_LOCK,
    CARGO_LOCK_SHA256,
    COMMON_ENVIRONMENT,
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_SHA256,
    FORMAL_RESULT,
    FORMAL_RESULT_SHA256,
    MODEL_PATH,
    MODEL_SHA256,
    MODULE_CONF,
    MODULE_CONF_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    SLA_PATH,
    SLA_SHA256,
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


ROOT = Path("tmp/nse_e3_random_prefix_training_20260830_v142")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_random_prefix_training_plan_v142.json"
)
PLAN_SHA256 = "8fb6d0e22d028c66de868145fe77316fc857341fcc1c2825a83d0175f12919dc"

V141_PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_random_anchor_training_plan_v141.json"
)
V141_PLAN_SHA256 = "50ee395d6cf9be9408c77d6e86cfbe2d99dae05bfa0a2ff9e702c53ff9f84f05"
V141_ROOT = Path("tmp/nse_e3_random_anchor_training_20260830_v141")
V141_PREPARED = V141_ROOT / "prepared-manifests-v141.json"
V141_PREPARED_SHA256 = (
    "ba4e7f16d1274bcda151ac07fa3835b5a4ba182e7afea413d5d035774488d1af"
)
V141_TAPE_CATALOG = V141_ROOT / "tapes.catalog.json"
V141_TAPE_CATALOG_SHA256 = (
    "c1bc6d60088f02361258a508e96be6bbfbe3a42ecdbf4621d3e752d5299660e0"
)
V141_FAILURE = V141_ROOT / "technical-reference-failure-v141.json"
V141_FAILURE_SHA256 = "b834ef970b4a749299c2b97b0f2361261e62d2ba0582d5ad91128a941fa7aa76"
V141_FAILURE_HASH = "396261f6f3b47843803127fd188c09444cacafbf1c345fff325b115951894a0b"

BINARY_PATH = Path("tmp/nse_v142_build_f7fe8eb/release/serverless_sim.exe")
BINARY_SHA256 = "ad2a07c33c1e4241dd8d8d544f7f785913d89793eededdd4c66352b8972a6ce5"
BINARY_SOURCE_COMMIT = "f7fe8eb0a54f82c5cec2e830f0b95fa39ad36b58"

TRAINING_SEED_LIST = ["E1526", "E1527", "E1528"]
TRAINING_SEEDS = set(TRAINING_SEED_LIST)
SOURCE_INITIAL_SEEDS = [
    *TRAINING_SEED_LIST,
    "E1448",
    "E1449",
    "E1450",
    "E1425",
    "E1426",
    "E1427",
    "E1402",
]
SOURCE_CI_SEEDS = [
    "E1403",
    "E1404",
    "E1379",
    "E1380",
    "E1381",
    "E1356",
    "E1357",
    "E1358",
    "E1333",
    "E1334",
]
RETIRED_V137_CONFIRMATION_SEEDS = [f"E{index}" for index in range(1474, 1494)]
RETIRED_OPENED_V138_TRAINING_SEEDS = ["E1494", "E1495", "E1496"]
RETIRED_OPENED_V139_TRAINING_SEEDS = ["E1517", "E1518", "E1519"]
RETIRED_OPENED_V140_TRAINING_SEEDS = ["E1520", "E1521", "E1522"]
RETIRED_OPENED_V141_TRAINING_SEEDS = ["E1523", "E1524", "E1525"]
NEW_CONFIRMATION_SEEDS = [f"E{index}" for index in range(1497, 1517)]
FORBIDDEN_SOURCE_SEEDS = set(
    RETIRED_V137_CONFIRMATION_SEEDS
    + RETIRED_OPENED_V138_TRAINING_SEEDS
    + RETIRED_OPENED_V139_TRAINING_SEEDS
    + RETIRED_OPENED_V140_TRAINING_SEEDS
    + RETIRED_OPENED_V141_TRAINING_SEEDS
    + NEW_CONFIRMATION_SEEDS
)

SCENARIOS = ["spike5x50ms", "sustained3x200ms", "pulse4x4x50ms"]
BASELINE_METHODS = [
    "greedy",
    "random",
    "hash",
    "load_least",
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_orion",
    "sche_jiagu",
]
BASELINE_METHOD_SET = set(BASELINE_METHODS)
ARMS = (
    (
        "v142-e3-random-prefix-service-safe-nash",
        "random_prefix_native_faithful_service_window_safe_pareto",
        "exact_random_prefix",
    ),
    (
        "v142-e3-random-prefix-service-pareto-portfolio-nash",
        "random_prefix_default_native_service_pareto_portfolio_nash",
        "random_prefix_service_pareto",
    ),
    (
        "v142-e3-random-prefix-welfare-pareto-portfolio-nash",
        "random_prefix_default_native_welfare_pareto_portfolio_nash",
        "random_prefix_welfare_pareto",
    ),
)
ARM_IDS = [item[0] for item in ARMS]
METHOD_LABELS = BASELINE_METHODS + ARM_IDS
RUN_ORDER_SEED = "NSE-V142-RCBD-E1526-E1528"
PORT = "3171"
RANDOM_PREFIX_COHORT_SOURCE = "exact_persistent_same_seed_native_Random_ScheCmd_prefix_with_unchanged_early_stop_semantics"
RANDOM_SHADOW_LIFECYCLE = "one_persistent_RandomScheduler_per_algorithm_seed_advanced_once_per_scheduling_window"
SERVICE_CERTIFICATE_SCOPE = "exact_random_emitted_command_prefix_players"
SERVICE_CERTIFICATE_STATE_DOMAIN = (
    "runtime_existing_aggregates_and_admitted_work_projected_to_exact_random_prefix"
)
PAPER_WELFARE_STATE_DOMAIN = "empty_current_joint_decision_aggregates_existing_contention_via_pressure_and_eq12_only_projected_to_exact_random_prefix"


def native_members(selection_rule: str) -> list[str]:
    if selection_rule == "exact_random_prefix":
        return ["random"]
    if selection_rule in {
        "random_prefix_service_pareto",
        "random_prefix_welfare_pareto",
    }:
        return ["random", "greedy", "hiku", "jiagu", "orion", "load_least"]
    raise RuntimeError(f"unknown V142 native selection rule: {selection_rule}")


def scenario_id(run: dict[str, Any]) -> str:
    kind = run["workload"]["burst"]["kind"]
    try:
        return {
            "spike": "spike5x50ms",
            "sustained": "sustained3x200ms",
            "pulse": "pulse4x4x50ms",
        }[kind]
    except KeyError as exc:
        raise RuntimeError(f"unexpected E3 burst kind: {kind}") from exc


def arm_path(root: Path, arm_id: str, stage: str = "unbound") -> Path:
    return root / f"manifest.{arm_id}.{stage}.json"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "config": root / "v142-e3-training-config.json",
        "source": root / "manifest.v142-training-source-full.unbound.json",
        "capture": root / "manifest.v142-tape-capture.unbound.json",
        "baselines": root / "manifest.v142-baselines.unbound.json",
        "prepared": root / "prepared-manifests-v142.json",
        "schedule": root / "frozen-run-order-v142.json",
    }


def _assert_hashed_object(path: Path, field: str) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    payload = dict(document)
    claimed = payload.pop(field, None)
    if not isinstance(claimed, str) or object_hash(payload) != claimed:
        raise RuntimeError(f"frozen hashed object changed: {path}")


def _assert_frozen_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V141_PLAN, V141_PLAN_SHA256),
        (V141_PREPARED, V141_PREPARED_SHA256),
        (V141_TAPE_CATALOG, V141_TAPE_CATALOG_SHA256),
        (V141_FAILURE, V141_FAILURE_SHA256),
        (FORMAL_RESULT, FORMAL_RESULT_SHA256),
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256),
        (SLA_PATH, SLA_SHA256),
        (MODEL_PATH, MODEL_SHA256),
        (BINARY_PATH, BINARY_SHA256),
        (PYTHON_PATH, PYTHON_SHA256),
        (CARGO_LOCK, CARGO_LOCK_SHA256),
        (MODULE_CONF, MODULE_CONF_SHA256),
    ):
        if not path.is_file() or file_hash(path).lower() != expected.lower():
            raise RuntimeError(f"frozen V142 input is missing or changed: {path}")
    _assert_hashed_object(V141_PREPARED, "receipt_hash")
    _assert_hashed_object(V141_TAPE_CATALOG, "catalog_hash")
    _assert_hashed_object(V141_FAILURE, "failure_hash")
    failure = json.loads(V141_FAILURE.read_text(encoding="utf-8"))
    if (
        failure.get("status")
        != "technical_reference_build_failure_before_online_execution"
        or failure.get("failure_hash") != V141_FAILURE_HASH
        or failure.get("performance_summaries_parsed") != 0
        or failure.get("performance_results_consulted") is not False
        or failure.get("online_runs_started") != 0
        or failure.get("online_runs_canonicalized") != 0
        or failure.get("blocked_reference_key_count") != 9
        or failure.get("quarantined_reference_attempt_count") != 27
        or failure.get("confirmation_inputs_opened") is not False
    ):
        raise RuntimeError("V141 pre-online technical failure disposition changed")


def _write_config(path: Path) -> None:
    if FORBIDDEN_SOURCE_SEEDS & set(SOURCE_INITIAL_SEEDS + SOURCE_CI_SEEDS):
        raise RuntimeError("V142 source seed policy reuses a retired or sealed seed")
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


def _is_training_e3(run: dict[str, Any]) -> bool:
    return (
        run["experiment_id"] == "E3"
        and run["seed"] in TRAINING_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced"
        and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
        and scenario_id(run) in SCENARIOS
    )


def _selected_ids(
    source: dict[str, Any], predicate: Callable[[dict[str, Any]], bool], expected: int
) -> list[str]:
    selected = [run["run_id"] for run in source["runs"] if predicate(run)]
    if len(selected) != expected:
        raise RuntimeError(f"expected {expected} selected runs, got {len(selected)}")
    return selected


def _base_marker(rewritten: dict[str, Any], purpose: str) -> dict[str, Any]:
    rewritten["created_at"] = utc_now()
    rewritten["formal_results_eligible"] = False
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": purpose,
            "v142_training_plan_sha256": PLAN_SHA256,
            "v142_training_only": True,
            "v142_binary_source_commit": BINARY_SOURCE_COMMIT,
            "selected_development_seeds": TRAINING_SEED_LIST,
            "retired_unmaterialized_v137_confirmation_seeds": RETIRED_V137_CONFIRMATION_SEEDS,
            "retired_opened_v138_training_seeds": RETIRED_OPENED_V138_TRAINING_SEEDS,
            "retired_opened_v139_training_seeds": RETIRED_OPENED_V139_TRAINING_SEEDS,
            "retired_opened_v140_training_seeds": RETIRED_OPENED_V140_TRAINING_SEEDS,
            "retired_opened_v141_training_seeds": RETIRED_OPENED_V141_TRAINING_SEEDS,
            "sealed_new_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
            "formal_results_eligible": False,
            "operational_group_closure_eligible": False,
            "performance_results_consulted": False,
            "formal_E01_E20_reexecution": 0,
            "strictly_serial": True,
            "run_order_seed": RUN_ORDER_SEED,
        }
    )
    return marker


def _finalize(rewritten: dict[str, Any]) -> dict[str, Any]:
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    marker = rewritten["integration_smoke_shard"]
    marker["selected_run_count"] = len(rewritten["runs"])
    marker["selected_reference_build_count"] = len(
        rewritten["reference_build_dependencies"]
    )
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _rewrite_capture(shard: dict[str, Any]) -> dict[str, Any]:
    rewritten = copy.deepcopy(shard)
    marker = _base_marker(rewritten, f"V142 fresh parent tapes {PLAN_SHA256}")
    marker["v142_role"] = "fresh_parent_tape_capture"
    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run.setdefault("metadata", {}).update(
            {
                "v142_training_plan_sha256": PLAN_SHA256,
                "v142_training_only": True,
                "v142_confirmation_inputs_opened": False,
            }
        )
        _assign_run_identity(run)
    return _finalize(rewritten)


def _rewrite_baselines(shard: dict[str, Any]) -> dict[str, Any]:
    rewritten = copy.deepcopy(shard)
    marker = _base_marker(rewritten, f"V142 complete baseline product {PLAN_SHA256}")
    marker.update(
        {
            "v142_role": "paper_baseline",
            "v142_expected_run_count": 81,
            "v142_expected_reference_count": 0,
            "v142_baseline_methods": BASELINE_METHODS,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = "v142-complete-paper-baselines"
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run.setdefault("metadata", {}).update(
            {
                "v142_training_plan_sha256": PLAN_SHA256,
                "v142_training_only": True,
                "v142_role": "paper_baseline",
                "v142_source_run_id": source_run_id,
                "v142_source_run_spec_hash": source_run_spec_hash,
                "v142_performance_consulted_before_execution": False,
                "v142_confirmation_inputs_opened": False,
                "v142_outcome_fields_drive_policy": False,
            }
        )
        _assign_run_identity(run)
    _validate_baseline_product(rewritten["runs"])
    return _finalize(rewritten)


def _rewrite_arm(
    shard: dict[str, Any],
    arm: tuple[str, str, str],
    frozen_model_config: dict[str, Any],
) -> dict[str, Any]:
    arm_id, profile, selection_rule = arm
    members = native_members(selection_rule)
    portfolio_enabled = selection_rule != "exact_random_prefix"
    rewritten = copy.deepcopy(shard)
    marker = _base_marker(rewritten, f"V142 {arm_id} {PLAN_SHA256}")
    marker.update(
        {
            "v142_role": "candidate",
            "v142_arm_id": arm_id,
            "v142_profile": profile,
            "v142_native_selection_rule": selection_rule,
            "v142_native_portfolio_enabled": portfolio_enabled,
            "v142_native_portfolio_members": members,
            "v142_expected_run_count": 9,
            "v142_expected_reference_count": 9,
            "v142_native_shadow_exactness_required": True,
            "v142_random_prefix_cohort_required": True,
            "v142_exact_random_command_count_required": True,
            "v142_tail_dispatch_forbidden": True,
            "v142_service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
            "v142_service_certificate_state_domain": SERVICE_CERTIFICATE_STATE_DOMAIN,
            "v142_paper_welfare_state_domain": PAPER_WELFARE_STATE_DOMAIN,
            "v142_selected_welfare_equals_guard_initializer_required": True,
            "v142_outcome_fields_drive_policy": False,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = arm_id
        run["environment"].update(COMMON_ENVIRONMENT)
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
        run["simulator_experiment"]["faasrank_model"] = copy.deepcopy(
            frozen_model_config
        )
        run.setdefault("metadata", {}).update(
            {
                "v142_training_plan_sha256": PLAN_SHA256,
                "v142_training_only": True,
                "v142_role": "candidate",
                "v142_arm_id": arm_id,
                "v142_profile": profile,
                "v142_native_selection_rule": selection_rule,
                "v142_native_portfolio_enabled": portfolio_enabled,
                "v142_native_portfolio_members": members,
                "v142_source_run_id": source_run_id,
                "v142_source_run_spec_hash": source_run_spec_hash,
                "v142_native_shadow_exactness_required": True,
                "v142_random_shadow_seed_source": "algorithm_seed",
                "v142_random_shadow_lifecycle": RANDOM_SHADOW_LIFECYCLE,
                "v142_random_default_required": True,
                "v142_random_prefix_cohort_required": True,
                "v142_exact_random_command_count_required": True,
                "v142_tail_dispatch_forbidden": True,
                "v142_nonrandom_native_sources_complete_all_frontier": True,
                "v142_native_candidates_projected_to_random_prefix": True,
                "v142_selected_player_order_from_random_prefix": True,
                "v142_prefix_service_complete_assignment_required": True,
                "v142_service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
                "v142_service_certificate_state_domain": SERVICE_CERTIFICATE_STATE_DOMAIN,
                "v142_paper_welfare_state_domain": PAPER_WELFARE_STATE_DOMAIN,
                "v142_selected_welfare_equals_guard_initializer_required": True,
                "v142_prefix_service_sum_strictly_lower": True,
                "v142_prefix_service_max_nonincreasing": True,
                "v142_immutable_baseline_welfare_nonworse": True,
                "v142_no_numeric_tuning": True,
                "v142_outcome_fields_drive_policy": False,
                "v142_scenario_or_burst_label_used_by_policy": False,
                "v142_future_arrivals_used_by_policy": False,
                "v142_confirmation_inputs_opened": False,
            }
        )
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"]["table_path"] = run[
            "reference_dependency"
        ]["path"]
        _assign_run_identity(run)
    _validate_arm_product(rewritten["runs"], arm_id, profile, selection_rule)
    return _finalize(rewritten)


def _validate_baseline_product(runs: list[dict[str, Any]]) -> None:
    expected = {
        (method, scenario, seed)
        for method in BASELINE_METHODS
        for scenario in SCENARIOS
        for seed in TRAINING_SEED_LIST
    }
    actual = {(run["method"], scenario_id(run), run["seed"]) for run in runs}
    if len(runs) != 81 or actual != expected:
        raise RuntimeError("V142 baseline method/scenario/seed product changed")
    if any(run.get("reference_dependency") is not None for run in runs):
        raise RuntimeError("V142 baseline product unexpectedly requires references")


def _validate_arm_product(
    runs: list[dict[str, Any]], arm_id: str, profile: str, selection_rule: str
) -> None:
    expected = {
        (scenario, seed) for scenario in SCENARIOS for seed in TRAINING_SEED_LIST
    }
    actual = {(scenario_id(run), run["seed"]) for run in runs}
    if len(runs) != 9 or actual != expected:
        raise RuntimeError(f"V142 arm product changed: {arm_id}")
    if {run["method"] for run in runs} != {"sche_nash"}:
        raise RuntimeError(f"V142 arm method changed: {arm_id}")
    if {run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") for run in runs} != {
        profile
    }:
        raise RuntimeError(f"V142 arm profile changed: {arm_id}")
    members = native_members(selection_rule)
    if any(
        run.get("metadata", {}).get("v142_native_selection_rule") != selection_rule
        or run.get("metadata", {}).get("v142_native_portfolio_enabled")
        is not (selection_rule != "exact_random_prefix")
        or run.get("metadata", {}).get("v142_native_portfolio_members") != members
        or run.get("metadata", {}).get("v142_random_default_required") is not True
        or run.get("metadata", {}).get("v142_random_shadow_seed_source")
        != "algorithm_seed"
        or run.get("metadata", {}).get("v142_random_shadow_lifecycle")
        != RANDOM_SHADOW_LIFECYCLE
        or run.get("metadata", {}).get(
            "v142_nonrandom_native_sources_complete_all_frontier"
        )
        is not True
        or run.get("metadata", {}).get(
            "v142_native_candidates_projected_to_random_prefix"
        )
        is not True
        or run.get("metadata", {}).get("v142_random_prefix_cohort_required") is not True
        or run.get("metadata", {}).get("v142_exact_random_command_count_required")
        is not True
        or run.get("metadata", {}).get("v142_tail_dispatch_forbidden") is not True
        or run.get("metadata", {}).get("v142_service_certificate_scope")
        != SERVICE_CERTIFICATE_SCOPE
        or run.get("metadata", {}).get("v142_service_certificate_state_domain")
        != SERVICE_CERTIFICATE_STATE_DOMAIN
        or run.get("metadata", {}).get("v142_paper_welfare_state_domain")
        != PAPER_WELFARE_STATE_DOMAIN
        or run.get("metadata", {}).get(
            "v142_selected_welfare_equals_guard_initializer_required"
        )
        is not True
        or run.get("metadata", {}).get("v142_outcome_fields_drive_policy") is not False
        or run.get("reference_dependency") is None
        for run in runs
    ):
        raise RuntimeError(f"V142 arm Random-prefix boundary changed: {arm_id}")


def _frozen_schedule(
    baselines: dict[str, Any], arms: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    lookup: dict[tuple[str, str, str], tuple[str, str]] = {}
    for run in baselines["runs"]:
        key = (scenario_id(run), run["seed"], run["method"])
        lookup[key] = ("baselines", run["run_id"])
    for arm_id, manifest in arms.items():
        for run in manifest["runs"]:
            key = (scenario_id(run), run["seed"], arm_id)
            lookup[key] = (arm_id, run["run_id"])

    rng = random.Random(RUN_ORDER_SEED)
    schedule: list[dict[str, Any]] = []
    block_orders: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        for seed in TRAINING_SEED_LIST:
            labels = list(METHOD_LABELS)
            rng.shuffle(labels)
            block_id = f"E3.{scenario}.{seed}"
            block_orders.append(
                {
                    "block_id": block_id,
                    "scenario": scenario,
                    "seed": seed,
                    "order": labels,
                }
            )
            for within_block_index, label in enumerate(labels, start=1):
                manifest_id, run_id = lookup[(scenario, seed, label)]
                schedule.append(
                    {
                        "ordinal": len(schedule) + 1,
                        "block_id": block_id,
                        "within_block_index": within_block_index,
                        "scenario": scenario,
                        "seed": seed,
                        "method_label": label,
                        "manifest_id": manifest_id,
                        "run_id": run_id,
                    }
                )
    if len(schedule) != 108 or len({item["run_id"] for item in schedule}) != 108:
        raise RuntimeError("V142 frozen run order is not an exact 108-run product")
    document = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_RUN_ORDER_V142_V1",
        "created_at": utc_now(),
        "performance_results_consulted": False,
        "run_order_seed": RUN_ORDER_SEED,
        "randomization_unit": "scenario_by_seed_complete_block",
        "method_labels": METHOD_LABELS,
        "block_orders": block_orders,
        "schedule": schedule,
    }
    document["schedule_hash"] = object_hash(document)
    return document


def prepare_v142(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V142 training root: {root}")
    root.mkdir(parents=True)
    output = paths(root)
    _write_config(output["config"])
    write_manifest(output["source"], output["config"], seed_stage="initial")
    source = json.loads(output["source"].read_text(encoding="utf-8"))
    validate_manifest(source)

    capture_ids = _selected_ids(
        source,
        lambda run: run["experiment_id"] == "E4"
        and run["method"] == "greedy"
        and run["seed"] in TRAINING_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced",
        3,
    )
    capture = derive_integration_smoke_shard(
        output["source"], capture_ids, purpose=f"V142 fresh parent tapes {PLAN_SHA256}"
    )
    write_json_atomic(output["capture"], _rewrite_capture(capture))

    baseline_ids = _selected_ids(
        source,
        lambda run: _is_training_e3(run) and run["method"] in BASELINE_METHOD_SET,
        81,
    )
    baseline_shard = derive_integration_smoke_shard(
        output["source"], baseline_ids, purpose=f"V142 baseline product {PLAN_SHA256}"
    )
    baselines = _rewrite_baselines(baseline_shard)
    write_json_atomic(output["baselines"], baselines)

    nash_ids = _selected_ids(
        source,
        lambda run: _is_training_e3(run) and run["method"] == "sche_nash",
        9,
    )
    model = verify_frozen_faasrank_model(MODEL_PATH)
    frozen_model_config = rust_faasrank_model_config(model)
    arm_manifests: dict[str, dict[str, Any]] = {}
    all_reference_keys: set[str] = set()
    for arm in ARMS:
        arm_id, _, _ = arm
        shard = derive_integration_smoke_shard(
            output["source"], nash_ids, purpose=f"V142 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite_arm(shard, arm, frozen_model_config)
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if len(keys) != 9 or all_reference_keys & keys:
            raise RuntimeError("V142 arm reference keys overlap or are incomplete")
        all_reference_keys.update(keys)
        arm_manifests[arm_id] = manifest
        write_json_atomic(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 27:
        raise RuntimeError("V142 must declare exactly 27 candidate references")

    schedule = _frozen_schedule(baselines, arm_manifests)
    write_json_atomic(output["schedule"], schedule)

    manifest_paths = [output["source"], output["capture"], output["baselines"]] + [
        arm_path(root, arm_id) for arm_id in ARM_IDS
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
        "schema_version": "NSE_E3_RANDOM_PREFIX_PREPARED_V142_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "v141_plan_path": str(V141_PLAN),
        "v141_plan_sha256": V141_PLAN_SHA256,
        "v141_prepared_path": str(V141_PREPARED),
        "v141_prepared_sha256": V141_PREPARED_SHA256,
        "v141_tape_catalog_path": str(V141_TAPE_CATALOG),
        "v141_tape_catalog_sha256": V141_TAPE_CATALOG_SHA256,
        "v141_failure_path": str(V141_FAILURE),
        "v141_failure_sha256": V141_FAILURE_SHA256,
        "v141_failure_hash": V141_FAILURE_HASH,
        "v141_disposition": "technical_reference_build_failure_before_online_execution_no_reveal",
        "v141_performance_summaries_parsed": 0,
        "v141_performance_results_consulted": False,
        "v141_online_runs_started": 0,
        "v141_online_runs_canonicalized": 0,
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
        "retired_unmaterialized_v137_confirmation_seeds": RETIRED_V137_CONFIRMATION_SEEDS,
        "retired_opened_v138_training_seeds": RETIRED_OPENED_V138_TRAINING_SEEDS,
        "retired_opened_v139_training_seeds": RETIRED_OPENED_V139_TRAINING_SEEDS,
        "retired_opened_v140_training_seeds": RETIRED_OPENED_V140_TRAINING_SEEDS,
        "retired_opened_v141_training_seeds": RETIRED_OPENED_V141_TRAINING_SEEDS,
        "sealed_new_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        "confirmation_inputs_generated": False,
        "base_tape_captures": 3,
        "derived_burst_tapes": 9,
        "baseline_online_runs": 81,
        "candidate_online_runs": 27,
        "total_online_runs": 108,
        "candidate_reference_builds": 27,
        "baseline_reference_builds": 0,
        "run_order_seed": RUN_ORDER_SEED,
        "frozen_schedule_path": str(output["schedule"]),
        "frozen_schedule_file_sha256": file_hash(output["schedule"]),
        "frozen_schedule_hash": schedule["schedule_hash"],
        "strictly_serial": True,
        "formal_E01_E20_reexecution": 0,
        "baseline_runs_by_method": dict(
            sorted(Counter(run["method"] for run in baselines["runs"]).items())
        ),
        "arms": [
            {
                "arm_id": arm_id,
                "profile": profile,
                "native_selection_rule": rule,
                "native_portfolio_enabled": rule != "exact_random_prefix",
                "native_portfolio_members": native_members(rule),
                "run_count": 9,
                "reference_build_count": 9,
            }
            for arm_id, profile, rule in ARMS
        ],
        "manifests": manifests,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def main() -> None:
    prepare_v142()


if __name__ == "__main__":
    main()
