from __future__ import annotations

import unittest
from collections import Counter

from scripts.reviewer_experiments.analysis.m1_diagnosis import (
    _finalize_aggregate,
    _summary_semantic_payload,
    _window_semantic_payload,
)
from scripts.reviewer_experiments.protocol.schema import ProtocolValidationError


class M1DiagnosisAnalysisTests(unittest.TestCase):
    def test_summary_semantics_exclude_only_identity_and_timing(self) -> None:
        left = {
            "run_id": "old",
            "completed": 10,
            "scheduler_wall_ns": 100,
            "nested": {"path": "old/artifact"},
        }
        right = {
            "run_id": "new",
            "completed": 10,
            "scheduler_wall_ns": 900,
            "nested": {"path": "new/artifact"},
        }
        self.assertEqual(
            _summary_semantic_payload(left, "old"),
            _summary_semantic_payload(right, "new"),
        )
        right["completed"] = 9
        self.assertNotEqual(
            _summary_semantic_payload(left, "old"),
            _summary_semantic_payload(right, "new"),
        )

    def test_window_semantics_remove_observation_and_timing_only(self) -> None:
        row = {
            "kind": "window",
            "frame": 3,
            "decision": {
                "assignment_hash": 7,
                "commands_sent": 2,
                "selected_running_warm_players": 1,
                "warm_path_diagnostic_definition": "observation",
            },
            "social": {"welfare": 4.0, "reference_lookup_us": 90},
            "overhead": {"scheduler_wall_us": 100},
        }
        semantic = _window_semantic_payload(row, "run")
        self.assertEqual(semantic["decision"], {"assignment_hash": 7, "commands_sent": 2})
        self.assertEqual(semantic["social"], {"welfare": 4.0})
        self.assertNotIn("overhead", semantic)

    def test_aggregate_conserves_paths_and_reports_weighted_means(self) -> None:
        counters = Counter(
            {
                "assigned_players": 10,
                "request_function_players": 10,
                "selected_running_warm_players": 4,
                "selected_starting_container_players": 6,
                "selected_cold_or_nonrunning_players": 0,
                "running_warm_available_players": 7,
                "running_warm_bypassed_players": 3,
                "selected_lower_utility_than_warm_players": 1,
                "warm_bypass_utility_advantage_sum": 6.0,
                "warm_bypass_finish_score_delta_sum": 12.0,
            }
        )
        result = _finalize_aggregate(counters)
        self.assertEqual(result["warm_availability_share_of_assigned"], 0.7)
        self.assertEqual(result["warm_bypass_share_of_warm_available"], 3 / 7)
        self.assertEqual(result["warm_bypass_utility_advantage_mean"], 2.0)
        self.assertEqual(result["warm_bypass_finish_score_delta_mean"], 4.0)

        counters["selected_starting_container_players"] = 5
        with self.assertRaises(ProtocolValidationError):
            _finalize_aggregate(counters)


if __name__ == "__main__":
    unittest.main()
