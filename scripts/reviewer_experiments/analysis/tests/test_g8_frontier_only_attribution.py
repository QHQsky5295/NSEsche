from __future__ import annotations

import math
import unittest
from types import SimpleNamespace

from scripts.reviewer_experiments.analysis.g8_frontier_only_attribution import (
    COHORTS,
    PAIR_NUMERIC_METRICS,
    _pair_rows,
    _reference_shape,
    _window_metrics,
    evaluate_conditions,
    summarize,
)
from scripts.reviewer_experiments.protocol.schema import ProtocolValidationError


def _raw(role: str, seed: str, value: float = 10.0) -> dict[str, object]:
    row: dict[str, object] = {
        "product": role,
        "role": role,
        "seed": seed,
        "run_id": f"{role}-{seed}",
        "workload_tape_sha256": f"tape-{seed}",
        "termination_counts": {"converged": 1},
    }
    row.update({metric: value for metric in PAIR_NUMERIC_METRICS})
    return row


class G8FrontierOnlyAttributionTests(unittest.TestCase):
    def test_summary_reports_t_interval_signs_and_all_loo_means(self) -> None:
        result = summarize([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(result["mean"], 3.0)
        self.assertEqual(result["positive"], 5)
        self.assertEqual(result["zero"], 0)
        self.assertEqual(len(result["leave_one_seed_out_means"]), 5)
        self.assertEqual(result["leave_one_seed_out_means"][0], 3.5)
        self.assertLess(result["ci95_low"], result["mean"])
        self.assertGreater(result["ci95_high"], result["mean"])

    def test_summary_rejects_post_hoc_sample_size(self) -> None:
        with self.assertRaises(ProtocolValidationError):
            summarize([1.0, 2.0, 3.0, 4.0])

    def test_reference_shape_accepts_only_two_exact_sources(self) -> None:
        self.assertEqual(
            _reference_shape(
                {
                    "reference_source": "offline_table",
                    "reference_state_key": 7,
                    "reference": 2.5,
                }
            ),
            "offline_table",
        )
        self.assertEqual(
            _reference_shape(
                {
                    "reference_source": "not_requested",
                    "reference_state_key": None,
                    "reference": None,
                    "reference_cache_hit": False,
                    "feedback_eligible": False,
                }
            ),
            "not_requested",
        )
        with self.assertRaises(ProtocolValidationError):
            _reference_shape(
                {
                    "reference_source": "not_requested",
                    "reference_state_key": None,
                    "reference": None,
                    "reference_cache_hit": True,
                    "feedback_eligible": False,
                }
            )

    def test_window_metrics_use_only_active_windows_as_denominator(self) -> None:
        def event(assigned: int, queue: int) -> dict[str, object]:
            return {
                "kind": "window",
                "decision": {
                    "assigned_players": assigned,
                    "complete_assignment": True,
                    "commands_prepared": assigned,
                    "commands_sent": assigned,
                    "invalid_assignments": 0,
                    "dispatch_channel_failed": False,
                    "initialization_running_warm_choices": assigned,
                    "initialization_refined_choices": assigned,
                    "initialization_lower_utility_choices": assigned,
                    "selected_running_warm_players": assigned,
                    "selected_starting_container_players": 0,
                    "selected_cold_or_nonrunning_players": 0,
                },
                "solver": {
                    "assignment_moves": assigned,
                    "inner_limit_hit": False,
                    "outer_limit_hit": False,
                    "oscillations": 0,
                    "inner_stable": assigned > 0,
                    "outer_stable": assigned > 0,
                    "termination": "converged" if assigned else "no_players",
                },
                "cluster": {
                    "queue_parent_blocked_total": queue,
                    "queue_resident_total": queue,
                    "queue_runnable_total": queue,
                    "queue_starting_resident_total": queue,
                    "queue_data_blocked_total": queue,
                },
                "social": {
                    "reference_source": "offline_table",
                    "reference_state_key": 7,
                    "reference": 2.5,
                },
            }

        artifacts = SimpleNamespace(nse_events=[event(0, 100), event(2, 4)])
        result = _window_metrics(artifacts)
        self.assertEqual(result["active_window_count"], 1)
        self.assertEqual(result["assigned_players"], 2)
        self.assertEqual(result["queue_parent_blocked_mean"], 4.0)
        self.assertEqual(result["selected_running_warm_share"], 1.0)

    def test_pair_rows_are_left_minus_right_and_tape_bound(self) -> None:
        rows = []
        for role in COHORTS:
            seeds = range(66, 71) if role.startswith("g2") else range(71, 76)
            for index in seeds:
                value = 12.0 if role in {"g2_warm", "g6", "g7"} else 10.0
                rows.append(_raw(role, f"D{index}", value))
        pairs = _pair_rows(rows)
        self.assertEqual(len(pairs), 20)
        g2 = next(row for row in pairs if row["contrast"] == "g2_warm_minus_g2_c0")
        self.assertEqual(g2["delta_qpr"], 2.0)
        self.assertEqual(g2["ratio_qpr"], 1.2)
        self.assertTrue(math.isclose(g2["delta_latency_ms"], 2.0))

        rows[0]["workload_tape_sha256"] = "changed"
        with self.assertRaises(ProtocolValidationError):
            _pair_rows(rows)

    def test_authorization_is_exact_conjunction(self) -> None:
        raw = []
        for role in COHORTS:
            seeds = range(66, 71) if role.startswith("g2") else range(71, 76)
            for index in seeds:
                row = _raw(role, f"D{index}")
                row["maximum_executable_frontier_hops_ahead"] = (
                    2.0 if role == "g6" else 1.0
                )
                row["frontier_hop_violation_count"] = 0.0
                row["initialization_refined_choices"] = 1.0 if role == "g7" else 0.0
                row["initialization_lower_utility_choices"] = (
                    1.0 if role == "g7" else 0.0
                )
                row["unreferenced_active_window_count"] = 2.0 if role == "g7" else 0.0
                raw.append(row)
        pairs = [
            {
                "contrast": "g7_minus_g6",
                "delta_queue_parent_blocked_mean": -1.0,
                "delta_queue_resident_mean": -1.0,
                "delta_throughput_kreq_per_s": -0.1,
                "delta_qpr": -0.2,
                "delta_unreferenced_active_window_count": 2.0,
            }
            for _ in range(5)
        ]
        decision = evaluate_conditions(raw, pairs)
        self.assertTrue(decision["g8_candidate_preregistration_authorized"])
        self.assertEqual(
            decision["status"],
            "complete_g8_frontier_only_preregistration_authorized",
        )

        next(row for row in raw if row["role"] == "g6")[
            "maximum_executable_frontier_hops_ahead"
        ] = 1.0
        next(
            row
            for row in raw
            if row["role"] == "g6" and row["maximum_executable_frontier_hops_ahead"] > 1
        )["maximum_executable_frontier_hops_ahead"] = 1.0
        decision = evaluate_conditions(raw, pairs)
        self.assertFalse(decision["g8_candidate_preregistration_authorized"])
        self.assertFalse(
            decision["conditions"]["A2_g6_deeper_than_one_hop_at_least_four_seeds"][
                "passed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
