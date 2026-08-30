from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_causal_burst_morphology_router_training_execute_v144 import (
    EXECUTION_RECEIPT,
    READY_SCHEDULE,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_burst_morphology_router_training_prepare_v144 import (
    ARM_ID,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    EXPERT_LIFECYCLE,
    NEW_CONFIRMATION_SEEDS,
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
    V144_SERVICE_STATE_DOMAIN,
    V144_WELFARE_STATE_DOMAIN,
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


PREPARED = ROOT / "prepared-manifest-v144.json"
OUTPUT = ROOT / "joint-blind-audit-v144-training.json"
RESULT = ROOT / "training-result-v144.json"
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
EXPECTED_REASONS = {
    "hash": "quiet_before_first_episode_hash",
    "greedy": "first_short_episode_or_post_episode_greedy",
    "faasrank": "first_sustained_episode_retained_faasrank",
    "load_least": "recurrent_episode_retained_load_least",
}


def _expected_route(
    history_valid: bool, episode_count: int, first_episode_sustained: bool
) -> tuple[str, str]:
    if not history_valid:
        return "hash", "arrival_history_discontinuity_fail_closed_hash"
    if episode_count == 0:
        return "hash", EXPECTED_REASONS["hash"]
    if episode_count >= 2:
        return "load_least", EXPECTED_REASONS["load_least"]
    if first_episode_sustained:
        return "faasrank", EXPECTED_REASONS["faasrank"]
    return "greedy", EXPECTED_REASONS["greedy"]


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
    _require(isinstance(reason, str), "invalid V144 guard reason")
    initializer_players = native.get("initializer_readiness_service_players")
    proposal_players = native.get("proposal_readiness_service_players")
    _require(
        type(initializer_players) is int
        and initializer_players >= 0
        and type(proposal_players) is int
        and proposal_players >= 0
        and native.get("certificate_uses_completion_outcomes") is False
        and native.get("service_certificate_scope") == SERVICE_CERTIFICATE_SCOPE,
        f"V144 native service boundary changed: {run_id}:{line_number}",
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
            f"V144 empty guard changed: {run_id}:{line_number}",
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
        f"V144 selected initializer changed: {run_id}:{line_number}",
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
            f"V144 proposal service changed: {run_id}:{line_number}",
        )
        proposal_sum = float(native["proposal_readiness_service_sum"])
        proposal_max = float(native["proposal_readiness_service_max"])
        _require(
            native.get("readiness_service_sum_delta") == proposal_sum - initializer_sum
            and native.get("readiness_service_max_delta")
            == proposal_max - initializer_max,
            f"V144 proposal deltas changed: {run_id}:{line_number}",
        )
    else:
        _require(
            proposal_players == 0
            and guard.get("accepted") is False
            and reason == "proposal_readiness_service_unavailable",
            f"V144 unavailable proposal changed: {run_id}:{line_number}",
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
        f"V144 welfare certificate changed: {run_id}:{line_number}",
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
        f"V144 guard disposition changed: {run_id}:{line_number}",
    )
    return reason, accepted


def _validate_v144_native_diagnostics(
    run: dict[str, Any], canonical: Path
) -> dict[str, Any]:
    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V144 Nash diagnostics: {run['run_id']}")
    counts = Counter()
    reasons = Counter()
    previous_active = False
    expected_episode_count = 0
    first_start: int | None = None
    expected_first_age = 0
    first_sustained = False
    active_player_windows = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") == "run_config":
                counts["run_config"] += 1
                _require(
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("operational_expert_proxy_contract") is None,
                    f"V144 run-config changed: {run['run_id']}:{line_number}",
                )
                continue
            if event.get("kind") != "window":
                continue
            frame = counts["windows"]
            counts["windows"] += 1
            decision = event.get("decision")
            _require(isinstance(decision, dict), "missing V144 decision diagnostics")
            portfolio = decision.get("native_portfolio")
            native = decision.get("native_shadow_anchor")
            guard = decision.get("window_safe_guard")
            detector = decision.get("load_least_dominance_gate", {}).get(
                "causal_arrival_shock"
            )
            morphology = (
                portfolio.get("v144_causal_burst_morphology")
                if isinstance(portfolio, dict)
                else None
            )
            _require(
                all(
                    isinstance(item, dict)
                    for item in (portfolio, native, guard, detector, morphology)
                ),
                f"missing V144 morphology diagnostics: {run['run_id']}:{line_number}",
            )
            _require(
                morphology.get("enabled") is True
                and morphology.get("frame") == frame
                and morphology.get("arrival_history_valid") is True
                and morphology.get("frame_reset_this_window") is False
                and morphology.get("history_discontinuity_this_window") is False
                and morphology.get("selector_inputs")
                == "first_seen_arrival_counts_and_current_frame_only"
                and morphology.get("scenario_seed_future_or_outcome_inputs_used")
                is False,
                f"V144 causal input boundary changed: {run['run_id']}:{line_number}",
            )
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
                and morphology.get("shock_active") is shock_active,
                f"V144 detector changed: {run['run_id']}:{line_number}",
            )
            started = shock_active and not previous_active
            if started:
                expected_episode_count += 1
                if expected_episode_count == 1:
                    first_start = frame
            if shock_active and expected_episode_count == 1 and first_start is not None:
                expected_first_age = frame - first_start + 1
                first_sustained = first_sustained or expected_first_age >= 50
            selected_kind, selection_reason = _expected_route(
                True, expected_episode_count, first_sustained
            )
            _require(
                morphology.get("episode_started_this_window") is started
                and morphology.get("episode_count") == expected_episode_count
                and morphology.get("first_episode_start_frame") == first_start
                and morphology.get("first_episode_active_age_frames")
                == expected_first_age
                and morphology.get("first_episode_sustained") is first_sustained
                and morphology.get("selected_kind") == selected_kind
                and morphology.get("selection_reason") == selection_reason,
                f"V144 state transition changed: {run['run_id']}:{line_number}",
            )
            previous_active = bool(shock_active)

            players = decision.get("request_function_players")
            _require(
                type(players) is int and players >= 0,
                f"V144 player count changed: {run['run_id']}:{line_number}",
            )
            candidates = portfolio.get("candidates")
            selected_candidate: dict[str, Any] | None = None
            if players == 0:
                _require(
                    portfolio.get("enabled") is False
                    and portfolio.get("rule") is None
                    and portfolio.get("candidate_count") == 0
                    and candidates == []
                    and portfolio.get("selected_kind") is None,
                    f"V144 empty portfolio changed: {run['run_id']}:{line_number}",
                )
            else:
                active_player_windows += 1
                _require(
                    portfolio.get("enabled") is True
                    and portfolio.get("rule") == "causal_burst_morphology"
                    and portfolio.get("deterministic_selection_reason")
                    == selection_reason
                    and portfolio.get("candidate_count") == 4
                    and isinstance(candidates, list)
                    and [item.get("kind") for item in candidates]
                    == RUNTIME_NATIVE_KINDS
                    and [item.get("selected") for item in candidates]
                    == [item.get("kind") == selected_kind for item in candidates]
                    and portfolio.get("selected_kind") == selected_kind,
                    f"V144 portfolio selection changed: {run['run_id']}:{line_number}",
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
                        and all(
                            _finite(candidate.get(field))
                            for field in ("service_sum", "service_max", "paper_welfare")
                        ),
                        f"V144 candidate invalid: {run['run_id']}:{line_number}",
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

            initializations = morphology.get("shadow_initializations")
            totals = morphology.get("shadow_invocations_total")
            per_window = morphology.get("shadow_invocations_this_window")
            _require(
                initializations
                == {"hash": 1, "greedy": 1, "faasrank": 1, "load_least": 1}
                and isinstance(totals, dict)
                and isinstance(per_window, dict)
                and per_window == {kind: 1 for kind in RUNTIME_NATIVE_KINDS}
                and all(
                    totals.get(kind) == counts["windows"]
                    for kind in RUNTIME_NATIVE_KINDS
                )
                and morphology.get("all_four_shadows_advanced_exactly_once_this_window")
                is True,
                f"V144 expert lifecycle changed: {run['run_id']}:{line_number}",
            )
            if selected_candidate is None:
                _require(
                    morphology.get("selected_native_ordered_command_hash") is None
                    or type(morphology.get("selected_native_ordered_command_hash"))
                    is int,
                    f"V144 empty command hash changed: {run['run_id']}:{line_number}",
                )
                _require(
                    morphology.get("selected_native_assignment_hash") is None
                    or type(morphology.get("selected_native_assignment_hash")) is int,
                    f"V144 empty assignment hash changed: {run['run_id']}:{line_number}",
                )
                _require(
                    morphology.get("selected_initializer_dispatched_exactly") is False
                    and morphology.get("accepted_nash_proposal_dispatched_exactly")
                    is False,
                    f"V144 empty dispatch changed: {run['run_id']}:{line_number}",
                )
            else:
                _require(
                    morphology.get("selected_native_ordered_command_hash")
                    == selected_candidate["ordered_command_hash"]
                    and morphology.get("selected_native_assignment_hash")
                    == selected_candidate["assignment_hash"],
                    f"V144 selected hashes changed: {run['run_id']}:{line_number}",
                )
            reason, accepted = _validate_guard(
                run["run_id"], line_number, players, selected_candidate, native, guard
            )
            reasons[reason] += 1
            if players > 0:
                _require(
                    morphology.get("selected_initializer_dispatched_exactly")
                    is (not accepted)
                    and morphology.get("accepted_nash_proposal_dispatched_exactly")
                    is accepted
                    and type(morphology.get("final_assignment_hash")) is int,
                    f"V144 final dispatch changed: {run['run_id']}:{line_number}",
                )
            if accepted:
                counts["accepted_windows"] += 1

    _require(
        counts["run_config"] == 1, f"V144 run-config count changed: {run['run_id']}"
    )
    _require(counts["windows"] == 4000, f"V144 window count changed: {run['run_id']}")
    _require(active_player_windows > 0, f"V144 has no player windows: {run['run_id']}")
    return {
        "window_count": counts["windows"],
        "native_player_window_count": active_player_windows,
        "accepted_proposal_window_count": counts["accepted_windows"],
        "episode_count": expected_episode_count,
        "first_episode_start_frame": first_start,
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
        "performance_fields_consulted": False,
    }


def _verify_references(candidate_manifest: Mapping[str, Any]) -> dict[str, Any]:
    path = reference_catalog_path(ROOT)
    _require(path.is_file(), "missing V144 reference catalog")
    catalog = read_json(path)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V144 references")
    entries = catalog.get("entries")
    expected = {
        run["reference_dependency"]["key"] for run in candidate_manifest["runs"]
    }
    _require(
        isinstance(entries, dict)
        and set(entries) == expected
        and len(entries) == 9
        and candidate_manifest.get("reference_catalog_hash") == catalog_hash,
        "V144 reference product changed",
    )
    stage_root = _stage_root_from_receipts(
        entries, "receipt_path", 9, "V144 references"
    )
    ledger, last_hash = _read_ledger(stage_root / "ledger.jsonl")
    counts = Counter(row["event_type"] for row in ledger)
    _require(
        counts == Counter({"reference_build_canonicalized": 9})
        and not list((stage_root / "quarantine").glob("**/attempt-*")),
        f"V144 reference ledger changed: {counts}",
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
            f"V144 reference evidence changed: {key}",
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
    _require(schedule_path.is_file(), "missing V144 ready schedule")
    _require(receipt_path.is_file(), "missing V144 execution receipt")
    schedule = read_json(schedule_path)
    schedule_hash = _assert_hashed_object(
        schedule, "schedule_hash", "V144 ready schedule"
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
        "V144 ready schedule binding changed",
    )
    receipt = read_json(receipt_path)
    receipt_hash = _assert_hashed_object(
        receipt, "receipt_hash", "V144 execution receipt"
    )
    _require(
        receipt.get("candidate_performance_summaries_parsed") == 0
        and receipt.get("performance_results_consulted_for_mechanism_design") is True
        and receipt.get("plan_sha256") == PLAN_SHA256
        and receipt.get("ready_schedule_hash") == schedule_hash
        and receipt.get("dispatch_count") == 9
        and receipt.get("all_exit_codes_zero") is True
        and len(receipt.get("dispatches", [])) == 9,
        "V144 execution boundary changed",
    )
    for scheduled, dispatched in zip(schedule["schedule"], receipt["dispatches"]):
        _require(
            all(
                scheduled[field] == dispatched[field]
                for field in ("ordinal", "scenario", "seed", "run_id")
            )
            and dispatched.get("exit_code") == 0,
            f"V144 frozen dispatch changed: {scheduled['ordinal']}",
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
    _require(not output.exists(), f"V144 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V144 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V144 plan changed")
    _require(PREPARED.is_file(), "missing V144 prepared receipt")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V144 prepared receipt"
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
        and prepared.get("training_seeds") == TRAINING_SEED_LIST
        and prepared.get("sealed_confirmation_seeds") == NEW_CONFIRMATION_SEEDS,
        "V144 prepared boundary changed",
    )
    _require(
        unbound_path.is_file()
        and file_hash(unbound_path) == prepared.get("manifest_file_sha256")
        and read_json(unbound_path).get("manifest_hash")
        == prepared.get("manifest_hash"),
        "V144 prepared unbound manifest changed",
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
        "V144 ready manifest boundary changed",
    )
    _require(
        execution["ready_manifest"].get("path") == str(candidate_path)
        and execution["ready_manifest"].get("file_sha256") == file_hash(candidate_path)
        and execution["ready_manifest"].get("manifest_hash")
        == candidate_manifest["manifest_hash"],
        "V144 ready schedule no longer matches the manifest",
    )
    tapes = _verify_tapes(candidate_manifest)
    references = _verify_references(candidate_manifest)
    pairing = read_json(pairing_path(ROOT))
    _require(
        pairing.get("passed") is True
        and pairing.get("failed_group_count") == 0
        and pairing.get("run_count") == 9,
        "V144 pairing changed",
    )
    workspace = workspace_path(ROOT)
    expected_ids = {run["run_id"] for run in candidate_manifest["runs"]}
    actual_ids = {
        path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
    }
    _require(actual_ids == expected_ids, "V144 canonical set changed")
    _require(
        not list((workspace / "quarantine").glob("**/attempt-*")),
        "V144 online quarantine is nonempty",
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
        f"V144 online ledger changed: {ledger_counts}",
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
            and metadata.get("v144_native_selection_rule") == SELECTION_RULE
            and metadata.get("v144_native_portfolio_members")
            == ["hash", "greedy", "sche_FaaSRank", "load_least"]
            and metadata.get("v144_all_four_experts_advanced_every_window") is True
            and metadata.get("v144_service_certificate_scope")
            == SERVICE_CERTIFICATE_SCOPE
            and metadata.get("v144_service_certificate_state_domain")
            == V144_SERVICE_STATE_DOMAIN
            and metadata.get("v144_paper_welfare_state_domain")
            == V144_WELFARE_STATE_DOMAIN
            and metadata.get("v144_outcome_fields_drive_policy") is False
            and metadata.get("v144_scenario_or_burst_label_used_by_policy") is False
            and metadata.get("v144_future_arrivals_used_by_policy") is False
            and metadata.get("v144_confirmation_inputs_opened") is False
            and isinstance(run.get("reference_dependency"), dict),
            f"V144 candidate manifest boundary changed: {run['run_id']}",
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
            f"V144 canonical status changed: {run['run_id']}",
        )
        runtime = _runtime_evidence(audit)
        for field, value in runtime.items():
            runtime_values[field].add(value)
        diagnostics = _validate_v144_native_diagnostics(run, canonical)
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
            f"V144 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V144 runtime git identity changed: {git_commits}",
    )
    _require(len(paired_inputs) == 9, "V144 paired block count changed")
    for (scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 10
            and {row["method_label"] for row in rows} == {*BASELINE_METHODS, ARM_ID},
            f"V144 paired product changed: {scenario}/{seed}",
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
                f"V144 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V144 common HPA changed: {scenario}/{seed}",
        )

    payload = {
        "schema_version": "NSE_E3_CAUSAL_BURST_MORPHOLOGY_BLIND_AUDIT_V144_V1",
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
