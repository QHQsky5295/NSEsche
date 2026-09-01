from __future__ import annotations

import argparse
import copy
import json
import math
import subprocess
from pathlib import Path
from statistics import NormalDist
from typing import Any, Mapping, Sequence

import numpy as np

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.analysis.stats import bca_interval
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_queue8_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_equivalence_complete_training_v182 as v182,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
    write_manifest,
)
from scripts.reviewer_experiments.protocol.runner import ProtocolRunner
from scripts.reviewer_experiments.protocol.schema import (
    load_and_validate_manifest,
    validate_manifest,
)
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


ROOT = Path(
    "tmp/nse_e1_homogeneous_20node_low_disjoint_unpaired_confirmation_20260901_v184"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_disjoint_unpaired_confirmation_plan_v184.json"
)
PLAN_SHA256 = "4227414cb5ec2d1e05693844bcb20cab84e01d07391dd6140e4913f00b5220cc"
PLAN_COMMIT = "8e1e3ef10f3b96b1525be31d53e84800db1908a9"
TRAINING_FREEZE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_training_freeze_v182.json"
)
TRAINING_FREEZE_SHA256 = (
    "c3a057dea5f573877d9e5df48f574c7b8663435fa4d4904443a2f69f375f95d5"
)
TRAINING_FREEZE_HASH = (
    "fdcbeae643d6081a91240201e741516cb0691795f1a3591416224530731a9ace"
)
IMPLEMENTATION_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_disjoint_unpaired_confirmation_implementation_v184.json"
)
FAILURE_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_fresh_seed_confirmation_failure_v183.json"
)
FAILURE_RECEIPT_FILE_SHA256 = (
    "2dd8f04977b68cde0379a1f7786f37fddba299d0e67da1ebac565cae0e4286b8"
)
FAILURE_RECEIPT_HASH = (
    "ed2cdb179f8020f44ff2ed9019ea3259e082fe1c920b30ee6a22f23c1ad2c409"
)
COMPLETE_TRAINING_RESULT = Path(
    "tmp/nse_e1_homogeneous_concurrent2_queue8_cpu_bounded_terminal_"
    "equivalence_complete_training_20260901_v182/complete-training-result-v182.json"
)
COMPLETE_TRAINING_RESULT_SHA256 = (
    "55881187b98f1b2f15d7106068705d004e6560b8ca57cc644396e2393515bf3f"
)
COMPLETE_TRAINING_RESULT_HASH = (
    "01cbcc58ff124e5a219d85b2d18411c2098d7f0201aaff6d9c0ec3b00ce2538d"
)
GOAL = Path(
    "C:/Users/99349/.codex/attachments/"
    "5ee79c4a-1c9c-4f97-9be0-02aace1da755/goal-objective.md"
)
GOAL_SHA256 = "030aa0c13427ae53aef822d7743a7601b3b4530aae5f9858bdebe8fb7bebd864"
DEFAULT_CONFIG = Path("scripts/reviewer_experiments/protocol/default_protocol.json")
DEFAULT_CONFIG_SHA256 = (
    "121d217b4c404c5fbb882c34ed684824b8bd1299d19e92e0f0d82fe8a53b85a2"
)
MODULE = Path(__file__)
TEST = Path(
    "scripts/reviewer_experiments/protocol/tests/"
    "test_nse_e1_low_confirmation_v184.py"
)

SEEDS = tuple(f"E{index}" for index in range(1590, 1610))
METHODS = ("sche_orion", "sche_OCS", "sche_nash")
EXECUTION_METHODS = ("sche_nash",)
PRIMARY = {
    "throughput_requests_per_ms": "sche_orion",
    "qpr_finite_only": "sche_OCS",
    "qpr_zero_completed_as_zero": "sche_OCS",
}
METRICS = tuple(PRIMARY)
FROZEN_BASELINES = {
    "throughput_requests_per_ms": {
        "method": "sche_orion",
        "mean": 1.4741,
    },
    "qpr_finite_only": {
        "method": "sche_OCS",
        "mean": 0.055577160345697,
    },
    "qpr_zero_completed_as_zero": {
        "method": "sche_OCS",
        "mean": 0.055577160345697,
    },
}
PROFILE = v182.PROFILE
FRONTIER = v182.FRONTIER
PORT = "3211"
BINARY_PATH = Path("serverless_sim/target_e1_v182/release/serverless_sim.exe")
BINARY_SHA256 = "0e5f555d3709d530f3984c3a973443d3fd37192fc907d9a0122f21fd3c5cde8a"
BINARY_BYTES = 5_903_872
BINARY_SOURCE_COMMIT = "95b3bd078355c7674244e7b2a79bd0433b47bb2c"
SCHEDULER_SOURCE = Path("serverless_sim/src/sche/sche_nash.rs")
SCHEDULER_SOURCE_SHA256 = (
    "e5e9879d6e15d73033a281d76982e54d120691c47ff41075dff320b7256afaa2"
)
PYTHON_PATH = Path("D:/Anaconda3/python.exe")
PYTHON_SHA256 = "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
CARGO_LOCK = Path("serverless_sim/Cargo.lock")
CARGO_LOCK_SHA256 = "17fe8bce08ba31f9edda8e6e331641cb7d981c1c9f1e21e7bf09178da6dd3205"
MODULE_CONF = Path("serverless_sim/module_conf_es.json")
MODULE_CONF_SEMANTIC_HASH = (
    "752e521c15ec7a84d2e11a7f73ffd86241a9ad56638964210c30d2c709662877"
)


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "config": root / "confirmation-config-v184.json",
        "source": root / "manifest.full-source.unbound.json",
        "manifest": root / "manifest.confirmation.unbound.json",
        "prepared": root / "prepared-v184.json",
        "schedule": root / "frozen-run-order-v184.json",
        "tape_workspace": root / "tape-stage",
        "tape_catalog": root / "tapes.catalog.json",
        "tapes": root / "manifest.confirmation.tapes.json",
        "tape_execution": root / "tape-execution-receipt-v184.json",
        "reference_workspace": root / "reference-stage",
        "reference_catalog": root / "references.catalog.json",
        "ready": root / "manifest.confirmation.ready.json",
        "reference_execution": root / "reference-execution-receipt-v184.json",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v184.json",
        "pairing": root / "candidate-inventory-audit-v184.json",
        "blind": root / "joint-blind-audit-v184.json",
        "result": root / "confirmation-result-v184.json",
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected: str, label: str) -> None:
    _require(path.is_file(), f"missing {label}: {path}")
    _require(file_hash(path) == expected, f"changed {label}: {path}")


def _assert_hashed(document: Mapping[str, Any], key: str, label: str) -> str:
    payload = dict(document)
    claimed = payload.pop(key, None)
    _require(isinstance(claimed, str), f"{label} lacks {key}")
    _require(object_hash(payload) == claimed, f"{label} self-hash changed")
    return claimed


def _reread_goal() -> None:
    _assert_file(GOAL, GOAL_SHA256, "goal objective")


def _assert_plan_and_training() -> dict[str, Any]:
    _assert_file(PLAN, PLAN_SHA256, "V184 confirmation plan")
    _assert_file(TRAINING_FREEZE, TRAINING_FREEZE_SHA256, "V182 training freeze")
    _assert_file(FAILURE_RECEIPT, FAILURE_RECEIPT_FILE_SHA256, "V183 failure receipt")
    _assert_file(
        COMPLETE_TRAINING_RESULT,
        COMPLETE_TRAINING_RESULT_SHA256,
        "V182 complete training result",
    )
    plan = read_json(PLAN)
    freeze = read_json(TRAINING_FREEZE)
    failure = read_json(FAILURE_RECEIPT)
    training_result = read_json(COMPLETE_TRAINING_RESULT)
    _require(
        plan.get("status")
        == "preregistered_before_E1590_E1609_input_manifest_tape_reference_or_online_generation",
        "V184 plan is not preregistered before inputs",
    )
    _require(
        tuple(plan["scientific_boundary"]["confirmation_seeds"]) == SEEDS
        and plan["pre_input_state"]
        == {
            "root_exists": False,
            "generated_E1590_E1609_run_specs": 0,
            "captured_E1590_E1609_tapes": 0,
            "built_E1590_E1609_references": 0,
            "E1590_E1609_online_runs": 0,
            "E1590_E1609_performance_values_read": 0,
        },
        "V184 seed or pre-input boundary changed",
    )
    _require(
        _assert_hashed(freeze, "receipt_hash", "V182 training freeze")
        == TRAINING_FREEZE_HASH
        and freeze.get("status")
        == "complete_twenty_seed_training_pass_frozen_pending_fresh_seed_confirmation"
        and freeze.get("performance_gates", {}).get("joint_training_gate_pass") is True
        and freeze.get("paper_superiority_claim_authorized") is False,
        "V182 training freeze does not authorize independent confirmation",
    )
    frozen = plan["frozen_baseline_evidence"]
    _require(
        plan["frozen_candidate"]["training_freeze_file_sha256"]
        == TRAINING_FREEZE_SHA256
        and plan["frozen_candidate"]["training_freeze_receipt_hash"]
        == TRAINING_FREEZE_HASH
        and frozen["throughput_primary"]
        == {
            "method": FROZEN_BASELINES["throughput_requests_per_ms"]["method"],
            "mean_requests_per_ms": FROZEN_BASELINES["throughput_requests_per_ms"][
                "mean"
            ],
        }
        and frozen["qpr_primary"]
        == {
            "method": FROZEN_BASELINES["qpr_finite_only"]["method"],
            "finite_only_mean": FROZEN_BASELINES["qpr_finite_only"]["mean"],
            "zero_completed_as_zero_mean": FROZEN_BASELINES[
                "qpr_zero_completed_as_zero"
            ]["mean"],
        }
        and frozen["baseline_online_reruns_authorized"] == 0,
        "V184 frozen baseline evidence changed",
    )
    _require(
        _assert_hashed(failure, "receipt_hash", "V183 failure receipt")
        == FAILURE_RECEIPT_HASH
        and failure.get("status")
        == "complete_fresh_seed_confirmation_failed_preregistered_consistency_gate"
        and failure.get("disposition", {}).get("retain_complete_E1570_E1589_cohort")
        is True,
        "V183 complete failure evidence changed",
    )
    _require(
        _assert_hashed(training_result, "result_hash", "V182 training result")
        == COMPLETE_TRAINING_RESULT_HASH,
        "V182 complete training result hash changed",
    )
    return plan


def _assert_frozen_inputs() -> dict[str, Any]:
    plan = _assert_plan_and_training()
    for path, expected, label in (
        (GOAL, GOAL_SHA256, "goal objective"),
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256, "default protocol"),
        (BINARY_PATH, BINARY_SHA256, "V182 binary"),
        (SCHEDULER_SOURCE, SCHEDULER_SOURCE_SHA256, "frozen scheduler source"),
        (PYTHON_PATH, PYTHON_SHA256, "Python executable"),
        (CARGO_LOCK, CARGO_LOCK_SHA256, "Cargo.lock"),
    ):
        _assert_file(path, expected, label)
    _require(BINARY_PATH.stat().st_size == BINARY_BYTES, "V182 binary size changed")
    v182.v181._assert_json_semantic(
        MODULE_CONF, MODULE_CONF_SEMANTIC_HASH, "module_conf_es.json"
    )
    _require(IMPLEMENTATION_RECEIPT.is_file(), "V184 implementation receipt missing")
    implementation = read_json(IMPLEMENTATION_RECEIPT)
    _assert_hashed(implementation, "receipt_hash", "V184 implementation receipt")
    _require(
        implementation.get("plan_sha256") == PLAN_SHA256
        and implementation.get("module_sha256") == file_hash(MODULE)
        and implementation.get("test_sha256") == file_hash(TEST)
        and implementation.get("candidate_rust_changed") is False
        and implementation.get("confirmation_inputs_generated_at_seal") == 0,
        "V184 implementation receipt does not bind this harness",
    )
    return plan


def _write_config(path: Path, seeds: Sequence[str]) -> None:
    _require(len(seeds) == 20 and len(set(seeds)) == 20, "V184 requires 20 seeds")
    config = read_json(DEFAULT_CONFIG)
    config["seed_policy"] = {
        "initial": list(seeds[:10]),
        "ci_extension": list(seeds[10:]),
        "ci_extension_requires_trigger": True,
        "e7_initial": list(seeds[:5]),
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


def _selected(run: Mapping[str, Any], seeds: set[str]) -> bool:
    workload = run.get("workload", {})
    cluster = run.get("cluster")
    return (
        run.get("experiment_id") == "E1"
        and run.get("method") in METHODS
        and run.get("seed") in seeds
        and workload.get("request_freq") == "low"
        and workload.get("arrival_profile") == "steady"
        and workload.get("topology") == "homogeneous"
        and workload.get("qos_profile") == "mixed"
        and cluster == {"node_count": 20, "topology": "homogeneous"}
    )


def _rewrite_confirmation(
    shard: dict[str, Any], seeds: Sequence[str], protocol_commit: str
) -> dict[str, Any]:
    source_lineage = {
        (item["source_method"], item["source_seed"]): copy.deepcopy(item)
        for item in shard["integration_smoke_shard"]["selected_source_runs"]
    }
    by_key = {(run["method"], run["seed"]): run for run in shard["runs"]}
    expected = {(method, seed) for method in METHODS for seed in seeds}
    _require(set(by_key) == expected, "V184 selected source product is not 3x20")
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    rewritten["runs"] = []
    lineage = []
    for method in METHODS:
        for seed in seeds:
            run = copy.deepcopy(by_key[(method, seed)])
            source_run_id = run["run_id"]
            source_spec_hash = run["run_spec_hash"]
            run["environment"]["SERVERLESS_SIM_PORT"] = PORT
            metadata = run.setdefault("metadata", {})
            metadata.update(
                {
                    "v184_confirmation_only": True,
                    "v184_plan_sha256": PLAN_SHA256,
                    "v184_plan_commit": PLAN_COMMIT,
                    "v184_protocol_source_commit": protocol_commit,
                    "v184_training_rows_pooled": False,
                    "v184_performance_fields_parsed_before_run": 0,
                    "v184_seed_replacement_or_selective_rerun": False,
                    "v184_fixed_method_order": list(METHODS),
                }
            )
            if method == "sche_nash":
                run["variant"] = "homogeneous-20node-low-frozen-v182-confirmation"
                run["environment"].update(v182.v181.COMMON_ENVIRONMENT)
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
                metadata.update(
                    {
                        "v184_frozen_candidate": True,
                        "v184_profile": PROFILE,
                        "v184_player_frontier": FRONTIER,
                        "v184_binary_source_commit": BINARY_SOURCE_COMMIT,
                        "v184_binary_sha256": BINARY_SHA256,
                    }
                )
                run["reference_dependency"] = _reference_dependency(run)
                run["simulator_experiment"]["reference"] = {
                    "mode": "offline_required",
                    "table_path": run["reference_dependency"]["path"],
                    "build_output_path": "",
                }
            else:
                run[
                    "variant"
                ] = f"v184-fresh-seed-{method.removeprefix('sche_').lower()}-control"
                metadata["v184_frozen_baseline"] = True
                # Tape binding uses field presence to identify runs that need
                # a tape-keyed offline reference.  Baselines therefore omit
                # the field entirely instead of carrying JSON null.
                run.pop("reference_dependency", None)
                run["simulator_experiment"]["reference"] = {
                    "mode": "sa_fallback",
                    "table_path": "",
                    "build_output_path": "",
                }
            _assign_run_identity(run)
            rewritten["runs"].append(run)
            lineage.append(
                {
                    "source_run_id": source_run_id,
                    "source_run_spec_hash": source_spec_hash,
                    "confirmation_run_id": run["run_id"],
                    "confirmation_run_spec_hash": run["run_spec_hash"],
                    "method": method,
                    "seed": seed,
                }
            )
    marker = rewritten["integration_smoke_shard"]
    marker["purpose"] = (
        "V184 preregistered E1590-E1609 independent confirmation; "
        "complete cohort only, never a training subset"
    )
    marker["selected_source_runs"] = [
        source_lineage[(method, seed)] for method in METHODS for seed in seeds
    ]
    marker.update(
        {
            "v184_confirmation_plan_sha256": PLAN_SHA256,
            "v184_confirmation_only": True,
            "v184_training_rows_pooled": False,
            "v184_selected_seeds": list(seeds),
            "v184_fixed_methods": list(METHODS),
            "v184_fixed_run_order": [
                {"method": method, "seed": seed} for method in METHODS for seed in seeds
            ],
            "v184_source_to_confirmation_lineage": lineage,
            "v184_expected_base_tapes": len(seeds),
            "v184_expected_references": len(seeds),
            "v184_expected_online_runs": len(seeds) * len(METHODS),
            "formal_results_eligible": False,
            "paper_superiority_claim_eligible_if_joint_gate_passes": True,
        }
    )
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
    _validate_product(rewritten, seeds, tapes_bound=False, references_bound=False)
    return rewritten


def _validate_product(
    manifest: Mapping[str, Any],
    seeds: Sequence[str] = SEEDS,
    *,
    tapes_bound: bool,
    references_bound: bool,
) -> None:
    expected_order = [(method, seed) for method in METHODS for seed in seeds]
    actual_order = [(run["method"], run["seed"]) for run in manifest.get("runs", [])]
    _require(
        actual_order == expected_order, "V184 run order or exact 3x20 product changed"
    )
    _require(
        len(manifest.get("reference_build_dependencies", [])) == len(seeds),
        "V184 requires exactly one Nash reference per seed",
    )
    _require(
        bool(manifest.get("all_tapes_bound", False)) is tapes_bound
        and bool(manifest.get("all_references_bound", False)) is references_bound,
        "V184 binding state changed",
    )
    by_seed: dict[str, list[Mapping[str, Any]]] = {seed: [] for seed in seeds}
    for run in manifest["runs"]:
        by_seed[run["seed"]].append(run)
        _require(_selected(run, set(seeds)), f"V184 run escaped scope: {run['run_id']}")
        _require(
            run["environment"].get("SERVERLESS_SIM_PORT") == PORT,
            "V184 isolated port changed",
        )
        if run["method"] == "sche_nash":
            _require(
                run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") == PROFILE
                and run["metadata"].get("v184_frozen_candidate") is True,
                "V184 frozen candidate changed",
            )
    for seed, runs in by_seed.items():
        keys = {run["workload_tape"]["key"] for run in runs}
        _require(len(keys) == 1, f"V184 {seed} does not share one tape key")
        if tapes_bound:
            hashes = {run["workload_tape"]["sha256"] for run in runs}
            _require(
                len(hashes) == 1 and None not in hashes, f"V184 {seed} tape mismatch"
            )


def _build_unbound_product(
    root: Path,
    seeds: Sequence[str],
    protocol_commit: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output = paths(root)
    _write_config(output["config"], seeds)
    write_manifest(output["source"], output["config"], seed_stage="all")
    source = load_and_validate_manifest(output["source"])
    seed_set = set(seeds)
    selected = [run for run in source["runs"] if _selected(run, seed_set)]
    _require(
        len(selected) == len(seeds) * len(METHODS), "V184 source selection changed"
    )
    shard = derive_integration_smoke_shard(
        output["source"],
        [run["run_id"] for run in selected],
        purpose="V184 independent homogeneous-low fresh-seed confirmation",
    )
    rewritten = _rewrite_confirmation(shard, seeds, protocol_commit)
    write_json_atomic(output["manifest"], rewritten)
    return source, rewritten


def prepare_v184(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    _require(not root.exists(), f"refusing to overwrite V184 root: {root}")
    root.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source, manifest = _build_unbound_product(root, SEEDS, commit)
    output = paths(root)
    schedule = {
        "schema_version": "NSE_E1_LOW_FRESH_CONFIRMATION_SCHEDULE_V184_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "capture_order": list(SEEDS),
        "reference_order": list(SEEDS),
        "online_order": [{"method": "sche_nash", "seed": seed} for seed in SEEDS],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    implementation = read_json(IMPLEMENTATION_RECEIPT)
    receipt = {
        "schema_version": "NSE_E1_LOW_FRESH_CONFIRMATION_PREPARED_V184_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "paper_superiority_claim_eligible_if_joint_gate_passes": True,
        "goal_objective_sha256": GOAL_SHA256,
        "plan_sha256": PLAN_SHA256,
        "implementation_receipt_hash": implementation["receipt_hash"],
        "protocol_source_commit": commit,
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": MODULE_CONF_SEMANTIC_HASH,
        "confirmation_seeds": list(SEEDS),
        "manifest_methods": list(METHODS),
        "execution_methods": list(EXECUTION_METHODS),
        "source_manifest_path": str(output["source"]),
        "source_manifest_hash": source["manifest_hash"],
        "source_manifest_file_sha256": file_hash(output["source"]),
        "manifest_path": str(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "manifest_file_sha256": file_hash(output["manifest"]),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "fresh_base_tapes": 20,
        "candidate_references": 20,
        "online_runs": 20,
        "performance_fields_parsed": 0,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def _run_logged(command: Sequence[str], stdout: Path, stderr: Path, label: str) -> None:
    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open("w", encoding="utf-8") as out, stderr.open(
        "w", encoding="utf-8"
    ) as err:
        completed = subprocess.run(
            list(command), cwd=Path.cwd(), stdout=out, stderr=err, check=False
        )
    _require(completed.returncode == 0, f"{label} failed: {completed.returncode}")


def capture_and_bind_tapes_v184(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifest = load_and_validate_manifest(output["manifest"])
    _validate_product(manifest, tapes_bound=False, references_bound=False)
    by_seed = {seed: set() for seed in SEEDS}
    for run in manifest["runs"]:
        by_seed[run["seed"]].add(run["workload_tape"]["key"])
    logs = root / "tape-execution-logs"
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        _require(len(by_seed[seed]) == 1, f"V184 {seed} tape key is not unique")
        key = next(iter(by_seed[seed]))
        stdout = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{seed}.stderr.log"
        _reread_goal()
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "capture-base-tapes",
                str(output["manifest"]),
                str(output["tape_workspace"]),
                str(output["tape_catalog"]),
                "--key",
                key,
            ],
            stdout,
            stderr,
            f"V184 tape capture {seed}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "key": key,
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    _run_logged(
        [
            str(PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "bind-tapes",
            str(output["manifest"]),
            str(output["tape_catalog"]),
            str(output["tapes"]),
        ],
        logs / "bind.stdout.log",
        logs / "bind.stderr.log",
        "V184 tape binding",
    )
    bound = load_and_validate_manifest(output["tapes"])
    _validate_product(bound, tapes_bound=True, references_bound=False)
    catalog = read_json(output["tape_catalog"])
    _require(len(catalog.get("entries", {})) == 20, "V184 tape catalog is not 20")
    ledger_count, ledger_hash = verify_ledger(
        output["tape_workspace"] / "capture_base_tapes" / "ledger.jsonl"
    )
    receipt = {
        "schema_version": "NSE_E1_LOW_FRESH_CONFIRMATION_TAPES_V184_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_capture": True,
        "performance_fields_parsed": 0,
        "dispatches": dispatches,
        "catalog_file_sha256": file_hash(output["tape_catalog"]),
        "catalog_entry_count": 20,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "bound_manifest_hash": bound["manifest_hash"],
        "bound_manifest_file_sha256": file_hash(output["tapes"]),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["tape_execution"], receipt)
    return receipt


def build_references_v184(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifest = load_and_validate_manifest(output["tapes"])
    _validate_product(manifest, tapes_bound=True, references_bound=False)
    candidates = {
        run["seed"]: run for run in manifest["runs"] if run["method"] == "sche_nash"
    }
    _require(set(candidates) == set(SEEDS), "V184 candidate reference set changed")
    logs = root / "reference-execution-logs"
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = candidates[seed]
        stdout = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{seed}.stderr.log"
        _reread_goal()
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "build-references",
                str(output["tapes"]),
                str(output["reference_workspace"]),
                str(output["reference_catalog"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V184 reference {seed}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    _run_logged(
        [
            str(PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "bind-references",
            str(output["tapes"]),
            str(output["reference_catalog"]),
            str(output["ready"]),
        ],
        logs / "bind.stdout.log",
        logs / "bind.stderr.log",
        "V184 reference binding",
    )
    ready = load_and_validate_manifest(output["ready"])
    _validate_product(ready, tapes_bound=True, references_bound=True)
    catalog = read_json(output["reference_catalog"])
    _require(len(catalog.get("entries", {})) == 20, "V184 reference catalog is not 20")
    ledger_count, ledger_hash = verify_ledger(
        output["reference_workspace"] / "reference_builds" / "ledger.jsonl"
    )
    receipt = {
        "schema_version": "NSE_E1_LOW_FRESH_CONFIRMATION_REFERENCES_V184_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_reference": True,
        "performance_fields_parsed": 0,
        "dispatches": dispatches,
        "catalog_file_sha256": file_hash(output["reference_catalog"]),
        "catalog_entry_count": 20,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "ready_manifest_hash": ready["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["reference_execution"], receipt)
    return receipt


def execute_v184(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, tapes_bound=True, references_bound=True)
    by_key = {(run["method"], run["seed"]): run for run in manifest["runs"]}
    logs = root / "execution-logs"
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        method = "sche_nash"
        run = by_key[(method, seed)]
        stdout = logs / f"{ordinal:02d}-{method}-{seed}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{method}-{seed}.stderr.log"
        _reread_goal()
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "run",
                str(output["ready"]),
                str(output["workspace"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V184 online {method}/{seed}",
        )
        canonical = output["workspace"] / "canonical" / run["run_id"]
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        _require(
            attempt.get("attempt") == 1
            and attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V184 run is not attempt-one QC pass: {run['run_id']}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "method": method,
                "seed": seed,
                "run_id": run["run_id"],
                "attempt_sha256": file_hash(canonical / "attempt.json"),
                "qc_sha256": file_hash(canonical / "qc_report.json"),
                "audit_sha256": file_hash(canonical / "manifest.json"),
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_LOW_FRESH_CONFIRMATION_NSESCHE_ONLY_EXECUTION_V184_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_online_dispatch": True,
        "performance_fields_parsed": 0,
        "baseline_online_runs": 0,
        "preregistered_plan_sha256": PLAN_SHA256,
        "fixed_order": [{"method": "sche_nash", "seed": seed} for seed in SEEDS],
        "dispatches": dispatches,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _runtime_identity(audits: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    identities = {
        (
            item.get("adapter_binary", {}).get("verified_sha256"),
            item.get("software_environment", {}).get("git", {}).get("commit"),
            item.get("software_environment", {})
            .get("python", {})
            .get("executable_sha256"),
            item.get("software_environment", {}).get("cargo_lock", {}).get("sha256"),
        )
        for item in audits
    }
    _require(len(identities) == 1, "V184 runtime identity is not unanimous")
    binary, git_commit, python_sha, cargo_sha = next(iter(identities))
    _require(
        binary == BINARY_SHA256
        and python_sha == PYTHON_SHA256
        and cargo_sha == CARGO_LOCK_SHA256
        and isinstance(git_commit, str)
        and len(git_commit) == 40,
        "V184 runtime identity changed",
    )
    return {
        "runtime_binary_sha256": binary,
        "runtime_git_commit": git_commit,
        "runtime_python_executable_sha256": python_sha,
        "runtime_cargo_lock_sha256": cargo_sha,
    }


def _assert_clean_ledger(path: Path, expected_run_ids: set[str]) -> tuple[int, str]:
    count, last_hash = verify_ledger(path)
    events = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    bad = {
        "attempt_failed",
        "attempt_quarantined",
        "run_blocked",
        "run_integrity_blocked",
    }
    _require(
        not any(event.get("event_type") in bad for event in events),
        "V184 ledger has failure events",
    )
    canonicalized = [
        event for event in events if event.get("event_type") == "attempt_canonicalized"
    ]
    _require(
        {event.get("payload", {}).get("run_id") for event in canonicalized}
        == expected_run_ids
        and all(
            event.get("payload", {}).get("attempt") == 1 for event in canonicalized
        ),
        "V184 ledger is not exact attempt-one coverage",
    )
    return count, last_hash


def _tape_catalog_evidence(
    manifest: Mapping[str, Any], output: Mapping[str, Path]
) -> list[dict[str, Any]]:
    catalog = read_json(output["tape_catalog"])
    entries = catalog.get("entries")
    expected = {run["workload_tape"]["key"] for run in manifest["runs"]}
    _require(
        isinstance(entries, dict) and set(entries) == expected and len(entries) == 20,
        "V184 tape catalog key set changed",
    )
    quarantine = output["tape_workspace"] / "capture_base_tapes" / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.rglob("attempt-*")),
        "V184 tape-capture quarantine is not empty",
    )
    evidence = []
    for key in sorted(entries):
        entry = entries[key]
        tape = Path(entry["path"])
        receipt = Path(entry["capture_receipt_path"])
        attempt_path = receipt.parent / "attempt.json"
        attempt = read_json(attempt_path)
        _require(
            entry.get("kind") == "base_steady"
            and tape.is_file()
            and file_hash(tape) == entry["sha256"]
            and receipt.is_file()
            and file_hash(receipt) == entry["capture_receipt_sha256"]
            and attempt.get("attempt") == 1
            and attempt.get("status") == "pass",
            f"V184 tape is not an attempt-one canonical capture: {key}",
        )
        evidence.append(
            {
                "key": key,
                "seed": entry["workload_seed"],
                "tape_sha256": entry["sha256"],
                "receipt_sha256": entry["capture_receipt_sha256"],
                "attempt_sha256": file_hash(attempt_path),
            }
        )
    _require(
        {item["seed"] for item in evidence} == set(SEEDS),
        "V184 tape catalog seed set changed",
    )
    return evidence


def _reference_catalog_evidence(
    manifest: Mapping[str, Any], output: Mapping[str, Path]
) -> list[dict[str, Any]]:
    catalog = read_json(output["reference_catalog"])
    entries = catalog.get("entries")
    expected = {
        run["reference_dependency"]["key"]
        for run in manifest["runs"]
        if run["method"] == "sche_nash"
    }
    _require(
        isinstance(entries, dict) and set(entries) == expected and len(entries) == 20,
        "V184 reference catalog key set changed",
    )
    quarantine = output["reference_workspace"] / "reference_builds" / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.rglob("attempt-*")),
        "V184 reference quarantine is not empty",
    )
    evidence = []
    for key in sorted(entries):
        entry = entries[key]
        table = Path(entry["path"])
        receipt = Path(entry["receipt_path"])
        process = Path(entry["build_process_observation_path"])
        attempt_path = table.parent / "attempt.json"
        attempt = read_json(attempt_path)
        _require(
            table.is_file()
            and file_hash(table) == entry["sha256"]
            and receipt.is_file()
            and file_hash(receipt) == entry["receipt_sha256"]
            and process.is_file()
            and file_hash(process) == entry["build_process_observation_sha256"]
            and attempt.get("attempt") == 1
            and attempt.get("status") == "pass",
            f"V184 reference is not an attempt-one canonical build: {key}",
        )
        evidence.append(
            {
                "key": key,
                "table_sha256": entry["sha256"],
                "receipt_sha256": entry["receipt_sha256"],
                "process_observation_sha256": entry["build_process_observation_sha256"],
                "attempt_sha256": file_hash(attempt_path),
            }
        )
    return evidence


def blind_audit_v184(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    _require(not output["blind"].exists(), "V184 blind audit already exists")
    _require(not output["result"].exists(), "V184 result exists before blind audit")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, tapes_bound=True, references_bound=True)
    prepared = read_json(output["prepared"])
    tape_execution = read_json(output["tape_execution"])
    reference_execution = read_json(output["reference_execution"])
    execution = read_json(output["execution"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V184 prepared receipt")
    tape_execution_hash = _assert_hashed(
        tape_execution, "receipt_hash", "V184 tape execution receipt"
    )
    reference_execution_hash = _assert_hashed(
        reference_execution, "receipt_hash", "V184 reference execution receipt"
    )
    execution_hash = _assert_hashed(execution, "receipt_hash", "V184 execution receipt")
    _require(
        [item["seed"] for item in tape_execution["dispatches"]] == list(SEEDS)
        and [item["seed"] for item in reference_execution["dispatches"]] == list(SEEDS)
        and [(item["method"], item["seed"]) for item in execution["dispatches"]]
        == [("sche_nash", seed) for seed in SEEDS]
        and execution.get("baseline_online_runs") == 0
        and execution.get("preregistered_plan_sha256") == PLAN_SHA256
        and tape_execution.get("performance_fields_parsed") == 0
        and reference_execution.get("performance_fields_parsed") == 0
        and execution.get("performance_fields_parsed") == 0,
        "V184 fixed execution order or result-blind receipts changed",
    )
    canonical_root = output["workspace"] / "canonical"
    candidate_runs = [run for run in manifest["runs"] if run["method"] == "sche_nash"]
    expected_ids = {run["run_id"] for run in candidate_runs}
    actual_ids = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    _require(actual_ids == expected_ids, "V184 canonical directory set changed")
    inventory = {
        "schema_version": "NSE_E1_LOW_FRESH_CONFIRMATION_CANDIDATE_INVENTORY_V184_V1",
        "created_at": utc_now(),
        "status": "pass",
        "method": "sche_nash",
        "seeds": list(SEEDS),
        "run_ids": [run["run_id"] for run in candidate_runs],
        "run_count": 20,
        "baseline_online_runs": 0,
        "metrics_consulted": False,
    }
    inventory["inventory_hash"] = object_hash(inventory)
    write_json_atomic(output["pairing"], inventory)
    quarantine = output["workspace"] / "quarantine"
    _require(
        not quarantine.exists() or not any(quarantine.rglob("attempt-*")),
        "V184 quarantine is not empty",
    )
    runner = ProtocolRunner(output["ready"], output["workspace"])
    audits = []
    run_evidence = []
    by_seed: dict[str, list[Mapping[str, Any]]] = {seed: [] for seed in SEEDS}
    for run in candidate_runs:
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        runner._validate_existing_canonical(run, canonical)
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        audit = read_json(canonical / "manifest.json")
        _require(
            attempt.get("attempt") == 1
            and attempt.get("classification") == "qc_pass"
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V184 non-clean canonical: {run['run_id']}",
        )
        audits.append(audit)
        by_seed[run["seed"]].append(run)
        run_evidence.append(
            {
                "run_id": run["run_id"],
                "method": run["method"],
                "seed": run["seed"],
                "run_spec_hash": run["run_spec_hash"],
                "tape_sha256": run["workload_tape"]["sha256"],
                "reference_sha256": (
                    run["reference_dependency"].get("sha256")
                    if run.get("reference_dependency")
                    else None
                ),
                "result_sha256": attempt["result_sha256"],
                "attempt_sha256": file_hash(canonical / "attempt.json"),
                "qc_sha256": file_hash(canonical / "qc_report.json"),
                "audit_sha256": file_hash(canonical / "manifest.json"),
            }
        )
    for seed, runs in by_seed.items():
        _require(
            len(runs) == 1 and runs[0]["method"] == "sche_nash",
            f"V184 {seed} candidate coverage changed",
        )
        environments = [run["workload_tape"].get("capture_environment") for run in runs]
        _require(
            all(isinstance(item, Mapping) for item in environments),
            f"V184 {seed} lacks semantic environment evidence",
        )
        _require(
            len({object_hash(item) for item in environments}) == 1,
            f"V184 {seed} semantic environment evidence changed",
        )
    tape_evidence = _tape_catalog_evidence(manifest, output)
    reference_evidence = _reference_catalog_evidence(manifest, output)
    run_count, run_hash = _assert_clean_ledger(
        output["workspace"] / "ledger.jsonl", expected_ids
    )
    tape_count, tape_hash = verify_ledger(
        output["tape_workspace"] / "capture_base_tapes" / "ledger.jsonl"
    )
    reference_count, reference_hash = verify_ledger(
        output["reference_workspace"] / "reference_builds" / "ledger.jsonl"
    )
    document = {
        "schema_version": "NSE_E1_LOW_FRESH_CONFIRMATION_NSESCHE_ONLY_BLIND_AUDIT_V184_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_eligible_if_joint_gate_passes": True,
        "plan_sha256": PLAN_SHA256,
        "metrics_consulted": False,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "training_rows_pooled": False,
        "confirmation_seeds": list(SEEDS),
        "observed_base_tapes": 20,
        "observed_candidate_references": 20,
        "observed_online_runs": 20,
        "attempt_one_qc_passes": 20,
        "zero_quarantine": True,
        "exact_candidate_cohort": True,
        "baseline_online_runs": 0,
        "prepared_receipt_hash": prepared_hash,
        "tape_execution_receipt_hash": tape_execution_hash,
        "reference_execution_receipt_hash": reference_execution_hash,
        "execution_receipt_hash": execution_hash,
        "runtime_identity": _runtime_identity(audits),
        "ready_manifest": {
            "path": str(output["ready"].resolve()),
            "file_sha256": file_hash(output["ready"]),
            "manifest_hash": manifest["manifest_hash"],
        },
        "candidate_inventory": {
            "path": str(output["pairing"].resolve()),
            "file_sha256": file_hash(output["pairing"]),
            "inventory_hash": inventory["inventory_hash"],
            "run_count": 20,
        },
        "frozen_baselines": copy.deepcopy(FROZEN_BASELINES),
        "ledgers": {
            "runs": {"events": run_count, "last_hash": run_hash},
            "tapes": {"events": tape_count, "last_hash": tape_hash},
            "references": {"events": reference_count, "last_hash": reference_hash},
        },
        "run_evidence": run_evidence,
        "tape_evidence": tape_evidence,
        "reference_evidence": reference_evidence,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _finite(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _summary_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    values = _nse_summary_metrics(summary)
    completed = values.get("completed")
    throughput = values.get("throughput")
    latency = values.get("latency_mean_ms")
    cost = values.get("cost")
    _require(
        isinstance(completed, int)
        and not isinstance(completed, bool)
        and completed >= 0,
        "invalid completion count",
    )
    _require(_finite(throughput) and float(throughput) >= 0.0, "invalid throughput")
    throughput = float(throughput)
    qpr = None
    if (
        completed > 0
        and throughput > 0.0
        and _finite(latency)
        and float(latency) > 0.0
        and _finite(cost)
        and float(cost) > 0.0
    ):
        candidate = throughput / (float(latency) * float(cost))
        if math.isfinite(candidate):
            qpr = candidate
    return {
        "completed": completed,
        "throughput_requests_per_ms": throughput,
        "latency_mean_ms": float(latency) if _finite(latency) else None,
        "cost_per_completed_request": float(cost) if _finite(cost) else None,
        "qpr_finite_only": qpr,
        "qpr_zero_completed_as_zero": 0.0 if qpr is None else qpr,
    }


def _frozen_comparator_values(metric: str) -> list[float]:
    result = read_json(COMPLETE_TRAINING_RESULT)
    _require(
        _assert_hashed(result, "result_hash", "V182 complete training result")
        == COMPLETE_TRAINING_RESULT_HASH,
        "V182 complete training result hash changed",
    )
    gate_key = "throughput" if metric == "throughput_requests_per_ms" else metric
    gate = result["hybrid_low_evaluation"]["gates"][gate_key]
    expected_comparator = FROZEN_BASELINES[metric]["method"].removeprefix("sche_")
    _require(
        str(gate.get("paired_comparator", "")).casefold()
        == expected_comparator.casefold()
        and str(gate.get("ceiling_algorithm", "")).casefold()
        == expected_comparator.casefold()
        and gate.get("paired_n") == 20
        and math.isclose(
            float(gate.get("ceiling_mean")),
            float(FROZEN_BASELINES[metric]["mean"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        ),
        f"V182 frozen comparator changed for {metric}",
    )
    paired_rows = gate.get("paired_rows")
    _require(
        isinstance(paired_rows, list)
        and [row.get("seed") for row in paired_rows]
        == [f"E{index:02d}" for index in range(1, 21)],
        f"V182 frozen comparator seed cohort changed for {metric}",
    )
    values = [row.get("comparator") for row in paired_rows]
    _require(
        all(_finite(value) for value in values),
        f"V182 frozen comparator has nonfinite {metric}",
    )
    numeric = [float(value) for value in values]
    _require(
        math.isclose(
            sum(numeric) / len(numeric),
            float(FROZEN_BASELINES[metric]["mean"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        ),
        f"V182 frozen comparator mean changed for {metric}",
    )
    return numeric


def _two_sample_bca_mean_difference(
    candidate: Sequence[float],
    comparator: Sequence[float],
    *,
    seed: int,
    n_resamples: int = 10_000,
) -> dict[str, Any]:
    left = np.asarray(candidate, dtype=float)
    right = np.asarray(comparator, dtype=float)
    _require(
        left.size >= 3
        and right.size >= 3
        and np.isfinite(left).all()
        and np.isfinite(right).all(),
        "independent BCa requires at least three finite values per cohort",
    )
    estimate = float(np.mean(left) - np.mean(right))
    rng = np.random.default_rng(seed)
    left_indices = rng.integers(0, left.size, size=(n_resamples, left.size))
    right_indices = rng.integers(0, right.size, size=(n_resamples, right.size))
    bootstrap = np.mean(left[left_indices], axis=1) - np.mean(
        right[right_indices], axis=1
    )
    less = float(np.count_nonzero(bootstrap < estimate))
    equal = float(np.count_nonzero(bootstrap == estimate))
    proportion = (less + 0.5 * equal) / float(bootstrap.size)
    guard = 0.5 / float(bootstrap.size)
    proportion = min(max(proportion, guard), 1.0 - guard)
    normal = NormalDist()
    bias = normal.inv_cdf(proportion)
    jackknife = np.concatenate(
        (
            (float(np.sum(left)) - left) / float(left.size - 1) - float(np.mean(right)),
            float(np.mean(left))
            - (float(np.sum(right)) - right) / float(right.size - 1),
        )
    )
    jackknife_mean = float(np.mean(jackknife))
    centered = jackknife_mean - jackknife
    denominator = 6.0 * float(np.sum(centered**2)) ** 1.5
    acceleration = (
        0.0 if denominator == 0.0 else float(np.sum(centered**3)) / denominator
    )
    adjusted = []
    for probability in (0.025, 0.975):
        z_alpha = normal.inv_cdf(probability)
        inner = bias + z_alpha
        denominator = 1.0 - acceleration * inner
        transformed = (
            0.0
            if denominator == 0.0 and inner < 0.0
            else 1.0
            if denominator == 0.0
            else normal.cdf(bias + inner / denominator)
        )
        adjusted.append(min(max(transformed, 0.0), 1.0))
    low, high = np.quantile(bootstrap, adjusted, method="linear")
    return {
        "estimate": estimate,
        "low": float(low),
        "high": float(high),
        "confidence": 0.95,
        "candidate_n": int(left.size),
        "comparator_n": int(right.size),
        "resamples": int(n_resamples),
        "method": "independent_two_sample_BCa_mean_difference",
        "bias_correction": float(bias),
        "acceleration": float(acceleration),
    }


def _unpaired_permutation_mean_difference(
    candidate: Sequence[float],
    comparator: Sequence[float],
    *,
    seed: int,
    n_resamples: int = 100_000,
) -> dict[str, Any]:
    left = np.asarray(candidate, dtype=float)
    right = np.asarray(comparator, dtype=float)
    _require(
        left.size > 0
        and right.size > 0
        and np.isfinite(left).all()
        and np.isfinite(right).all(),
        "unpaired permutation requires finite nonempty cohorts",
    )
    pooled = np.concatenate((left, right))
    observed = float(np.mean(left) - np.mean(right))
    tolerance = np.finfo(float).eps * max(1.0, abs(observed)) * 8.0
    rng = np.random.default_rng(seed)
    extreme = 0
    generated = 0
    batch_size = 5_000
    pooled_sum = float(np.sum(pooled))
    while generated < n_resamples:
        current = min(batch_size, n_resamples - generated)
        scores = rng.random((current, pooled.size))
        indices = np.argpartition(scores, left.size - 1, axis=1)[:, : left.size]
        left_sums = np.sum(pooled[indices], axis=1)
        differences = left_sums / float(left.size) - (pooled_sum - left_sums) / float(
            right.size
        )
        extreme += int(
            np.count_nonzero(np.abs(differences) >= abs(observed) - tolerance)
        )
        generated += current
    return {
        "mean_difference": observed,
        "p_value": float((extreme + 1.0) / (n_resamples + 1.0)),
        "alternative": "two-sided",
        "exact": False,
        "candidate_n": int(left.size),
        "comparator_n": int(right.size),
        "resamples": int(n_resamples),
        "method": "unpaired_label_permutation_with_plus_one_correction",
    }


def _evaluate_confirmation(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = set(SEEDS)
    by_seed = {row["seed"]: row for row in rows}
    _require(
        set(by_seed) == expected
        and len(rows) == 20
        and all(row.get("method") == "sche_nash" for row in rows),
        "V184 reveal rows are not the exact 20-run NSESche cohort",
    )
    gates = {}
    for metric in METRICS:
        series = [by_seed[seed].get(metric) for seed in SEEDS]
        _require(
            all(_finite(value) for value in series),
            f"V184 sche_nash/{metric} has nonfinite values",
        )
        candidate = [float(value) for value in series]
        baseline = FROZEN_BASELINES[metric]
        comparator = _frozen_comparator_values(metric)
        threshold = float(baseline["mean"])
        candidate_mean = sum(candidate) / len(candidate)
        candidate_interval = bca_interval(
            candidate,
            n_resamples=10_000,
            seed=184_000 + METRICS.index(metric),
        )
        difference_interval = _two_sample_bca_mean_difference(
            candidate,
            comparator,
            n_resamples=10_000,
            seed=184_100 + METRICS.index(metric),
        )
        permutation = _unpaired_permutation_mean_difference(
            candidate,
            comparator,
            n_resamples=100_000,
            seed=184_200 + METRICS.index(metric),
        )
        passed = candidate_mean > threshold
        gates[metric] = {
            "frozen_primary_comparator": baseline["method"],
            "frozen_baseline_mean": threshold,
            "frozen_comparator_n": len(comparator),
            "candidate_mean": candidate_mean,
            "candidate_strictly_exceeds_frozen_baseline_mean": candidate_mean
            > threshold,
            "candidate_n": 20,
            "candidate_minus_frozen_baseline_mean": candidate_mean - threshold,
            "candidate_mean_BCa_95_percent_interval": candidate_interval,
            "unpaired_candidate_minus_frozen_comparator_BCa_95_percent_interval": difference_interval,
            "two_sided_unpaired_permutation": permutation,
            "individual_candidate_values_above_global_comparator_mean": {
                "count": sum(value > threshold for value in candidate),
                "used_as_gate": False,
                "reason": "independent workload draws are not paired by seed",
            },
            "passed": passed,
        }
    all_candidate_qpr_finite = all(
        _finite(by_seed[seed].get("qpr_finite_only")) for seed in SEEDS
    )
    gates["qpr_finite_only"][
        "all_twenty_candidate_values_finite"
    ] = all_candidate_qpr_finite
    gates["qpr_finite_only"]["passed"] = (
        gates["qpr_finite_only"]["passed"] and all_candidate_qpr_finite
    )
    return {
        "gates": gates,
        "all_three_metric_gates_pass": all(
            gates[metric]["passed"] for metric in METRICS
        ),
    }


def reveal_v184(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    _require(not output["result"].exists(), "V184 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V184 blind audit")
    _require(
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("metrics_consulted") is False
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("observed_online_runs") == 20
        and blind.get("attempt_one_qc_passes") == 20
        and blind.get("zero_quarantine") is True
        and blind.get("exact_candidate_cohort") is True
        and blind.get("baseline_online_runs") == 0,
        "V184 blind audit does not authorize reveal",
    )
    _reread_goal()
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, tapes_bound=True, references_bound=True)
    rows = []
    for run in manifest["runs"]:
        if run["method"] != "sche_nash":
            continue
        summary_path = (
            output["workspace"]
            / "canonical"
            / run["run_id"]
            / "reviewer_records"
            / run["run_id"]
            / "summary.json"
        )
        summary = read_json(summary_path)
        _require(
            summary.get("run_complete") is True, f"incomplete summary: {run['run_id']}"
        )
        rows.append(
            {
                "method": run["method"],
                "seed": run["seed"],
                "run_id": run["run_id"],
                **_summary_metrics(summary),
                "summary_path": str(summary_path),
                "summary_file_sha256": file_hash(summary_path),
            }
        )
    evaluation = _evaluate_confirmation(rows)
    passed = evaluation["all_three_metric_gates_pass"]
    document = {
        "schema_version": "NSE_E1_LOW_DISJOINT_UNPAIRED_CONFIRMATION_RESULT_V184_V1",
        "created_at": utc_now(),
        "status": "confirmation_pass" if passed else "confirmation_fail",
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": passed,
        "homogeneous_20node_low_closed": passed,
        "middle_load_authorized": passed,
        "plan_sha256": PLAN_SHA256,
        "V183_failure_receipt_hash": FAILURE_RECEIPT_HASH,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "confirmation_seeds": list(SEEDS),
        "training_rows_pooled": False,
        "baseline_online_runs": 0,
        "frozen_baselines": copy.deepcopy(FROZEN_BASELINES),
        "complete_confirmation_rows": rows,
        "evaluation": evaluation,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
        "decision": (
            "freeze_complete_E1590_E1609_confirmation_and_proceed_to_middle"
            if passed
            else "retain_complete_E1590_E1609_failure_and_require_new_disjoint_cycle"
        ),
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "capture-tapes",
            "build-references",
            "execute",
            "blind-audit",
            "reveal",
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    actions = {
        "prepare": prepare_v184,
        "capture-tapes": capture_and_bind_tapes_v184,
        "build-references": build_references_v184,
        "execute": execute_v184,
        "blind-audit": blind_audit_v184,
        "reveal": reveal_v184,
    }
    document = actions[action]()
    key = next(
        key
        for key in ("receipt_hash", "blind_audit_hash", "result_hash")
        if key in document
    )
    print(json.dumps({key: document[key], "action": action}, indent=2))


if __name__ == "__main__":
    main()
