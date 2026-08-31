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
    nse_e1_homogeneous_dual_lifetime_credit2_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v166 as base,
)
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
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
    "tmp/nse_e1_homogeneous_aged_dual_lifetime_credit2_slack_short_work_"
    "terminal_pipeline_queue8_low_diagnostic_20260901_v167"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_aged_dual_lifetime_credit2_slack_short_work_"
    "terminal_pipeline_queue8_low_diagnostic_plan_v167.json"
)
PLAN_SHA256 = "6036e4b1a76b24162db860d4ac42a847b53f9d5ef88cba3517b4b508c2b8a24e"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_aged_dual_lifetime_credit2_slack_short_work_"
    "terminal_pipeline_queue8_low_diagnostic_implementation_v167.json"
)
IMPLEMENTATION_SHA256 = (
    "8beecbb379f43136b1f0c38419976126bd6f6a7078a28e9c70d92d2ab2f30aa9"
)
V166_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_dual_lifetime_credit2_slack_short_work_terminal_"
    "pipeline_queue8_low_diagnostic_mechanism_failure_v166.json"
)
V166_FAILURE_SHA256 = "9b4653ff340ea414811e6cb10943fb2d28dda6cc5304483dcaba1f05d65964c0"
V166_FAILURE_HASH = "e74bc16b5ce889359b6a1a19e6242afa71092ce6611b56ad2b89a8d0db665bbd"
V166_TIMING = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_dual_lifetime_credit2_slack_short_work_terminal_"
    "pipeline_queue8_low_diagnostic_mechanism_timing_v166.json"
)
V166_TIMING_SHA256 = "2646ca45afbf84d2424b389c52e212c15b6ce44286c411fd700eca865f27079e"
V166_TIMING_HASH = "d149dff8e9d61e04074bb4e3429eb905497405d668de40ce3b1a6b15e42d0084"

ARM_ID = (
    "v167-low-srpt-slack-aged-dual-lifetime-credit2-short5p5-terminal-"
    "pipeline-hiku2-ocs-queue8"
)
PROFILE = (
    "srpt_slack_aged_dual_lifetime_credit2_short5p5_terminal_pipeline_"
    "hiku2_ocs_queue8"
)
FRONTIER = (
    "parents_completed_or_terminal_or_slack_aged_dual_lifetime_credit2_"
    "short_work_parents_scheduled"
)
SINGLE_CHANGE = (
    "V166_dual_lifetime_credit2_plus_identity_level_minimum_two_window_"
    "age_before_the_second_credit"
)
TERMINAL_DEFINITION = (
    "V163_frontier_and_scoring_with_at_most_two_deterministic_short_"
    "incomplete-parent_nonterminal_admissions_per_request_lifetime;"
    "the_second_requires_identity-level-age-at-least-two-windows_and_"
    "current_outstanding_speculation_at_most_one"
)
LIFETIME_CREDIT_DEFINITION = (
    "at_most_two_nonreusable_incomplete-parent_nonterminal_admissions_per_"
    "request_lifetime_with_identity_level_age_at_least_two_windows_and_"
    "current_outstanding_at_most_one_required_before_the_second"
)
LIFETIME_CREDIT_CONTRACT_DEFINITION = (
    "at_most_two_nonreusable_incomplete-parent_nonterminal_admissions_per_"
    "request_lifetime;the_second_requires_identity_level_age_at_least_two_"
    "windows_and_current_outstanding_speculation_at_most_one;select_maximum_"
    "immutable_critical_path_rank_then_minimum_function_id"
)
SELECTION_ORDER = base.SELECTION_ORDER
WORK_DEFINITION = base.WORK_DEFINITION
LOW_EXPERT = base.LOW_EXPERT
HIGH_EXPERT = base.HIGH_EXPERT
QUEUE_THRESHOLD = 8.0
SHORT_WORK_THRESHOLD = 5.5
MINIMUM_AGE_WINDOWS = 2
PORT = "3218"
BINARY_SOURCE_COMMIT = "a4a66be36c9ee064b929be67b39be3567fde44b7"
BINARY_PATH = Path("serverless_sim/target_e1_v167/release/serverless_sim.exe")
BINARY_SHA256 = "30bac01bef836cc00e8f7a30e04fff85366aa54b074cc0d863ee9f303042c637"
SEEDS = base.SEEDS


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v167.json",
        "schedule": root / "frozen-run-order-v167.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v167.json",
        "pairing": root / "pairing-audit-v167.json",
        "blind": root / "joint-blind-audit-v167.json",
        "result": root / "diagnostic-result-v167.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = base.previous._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V167 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V167 implementation receipt"),
        (V166_FAILURE, V166_FAILURE_SHA256, "V166 mechanism failure receipt"),
        (V166_TIMING, V166_TIMING_SHA256, "V166 mechanism timing audit"),
        (BINARY_PATH, BINARY_SHA256, "V167 release binary"),
        (base.PYTHON_PATH, base.PYTHON_SHA256, "frozen Python"),
        (
            Path("serverless_sim/Cargo.lock"),
            base.CARGO_LOCK_SHA256,
            "frozen Cargo.lock",
        ),
    ):
        base._assert_file(path, sha256, label)
    implementation = read_json(IMPLEMENTATION)
    change = implementation.get("single_scientific_change", {})
    if not (
        implementation.get("implementation_git_commit") == BINARY_SOURCE_COMMIT
        and implementation.get("plan_file_sha256") == PLAN_SHA256
        and implementation.get("release", {}).get("sha256") == BINARY_SHA256
        and implementation.get("profile") == PROFILE
        and change.get("second_credit_minimum_age_windows") == MINIMUM_AGE_WINDOWS
        and change.get("second_credit_max_outstanding_before_admission") == 1
        and change.get("credit_cap_per_request_lifetime") == 2
        and change.get("selected_credit_players_per_request_per_window_cap") == 1
        and change.get("projected_outstanding_speculation_cap") == 2
        and change.get("selection_order") == SELECTION_ORDER
        and change.get("operational_penalty") == "exact_V163_router_for_every_player"
        and change.get("changes_paper_formula_welfare_pricing_hpa_metrics_or_reference")
        is False
        and change.get(
            "uses_seed_load_tape_future_arrival_aggregate_completion_or_performance_outcomes"
        )
        is False
    ):
        raise RuntimeError("V167 implementation boundary changed")
    failure = read_json(V166_FAILURE)
    timing = read_json(V166_TIMING)
    if not (
        base._assert_hashed(failure, "receipt_hash", "V166 failure")
        == V166_FAILURE_HASH
        and failure.get("performance_reveal_authorized") is False
        and failure.get("performance_summary_files_opened") is False
        and base._assert_hashed(timing, "audit_hash", "V166 timing") == V166_TIMING_HASH
        and timing.get("performance_reveal_authorized") is False
        and timing.get("performance_summary_files_opened") is False
        and timing.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
    ):
        raise RuntimeError("V166 sealed result-blind boundary changed")
    base._assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        base.MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _contract(protocol_source_commit: str) -> dict[str, Any]:
    return {
        "v167_training_only": True,
        "v167_role": "result_blind_aged_dual_lifetime_credit2_falsification",
        "v167_plan_sha256": PLAN_SHA256,
        "v167_implementation_sha256": IMPLEMENTATION_SHA256,
        "v167_binary_source_commit": BINARY_SOURCE_COMMIT,
        "v167_protocol_source_commit": protocol_source_commit,
        "v167_binary_sha256": BINARY_SHA256,
        "v167_arm_id": ARM_ID,
        "v167_profile": PROFILE,
        "v167_player_frontier": FRONTIER,
        "v167_single_change_from_v166": SINGLE_CHANGE,
        "v167_short_work_threshold": SHORT_WORK_THRESHOLD,
        "v167_queue_density_threshold": QUEUE_THRESHOLD,
        "v167_queue_boundary": "below_is_strict",
        "v167_lifetime_credit_definition": LIFETIME_CREDIT_DEFINITION,
        "v167_lifetime_credit_contract_definition": LIFETIME_CREDIT_CONTRACT_DEFINITION,
        "v167_lifetime_credit_limit_per_request": 2,
        "v167_selection_order": SELECTION_ORDER,
        "v167_credit_reuse_after_parent_or_function_completion": False,
        "v167_second_credit_minimum_age_windows": MINIMUM_AGE_WINDOWS,
        "v167_second_credit_max_outstanding_before_admission": 1,
        "v167_selected_credit_players_per_request_per_window_cap": 1,
        "v167_projected_outstanding_speculation_cap": 2,
        "v167_ready_antihotspot_enabled": False,
        "v167_operational_score": "exact_V163_router_for_every_player",
        "v167_remaining_seventeen_authorized": False,
        "v167_confirmation_inputs_generated": False,
    }


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = base.previous._rewrite_candidate(source, protocol_source_commit)
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    for key in list(marker):
        if key.startswith("v163_"):
            marker.pop(key)
    contract = _contract(protocol_source_commit)
    marker.update(
        {
            "purpose": "V167 result-blind three-seed aged dual-credit diagnostic",
            **contract,
            "v167_environment": base.COMMON_ENVIRONMENT,
            "v167_expected_run_count": 3,
            "v167_expected_reference_build_count": 3,
            "v167_fixed_order": list(SEEDS),
            "v167_candidate_performance_summaries_parsed": 0,
        }
    )
    for run in rewritten["runs"]:
        old = run.get("metadata", {})
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            **contract,
            "v167_source_e1_run_id": old.get("v163_source_e1_run_id"),
            "v167_source_e1_run_spec_hash": old.get("v163_source_e1_run_spec_hash"),
            "v167_candidate_performance_summaries_parsed_before_run": 0,
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
        raise RuntimeError("V167 exact E09/E18/E20 product changed")
    expected = {**base.COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and all(run["environment"].get(k) == v for k, v in expected.items())
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v167_profile") == PROFILE
            and metadata.get("v167_player_frontier") == FRONTIER
            and metadata.get("v167_second_credit_minimum_age_windows")
            == MINIMUM_AGE_WINDOWS
            and metadata.get("v167_second_credit_max_outstanding_before_admission") == 1
            and metadata.get("v167_lifetime_credit_limit_per_request") == 2
            and metadata.get("v167_projected_outstanding_speculation_cap") == 2
            and metadata.get("v167_operational_score")
            == "exact_V163_router_for_every_player"
        ):
            raise RuntimeError(f"V167 run contract changed: {run.get('run_id')}")


def prepare_v167(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V167 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AGED_DUAL_LIFETIME_CREDIT2_LOW_SCHEDULE_V167_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AGED_DUAL_LIFETIME_CREDIT2_LOW_PREPARED_V167_V1",
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
        "python_sha256": base.PYTHON_SHA256,
        "cargo_lock_sha256": base.CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": base.MODULE_CONF_SEMANTIC_HASH,
        "source_manifest_hash": base.SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": base.SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": base.SOURCE_PAIRING_SHA256,
        "v166_failure_file_sha256": V166_FAILURE_SHA256,
        "v166_failure_hash": V166_FAILURE_HASH,
        "v166_timing_file_sha256": V166_TIMING_SHA256,
        "v166_timing_hash": V166_TIMING_HASH,
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
        "minimum_second_credit_age_windows": MINIMUM_AGE_WINDOWS,
        "second_credit_max_outstanding_before_admission": 1,
        "projected_outstanding_speculation_cap": 2,
        "operational_score": "exact_V163_router_for_every_player",
        "environment": base.COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v167(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V167 execution receipt already exists")
    prepared = read_json(output["prepared"])
    base._assert_hashed(prepared, "receipt_hash", "V167 prepared receipt")
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
            str(base.PYTHON_PATH),
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
                command, stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(f"V167 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V167 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AGED_DUAL_LIFETIME_CREDIT2_LOW_EXECUTION_V167_V1",
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
        raise RuntimeError(f"V167 {label} is invalid")
    return value


def _finite_optional(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V167 {label} is invalid")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(f"V167 {label} is non-finite")
    return result


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    archive = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    if not archive.is_file():
        raise RuntimeError(f"V167 nash archive missing: {run['run_id']}")
    counts = {
        "run_config": 0,
        "window": 0,
        "run_summary": 0,
        "function_profile": 0,
        "terminal": 0,
        "short": 0,
        "first": 0,
        "second": 0,
        "age_rejected": 0,
        "outstanding_rejected": 0,
        "already_credited": 0,
        "same_window_rejected": 0,
        "repeat_violations": 0,
        "age_violations": 0,
        "outstanding_violations": 0,
        "over_limit": 0,
        "requests_observed": 0,
        "credited_before": 0,
        "credited_after": 0,
        "second_before": 0,
        "second_after": 0,
        "retired_first": 0,
        "retired_second": 0,
        "frame_before": 0,
        "frame_after": 0,
        "retired_frames": 0,
        "missing_frames": 0,
        "orphan_frames": 0,
        "rejected": 0,
        "queue_rejected": 0,
        "low_routes": 0,
        "high_routes": 0,
    }
    selected_max = projected_max = credited_max = second_max = frame_max = 0
    admitted_work_max = admitted_density_max = None
    rejected_work_min = rejected_density_min = None
    admitted_age_min = admitted_age_max = None
    with gzip.open(archive, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"V167 malformed nash line {line_number}") from exc
            kind = event.get("kind")
            if kind == "function_profile":
                counts["function_profile"] += 1
                continue
            if kind == "run_config":
                counts["run_config"] += 1
                contract = event.get("operational_expert_proxy_contract", {})
                diagnostics = contract.get("lifetime_short_work_credit_diagnostics", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V167"
                    and contract.get("player_frontier") == FRONTIER
                    and contract.get("single_change_from_v155") == SINGLE_CHANGE
                    and contract.get("terminal_pipeline_definition")
                    == TERMINAL_DEFINITION
                    and contract.get("lifetime_short_work_credit_definition")
                    == LIFETIME_CREDIT_CONTRACT_DEFINITION
                    and diagnostics.get("credit_limit_per_request_lifetime") == 2
                    and diagnostics.get("second_credit_minimum_age_windows")
                    == MINIMUM_AGE_WINDOWS
                    and diagnostics.get(
                        "second_credit_max_outstanding_before_admission"
                    )
                    == 1
                    and diagnostics.get("projected_outstanding_limit") == 2
                    and contract.get("ready_antihotspot_required") is False
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V167 run_config contract changed")
                continue
            if kind == "run_summary":
                counts["run_summary"] += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V167 terminal nash marker changed")
                continue
            if kind != "window":
                raise RuntimeError(f"V167 unexpected nash kind: {kind}")
            expected_frame = counts["window"]
            if event.get("frame") != expected_frame:
                raise RuntimeError("V167 window sequence changed")
            counts["window"] += 1
            decision = event.get("decision", {})
            terminal = decision.get("terminal_pipeline_frontier", {})
            credit = terminal.get("lifetime_short_work_credit", {})
            router = decision.get("srpt_hiku2_ocs_queue_router", {})
            if not (
                decision.get("player_frontier") == FRONTIER
                and decision.get("pipeline_observation_fields_drive_future_windows")
                is False
                and terminal.get("enabled") is True
                and terminal.get("definition") == FRONTIER
                and terminal.get("uses_completion_or_performance_outcomes") is False
                and credit.get("enabled") is True
                and credit.get("definition") == LIFETIME_CREDIT_DEFINITION
                and credit.get("credit_limit_per_request_lifetime") == 2
                and credit.get("selection_order") == SELECTION_ORDER
                and credit.get("credit_reuse_after_parent_or_function_completion")
                is False
                and credit.get("second_credit_minimum_age_windows")
                == MINIMUM_AGE_WINDOWS
                and credit.get("second_credit_max_outstanding_before_admission") == 1
                and credit.get("projected_outstanding_limit") == 2
                and credit.get("uses_completion_or_performance_outcomes") is False
                and router.get("enabled") is True
                and router.get("queue_density_threshold") == QUEUE_THRESHOLD
                and router.get("player_frontier") == FRONTIER
                and router.get("uses_completion_outcomes") is False
            ):
                raise RuntimeError("V167 window mechanism contract changed")
            current = {
                key: _count(credit.get(source), f"{key} line {line_number}")
                for key, source in {
                    "first": "first_admissions",
                    "second": "second_admissions",
                    "age_rejected": "second_rejected_below_minimum_age",
                    "outstanding_rejected": "rejected_second_while_outstanding",
                    "already_credited": "rejected_already_credited",
                    "same_window_rejected": "rejected_same_window_not_selected",
                    "repeat_violations": "repeat_admission_violations",
                    "age_violations": "second_admission_age_violations",
                    "outstanding_violations": "second_admission_outstanding_violations",
                    "over_limit": "projected_requests_over_limit",
                    "requests_observed": "requests_observed",
                    "credited_before": "credited_requests_before",
                    "credited_after": "credited_requests_after",
                    "second_before": "second_credited_requests_before",
                    "second_after": "second_credited_requests_after",
                    "retired_first": "retired_credited_requests",
                    "retired_second": "retired_second_credited_requests",
                    "frame_before": "first_admission_frame_requests_before",
                    "frame_after": "first_admission_frame_requests_after",
                    "retired_frames": "retired_first_admission_frame_requests",
                    "missing_frames": "first_admission_frame_missing_requests",
                    "orphan_frames": "first_admission_frame_orphan_requests",
                }.items()
            }
            if not (
                current["credited_after"]
                == current["credited_before"]
                - current["retired_first"]
                + current["first"]
                and current["second_after"]
                == current["second_before"]
                - current["retired_second"]
                + current["second"]
                and current["frame_after"]
                == current["frame_before"]
                - current["retired_frames"]
                + current["first"]
                and current["frame_after"] == current["credited_after"]
                and current["missing_frames"] == 0
                and current["orphan_frames"] == 0
            ):
                raise RuntimeError("V167 identity-level credit conservation changed")
            age_min = credit.get("second_admission_age_min")
            age_max = credit.get("second_admission_age_max")
            if current["second"] > 0:
                age_min = _count(age_min, "second admission age min")
                age_max = _count(age_max, "second admission age max")
                if not (MINIMUM_AGE_WINDOWS <= age_min <= age_max):
                    raise RuntimeError("V167 second admission age changed")
                admitted_age_min = (
                    age_min
                    if admitted_age_min is None
                    else min(admitted_age_min, age_min)
                )
                admitted_age_max = (
                    age_max
                    if admitted_age_max is None
                    else max(admitted_age_max, age_max)
                )
            elif age_min is not None or age_max is not None:
                raise RuntimeError("V167 age diagnostic without second admission")
            for key, value in current.items():
                counts[key] += value
            selected_max = max(
                selected_max,
                _count(credit.get("selected_per_request_max"), "selected max"),
            )
            projected_max = max(
                projected_max,
                _count(credit.get("projected_outstanding_max"), "projected max"),
            )
            credited_max = max(credited_max, current["credited_after"])
            second_max = max(second_max, current["second_after"])
            frame_max = max(frame_max, current["frame_after"])
            terminal_admitted = _count(
                terminal.get("admitted_terminal_players_with_incomplete_parents"),
                "terminal admitted",
            )
            short_admitted = _count(
                terminal.get(
                    "admitted_short_work_nonterminal_players_with_incomplete_parents"
                ),
                "short admitted",
            )
            rejected = _count(
                terminal.get("rejected_nonterminal_players_with_incomplete_parents"),
                "nonterminal rejected",
            )
            queue_gate = terminal.get("short_work_queue_gate", {})
            queue_rejected = _count(
                queue_gate.get("rejected_short_work_at_or_above_threshold"),
                "queue rejected",
            )
            counts["terminal"] += terminal_admitted
            counts["short"] += short_admitted
            counts["rejected"] += rejected
            counts["queue_rejected"] += queue_rejected
            admitted_work = _finite_optional(
                terminal.get("admitted_short_work_remaining_work_max"), "admitted work"
            )
            rejected_work = _finite_optional(
                terminal.get("rejected_nonterminal_remaining_work_min"), "rejected work"
            )
            admitted_density = _finite_optional(
                queue_gate.get("admitted_short_work_queue_density_max"),
                "admitted density",
            )
            rejected_density = _finite_optional(
                queue_gate.get("rejected_short_work_queue_density_min"),
                "rejected density",
            )
            if admitted_work is not None:
                admitted_work_max = (
                    admitted_work
                    if admitted_work_max is None
                    else max(admitted_work_max, admitted_work)
                )
            if rejected_work is not None:
                rejected_work_min = (
                    rejected_work
                    if rejected_work_min is None
                    else min(rejected_work_min, rejected_work)
                )
            if admitted_density is not None:
                admitted_density_max = (
                    admitted_density
                    if admitted_density_max is None
                    else max(admitted_density_max, admitted_density)
                )
            if rejected_density is not None:
                rejected_density_min = (
                    rejected_density
                    if rejected_density_min is None
                    else min(rejected_density_min, rejected_density)
                )
            selected = router.get("selected_expert")
            if selected == LOW_EXPERT:
                counts["low_routes"] += 1
            elif selected == HIGH_EXPERT:
                counts["high_routes"] += 1
            else:
                raise RuntimeError("V167 router expert changed")
    if not (
        counts["run_config"] == 1
        and counts["window"] == 1000
        and counts["run_summary"] == 1
    ):
        raise RuntimeError("V167 nash event product changed")
    return {
        "seed": run["seed"],
        "run_id": run["run_id"],
        "archive_sha256": file_hash(archive),
        "windows": counts["window"],
        "admitted_terminal_players_with_incomplete_parents": counts["terminal"],
        "admitted_slack_short_work_nonterminal_players": counts["short"],
        "first_lifetime_credit_admissions": counts["first"],
        "second_lifetime_credit_admissions": counts["second"],
        "second_credit_rejected_below_minimum_age": counts["age_rejected"],
        "rejected_second_while_outstanding": counts["outstanding_rejected"],
        "rejected_cap_exhausted": counts["already_credited"],
        "rejected_same_window_not_selected": counts["same_window_rejected"],
        "repeat_admission_violations": counts["repeat_violations"],
        "second_admission_age_violations": counts["age_violations"],
        "second_admission_outstanding_violations": counts["outstanding_violations"],
        "projected_requests_over_limit": counts["over_limit"],
        "selected_per_request_max": selected_max,
        "projected_outstanding_max": projected_max,
        "second_admission_age_min": admitted_age_min,
        "second_admission_age_max": admitted_age_max,
        "requests_observed": counts["requests_observed"],
        "credited_request_observations_before": counts["credited_before"],
        "credited_request_observations_after": counts["credited_after"],
        "second_credited_request_observations_before": counts["second_before"],
        "second_credited_request_observations_after": counts["second_after"],
        "first_frame_request_observations_before": counts["frame_before"],
        "first_frame_request_observations_after": counts["frame_after"],
        "retired_first_credited_requests": counts["retired_first"],
        "retired_second_credited_requests": counts["retired_second"],
        "retired_first_frame_requests": counts["retired_frames"],
        "first_frame_missing_requests": counts["missing_frames"],
        "first_frame_orphan_requests": counts["orphan_frames"],
        "credited_requests_max": credited_max,
        "second_credited_requests_max": second_max,
        "first_frame_requests_max": frame_max,
        "rejected_nonterminal_players_with_incomplete_parents": counts["rejected"],
        "rejected_short_work_at_or_above_queue_threshold": counts["queue_rejected"],
        "admitted_short_work_remaining_work_max": admitted_work_max,
        "rejected_over_threshold_remaining_work_min": rejected_work_min,
        "admitted_short_work_queue_density_max": admitted_density_max,
        "rejected_short_work_queue_density_min": rejected_density_min,
        "below_threshold_route_windows": counts["low_routes"],
        "at_or_above_threshold_route_windows": counts["high_routes"],
        "function_profile_records_seen_without_payload_access": counts[
            "function_profile"
        ],
        "performance_outcome_fields_parsed": 0,
    }


def _mechanism_falsification_gate(
    audits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    summed = lambda key: sum(int(item[key]) for item in audits)
    first = summed("first_lifetime_credit_admissions")
    second = summed("second_lifetime_credit_admissions")
    age_rejected = summed("second_credit_rejected_below_minimum_age")
    terminal = summed("admitted_terminal_players_with_incomplete_parents")
    short = summed("admitted_slack_short_work_nonterminal_players")
    rejected = summed("rejected_nonterminal_players_with_incomplete_parents")
    queue_rejected = summed("rejected_short_work_at_or_above_queue_threshold")
    age_mins = [
        item["second_admission_age_min"]
        for item in audits
        if item["second_admission_age_min"] is not None
    ]
    age_maxs = [
        item["second_admission_age_max"]
        for item in audits
        if item["second_admission_age_max"] is not None
    ]
    admitted_work = [
        item["admitted_short_work_remaining_work_max"]
        for item in audits
        if item["admitted_short_work_remaining_work_max"] is not None
    ]
    rejected_work = [
        item["rejected_over_threshold_remaining_work_min"]
        for item in audits
        if item["rejected_over_threshold_remaining_work_min"] is not None
    ]
    admitted_density = [
        item["admitted_short_work_queue_density_max"]
        for item in audits
        if item["admitted_short_work_queue_density_max"] is not None
    ]
    rejected_density = [
        item["rejected_short_work_queue_density_min"]
        for item in audits
        if item["rejected_short_work_queue_density_min"] is not None
    ]
    low_routes = summed("below_threshold_route_windows")
    high_routes = summed("at_or_above_threshold_route_windows")
    selected_max = max(int(item["selected_per_request_max"]) for item in audits)
    projected_max = max(int(item["projected_outstanding_max"]) for item in audits)
    invariants = (
        first > 0
        and second > 0
        and second <= first
        and first + second <= short
        and summed("repeat_admission_violations") == 0
        and summed("second_admission_age_violations") == 0
        and summed("second_admission_outstanding_violations") == 0
        and summed("projected_requests_over_limit") == 0
        and summed("first_frame_missing_requests") == 0
        and summed("first_frame_orphan_requests") == 0
        and summed("retired_first_credited_requests")
        == summed("retired_first_frame_requests")
        and selected_max <= 1
        and projected_max <= 2
        and bool(age_mins)
        and min(age_mins) >= MINIMUM_AGE_WINDOWS
    )
    work_invariants = (
        bool(admitted_work)
        and bool(rejected_work)
        and bool(admitted_density)
        and bool(rejected_density)
        and max(admitted_work) <= SHORT_WORK_THRESHOLD
        and min(rejected_work) > SHORT_WORK_THRESHOLD
        and max(admitted_density) < QUEUE_THRESHOLD
        and min(rejected_density) >= QUEUE_THRESHOLD
    )
    breadth = {
        "terminal_admission": terminal > 0,
        "first_lifetime_credit_admission": first > 0,
        "second_aged_dual_lifetime_credit_admission": second > 0,
        "second_credit_blocked_below_minimum_age": age_rejected > 0,
        "generic_incomplete_parent_rejection": rejected > 0,
        "queue_threshold_rejection": queue_rejected > 0,
        "below_threshold_route": low_routes > 0,
        "at_or_above_threshold_route": high_routes > 0,
    }
    failures = [f"unexercised_{name}" for name, passed in breadth.items() if not passed]
    if not invariants:
        failures.append("aged_dual_lifetime_credit_invariant_failed")
    if not work_invariants:
        failures.append("work_or_queue_threshold_invariant_failed")
    metrics = {
        "admitted_terminal_players_with_incomplete_parents": terminal,
        "admitted_slack_short_work_nonterminal_players": short,
        "first_lifetime_credit_admissions": first,
        "second_lifetime_credit_admissions": second,
        "second_credit_rejected_below_minimum_age": age_rejected,
        "rejected_second_while_outstanding": summed(
            "rejected_second_while_outstanding"
        ),
        "rejected_cap_exhausted": summed("rejected_cap_exhausted"),
        "rejected_same_window_not_selected": summed(
            "rejected_same_window_not_selected"
        ),
        "repeat_admission_violations": summed("repeat_admission_violations"),
        "second_admission_age_violations": summed("second_admission_age_violations"),
        "second_admission_outstanding_violations": summed(
            "second_admission_outstanding_violations"
        ),
        "projected_requests_over_limit": summed("projected_requests_over_limit"),
        "selected_per_request_max": selected_max,
        "projected_outstanding_max": projected_max,
        "second_admission_age_min": min(age_mins) if age_mins else None,
        "second_admission_age_max": max(age_maxs) if age_maxs else None,
        "first_frame_missing_requests": summed("first_frame_missing_requests"),
        "first_frame_orphan_requests": summed("first_frame_orphan_requests"),
        "retired_first_credited_requests": summed("retired_first_credited_requests"),
        "retired_first_frame_requests": summed("retired_first_frame_requests"),
        "rejected_nonterminal_players_with_incomplete_parents": rejected,
        "rejected_short_work_at_or_above_queue_threshold": queue_rejected,
        "admitted_short_work_remaining_work_max": max(admitted_work)
        if admitted_work
        else None,
        "rejected_over_threshold_remaining_work_min": min(rejected_work)
        if rejected_work
        else None,
        "admitted_short_work_queue_density_max": max(admitted_density)
        if admitted_density
        else None,
        "rejected_short_work_queue_density_min": min(rejected_density)
        if rejected_density
        else None,
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
    }
    passed = all(breadth.values()) and invariants and work_invariants
    return {
        "passed": passed,
        "failure_reasons": failures,
        "breadth_paths": breadth,
        "metrics": metrics,
        "aged_dual_lifetime_credit_invariants_passed": invariants,
        "work_and_queue_threshold_invariants_passed": work_invariants,
        "both_routes_exercised": low_routes > 0 and high_routes > 0,
    }


def blind_audit_v167(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V167 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = base._assert_hashed(prepared, "receipt_hash", "V167 prepared")
    execution = read_json(output["execution"])
    execution_hash = base._assert_hashed(execution, "receipt_hash", "V167 execution")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = base.audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed")
        and pairing.get("run_count") == 3
        and pairing.get("group_count") == 3
    ):
        raise RuntimeError("V167 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = base.verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = base._validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=3
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V167 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V167 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V167 has unexplained quarantined attempts")
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
        raise RuntimeError("V167 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == base.PYTHON_SHA256
        and cargo == base.CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V167 runtime identity changed")
    mechanism = _mechanism_falsification_gate(audits)
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AGED_DUAL_LIFETIME_CREDIT2_LOW_BLIND_AUDIT_V167_V1",
        "created_at": utc_now(),
        "status": "pass" if mechanism["passed"] else "fail",
        "performance_reveal_authorized": mechanism["passed"],
        "failure_reasons": mechanism["failure_reasons"],
        "mechanism_breadth_paths": mechanism["breadth_paths"],
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
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
        **mechanism["metrics"],
        "aged_dual_lifetime_credit_invariants_passed": mechanism[
            "aged_dual_lifetime_credit_invariants_passed"
        ],
        "work_and_queue_threshold_invariants_passed": mechanism[
            "work_and_queue_threshold_invariants_passed"
        ],
        "both_routes_exercised": mechanism["both_routes_exercised"],
        "ready_antihotspot_disabled": True,
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
                **base._metrics(
                    values.get("throughput"),
                    values.get("latency_mean_ms"),
                    values.get("cost"),
                    values.get("completed"),
                ),
            }
        )
    if len(rows) != 3 or [row["seed"] for row in rows] != list(SEEDS):
        raise RuntimeError("V167 candidate result product changed")
    return rows


def reveal_v167(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V167 result already exists")
    blind = read_json(output["blind"])
    blind_hash = base._assert_hashed(blind, "blind_audit_hash", "V167 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("aged_dual_lifetime_credit_invariants_passed") is True
        and blind.get("work_and_queue_threshold_invariants_passed") is True
        and blind.get("both_routes_exercised") is True
        and blind.get("ready_antihotspot_disabled") is True
        and blind.get("mechanism_breadth_paths", {}).get(
            "first_lifetime_credit_admission"
        )
        is True
        and blind.get("mechanism_breadth_paths", {}).get(
            "second_aged_dual_lifetime_credit_admission"
        )
        is True
        and blind.get("mechanism_breadth_paths", {}).get(
            "second_credit_blocked_below_minimum_age"
        )
        is True
    ):
        raise RuntimeError("V167 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = _load_candidate(manifest, root)
    v155_rows = base._load_v155_candidate(
        load_and_validate_manifest(base.V155_READY), base.V155_ROOT
    )
    hybrid = base._hybrid_rows(v155_rows, candidate)
    evaluation = base._evaluate_load("low", hybrid, base._load_baselines())
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
        > base.THROUGHPUT_THREE_SEED_SUM_GATE,
        "throughput_three_seed_paired_wins": throughput_wins,
        "throughput_three_seed_paired_wins_pass": throughput_wins >= 2,
        "qpr_three_seed_sum": qpr_sum,
        "qpr_three_seed_sum_pass": qpr_sum > base.QPR_THREE_SEED_SUM_GATE,
        "qpr_three_seed_all_finite": all(math.isfinite(value) for value in qpr_values),
    }
    passed = (
        evaluation["all_three_metric_gates_pass"]
        and diagnostic["throughput_three_seed_sum_pass"]
        and diagnostic["throughput_three_seed_paired_wins_pass"]
        and diagnostic["qpr_three_seed_sum_pass"]
        and diagnostic["qpr_three_seed_all_finite"]
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_AGED_DUAL_LIFETIME_CREDIT2_LOW_DIAGNOSTIC_RESULT_V167_V1",
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
        "mechanism_gate": {
            "pass": True,
            "first_lifetime_credit_admissions": blind[
                "first_lifetime_credit_admissions"
            ],
            "second_lifetime_credit_admissions": blind[
                "second_lifetime_credit_admissions"
            ],
            "second_credit_rejected_below_minimum_age": blind[
                "second_credit_rejected_below_minimum_age"
            ],
            "second_admission_age_min": blind["second_admission_age_min"],
            "second_admission_age_max": blind["second_admission_age_max"],
        },
        "joint_diagnostic_pass": passed,
        "disposition": (
            "authorize_separately_committed_remaining_seventeen_training_plan_without_rerunning_E09_E18_E20"
            if passed
            else "retain_all_three_valid_diagnostic_runs_and_retire_aged_dual_lifetime_credit2_candidate"
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
        document, key = prepare_v167(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v167(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v167(), "blind_audit_hash"
    else:
        document, key = reveal_v167(), "result_hash"
    print(json.dumps({key: document[key], "runs": 3}))


if __name__ == "__main__":
    main()
