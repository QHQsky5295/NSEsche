from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_all_native_portfolio_training_blind_audit_v140 import (
    NATIVE_KINDS,
    _expected_portfolio_selection,
    _rank_portfolio_candidates,
    _validate_native_diagnostics,
)
from scripts.reviewer_experiments.protocol.nse_e3_all_native_portfolio_training_prepare_v140 import (
    ARMS,
    NEW_CONFIRMATION_SEEDS,
    RETIRED_OPENED_V138_TRAINING_SEEDS,
    RETIRED_OPENED_V139_TRAINING_SEEDS,
    RETIRED_V137_CONFIRMATION_SEEDS,
    TRAINING_SEED_LIST,
)


def _portfolio_candidates(rule: str) -> tuple[list[dict], int, str]:
    values = [
        ("greedy", 5.0, 10.0, 100.0),
        ("hiku", 4.0, 12.0, 90.0),
        ("jiagu", 6.0, 8.0, 110.0),
        ("orion", 7.0, 9.0, 80.0),
        ("load_least", 8.0, 7.0, 70.0),
    ]
    candidates = [
        {
            "kind": kind,
            "commands": 1,
            "duplicate_commands": 0,
            "unexpected_messages": 0,
            "missing_players": 0,
            "extra_players": 0,
            "infeasible_commands": 0,
            "valid": True,
            "ordered_command_hash": 100 + index,
            "assignment_hash": 200 + index,
            "service_complete": True,
            "service_players": 1,
            "service_max": service_max,
            "service_sum": service_sum,
            "paper_welfare": welfare,
            "selected": False,
        }
        for index, (kind, service_max, service_sum, welfare) in enumerate(values)
    ]
    ranks = _rank_portfolio_candidates(candidates)
    for candidate, candidate_ranks in zip(candidates, ranks):
        candidate.update(candidate_ranks)
    selected, reason = _expected_portfolio_selection(rule, candidates, ranks)
    candidates[selected]["selected"] = True
    return candidates, selected, reason


def window_event(frame: int, rule: str = "minimax_service") -> dict:
    candidates, selected, selection_reason = _portfolio_candidates(rule)
    selected_candidate = candidates[selected]
    return {
        "kind": "window",
        "frame": frame,
        "decision": {
            "request_function_players": 1,
            "native_shadow_anchor": {
                "kind": selected_candidate["kind"],
                "valid": True,
                "commands": 1,
                "duplicate_commands": 0,
                "unexpected_messages": 0,
                "missing_players": 0,
                "extra_players": 0,
                "infeasible_commands": 0,
                "anchor_assignment_hash": selected_candidate["assignment_hash"],
                "ordered_command_hash": selected_candidate["ordered_command_hash"],
                "certificate_uses_completion_outcomes": False,
                "service_certificate_scope": "all_feasible_players",
                "initializer_readiness_service_players": 1,
                "proposal_readiness_service_players": 1,
                "initializer_readiness_service_complete": True,
                "proposal_readiness_service_complete": True,
                "initializer_readiness_service_sum": selected_candidate["service_sum"],
                "proposal_readiness_service_sum": selected_candidate["service_sum"]
                - 1.0,
                "initializer_readiness_service_max": selected_candidate["service_max"],
                "proposal_readiness_service_max": selected_candidate["service_max"],
                "readiness_service_sum_delta": -1.0,
                "readiness_service_max_delta": 0.0,
            },
            "native_portfolio": {
                "enabled": True,
                "rule": rule,
                "selected_kind": selected_candidate["kind"],
                "deterministic_selection_reason": selection_reason,
                "candidate_count": 5,
                "certificate_uses_completion_outcomes": False,
                "configured_bandwidth_snapshot_complete": True,
                "configured_bandwidth_snapshot_source": "current_SimEnvObserve_configured_directed_bandwidth",
                "all_player_service_definition": "current_admitted_immutable_CPU_plus_prior_same_window_projected_immutable_CPU_plus_current_player_immutable_CPU_divided_by_current_node_capacity_plus_cold_start_plus_current_or_complete_assignment_parent_transfer",
                "service_certificate_state_domain": "runtime_existing_aggregates_and_admitted_work",
                "paper_welfare_price_basis": "immutable_pre_feedback_baseline_prices",
                "paper_welfare_state_domain": "empty_current_joint_decision_aggregates_existing_contention_via_pressure_and_eq12_only",
                "candidates": candidates,
            },
            "window_safe_guard": {
                "evaluated": True,
                "accepted": True,
                "fallback_applied": False,
                "reason": "accepted",
                "initializer_baseline_welfare": selected_candidate["paper_welfare"],
                "proposal_baseline_welfare": selected_candidate["paper_welfare"] + 0.5,
                "baseline_welfare_delta": 0.5,
            },
        },
    }


class AllNativePortfolioBlindAuditV140Tests(unittest.TestCase):
    def _write(self, root: Path, run_id: str, events: list[dict]) -> Path:
        canonical = root / "canonical"
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        with gzip.open(record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8") as out:
            for event in events:
                out.write(json.dumps(event) + "\n")
        return canonical

    def test_preregistered_product_and_seed_boundaries_are_exact(self) -> None:
        self.assertEqual(TRAINING_SEED_LIST, ["E1520", "E1521", "E1522"])
        self.assertEqual(
            [rule for _, _, rule in ARMS],
            ["minimax_service", "minsum_service", "service_welfare_borda"],
        )
        self.assertEqual(
            NATIVE_KINDS, ["greedy", "hiku", "jiagu", "orion", "load_least"]
        )
        self.assertEqual(
            RETIRED_V137_CONFIRMATION_SEEDS, [f"E{i}" for i in range(1474, 1494)]
        )
        self.assertEqual(
            RETIRED_OPENED_V138_TRAINING_SEEDS, ["E1494", "E1495", "E1496"]
        )
        self.assertEqual(
            RETIRED_OPENED_V139_TRAINING_SEEDS, ["E1517", "E1518", "E1519"]
        )
        self.assertEqual(NEW_CONFIRMATION_SEEDS, [f"E{i}" for i in range(1497, 1517)])
        self.assertFalse(
            set(TRAINING_SEED_LIST)
            & set(
                RETIRED_V137_CONFIRMATION_SEEDS
                + RETIRED_OPENED_V138_TRAINING_SEEDS
                + RETIRED_OPENED_V139_TRAINING_SEEDS
                + NEW_CONFIRMATION_SEEDS
            )
        )

    def test_all_three_portfolio_rules_are_recomputed_deterministically(self) -> None:
        expected = {
            "minimax_service": (1, "minimum_service_max"),
            "minsum_service": (4, "minimum_service_sum"),
            "service_welfare_borda": (2, "minimum_ordinal_rank_sum"),
        }
        for rule, result in expected.items():
            candidates, _, _ = _portfolio_candidates(rule)
            ranks = _rank_portfolio_candidates(candidates)
            self.assertEqual(
                _expected_portfolio_selection(rule, candidates, ranks), result
            )

        tied = [
            {"service_max": 0.0, "service_sum": 1.0, "paper_welfare": 1.0},
            {"service_max": -0.0, "service_sum": 1.0, "paper_welfare": 1.0},
        ]
        ranks = _rank_portfolio_candidates(tied)
        self.assertEqual(ranks[1]["service_max_rank"], 1)
        self.assertEqual(ranks[0]["service_max_rank"], 2)

    def test_valid_five_member_portfolio_and_guard_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v140"
            canonical = self._write(
                Path(temporary), run_id, [window_event(frame) for frame in range(4000)]
            )
            evidence = _validate_native_diagnostics(
                {"run_id": run_id}, canonical, "minimax_service"
            )
            self.assertEqual(evidence["window_count"], 4000)
            self.assertEqual(evidence["native_player_window_count"], 4000)
            self.assertEqual(evidence["service_certificate_window_count"], 4000)
            self.assertEqual(evidence["accepted_proposal_window_count"], 4000)
            self.assertEqual(evidence["selected_native_counts"]["hiku"], 4000)
            self.assertFalse(evidence["performance_fields_consulted"])

    def test_any_candidate_alignment_or_selection_error_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v140-corrupt"
            events = [window_event(frame) for frame in range(4000)]
            events[7]["decision"]["native_portfolio"]["candidates"][0][
                "extra_players"
            ] = 1
            canonical = self._write(Path(temporary), run_id, events)
            with self.assertRaisesRegex(RuntimeError, "portfolio candidate invalid"):
                _validate_native_diagnostics(
                    {"run_id": run_id}, canonical, "minimax_service"
                )

    def test_incomplete_configured_bandwidth_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v140-missing-bandwidth"
            events = [window_event(frame) for frame in range(4000)]
            events[0]["decision"]["native_portfolio"][
                "configured_bandwidth_snapshot_complete"
            ] = False
            canonical = self._write(Path(temporary), run_id, events)
            with self.assertRaisesRegex(RuntimeError, "configured bandwidth snapshot"):
                _validate_native_diagnostics(
                    {"run_id": run_id}, canonical, "minimax_service"
                )

    def test_runtime_aggregate_paper_welfare_domain_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v140-wrong-welfare-domain"
            events = [window_event(frame) for frame in range(4000)]
            events[0]["decision"]["native_portfolio"][
                "paper_welfare_state_domain"
            ] = "runtime_existing_aggregates"
            canonical = self._write(Path(temporary), run_id, events)
            with self.assertRaisesRegex(RuntimeError, "certificate definition"):
                _validate_native_diagnostics(
                    {"run_id": run_id}, canonical, "minimax_service"
                )

    def test_unavailable_proposal_certificate_is_audited_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v140-unavailable-proposal"
            events = [window_event(frame) for frame in range(4000)]
            for event in events:
                native = event["decision"]["native_shadow_anchor"]
                native.update(
                    {
                        "proposal_readiness_service_players": 0,
                        "proposal_readiness_service_complete": False,
                        "proposal_readiness_service_sum": None,
                        "proposal_readiness_service_max": None,
                        "readiness_service_sum_delta": None,
                        "readiness_service_max_delta": None,
                    }
                )
                event["decision"]["window_safe_guard"].update(
                    {
                        "accepted": False,
                        "fallback_applied": True,
                        "reason": "proposal_readiness_service_unavailable",
                    }
                )
            canonical = self._write(Path(temporary), run_id, events)
            evidence = _validate_native_diagnostics(
                {"run_id": run_id}, canonical, "minimax_service"
            )
            self.assertEqual(evidence["service_certificate_window_count"], 0)
            self.assertEqual(evidence["accepted_proposal_window_count"], 0)

    def test_empty_window_not_applicable_diagnostics_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v140-empty-window"
            events = [window_event(frame) for frame in range(4000)]
            empty = events[0]["decision"]
            empty["request_function_players"] = 0
            empty["native_portfolio"].update(
                {
                    "enabled": False,
                    "rule": None,
                    "selected_kind": None,
                    "deterministic_selection_reason": None,
                    "candidate_count": 0,
                    "candidates": [],
                }
            )
            empty["native_shadow_anchor"].update(
                {
                    "valid": False,
                    "commands": 0,
                    "anchor_assignment_hash": 0,
                    "ordered_command_hash": 0,
                    "initializer_readiness_service_players": 0,
                    "proposal_readiness_service_players": 0,
                    "initializer_readiness_service_complete": False,
                    "proposal_readiness_service_complete": False,
                }
            )
            empty["window_safe_guard"].update(
                {
                    "evaluated": False,
                    "accepted": False,
                    "fallback_applied": False,
                    "reason": "not_applicable",
                    "initializer_baseline_welfare": None,
                    "proposal_baseline_welfare": None,
                    "baseline_welfare_delta": None,
                }
            )
            canonical = self._write(Path(temporary), run_id, events)
            evidence = _validate_native_diagnostics(
                {"run_id": run_id}, canonical, "minimax_service"
            )
            self.assertEqual(evidence["native_player_window_count"], 3999)
            self.assertEqual(evidence["guard_reasons"]["not_applicable"], 1)

    def test_empty_window_enabled_portfolio_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v140-invalid-enabled-empty-window"
            events = [window_event(frame) for frame in range(4000)]
            empty = events[0]["decision"]
            empty["request_function_players"] = 0
            empty["native_portfolio"].update(
                {
                    "selected_kind": None,
                    "deterministic_selection_reason": None,
                    "candidate_count": 0,
                    "candidates": [],
                }
            )
            empty["native_shadow_anchor"].update(
                {
                    "initializer_readiness_service_players": 0,
                    "proposal_readiness_service_players": 0,
                    "initializer_readiness_service_complete": False,
                    "proposal_readiness_service_complete": False,
                }
            )
            empty["window_safe_guard"].update(
                {
                    "evaluated": False,
                    "accepted": False,
                    "fallback_applied": False,
                    "reason": "not_applicable",
                }
            )
            canonical = self._write(Path(temporary), run_id, events)
            with self.assertRaisesRegex(
                RuntimeError, "empty-window diagnostics mismatch"
            ):
                _validate_native_diagnostics(
                    {"run_id": run_id}, canonical, "minimax_service"
                )


if __name__ == "__main__":
    unittest.main()
