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
    nse_e1_homogeneous_lifetime_credit_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v163 as previous,
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
    "tmp/nse_e1_homogeneous_ready_antihotspot_lifetime_credit_slack_short_work_terminal_pipeline_queue8_low_diagnostic_20260901_v164"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_ready_antihotspot_lifetime_credit_slack_short_work_terminal_pipeline_queue8_low_diagnostic_plan_v164.json"
)
PLAN_SHA256 = "d6a25c0fcb5f685323f6b81740d2a3909c17c452121c9c81bd8935aec758d3c4"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_ready_antihotspot_lifetime_credit_slack_short_work_terminal_pipeline_queue8_low_diagnostic_implementation_v164.json"
)
IMPLEMENTATION_SHA256 = (
    "4af8c4aa6f30ff455d7c1be87fcb3d5aa7c45f79d6095f3e3470cd8f692d1079"
)
V163_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_lifetime_credit_slack_short_work_terminal_pipeline_queue8_low_diagnostic_failure_v163.json"
)
V163_FAILURE_SHA256 = "3326d72476b4bba81f78ac2882585b79e238ef1554b71df64c4dc279d009b7aa"
V163_FAILURE_HASH = "845c737a8f64b7d522a468dc140f19fded015e5eead1ba359af8b9871954ca52"

ARM_ID = "v164-low-srpt-slack-lifetime-credit-short5p5-terminal-pipeline-ready-antihotspot-hiku2-ocs-queue8"
PROFILE = (
    "srpt_slack_lifetime_credit_short5p5_terminal_pipeline_"
    "ready_antihotspot_hiku2_ocs_queue8"
)
FRONTIER = (
    "parents_completed_or_terminal_or_slack_lifetime_credit_"
    "short_work_parents_scheduled"
)
SINGLE_CHANGE = (
    "V163_plus_one_recent_same-function_placement_antihotspot_vote_"
    "for_parents-completed_players_only"
)
TERMINAL_DEFINITION = (
    "V163_frontier_unchanged;parents-completed_player_scoring_adds_one_recent_"
    "same-function_placement_antihotspot_vote"
)
LIFETIME_CREDIT_DEFINITION = (
    "one_nonreusable_incomplete-parent_nonterminal_admission_per_request_lifetime"
)
SELECTION_ORDER = "maximum_immutable_critical_path_rank_then_minimum_function_id"
WORK_DEFINITION = previous.WORK_DEFINITION
LOW_EXPERT = previous.LOW_EXPERT
HIGH_EXPERT = previous.HIGH_EXPERT
QUEUE_THRESHOLD = 8.0
SHORT_WORK_THRESHOLD = 5.5
READY_ANTIHOTSPOT_HISTORY_LIMIT = 64
PORT = "3215"
BINARY_SOURCE_COMMIT = "9764c47895cad84ab6fcf82e821a5dc30051ae7c"
BINARY_PATH = Path("serverless_sim/target_e1_v164/release/serverless_sim.exe")
BINARY_SHA256 = "837d734d995a77d954a4e8153f7623f8fdbc6eb463b915283529a704d76011ff"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v164.json",
        "schedule": root / "frozen-run-order-v164.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v164.json",
        "pairing": root / "pairing-audit-v164.json",
        "blind": root / "joint-blind-audit-v164.json",
        "result": root / "diagnostic-result-v164.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = previous._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V164 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V164 implementation receipt"),
        (V163_FAILURE, V163_FAILURE_SHA256, "V163 joint-gate failure receipt"),
        (BINARY_PATH, BINARY_SHA256, "V164 release binary"),
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
        and change.get("to_player_frontier") == "identical_to_v163"
        and change.get("short_work_remaining_work_threshold") == SHORT_WORK_THRESHOLD
        and change.get("short_work_queue_density_threshold") == QUEUE_THRESHOLD
        and change.get("queue_boundary") == "below_is_strict"
        and change.get("v163_lifetime_credit_definition_unchanged") is True
        and change.get("ready_player_definition") == "all_direct_parents_completed"
        and change.get("history_update_point")
        == "only_after_the_actual_scheduling_command_batch_is_successfully_sent"
        and change.get("nonready_operational_penalty") == "exact_V163_router"
        and change.get("changes_paper_formula_welfare_pricing_hpa_metrics_or_reference")
        is False
    ):
        raise RuntimeError("V164 implementation boundary changed")
    failure = read_json(V163_FAILURE)
    if not (
        _assert_hashed(failure, "receipt_hash", "V163 failure receipt")
        == V163_FAILURE_HASH
        and failure.get("status")
        == "mechanism_gate_passed_but_joint_performance_gate_failed"
        and failure.get("disposition", {}).get("retain_all_three_valid_diagnostic_runs")
        is True
        and failure.get("disposition", {}).get(
            "remaining_seventeen_v163_runs_authorized"
        )
        is False
    ):
        raise RuntimeError("V163 sealed failure boundary changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = previous._rewrite_candidate(source, protocol_source_commit)
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    for key in list(marker):
        if key.startswith("v163_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": (
                "V164 outcome-disclosed three-seed ready-player anti-hotspot "
                "diagnostic on the frozen V163 frontier; "
                "never a formal result or paper superiority claim"
            ),
            "v164_role": ("result_blind_ready_antihotspot_falsification"),
            "v164_plan_sha256": PLAN_SHA256,
            "v164_implementation_sha256": IMPLEMENTATION_SHA256,
            "v164_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v164_protocol_source_commit": protocol_source_commit,
            "v164_binary_sha256": BINARY_SHA256,
            "v164_arm_id": ARM_ID,
            "v164_profile": PROFILE,
            "v164_player_frontier": FRONTIER,
            "v164_single_change_from_v163": SINGLE_CHANGE,
            "v164_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v164_queue_density_threshold": QUEUE_THRESHOLD,
            "v164_queue_boundary": "below_is_strict",
            "v164_lifetime_credit_definition": LIFETIME_CREDIT_DEFINITION,
            "v164_lifetime_credit_limit_per_request": 1,
            "v164_selection_order": SELECTION_ORDER,
            "v164_credit_reuse_after_parent_or_function_completion": False,
            "v164_ready_antihotspot_history_limit": READY_ANTIHOTSPOT_HISTORY_LIMIT,
            "v164_ready_antihotspot_below_queue8_votes": [
                "hiku",
                "hiku",
                "ocs",
                "ready_antihotspot",
            ],
            "v164_ready_antihotspot_high_queue_votes": [
                "ocs",
                "ready_antihotspot",
            ],
            "v164_nonready_score": "exact_V163_router",
            "v164_environment": COMMON_ENVIRONMENT,
            "v164_expected_run_count": 3,
            "v164_expected_reference_build_count": 3,
            "v164_fixed_order": list(SEEDS),
            "v164_candidate_performance_summaries_parsed": 0,
            "v164_remaining_seventeen_authorized": False,
            "v164_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        old = run.get("metadata", {})
        source_run_id = old.get("v163_source_e1_run_id")
        source_run_spec_hash = old.get("v163_source_e1_run_spec_hash")
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v164_training_only": True,
            "v164_role": ("result_blind_ready_antihotspot_falsification"),
            "v164_plan_sha256": PLAN_SHA256,
            "v164_implementation_sha256": IMPLEMENTATION_SHA256,
            "v164_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v164_protocol_source_commit": protocol_source_commit,
            "v164_binary_sha256": BINARY_SHA256,
            "v164_arm_id": ARM_ID,
            "v164_profile": PROFILE,
            "v164_player_frontier": FRONTIER,
            "v164_single_change_from_v163": SINGLE_CHANGE,
            "v164_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v164_queue_density_threshold": QUEUE_THRESHOLD,
            "v164_queue_boundary": "below_is_strict",
            "v164_lifetime_credit_definition": LIFETIME_CREDIT_DEFINITION,
            "v164_lifetime_credit_limit_per_request": 1,
            "v164_selection_order": SELECTION_ORDER,
            "v164_credit_reuse_after_parent_or_function_completion": False,
            "v164_ready_antihotspot_history_limit": READY_ANTIHOTSPOT_HISTORY_LIMIT,
            "v164_ready_antihotspot_below_queue8_votes": [
                "hiku",
                "hiku",
                "ocs",
                "ready_antihotspot",
            ],
            "v164_ready_antihotspot_high_queue_votes": [
                "ocs",
                "ready_antihotspot",
            ],
            "v164_nonready_score": "exact_V163_router",
            "v164_source_e1_run_id": source_run_id,
            "v164_source_e1_run_spec_hash": source_run_spec_hash,
            "v164_candidate_performance_summaries_parsed_before_run": 0,
            "v164_remaining_seventeen_authorized": False,
            "v164_confirmation_inputs_generated": False,
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
        raise RuntimeError("V164 exact E09/E18/E20 product changed")
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
            and metadata.get("v164_profile") == PROFILE
            and metadata.get("v164_player_frontier") == FRONTIER
            and metadata.get("v164_short_work_threshold") == SHORT_WORK_THRESHOLD
            and metadata.get("v164_queue_density_threshold") == QUEUE_THRESHOLD
            and metadata.get("v164_queue_boundary") == "below_is_strict"
            and metadata.get("v164_lifetime_credit_definition")
            == LIFETIME_CREDIT_DEFINITION
            and metadata.get("v164_lifetime_credit_limit_per_request") == 1
            and metadata.get("v164_selection_order") == SELECTION_ORDER
            and metadata.get("v164_credit_reuse_after_parent_or_function_completion")
            is False
            and metadata.get("v164_ready_antihotspot_history_limit")
            == READY_ANTIHOTSPOT_HISTORY_LIMIT
            and metadata.get("v164_nonready_score") == "exact_V163_router"
        ):
            raise RuntimeError(f"V164 run contract changed: {run.get('run_id')}")


def prepare_v164(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V164 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_READY_ANTIHOTSPOT_LIFETIME_CREDIT_LOW_SCHEDULE_V164_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_READY_ANTIHOTSPOT_LIFETIME_CREDIT_LOW_PREPARED_V164_V1",
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
        "v163_failure_receipt_file_sha256": V163_FAILURE_SHA256,
        "v163_failure_receipt_hash": V163_FAILURE_HASH,
        "v163_performance_revealed_and_used_for_training_diagnosis": True,
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
        "lifetime_credit_definition": LIFETIME_CREDIT_DEFINITION,
        "lifetime_credit_limit_per_request": 1,
        "selection_order": SELECTION_ORDER,
        "credit_reuse_after_parent_or_function_completion": False,
        "ready_antihotspot_history_limit": READY_ANTIHOTSPOT_HISTORY_LIMIT,
        "ready_antihotspot_below_queue8_votes": [
            "hiku",
            "hiku",
            "ocs",
            "ready_antihotspot",
        ],
        "ready_antihotspot_high_queue_votes": ["ocs", "ready_antihotspot"],
        "nonready_score": "exact_V163_router",
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v164(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V164 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V164 prepared receipt")
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
            raise RuntimeError(f"V164 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V164 canonical is not a QC pass: {run['run_id']}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_READY_ANTIHOTSPOT_LIFETIME_CREDIT_LOW_EXECUTION_V164_V1",
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
        raise RuntimeError(f"V164 {label} is invalid")
    return value


def _finite_optional(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V164 {label} is invalid")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(f"V164 {label} is nonfinite")
    return result


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    counts = {"run_config": 0, "window": 0, "run_summary": 0, "function_profile": 0}
    terminal = short = first_admissions = 0
    rejected = queue_rejected = incomplete = 0
    already_credited_rejected = same_window_rejected = repeat_violations = 0
    requests_observed = credited_before_observations = credited_after_observations = 0
    credited_requests_max = 0
    antihotspot_eligible = antihotspot_dispatched = antihotspot_with_history = 0
    antihotspot_anchor_substitutions = antihotspot_history_length_max = 0
    low_routes = high_routes = reference_available = reference_not_requested = 0
    admitted_work_max = (
        rejected_work_min
    ) = admitted_density_max = rejected_density_min = None
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind not in counts:
                raise RuntimeError(f"unexpected V164 Nash observation kind: {kind}")
            counts[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                antihotspot_contract = contract.get("ready_antihotspot_definition", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V164"
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
                    and contract.get("jit_parent_tail_short_work_required") is False
                    and contract.get("jit_parent_tail_definition") is None
                    and contract.get("one_outstanding_short_work_credit_required")
                    is False
                    and contract.get("one_outstanding_short_work_credit_definition")
                    is None
                    and contract.get("lifetime_short_work_credit_required") is True
                    and contract.get("lifetime_short_work_credit_definition")
                    == (
                        LIFETIME_CREDIT_DEFINITION
                        + ";when_unused_select_"
                        + SELECTION_ORDER
                    )
                    and contract.get("ready_antihotspot_required") is True
                    and antihotspot_contract.get("eligible_players")
                    == "direct_parents_all_completed_only"
                    and antihotspot_contract.get("history")
                    == "last_at_most_64_successfully_sent_same-function_placement_decisions_plus_current_projected_assignments"
                    and antihotspot_contract.get("candidate_penalty")
                    == "same-function_candidate_share_ascending_then_node_id"
                    and antihotspot_contract.get("below_queue8_votes")
                    == ["hiku", "hiku", "ocs", "ready_antihotspot"]
                    and antihotspot_contract.get("at_or_above_queue8_votes")
                    == ["ocs", "ready_antihotspot"]
                    and antihotspot_contract.get("nonready_score")
                    == "exact_V163_router"
                    and antihotspot_contract.get("history_update")
                    == "only_after_successful_command_batch_send"
                    and antihotspot_contract.get("uses_completed_request_outcomes")
                    is False
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V164 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != counts["window"] - 1:
                    raise RuntimeError("V164 scheduler window sequence changed")
                decision = event.get("decision", {})
                decision_hash = decision.get("assignment_hash")
                if (
                    isinstance(decision_hash, bool)
                    or not isinstance(decision_hash, int)
                    or decision_hash < 0
                    or decision.get("player_frontier") != FRONTIER
                ):
                    raise RuntimeError("V164 decision frontier/hash changed")
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
                credit = frontier.get("lifetime_short_work_credit", {})
                antihotspot = frontier.get("ready_antihotspot", {})
                antihotspot_eligible_now = _count(
                    antihotspot.get("eligible_ready_players"),
                    "ready anti-hotspot eligible-player count",
                )
                antihotspot_dispatched_now = _count(
                    antihotspot.get("dispatched_ready_players"),
                    "ready anti-hotspot dispatched-player count",
                )
                antihotspot_with_history_now = _count(
                    antihotspot.get("dispatched_with_nonempty_history"),
                    "ready anti-hotspot nonempty-history count",
                )
                antihotspot_substitutions_now = _count(
                    antihotspot.get("v163_anchor_substitutions"),
                    "ready anti-hotspot V163-anchor substitution count",
                )
                antihotspot_history_max_now = _count(
                    antihotspot.get("history_length_max_before_update"),
                    "ready anti-hotspot history-length maximum",
                )
                requests_observed_now = _count(
                    credit.get("requests_observed"), "observed request count"
                )
                credited_before_now = _count(
                    credit.get("credited_requests_before"),
                    "credited request count before dispatch",
                )
                credited_after_now = _count(
                    credit.get("credited_requests_after"),
                    "credited request count after dispatch",
                )
                first_admissions_now = _count(
                    credit.get("first_admissions"),
                    "first lifetime-credit admission count",
                )
                already_credited_rejected_now = _count(
                    credit.get("rejected_already_credited"),
                    "already-credited rejection count",
                )
                same_window_rejected_now = _count(
                    credit.get("rejected_same_window_not_selected"),
                    "same-window extra-candidate rejection count",
                )
                repeat_violations_now = _count(
                    credit.get("repeat_admission_violations"),
                    "repeat lifetime-credit admission violation count",
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
                    and credit.get("enabled") is True
                    and credit.get("definition") == LIFETIME_CREDIT_DEFINITION
                    and credit.get("credit_limit_per_request_lifetime") == 1
                    and credit.get("selection_order") == SELECTION_ORDER
                    and credit.get("terminal_players_consume_credit") is False
                    and credit.get("ready_players_consume_credit") is False
                    and credit.get("credit_reuse_after_parent_or_function_completion")
                    is False
                    and credit.get("uses_completion_or_performance_outcomes") is False
                    and antihotspot.get("enabled") is True
                    and antihotspot.get("history_limit")
                    == READY_ANTIHOTSPOT_HISTORY_LIMIT
                    and antihotspot.get("history_updates_after_successful_send") is True
                    and antihotspot.get("uses_completion_or_performance_outcomes")
                    is False
                    and antihotspot_dispatched_now <= antihotspot_eligible_now
                    and antihotspot_with_history_now <= antihotspot_dispatched_now
                    and antihotspot_substitutions_now <= antihotspot_dispatched_now
                    and antihotspot_history_max_now <= READY_ANTIHOTSPOT_HISTORY_LIMIT
                    and incomplete_now <= terminal_now + short_now
                    and first_admissions_now <= short_now
                    and already_credited_rejected_now + same_window_rejected_now
                    <= rejected_now
                    and credited_before_now <= requests_observed_now
                    and credited_after_now <= requests_observed_now
                    and credited_after_now == credited_before_now + first_admissions_now
                    and repeat_violations_now == 0
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
                    raise RuntimeError(
                        "V164 lifetime-credit slack short-work evidence changed"
                    )
                terminal += terminal_now
                short += short_now
                first_admissions += first_admissions_now
                rejected += rejected_now
                queue_rejected += queue_rejected_now
                incomplete += incomplete_now
                already_credited_rejected += already_credited_rejected_now
                same_window_rejected += same_window_rejected_now
                repeat_violations += repeat_violations_now
                requests_observed += requests_observed_now
                credited_before_observations += credited_before_now
                credited_after_observations += credited_after_now
                credited_requests_max = max(credited_requests_max, credited_after_now)
                antihotspot_eligible += antihotspot_eligible_now
                antihotspot_dispatched += antihotspot_dispatched_now
                antihotspot_with_history += antihotspot_with_history_now
                antihotspot_anchor_substitutions += antihotspot_substitutions_now
                antihotspot_history_length_max = max(
                    antihotspot_history_length_max, antihotspot_history_max_now
                )
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
                    raise RuntimeError("V164 route telemetry is incomplete")
                expected = (
                    LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
                )
                if route.get("selected_expert") != expected:
                    raise RuntimeError("V164 route does not match queue density")
                low_routes += expected == LOW_EXPERT
                high_routes += expected == HIGH_EXPERT
                social = event.get("social", {})
                key, source = social.get("reference_state_key"), social.get(
                    "reference_source"
                )
                if key is None:
                    if source != "not_requested":
                        raise RuntimeError("V164 unrequested reference reason changed")
                    reference_not_requested += 1
                elif source in ("offline_table", "offline_table_nonpositive"):
                    reference_available += 1
                else:
                    raise RuntimeError("V164 bound reference source changed")
            elif kind == "run_summary":
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V164 Nash terminal marker changed")
            # Function-profile payloads are deliberately not inspected.
    if (
        counts["run_config"] != 1
        or counts["window"] != 1000
        or counts["run_summary"] != 1
    ):
        raise RuntimeError("V164 Nash log cardinality changed")
    if reference_available + reference_not_requested != counts["window"]:
        raise RuntimeError("V164 reference replay coverage changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": counts["window"],
        "admitted_terminal_players_with_incomplete_parents": terminal,
        "admitted_slack_short_work_nonterminal_players": short,
        "first_lifetime_credit_admissions": first_admissions,
        "rejected_already_credited": already_credited_rejected,
        "rejected_same_window_not_selected": same_window_rejected,
        "repeat_admission_violations": repeat_violations,
        "requests_observed": requests_observed,
        "credited_request_observations_before": credited_before_observations,
        "credited_request_observations_after": credited_after_observations,
        "credited_requests_max": credited_requests_max,
        "ready_antihotspot_eligible_players": antihotspot_eligible,
        "ready_antihotspot_dispatched_players": antihotspot_dispatched,
        "ready_antihotspot_dispatched_with_history": antihotspot_with_history,
        "ready_antihotspot_v163_anchor_substitutions": antihotspot_anchor_substitutions,
        "ready_antihotspot_history_length_max": antihotspot_history_length_max,
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


def _mechanism_falsification_gate(
    audits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    terminal = sum(
        x["admitted_terminal_players_with_incomplete_parents"] for x in audits
    )
    short = sum(x["admitted_slack_short_work_nonterminal_players"] for x in audits)
    first_admissions = sum(x["first_lifetime_credit_admissions"] for x in audits)
    already_credited_rejected = sum(x["rejected_already_credited"] for x in audits)
    same_window_rejected = sum(x["rejected_same_window_not_selected"] for x in audits)
    repeat_violations = sum(x["repeat_admission_violations"] for x in audits)
    requests_observed = sum(x["requests_observed"] for x in audits)
    credited_before_observations = sum(
        x["credited_request_observations_before"] for x in audits
    )
    credited_after_observations = sum(
        x["credited_request_observations_after"] for x in audits
    )
    credited_requests_max = max(x["credited_requests_max"] for x in audits)
    antihotspot_eligible = sum(x["ready_antihotspot_eligible_players"] for x in audits)
    antihotspot_dispatched = sum(
        x["ready_antihotspot_dispatched_players"] for x in audits
    )
    antihotspot_with_history = sum(
        x["ready_antihotspot_dispatched_with_history"] for x in audits
    )
    antihotspot_anchor_substitutions = sum(
        x["ready_antihotspot_v163_anchor_substitutions"] for x in audits
    )
    antihotspot_history_length_max = max(
        x["ready_antihotspot_history_length_max"] for x in audits
    )
    rejected = sum(
        x["rejected_nonterminal_players_with_incomplete_parents"] for x in audits
    )
    queue_rejected = sum(
        x["rejected_short_work_at_or_above_queue_threshold"] for x in audits
    )
    admitted_work = [
        x["admitted_short_work_remaining_work_max"]
        for x in audits
        if x["admitted_short_work_remaining_work_max"] is not None
    ]
    admitted_density = [
        x["admitted_short_work_queue_density_max"]
        for x in audits
        if x["admitted_short_work_queue_density_max"] is not None
    ]
    rejected_work = [
        x["rejected_over_threshold_remaining_work_min"]
        for x in audits
        if x["rejected_over_threshold_remaining_work_min"] is not None
    ]
    rejected_density = [
        x["rejected_short_work_queue_density_min"]
        for x in audits
        if x["rejected_short_work_queue_density_min"] is not None
    ]
    low_routes = sum(x["below_threshold_route_windows"] for x in audits)
    high_routes = sum(x["at_or_above_threshold_route_windows"] for x in audits)
    breadth_paths = {
        "terminal_admission": terminal > 0,
        "first_lifetime_credit_admission": first_admissions > 0,
        "already_credited_rejection": already_credited_rejected > 0,
        "generic_incomplete_parent_rejection": rejected > 0,
        "queue_threshold_rejection": queue_rejected > 0,
        "admitted_work_observation": bool(admitted_work),
        "admitted_density_observation": bool(admitted_density),
        "rejected_work_observation": bool(rejected_work),
        "rejected_density_observation": bool(rejected_density),
        "below_threshold_route": low_routes > 0,
        "at_or_above_threshold_route": high_routes > 0,
        "ready_antihotspot_eligible_player": antihotspot_eligible > 0,
        "ready_antihotspot_dispatched_with_history": antihotspot_with_history > 0,
        "ready_antihotspot_v163_anchor_substitution": (
            antihotspot_anchor_substitutions > 0
        ),
    }
    admitted_work_max = max(admitted_work) if admitted_work else None
    admitted_density_max = max(admitted_density) if admitted_density else None
    rejected_work_min = min(rejected_work) if rejected_work else None
    rejected_density_min = min(rejected_density) if rejected_density else None
    credit_invariants = (
        first_admissions <= short
        and repeat_violations == 0
        and credited_after_observations
        == credited_before_observations + first_admissions
        and already_credited_rejected + same_window_rejected <= rejected
    )
    work_invariants = (
        admitted_work_max is not None
        and admitted_density_max is not None
        and rejected_work_min is not None
        and rejected_density_min is not None
        and admitted_work_max <= SHORT_WORK_THRESHOLD
        and admitted_density_max < QUEUE_THRESHOLD
        and rejected_work_min > SHORT_WORK_THRESHOLD
        and rejected_density_min >= QUEUE_THRESHOLD
    )
    breadth_passed = all(breadth_paths.values())
    both_routes = low_routes > 0 and high_routes > 0
    antihotspot_invariants = (
        antihotspot_dispatched <= antihotspot_eligible
        and antihotspot_with_history <= antihotspot_dispatched
        and antihotspot_anchor_substitutions <= antihotspot_dispatched
        and antihotspot_history_length_max <= READY_ANTIHOTSPOT_HISTORY_LIMIT
    )
    failure_reasons = [
        f"unexercised_{name}" for name, passed in breadth_paths.items() if not passed
    ]
    if not credit_invariants:
        failure_reasons.append("lifetime_credit_invariant_failed")
    if not work_invariants:
        failure_reasons.append("work_or_queue_threshold_invariant_failed")
    if not both_routes:
        failure_reasons.append("both_router_branches_not_exercised")
    if not antihotspot_invariants:
        failure_reasons.append("ready_antihotspot_invariant_failed")
    return {
        "passed": breadth_passed
        and credit_invariants
        and work_invariants
        and both_routes
        and antihotspot_invariants,
        "failure_reasons": failure_reasons,
        "breadth_paths": breadth_paths,
        "metrics": {
            "admitted_terminal_players_with_incomplete_parents": terminal,
            "admitted_slack_short_work_nonterminal_players": short,
            "first_lifetime_credit_admissions": first_admissions,
            "rejected_already_credited": already_credited_rejected,
            "rejected_same_window_not_selected": same_window_rejected,
            "same_window_choice_observed": same_window_rejected > 0,
            "repeat_admission_violations": repeat_violations,
            "requests_observed": requests_observed,
            "credited_request_observations_before": credited_before_observations,
            "credited_request_observations_after": credited_after_observations,
            "credited_requests_max": credited_requests_max,
            "rejected_nonterminal_players_with_incomplete_parents": rejected,
            "rejected_short_work_at_or_above_queue_threshold": queue_rejected,
            "admitted_short_work_remaining_work_max": admitted_work_max,
            "rejected_over_threshold_remaining_work_min": rejected_work_min,
            "admitted_short_work_queue_density_max": admitted_density_max,
            "rejected_short_work_queue_density_min": rejected_density_min,
            "below_threshold_route_windows": low_routes,
            "at_or_above_threshold_route_windows": high_routes,
            "ready_antihotspot_eligible_players": antihotspot_eligible,
            "ready_antihotspot_dispatched_players": antihotspot_dispatched,
            "ready_antihotspot_dispatched_with_history": antihotspot_with_history,
            "ready_antihotspot_v163_anchor_substitutions": (
                antihotspot_anchor_substitutions
            ),
            "ready_antihotspot_history_length_max": antihotspot_history_length_max,
        },
        "required_lifetime_credit_terminal_congested_short_and_over_work_paths_exercised": breadth_passed,
        "deterministic_selection_contract_verified": True,
        "same_window_choice_observed": same_window_rejected > 0,
        "lifetime_credit_invariants_passed": credit_invariants,
        "work_and_queue_threshold_invariants_passed": work_invariants,
        "both_routes_exercised": both_routes,
        "ready_antihotspot_invariants_passed": antihotspot_invariants,
    }


def blind_audit_v164(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V164 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V164 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V164 execution receipt")
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
        raise RuntimeError("V164 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=3
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V164 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V164 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V164 has unexplained quarantined attempts")
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
        raise RuntimeError("V164 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V164 runtime identity changed")
    mechanism = _mechanism_falsification_gate(audits)
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_READY_ANTIHOTSPOT_LIFETIME_CREDIT_LOW_BLIND_AUDIT_V164_V1",
        "created_at": utc_now(),
        "status": "pass" if mechanism["passed"] else "fail",
        "performance_reveal_authorized": mechanism["passed"],
        "failure_reasons": mechanism["failure_reasons"],
        "mechanism_breadth_paths": mechanism["breadth_paths"],
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
        **mechanism["metrics"],
        "required_lifetime_credit_terminal_congested_short_and_over_work_paths_exercised": mechanism[
            "required_lifetime_credit_terminal_congested_short_and_over_work_paths_exercised"
        ],
        "deterministic_selection_contract_verified": mechanism[
            "deterministic_selection_contract_verified"
        ],
        "same_window_choice_observed": mechanism["same_window_choice_observed"],
        "same_window_choice_absence_is_not_a_failure": True,
        "lifetime_credit_invariants_passed": mechanism[
            "lifetime_credit_invariants_passed"
        ],
        "work_and_queue_threshold_invariants_passed": mechanism[
            "work_and_queue_threshold_invariants_passed"
        ],
        "both_routes_exercised": mechanism["both_routes_exercised"],
        "ready_antihotspot_invariants_passed": mechanism[
            "ready_antihotspot_invariants_passed"
        ],
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
        raise RuntimeError("V164 candidate result product changed")
    return rows


def reveal_v164(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V164 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V164 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get(
            "required_lifetime_credit_terminal_congested_short_and_over_work_paths_exercised"
        )
        is True
        and blind.get("deterministic_selection_contract_verified") is True
        and blind.get("same_window_choice_absence_is_not_a_failure") is True
        and blind.get("lifetime_credit_invariants_passed") is True
        and blind.get("work_and_queue_threshold_invariants_passed") is True
        and blind.get("both_routes_exercised") is True
        and blind.get("ready_antihotspot_invariants_passed") is True
    ):
        raise RuntimeError("V164 blind audit did not authorize reveal")
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
            "first_lifetime_credit_admissions",
            "rejected_already_credited",
            "rejected_same_window_not_selected",
            "same_window_choice_observed",
            "repeat_admission_violations",
            "requests_observed",
            "credited_request_observations_before",
            "credited_request_observations_after",
            "credited_requests_max",
            "rejected_nonterminal_players_with_incomplete_parents",
            "rejected_short_work_at_or_above_queue_threshold",
            "admitted_short_work_remaining_work_max",
            "rejected_over_threshold_remaining_work_min",
            "admitted_short_work_queue_density_max",
            "rejected_short_work_queue_density_min",
            "ready_antihotspot_eligible_players",
            "ready_antihotspot_dispatched_players",
            "ready_antihotspot_dispatched_with_history",
            "ready_antihotspot_v163_anchor_substitutions",
            "ready_antihotspot_history_length_max",
        )
    }
    mechanism["pass"] = (
        blind[
            "required_lifetime_credit_terminal_congested_short_and_over_work_paths_exercised"
        ]
        and blind["deterministic_selection_contract_verified"]
        and blind["lifetime_credit_invariants_passed"]
        and blind["work_and_queue_threshold_invariants_passed"]
        and blind["both_routes_exercised"]
        and blind["ready_antihotspot_invariants_passed"]
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
        "schema_version": "NSE_E1_HOMOGENEOUS_READY_ANTIHOTSPOT_LIFETIME_CREDIT_LOW_DIAGNOSTIC_RESULT_V164_V1",
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
            else "retain_all_three_valid_diagnostic_runs_and_retire_ready_antihotspot_candidate"
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
        document, key = prepare_v164(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v164(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v164(), "blind_audit_hash"
    else:
        document, key = reveal_v164(), "result_hash"
    print(json.dumps({key: document[key], "runs": 3}))


if __name__ == "__main__":
    main()
