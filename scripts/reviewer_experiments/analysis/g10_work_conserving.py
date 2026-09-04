"""Result-blind selection freeze and fail-closed G10 development analysis.

G10 is a development gate rather than paper evidence.  Its exact selection and
this analyzer are frozen before the online result directory exists.  Every
first QC-valid run is retained, including zero-completion runs whose QPR is
explicitly undefined.
"""

from __future__ import annotations

import argparse
import copy
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Mapping, Sequence

from ..protocol.g10_work_conserving import (
    G10_CANDIDATES,
    G10_CONTROL,
    G10_EFFECTIVE_METHODS,
    G10_MANIFEST_SCHEMA,
)
from ..protocol.m1_qualification import _canonical_summary_path
from ..protocol.schema import (
    FORMAL_E1_LOADS,
    G10_WORK_CONSERVING_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
)
from ..protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from .feedback_trace import validate_runtime_contract_config
from .formal_inputs import validate_canonical_run
from .observability import (
    RunArtifacts,
    load_run_artifacts,
    stage_wait_run_metrics,
)


SELECTION_SCHEMA = "NSE_G10_WORK_CONSERVING_ONLINE_SELECTION_V1"
REPORT_SCHEMA = "NSE_G10_WORK_CONSERVING_GATE_REPORT_V1"
EXPECTED_RUN_COUNT = 45
EXPECTED_SELECTOR = {
    "schema": None,
    "semantics": "single_ready_order_path",
    "orders": None,
    "eligibility": None,
    "ranking": None,
    "welfare_tolerance": None,
    "dispatch_feedback": False,
}
PRIMARY_METRICS = ("throughput_requests_per_ms", "qpr")
AGGREGATE_METRICS = (
    *PRIMARY_METRICS,
    "completion_ratio",
    "latency_mean_ms",
    "latency_p95_ms",
    "latency_p99_ms",
    "cost_per_completed_request",
    "queue_area_request_frames",
    "cpu_utilization_mean",
    "cpu_utilization_p95",
    "cpu_utilization_peak",
    "memory_utilization_mean",
    "memory_utilization_p95",
    "memory_utilization_peak",
    "placement_policy_wall_mean_ns",
    "schedule_wait_mean_ms",
    "schedule_wait_p95_ms",
    "cold_start_wait_mean_ms",
    "cold_start_wait_p95_ms",
    "data_wait_mean_ms",
    "data_wait_p95_ms",
    "execution_mean_ms",
    "execution_p95_ms",
    "stage_latency_mean_ms",
    "stage_latency_p95_ms",
)
WORK_CONSERVING_SCHEMA = (
    "all_ready_remaining_work_with_global_one_hop_frontier_bound_v1"
)


def _number(
    value: Any, *, positive: bool = False, nonnegative: bool = False
) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    if positive and result <= 0.0:
        return None
    if nonnegative and result < 0.0:
        return None
    return result


def _finite_int(value: Any) -> int | None:
    number = _number(value, nonnegative=True)
    if number is None or number != int(number):
        return None
    return int(number)


def _count(value: Any, label: str) -> int:
    number = _finite_int(value)
    if number is None:
        raise ProtocolValidationError(f"{label} is not a nonnegative integer")
    return number


def _verified_artifact(
    manifest_path: Path,
    raw_path: Any,
    expected_hash: Any,
    cache: dict[Path, str],
    label: str,
) -> Path:
    if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
        raise ProtocolValidationError(f"{label} is not path/hash-bound")
    path = Path(raw_path)
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if not path.is_file():
        raise ProtocolValidationError(f"{label} is missing: {path}")
    actual = cache.setdefault(path, file_hash(path))
    if actual != expected_hash:
        raise ProtocolValidationError(f"{label} hash differs from the manifest")
    return path


def _effective_method(run: Mapping[str, Any]) -> str:
    if run.get("method") != "sche_nash":
        raise ProtocolValidationError("G10 initial stage admits only sche_nash arms")
    metadata = run.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ProtocolValidationError("G10 run lacks candidate metadata")
    method = str(metadata.get("m1_operational_candidate", ""))
    if method not in G10_EFFECTIVE_METHODS:
        raise ProtocolValidationError(f"unsupported G10 effective method: {method}")
    return method


def _validate_ready_manifest(path: Path) -> dict[str, Any]:
    manifest = load_and_validate_manifest(path)
    marker = manifest.get("g10_work_conserving_development")
    if (
        not isinstance(marker, Mapping)
        or marker.get("schema_version") != G10_MANIFEST_SCHEMA
        or marker.get("control") != G10_CONTROL
        or tuple(marker.get("candidates", ())) != G10_CANDIDATES
        or tuple(marker.get("loads", ())) != tuple(FORMAL_E1_LOADS)
        or tuple(marker.get("development_seeds", ()))
        != tuple(G10_WORK_CONSERVING_SEEDS)
        or marker.get("strong_baselines_in_initial_stage") is not False
        or manifest.get("phase") != "development"
        or manifest.get("formal_results_eligible") is not False
        or manifest.get("all_tapes_bound") is not True
        or manifest.get("all_references_bound") is not True
        or manifest.get("all_faasrank_models_bound") is not False
        or len(manifest.get("runs", ())) != EXPECTED_RUN_COUNT
    ):
        raise ProtocolValidationError("G10 requires the complete bound 45-run manifest")

    expected = {
        (load, seed, method)
        for load in FORMAL_E1_LOADS
        for seed in G10_WORK_CONSERVING_SEEDS
        for method in G10_EFFECTIVE_METHODS
    }
    observed: set[tuple[str, str, str]] = set()
    run_ids: set[str] = set()
    spec_hashes: set[str] = set()
    tape_groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    tape_hashes: set[str] = set()
    reference_hashes: set[str] = set()
    artifact_cache: dict[Path, str] = {}
    runtime = marker.get("runtime_binary")
    if not isinstance(runtime, Mapping):
        raise ProtocolValidationError("G10 runtime receipt is missing")
    _verified_artifact(
        path,
        runtime.get("path"),
        runtime.get("sha256"),
        artifact_cache,
        "G10 runtime binary",
    )
    for run in manifest["runs"]:
        load = str(run.get("workload", {}).get("request_freq", ""))
        seed = str(run.get("seed", ""))
        method = _effective_method(run)
        identity = (load, seed, method)
        if identity in observed:
            raise ProtocolValidationError(f"duplicate G10 matrix identity: {identity}")
        observed.add(identity)
        run_id = str(run.get("run_id", ""))
        spec_hash = str(run.get("run_spec_hash", ""))
        if not run_id or run_id in run_ids or len(spec_hash) != 64:
            raise ProtocolValidationError("G10 run identity is missing or duplicated")
        if spec_hash in spec_hashes:
            raise ProtocolValidationError("G10 run_spec_hash is duplicated")
        run_ids.add(run_id)
        spec_hashes.add(spec_hash)
        tape = run.get("workload_tape")
        tape_hash = tape.get("sha256") if isinstance(tape, Mapping) else None
        if not isinstance(tape_hash, str) or len(tape_hash) != 64:
            raise ProtocolValidationError("G10 workload tape is not hash-bound")
        _verified_artifact(
            path, tape.get("path"), tape_hash, artifact_cache, "G10 workload tape"
        )
        tape_groups[(load, seed)].add(tape_hash)
        tape_hashes.add(tape_hash)
        dependency = run.get("reference_dependency")
        if (
            not isinstance(dependency, Mapping)
            or dependency.get("build_required") is not False
            or not isinstance(dependency.get("sha256"), str)
            or len(dependency["sha256"]) != 64
            or not isinstance(dependency.get("receipt_sha256"), str)
            or len(dependency["receipt_sha256"]) != 64
        ):
            raise ProtocolValidationError("G10 reference is not fully bound")
        _verified_artifact(
            path,
            dependency.get("path"),
            dependency.get("sha256"),
            artifact_cache,
            "G10 offline reference",
        )
        _verified_artifact(
            path,
            dependency.get("receipt_path"),
            dependency.get("receipt_sha256"),
            artifact_cache,
            "G10 reference receipt",
        )
        reference_hashes.add(str(dependency["sha256"]))
    if observed != expected:
        raise ProtocolValidationError("G10 manifest does not cover the exact product")
    if len(tape_groups) != 15 or any(len(group) != 1 for group in tape_groups.values()):
        raise ProtocolValidationError(
            "G10 methods are not paired on one tape per load/seed"
        )
    if len(tape_hashes) != 15 or len(reference_hashes) != 45:
        raise ProtocolValidationError("G10 tape/reference identities are not unique")
    return manifest


def _selection_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for ordinal, run in enumerate(manifest["runs"], start=1):
        dependency = run["reference_dependency"]
        rows.append(
            {
                "ordinal": ordinal,
                "execution_order": "development_manifest_order",
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "load": run["workload"]["request_freq"],
                "seed": run["seed"],
                "manifest_method": run["method"],
                "effective_method": _effective_method(run),
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": dependency["sha256"],
                "artifact_hashes": copy.deepcopy(run.get("artifact_hashes", {})),
            }
        )
    return rows


def build_online_selection(manifest_path: Path, canonical_root: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    if canonical_root.exists() or canonical_root.parent.exists():
        raise ProtocolValidationError(
            "G10 selection must be frozen before the online result workspace exists"
        )
    report: dict[str, Any] = {
        "schema_version": SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": "frozen_before_online_execution",
        "development_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "canonical_root": str(canonical_root),
        "canonical_parent_present_at_freeze": False,
        "online_results_present_at_freeze": False,
        "run_count": EXPECTED_RUN_COUNT,
        "execution_order": "development_manifest_order",
        "all_valid_runs_retained": True,
        "result_conditioned_seed_or_run_selection": False,
        "technical_retry_only": True,
        "scientific_outcome_retryable": False,
        "analysis_contract": {
            "path": str(Path(__file__).resolve()),
            "sha256": file_hash(Path(__file__).resolve()),
            "gate_condition_count_per_candidate": 9,
        },
        "runs": _selection_rows(manifest),
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_online_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite frozen G10 selection")
    report = build_online_selection(manifest_path, canonical_root)
    write_json_atomic(output_path, report)
    return report


def _validate_selection(
    selection_path: Path,
    manifest_path: Path,
    canonical_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    selection = read_json(selection_path)
    if not isinstance(selection, dict):
        raise ProtocolValidationError("G10 selection is not an object")
    stored = selection.get("document_sha256")
    payload = dict(selection)
    payload.pop("document_sha256", None)
    if not isinstance(stored, str) or object_hash(payload) != stored:
        raise ProtocolValidationError("G10 selection document hash mismatch")
    frozen_manifest = selection.get("development_manifest")
    contract = selection.get("analysis_contract")
    if (
        selection.get("schema_version") != SELECTION_SCHEMA
        or selection.get("status") != "frozen_before_online_execution"
        or selection.get("online_results_present_at_freeze") is not False
        or selection.get("canonical_parent_present_at_freeze") is not False
        or selection.get("result_conditioned_seed_or_run_selection") is not False
        or selection.get("all_valid_runs_retained") is not True
        or selection.get("execution_order") != "development_manifest_order"
        or selection.get("run_count") != EXPECTED_RUN_COUNT
        or not isinstance(contract, Mapping)
        or Path(str(contract.get("path", ""))).resolve() != Path(__file__).resolve()
        or contract.get("sha256") != file_hash(Path(__file__).resolve())
        or contract.get("gate_condition_count_per_candidate") != 9
        or not isinstance(frozen_manifest, Mapping)
        or Path(str(frozen_manifest.get("path", ""))).resolve()
        != manifest_path.resolve()
        or frozen_manifest.get("manifest_hash") != manifest.get("manifest_hash")
        or frozen_manifest.get("file_sha256") != file_hash(manifest_path)
        or Path(str(selection.get("canonical_root", ""))).resolve()
        != canonical_root.resolve()
        or selection.get("runs") != _selection_rows(manifest)
    ):
        raise ProtocolValidationError("G10 selection no longer matches frozen inputs")
    return selection


def _summary_number(
    value: Any, *, positive: bool = False, nonnegative: bool = False
) -> float | None:
    return _number(value, positive=positive, nonnegative=nonnegative)


def _metric_row(
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
    stage_wait: Mapping[str, Any],
) -> dict[str, Any]:
    fixed = summary.get("fixed_observation_window")
    drained = summary.get("drained_arrival_cohort")
    if not isinstance(fixed, Mapping) or not isinstance(drained, Mapping):
        raise ProtocolValidationError("G10 summary lacks explicit cohort metrics")
    completed = _count(fixed.get("completed"), "fixed completed count")
    arrivals = _count(fixed.get("arrivals"), "fixed arrival count")
    throughput_rps = _summary_number(
        fixed.get("throughput_requests_per_second"), nonnegative=True
    )
    latency_obj = drained.get("latency_ms")
    if not isinstance(latency_obj, Mapping):
        latency_obj = {}
    latency = _summary_number(latency_obj.get("mean"), positive=True)
    cost = _summary_number(
        summary.get("simulator_internal_cost_per_completed_request"), positive=True
    )
    placement = summary.get("placement_policy_wall_ns")
    placement_wall = (
        _summary_number(placement.get("mean"), nonnegative=True)
        if isinstance(placement, Mapping)
        else None
    )
    reasons = []
    if completed == 0:
        reasons.append("zero_completion")
    if throughput_rps is None or throughput_rps <= 0.0:
        reasons.append("nonpositive_or_invalid_throughput")
    if latency is None:
        reasons.append("nonpositive_or_invalid_latency")
    if cost is None:
        reasons.append("nonpositive_or_invalid_cost")
    throughput = None if throughput_rps is None else throughput_rps / 1000.0
    qpr = (
        throughput / (latency * cost)
        if throughput is not None
        and throughput > 0.0
        and latency is not None
        and cost is not None
        else None
    )
    completion_ratio = _summary_number(
        fixed.get("completion_ratio", summary.get("completion_ratio")),
        nonnegative=True,
    )
    if completion_ratio is None or completion_ratio > 1.0:
        raise ProtocolValidationError("G10 completion ratio is outside [0,1]")
    return {
        "run_id": str(run["run_id"]),
        "run_spec_hash": str(run["run_spec_hash"]),
        "load": str(run["workload"]["request_freq"]),
        "seed": str(run["seed"]),
        "manifest_method": str(run["method"]),
        "effective_method": _effective_method(run),
        "workload_tape_sha256": str(run["workload_tape"]["sha256"]),
        "qc_valid": True,
        "fixed_arrival_count": arrivals,
        "fixed_completion_count": completed,
        "completion_ratio": completion_ratio,
        "throughput_requests_per_ms": throughput,
        "latency_mean_ms": latency,
        "latency_p95_ms": _summary_number(latency_obj.get("p95"), positive=True),
        "latency_p99_ms": _summary_number(latency_obj.get("p99"), positive=True),
        "cost_per_completed_request": cost,
        "qpr": qpr,
        "qpr_applicable": qpr is not None,
        "qpr_nonapplicability_reasons": reasons,
        "queue_area_request_frames": _summary_number(
            summary.get("queue_area_request_frames"), nonnegative=True
        ),
        "cpu_utilization_mean": _summary_number(
            summary.get("node_cpu_utilization_mean"), nonnegative=True
        ),
        "cpu_utilization_p95": _summary_number(
            summary.get("node_cpu_utilization_p95"), nonnegative=True
        ),
        "cpu_utilization_peak": _summary_number(
            summary.get("node_cpu_utilization_peak"), nonnegative=True
        ),
        "memory_utilization_mean": _summary_number(
            summary.get("node_memory_utilization_mean"), nonnegative=True
        ),
        "memory_utilization_p95": _summary_number(
            summary.get("node_memory_utilization_p95"), nonnegative=True
        ),
        "memory_utilization_peak": _summary_number(
            summary.get("node_memory_utilization_peak"), nonnegative=True
        ),
        "placement_policy_wall_mean_ns": placement_wall,
        **{
            key: _summary_number(stage_wait.get(key), nonnegative=True)
            for key in (
                "schedule_wait_mean_ms",
                "schedule_wait_p95_ms",
                "cold_start_wait_mean_ms",
                "cold_start_wait_p95_ms",
                "data_wait_mean_ms",
                "data_wait_p95_ms",
                "execution_mean_ms",
                "execution_p95_ms",
                "stage_latency_mean_ms",
                "stage_latency_p95_ms",
            )
        },
        "completed_function_invocation_samples": _finite_int(
            stage_wait.get("completed_function_invocation_samples")
        ),
        "stage_wait_coverage_status": stage_wait.get("stage_wait_coverage_status"),
    }


def _audit_identity(
    audit: Mapping[str, Any], marker: Mapping[str, Any]
) -> dict[str, Any]:
    issues = []
    expected = marker.get("runtime_binary")
    adapter = audit.get("adapter_binary")
    software = audit.get("software_environment")
    git = software.get("git") if isinstance(software, Mapping) else None
    if not isinstance(expected, Mapping) or not isinstance(adapter, Mapping):
        return {
            "runtime_identity_pass": False,
            "runtime_identity_issues": ["runtime identity receipt is missing"],
            "runtime_binary_sha256": None,
            "runtime_git_commit": None,
        }
    expected_hash = expected.get("sha256")
    if (
        adapter.get("observed_hash_matches_file") is not True
        or adapter.get("verified_sha256") != expected_hash
        or adapter.get("observed_sha256") != expected_hash
    ):
        issues.append("runtime binary identity differs from frozen manifest")
    git_commit = git.get("commit") if isinstance(git, Mapping) else None
    if (
        not isinstance(git_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", git_commit) is None
    ):
        issues.append("execution-time orchestration Git identity is invalid")
    return {
        "runtime_identity_pass": not issues,
        "runtime_identity_issues": issues,
        "runtime_binary_sha256": adapter.get("verified_sha256"),
        "runtime_git_commit": git_commit,
    }


def _nash_runtime(
    run: Mapping[str, Any],
    artifacts: RunArtifacts,
    qc: Mapping[str, Any],
    audit: Mapping[str, Any],
    marker: Mapping[str, Any],
) -> dict[str, Any]:
    effective = _effective_method(run)
    identity = _audit_identity(audit, marker)
    issues = list(identity["runtime_identity_issues"])
    activation_issues: list[str] = []
    configs = [
        event for event in artifacts.nse_events if event.get("kind") == "run_config"
    ]
    if len(configs) != 1:
        issues.append("expected exactly one run_config event")
        config: Mapping[str, Any] = {}
    else:
        config = configs[0]
        try:
            expected_r0 = float(
                run["simulator_experiment"]["nash"]["price_feedback_rate"]
            )
            issues.extend(
                validate_runtime_contract_config(
                    config,
                    expected_candidate=effective,
                    expected_r0=expected_r0,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"runtime contract could not be checked: {exc}")
    reference = config.get("reference") if isinstance(config, Mapping) else None
    if (
        config.get("operational_equilibrium_selection") != EXPECTED_SELECTOR
        or config.get("decision_neutral_diagnostics", {}).get(
            "order_counterfactual_enabled"
        )
        is not False
        or not isinstance(reference, Mapping)
        or reference.get("mode") != "offline_required"
        or reference.get("offline_load_ok") is not True
        or (_finite_int(reference.get("offline_entries")) or 0) <= 0
    ):
        issues.append("single-path/offline-reference run contract is invalid")
    contract = qc.get("observations", {}).get("nash_runtime_contract")
    if (
        not isinstance(contract, Mapping)
        or contract.get("strict_eq15_ready") is not True
        or contract.get("stream_contract_ready") is not True
    ):
        issues.append("strict Eq. (15) or stream QC contract is not ready")

    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        issues.append("no Nash policy windows were recorded")
    active_windows = 0
    assigned_players = 0
    pne_windows = 0
    reference_hits = 0
    frontier_admitted_total = 0
    frontier_positive_windows = 0
    ready_candidates_total = 0
    ready_omissions_total = 0
    frontier_bound_violations = 0
    frontier_one_hop_violations = 0
    dispatch_class_violations = 0
    expected_remaining = effective != G10_CONTROL
    expected_frontier = effective == G10_CANDIDATES[1]
    for index, window in enumerate(windows):
        decision = window.get("decision")
        solver = window.get("solver")
        social = window.get("social")
        telemetry = window.get("work_conserving_remaining_work")
        if not isinstance(decision, Mapping) or not isinstance(solver, Mapping):
            issues.append(f"window {index} lacks decision/solver evidence")
            continue
        assigned = _finite_int(decision.get("assigned_players"))
        if assigned is None:
            issues.append(f"window {index} has invalid assigned-player count")
            continue
        if not isinstance(telemetry, Mapping):
            activation_issues.append(f"window {index} lacks G10 telemetry")
        else:
            counts = {
                key: _finite_int(telemetry.get(key))
                for key in (
                    "ready_candidates",
                    "ready_admitted",
                    "ready_omissions",
                    "ready_set_hash",
                    "frontier_candidates",
                    "outstanding_frontier",
                    "frontier_limit",
                    "frontier_budget",
                    "frontier_admitted",
                    "frontier_set_hash",
                    "frontier_bound_violations",
                    "frontier_one_hop_violations",
                    "dispatch_class_violations",
                    "dispatch_ready_players",
                    "dispatch_frontier_players",
                )
            }
            if (
                telemetry.get("schema") != WORK_CONSERVING_SCHEMA
                or telemetry.get("remaining_work_enabled") is not expected_remaining
                or telemetry.get("bounded_frontier_enabled") is not expected_frontier
                or any(value is None for value in counts.values())
            ):
                activation_issues.append(
                    f"window {index} has invalid mode/count telemetry"
                )
            else:
                ready_candidates = int(counts["ready_candidates"])
                ready_admitted = int(counts["ready_admitted"])
                omissions = int(counts["ready_omissions"])
                ready_candidates_total += ready_candidates
                ready_omissions_total += omissions
                frontier_admitted = int(counts["frontier_admitted"])
                frontier_admitted_total += frontier_admitted
                frontier_positive_windows += int(frontier_admitted > 0)
                frontier_bound_violations += int(counts["frontier_bound_violations"])
                frontier_one_hop_violations += int(
                    counts["frontier_one_hop_violations"]
                )
                dispatch_class_violations += int(counts["dispatch_class_violations"])
                if ready_admitted != ready_candidates or omissions != 0:
                    activation_issues.append(f"window {index} omitted a ready player")
                unfinished_min = telemetry.get("unfinished_functions_min")
                unfinished_max = telemetry.get("unfinished_functions_max")
                if ready_candidates > 0 and (
                    _finite_int(unfinished_min) is None
                    or _finite_int(unfinished_max) is None
                    or int(unfinished_min) > int(unfinished_max)
                ):
                    activation_issues.append(
                        f"window {index} has invalid unfinished-work range"
                    )
                if expected_frontier:
                    expected_budget = max(
                        0,
                        int(counts["frontier_limit"])
                        - int(counts["outstanding_frontier"]),
                    )
                    if (
                        int(counts["frontier_limit"]) != int(marker["node_count"])
                        or int(counts["frontier_budget"]) != expected_budget
                        or frontier_admitted
                        > min(int(counts["frontier_candidates"]), expected_budget)
                        or int(counts["outstanding_frontier"]) + frontier_admitted
                        > int(counts["frontier_limit"])
                        or int(counts["frontier_bound_violations"]) != 0
                        or int(counts["frontier_one_hop_violations"]) != 0
                        or int(counts["dispatch_class_violations"]) != 0
                        or int(counts["dispatch_ready_players"])
                        + int(counts["dispatch_frontier_players"])
                        != assigned
                    ):
                        activation_issues.append(
                            f"window {index} violates bounded-frontier accounting"
                        )
                elif (
                    int(counts["frontier_candidates"]) != 0
                    or int(counts["outstanding_frontier"]) != 0
                    or int(counts["frontier_admitted"]) != 0
                    or int(counts["frontier_bound_violations"]) != 0
                    or int(counts["frontier_one_hop_violations"]) != 0
                    or int(counts["dispatch_class_violations"]) != 0
                    or (
                        effective == G10_CANDIDATES[0]
                        and int(counts["dispatch_ready_players"]) != assigned
                    )
                    or int(counts["dispatch_frontier_players"]) != 0
                ):
                    activation_issues.append(
                        f"window {index} violates ready-only accounting"
                    )
        if assigned == 0:
            continue
        active_windows += 1
        assigned_players += assigned
        if (
            decision.get("complete_assignment") is not True
            or _finite_int(decision.get("commands_prepared")) != assigned
            or _finite_int(decision.get("commands_sent")) != assigned
            or _finite_int(decision.get("invalid_assignments")) != 0
            or decision.get("dispatch_channel_failed") is not False
        ):
            issues.append(f"active window {index} failed dispatch accounting")
        if (
            solver.get("inner_stable") is not True
            or solver.get("inner_limit_hit") is not False
            or _finite_int(solver.get("oscillations")) != 0
        ):
            issues.append(f"active window {index} lacks a strict PNE certificate")
        else:
            pne_windows += 1
        if (
            not isinstance(social, Mapping)
            or social.get("reference_source") != "offline_table"
            or _finite_int(social.get("reference_state_key")) is None
            or _number(social.get("reference")) is None
        ):
            issues.append(f"active window {index} lacks its offline reference")
        else:
            reference_hits += 1
    if active_windows == 0 or assigned_players == 0:
        issues.append("Nash arm performed no active scheduling work")
    activation_pass = not activation_issues
    return {
        **identity,
        "nash_runtime_pass": not issues and activation_pass,
        "nash_runtime_issues": [*issues, *activation_issues],
        "g10_activation_pass": activation_pass,
        "g10_activation_issues": activation_issues,
        "ready_set_contract_pass": activation_pass and not expected_frontier,
        "frontier_contract_pass": activation_pass if expected_frontier else None,
        "policy_window_count": len(windows),
        "active_window_count": active_windows,
        "assigned_players": assigned_players,
        "strict_pne_active_windows": pne_windows,
        "offline_reference_hit_windows": reference_hits,
        "ready_candidates_total": ready_candidates_total,
        "ready_omissions_total": ready_omissions_total,
        "frontier_admitted_total": frontier_admitted_total,
        "frontier_positive_window_count": frontier_positive_windows,
        "frontier_bound_violations": frontier_bound_violations,
        "frontier_one_hop_violations": frontier_one_hop_violations,
        "dispatch_class_violations": dispatch_class_violations,
    }


def _series_summary(
    rows: Sequence[Mapping[str, Any]], field: str, *, signed: bool = False
) -> dict[str, Any]:
    ordered = sorted(
        rows, key=lambda row: G10_WORK_CONSERVING_SEEDS.index(str(row["seed"]))
    )
    values = [_number(row.get(field), nonnegative=not signed) for row in ordered]
    complete = len(ordered) == 5 and all(value is not None for value in values)
    defined = [float(value) for value in values if value is not None]
    mean = fmean(defined) if complete else None
    sd = stdev(defined) if complete and len(defined) > 1 else None
    half_width = 2.7764451051977987 * sd / math.sqrt(5) if sd is not None else None
    loo = []
    for omitted, row in enumerate(ordered):
        retained = [value for index, value in enumerate(values) if index != omitted]
        loo.append(
            {
                "omitted_seed": row["seed"],
                "mean": (
                    fmean(float(value) for value in retained if value is not None)
                    if len(retained) == 4
                    and all(value is not None for value in retained)
                    else None
                ),
            }
        )
    return {
        "n": len(ordered),
        "n_defined": len(defined),
        "mean": mean,
        "sd": sd,
        "descriptive_paired_95pct_t_interval": (
            [mean - half_width, mean + half_width]
            if mean is not None and half_width is not None
            else None
        ),
        "values": [
            {"seed": row["seed"], "value": value} for row, value in zip(ordered, values)
        ],
        "leave_one_seed_out_means": loo,
    }


def _difference(left: Any, right: Any) -> float | None:
    lhs = _number(left, nonnegative=True)
    rhs = _number(right, nonnegative=True)
    return None if lhs is None or rhs is None else lhs - rhs


def _ratio(left: Any, right: Any) -> float | None:
    lhs = _number(left, nonnegative=True)
    rhs = _number(right, positive=True)
    return None if lhs is None or rhs is None else lhs / rhs


def evaluate_gate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {
        (load, seed, method)
        for load in FORMAL_E1_LOADS
        for seed in G10_WORK_CONSERVING_SEEDS
        for method in G10_EFFECTIVE_METHODS
    }
    index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    run_ids: set[str] = set()
    spec_hashes: set[str] = set()
    duplicates = []
    for row in rows:
        key = (
            str(row.get("load")),
            str(row.get("seed")),
            str(row.get("effective_method")),
        )
        if key in index:
            duplicates.append(key)
        index[key] = row
        run_ids.add(str(row.get("run_id", "")))
        spec_hashes.add(str(row.get("run_spec_hash", "")))
    exact_matrix = (
        len(rows) == EXPECTED_RUN_COUNT
        and len(index) == EXPECTED_RUN_COUNT
        and set(index) == expected
        and not duplicates
        and len(run_ids) == EXPECTED_RUN_COUNT
        and len(spec_hashes) == EXPECTED_RUN_COUNT
        and all(bool(row.get("qc_valid")) for row in rows)
    )
    paired_tapes = True
    for load in FORMAL_E1_LOADS:
        for seed in G10_WORK_CONSERVING_SEEDS:
            hashes = {
                index[(load, seed, method)].get("workload_tape_sha256")
                for method in G10_EFFECTIVE_METHODS
                if (load, seed, method) in index
            }
            paired_tapes &= len(hashes) == 1 and None not in hashes
    positive_rows = [
        {
            "run_id": row.get("run_id"),
            "load": row.get("load"),
            "seed": row.get("seed"),
            "effective_method": row.get("effective_method"),
            "fixed_completion_count": row.get("fixed_completion_count"),
            "qpr": row.get("qpr"),
            "reasons": row.get("qpr_nonapplicability_reasons", []),
            "passed": (_finite_int(row.get("fixed_completion_count")) or 0) > 0
            and _number(row.get("qpr"), positive=True) is not None,
        }
        for row in rows
    ]
    runtime_rows = [
        {
            "run_id": row.get("run_id"),
            "runtime_binary_sha256": row.get("runtime_binary_sha256"),
            "runtime_git_commit": row.get("runtime_git_commit"),
            "identity_pass": row.get("runtime_identity_pass") is True,
            "nash_runtime_pass": row.get("nash_runtime_pass") is True,
            "issues": [
                *row.get("runtime_identity_issues", []),
                *row.get("nash_runtime_issues", []),
            ],
        }
        for row in rows
    ]
    binary_hashes = {row["runtime_binary_sha256"] for row in runtime_rows}
    git_commits = {row["runtime_git_commit"] for row in runtime_rows}
    one_runtime = (
        len(runtime_rows) == EXPECTED_RUN_COUNT
        and all(row["identity_pass"] for row in runtime_rows)
        and len(binary_hashes) == 1
        and None not in binary_hashes
        and len(git_commits) == 1
        and None not in git_commits
    )
    integrity_pass = one_runtime and all(
        row["nash_runtime_pass"] for row in runtime_rows
    )
    population_pass = (
        exact_matrix
        and paired_tapes
        and len(positive_rows) == EXPECTED_RUN_COUNT
        and all(row["passed"] for row in positive_rows)
        and one_runtime
    )

    aggregates: list[dict[str, Any]] = []
    aggregate_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for load in FORMAL_E1_LOADS:
        for method in G10_EFFECTIVE_METHODS:
            group = [
                index[(load, seed, method)]
                for seed in G10_WORK_CONSERVING_SEEDS
                if (load, seed, method) in index
            ]
            for metric in AGGREGATE_METRICS:
                summary = _series_summary(group, metric)
                item = {
                    "load": load,
                    "effective_method": method,
                    "metric": metric,
                    **summary,
                }
                aggregates.append(item)
                aggregate_index[(load, method, metric)] = item

    paired_rows = []
    for candidate in G10_CANDIDATES:
        for load in FORMAL_E1_LOADS:
            for seed in G10_WORK_CONSERVING_SEEDS:
                candidate_row = index.get((load, seed, candidate), {})
                control_row = index.get((load, seed, G10_CONTROL), {})
                throughput_difference = _difference(
                    candidate_row.get("throughput_requests_per_ms"),
                    control_row.get("throughput_requests_per_ms"),
                )
                qpr_difference = _difference(
                    candidate_row.get("qpr"), control_row.get("qpr")
                )
                throughput_ratio = _ratio(
                    candidate_row.get("throughput_requests_per_ms"),
                    control_row.get("throughput_requests_per_ms"),
                )
                latency_ratio = _ratio(
                    candidate_row.get("latency_mean_ms"),
                    control_row.get("latency_mean_ms"),
                )
                cost_ratio = _ratio(
                    candidate_row.get("cost_per_completed_request"),
                    control_row.get("cost_per_completed_request"),
                )
                qpr_ratio = _ratio(candidate_row.get("qpr"), control_row.get("qpr"))
                factored = (
                    throughput_ratio / (latency_ratio * cost_ratio)
                    if throughput_ratio is not None
                    and latency_ratio is not None
                    and latency_ratio > 0.0
                    and cost_ratio is not None
                    and cost_ratio > 0.0
                    else None
                )
                throughput_win = (
                    throughput_difference is not None and throughput_difference > 0.0
                )
                qpr_win = qpr_difference is not None and qpr_difference > 0.0
                paired_rows.append(
                    {
                        "candidate": candidate,
                        "load": load,
                        "seed": seed,
                        "candidate_run_id": candidate_row.get("run_id"),
                        "control_run_id": control_row.get("run_id"),
                        "throughput_difference": throughput_difference,
                        "qpr_difference": qpr_difference,
                        "completion_ratio_difference": _difference(
                            candidate_row.get("completion_ratio"),
                            control_row.get("completion_ratio"),
                        ),
                        "latency_mean_difference_ms": _difference(
                            candidate_row.get("latency_mean_ms"),
                            control_row.get("latency_mean_ms"),
                        ),
                        "throughput_ratio": throughput_ratio,
                        "qpr_ratio": qpr_ratio,
                        "latency_ratio": latency_ratio,
                        "cost_ratio": cost_ratio,
                        "qpr_ratio_from_factors": factored,
                        "qpr_factor_identity_absolute_error": (
                            abs(qpr_ratio - factored)
                            if qpr_ratio is not None and factored is not None
                            else None
                        ),
                        "throughput_win": throughput_win,
                        "qpr_win": qpr_win,
                        "joint_win": throughput_win and qpr_win,
                    }
                )

    paired_summaries = []
    for candidate in G10_CANDIDATES:
        for load in FORMAL_E1_LOADS:
            group = [
                row
                for row in paired_rows
                if row["candidate"] == candidate and row["load"] == load
            ]
            for metric, field in (
                ("throughput_requests_per_ms", "throughput_difference"),
                ("qpr", "qpr_difference"),
                ("completion_ratio", "completion_ratio_difference"),
                ("latency_mean_ms", "latency_mean_difference_ms"),
            ):
                paired_summaries.append(
                    {
                        "candidate": candidate,
                        "load": load,
                        "metric": metric,
                        **_series_summary(group, field, signed=True),
                    }
                )

    candidate_reports = []
    for candidate in G10_CANDIDATES:
        mean_ratio_rows = []
        win_rows = []
        floor_rows = []
        loo_rows = []
        completion_latency_rows = []
        overhead_rows = []
        activation_rows = []
        for load in FORMAL_E1_LOADS:
            ratios: dict[str, float | None] = {}
            for metric in PRIMARY_METRICS:
                candidate_mean = aggregate_index[(load, candidate, metric)]["mean"]
                control_mean = aggregate_index[(load, G10_CONTROL, metric)]["mean"]
                ratios[metric] = _ratio(candidate_mean, control_mean)
            mean_ratio_rows.append(
                {
                    "load": load,
                    "throughput_ratio": ratios["throughput_requests_per_ms"],
                    "qpr_ratio": ratios["qpr"],
                    "passed": all(
                        value is not None and value > 1.0 for value in ratios.values()
                    ),
                }
            )
            group = [
                row
                for row in paired_rows
                if row["candidate"] == candidate and row["load"] == load
            ]
            throughput_wins = sum(bool(row["throughput_win"]) for row in group)
            qpr_wins = sum(bool(row["qpr_win"]) for row in group)
            joint_wins = sum(bool(row["joint_win"]) for row in group)
            win_rows.append(
                {
                    "load": load,
                    "throughput_wins": throughput_wins,
                    "qpr_wins": qpr_wins,
                    "joint_wins": joint_wins,
                    "passed": len(group) == 5
                    and min(throughput_wins, qpr_wins, joint_wins) >= 3,
                }
            )
            floor_rows.extend(
                {
                    "load": load,
                    "seed": row["seed"],
                    "throughput_ratio": row["throughput_ratio"],
                    "qpr_ratio": row["qpr_ratio"],
                    "passed": row["throughput_ratio"] is not None
                    and row["qpr_ratio"] is not None
                    and row["throughput_ratio"] >= 0.80
                    and row["qpr_ratio"] >= 0.80,
                }
                for row in group
            )
            for metric in PRIMARY_METRICS:
                summary = next(
                    row
                    for row in paired_summaries
                    if row["candidate"] == candidate
                    and row["load"] == load
                    and row["metric"] == metric
                )
                loo_rows.append(
                    {
                        "load": load,
                        "metric": metric,
                        "values": copy.deepcopy(summary["leave_one_seed_out_means"]),
                        "passed": all(
                            item["mean"] is not None and item["mean"] > 0.0
                            for item in summary["leave_one_seed_out_means"]
                        ),
                    }
                )
            candidate_completion = aggregate_index[
                (load, candidate, "completion_ratio")
            ]["mean"]
            control_completion = aggregate_index[
                (load, G10_CONTROL, "completion_ratio")
            ]["mean"]
            candidate_latency = aggregate_index[(load, candidate, "latency_mean_ms")][
                "mean"
            ]
            control_latency = aggregate_index[(load, G10_CONTROL, "latency_mean_ms")][
                "mean"
            ]
            completion_latency_rows.append(
                {
                    "load": load,
                    "candidate_completion_ratio_mean": candidate_completion,
                    "control_completion_ratio_mean": control_completion,
                    "candidate_latency_mean_ms": candidate_latency,
                    "control_latency_mean_ms": control_latency,
                    "passed": candidate_completion is not None
                    and control_completion is not None
                    and candidate_completion >= control_completion
                    and candidate_latency is not None
                    and control_latency is not None
                    and candidate_latency < control_latency,
                }
            )
            candidate_wall = aggregate_index[
                (load, candidate, "placement_policy_wall_mean_ns")
            ]["mean"]
            control_wall = aggregate_index[
                (load, G10_CONTROL, "placement_policy_wall_mean_ns")
            ]["mean"]
            wall_ratio = _ratio(candidate_wall, control_wall)
            overhead_rows.append(
                {
                    "load": load,
                    "candidate_mean_ns": candidate_wall,
                    "control_mean_ns": control_wall,
                    "ratio": wall_ratio,
                    "passed": wall_ratio is not None and wall_ratio <= 1.50,
                }
            )
            candidate_activation = [
                index.get((load, seed, candidate), {})
                for seed in G10_WORK_CONSERVING_SEEDS
            ]
            if candidate == G10_CANDIDATES[0]:
                passed_activation = len(candidate_activation) == 5 and all(
                    row.get("ready_set_contract_pass") is True
                    for row in candidate_activation
                )
                positive_seeds = None
            else:
                positive_seeds = sum(
                    (_finite_int(row.get("frontier_admitted_total")) or 0) > 0
                    for row in candidate_activation
                )
                passed_activation = (
                    len(candidate_activation) == 5
                    and all(
                        row.get("frontier_contract_pass") is True
                        and (_finite_int(row.get("ready_omissions_total")) or 0) == 0
                        and (_finite_int(row.get("frontier_bound_violations")) or 0)
                        == 0
                        and (_finite_int(row.get("frontier_one_hop_violations")) or 0)
                        == 0
                        and (_finite_int(row.get("dispatch_class_violations")) or 0)
                        == 0
                        for row in candidate_activation
                    )
                    and positive_seeds >= 3
                )
            activation_rows.append(
                {
                    "load": load,
                    "candidate": candidate,
                    "positive_frontier_admission_seeds": positive_seeds,
                    "run_evidence": [
                        {
                            "seed": row.get("seed"),
                            "run_id": row.get("run_id"),
                            "ready_set_contract_pass": row.get(
                                "ready_set_contract_pass"
                            ),
                            "frontier_contract_pass": row.get("frontier_contract_pass"),
                            "frontier_admitted_total": row.get(
                                "frontier_admitted_total"
                            ),
                            "issues": row.get("g10_activation_issues", []),
                        }
                        for row in candidate_activation
                    ],
                    "passed": passed_activation,
                }
            )
        conditions = {
            "01_all_45_unique_paired_qc_positive_defined_qpr_one_runtime": population_pass,
            "02_mean_throughput_and_qpr_above_control_each_load": all(
                row["passed"] for row in mean_ratio_rows
            ),
            "03_at_least_3_of_5_paired_throughput_qpr_joint_wins_each_load": all(
                row["passed"] for row in win_rows
            ),
            "04_every_seed_throughput_and_qpr_ratio_at_least_0_80": all(
                row["passed"] for row in floor_rows
            ),
            "05_every_leave_one_seed_out_mean_difference_positive": all(
                row["passed"] for row in loo_rows
            ),
            "06_completion_not_below_and_latency_below_control_each_load": all(
                row["passed"] for row in completion_latency_rows
            ),
            "07_work_conserving_activation_and_integrity": all(
                row["passed"] for row in activation_rows
            ),
            "08_strict_eq15_pne_reference_dispatch_runtime_identity": integrity_pass,
            "09_mean_policy_wall_ratio_at_most_1_50_each_load": all(
                row["passed"] for row in overhead_rows
            ),
        }
        primary_ratios = [
            value
            for row in mean_ratio_rows
            for value in (row["throughput_ratio"], row["qpr_ratio"])
        ]
        score = {
            "minimum_of_six_primary_ratios": (
                min(primary_ratios)
                if all(v is not None for v in primary_ratios)
                else None
            ),
            "mean_of_six_primary_ratios": (
                fmean(float(v) for v in primary_ratios if v is not None)
                if all(v is not None for v in primary_ratios)
                else None
            ),
            "joint_paired_wins": sum(row["joint_wins"] for row in win_rows),
        }
        candidate_reports.append(
            {
                "candidate": candidate,
                "qualified": all(conditions.values()),
                "conditions": conditions,
                "failure_reasons": [
                    name for name, value in conditions.items() if not value
                ],
                "mean_ratio_rows": mean_ratio_rows,
                "paired_win_rows": win_rows,
                "per_seed_floor_rows": floor_rows,
                "leave_one_seed_out_rows": loo_rows,
                "completion_latency_rows": completion_latency_rows,
                "activation_rows": activation_rows,
                "policy_wall_overhead_rows": overhead_rows,
                "selection_score": score,
            }
        )

    qualified = [row for row in candidate_reports if row["qualified"]]
    selected = None
    if qualified:
        selected = max(
            qualified,
            key=lambda row: (
                row["selection_score"]["minimum_of_six_primary_ratios"],
                row["selection_score"]["mean_of_six_primary_ratios"],
                row["selection_score"]["joint_paired_wins"],
                row["candidate"] == G10_CANDIDATES[0],
            ),
        )["candidate"]
    return {
        "status": (
            "complete_g10_development_strong_baseline_preregistration_authorized"
            if selected is not None
            else "complete_g10_development_gate_failed"
        ),
        "selected_candidate": selected,
        "candidate_development_qualified": selected is not None,
        "strong_baseline_addendum_preregistration_authorized": selected is not None,
        "strong_baseline_sampling_authorized": False,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
        "all_valid_runs_retained": True,
        "population_integrity": {
            "exact_matrix": exact_matrix,
            "paired_tapes": paired_tapes,
            "positive_completion_defined_qpr": all(
                row["passed"] for row in positive_rows
            ),
            "one_runtime": one_runtime,
            "strict_pne_reference_dispatch_runtime_integrity": integrity_pass,
        },
        "positive_completion_and_qpr_rows": positive_rows,
        "runtime_integrity_rows": runtime_rows,
        "candidate_reports": candidate_reports,
        "aggregate_summaries": aggregates,
        "paired_rows": paired_rows,
        "paired_summaries": paired_summaries,
    }


def analyze(
    manifest_path: Path, selection_path: Path, canonical_root: Path
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    selection_path = selection_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    selection = _validate_selection(
        selection_path, manifest_path, canonical_root, manifest
    )
    marker = manifest["g10_work_conserving_development"]
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    rows = []
    receipts = []
    for run in manifest["runs"]:
        run_dir = canonical_root / str(run["run_id"])
        qc = validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=result_relative_path,
        )
        summary_path = _canonical_summary_path(canonical_root, str(run["run_id"]))
        summary = read_json(summary_path)
        if not isinstance(summary, Mapping):
            raise ProtocolValidationError("G10 canonical summary is not an object")
        artifacts = load_run_artifacts(
            run,
            canonical_root,
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=result_relative_path,
        )
        stage_wait = stage_wait_run_metrics(artifacts)
        row = _metric_row(run, summary, stage_wait)
        audit_path = run_dir / "manifest.json"
        audit = read_json(audit_path)
        if not isinstance(audit, Mapping):
            raise ProtocolValidationError("G10 canonical audit is not an object")
        row.update(_nash_runtime(run, artifacts, qc, audit, marker))
        rows.append(row)
        receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": run["reference_dependency"]["sha256"],
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "summary_sha256": file_hash(summary_path),
                "audit_manifest_sha256": file_hash(audit_path),
            }
        )
    gate = evaluate_gate(rows)
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": gate["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "development_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "frozen_online_selection": {
            "path": str(selection_path),
            "document_sha256": selection["document_sha256"],
            "file_sha256": file_hash(selection_path),
        },
        "canonical_root": str(canonical_root),
        "definitions": {
            "independent_unit": "run/seed",
            "qpr": "throughput_requests_per_ms/(drained_latency_mean_ms*simulator_internal_cost_per_completed_request)",
            "zero_completion": "retained_with_qpr_null_and_gate_failure",
            "mean_ratio": "candidate_five_seed_arithmetic_mean/control_five_seed_arithmetic_mean",
            "paired_difference": "candidate_minus_control_on_identical_load_seed_tape",
            "descriptive_interval": "two_sided_t_interval_df4_not_used_for_gate",
            "ready_set_identity": "state_local_dependency_ready_eligibility_with_all_ready_admitted; dynamic trajectories are not required to have equal per-frame hashes",
            "qpr_factorization": "throughput_ratio/(latency_ratio*cost_ratio)",
            "leave_one_seed_out": "frozen_robustness_gate_and_reported_for_every_primary_metric",
            "all_valid_runs_retained": True,
            "result_conditioned_seed_or_run_selection": False,
        },
        "activation_gate": copy.deepcopy(marker["activation_gate"]),
        "performance_gate": copy.deepcopy(marker["performance_gate"]),
        "selection_rule": copy.deepcopy(marker["selection_rule"]),
        "run_metrics": rows,
        "gate_result": gate,
        "artifact_receipts": receipts,
        "run_count": len(rows),
        "selected_candidate": gate["selected_candidate"],
        "strong_baseline_addendum_preregistration_authorized": gate[
            "strong_baseline_addendum_preregistration_authorized"
        ],
        "strong_baseline_sampling_authorized": False,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_analysis(
    manifest_path: Path,
    selection_path: Path,
    canonical_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G10 gate report")
    report = analyze(manifest_path, selection_path, canonical_root)
    write_json_atomic(output_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-selection")
    freeze.add_argument("manifest", type=Path)
    freeze.add_argument("canonical_root", type=Path)
    freeze.add_argument("output", type=Path)
    analyze_parser = commands.add_parser("analyze")
    analyze_parser.add_argument("manifest", type=Path)
    analyze_parser.add_argument("selection", type=Path)
    analyze_parser.add_argument("canonical_root", type=Path)
    analyze_parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "freeze-selection":
        write_online_selection(args.manifest, args.canonical_root, args.output)
    else:
        write_analysis(args.manifest, args.selection, args.canonical_root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
