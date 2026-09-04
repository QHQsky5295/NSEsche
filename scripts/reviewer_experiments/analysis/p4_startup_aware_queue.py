"""Result-blind P4 startup-aware queue selection and gate analysis."""

from __future__ import annotations

import argparse
import copy
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Mapping, Sequence

from ..protocol.m1_qualification import _canonical_summary_path
from ..protocol.p4_startup_aware_queue import (
    P4_CANDIDATE,
    P4_CONTROL,
    P4_MANIFEST_SCHEMA,
    P4_OPERATIONAL_REFINEMENT,
    P4_SETTING_LABELS,
)
from ..protocol.schema import (
    P4_STARTUP_AWARE_QUEUE_SEEDS,
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


SELECTION_SCHEMA = "NSE_P4_STARTUP_AWARE_QUEUE_ONLINE_SELECTION_V1"
REPORT_SCHEMA = "NSE_P4_STARTUP_AWARE_QUEUE_GATE_REPORT_V1"
EXPECTED_RUN_COUNT = 10
PRIMARY_METRICS = ("throughput_requests_per_ms", "qpr")
AGGREGATE_METRICS = (
    *PRIMARY_METRICS,
    "completion_ratio",
    "latency_mean_ms",
    "cost_per_completed_request",
    "placement_policy_wall_mean_ns",
)
EXPECTED_SELECTOR = {
    "schema": None,
    "semantics": "single_ready_order_path",
    "orders": None,
    "eligibility": None,
    "ranking": None,
    "welfare_tolerance": None,
    "dispatch_feedback": False,
}


_number = shared._number
_finite_int = shared._finite_int
_verified_artifact = shared._verified_artifact
_ratio = shared._ratio


def _setting(run: Mapping[str, Any]) -> str:
    if run.get("method") != "sche_nash":
        raise ProtocolValidationError("P4 startup-aware screen admits only sche_nash")
    metadata = run.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ProtocolValidationError("P4 startup-aware run lacks metadata")
    label = str(metadata.get("queue_pressure_setting", ""))
    if label not in P4_SETTING_LABELS:
        raise ProtocolValidationError(f"unsupported P4 queue setting: {label}")
    return label


def _validate_ready_manifest(path: Path) -> dict[str, Any]:
    manifest = load_and_validate_manifest(path)
    marker = manifest.get("p4_startup_aware_queue_development")
    if (
        not isinstance(marker, Mapping)
        or marker.get("schema_version") != P4_MANIFEST_SCHEMA
        or tuple(marker.get("development_seeds", ()))
        != tuple(P4_STARTUP_AWARE_QUEUE_SEEDS)
        or tuple(row.get("label") for row in marker.get("settings", ()))
        != P4_SETTING_LABELS
        or marker.get("control_setting") != P4_CONTROL
        or marker.get("candidate_setting") != P4_CANDIDATE
        or marker.get("operational_refinement") != P4_OPERATIONAL_REFINEMENT
        or marker.get("reference_key_schema_version") != 15
        or marker.get("strong_baselines_in_screen") is not False
        or marker.get("all_valid_runs_retained") is not True
        or marker.get("result_conditioned_seed_setting_or_run_selection") is not False
        or manifest.get("phase") != "development"
        or manifest.get("formal_results_eligible") is not False
        or manifest.get("all_tapes_bound") is not True
        or manifest.get("all_references_bound") is not True
        or manifest.get("all_faasrank_models_bound") is not False
        or len(manifest.get("runs", ())) != EXPECTED_RUN_COUNT
    ):
        raise ProtocolValidationError(
            "P4 analysis requires the complete bound ten-run manifest"
        )

    expected = [
        (seed, label)
        for seed in P4_STARTUP_AWARE_QUEUE_SEEDS
        for label in P4_SETTING_LABELS
    ]
    observed = []
    run_ids: set[str] = set()
    spec_hashes: set[str] = set()
    tape_groups: dict[str, set[str]] = defaultdict(set)
    tape_hashes: set[str] = set()
    reference_hashes: set[str] = set()
    artifact_cache: dict[Path, str] = {}
    runtime = marker.get("runtime_binary")
    if not isinstance(runtime, Mapping):
        raise ProtocolValidationError("P4 runtime receipt is missing")
    _verified_artifact(
        path,
        runtime.get("path"),
        runtime.get("sha256"),
        artifact_cache,
        "P4 runtime binary",
    )
    for run in manifest["runs"]:
        seed = str(run.get("seed", ""))
        label = _setting(run)
        observed.append((seed, label))
        run_id = str(run.get("run_id", ""))
        spec_hash = str(run.get("run_spec_hash", ""))
        if not run_id or run_id in run_ids or len(spec_hash) != 64:
            raise ProtocolValidationError("P4 run identity is missing or duplicated")
        if spec_hash in spec_hashes:
            raise ProtocolValidationError("P4 run_spec_hash is duplicated")
        run_ids.add(run_id)
        spec_hashes.add(spec_hash)
        tape = run.get("workload_tape")
        tape_hash = tape.get("sha256") if isinstance(tape, Mapping) else None
        if not isinstance(tape_hash, str) or len(tape_hash) != 64:
            raise ProtocolValidationError("P4 tape is not hash-bound")
        _verified_artifact(
            path, tape.get("path"), tape_hash, artifact_cache, "P4 workload tape"
        )
        tape_groups[seed].add(tape_hash)
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
            raise ProtocolValidationError("P4 reference is not fully bound")
        _verified_artifact(
            path,
            dependency.get("path"),
            dependency.get("sha256"),
            artifact_cache,
            "P4 offline reference",
        )
        _verified_artifact(
            path,
            dependency.get("receipt_path"),
            dependency.get("receipt_sha256"),
            artifact_cache,
            "P4 reference receipt",
        )
        reference_hashes.add(str(dependency["sha256"]))
    if observed != expected:
        raise ProtocolValidationError("P4 manifest order/product differs")
    if len(tape_groups) != 5 or any(len(group) != 1 for group in tape_groups.values()):
        raise ProtocolValidationError("P4 settings are not tape-paired by seed")
    if len(tape_hashes) != 5 or len(reference_hashes) != EXPECTED_RUN_COUNT:
        raise ProtocolValidationError("P4 tape/reference identities are not unique")
    return manifest


def _selection_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for ordinal, run in enumerate(manifest["runs"], start=1):
        dependency = run["reference_dependency"]
        rows.append(
            {
                "ordinal": ordinal,
                "execution_order": "seed_major_then_setting_ordinal",
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "seed": run["seed"],
                "setting": _setting(run),
                "queue_pressure_semantics": run["metadata"][
                    "queue_pressure_semantics"
                ],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": dependency["sha256"],
            }
        )
    return rows


def build_online_selection(manifest_path: Path, canonical_root: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    if canonical_root.exists():
        raise ProtocolValidationError(
            "P4 canonical result root must not exist at selection freeze"
        )
    report: dict[str, Any] = {
        "schema_version": SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": "frozen_before_online_execution",
        "online_results_present_at_freeze": False,
        "canonical_parent_present_at_freeze": False,
        "development_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "canonical_root": str(canonical_root),
        "execution_order": "seed_major_then_setting_ordinal",
        "run_count": EXPECTED_RUN_COUNT,
        "result_conditioned_seed_setting_or_run_selection": False,
        "all_valid_runs_retained": True,
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
        raise ProtocolValidationError("refusing to overwrite P4 online selection")
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
        raise ProtocolValidationError("P4 selection is not an object")
    stored = selection.get("document_sha256")
    payload = dict(selection)
    payload.pop("document_sha256", None)
    contract = selection.get("analysis_contract")
    frozen_manifest = selection.get("development_manifest")
    if (
        not isinstance(stored, str)
        or object_hash(payload) != stored
        or selection.get("schema_version") != SELECTION_SCHEMA
        or selection.get("status") != "frozen_before_online_execution"
        or selection.get("online_results_present_at_freeze") is not False
        or selection.get("canonical_parent_present_at_freeze") is not False
        or selection.get("result_conditioned_seed_setting_or_run_selection")
        is not False
        or selection.get("all_valid_runs_retained") is not True
        or selection.get("technical_retry_only") is not True
        or selection.get("scientific_outcome_retryable") is not False
        or selection.get("execution_order") != "seed_major_then_setting_ordinal"
        or selection.get("run_count") != EXPECTED_RUN_COUNT
        or not isinstance(contract, Mapping)
        or Path(str(contract.get("path", ""))).resolve() != Path(__file__).resolve()
        or contract.get("sha256") != file_hash(Path(__file__).resolve())
        or contract.get("gate_condition_count") != 10
        or not isinstance(frozen_manifest, Mapping)
        or Path(str(frozen_manifest.get("path", ""))).resolve()
        != manifest_path.resolve()
        or frozen_manifest.get("manifest_hash") != manifest.get("manifest_hash")
        or frozen_manifest.get("file_sha256") != file_hash(manifest_path)
        or Path(str(selection.get("canonical_root", ""))).resolve()
        != canonical_root.resolve()
        or selection.get("runs") != _selection_rows(manifest)
    ):
        raise ProtocolValidationError("P4 selection no longer matches inputs")
    return selection


def _metric_row(
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
    stage_wait: Mapping[str, Any],
) -> dict[str, Any]:
    adapted = copy.deepcopy(dict(run))
    adapted["metadata"]["m1_operational_candidate"] = shared.G12_CONTROL
    row = shared._metric_row(adapted, summary, stage_wait)
    row["effective_method"] = _setting(run)
    row["setting"] = _setting(run)
    row["queue_pressure_semantics"] = run["metadata"]["queue_pressure_semantics"]
    return row


def _nash_runtime(
    run: Mapping[str, Any],
    artifacts: RunArtifacts,
    qc: Mapping[str, Any],
    audit: Mapping[str, Any],
    marker: Mapping[str, Any],
) -> dict[str, Any]:
    identity = shared._audit_identity(audit, marker)
    issues = list(identity["runtime_identity_issues"])
    boundary_issues = []
    configs = [
        event for event in artifacts.nse_events if event.get("kind") == "run_config"
    ]
    expected_semantics = str(run["metadata"]["queue_pressure_semantics"])
    expected_definition = (
        "q_n=pending+runnable"
        if expected_semantics == P4_CONTROL
        else "q_n=pending+runnable+starting_resident"
    )
    expected_source = (
        "node_pending_plus_runnable_resident"
        if expected_semantics == P4_CONTROL
        else "node_pending_plus_runnable_resident_plus_starting_resident"
    )
    if len(configs) != 1:
        boundary_issues.append("expected exactly one run_config event")
        config: Mapping[str, Any] = {}
    else:
        config = configs[0]
        boundary_issues.extend(
            validate_runtime_contract_config(
                config,
                expected_candidate=P4_OPERATIONAL_REFINEMENT,
                expected_r0=0.60,
            )
        )
        observed_quality = _number(config.get("quality_weight"), nonnegative=True)
        if observed_quality is None or not math.isclose(
            observed_quality, 0.50, rel_tol=1.0e-6, abs_tol=1.0e-8
        ):
            boundary_issues.append("run_config quality weight differs from P4")
        reference = config.get("reference")
        if (
            config.get("queue_pressure_semantics") != expected_semantics
            or config.get("queue_pressure_semantics_schema")
            != "execution_ready_or_startup_aware_v1"
            or config.get("queue_pressure_definition") != expected_definition
            or config.get("queue_pressure_source") != expected_source
            or config.get("queue_normalization_mode") != "window_max"
            or config.get("queue_normalizer_fixed") is not None
            or not isinstance(reference, Mapping)
            or reference.get("state_key_schema_version") != 15
        ):
            boundary_issues.append("queue semantics or reference-key config differs")
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
    if len(windows) != 1_000:
        issues.append("P4 requires exactly 1,000 Nash policy windows")
    active_windows = 0
    startup_positive_active_windows = 0
    assigned_players = 0
    pne_windows = 0
    reference_hits = 0
    inner_limit_windows = 0
    oscillations = 0
    assignment_trace = []
    for index, window in enumerate(windows):
        decision = window.get("decision")
        solver = window.get("solver")
        social = window.get("social")
        cluster = window.get("cluster")
        if window.get("global_ready_player_admission") is not None:
            boundary_issues.append(f"ready_order window {index} has deferral telemetry")
        if (
            not isinstance(decision, Mapping)
            or not isinstance(solver, Mapping)
            or not isinstance(cluster, Mapping)
        ):
            issues.append(f"window {index} lacks decision/solver/cluster evidence")
            continue
        assigned = _finite_int(decision.get("assigned_players"))
        assignment_hash = _finite_int(decision.get("assignment_hash"))
        execution_ready = _finite_int(cluster.get("queue_execution_ready_count_total"))
        starting = _finite_int(cluster.get("queue_starting_resident_total"))
        actual = _finite_int(cluster.get("queue_pressure_count_total"))
        normalizer = _number(cluster.get("queue_normalizer_used"), positive=True)
        ratio_max = _number(cluster.get("queue_pressure_ratio_max"), nonnegative=True)
        expected_actual = (
            execution_ready
            if expected_semantics == P4_CONTROL
            else (
                execution_ready + starting
                if execution_ready is not None and starting is not None
                else None
            )
        )
        if (
            assigned is None
            or assignment_hash is None
            or execution_ready is None
            or starting is None
            or actual is None
            or expected_actual is None
            or actual != expected_actual
            or cluster.get("queue_pressure_semantics") != expected_semantics
            or cluster.get("queue_resident_partition_invariant_pass") is not True
            or cluster.get("queue_pressure_count_semantics_invariant_pass") is not True
            or normalizer is None
            or ratio_max is None
            or ratio_max > 1.0 + 1.0e-6
        ):
            boundary_issues.append(f"window {index} queue semantics/invariant failed")
        assignment_trace.append(
            {
                "window": _finite_int(window.get("window")),
                "assigned_players": assigned,
                "assignment_hash": assignment_hash,
            }
        )
        if assigned is None or assigned == 0:
            continue
        active_windows += 1
        assigned_players += assigned
        if starting is not None and starting > 0:
            startup_positive_active_windows += 1
        if (
            decision.get("complete_assignment") is not True
            or _finite_int(decision.get("commands_prepared")) != assigned
            or _finite_int(decision.get("commands_sent")) != assigned
            or _finite_int(decision.get("invalid_assignments")) != 0
            or decision.get("dispatch_channel_failed") is not False
        ):
            issues.append(f"active window {index} failed dispatch accounting")
        current_oscillations = _finite_int(solver.get("oscillations"))
        if current_oscillations is not None:
            oscillations += current_oscillations
        if solver.get("inner_limit_hit") is True:
            inner_limit_windows += 1
        if (
            solver.get("inner_stable") is not True
            or solver.get("inner_limit_hit") is not False
            or current_oscillations != 0
        ):
            issues.append(f"active window {index} lacks a strict PNE certificate")
        else:
            pne_windows += 1
        reference_value = (
            _number(social.get("reference"), positive=True)
            if isinstance(social, Mapping)
            else None
        )
        if (
            not isinstance(social, Mapping)
            or social.get("reference_source") != "offline_table"
            or _finite_int(social.get("reference_state_key")) is None
            or reference_value is None
        ):
            issues.append(f"active window {index} lacks a positive offline reference")
        else:
            reference_hits += 1
    if active_windows == 0 or assigned_players == 0:
        issues.append("P4 arm performed no active scheduling work")
    issues.extend(boundary_issues)
    return {
        **identity,
        "formula_method_boundary_pass": not boundary_issues,
        "formula_method_boundary_issues": boundary_issues,
        "nash_runtime_pass": not issues,
        "nash_runtime_issues": issues,
        "policy_window_count": len(windows),
        "active_window_count": active_windows,
        "startup_positive_active_window_count": startup_positive_active_windows,
        "startup_positive_active_window_share": (
            startup_positive_active_windows / active_windows
            if active_windows > 0
            else None
        ),
        "assigned_players": assigned_players,
        "strict_pne_active_windows": pne_windows,
        "offline_reference_hit_windows": reference_hits,
        "inner_limit_window_count": inner_limit_windows,
        "oscillation_count": oscillations,
        "window_assignment_trace": assignment_trace,
    }


def _series_summary(
    rows: Sequence[Mapping[str, Any]], field: str, *, signed: bool = False
) -> dict[str, Any]:
    order = {seed: index for index, seed in enumerate(P4_STARTUP_AWARE_QUEUE_SEEDS)}
    ordered = sorted(rows, key=lambda row: order.get(str(row.get("seed")), 999))
    values = [_number(row.get(field), nonnegative=not signed) for row in ordered]
    complete = len(ordered) == 5 and all(value is not None for value in values)
    defined = [float(value) for value in values if value is not None]
    mean = fmean(defined) if complete else None
    sd = stdev(defined) if complete and len(defined) > 1 else None
    half_width = 2.7764451051977987 * sd / math.sqrt(5) if sd is not None else None
    leave_one_out = []
    for omitted, row in enumerate(ordered):
        retained = [value for index, value in enumerate(values) if index != omitted]
        leave_one_out.append(
            {
                "omitted_seed": row.get("seed"),
                "mean": (
                    fmean(float(value) for value in retained if value is not None)
                    if len(retained) == 4 and all(value is not None for value in retained)
                    else None
                ),
            }
        )
    return {
        "n": len(ordered),
        "n_defined": len(defined),
        "mean": mean,
        "sd": sd,
        "descriptive_95pct_t_interval": (
            [mean - half_width, mean + half_width]
            if mean is not None and half_width is not None
            else None
        ),
        "values": [
            {"seed": row.get("seed"), "value": value}
            for row, value in zip(ordered, values)
        ],
        "leave_one_seed_out_means": leave_one_out,
    }


def _assignment_change(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    control_trace = control.get("window_assignment_trace")
    candidate_trace = candidate.get("window_assignment_trace")
    if not isinstance(control_trace, list) or not isinstance(candidate_trace, list):
        return {"aligned": False, "active_aligned_windows": 0, "changed_windows": 0}
    if len(control_trace) != 1_000 or len(candidate_trace) != 1_000:
        return {"aligned": False, "active_aligned_windows": 0, "changed_windows": 0}
    active = 0
    changed = 0
    for control_window, candidate_window in zip(control_trace, candidate_trace):
        if control_window.get("window") != candidate_window.get("window"):
            return {"aligned": False, "active_aligned_windows": 0, "changed_windows": 0}
        control_assigned = _finite_int(control_window.get("assigned_players"))
        candidate_assigned = _finite_int(candidate_window.get("assigned_players"))
        if control_assigned is None or candidate_assigned is None:
            return {"aligned": False, "active_aligned_windows": 0, "changed_windows": 0}
        if control_assigned > 0 or candidate_assigned > 0:
            active += 1
            if control_window.get("assignment_hash") != candidate_window.get(
                "assignment_hash"
            ):
                changed += 1
    return {"aligned": True, "active_aligned_windows": active, "changed_windows": changed}


def evaluate_gate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {
        (seed, label)
        for seed in P4_STARTUP_AWARE_QUEUE_SEEDS
        for label in P4_SETTING_LABELS
    }
    index: dict[tuple[str, str], Mapping[str, Any]] = {}
    duplicate_keys = []
    for row in rows:
        key = (str(row.get("seed")), str(row.get("setting")))
        if key in index:
            duplicate_keys.append(key)
        else:
            index[key] = row
    population_pass = (
        not duplicate_keys
        and set(index) == expected
        and len(rows) == EXPECTED_RUN_COUNT
        and all(row.get("qc_valid") is True for row in index.values())
        and all(row.get("qpr") is not None for row in index.values())
    )

    aggregate_summaries = []
    aggregate_index: dict[tuple[str, str], dict[str, Any]] = {}
    for label in P4_SETTING_LABELS:
        group = [
            index[(seed, label)]
            for seed in P4_STARTUP_AWARE_QUEUE_SEEDS
            if (seed, label) in index
        ]
        for metric in AGGREGATE_METRICS:
            summary = _series_summary(group, metric)
            record = {"setting": label, "metric": metric, **summary}
            aggregate_summaries.append(record)
            aggregate_index[(label, metric)] = record

    paired_rows = []
    activation_seed_count = 0
    assignment_change_seed_count = 0
    tolerance = 1.0e-12
    for seed in P4_STARTUP_AWARE_QUEUE_SEEDS:
        control = index.get((seed, P4_CONTROL), {})
        candidate = index.get((seed, P4_CANDIDATE), {})
        throughput_difference = (
            _number(candidate.get("throughput_requests_per_ms"), nonnegative=True)
            - _number(control.get("throughput_requests_per_ms"), nonnegative=True)
            if _number(candidate.get("throughput_requests_per_ms"), nonnegative=True)
            is not None
            and _number(control.get("throughput_requests_per_ms"), nonnegative=True)
            is not None
            else None
        )
        qpr_difference = (
            _number(candidate.get("qpr"), nonnegative=True)
            - _number(control.get("qpr"), nonnegative=True)
            if _number(candidate.get("qpr"), nonnegative=True) is not None
            and _number(control.get("qpr"), nonnegative=True) is not None
            else None
        )
        startup_share = _number(
            candidate.get("startup_positive_active_window_share"), nonnegative=True
        )
        activated = startup_share is not None and startup_share >= 0.10
        assignment = _assignment_change(control, candidate)
        changed = assignment["aligned"] and assignment["changed_windows"] >= 1
        activation_seed_count += int(activated)
        assignment_change_seed_count += int(changed)
        paired_rows.append(
            {
                "seed": seed,
                "throughput_difference": throughput_difference,
                "qpr_difference": qpr_difference,
                "throughput_ratio": _ratio(
                    _number(candidate.get("throughput_requests_per_ms"), nonnegative=True),
                    _number(control.get("throughput_requests_per_ms"), nonnegative=True),
                ),
                "qpr_ratio": _ratio(
                    _number(candidate.get("qpr"), nonnegative=True),
                    _number(control.get("qpr"), nonnegative=True),
                ),
                "strict_joint_win": (
                    throughput_difference is not None
                    and qpr_difference is not None
                    and throughput_difference > tolerance
                    and qpr_difference > tolerance
                ),
                "joint_nonloss": (
                    throughput_difference is not None
                    and qpr_difference is not None
                    and throughput_difference >= -tolerance
                    and qpr_difference >= -tolerance
                ),
                "startup_positive_active_window_share": startup_share,
                "startup_activation_pass": activated,
                "assignment_alignment_pass": assignment["aligned"],
                "active_aligned_windows": assignment["active_aligned_windows"],
                "assignment_changed_windows": assignment["changed_windows"],
                "assignment_change_pass": changed,
            }
        )

    throughput_difference_summary = _series_summary(
        paired_rows, "throughput_difference", signed=True
    )
    qpr_difference_summary = _series_summary(paired_rows, "qpr_difference", signed=True)
    throughput_mean = aggregate_index[(P4_CANDIDATE, "throughput_requests_per_ms")][
        "mean"
    ]
    control_throughput_mean = aggregate_index[
        (P4_CONTROL, "throughput_requests_per_ms")
    ]["mean"]
    qpr_mean = aggregate_index[(P4_CANDIDATE, "qpr")]["mean"]
    control_qpr_mean = aggregate_index[(P4_CONTROL, "qpr")]["mean"]
    completion_mean = aggregate_index[(P4_CANDIDATE, "completion_ratio")]["mean"]
    control_completion_mean = aggregate_index[(P4_CONTROL, "completion_ratio")][
        "mean"
    ]
    latency_mean = aggregate_index[(P4_CANDIDATE, "latency_mean_ms")]["mean"]
    control_latency_mean = aggregate_index[(P4_CONTROL, "latency_mean_ms")]["mean"]
    wall_mean = aggregate_index[(P4_CANDIDATE, "placement_policy_wall_mean_ns")][
        "mean"
    ]
    control_wall_mean = aggregate_index[
        (P4_CONTROL, "placement_policy_wall_mean_ns")
    ]["mean"]
    mean_throughput_ratio = _ratio(throughput_mean, control_throughput_mean)
    mean_qpr_ratio = _ratio(qpr_mean, control_qpr_mean)
    latency_ratio = _ratio(latency_mean, control_latency_mean)
    wall_ratio = _ratio(wall_mean, control_wall_mean)
    joint_wins = sum(bool(row["strict_joint_win"]) for row in paired_rows)
    joint_nonlosses = sum(bool(row["joint_nonloss"]) for row in paired_rows)
    per_seed_floor_pass = all(
        row["throughput_ratio"] is not None
        and row["qpr_ratio"] is not None
        and row["throughput_ratio"] >= 0.80
        and row["qpr_ratio"] >= 0.80
        for row in paired_rows
    )
    loo_rows = []
    for metric, summary in (
        ("throughput_requests_per_ms", throughput_difference_summary),
        ("qpr", qpr_difference_summary),
    ):
        values = summary["leave_one_seed_out_means"]
        nonnegative = sum(
            row["mean"] is not None and row["mean"] >= -tolerance for row in values
        )
        positive = sum(
            row["mean"] is not None and row["mean"] > tolerance for row in values
        )
        loo_rows.append(
            {
                "metric": metric,
                "values": values,
                "nonnegative_count": nonnegative,
                "strictly_positive_count": positive,
                "passed": len(values) == 5 and nonnegative == 5 and positive >= 4,
            }
        )
    runtime_rows = [
        index.get((seed, setting), {})
        for seed in P4_STARTUP_AWARE_QUEUE_SEEDS
        for setting in P4_SETTING_LABELS
    ]
    conditions = {
        "condition_1_population_and_identity": population_pass,
        "condition_2_formula_and_method_boundary": (
            len(runtime_rows) == 10
            and all(row.get("formula_method_boundary_pass") is True for row in runtime_rows)
        ),
        "condition_3_mechanism_activation": (
            len(paired_rows) == 5
            and all(row["assignment_alignment_pass"] for row in paired_rows)
            and activation_seed_count >= 4
            and assignment_change_seed_count >= 4
        ),
        "condition_4_viable_dual_mean_effect": (
            mean_throughput_ratio is not None
            and mean_throughput_ratio >= 1.015
            and mean_qpr_ratio is not None
            and mean_qpr_ratio >= 1.11
        ),
        "condition_5_paired_robustness": (
            len(paired_rows) == 5 and joint_wins >= 3 and joint_nonlosses >= 4
        ),
        "condition_6_per_seed_safety": per_seed_floor_pass,
        "condition_7_leave_one_out_stability": all(row["passed"] for row in loo_rows),
        "condition_8_completion_and_latency": (
            completion_mean is not None
            and control_completion_mean is not None
            and completion_mean >= control_completion_mean - tolerance
            and latency_ratio is not None
            and latency_ratio <= 1.05
        ),
        "condition_9_runtime_reference_integrity": (
            len(runtime_rows) == 10
            and all(row.get("nash_runtime_pass") is True for row in runtime_rows)
        ),
        "condition_10_overhead": wall_ratio is not None and wall_ratio <= 1.50,
    }
    qualified = all(conditions.values())
    status = (
        "complete_p4_startup_aware_selected_baseline_compatibility_preregistration_authorized"
        if qualified
        else "complete_p4_startup_aware_failed_family_closed"
    )
    return {
        "status": status,
        "population_pass": population_pass,
        "observed_identity_count": len(index),
        "duplicate_identities": duplicate_keys,
        "aggregate_summaries": aggregate_summaries,
        "mean_throughput_ratio": mean_throughput_ratio,
        "mean_qpr_ratio": mean_qpr_ratio,
        "latency_ratio": latency_ratio,
        "policy_wall_time_ratio": wall_ratio,
        "joint_wins": joint_wins,
        "joint_nonlosses": joint_nonlosses,
        "activation_seed_count": activation_seed_count,
        "assignment_change_seed_count": assignment_change_seed_count,
        "paired_rows": paired_rows,
        "throughput_difference_summary": throughput_difference_summary,
        "qpr_difference_summary": qpr_difference_summary,
        "leave_one_out_rows": loo_rows,
        "conditions": conditions,
        "qualified": qualified,
        "failure_reasons": [name for name, passed in conditions.items() if not passed],
        "selected_setting": P4_CANDIDATE if qualified else None,
        "baseline_compatibility_preregistration_authorized": qualified,
        "baseline_compatibility_sampling_authorized": False,
        "formal_progression_authorized": False,
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
    marker = manifest["p4_startup_aware_queue_development"]
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
            raise ProtocolValidationError("P4 canonical summary is not an object")
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
            raise ProtocolValidationError("P4 canonical audit is not an object")
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
            "paired_difference": "startup_aware_minus_execution_ready_on_identical_seed_tape",
            "active_window": "assigned_players>0",
            "startup_activation": "candidate active window has queue_starting_resident_total>0",
            "assignment_change": "aligned active window final assignment hashes differ",
            "development_rows_are_formal_results": False,
            "all_valid_runs_retained": True,
            "result_conditioned_seed_setting_or_run_selection": False,
        },
        "gate": copy.deepcopy(marker["gate"]),
        "selection_rule": copy.deepcopy(marker["selection_rule"]),
        "run_metrics": rows,
        "gate_result": gate,
        "artifact_receipts": receipts,
        "run_count": len(rows),
        "selected_setting": gate["selected_setting"],
        "baseline_compatibility_preregistration_authorized": gate[
            "baseline_compatibility_preregistration_authorized"
        ],
        "baseline_compatibility_sampling_authorized": False,
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
        raise ProtocolValidationError("refusing to overwrite P4 gate report")
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
