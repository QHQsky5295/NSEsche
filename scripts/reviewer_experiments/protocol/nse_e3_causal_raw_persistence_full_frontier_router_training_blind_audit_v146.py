from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_execute_v146 import (
    EXECUTION_RECEIPT,
    READY_SCHEDULE,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_prepare_v146 import (
    ARM_ID,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    EXPERT_LIFECYCLE,
    NEW_CONFIRMATION_SEEDS,
    NATIVE_MEMBERS,
    PERSISTENCE_BASELINE_FRAMES,
    PERSISTENCE_EVALUATION_AGE_FRAMES,
    PERSISTENCE_RECENT_FRAMES,
    PERSISTENCE_THRESHOLD_DENOMINATOR,
    PERSISTENCE_THRESHOLD_NUMERATOR,
    PLAYER_FRONTIER,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    PYTHON_SHA256,
    ROOT,
    RUNTIME_NATIVE_KINDS,
    SELECTION_RULE,
    SERVICE_CERTIFICATE_SCOPE,
    SHOCK_ACTIVE_FRAMES,
    SHOCK_BASELINE_FRAMES,
    SHOCK_RECENT_FRAMES,
    SHOCK_THRESHOLD_DENOMINATOR,
    SHOCK_THRESHOLD_NUMERATOR,
    TRAINING_SEED_LIST,
    V142_BASELINE_PAIRING,
    V142_BASELINE_READY,
    V145_BLIND_HASH,
    V145_BLIND_SHA256,
    V145_PLAN_SHA256,
    V145_RESULT_HASH,
    V145_RESULT_SHA256,
    V146_SERVICE_STATE_DOMAIN,
    V146_WELFARE_STATE_DOMAIN,
    pairing_path,
    paths,
    ready_manifest_path,
    reference_catalog_path,
    scenario_id,
    workspace_path,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_blind_audit_v143 import (
    EXPECTED_COMMON_HPA_SHA256,
    _verify_tapes,
    _verify_v142_baselines,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_blind_audit_v142 import (
    _f32,
    _finite,
    _runtime_evidence,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
)
from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_blind_audit_v100 import (
    _assert_hashed_object,
    _read_ledger,
    _require,
    _stage_root_from_receipts,
)
from scripts.reviewer_experiments.protocol.reference import inspect_reference_table
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


PREPARED = ROOT / "prepared-manifest-v146.json"
OUTPUT = ROOT / "joint-blind-audit-v146-training.json"
RESULT = ROOT / "training-result-v146.json"
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
EXPECTED_REASONS = {
    "invalid": "arrival_history_or_arithmetic_fail_closed_greedy",
    "quiet": "quiet_before_first_episode_greedy",
    "unclassified": "first_episode_unclassified_through_age54_greedy",
    "short": "age55_raw_persistence_short_retained_greedy",
    "sustained": "age55_raw_persistence_sustained_retained_faasrank",
    "load_least": "recurrent_episode_retained_load_least",
}


def _expected_route(
    history_valid: bool,
    episode_count: int,
    persistence_evaluated: bool,
    first_episode_sustained: bool,
) -> tuple[str, str]:
    if not history_valid:
        return "greedy", EXPECTED_REASONS["invalid"]
    if episode_count >= 2:
        return "load_least", EXPECTED_REASONS["load_least"]
    if persistence_evaluated and first_episode_sustained:
        return "faasrank", EXPECTED_REASONS["sustained"]
    if persistence_evaluated:
        return "greedy", EXPECTED_REASONS["short"]
    if episode_count == 0:
        return "greedy", EXPECTED_REASONS["quiet"]
    return "greedy", EXPECTED_REASONS["unclassified"]


def _persistence_comparison(recent: int, baseline: int) -> dict[str, Any]:
    if (
        type(recent) is not int
        or recent < 0
        or type(baseline) is not int
        or baseline < 0
    ):
        raise ValueError("V146 persistence counts must be nonnegative integers")
    recent_scaled = (
        recent * PERSISTENCE_BASELINE_FRAMES * PERSISTENCE_THRESHOLD_DENOMINATOR
    )
    baseline_scaled = (
        baseline * PERSISTENCE_RECENT_FRAMES * PERSISTENCE_THRESHOLD_NUMERATOR
    )
    return {
        "recent_scaled": recent_scaled,
        "baseline_scaled": baseline_scaled,
        "sustained": recent_scaled >= baseline_scaled,
    }


def _candidate_hash_agreement(candidates: list[Mapping[str, Any]]) -> tuple[int, int]:
    """Return distinct hash pairs and coincident expert outputs.

    Independent native experts may legitimately select the same complete placement in a
    window.  Expert identity, lifecycle, feasibility, and selected-stream equality are
    audited separately; agreement between experts is therefore diagnostic rather than
    an integrity failure.
    """

    pairs = {
        (candidate["ordered_command_hash"], candidate["assignment_hash"])
        for candidate in candidates
    }
    return len(pairs), len(candidates) - len(pairs)


def _validate_guard(
    run_id: str,
    line_number: int,
    players: int,
    selected: dict[str, Any] | None,
    native: Mapping[str, Any],
    guard: Mapping[str, Any],
) -> tuple[str, bool]:
    reason = guard.get("reason")
    _require(isinstance(reason, str), "invalid V146 guard reason")
    initializer_players = native.get("initializer_readiness_service_players")
    proposal_players = native.get("proposal_readiness_service_players")
    _require(
        type(initializer_players) is int
        and initializer_players >= 0
        and type(proposal_players) is int
        and proposal_players >= 0
        and native.get("certificate_uses_completion_outcomes") is False
        and native.get("service_certificate_scope") == SERVICE_CERTIFICATE_SCOPE,
        f"V146 native service boundary changed: {run_id}:{line_number}",
    )
    if players == 0:
        _require(
            selected is None
            and native.get("initializer_readiness_service_complete") is False
            and native.get("proposal_readiness_service_complete") is False
            and initializer_players == proposal_players == 0
            and guard.get("evaluated") is False
            and guard.get("accepted") is False
            and guard.get("fallback_applied") is False
            and reason == "not_applicable",
            f"V146 empty guard changed: {run_id}:{line_number}",
        )
        return reason, False

    _require(
        selected is not None
        and native.get("kind") == selected["kind"]
        and native.get("valid") is True
        and native.get("commands") == players
        and native.get("duplicate_commands") == 0
        and native.get("unexpected_messages") == 0
        and native.get("missing_players") == 0
        and native.get("extra_players") == 0
        and native.get("infeasible_commands") == 0
        and native.get("anchor_assignment_hash") == selected["assignment_hash"]
        and native.get("ordered_command_hash") == selected["ordered_command_hash"]
        and native.get("initializer_readiness_service_complete") is True
        and initializer_players == players
        and native.get("initializer_readiness_service_sum") == selected["service_sum"]
        and native.get("initializer_readiness_service_max") == selected["service_max"],
        f"V146 selected initializer changed: {run_id}:{line_number}",
    )
    proposal_complete = native.get("proposal_readiness_service_complete") is True
    initializer_sum = float(native["initializer_readiness_service_sum"])
    initializer_max = float(native["initializer_readiness_service_max"])
    if proposal_complete:
        _require(
            proposal_players == players
            and all(
                _finite(native.get(field))
                for field in (
                    "proposal_readiness_service_sum",
                    "proposal_readiness_service_max",
                    "readiness_service_sum_delta",
                    "readiness_service_max_delta",
                )
            ),
            f"V146 proposal service changed: {run_id}:{line_number}",
        )
        proposal_sum = float(native["proposal_readiness_service_sum"])
        proposal_max = float(native["proposal_readiness_service_max"])
        _require(
            native.get("readiness_service_sum_delta") == proposal_sum - initializer_sum
            and native.get("readiness_service_max_delta")
            == proposal_max - initializer_max,
            f"V146 proposal deltas changed: {run_id}:{line_number}",
        )
    else:
        _require(
            proposal_players == 0
            and guard.get("accepted") is False
            and reason == "proposal_readiness_service_unavailable",
            f"V146 unavailable proposal changed: {run_id}:{line_number}",
        )
        proposal_sum = float("inf")
        proposal_max = float("inf")

    initializer_welfare = guard.get("initializer_baseline_welfare")
    proposal_welfare = guard.get("proposal_baseline_welfare")
    welfare_delta = guard.get("baseline_welfare_delta")
    _require(
        guard.get("evaluated") is True
        and _finite(initializer_welfare)
        and _finite(proposal_welfare)
        and _finite(welfare_delta)
        and float(initializer_welfare) == float(selected["paper_welfare"])
        and _f32(float(proposal_welfare) - float(initializer_welfare))
        == float(welfare_delta),
        f"V146 welfare certificate changed: {run_id}:{line_number}",
    )
    if not proposal_complete:
        expected_reason = "proposal_readiness_service_unavailable"
    elif _f32(float(proposal_welfare) + _f32(1.0e-6)) < float(initializer_welfare):
        expected_reason = "paper_welfare_worse"
    elif proposal_max > initializer_max + 1.0e-6:
        expected_reason = "readiness_service_max_worse"
    elif proposal_sum + 1.0e-6 >= initializer_sum:
        expected_reason = "readiness_service_sum_not_strictly_improved"
    else:
        expected_reason = "accepted"
    accepted = expected_reason == "accepted"
    _require(
        reason == expected_reason
        and guard.get("accepted") is accepted
        and guard.get("fallback_applied") is (not accepted),
        f"V146 guard disposition changed: {run_id}:{line_number}",
    )
    return reason, accepted


def _validate_v146_native_diagnostics(
    run: dict[str, Any], canonical: Path
) -> dict[str, Any]:
    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V146 Nash diagnostics: {run['run_id']}")
    counts = Counter()
    reasons = Counter()
    previous_active = False
    expected_episode_count = 0
    first_start: int | None = None
    baseline_80_count: int | None = None
    recent_5_count: int | None = None
    persistence_evaluated = False
    first_sustained = False
    raw_arrivals: list[int] = []
    active_player_windows = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") == "run_config":
                counts["run_config"] += 1
                _require(
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("operational_player_frontier") == PLAYER_FRONTIER
                    and event.get("operational_expert_proxy_contract") is None,
                    f"V146 run-config changed: {run['run_id']}:{line_number}",
                )
                continue
            if event.get("kind") != "window":
                continue
            frame = counts["windows"]
            counts["windows"] += 1
            decision = event.get("decision")
            _require(isinstance(decision, dict), "missing V146 decision diagnostics")
            portfolio = decision.get("native_portfolio")
            native = decision.get("native_shadow_anchor")
            guard = decision.get("window_safe_guard")
            detector = decision.get("load_least_dominance_gate", {}).get(
                "causal_arrival_shock"
            )
            persistence = (
                portfolio.get("v145_causal_raw_persistence")
                if isinstance(portfolio, dict)
                else None
            )
            full_frontier = (
                portfolio.get("v146_causal_raw_persistence_full_frontier")
                if isinstance(portfolio, dict)
                else None
            )
            _require(
                all(
                    isinstance(item, dict)
                    for item in (
                        portfolio,
                        native,
                        guard,
                        detector,
                        persistence,
                        full_frontier,
                    )
                ),
                f"missing V146 persistence diagnostics: {run['run_id']}:{line_number}",
            )
            raw_current = persistence.get("raw_first_seen_current_frame")
            _require(
                persistence.get("enabled") is True
                and persistence.get("frame") == frame
                and persistence.get("arrival_history_valid") is True
                and persistence.get("frame_reset_this_window") is False
                and persistence.get("history_discontinuity_this_window") is False
                and persistence.get("checked_arithmetic_valid") is True
                and type(raw_current) is int
                and raw_current >= 0
                and persistence.get("selector_inputs")
                == "first_seen_arrival_counts_and_current_frame_only"
                and persistence.get("scenario_seed_future_or_outcome_inputs_used")
                is False,
                f"V146 causal input boundary changed: {run['run_id']}:{line_number}",
            )
            raw_arrivals.append(raw_current)
            shock_active = detector.get("active")
            _require(
                detector.get("gate_enabled") is True
                and detector.get("baseline_frames") == SHOCK_BASELINE_FRAMES
                and detector.get("recent_frames") == SHOCK_RECENT_FRAMES
                and detector.get("threshold_numerator") == SHOCK_THRESHOLD_NUMERATOR
                and detector.get("threshold_denominator") == SHOCK_THRESHOLD_DENOMINATOR
                and detector.get("active_frames") == SHOCK_ACTIVE_FRAMES
                and detector.get("uses_first_seen_request_ids_only") is True
                and type(shock_active) is bool
                and persistence.get("rolling_shock_active") is shock_active,
                f"V146 detector changed: {run['run_id']}:{line_number}",
            )
            started = shock_active and not previous_active
            if started:
                expected_episode_count += 1
                counts["episode_starts"] += 1
                if expected_episode_count == 1:
                    first_start = frame
                    _require(
                        frame >= PERSISTENCE_BASELINE_FRAMES,
                        f"V146 first episode lacks preceding baseline: {run['run_id']}:{line_number}",
                    )
                    baseline_80_count = sum(
                        raw_arrivals[frame - PERSISTENCE_BASELINE_FRAMES : frame]
                    )
                    _require(
                        baseline_80_count >= 20,
                        f"V146 first episode baseline is ineligible: {run['run_id']}:{line_number}",
                    )
            expected_first_age = (
                frame - first_start + 1 if first_start is not None else 0
            )
            if (
                first_start is not None
                and expected_first_age == PERSISTENCE_EVALUATION_AGE_FRAMES
                and not persistence_evaluated
            ):
                persistence_evaluated = True
                counts["age55_evaluations"] += 1
                recent_5_count = sum(raw_arrivals[-PERSISTENCE_RECENT_FRAMES:])
                _require(
                    baseline_80_count is not None,
                    f"V146 persistence baseline disappeared: {run['run_id']}:{line_number}",
                )
                comparison = _persistence_comparison(recent_5_count, baseline_80_count)
                first_sustained = comparison["sustained"]
                counts[
                    "sustained_evaluations" if first_sustained else "short_evaluations"
                ] += 1
            expected_comparison = None
            if persistence_evaluated:
                _require(
                    baseline_80_count is not None and recent_5_count is not None,
                    f"V146 evaluated persistence state is incomplete: {run['run_id']}:{line_number}",
                )
                expected_comparison = _persistence_comparison(
                    recent_5_count, baseline_80_count
                )
            selected_kind, selection_reason = _expected_route(
                True,
                expected_episode_count,
                persistence_evaluated,
                first_sustained,
            )
            _require(
                persistence.get("episode_started_this_window") is started
                and persistence.get("episode_count") == expected_episode_count
                and persistence.get("first_episode_start_frame") == first_start
                and persistence.get("first_episode_age_frames") == expected_first_age
                and persistence.get("baseline_frames") == PERSISTENCE_BASELINE_FRAMES
                and persistence.get("baseline_80_count") == baseline_80_count
                and persistence.get("recent_frames") == PERSISTENCE_RECENT_FRAMES
                and persistence.get("recent_5_count") == recent_5_count
                and persistence.get("evaluation_age_frames")
                == PERSISTENCE_EVALUATION_AGE_FRAMES
                and persistence.get("threshold_numerator")
                == PERSISTENCE_THRESHOLD_NUMERATOR
                and persistence.get("threshold_denominator")
                == PERSISTENCE_THRESHOLD_DENOMINATOR
                and persistence.get("persistence_evaluated_once")
                is persistence_evaluated
                and persistence.get("persistence_evaluation_count")
                == int(persistence_evaluated)
                and persistence.get("persistence_comparison") == expected_comparison
                and persistence.get("first_episode_sustained") is first_sustained
                and persistence.get("selected_kind") == selected_kind
                and persistence.get("selection_reason") == selection_reason,
                f"V146 state transition changed: {run['run_id']}:{line_number}",
            )
            previous_active = bool(shock_active)

            players = decision.get("request_function_players")
            _require(
                type(players) is int
                and players >= 0
                and decision.get("player_frontier") == PLAYER_FRONTIER,
                f"V146 player count changed: {run['run_id']}:{line_number}",
            )
            source_counts = full_frontier.get("source_native_command_counts")
            source_hashes = full_frontier.get("source_native_ordered_command_hashes")
            projected_counts = full_frontier.get("projected_command_counts")
            projected_hashes = full_frontier.get("projected_ordered_command_hashes")
            dropped_counts = full_frontier.get("dropped_noncohort_command_counts")
            _require(
                full_frontier.get("enabled") is True
                and full_frontier.get("frame") == frame
                and full_frontier.get("player_frontier") == PLAYER_FRONTIER
                and full_frontier.get("collect_task_config") == PLAYER_FRONTIER
                and full_frontier.get("common_hpa_candidate_filter_only") is True
                and full_frontier.get("full_frontier_feasible_player_count") == players
                and full_frontier.get(
                    "all_three_projected_assignments_cover_exact_full_feasible_cohort"
                )
                is True
                and full_frontier.get("selected_kind") == selected_kind
                and full_frontier.get("selection_reason") == selection_reason
                and all(
                    isinstance(item, dict)
                    for item in (
                        source_counts,
                        source_hashes,
                        projected_counts,
                        projected_hashes,
                        dropped_counts,
                    )
                ),
                f"V146 full-frontier boundary changed: {run['run_id']}:{line_number}",
            )
            for kind in RUNTIME_NATIVE_KINDS:
                source_count = source_counts.get(kind)
                projected_count = projected_counts.get(kind)
                _require(
                    type(source_count) is int
                    and source_count >= players
                    and projected_count == players
                    and dropped_counts.get(kind) == source_count - players
                    and type(source_hashes.get(kind)) is int
                    and type(projected_hashes.get(kind)) is int,
                    f"V146 {kind} projection changed: {run['run_id']}:{line_number}",
                )
                counts[f"source_{kind}_commands"] += source_count
                counts[f"projected_{kind}_commands"] += projected_count
                counts[f"dropped_{kind}_commands"] += source_count - players
            candidates = portfolio.get("candidates")
            selected_candidate: dict[str, Any] | None = None
            if players == 0:
                _require(
                    portfolio.get("enabled") is False
                    and portfolio.get("rule") is None
                    and portfolio.get("candidate_count") == 0
                    and candidates == []
                    and portfolio.get("selected_kind") is None,
                    f"V146 empty portfolio changed: {run['run_id']}:{line_number}",
                )
            else:
                active_player_windows += 1
                _require(
                    portfolio.get("enabled") is True
                    and portfolio.get("rule") == "causal_raw_persistence_full_frontier"
                    and portfolio.get("deterministic_selection_reason")
                    == selection_reason
                    and portfolio.get("candidate_count") == len(RUNTIME_NATIVE_KINDS)
                    and isinstance(candidates, list)
                    and [item.get("kind") for item in candidates]
                    == RUNTIME_NATIVE_KINDS
                    and [item.get("selected") for item in candidates]
                    == [item.get("kind") == selected_kind for item in candidates]
                    and portfolio.get("selected_kind") == selected_kind,
                    f"V146 portfolio selection changed: {run['run_id']}:{line_number}",
                )
                for candidate in candidates:
                    _require(
                        candidate.get("valid") is True
                        and candidate.get("commands") == players
                        and candidate.get("duplicate_commands") == 0
                        and candidate.get("unexpected_messages") == 0
                        and candidate.get("missing_players") == 0
                        and candidate.get("extra_players") == 0
                        and candidate.get("infeasible_commands") == 0
                        and type(candidate.get("ordered_command_hash")) is int
                        and type(candidate.get("assignment_hash")) is int
                        and candidate.get("service_complete") is True
                        and candidate.get("service_players") == players
                        and projected_hashes.get(candidate.get("kind"))
                        == candidate.get("ordered_command_hash")
                        and all(
                            _finite(candidate.get(field))
                            for field in ("service_sum", "service_max", "paper_welfare")
                        ),
                        f"V146 candidate invalid: {run['run_id']}:{line_number}",
                    )
                distinct_hashes, coincident_outputs = _candidate_hash_agreement(
                    candidates
                )
                counts["candidate_distinct_hash_pairs"] += distinct_hashes
                counts["candidate_coincident_expert_outputs"] += coincident_outputs
                if coincident_outputs:
                    counts["candidate_agreement_windows"] += 1
                selected_candidate = next(
                    item for item in candidates if item["kind"] == selected_kind
                )
                counts[f"selected_{selected_kind}"] += 1

            initializations = persistence.get("shadow_initializations")
            totals = persistence.get("shadow_invocations_total")
            per_window = persistence.get("shadow_invocations_this_window")
            expected_per_window = {kind: 1 for kind in RUNTIME_NATIVE_KINDS}
            _require(
                initializations == {"greedy": 1, "faasrank": 1, "load_least": 1}
                and isinstance(totals, dict)
                and isinstance(per_window, dict)
                and per_window == expected_per_window
                and all(
                    totals.get(kind) == counts["windows"]
                    for kind in RUNTIME_NATIVE_KINDS
                )
                and persistence.get(
                    "all_three_shadows_advanced_exactly_once_this_window"
                )
                is True,
                f"V146 expert lifecycle changed: {run['run_id']}:{line_number}",
            )
            if selected_candidate is None:
                _require(
                    persistence.get("selected_native_ordered_command_hash") is None
                    or type(persistence.get("selected_native_ordered_command_hash"))
                    is int,
                    f"V146 empty command hash changed: {run['run_id']}:{line_number}",
                )
                _require(
                    persistence.get("selected_native_assignment_hash") is None
                    or type(persistence.get("selected_native_assignment_hash")) is int,
                    f"V146 empty assignment hash changed: {run['run_id']}:{line_number}",
                )
                _require(
                    persistence.get("selected_initializer_dispatched_exactly") is False
                    and persistence.get("accepted_nash_proposal_dispatched_exactly")
                    is False
                    and full_frontier.get("selected_initializer_dispatched_exactly")
                    is False
                    and full_frontier.get("accepted_nash_proposal_dispatched_exactly")
                    is False,
                    f"V146 empty dispatch changed: {run['run_id']}:{line_number}",
                )
            else:
                _require(
                    persistence.get("selected_native_ordered_command_hash")
                    == selected_candidate["ordered_command_hash"]
                    and persistence.get("selected_native_assignment_hash")
                    == selected_candidate["assignment_hash"]
                    and full_frontier.get("selected_native_ordered_command_hash")
                    == selected_candidate["ordered_command_hash"]
                    and full_frontier.get("selected_native_assignment_hash")
                    == selected_candidate["assignment_hash"],
                    f"V146 selected hashes changed: {run['run_id']}:{line_number}",
                )
            reason, accepted = _validate_guard(
                run["run_id"], line_number, players, selected_candidate, native, guard
            )
            reasons[reason] += 1
            if players > 0:
                _require(
                    persistence.get("selected_initializer_dispatched_exactly")
                    is (not accepted)
                    and persistence.get("accepted_nash_proposal_dispatched_exactly")
                    is accepted
                    and full_frontier.get("selected_initializer_dispatched_exactly")
                    is (not accepted)
                    and full_frontier.get("accepted_nash_proposal_dispatched_exactly")
                    is accepted
                    and type(persistence.get("final_assignment_hash")) is int
                    and full_frontier.get("final_assignment_hash")
                    == persistence.get("final_assignment_hash"),
                    f"V146 final dispatch changed: {run['run_id']}:{line_number}",
                )
            if accepted:
                counts["accepted_windows"] += 1

    _require(
        counts["run_config"] == 1, f"V146 run-config count changed: {run['run_id']}"
    )
    _require(counts["windows"] == 4000, f"V146 window count changed: {run['run_id']}")
    _require(active_player_windows > 0, f"V146 has no player windows: {run['run_id']}")
    return {
        "window_count": counts["windows"],
        "native_player_window_count": active_player_windows,
        "accepted_proposal_window_count": counts["accepted_windows"],
        "episode_count": expected_episode_count,
        "episode_start_count": counts["episode_starts"],
        "first_episode_start_frame": first_start,
        "baseline_80_count": baseline_80_count,
        "recent_5_count": recent_5_count,
        "persistence_evaluation_count": counts["age55_evaluations"],
        "short_evaluation_count": counts["short_evaluations"],
        "sustained_evaluation_count": counts["sustained_evaluations"],
        "first_episode_sustained": first_sustained,
        "selected_native_counts": {
            kind: counts[f"selected_{kind}"] for kind in RUNTIME_NATIVE_KINDS
        },
        "candidate_distinct_hash_pair_count": counts["candidate_distinct_hash_pairs"],
        "candidate_coincident_expert_output_count": counts[
            "candidate_coincident_expert_outputs"
        ],
        "candidate_agreement_window_count": counts["candidate_agreement_windows"],
        "guard_reasons": dict(sorted(reasons.items())),
        "native_selection_rule": SELECTION_RULE,
        "expert_lifecycle": EXPERT_LIFECYCLE,
        "player_frontier": PLAYER_FRONTIER,
        "source_native_command_totals": {
            kind: counts[f"source_{kind}_commands"] for kind in RUNTIME_NATIVE_KINDS
        },
        "projected_command_totals": {
            kind: counts[f"projected_{kind}_commands"] for kind in RUNTIME_NATIVE_KINDS
        },
        "dropped_noncohort_command_totals": {
            kind: counts[f"dropped_{kind}_commands"] for kind in RUNTIME_NATIVE_KINDS
        },
        "performance_fields_consulted": False,
    }


def _verify_references(candidate_manifest: Mapping[str, Any]) -> dict[str, Any]:
    path = reference_catalog_path(ROOT)
    _require(path.is_file(), "missing V146 reference catalog")
    catalog = read_json(path)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V146 references")
    entries = catalog.get("entries")
    expected = {
        run["reference_dependency"]["key"] for run in candidate_manifest["runs"]
    }
    _require(
        isinstance(entries, dict)
        and set(entries) == expected
        and len(entries) == 9
        and candidate_manifest.get("reference_catalog_hash") == catalog_hash,
        "V146 reference product changed",
    )
    stage_root = _stage_root_from_receipts(
        entries, "receipt_path", 9, "V146 references"
    )
    ledger, last_hash = _read_ledger(stage_root / "ledger.jsonl")
    counts = Counter(row["event_type"] for row in ledger)
    _require(
        counts == Counter({"reference_build_canonicalized": 9})
        and not list((stage_root / "quarantine").glob("**/attempt-*")),
        f"V146 reference ledger changed: {counts}",
    )
    bound = {
        run["reference_dependency"]["key"]: run["reference_dependency"]
        for run in candidate_manifest["runs"]
    }
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_reference_table(Path(entry["path"]))
        dependency = bound[key]
        fields = (
            "path",
            "sha256",
            "bytes",
            "line_count",
            "state_pair_sequence_sha256",
            "receipt_path",
            "receipt_sha256",
            "build_spec_hash",
            "build_process_observation_path",
            "build_process_observation_sha256",
        )
        _require(
            all(dependency.get(field) == entry.get(field) for field in fields)
            and info.sha256 == entry["sha256"]
            and info.bytes == entry["bytes"]
            and info.line_count == entry["line_count"]
            and info.state_pair_sequence_sha256 == entry["state_pair_sequence_sha256"]
            and file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"]
            and file_hash(Path(entry["build_process_observation_path"]))
            == entry["build_process_observation_sha256"],
            f"V146 reference evidence changed: {key}",
        )
        evidence.append(
            {
                "key": key,
                "sha256": entry["sha256"],
                "receipt_sha256": entry["receipt_sha256"],
                "build_spec_hash": entry["build_spec_hash"],
                "workload_tape_sha256": entry["workload_tape_sha256"],
            }
        )
    return {
        "path": str(path),
        "file_sha256": file_hash(path),
        "catalog_hash": catalog_hash,
        "ledger_last_hash": last_hash,
        "entries": evidence,
    }


def _validate_execution_receipt() -> dict[str, Any]:
    schedule_path = ROOT / READY_SCHEDULE.name
    receipt_path = ROOT / EXECUTION_RECEIPT.name
    _require(schedule_path.is_file(), "missing V146 ready schedule")
    _require(receipt_path.is_file(), "missing V146 execution receipt")
    schedule = read_json(schedule_path)
    schedule_hash = _assert_hashed_object(
        schedule, "schedule_hash", "V146 ready schedule"
    )
    frozen_manifest = schedule.get("ready_manifest")
    _require(
        isinstance(schedule.get("schedule"), list)
        and len(schedule["schedule"]) == 9
        and len({item.get("run_id") for item in schedule["schedule"]}) == 9
        and isinstance(frozen_manifest, dict)
        and frozen_manifest.get("run_count") == 9
        and Path(str(frozen_manifest.get("path"))).is_file()
        and file_hash(Path(str(frozen_manifest["path"])))
        == frozen_manifest.get("file_sha256"),
        "V146 ready schedule binding changed",
    )
    receipt = read_json(receipt_path)
    receipt_hash = _assert_hashed_object(
        receipt, "receipt_hash", "V146 execution receipt"
    )
    _require(
        receipt.get("candidate_performance_summaries_parsed") == 0
        and receipt.get("performance_results_consulted_for_mechanism_design") is True
        and receipt.get("plan_sha256") == PLAN_SHA256
        and receipt.get("ready_schedule_hash") == schedule_hash
        and receipt.get("dispatch_count") == 9
        and receipt.get("all_exit_codes_zero") is True
        and len(receipt.get("dispatches", [])) == 9,
        "V146 execution boundary changed",
    )
    for scheduled, dispatched in zip(schedule["schedule"], receipt["dispatches"]):
        _require(
            all(
                scheduled[field] == dispatched[field]
                for field in ("ordinal", "scenario", "seed", "run_id")
            )
            and dispatched.get("exit_code") == 0,
            f"V146 frozen dispatch changed: {scheduled['ordinal']}",
        )
    return {
        "ready_schedule_path": str(schedule_path),
        "ready_schedule_file_sha256": file_hash(schedule_path),
        "ready_schedule_hash": schedule_hash,
        "ready_manifest": frozen_manifest,
        "execution_receipt_path": str(receipt_path),
        "execution_receipt_file_sha256": file_hash(receipt_path),
        "execution_receipt_hash": receipt_hash,
    }


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V146 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V146 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V146 plan changed")
    _require(PREPARED.is_file(), "missing V146 prepared receipt")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V146 prepared receipt"
    )
    unbound_path = paths(ROOT)["manifest"]
    _require(
        prepared.get("plan_sha256") == PLAN_SHA256
        and prepared.get("candidate_performance_summaries_parsed") == 0
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("reused_frozen_v142_baseline_runs") == 81
        and prepared.get("baseline_reruns") == 0
        and prepared.get("candidate_online_runs") == 9
        and prepared.get("candidate_reference_builds") == 9
        and prepared.get("binary_sha256") == BINARY_SHA256
        and prepared.get("arm_id") == ARM_ID
        and prepared.get("profile") == PROFILE
        and prepared.get("native_selection_rule") == SELECTION_RULE
        and prepared.get("player_frontier") == PLAYER_FRONTIER
        and prepared.get("single_factor_change")
        == "parents_completed_to_all_unscheduled_functions"
        and prepared.get("source_and_projected_native_command_evidence_required")
        is True
        and prepared.get("v145_plan_file_sha256") == V145_PLAN_SHA256
        and prepared.get("v145_blind_file_sha256") == V145_BLIND_SHA256
        and prepared.get("v145_blind_hash") == V145_BLIND_HASH
        and prepared.get("v145_result_file_sha256") == V145_RESULT_SHA256
        and prepared.get("v145_result_hash") == V145_RESULT_HASH
        and prepared.get("parent_disposition")
        == "V145_complete_training_falsified_zero_of_nine_gates_no_confirmation_inputs_generated"
        and prepared.get("training_seeds") == TRAINING_SEED_LIST
        and prepared.get("sealed_confirmation_seeds") == NEW_CONFIRMATION_SEEDS,
        "V146 prepared boundary changed",
    )
    _require(
        unbound_path.is_file()
        and file_hash(unbound_path) == prepared.get("manifest_file_sha256")
        and read_json(unbound_path).get("manifest_hash")
        == prepared.get("manifest_hash"),
        "V146 prepared unbound manifest changed",
    )
    execution = _validate_execution_receipt()
    baseline_manifest, baseline_evidence = _verify_v142_baselines()
    candidate_path = ready_manifest_path(ROOT)
    candidate_manifest = load_and_validate_manifest(candidate_path)
    _require(
        len(candidate_manifest["runs"]) == 9
        and candidate_manifest.get("all_tapes_bound") is True
        and candidate_manifest.get("all_sla_targets_bound") is True
        and candidate_manifest.get("all_references_bound") is True
        and candidate_manifest.get("all_faasrank_models_bound") is False,
        "V146 ready manifest boundary changed",
    )
    _require(
        execution["ready_manifest"].get("path") == str(candidate_path)
        and execution["ready_manifest"].get("file_sha256") == file_hash(candidate_path)
        and execution["ready_manifest"].get("manifest_hash")
        == candidate_manifest["manifest_hash"],
        "V146 ready schedule no longer matches the manifest",
    )
    tapes = _verify_tapes(candidate_manifest)
    references = _verify_references(candidate_manifest)
    pairing = read_json(pairing_path(ROOT))
    _require(
        pairing.get("passed") is True
        and pairing.get("failed_group_count") == 0
        and pairing.get("run_count") == 9,
        "V146 pairing changed",
    )
    workspace = workspace_path(ROOT)
    expected_ids = {run["run_id"] for run in candidate_manifest["runs"]}
    actual_ids = {
        path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
    }
    _require(actual_ids == expected_ids, "V146 canonical set changed")
    _require(
        not list((workspace / "quarantine").glob("**/attempt-*")),
        "V146 online quarantine is nonempty",
    )
    ledger, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
    ledger_counts = Counter(row["event_type"] for row in ledger)
    _require(
        ledger_counts["attempt_started"] == 9
        and ledger_counts["attempt_canonicalized"] == 9
        and not any(
            ledger_counts[event]
            for event in (
                "attempt_failed",
                "attempt_quarantined",
                "run_blocked",
                "partial_abandoned",
            )
        ),
        f"V146 online ledger changed: {ledger_counts}",
    )

    runtime_values: dict[str, set[str]] = defaultdict(set)
    candidate_evidence = []
    paired_inputs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in baseline_evidence:
        paired_inputs[(item["scenario"], item["seed"])].append(item)
    for run in candidate_manifest["runs"]:
        metadata = run.get("metadata", {})
        _require(
            run.get("method") == "sche_nash"
            and run.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == PROFILE
            and metadata.get("v146_native_selection_rule") == SELECTION_RULE
            and metadata.get("v146_native_portfolio_members") == NATIVE_MEMBERS
            and metadata.get("v146_all_three_experts_advanced_every_window") is True
            and metadata.get("v146_shock_detector")
            == "first_seen_arrivals_80_frame_baseline_20_frame_recent_3_over_2_threshold_50_frame_latch_for_episode_onset_only"
            and metadata.get("v146_persistence_test")
            == "freeze_preceding80_raw_arrivals_at_first_onset_then_at_age55_compare_recent5_mean_to_3_over_2_baseline_mean_once_with_checked_integer_arithmetic"
            and metadata.get("v146_player_frontier") == PLAYER_FRONTIER
            and metadata.get("v146_single_factor_change")
            == "parents_completed_to_all_unscheduled_functions"
            and metadata.get(
                "v146_source_and_projected_native_command_evidence_required"
            )
            is True
            and metadata.get("v146_quiet_route") == "greedy"
            and metadata.get("v146_first_short_route") == "greedy"
            and metadata.get("v146_first_sustained_route") == "faasrank"
            and metadata.get("v146_recurrent_route") == "load_least"
            and metadata.get("v146_service_certificate_scope")
            == SERVICE_CERTIFICATE_SCOPE
            and metadata.get("v146_service_certificate_state_domain")
            == V146_SERVICE_STATE_DOMAIN
            and metadata.get("v146_paper_welfare_state_domain")
            == V146_WELFARE_STATE_DOMAIN
            and metadata.get("v146_outcome_fields_drive_policy") is False
            and metadata.get("v146_scenario_or_burst_label_used_by_policy") is False
            and metadata.get("v146_future_arrivals_used_by_policy") is False
            and metadata.get("v146_confirmation_inputs_opened") is False
            and isinstance(run.get("reference_dependency"), dict),
            f"V146 candidate manifest boundary changed: {run['run_id']}",
        )
        canonical = workspace / "canonical" / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=candidate_manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        audit = read_json(canonical / "manifest.json")
        _require(
            attempt.get("attempt") == 1
            and attempt.get("status") == "qc_pass"
            and attempt.get("classification") == "qc_pass"
            and attempt.get("exit_code") == 0
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V146 canonical status changed: {run['run_id']}",
        )
        runtime = _runtime_evidence(audit)
        for field, value in runtime.items():
            runtime_values[field].add(value)
        diagnostics = _validate_v146_native_diagnostics(run, canonical)
        paired = {
            "method_label": ARM_ID,
            "run_id": run["run_id"],
            "scenario": scenario_id(run),
            "seed": run["seed"],
            "workload_tape_sha256": run["workload_tape"]["sha256"],
            "workload_tape_key": run["workload_tape"]["key"],
            "workload_spec_hash": run["workload_spec_hash"],
            "capture_environment_sha256": run["workload_tape"]["capture_environment"][
                "capture_environment_sha256"
            ],
            "common_hpa_hash": run["common_hpa_hash"],
            "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
            "simulation": run["simulation"],
        }
        paired_inputs[(paired["scenario"], paired["seed"])].append(paired)
        candidate_evidence.append(
            {
                "manifest_id": ARM_ID,
                "method_label": ARM_ID,
                "run_id": run["run_id"],
                "scenario": paired["scenario"],
                "seed": run["seed"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "reference_key": run["reference_dependency"]["key"],
                "result_sha256": attempt["result_sha256"],
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "attempt": 1,
                "classification": "qc_pass",
                "native_diagnostics": diagnostics,
                "ledger_last_hash": ledger_last_hash,
                "reference_ledger_last_hash": references["ledger_last_hash"],
            }
        )

    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V146 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V146 runtime git identity changed: {git_commits}",
    )
    _require(len(paired_inputs) == 9, "V146 paired block count changed")
    for (scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 10
            and {row["method_label"] for row in rows} == {*BASELINE_METHODS, ARM_ID},
            f"V146 paired product changed: {scenario}/{seed}",
        )
        for field in (
            "workload_tape_sha256",
            "workload_tape_key",
            "workload_spec_hash",
            "capture_environment_sha256",
            "common_hpa_hash",
            "sla_artifact_sha256",
            "simulation",
        ):
            _require(
                len({object_hash(row[field]) for row in rows}) == 1,
                f"V146 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V146 common HPA changed: {scenario}/{seed}",
        )

    payload = {
        "schema_version": "NSE_E3_CAUSAL_RAW_PERSISTENCE_FULL_FRONTIER_BLIND_AUDIT_V146_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "performance_results_consulted_for_mechanism_design": True,
        "candidate_performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "runtime_identity": {
            **EXPECTED_RUNTIME,
            "git_commit": next(iter(git_commits)),
        },
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": TRAINING_SEED_LIST,
        "sealed_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        "player_frontier": PLAYER_FRONTIER,
        "single_factor_change": "parents_completed_to_all_unscheduled_functions",
        "source_and_projected_native_command_evidence_required": True,
        "v145_parent": {
            "plan_file_sha256": V145_PLAN_SHA256,
            "blind_file_sha256": V145_BLIND_SHA256,
            "blind_hash": V145_BLIND_HASH,
            "result_file_sha256": V145_RESULT_SHA256,
            "result_hash": V145_RESULT_HASH,
            "disposition": "complete_training_falsified_zero_of_nine_gates_no_confirmation_inputs_generated",
        },
        "baseline_rerun_count": 0,
        "baseline_run_count": 81,
        "candidate_run_count": 9,
        "analyzed_run_count": 90,
        "reference_count": 9,
        "tape_count": 12,
        "block_count": 9,
        "execution": execution,
        "v142_baseline_manifest": {
            "path": str(V142_BASELINE_READY),
            "file_sha256": file_hash(V142_BASELINE_READY),
            "manifest_hash": baseline_manifest["manifest_hash"],
            "run_count": 81,
        },
        "v142_baseline_pairing": {
            "path": str(V142_BASELINE_PAIRING),
            "file_sha256": file_hash(V142_BASELINE_PAIRING),
        },
        "candidate_manifest": {
            "path": str(candidate_path),
            "file_sha256": file_hash(candidate_path),
            "manifest_hash": candidate_manifest["manifest_hash"],
            "run_count": 9,
        },
        "candidate_pairing": {
            "path": str(pairing_path(ROOT)),
            "file_sha256": file_hash(pairing_path(ROOT)),
            "run_count": pairing["run_count"],
            "group_count": pairing["group_count"],
        },
        "tapes": tapes,
        "references": references,
        "baseline_runs": baseline_evidence,
        "candidate_runs": candidate_evidence,
    }
    payload["audit_hash"] = object_hash(payload)
    write_json_atomic(output, payload)
    return payload


def main() -> None:
    audit = run_blind_audit()
    print(
        json.dumps(
            {
                "status": audit["status"],
                "candidate_runs": audit["candidate_run_count"],
                "audit_hash": audit["audit_hash"],
            }
        )
    )


if __name__ == "__main__":
    main()
