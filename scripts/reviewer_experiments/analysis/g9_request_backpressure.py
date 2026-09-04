"""Result-free selection freeze and fail-closed G9 development analysis.

The G9 experiment is deliberately a development gate, not paper evidence.  The
selection command must run before the online result root exists.  The analysis
then retains every QC-valid run, including scientifically adverse zero-completion
runs for which QPR is explicitly non-applicable.
"""

from __future__ import annotations

import argparse
import copy
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping, Sequence

from ..protocol.g9_request_backpressure import (
    G9_BASELINES,
    G9_CANDIDATE,
    G9_CONTROL,
    G9_EFFECTIVE_METHODS,
    G9_MANIFEST_SCHEMA,
)
from ..protocol.m1_qualification import _canonical_summary_path
from ..protocol.schema import (
    FORMAL_E1_LOADS,
    G9_REQUEST_BACKPRESSURE_SEEDS,
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
from .observability import RunArtifacts, load_run_artifacts


SELECTION_SCHEMA = "NSE_G9_REQUEST_BACKPRESSURE_ONLINE_SELECTION_V1"
REPORT_SCHEMA = "NSE_G9_REQUEST_BACKPRESSURE_GATE_REPORT_V1"
EXPECTED_RUN_COUNT = 75
EXPECTED_SELECTOR = {
    "schema": None,
    "semantics": "single_ready_order_path",
    "orders": None,
    "eligibility": None,
    "ranking": None,
    "welfare_tolerance": None,
    "dispatch_feedback": False,
}
METRICS = ("throughput_requests_per_ms", "qpr")


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
    method = str(run.get("method", ""))
    if method == "sche_nash":
        metadata = run.get("metadata")
        if not isinstance(metadata, Mapping):
            raise ProtocolValidationError("G9 sche_nash run lacks metadata")
        method = str(metadata.get("m1_operational_candidate", ""))
    if method not in G9_EFFECTIVE_METHODS:
        raise ProtocolValidationError(f"unsupported G9 effective method: {method}")
    return method


def _validate_ready_manifest(path: Path) -> dict[str, Any]:
    manifest = load_and_validate_manifest(path)
    marker = manifest.get("g9_request_backpressure_development")
    if (
        not isinstance(marker, Mapping)
        or marker.get("schema_version") != G9_MANIFEST_SCHEMA
        or marker.get("candidate") != G9_CANDIDATE
        or marker.get("control") != G9_CONTROL
        or tuple(marker.get("baseline_methods", ())) != G9_BASELINES
        or tuple(marker.get("loads", ())) != tuple(FORMAL_E1_LOADS)
        or tuple(marker.get("development_seeds", ()))
        != tuple(G9_REQUEST_BACKPRESSURE_SEEDS)
        or manifest.get("phase") != "development"
        or manifest.get("formal_results_eligible") is not False
        or manifest.get("all_tapes_bound") is not True
        or manifest.get("all_references_bound") is not True
        or manifest.get("all_faasrank_models_bound") is not True
        or len(manifest.get("runs", ())) != EXPECTED_RUN_COUNT
    ):
        raise ProtocolValidationError("G9 requires the complete bound 75-run manifest")

    expected = {
        (load, seed, method)
        for load in FORMAL_E1_LOADS
        for seed in G9_REQUEST_BACKPRESSURE_SEEDS
        for method in G9_EFFECTIVE_METHODS
    }
    observed: set[tuple[str, str, str]] = set()
    run_ids: set[str] = set()
    spec_hashes: set[str] = set()
    tape_groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    artifact_cache: dict[Path, str] = {}
    runtime = marker.get("runtime_binary")
    if not isinstance(runtime, Mapping):
        raise ProtocolValidationError("G9 runtime receipt is missing")
    _verified_artifact(
        path,
        runtime.get("path"),
        runtime.get("sha256"),
        artifact_cache,
        "G9 runtime binary",
    )
    for run in manifest["runs"]:
        load = str(run.get("workload", {}).get("request_freq", ""))
        seed = str(run.get("seed", ""))
        method = _effective_method(run)
        identity = (load, seed, method)
        if identity in observed:
            raise ProtocolValidationError(f"duplicate G9 matrix identity: {identity}")
        observed.add(identity)
        run_id = str(run.get("run_id", ""))
        spec_hash = str(run.get("run_spec_hash", ""))
        if not run_id or run_id in run_ids or len(spec_hash) != 64:
            raise ProtocolValidationError("G9 run identity is missing or duplicated")
        if spec_hash in spec_hashes:
            raise ProtocolValidationError("G9 run_spec_hash is duplicated")
        run_ids.add(run_id)
        spec_hashes.add(spec_hash)
        tape = run.get("workload_tape")
        tape_hash = tape.get("sha256") if isinstance(tape, Mapping) else None
        if not isinstance(tape_hash, str) or len(tape_hash) != 64:
            raise ProtocolValidationError("G9 workload tape is not hash-bound")
        _verified_artifact(
            path,
            tape.get("path"),
            tape_hash,
            artifact_cache,
            "G9 workload tape",
        )
        tape_groups[(load, seed)].add(tape_hash)
        if run.get("method") == "sche_nash":
            dependency = run.get("reference_dependency")
            if (
                not isinstance(dependency, Mapping)
                or dependency.get("build_required") is not False
                or not isinstance(dependency.get("sha256"), str)
                or len(dependency["sha256"]) != 64
            ):
                raise ProtocolValidationError("G9 Nash reference is not fully bound")
            _verified_artifact(
                path,
                dependency.get("path"),
                dependency.get("sha256"),
                artifact_cache,
                "G9 offline reference",
            )
    if observed != expected:
        raise ProtocolValidationError("G9 manifest does not cover the exact product")
    if (
        any(len(hashes) != 1 for hashes in tape_groups.values())
        or len(tape_groups) != 15
    ):
        raise ProtocolValidationError(
            "G9 methods are not paired on one tape per load/seed"
        )
    return manifest


def _selection_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    order = {
        (load, seed, method): ordinal
        for ordinal, (load, seed, method) in enumerate(
            (
                (load, seed, method)
                for load in FORMAL_E1_LOADS
                for seed in G9_REQUEST_BACKPRESSURE_SEEDS
                for method in G9_EFFECTIVE_METHODS
            ),
            start=1,
        )
    }
    rows = []
    for run in manifest["runs"]:
        load = str(run["workload"]["request_freq"])
        seed = str(run["seed"])
        method = _effective_method(run)
        dependency = run.get("reference_dependency")
        rows.append(
            {
                "ordinal": order[(load, seed, method)],
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "load": load,
                "seed": seed,
                "manifest_method": run["method"],
                "effective_method": method,
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": (
                    dependency.get("sha256")
                    if isinstance(dependency, Mapping)
                    else None
                ),
                "artifact_hashes": copy.deepcopy(run.get("artifact_hashes", {})),
            }
        )
    return sorted(rows, key=lambda row: int(row["ordinal"]))


def build_online_selection(manifest_path: Path, canonical_root: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    if canonical_root.exists() or canonical_root.parent.exists():
        raise ProtocolValidationError(
            "G9 selection must be frozen before the online result workspace exists"
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
        "all_valid_runs_retained": True,
        "result_conditioned_seed_or_run_selection": False,
        "technical_retry_only": True,
        "scientific_outcome_retryable": False,
        "analysis_contract": {
            "path": str(Path(__file__).resolve()),
            "sha256": file_hash(Path(__file__).resolve()),
            "gate_condition_count": 10,
        },
        "runs": _selection_rows(manifest),
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_online_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite frozen G9 selection")
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
        raise ProtocolValidationError("G9 selection is not an object")
    stored = selection.get("document_sha256")
    payload = dict(selection)
    payload.pop("document_sha256", None)
    if not isinstance(stored, str) or object_hash(payload) != stored:
        raise ProtocolValidationError("G9 selection document hash mismatch")
    frozen_manifest = selection.get("development_manifest")
    analysis_contract = selection.get("analysis_contract")
    if (
        selection.get("schema_version") != SELECTION_SCHEMA
        or selection.get("status") != "frozen_before_online_execution"
        or selection.get("online_results_present_at_freeze") is not False
        or selection.get("canonical_parent_present_at_freeze") is not False
        or selection.get("result_conditioned_seed_or_run_selection") is not False
        or selection.get("all_valid_runs_retained") is not True
        or selection.get("run_count") != EXPECTED_RUN_COUNT
        or not isinstance(analysis_contract, Mapping)
        or Path(str(analysis_contract.get("path", ""))).resolve()
        != Path(__file__).resolve()
        or analysis_contract.get("sha256") != file_hash(Path(__file__).resolve())
        or analysis_contract.get("gate_condition_count") != 10
        or not isinstance(frozen_manifest, Mapping)
        or Path(str(frozen_manifest.get("path", ""))).resolve()
        != manifest_path.resolve()
        or frozen_manifest.get("manifest_hash") != manifest.get("manifest_hash")
        or frozen_manifest.get("file_sha256") != file_hash(manifest_path)
        or Path(str(selection.get("canonical_root", ""))).resolve()
        != canonical_root.resolve()
        or selection.get("runs") != _selection_rows(manifest)
    ):
        raise ProtocolValidationError("G9 selection no longer matches frozen inputs")
    return selection


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


def _count(value: Any, label: str) -> int:
    number = _number(value, nonnegative=True)
    if number is None or number != int(number):
        raise ProtocolValidationError(f"{label} is not a nonnegative integer")
    return int(number)


def _metric_row(run: Mapping[str, Any], summary: Mapping[str, Any]) -> dict[str, Any]:
    fixed = summary.get("fixed_observation_window")
    drained = summary.get("drained_arrival_cohort")
    if not isinstance(fixed, Mapping) or not isinstance(drained, Mapping):
        raise ProtocolValidationError("G9 summary lacks explicit cohort metrics")
    completed = _count(fixed.get("completed"), "fixed completed count")
    arrivals = _count(fixed.get("arrivals"), "fixed arrival count")
    throughput_rps = _number(
        fixed.get("throughput_requests_per_second"), nonnegative=True
    )
    latency_obj = drained.get("latency_ms")
    latency = (
        _number(latency_obj.get("mean"), positive=True)
        if isinstance(latency_obj, Mapping)
        else None
    )
    cost = _number(
        summary.get("simulator_internal_cost_per_completed_request"), positive=True
    )
    placement = summary.get("placement_policy_wall_ns")
    placement_wall = (
        _number(placement.get("mean"), nonnegative=True)
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
    completion_ratio = _number(
        fixed.get("completion_ratio", summary.get("completion_ratio")),
        nonnegative=True,
    )
    if completion_ratio is None or completion_ratio > 1.0:
        raise ProtocolValidationError("G9 completion ratio is outside [0,1]")
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
        "cost_per_completed_request": cost,
        "qpr": qpr,
        "qpr_applicable": qpr is not None,
        "qpr_nonapplicability_reasons": reasons,
        "placement_policy_wall_mean_ns": placement_wall,
    }


def _finite_int(value: Any) -> int | None:
    number = _number(value, nonnegative=True)
    if number is None or number != int(number):
        return None
    return int(number)


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
    reference_hits = 0
    pne_windows = 0
    backpressure_issues: list[str] = []
    over_limit_windows = 0
    deferred_positive_windows = 0
    previous_admissions = -1
    previous_completions = -1
    for index, window in enumerate(windows):
        decision = window.get("decision")
        solver = window.get("solver")
        social = window.get("social")
        if not isinstance(decision, Mapping) or not isinstance(solver, Mapping):
            issues.append(f"window {index} lacks decision/solver evidence")
            continue
        assigned = _finite_int(decision.get("assigned_players"))
        if assigned is None:
            issues.append(f"window {index} has invalid assigned-player count")
            continue
        if effective == G9_CANDIDATE:
            bp = window.get("request_backpressure")
            if not isinstance(bp, Mapping):
                backpressure_issues.append(f"window {index} lacks cohort telemetry")
            else:
                live = _finite_int(bp.get("live_requests"))
                limit = _finite_int(bp.get("cohort_limit"))
                admitted = _finite_int(bp.get("admitted_requests"))
                deferred = _finite_int(bp.get("deferred_requests"))
                ready = _finite_int(bp.get("ready_players_before_filter"))
                admitted_ready = _finite_int(bp.get("admitted_ready_players"))
                admissions = _finite_int(bp.get("cumulative_request_admissions"))
                completions = _finite_int(bp.get("cumulative_cohort_completions"))
                counts = (live, limit, admitted, deferred, ready, admitted_ready)
                if (
                    bp.get("schema") != "oldest_live_request_cohort_node_count_v1"
                    or any(value is None for value in counts)
                    or limit != 20
                    or admitted is None
                    or live is None
                    or admitted > min(live, limit)
                    or deferred != live - admitted
                    or ready is None
                    or admitted_ready is None
                    or admitted_ready > ready
                    or _finite_int(bp.get("retention_violations")) != 0
                    or _finite_int(bp.get("dispatch_player_violations")) != 0
                ):
                    backpressure_issues.append(
                        f"window {index} violates cohort accounting"
                    )
                if live is not None and limit is not None and live > limit:
                    over_limit_windows += 1
                    if deferred is not None and deferred > 0:
                        deferred_positive_windows += 1
                    else:
                        backpressure_issues.append(
                            f"window {index} did not defer an over-limit cohort"
                        )
                low = bp.get("cohort_min_arrival_frame")
                high = bp.get("cohort_max_arrival_frame")
                if admitted == 0:
                    if low is not None or high is not None:
                        backpressure_issues.append(
                            f"window {index} has bounds for an empty cohort"
                        )
                elif (
                    _finite_int(low) is None
                    or _finite_int(high) is None
                    or int(low) > int(high)
                ):
                    backpressure_issues.append(
                        f"window {index} has invalid cohort arrival bounds"
                    )
                if (
                    admissions is None
                    or completions is None
                    or admissions < previous_admissions
                    or completions < previous_completions
                    or completions > admissions
                ):
                    backpressure_issues.append(
                        f"window {index} has invalid cumulative cohort counters"
                    )
                if admissions is not None:
                    previous_admissions = admissions
                if completions is not None:
                    previous_completions = completions
        elif window.get("request_backpressure") is not None:
            issues.append(f"control window {index} unexpectedly enabled backpressure")

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
    backpressure_pass: bool | None = None
    if effective == G9_CANDIDATE:
        if over_limit_windows == 0:
            backpressure_issues.append(
                "backpressure never encountered live_requests > 20"
            )
        backpressure_pass = not backpressure_issues
    return {
        **identity,
        "nash_runtime_pass": not issues,
        "nash_runtime_issues": issues,
        "backpressure_activation_pass": backpressure_pass,
        "backpressure_activation_issues": backpressure_issues,
        "policy_window_count": len(windows),
        "active_window_count": active_windows,
        "assigned_players": assigned_players,
        "strict_pne_active_windows": pne_windows,
        "offline_reference_hit_windows": reference_hits,
        "over_limit_window_count": over_limit_windows,
        "deferred_positive_window_count": deferred_positive_windows,
    }


def _series_summary(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, Any]:
    ordered = sorted(
        rows, key=lambda row: G9_REQUEST_BACKPRESSURE_SEEDS.index(str(row["seed"]))
    )
    signed = field.endswith("_difference")
    values = [_number(row.get(field), nonnegative=not signed) for row in ordered]
    complete = len(ordered) == 5 and all(value is not None for value in values)
    mean = fmean(value for value in values if value is not None) if complete else None
    loo = []
    for omitted, row in enumerate(ordered):
        retained = [value for index, value in enumerate(values) if index != omitted]
        loo.append(
            {
                "omitted_seed": row["seed"],
                "mean": (
                    fmean(value for value in retained if value is not None)
                    if len(retained) == 4
                    and all(value is not None for value in retained)
                    else None
                ),
            }
        )
    return {
        "n": len(ordered),
        "n_defined": sum(value is not None for value in values),
        "mean": mean,
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
        for seed in G9_REQUEST_BACKPRESSURE_SEEDS
        for method in G9_EFFECTIVE_METHODS
    }
    index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    run_ids = set()
    spec_hashes = set()
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
        for seed in G9_REQUEST_BACKPRESSURE_SEEDS:
            hashes = {
                index[(load, seed, method)].get("workload_tape_sha256")
                for method in G9_EFFECTIVE_METHODS
                if (load, seed, method) in index
            }
            paired_tapes &= len(hashes) == 1 and None not in hashes

    aggregates: list[dict[str, Any]] = []
    aggregate_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for load in FORMAL_E1_LOADS:
        for method in G9_EFFECTIVE_METHODS:
            group = [
                index[(load, seed, method)]
                for seed in G9_REQUEST_BACKPRESSURE_SEEDS
                if (load, seed, method) in index
            ]
            for metric in (*METRICS, "placement_policy_wall_mean_ns"):
                summary = _series_summary(group, metric)
                item = {
                    "load": load,
                    "effective_method": method,
                    "metric": metric,
                    **summary,
                }
                aggregates.append(item)
                aggregate_index[(load, method, metric)] = item

    rankings = []
    for load in FORMAL_E1_LOADS:
        for metric in METRICS:
            values = {
                method: aggregate_index[(load, method, metric)]["mean"]
                for method in G9_EFFECTIVE_METHODS
            }
            candidate_value = values[G9_CANDIDATE]
            strict_first = candidate_value is not None and all(
                value is not None and candidate_value > value
                for method, value in values.items()
                if method != G9_CANDIDATE
            )
            rankings.append(
                {
                    "load": load,
                    "metric": metric,
                    "means": values,
                    "candidate_strictly_first": strict_first,
                }
            )

    paired_rows = []
    for load in FORMAL_E1_LOADS:
        for comparator in (G9_CONTROL, *G9_BASELINES):
            for seed in G9_REQUEST_BACKPRESSURE_SEEDS:
                candidate = index.get((load, seed, G9_CANDIDATE), {})
                other = index.get((load, seed, comparator), {})
                throughput_diff = _difference(
                    candidate.get("throughput_requests_per_ms"),
                    other.get("throughput_requests_per_ms"),
                )
                qpr_diff = _difference(candidate.get("qpr"), other.get("qpr"))
                paired_rows.append(
                    {
                        "load": load,
                        "seed": seed,
                        "comparator": comparator,
                        "candidate_run_id": candidate.get("run_id"),
                        "comparator_run_id": other.get("run_id"),
                        "throughput_difference": throughput_diff,
                        "qpr_difference": qpr_diff,
                        "throughput_ratio": _ratio(
                            candidate.get("throughput_requests_per_ms"),
                            other.get("throughput_requests_per_ms"),
                        ),
                        "qpr_ratio": _ratio(candidate.get("qpr"), other.get("qpr")),
                        "throughput_win": (
                            throughput_diff is not None and throughput_diff > 0.0
                        ),
                        "qpr_win": qpr_diff is not None and qpr_diff > 0.0,
                    }
                )

    paired_summaries = []
    for load in FORMAL_E1_LOADS:
        for comparator in (G9_CONTROL, *G9_BASELINES):
            group = [
                row
                for row in paired_rows
                if row["load"] == load and row["comparator"] == comparator
            ]
            for metric in METRICS:
                field = (
                    "throughput_difference"
                    if metric.startswith("throughput")
                    else "qpr_difference"
                )
                summary = _series_summary(group, field)
                paired_summaries.append(
                    {
                        "load": load,
                        "comparator": comparator,
                        "metric": metric,
                        "win_count": sum(
                            bool(row[field.replace("difference", "win")])
                            for row in group
                        ),
                        **summary,
                    }
                )

    control_pairs = [row for row in paired_rows if row["comparator"] == G9_CONTROL]
    control_win_rows = []
    floor_rows = []
    overhead_rows = []
    for load in FORMAL_E1_LOADS:
        group = [row for row in control_pairs if row["load"] == load]
        control_win_rows.append(
            {
                "load": load,
                "throughput_wins": sum(bool(row["throughput_win"]) for row in group),
                "qpr_wins": sum(bool(row["qpr_win"]) for row in group),
                "passed": len(group) == 5
                and sum(bool(row["throughput_win"]) for row in group) >= 4
                and sum(bool(row["qpr_win"]) for row in group) >= 4,
            }
        )
        for row in group:
            floor_rows.append(
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
            )
        candidate_wall = aggregate_index[
            (load, G9_CANDIDATE, "placement_policy_wall_mean_ns")
        ]["mean"]
        control_wall = aggregate_index[
            (load, G9_CONTROL, "placement_policy_wall_mean_ns")
        ]["mean"]
        ratio = _ratio(candidate_wall, control_wall)
        overhead_rows.append(
            {
                "load": load,
                "candidate_mean_ns": candidate_wall,
                "control_mean_ns": control_wall,
                "ratio": ratio,
                "passed": ratio is not None and ratio <= 1.25,
            }
        )

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
    activation_rows = [
        {
            "run_id": row.get("run_id"),
            "load": row.get("load"),
            "seed": row.get("seed"),
            "over_limit_window_count": row.get("over_limit_window_count"),
            "deferred_positive_window_count": row.get("deferred_positive_window_count"),
            "issues": row.get("backpressure_activation_issues", []),
            "passed": row.get("backpressure_activation_pass") is True,
        }
        for row in rows
        if row.get("effective_method") == G9_CANDIDATE
    ]
    nash_integrity_rows = [
        {
            "run_id": row.get("run_id"),
            "load": row.get("load"),
            "seed": row.get("seed"),
            "effective_method": row.get("effective_method"),
            "active_window_count": row.get("active_window_count"),
            "strict_pne_active_windows": row.get("strict_pne_active_windows"),
            "offline_reference_hit_windows": row.get("offline_reference_hit_windows"),
            "issues": row.get("nash_runtime_issues", []),
            "passed": row.get("nash_runtime_pass") is True,
        }
        for row in rows
        if row.get("effective_method") in (G9_CONTROL, G9_CANDIDATE)
    ]
    runtime_identity_rows = [
        {
            "run_id": row.get("run_id"),
            "runtime_binary_sha256": row.get("runtime_binary_sha256"),
            "runtime_git_commit": row.get("runtime_git_commit"),
            "issues": row.get("runtime_identity_issues", []),
            "passed": row.get("runtime_identity_pass") is True,
        }
        for row in rows
    ]
    runtime_binary_hashes = {
        row["runtime_binary_sha256"] for row in runtime_identity_rows
    }
    runtime_git_commits = {row["runtime_git_commit"] for row in runtime_identity_rows}
    baseline_summaries = [
        row for row in paired_summaries if row["comparator"] in G9_BASELINES
    ]
    conditions = {
        "01_all_75_unique_paired_qc_valid": exact_matrix and paired_tapes,
        "02_all_75_positive_completion_defined_qpr": len(positive_rows) == 75
        and all(row["passed"] for row in positive_rows),
        "03_candidate_first_mean_throughput_each_load": all(
            row["candidate_strictly_first"]
            for row in rankings
            if row["metric"] == "throughput_requests_per_ms"
        ),
        "04_candidate_first_mean_qpr_each_load": all(
            row["candidate_strictly_first"]
            for row in rankings
            if row["metric"] == "qpr"
        ),
        "05_control_paired_wins_at_least_4_of_5_each_metric_load": len(control_win_rows)
        == 3
        and all(row["passed"] for row in control_win_rows),
        "06_positive_paired_mean_vs_each_baseline_metric_load": len(baseline_summaries)
        == 18
        and all(
            row["n"] == 5
            and row["n_defined"] == 5
            and row["mean"] is not None
            and row["mean"] > 0.0
            for row in baseline_summaries
        ),
        "07_every_candidate_seed_control_ratio_at_least_0_80": len(floor_rows) == 15
        and all(row["passed"] for row in floor_rows),
        "08_request_backpressure_activation_and_integrity": len(activation_rows) == 15
        and all(row["passed"] for row in activation_rows),
        "09_strict_eq15_pne_reference_dispatch_runtime_identity": len(
            nash_integrity_rows
        )
        == 30
        and all(row["passed"] for row in nash_integrity_rows)
        and len(runtime_identity_rows) == 75
        and all(row["passed"] for row in runtime_identity_rows)
        and len(runtime_binary_hashes) == 1
        and None not in runtime_binary_hashes
        and len(runtime_git_commits) == 1
        and None not in runtime_git_commits,
        "10_mean_policy_wall_ratio_at_most_1_25_each_load": len(overhead_rows) == 3
        and all(row["passed"] for row in overhead_rows),
    }
    passed = all(conditions.values())
    return {
        "status": (
            "complete_g9_development_confirmation_preregistration_authorized"
            if passed
            else "complete_g9_development_gate_failed"
        ),
        "candidate_development_qualified": passed,
        "confirmation_preregistration_authorized": passed,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
        "all_valid_runs_retained": True,
        "conditions": conditions,
        "failure_reasons": [name for name, value in conditions.items() if not value],
        "positive_completion_and_qpr_rows": positive_rows,
        "rankings": rankings,
        "control_win_rows": control_win_rows,
        "control_floor_rows": floor_rows,
        "baseline_paired_summaries": baseline_summaries,
        "policy_wall_overhead_rows": overhead_rows,
        "activation_rows": activation_rows,
        "nash_integrity_rows": nash_integrity_rows,
        "runtime_identity_rows": runtime_identity_rows,
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
    marker = manifest["g9_request_backpressure_development"]
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
            raise ProtocolValidationError("G9 canonical summary is not an object")
        row = _metric_row(run, summary)
        audit_path = run_dir / "manifest.json"
        audit = read_json(audit_path)
        if not isinstance(audit, Mapping):
            raise ProtocolValidationError("G9 canonical audit is not an object")
        if run["method"] == "sche_nash":
            artifacts = load_run_artifacts(
                run,
                canonical_root,
                expected_manifest_hash=str(manifest["manifest_hash"]),
                result_relative_path=result_relative_path,
            )
            row.update(_nash_runtime(run, artifacts, qc, audit, marker))
        else:
            row.update(_audit_identity(audit, marker))
            row.update(
                {
                    "nash_runtime_pass": None,
                    "nash_runtime_issues": [],
                    "backpressure_activation_pass": None,
                    "backpressure_activation_issues": [],
                }
            )
        rows.append(row)
        receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
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
            "ranking": "strict_arithmetic_mean_rank_over_all_five_fixed_seeds",
            "paired_difference": "candidate_minus_comparator_on_identical_load_seed_tape",
            "policy_wall_overhead": "ratio_of_candidate_and_control_arithmetic_means_of_per_run_placement_policy_wall_ns.mean",
            "leave_one_seed_out": "diagnostic_only_never_used_for_selection",
            "all_valid_runs_retained": True,
            "result_conditioned_seed_or_run_selection": False,
        },
        "activation_gate": copy.deepcopy(marker["activation_gate"]),
        "performance_gate": copy.deepcopy(marker["performance_gate"]),
        "run_metrics": rows,
        "gate_result": gate,
        "artifact_receipts": receipts,
        "run_count": len(rows),
        "confirmation_preregistration_authorized": gate[
            "confirmation_preregistration_authorized"
        ],
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
        raise ProtocolValidationError("refusing to overwrite G9 gate report")
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
