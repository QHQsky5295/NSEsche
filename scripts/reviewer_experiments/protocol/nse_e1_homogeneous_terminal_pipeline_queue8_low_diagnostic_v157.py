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
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_pipeline_queue8_low_diagnostic_v156 import (
    QPR_THREE_SEED_SUM_GATE,
    SEEDS,
    THROUGHPUT_THREE_SEED_SUM_GATE,
    V155_READY,
    _assert_frozen_inputs as _assert_v156_frozen_inputs,
    _hybrid_rows,
    _load_v155_candidate,
    _rewrite_candidate as _rewrite_v156_candidate,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_queue8_low_training_v155 import (
    CARGO_LOCK_SHA256,
    MODULE_CONF_SEMANTIC_HASH,
    ROOT as V155_ROOT,
    _assert_json_semantic,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import (
    load_and_validate_manifest,
    validate_manifest,
)
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


ROOT = Path(
    "tmp/nse_e1_homogeneous_terminal_pipeline_queue8_low_diagnostic_20260831_v157"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_terminal_pipeline_queue8_low_diagnostic_plan_v157.json"
)
PLAN_SHA256 = "b1a5ea99027f4ce8159d561c2efb1d8f37a4a0e6c3fe4078dea5cb4d7927b2dd"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_terminal_pipeline_queue8_low_diagnostic_implementation_v157.json"
)
IMPLEMENTATION_SHA256 = (
    "5442966591bbcbb54860ff9a4abb239b45a6522cbe33ca9e032f96b5a7097988"
)
V156_RESULT = Path(
    "tmp/nse_e1_homogeneous_pipeline_queue8_low_diagnostic_20260831_v156/"
    "diagnostic-result-v156.json"
)
V156_RESULT_SHA256 = "06a122ffb26d5ab51e268cc7cb4e6ed2d4110af749d13c064eccdad75394eee5"
V156_RESULT_HASH = "a18c2a891ce634194def5379e6917c7e0e663437bbf6ab8c9bb2705683e51fc8"

ARM_ID = "v157-low-srpt-terminal-pipeline-hiku2-ocs-queue8"
PROFILE = "srpt_terminal_pipeline_hiku2_ocs_queue8"
FRONTIER = "parents_completed_or_terminal_parents_scheduled"
SINGLE_CHANGE = "parents_completed_to_parents_completed_or_terminal_parents_scheduled"
LOW_EXPERT = "srpt_ready_hiku2_ocs_borda"
HIGH_EXPERT = "srpt_ready_ocs_current_demand"
QUEUE_THRESHOLD = 8.0
PORT = "3208"
BINARY_SOURCE_COMMIT = "5cf154413f5a2abde52c9910fa8471c2c3d9f5d3"
BINARY_PATH = Path("serverless_sim/target_e1_v157/release/serverless_sim.exe")
BINARY_SHA256 = "e80fdfefa07c74905fbe34a632a71c5f457565083d7848acffd22f1adb061fb8"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v157.json",
        "schedule": root / "frozen-run-order-v157.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v157.json",
        "pairing": root / "pairing-audit-v157.json",
        "blind": root / "joint-blind-audit-v157.json",
        "result": root / "diagnostic-result-v157.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = _assert_v156_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V157 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V157 implementation receipt"),
        (V156_RESULT, V156_RESULT_SHA256, "V156 result"),
        (BINARY_PATH, BINARY_SHA256, "V157 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    implementation = read_json(IMPLEMENTATION)
    change = implementation.get("single_scientific_change", {})
    if not (
        implementation.get("implementation_git_commit") == BINARY_SOURCE_COMMIT
        and implementation.get("plan_file_sha256") == PLAN_SHA256
        and implementation.get("release", {}).get("sha256") == BINARY_SHA256
        and implementation.get("profile") == PROFILE
        and change.get("to_player_frontier") == FRONTIER
        and change.get("nonterminal_pipeline_players_rejected") is True
        and change.get("changes_paper_formula_welfare_pricing_hpa_metrics_or_reference")
        is False
    ):
        raise RuntimeError("V157 implementation boundary changed")
    v156 = read_json(V156_RESULT)
    if not (
        _assert_hashed(v156, "result_hash", "V156 result") == V156_RESULT_HASH
        and v156.get("joint_diagnostic_pass") is False
        and v156.get("remaining_seventeen_training_runs_authorized") is False
        and v156.get("confirmation_inputs_generated") is False
    ):
        raise RuntimeError("V156 result boundary changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = _rewrite_v156_candidate(source, protocol_source_commit)
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    for key in list(marker):
        if key.startswith("v156_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": (
                "V157 outcome-disclosed three-seed terminal-pipeline diagnostic; "
                "never a formal result or paper superiority claim"
            ),
            "v157_role": "result_blind_terminal_pipeline_falsification",
            "v157_plan_sha256": PLAN_SHA256,
            "v157_implementation_sha256": IMPLEMENTATION_SHA256,
            "v157_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v157_protocol_source_commit": protocol_source_commit,
            "v157_binary_sha256": BINARY_SHA256,
            "v157_arm_id": ARM_ID,
            "v157_profile": PROFILE,
            "v157_player_frontier": FRONTIER,
            "v157_single_change_from_v155": SINGLE_CHANGE,
            "v157_queue_density_threshold": QUEUE_THRESHOLD,
            "v157_environment": COMMON_ENVIRONMENT,
            "v157_expected_run_count": 3,
            "v157_expected_reference_build_count": 3,
            "v157_fixed_order": list(SEEDS),
            "v157_candidate_performance_summaries_parsed": 0,
            "v157_remaining_seventeen_authorized": False,
            "v157_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run.get("metadata", {}).get("v156_source_e1_run_id")
        source_run_spec_hash = run.get("metadata", {}).get(
            "v156_source_e1_run_spec_hash"
        )
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v157_training_only": True,
            "v157_role": "result_blind_terminal_pipeline_falsification",
            "v157_plan_sha256": PLAN_SHA256,
            "v157_implementation_sha256": IMPLEMENTATION_SHA256,
            "v157_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v157_protocol_source_commit": protocol_source_commit,
            "v157_binary_sha256": BINARY_SHA256,
            "v157_arm_id": ARM_ID,
            "v157_profile": PROFILE,
            "v157_player_frontier": FRONTIER,
            "v157_single_change_from_v155": SINGLE_CHANGE,
            "v157_queue_density_threshold": QUEUE_THRESHOLD,
            "v157_source_e1_run_id": source_run_id,
            "v157_source_e1_run_spec_hash": source_run_spec_hash,
            "v157_candidate_performance_summaries_parsed_before_run": 0,
            "v157_remaining_seventeen_authorized": False,
            "v157_confirmation_inputs_generated": False,
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
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == 3
        and [run["seed"] for run in manifest["runs"]] == list(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and len(manifest.get("reference_build_dependencies", [])) == 3
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V157 exact E09/E18/E20 product changed")
    expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and all(
                run["environment"].get(key) == value for key, value in expected.items()
            )
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v157_profile") == PROFILE
            and metadata.get("v157_player_frontier") == FRONTIER
        ):
            raise RuntimeError(f"V157 run contract changed: {run.get('run_id')}")


def prepare_v157(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V157 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_TERMINAL_PIPELINE_QUEUE8_LOW_SCHEDULE_V157_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_TERMINAL_PIPELINE_QUEUE8_LOW_PREPARED_V157_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "implementation_file_sha256": IMPLEMENTATION_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": MODULE_CONF_SEMANTIC_HASH,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "v156_result_file_sha256": V156_RESULT_SHA256,
        "v156_result_hash": V156_RESULT_HASH,
        "candidate_online_runs": 3,
        "candidate_reference_builds": 3,
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v157(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V157 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V157 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    dispatches = []
    logs = root / "execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = logs / f"{ordinal:02d}-{seed}.stderr.log"
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
            raise RuntimeError(f"V157 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V157 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
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
        "schema_version": "NSE_E1_HOMOGENEOUS_TERMINAL_PIPELINE_QUEUE8_LOW_EXECUTION_V157_V1",
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


def _count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V157 {label} is invalid")
    return value


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    counts = {"run_config": 0, "window": 0, "run_summary": 0, "function_profile": 0}
    admitted = rejected = pipeline_incomplete = low_routes = high_routes = 0
    reference_available = reference_not_requested = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind not in counts:
                raise RuntimeError(f"unexpected V157 Nash observation kind: {kind}")
            counts[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V157"
                    and contract.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and contract.get("below_threshold_expert") == LOW_EXPERT
                    and contract.get("at_or_above_threshold_expert") == HIGH_EXPERT
                    and contract.get("player_frontier") == FRONTIER
                    and contract.get("single_change_from_v155") == SINGLE_CHANGE
                    and contract.get("terminal_pipeline_definition")
                    == "admit_all_parents-completed_players_plus_only_immutable-DAG-terminal_players_whose_parents_are_all_assigned"
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V157 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != counts["window"] - 1:
                    raise RuntimeError("V157 scheduler window sequence changed")
                decision = event.get("decision", {})
                decision_hash = decision.get("assignment_hash")
                if (
                    isinstance(decision_hash, bool)
                    or not isinstance(decision_hash, int)
                    or decision_hash < 0
                    or decision.get("player_frontier") != FRONTIER
                ):
                    raise RuntimeError("V157 decision frontier/hash changed")
                terminal = decision.get("terminal_pipeline_frontier", {})
                admitted_now = _count(
                    terminal.get("admitted_terminal_players_with_incomplete_parents"),
                    "admitted terminal pipeline count",
                )
                rejected_now = _count(
                    terminal.get(
                        "rejected_nonterminal_players_with_incomplete_parents"
                    ),
                    "rejected nonterminal pipeline count",
                )
                incomplete_now = _count(
                    decision.get("pipeline_players_with_incomplete_parents"),
                    "pipeline incomplete-parent count",
                )
                if not (
                    terminal.get("enabled") is True
                    and terminal.get("definition") == FRONTIER
                    and terminal.get("terminal_topology_source")
                    == "immutable_function_children_is_empty"
                    and terminal.get("uses_completion_or_performance_outcomes") is False
                    and incomplete_now <= admitted_now
                    and decision.get("pipeline_observation_fields_drive_future_windows")
                    is False
                ):
                    raise RuntimeError("V157 terminal-pipeline evidence changed")
                admitted += admitted_now
                rejected += rejected_now
                pipeline_incomplete += incomplete_now
                route = decision.get("srpt_hiku2_ocs_queue_router", {})
                density = route.get("queue_density")
                selected = route.get("selected_expert")
                if not (
                    route.get("enabled") is True
                    and isinstance(density, (int, float))
                    and not isinstance(density, bool)
                    and math.isfinite(float(density))
                    and route.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and route.get("player_frontier") == FRONTIER
                    and route.get("dependency_pipeline_frontier") is True
                    and route.get("uses_completion_outcomes") is False
                ):
                    raise RuntimeError("V157 route telemetry is incomplete")
                expected = (
                    LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
                )
                if selected != expected:
                    raise RuntimeError(
                        "V157 route does not match current queue density"
                    )
                low_routes += selected == LOW_EXPERT
                high_routes += selected == HIGH_EXPERT
                social = event.get("social", {})
                key = social.get("reference_state_key")
                source = social.get("reference_source")
                if key is None:
                    if source != "not_requested":
                        raise RuntimeError("V157 unrequested reference reason changed")
                    reference_not_requested += 1
                elif source in ("offline_table", "offline_table_nonpositive"):
                    reference_available += 1
                else:
                    raise RuntimeError("V157 bound reference source changed")
            elif kind == "run_summary":
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V157 Nash terminal marker changed")
            # function_profile payload is intentionally never read.
    if (
        counts["run_config"] != 1
        or counts["window"] != 1000
        or counts["run_summary"] != 1
    ):
        raise RuntimeError("V157 Nash log cardinality changed")
    if reference_available + reference_not_requested != counts["window"]:
        raise RuntimeError("V157 reference replay coverage changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": counts["window"],
        "admitted_terminal_players_with_incomplete_parents": admitted,
        "rejected_nonterminal_players_with_incomplete_parents": rejected,
        "feasible_pipeline_players_with_incomplete_parents": pipeline_incomplete,
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
        "offline_reference_windows": reference_available,
        "legitimate_not_requested_windows": reference_not_requested,
        "function_profile_records_seen_without_payload_access": counts[
            "function_profile"
        ],
        "performance_outcome_fields_parsed": 0,
    }


def blind_audit_v157(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V157 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V157 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V157 execution receipt")
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
        raise RuntimeError("V157 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=3
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V157 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V157 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V157 has unexplained quarantined attempts")
    audits = []
    identities = set()
    for run in manifest["runs"]:
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
        raise RuntimeError("V157 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V157 runtime identity changed")
    admitted = sum(
        item["admitted_terminal_players_with_incomplete_parents"] for item in audits
    )
    rejected = sum(
        item["rejected_nonterminal_players_with_incomplete_parents"] for item in audits
    )
    low_routes = sum(item["below_threshold_route_windows"] for item in audits)
    high_routes = sum(item["at_or_above_threshold_route_windows"] for item in audits)
    if min(admitted, rejected, low_routes, high_routes) <= 0:
        raise RuntimeError("V157 mechanism falsification breadth is insufficient")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_TERMINAL_PIPELINE_QUEUE8_LOW_BLIND_AUDIT_V157_V1",
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
        "admitted_terminal_players_with_incomplete_parents": admitted,
        "rejected_nonterminal_players_with_incomplete_parents": rejected,
        "feasible_pipeline_players_with_incomplete_parents": sum(
            item["feasible_pipeline_players_with_incomplete_parents"] for item in audits
        ),
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
        "terminal_and_rejected_nonterminal_paths_exercised": True,
        "both_routes_exercised": True,
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": PROFILE,
        "player_frontier": FRONTIER,
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
        raise RuntimeError("V157 candidate result product changed")
    return rows


def reveal_v157(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V157 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V157 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("terminal_and_rejected_nonterminal_paths_exercised") is True
        and blind.get("both_routes_exercised") is True
    ):
        raise RuntimeError("V157 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    v157 = _load_candidate(manifest, root)
    v155 = _load_v155_candidate(load_and_validate_manifest(V155_READY), V155_ROOT)
    hybrid = _hybrid_rows(v155, v157)
    evaluation = _evaluate_load("low", hybrid, _load_baselines())
    throughput_sum = sum(float(row["throughput"]) for row in v157)
    qpr_values = [float(row["qpr_finite_only"]) for row in v157]
    qpr_sum = sum(qpr_values)
    throughput_rows = evaluation["gates"]["throughput"]["paired_rows"]
    throughput_wins = sum(
        row["difference"] > 0 for row in throughput_rows if row["seed"] in SEEDS
    )
    diagnostic = {
        "throughput_three_seed_sum": throughput_sum,
        "throughput_three_seed_sum_pass": throughput_sum
        > THROUGHPUT_THREE_SEED_SUM_GATE,
        "throughput_three_seed_paired_wins": throughput_wins,
        "throughput_three_seed_paired_wins_pass": throughput_wins >= 2,
        "qpr_three_seed_sum": qpr_sum,
        "qpr_three_seed_sum_pass": qpr_sum > QPR_THREE_SEED_SUM_GATE,
        "qpr_three_seed_all_finite": all(math.isfinite(value) for value in qpr_values),
    }
    mechanism = {
        "admitted_terminal_players_with_incomplete_parents": blind[
            "admitted_terminal_players_with_incomplete_parents"
        ],
        "rejected_nonterminal_players_with_incomplete_parents": blind[
            "rejected_nonterminal_players_with_incomplete_parents"
        ],
        "pass": blind["terminal_and_rejected_nonterminal_paths_exercised"]
        and blind["both_routes_exercised"],
    }
    passed = (
        evaluation["all_three_metric_gates_pass"]
        and mechanism["pass"]
        and diagnostic["throughput_three_seed_sum_pass"]
        and diagnostic["throughput_three_seed_paired_wins_pass"]
        and diagnostic["qpr_three_seed_sum_pass"]
        and diagnostic["qpr_three_seed_all_finite"]
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_TERMINAL_PIPELINE_QUEUE8_LOW_DIAGNOSTIC_RESULT_V157_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
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
        "diagnostic_three_seed_gates": diagnostic,
        "mechanism_gate": mechanism,
        "joint_diagnostic_pass": passed,
        "disposition": (
            "authorize_separately_committed_remaining_seventeen_training_plan_without_rerunning_E09_E18_E20"
            if passed
            else "retain_all_three_valid_diagnostic_runs_and_retire_terminal_pipeline_candidate"
        ),
        "remaining_seventeen_training_runs_authorized": passed,
        "confirmation_inputs_generated": False,
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
        document, key = prepare_v157(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v157(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v157(), "blind_audit_hash"
    else:
        document, key = reveal_v157(), "result_hash"
    print(json.dumps({key: document[key], "runs": 3}))


if __name__ == "__main__":
    main()
