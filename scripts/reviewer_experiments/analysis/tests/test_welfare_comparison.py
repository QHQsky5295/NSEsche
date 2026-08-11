from __future__ import annotations

import math
import unittest
from pathlib import Path

from scripts.reviewer_experiments.analysis.observability import (
    RunArtifacts,
    analyze_scheduler_run,
)


class WelfareComparisonTests(unittest.TestCase):
    def test_non_nash_posthoc_welfare_is_not_reported_as_na(self) -> None:
        artifacts = RunArtifacts(
            spec={
                "experiment_id": "E6",
                "cell_id": "E6.cp_br.middle",
                "run_id": "cp-br-e01",
                "seed": "E01",
                "method": "cp_br",
                "workload": {
                    "request_freq": "middle",
                    "topology": "heterogeneous",
                    "qos_profile": "mixed",
                },
                "cluster": {"node_count": 20, "topology": "heterogeneous"},
                "simulator_experiment": {"reference": {"mode": "offline_required"}},
                "reference_dependency": {"bytes": 1024},
            },
            run_directory=Path("synthetic"),
            environment={},
            frames=[],
            requests=[],
            scheduler_windows=[
                {
                    "policy_wall_time_ns": 40_000,
                    "policy_thread_cpu_ns": 30_000,
                    "wall_time_ns": 90_000,
                    "thread_cpu_ns": 70_000,
                    "welfare_evaluation_wall_time_ns": 45_000,
                    "welfare_evaluation_thread_cpu_ns": 35_000,
                }
            ],
            nse_events=[
                {
                    "kind": "welfare_window",
                    "schema": "NSE_POSTHOC_WELFARE_WINDOW_V1",
                    "decision": {
                        "initial_assignment_hash": 7,
                        "assignment_hash": 7,
                        "complete_assignment": True,
                    },
                    "social": {
                        "final_assignment_baseline_welfare": 80.0,
                        "final_welfare": 80.0,
                        "reference": 100.0,
                        "reference_source": "offline_table",
                        "reference_cache_hit": True,
                        "reference_compute_us": 0,
                        "reference_lookup_us": 2,
                        "empirical_gap": 0.2,
                    },
                    "overhead": {"evaluation_compute_us": 10},
                },
                {
                    "kind": "welfare_run_summary",
                    "schema": "NSE_POSTHOC_WELFARE_RUN_V1",
                    "reference_validation": {
                        "windows": 1,
                        "missing": 0,
                        "missing_ratio": 0.0,
                        "zero": 0,
                        "zero_ratio": 0.0,
                        "negative": 0,
                        "negative_ratio": 0.0,
                        "unavailable": 0,
                        "unavailable_ratio": 0.0,
                        "persist_failures": 0,
                        "offline_required_ok": True,
                    },
                },
            ],
        )

        row = analyze_scheduler_run(artifacts)
        self.assertEqual(row["nse_solver_window_count"], 0)
        self.assertEqual(row["welfare_evaluation_window_count"], 1)
        self.assertAlmostEqual(row["welfare_gap_mean"], 0.2)
        self.assertEqual(row["welfare_gap_valid_windows"], 1)
        self.assertAlmostEqual(row["placement_policy_wall_mean_us"], 40.0)
        self.assertAlmostEqual(row["scheduler_wall_mean_us"], 40.0)
        self.assertAlmostEqual(row["mechanism_total_wall_mean_us"], 90.0)
        self.assertAlmostEqual(row["welfare_evaluation_wall_mean_us"], 45.0)
        self.assertEqual(row["reference_validation_status"], "ok")
        self.assertEqual(row["reference_missing_ratio"], 0.0)
        self.assertEqual(row["reference_unavailable_ratio"], 0.0)
        self.assertEqual(row["reference_persist_failures"], 0.0)
        self.assertEqual(row["reference_offline_required_ok"], 1.0)
        self.assertFalse(row["policy_timing_derived_by_subtraction"])

    def test_common_mechanism_total_is_not_a_policy_timing_fallback(self) -> None:
        artifacts = RunArtifacts(
            spec={
                "experiment_id": "E1",
                "run_id": "legacy-without-policy-boundary",
                "seed": "E01",
                "method": "greedy",
            },
            run_directory=Path("synthetic"),
            environment={},
            frames=[],
            requests=[],
            scheduler_windows=[{"wall_time_ns": 90_000, "thread_cpu_ns": 70_000}],
            nse_events=[],
        )

        row = analyze_scheduler_run(artifacts)

        self.assertTrue(math.isnan(row["placement_policy_wall_mean_us"]))
        self.assertTrue(math.isnan(row["placement_policy_cpu_mean_us"]))
        self.assertAlmostEqual(row["mechanism_total_wall_mean_us"], 90.0)
        self.assertAlmostEqual(row["mechanism_total_cpu_mean_us"], 70.0)


if __name__ == "__main__":
    unittest.main()
