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


ROOT = Path("tmp/nse_e3_all_native_portfolio_training_20260830_v140")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_all_native_portfolio_training_plan_v140.json"
)
PLAN_SHA256 = "483a337047fbf23063135cf389dcb85ecdd73d3050d14b022ba3a78137b1bb3f"

V139_PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_all_native_portfolio_training_plan_v139.json"
)
V139_PLAN_SHA256 = "e46f52a5da2d8106d17ab6acebeb3713d0f9fdd599cf92bed63e009481967922"
V139_PREPARED = Path(
    "tmp/nse_e3_all_native_portfolio_training_20260830_v139/"
    "prepared-manifests-v139.json"
)
V139_PREPARED_SHA256 = (
    "074eb4456f61eb1f24374d084569b996888714bd1a42977ddb47879fa9e8c314"
)
V139_TAPE_CATALOG = Path(
    "tmp/nse_e3_all_native_portfolio_training_20260830_v139/tapes.catalog.json"
)
V139_TAPE_CATALOG_SHA256 = (
    "e356b062571b69d5987f1913138cad1f628213288df0687591eb1fdffcf44f37"
)
V139_READY_SCHEDULE = Path(
    "tmp/nse_e3_all_native_portfolio_training_20260830_v139/"
    "frozen-ready-run-order-v139.json"
)
V139_READY_SCHEDULE_SHA256 = (
    "0f496d571b46c4ca684bf6525b7aeefdbb90eabf0d3a8c0ebeab58328f513062"
)
V139_EXECUTION_RECEIPT = Path(
    "tmp/nse_e3_all_native_portfolio_training_20260830_v139/"
    "execution-receipt-v139.json"
)
V139_EXECUTION_RECEIPT_SHA256 = (
    "1e068ef4c9bc10dbc8dc89d62209200bab0c6df81b9d50b1096f66dd8a73b918"
)
V139_FAILURE_RECEIPT = Path(
    "tmp/nse_e3_all_native_portfolio_training_20260830_v139/"
    "blind-audit-failure-v139.json"
)
V139_FAILURE_RECEIPT_SHA256 = (
    "eab2003525ba841487459d3d204fe5793c51f9e6a95ea5a17746eb15f9994b27"
)

BINARY_PATH = Path("tmp/nse_v140_build_581fad1/release/serverless_sim.exe")
BINARY_SHA256 = "ee1770439999eeee537a8d67098d1015064929a77e5599977b0639a3f19e2a35"
BINARY_SOURCE_COMMIT = "581fad1b5763d05f1f46856692a1152e3925682b"

TRAINING_SEED_LIST = ["E1520", "E1521", "E1522"]
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
NEW_CONFIRMATION_SEEDS = [f"E{index}" for index in range(1497, 1517)]
FORBIDDEN_SOURCE_SEEDS = set(
    RETIRED_V137_CONFIRMATION_SEEDS
    + RETIRED_OPENED_V138_TRAINING_SEEDS
    + RETIRED_OPENED_V139_TRAINING_SEEDS
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
        "v140-e3-all-native-minimax-service-portfolio-nash",
        "all_native_portfolio_minimax_service_nash",
        "minimax_service",
    ),
    (
        "v140-e3-all-native-minsum-service-portfolio-nash",
        "all_native_portfolio_minsum_service_nash",
        "minsum_service",
    ),
    (
        "v140-e3-all-native-service-welfare-borda-portfolio-nash",
        "all_native_portfolio_service_welfare_borda_nash",
        "service_welfare_borda",
    ),
)
ARM_IDS = [item[0] for item in ARMS]
METHOD_LABELS = BASELINE_METHODS + ARM_IDS
RUN_ORDER_SEED = "NSE-V140-RCBD-E1520-E1522"
PORT = "3169"


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
        "config": root / "v140-e3-training-config.json",
        "source": root / "manifest.v140-training-source-full.unbound.json",
        "capture": root / "manifest.v140-tape-capture.unbound.json",
        "baselines": root / "manifest.v140-baselines.unbound.json",
        "prepared": root / "prepared-manifests-v140.json",
        "schedule": root / "frozen-run-order-v140.json",
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
        (V139_PLAN, V139_PLAN_SHA256),
        (V139_PREPARED, V139_PREPARED_SHA256),
        (V139_TAPE_CATALOG, V139_TAPE_CATALOG_SHA256),
        (V139_READY_SCHEDULE, V139_READY_SCHEDULE_SHA256),
        (V139_EXECUTION_RECEIPT, V139_EXECUTION_RECEIPT_SHA256),
        (V139_FAILURE_RECEIPT, V139_FAILURE_RECEIPT_SHA256),
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
            raise RuntimeError(f"frozen V140 input is missing or changed: {path}")
    _assert_hashed_object(V139_PREPARED, "receipt_hash")
    _assert_hashed_object(V139_TAPE_CATALOG, "catalog_hash")
    _assert_hashed_object(V139_READY_SCHEDULE, "schedule_hash")
    _assert_hashed_object(V139_EXECUTION_RECEIPT, "receipt_hash")
    _assert_hashed_object(V139_FAILURE_RECEIPT, "failure_hash")
    execution = json.loads(V139_EXECUTION_RECEIPT.read_text(encoding="utf-8"))
    failure = json.loads(V139_FAILURE_RECEIPT.read_text(encoding="utf-8"))
    if (
        execution.get("performance_results_consulted") is not False
        or execution.get("dispatch_count") != 108
        or failure.get("status") != "technical_audit_failure_before_reveal"
        or failure.get("performance_summaries_parsed") != 0
        or failure.get("performance_results_consulted") is not False
        or failure.get("reveal_authorized") is not False
        or failure.get("run_count_completed_qc_pass") != 108
        or failure.get("quarantine_count") != 0
    ):
        raise RuntimeError("V139 pre-reveal technical disposition changed")


def _write_config(path: Path) -> None:
    if FORBIDDEN_SOURCE_SEEDS & set(SOURCE_INITIAL_SEEDS + SOURCE_CI_SEEDS):
        raise RuntimeError("V140 source seed policy reuses a retired or sealed seed")
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
            "v140_training_plan_sha256": PLAN_SHA256,
            "v140_training_only": True,
            "v140_binary_source_commit": BINARY_SOURCE_COMMIT,
            "selected_development_seeds": TRAINING_SEED_LIST,
            "retired_unmaterialized_v137_confirmation_seeds": RETIRED_V137_CONFIRMATION_SEEDS,
            "retired_opened_v138_training_seeds": RETIRED_OPENED_V138_TRAINING_SEEDS,
            "retired_opened_v139_training_seeds": RETIRED_OPENED_V139_TRAINING_SEEDS,
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
    marker = _base_marker(rewritten, f"V140 fresh parent tapes {PLAN_SHA256}")
    marker["v140_role"] = "fresh_parent_tape_capture"
    for run in rewritten["runs"]:
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run.setdefault("metadata", {}).update(
            {
                "v140_training_plan_sha256": PLAN_SHA256,
                "v140_training_only": True,
                "v140_confirmation_inputs_opened": False,
            }
        )
        _assign_run_identity(run)
    return _finalize(rewritten)


def _rewrite_baselines(shard: dict[str, Any]) -> dict[str, Any]:
    rewritten = copy.deepcopy(shard)
    marker = _base_marker(rewritten, f"V140 complete baseline product {PLAN_SHA256}")
    marker.update(
        {
            "v140_role": "paper_baseline",
            "v140_expected_run_count": 81,
            "v140_expected_reference_count": 0,
            "v140_baseline_methods": BASELINE_METHODS,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = "v140-complete-paper-baselines"
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run.setdefault("metadata", {}).update(
            {
                "v140_training_plan_sha256": PLAN_SHA256,
                "v140_training_only": True,
                "v140_role": "paper_baseline",
                "v140_source_run_id": source_run_id,
                "v140_source_run_spec_hash": source_run_spec_hash,
                "v140_performance_consulted_before_execution": False,
                "v140_confirmation_inputs_opened": False,
                "v140_outcome_fields_drive_policy": False,
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
    arm_id, profile, portfolio_rule = arm
    rewritten = copy.deepcopy(shard)
    marker = _base_marker(rewritten, f"V140 {arm_id} {PLAN_SHA256}")
    marker.update(
        {
            "v140_role": "candidate",
            "v140_arm_id": arm_id,
            "v140_profile": profile,
            "v140_native_portfolio_rule": portfolio_rule,
            "v140_native_portfolio_members": [
                "greedy",
                "hiku",
                "jiagu",
                "orion",
                "load_least",
            ],
            "v140_expected_run_count": 9,
            "v140_expected_reference_count": 9,
            "v140_native_shadow_exactness_required": True,
            "v140_all_player_service_certificate_required": True,
            "v140_service_certificate_state_domain": "runtime_existing_aggregates_and_admitted_work",
            "v140_paper_welfare_state_domain": "empty_window_aggregates",
            "v140_selected_welfare_equals_guard_initializer_required": True,
            "v140_outcome_fields_drive_policy": False,
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
                "v140_training_plan_sha256": PLAN_SHA256,
                "v140_training_only": True,
                "v140_role": "candidate",
                "v140_arm_id": arm_id,
                "v140_profile": profile,
                "v140_native_portfolio_rule": portfolio_rule,
                "v140_native_portfolio_members": [
                    "greedy",
                    "hiku",
                    "jiagu",
                    "orion",
                    "load_least",
                ],
                "v140_source_run_id": source_run_id,
                "v140_source_run_spec_hash": source_run_spec_hash,
                "v140_native_shadow_exactness_required": True,
                "v140_all_native_members_use_all_frontier": True,
                "v140_selected_player_order_from_native_shadow": True,
                "v140_all_player_service_complete_assignment_required": True,
                "v140_service_certificate_state_domain": "runtime_existing_aggregates_and_admitted_work",
                "v140_paper_welfare_state_domain": "empty_window_aggregates",
                "v140_selected_welfare_equals_guard_initializer_required": True,
                "v140_all_player_service_sum_strictly_lower": True,
                "v140_all_player_service_max_nonincreasing": True,
                "v140_immutable_baseline_welfare_nonworse": True,
                "v140_no_numeric_tuning": True,
                "v140_outcome_fields_drive_policy": False,
                "v140_scenario_or_burst_label_used_by_policy": False,
                "v140_future_arrivals_used_by_policy": False,
                "v140_confirmation_inputs_opened": False,
            }
        )
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"]["table_path"] = run[
            "reference_dependency"
        ]["path"]
        _assign_run_identity(run)
    _validate_arm_product(rewritten["runs"], arm_id, profile, portfolio_rule)
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
        raise RuntimeError("V140 baseline method/scenario/seed product changed")
    if any(run.get("reference_dependency") is not None for run in runs):
        raise RuntimeError("V140 baseline product unexpectedly requires references")


def _validate_arm_product(
    runs: list[dict[str, Any]], arm_id: str, profile: str, portfolio_rule: str
) -> None:
    expected = {
        (scenario, seed) for scenario in SCENARIOS for seed in TRAINING_SEED_LIST
    }
    actual = {(scenario_id(run), run["seed"]) for run in runs}
    if len(runs) != 9 or actual != expected:
        raise RuntimeError(f"V140 arm product changed: {arm_id}")
    if {run["method"] for run in runs} != {"sche_nash"}:
        raise RuntimeError(f"V140 arm method changed: {arm_id}")
    if {run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") for run in runs} != {
        profile
    }:
        raise RuntimeError(f"V140 arm profile changed: {arm_id}")
    if any(
        run.get("metadata", {}).get("v140_native_portfolio_rule") != portfolio_rule
        or run.get("metadata", {}).get("v140_native_portfolio_members")
        != ["greedy", "hiku", "jiagu", "orion", "load_least"]
        or run.get("metadata", {}).get("v140_all_native_members_use_all_frontier")
        is not True
        or run.get("metadata", {}).get("v140_service_certificate_state_domain")
        != "runtime_existing_aggregates_and_admitted_work"
        or run.get("metadata", {}).get("v140_paper_welfare_state_domain")
        != "empty_window_aggregates"
        or run.get("metadata", {}).get(
            "v140_selected_welfare_equals_guard_initializer_required"
        )
        is not True
        or run.get("metadata", {}).get("v140_outcome_fields_drive_policy") is not False
        or run.get("reference_dependency") is None
        for run in runs
    ):
        raise RuntimeError(f"V140 arm portfolio boundary changed: {arm_id}")


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
        raise RuntimeError("V140 frozen run order is not an exact 108-run product")
    document = {
        "schema_version": "NSE_E3_ALL_NATIVE_PORTFOLIO_RUN_ORDER_V140_V1",
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


def prepare_v140(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V140 training root: {root}")
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
        output["source"], capture_ids, purpose=f"V140 fresh parent tapes {PLAN_SHA256}"
    )
    write_json_atomic(output["capture"], _rewrite_capture(capture))

    baseline_ids = _selected_ids(
        source,
        lambda run: _is_training_e3(run) and run["method"] in BASELINE_METHOD_SET,
        81,
    )
    baseline_shard = derive_integration_smoke_shard(
        output["source"], baseline_ids, purpose=f"V140 baseline product {PLAN_SHA256}"
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
            output["source"], nash_ids, purpose=f"V140 {arm_id} {PLAN_SHA256}"
        )
        manifest = _rewrite_arm(shard, arm, frozen_model_config)
        keys = {item["key"] for item in manifest["reference_build_dependencies"]}
        if len(keys) != 9 or all_reference_keys & keys:
            raise RuntimeError("V140 arm reference keys overlap or are incomplete")
        all_reference_keys.update(keys)
        arm_manifests[arm_id] = manifest
        write_json_atomic(arm_path(root, arm_id), manifest)
    if len(all_reference_keys) != 27:
        raise RuntimeError("V140 must declare exactly 27 candidate references")

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
        "schema_version": "NSE_E3_ALL_NATIVE_PORTFOLIO_PREPARED_V140_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "v139_plan_path": str(V139_PLAN),
        "v139_plan_sha256": V139_PLAN_SHA256,
        "v139_prepared_path": str(V139_PREPARED),
        "v139_prepared_sha256": V139_PREPARED_SHA256,
        "v139_tape_catalog_path": str(V139_TAPE_CATALOG),
        "v139_tape_catalog_sha256": V139_TAPE_CATALOG_SHA256,
        "v139_ready_schedule_path": str(V139_READY_SCHEDULE),
        "v139_ready_schedule_sha256": V139_READY_SCHEDULE_SHA256,
        "v139_execution_receipt_path": str(V139_EXECUTION_RECEIPT),
        "v139_execution_receipt_sha256": V139_EXECUTION_RECEIPT_SHA256,
        "v139_failure_receipt_path": str(V139_FAILURE_RECEIPT),
        "v139_failure_receipt_sha256": V139_FAILURE_RECEIPT_SHA256,
        "v139_disposition": "aborted_pre_reveal_technical_audit_failure_retained",
        "v139_performance_summaries_parsed": 0,
        "v139_performance_results_consulted": False,
        "v139_reveal_authorized": False,
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
                "native_portfolio_rule": rule,
                "native_portfolio_members": [
                    "greedy",
                    "hiku",
                    "jiagu",
                    "orion",
                    "load_least",
                ],
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
    prepare_v140()


if __name__ == "__main__":
    main()
