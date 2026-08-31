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


ROOT = Path(
    "tmp/nse_e1_homogeneous_causal_native_expert_closure_training_20260831_v149"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_causal_native_expert_closure_training_plan_v149.json"
)
PLAN_SHA256 = "91d96eb84c5b0bf9afa8d96b52c9f491d72ea944a5611d7e99bcb4b32bd4bfc7"
AMENDMENT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_causal_native_expert_closure_training_amendment_v149a.json"
)
AMENDMENT_SHA256 = "fc4fc6ed6aa869d120b2440a5aaa0bbdb971e95651b396da9fe01adc1727d6ce"

SOURCE_ROOT = Path(
    r"C:\Users\99349\Desktop\serverless_sim_game\tmp\formal_e1_atomic_hpa_reviewer_v3_20260813"
)
SOURCE_MANIFEST = SOURCE_ROOT / "manifest.e1-homogeneous.ready.json"
SOURCE_MANIFEST_SHA256 = (
    "b40b07fa0c97fb9c6ccb7fdf06180f5d81fd2e227bf0246670e03f99b438db12"
)
SOURCE_MANIFEST_HASH = (
    "f073a3a526f5574dbec49fbcf4bbb52b43760f964cdda08104d79bf51387af5e"
)
SOURCE_RUNS = SOURCE_ROOT / "analysis/strict-runtime-v2/runs-physical-e1.csv"
SOURCE_RUNS_SHA256 = "319f16749c4cdc875b20ee3433a7e0585e9ecaa30181caf21360be19d383e348"
SOURCE_SUMMARY = (
    SOURCE_ROOT / "analysis/strict-runtime-v2/stats-e1-physical/summary.csv"
)
SOURCE_SUMMARY_SHA256 = (
    "b7b340419418d514208bd8365d30751e39c918ac4bd6c03f35bdf1cb99dda9a3"
)
SOURCE_PAIRING = SOURCE_ROOT / "pairing-audit-runtime-v2.json"
SOURCE_PAIRING_SHA256 = (
    "ab23569221780f9c7d1d205f29acb4138d42b047dcef5663e5994354aba2a5e5"
)

BINARY_PATH = Path("serverless_sim/target_e1_closure/release/serverless_sim.exe")
BINARY_SHA256 = "1f961825848a50c20f1d93e749fb3744fa6718120e8919ac1f9da46c4930a281"
BINARY_SOURCE_COMMIT = "73712b6ffaeb0369867d2422de83b177e1b4e004"
PYTHON_PATH = Path(r"D:\Anaconda3\python.exe")
PYTHON_SHA256 = "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
CARGO_LOCK = Path("serverless_sim/Cargo.lock")
CARGO_LOCK_SHA256 = "17fe8bce08ba31f9edda8e6e331641cb7d981c1c9f1e21e7bf09178da6dd3205"
MODULE_CONF = Path("serverless_sim/module_conf_es.json")
MODULE_CONF_SHA256 = "788a81b38e47b44b591953045565a835364a860f7ae071b69f30e2720631bd0e"

ARM_ID = "v149-e1-homogeneous-causal-native-expert-closure-nash"
PROFILE = "causal_steady_load_ocs_faasrank_jiagu_closure_nash"
RUN_ORDER_SEED = "NSE-V149-E1-HOMOGENEOUS-CAUSAL-NATIVE-EXPERT-E01-E20"
PORT = "3199"
LOADS = ["low", "middle", "high"]
SEEDS = [f"E{index:02d}" for index in range(1, 21)]
HIGH_GATE_THRESHOLD = 70
MIDDLE_GATE_THRESHOLD = 213


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-manifest-v149.json",
        "schedule": root / "frozen-run-order-v149.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "workspace": root / "formal-runs",
        "pairing": root / "pairing-audit-v149.json",
    }


def _assert_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or file_hash(path) != expected_sha256:
        raise RuntimeError(f"{label} is missing or changed: {path}")


def _assert_frozen_inputs() -> dict[str, Any]:
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V149 plan"),
        (AMENDMENT, AMENDMENT_SHA256, "V149 lifecycle amendment"),
        (SOURCE_MANIFEST, SOURCE_MANIFEST_SHA256, "frozen E1 manifest"),
        (SOURCE_RUNS, SOURCE_RUNS_SHA256, "frozen E1 physical rows"),
        (SOURCE_SUMMARY, SOURCE_SUMMARY_SHA256, "frozen E1 summary"),
        (SOURCE_PAIRING, SOURCE_PAIRING_SHA256, "frozen E1 pairing audit"),
        (BINARY_PATH, BINARY_SHA256, "V149 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python executable"),
        (CARGO_LOCK, CARGO_LOCK_SHA256, "V149 Cargo.lock"),
        (MODULE_CONF, MODULE_CONF_SHA256, "V149 module_conf_es.json"),
    ):
        _assert_file(path, sha256, label)
    source = read_json(SOURCE_MANIFEST)
    if (
        source.get("manifest_hash") != SOURCE_MANIFEST_HASH
        or source.get("formal_results_eligible") is not True
        or source.get("seed_stage") != "all"
        or len(source.get("runs", [])) != 600
    ):
        raise RuntimeError("frozen E1 source manifest boundary changed")
    pairing = read_json(SOURCE_PAIRING)
    if pairing.get("passed") is not True or pairing.get("run_count") != 600:
        raise RuntimeError("frozen E1 pairing audit is not a 600-run pass")
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str | None = None
) -> dict[str, Any]:
    if protocol_source_commit is None:
        protocol_source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V149 protocol source commit is invalid")
    source_ids = [
        run["run_id"] for run in source["runs"] if run.get("method") == "sche_nash"
    ]
    if len(source_ids) != 60:
        raise RuntimeError("frozen E1 source no longer has exactly 60 NSESche runs")
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        source_ids,
        purpose=(
            "V149 adaptive in-sample E1 homogeneous closure training only; "
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
                "V149 adaptive in-sample E1 homogeneous closure training only; "
                "never a formal result or paper superiority claim"
            ),
            "v149_role": "adaptive_training_candidate",
            "v149_plan_sha256": PLAN_SHA256,
            "v149_amendment_sha256": AMENDMENT_SHA256,
            "v149_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v149_protocol_source_commit": protocol_source_commit,
            "v149_binary_sha256": BINARY_SHA256,
            "v149_arm_id": ARM_ID,
            "v149_profile": PROFILE,
            "v149_expected_run_count": 60,
            "v149_expected_reference_build_count": 60,
            "v149_reused_frozen_baseline_runs": 600,
            "v149_baseline_rerun_count": 0,
            "v149_performance_results_consulted_for_design": True,
            "v149_candidate_performance_summaries_parsed": 0,
            "v149_confirmation_inputs_generated": False,
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
        run["environment"]["NASH_OPERATIONAL_DIRECT_INITIALIZATION"] = "1"
        run["metadata"] = {
            "v149_training_only": True,
            "v149_role": "adaptive_training_candidate",
            "v149_plan_sha256": PLAN_SHA256,
            "v149_amendment_sha256": AMENDMENT_SHA256,
            "v149_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v149_protocol_source_commit": protocol_source_commit,
            "v149_binary_sha256": BINARY_SHA256,
            "v149_arm_id": ARM_ID,
            "v149_profile": PROFILE,
            "v149_source_e1_run_id": source_run_id,
            "v149_source_e1_run_spec_hash": source_run_spec_hash,
            "v149_classifier": (
                "first_seen_arrivals_frame20_ge70_high_else_"
                "frame100_ge213_middle_else_low"
            ),
            "v149_initial_route": "ocs",
            "v149_low_route": "ocs_with_fresh_stateless_orion_projection_advisory",
            "v149_middle_route": "fresh_faasrank_at_frame100",
            "v149_high_route": "fresh_jiagu_at_frame20",
            "v149_selected_state_only": True,
            "v149_same_cohort_service_welfare_certificate": True,
            "v149_outcome_fields_drive_policy": False,
            "v149_request_freq_or_scenario_label_drive_policy": False,
            "v149_future_arrivals_drive_policy": False,
            "v149_candidate_performance_summaries_parsed_before_run": 0,
            "v149_confirmation_inputs_generated": False,
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
        raise RuntimeError("V149 load/seed product changed")
    if {run["method"] for run in manifest["runs"]} != {"sche_nash"}:
        raise RuntimeError("V149 method product changed")
    if len(manifest["reference_build_dependencies"]) != 60:
        raise RuntimeError("V149 reference product changed")
    if manifest.get("all_references_bound") is not False:
        raise RuntimeError("V149 unbound manifest unexpectedly claims bound references")
    for run in manifest["runs"]:
        if (
            run["experiment_id"] != "E1"
            or run["cluster"] != {"node_count": 20, "topology": "homogeneous"}
            or run["workload"]["topology"] != "homogeneous"
            or run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY") != PROFILE
            or run["environment"].get("NASH_OPERATIONAL_DIRECT_INITIALIZATION") != "1"
            or run.get("metadata", {}).get("v149_selected_state_only") is not True
            or run["reference_dependency"].get("build_required") is not True
        ):
            raise RuntimeError(f"V149 run contract changed: {run.get('run_id')}")


def _classifier_input_evidence(source: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for run in source["runs"]:
        if run.get("method") != "sche_nash":
            continue
        tape = run["workload_tape"]
        tape_path = Path(tape["path"])
        if not tape_path.is_file() or file_hash(tape_path) != tape["sha256"]:
            raise RuntimeError(
                f"V149 classifier tape is missing or changed: {tape_path}"
            )
        tape_document = read_json(tape_path)
        events = tape_document.get("events")
        if not isinstance(events, list) or len(events) != tape["event_count"]:
            raise RuntimeError("V149 classifier tape event product changed")
        frame20 = sum(
            int(isinstance(event, dict) and event.get("frame", 20) < 20)
            for event in events
        )
        frame100 = sum(
            int(isinstance(event, dict) and event.get("frame", 100) < 100)
            for event in events
        )
        load = run["workload"]["request_freq"]
        separated = (
            (load == "high" and frame20 >= HIGH_GATE_THRESHOLD)
            or (
                load == "middle"
                and frame20 < HIGH_GATE_THRESHOLD
                and frame100 >= MIDDLE_GATE_THRESHOLD
            )
            or (
                load == "low"
                and frame20 < HIGH_GATE_THRESHOLD
                and frame100 < MIDDLE_GATE_THRESHOLD
            )
        )
        if not separated:
            raise RuntimeError(
                f"V149 causal classifier does not separate frozen input {load}/{run['seed']}"
            )
        evidence.append(
            {
                "load": load,
                "seed": run["seed"],
                "tape_path": str(tape_path),
                "tape_sha256": tape["sha256"],
                "first_seen_arrivals_frames_0_through_19": frame20,
                "first_seen_arrivals_frames_0_through_99": frame100,
            }
        )
    if len(evidence) != 60 or {(item["load"], item["seed"]) for item in evidence} != {
        (load, seed) for load in LOADS for seed in SEEDS
    }:
        raise RuntimeError(
            "V149 classifier input evidence is not an exact 60-cell product"
        )
    return evidence


def _frozen_schedule(manifest: dict[str, Any]) -> dict[str, Any]:
    cells = [
        {
            "load": run["workload"]["request_freq"],
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
        "schema_version": "NSE_E1_HOMOGENEOUS_CAUSAL_NATIVE_EXPERT_CLOSURE_RUN_ORDER_V149_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "amendment_sha256": AMENDMENT_SHA256,
        "run_order_seed": RUN_ORDER_SEED,
        "randomization_unit": "sixty_load_by_seed_candidate_cells",
        "schedule": schedule,
    }
    document["schedule_hash"] = object_hash(document)
    return document


def prepare_v149(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    classifier_evidence = _classifier_input_evidence(source)
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V149 training root: {root}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_CAUSAL_NATIVE_EXPERT_CLOSURE_PREPARED_V149_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "performance_results_consulted_for_design": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "amendment_path": str(AMENDMENT),
        "amendment_sha256": AMENDMENT_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "implementation_frozen_before_manifest_generation": True,
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
        "reused_frozen_baseline_runs": 600,
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
        "profile": PROFILE,
        "classifier_input_evidence": classifier_evidence,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def main() -> None:
    receipt = prepare_v149()
    print(json.dumps({"receipt_hash": receipt["receipt_hash"], "runs": 60}))


if __name__ == "__main__":
    main()
