from __future__ import annotations

import unittest

from scripts.reviewer_experiments.analysis.g3_existing_diagnosis import (
    spearman,
    stage_breakdown,
)


class G3ExistingDiagnosisTests(unittest.TestCase):
    def test_stage_breakdown_matches_completed_function_boundaries(self) -> None:
        result = stage_breakdown(
            [
                {
                    "request_id": 1,
                    "functions": [
                        {
                            "ready_schedule_frame": 2,
                            "scheduled_frame": 4,
                            "cold_start_done_frame": 9,
                            "data_received_frame": 12,
                            "function_done_frame": 18,
                        },
                        {
                            "ready_schedule_frame": 18,
                            "scheduled_frame": 19,
                            "cold_start_done_frame": None,
                            "data_received_frame": None,
                            "function_done_frame": 23,
                        },
                    ],
                }
            ]
        )
        self.assertEqual(result["completed_request_events"], 1)
        self.assertEqual(result["completed_function_events"], 2)
        self.assertEqual(result["cold_start_event_share"], 0.5)
        self.assertEqual(result["schedule_wait_ms"], 1.5)
        self.assertEqual(result["cold_start_wait_ms"], 2.5)
        self.assertEqual(result["data_wait_ms"], 1.5)
        self.assertEqual(result["execution_ms"], 5.0)

    def test_spearman_reports_all_ties_and_missing_pairwise(self) -> None:
        rho, count = spearman([1, 2, 2, None, 4], [10, 20, 20, 99, 40])
        self.assertEqual(count, 4)
        self.assertAlmostEqual(rho, 1.0)

        rho, count = spearman([1, 1, 1], [2, 3, 4])
        self.assertEqual(count, 3)
        self.assertIsNone(rho)


if __name__ == "__main__":
    unittest.main()
