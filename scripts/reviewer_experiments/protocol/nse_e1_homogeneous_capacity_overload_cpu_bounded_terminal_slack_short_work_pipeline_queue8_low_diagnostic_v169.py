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
    nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v159 as v159,
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
    "tmp/nse_e1_homogeneous_capacity_overload_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_20260901_v169"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_capacity_overload_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_plan_v169.json"
)
PLAN_SHA256 = "ab9f4d3f88faa04b041ead9b22b49e44dad864e14fffc40faacf50fe25fd8801"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_capacity_overload_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_implementation_v169.json"
)
IMPLEMENTATION_SHA256 = (
    "1d96a280a056aa4f46170ec00f0650f05013f8f77eb21b146a19359897a7040c"
)
V168_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_failure_v168.json"
)
V168_FAILURE_SHA256 = "aa0ca95bba6f724374325a56ae2a69f3441c7cbe849f8793dc30955f02ff0cde"
V168_FAILURE_HASH = "cb98a549cfdf8ab90822fd4ec1eef4d23aec4e589b2fcf07ac02a5dd2c0fdecd"

ARM_ID = "v169-low-srpt-slack-capacity-overload-cpu-bounded-terminal-short5p5-pipeline-hiku2-ocs-queue8"
PROFILE = "srpt_slack_capacity_overload_cpu_bounded_terminal_short5p5_pipeline_hiku2_ocs_queue8"
FRONTIER = "parents_completed_or_capacity_overload_cpu_bounded_terminal_or_slack_short_work_parents_scheduled"
SINGLE_CHANGE = (
    "V168_cpu_bound_activated_only_when_current_heavy_incomplete_parent_terminal_"
    "player_count_strictly_exceeds_node_count"
)
TERMINAL_DEFINITION = (
    "admit_all_parents-completed_players;activate_the_V168_incomplete-parent-terminal_"
    "CPU_bound_only_when_current_heavy_terminal_player_count_strictly_exceeds_"
    "node_count;otherwise_retain_V159_terminal_admission;retain_V159_nonterminal_"
    "short-work_frontier"
)
CPU_THRESHOLD = 1.0
SHORT_WORK_THRESHOLD = v159.SHORT_WORK_THRESHOLD
QUEUE_THRESHOLD = v159.QUEUE_THRESHOLD
LOW_EXPERT = v159.LOW_EXPERT
HIGH_EXPERT = v159.HIGH_EXPERT
WORK_DEFINITION = v159.WORK_DEFINITION
PORT = v159.PORT

BINARY_SOURCE_COMMIT = "3f4fe59c559365895de5dd5ef96d95621a8b19f2"
BINARY_PATH = Path("serverless_sim/target_e1_v169/release/serverless_sim.exe")
BINARY_SHA256 = "28c1808c1eb0924f484f0118b6dc6d00efcdf03fe7f7526db01c5017b8eba248"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v169.json",
        "schedule": root / "frozen-run-order-v169.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v169.json",
        "pairing": root / "pairing-audit-v169.json",
        "blind": root / "joint-blind-audit-v169.json",
        "result": root / "diagnostic-result-v169.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v159._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V169 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V169 implementation receipt"),
        (V168_FAILURE, V168_FAILURE_SHA256, "V168 sealed failure receipt"),
        (BINARY_PATH, BINARY_SHA256, "V169 release binary"),
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
        and change.get("activation_boundary") == "strictly_above_activates"
        and change.get("capacity_threshold") == "current cluster node_count"
        and change.get("inactive_behavior") == "exact_V159_terminal_admission"
        and change.get("active_behavior") == "exact_V168_CPU_bound"
        and change.get("parents_completed_bypass") is True
        and change.get("short_work_remaining_work_threshold") == SHORT_WORK_THRESHOLD
        and change.get("short_work_queue_density_threshold") == QUEUE_THRESHOLD
        and change.get("changes_paper_formula_welfare_pricing_hpa_metrics_or_reference")
        is False
    ):
        raise RuntimeError("V169 implementation boundary changed")
    failure = read_json(V168_FAILURE)
    if not (
        _assert_hashed(failure, "receipt_hash", "V168 failure receipt")
        == V168_FAILURE_HASH
        and failure.get("disposition", {}).get(
            "remaining_seventeen_v168_runs_authorized"
        )
        is False
        and failure.get("disposition", {}).get("retain_all_three_valid_diagnostic_runs")
        is True
    ):
        raise RuntimeError("V168 failure boundary changed")
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = v159._rewrite_candidate(source, protocol_source_commit)
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    for key in list(marker):
        if key.startswith("v159_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": (
                "V169 outcome-disclosed three-seed capacity-overload CPU-bounded "
                "terminal diagnostic; "
                "never a formal result or paper superiority claim"
            ),
            "v169_role": "result_blind_capacity_overload_cpu_bounded_terminal_falsification",
            "v169_plan_sha256": PLAN_SHA256,
            "v169_implementation_sha256": IMPLEMENTATION_SHA256,
            "v169_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v169_protocol_source_commit": protocol_source_commit,
            "v169_binary_sha256": BINARY_SHA256,
            "v169_arm_id": ARM_ID,
            "v169_profile": PROFILE,
            "v169_player_frontier": FRONTIER,
            "v169_single_change_from_v168": SINGLE_CHANGE,
            "v169_cpu_threshold": CPU_THRESHOLD,
            "v169_cpu_boundary": "at_or_below_is_admitted",
            "v169_overload_threshold": "current_cluster_node_count",
            "v169_overload_activation_boundary": "strictly_above_activates",
            "v169_inactive_behavior": "exact_V159_terminal_admission",
            "v169_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v169_queue_density_threshold": QUEUE_THRESHOLD,
            "v169_queue_boundary": "below_is_strict",
            "v169_environment": COMMON_ENVIRONMENT,
            "v169_expected_run_count": 3,
            "v169_expected_reference_build_count": 3,
            "v169_fixed_order": list(SEEDS),
            "v169_candidate_performance_summaries_parsed": 0,
            "v169_remaining_seventeen_authorized": False,
            "v169_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        old = run.get("metadata", {})
        source_run_id = old.get("v159_source_e1_run_id")
        source_run_spec_hash = old.get("v159_source_e1_run_spec_hash")
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v169_training_only": True,
            "v169_role": "result_blind_capacity_overload_cpu_bounded_terminal_falsification",
            "v169_plan_sha256": PLAN_SHA256,
            "v169_implementation_sha256": IMPLEMENTATION_SHA256,
            "v169_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v169_protocol_source_commit": protocol_source_commit,
            "v169_binary_sha256": BINARY_SHA256,
            "v169_arm_id": ARM_ID,
            "v169_profile": PROFILE,
            "v169_player_frontier": FRONTIER,
            "v169_single_change_from_v168": SINGLE_CHANGE,
            "v169_cpu_threshold": CPU_THRESHOLD,
            "v169_cpu_boundary": "at_or_below_is_admitted",
            "v169_overload_threshold": "current_cluster_node_count",
            "v169_overload_activation_boundary": "strictly_above_activates",
            "v169_inactive_behavior": "exact_V159_terminal_admission",
            "v169_short_work_threshold": SHORT_WORK_THRESHOLD,
            "v169_queue_density_threshold": QUEUE_THRESHOLD,
            "v169_queue_boundary": "below_is_strict",
            "v169_source_e1_run_id": source_run_id,
            "v169_source_e1_run_spec_hash": source_run_spec_hash,
            "v169_candidate_performance_summaries_parsed_before_run": 0,
            "v169_remaining_seventeen_authorized": False,
            "v169_confirmation_inputs_generated": False,
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
        raise RuntimeError("V169 exact E09/E18/E20 product changed")
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
            and metadata.get("v169_profile") == PROFILE
            and metadata.get("v169_player_frontier") == FRONTIER
            and metadata.get("v169_cpu_threshold") == CPU_THRESHOLD
            and metadata.get("v169_cpu_boundary") == "at_or_below_is_admitted"
            and metadata.get("v169_overload_threshold") == "current_cluster_node_count"
            and metadata.get("v169_overload_activation_boundary")
            == "strictly_above_activates"
            and metadata.get("v169_inactive_behavior")
            == "exact_V159_terminal_admission"
            and metadata.get("v169_short_work_threshold") == SHORT_WORK_THRESHOLD
            and metadata.get("v169_queue_density_threshold") == QUEUE_THRESHOLD
            and metadata.get("v169_queue_boundary") == "below_is_strict"
        ):
            raise RuntimeError(f"V169 run contract changed: {run.get('run_id')}")


def prepare_v169(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V169 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAPACITY_OVERLOAD_CPU_BOUNDED_TERMINAL_LOW_SCHEDULE_V169_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAPACITY_OVERLOAD_CPU_BOUNDED_TERMINAL_LOW_PREPARED_V169_V1",
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
        "v168_failure_file_sha256": V168_FAILURE_SHA256,
        "v168_failure_hash": V168_FAILURE_HASH,
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
        "cpu_threshold": CPU_THRESHOLD,
        "cpu_boundary": "at_or_below_is_admitted",
        "overload_threshold": "current_cluster_node_count",
        "overload_activation_boundary": "strictly_above_activates",
        "inactive_behavior": "exact_V159_terminal_admission",
        "short_work_threshold": SHORT_WORK_THRESHOLD,
        "queue_density_threshold": QUEUE_THRESHOLD,
        "queue_boundary": "below_is_strict",
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v169(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V169 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V169 prepared receipt")
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
            raise RuntimeError(f"V169 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V169 canonical is not a QC pass: {run['run_id']}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_CAPACITY_OVERLOAD_CPU_BOUNDED_TERMINAL_LOW_EXECUTION_V169_V1",
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


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    counts = {"run_config": 0, "window": 0, "run_summary": 0, "function_profile": 0}
    totals = {
        "terminal": 0,
        "short": 0,
        "rejected": 0,
        "queue_rejected": 0,
        "incomplete": 0,
        "guard_admitted": 0,
        "guard_rejected": 0,
        "guard_bypass": 0,
        "capacity_overload_heavy": 0,
        "capacity_overload_active_windows": 0,
        "capacity_overload_inactive_windows": 0,
        "capacity_overload_inactive_heavy_admissions": 0,
        "low_routes": 0,
        "high_routes": 0,
        "reference_available": 0,
        "reference_not_requested": 0,
    }
    extrema: dict[str, float | None] = {
        "admitted_work_max": None,
        "rejected_work_min": None,
        "admitted_density_max": None,
        "rejected_density_min": None,
        "guard_admitted_ratio_max": None,
        "guard_active_admitted_ratio_max": None,
        "guard_inactive_admitted_ratio_max": None,
        "guard_rejected_ratio_min": None,
    }

    def update_max(key: str, value: float | None) -> None:
        if value is not None:
            extrema[key] = value if extrema[key] is None else max(extrema[key], value)

    def update_min(key: str, value: float | None) -> None:
        if value is not None:
            extrema[key] = value if extrema[key] is None else min(extrema[key], value)

    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind not in counts:
                raise RuntimeError(f"unexpected V169 Nash observation kind: {kind}")
            counts[kind] += 1
            if kind == "run_config":
                contract = event.get("operational_expert_proxy_contract", {})
                guard = contract.get("cpu_bounded_terminal_guard", {})
                activation = guard.get("capacity_overload_activation", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V169"
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
                    and guard.get("normalized_cpu_threshold") == CPU_THRESHOLD
                    and guard.get("boundary") == "at_or_below_is_admitted"
                    and guard.get("numerator") == "immutable_function_cpu_work"
                    and guard.get("denominator")
                    == "current_cluster_mean_node_cpu_capacity"
                    and guard.get("parents_completed_bypass") is True
                    and guard.get("uses_completion_or_performance_outcomes") is False
                    and activation.get("heavy_player_definition")
                    == "collectable_incomplete-parent_terminal_player_with_immutable_function_cpu_work_over_current_cluster_mean_node_cpu_capacity_strictly_above_one"
                    and activation.get("capacity_threshold")
                    == "current_cluster_node_count"
                    and activation.get("activation_boundary")
                    == "heavy_player_count_strictly_above_node_count"
                    and activation.get("inactive_behavior") == "V159_terminal_admission"
                    and activation.get(
                        "uses_seed_load_dag_function_or_performance_labels"
                    )
                    is False
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V169 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != counts["window"] - 1:
                    raise RuntimeError("V169 scheduler window sequence changed")
                decision = event.get("decision", {})
                decision_hash = decision.get("assignment_hash")
                if (
                    isinstance(decision_hash, bool)
                    or not isinstance(decision_hash, int)
                    or decision_hash < 0
                    or decision.get("player_frontier") != FRONTIER
                ):
                    raise RuntimeError("V169 decision frontier/hash changed")
                frontier = decision.get("terminal_pipeline_frontier", {})
                terminal_now = v159._count(
                    frontier.get("admitted_terminal_players_with_incomplete_parents"),
                    "terminal admission count",
                )
                short_now = v159._count(
                    frontier.get(
                        "admitted_short_work_nonterminal_players_with_incomplete_parents"
                    ),
                    "short-work admission count",
                )
                rejected_now = v159._count(
                    frontier.get(
                        "rejected_nonterminal_players_with_incomplete_parents"
                    ),
                    "frontier rejection count",
                )
                incomplete_now = v159._count(
                    decision.get("pipeline_players_with_incomplete_parents"),
                    "pipeline incomplete-parent count",
                )
                work_max_now = v159._finite_optional(
                    frontier.get("admitted_short_work_remaining_work_max"),
                    "admitted work maximum",
                )
                work_min_now = v159._finite_optional(
                    frontier.get("rejected_nonterminal_remaining_work_min"),
                    "rejected work minimum",
                )
                queue_gate = frontier.get("short_work_queue_gate", {})
                queue_rejected_now = v159._count(
                    queue_gate.get("rejected_short_work_at_or_above_threshold"),
                    "queue-gated rejection count",
                )
                admitted_density_now = v159._finite_optional(
                    queue_gate.get("admitted_short_work_queue_density_max"),
                    "admitted queue-density maximum",
                )
                rejected_density_now = v159._finite_optional(
                    queue_gate.get("rejected_short_work_queue_density_min"),
                    "rejected queue-density minimum",
                )
                guard = frontier.get("cpu_bounded_terminal_guard", {})
                guard_admitted_now = v159._count(
                    guard.get("admitted_incomplete_parent_terminal_players"),
                    "CPU-guard admitted count",
                )
                guard_rejected_now = v159._count(
                    guard.get("rejected_heavy_incomplete_parent_terminal_players"),
                    "CPU-guard rejected count",
                )
                guard_bypass_now = v159._count(
                    guard.get("parents_completed_heavy_terminal_bypass_players"),
                    "CPU-guard parent-completed bypass count",
                )
                guard_admitted_ratio_now = v159._finite_optional(
                    guard.get("admitted_normalized_cpu_max"),
                    "CPU-guard admitted ratio maximum",
                )
                guard_rejected_ratio_now = v159._finite_optional(
                    guard.get("rejected_normalized_cpu_min"),
                    "CPU-guard rejected ratio minimum",
                )
                activation = guard.get("capacity_overload_activation", {})
                heavy_now = v159._count(
                    activation.get("heavy_incomplete_parent_terminal_players"),
                    "capacity-overload heavy player count",
                )
                node_count_now = v159._count(
                    activation.get("node_count_threshold"),
                    "capacity-overload node count",
                )
                inactive_heavy_admissions_now = v159._count(
                    activation.get("guard_inactive_heavy_terminal_admissions"),
                    "capacity-overload inactive heavy admission count",
                )
                guard_active_now = activation.get("guard_active")
                guard_inactive_now = activation.get("guard_inactive")
                if not (
                    frontier.get("enabled") is True
                    and frontier.get("definition") == FRONTIER
                    and frontier.get("short_work_remaining_work_threshold")
                    == SHORT_WORK_THRESHOLD
                    and frontier.get("terminal_topology_source")
                    == "immutable_function_children_is_empty"
                    and frontier.get("uses_completion_or_performance_outcomes") is False
                    and guard.get("enabled") is True
                    and guard.get("normalized_cpu_threshold") == CPU_THRESHOLD
                    and guard.get("boundary") == "at_or_below_is_admitted"
                    and guard.get("numerator") == "immutable_function_cpu_work"
                    and guard.get("denominator")
                    == "current_cluster_mean_node_cpu_capacity"
                    and guard.get("uses_completion_or_performance_outcomes") is False
                    and activation.get("enabled") is True
                    and node_count_now == 20
                    and activation.get("activation_boundary")
                    == "strictly_above_activates"
                    and isinstance(guard_active_now, bool)
                    and isinstance(guard_inactive_now, bool)
                    and guard_inactive_now is (not guard_active_now)
                    and guard_active_now is (heavy_now > node_count_now)
                    and activation.get(
                        "uses_seed_load_dag_function_or_performance_labels"
                    )
                    is False
                    and guard_admitted_now == terminal_now
                    and (guard_admitted_now == 0) == (guard_admitted_ratio_now is None)
                    and (guard_rejected_now == 0) == (guard_rejected_ratio_now is None)
                    and (
                        not guard_active_now
                        or guard_admitted_ratio_now is None
                        or guard_admitted_ratio_now <= CPU_THRESHOLD
                    )
                    and (
                        guard_rejected_ratio_now is None
                        or guard_rejected_ratio_now > CPU_THRESHOLD
                    )
                    and (
                        guard_active_now
                        and guard_rejected_now == heavy_now
                        and inactive_heavy_admissions_now == 0
                        or guard_inactive_now
                        and guard_rejected_now == 0
                        and inactive_heavy_admissions_now == heavy_now
                    )
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
                    raise RuntimeError("V169 CPU/slack/queue frontier evidence changed")
                totals["terminal"] += terminal_now
                totals["short"] += short_now
                totals["rejected"] += rejected_now
                totals["queue_rejected"] += queue_rejected_now
                totals["incomplete"] += incomplete_now
                totals["guard_admitted"] += guard_admitted_now
                totals["guard_rejected"] += guard_rejected_now
                totals["guard_bypass"] += guard_bypass_now
                totals["capacity_overload_heavy"] += heavy_now
                totals["capacity_overload_active_windows"] += int(guard_active_now)
                totals["capacity_overload_inactive_windows"] += int(guard_inactive_now)
                totals[
                    "capacity_overload_inactive_heavy_admissions"
                ] += inactive_heavy_admissions_now
                update_max("admitted_work_max", work_max_now)
                update_min("rejected_work_min", work_min_now)
                update_max("admitted_density_max", admitted_density_now)
                update_min("rejected_density_min", rejected_density_now)
                update_max("guard_admitted_ratio_max", guard_admitted_ratio_now)
                if guard_active_now:
                    update_max(
                        "guard_active_admitted_ratio_max", guard_admitted_ratio_now
                    )
                else:
                    update_max(
                        "guard_inactive_admitted_ratio_max", guard_admitted_ratio_now
                    )
                update_min("guard_rejected_ratio_min", guard_rejected_ratio_now)
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
                    raise RuntimeError("V169 route telemetry is incomplete")
                expected = (
                    LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
                )
                if route.get("selected_expert") != expected:
                    raise RuntimeError("V169 route does not match queue density")
                totals["low_routes"] += expected == LOW_EXPERT
                totals["high_routes"] += expected == HIGH_EXPERT
                social = event.get("social", {})
                key, source = social.get("reference_state_key"), social.get(
                    "reference_source"
                )
                if key is None:
                    if source != "not_requested":
                        raise RuntimeError("V169 unrequested reference reason changed")
                    totals["reference_not_requested"] += 1
                elif source in ("offline_table", "offline_table_nonpositive"):
                    totals["reference_available"] += 1
                else:
                    raise RuntimeError("V169 bound reference source changed")
            elif kind == "run_summary":
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V169 Nash terminal marker changed")
            # Function-profile payloads are deliberately not inspected.
    if (
        counts["run_config"] != 1
        or counts["window"] != 1000
        or counts["run_summary"] != 1
    ):
        raise RuntimeError("V169 Nash log cardinality changed")
    if (
        totals["reference_available"] + totals["reference_not_requested"]
        != counts["window"]
    ):
        raise RuntimeError("V169 reference replay coverage changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": counts["window"],
        "admitted_terminal_players_with_incomplete_parents": totals["terminal"],
        "admitted_slack_short_work_nonterminal_players": totals["short"],
        "rejected_frontier_players_with_incomplete_parents": totals["rejected"],
        "rejected_short_work_at_or_above_queue_threshold": totals["queue_rejected"],
        "cpu_guard_admitted_incomplete_parent_terminal_players": totals[
            "guard_admitted"
        ],
        "cpu_guard_rejected_heavy_incomplete_parent_terminal_players": totals[
            "guard_rejected"
        ],
        "cpu_guard_parent_completed_heavy_terminal_bypass_players": totals[
            "guard_bypass"
        ],
        "cpu_guard_admitted_normalized_cpu_max": extrema["guard_admitted_ratio_max"],
        "cpu_guard_active_admitted_normalized_cpu_max": extrema[
            "guard_active_admitted_ratio_max"
        ],
        "cpu_guard_inactive_admitted_normalized_cpu_max": extrema[
            "guard_inactive_admitted_ratio_max"
        ],
        "cpu_guard_rejected_normalized_cpu_min": extrema["guard_rejected_ratio_min"],
        "capacity_overload_heavy_incomplete_parent_terminal_players": totals[
            "capacity_overload_heavy"
        ],
        "capacity_overload_guard_active_windows": totals[
            "capacity_overload_active_windows"
        ],
        "capacity_overload_guard_inactive_windows": totals[
            "capacity_overload_inactive_windows"
        ],
        "capacity_overload_guard_inactive_heavy_terminal_admissions": totals[
            "capacity_overload_inactive_heavy_admissions"
        ],
        "admitted_short_work_remaining_work_max": extrema["admitted_work_max"],
        "rejected_over_threshold_remaining_work_min": extrema["rejected_work_min"],
        "admitted_short_work_queue_density_max": extrema["admitted_density_max"],
        "rejected_short_work_queue_density_min": extrema["rejected_density_min"],
        "feasible_pipeline_players_with_incomplete_parents": totals["incomplete"],
        "below_threshold_route_windows": totals["low_routes"],
        "at_or_above_threshold_route_windows": totals["high_routes"],
        "offline_reference_windows": totals["reference_available"],
        "legitimate_not_requested_windows": totals["reference_not_requested"],
        "function_profile_records_seen_without_payload_access": counts[
            "function_profile"
        ],
        "performance_outcome_fields_parsed": 0,
    }


def _mechanism_falsification_gate(
    audits: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    sum_keys = (
        "admitted_terminal_players_with_incomplete_parents",
        "admitted_slack_short_work_nonterminal_players",
        "rejected_frontier_players_with_incomplete_parents",
        "rejected_short_work_at_or_above_queue_threshold",
        "cpu_guard_admitted_incomplete_parent_terminal_players",
        "cpu_guard_rejected_heavy_incomplete_parent_terminal_players",
        "cpu_guard_parent_completed_heavy_terminal_bypass_players",
        "capacity_overload_heavy_incomplete_parent_terminal_players",
        "capacity_overload_guard_active_windows",
        "capacity_overload_guard_inactive_windows",
        "capacity_overload_guard_inactive_heavy_terminal_admissions",
        "below_threshold_route_windows",
        "at_or_above_threshold_route_windows",
    )
    totals = {key: sum(int(audit[key]) for audit in audits) for key in sum_keys}
    max_keys = (
        "cpu_guard_admitted_normalized_cpu_max",
        "cpu_guard_active_admitted_normalized_cpu_max",
        "cpu_guard_inactive_admitted_normalized_cpu_max",
        "admitted_short_work_remaining_work_max",
        "admitted_short_work_queue_density_max",
    )
    min_keys = (
        "cpu_guard_rejected_normalized_cpu_min",
        "rejected_over_threshold_remaining_work_min",
        "rejected_short_work_queue_density_min",
    )
    extrema: dict[str, float | None] = {}
    for key in max_keys:
        values = [float(a[key]) for a in audits if a[key] is not None]
        extrema[key] = max(values) if values else None
    for key in min_keys:
        values = [float(a[key]) for a in audits if a[key] is not None]
        extrema[key] = min(values) if values else None
    passed = (
        all(value > 0 for value in totals.values())
        and all(extrema[key] is not None for key in extrema)
        and extrema["cpu_guard_active_admitted_normalized_cpu_max"] <= CPU_THRESHOLD
        and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"] > CPU_THRESHOLD
        and extrema["cpu_guard_rejected_normalized_cpu_min"] > CPU_THRESHOLD
        and extrema["admitted_short_work_remaining_work_max"] <= SHORT_WORK_THRESHOLD
        and extrema["rejected_over_threshold_remaining_work_min"] > SHORT_WORK_THRESHOLD
        and extrema["admitted_short_work_queue_density_max"] < QUEUE_THRESHOLD
        and extrema["rejected_short_work_queue_density_min"] >= QUEUE_THRESHOLD
    )
    return {
        **totals,
        **extrema,
        "cpu_guard_light_admission_heavy_rejection_and_parent_completed_bypass_exercised": (
            totals["cpu_guard_admitted_incomplete_parent_terminal_players"] > 0
            and totals["cpu_guard_rejected_heavy_incomplete_parent_terminal_players"]
            > 0
            and totals["cpu_guard_parent_completed_heavy_terminal_bypass_players"] > 0
        ),
        "cpu_guard_boundary_invariants_passed": (
            extrema["cpu_guard_active_admitted_normalized_cpu_max"] is not None
            and extrema["cpu_guard_active_admitted_normalized_cpu_max"] <= CPU_THRESHOLD
            and extrema["cpu_guard_rejected_normalized_cpu_min"] is not None
            and extrema["cpu_guard_rejected_normalized_cpu_min"] > CPU_THRESHOLD
        ),
        "capacity_overload_activation_and_v159_inactive_admission_exercised": (
            totals["capacity_overload_guard_active_windows"] > 0
            and totals["capacity_overload_guard_inactive_windows"] > 0
            and totals["capacity_overload_guard_inactive_heavy_terminal_admissions"] > 0
            and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"] is not None
            and extrema["cpu_guard_inactive_admitted_normalized_cpu_max"]
            > CPU_THRESHOLD
        ),
        "work_and_queue_threshold_invariants_passed": (
            extrema["admitted_short_work_remaining_work_max"] is not None
            and extrema["admitted_short_work_remaining_work_max"]
            <= SHORT_WORK_THRESHOLD
            and extrema["rejected_over_threshold_remaining_work_min"] is not None
            and extrema["rejected_over_threshold_remaining_work_min"]
            > SHORT_WORK_THRESHOLD
            and extrema["admitted_short_work_queue_density_max"] is not None
            and extrema["admitted_short_work_queue_density_max"] < QUEUE_THRESHOLD
            and extrema["rejected_short_work_queue_density_min"] is not None
            and extrema["rejected_short_work_queue_density_min"] >= QUEUE_THRESHOLD
        ),
        "both_routes_exercised": (
            totals["below_threshold_route_windows"] > 0
            and totals["at_or_above_threshold_route_windows"] > 0
        ),
        "pass": passed,
    }


def blind_audit_v169(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V169 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V169 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V169 execution receipt")
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
        raise RuntimeError("V169 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=3
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V169 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V169 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V169 has unexplained quarantined attempts")
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
        raise RuntimeError("V169 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V169 runtime identity changed")
    mechanism = _mechanism_falsification_gate(audits)
    if not mechanism["pass"]:
        raise RuntimeError("V169 mechanism falsification breadth is insufficient")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAPACITY_OVERLOAD_CPU_BOUNDED_TERMINAL_LOW_BLIND_AUDIT_V169_V1",
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
        **mechanism,
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
        raise RuntimeError("V169 candidate result product changed")
    return rows


def reveal_v169(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V169 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V169 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get(
            "cpu_guard_light_admission_heavy_rejection_and_parent_completed_bypass_exercised"
        )
        is True
        and blind.get("cpu_guard_boundary_invariants_passed") is True
        and blind.get(
            "capacity_overload_activation_and_v159_inactive_admission_exercised"
        )
        is True
        and blind.get("work_and_queue_threshold_invariants_passed") is True
        and blind.get("both_routes_exercised") is True
        and blind.get("pass") is True
    ):
        raise RuntimeError("V169 blind audit did not authorize reveal")
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
            "cpu_guard_admitted_incomplete_parent_terminal_players",
            "cpu_guard_rejected_heavy_incomplete_parent_terminal_players",
            "cpu_guard_parent_completed_heavy_terminal_bypass_players",
            "cpu_guard_admitted_normalized_cpu_max",
            "cpu_guard_active_admitted_normalized_cpu_max",
            "cpu_guard_inactive_admitted_normalized_cpu_max",
            "cpu_guard_rejected_normalized_cpu_min",
            "capacity_overload_heavy_incomplete_parent_terminal_players",
            "capacity_overload_guard_active_windows",
            "capacity_overload_guard_inactive_windows",
            "capacity_overload_guard_inactive_heavy_terminal_admissions",
            "admitted_slack_short_work_nonterminal_players",
            "rejected_short_work_at_or_above_queue_threshold",
            "admitted_short_work_remaining_work_max",
            "rejected_over_threshold_remaining_work_min",
            "admitted_short_work_queue_density_max",
            "rejected_short_work_queue_density_min",
        )
    }
    mechanism["pass"] = blind["pass"]
    passed = (
        evaluation["all_three_metric_gates_pass"]
        and mechanism["pass"]
        and diagnostic["throughput_three_seed_sum_pass"]
        and diagnostic["throughput_three_seed_paired_wins_pass"]
        and diagnostic["qpr_three_seed_sum_pass"]
        and diagnostic["qpr_three_seed_all_finite"]
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAPACITY_OVERLOAD_CPU_BOUNDED_TERMINAL_LOW_DIAGNOSTIC_RESULT_V169_V1",
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
            else "retain_all_three_valid_diagnostic_runs_and_retire_capacity_overload_cpu_bounded_terminal_candidate"
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
        document, key = prepare_v169(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v169(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v169(), "blind_audit_hash"
    else:
        document, key = reveal_v169(), "result_hash"
    print(json.dumps({key: document[key], "runs": 3}))


if __name__ == "__main__":
    main()
