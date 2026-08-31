from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_route_native_frontier_training_blind_audit_v147 import (
    _expected_route,
    _persistence_comparison,
    _validate_v147_native_diagnostics,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_route_native_frontier_training_prepare_v147 import (
    ARM_ID,
    NEW_CONFIRMATION_SEEDS,
    PLAN_SHA256,
    PLAYER_FRONTIER,
    PROFILE,
    ROUTE_FRONTIERS,
    RUNTIME_NATIVE_KINDS,
    SERVICE_CERTIFICATE_SCOPE,
    TRAINING_SEED_LIST,
    V145_RESULT_HASH,
    V146_INVALIDATION_HASH,
    V146_INVALIDATION_SHA256,
    V146_PLAN_SHA256,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_route_native_frontier_training_reveal_v147 import (
    _validate_blind_audit,
    _validate_blind_document,
    evaluate_training_rows,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
    SCENARIOS,
)
from scripts.reviewer_experiments.protocol.tests.test_nse_e3_causal_raw_persistence_router_training_blind_reveal_v145 import (
    _synthetic_window as _v145_synthetic_window,
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
    tamper_comparison: bool = False,
    tamper_frontier: bool = False,
) -> dict[str, object]:
    event = _v145_synthetic_window(
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
        window_count,
        tamper_comparison=tamper_comparison,
    )
    decision = event["decision"]
    players = decision["request_function_players"]
    decision["player_frontier"] = PLAYER_FRONTIER
    decision["native_shadow_anchor"][
        "service_certificate_scope"
    ] = SERVICE_CERTIFICATE_SCOPE
    portfolio = decision["native_portfolio"]
    selected_kind = portfolio["v145_causal_raw_persistence"]["selected_kind"]
    if players:
        portfolio["rule"] = "causal_raw_persistence_route_native_frontier"
    selected = next(
        (item for item in portfolio["candidates"] if item["kind"] == selected_kind),
        None,
    )
    portfolio["candidates"] = [selected] if selected is not None and players else []
    portfolio["candidate_count"] = len(portfolio["candidates"])
    portfolio["selected_kind"] = selected_kind if players else None
    frontier_counts = {kind: players for kind in RUNTIME_NATIVE_KINDS}
    if players and selected_kind == "faasrank":
        frontier_counts["greedy"] = players + 1
        frontier_counts["load_least"] = players + 1
    elif players:
        frontier_counts["faasrank"] = max(0, players - 1)
    native_counts = dict(frontier_counts)
    if tamper_frontier and frame == 0:
        native_counts["greedy"] += 1
    native_hashes = {
        kind: 1000 + index for index, kind in enumerate(RUNTIME_NATIVE_KINDS, start=1)
    }
    if selected is not None and players:
        native_hashes[selected_kind] = selected["ordered_command_hash"]
    portfolio["v146_causal_raw_persistence_full_frontier"] = {"enabled": False}
    portfolio["v147_causal_raw_persistence_route_native_frontier"] = {
        "enabled": True,
        "frame": frame,
        "router_selected_kind": selected_kind,
        "router_selection_reason": portfolio["v145_causal_raw_persistence"][
            "selection_reason"
        ],
        "native_frontiers": ROUTE_FRONTIERS,
        "native_frontier_player_counts": frontier_counts,
        "native_command_counts": native_counts,
        "native_ordered_command_hashes": native_hashes,
        "shadow_invocations_this_window": {kind: 1 for kind in RUNTIME_NATIVE_KINDS},
        "all_three_shadows_advanced_exactly_once_this_window": True,
        "every_native_capture_complete_on_own_frontier": True,
        "selected_frontier": ROUTE_FRONTIERS[selected_kind],
        "selected_frontier_player_count": players,
        "selected_frontier_player_order_hash": 2000 + frame,
        "selected_capture_complete_on_own_frontier": bool(players),
        "selected_native_ordered_command_hash": (
            selected["ordered_command_hash"] if selected else None
        ),
        "selected_native_assignment_hash": (
            selected["assignment_hash"] if selected else None
        ),
        "final_assignment_hash": portfolio["v145_causal_raw_persistence"][
            "final_assignment_hash"
        ],
        "no_cross_expert_cohort_tail_fill": True,
        "selected_initializer_dispatched_exactly": portfolio[
            "v145_causal_raw_persistence"
        ]["selected_initializer_dispatched_exactly"],
        "accepted_nash_proposal_dispatched_exactly": portfolio[
            "v145_causal_raw_persistence"
        ]["accepted_nash_proposal_dispatched_exactly"],
    }
    return event


def _write_synthetic_diagnostics(
    canonical: Path, *, tamper_frontier: bool = False
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
                    "operational_player_frontier": PLAYER_FRONTIER,
                    "operational_expert_proxy_contract": {
                        "version": "V147",
                        "router": "frozen_V145_causal_raw_persistence_state_machine",
                        "native_frontiers": ROUTE_FRONTIERS,
                        "cross_expert_tail_fill": False,
                        "uses_completed_request_outcomes": False,
                        "reference_policy_independent": True,
                    },
                }
            )
            + "\n"
        )
        for frame in range(4000):
            raw = 30 if 100 <= frame <= 154 else 10
            shock_active = 100 <= frame <= 149 or 200 <= frame <= 249
            episode_count = int(frame >= 100) + int(frame >= 200)
            first_start = 100 if frame >= 100 else None
            evaluated = frame >= 154
            event = _synthetic_window(
                frame,
                raw,
                shock_active,
                episode_count,
                first_start,
                800 if frame >= 100 else None,
                150 if evaluated else None,
                evaluated,
                evaluated,
                frame in {100, 200},
                frame + 1,
                tamper_frontier=tamper_frontier,
            )
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")


class V147RouteNativeFrontierBlindRevealTests(unittest.TestCase):
    def test_causal_route_and_integer_boundary_are_unchanged(self) -> None:
        self.assertEqual(
            _expected_route(True, 1, True, True),
            ("faasrank", "age55_raw_persistence_sustained_retained_faasrank"),
        )
        self.assertEqual(
            _expected_route(True, 2, True, True),
            ("load_least", "recurrent_episode_retained_load_least"),
        )
        boundary = _persistence_comparison(recent=75, baseline=800)
        self.assertEqual(boundary["recent_scaled"], 12_000)
        self.assertEqual(boundary["baseline_scaled"], 12_000)
        self.assertTrue(boundary["sustained"])

    def test_blind_diagnostics_require_exact_route_native_frontiers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            _write_synthetic_diagnostics(canonical)
            evidence = _validate_v147_native_diagnostics(
                {"run_id": "synthetic"}, canonical
            )
            self.assertEqual(evidence["window_count"], 4000)
            self.assertEqual(evidence["player_frontier"], PLAYER_FRONTIER)
            self.assertEqual(evidence["route_frontiers"], ROUTE_FRONTIERS)
            self.assertEqual(evidence["persistence_evaluation_count"], 1)
            self.assertEqual(
                evidence["native_frontier_player_totals"],
                evidence["native_command_totals"],
            )
            self.assertFalse(evidence["cross_expert_tail_fill_observed"])
            self.assertFalse(evidence["performance_fields_consulted"])
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            _write_synthetic_diagnostics(canonical, tamper_frontier=True)
            with self.assertRaisesRegex(RuntimeError, "native frontier changed"):
                _validate_v147_native_diagnostics({"run_id": "synthetic"}, canonical)

    def test_reveal_is_fail_closed_until_v147_blind_hashes_are_frozen(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "has not been frozen"):
            _validate_blind_audit()

    def test_blind_document_requires_zero_reads_and_v145_lineage(self) -> None:
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
            "player_frontier": PLAYER_FRONTIER,
            "route_frontiers": ROUTE_FRONTIERS,
            "single_factor_change": "universal_all_unscheduled_to_route_selected_expert_native_frontier",
            "native_frontier_command_evidence_required": True,
            "v145_parent": {
                "result_hash": V145_RESULT_HASH,
                "disposition": "complete_training_falsified_zero_of_nine_gates_no_confirmation_inputs_generated",
            },
            "v146_parent": {
                "plan_file_sha256": V146_PLAN_SHA256,
                "invalidation_file_sha256": V146_INVALIDATION_SHA256,
                "invalidation_hash": V146_INVALIDATION_HASH,
                "disposition": "retired_before_online_execution_after_all_nine_reference_dependencies_blocked",
            },
        }
        expected_hash = object_hash(blind)
        blind["audit_hash"] = expected_hash
        _validate_blind_document(blind, expected_hash)
        blind["performance_summaries_parsed"] = 1
        with self.assertRaisesRegex(RuntimeError, "does not authorize reveal"):
            _validate_blind_document(blind, expected_hash)

    def test_all_nine_gates_are_required(self) -> None:
        rows = []
        for method_index, method in enumerate([*BASELINE_METHODS, ARM_ID]):
            for scenario in SCENARIOS:
                for seed in TRAINING_SEED_LIST:
                    value = 20.0 if method == ARM_ID else 10.0 + method_index / 100.0
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
