from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_router_training_blind_audit_v145 import (
    _candidate_hash_agreement,
    _expected_route,
    _persistence_comparison,
    _validate_v145_native_diagnostics,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_router_training_prepare_v145 import (
    ARM_ID,
    NEW_CONFIRMATION_SEEDS,
    PLAN_SHA256,
    PROFILE,
    RUNTIME_NATIVE_KINDS,
    SERVICE_CERTIFICATE_SCOPE,
    TRAINING_SEED_LIST,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_router_training_reveal_v145 import (
    _validate_blind_audit,
    _validate_blind_document,
    evaluate_training_rows,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
    SCENARIOS,
)
from scripts.reviewer_experiments.protocol.util import object_hash


def _synthetic_window(
    frame: int,
    raw: int,
    shock_active: bool,
    episode_count: int,
    first_start: int | None,
    baseline: int | None,
    recent: int | None,
    evaluated: bool,
    sustained: bool,
    started: bool,
    window_count: int,
    *,
    tamper_comparison: bool,
) -> dict[str, object]:
    selected_kind, reason = _expected_route(True, episode_count, evaluated, sustained)
    players = int(frame in {0, 100, 153, 154, 200})
    comparison = _persistence_comparison(recent, baseline) if evaluated else None
    if tamper_comparison and frame == 154:
        comparison = dict(comparison)
        comparison["recent_scaled"] += 1
    candidates = []
    selected = None
    if players:
        for index, kind in enumerate(RUNTIME_NATIVE_KINDS, start=1):
            candidate = {
                "kind": kind,
                "selected": kind == selected_kind,
                "valid": True,
                "commands": 1,
                "duplicate_commands": 0,
                "unexpected_messages": 0,
                "missing_players": 0,
                "extra_players": 0,
                "infeasible_commands": 0,
                "ordered_command_hash": 100 + index,
                "assignment_hash": 200 + index,
                "service_complete": True,
                "service_players": 1,
                "service_sum": 1.0,
                "service_max": 1.0,
                "paper_welfare": 1.0,
            }
            candidates.append(candidate)
            if candidate["selected"]:
                selected = candidate
    if players:
        native = {
            "kind": selected_kind,
            "valid": True,
            "commands": 1,
            "duplicate_commands": 0,
            "unexpected_messages": 0,
            "missing_players": 0,
            "extra_players": 0,
            "infeasible_commands": 0,
            "anchor_assignment_hash": selected["assignment_hash"],
            "ordered_command_hash": selected["ordered_command_hash"],
            "initializer_readiness_service_complete": True,
            "initializer_readiness_service_players": 1,
            "initializer_readiness_service_sum": 1.0,
            "initializer_readiness_service_max": 1.0,
            "proposal_readiness_service_complete": True,
            "proposal_readiness_service_players": 1,
            "proposal_readiness_service_sum": 1.0,
            "proposal_readiness_service_max": 1.0,
            "readiness_service_sum_delta": 0.0,
            "readiness_service_max_delta": 0.0,
            "certificate_uses_completion_outcomes": False,
            "service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
        }
        guard = {
            "reason": "readiness_service_sum_not_strictly_improved",
            "evaluated": True,
            "accepted": False,
            "fallback_applied": True,
            "initializer_baseline_welfare": 1.0,
            "proposal_baseline_welfare": 1.0,
            "baseline_welfare_delta": 0.0,
        }
    else:
        native = {
            "initializer_readiness_service_complete": False,
            "initializer_readiness_service_players": 0,
            "proposal_readiness_service_complete": False,
            "proposal_readiness_service_players": 0,
            "certificate_uses_completion_outcomes": False,
            "service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
        }
        guard = {
            "reason": "not_applicable",
            "evaluated": False,
            "accepted": False,
            "fallback_applied": False,
        }
    per_window = {kind: 1 for kind in RUNTIME_NATIVE_KINDS}
    return {
        "kind": "window",
        "decision": {
            "request_function_players": players,
            "load_least_dominance_gate": {
                "causal_arrival_shock": {
                    "gate_enabled": True,
                    "baseline_frames": 80,
                    "recent_frames": 20,
                    "threshold_numerator": 3,
                    "threshold_denominator": 2,
                    "active_frames": 50,
                    "uses_first_seen_request_ids_only": True,
                    "active": shock_active,
                }
            },
            "native_portfolio": {
                "enabled": bool(players),
                "rule": "causal_raw_persistence" if players else None,
                "deterministic_selection_reason": reason if players else None,
                "candidate_count": len(candidates),
                "candidates": candidates,
                "selected_kind": selected_kind if players else None,
                "v145_causal_raw_persistence": {
                    "enabled": True,
                    "frame": frame,
                    "arrival_history_valid": True,
                    "frame_reset_this_window": False,
                    "history_discontinuity_this_window": False,
                    "checked_arithmetic_valid": True,
                    "raw_first_seen_current_frame": raw,
                    "rolling_shock_active": shock_active,
                    "episode_started_this_window": started,
                    "episode_count": episode_count,
                    "first_episode_start_frame": first_start,
                    "first_episode_age_frames": (
                        frame - first_start + 1 if first_start is not None else 0
                    ),
                    "baseline_frames": 80,
                    "baseline_80_count": baseline,
                    "recent_frames": 5,
                    "recent_5_count": recent,
                    "evaluation_age_frames": 55,
                    "threshold_numerator": 3,
                    "threshold_denominator": 2,
                    "persistence_evaluated_once": evaluated,
                    "persistence_evaluation_count": int(evaluated),
                    "persistence_comparison": comparison,
                    "first_episode_sustained": sustained,
                    "selected_kind": selected_kind,
                    "selection_reason": reason,
                    "selector_inputs": "first_seen_arrival_counts_and_current_frame_only",
                    "scenario_seed_future_or_outcome_inputs_used": False,
                    "shadow_initializations": {
                        "greedy": 1,
                        "faasrank": 1,
                        "load_least": 1,
                    },
                    "shadow_invocations_total": {
                        kind: window_count for kind in RUNTIME_NATIVE_KINDS
                    },
                    "shadow_invocations_this_window": per_window,
                    "all_three_shadows_advanced_exactly_once_this_window": True,
                    "selected_native_ordered_command_hash": (
                        selected["ordered_command_hash"] if players else None
                    ),
                    "selected_native_assignment_hash": (
                        selected["assignment_hash"] if players else None
                    ),
                    "final_assignment_hash": (
                        selected["assignment_hash"] if players else 0
                    ),
                    "selected_initializer_dispatched_exactly": bool(players),
                    "accepted_nash_proposal_dispatched_exactly": False,
                },
            },
            "native_shadow_anchor": native,
            "window_safe_guard": guard,
        },
    }


def _write_synthetic_diagnostics(
    canonical: Path, *, tamper_comparison: bool = False
) -> None:
    path = canonical / "reviewer_records" / "synthetic"
    path.mkdir(parents=True)
    with gzip.open(path / "nash_metrics.jsonl.gz", "wt", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "kind": "run_config",
                    "scheduler": "sche_nash",
                    "operational_expert_proxy": PROFILE,
                    "operational_expert_proxy_contract": None,
                }
            )
            + "\n"
        )
        for frame in range(4000):
            raw = 30 if 100 <= frame <= 154 else 10
            shock_active = 100 <= frame <= 149 or 200 <= frame <= 249
            episode_count = int(frame >= 100) + int(frame >= 200)
            first_start = 100 if frame >= 100 else None
            baseline = 800 if frame >= 100 else None
            evaluated = frame >= 154
            recent = 150 if evaluated else None
            sustained = evaluated
            started = frame in {100, 200}
            event = _synthetic_window(
                frame,
                raw,
                shock_active,
                episode_count,
                first_start,
                baseline,
                recent,
                evaluated,
                sustained,
                started,
                frame + 1,
                tamper_comparison=tamper_comparison,
            )
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")


class V145CausalRawPersistenceBlindRevealTests(unittest.TestCase):
    def test_causal_route_is_exact_preregistered_state_machine(self) -> None:
        self.assertEqual(
            _expected_route(True, 0, False, False),
            ("greedy", "quiet_before_first_episode_greedy"),
        )
        self.assertEqual(
            _expected_route(True, 1, False, False),
            ("greedy", "first_episode_unclassified_through_age54_greedy"),
        )
        self.assertEqual(
            _expected_route(True, 1, True, False),
            ("greedy", "age55_raw_persistence_short_retained_greedy"),
        )
        self.assertEqual(
            _expected_route(True, 1, True, True),
            ("faasrank", "age55_raw_persistence_sustained_retained_faasrank"),
        )
        self.assertEqual(
            _expected_route(True, 2, True, True),
            ("load_least", "recurrent_episode_retained_load_least"),
        )
        self.assertEqual(
            _expected_route(False, 2, True, True),
            ("greedy", "arrival_history_or_arithmetic_fail_closed_greedy"),
        )

    def test_integer_persistence_boundary_is_inclusive_and_scale_exact(self) -> None:
        boundary = _persistence_comparison(recent=75, baseline=800)
        self.assertEqual(boundary["recent_scaled"], 12_000)
        self.assertEqual(boundary["baseline_scaled"], 12_000)
        self.assertTrue(boundary["sustained"])
        self.assertFalse(_persistence_comparison(recent=74, baseline=800)["sustained"])
        with self.assertRaises(ValueError):
            _persistence_comparison(recent=-1, baseline=800)

    def test_blind_diagnostics_recompute_age55_state_without_performance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            _write_synthetic_diagnostics(canonical)
            evidence = _validate_v145_native_diagnostics(
                {"run_id": "synthetic"}, canonical
            )
            self.assertEqual(evidence["window_count"], 4000)
            self.assertEqual(evidence["episode_count"], 2)
            self.assertEqual(evidence["persistence_evaluation_count"], 1)
            self.assertEqual(evidence["sustained_evaluation_count"], 1)
            self.assertEqual(evidence["baseline_80_count"], 800)
            self.assertEqual(evidence["recent_5_count"], 150)
            self.assertFalse(evidence["performance_fields_consulted"])

        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            _write_synthetic_diagnostics(canonical, tamper_comparison=True)
            with self.assertRaisesRegex(RuntimeError, "state transition changed"):
                _validate_v145_native_diagnostics({"run_id": "synthetic"}, canonical)

    def test_reveal_fails_closed_until_blind_hashes_are_frozen(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "has not been frozen"):
            _validate_blind_audit()

    def test_blind_document_requires_zero_candidate_performance_reads(self) -> None:
        blind = {
            "status": "pass",
            "plan_file_sha256": PLAN_SHA256,
            "performance_summaries_parsed": 0,
            "candidate_performance_results_consulted": False,
            "reveal_authorized": True,
            "confirmation_inputs_opened": False,
            "baseline_rerun_count": 0,
            "baseline_run_count": 81,
            "candidate_run_count": 9,
            "analyzed_run_count": 90,
            "reference_count": 9,
            "tape_count": 12,
            "block_count": 9,
            "training_seeds": TRAINING_SEED_LIST,
            "sealed_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        }
        expected_hash = object_hash(blind)
        blind["audit_hash"] = expected_hash
        _validate_blind_document(blind, expected_hash)
        blind["performance_summaries_parsed"] = 1
        with self.assertRaisesRegex(RuntimeError, "does not authorize reveal"):
            _validate_blind_document(blind, expected_hash)

    def test_native_experts_may_legitimately_agree_on_a_placement(self) -> None:
        candidates = [
            {"ordered_command_hash": 11, "assignment_hash": 21},
            {"ordered_command_hash": 12, "assignment_hash": 22},
            {"ordered_command_hash": 11, "assignment_hash": 21},
        ]
        self.assertEqual(_candidate_hash_agreement(candidates), (2, 1))

    def test_all_nine_gates_are_required(self) -> None:
        rows = []
        for method_index, method in enumerate([*BASELINE_METHODS, ARM_ID]):
            for scenario in SCENARIOS:
                for seed in TRAINING_SEED_LIST:
                    candidate = method == ARM_ID
                    value = 20.0 if candidate else 10.0 + method_index / 100.0
                    rows.append(
                        {
                            "method_label": method,
                            "scenario": scenario,
                            "seed": seed,
                            "run_id": f"{method}-{scenario}-{seed}",
                            "fixed_window_completed": 1,
                            "throughput_requests_per_ms": value,
                            "qpr_finite_only": value,
                            "qpr_zero_completed_as_zero": value,
                        }
                    )
        evaluation = evaluate_training_rows(rows)
        self.assertTrue(evaluation["family_training_gate_pass"])
        self.assertEqual(
            evaluation["candidate_result"]["score"]["passed_gate_count"], 9
        )
        for row in rows:
            if row["method_label"] == ARM_ID and row["scenario"] == SCENARIOS[-1]:
                row["throughput_requests_per_ms"] = 0.0
        self.assertFalse(evaluate_training_rows(rows)["family_training_gate_pass"])


if __name__ == "__main__":
    unittest.main()
