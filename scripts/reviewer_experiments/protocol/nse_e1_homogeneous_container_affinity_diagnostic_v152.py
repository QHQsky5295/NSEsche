from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_prepare_v149 import (
    CARGO_LOCK,
    CARGO_LOCK_SHA256,
    MODULE_CONF,
    MODULE_CONF_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_HASH,
    SOURCE_MANIFEST_SHA256,
    SOURCE_PAIRING,
    SOURCE_PAIRING_SHA256,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
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


ROOT = Path("tmp/nse_e1_homogeneous_container_affinity_diagnostic_20260831_v152")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_container_affinity_diagnostic_plan_v152.json"
)
PLAN_SHA256 = "2cd698dc4b7a2100dbfba9dd50b29887884fddcf831a539e62d6245db171a4e1"
V151_ROOT = Path("tmp/nse_e1_homogeneous_cross_scenario_anchor_training_20260831_v151")
V151_RESULT = V151_ROOT / "training-result-v151.json"
V151_RESULT_SHA256 = "bc1e81fcf023c2ed952f787112ea4933c27bcc862afb126ab25c5cdcf4df12c0"
V151_RESULT_HASH = "b4e23b9a6643f88cc59948d41fd073e0871f565587be19035e0f96da86545f06"
V151_READY = (
    V151_ROOT / "manifest.v151-e1-homogeneous-cross-scenario-anchors.ready.json"
)
V151_WORKSPACE = V151_ROOT / "formal-runs"

BINARY_PATH = Path("serverless_sim/target_e1_closure/release/serverless_sim.exe")
BINARY_SHA256 = "5763f745cf01309ade6a5c1ac01838e15706373e30ad24a7384a5c5deff206a7"
BINARY_SOURCE_COMMIT = "7cbc957b03bf35695704b9f39bea92b20f06088a"
ARM_ID = "v152-middle-srpt-ready-stable-function-affinity"
PROFILE = "srpt_ready_stable_function_affinity"
SEEDS = ("E09", "E17")
PORT = "3203"
COMMON_ENVIRONMENT = {
    "NASH_OPERATIONAL_DIRECT_INITIALIZATION": "1",
    "NASH_OPERATIONAL_INDIFFERENCE_EPSILON": "15.0",
    "NASH_OPERATIONAL_SWITCH_THRESHOLD": "0.0",
    "NASH_OPERATIONAL_ADAPTIVE_PROXY": "0",
    "NASH_OPERATIONAL_STRUCTURAL_PROXY": "0",
    "NASH_OPERATIONAL_HYBRID_PROXY": "1",
    "NASH_OPERATIONAL_BOUNDED_PROXY": "0",
    "NASH_OPERATIONAL_QUEUE_WEIGHT": "0.20",
    "NASH_OPERATIONAL_COLD_START_WEIGHT": "0.55",
    "NASH_OPERATIONAL_PROJECTED_LOAD_WEIGHT": "1.0",
    "NASH_OPERATIONAL_RESOURCE_WEIGHT": "0.15",
    "NASH_OPERATIONAL_UNRESTRICTED_INITIALIZATION": "1",
}
LEGAL_NOT_REQUESTED_TERMINATIONS = {
    "no_players",
    "inner_iteration_limit",
    "oscillation_guard",
}


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v152.json",
        "schedule": root / "frozen-run-order-v152.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v152.json",
        "pairing": root / "pairing-audit-v152.json",
        "blind": root / "joint-blind-audit-v152.json",
        "result": root / "diagnostic-result-v152.json",
    }


def _assert_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or file_hash(path) != expected_sha256:
        raise RuntimeError(f"{label} is missing or changed: {path}")


def _assert_hashed(document: Mapping[str, Any], field: str, label: str) -> str:
    payload = dict(document)
    claimed = payload.pop(field, None)
    if not isinstance(claimed, str) or object_hash(payload) != claimed:
        raise RuntimeError(f"{label} self-hash changed")
    return claimed


def _assert_frozen_inputs() -> dict[str, Any]:
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V152 plan"),
        (SOURCE_MANIFEST, SOURCE_MANIFEST_SHA256, "frozen E1 manifest"),
        (SOURCE_PAIRING, SOURCE_PAIRING_SHA256, "frozen E1 pairing audit"),
        (V151_RESULT, V151_RESULT_SHA256, "V151 result"),
        (BINARY_PATH, BINARY_SHA256, "V152 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python executable"),
        (CARGO_LOCK, CARGO_LOCK_SHA256, "frozen Cargo.lock"),
        (MODULE_CONF, MODULE_CONF_SHA256, "frozen module_conf_es.json"),
    ):
        _assert_file(path, sha256, label)
    source = read_json(SOURCE_MANIFEST)
    if not (
        source.get("manifest_hash") == SOURCE_MANIFEST_HASH
        and source.get("formal_results_eligible") is True
        and source.get("seed_stage") == "all"
        and len(source.get("runs", [])) == 600
    ):
        raise RuntimeError("frozen E1 source manifest boundary changed")
    pairing = read_json(SOURCE_PAIRING)
    if pairing.get("passed") is not True or pairing.get("run_count") != 600:
        raise RuntimeError("frozen E1 pairing boundary changed")
    v151 = read_json(V151_RESULT)
    if not (
        _assert_hashed(v151, "result_hash", "V151 result") == V151_RESULT_HASH
        and v151.get("all_nine_training_gates_pass") is False
        and v151.get("candidate_run_count") == 60
        and v151.get("valid_seed_deletion_replacement_relabeling_or_selective_rerun")
        is False
    ):
        raise RuntimeError("V151 retained-result boundary changed")
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V152 protocol source commit is invalid")
    selected = [
        run
        for run in source["runs"]
        if run.get("method") == "sche_nash"
        and run.get("seed") in SEEDS
        and run.get("workload", {}).get("request_freq") == "middle"
        and run.get("cluster") == {"node_count": 20, "topology": "homogeneous"}
    ]
    if len(selected) != 2 or {run["seed"] for run in selected} != set(SEEDS):
        raise RuntimeError("frozen E1 source no longer has exact V152 inputs")
    by_seed = {run["seed"]: run for run in selected}
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        [by_seed[seed]["run_id"] for seed in SEEDS],
        purpose=(
            "V152 input-selected two-point E1 middle-load mechanism diagnostic; "
            "never a formal result or paper superiority claim"
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
                "V152 input-selected two-point E1 middle-load mechanism diagnostic; "
                "never a formal result or paper superiority claim"
            ),
            "v152_role": "result_blind_mechanism_diagnostic",
            "v152_plan_sha256": PLAN_SHA256,
            "v152_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v152_protocol_source_commit": protocol_source_commit,
            "v152_binary_sha256": BINARY_SHA256,
            "v152_arm_id": ARM_ID,
            "v152_profile": PROFILE,
            "v152_environment": COMMON_ENVIRONMENT,
            "v152_expected_run_count": 2,
            "v152_expected_reference_build_count": 2,
            "v152_fixed_order": list(SEEDS),
            "v152_input_selection_only": True,
            "v152_candidate_performance_summaries_parsed": 0,
            "v152_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"].update(COMMON_ENVIRONMENT)
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v152_training_only": True,
            "v152_role": "result_blind_mechanism_diagnostic",
            "v152_plan_sha256": PLAN_SHA256,
            "v152_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v152_protocol_source_commit": protocol_source_commit,
            "v152_binary_sha256": BINARY_SHA256,
            "v152_arm_id": ARM_ID,
            "v152_profile": PROFILE,
            "v152_source_e1_run_id": source_run_id,
            "v152_source_e1_run_spec_hash": source_run_spec_hash,
            "v152_seed_selected_by_input_only_extreme": True,
            "v152_candidate_performance_summaries_parsed_before_run": 0,
            "v152_confirmation_inputs_generated": False,
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
    marker["selected_run_count"] = 2
    marker["selected_reference_build_count"] = 2
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == 2
        and {run["seed"] for run in manifest["runs"]} == set(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and {
            (run["workload"]["request_freq"], run["cluster"]["node_count"])
            for run in manifest["runs"]
        }
        == {("middle", 20)}
        and len(manifest.get("reference_build_dependencies", [])) == 2
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V152 exact two-cell product changed")
    for run in manifest["runs"]:
        expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
        if (
            run["experiment_id"] != "E1"
            or run["cluster"]["topology"] != "homogeneous"
            or any(
                run["environment"].get(key) != value for key, value in expected.items()
            )
            or run.get("metadata", {}).get("v152_profile") != PROFILE
        ):
            raise RuntimeError(f"V152 run contract changed: {run.get('run_id')}")


def prepare_v152(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V152 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AFFINITY_RUN_ORDER_V152_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "selection_rule": "middle input-only minimum and maximum arrival-weighted DAG size",
        "schedule": [
            {"ordinal": ordinal, "seed": seed, "source": "input_only_extreme"}
            for ordinal, seed in enumerate(SEEDS, start=1)
        ],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AFFINITY_PREPARED_V152_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_sha256": MODULE_CONF_SHA256,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "v151_result_file_sha256": V151_RESULT_SHA256,
        "v151_result_hash": V151_RESULT_HASH,
        "candidate_online_runs": 2,
        "candidate_reference_builds": 2,
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "environment": COMMON_ENVIRONMENT,
        "aggregation_contract": {
            "placement_dispersion_mean": (
                "arithmetic mean of finite placement_dispersion_normalized over "
                "windows with assigned_players > 0"
            ),
            "container_mean": "arithmetic mean of containers_total over all 1000 windows",
            "container_p95": "type-7 linearly interpolated p95 over all 1000 windows",
        },
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v152(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V152 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V152 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    dispatches = []
    log_root = root / "execution-logs"
    log_root.mkdir(parents=True, exist_ok=True)
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = log_root / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = log_root / f"{ordinal:02d}-{seed}.stderr.log"
        command = [
            str(PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "run",
            str(output["ready"]),
            str(output["workspace"]),
            "--run-id",
            run["run_id"],
        ]
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(f"V152 dispatch {seed} failed: {completed.returncode}")
        canonical = output["workspace"] / "canonical" / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        if not (
            attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
        ):
            raise RuntimeError(f"V152 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "exit_code": completed.returncode,
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "stdout_path": str(stdout_path),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_path": str(stderr_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AFFINITY_EXECUTION_V152_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": 2,
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    run_configs = 0
    windows = 0
    summaries = 0
    offline = 0
    not_requested = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for raw in stream:
            event = json.loads(raw)
            kind = event.get("kind")
            if kind == "run_config":
                run_configs += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("operational_direct_initialization") is True
                    and event.get("operational_unrestricted_initialization") is True
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                ):
                    raise RuntimeError("V152 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != windows:
                    raise RuntimeError("V152 window sequence changed")
                social = event.get("social", {})
                solver = event.get("solver", {})
                if social.get("reference_state_key") is None:
                    if not (
                        social.get("reference_source") == "not_requested"
                        and solver.get("termination")
                        in LEGAL_NOT_REQUESTED_TERMINATIONS
                    ):
                        raise RuntimeError(
                            "V152 reference-not-requested reason changed"
                        )
                    not_requested += 1
                elif social.get("reference_source") in {
                    "offline_table",
                    "offline_table_nonpositive",
                }:
                    offline += 1
                else:
                    raise RuntimeError("V152 offline reference replay changed")
                decision = event.get("decision", {})
                if not (
                    isinstance(decision.get("assigned_players"), int)
                    and isinstance(
                        decision.get("placement_dispersion_normalized"), (int, float)
                    )
                    and isinstance(
                        event.get("cluster", {}).get("containers_total"), int
                    )
                ):
                    raise RuntimeError("V152 mechanism telemetry is incomplete")
                windows += 1
            elif kind == "run_summary":
                summaries += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V152 terminal marker changed")
            elif kind != "function_profile":
                raise RuntimeError(f"unexpected V152 Nash event: {kind}")
    if run_configs != 1 or windows != 1000 or summaries != 1 or offline == 0:
        raise RuntimeError("V152 Nash log cardinality or reference coverage changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "nash_metrics_sha256": file_hash(log),
        "windows": windows,
        "offline_reference_windows": offline,
        "legitimate_not_requested_windows": not_requested,
    }


def _validate_reference_catalog(
    manifest: Mapping[str, Any],
    catalog_path: Path,
    *,
    expected_entry_count: int = 2,
) -> dict[str, Any]:
    catalog = read_json(catalog_path)
    catalog_hash = _assert_hashed(catalog, "catalog_hash", "V152 reference catalog")
    entries = catalog.get("entries")
    expected = {item["key"] for item in manifest["reference_build_dependencies"]}
    if (
        not isinstance(entries, Mapping)
        or set(entries) != expected
        or len(entries) != expected_entry_count
    ):
        raise RuntimeError("V152 reference catalog product changed")
    for item in entries.values():
        if (
            not Path(item["path"]).is_file()
            or file_hash(Path(item["path"])) != item["sha256"]
            or file_hash(Path(item["receipt_path"])) != item["receipt_sha256"]
        ):
            raise RuntimeError("V152 reference artifact hash changed")
    return {"catalog_hash": catalog_hash, "entry_count": expected_entry_count}


def blind_audit_v152(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V152 blind audit already exists")
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V152 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V152 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed") is True
        and pairing.get("run_count") == 2
        and pairing.get("group_count") == 2
    ):
        raise RuntimeError("V152 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_path = output["workspace"] / "ledger.jsonl"
    ledger_count, ledger_hash = verify_ledger(ledger_path)
    reference = _validate_reference_catalog(manifest, output["catalog"])
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V152 fixed execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V152 canonical directory product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V152 has unexplained quarantined attempts")
    audits = []
    identities = set()
    for seed in SEEDS:
        run = by_seed[seed]
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit = read_json(canonical / "manifest.json")
        software = audit.get("software_environment", {})
        identities.add(
            (
                audit.get("adapter_binary", {}).get("verified_sha256"),
                software.get("git", {}).get("commit"),
                software.get("python", {}).get("executable_sha256"),
                software.get("cargo_lock", {}).get("sha256"),
            )
        )
        audits.append(_audit_nash_log(canonical, run))
    if len(identities) != 1:
        raise RuntimeError("V152 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V152 runtime identity changed")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AFFINITY_BLIND_AUDIT_V152_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_path": str(output["pairing"]),
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "run_count": 2,
        "window_count": sum(item["windows"] for item in audits),
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": PROFILE,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _p95_type7(values: Sequence[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise RuntimeError("cannot compute V152 p95 from an empty sequence")
    rank = 0.95 * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (rank - lower) * (ordered[upper] - ordered[lower])


def _diagnostic_metrics(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    record_root = canonical / "reviewer_records" / run_id
    summary = read_json(record_root / "summary.json")
    fixed = summary.get("fixed_observation_window", {})
    completed = fixed.get("completed")
    throughput = fixed.get("throughput_requests_per_second")
    if not (
        isinstance(completed, int)
        and isinstance(throughput, (int, float))
        and math.isfinite(throughput)
    ):
        raise RuntimeError("V152 fixed-window metrics are invalid")
    dispersions = []
    containers = []
    log = record_root / "nash_metrics.jsonl.gz"
    windows = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for raw in stream:
            event = json.loads(raw)
            if event.get("kind") != "window":
                continue
            decision = event["decision"]
            dispersion = decision["placement_dispersion_normalized"]
            assigned = decision["assigned_players"]
            container_count = event["cluster"]["containers_total"]
            if assigned > 0:
                if not isinstance(dispersion, (int, float)) or not math.isfinite(
                    dispersion
                ):
                    raise RuntimeError("V152 nonempty-window dispersion is invalid")
                dispersions.append(float(dispersion))
            if not isinstance(container_count, int) or container_count < 0:
                raise RuntimeError("V152 container count is invalid")
            containers.append(float(container_count))
            windows += 1
    if windows != 1000 or not dispersions or len(containers) != 1000:
        raise RuntimeError("V152 diagnostic telemetry product changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "fixed_window_completed": completed,
        "fixed_window_throughput_requests_per_second": float(throughput),
        "placement_dispersion_nonempty_window_count": len(dispersions),
        "placement_dispersion_nonempty_window_mean": statistics.fmean(dispersions),
        "container_count_window_count": len(containers),
        "container_count_mean": statistics.fmean(containers),
        "container_count_p95_type7": _p95_type7(containers),
    }


def reveal_v152(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V152 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V152 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
    ):
        raise RuntimeError("V152 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    v151_manifest = load_and_validate_manifest(V151_READY)
    candidate_by_seed = {run["seed"]: run for run in manifest["runs"]}
    baseline_by_seed = {
        run["seed"]: run
        for run in v151_manifest["runs"]
        if run["workload"]["request_freq"] == "middle" and run["seed"] in SEEDS
    }
    if set(candidate_by_seed) != set(SEEDS) or set(baseline_by_seed) != set(SEEDS):
        raise RuntimeError("V152 reveal comparison product changed")
    comparisons = {}
    for seed in SEEDS:
        candidate_run = candidate_by_seed[seed]
        baseline_run = baseline_by_seed[seed]
        candidate = _diagnostic_metrics(
            output["workspace"] / "canonical" / candidate_run["run_id"],
            candidate_run,
        )
        baseline = _diagnostic_metrics(
            V151_WORKSPACE / "canonical" / baseline_run["run_id"], baseline_run
        )
        comparisons[seed] = {"candidate": candidate, "v151_baseline": baseline}
    e17 = comparisons["E17"]
    e17_gates = {
        "fixed_window_completed_strictly_positive": (
            e17["candidate"]["fixed_window_completed"] > 0
        ),
        "placement_dispersion_mean_lower_than_v151": (
            e17["candidate"]["placement_dispersion_nonempty_window_mean"]
            < e17["v151_baseline"]["placement_dispersion_nonempty_window_mean"]
        ),
        "container_mean_or_p95_lower_than_v151": (
            e17["candidate"]["container_count_mean"]
            < e17["v151_baseline"]["container_count_mean"]
            or e17["candidate"]["container_count_p95_type7"]
            < e17["v151_baseline"]["container_count_p95_type7"]
        ),
    }
    e09 = comparisons["E09"]
    e09_threshold = (
        0.90 * e09["v151_baseline"]["fixed_window_throughput_requests_per_second"]
    )
    e09_gates = {
        "throughput_at_least_90_percent_of_v151": (
            e09["candidate"]["fixed_window_throughput_requests_per_second"]
            >= e09_threshold
        ),
        "fixed_window_completed_strictly_positive": (
            e09["candidate"]["fixed_window_completed"] > 0
        ),
    }
    joint_pass = all(e17_gates.values()) and all(e09_gates.values())
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AFFINITY_DIAGNOSTIC_RESULT_V152_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_hash": blind_hash,
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "candidate_run_count": 2,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "comparisons": comparisons,
        "E17_gates": e17_gates,
        "E09_throughput_threshold_requests_per_second": e09_threshold,
        "E09_gates": e09_gates,
        "joint_mechanism_gate_pass": joint_pass,
        "disposition": (
            "eligible_only_for_separately_preregistered_complete_middle_E01_E20_training_block"
            if joint_pass
            else "retain_both_runs_and_retire_affinity_mechanism_without_threshold_tuning"
        ),
        "full_middle_training_inputs_generated": False,
        "homogeneous_claim_closed": False,
        "later_experiment_execution_authorized": False,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("prepare", "execute", "blind-audit", "reveal")
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    if action == "prepare":
        document = prepare_v152()
        key = "receipt_hash"
    elif action == "execute":
        document = execute_v152()
        key = "receipt_hash"
    elif action == "blind-audit":
        document = blind_audit_v152()
        key = "blind_audit_hash"
    else:
        document = reveal_v152()
        key = "result_hash"
    print(json.dumps({key: document[key], "runs": 2}))


if __name__ == "__main__":
    main()
