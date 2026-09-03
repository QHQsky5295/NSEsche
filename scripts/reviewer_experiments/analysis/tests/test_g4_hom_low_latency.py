from __future__ import annotations

import unittest

from scripts.reviewer_experiments.analysis.g4_hom_low_latency import (
    _association_passes,
    _function_stages,
    _match_pair,
)


class G4HomLowLatencyTests(unittest.TestCase):
    def test_function_boundaries_match_frozen_definitions(self) -> None:
        stages = _function_stages(
            {
                "ready_schedule_frame": 3,
                "scheduled_frame": 5,
                "cold_start_done_frame": 8,
                "data_received_frame": 11,
                "function_done_frame": 17,
            }
        )
        self.assertEqual(
            stages,
            {
                "schedule_wait_ms": 2.0,
                "cold_start_wait_ms": 3.0,
                "data_wait_ms": 3.0,
                "execution_ms": 6.0,
            },
        )

    def test_early_binding_and_missing_boundaries_are_zero_clamped(self) -> None:
        stages = _function_stages(
            {
                "ready_schedule_frame": 9,
                "scheduled_frame": 4,
                "cold_start_done_frame": None,
                "data_received_frame": None,
                "function_done_frame": 12,
            }
        )
        self.assertEqual(stages["schedule_wait_ms"], 0.0)
        self.assertEqual(stages["cold_start_wait_ms"], 0.0)
        self.assertEqual(stages["data_wait_ms"], 0.0)
        self.assertEqual(stages["execution_ms"], 3.0)

    def test_common_completion_pair_preserves_asymmetric_counts(self) -> None:
        def function(stage: float) -> dict[str, object]:
            return {
                "stages": {
                    "schedule_wait_ms": stage,
                    "cold_start_wait_ms": 0.0,
                    "data_wait_ms": 0.0,
                    "execution_ms": 1.0,
                }
            }

        nash = {
            "seed": "D71",
            "run_id": "nash",
            "full_cohort_latency_mean_ms": 10.0,
            "_requests": {"a": {"latency_ms": 10.0}, "b": {"latency_ms": 12.0}},
            "_functions": {("a", "0"): function(4.0), ("b", "0"): function(5.0)},
        }
        baseline = {
            "seed": "D71",
            "run_id": "base",
            "method": "sche_Hiku",
            "full_cohort_latency_mean_ms": 7.0,
            "_requests": {"a": {"latency_ms": 7.0}, "c": {"latency_ms": 8.0}},
            "_functions": {("a", "0"): function(1.0), ("c", "0"): function(2.0)},
        }
        for row, schedule_mean in ((nash, 4.5), (baseline, 1.5)):
            for stage in (
                "schedule_wait_ms",
                "cold_start_wait_ms",
                "data_wait_ms",
                "execution_ms",
            ):
                row[f"{stage}_mean"] = (
                    schedule_mean if stage == "schedule_wait_ms" else 0.0
                )
        result = _match_pair(nash, baseline)
        self.assertEqual(result["common_completed_requests"], 1)
        self.assertEqual(result["nash_only_completed_requests"], 1)
        self.assertEqual(result["baseline_only_completed_requests"], 1)
        self.assertEqual(result["matched_request_latency_difference_mean"], 3.0)
        self.assertEqual(
            result["matched_function_schedule_wait_ms_difference_mean"], 3.0
        )

    def test_expected_direction_association_requires_loo_stability(self) -> None:
        passing = {
            "rho": 0.7,
            "expected_sign": 1,
            "leave_one_seed_out": [
                {"rho": 0.6},
                {"rho": 0.7},
                {"rho": 0.8},
                {"rho": 0.5},
                {"rho": -0.2},
            ],
        }
        self.assertTrue(_association_passes(passing))
        passing["leave_one_seed_out"][1]["rho"] = -0.1
        self.assertFalse(_association_passes(passing))


if __name__ == "__main__":
    unittest.main()
