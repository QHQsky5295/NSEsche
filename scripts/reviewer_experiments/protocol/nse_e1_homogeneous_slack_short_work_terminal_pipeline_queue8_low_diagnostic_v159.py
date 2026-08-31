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
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_short_work_terminal_pipeline_queue8_low_diagnostic_v158 as v158,
)
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
    _hybrid_rows,
    _load_v155_candidate,
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
    "tmp/nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_20260831_v159"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_plan_v159.json"
)
PLAN_SHA256 = "d8102b1b21eb12b40f726e5a20819d0cab2117548c94ea333bcacc84b3d4fb7f"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_implementation_v159.json"
)
IMPLEMENTATION_SHA256 = (
    "2be1286d38573147720d52b9e4b6151d6474ff2cb022d58a3de8868d69b3be5d"
)
V158_RESULT = Path(
    "tmp/nse_e1_homogeneous_short_work_terminal_pipeline_queue8_low_diagnostic_20260831_v158/"
    "diagnostic-result-v158.json"
)
V158_RESULT_SHA256 = "d7ac7df363ca3c0635077b83b6e24d40e377ff27300e942218d1fe7d75fc91f5"
V158_RESULT_HASH = "a0c423c6a2bebafba527d5e11a49835b3acbd6920b630c3dbcd32068d3222d4a"

ARM_ID = "v159-low-srpt-slack-short5p5-terminal-pipeline-hiku2-ocs-queue8"
PROFILE = "srpt_slack_short5p5_terminal_pipeline_hiku2_ocs_queue8"
FRONTIER = "parents_completed_or_terminal_or_slack_short_work_parents_scheduled"
SINGLE_CHANGE = "V158_short_work_pipeline_plus_current_queue_density_strictly_below_8"
TERMINAL_DEFINITION = (
    "admit_all_parents-completed_and_terminal_parents-scheduled_players_plus_"
    "nonterminal_parents-scheduled_players_with_request_remaining_work_at_most_"
    "5p5_only_when_current_queue_density_is_strictly_below_8"
)
WORK_DEFINITION = v158.WORK_DEFINITION
LOW_EXPERT = v158.LOW_EXPERT
HIGH_EXPERT = v158.HIGH_EXPERT
QUEUE_THRESHOLD = 8.0
SHORT_WORK_THRESHOLD = 5.5
PORT = "3210"
BINARY_SOURCE_COMMIT = "585801ca1752a82e479108801441c89b8bfc31a6"
BINARY_PATH = Path("serverless_sim/target_e1_v159/release/serverless_sim.exe")
BINARY_SHA256 = "2c23991a116e702664fc288d769279da443c1155c1b8f07b33721a003c654514"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v159.json",
        "schedule": root / "frozen-run-order-v159.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v159.json",
        "pairing": root / "pairing-audit-v159.json",
        "blind": root / "joint-blind-audit-v159.json",
        "result": root / "diagnostic-result-v159.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v158._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V159 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V159 implementation receipt"),
        (V158_RESULT, V158_RESULT_SHA256, "V158 result"),
        (BINARY_PATH, BINARY_SHA256, "V159 release binary"),
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
        and change.get("short_work_remaining_work_threshold") == SHORT_WORK_THRESHOLD
        and change.get("short_work_queue_density_threshold") == QUEUE_THRESHOLD
        and change.get("queue_boundary") == "below_is_strict"
        and change.get("changes_paper_formula_welfare_pricing_hpa_metrics_or_reference")
        is False
    ):
        raise RuntimeError("V159 implementation boundary changed")
    result = read_json(V158_RESULT)
    if not (
        _assert_hashed(result, "result_hash", "V158 result") == V158_RESULT_HASH
        and result.get("joint_diagnostic_pass") is False
        and result.get("remaining_seventeen_training_runs_authorized") is False
        and result.get("confirmation_inputs_generated") is False
    ):
        raise RuntimeError("V158 result boundary changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = v158._rewrite_candidate(source, protocol_source_commit)
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    for key in list(marker):
        if key.startswith("v158_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": (
                "V159 outcome-disclosed three-seed slack short-work diagnostic; "
                "never a formal result or paper superiority claim"
            ),
            "v159_role": "result_blind_slack_short_work_falsification",
            "v159_plan_sha256": PLAN_SHA256,
            "v159_implementation_sha256": IMPLEMENTATION_SHA256,
            "v159_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v159_protocol_source_commit": protocol_source_commit,
            "v159_binary_sha256": BINARY_SHA256,
            "v159_arm_id": ARM_ID,
            "v159_profile": PROFILE,
            "v159_player_frontier": FRONTIER,
            "v159_single_change_from_v158": SINGLE_CHANGE,
            "v159_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v159_queue_density_threshold": QUEUE_THRESHOLD,
            "v159_queue_boundary": "below_is_strict",
            "v159_environment": COMMON_ENVIRONMENT,
            "v159_expected_run_count": 3,
            "v159_expected_reference_build_count": 3,
            "v159_fixed_order": list(SEEDS),
            "v159_candidate_performance_summaries_parsed": 0,
            "v159_remaining_seventeen_authorized": False,
            "v159_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        old = run.get("metadata", {})
        source_run_id = old.get("v158_source_e1_run_id")
        source_run_spec_hash = old.get("v158_source_e1_run_spec_hash")
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v159_training_only": True,
            "v159_role": "result_blind_slack_short_work_falsification",
            "v159_plan_sha256": PLAN_SHA256,
            "v159_implementation_sha256": IMPLEMENTATION_SHA256,
            "v159_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v159_protocol_source_commit": protocol_source_commit,
            "v159_binary_sha256": BINARY_SHA256,
            "v159_arm_id": ARM_ID,
            "v159_profile": PROFILE,
            "v159_player_frontier": FRONTIER,
            "v159_single_change_from_v158": SINGLE_CHANGE,
            "v159_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v159_queue_density_threshold": QUEUE_THRESHOLD,
            "v159_queue_boundary": "below_is_strict",
            "v159_source_e1_run_id": source_run_id,
            "v159_source_e1_run_spec_hash": source_run_spec_hash,
            "v159_candidate_performance_summaries_parsed_before_run": 0,
            "v159_remaining_seventeen_authorized": False,
            "v159_confirmation_inputs_generated": False,
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
        raise RuntimeError("V159 exact E09/E18/E20 product changed")
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
            and metadata.get("v159_profile") == PROFILE
            and metadata.get("v159_player_frontier") == FRONTIER
            and metadata.get("v159_short_work_threshold") == SHORT_WORK_THRESHOLD
            and metadata.get("v159_queue_density_threshold") == QUEUE_THRESHOLD
            and metadata.get("v159_queue_boundary") == "below_is_strict"
        ):
            raise RuntimeError(f"V159 run contract changed: {run.get('run_id')}")


def prepare_v159(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V159 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_SLACK_SHORT_WORK_TERMINAL_PIPELINE_QUEUE8_LOW_SCHEDULE_V159_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_SLACK_SHORT_WORK_TERMINAL_PIPELINE_QUEUE8_LOW_PREPARED_V159_V1",
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
        "v158_result_file_sha256": V158_RESULT_SHA256,
        "v158_result_hash": V158_RESULT_HASH,
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
        "short_work_threshold": SHORT_WORK_THRESHOLD,
        "queue_density_threshold": QUEUE_THRESHOLD,
        "queue_boundary": "below_is_strict",
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v159(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V159 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V159 prepared receipt")
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
            raise RuntimeError(f"V159 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V159 canonical is not a QC pass: {run['run_id']}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_SLACK_SHORT_WORK_TERMINAL_PIPELINE_QUEUE8_LOW_EXECUTION_V159_V1",
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
        raise RuntimeError(f"V159 {label} is invalid")
    return value


def _finite_optional(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V159 {label} is invalid")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(f"V159 {label} is nonfinite")
    return result


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    counts = {"run_config": 0, "window": 0, "run_summary": 0, "function_profile": 0}
    terminal = short = rejected = queue_rejected = incomplete = 0
    low_routes = high_routes = reference_available = reference_not_requested = 0
    admitted_work_max = (
        rejected_work_min
    ) = admitted_density_max = rejected_density_min = None
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind not in counts:
                raise RuntimeError(f"unexpected V159 Nash observation kind: {kind}")
            counts[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V159"
                    and contract.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and contract.get("below_threshold_expert") == LOW_EXPERT
                    and contract.get("at_or_above_threshold_expert") == HIGH_EXPERT
                    and contract.get("player_frontier") == FRONTIER
                    and contract.get("single_change_from_v155") == SINGLE_CHANGE
                    and contract.get("terminal_pipeline_definition")
                    == TERMINAL_DEFINITION
                    and contract.get("short_work_pipeline_remaining_work_threshold")
                    == SHORT_WORK_THRESHOLD
                    and contract.get("short_work_pipeline_queue_density_threshold")
                    == QUEUE_THRESHOLD
                    and contract.get("short_work_pipeline_queue_boundary")
                    == "below_is_strict"
                    and contract.get("short_work_definition") == WORK_DEFINITION
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V159 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != counts["window"] - 1:
                    raise RuntimeError("V159 scheduler window sequence changed")
                decision = event.get("decision", {})
                decision_hash = decision.get("assignment_hash")
                if (
                    isinstance(decision_hash, bool)
                    or not isinstance(decision_hash, int)
                    or decision_hash < 0
                    or decision.get("player_frontier") != FRONTIER
                ):
                    raise RuntimeError("V159 decision frontier/hash changed")
                frontier = decision.get("terminal_pipeline_frontier", {})
                terminal_now = _count(
                    frontier.get("admitted_terminal_players_with_incomplete_parents"),
                    "terminal admission count",
                )
                short_now = _count(
                    frontier.get(
                        "admitted_short_work_nonterminal_players_with_incomplete_parents"
                    ),
                    "short-work admission count",
                )
                rejected_now = _count(
                    frontier.get(
                        "rejected_nonterminal_players_with_incomplete_parents"
                    ),
                    "nonterminal rejection count",
                )
                incomplete_now = _count(
                    decision.get("pipeline_players_with_incomplete_parents"),
                    "pipeline incomplete-parent count",
                )
                work_max_now = _finite_optional(
                    frontier.get("admitted_short_work_remaining_work_max"),
                    "admitted work maximum",
                )
                work_min_now = _finite_optional(
                    frontier.get("rejected_nonterminal_remaining_work_min"),
                    "rejected work minimum",
                )
                queue_gate = frontier.get("short_work_queue_gate", {})
                queue_rejected_now = _count(
                    queue_gate.get("rejected_short_work_at_or_above_threshold"),
                    "queue-gated rejection count",
                )
                admitted_density_now = _finite_optional(
                    queue_gate.get("admitted_short_work_queue_density_max"),
                    "admitted queue-density maximum",
                )
                rejected_density_now = _finite_optional(
                    queue_gate.get("rejected_short_work_queue_density_min"),
                    "rejected queue-density minimum",
                )
                if not (
                    frontier.get("enabled") is True
                    and frontier.get("definition") == FRONTIER
                    and frontier.get("short_work_remaining_work_threshold")
                    == SHORT_WORK_THRESHOLD
                    and frontier.get("terminal_topology_source")
                    == "immutable_function_children_is_empty"
                    and frontier.get("uses_completion_or_performance_outcomes") is False
                    and queue_gate.get("enabled") is True
                    and queue_gate.get("threshold") == QUEUE_THRESHOLD
                    and queue_gate.get("boundary") == "below_is_strict"
                    and incomplete_now <= terminal_now + short_now
                    and queue_rejected_now <= rejected_now
                    and (short_now == 0)
                    == (work_max_now is None and admitted_density_now is None)
                    and (queue_rejected_now == 0) == (rejected_density_now is None)
                    and (work_max_now is None or work_max_now <= SHORT_WORK_THRESHOLD)
                    and (
                        admitted_density_now is None
                        or admitted_density_now < QUEUE_THRESHOLD
                    )
                    and (work_min_now is None or work_min_now > SHORT_WORK_THRESHOLD)
                    and (
                        rejected_density_now is None
                        or rejected_density_now >= QUEUE_THRESHOLD
                    )
                    and decision.get("pipeline_observation_fields_drive_future_windows")
                    is False
                ):
                    raise RuntimeError("V159 slack short-work evidence changed")
                terminal += terminal_now
                short += short_now
                rejected += rejected_now
                queue_rejected += queue_rejected_now
                incomplete += incomplete_now
                if work_max_now is not None:
                    admitted_work_max = (
                        work_max_now
                        if admitted_work_max is None
                        else max(admitted_work_max, work_max_now)
                    )
                if admitted_density_now is not None:
                    admitted_density_max = (
                        admitted_density_now
                        if admitted_density_max is None
                        else max(admitted_density_max, admitted_density_now)
                    )
                if work_min_now is not None:
                    rejected_work_min = (
                        work_min_now
                        if rejected_work_min is None
                        else min(rejected_work_min, work_min_now)
                    )
                if rejected_density_now is not None:
                    rejected_density_min = (
                        rejected_density_now
                        if rejected_density_min is None
                        else min(rejected_density_min, rejected_density_now)
                    )
                route = decision.get("srpt_hiku2_ocs_queue_router", {})
                density = route.get("queue_density")
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
                    raise RuntimeError("V159 route telemetry is incomplete")
                expected = (
                    LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
                )
                if route.get("selected_expert") != expected:
                    raise RuntimeError("V159 route does not match queue density")
                low_routes += expected == LOW_EXPERT
                high_routes += expected == HIGH_EXPERT
                social = event.get("social", {})
                key, source = social.get("reference_state_key"), social.get(
                    "reference_source"
                )
                if key is None:
                    if source != "not_requested":
                        raise RuntimeError("V159 unrequested reference reason changed")
                    reference_not_requested += 1
                elif source in ("offline_table", "offline_table_nonpositive"):
                    reference_available += 1
                else:
                    raise RuntimeError("V159 bound reference source changed")
            elif kind == "run_summary":
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V159 Nash terminal marker changed")
            # Function-profile payloads are deliberately not inspected.
    if (
        counts["run_config"] != 1
        or counts["window"] != 1000
        or counts["run_summary"] != 1
    ):
        raise RuntimeError("V159 Nash log cardinality changed")
    if reference_available + reference_not_requested != counts["window"]:
        raise RuntimeError("V159 reference replay coverage changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": counts["window"],
        "admitted_terminal_players_with_incomplete_parents": terminal,
        "admitted_slack_short_work_nonterminal_players": short,
        "rejected_nonterminal_players_with_incomplete_parents": rejected,
        "rejected_short_work_at_or_above_queue_threshold": queue_rejected,
        "admitted_short_work_remaining_work_max": admitted_work_max,
        "rejected_over_threshold_remaining_work_min": rejected_work_min,
        "admitted_short_work_queue_density_max": admitted_density_max,
        "rejected_short_work_queue_density_min": rejected_density_min,
        "feasible_pipeline_players_with_incomplete_parents": incomplete,
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
        "offline_reference_windows": reference_available,
        "legitimate_not_requested_windows": reference_not_requested,
        "function_profile_records_seen_without_payload_access": counts[
            "function_profile"
        ],
        "performance_outcome_fields_parsed": 0,
    }


def blind_audit_v159(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V159 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V159 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V159 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if (
        not pairing.get("passed")
        or pairing.get("run_count") != 3
        or pairing.get("group_count") != 3
    ):
        raise RuntimeError("V159 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=3
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V159 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V159 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V159 has unexplained quarantined attempts")
    audits, identities = [], set()
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
        raise RuntimeError("V159 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V159 runtime identity changed")
    terminal = sum(
        x["admitted_terminal_players_with_incomplete_parents"] for x in audits
    )
    short = sum(x["admitted_slack_short_work_nonterminal_players"] for x in audits)
    rejected = sum(
        x["rejected_nonterminal_players_with_incomplete_parents"] for x in audits
    )
    queue_rejected = sum(
        x["rejected_short_work_at_or_above_queue_threshold"] for x in audits
    )
    admitted_work_max = max(
        x["admitted_short_work_remaining_work_max"]
        for x in audits
        if x["admitted_short_work_remaining_work_max"] is not None
    )
    admitted_density_max = max(
        x["admitted_short_work_queue_density_max"]
        for x in audits
        if x["admitted_short_work_queue_density_max"] is not None
    )
    rejected_work_min = min(
        x["rejected_over_threshold_remaining_work_min"]
        for x in audits
        if x["rejected_over_threshold_remaining_work_min"] is not None
    )
    rejected_density_min = min(
        x["rejected_short_work_queue_density_min"]
        for x in audits
        if x["rejected_short_work_queue_density_min"] is not None
    )
    low_routes = sum(x["below_threshold_route_windows"] for x in audits)
    high_routes = sum(x["at_or_above_threshold_route_windows"] for x in audits)
    if (
        min(terminal, short, rejected, queue_rejected, low_routes, high_routes) <= 0
        or admitted_work_max > SHORT_WORK_THRESHOLD
        or admitted_density_max >= QUEUE_THRESHOLD
        or rejected_work_min <= SHORT_WORK_THRESHOLD
        or rejected_density_min < QUEUE_THRESHOLD
    ):
        raise RuntimeError("V159 mechanism falsification breadth is insufficient")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_SLACK_SHORT_WORK_TERMINAL_PIPELINE_QUEUE8_LOW_BLIND_AUDIT_V159_V1",
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
        "window_count": sum(x["windows"] for x in audits),
        "admitted_terminal_players_with_incomplete_parents": terminal,
        "admitted_slack_short_work_nonterminal_players": short,
        "rejected_nonterminal_players_with_incomplete_parents": rejected,
        "rejected_short_work_at_or_above_queue_threshold": queue_rejected,
        "admitted_short_work_remaining_work_max": admitted_work_max,
        "rejected_over_threshold_remaining_work_min": rejected_work_min,
        "admitted_short_work_queue_density_max": admitted_density_max,
        "rejected_short_work_queue_density_min": rejected_density_min,
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
        "terminal_slack_short_congested_short_and_over_work_paths_exercised": True,
        "work_and_queue_threshold_invariants_passed": True,
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
        raise RuntimeError("V159 candidate result product changed")
    return rows


def reveal_v159(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V159 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V159 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get(
            "terminal_slack_short_congested_short_and_over_work_paths_exercised"
        )
        is True
        and blind.get("work_and_queue_threshold_invariants_passed") is True
        and blind.get("both_routes_exercised") is True
    ):
        raise RuntimeError("V159 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = _load_candidate(manifest, root)
    v155_rows = _load_v155_candidate(load_and_validate_manifest(V155_READY), V155_ROOT)
    hybrid = _hybrid_rows(v155_rows, candidate)
    evaluation = _evaluate_load("low", hybrid, _load_baselines())
    throughput_sum = sum(float(row["throughput"]) for row in candidate)
    qpr_values = [float(row["qpr_finite_only"]) for row in candidate]
    qpr_sum = sum(qpr_values)
    throughput_wins = sum(
        row["difference"] > 0
        for row in evaluation["gates"]["throughput"]["paired_rows"]
        if row["seed"] in SEEDS
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
        key: blind[key]
        for key in (
            "admitted_terminal_players_with_incomplete_parents",
            "admitted_slack_short_work_nonterminal_players",
            "rejected_nonterminal_players_with_incomplete_parents",
            "rejected_short_work_at_or_above_queue_threshold",
            "admitted_short_work_remaining_work_max",
            "rejected_over_threshold_remaining_work_min",
            "admitted_short_work_queue_density_max",
            "rejected_short_work_queue_density_min",
        )
    }
    mechanism["pass"] = (
        blind["terminal_slack_short_congested_short_and_over_work_paths_exercised"]
        and blind["work_and_queue_threshold_invariants_passed"]
        and blind["both_routes_exercised"]
    )
    passed = (
        evaluation["all_three_metric_gates_pass"]
        and mechanism["pass"]
        and diagnostic["throughput_three_seed_sum_pass"]
        and diagnostic["throughput_three_seed_paired_wins_pass"]
        and diagnostic["qpr_three_seed_sum_pass"]
        and diagnostic["qpr_three_seed_all_finite"]
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_SLACK_SHORT_WORK_TERMINAL_PIPELINE_QUEUE8_LOW_DIAGNOSTIC_RESULT_V159_V1",
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
            else "retain_all_three_valid_diagnostic_runs_and_retire_slack_short_work_candidate"
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
        document, key = prepare_v159(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v159(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v159(), "blind_audit_hash"
    else:
        document, key = reveal_v159(), "result_hash"
    print(json.dumps({key: document[key], "runs": 3}))


if __name__ == "__main__":
    main()
