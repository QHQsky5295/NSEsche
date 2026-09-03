"""Analyze the preregistered G3 strict-PNE order counterfactual.

Selection deliberately ignores observed throughput, QPR, latency, and cost.
Those online quantities are used only to prove that the instrumented live C0
path exactly replays each retained source run.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .formal_inputs import validate_canonical_run
from ..protocol.g3_order_counterfactual import (
    G3_COUNTERFACTUAL_STREAM_SCHEMA,
    G3_ENVELOPE,
    G3_ORDERS,
    G3_ORDER_COUNTERFACTUAL_SCHEMA,
    G3_STRATA,
)
from ..protocol.schema import (
    G3_ORDER_COUNTERFACTUAL_MARKER,
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


ANALYSIS_SCHEMA = "NSE_G3_ORDER_COUNTERFACTUAL_ANALYSIS_V1"
PARITY_FLOAT_REL_TOLERANCE = 1e-6
ASSIGNMENT_DIFFERENCE_MIN_FRACTION = 0.01
WELFARE_MAX_STRATUM_REGRESSION = 0.001
PROXY_MAX_STRATUM_REGRESSION = 0.01
NONWORSE_MIN_STRATA = 5
DIFFERENT_MIN_STRATA = 4
ORDER_TO_MECHANISM = {
    "ready_order": "O0",
    "reverse_ready_order": "O1",
    "service_scarcity_first": "O2",
    "capacity_scarcity_first": "O3",
    "resource_impact_first": "O4",
}
MECHANISMS = ("O0", "O1", "O2", "O3", "O4", "E0")
ALTERNATIVES = ("O1", "O2", "O3", "O4", "E0")
SIMPLICITY_ORDER = ("O2", "O3", "O4", "O1", "E0")
SUMMARY_PARITY_PATHS = (
    ("arrivals",),
    ("completed",),
    ("completion_ratio",),
    ("final_frame",),
    ("frames_recorded",),
    ("observation_time_ms",),
    ("throughput_requests_per_second",),
    ("latency_ms", "mean"),
    ("latency_ms", "p50"),
    ("latency_ms", "p95"),
    ("latency_ms", "p99"),
    ("simulator_internal_cost_total",),
    ("simulator_internal_cost_per_completed_request",),
    ("queue_area_request_frames",),
    ("queue_peak",),
    ("placement_rejections",),
    ("admission_drop",),
    ("admission_reject",),
    ("timeout",),
    ("fixed_observation_window", "arrivals"),
    ("fixed_observation_window", "completed"),
    ("fixed_observation_window", "completion_ratio"),
    ("fixed_observation_window", "throughput_requests_per_second"),
    ("drained_arrival_cohort", "arrivals"),
    ("drained_arrival_cohort", "completed"),
    ("drained_arrival_cohort", "completion_ratio"),
    ("drained_arrival_cohort", "latency_ms", "mean"),
    ("drained_arrival_cohort", "latency_ms", "p50"),
    ("drained_arrival_cohort", "latency_ms", "p95"),
    ("drained_arrival_cohort", "latency_ms", "p99"),
)
WINDOW_EXACT_PARITY_PATHS = (
    ("window",),
    ("frame",),
    ("decision", "request_function_players"),
    ("decision", "assigned_players"),
    ("decision", "assignment_hash"),
    ("decision", "commands_prepared"),
    ("decision", "commands_sent"),
    ("decision", "scale_ups_prepared"),
    ("decision", "scale_ups_sent"),
    ("solver", "termination"),
)


def _nested(value: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _finite(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def _close(left: Any, right: Any, rel: float = PARITY_FLOAT_REL_TOLERANCE) -> bool:
    left_value = _finite(left)
    right_value = _finite(right)
    if left_value is None or right_value is None:
        return left == right
    return abs(left_value - right_value) <= rel * max(
        1.0, abs(left_value), abs(right_value)
    )


def _mean(values: Iterable[float]) -> float:
    materialized = [float(value) for value in values]
    if not materialized:
        raise ProtocolValidationError("cannot average an empty G3 metric")
    return statistics.fmean(materialized)


def _json_lines(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ProtocolValidationError(
                    f"G3 JSONL line is not an object: {path}:{line_number}"
                )
            yield value


def _windows(path: Path) -> list[dict[str, Any]]:
    windows = [event for event in _json_lines(path) if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError(f"G3 stream contains no windows: {path}")
    identities = [(item.get("window"), item.get("frame")) for item in windows]
    if len(identities) != len(set(identities)):
        raise ProtocolValidationError(f"G3 stream repeats a window identity: {path}")
    return windows


def _one(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.rglob(pattern))
    if len(matches) != 1:
        raise ProtocolValidationError(
            f"expected one {pattern} below {directory}, found {len(matches)}"
        )
    return matches[0]


def _artifact_path(binding: Mapping[str, Any], name: str) -> Path:
    artifact = binding.get(name)
    if not isinstance(artifact, Mapping):
        raise ProtocolValidationError(f"source artifact binding {name} is missing")
    path = Path(str(artifact.get("path", ""))).resolve()
    if not path.is_file() or file_hash(path) != artifact.get("sha256"):
        raise ProtocolValidationError(f"source artifact hash mismatch: {path}")
    return path


def _scientific_summary_parity(
    source: Mapping[str, Any], replay: Mapping[str, Any]
) -> list[str]:
    mismatches: list[str] = []
    for path in SUMMARY_PARITY_PATHS:
        source_value = _nested(source, path)
        replay_value = _nested(replay, path)
        if not _close(source_value, replay_value):
            mismatches.append(".".join(path))
    return mismatches


def _window_parity(source: Mapping[str, Any], replay: Mapping[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for path in WINDOW_EXACT_PARITY_PATHS:
        if _nested(source, path) != _nested(replay, path):
            mismatches.append(".".join(path))
    welfare_path = ("social", "final_assignment_baseline_welfare")
    if not _close(_nested(source, welfare_path), _nested(replay, welfare_path)):
        mismatches.append(".".join(welfare_path))
    return mismatches


def _outcome_is_bad(outcome: Mapping[str, Any]) -> bool:
    certificate = outcome.get("strict_pne")
    return not (
        outcome.get("complete") is True
        and outcome.get("stable") is True
        and outcome.get("inner_limit_hit") is False
        and int(outcome.get("oscillations", -1)) == 0
        and isinstance(certificate, Mapping)
        and certificate.get("certified") is True
    )


def _validate_counterfactual(
    run_id: str, window: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], list[str]]:
    errors: list[str] = []
    payload = window.get("order_counterfactual")
    if not isinstance(payload, Mapping):
        return {}, {}, ["missing_order_counterfactual"]
    if payload.get("schema") != G3_COUNTERFACTUAL_STREAM_SCHEMA:
        errors.append("counterfactual_schema")
    if payload.get("decision_feedback") is not False:
        errors.append("decision_feedback")
    outcomes_list = payload.get("outcomes")
    if not isinstance(outcomes_list, list):
        return {}, {}, [*errors, "outcomes_not_array"]
    outcomes = {
        str(outcome.get("order")): outcome
        for outcome in outcomes_list
        if isinstance(outcome, Mapping)
    }
    if len(outcomes_list) != len(G3_ORDERS) or set(outcomes) != set(G3_ORDERS):
        errors.append("order_set")
    common_candidate_hash = payload.get("candidate_set_hash")
    if any(
        outcome.get("candidate_set_hash") != common_candidate_hash
        for outcome in outcomes.values()
    ):
        errors.append("candidate_set_hash")
    if outcomes:
        player_counts = {outcome.get("players") for outcome in outcomes.values()}
        if len(player_counts) != 1:
            errors.append("player_count_invariance")
        o0 = outcomes.get("ready_order")
        if isinstance(o0, Mapping):
            players = int(o0.get("players", -1))
            live_hash = payload.get("live_first_inner_assignment_hash")
            match = payload.get("o0_first_inner_hash_match")
            if players > 0 and (live_hash is None or match is not True):
                errors.append("o0_first_inner_hash_parity")
            if players == 0 and not (live_hash is None and match is None):
                errors.append("o0_empty_first_inner_contract")
            certificate = o0.get("strict_pne", {})
            if o0.get("complete") is True and o0.get("stable") is True:
                if (
                    not isinstance(certificate, Mapping)
                    or certificate.get("certified") is not True
                    or certificate.get("violating_players") != 0
                    or certificate.get("missing_current_utility_players") != 0
                    or float(certificate.get("maximum_profitable_gain", 1.0)) > 1e-6
                ):
                    errors.append("o0_strict_pne_certificate")
        else:
            errors.append("missing_o0")
    envelope = payload.get("envelope")
    if not isinstance(envelope, Mapping):
        errors.append("missing_envelope")
        envelope = {}
    elif envelope.get("name") != G3_ENVELOPE:
        errors.append("envelope_name")
    else:
        selected_order = envelope.get("selected_order")
        selected = outcomes.get(str(selected_order))
        o0 = outcomes.get("ready_order")
        if selected is None or o0 is None:
            errors.append("envelope_selected_order")
        else:
            tolerance = _finite(envelope.get("welfare_tolerance"))
            selected_welfare = _finite(_nested(selected, ("welfare", "total")))
            o0_welfare = _finite(_nested(o0, ("welfare", "total")))
            if (
                tolerance is None
                or selected_welfare is None
                or o0_welfare is None
                or _outcome_is_bad(selected)
                or selected_welfare + tolerance < o0_welfare
                or envelope.get("selected_assignment_hash")
                != selected.get("assignment_hash")
                or envelope.get("selected_non_o0")
                is not (selected_order != "ready_order")
            ):
                errors.append("envelope_noninferiority")
    return outcomes, dict(envelope), [f"{run_id}:{item}" for item in errors]


def _metric_sum(outcome: Mapping[str, Any], field: str) -> float:
    value = _finite(outcome.get(field))
    if value is None:
        raise ProtocolValidationError(f"counterfactual outcome lacks finite {field}")
    return value


def _welfare_sum(outcome: Mapping[str, Any]) -> float:
    value = _finite(_nested(outcome, ("welfare", "total")))
    if value is None:
        raise ProtocolValidationError(
            "counterfactual outcome lacks finite welfare.total"
        )
    return value


def _per_player(total: float, players: int) -> float:
    return total / players if players > 0 else 0.0


def _run_aggregates(
    run: Mapping[str, Any],
    current_windows: Sequence[Mapping[str, Any]],
    raw_rows: list[dict[str, Any]],
    raw_stream_rows: list[dict[str, Any]],
    diagnostic_errors: list[str],
) -> list[dict[str, Any]]:
    run_id = str(run["run_id"])
    source_run_id = str(run["metadata"]["source_run_id"])
    stratum = str(run["metadata"]["g3_reporting_stratum"])
    accumulators = {
        mechanism: {
            "players": 0,
            "welfare": 0.0,
            "startup": 0.0,
            "finish": 0.0,
            "different": 0,
            "additional_bad": 0,
            "windows": 0,
            "envelope_violations": 0,
        }
        for mechanism in MECHANISMS
    }
    comparable_windows = 0
    for window in current_windows:
        raw_stream_rows.append(
            {
                "schema": G3_COUNTERFACTUAL_STREAM_SCHEMA,
                "run_id": run_id,
                "source_run_id": source_run_id,
                "stratum": stratum,
                "seed": run["seed"],
                "window": window.get("window"),
                "frame": window.get("frame"),
                "order_counterfactual": window.get("order_counterfactual"),
            }
        )
        outcomes, envelope, errors = _validate_counterfactual(run_id, window)
        diagnostic_errors.extend(errors)
        if set(outcomes) != set(G3_ORDERS):
            continue
        o0 = outcomes["ready_order"]
        if _outcome_is_bad(o0):
            continue
        comparable_windows += 1
        selected_order = str(envelope.get("selected_order"))
        envelope_outcome = outcomes.get(selected_order, o0)
        mechanism_outcomes = {
            **{
                ORDER_TO_MECHANISM[order]: outcome
                for order, outcome in outcomes.items()
            },
            "E0": envelope_outcome,
        }
        for mechanism, outcome in mechanism_outcomes.items():
            accumulator = accumulators[mechanism]
            players = int(outcome.get("assigned_players", 0))
            accumulator["players"] += players
            accumulator["welfare"] += _welfare_sum(outcome)
            accumulator["startup"] += _metric_sum(outcome, "startup_burden_sum")
            accumulator["finish"] += _metric_sum(outcome, "projected_finish_sum")
            accumulator["different"] += int(
                outcome.get("assignment_hash") != o0.get("assignment_hash")
            )
            accumulator["additional_bad"] += int(_outcome_is_bad(outcome))
            accumulator["windows"] += 1
            if mechanism == "E0":
                tolerance = float(envelope.get("welfare_tolerance", 0.0))
                accumulator["envelope_violations"] += int(
                    _outcome_is_bad(outcome)
                    or _welfare_sum(outcome) + tolerance < _welfare_sum(o0)
                )
            raw_rows.append(
                {
                    "run_id": run_id,
                    "source_run_id": source_run_id,
                    "stratum": stratum,
                    "seed": run["seed"],
                    "window": window.get("window"),
                    "frame": window.get("frame"),
                    "mechanism": mechanism,
                    "order": outcome.get("order"),
                    "players": outcome.get("players"),
                    "assigned_players": outcome.get("assigned_players"),
                    "complete": outcome.get("complete"),
                    "stable": outcome.get("stable"),
                    "inner_limit_hit": outcome.get("inner_limit_hit"),
                    "oscillations": outcome.get("oscillations"),
                    "termination": outcome.get("termination"),
                    "strict_pne_certified": _nested(
                        outcome, ("strict_pne", "certified")
                    ),
                    "strict_pne_violating_players": _nested(
                        outcome, ("strict_pne", "violating_players")
                    ),
                    "order_hash": outcome.get("order_hash"),
                    "candidate_set_hash": outcome.get("candidate_set_hash"),
                    "assignment_hash": outcome.get("assignment_hash"),
                    "different_from_o0": outcome.get("assignment_hash")
                    != o0.get("assignment_hash"),
                    "welfare_total": _welfare_sum(outcome),
                    "startup_burden_sum": outcome.get("startup_burden_sum"),
                    "projected_finish_sum": outcome.get("projected_finish_sum"),
                    "selected_running_warm_players": outcome.get(
                        "selected_running_warm_players"
                    ),
                    "selected_starting_container_players": outcome.get(
                        "selected_starting_container_players"
                    ),
                    "selected_cold_or_nonrunning_players": outcome.get(
                        "selected_cold_or_nonrunning_players"
                    ),
                    "assigned_node_count": outcome.get("assigned_node_count"),
                    "placement_dispersion_normalized": outcome.get(
                        "placement_dispersion_normalized"
                    ),
                    "co_location_conflict_pair_ratio": outcome.get(
                        "co_location_conflict_pair_ratio"
                    ),
                    "projected_reserved_memory_ratio_mean": outcome.get(
                        "projected_reserved_memory_ratio_mean"
                    ),
                    "envelope_selected_order": selected_order,
                    "envelope_selected_non_o0": envelope.get("selected_non_o0"),
                }
            )
    rows: list[dict[str, Any]] = []
    for mechanism, accumulator in accumulators.items():
        players = int(accumulator["players"])
        windows = int(accumulator["windows"])
        rows.append(
            {
                "run_id": run_id,
                "source_run_id": source_run_id,
                "stratum": stratum,
                "seed": run["seed"],
                "mechanism": mechanism,
                "total_windows": len(current_windows),
                "comparable_windows": comparable_windows,
                "aggregated_windows": windows,
                "assigned_players": players,
                "welfare_per_player": _per_player(
                    float(accumulator["welfare"]), players
                ),
                "startup_burden_per_player": _per_player(
                    float(accumulator["startup"]), players
                ),
                "projected_finish_per_player": _per_player(
                    float(accumulator["finish"]), players
                ),
                "different_assignment_windows": int(accumulator["different"]),
                "different_assignment_fraction": (
                    float(accumulator["different"]) / windows if windows else 0.0
                ),
                "additional_bad_windows": int(accumulator["additional_bad"]),
                "envelope_welfare_violations": int(accumulator["envelope_violations"]),
            }
        )
    return rows


def _aggregate_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["mechanism"])].append(row)
    result: dict[str, dict[str, Any]] = {}
    for mechanism in MECHANISMS:
        mechanism_rows = grouped[mechanism]
        result[mechanism] = {
            "run_count": len(mechanism_rows),
            "welfare_per_player": _mean(
                float(row["welfare_per_player"]) for row in mechanism_rows
            ),
            "startup_burden_per_player": _mean(
                float(row["startup_burden_per_player"]) for row in mechanism_rows
            ),
            "projected_finish_per_player": _mean(
                float(row["projected_finish_per_player"]) for row in mechanism_rows
            ),
            "different_assignment_fraction": (
                sum(int(row["different_assignment_windows"]) for row in mechanism_rows)
                / sum(int(row["aggregated_windows"]) for row in mechanism_rows)
            ),
            "additional_bad_windows": sum(
                int(row["additional_bad_windows"]) for row in mechanism_rows
            ),
            "envelope_welfare_violations": sum(
                int(row["envelope_welfare_violations"]) for row in mechanism_rows
            ),
        }
    return result


def _regression_fraction(alternative: float, baseline: float) -> float | None:
    if abs(baseline) <= 1e-12:
        return 0.0 if alternative <= baseline + 1e-12 else None
    return (alternative - baseline) / abs(baseline)


def _benefit_ratio(
    alternative: float, baseline: float, higher_is_better: bool
) -> float:
    if higher_is_better:
        if abs(baseline) <= 1e-12:
            return 1.0 if abs(alternative) <= 1e-12 else 1e12
        return alternative / baseline
    if abs(alternative) <= 1e-12:
        return 1.0 if abs(baseline) <= 1e-12 else 1e12
    return baseline / alternative


def apply_frozen_eligibility(
    overall: Mapping[str, Mapping[str, Any]],
    strata: Mapping[str, Mapping[str, Mapping[str, Any]]],
    *,
    integrity_passed: bool,
) -> dict[str, Any]:
    """Apply only the thresholds frozen in the G3 preregistration."""

    decisions: dict[str, dict[str, Any]] = {}
    o0_overall = overall["O0"]
    for mechanism in ALTERNATIVES:
        candidate = overall[mechanism]
        distinct_strata = sum(
            strata[stratum][mechanism]["different_assignment_fraction"]
            >= ASSIGNMENT_DIFFERENCE_MIN_FRACTION
            for stratum in G3_STRATA
        )
        # Express welfare loss as a positive fraction for the upper-bound test.
        welfare_loss_fractions = []
        for stratum in G3_STRATA:
            baseline = float(strata[stratum]["O0"]["welfare_per_player"])
            alternative = float(strata[stratum][mechanism]["welfare_per_player"])
            welfare_loss_fractions.append(
                max(0.0, (baseline - alternative) / max(abs(baseline), 1e-12))
            )
        startup_regressions = [
            _regression_fraction(
                float(strata[stratum][mechanism]["startup_burden_per_player"]),
                float(strata[stratum]["O0"]["startup_burden_per_player"]),
            )
            for stratum in G3_STRATA
        ]
        finish_regressions = [
            _regression_fraction(
                float(strata[stratum][mechanism]["projected_finish_per_player"]),
                float(strata[stratum]["O0"]["projected_finish_per_player"]),
            )
            for stratum in G3_STRATA
        ]
        startup_nonworse = sum(
            float(strata[stratum][mechanism]["startup_burden_per_player"])
            <= float(strata[stratum]["O0"]["startup_burden_per_player"]) + 1e-12
            for stratum in G3_STRATA
        )
        finish_nonworse = sum(
            float(strata[stratum][mechanism]["projected_finish_per_player"])
            <= float(strata[stratum]["O0"]["projected_finish_per_player"]) + 1e-12
            for stratum in G3_STRATA
        )
        gates = {
            "integrity": integrity_passed,
            "no_additional_bad_windows": candidate["additional_bad_windows"] == 0,
            "different_overall": candidate["different_assignment_fraction"]
            >= ASSIGNMENT_DIFFERENCE_MIN_FRACTION,
            "different_in_four_strata": distinct_strata >= DIFFERENT_MIN_STRATA,
            "startup_lower_overall": candidate["startup_burden_per_player"]
            < o0_overall["startup_burden_per_player"] - 1e-12,
            "startup_nonworse_five_strata": startup_nonworse >= NONWORSE_MIN_STRATA,
            "startup_max_regression": all(
                value is not None and value <= PROXY_MAX_STRATUM_REGRESSION + 1e-12
                for value in startup_regressions
            ),
            "finish_lower_overall": candidate["projected_finish_per_player"]
            < o0_overall["projected_finish_per_player"] - 1e-12,
            "finish_nonworse_five_strata": finish_nonworse >= NONWORSE_MIN_STRATA,
            "finish_max_regression": all(
                value is not None and value <= PROXY_MAX_STRATUM_REGRESSION + 1e-12
                for value in finish_regressions
            ),
        }
        if mechanism == "E0":
            gates["envelope_welfare_noninferiority"] = (
                candidate["envelope_welfare_violations"] == 0
            )
        else:
            gates.update(
                {
                    "welfare_nonnegative_overall": candidate["welfare_per_player"]
                    >= o0_overall["welfare_per_player"] - 1e-12,
                    "welfare_max_stratum_regression": max(welfare_loss_fractions)
                    <= WELFARE_MAX_STRATUM_REGRESSION + 1e-12,
                }
            )
        ratios: list[float] = []
        for stratum in G3_STRATA:
            baseline = strata[stratum]["O0"]
            alternative = strata[stratum][mechanism]
            ratios.extend(
                (
                    _benefit_ratio(
                        float(alternative["welfare_per_player"]),
                        float(baseline["welfare_per_player"]),
                        True,
                    ),
                    _benefit_ratio(
                        float(alternative["startup_burden_per_player"]),
                        float(baseline["startup_burden_per_player"]),
                        False,
                    ),
                    _benefit_ratio(
                        float(alternative["projected_finish_per_player"]),
                        float(baseline["projected_finish_per_player"]),
                        False,
                    ),
                )
            )
        decisions[mechanism] = {
            "eligible": all(gates.values()),
            "gates": gates,
            "distinct_strata": distinct_strata,
            "startup_nonworse_strata": startup_nonworse,
            "projected_finish_nonworse_strata": finish_nonworse,
            "rank_min_ratio": min(ratios),
            "rank_mean_ratio": statistics.fmean(ratios),
        }
    ranked = sorted(
        (mechanism for mechanism in ALTERNATIVES if decisions[mechanism]["eligible"]),
        key=lambda mechanism: (
            -float(decisions[mechanism]["rank_min_ratio"]),
            -float(decisions[mechanism]["rank_mean_ratio"]),
            SIMPLICITY_ORDER.index(mechanism),
        ),
    )
    return {
        "decisions": decisions,
        "eligible_ranked": ranked,
        "later_candidate_preregistration_options": ranked[:2],
        "D71_authorized": False,
        "selection_uses_throughput_or_qpr": False,
    }


def analyze_g3_order_counterfactual(
    manifest_path: Path, canonical_root: Path
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get(G3_ORDER_COUNTERFACTUAL_MARKER)
    if (
        not isinstance(marker, Mapping)
        or marker.get("schema_version") != G3_ORDER_COUNTERFACTUAL_SCHEMA
    ):
        raise ProtocolValidationError("manifest is not the frozen G3 order diagnostic")
    declared_ids = {str(run["run_id"]) for run in manifest["runs"]}
    actual_ids = (
        {path.name for path in canonical_root.iterdir() if path.is_dir()}
        if canonical_root.is_dir()
        else set()
    )
    missing_ids = sorted(declared_ids - actual_ids)
    unexpected_ids = sorted(actual_ids - declared_ids)
    if missing_ids:
        raise ProtocolValidationError(
            f"G3 canonical set is incomplete; missing {len(missing_ids)} runs"
        )
    parity_errors: list[str] = []
    diagnostic_errors: list[str] = []
    parity_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    raw_stream_rows: list[dict[str, Any]] = []
    result_template = str(
        manifest["execution"].get("result_relative_path", "result.json")
    )
    for run in manifest["runs"]:
        run_id = str(run["run_id"])
        canonical = canonical_root / run_id
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_template,
        )
        source_artifacts = run["metadata"]["source_artifacts"]
        source_stream = _artifact_path(source_artifacts, "nash_metrics")
        source_summary_path = _artifact_path(source_artifacts, "summary")
        _artifact_path(source_artifacts, "run_config")
        replay_stream = _one(canonical, "nash_metrics.jsonl.gz")
        replay_summary_path = _one(canonical, "summary.json")
        source_windows = _windows(source_stream)
        replay_windows = _windows(replay_stream)
        run_parity: list[str] = []
        if len(source_windows) != len(replay_windows):
            run_parity.append(
                f"window_count:{len(source_windows)}!={len(replay_windows)}"
            )
        for index, (source_window, replay_window) in enumerate(
            zip(source_windows, replay_windows)
        ):
            for field in _window_parity(source_window, replay_window):
                run_parity.append(f"window[{index}].{field}")
        source_summary = read_json(source_summary_path)
        replay_summary = read_json(replay_summary_path)
        if not isinstance(source_summary, Mapping) or not isinstance(
            replay_summary, Mapping
        ):
            raise ProtocolValidationError("G3 source/replay summary is not an object")
        run_parity.extend(
            f"summary.{field}"
            for field in _scientific_summary_parity(source_summary, replay_summary)
        )
        parity_errors.extend(f"{run_id}:{error}" for error in run_parity)
        parity_rows.append(
            {
                "run_id": run_id,
                "source_run_id": run["metadata"]["source_run_id"],
                "stratum": run["metadata"]["g3_reporting_stratum"],
                "source_window_count": len(source_windows),
                "replay_window_count": len(replay_windows),
                "parity_mismatch_count": len(run_parity),
                "parity_passed": not run_parity,
                "source_stream_sha256": file_hash(source_stream),
                "replay_stream_sha256": file_hash(replay_stream),
            }
        )
        run_rows.extend(
            _run_aggregates(
                run,
                replay_windows,
                raw_rows,
                raw_stream_rows,
                diagnostic_errors,
            )
        )
    stratum_rows: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in run_rows:
        stratum_rows[str(row["stratum"])].append(row)
    strata = {stratum: _aggregate_rows(stratum_rows[stratum]) for stratum in G3_STRATA}
    overall = _aggregate_rows(run_rows)
    integrity_gates = {
        "exact_50_declared_and_complete": len(manifest["runs"]) == 50
        and not missing_ids
        and not unexpected_ids,
        "live_c0_source_parity": not parity_errors,
        "o0_first_inner_and_counterfactual_schema": not diagnostic_errors,
        "all_o0_stable_complete_certified": not any(
            "o0_strict_pne_certificate" in error for error in diagnostic_errors
        ),
        "decision_feedback_false": not any(
            "decision_feedback" in error for error in diagnostic_errors
        ),
        "complete_raw_output": len(raw_rows)
        == sum(
            int(row["total_windows"]) for row in run_rows if row["mechanism"] == "O0"
        )
        * len(MECHANISMS),
    }
    integrity_passed = all(integrity_gates.values())
    eligibility = apply_frozen_eligibility(
        overall, strata, integrity_passed=integrity_passed
    )
    report: dict[str, Any] = {
        "schema_version": ANALYSIS_SCHEMA,
        "created_at": utc_now(),
        "status": (
            "complete_valid_diagnostic"
            if integrity_passed
            else "invalid_diagnostic_integrity_gate_failed"
        ),
        "manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "counts": {
            "declared_runs": len(manifest["runs"]),
            "canonical_runs": len(actual_ids & declared_ids),
            "unexpected_canonical_directories": len(unexpected_ids),
            "run_summary_rows": len(run_rows),
            "raw_window_rows": len(raw_rows),
            "raw_stream_windows": len(raw_stream_rows),
            "parity_errors": len(parity_errors),
            "diagnostic_errors": len(diagnostic_errors),
        },
        "integrity_gates": integrity_gates,
        "integrity_passed": integrity_passed,
        "missing_run_ids": missing_ids,
        "unexpected_run_ids": unexpected_ids,
        "parity_error_examples": parity_errors[:200],
        "diagnostic_error_examples": diagnostic_errors[:200],
        "overall": overall,
        "strata": strata,
        "eligibility": eligibility,
        "decision_boundary": {
            "observation_only": True,
            "candidate_effect_estimated": False,
            "D71_authorized": False,
            "homogeneous_middle_formal_authorized": False,
            "paper_ready_groups": 0,
            "throughput_qpr_used_for_selection": False,
        },
    }
    report["document_sha256"] = object_hash(report)
    stratum_csv_rows = [
        {"stratum": stratum, "mechanism": mechanism, **strata[stratum][mechanism]}
        for stratum in G3_STRATA
        for mechanism in MECHANISMS
    ]
    return report, raw_rows, raw_stream_rows, run_rows, parity_rows + stratum_csv_rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if not isinstance(value, (dict, list))
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def write_jsonl_gz(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
                + "\n"
            )


def write_g3_order_counterfactual_analysis(
    manifest_path: Path, canonical_root: Path, output_directory: Path
) -> dict[str, Any]:
    output_directory = output_directory.resolve()
    if output_directory.exists() and any(output_directory.iterdir()):
        raise ProtocolValidationError(
            "refusing to overwrite a non-empty G3 analysis directory"
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    (
        report,
        raw_rows,
        raw_stream_rows,
        run_rows,
        parity_and_strata_rows,
    ) = analyze_g3_order_counterfactual(manifest_path, canonical_root)
    report_path = output_directory / "g3.order-counterfactual.analysis.json"
    raw_stream_path = output_directory / "g3.order-counterfactual.raw.jsonl.gz"
    raw_path = output_directory / "g3.order-counterfactual.windows.csv"
    run_path = output_directory / "g3.order-counterfactual.runs.csv"
    parity_path = output_directory / "g3.order-counterfactual.parity.csv"
    strata_path = output_directory / "g3.order-counterfactual.strata.csv"
    write_json_atomic(report_path, report)
    write_jsonl_gz(raw_stream_path, raw_stream_rows)
    write_csv(raw_path, raw_rows)
    write_csv(run_path, run_rows)
    write_csv(
        parity_path,
        [row for row in parity_and_strata_rows if "parity_passed" in row],
    )
    write_csv(
        strata_path,
        [row for row in parity_and_strata_rows if "mechanism" in row],
    )
    return {
        "report": report,
        "outputs": {
            "analysis": {
                "path": str(report_path),
                "sha256": file_hash(report_path),
            },
            "raw_counterfactual_jsonl": {
                "path": str(raw_stream_path),
                "sha256": file_hash(raw_stream_path),
            },
            "window_csv": {"path": str(raw_path), "sha256": file_hash(raw_path)},
            "run_csv": {"path": str(run_path), "sha256": file_hash(run_path)},
            "parity_csv": {
                "path": str(parity_path),
                "sha256": file_hash(parity_path),
            },
            "strata_csv": {
                "path": str(strata_path),
                "sha256": file_hash(strata_path),
            },
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("canonical_root", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args(argv)
    receipt = write_g3_order_counterfactual_analysis(
        args.manifest, args.canonical_root, args.output_directory
    )
    print(
        json.dumps(
            {
                "status": receipt["report"]["status"],
                "integrity_passed": receipt["report"]["integrity_passed"],
                "eligible_ranked": receipt["report"]["eligibility"]["eligible_ranked"],
                "D71_authorized": False,
                "outputs": receipt["outputs"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
