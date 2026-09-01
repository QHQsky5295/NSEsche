from __future__ import annotations

import argparse
import copy
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.stats import bca_interval
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_disjoint_unpaired_confirmation_v184 as v184,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_cpu_work_shrink_ocs_training_v186 as v186,
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
    "tmp/nse_e1_homogeneous_20node_low_response_time_ocs_training_20260901_v187"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_response_time_ocs_training_plan_v187.json"
)
PLAN_SHA256 = "c0788960cb6ecf849884b694ea32496f4a71951b4055747df3fe142e50cdc882"
PLAN_HASH = "317788caba83491419b7069e82ec780982e2afe326ab742ca1d8f16aed24b6c7"
PLAN_COMMIT = "d65fb81f5cb41816ce7b1906144af2c0790c42fc"
FAILURE_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_cpu_work_shrink_ocs_training_failure_v186.json"
)
FAILURE_RECEIPT_SHA256 = (
    "bc46fb76941be00ddb046f3e612b78794bcfbdccf21395d30fe43cda71725554"
)
FAILURE_RECEIPT_HASH = (
    "e5b776a2e15d998e243170816773b9f04bd4d40b201ebbfb3fb20a20bc520d0a"
)
IMPLEMENTATION_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_20node_low_response_time_ocs_training_implementation_v187.json"
)
MODULE = Path(__file__)
TEST = Path(
    "scripts/reviewer_experiments/protocol/tests/"
    "test_nse_e1_low_response_time_ocs_training_v187.py"
)
GOAL = v184.GOAL
GOAL_SHA256 = v184.GOAL_SHA256
DEFAULT_CONFIG = v184.DEFAULT_CONFIG
DEFAULT_CONFIG_SHA256 = v184.DEFAULT_CONFIG_SHA256

SEEDS = tuple(f"E{index}" for index in range(1610, 1630))
ARMS = ("control", "candidate")
CONTROL_PROFILE = (
    "srpt_slack_concurrent2_queue8_cpu_bounded_terminal_short5p5_"
    "pipeline_hiku2_ocs_queue8"
)
CANDIDATE_PROFILE = (
    "srpt_slack_concurrent2_queue8_cpu_bounded_terminal_short5p5_"
    "pipeline_hiku2_response2_ocs1_queue8"
)
PROFILES = {"control": CONTROL_PROFILE, "candidate": CANDIDATE_PROFILE}
FRONTIER = v184.FRONTIER
PORT = "3213"
BINARY_PATH = Path("serverless_sim/target_e1_v187/release/serverless_sim.exe")
BINARY_SHA256 = "cd8c31f309f375a29436f30a24dcb12b34960058702bf52f8549f6e919236f6d"
BINARY_BYTES = 5_906_432
BINARY_SOURCE_COMMIT = "9db6f759798f1489d793661655aefb0ec1cc4e20"
SCHEDULER_SOURCE = Path("serverless_sim/src/sche/sche_nash.rs")
SCHEDULER_SOURCE_SHA256 = (
    "0c6d492d22c083f84ef2e4cae6fb703854f544844d48162ea2ebb8cfa83b63a7"
)
PYTHON_PATH = v184.PYTHON_PATH
PYTHON_SHA256 = v184.PYTHON_SHA256
CARGO_LOCK = v184.CARGO_LOCK
CARGO_LOCK_SHA256 = v184.CARGO_LOCK_SHA256
MODULE_CONF = v184.MODULE_CONF
MODULE_CONF_SEMANTIC_HASH = v184.MODULE_CONF_SEMANTIC_HASH
FROZEN_BASELINES = copy.deepcopy(v184.FROZEN_BASELINES)
METRICS = tuple(FROZEN_BASELINES)


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "config": root / "training-config-v187.json",
        "source": root / "manifest.full-source.unbound.json",
        "control_unbound": root / "manifest.control.unbound.json",
        "candidate_unbound": root / "manifest.candidate.unbound.json",
        "schedule": root / "counterbalanced-schedule-v187.json",
        "prepared": root / "prepared-v187.json",
        "tape_workspace": root / "tape-stage",
        "tape_catalog": root / "tapes.catalog.json",
        "control_tapes": root / "manifest.control.tapes.json",
        "candidate_tapes": root / "manifest.candidate.tapes.json",
        "tape_execution": root / "tape-execution-receipt-v187.json",
        "control_reference_workspace": root / "reference-control-stage",
        "candidate_reference_workspace": root / "reference-candidate-stage",
        "control_reference_catalog": root / "references.control.catalog.json",
        "candidate_reference_catalog": root / "references.candidate.catalog.json",
        "control_ready": root / "manifest.control.ready.json",
        "candidate_ready": root / "manifest.candidate.ready.json",
        "reference_execution": root / "reference-execution-receipt-v187.json",
        "control_workspace": root / "formal-runs-control",
        "candidate_workspace": root / "formal-runs-candidate",
        "execution": root / "execution-receipt-v187.json",
        "inventory": root / "paired-inventory-audit-v187.json",
        "blind": root / "joint-blind-audit-v187.json",
        "result": root / "training-result-v187.json",
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected: str, label: str) -> None:
    _require(path.is_file(), f"missing {label}: {path}")
    _require(file_hash(path) == expected, f"{label} hash changed: {path}")


def _assert_hashed(document: Mapping[str, Any], key: str, label: str) -> str:
    value = document.get(key)
    _require(isinstance(value, str) and len(value) == 64, f"{label} lacks {key}")
    payload = copy.deepcopy(dict(document))
    payload.pop(key, None)
    _require(object_hash(payload) == value, f"{label} self-hash changed")
    return value


def _reread_goal() -> None:
    _assert_file(GOAL, GOAL_SHA256, "goal objective")


def _assert_plan() -> dict[str, Any]:
    _assert_file(PLAN, PLAN_SHA256, "V187 plan")
    _assert_file(FAILURE_RECEIPT, FAILURE_RECEIPT_SHA256, "V186 failure receipt")
    plan = read_json(PLAN)
    failure = read_json(FAILURE_RECEIPT)
    _require(
        _assert_hashed(plan, "plan_hash", "V187 plan") == PLAN_HASH
        and plan.get("training_only") is True
        and tuple(plan.get("cohort", {}).get("seed_order", [])) == SEEDS
        and plan.get("cohort", {}).get("online_runs") == 40
        and plan.get("candidate", {}).get("profile") == CANDIDATE_PROFILE
        and plan.get("paired_control", {}).get("profile") == CONTROL_PROFILE
        and plan.get("frozen_comparators", {})
        .get("throughput", {})
        .get("mean_requests_per_ms")
        == FROZEN_BASELINES["throughput_requests_per_ms"]["mean"]
        and plan.get("frozen_comparators", {}).get("qpr", {}).get("mean")
        == FROZEN_BASELINES["qpr_finite_only"]["mean"],
        "V187 plan boundary changed",
    )
    _require(
        _assert_hashed(failure, "receipt_hash", "V186 failure receipt")
        == FAILURE_RECEIPT_HASH
        and failure.get("status") == "complete_same_tape_training_failed_qpr_gates"
        and failure.get("technical_integrity", {}).get("all_valid_rows_retained")
        is True
        and failure.get("disposition", {}).get(
            "delete_or_replace_unfavorable_valid_seeds"
        )
        is False,
        "V186 failure evidence changed",
    )
    return plan


def _assert_frozen_inputs() -> dict[str, Any]:
    plan = _assert_plan()
    for path, expected, label in (
        (GOAL, GOAL_SHA256, "goal objective"),
        (DEFAULT_CONFIG, DEFAULT_CONFIG_SHA256, "default protocol"),
        (BINARY_PATH, BINARY_SHA256, "V187 binary"),
        (SCHEDULER_SOURCE, SCHEDULER_SOURCE_SHA256, "V187 scheduler source"),
        (PYTHON_PATH, PYTHON_SHA256, "Python executable"),
        (CARGO_LOCK, CARGO_LOCK_SHA256, "Cargo.lock"),
    ):
        _assert_file(path, expected, label)
    _require(BINARY_PATH.stat().st_size == BINARY_BYTES, "V187 binary size changed")
    v184.v182.v181._assert_json_semantic(
        MODULE_CONF, MODULE_CONF_SEMANTIC_HASH, "module_conf_es.json"
    )
    _require(IMPLEMENTATION_RECEIPT.is_file(), "V187 implementation receipt missing")
    receipt = read_json(IMPLEMENTATION_RECEIPT)
    _assert_hashed(receipt, "receipt_hash", "V187 implementation receipt")
    _require(
        receipt.get("plan_sha256") == PLAN_SHA256
        and receipt.get("module_sha256") == file_hash(MODULE)
        and receipt.get("test_sha256") == file_hash(TEST)
        and receipt.get("runtime_binary_sha256") == BINARY_SHA256
        and receipt.get("online_runs_before_seal") == 0,
        "V187 implementation receipt does not bind this harness",
    )
    return plan


def _counterbalanced_order() -> list[dict[str, str]]:
    order: list[dict[str, str]] = []
    for seed in SEEDS:
        arms = ARMS if int(seed[1:]) % 2 == 0 else tuple(reversed(ARMS))
        order.extend({"arm": arm, "seed": seed} for arm in arms)
    return order


def _write_config(path: Path) -> None:
    config = read_json(DEFAULT_CONFIG)
    config["seed_policy"] = {
        "initial": list(SEEDS[:10]),
        "ci_extension": list(SEEDS[10:]),
        "ci_extension_requires_trigger": True,
        "e7_initial": list(SEEDS[:5]),
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


def _selected(run: Mapping[str, Any]) -> bool:
    workload = run.get("workload", {})
    return (
        run.get("experiment_id") == "E1"
        and run.get("method") == "sche_nash"
        and run.get("seed") in SEEDS
        and workload.get("request_freq") == "low"
        and workload.get("arrival_profile") == "steady"
        and workload.get("topology") == "homogeneous"
        and workload.get("qos_profile") == "mixed"
        and run.get("cluster") == {"node_count": 20, "topology": "homogeneous"}
    )


def _rewrite_arm(
    shard: Mapping[str, Any], arm: str, protocol_commit: str
) -> dict[str, Any]:
    _require(arm in ARMS, f"unknown V187 arm: {arm}")
    rewritten = copy.deepcopy(dict(shard))
    source_runs = {run["seed"]: run for run in rewritten["runs"]}
    _require(set(source_runs) == set(SEEDS), "V187 source product is not exact 20")
    rewritten["created_at"] = utc_now()
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    rewritten["runs"] = []
    lineage = []
    for seed in SEEDS:
        source = source_runs[seed]
        run = copy.deepcopy(source)
        source_run_id = run["run_id"]
        source_spec_hash = run["run_spec_hash"]
        run["variant"] = f"homogeneous-20node-low-v187-{arm}-training"
        run["environment"].update(v184.v182.v181.COMMON_ENVIRONMENT)
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILES[arm]
        run["metadata"] = {
            "v187_training_only": True,
            "v187_arm": arm,
            "v187_plan_sha256": PLAN_SHA256,
            "v187_plan_commit": PLAN_COMMIT,
            "v187_protocol_source_commit": protocol_commit,
            "v187_profile": PROFILES[arm],
            "v187_player_frontier": FRONTIER,
            "v187_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v187_binary_sha256": BINARY_SHA256,
            "v187_source_run_id": source_run_id,
            "v187_source_run_spec_hash": source_spec_hash,
            "v187_shared_fresh_tape": True,
            "v187_non_nsesche_online_runs": 0,
            "v187_performance_fields_parsed_before_run": 0,
            "v187_seed_deletion_replacement_or_selective_rerun": False,
        }
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
        _assign_run_identity(run)
        rewritten["runs"].append(run)
        lineage.append(
            {
                "seed": seed,
                "source_run_id": source_run_id,
                "source_run_spec_hash": source_spec_hash,
                "training_run_id": run["run_id"],
                "training_run_spec_hash": run["run_spec_hash"],
                "arm": arm,
            }
        )
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": f"V187 paired {arm} arm on fresh E1610-E1629 tapes",
            "v187_training_only": True,
            "v187_arm": arm,
            "v187_plan_sha256": PLAN_SHA256,
            "v187_profile": PROFILES[arm],
            "v187_source_to_training_lineage": lineage,
            "v187_expected_runs": 20,
            "v187_expected_references": 20,
            "v187_non_nsesche_online_runs": 0,
            "selected_run_count": 20,
            "selected_reference_build_count": 20,
        }
    )
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    rewritten["all_tapes_bound"] = False
    rewritten["all_references_bound"] = False
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    _validate_arm(rewritten, arm, tapes_bound=False, references_bound=False)
    return rewritten


def _validate_arm(
    manifest: Mapping[str, Any],
    arm: str,
    *,
    tapes_bound: bool,
    references_bound: bool,
) -> None:
    runs = manifest.get("runs", [])
    _require(
        [(run.get("method"), run.get("seed")) for run in runs]
        == [("sche_nash", seed) for seed in SEEDS],
        f"V187 {arm} exact ordered product changed",
    )
    _require(
        manifest.get("all_tapes_bound") is tapes_bound
        and manifest.get("all_references_bound") is references_bound
        and len(manifest.get("reference_build_dependencies", [])) == 20,
        f"V187 {arm} binding state changed",
    )
    for run in runs:
        tape = run.get("workload_tape", {})
        reference = run.get("reference_dependency", {})
        _require(
            _selected(run)
            and run.get("variant") == f"homogeneous-20node-low-v187-{arm}-training"
            and run.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == PROFILES[arm]
            and run.get("environment", {}).get("SERVERLESS_SIM_PORT") == PORT
            and run.get("metadata", {}).get("v187_arm") == arm
            and bool(tape.get("sha256")) is tapes_bound
            and bool(reference.get("sha256")) is references_bound
            and bool(reference.get("build_required")) is (not references_bound),
            f"V187 {arm} run contract changed: {run.get('run_id')}",
        )


def _build_unbound_products(
    root: Path, protocol_commit: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    output = paths(root)
    _write_config(output["config"])
    write_manifest(output["source"], output["config"], seed_stage="all")
    source = load_and_validate_manifest(output["source"])
    selected = [run for run in source["runs"] if _selected(run)]
    _require(len(selected) == 20, "V187 source selection is not exact 20")
    shard = derive_integration_smoke_shard(
        output["source"],
        [run["run_id"] for run in selected],
        purpose="V187 paired NSESche response-time expert training",
    )
    manifests = {arm: _rewrite_arm(shard, arm, protocol_commit) for arm in ARMS}
    for arm in ARMS:
        write_json_atomic(output[f"{arm}_unbound"], manifests[arm])
    return source, manifests


def prepare_v187(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    _require(not root.exists(), f"refusing to overwrite V187 root: {root}")
    root.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source, manifests = _build_unbound_products(root, commit)
    output = paths(root)
    schedule = {
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_SCHEDULE_V187_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "capture_order": list(SEEDS),
        "reference_order": _counterbalanced_order(),
        "online_order": _counterbalanced_order(),
        "performance_fields_parsed": 0,
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    implementation = read_json(IMPLEMENTATION_RECEIPT)
    receipt = {
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_PREPARED_V187_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_fields_parsed": 0,
        "goal_sha256": GOAL_SHA256,
        "plan_sha256": PLAN_SHA256,
        "implementation_receipt_hash": implementation["receipt_hash"],
        "protocol_source_commit": commit,
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "source_manifest_hash": source["manifest_hash"],
        "source_manifest_file_sha256": file_hash(output["source"]),
        "control_manifest_hash": manifests["control"]["manifest_hash"],
        "candidate_manifest_hash": manifests["candidate"]["manifest_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "new_base_tapes": 20,
        "reference_builds_planned": 40,
        "online_runs_planned": 40,
        "non_nsesche_online_runs": 0,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def _run_logged(command: Sequence[str], stdout: Path, stderr: Path, label: str) -> None:
    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open("w", encoding="utf-8") as out, stderr.open(
        "w", encoding="utf-8"
    ) as err:
        completed = subprocess.run(command, stdout=out, stderr=err, check=False)
    _require(completed.returncode == 0, f"{label} failed: exit={completed.returncode}")


def capture_and_bind_tapes_v187(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifests = {
        arm: load_and_validate_manifest(output[f"{arm}_unbound"]) for arm in ARMS
    }
    for arm in ARMS:
        _validate_arm(manifests[arm], arm, tapes_bound=False, references_bound=False)
    control_by_seed = {run["seed"]: run for run in manifests["control"]["runs"]}
    candidate_by_seed = {run["seed"]: run for run in manifests["candidate"]["runs"]}
    logs = root / "tape-execution-logs"
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        control_key = control_by_seed[seed]["workload_tape"]["key"]
        candidate_key = candidate_by_seed[seed]["workload_tape"]["key"]
        _require(control_key == candidate_key, f"V187 {seed} tape key differs by arm")
        _reread_goal()
        stdout = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{seed}.stderr.log"
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "capture-base-tapes",
                str(output["control_unbound"]),
                str(output["tape_workspace"]),
                str(output["tape_catalog"]),
                "--key",
                control_key,
            ],
            stdout,
            stderr,
            f"V187 tape capture {seed}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "key": control_key,
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    bound = {}
    for arm in ARMS:
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "bind-tapes",
                str(output[f"{arm}_unbound"]),
                str(output["tape_catalog"]),
                str(output[f"{arm}_tapes"]),
            ],
            logs / f"bind-{arm}.stdout.log",
            logs / f"bind-{arm}.stderr.log",
            f"V187 {arm} tape binding",
        )
        bound[arm] = load_and_validate_manifest(output[f"{arm}_tapes"])
        _validate_arm(bound[arm], arm, tapes_bound=True, references_bound=False)
    for seed in SEEDS:
        control = next(run for run in bound["control"]["runs"] if run["seed"] == seed)
        candidate = next(
            run for run in bound["candidate"]["runs"] if run["seed"] == seed
        )
        _require(
            control["workload_tape"] == candidate["workload_tape"],
            f"V187 {seed} bound tape differs by arm",
        )
    catalog = read_json(output["tape_catalog"])
    _require(len(catalog.get("entries", {})) == 20, "V187 tape catalog is not 20")
    count, last_hash = verify_ledger(
        output["tape_workspace"] / "capture_base_tapes" / "ledger.jsonl"
    )
    receipt = {
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_TAPES_V187_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_capture": True,
        "performance_fields_parsed": 0,
        "dispatches": dispatches,
        "catalog_file_sha256": file_hash(output["tape_catalog"]),
        "catalog_entry_count": 20,
        "ledger_event_count": count,
        "ledger_last_hash": last_hash,
        "bound_manifest_hashes": {arm: bound[arm]["manifest_hash"] for arm in ARMS},
        "bound_manifest_file_sha256": {
            arm: file_hash(output[f"{arm}_tapes"]) for arm in ARMS
        },
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["tape_execution"], receipt)
    return receipt


def build_references_v187(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifests = {
        arm: load_and_validate_manifest(output[f"{arm}_tapes"]) for arm in ARMS
    }
    by_arm_seed = {}
    for arm in ARMS:
        _validate_arm(manifests[arm], arm, tapes_bound=True, references_bound=False)
        by_arm_seed[arm] = {run["seed"]: run for run in manifests[arm]["runs"]}
    logs = root / "reference-execution-logs"
    dispatches = []
    for ordinal, item in enumerate(_counterbalanced_order(), start=1):
        arm, seed = item["arm"], item["seed"]
        run = by_arm_seed[arm][seed]
        _reread_goal()
        stdout = logs / f"{ordinal:02d}-{seed}-{arm}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{seed}-{arm}.stderr.log"
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "build-references",
                str(output[f"{arm}_tapes"]),
                str(output[f"{arm}_reference_workspace"]),
                str(output[f"{arm}_reference_catalog"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V187 reference {arm}/{seed}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "arm": arm,
                "seed": seed,
                "run_id": run["run_id"],
                "stdout_sha256": file_hash(stdout),
                "stderr_sha256": file_hash(stderr),
            }
        )
    ready = {}
    ledger_evidence = {}
    for arm in ARMS:
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "bind-references",
                str(output[f"{arm}_tapes"]),
                str(output[f"{arm}_reference_catalog"]),
                str(output[f"{arm}_ready"]),
            ],
            logs / f"bind-{arm}.stdout.log",
            logs / f"bind-{arm}.stderr.log",
            f"V187 {arm} reference binding",
        )
        ready[arm] = load_and_validate_manifest(output[f"{arm}_ready"])
        _validate_arm(ready[arm], arm, tapes_bound=True, references_bound=True)
        catalog = read_json(output[f"{arm}_reference_catalog"])
        _require(
            len(catalog.get("entries", {})) == 20,
            f"V187 {arm} reference catalog is not 20",
        )
        count, last_hash = verify_ledger(
            output[f"{arm}_reference_workspace"] / "reference_builds" / "ledger.jsonl"
        )
        ledger_evidence[arm] = {"events": count, "last_hash": last_hash}
    receipt = {
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_REFERENCES_V187_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_reference": True,
        "performance_fields_parsed": 0,
        "dispatches": dispatches,
        "catalog_entry_counts": {arm: 20 for arm in ARMS},
        "catalog_file_sha256": {
            arm: file_hash(output[f"{arm}_reference_catalog"]) for arm in ARMS
        },
        "reference_ledgers": ledger_evidence,
        "ready_manifest_hashes": {arm: ready[arm]["manifest_hash"] for arm in ARMS},
        "ready_manifest_file_sha256": {
            arm: file_hash(output[f"{arm}_ready"]) for arm in ARMS
        },
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["reference_execution"], receipt)
    return receipt


def execute_v187(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    manifests = {
        arm: load_and_validate_manifest(output[f"{arm}_ready"]) for arm in ARMS
    }
    by_arm_seed = {}
    for arm in ARMS:
        _validate_arm(manifests[arm], arm, tapes_bound=True, references_bound=True)
        by_arm_seed[arm] = {run["seed"]: run for run in manifests[arm]["runs"]}
    logs = root / "execution-logs"
    dispatches = []
    for ordinal, item in enumerate(_counterbalanced_order(), start=1):
        arm, seed = item["arm"], item["seed"]
        run = by_arm_seed[arm][seed]
        _reread_goal()
        stdout = logs / f"{ordinal:02d}-{seed}-{arm}.stdout.log"
        stderr = logs / f"{ordinal:02d}-{seed}-{arm}.stderr.log"
        _run_logged(
            [
                str(PYTHON_PATH),
                "-m",
                "scripts.reviewer_experiments.protocol",
                "run",
                str(output[f"{arm}_ready"]),
                str(output[f"{arm}_workspace"]),
                "--run-id",
                run["run_id"],
            ],
            stdout,
            stderr,
            f"V187 online {arm}/{seed}",
        )
        canonical = output[f"{arm}_workspace"] / "canonical" / run["run_id"]
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        _require(
            attempt.get("attempt") == 1
            and attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V187 run is not attempt-one QC pass: {run['run_id']}",
        )
        dispatches.append(
            {
                "ordinal": ordinal,
                "arm": arm,
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
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_EXECUTION_V187_V1",
        "created_at": utc_now(),
        "goal_reread_before_every_online_dispatch": True,
        "performance_fields_parsed": 0,
        "non_nsesche_online_runs": 0,
        "plan_sha256": PLAN_SHA256,
        "fixed_counterbalanced_order": _counterbalanced_order(),
        "dispatches": dispatches,
        "ready_manifest_hashes": {arm: manifests[arm]["manifest_hash"] for arm in ARMS},
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
    _require(len(identities) == 1, "V187 runtime identity is not unanimous")
    binary, git_commit, python_sha, cargo_sha = next(iter(identities))
    _require(
        binary == BINARY_SHA256
        and python_sha == PYTHON_SHA256
        and cargo_sha == CARGO_LOCK_SHA256
        and isinstance(git_commit, str)
        and len(git_commit) == 40,
        "V187 runtime identity changed",
    )
    return {
        "runtime_binary_sha256": binary,
        "runtime_git_commit": git_commit,
        "runtime_python_executable_sha256": python_sha,
        "runtime_cargo_lock_sha256": cargo_sha,
    }


def blind_audit_v187(root: Path = ROOT) -> dict[str, Any]:
    _assert_frozen_inputs()
    output = paths(root)
    _require(not output["blind"].exists(), "V187 blind audit already exists")
    _require(not output["result"].exists(), "V187 result exists before blind audit")
    prepared = read_json(output["prepared"])
    tape_receipt = read_json(output["tape_execution"])
    reference_receipt = read_json(output["reference_execution"])
    execution = read_json(output["execution"])
    receipt_hashes = {
        "prepared": _assert_hashed(prepared, "receipt_hash", "V187 prepared"),
        "tapes": _assert_hashed(tape_receipt, "receipt_hash", "V187 tapes"),
        "references": _assert_hashed(
            reference_receipt, "receipt_hash", "V187 references"
        ),
        "execution": _assert_hashed(execution, "receipt_hash", "V187 execution"),
    }
    _require(
        execution.get("fixed_counterbalanced_order") == _counterbalanced_order()
        and [(item["arm"], item["seed"]) for item in execution["dispatches"]]
        == [(item["arm"], item["seed"]) for item in _counterbalanced_order()]
        and len(execution["dispatches"]) == 40
        and prepared.get("performance_fields_parsed") == 0
        and tape_receipt.get("performance_fields_parsed") == 0
        and reference_receipt.get("performance_fields_parsed") == 0
        and execution.get("performance_fields_parsed") == 0,
        "V187 result-blind receipts changed",
    )
    manifests = {
        arm: load_and_validate_manifest(output[f"{arm}_ready"]) for arm in ARMS
    }
    audits = []
    run_evidence = []
    ledger_evidence = {}
    for arm in ARMS:
        manifest = manifests[arm]
        _validate_arm(manifest, arm, tapes_bound=True, references_bound=True)
        canonical_root = output[f"{arm}_workspace"] / "canonical"
        expected_ids = {run["run_id"] for run in manifest["runs"]}
        actual_ids = {path.name for path in canonical_root.iterdir() if path.is_dir()}
        _require(actual_ids == expected_ids, f"V187 {arm} canonical set changed")
        quarantine = output[f"{arm}_workspace"] / "quarantine"
        _require(
            not quarantine.exists() or not any(quarantine.rglob("attempt-*")),
            f"V187 {arm} quarantine is not empty",
        )
        runner = ProtocolRunner(output[f"{arm}_ready"], output[f"{arm}_workspace"])
        for run in manifest["runs"]:
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
                f"V187 non-clean canonical: {run['run_id']}",
            )
            audits.append(audit)
            run_evidence.append(
                {
                    "arm": arm,
                    "seed": run["seed"],
                    "run_id": run["run_id"],
                    "run_spec_hash": run["run_spec_hash"],
                    "tape_sha256": run["workload_tape"]["sha256"],
                    "reference_sha256": run["reference_dependency"]["sha256"],
                    "result_sha256": attempt["result_sha256"],
                    "attempt_sha256": file_hash(canonical / "attempt.json"),
                    "qc_sha256": file_hash(canonical / "qc_report.json"),
                    "audit_sha256": file_hash(canonical / "manifest.json"),
                }
            )
        count, last_hash = v184._assert_clean_ledger(
            output[f"{arm}_workspace"] / "ledger.jsonl", expected_ids
        )
        reference_count, reference_last_hash = verify_ledger(
            output[f"{arm}_reference_workspace"] / "reference_builds" / "ledger.jsonl"
        )
        ledger_evidence[arm] = {
            "runs": {"events": count, "last_hash": last_hash},
            "references": {
                "events": reference_count,
                "last_hash": reference_last_hash,
            },
        }
    for seed in SEEDS:
        evidence = [item for item in run_evidence if item["seed"] == seed]
        _require(
            len(evidence) == 2 and len({item["tape_sha256"] for item in evidence}) == 1,
            f"V187 {seed} does not have one shared tape hash",
        )
    inventory = {
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_INVENTORY_V187_V1",
        "created_at": utc_now(),
        "status": "pass",
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "run_count": 40,
        "non_nsesche_online_runs": 0,
        "metrics_consulted": False,
        "run_ids": [item["run_id"] for item in run_evidence],
    }
    inventory["inventory_hash"] = object_hash(inventory)
    write_json_atomic(output["inventory"], inventory)
    document = {
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_BLIND_AUDIT_V187_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "training_only": True,
        "formal_results_eligible": False,
        "metrics_consulted": False,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "seeds": list(SEEDS),
        "observed_new_base_tapes": 20,
        "observed_references": 40,
        "observed_online_runs": 40,
        "attempt_one_qc_passes": 40,
        "zero_quarantine": True,
        "exact_paired_cohort": True,
        "non_nsesche_online_runs": 0,
        "receipt_hashes": receipt_hashes,
        "runtime_identity": _runtime_identity(audits),
        "ready_manifests": {
            arm: {
                "path": str(output[f"{arm}_ready"].resolve()),
                "file_sha256": file_hash(output[f"{arm}_ready"]),
                "manifest_hash": manifests[arm]["manifest_hash"],
            }
            for arm in ARMS
        },
        "inventory": {
            "path": str(output["inventory"].resolve()),
            "file_sha256": file_hash(output["inventory"]),
            "inventory_hash": inventory["inventory_hash"],
        },
        "ledgers": ledger_evidence,
        "run_evidence": run_evidence,
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


def _evaluate_training(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_key = {(row.get("arm"), row.get("seed")): row for row in rows}
    _require(
        len(rows) == 40
        and set(by_key) == {(arm, seed) for arm in ARMS for seed in SEEDS},
        "V187 rows are not the exact paired 40-run product",
    )
    gates = {}
    for index, metric in enumerate(METRICS):
        candidate = [by_key[("candidate", seed)].get(metric) for seed in SEEDS]
        control = [by_key[("control", seed)].get(metric) for seed in SEEDS]
        _require(
            all(_finite(value) for value in candidate + control),
            f"V187 {metric} contains nonfinite values",
        )
        candidate_values = [float(value) for value in candidate]
        control_values = [float(value) for value in control]
        differences = [a - b for a, b in zip(candidate_values, control_values)]
        candidate_mean = sum(candidate_values) / 20
        control_mean = sum(control_values) / 20
        difference_mean = sum(differences) / 20
        baseline = FROZEN_BASELINES[metric]
        absolute_pass = candidate_mean > float(baseline["mean"])
        paired_pass = difference_mean >= 0.0 if index == 0 else difference_mean > 0.0
        gates[metric] = {
            "frozen_primary_comparator": baseline["method"],
            "frozen_baseline_mean": baseline["mean"],
            "candidate_mean": candidate_mean,
            "same_tape_control_mean": control_mean,
            "candidate_minus_control_mean": difference_mean,
            "candidate_strictly_exceeds_frozen_baseline_mean": absolute_pass,
            "paired_requirement": "nonnegative" if index == 0 else "strictly_positive",
            "paired_requirement_pass": paired_pass,
            "paired_positive_wins": sum(value > 0.0 for value in differences),
            "paired_ties": sum(value == 0.0 for value in differences),
            "paired_negative_losses": sum(value < 0.0 for value in differences),
            "paired_n": 20,
            "paired_difference_BCa_95_percent_interval": bca_interval(
                differences, n_resamples=10_000, seed=187_000 + index
            ),
            "two_sided_paired_permutation": v186._paired_permutation(
                differences, seed=187_100 + index
            ),
            "passed": absolute_pass and paired_pass,
        }
    return {
        "gates": gates,
        "all_forty_qpr_values_finite": True,
        "all_six_preregistered_performance_requirements_pass": all(
            gate["passed"] for gate in gates.values()
        ),
    }


def reveal_v187(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    _require(not output["result"].exists(), "V187 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V187 blind audit")
    _require(
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("metrics_consulted") is False
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("observed_online_runs") == 40
        and blind.get("attempt_one_qc_passes") == 40
        and blind.get("zero_quarantine") is True
        and blind.get("non_nsesche_online_runs") == 0,
        "V187 blind audit does not authorize reveal",
    )
    _reread_goal()
    rows = []
    for arm in ARMS:
        manifest = load_and_validate_manifest(output[f"{arm}_ready"])
        _validate_arm(manifest, arm, tapes_bound=True, references_bound=True)
        for run in manifest["runs"]:
            summary_path = (
                output[f"{arm}_workspace"]
                / "canonical"
                / run["run_id"]
                / "reviewer_records"
                / run["run_id"]
                / "summary.json"
            )
            summary = read_json(summary_path)
            _require(summary.get("run_complete") is True, f"incomplete {run['run_id']}")
            rows.append(
                {
                    "arm": arm,
                    "method": "sche_nash",
                    "seed": run["seed"],
                    "run_id": run["run_id"],
                    **v184._summary_metrics(summary),
                    "summary_path": str(summary_path),
                    "summary_file_sha256": file_hash(summary_path),
                }
            )
    evaluation = _evaluate_training(rows)
    passed = evaluation["all_six_preregistered_performance_requirements_pass"]
    document = {
        "schema_version": "NSE_E1_LOW_RESPONSE_TIME_OCS_TRAINING_RESULT_V187_V1",
        "created_at": utc_now(),
        "status": "training_pass" if passed else "training_fail",
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "homogeneous_20node_low_closed": False,
        "middle_load_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "seeds": list(SEEDS),
        "same_new_tape_paired_training": True,
        "non_nsesche_online_runs": 0,
        "complete_training_rows": rows,
        "evaluation": evaluation,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
        "decision": (
            "freeze_V187_training_winner_and_preregister_disjoint_low_confirmation"
            if passed
            else "retain_complete_V187_failure_close_axis_and_do_not_advance_to_middle"
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
    functions = {
        "prepare": prepare_v187,
        "capture-tapes": capture_and_bind_tapes_v187,
        "build-references": build_references_v187,
        "execute": execute_v187,
        "blind-audit": blind_audit_v187,
        "reveal": reveal_v187,
    }
    document = functions[action]()
    key = next(
        key
        for key in ("receipt_hash", "blind_audit_hash", "result_hash")
        if key in document
    )
    print(json.dumps({"action": action, key: document[key]}, indent=2))


if __name__ == "__main__":
    main()
