from __future__ import annotations

import argparse
import gzip
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    _evaluate_load,
    _load_baselines,
    _metrics,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    PYTHON_PATH,
    PYTHON_SHA256,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_HASH,
    SOURCE_MANIFEST_SHA256,
    SOURCE_PAIRING_SHA256,
    _assert_file,
    _assert_hashed,
    _validate_reference_catalog,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_legacy_profile_training_prepare_v150 import (
    COMMON_ENVIRONMENT,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_queue8_low_training_v155 import (
    CARGO_LOCK_SHA256,
    MODULE_CONF_SEMANTIC_HASH,
    ROOT as V155_ROOT,
    _assert_frozen_inputs as _assert_v155_frozen_inputs,
    _assert_json_semantic,
    _load_candidate as _load_v155_candidate,
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


ROOT = Path("tmp/nse_e1_homogeneous_pipeline_queue8_low_diagnostic_20260831_v156")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_pipeline_queue8_low_diagnostic_plan_v156.json"
)
PLAN_SHA256 = "410b0b02585e33b8786f35e82565df3fb950f81b9c579e2c8d20f845e1b46dba"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_pipeline_queue8_low_diagnostic_implementation_v156.json"
)
IMPLEMENTATION_SHA256 = (
    "b694cb636864a7069ecfe9b4fbcecfb6de2af226d706ae6e4ac4e1b9041fa495"
)
V155_RESULT = V155_ROOT / "training-result-v155.json"
V155_RESULT_SHA256 = "bdb92c0505cd3cbb3774c332f5bf9202fc93ae216e951938ecff47c66404457a"
V155_RESULT_HASH = "d13908a16458d8c90faeb72875a08f197af263c9af6016f9dd2c7246f0de1fb0"
V155_READY = V155_ROOT / "manifest.v155-low-srpt-ready-hiku2-ocs-queue8.ready.json"

ARM_ID = "v156-low-srpt-pipeline-hiku2-ocs-queue8"
PROFILE = "srpt_pipeline_hiku2_ocs_queue8"
LOW_EXPERT = "srpt_ready_hiku2_ocs_borda"
HIGH_EXPERT = "srpt_ready_ocs_current_demand"
QUEUE_THRESHOLD = 8.0
SEEDS = ("E09", "E18", "E20")
PORT = "3207"
BINARY_SOURCE_COMMIT = "182a2026ef14c154ec2f38cd659d4823f5314e5f"
BINARY_PATH = Path("serverless_sim/target_e1_v156/release/serverless_sim.exe")
BINARY_SHA256 = "b68c2ee09d0d75eee7c30e6ee447202fe332a488d8f9df3d3acf400ba6e8aa18"
MODULE_CONF_FILE_SHA256_AT_BUILD = (
    "9b607f7c450cbf9fd63f8cb102846570d9a437761371054f73f7c7df5aa46a83"
)
THROUGHPUT_THREE_SEED_SUM_GATE = 4.042
QPR_THREE_SEED_SUM_GATE = 0.187264280342794


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v156.json",
        "schedule": root / "frozen-run-order-v156.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v156.json",
        "pairing": root / "pairing-audit-v156.json",
        "blind": root / "joint-blind-audit-v156.json",
        "result": root / "diagnostic-result-v156.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = _assert_v155_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V156 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V156 implementation receipt"),
        (V155_RESULT, V155_RESULT_SHA256, "V155 result"),
        (BINARY_PATH, BINARY_SHA256, "V156 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    implementation = read_json(IMPLEMENTATION)
    release = implementation.get("release", {})
    change = implementation.get("single_scientific_change", {})
    if not (
        implementation.get("implementation_git_commit") == BINARY_SOURCE_COMMIT
        and implementation.get("plan_file_sha256") == PLAN_SHA256
        and release.get("sha256") == BINARY_SHA256
        and release.get("cargo_lock_sha256") == CARGO_LOCK_SHA256
        and implementation.get("profile") == PROFILE
        and change.get("from_player_frontier") == "parents_completed"
        and change.get("to_player_frontier") == "parents_scheduled"
        and change.get("unchanged_v155_router") is True
        and change.get("changes_paper_formula_welfare_pricing_hpa_metrics_or_reference")
        is False
    ):
        raise RuntimeError("V156 implementation boundary changed")
    v155 = read_json(V155_RESULT)
    if not (
        _assert_hashed(v155, "result_hash", "V155 result") == V155_RESULT_HASH
        and v155.get("candidate_run_count") == 20
        and v155.get("joint_training_pass") is False
        and v155.get("confirmation_inputs_generated") is False
    ):
        raise RuntimeError("V155 result boundary changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V156 protocol source commit is invalid")
    selected = [
        run
        for run in source["runs"]
        if run.get("method") == "sche_nash"
        and run.get("seed") in SEEDS
        and run.get("workload", {}).get("request_freq") == "low"
        and run.get("cluster") == {"node_count": 20, "topology": "homogeneous"}
    ]
    if len(selected) != 3 or {run["seed"] for run in selected} != set(SEEDS):
        raise RuntimeError("frozen source no longer has the V156 diagnostic product")
    by_seed = {run["seed"]: run for run in selected}
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        [by_seed[seed]["run_id"] for seed in SEEDS],
        purpose=(
            "V156 outcome-disclosed three-seed pipeline-frontier diagnostic; "
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
                "V156 outcome-disclosed three-seed pipeline-frontier diagnostic; "
                "never a formal result or paper superiority claim"
            ),
            "v156_role": "result_blind_pipeline_frontier_falsification",
            "v156_plan_sha256": PLAN_SHA256,
            "v156_implementation_sha256": IMPLEMENTATION_SHA256,
            "v156_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v156_protocol_source_commit": protocol_source_commit,
            "v156_binary_sha256": BINARY_SHA256,
            "v156_arm_id": ARM_ID,
            "v156_profile": PROFILE,
            "v156_player_frontier": "parents_scheduled",
            "v156_single_change_from_v155": "parents_completed_to_parents_scheduled",
            "v156_queue_density_threshold": QUEUE_THRESHOLD,
            "v156_environment": COMMON_ENVIRONMENT,
            "v156_expected_run_count": 3,
            "v156_expected_reference_build_count": 3,
            "v156_fixed_order": list(SEEDS),
            "v156_candidate_performance_summaries_parsed": 0,
            "v156_remaining_seventeen_authorized": False,
            "v156_confirmation_inputs_generated": False,
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
            "v156_training_only": True,
            "v156_role": "result_blind_pipeline_frontier_falsification",
            "v156_plan_sha256": PLAN_SHA256,
            "v156_implementation_sha256": IMPLEMENTATION_SHA256,
            "v156_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v156_protocol_source_commit": protocol_source_commit,
            "v156_binary_sha256": BINARY_SHA256,
            "v156_arm_id": ARM_ID,
            "v156_profile": PROFILE,
            "v156_player_frontier": "parents_scheduled",
            "v156_single_change_from_v155": "parents_completed_to_parents_scheduled",
            "v156_queue_density_threshold": QUEUE_THRESHOLD,
            "v156_source_e1_run_id": source_run_id,
            "v156_source_e1_run_spec_hash": source_run_spec_hash,
            "v156_candidate_performance_summaries_parsed_before_run": 0,
            "v156_remaining_seventeen_authorized": False,
            "v156_confirmation_inputs_generated": False,
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
    marker["selected_run_count"] = 3
    marker["selected_reference_build_count"] = 3
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == 3
        and [run["seed"] for run in manifest["runs"]] == list(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and {
            (
                run["workload"]["request_freq"],
                run["cluster"]["node_count"],
                run["cluster"]["topology"],
            )
            for run in manifest["runs"]
        }
        == {("low", 20, "homogeneous")}
        and len(manifest.get("reference_build_dependencies", [])) == 3
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V156 exact E09/E18/E20 product changed")
    expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if (
            run["experiment_id"] != "E1"
            or any(
                run["environment"].get(key) != value for key, value in expected.items()
            )
            or run["environment"].get("SERVERLESS_SIM_PORT") != PORT
            or metadata.get("v156_profile") != PROFILE
            or metadata.get("v156_player_frontier") != "parents_scheduled"
            or metadata.get("v156_queue_density_threshold") != QUEUE_THRESHOLD
        ):
            raise RuntimeError(f"V156 run contract changed: {run.get('run_id')}")


def prepare_v156(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V156 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_PIPELINE_QUEUE8_LOW_SCHEDULE_V156_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_PIPELINE_QUEUE8_LOW_PREPARED_V156_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "implementation_path": str(IMPLEMENTATION),
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_file_sha256_at_build": MODULE_CONF_FILE_SHA256_AT_BUILD,
        "module_conf_semantic_hash": MODULE_CONF_SEMANTIC_HASH,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "v155_result_file_sha256": V155_RESULT_SHA256,
        "v155_result_hash": V155_RESULT_HASH,
        "candidate_online_runs": 3,
        "candidate_reference_builds": 3,
        "reused_v155_candidate_rows_after_reveal": 17,
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "player_frontier": "parents_scheduled",
        "single_change_from_v155": "parents_completed_to_parents_scheduled",
        "queue_density_threshold": QUEUE_THRESHOLD,
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v156(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V156 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V156 prepared receipt")
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
            raise RuntimeError(f"V156 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V156 canonical is not a QC pass: {run['run_id']}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_PIPELINE_QUEUE8_LOW_EXECUTION_V156_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": 3,
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _as_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V156 {label} is invalid")
    return value


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    if not log.is_file():
        raise RuntimeError(f"V156 Nash log is missing: {run_id}")
    counts = {"run_config": 0, "window": 0, "run_summary": 0, "function_profile": 0}
    low_routes = high_routes = reference_available = reference_not_requested = 0
    pipeline_players = pipeline_ahead = ready_players = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind not in counts:
                raise RuntimeError(f"unexpected V156 Nash observation kind: {kind}")
            counts[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("operational_direct_initialization") is True
                    and event.get("operational_unrestricted_initialization") is True
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V156"
                    and contract.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and contract.get("below_threshold_expert") == LOW_EXPERT
                    and contract.get("at_or_above_threshold_expert") == HIGH_EXPERT
                    and contract.get("player_frontier") == "parents_scheduled"
                    and contract.get("single_change_from_v155")
                    == "parents_completed_to_parents_scheduled"
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V156 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != counts["window"] - 1:
                    raise RuntimeError("V156 scheduler window sequence changed")
                decision = event.get("decision", {})
                decision_hash = decision.get("assignment_hash")
                if (
                    isinstance(decision_hash, bool)
                    or not isinstance(decision_hash, int)
                    or decision_hash < 0
                ):
                    raise RuntimeError("V156 final assignment hash is invalid")
                total = _as_count(
                    decision.get("request_function_players"), "player count"
                )
                pipeline = _as_count(
                    decision.get("dependency_pipeline_player_count"),
                    "dependency-pipeline player count",
                )
                ahead = _as_count(
                    decision.get("pipeline_players_with_incomplete_parents"),
                    "pipeline-ahead player count",
                )
                ready = _as_count(
                    decision.get("ready_players_with_all_parents_done"),
                    "ready player count",
                )
                if not (
                    decision.get("player_frontier") == "parents_scheduled"
                    and total == pipeline
                    and ahead + ready == pipeline
                    and decision.get("pipeline_observation_fields_drive_future_windows")
                    is False
                ):
                    raise RuntimeError(
                        "V156 dependency-pipeline frontier evidence changed"
                    )
                pipeline_players += pipeline
                pipeline_ahead += ahead
                ready_players += ready
                route = decision.get("srpt_hiku2_ocs_queue_router", {})
                density = route.get("queue_density")
                selected = route.get("selected_expert")
                if not (
                    route.get("enabled") is True
                    and isinstance(density, (int, float))
                    and not isinstance(density, bool)
                    and math.isfinite(float(density))
                    and float(density) >= 0.0
                    and route.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and route.get("player_frontier") == "parents_scheduled"
                    and route.get("dependency_pipeline_frontier") is True
                    and route.get("uses_completion_outcomes") is False
                ):
                    raise RuntimeError("V156 route telemetry is incomplete")
                expected = (
                    LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
                )
                if selected != expected:
                    raise RuntimeError(
                        "V156 route does not match current queue density"
                    )
                low_routes += selected == LOW_EXPERT
                high_routes += selected == HIGH_EXPERT
                social = event.get("social", {})
                key = social.get("reference_state_key")
                source = social.get("reference_source")
                if key is None:
                    if source != "not_requested":
                        raise RuntimeError("V156 unrequested reference reason changed")
                    reference_not_requested += 1
                elif source in ("offline_table", "offline_table_nonpositive"):
                    reference_available += 1
                else:
                    raise RuntimeError("V156 bound reference source changed")
            elif kind == "run_summary":
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V156 Nash terminal marker changed")
            # function_profile is deliberately counted without reading its payload.
    if (
        counts["run_config"] != 1
        or counts["window"] != 1000
        or counts["run_summary"] != 1
    ):
        raise RuntimeError("V156 Nash log cardinality changed")
    if reference_available + reference_not_requested != counts["window"]:
        raise RuntimeError("V156 reference replay coverage changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": counts["window"],
        "dependency_pipeline_players": pipeline_players,
        "pipeline_players_with_incomplete_parents": pipeline_ahead,
        "ready_players_with_all_parents_done": ready_players,
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
        "offline_reference_windows": reference_available,
        "legitimate_not_requested_windows": reference_not_requested,
        "function_profile_records_seen_without_payload_access": counts[
            "function_profile"
        ],
        "performance_outcome_fields_parsed": 0,
    }


def blind_audit_v156(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V156 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V156 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V156 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed") is True
        and pairing.get("run_count") == 3
        and pairing.get("group_count") == 3
    ):
        raise RuntimeError("V156 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=3
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V156 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V156 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V156 has unexplained quarantined attempts")
    by_seed = {run["seed"]: run for run in manifest["runs"]}
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
        raise RuntimeError("V156 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V156 runtime identity changed")
    low_routes = sum(item["below_threshold_route_windows"] for item in audits)
    high_routes = sum(item["at_or_above_threshold_route_windows"] for item in audits)
    pipeline_ahead = sum(
        item["pipeline_players_with_incomplete_parents"] for item in audits
    )
    if pipeline_ahead <= 0 or low_routes <= 0 or high_routes <= 0:
        raise RuntimeError("V156 mechanism falsification breadth is insufficient")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_PIPELINE_QUEUE8_LOW_BLIND_AUDIT_V156_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "aggregate_runtime_breadth_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_path": str(output["pairing"]),
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "run_count": 3,
        "window_count": sum(item["windows"] for item in audits),
        "dependency_pipeline_players": sum(
            item["dependency_pipeline_players"] for item in audits
        ),
        "pipeline_players_with_incomplete_parents": pipeline_ahead,
        "ready_players_with_all_parents_done": sum(
            item["ready_players_with_all_parents_done"] for item in audits
        ),
        "pipeline_ahead_players_observed": True,
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
        "both_routes_exercised": True,
        "function_profile_records_seen_without_payload_access": sum(
            item["function_profile_records_seen_without_payload_access"]
            for item in audits
        ),
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "module_conf_identity": _assert_json_semantic(
            Path("serverless_sim/module_conf_es.json"),
            MODULE_CONF_SEMANTIC_HASH,
            "frozen module_conf_es.json",
        ),
        "profile": PROFILE,
        "player_frontier": "parents_scheduled",
        "single_change_from_v155": "parents_completed_to_parents_scheduled",
        "queue_density_threshold": QUEUE_THRESHOLD,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _load_candidate(
    manifest: Mapping[str, Any], root: Path = ROOT
) -> list[dict[str, Any]]:
    rows = []
    for run in manifest["runs"]:
        summary = (
            paths(root)["workspace"]
            / "canonical"
            / run["run_id"]
            / "reviewer_records"
            / run["run_id"]
            / "summary.json"
        )
        values = _nse_summary_metrics(read_json(summary))
        rows.append(
            {
                "load": "low",
                "seed": run["seed"],
                "run_id": run["run_id"],
                **_metrics(
                    values.get("throughput"),
                    values.get("latency_mean_ms"),
                    values.get("cost"),
                    values.get("completed"),
                ),
            }
        )
    if len(rows) != 3 or [row["seed"] for row in rows] != list(SEEDS):
        raise RuntimeError("V156 candidate result product changed")
    return rows


def _hybrid_rows(
    v155_rows: Sequence[Mapping[str, Any]], v156_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    if len(v155_rows) != 20 or {row["seed"] for row in v155_rows} != {
        f"E{index:02d}" for index in range(1, 21)
    }:
        raise RuntimeError("V155 complete candidate cohort changed")
    if len(v156_rows) != 3 or {row["seed"] for row in v156_rows} != set(SEEDS):
        raise RuntimeError("V156 diagnostic candidate cohort changed")
    replacements = {row["seed"]: dict(row) for row in v156_rows}
    return [
        replacements.get(row["seed"], dict(row))
        for row in sorted(v155_rows, key=lambda item: item["seed"])
    ]


def reveal_v156(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V156 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V156 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("aggregate_runtime_breadth_fields_parsed") == 0
        and blind.get("pipeline_ahead_players_observed") is True
        and blind.get("both_routes_exercised") is True
    ):
        raise RuntimeError("V156 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    v156 = _load_candidate(manifest, root)
    v155_manifest = load_and_validate_manifest(V155_READY)
    v155 = _load_v155_candidate(v155_manifest, V155_ROOT)
    hybrid = _hybrid_rows(v155, v156)
    baselines = _load_baselines()
    evaluation = _evaluate_load("low", hybrid, baselines)
    throughput_sum = sum(float(row["throughput"]) for row in v156)
    qpr_values = [float(row["qpr_finite_only"]) for row in v156]
    qpr_sum = sum(qpr_values)
    throughput_gate = evaluation["gates"]["throughput"]
    diagnostic_throughput_wins = sum(
        row["difference"] > 0
        for row in throughput_gate["paired_rows"]
        if row["seed"] in SEEDS
    )
    mechanism_gate = {
        "pipeline_players_with_incomplete_parents": blind[
            "pipeline_players_with_incomplete_parents"
        ],
        "below_threshold_route_windows": blind["below_threshold_route_windows"],
        "at_or_above_threshold_route_windows": blind[
            "at_or_above_threshold_route_windows"
        ],
        "pass": blind["pipeline_ahead_players_observed"]
        and blind["both_routes_exercised"],
    }
    diagnostic_gates = {
        "throughput_three_seed_sum": throughput_sum,
        "throughput_three_seed_sum_threshold_strict": THROUGHPUT_THREE_SEED_SUM_GATE,
        "throughput_three_seed_sum_pass": throughput_sum
        > THROUGHPUT_THREE_SEED_SUM_GATE,
        "throughput_three_seed_paired_wins": diagnostic_throughput_wins,
        "throughput_three_seed_paired_wins_pass": diagnostic_throughput_wins >= 2,
        "qpr_three_seed_sum": qpr_sum,
        "qpr_three_seed_sum_threshold_strict": QPR_THREE_SEED_SUM_GATE,
        "qpr_three_seed_sum_pass": qpr_sum > QPR_THREE_SEED_SUM_GATE,
        "qpr_three_seed_all_finite": all(math.isfinite(value) for value in qpr_values),
    }
    passed = (
        evaluation["all_three_metric_gates_pass"]
        and mechanism_gate["pass"]
        and all(
            value
            for key, value in diagnostic_gates.items()
            if key.endswith("_pass") or key.endswith("_all_finite")
        )
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_PIPELINE_QUEUE8_LOW_DIAGNOSTIC_RESULT_V156_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "new_candidate_run_count": 3,
        "reused_v155_candidate_run_count": 17,
        "reused_frozen_baseline_run_count": 180,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "hybrid_low_evaluation": evaluation,
        "diagnostic_three_seed_gates": diagnostic_gates,
        "mechanism_gate": mechanism_gate,
        "joint_diagnostic_pass": passed,
        "disposition": (
            "authorize_separately_committed_remaining_seventeen_training_plan_without_rerunning_E09_E18_E20"
            if passed
            else "retain_all_three_valid_diagnostic_runs_and_retire_pipeline_frontier_candidate"
        ),
        "remaining_seventeen_training_runs_authorized": passed,
        "confirmation_inputs_generated": False,
        "fresh_confirmation_inputs_opened": False,
        "homogeneous_low_claim_closed": False,
        "middle_or_later_execution_authorized": False,
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
        document = prepare_v156()
        key = "receipt_hash"
    elif action == "execute":
        document = execute_v156()
        key = "receipt_hash"
    elif action == "blind-audit":
        document = blind_audit_v156()
        key = "blind_audit_hash"
    else:
        document = reveal_v156()
        key = "result_hash"
    print(json.dumps({key: document[key], "runs": 3}))


if __name__ == "__main__":
    main()
