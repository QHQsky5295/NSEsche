"""Read-only diagnosis of the frozen G3-E0 development product.

Frames and scheduler windows are reduced to one row per independent run before
cross-run statistics are computed. The module never treats within-run records
as independent repetitions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Iterable, Mapping, Sequence

from scipy import stats as scipy_stats

from ..protocol.g3_e0_operational import (
    G3_E0_OPERATIONAL_BASELINES,
    G3_E0_OPERATIONAL_CANDIDATES,
    G3_E0_OPERATIONAL_LOADS,
    G3_E0_OPERATIONAL_SEEDS,
    G3_E0_OPERATIONAL_TOPOLOGIES,
)
from ..protocol.m1_qualification import _screen_metrics
from ..protocol.schema import ProtocolValidationError, load_and_validate_manifest
from ..protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from .observability import RunArtifacts, load_run_artifacts
from .stats import holm_adjust


SCHEMA_VERSION = "NSE_G3_POSTFAIL_CLAIM_SCENE_DIAGNOSIS_V1"
EXPECTED_SELECTION_FILE_SHA256 = (
    "22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7"
)
EXPECTED_SELECTION_DOCUMENT_SHA256 = (
    "4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34"
)
CONTROL = "ready_order"
ACTIVE_CANDIDATES = tuple(
    candidate for candidate in G3_E0_OPERATIONAL_CANDIDATES if candidate != CONTROL
)
ADVANCED_BASELINES = frozenset(
    {"faasrank", "faasrank_p", "ocs", "hiku", "jiagu", "orion"}
)
COMPONENTS = (
    "throughput_contribution",
    "latency_contribution",
    "cost_contribution",
)

FRAME_FIELDS = (
    "active_requests",
    "tasks_in_system",
    "queue_total",
    "unscheduled_tasks",
    "ready_unscheduled_tasks",
    "pending_tasks",
    "running_tasks",
    "running_containers",
    "starting_containers",
    "node_cpu_utilization_mean",
    "node_memory_utilization_mean",
)

WINDOW_FIELDS: dict[str, tuple[str, ...]] = {
    "queue_total": ("cluster", "queue_total"),
    "queue_resident_total": ("cluster", "queue_resident_total"),
    "queue_runnable_total": ("cluster", "queue_runnable_total"),
    "queue_starting_resident_total": (
        "cluster",
        "queue_starting_resident_total",
    ),
    "containers_running": ("cluster", "containers_running"),
    "containers_starting": ("cluster", "containers_starting"),
    "pressure_mean": ("cluster", "pressure_mean"),
    "pressure_max": ("cluster", "pressure_max"),
    "arrival_rps": ("traffic", "arrival_rps"),
    "throughput_rps": ("traffic", "throughput_rps"),
    "assigned_players": ("decision", "assigned_players"),
    "near_tie_player_ratio": ("decision", "near_tie_player_ratio"),
    "cross_node_placement_ratio": ("network", "cross_node_placement_ratio"),
    "final_welfare": ("social", "final_welfare"),
    "empirical_gap": ("social", "empirical_gap"),
    "reference_below_current": ("social", "reference_below_current"),
    "selected_path_inner_rounds": (
        "operational_equilibrium_selection",
        "selected_path_inner_rounds",
    ),
    "solver_inner_rounds": ("solver", "inner_rounds"),
    "solver_outer_rounds": ("solver", "outer_rounds"),
    "inner_limit_hit": ("solver", "inner_limit_hit"),
    "outer_limit_hit": ("solver", "outer_limit_hit"),
}

DECISION_SHARE_NUMERATORS = {
    "running_warm_available_share": "running_warm_available_players",
    "selected_running_warm_share": "selected_running_warm_players",
    "selected_starting_container_share": "selected_starting_container_players",
    "selected_cold_or_nonrunning_share": "selected_cold_or_nonrunning_players",
}

PAIR_SCENE_FIELDS = (
    "completion_ratio",
    "queue_area_per_arrival",
    "starting_container_frames_per_arrival",
    "ready_unscheduled_tasks_mean",
    "running_containers_mean",
    "node_cpu_utilization_mean_mean",
    "cross_node_placement_ratio_active_mean",
)

ROOT_ASSOCIATION_SPECS = (
    (
        "throughput_contribution_vs_completion_ratio",
        "delta_completion_ratio",
        "throughput_contribution",
        "throughput_contribution",
    ),
    (
        "throughput_contribution_vs_queue_area_per_arrival",
        "delta_queue_area_per_arrival",
        "throughput_contribution",
        "throughput_contribution",
    ),
    (
        "throughput_contribution_vs_ready_unscheduled_mean",
        "delta_ready_unscheduled_tasks_mean",
        "throughput_contribution",
        "throughput_contribution",
    ),
    (
        "latency_contribution_vs_queue_area_per_arrival",
        "delta_queue_area_per_arrival",
        "latency_contribution",
        "latency_contribution",
    ),
    (
        "latency_contribution_vs_starting_container_occupancy",
        "delta_starting_container_frames_per_arrival",
        "latency_contribution",
        "latency_contribution",
    ),
    (
        "latency_contribution_vs_selected_cold_share",
        "candidate_selected_cold_or_nonrunning_share",
        "latency_contribution",
        "latency_contribution",
    ),
    (
        "cost_contribution_vs_starting_container_occupancy",
        "delta_starting_container_frames_per_arrival",
        "cost_contribution",
        "cost_contribution",
    ),
    (
        "cost_contribution_vs_running_containers",
        "delta_running_containers_mean",
        "cost_contribution",
        "cost_contribution",
    ),
    (
        "cost_contribution_vs_cpu_utilization",
        "delta_node_cpu_utilization_mean_mean",
        "cost_contribution",
        "cost_contribution",
    ),
    (
        "log_qpr_change_vs_intervention_share",
        "intervention_active_window_share",
        "delta_log_qpr",
        "qpr_total",
    ),
)

BROAD_ASSOCIATION_OUTCOMES = (
    "delta_throughput_requests_per_ms",
    "delta_qpr",
    "delta_latency_mean_ms",
    "delta_cost_per_completed_request",
    "delta_completion_ratio",
    "delta_queue_area_per_arrival",
    "delta_starting_container_frames_per_arrival",
)

TOPOLOGY_FIELDS = (
    "delta_log_throughput",
    "throughput_contribution",
    "latency_contribution",
    "cost_contribution",
    "delta_log_qpr",
    "delta_completion_ratio",
    "delta_queue_area_per_arrival",
    "delta_starting_container_frames_per_arrival",
    "delta_cross_node_placement_ratio_active_mean",
)


def _required_number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0.0):
        raise ProtocolValidationError(f"{label} is not finite/positive")
    return number


def _optional_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _nested(row: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = row
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _mean_optional(values: Iterable[Any]) -> tuple[float | None, int]:
    finite = [value for item in values if (value := _optional_number(item)) is not None]
    return (fmean(finite), len(finite)) if finite else (None, 0)


def _t_summary(values: Sequence[float]) -> dict[str, Any]:
    sample = [_required_number(value, "t-summary value") for value in values]
    if len(sample) < 2:
        raise ProtocolValidationError("t summary requires at least two values")
    mean = fmean(sample)
    sd = stdev(sample)
    half_width = (
        float(scipy_stats.t.ppf(0.975, len(sample) - 1)) * sd / math.sqrt(len(sample))
    )
    epsilon = 1e-15
    return {
        "n": len(sample),
        "mean": mean,
        "sample_sd": sd,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "positive": sum(value > epsilon for value in sample),
        "neutral": sum(abs(value) <= epsilon for value in sample),
        "negative": sum(value < -epsilon for value in sample),
        "values": sample,
    }


def _validate_selection(selection_path: Path) -> dict[str, Any]:
    selection_path = selection_path.resolve()
    if file_hash(selection_path) != EXPECTED_SELECTION_FILE_SHA256:
        raise ProtocolValidationError("unexpected G3-E0 selection file hash")
    selection = read_json(selection_path)
    if not isinstance(selection, dict):
        raise ProtocolValidationError("G3-E0 selection is not an object")
    stored_hash = selection.get("document_sha256")
    payload = dict(selection)
    payload.pop("document_sha256", None)
    if (
        stored_hash != EXPECTED_SELECTION_DOCUMENT_SHA256
        or object_hash(payload) != EXPECTED_SELECTION_DOCUMENT_SHA256
    ):
        raise ProtocolValidationError("G3-E0 selection document hash mismatch")
    if (
        selection.get("status") != "complete_g3_e0_development_gate_failed"
        or selection.get("run_count") != 135
        or selection.get("formal_confirmation_authorized") is not False
    ):
        raise ProtocolValidationError(
            "G3-E0 selection does not bind the failed product"
        )
    return selection


def _frame_summary(
    frames: Sequence[Mapping[str, Any]], arrivals: float
) -> dict[str, Any]:
    if not frames:
        raise ProtocolValidationError("run lacks frame records")
    row: dict[str, Any] = {}
    for field in FRAME_FIELDS:
        values = [
            _required_number(frame.get(field), f"frame.{field}") for frame in frames
        ]
        row[f"{field}_mean"] = fmean(values)
        row[f"{field}_max"] = max(values)
    starting_area = sum(
        _required_number(frame.get("starting_containers"), "frame.starting_containers")
        for frame in frames
    )
    row["starting_container_frames_per_arrival"] = starting_area / arrivals
    return row


def _window_value(window: Mapping[str, Any], field: str) -> float | None:
    if field in DECISION_SHARE_NUMERATORS:
        assigned = _optional_number(_nested(window, ("decision", "assigned_players")))
        numerator = _optional_number(
            _nested(window, ("decision", DECISION_SHARE_NUMERATORS[field]))
        )
        if assigned is None or numerator is None or assigned <= 0.0:
            return None
        return numerator / assigned
    value = _nested(window, WINDOW_FIELDS[field])
    return _optional_number(value)


def _nash_window_summary(
    artifacts: RunArtifacts, candidate: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError(
            f"NSESche run {artifacts.run_id} lacks window events"
        )
    active = [
        window
        for window in windows
        if _required_number(
            _nested(window, ("decision", "assigned_players")),
            "decision.assigned_players",
        )
        > 0.0
    ]
    if not active:
        raise ProtocolValidationError(
            f"NSESche run {artifacts.run_id} has no active windows"
        )

    def is_intervention(window: Mapping[str, Any]) -> bool:
        selected = _nested(
            window,
            ("operational_equilibrium_selection", "selected_non_o0_rounds"),
        )
        if candidate == CONTROL:
            return False
        return _required_number(selected, "selected_non_o0_rounds") > 0.0

    intervention = [window for window in active if is_intervention(window)]
    nonintervention = [window for window in active if not is_intervention(window)]
    summary: dict[str, Any] = {
        "scheduler_window_count": len(windows),
        "active_window_count": len(active),
        "intervention_window_count": len(intervention),
        "intervention_active_window_share": len(intervention) / len(active),
    }
    rounds = 0.0
    non_o0_rounds = 0.0
    for window in active:
        selection = window.get("operational_equilibrium_selection")
        if candidate == CONTROL:
            continue
        if not isinstance(selection, Mapping):
            raise ProtocolValidationError("candidate active window lacks E0 selection")
        rounds += _required_number(selection.get("rounds"), "selection.rounds")
        non_o0_rounds += _required_number(
            selection.get("selected_non_o0_rounds"), "selection.selected_non_o0_rounds"
        )
    summary["selected_non_o0_round_share"] = (
        non_o0_rounds / rounds if rounds > 0.0 else 0.0
    )

    all_fields = tuple(WINDOW_FIELDS) + tuple(DECISION_SHARE_NUMERATORS)
    contrasts: list[dict[str, Any]] = []
    for field in all_fields:
        active_mean, active_n = _mean_optional(
            _window_value(window, field) for window in active
        )
        intervention_mean, intervention_n = _mean_optional(
            _window_value(window, field) for window in intervention
        )
        nonintervention_mean, nonintervention_n = _mean_optional(
            _window_value(window, field) for window in nonintervention
        )
        summary[f"{field}_active_mean"] = active_mean
        summary[f"{field}_active_n"] = active_n
        contrasts.append(
            {
                "run_id": artifacts.run_id,
                "seed": artifacts.seed,
                "candidate": candidate,
                "load": artifacts.spec["workload"]["request_freq"],
                "topology": artifacts.spec["cluster"]["topology"],
                "field": field,
                "intervention_mean": intervention_mean,
                "intervention_n": intervention_n,
                "nonintervention_mean": nonintervention_mean,
                "nonintervention_n": nonintervention_n,
                "intervention_minus_nonintervention": (
                    intervention_mean - nonintervention_mean
                    if intervention_mean is not None
                    and nonintervention_mean is not None
                    else None
                ),
            }
        )
    return summary, contrasts


def _summarize_run(
    run: Mapping[str, Any], artifacts: RunArtifacts
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = artifacts.summary
    if (
        summary.get("schema") != "NSE_SUMMARY_V1"
        or summary.get("run_id") != run.get("run_id")
        or summary.get("run_complete") is not True
    ):
        raise ProtocolValidationError(f"invalid summary for {run.get('run_id')}")
    throughput, qpr, latency, cost = _screen_metrics(dict(summary))
    fixed = summary.get("fixed_observation_window")
    drained = summary.get("drained_arrival_cohort")
    if not isinstance(fixed, Mapping) or not isinstance(drained, Mapping):
        raise ProtocolValidationError("summary lacks fixed/drained scopes")
    arrivals = _required_number(
        summary.get("arrivals"), "summary.arrivals", positive=True
    )
    method = str(run.get("method"))
    metadata = run.get("metadata")
    candidate = (
        str(metadata.get("m1_operational_candidate"))
        if method == "sche_nash" and isinstance(metadata, Mapping)
        else None
    )
    row: dict[str, Any] = {
        "run_id": str(run["run_id"]),
        "seed": str(run["seed"]),
        "method": method,
        "candidate": candidate,
        "load": str(run["workload"]["request_freq"]),
        "topology": str(run["cluster"]["topology"]),
        "throughput_requests_per_ms": throughput,
        "qpr": qpr,
        "latency_mean_ms": latency,
        "cost_per_completed_request": cost,
        "log_throughput": math.log(throughput),
        "log_qpr": math.log(qpr),
        "log_latency": math.log(latency),
        "log_cost": math.log(cost),
        "arrivals": arrivals,
        "completed": _required_number(summary.get("completed"), "summary.completed"),
        "completion_ratio": _required_number(
            summary.get("completion_ratio"), "summary.completion_ratio"
        ),
        "fixed_arrivals": _required_number(fixed.get("arrivals"), "fixed.arrivals"),
        "fixed_completed": _required_number(fixed.get("completed"), "fixed.completed"),
        "fixed_completion_ratio": _required_number(
            fixed.get("completion_ratio"), "fixed.completion_ratio"
        ),
        "drained_arrivals": _required_number(
            drained.get("arrivals"), "drained.arrivals"
        ),
        "drained_completed": _required_number(
            drained.get("completed"), "drained.completed"
        ),
        "drained_completion_ratio": _required_number(
            drained.get("completion_ratio"), "drained.completion_ratio"
        ),
        "drained_latency_p95_ms": _required_number(
            _nested(drained, ("latency_ms", "p95")), "drained.latency.p95"
        ),
        "drained_latency_p99_ms": _required_number(
            _nested(drained, ("latency_ms", "p99")), "drained.latency.p99"
        ),
        "drain_duration_after_arrivals_ms": _required_number(
            drained.get("drain_duration_after_arrivals_ms"), "drained.drain_duration"
        ),
        "simulator_internal_cost_total": _required_number(
            summary.get("simulator_internal_cost_total"), "summary.cost_total"
        ),
        "placement_rejections": _required_number(
            summary.get("placement_rejections"), "summary.placement_rejections"
        ),
        "admission_reject": _required_number(
            summary.get("admission_reject"), "summary.admission_reject"
        ),
        "admission_drop": _required_number(
            summary.get("admission_drop"), "summary.admission_drop"
        ),
        "timeout": _required_number(summary.get("timeout"), "summary.timeout"),
        "queue_peak": _required_number(summary.get("queue_peak"), "summary.queue_peak"),
        "queue_area_per_arrival": _required_number(
            summary.get("queue_area_request_frames"), "summary.queue_area"
        )
        / arrivals,
    }
    row.update(_frame_summary(artifacts.frames, arrivals))
    contrasts: list[dict[str, Any]] = []
    if method == "sche_nash":
        if candidate not in G3_E0_OPERATIONAL_CANDIDATES:
            raise ProtocolValidationError(f"unexpected NSESche candidate {candidate}")
        nash_summary, contrasts = _nash_window_summary(artifacts, str(candidate))
        row.update(nash_summary)
    return row, contrasts


def _difference(left: Any, right: Any, label: str) -> float:
    return _required_number(left, f"left {label}") - _required_number(
        right, f"right {label}"
    )


def _pair_row(
    treatment: Mapping[str, Any], control: Mapping[str, Any], comparison_type: str
) -> dict[str, Any]:
    for key in ("seed", "load", "topology"):
        if treatment.get(key) != control.get(key):
            raise ProtocolValidationError(f"broken {comparison_type} pair on {key}")
    delta_log_t = _difference(
        treatment["log_throughput"], control["log_throughput"], "log T"
    )
    delta_log_l = _difference(treatment["log_latency"], control["log_latency"], "log L")
    delta_log_c = _difference(treatment["log_cost"], control["log_cost"], "log C")
    delta_log_qpr = _difference(treatment["log_qpr"], control["log_qpr"], "log QPR")
    row: dict[str, Any] = {
        "comparison_type": comparison_type,
        "treatment_run_id": treatment["run_id"],
        "control_run_id": control["run_id"],
        "seed": treatment["seed"],
        "load": treatment["load"],
        "topology": treatment["topology"],
        "treatment": treatment.get("candidate") or treatment.get("method"),
        "delta_log_throughput": delta_log_t,
        "throughput_contribution": delta_log_t,
        "latency_contribution": -delta_log_l,
        "cost_contribution": -delta_log_c,
        "delta_log_qpr": delta_log_qpr,
        "identity_residual": delta_log_qpr - (delta_log_t - delta_log_l - delta_log_c),
    }
    if abs(row["identity_residual"]) > 1e-12:
        raise ProtocolValidationError("QPR log-factorization identity failed")
    for field in (
        "throughput_requests_per_ms",
        "qpr",
        "latency_mean_ms",
        "cost_per_completed_request",
        *PAIR_SCENE_FIELDS,
    ):
        left = treatment.get(field)
        right = control.get(field)
        row[f"delta_{field}"] = (
            _difference(left, right, field)
            if left is not None and right is not None
            else None
        )
        row[f"ratio_{field}"] = (
            _required_number(left, f"left {field}")
            / _required_number(right, f"right {field}", positive=True)
            if left is not None and right is not None
            else None
        )
    row["intervention_active_window_share"] = treatment.get(
        "intervention_active_window_share"
    )
    row["candidate_selected_cold_or_nonrunning_share"] = treatment.get(
        "selected_cold_or_nonrunning_share_active_mean"
    )
    return row


def _component_aggregate(
    treatment: str, load: str, topology: str, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    group = [
        row
        for row in rows
        if row["treatment"] == treatment
        and row["load"] == load
        and row["topology"] == topology
    ]
    if len(group) != 5 or {row["seed"] for row in group} != set(
        G3_E0_OPERATIONAL_SEEDS
    ):
        raise ProtocolValidationError(
            f"incomplete component group {treatment}/{load}/{topology}"
        )
    summaries = {
        field: _t_summary([_required_number(row[field], field) for row in group])
        for field in (*COMPONENTS, "delta_log_qpr")
    }
    component_means = {field: summaries[field]["mean"] for field in COMPONENTS}
    minimum = min(component_means.values())
    maximum = max(component_means.values())
    return {
        "treatment": treatment,
        "load": load,
        "topology": topology,
        "components": summaries,
        "most_adverse_components": sorted(
            field
            for field, value in component_means.items()
            if abs(value - minimum) <= 1e-12
        ),
        "most_favorable_components": sorted(
            field
            for field, value in component_means.items()
            if abs(value - maximum) <= 1e-12
        ),
    }


def _spearman_row(
    rows: Sequence[Mapping[str, Any]], x_field: str, y_field: str
) -> dict[str, Any]:
    pairs = [
        (
            _optional_number(row.get(x_field)),
            _optional_number(row.get(y_field)),
            str(row["seed"]),
        )
        for row in rows
    ]
    pairs = [(x, y, seed) for x, y, seed in pairs if x is not None and y is not None]
    if len(pairs) < 3:
        return {
            "x_field": x_field,
            "y_field": y_field,
            "n": len(pairs),
            "rho": None,
            "nominal_p": None,
            "status": "insufficient_pairs",
            "leave_one_seed_out": [],
        }
    x = [pair[0] for pair in pairs]
    y = [pair[1] for pair in pairs]
    if len(set(x)) == 1 or len(set(y)) == 1:
        return {
            "x_field": x_field,
            "y_field": y_field,
            "n": len(pairs),
            "rho": None,
            "nominal_p": None,
            "status": "constant_input",
            "leave_one_seed_out": [],
        }
    result = scipy_stats.spearmanr(x, y)
    rho = float(result.statistic)
    p_value = float(result.pvalue)
    leave_one_out = []
    for seed in G3_E0_OPERATIONAL_SEEDS:
        kept = [(left, right) for left, right, item_seed in pairs if item_seed != seed]
        if (
            len(kept) < 3
            or len({item[0] for item in kept}) == 1
            or len({item[1] for item in kept}) == 1
        ):
            loo_rho = None
        else:
            loo_rho = float(
                scipy_stats.spearmanr(
                    [item[0] for item in kept], [item[1] for item in kept]
                ).statistic
            )
        leave_one_out.append({"omitted_seed": seed, "rho": loo_rho, "n": len(kept)})
    return {
        "x_field": x_field,
        "y_field": y_field,
        "n": len(pairs),
        "rho": rho,
        "nominal_p": p_value,
        "status": "ok",
        "leave_one_seed_out": leave_one_out,
    }


def _adjust_family(rows: list[dict[str, Any]], *, alpha: float = 0.10) -> None:
    p_values = [
        float(row["nominal_p"]) if row.get("nominal_p") is not None else 1.0
        for row in rows
    ]
    adjusted, rejected = holm_adjust(p_values, alpha=alpha)
    for row, adjusted_p, decision in zip(rows, adjusted, rejected):
        row["holm_adjusted_p"] = adjusted_p
        row["holm_reject_at_0_10"] = decision


def _association_families(
    pair_rows: Sequence[Mapping[str, Any]], candidate: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    group = [row for row in pair_rows if row["treatment"] == candidate]
    if len(group) != 30:
        raise ProtocolValidationError(f"candidate {candidate} lacks 30 paired rows")
    root_rows: list[dict[str, Any]] = []
    for name, x_field, y_field, component in ROOT_ASSOCIATION_SPECS:
        row = _spearman_row(group, x_field, y_field)
        row.update(
            {
                "candidate": candidate,
                "family": "root_cause_prespecified_10",
                "association": name,
                "component": component,
            }
        )
        root_rows.append(row)
    _adjust_family(root_rows)

    broad_rows: list[dict[str, Any]] = []
    for outcome in BROAD_ASSOCIATION_OUTCOMES:
        row = _spearman_row(group, "intervention_active_window_share", outcome)
        row.update(
            {
                "candidate": candidate,
                "family": "exploratory_intervention_share_7",
                "association": f"intervention_share_vs_{outcome}",
                "component": None,
            }
        )
        broad_rows.append(row)
    _adjust_family(broad_rows)
    return root_rows, broad_rows


def _topology_rows(
    candidate_pairs: Sequence[Mapping[str, Any]], candidate: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed = {
        (row["load"], row["topology"], row["seed"]): row
        for row in candidate_pairs
        if row["treatment"] == candidate
    }
    rows: list[dict[str, Any]] = []
    aggregates: list[dict[str, Any]] = []
    for load in G3_E0_OPERATIONAL_LOADS:
        for seed in G3_E0_OPERATIONAL_SEEDS:
            homogeneous = indexed.get((load, "homogeneous", seed))
            heterogeneous = indexed.get((load, "heterogeneous", seed))
            if homogeneous is None or heterogeneous is None:
                raise ProtocolValidationError(
                    f"missing topology pair {candidate}/{load}/{seed}"
                )
            row: dict[str, Any] = {"candidate": candidate, "load": load, "seed": seed}
            for field in TOPOLOGY_FIELDS:
                left = heterogeneous.get(field)
                right = homogeneous.get(field)
                row[f"did_{field}"] = (
                    _difference(left, right, field)
                    if left is not None and right is not None
                    else None
                )
            rows.append(row)
        load_rows = [row for row in rows if row["load"] == load]
        aggregates.append(
            {
                "candidate": candidate,
                "load": load,
                "fields": {
                    field: _t_summary(
                        [
                            _required_number(row[f"did_{field}"], field)
                            for row in load_rows
                        ]
                    )
                    for field in TOPOLOGY_FIELDS
                },
            }
        )
    return rows, aggregates


def _loo_sign_stable(row: Mapping[str, Any]) -> bool:
    rho = _optional_number(row.get("rho"))
    values = [
        _optional_number(item.get("rho"))
        for item in row.get("leave_one_seed_out", [])
        if isinstance(item, Mapping)
    ]
    if rho is None or len(values) != 5 or any(value is None for value in values):
        return False
    return all(value * rho > 0.0 for value in values if value is not None)


def _root_decision(
    candidate_aggregates: Sequence[Mapping[str, Any]],
    baseline_aggregates: Sequence[Mapping[str, Any]],
    topology_aggregates: Sequence[Mapping[str, Any]],
    root_associations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    high_hom = {
        row["treatment"]: row
        for row in candidate_aggregates
        if row["load"] == "high" and row["topology"] == "homogeneous"
    }
    high_het = {
        row["treatment"]: row
        for row in candidate_aggregates
        if row["load"] == "high" and row["topology"] == "heterogeneous"
    }
    adverse_lists = [
        high_hom[candidate]["most_adverse_components"]
        for candidate in ACTIVE_CANDIDATES
    ]
    common = set(adverse_lists[0]).intersection(*map(set, adverse_lists[1:]))
    opposite = []
    for component in sorted(common):
        if all(
            high_hom[candidate]["components"][component]["mean"] < 0.0
            and high_het[candidate]["components"][component]["mean"] > 0.0
            for candidate in ACTIVE_CANDIDATES
        ):
            opposite.append(component)
    criterion_1 = len(opposite) == 1
    component = opposite[0] if criterion_1 else None

    topology_rows = {
        (row["candidate"], row["load"]): row for row in topology_aggregates
    }
    criterion_2 = bool(
        component
        and all(
            topology_rows[(candidate, "high")]["fields"][component]["positive"] >= 4
            for candidate in ACTIVE_CANDIDATES
        )
    )
    qualifying_associations = [
        row
        for row in root_associations
        if component is not None
        and row.get("component") == component
        and row.get("status") == "ok"
        and abs(_required_number(row.get("rho"), "association rho")) >= 0.50
        and _required_number(row.get("holm_adjusted_p"), "adjusted p") < 0.10
        and _loo_sign_stable(row)
    ]
    criterion_3 = bool(qualifying_associations)

    advanced_matching = [
        row["treatment"]
        for row in baseline_aggregates
        if str(row["treatment"]).lower() in ADVANCED_BASELINES
        and component is not None
        and component in row["most_favorable_components"]
    ]
    criterion_4 = len(advanced_matching) >= 3
    source_mapping = (
        {
            "single_operational_mechanism": "state-conditioned operational equilibrium selection",
            "source_file": "serverless_sim/src/sche/sche_nash.rs",
            "source_symbols": [
                "select_counterfactual_envelope_outcome",
                "operational_envelope_selection",
            ],
            "outside_equations_1_20": True,
            "mapped_associations": [
                row["association"] for row in qualifying_associations
            ],
        }
        if criterion_3
        else None
    )
    criterion_5 = source_mapping is not None
    supported = all((criterion_1, criterion_2, criterion_3, criterion_4, criterion_5))
    return {
        "status": (
            "complete_single_actionable_cause_supported"
            if supported
            else "complete_no_single_actionable_cause"
        ),
        "diagnostically_supported": supported,
        "selected_component": component,
        "criteria": {
            "common_adverse_component_with_opposite_high_topology_sign": criterion_1,
            "high_topology_contrast_positive_at_least_4_of_5_both_candidates": criterion_2,
            "prespecified_holm_stable_state_association": criterion_3,
            "same_advanced_baseline_advantage_component_at_least_3": criterion_4,
            "single_source_mechanism_outside_equations": criterion_5,
        },
        "high_homogeneous_adverse_components": dict(
            zip(ACTIVE_CANDIDATES, adverse_lists)
        ),
        "opposite_sign_components": opposite,
        "qualifying_associations": qualifying_associations,
        "advanced_baselines_matching_component": advanced_matching,
        "source_mapping": source_mapping,
        "new_candidate_authorized": False,
        "new_sampling_authorized": False,
    }


def analyze(selection_path: Path, canonical_root: Path) -> dict[str, Any]:
    selection = _validate_selection(selection_path)
    manifest_info = selection.get("development_manifest")
    if not isinstance(manifest_info, Mapping):
        raise ProtocolValidationError("selection lacks development manifest")
    manifest_path = Path(str(manifest_info.get("path", ""))).resolve()
    if file_hash(manifest_path) != manifest_info.get("file_sha256"):
        raise ProtocolValidationError("ready manifest file hash mismatch")
    manifest = load_and_validate_manifest(manifest_path)
    if manifest.get("manifest_hash") != manifest_info.get("manifest_hash"):
        raise ProtocolValidationError("ready manifest document hash mismatch")
    runs = manifest.get("runs")
    if not isinstance(runs, list) or len(runs) != 135:
        raise ProtocolValidationError("diagnosis requires exactly 135 runs")
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )

    run_rows: list[dict[str, Any]] = []
    intervention_contrasts: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for run in runs:
        artifacts = load_run_artifacts(
            run,
            canonical_root,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        row, contrasts = _summarize_run(run, artifacts)
        run_rows.append(row)
        if row["candidate"] in ACTIVE_CANDIDATES:
            intervention_contrasts.extend(contrasts)
        receipts.append(
            {
                "run_id": run["run_id"],
                "manifest_sha256": file_hash(artifacts.run_directory / "manifest.json"),
                "qc_report_sha256": file_hash(
                    artifacts.run_directory / "qc_report.json"
                ),
                "summary_sha256": file_hash(
                    artifacts.run_directory
                    / "reviewer_records"
                    / str(run["run_id"])
                    / "summary.json"
                ),
                "nse_event_source": artifacts.nse_event_source,
            }
        )

    controls = {
        (row["seed"], row["load"], row["topology"]): row
        for row in run_rows
        if row.get("candidate") == CONTROL
    }
    if len(controls) != 30:
        raise ProtocolValidationError("control matrix is incomplete")
    candidate_pairs = []
    for row in run_rows:
        if row.get("candidate") not in ACTIVE_CANDIDATES:
            continue
        key = (row["seed"], row["load"], row["topology"])
        if key not in controls:
            raise ProtocolValidationError(f"missing control pair {key}")
        candidate_pairs.append(_pair_row(row, controls[key], "candidate_vs_c0"))
    if len(candidate_pairs) != 60:
        raise ProtocolValidationError("candidate pair matrix is incomplete")

    low_controls = {
        row["seed"]: row
        for row in run_rows
        if row.get("candidate") == CONTROL
        and row["load"] == "low"
        and row["topology"] == "homogeneous"
    }
    baseline_pairs = []
    for row in run_rows:
        if row["method"] not in G3_E0_OPERATIONAL_BASELINES:
            continue
        if row["seed"] not in low_controls:
            raise ProtocolValidationError(f"missing low control for {row['seed']}")
        baseline_pairs.append(
            _pair_row(row, low_controls[row["seed"]], "baseline_vs_c0")
        )
    if len(baseline_pairs) != 45:
        raise ProtocolValidationError("baseline pair matrix is incomplete")

    candidate_aggregates = [
        _component_aggregate(candidate, load, topology, candidate_pairs)
        for candidate in ACTIVE_CANDIDATES
        for load in G3_E0_OPERATIONAL_LOADS
        for topology in G3_E0_OPERATIONAL_TOPOLOGIES
    ]
    baseline_aggregates = [
        _component_aggregate(method, "low", "homogeneous", baseline_pairs)
        for method in G3_E0_OPERATIONAL_BASELINES
    ]

    root_associations: list[dict[str, Any]] = []
    broad_associations: list[dict[str, Any]] = []
    topology_rows: list[dict[str, Any]] = []
    topology_aggregates: list[dict[str, Any]] = []
    for candidate in ACTIVE_CANDIDATES:
        root, broad = _association_families(candidate_pairs, candidate)
        root_associations.extend(root)
        broad_associations.extend(broad)
        per_seed, aggregate = _topology_rows(candidate_pairs, candidate)
        topology_rows.extend(per_seed)
        topology_aggregates.extend(aggregate)

    decision = _root_decision(
        candidate_aggregates,
        baseline_aggregates,
        topology_aggregates,
        root_associations,
    )
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": decision["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "selection_artifact": {
            "path": str(selection_path.resolve()),
            "file_sha256": EXPECTED_SELECTION_FILE_SHA256,
            "document_sha256": EXPECTED_SELECTION_DOCUMENT_SHA256,
        },
        "development_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "definitions": {
            "qpr": "throughput_requests_per_ms/(drained_mean_latency_ms*simulator_internal_cost_per_completed_request)",
            "qpr_log_factorization": "delta_log_T-delta_log_L-delta_log_C",
            "starting_container_proxy": "sum_frame_starting_containers/arrivals; not measured cold-start latency or count",
            "queue_exposure_proxy": "queue_area_request_frames/arrivals; not request-level waiting time",
            "independent_unit": "run/seed",
            "all_valid_runs_retained": True,
        },
        "run_scene_metrics": run_rows,
        "candidate_qpr_pairs": candidate_pairs,
        "baseline_qpr_pairs": baseline_pairs,
        "candidate_component_aggregates": candidate_aggregates,
        "baseline_component_aggregates": baseline_aggregates,
        "intervention_state_contrasts": intervention_contrasts,
        "root_associations": root_associations,
        "exploratory_intervention_associations": broad_associations,
        "topology_difference_in_differences": topology_rows,
        "topology_aggregates": topology_aggregates,
        "root_cause_decision": decision,
        "artifact_receipts": receipts,
        "run_count": len(run_rows),
        "candidate_pair_count": len(candidate_pairs),
        "baseline_pair_count": len(baseline_pairs),
        "new_candidate_authorized": False,
        "new_sampling_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def _write_csv_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ProtocolValidationError(f"refusing to write empty CSV {path.name}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})
    temporary.replace(path)


def write_outputs(report: Mapping[str, Any], output_dir: Path) -> list[Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "g3_postfail_diagnosis.json": None,
        "g3_postfail_qpr_pairs.csv": [
            *report["candidate_qpr_pairs"],
            *report["baseline_qpr_pairs"],
        ],
        "g3_postfail_run_scene_metrics.csv": report["run_scene_metrics"],
        "g3_postfail_intervention_state_contrasts.csv": report[
            "intervention_state_contrasts"
        ],
        "g3_postfail_associations.csv": [
            *report["root_associations"],
            *report["exploratory_intervention_associations"],
        ],
        "g3_postfail_topology_differences.csv": report[
            "topology_difference_in_differences"
        ],
    }
    paths = [output_dir / name for name in outputs]
    existing = [path for path in paths if path.exists()]
    if existing:
        raise FileExistsError(f"diagnosis output already exists: {existing[0]}")
    json_path = paths[0]
    write_json_atomic(json_path, dict(report))
    try:
        for path in paths[1:]:
            _write_csv_atomic(path, outputs[path.name])
    except Exception:
        for path in paths:
            if path.exists():
                path.unlink()
            temporary = path.with_suffix(path.suffix + ".tmp")
            if temporary.exists():
                temporary.unlink()
        raise
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.selection, args.canonical_root)
    paths = write_outputs(report, args.output_dir)
    print(
        json.dumps(
            {
                "status": report["status"],
                "document_sha256": report["document_sha256"],
                "run_count": report["run_count"],
                "outputs": [str(path) for path in paths],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
