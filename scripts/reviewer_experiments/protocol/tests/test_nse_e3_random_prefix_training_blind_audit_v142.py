from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_blind_audit_v142 import (
    NATIVE_KINDS,
    RUNTIME_PORTFOLIO_RULES,
    _expected_portfolio_selection,
    _rank_portfolio_candidates,
    _validate_native_diagnostics,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    ARMS,
    NEW_CONFIRMATION_SEEDS,
    RETIRED_OPENED_V138_TRAINING_SEEDS,
    RETIRED_OPENED_V139_TRAINING_SEEDS,
    RETIRED_OPENED_V140_TRAINING_SEEDS,
    RETIRED_OPENED_V141_TRAINING_SEEDS,
    RETIRED_V137_CONFIRMATION_SEEDS,
    TRAINING_SEED_LIST,
)


VALUES = [
    ("random", 5.0, 10.0, 100.0),
    ("greedy", 5.0, 9.0, 100.0),
    ("hiku", 4.0, 10.0, 110.0),
    ("jiagu", 6.0, 8.0, 120.0),
    ("orion", 5.0, 8.0, 90.0),
    ("load_least", 4.0, 7.0, 105.0),
]


def _run(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "simulator_experiment": {"algorithm_seed": "E1526"},
    }


def _predicate_fields(candidate: dict, random: dict) -> dict[str, bool]:
    epsilon = 1.0e-6
    fields = {
        "random_service_max_nonworse": candidate["service_max"]
        <= random["service_max"] + epsilon,
        "random_service_sum_nonworse": candidate["service_sum"]
        <= random["service_sum"] + epsilon,
        "random_service_sum_strictly_lower": candidate["service_sum"]
        < random["service_sum"] - epsilon,
        "random_welfare_nonworse": candidate["paper_welfare"] + epsilon
        >= random["paper_welfare"],
        "random_welfare_strictly_higher": candidate["paper_welfare"]
        > random["paper_welfare"] + epsilon,
    }
    fields["random_service_pareto_admissible"] = (
        fields["random_service_max_nonworse"]
        and fields["random_service_sum_strictly_lower"]
        and fields["random_welfare_nonworse"]
    )
    fields["random_welfare_pareto_admissible"] = (
        fields["random_service_max_nonworse"]
        and fields["random_service_sum_nonworse"]
        and fields["random_welfare_strictly_higher"]
    )
    return fields


def _portfolio_candidates(
    rule: str, values: list[tuple[str, float, float, float]] | None = None
) -> tuple[list[dict], int, str]:
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
        for index, (kind, service_max, service_sum, welfare) in enumerate(
            values or VALUES
        )
    ]
    random = candidates[0]
    for candidate in candidates:
        candidate.update(_predicate_fields(candidate, random))
    ranks = _rank_portfolio_candidates(candidates)
    for candidate, candidate_ranks in zip(candidates, ranks):
        candidate.update(candidate_ranks)
    selected, reason = _expected_portfolio_selection(rule, candidates, ranks)
    candidates[selected]["selected"] = True
    return candidates, selected, reason


def window_event(
    frame: int, selection_rule: str = "random_prefix_service_pareto"
) -> dict:
    portfolio_enabled = selection_rule != "exact_random_prefix"
    if portfolio_enabled:
        candidates, selected, selection_reason = _portfolio_candidates(selection_rule)
        selected_candidate = candidates[selected]
    else:
        candidates = []
        selection_reason = None
        selected_candidate = {
            "kind": "random",
            "ordered_command_hash": 100,
            "assignment_hash": 200,
            "service_max": 5.0,
            "service_sum": 10.0,
            "paper_welfare": 100.0,
        }
    return {
        "kind": "window",
        "frame": frame,
        "decision": {
            "request_function_players": 1,
            "random_prefix_cohort": {
                "enabled": True,
                "feasible_player_count": 2,
                "player_count": 1,
                "missing_feasible_player_count": 1,
                "early_stop_observed": True,
                "ordered_command_hash": 100,
                "dispatch_player_count": 1,
                "commands_prepared": 1,
                "cohort_equals_dispatch": True,
                "tail_players_dispatched": 0,
                "cohort_source": "exact_persistent_same_seed_native_Random_ScheCmd_prefix_with_unchanged_early_stop_semantics",
                "uses_completion_outcomes": False,
            },
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
                "service_certificate_scope": "exact_random_emitted_command_prefix_players",
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
                "enabled": portfolio_enabled,
                "rule": (
                    RUNTIME_PORTFOLIO_RULES[selection_rule]
                    if portfolio_enabled
                    else None
                ),
                "selected_kind": (
                    selected_candidate["kind"] if portfolio_enabled else None
                ),
                "deterministic_selection_reason": selection_reason,
                "candidate_count": len(candidates),
                "random_default_index": 0 if portfolio_enabled else None,
                "random_shadow_seeded": True,
                "random_shadow_seed_source": "algorithm_seed",
                "random_shadow_algorithm_seed": "E1526",
                "random_shadow_lifecycle": "one_persistent_RandomScheduler_per_algorithm_seed_advanced_once_per_scheduling_window",
                "random_shadow_initialization_count": 1,
                "random_shadow_invocation_count": frame + 1,
                "random_shadow_invocations_this_window": 1,
                "early_stop_command_position": 1,
                "certificate_uses_completion_outcomes": False,
                "configured_bandwidth_snapshot_complete": True,
                "configured_bandwidth_snapshot_source": "current_SimEnvObserve_configured_directed_bandwidth",
                "all_player_service_definition": "current_admitted_immutable_CPU_plus_prior_same_window_projected_immutable_CPU_plus_current_player_immutable_CPU_divided_by_current_node_capacity_plus_cold_start_plus_current_or_complete_assignment_parent_transfer",
                "service_certificate_state_domain": "runtime_existing_aggregates_and_admitted_work_projected_to_exact_random_prefix",
                "paper_welfare_price_basis": "immutable_pre_feedback_baseline_prices",
                "paper_welfare_state_domain": "empty_current_joint_decision_aggregates_existing_contention_via_pressure_and_eq12_only_projected_to_exact_random_prefix",
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


class RandomAnchorBlindAuditV142Tests(unittest.TestCase):
    def _write(self, root: Path, run_id: str, events: list[dict]) -> Path:
        canonical = root / "canonical"
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        with gzip.open(record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8") as out:
            for event in events:
                out.write(json.dumps(event) + "\n")
        return canonical

    def test_preregistered_product_and_seed_boundaries_are_exact(self) -> None:
        self.assertEqual(TRAINING_SEED_LIST, ["E1526", "E1527", "E1528"])
        self.assertEqual(
            [rule for _, _, rule in ARMS],
            [
                "exact_random_prefix",
                "random_prefix_service_pareto",
                "random_prefix_welfare_pareto",
            ],
        )
        self.assertEqual(
            NATIVE_KINDS,
            ["random", "greedy", "hiku", "jiagu", "orion", "load_least"],
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
        self.assertEqual(
            RETIRED_OPENED_V140_TRAINING_SEEDS, ["E1520", "E1521", "E1522"]
        )
        self.assertEqual(
            RETIRED_OPENED_V141_TRAINING_SEEDS, ["E1523", "E1524", "E1525"]
        )
        self.assertEqual(NEW_CONFIRMATION_SEEDS, [f"E{i}" for i in range(1497, 1517)])
        self.assertFalse(
            set(TRAINING_SEED_LIST)
            & set(
                RETIRED_V137_CONFIRMATION_SEEDS
                + RETIRED_OPENED_V138_TRAINING_SEEDS
                + RETIRED_OPENED_V139_TRAINING_SEEDS
                + RETIRED_OPENED_V140_TRAINING_SEEDS
                + RETIRED_OPENED_V141_TRAINING_SEEDS
                + NEW_CONFIRMATION_SEEDS
            )
        )

    def test_both_pareto_rules_are_recomputed_deterministically(self) -> None:
        expected = {
            "random_prefix_service_pareto": (
                5,
                "strict_service_pareto_replacement_minimum_service_sum",
            ),
            "random_prefix_welfare_pareto": (
                2,
                "strict_welfare_pareto_replacement_maximum_paper_welfare",
            ),
        }
        for rule, result in expected.items():
            candidates, _, _ = _portfolio_candidates(rule)
            ranks = _rank_portfolio_candidates(candidates)
            self.assertEqual(
                _expected_portfolio_selection(rule, candidates, ranks), result
            )

        no_replacement = [
            VALUES[0],
            *[(kind, 6.0, 11.0, 99.0) for kind, *_ in VALUES[1:]],
        ]
        for rule in expected:
            candidates, selected, _ = _portfolio_candidates(rule, no_replacement)
            self.assertEqual(selected, 0)
            self.assertTrue(candidates[0]["selected"])

    def test_exact_random_prefix_and_both_portfolios_pass(self) -> None:
        for rule, expected_kind in (
            ("exact_random_prefix", "random"),
            ("random_prefix_service_pareto", "load_least"),
            ("random_prefix_welfare_pareto", "hiku"),
        ):
            with self.subTest(rule=rule), tempfile.TemporaryDirectory() as temporary:
                run_id = f"synthetic-v142-{rule}"
                canonical = self._write(
                    Path(temporary),
                    run_id,
                    [window_event(frame, rule) for frame in range(4000)],
                )
                evidence = _validate_native_diagnostics(_run(run_id), canonical, rule)
                self.assertEqual(evidence["window_count"], 4000)
                self.assertEqual(evidence["native_player_window_count"], 4000)
                self.assertEqual(evidence["service_certificate_window_count"], 4000)
                self.assertEqual(evidence["accepted_proposal_window_count"], 4000)
                self.assertEqual(
                    evidence["selected_native_counts"][expected_kind], 4000
                )
                self.assertFalse(evidence["performance_fields_consulted"])

    def test_external_prefix_rule_requires_the_frozen_runtime_enum_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v142-runtime-rule"
            events = [window_event(frame) for frame in range(4000)]
            events[7]["decision"]["native_portfolio"][
                "rule"
            ] = "random_prefix_service_pareto"
            canonical = self._write(Path(temporary), run_id, events)
            with self.assertRaisesRegex(RuntimeError, "active portfolio boundary"):
                _validate_native_diagnostics(
                    _run(run_id), canonical, "random_prefix_service_pareto"
                )

    def test_random_predicate_or_candidate_alignment_error_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v142-corrupt"
            events = [window_event(frame) for frame in range(4000)]
            events[7]["decision"]["native_portfolio"]["candidates"][0][
                "random_welfare_nonworse"
            ] = False
            canonical = self._write(Path(temporary), run_id, events)
            with self.assertRaisesRegex(RuntimeError, "Random-relative predicates"):
                _validate_native_diagnostics(
                    _run(run_id), canonical, "random_prefix_service_pareto"
                )

    def test_random_lifecycle_or_bandwidth_boundary_fails_closed(self) -> None:
        for field, value, message in (
            ("random_shadow_algorithm_seed", 999, "Random shadow lifecycle"),
            (
                "configured_bandwidth_snapshot_complete",
                False,
                "configured bandwidth snapshot",
            ),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                run_id = f"synthetic-v142-{field}"
                events = [window_event(frame) for frame in range(4000)]
                events[0]["decision"]["native_portfolio"][field] = value
                canonical = self._write(Path(temporary), run_id, events)
                with self.assertRaisesRegex(RuntimeError, message):
                    _validate_native_diagnostics(
                        _run(run_id), canonical, "random_prefix_service_pareto"
                    )

    def test_unavailable_proposal_certificate_is_audited_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v142-unavailable-proposal"
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
                _run(run_id), canonical, "random_prefix_service_pareto"
            )
            self.assertEqual(evidence["service_certificate_window_count"], 0)
            self.assertEqual(evidence["accepted_proposal_window_count"], 0)

    def test_empty_window_not_applicable_and_enabled_portfolio_fails(self) -> None:
        for corrupt in (False, True):
            with self.subTest(
                corrupt=corrupt
            ), tempfile.TemporaryDirectory() as temporary:
                run_id = f"synthetic-v142-empty-{corrupt}"
                events = [window_event(frame) for frame in range(4000)]
                empty = events[0]["decision"]
                empty["request_function_players"] = 0
                empty["random_prefix_cohort"].update(
                    {
                        "feasible_player_count": 0,
                        "player_count": 0,
                        "missing_feasible_player_count": 0,
                        "early_stop_observed": False,
                        "ordered_command_hash": 0,
                        "dispatch_player_count": 0,
                        "commands_prepared": 0,
                    }
                )
                empty["native_portfolio"].update(
                    {
                        "enabled": corrupt,
                        "rule": None,
                        "selected_kind": None,
                        "deterministic_selection_reason": None,
                        "candidate_count": 0,
                        "random_default_index": None,
                        "early_stop_command_position": None,
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
                if corrupt:
                    with self.assertRaisesRegex(
                        RuntimeError, "empty-window diagnostics mismatch"
                    ):
                        _validate_native_diagnostics(
                            _run(run_id), canonical, "random_prefix_service_pareto"
                        )
                else:
                    evidence = _validate_native_diagnostics(
                        _run(run_id), canonical, "random_prefix_service_pareto"
                    )
                    self.assertEqual(evidence["native_player_window_count"], 3999)
                    self.assertEqual(evidence["guard_reasons"]["not_applicable"], 1)

    def test_first_infeasible_random_player_can_yield_empty_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v142-empty-early-stop-prefix"
            events = [window_event(frame) for frame in range(4000)]
            empty = events[0]["decision"]
            empty["request_function_players"] = 0
            empty["random_prefix_cohort"].update(
                {
                    "feasible_player_count": 2,
                    "player_count": 0,
                    "missing_feasible_player_count": 2,
                    "early_stop_observed": True,
                    "ordered_command_hash": 0,
                    "dispatch_player_count": 0,
                    "commands_prepared": 0,
                }
            )
            empty["native_portfolio"].update(
                {
                    "enabled": False,
                    "rule": None,
                    "selected_kind": None,
                    "deterministic_selection_reason": None,
                    "candidate_count": 0,
                    "random_default_index": None,
                    "early_stop_command_position": 0,
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
                _run(run_id), canonical, "random_prefix_service_pareto"
            )
            self.assertEqual(evidence["native_player_window_count"], 3999)
            self.assertEqual(evidence["random_early_stop_window_count"], 4000)
            self.assertEqual(evidence["random_missing_feasible_player_count"], 4001)


if __name__ == "__main__":
    unittest.main()
