from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.p1_retained_evidence import (
    RetainedEvidenceError,
    aggregate_seed,
)


def _window(active: bool, stable: bool = True) -> dict:
    if not active:
        return {
            "decision": {"request_function_players": 0},
            "solver": {
                "inner_stable": False,
                "outer_stable": False,
                "inner_limit_hit": False,
                "outer_limit_hit": False,
                "inner_rounds": 0,
                "outer_rounds": 0,
                "oscillations": 0,
                "termination": "no_players",
                "outer_feedback_trace": [],
            },
            "social": {
                "feedback_eligible": False,
                "reference_source": "not_requested",
                "reference": None,
                "reference_state_key": None,
                "reference_below_current": False,
                "reference_search_suboptimal": False,
                "reference_lookup_us": 0,
            },
            "overhead": {"solve_us": 0},
            "pricing": {"network_beta": 1.0},
        }
    reference = 10.0
    nash = 9.0
    gap = 0.1
    gamma = 0.2
    return {
        "decision": {"request_function_players": 2},
        "solver": {
            "inner_stable": stable,
            "outer_stable": stable,
            "inner_limit_hit": not stable,
            "outer_limit_hit": False,
            "inner_rounds": 1,
            "outer_rounds": 1,
            "oscillations": 0,
            "termination": "social_gap_zero" if stable else "inner_iteration_limit",
            "outer_feedback_trace": [
                {
                    "feedback_applied": True,
                    "feedback_gap": gap,
                    "gamma": gamma,
                    "price_multiplier_for_current_round": 1.0,
                    "price_multiplier_for_next_round": 1.0 + gamma * gap,
                    "reference_welfare_at_baseline_prices": reference,
                    "nash_welfare_at_current_prices": nash,
                }
            ],
        },
        "social": {
            "feedback_eligible": True,
            "reference_source": "offline_table",
            "reference": reference,
            "reference_state_key": 1,
            "reference_below_current": False,
            "reference_search_suboptimal": False,
            "reference_lookup_us": 3,
        },
        "overhead": {"solve_us": 7},
        "pricing": {"network_beta": 1.0},
    }


def _timing() -> dict:
    return {
        "schema": "NSE_SCHEDULER_WINDOW_V1",
        "timing_scope": {"wall_time_ns": "complete"},
        "wall_time_ns": 100,
        "thread_cpu_ns": 0,
        "policy_wall_time_ns": 70,
        "policy_thread_cpu_ns": 0,
        "welfare_evaluation_wall_time_ns": 10,
        "welfare_evaluation_thread_cpu_ns": 0,
    }


class P1RetainedEvidenceTests(unittest.TestCase):
    def test_active_stratum_and_nonconvergence_are_not_value_selected(self) -> None:
        windows = [_window(False) for _ in range(100)] + [
            _window(True, stable=index != 0) for index in range(900)
        ]
        row, counts = aggregate_seed(
            "Q61",
            "synthetic",
            windows,
            [_timing() for _ in range(1000)],
            {
                "duration_seconds": 2.0,
                "process_tree_cpu_seconds": 1.5,
                "peak_process_tree_rss_bytes": 1024,
                "timed_out": False,
                "exit_code": 0,
            },
        )
        self.assertEqual(row["active_windows"], 900)
        self.assertEqual(row["no_player_windows"], 100)
        self.assertEqual(row["nonconverged_count"], 1)
        self.assertAlmostEqual(row["nonconverged_rate"], 1 / 900)
        self.assertEqual(row["feedback_applied_rounds"], 900)
        self.assertEqual(row["feedback_eligible_trace_rounds"], 900)
        self.assertTrue(any(item["stratum"] == "no_player" for item in counts))

    def test_eq16_trace_mismatch_is_a_structural_failure(self) -> None:
        windows = [_window(False) for _ in range(999)] + [_window(True)]
        windows[-1] = copy.deepcopy(windows[-1])
        windows[-1]["solver"]["outer_feedback_trace"][0]["feedback_gap"] = 0.4
        with self.assertRaises(RetainedEvidenceError):
            aggregate_seed(
                "Q61",
                "synthetic",
                windows,
                [_timing() for _ in range(1000)],
                {
                    "duration_seconds": 2.0,
                    "process_tree_cpu_seconds": 1.5,
                    "peak_process_tree_rss_bytes": 1024,
                    "timed_out": False,
                    "exit_code": 0,
                },
            )

    def test_eq19_multiplier_includes_logged_network_beta(self) -> None:
        windows = [_window(False) for _ in range(999)] + [_window(True)]
        active = windows[-1]
        active["pricing"]["network_beta"] = 1.5
        trace = active["solver"]["outer_feedback_trace"][0]
        trace["price_multiplier_for_next_round"] = (
            1.0 + trace["gamma"] * 1.5 * trace["feedback_gap"]
        )
        row, _ = aggregate_seed(
            "Q61",
            "synthetic",
            windows,
            [_timing() for _ in range(1000)],
            {
                "duration_seconds": 2.0,
                "process_tree_cpu_seconds": 1.5,
                "peak_process_tree_rss_bytes": 1024,
                "timed_out": False,
                "exit_code": 0,
            },
        )
        self.assertEqual(row["feedback_applied_rounds"], 1)


if __name__ == "__main__":
    unittest.main()
