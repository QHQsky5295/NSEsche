"""Result-blind selection freeze and fail-closed G16 development analysis.

The exact 30-run selection and this analyzer are frozen before the online
result directory exists. Every first QC-valid run is retained, including
zero-completion runs whose QPR is explicitly undefined. The already-frozen
G12 paired-statistics core is reused through an exact candidate/seed relabeling;
the preregistered G16 performance differences and magnitude-valve activation
contract are evaluated independently below.
"""

from __future__ import annotations

import argparse
import copy
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..protocol.g16_overflow_magnitude_valve import (
    G16_CANDIDATE,
    G16_CONTROL,
    G16_EFFECTIVE_METHODS,
    G16_MANIFEST_SCHEMA,
)
from ..protocol.m1_qualification import _canonical_summary_path
from ..protocol.schema import (
    FORMAL_E1_LOADS,
    G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS,
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
from . import g12_global_ready_admission as shared
from .feedback_trace import validate_runtime_contract_config
from .formal_inputs import validate_canonical_run
from .observability import RunArtifacts, load_run_artifacts, stage_wait_run_metrics


SELECTION_SCHEMA = "NSE_G16_OVERFLOW_MAGNITUDE_VALVE_ONLINE_SELECTION_V1"
REPORT_SCHEMA = "NSE_G16_OVERFLOW_MAGNITUDE_VALVE_GATE_REPORT_V1"
EXPECTED_RUN_COUNT = 30
EXPECTED_SELECTOR = {
    "schema": None,
    "semantics": "single_ready_order_path",
    "orders": None,
    "eligibility": None,
    "ranking": None,
    "welfare_tolerance": None,
    "dispatch_feedback": False,
}
OVERFLOW_MAGNITUDE_RELEASE_VALVE_SCHEMA = (
    "global_feasible_ready_material_first_overflow_5_over_4_prefix_then_"
    "persistent_full_release_v1"
)
ZERO_VIOLATION_FIELDS = (
    "readiness_violations",
    "feasibility_violations",
    "legacy_order_violations",
    "prefix_violations",
    "bound_violations",
    "magnitude_comparison_violations",
    "admission_rule_violations",
    "state_transition_violations",
    "dispatch_set_violations",
)
G16_TO_SHARED_SEEDS = dict(
    zip(
        G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS,
        shared.G12_GLOBAL_READY_ADMISSION_SEEDS,
    )
)
SHARED_TO_G16_SEEDS = {value: key for key, value in G16_TO_SHARED_SEEDS.items()}


_number = shared._number
_finite_int = shared._finite_int
_verified_artifact = shared._verified_artifact
_ratio = shared._ratio


def _telemetry_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _effective_method(run: Mapping[str, Any]) -> str:
    if run.get("method") != "sche_nash":
        raise ProtocolValidationError("G16 initial stage admits only sche_nash arms")
    metadata = run.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ProtocolValidationError("G16 run lacks candidate metadata")
    method = str(metadata.get("m1_operational_candidate", ""))
    if method not in G16_EFFECTIVE_METHODS:
        raise ProtocolValidationError(f"unsupported G16 effective method: {method}")
    return method


def _validate_ready_manifest(path: Path) -> dict[str, Any]:
    manifest = load_and_validate_manifest(path)
    marker = manifest.get("g16_overflow_magnitude_valve_development")
    if (
        not isinstance(marker, Mapping)
        or marker.get("schema_version") != G16_MANIFEST_SCHEMA
        or marker.get("control") != G16_CONTROL
        or marker.get("candidate") != G16_CANDIDATE
        or tuple(marker.get("loads", ())) != tuple(FORMAL_E1_LOADS)
        or tuple(marker.get("development_seeds", ()))
        != tuple(G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS)
        or marker.get("strong_baselines_in_initial_stage") is not False
        or marker.get("all_valid_runs_retained") is not True
        or marker.get("result_conditioned_seed_or_run_selection") is not False
        or manifest.get("phase") != "development"
        or manifest.get("formal_results_eligible") is not False
        or manifest.get("all_tapes_bound") is not True
        or manifest.get("all_references_bound") is not True
        or manifest.get("all_faasrank_models_bound") is not False
        or len(manifest.get("runs", ())) != EXPECTED_RUN_COUNT
    ):
        raise ProtocolValidationError("G16 requires the complete bound 30-run manifest")

    expected = {
        (load, seed, method)
        for load in FORMAL_E1_LOADS
        for seed in G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS
        for method in G16_EFFECTIVE_METHODS
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
        raise ProtocolValidationError("G16 runtime receipt is missing")
    _verified_artifact(
        path,
        runtime.get("path"),
        runtime.get("sha256"),
        artifact_cache,
        "G16 runtime binary",
    )
    for run in manifest["runs"]:
        load = str(run.get("workload", {}).get("request_freq", ""))
        seed = str(run.get("seed", ""))
        method = _effective_method(run)
        identity = (load, seed, method)
        if identity in observed:
            raise ProtocolValidationError(f"duplicate G16 matrix identity: {identity}")
        observed.add(identity)
        run_id = str(run.get("run_id", ""))
        spec_hash = str(run.get("run_spec_hash", ""))
        if not run_id or run_id in run_ids or len(spec_hash) != 64:
            raise ProtocolValidationError("G16 run identity is missing or duplicated")
        if spec_hash in spec_hashes:
            raise ProtocolValidationError("G16 run_spec_hash is duplicated")
        run_ids.add(run_id)
        spec_hashes.add(spec_hash)
        tape = run.get("workload_tape")
        tape_hash = tape.get("sha256") if isinstance(tape, Mapping) else None
        if not isinstance(tape_hash, str) or len(tape_hash) != 64:
            raise ProtocolValidationError("G16 workload tape is not hash-bound")
        _verified_artifact(
            path, tape.get("path"), tape_hash, artifact_cache, "G16 workload tape"
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
            raise ProtocolValidationError("G16 reference is not fully bound")
        _verified_artifact(
            path,
            dependency.get("path"),
            dependency.get("sha256"),
            artifact_cache,
            "G16 offline reference",
        )
        _verified_artifact(
            path,
            dependency.get("receipt_path"),
            dependency.get("receipt_sha256"),
            artifact_cache,
            "G16 reference receipt",
        )
        reference_hashes.add(str(dependency["sha256"]))
    if observed != expected:
        raise ProtocolValidationError("G16 manifest does not cover the exact product")
    if len(tape_groups) != 15 or any(len(group) != 1 for group in tape_groups.values()):
        raise ProtocolValidationError(
            "G16 methods are not paired on one tape per load/seed"
        )
    if len(tape_hashes) != 15 or len(reference_hashes) != EXPECTED_RUN_COUNT:
        raise ProtocolValidationError("G16 tape/reference identities are not unique")
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
            "G16 selection must be frozen before the online result workspace exists"
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
            "gate_condition_count": 9,
        },
        "runs": _selection_rows(manifest),
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_online_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite frozen G16 selection")
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
        raise ProtocolValidationError("G16 selection is not an object")
    stored = selection.get("document_sha256")
    payload = dict(selection)
    payload.pop("document_sha256", None)
    if not isinstance(stored, str) or object_hash(payload) != stored:
        raise ProtocolValidationError("G16 selection document hash mismatch")
    frozen_manifest = selection.get("development_manifest")
    contract = selection.get("analysis_contract")
    if (
        selection.get("schema_version") != SELECTION_SCHEMA
        or selection.get("status") != "frozen_before_online_execution"
        or selection.get("online_results_present_at_freeze") is not False
        or selection.get("canonical_parent_present_at_freeze") is not False
        or selection.get("result_conditioned_seed_or_run_selection") is not False
        or selection.get("all_valid_runs_retained") is not True
        or selection.get("technical_retry_only") is not True
        or selection.get("scientific_outcome_retryable") is not False
        or selection.get("execution_order") != "development_manifest_order"
        or selection.get("run_count") != EXPECTED_RUN_COUNT
        or not isinstance(contract, Mapping)
        or Path(str(contract.get("path", ""))).resolve() != Path(__file__).resolve()
        or contract.get("sha256") != file_hash(Path(__file__).resolve())
        or contract.get("gate_condition_count") != 9
        or not isinstance(frozen_manifest, Mapping)
        or Path(str(frozen_manifest.get("path", ""))).resolve()
        != manifest_path.resolve()
        or frozen_manifest.get("manifest_hash") != manifest.get("manifest_hash")
        or frozen_manifest.get("file_sha256") != file_hash(manifest_path)
        or Path(str(selection.get("canonical_root", ""))).resolve()
        != canonical_root.resolve()
        or selection.get("runs") != _selection_rows(manifest)
    ):
        raise ProtocolValidationError("G16 selection no longer matches frozen inputs")
    return selection


def _metric_row(
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
    stage_wait: Mapping[str, Any],
) -> dict[str, Any]:
    """Reuse the frozen metric extractor after an identity-only relabeling."""

    effective = _effective_method(run)
    adapted = copy.deepcopy(dict(run))
    if effective == G16_CANDIDATE:
        adapted["metadata"]["m1_operational_candidate"] = shared.G12_CANDIDATE
    row = shared._metric_row(adapted, summary, stage_wait)
    row["effective_method"] = effective
    return row


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


def _overflow_magnitude_telemetry(
    records: Sequence[tuple[int, Mapping[str, Any], int]], node_count: int
) -> dict[str, Any]:
    issues: list[str] = []
    totals = {
        "dependency_ready_candidates_total": 0,
        "feasible_ready_candidates_total": 0,
        "admitted_players_total": 0,
        "deferred_feasible_players_total": 0,
        "deferred_positive_window_count": 0,
        "magnitude_gate_applicable_window_count": 0,
        "magnitude_gate_pass_window_count": 0,
        "first_overflow_below_magnitude_release_window_count": 0,
        "first_overflow_magnitude_bounded_window_count": 0,
        "persistent_overflow_release_window_count": 0,
        "below_limit_window_count": 0,
        "post_overflow_reset_window_count": 0,
    }
    violation_totals = {field: 0 for field in ZERO_VIOLATION_FIELDS}
    expected_valve_open = False
    deferral_streak = 0
    longest_deferral_streak = 0
    for index, telemetry, assigned in records:
        int_fields = (
            "dependency_ready_candidates",
            "feasible_ready_candidates",
            "configured_node_count",
            "admission_limit",
            "admitted_players",
            "deferred_feasible_players",
            "candidate_order_hash",
            "admitted_order_hash",
            "magnitude_threshold_numerator",
            "magnitude_threshold_denominator",
            "magnitude_comparison_lhs",
            "magnitude_comparison_rhs",
            *ZERO_VIOLATION_FIELDS,
        )
        values = {field: _telemetry_int(telemetry.get(field)) for field in int_fields}
        boolean_fields = (
            "current_overflow",
            "valve_open_before",
            "valve_open_after",
            "magnitude_gate_applicable",
            "magnitude_gate_pass",
        )
        booleans = {field: telemetry.get(field) for field in boolean_fields}
        if (
            telemetry.get("schema") != OVERFLOW_MAGNITUDE_RELEASE_VALVE_SCHEMA
            or any(value is None for value in values.values())
            or any(not isinstance(value, bool) for value in booleans.values())
        ):
            issues.append(
                f"window {index} has invalid G16 schema/count/state telemetry"
            )
            continue
        dependency_ready = int(values["dependency_ready_candidates"])
        feasible_ready = int(values["feasible_ready_candidates"])
        configured = int(values["configured_node_count"])
        admission_limit = int(values["admission_limit"])
        admitted = int(values["admitted_players"])
        deferred = int(values["deferred_feasible_players"])
        current_overflow = bool(booleans["current_overflow"])
        valve_open_before = bool(booleans["valve_open_before"])
        valve_open_after = bool(booleans["valve_open_after"])
        magnitude_applicable = bool(booleans["magnitude_gate_applicable"])
        magnitude_pass = bool(booleans["magnitude_gate_pass"])
        expected_overflow = feasible_ready > node_count
        expected_first_overflow = not expected_valve_open and expected_overflow
        expected_lhs = 4 * feasible_ready
        expected_rhs = 5 * node_count
        expected_magnitude_pass = (
            expected_first_overflow and expected_lhs >= expected_rhs
        )
        if not expected_overflow and not expected_valve_open:
            expected_mode = "below_limit"
        elif not expected_overflow:
            expected_mode = "post_overflow_reset"
        elif expected_valve_open:
            expected_mode = "persistent_overflow_release"
        elif expected_magnitude_pass:
            expected_mode = "first_overflow_magnitude_bounded"
        else:
            expected_mode = "first_overflow_below_magnitude_release"
        expected_admitted = node_count if expected_magnitude_pass else feasible_ready
        expected_deferred = feasible_ready - expected_admitted
        min_arrival = telemetry.get("admitted_min_arrival_frame")
        max_arrival = telemetry.get("admitted_max_arrival_frame")
        arrival_range_valid = (
            admitted == 0 and min_arrival is None and max_arrival is None
        ) or (
            admitted > 0
            and _telemetry_int(min_arrival) is not None
            and _telemetry_int(max_arrival) is not None
            and int(min_arrival) <= int(max_arrival)
        )
        for field in violation_totals:
            violation_totals[field] += int(values[field])
        if (
            dependency_ready < feasible_ready
            or configured != node_count
            or current_overflow != expected_overflow
            or valve_open_before != expected_valve_open
            or valve_open_after != expected_overflow
            or magnitude_applicable != expected_first_overflow
            or magnitude_pass != expected_magnitude_pass
            or int(values["magnitude_threshold_numerator"]) != 5
            or int(values["magnitude_threshold_denominator"]) != 4
            or int(values["magnitude_comparison_lhs"]) != expected_lhs
            or int(values["magnitude_comparison_rhs"]) != expected_rhs
            or telemetry.get("admission_mode") != expected_mode
            or admission_limit != expected_admitted
            or admitted != expected_admitted
            or deferred != expected_deferred
            or assigned != admitted
            or not arrival_range_valid
            or (
                admitted == feasible_ready
                and values["candidate_order_hash"] != values["admitted_order_hash"]
            )
            or any(int(values[field]) != 0 for field in violation_totals)
        ):
            issues.append(f"window {index} violates G16 magnitude-valve accounting")
        totals["dependency_ready_candidates_total"] += dependency_ready
        totals["feasible_ready_candidates_total"] += feasible_ready
        totals["admitted_players_total"] += admitted
        totals["deferred_feasible_players_total"] += deferred
        totals["deferred_positive_window_count"] += int(deferred > 0)
        totals["magnitude_gate_applicable_window_count"] += int(magnitude_applicable)
        totals["magnitude_gate_pass_window_count"] += int(magnitude_pass)
        mode_counter = {
            "first_overflow_below_magnitude_release": (
                "first_overflow_below_magnitude_release_window_count"
            ),
            "first_overflow_magnitude_bounded": (
                "first_overflow_magnitude_bounded_window_count"
            ),
            "persistent_overflow_release": "persistent_overflow_release_window_count",
            "below_limit": "below_limit_window_count",
            "post_overflow_reset": "post_overflow_reset_window_count",
        }.get(str(telemetry.get("admission_mode")))
        if mode_counter is not None:
            totals[mode_counter] += 1
        deferral_streak = deferral_streak + 1 if deferred > 0 else 0
        longest_deferral_streak = max(longest_deferral_streak, deferral_streak)
        expected_valve_open = expected_overflow
    if longest_deferral_streak > 1:
        issues.append("positive deferral persists across adjacent scheduler windows")
    return {
        "g16_activation_pass": not issues,
        "g16_activation_issues": issues,
        "longest_positive_deferral_episode_windows": longest_deferral_streak,
        **totals,
        **violation_totals,
    }


def _empty_telemetry_result(issues: Sequence[str]) -> dict[str, Any]:
    return {
        "g16_activation_pass": not issues,
        "g16_activation_issues": list(issues),
        "longest_positive_deferral_episode_windows": 0,
        "dependency_ready_candidates_total": 0,
        "feasible_ready_candidates_total": 0,
        "admitted_players_total": 0,
        "deferred_feasible_players_total": 0,
        "deferred_positive_window_count": 0,
        "magnitude_gate_applicable_window_count": 0,
        "magnitude_gate_pass_window_count": 0,
        "first_overflow_below_magnitude_release_window_count": 0,
        "first_overflow_magnitude_bounded_window_count": 0,
        "persistent_overflow_release_window_count": 0,
        "below_limit_window_count": 0,
        "post_overflow_reset_window_count": 0,
        **{field: 0 for field in ZERO_VIOLATION_FIELDS},
    }


def _nash_runtime(
    run: Mapping[str, Any],
    artifacts: RunArtifacts,
    qc: Mapping[str, Any],
    audit: Mapping[str, Any],
    marker: Mapping[str, Any],
) -> dict[str, Any]:
    effective = _effective_method(run)
    is_candidate = effective == G16_CANDIDATE
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
    telemetry_records: list[tuple[int, Mapping[str, Any], int]] = []
    for index, window in enumerate(windows):
        decision = window.get("decision")
        solver = window.get("solver")
        social = window.get("social")
        telemetry = window.get("global_ready_player_admission")
        if not isinstance(decision, Mapping) or not isinstance(solver, Mapping):
            issues.append(f"window {index} lacks decision/solver evidence")
            continue
        assigned = _finite_int(decision.get("assigned_players"))
        if assigned is None:
            issues.append(f"window {index} has invalid assigned-player count")
            continue
        if not is_candidate:
            if telemetry is not None:
                activation_issues.append(
                    f"control window {index} unexpectedly has G16 telemetry"
                )
        elif not isinstance(telemetry, Mapping):
            activation_issues.append(f"candidate window {index} lacks G16 telemetry")
        else:
            telemetry_records.append((index, telemetry, assigned))
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
    telemetry_result = _empty_telemetry_result(activation_issues)
    if is_candidate:
        telemetry_result = _overflow_magnitude_telemetry(
            telemetry_records, int(marker["node_count"])
        )
        telemetry_result["g16_activation_issues"] = [
            *activation_issues,
            *telemetry_result["g16_activation_issues"],
        ]
        telemetry_result["g16_activation_pass"] = not telemetry_result[
            "g16_activation_issues"
        ]
    activation_pass = telemetry_result["g16_activation_pass"]
    return {
        **identity,
        "nash_runtime_pass": not issues and activation_pass,
        "nash_runtime_issues": [*issues, *telemetry_result["g16_activation_issues"]],
        "policy_window_count": len(windows),
        "active_window_count": active_windows,
        "assigned_players": assigned_players,
        "strict_pne_active_windows": pne_windows,
        "offline_reference_hit_windows": reference_hits,
        **telemetry_result,
    }


def _to_shared_row(row: Mapping[str, Any]) -> dict[str, Any]:
    adapted = copy.deepcopy(dict(row))
    seed = str(adapted.get("seed", ""))
    if seed in G16_TO_SHARED_SEEDS:
        adapted["seed"] = G16_TO_SHARED_SEEDS[seed]
    if adapted.get("effective_method") == G16_CANDIDATE:
        adapted["effective_method"] = shared.G12_CANDIDATE
    adapted["g12_activation_pass"] = adapted.get("g16_activation_pass")
    adapted["g12_activation_issues"] = copy.deepcopy(
        adapted.get("g16_activation_issues", [])
    )
    return adapted


def _restore_shared_labels(value: Any) -> Any:
    if isinstance(value, list):
        return [_restore_shared_labels(item) for item in value]
    if isinstance(value, dict):
        return {key: _restore_shared_labels(item) for key, item in value.items()}
    if value == shared.G12_CANDIDATE:
        return G16_CANDIDATE
    if isinstance(value, str) and value in SHARED_TO_G16_SEEDS:
        return SHARED_TO_G16_SEEDS[value]
    if value == "complete_g12_development_strong_baseline_preregistration_authorized":
        return "complete_g16_development_strong_baseline_preregistration_authorized"
    if value == "complete_g12_development_gate_failed":
        return "complete_g16_development_gate_failed"
    return value


def _activation_evidence(
    index: Mapping[tuple[str, str, str], Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], bool]:
    activation_rows = []
    below_threshold_runs = []
    persistent_runs = []
    for load in FORMAL_E1_LOADS:
        candidates = [
            index.get((load, seed, G16_CANDIDATE), {})
            for seed in G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS
        ]
        bounded = sum(
            (_finite_int(row.get("first_overflow_magnitude_bounded_window_count")) or 0)
            > 0
            for row in candidates
        )
        for row in candidates:
            if (
                _finite_int(
                    row.get("first_overflow_below_magnitude_release_window_count")
                )
                or 0
            ) > 0:
                below_threshold_runs.append(
                    {
                        "load": load,
                        "seed": row.get("seed"),
                        "run_id": row.get("run_id"),
                        "window_count": row.get(
                            "first_overflow_below_magnitude_release_window_count"
                        ),
                    }
                )
            if (
                _finite_int(row.get("persistent_overflow_release_window_count")) or 0
            ) > 0:
                persistent_runs.append(
                    {
                        "load": load,
                        "seed": row.get("seed"),
                        "run_id": row.get("run_id"),
                        "window_count": row.get(
                            "persistent_overflow_release_window_count"
                        ),
                    }
                )
        local_pass = (
            len(candidates) == 5
            and bounded >= 1
            and all(
                row.get("g16_activation_pass") is True
                and (
                    _finite_int(row.get("longest_positive_deferral_episode_windows"))
                    or 0
                )
                <= 1
                and all(
                    (_finite_int(row.get(field)) or 0) == 0
                    for field in ZERO_VIOLATION_FIELDS
                )
                for row in candidates
            )
        )
        activation_rows.append(
            {
                "load": load,
                "material_first_overflow_bounded_seeds": bounded,
                "run_evidence": [
                    {
                        "seed": row.get("seed"),
                        "run_id": row.get("run_id"),
                        "first_overflow_magnitude_bounded_window_count": row.get(
                            "first_overflow_magnitude_bounded_window_count"
                        ),
                        "first_overflow_below_magnitude_release_window_count": row.get(
                            "first_overflow_below_magnitude_release_window_count"
                        ),
                        "persistent_overflow_release_window_count": row.get(
                            "persistent_overflow_release_window_count"
                        ),
                        "longest_positive_deferral_episode_windows": row.get(
                            "longest_positive_deferral_episode_windows"
                        ),
                        "issues": row.get("g16_activation_issues", []),
                    }
                    for row in candidates
                ],
                "local_pass": local_pass,
            }
        )

    def cross_load_summary(evidence: list[dict[str, Any]]) -> dict[str, Any]:
        loads = sorted({str(row["load"]) for row in evidence})
        return {
            "run_count": len(evidence),
            "loads": loads,
            "load_count": len(loads),
            "run_evidence": evidence,
            "passed": len(evidence) >= 3 and len(loads) >= 2,
        }

    below_summary = cross_load_summary(below_threshold_runs)
    persistent_summary = cross_load_summary(persistent_runs)
    passed = (
        all(row["local_pass"] for row in activation_rows)
        and below_summary["passed"]
        and persistent_summary["passed"]
    )
    return activation_rows, below_summary, persistent_summary, passed


def evaluate_gate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Evaluate all nine immutable G16 development gate conditions."""

    expected = {
        (load, seed, method)
        for load in FORMAL_E1_LOADS
        for seed in G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS
        for method in G16_EFFECTIVE_METHODS
    }
    index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("load")),
            str(row.get("seed")),
            str(row.get("effective_method")),
        )
        if key not in index:
            index[key] = row
    result = _restore_shared_labels(
        shared.evaluate_gate([_to_shared_row(row) for row in rows])
    )
    candidate_report = result["candidate_reports"][0]

    paired_win_rows = []
    for load in FORMAL_E1_LOADS:
        group = [row for row in result["paired_rows"] if row["load"] == load]
        joint_wins = sum(bool(row["joint_win"]) for row in group)
        joint_nonlosses = sum(
            row["throughput_difference"] is not None
            and row["qpr_difference"] is not None
            and row["throughput_difference"] >= 0.0
            and row["qpr_difference"] >= 0.0
            for row in group
        )
        paired_win_rows.append(
            {
                "load": load,
                "joint_wins": joint_wins,
                "joint_nonlosses": joint_nonlosses,
                "passed": len(group) == 5 and joint_wins >= 1 and joint_nonlosses >= 4,
            }
        )

    leave_one_out_rows = []
    for load in FORMAL_E1_LOADS:
        for metric in shared.PRIMARY_METRICS:
            summary = next(
                row
                for row in result["paired_summaries"]
                if row["load"] == load and row["metric"] == metric
            )
            values = copy.deepcopy(summary["leave_one_seed_out_means"])
            nonnegative = sum(
                item["mean"] is not None and item["mean"] >= 0.0 for item in values
            )
            positive = sum(
                item["mean"] is not None and item["mean"] > 0.0 for item in values
            )
            leave_one_out_rows.append(
                {
                    "load": load,
                    "metric": metric,
                    "values": values,
                    "nonnegative_count": nonnegative,
                    "strictly_positive_count": positive,
                    "passed": len(values) == 5 and nonnegative == 5 and positive >= 4,
                }
            )

    aggregate_index = {
        (row["load"], row["effective_method"], row["metric"]): row
        for row in result["aggregate_summaries"]
    }
    completion_latency_rows = []
    for load in FORMAL_E1_LOADS:
        candidate_completion = aggregate_index[
            (load, G16_CANDIDATE, "completion_ratio")
        ]["mean"]
        control_completion = aggregate_index[(load, G16_CONTROL, "completion_ratio")][
            "mean"
        ]
        candidate_latency = aggregate_index[(load, G16_CANDIDATE, "latency_mean_ms")][
            "mean"
        ]
        control_latency = aggregate_index[(load, G16_CONTROL, "latency_mean_ms")][
            "mean"
        ]
        latency_ratio = _ratio(candidate_latency, control_latency)
        completion_latency_rows.append(
            {
                "load": load,
                "candidate_completion_ratio_mean": candidate_completion,
                "control_completion_ratio_mean": control_completion,
                "candidate_latency_mean_ms": candidate_latency,
                "control_latency_mean_ms": control_latency,
                "latency_ratio": latency_ratio,
                "passed": candidate_completion is not None
                and control_completion is not None
                and candidate_completion >= control_completion
                and latency_ratio is not None
                and latency_ratio <= 1.05,
            }
        )

    (
        activation_rows,
        below_summary,
        persistent_summary,
        activation_pass,
    ) = _activation_evidence(index)
    old_conditions = candidate_report["conditions"]
    conditions = {
        "01_all_30_unique_paired_qc_positive_defined_qpr_one_runtime": old_conditions[
            "01_all_30_unique_paired_qc_positive_defined_qpr_one_runtime"
        ],
        "02_mean_throughput_and_qpr_above_control_each_load": old_conditions[
            "02_mean_throughput_and_qpr_above_control_each_load"
        ],
        "03_at_least_1_joint_win_and_4_joint_nonlosses_each_load": all(
            row["passed"] for row in paired_win_rows
        ),
        "04_every_seed_throughput_and_qpr_ratio_at_least_0_80": old_conditions[
            "04_every_seed_throughput_and_qpr_ratio_at_least_0_80"
        ],
        "05_every_leave_one_seed_out_nonnegative_and_at_least_4_positive": all(
            row["passed"] for row in leave_one_out_rows
        ),
        "06_completion_not_below_and_latency_ratio_at_most_1_05_each_load": all(
            row["passed"] for row in completion_latency_rows
        ),
        "07_magnitude_valve_activation_and_nine_zero_violation_contracts": (
            set(index) == expected and activation_pass
        ),
        "08_strict_eq15_pne_reference_dispatch_runtime_identity": old_conditions[
            "08_strict_eq15_pne_reference_dispatch_runtime_identity"
        ],
        "09_mean_policy_wall_ratio_at_most_1_50_each_load": old_conditions[
            "09_mean_policy_wall_ratio_at_most_1_50_each_load"
        ],
    }
    candidate_report["conditions"] = conditions
    candidate_report["paired_win_rows"] = paired_win_rows
    candidate_report["leave_one_seed_out_rows"] = leave_one_out_rows
    candidate_report["completion_latency_rows"] = completion_latency_rows
    candidate_report["activation_rows"] = activation_rows
    candidate_report["below_threshold_release_summary"] = below_summary
    candidate_report["persistent_release_summary"] = persistent_summary
    qualified = all(conditions.values())
    candidate_report["qualified"] = qualified
    candidate_report["failure_reasons"] = [
        name for name, value in conditions.items() if not value
    ]
    result["status"] = (
        "complete_g16_development_strong_baseline_preregistration_authorized"
        if qualified
        else "complete_g16_development_gate_failed"
    )
    result["selected_candidate"] = G16_CANDIDATE if qualified else None
    result["candidate_development_qualified"] = qualified
    result["strong_baseline_addendum_preregistration_authorized"] = qualified
    result["strong_baseline_sampling_authorized"] = False
    result["confirmation_sampling_authorized"] = False
    result["formal_progression_authorized"] = False
    result["shared_statistics_core"] = {
        "module": str(Path(shared.__file__).resolve()),
        "sha256": file_hash(Path(shared.__file__).resolve()),
        "identity_relabeling_only": True,
        "g16_conditions_3_5_6_7_evaluated_separately": True,
    }
    return result


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
    marker = manifest["g16_overflow_magnitude_valve_development"]
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
            raise ProtocolValidationError("G16 canonical summary is not an object")
        artifacts = load_run_artifacts(
            run,
            canonical_root,
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=result_relative_path,
        )
        row = _metric_row(run, summary, stage_wait_run_metrics(artifacts))
        audit_path = run_dir / "manifest.json"
        audit = read_json(audit_path)
        if not isinstance(audit, Mapping):
            raise ProtocolValidationError("G16 canonical audit is not an object")
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
            "joint_nonloss": "paired_throughput_difference_and_qpr_difference_both_nonnegative",
            "descriptive_interval": "two_sided_t_interval_df4_not_used_for_gate",
            "overflow_magnitude_valve": "first_overflow_admits_N_only_when_4F_at_least_5N_else_releases_all; adjacent_overflow_releases_all",
            "qpr_factorization": "throughput_ratio/(latency_ratio*cost_ratio)",
            "leave_one_seed_out": "all_nonnegative_and_at_least_four_strictly_positive_per_primary_metric_load",
            "all_valid_runs_retained": True,
            "result_conditioned_seed_or_run_selection": False,
        },
        "activation_gate": copy.deepcopy(marker["activation_gate"]),
        "performance_gate": copy.deepcopy(marker["performance_gate"]),
        "decision_rule": copy.deepcopy(marker["decision_rule"]),
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
        raise ProtocolValidationError("refusing to overwrite G16 gate report")
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
