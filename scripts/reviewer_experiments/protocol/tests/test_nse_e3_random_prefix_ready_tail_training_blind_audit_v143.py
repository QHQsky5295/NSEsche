from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_blind_audit_v143 import (
    EXPECTED_RUN_CONFIG_CONTRACT,
    RANDOM_RELATIVE_FIELDS,
    _expected_v143_selection,
    _validate_v143_native_diagnostics,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_prepare_v143 import (
    COHORT_SOURCE,
    NEW_CONFIRMATION_SEEDS,
    RANDOM_SHADOW_LIFECYCLE,
    READY_TAIL_PREDICATE,
    RUNTIME_NATIVE_KINDS,
    SELECTION_RULE,
    SERVICE_CERTIFICATE_SCOPE,
    TRAINING_SEED_LIST,
    V143_SERVICE_STATE_DOMAIN,
    V143_WELFARE_STATE_DOMAIN,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_blind_audit_v142 import (
    _rank_portfolio_candidates,
)


VALUES = [
    ("faasrank", 5.0, 10.0, 100.0),
    ("greedy", 5.0, 9.0, 100.0),
    ("hiku", 4.0, 9.0, 110.0),
    ("jiagu", 6.0, 8.0, 120.0),
    ("orion", 5.0, 8.0, 90.0),
    ("load_least", 4.0, 7.0, 105.0),
    ("ocs", 4.0, 7.0, 105.0),
]


def _run(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "simulator_experiment": {"algorithm_seed": "E1526"},
    }


def _candidates(values: list[tuple[str, float, float, float]] | None = None):
    candidates = [
        {
            "kind": kind,
            "commands": 3,
            "duplicate_commands": 0,
            "unexpected_messages": 0,
            "missing_players": 0,
            "extra_players": 0,
            "infeasible_commands": 0,
            "valid": True,
            "ordered_command_hash": 500 + index,
            "assignment_hash": 600 + index,
            "service_complete": True,
            "service_players": 3,
            "service_max": service_max,
            "service_sum": service_sum,
            "paper_welfare": welfare,
            "default_kind": "faasrank",
            "selected": False,
        }
        for index, (kind, service_max, service_sum, welfare) in enumerate(
            values or VALUES
        )
    ]
    default = candidates[0]
    for candidate in candidates:
        predicates = {
            "default_service_max_nonworse": candidate["service_max"]
            <= default["service_max"] + 1.0e-6,
            "default_service_sum_nonworse": candidate["service_sum"]
            <= default["service_sum"] + 1.0e-6,
            "default_service_sum_strictly_lower": candidate["service_sum"]
            < default["service_sum"] - 1.0e-6,
            "default_welfare_nonworse": candidate["paper_welfare"] + 1.0e-6
            >= default["paper_welfare"],
        }
        predicates["default_service_pareto_admissible"] = (
            predicates["default_service_max_nonworse"]
            and predicates["default_service_sum_strictly_lower"]
            and predicates["default_welfare_nonworse"]
        )
        candidate.update(predicates)
        candidate.update({field: None for field in RANDOM_RELATIVE_FIELDS})
    for candidate, ranks in zip(candidates, _rank_portfolio_candidates(candidates)):
        candidate.update(ranks)
    selected, reason = _expected_v143_selection(candidates)
    candidates[selected]["selected"] = True
    return candidates, selected, reason


def _partitions(prefix_hash: int = 100, combined_hash: int = 200) -> list[dict]:
    return [
        {
            "kind": kind,
            "cohort_player_order_hash": combined_hash,
            "random_prefix_player_count": 1,
            "random_prefix_assignment_hash": prefix_hash,
            "expected_random_prefix_assignment_hash": prefix_hash,
            "random_prefix_nodes_preserved": True,
            "ready_tail_player_count": 2,
            "ready_tail_assignment_hash": 300 + index,
        }
        for index, kind in enumerate(RUNTIME_NATIVE_KINDS)
    ]


def _common_portfolio(frame: int) -> dict:
    return {
        "enabled": True,
        "rule": SELECTION_RULE,
        "random_default_index": None,
        "random_shadow_seeded": True,
        "random_shadow_seed_source": "algorithm_seed",
        "random_shadow_algorithm_seed": "E1526",
        "random_shadow_lifecycle": RANDOM_SHADOW_LIFECYCLE,
        "random_shadow_initialization_count": 1,
        "random_shadow_invocation_count": frame + 1,
        "random_shadow_invocations_this_window": 1,
        "certificate_uses_completion_outcomes": False,
        "configured_bandwidth_snapshot_complete": True,
        "configured_bandwidth_snapshot_source": "current_SimEnvObserve_configured_directed_bandwidth",
        "all_player_service_definition": "current_admitted_immutable_CPU_plus_prior_same_window_projected_immutable_CPU_plus_current_player_immutable_CPU_divided_by_current_node_capacity_plus_cold_start_plus_current_or_complete_assignment_parent_transfer",
        "service_certificate_state_domain": V143_SERVICE_STATE_DOMAIN,
        "paper_welfare_price_basis": "immutable_pre_feedback_baseline_prices",
        "paper_welfare_state_domain": V143_WELFARE_STATE_DOMAIN,
    }


def window_event(frame: int) -> dict:
    candidates, selected, reason = _candidates()
    selected_candidate = candidates[selected]
    portfolio = _common_portfolio(frame)
    portfolio.update(
        {
            "selected_kind": selected_candidate["kind"],
            "deterministic_selection_reason": reason,
            "candidate_count": 7,
            "default_index": 0,
            "default_kind": "faasrank",
            "early_stop_command_position": 1,
            "candidates": candidates,
            "v143_candidate_partitions": _partitions(),
        }
    )
    return {
        "kind": "window",
        "frame": frame,
        "decision": {
            "request_function_players": 3,
            "random_prefix_cohort": {
                "enabled": True,
                "feasible_player_count": 2,
                "player_count": 1,
                "missing_feasible_player_count": 1,
                "early_stop_observed": True,
                "ordered_command_hash": 100,
                "dispatch_player_count": 3,
                "commands_prepared": 3,
                "cohort_equals_dispatch": True,
                "ready_feasible_player_count": 3,
                "prefix_ready_overlap_count": 1,
                "ready_tail_player_count": 2,
                "combined_cohort_player_count": 3,
                "combined_cohort_ordered_hash": 200,
                "tail_players_dispatched": 2,
                "cohort_source": COHORT_SOURCE,
                "ready_tail_predicate": READY_TAIL_PREDICATE,
                "uses_completion_outcomes": False,
            },
            "native_shadow_anchor": {
                "kind": selected_candidate["kind"],
                "valid": True,
                "commands": 3,
                "duplicate_commands": 0,
                "unexpected_messages": 0,
                "missing_players": 0,
                "extra_players": 0,
                "infeasible_commands": 0,
                "anchor_assignment_hash": selected_candidate["assignment_hash"],
                "ordered_command_hash": selected_candidate["ordered_command_hash"],
                "certificate_uses_completion_outcomes": False,
                "service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
                "initializer_readiness_service_players": 3,
                "proposal_readiness_service_players": 3,
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
            "native_portfolio": portfolio,
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


def empty_window_event(frame: int) -> dict:
    empty_hash = 14_695_981_039_346_656_037
    portfolio = _common_portfolio(frame)
    partitions = _partitions(empty_hash, empty_hash)
    for partition in partitions:
        partition["random_prefix_player_count"] = 0
        partition["ready_tail_player_count"] = 0
        partition["ready_tail_assignment_hash"] = empty_hash
    portfolio.update(
        {
            "enabled": False,
            "rule": None,
            "selected_kind": None,
            "deterministic_selection_reason": None,
            "candidate_count": 0,
            "default_index": None,
            "default_kind": None,
            "early_stop_command_position": None,
            "candidates": [],
            "v143_candidate_partitions": partitions,
        }
    )
    return {
        "kind": "window",
        "frame": frame,
        "decision": {
            "request_function_players": 0,
            "random_prefix_cohort": {
                "enabled": True,
                "feasible_player_count": 0,
                "player_count": 0,
                "missing_feasible_player_count": 0,
                "early_stop_observed": False,
                "ordered_command_hash": empty_hash,
                "dispatch_player_count": 0,
                "commands_prepared": 0,
                "cohort_equals_dispatch": True,
                "ready_feasible_player_count": 0,
                "prefix_ready_overlap_count": 0,
                "ready_tail_player_count": 0,
                "combined_cohort_player_count": 0,
                "combined_cohort_ordered_hash": empty_hash,
                "tail_players_dispatched": 0,
                "cohort_source": COHORT_SOURCE,
                "ready_tail_predicate": READY_TAIL_PREDICATE,
                "uses_completion_outcomes": False,
            },
            "native_shadow_anchor": {
                "certificate_uses_completion_outcomes": False,
                "service_certificate_scope": SERVICE_CERTIFICATE_SCOPE,
                "initializer_readiness_service_players": 0,
                "proposal_readiness_service_players": 0,
                "initializer_readiness_service_complete": False,
                "proposal_readiness_service_complete": False,
            },
            "native_portfolio": portfolio,
            "window_safe_guard": {
                "evaluated": False,
                "accepted": False,
                "fallback_applied": False,
                "reason": "not_applicable",
            },
        },
    }


class ReadyTailBlindAuditV143Tests(unittest.TestCase):
    def _write(self, root: Path, run_id: str, events: list[dict]) -> Path:
        canonical = root / "canonical"
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        with gzip.open(
            record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8"
        ) as output:
            output.write(
                json.dumps(
                    {
                        "kind": "run_config",
                        "scheduler": "sche_nash",
                        "operational_expert_proxy_contract": EXPECTED_RUN_CONFIG_CONTRACT,
                    }
                )
                + "\n"
            )
            for event in events:
                output.write(json.dumps(event) + "\n")
        return canonical

    def test_preregistered_boundaries_are_exact(self) -> None:
        self.assertEqual(TRAINING_SEED_LIST, ["E1526", "E1527", "E1528"])
        self.assertEqual(
            RUNTIME_NATIVE_KINDS,
            ["faasrank", "greedy", "hiku", "jiagu", "orion", "load_least", "ocs"],
        )
        self.assertEqual(NEW_CONFIRMATION_SEEDS, [f"E{i}" for i in range(1497, 1517)])

    def test_faasrank_default_selection_and_fallback_are_deterministic(self) -> None:
        candidates, selected, reason = _candidates()
        self.assertEqual(selected, 5)
        self.assertEqual(
            reason, "strict_service_pareto_replacement_minimum_service_sum"
        )
        self.assertEqual(_expected_v143_selection(candidates), (selected, reason))

        worse = [VALUES[0], *[(kind, 6.0, 11.0, 99.0) for kind, *_ in VALUES[1:]]]
        candidates, selected, reason = _candidates(worse)
        self.assertEqual(selected, 0)
        self.assertEqual(
            reason, "faasrank_default_no_strict_service_pareto_replacement"
        )

    def test_full_window_trace_including_empty_window_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v143-ready-tail"
            events = [empty_window_event(0), *[window_event(i) for i in range(1, 4000)]]
            canonical = self._write(Path(temporary), run_id, events)
            result = _validate_v143_native_diagnostics(_run(run_id), canonical)
            self.assertEqual(result["window_count"], 4000)
            self.assertEqual(result["ready_tail_window_count"], 3999)
            self.assertEqual(result["selected_native_counts"]["load_least"], 3999)
            self.assertFalse(result["performance_fields_consulted"])

    def test_prefix_node_partition_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v143-partition-tamper"
            events = [window_event(i) for i in range(4000)]
            events[17]["decision"]["native_portfolio"]["v143_candidate_partitions"][0][
                "random_prefix_nodes_preserved"
            ] = False
            canonical = self._write(Path(temporary), run_id, events)
            with self.assertRaisesRegex(RuntimeError, "hybrid partition"):
                _validate_v143_native_diagnostics(_run(run_id), canonical)


if __name__ == "__main__":
    unittest.main()
