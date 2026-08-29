from __future__ import annotations

import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_blind_audit_v100 import (
    _assert_hashed_object,
    _assert_ledger_contract,
    _read_ledger,
    _require,
    _stage_root_from_receipts,
)
from scripts.reviewer_experiments.protocol.nse_e3_final_margin_training_prepare_v121 import (
    ARMS as PREPARED_ARMS,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    CONFIRMATION_SEEDS,
    OTHER_UNOPENED_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUS_CONFIRMATION_SEEDS,
    PYTHON_SHA256,
    ROOT,
    TRAINING_SEEDS,
    V120_RESULT_RECEIPT_COMMIT,
    V120_RESULT_RECEIPT_HASH,
)
from scripts.reviewer_experiments.protocol.reference import inspect_reference_table
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.tape import inspect_tape
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


PREPARED = ROOT / "prepared-manifests-v121.json"
TAPES = ROOT / "tapes.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v121-training.json"
RESULT = ROOT / "training-result-v121.json"
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
ADMITTED_WORK_SOURCE = (
    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
)
LEGACY_WORK_SOURCE = "legacy_task_count_times_current_player_cpu_v108"
ARMS = {
    arm_id: {
        "experiment_id": "E3",
        "role": role,
        "profile": profile,
        "shock_rate_ratio": "3/2" if role == "candidate" else None,
        "shock_threshold_numerator": 3 if role == "candidate" else None,
        "shock_threshold_denominator": 2 if role == "candidate" else None,
        "shock_activation_horizon_frames": 50 if role == "candidate" else None,
        "diagnostic_activation_horizon_frames": 50 if role == "candidate" else 100,
        "critical_service_threshold_numerator": 9 if role == "candidate" else None,
        "critical_service_threshold_denominator": 10 if role == "candidate" else None,
        "work_source": ADMITTED_WORK_SOURCE
        if role == "candidate"
        else LEGACY_WORK_SOURCE,
        "componentwise_service_enabled": role == "candidate",
        "run_count": count,
    }
    for arm_id, role, profile, count in PREPARED_ARMS
}


def _arm_paths(arm_id: str) -> dict[str, Path]:
    workspace = ROOT / "runs" / arm_id
    return {
        "ready": ROOT / f"manifest.{arm_id}.ready.json",
        "references": ROOT / f"references.{arm_id}.catalog.json",
        "pairing": ROOT / f"pairing-audit.{arm_id}.json",
        "workspace": workspace,
    }


def _scenario(run: dict[str, Any]) -> str:
    return f"E3.{run['workload']['burst_name']}"


def _finite_nonnegative(value: Any) -> bool:
    return (
        type(value) in (int, float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0.0
    )


def _validate_admitted_work_diagnostics(
    run: dict[str, Any], canonical: Path, expected: dict[str, Any]
) -> dict[str, Any]:
    """Validate V121 mechanism evidence without opening any performance summary."""

    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V121 Nash diagnostics: {run['run_id']}")
    candidate = expected["role"] == "candidate"
    counts = Counter()
    exact_pending_total_sum = 0.0
    resident_remaining_total_sum = 0.0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            counts["windows"] += 1
            frame = event.get("frame")
            _require(type(frame) is int and frame >= 0, "invalid V121 window frame")

            cluster = event.get("cluster")
            _require(isinstance(cluster, dict), "missing V121 cluster diagnostics")
            admitted_fields = (
                "queue_pending_cpu_work_total",
                "queue_pending_cpu_work_max",
                "queue_resident_remaining_cpu_work_total",
                "queue_resident_remaining_cpu_work_max",
            )
            frozen_v110_fields = (
                "queue_runnable_cpu_work_total",
                "queue_runnable_cpu_work_max",
            )
            if candidate:
                _require(
                    cluster.get("queue_cpu_work_observation_complete") is True
                    and cluster.get("queue_admitted_work_observation_complete") is True
                    and all(
                        _finite_nonnegative(cluster.get(field))
                        for field in (*admitted_fields, *frozen_v110_fields)
                    ),
                    f"V121 admitted-work observation changed: {run['run_id']}:{line_number}",
                )
                pending_count = cluster.get("queue_pending_cpu_value_count")
                resident_count = cluster.get("queue_resident_remaining_cpu_value_count")
                _require(
                    type(pending_count) is int
                    and pending_count >= 0
                    and pending_count == cluster.get("queue_pending_total")
                    and type(resident_count) is int
                    and resident_count >= 0
                    and resident_count == cluster.get("queue_resident_total"),
                    f"V121 admitted-work snapshot counts changed: "
                    f"{run['run_id']}:{line_number}",
                )
                _require(
                    float(cluster["queue_pending_cpu_work_total"]) + 1.0e-9
                    >= float(cluster["queue_pending_cpu_work_max"])
                    and float(cluster["queue_resident_remaining_cpu_work_total"])
                    + 1.0e-9
                    >= float(cluster["queue_resident_remaining_cpu_work_max"]),
                    f"V121 admitted-work aggregate changed: {run['run_id']}:{line_number}",
                )
                exact_pending_total_sum += float(
                    cluster["queue_pending_cpu_work_total"]
                )
                resident_remaining_total_sum += float(
                    cluster["queue_resident_remaining_cpu_work_total"]
                )
                counts["admitted_work_complete_windows"] += 1
                counts["pending_cpu_value_count"] += pending_count
                counts["resident_remaining_cpu_value_count"] += resident_count

            dominance = event.get("decision", {}).get("load_least_dominance_gate", {})
            gate = dominance.get("causal_arrival_shock")
            _require(
                isinstance(gate, dict)
                and gate.get("gate_enabled") is candidate
                and gate.get("baseline_frames") == 80
                and gate.get("recent_frames") == 20
                and gate.get("min_requests_per_window") == 20
                and gate.get("threshold_numerator")
                == expected["shock_threshold_numerator"]
                and gate.get("threshold_denominator")
                == expected["shock_threshold_denominator"]
                and gate.get("active_frames")
                == expected["diagnostic_activation_horizon_frames"]
                and gate.get("uses_first_seen_request_ids_only") is True,
                f"V121 causal contract changed: {run['run_id']}:{line_number}",
            )
            for field in ("first_seen_current_frame", "baseline_count", "recent_count"):
                _require(
                    type(gate.get(field)) is int and gate[field] >= 0,
                    f"V121 causal {field} changed: {run['run_id']}:{line_number}",
                )
            _require(
                type(gate.get("history_complete")) is bool
                and type(gate.get("active")) is bool,
                f"V121 causal types changed: {run['run_id']}:{line_number}",
            )
            until_frame = gate.get("until_frame")
            _require(
                until_frame is None or (type(until_frame) is int and until_frame >= 0),
                f"V121 causal deadline changed: {run['run_id']}:{line_number}",
            )
            _require(
                gate["active"] is (until_frame is not None and frame <= until_frame),
                f"V121 causal active flag changed: {run['run_id']}:{line_number}",
            )

            critical = dominance.get("critical_service_proxy")
            _require(isinstance(critical, dict), "missing V121 critical diagnostics")
            solver_termination = event.get("solver", {}).get("termination")
            invoked = candidate and solver_termination != "no_players"
            _require(
                critical.get("gate_enabled") is invoked
                and type(critical.get("evaluated")) is bool
                and type(critical.get("accepted")) is bool
                and critical.get("threshold_numerator")
                == (
                    expected["critical_service_threshold_numerator"]
                    if invoked
                    else None
                )
                and critical.get("threshold_denominator")
                == (
                    expected["critical_service_threshold_denominator"]
                    if invoked
                    else None
                )
                and critical.get("work_source") == expected["work_source"]
                and critical.get("noncritical_players_preserve_exact_anchor")
                is (not (candidate and critical.get("gate_enabled")))
                and critical.get("proxy_uses_completion_outcomes") is False,
                f"V121 critical-service contract changed: {run['run_id']}:{line_number}",
            )
            service_directed = critical.get("service_directed_construction")
            _require(
                isinstance(service_directed, dict)
                and service_directed.get("enabled") is critical.get("gate_enabled")
                and service_directed.get("scope")
                == (
                    "all_current_players"
                    if candidate and critical.get("gate_enabled")
                    else "not_applicable"
                )
                and service_directed.get("dual_prefix_anchor_enabled")
                is (candidate and critical.get("gate_enabled"))
                and service_directed.get("anchor_service_baseline_state")
                == (
                    "independent_exact_anchor_native_order_prefix"
                    if candidate and critical.get("gate_enabled")
                    else "not_applicable"
                )
                and service_directed.get("candidate_service_state")
                == (
                    "evolving_alternative_native_order_prefix"
                    if candidate and critical.get("gate_enabled")
                    else "not_applicable"
                )
                and service_directed.get("choice_rule")
                == (
                    "existing_v113_admitted_work_service_choice_with_exact_anchor_prefix_baseline_and_frozen_ratio_and_safety_filters"
                    if candidate and critical.get("gate_enabled")
                    else "existing_v113_admitted_work_service_choice_with_frozen_ratio_and_safety_filters"
                )
                and service_directed.get("uses_completion_outcomes") is False,
                f"V121 service-directed construction contract changed: "
                f"{run['run_id']}:{line_number}",
            )
            for field in (
                "target_player_count",
                "evaluated_player_count",
                "input_unavailable_player_count",
                "substitution_count",
                "critical_substitution_count",
                "noncritical_substitution_count",
                "anchor_prefix_completed_player_count",
                "anchor_prefix_input_unavailable_player_count",
                "candidate_prefix_input_unavailable_count",
            ):
                _require(
                    type(service_directed.get(field)) is int
                    and service_directed[field] >= 0,
                    f"V121 service-directed {field} changed: "
                    f"{run['run_id']}:{line_number}",
                )
            _require(
                service_directed["substitution_count"]
                == service_directed["critical_substitution_count"]
                + service_directed["noncritical_substitution_count"],
                f"V121 service-directed substitution partition changed: "
                f"{run['run_id']}:{line_number}",
            )
            if candidate and critical.get("gate_enabled"):
                request_players = event["decision"]["request_function_players"]
                _require(
                    service_directed["target_player_count"] == request_players
                    and service_directed["evaluated_player_count"]
                    in (0, request_players)
                    and service_directed["input_unavailable_player_count"] == 0,
                    f"V121 all-player construction coverage changed: "
                    f"{run['run_id']}:{line_number}",
                )
                _require(
                    service_directed["anchor_prefix_completed_player_count"]
                    == service_directed["evaluated_player_count"]
                    and service_directed["anchor_prefix_input_unavailable_player_count"]
                    == 0
                    and service_directed["candidate_prefix_input_unavailable_count"]
                    == 0,
                    f"V121 dual-prefix construction coverage changed: "
                    f"{run['run_id']}:{line_number}",
                )
            else:
                _require(
                    all(
                        service_directed[field] == 0
                        for field in (
                            "target_player_count",
                            "evaluated_player_count",
                            "input_unavailable_player_count",
                            "substitution_count",
                            "critical_substitution_count",
                            "noncritical_substitution_count",
                            "anchor_prefix_completed_player_count",
                            "anchor_prefix_input_unavailable_player_count",
                            "candidate_prefix_input_unavailable_count",
                        )
                    ),
                    f"V121 inapplicable service construction was populated: "
                    f"{run['run_id']}:{line_number}",
                )
            componentwise = critical.get("complete_componentwise_pareto")
            _require(
                isinstance(componentwise, dict)
                and componentwise.get("gate_enabled") is critical.get("gate_enabled")
                and componentwise.get("evaluated") is critical.get("evaluated")
                and type(componentwise.get("accepted")) is bool
                and componentwise.get("critical_player_count")
                == critical.get("critical_player_count")
                and componentwise.get("scope")
                == ("all_current_players" if candidate else "not_applicable")
                and componentwise.get("comparison")
                == (
                    "every_current_player_alternative_nonworse_and_every_changed_player_retains_frozen_nine_tenths_margin"
                    if candidate and componentwise.get("gate_enabled")
                    else "every_current_player_alternative_less_than_or_equal_to_anchor"
                    if candidate
                    else "every_current_critical_player_alternative_less_than_or_equal_to_anchor"
                )
                and componentwise.get("replay_order")
                == "frozen_native_player_order_with_independent_assignment_prefixes"
                and componentwise.get("work_source")
                == "v113_admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                and componentwise.get("uses_completion_outcomes") is False,
                f"V121 componentwise-service contract changed: "
                f"{run['run_id']}:{line_number}",
            )
            for field in (
                "target_player_count",
                "compared_player_count",
                "input_unavailable_count",
                "worse_player_count",
            ):
                _require(
                    type(componentwise.get(field)) is int and componentwise[field] >= 0,
                    f"V121 componentwise {field} changed: "
                    f"{run['run_id']}:{line_number}",
                )
            changed_margin = componentwise.get("changed_player_margin")
            margin_enabled = candidate and componentwise["gate_enabled"]
            _require(
                isinstance(changed_margin, dict)
                and changed_margin.get("enabled") is margin_enabled
                and changed_margin.get("numerator") == (9 if margin_enabled else None)
                and changed_margin.get("denominator")
                == (10 if margin_enabled else None),
                f"V121 changed-player margin contract changed: "
                f"{run['run_id']}:{line_number}",
            )
            for field in ("changed_player_count", "violation_count"):
                _require(
                    type(changed_margin.get(field)) is int
                    and changed_margin[field] >= 0,
                    f"V121 changed-player margin {field} changed: "
                    f"{run['run_id']}:{line_number}",
                )
            changed_maximum_ratio = changed_margin.get(
                "maximum_alternative_to_anchor_ratio"
            )
            _require(
                changed_maximum_ratio is None
                or _finite_nonnegative(changed_maximum_ratio),
                f"V121 changed-player margin ratio changed: "
                f"{run['run_id']}:{line_number}",
            )
            if not margin_enabled or not componentwise["evaluated"]:
                _require(
                    changed_margin["changed_player_count"] == 0
                    and changed_margin["violation_count"] == 0
                    and changed_maximum_ratio is None,
                    f"V121 inapplicable changed-player margin was populated: "
                    f"{run['run_id']}:{line_number}",
                )
            _require(
                changed_margin["violation_count"]
                <= changed_margin["changed_player_count"],
                f"V121 changed-player margin partition changed: "
                f"{run['run_id']}:{line_number}",
            )
            if componentwise["accepted"] and changed_margin["changed_player_count"] > 0:
                _require(
                    changed_maximum_ratio is not None
                    and float(changed_maximum_ratio) <= 0.900001,
                    f"V121 accepted changed-player margin is not retained: "
                    f"{run['run_id']}:{line_number}",
                )
            expected_componentwise_accept = (
                componentwise["evaluated"]
                and componentwise["input_unavailable_count"] == 0
                and componentwise["compared_player_count"]
                == componentwise["target_player_count"]
                and componentwise["worse_player_count"] == 0
                and changed_margin["violation_count"] == 0
            )
            _require(
                componentwise["accepted"] is expected_componentwise_accept,
                f"V121 componentwise acceptance changed: "
                f"{run['run_id']}:{line_number}",
            )
            expected_componentwise_reason = (
                "not_applicable"
                if not componentwise["evaluated"]
                else "componentwise_critical_service_unavailable"
                if componentwise["input_unavailable_count"] > 0
                else "componentwise_critical_service_coverage_mismatch"
                if componentwise["compared_player_count"]
                != componentwise["target_player_count"]
                else "componentwise_critical_service_worse"
                if componentwise["worse_player_count"] > 0
                else "changed_player_service_margin_not_retained"
                if changed_margin["violation_count"] > 0
                else "accepted"
            )
            _require(
                componentwise.get("reason") == expected_componentwise_reason,
                f"V121 componentwise reason changed: {run['run_id']}:{line_number}",
            )
            if not componentwise["evaluated"]:
                _require(
                    componentwise["target_player_count"] == 0
                    and componentwise["compared_player_count"] == 0
                    and componentwise["input_unavailable_count"] == 0
                    and componentwise["worse_player_count"] == 0
                    and componentwise.get("maximum_alternative_minus_anchor") is None
                    and componentwise.get("maximum_alternative_to_anchor_ratio")
                    is None,
                    f"V121 unevaluated componentwise evidence was populated: "
                    f"{run['run_id']}:{line_number}",
                )
            maximum_delta = componentwise.get("maximum_alternative_minus_anchor")
            maximum_ratio = componentwise.get("maximum_alternative_to_anchor_ratio")
            _require(
                maximum_delta is None
                or (
                    type(maximum_delta) in (int, float)
                    and not isinstance(maximum_delta, bool)
                    and math.isfinite(float(maximum_delta))
                ),
                f"V121 componentwise delta changed: {run['run_id']}:{line_number}",
            )
            _require(
                maximum_ratio is None or _finite_nonnegative(maximum_ratio),
                f"V121 componentwise ratio changed: {run['run_id']}:{line_number}",
            )
            if componentwise["evaluated"]:
                _require(
                    componentwise["target_player_count"]
                    == event["decision"]["request_function_players"],
                    f"V121 all-player target coverage changed: "
                    f"{run['run_id']}:{line_number}",
                )
            if componentwise["accepted"] and componentwise["target_player_count"] > 0:
                _require(
                    maximum_delta is not None and float(maximum_delta) <= 1.000001e-6,
                    f"V121 accepted componentwise delta is worse: "
                    f"{run['run_id']}:{line_number}",
                )
            _require(
                not critical["accepted"] or componentwise["accepted"],
                f"V121 main certificate bypassed componentwise gate: "
                f"{run['run_id']}:{line_number}",
            )
            componentwise_rejection_reasons = {
                "componentwise_critical_service_unavailable",
                "componentwise_critical_service_coverage_mismatch",
                "componentwise_critical_service_worse",
                "changed_player_service_margin_not_retained",
            }
            if dominance.get("reason") in componentwise_rejection_reasons:
                _require(
                    componentwise["accepted"] is False
                    and dominance.get("accepted") is False
                    and dominance.get("selected_initializer_assignment_hash")
                    == dominance.get("anchor_assignment_hash"),
                    f"V121 componentwise fallback was not exact anchor: "
                    f"{run['run_id']}:{line_number}",
                )
            phase = gate.get("non_decreasing_phase")
            interference = critical.get("admitted_interference_pareto")
            _require(
                isinstance(phase, dict)
                and phase.get("gate_enabled") is False
                and isinstance(interference, dict)
                and interference.get("gate_enabled") is False
                and interference.get("componentwise_gate_enabled") is False,
                f"V121 re-enabled a failed V114-V116 axis: "
                f"{run['run_id']}:{line_number}",
            )
            for field in (
                "critical_player_count",
                "candidate_evaluation_count",
                "substitution_count",
                "proxy_input_unavailable_count",
            ):
                _require(
                    type(critical.get(field)) is int and critical[field] >= 0,
                    f"V121 critical {field} changed: {run['run_id']}:{line_number}",
                )
            _require(
                not critical["accepted"] or critical["evaluated"],
                f"V121 accepted without evaluation: {run['run_id']}:{line_number}",
            )
            if not invoked:
                _require(
                    critical["evaluated"] is False
                    and critical["accepted"] is False
                    and critical["critical_player_count"] == 0
                    and critical["candidate_evaluation_count"] == 0
                    and critical["substitution_count"] == 0
                    and critical["proxy_input_unavailable_count"] == 0,
                    f"V121 non-invoked critical state changed: {run['run_id']}:{line_number}",
                )
            if critical["accepted"]:
                values = tuple(
                    critical.get(field)
                    for field in (
                        "anchor_sum",
                        "alternative_sum",
                        "alternative_minus_anchor",
                        "minimum_individually_accepted_ratio",
                        "maximum_individually_accepted_ratio",
                    )
                )
                _require(
                    all(_finite_nonnegative(value) for value in values[:2])
                    and all(
                        type(value) in (int, float)
                        and not isinstance(value, bool)
                        and math.isfinite(float(value))
                        for value in values[2:]
                    ),
                    f"V121 accepted evidence is nonfinite: {run['run_id']}:{line_number}",
                )
                anchor_sum, alternative_sum, delta, minimum_ratio, maximum_ratio = (
                    float(value) for value in values
                )
                _require(
                    critical["substitution_count"] > 0
                    and alternative_sum < anchor_sum
                    and math.isclose(
                        delta,
                        alternative_sum - anchor_sum,
                        rel_tol=1.0e-12,
                        abs_tol=1.0e-9,
                    )
                    and 0.0 <= minimum_ratio <= maximum_ratio <= 0.900001,
                    f"V121 accepted admitted-work certificate changed: "
                    f"{run['run_id']}:{line_number}",
                )
            counts["active_windows"] += int(gate["active"])
            counts["critical_evaluated_windows"] += int(critical["evaluated"])
            counts["critical_accepted_windows"] += int(critical["accepted"])
            counts["componentwise_evaluated_windows"] += int(componentwise["evaluated"])
            counts["componentwise_accepted_windows"] += int(componentwise["accepted"])
            counts["componentwise_rejected_windows"] += int(
                componentwise["evaluated"] and not componentwise["accepted"]
            )
            counts["componentwise_compared_players"] += componentwise[
                "compared_player_count"
            ]
            counts["componentwise_target_players"] += componentwise[
                "target_player_count"
            ]
            counts["componentwise_unavailable"] += componentwise[
                "input_unavailable_count"
            ]
            counts["componentwise_worse_players"] += componentwise["worse_player_count"]
            counts["changed_player_margin_evaluated_windows"] += int(
                margin_enabled and componentwise["evaluated"]
            )
            counts["changed_player_margin_accepted_windows"] += int(
                margin_enabled
                and componentwise["evaluated"]
                and changed_margin["changed_player_count"] > 0
                and changed_margin["violation_count"] == 0
            )
            counts["changed_player_margin_rejected_windows"] += int(
                margin_enabled and changed_margin["violation_count"] > 0
            )
            counts["changed_players"] += changed_margin["changed_player_count"]
            counts["changed_player_margin_violations"] += changed_margin[
                "violation_count"
            ]
            counts["critical_players"] += critical["critical_player_count"]
            counts["candidate_evaluations"] += critical["candidate_evaluation_count"]
            counts["substitutions"] += critical["substitution_count"]
            counts["proxy_input_unavailable"] += critical[
                "proxy_input_unavailable_count"
            ]
            counts["service_choice_target_players"] += service_directed[
                "target_player_count"
            ]
            counts["service_choice_evaluated_players"] += service_directed[
                "evaluated_player_count"
            ]
            counts["service_choice_unavailable_players"] += service_directed[
                "input_unavailable_player_count"
            ]
            counts["service_choice_substitutions"] += service_directed[
                "substitution_count"
            ]
            counts["service_choice_critical_substitutions"] += service_directed[
                "critical_substitution_count"
            ]
            counts["service_choice_noncritical_substitutions"] += service_directed[
                "noncritical_substitution_count"
            ]
            counts["anchor_prefix_completed_players"] += service_directed[
                "anchor_prefix_completed_player_count"
            ]
            counts["anchor_prefix_unavailable_players"] += service_directed[
                "anchor_prefix_input_unavailable_player_count"
            ]
            counts["candidate_prefix_unavailable"] += service_directed[
                "candidate_prefix_input_unavailable_count"
            ]

            if not candidate:
                _require(
                    gate["history_complete"] is False
                    and gate["baseline_count"] == 0
                    and gate["recent_count"] == 0
                    and gate["active"] is False
                    and until_frame is None,
                    f"V121 anchor used causal state: {run['run_id']}:{line_number}",
                )
                continue
            if not gate["history_complete"]:
                _require(
                    gate["baseline_count"] == 0 and gate["recent_count"] == 0,
                    f"V121 incomplete history leaked counts: {run['run_id']}:{line_number}",
                )
                continue
            sufficient = (
                gate["baseline_count"] >= gate["min_requests_per_window"]
                and gate["recent_count"] >= gate["min_requests_per_window"]
            )
            recent_scaled = (
                gate["recent_count"]
                * gate["baseline_frames"]
                * gate["threshold_denominator"]
            )
            baseline_scaled = (
                gate["baseline_count"]
                * gate["recent_frames"]
                * gate["threshold_numerator"]
            )
            if sufficient and recent_scaled >= baseline_scaled:
                counts["threshold_met_windows"] += 1
                _require(
                    gate["active"] is True
                    and until_frame
                    >= frame + expected["diagnostic_activation_horizon_frames"] - 1,
                    f"V121 exact threshold did not activate: "
                    f"{run['run_id']}:{line_number}",
                )

    _require(
        counts["windows"] == run["simulation"]["total_frame"],
        f"V121 diagnostic window count changed: {run['run_id']}",
    )
    if candidate:
        _require(
            counts["admitted_work_complete_windows"] == counts["windows"]
            and counts["threshold_met_windows"] > 0
            and counts["active_windows"] > 0
            and counts["critical_evaluated_windows"] > 0,
            f"V121 mechanism was not exercised: {run['run_id']}",
        )
    return {
        "file_sha256": file_hash(path),
        "window_count": counts["windows"],
        "admitted_work_complete_window_count": counts["admitted_work_complete_windows"],
        "pending_cpu_value_count": counts["pending_cpu_value_count"],
        "resident_remaining_cpu_value_count": counts[
            "resident_remaining_cpu_value_count"
        ],
        "exact_pending_cpu_work_total_sum": exact_pending_total_sum,
        "resident_remaining_cpu_work_total_sum": resident_remaining_total_sum,
        "active_window_count": counts["active_windows"],
        "threshold_met_window_count": counts["threshold_met_windows"],
        "critical_evaluated_window_count": counts["critical_evaluated_windows"],
        "critical_accepted_window_count": counts["critical_accepted_windows"],
        "componentwise_evaluated_window_count": counts[
            "componentwise_evaluated_windows"
        ],
        "componentwise_accepted_window_count": counts["componentwise_accepted_windows"],
        "componentwise_rejected_window_count": counts["componentwise_rejected_windows"],
        "componentwise_target_player_count": counts["componentwise_target_players"],
        "componentwise_compared_player_count": counts["componentwise_compared_players"],
        "componentwise_input_unavailable_count": counts["componentwise_unavailable"],
        "componentwise_worse_player_count": counts["componentwise_worse_players"],
        "changed_player_margin_evaluated_window_count": counts[
            "changed_player_margin_evaluated_windows"
        ],
        "changed_player_margin_accepted_window_count": counts[
            "changed_player_margin_accepted_windows"
        ],
        "changed_player_margin_rejected_window_count": counts[
            "changed_player_margin_rejected_windows"
        ],
        "changed_player_count": counts["changed_players"],
        "changed_player_margin_violation_count": counts[
            "changed_player_margin_violations"
        ],
        "critical_player_count": counts["critical_players"],
        "critical_candidate_evaluation_count": counts["candidate_evaluations"],
        "critical_substitution_count": counts["substitutions"],
        "proxy_input_unavailable_count": counts["proxy_input_unavailable"],
        "service_choice_target_player_count": counts["service_choice_target_players"],
        "service_choice_evaluated_player_count": counts[
            "service_choice_evaluated_players"
        ],
        "service_choice_input_unavailable_player_count": counts[
            "service_choice_unavailable_players"
        ],
        "service_choice_substitution_count": counts["service_choice_substitutions"],
        "service_choice_critical_substitution_count": counts[
            "service_choice_critical_substitutions"
        ],
        "service_choice_noncritical_substitution_count": counts[
            "service_choice_noncritical_substitutions"
        ],
        "anchor_prefix_completed_player_count": counts[
            "anchor_prefix_completed_players"
        ],
        "anchor_prefix_input_unavailable_player_count": counts[
            "anchor_prefix_unavailable_players"
        ],
        "candidate_prefix_input_unavailable_count": counts[
            "candidate_prefix_unavailable"
        ],
        "work_source": expected["work_source"],
        "performance_fields_consulted": False,
    }


def _verify_tape_catalog() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(TAPES.is_file(), f"missing V121 tape catalog: {TAPES}")
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V121 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12, "V121 tape count changed"
    )
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(info.sha256 == entry["sha256"], f"tape hash changed: {key}")
        _require(info.workload_seed in TRAINING_SEEDS, f"unexpected tape seed: {key}")
        evidence.append(
            {
                "key": key,
                "sha256": info.sha256,
                "event_count": info.event_count,
                "dag_order_sha256": info.dag_order_sha256,
                "workload_seed": info.workload_seed,
                "kind": entry["kind"],
            }
        )
    _require(
        Counter(item["kind"] for item in evidence)
        == Counter({"base_steady": 3, "derived_burst": 9}),
        "V121 tape kind boundary changed",
    )
    _require(
        Counter(item["workload_seed"] for item in evidence)
        == Counter({seed: 4 for seed in TRAINING_SEEDS}),
        "V121 paired tape seed product changed",
    )
    base_entries = {
        key: entry for key, entry in entries.items() if entry["kind"] == "base_steady"
    }
    capture_root = _stage_root_from_receipts(
        base_entries, "capture_receipt_path", 3, "V121 tape capture"
    )
    rows, last_hash = _read_ledger(capture_root / "ledger.jsonl")
    _assert_ledger_contract(
        rows, Counter({"capture_canonicalized": 3}), "V121 tape capture"
    )
    _require(
        not list((capture_root / "quarantine").glob("**/attempt-*")),
        "V121 tape capture has quarantined attempts",
    )
    return evidence, {
        "catalog_path": str(TAPES),
        "catalog_file_sha256": file_hash(TAPES),
        "catalog_hash": catalog_hash,
        "capture_stage_root": str(capture_root),
        "capture_ledger_last_hash": last_hash,
    }


def _verify_reference_stage_ledgers() -> tuple[dict[str, Path], dict[Path, str]]:
    roots: dict[str, Path] = {}
    expected_by_root: Counter[Path] = Counter()
    for arm_id, expected in ARMS.items():
        catalog_path = ROOT / f"references.{arm_id}.catalog.json"
        _require(catalog_path.is_file(), f"missing reference catalog: {arm_id}")
        entries = read_json(catalog_path).get("entries")
        _require(isinstance(entries, dict), f"reference catalog malformed: {arm_id}")
        root = _stage_root_from_receipts(
            entries, "receipt_path", expected["run_count"], f"V121 reference {arm_id}"
        )
        roots[arm_id] = root
        expected_by_root[root] += expected["run_count"]
    hashes: dict[Path, str] = {}
    for root, expected_count in expected_by_root.items():
        rows, last_hash = _read_ledger(root / "ledger.jsonl")
        _assert_ledger_contract(
            rows,
            Counter({"reference_build_canonicalized": expected_count}),
            f"V121 reference stage {root}",
        )
        _require(
            not list((root / "quarantine").glob("**/attempt-*")),
            f"V121 reference quarantine is nonempty: {root}",
        )
        hashes[root] = last_hash
    return roots, hashes


def _validate_run_boundary(
    run: dict[str, Any], arm_id: str, expected: dict[str, Any]
) -> None:
    candidate = expected["role"] == "candidate"
    metadata = run.get("metadata", {})
    required = {
        "v121_training_plan_sha256": PLAN_SHA256,
        "v121_training_only": True,
        "v121_training_seed_metrics_previously_revealed": False,
        "v121_confirmation_seeds_opened": False,
        "v121_other_unopened_seeds_opened": False,
        "v121_formal_E01_E20_reexecution": False,
        "v121_arm_id": arm_id,
        "v121_arm_role": expected["role"],
        "v121_candidate_profile": expected["profile"],
        "v121_candidate_experiment": "E3",
        "v121_shock_rate_ratio": expected["shock_rate_ratio"],
        "v121_shock_threshold_numerator": expected["shock_threshold_numerator"],
        "v121_shock_threshold_denominator": expected["shock_threshold_denominator"],
        "v121_arrival_history_baseline_frames": 80 if candidate else None,
        "v121_arrival_history_recent_frames": 20 if candidate else None,
        "v121_arrival_min_requests_per_window": 20 if candidate else None,
        "v121_shock_activation_horizon_frames": expected[
            "shock_activation_horizon_frames"
        ],
        "v121_nonterminal_queue_density_floor": 8.0 if candidate else None,
        "v121_warm_admissibility": "preserve_anchor_warmness" if candidate else None,
        "v121_load_least_window_certificate_mode": (
            "disabled" if candidate else "not_applicable"
        ),
        "v121_critical_service_ratio_numerator": expected[
            "critical_service_threshold_numerator"
        ],
        "v121_critical_service_ratio_denominator": expected[
            "critical_service_threshold_denominator"
        ],
        "v121_critical_service_proxy": (
            "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
            if candidate
            else "not_applicable"
        ),
        "v121_service_proxy_work_source": (
            ADMITTED_WORK_SOURCE if candidate else "not_applicable"
        ),
        "v121_admitted_work_includes_all_blocked_resident": candidate,
        "v121_admitted_work_deterministic_f64_sum": candidate,
        "v121_complete_componentwise_service_pareto": candidate,
        "v121_componentwise_service_scope": (
            "all_current_players" if candidate else "not_applicable"
        ),
        "v121_componentwise_service_comparison": (
            "every_current_player_nonworse_and_every_changed_player_retains_nine_tenths_margin"
            if candidate
            else "not_applicable"
        ),
        "v121_componentwise_service_replay_order": (
            "native_player_order" if candidate else "not_applicable"
        ),
        "v121_componentwise_service_inputs_finite_fail_closed": candidate,
        "v121_componentwise_service_coverage_mismatch_fail_closed": candidate,
        "v121_interference_constraints": False,
        "v121_arrival_phase_guard": False,
        "v121_critical_service_proxy_inputs_finite_fail_closed": candidate,
        "v121_cpu_memory_individual_noninferiority": candidate,
        "v121_scalar_faasrank_noninferiority": candidate,
        "v121_input_locality_component_noninferiority": candidate,
        "v121_per_child_current_warm_downstream_locality_noninferiority": candidate,
        "v121_critical_frontier_substitution": candidate,
        "v121_critical_frontier_rank_source": (
            "immutable_srpt_remaining_critical_path_rank"
            if candidate
            else "not_applicable"
        ),
        "v121_service_directed_construction": candidate,
        "v121_service_choice_scope": (
            "all_current_players" if candidate else "not_applicable"
        ),
        "v121_dual_prefix_anchor_enabled": candidate,
        "v121_anchor_service_baseline_state": (
            "independent_exact_anchor_native_order_prefix"
            if candidate
            else "not_applicable"
        ),
        "v121_candidate_service_state": (
            "evolving_alternative_native_order_prefix"
            if candidate
            else "not_applicable"
        ),
        "v121_dual_prefix_inputs_finite_fail_closed": candidate,
        "v121_completed_changed_player_margin_enabled": candidate,
        "v121_completed_changed_player_margin_numerator": 9 if candidate else None,
        "v121_completed_changed_player_margin_denominator": 10 if candidate else None,
        "v121_completed_changed_player_definition": (
            "alternative_node_differs_from_exact_anchor_node"
            if candidate
            else "not_applicable"
        ),
        "v121_noncritical_exact_anchor": False,
        "v121_complete_summed_critical_service_proxy_strictly_lower": candidate,
        "v121_complete_routed_score_nonworse": candidate,
        "v121_complete_exact_ocs_score_nonworse": candidate,
        "v121_complete_immutable_baseline_welfare_nonworse": candidate,
        "v121_outcome_fields_drive_policy": False,
        "v121_scenario_or_burst_label_used_by_policy": False,
        "v121_completion_or_performance_fields_used_by_policy": False,
        "v121_future_arrivals_used_by_policy": False,
    }
    _require(
        run["experiment_id"] == "E3"
        and run["method"] == "sche_nash"
        and run["seed"] in TRAINING_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced"
        and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
        and run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
        == expected["profile"]
        and all(metadata.get(key) == value for key, value in required.items()),
        f"V121 run boundary changed: {run['run_id']}",
    )


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V121 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V121 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V121 plan changed")
    plan = read_json(PLAN)
    _require(plan.get("formal_results_eligible") is False, "V121 eligibility changed")
    _require(PREPARED.is_file(), f"missing V121 prepared receipt: {PREPARED}")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V121 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("other_unopened_inputs_generated") is False
        and set(prepared.get("training_seeds", [])) == TRAINING_SEEDS
        and prepared.get("untouched_confirmation_seeds") == CONFIRMATION_SEEDS
        and prepared.get("previous_confirmation_seeds_remaining_sealed")
        == PREVIOUS_CONFIRMATION_SEEDS
        and prepared.get("other_unopened_seeds_untouched") == OTHER_UNOPENED_SEEDS
        and prepared.get("arm_online_runs") == 18
        and prepared.get("arm_reference_builds") == 18
        and prepared.get("V120_result_receipt_hash") == V120_RESULT_RECEIPT_HASH
        and prepared.get("V120_result_receipt_commit") == V120_RESULT_RECEIPT_COMMIT,
        "V121 prepared scientific boundary changed",
    )
    tape_evidence, tape_catalog_evidence = _verify_tape_catalog()
    reference_roots, reference_ledger_hashes = _verify_reference_stage_ledgers()

    run_evidence: list[dict[str, Any]] = []
    reference_evidence: list[dict[str, Any]] = []
    pairing_evidence: list[dict[str, Any]] = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    paired_inputs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    ready_manifests: dict[str, dict[str, Any]] = {}

    for arm_id, expected in ARMS.items():
        paths = _arm_paths(arm_id)
        _require(paths["ready"].is_file(), f"missing V121 ready manifest: {arm_id}")
        manifest = load_and_validate_manifest(paths["ready"])
        _require(
            len(manifest["runs"]) == expected["run_count"]
            and manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_faasrank_models_bound") is False
            and manifest.get("all_references_bound") is True,
            f"V121 ready boundary changed: {arm_id}",
        )
        ready_manifests[arm_id] = {
            "path": str(paths["ready"]),
            "file_sha256": file_hash(paths["ready"]),
            "manifest_hash": manifest["manifest_hash"],
        }

        references = read_json(paths["references"])
        reference_catalog_hash = _assert_hashed_object(
            references, "catalog_hash", f"V121 references {arm_id}"
        )
        entries = references.get("entries")
        declared_keys = {
            item["key"] for item in manifest["reference_build_dependencies"]
        }
        _require(
            isinstance(entries, dict)
            and set(entries) == declared_keys
            and len(entries) == expected["run_count"],
            f"V121 reference key set changed: {arm_id}",
        )
        for key, entry in sorted(entries.items()):
            info = inspect_reference_table(Path(entry["path"]))
            _require(
                all(
                    getattr(info, field) == entry[field]
                    for field in (
                        "sha256",
                        "bytes",
                        "line_count",
                        "state_pair_sequence_sha256",
                    )
                )
                and file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"]
                and file_hash(Path(entry["build_process_observation_path"]))
                == entry["build_process_observation_sha256"],
                f"V121 reference evidence changed: {key}",
            )
            reference_evidence.append(
                {
                    "arm_id": arm_id,
                    "key": key,
                    "sha256": entry["sha256"],
                    "receipt_sha256": entry["receipt_sha256"],
                    "build_spec_hash": entry["build_spec_hash"],
                    "workload_tape_sha256": entry["workload_tape_sha256"],
                    "catalog_hash": reference_catalog_hash,
                }
            )
        reference_last_hash = reference_ledger_hashes[reference_roots[arm_id]]

        pairing = read_json(paths["pairing"])
        _require(
            pairing.get("passed") is True
            and pairing.get("failed_group_count") == 0
            and pairing.get("run_count") == expected["run_count"]
            and pairing.get("group_count") == expected["run_count"],
            f"V121 pairing changed: {arm_id}",
        )
        pairing_evidence.append(
            {
                "arm_id": arm_id,
                "file_sha256": file_hash(paths["pairing"]),
                "run_count": pairing["run_count"],
                "group_count": pairing["group_count"],
                "passed": True,
            }
        )

        workspace = paths["workspace"]
        expected_ids = {run["run_id"] for run in manifest["runs"]}
        actual_ids = {
            path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
        }
        _require(actual_ids == expected_ids, f"V121 canonical set changed: {arm_id}")
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V121 online quarantine is nonempty: {arm_id}",
        )
        ledger_rows, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
        _assert_ledger_contract(
            ledger_rows,
            Counter(
                {
                    "batch_started": 1,
                    "attempt_started": expected["run_count"],
                    "attempt_canonicalized": expected["run_count"],
                    "batch_finished": 1,
                }
            ),
            f"V121 online {arm_id}",
        )

        for run in manifest["runs"]:
            _validate_run_boundary(run, arm_id, expected)
            canonical = workspace / "canonical" / run["run_id"]
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            diagnostics = _validate_admitted_work_diagnostics(run, canonical, expected)
            attempt = read_json(canonical / "attempt.json")
            qc = read_json(canonical / "qc_report.json")
            audit_manifest = read_json(canonical / "manifest.json")
            _require(
                attempt.get("attempt") == 1
                and attempt.get("status") == "qc_pass"
                and attempt.get("classification") == "qc_pass"
                and attempt.get("timed_out") is False
                and attempt.get("exit_code") == 0
                and qc.get("passed") is True
                and qc.get("classification") == "qc_pass",
                f"V121 canonical status changed: {run['run_id']}",
            )
            runtime = {
                "binary_sha256": audit_manifest["adapter_binary"]["verified_sha256"],
                "git_commit": audit_manifest["software_environment"]["git"]["commit"],
                "python_executable_sha256": audit_manifest["software_environment"][
                    "python"
                ]["executable_sha256"],
                "cargo_lock_sha256": audit_manifest["software_environment"][
                    "cargo_lock"
                ]["sha256"],
            }
            for field, value in runtime.items():
                runtime_values[field].add(str(value))
            scenario = _scenario(run)
            paired_inputs[(scenario, run["seed"])].append(
                {
                    "arm_id": arm_id,
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "workload_tape_key": run["workload_tape"]["key"],
                    "workload_spec_hash": run["workload_spec_hash"],
                    "capture_environment_sha256": run["workload_tape"][
                        "capture_environment"
                    ]["capture_environment_sha256"],
                    "common_hpa_hash": run["common_hpa_hash"],
                    "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
                    "faasrank_model": run["simulator_experiment"]["faasrank_model"],
                    "simulation": run["simulation"],
                }
            )
            run_evidence.append(
                {
                    "arm_id": arm_id,
                    "run_id": run["run_id"],
                    "experiment_id": "E3",
                    "scenario": scenario,
                    "seed": run["seed"],
                    "run_spec_hash": run["run_spec_hash"],
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "reference_key": run["reference_dependency"]["key"],
                    "result_sha256": attempt["result_sha256"],
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "attempt": 1,
                    "classification": "qc_pass",
                    "admitted_work_diagnostics": diagnostics,
                    "ledger_last_hash": ledger_last_hash,
                    "reference_ledger_last_hash": reference_last_hash,
                }
            )

    _require(len(run_evidence) == 18, "V121 run evidence count must be 18")
    _require(len(reference_evidence) == 18, "V121 reference evidence count must be 18")
    _require(len(tape_evidence) == 12, "V121 tape evidence count must be 12")
    candidate_diagnostics = [
        row["admitted_work_diagnostics"]
        for row in run_evidence
        if ARMS[row["arm_id"]]["role"] == "candidate"
    ]
    anchor_diagnostics = [
        row["admitted_work_diagnostics"]
        for row in run_evidence
        if ARMS[row["arm_id"]]["role"] == "anchor"
    ]
    _require(
        sum(
            row["componentwise_evaluated_window_count"] for row in candidate_diagnostics
        )
        > 0
        and sum(
            row["componentwise_accepted_window_count"] for row in candidate_diagnostics
        )
        > 0
        and sum(
            row["componentwise_rejected_window_count"] for row in candidate_diagnostics
        )
        > 0
        and sum(
            row["componentwise_worse_player_count"] for row in candidate_diagnostics
        )
        > 0,
        "V121 componentwise certificate did not exercise both accept and reject paths",
    )
    _require(
        sum(
            row["changed_player_margin_evaluated_window_count"]
            for row in candidate_diagnostics
        )
        > 0
        and sum(
            row["changed_player_margin_accepted_window_count"]
            for row in candidate_diagnostics
        )
        > 0
        and sum(
            row["changed_player_margin_rejected_window_count"]
            for row in candidate_diagnostics
        )
        > 0
        and sum(row["changed_player_count"] for row in candidate_diagnostics) > 0
        and sum(
            row["changed_player_margin_violation_count"]
            for row in candidate_diagnostics
        )
        > 0,
        "V121 changed-player margin did not exercise both accept and reject paths",
    )
    _require(
        sum(
            row["componentwise_input_unavailable_count"]
            for row in candidate_diagnostics
        )
        == 0
        and sum(
            row["componentwise_target_player_count"] for row in candidate_diagnostics
        )
        == sum(
            row["componentwise_compared_player_count"] for row in candidate_diagnostics
        ),
        "V121 all-player componentwise evidence is unavailable or incomplete",
    )
    _require(
        sum(
            row["service_choice_evaluated_player_count"]
            for row in candidate_diagnostics
        )
        > 0
        and sum(
            row["service_choice_input_unavailable_player_count"]
            for row in candidate_diagnostics
        )
        == 0
        and sum(
            row["anchor_prefix_completed_player_count"] for row in candidate_diagnostics
        )
        == sum(
            row["service_choice_evaluated_player_count"]
            for row in candidate_diagnostics
        )
        and sum(
            row["anchor_prefix_input_unavailable_player_count"]
            for row in candidate_diagnostics
        )
        == 0
        and sum(
            row["candidate_prefix_input_unavailable_count"]
            for row in candidate_diagnostics
        )
        == 0
        and sum(
            row["service_choice_critical_substitution_count"]
            for row in candidate_diagnostics
        )
        > 0
        and sum(
            row["service_choice_noncritical_substitution_count"]
            for row in candidate_diagnostics
        )
        > 0,
        "V121 service-directed construction did not exercise both critical and "
        "noncritical substitution paths",
    )
    _require(
        all(
            row["componentwise_evaluated_window_count"] == 0
            and row["componentwise_accepted_window_count"] == 0
            and row["componentwise_rejected_window_count"] == 0
            and row["componentwise_target_player_count"] == 0
            and row["changed_player_margin_evaluated_window_count"] == 0
            and row["changed_player_margin_accepted_window_count"] == 0
            and row["changed_player_margin_rejected_window_count"] == 0
            and row["changed_player_count"] == 0
            and row["changed_player_margin_violation_count"] == 0
            and row["service_choice_target_player_count"] == 0
            and row["service_choice_evaluated_player_count"] == 0
            and row["service_choice_substitution_count"] == 0
            and row["anchor_prefix_completed_player_count"] == 0
            and row["anchor_prefix_input_unavailable_player_count"] == 0
            and row["candidate_prefix_input_unavailable_count"] == 0
            for row in anchor_diagnostics
        ),
        "V121 anchor unexpectedly exercised the service construction or certificate",
    )
    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V121 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V121 runtime git identity is not singular: {git_commits}",
    )
    _require(len(paired_inputs) == 9, "V121 paired input product changed")
    for (scenario, seed), rows in paired_inputs.items():
        _require(len(rows) == 2, f"V121 paired arm count changed: {scenario}/{seed}")
        for field in (
            "workload_tape_sha256",
            "workload_tape_key",
            "workload_spec_hash",
            "capture_environment_sha256",
            "common_hpa_hash",
            "sla_artifact_sha256",
            "faasrank_model",
            "simulation",
        ):
            _require(
                len({object_hash(row[field]) for row in rows}) == 1,
                f"V121 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V121 common HPA changed: {scenario}/{seed}",
        )

    output_payload = {
        "schema_version": "NSE_E3_FINAL_MARGIN_BLIND_AUDIT_V121_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "mechanism_diagnostic_windows_parsed": sum(
            run["admitted_work_diagnostics"]["window_count"] for run in run_evidence
        ),
        "mechanism_diagnostics_consulted_for_performance_selection": False,
        "performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "other_unopened_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "runtime_identity": {
            **EXPECTED_RUNTIME,
            "git_commit": next(iter(runtime_values["git_commit"])),
        },
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "previous_confirmation_seeds_remaining_sealed": PREVIOUS_CONFIRMATION_SEEDS,
        "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
        "arm_count": len(ARMS),
        "run_count": len(run_evidence),
        "reference_count": len(reference_evidence),
        "tape_count": len(tape_evidence),
        "ready_manifests": ready_manifests,
        "tape_catalog": tape_catalog_evidence,
        "pairing_audits": pairing_evidence,
        "tapes": tape_evidence,
        "references": reference_evidence,
        "runs": run_evidence,
    }
    output_payload["audit_hash"] = object_hash(output_payload)
    write_json_atomic(output, output_payload)
    return output_payload


def main() -> None:
    audit = run_blind_audit()
    print(OUTPUT)
    print(file_hash(OUTPUT))
    print(audit["audit_hash"])


if __name__ == "__main__":
    main()
