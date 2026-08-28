from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol.nse_e3e4_qpr_recovery_training_reveal_v95 import (
    EXPECTED_SCENARIOS,
    METRICS,
    _aggregate,
    evaluate_training_rows,
    summary_metrics,
)


class V95QprRecoveryTrainingRevealTests(unittest.TestCase):
    @staticmethod
    def _row(
        candidate_id: str,
        scenario_id: str,
        seed: str,
        values: tuple[float, float, float],
    ) -> dict:
        return {
            "candidate_id": candidate_id,
            "scenario_id": scenario_id,
            "seed": seed,
            "run_id": f"{candidate_id}.{scenario_id}.{seed}",
            "fixed_window_completed": 1,
            **dict(zip(METRICS, values)),
        }

    def test_independent_E3_and_E4_winners_may_come_from_different_pairs(self) -> None:
        candidates = {
            "a": {"E3_profile": "e3-a", "E4_profile": "e4-a"},
            "b": {"E3_profile": "e3-b", "E4_profile": "e4-b"},
        }
        thresholds = {
            scenario: {metric: 1.0 for metric in METRICS}
            for scenario in EXPECTED_SCENARIOS
        }
        rows = []
        for candidate_id in candidates:
            for scenario in EXPECTED_SCENARIOS:
                if scenario == "E4.steady":
                    value = 1.1 if candidate_id == "b" else 0.9
                else:
                    value = 1.2 if candidate_id == "a" else 0.8
                for seed in ("E726", "E727", "E728"):
                    rows.append(
                        self._row(candidate_id, scenario, seed, (value, value, value))
                    )
        result = evaluate_training_rows(rows, thresholds, candidate_profiles=candidates)
        self.assertTrue(result["joint_training_gate_pass"])
        self.assertEqual(result["selected_profiles"]["E3"]["candidate_id"], "a")
        self.assertEqual(result["selected_profiles"]["E4"]["candidate_id"], "b")

    def test_ties_fail_and_lexical_id_breaks_equal_passer_score(self) -> None:
        candidates = {
            "a": {"E3_profile": "e3-a", "E4_profile": "e4-a"},
            "b": {"E3_profile": "e3-b", "E4_profile": "e4-b"},
        }
        thresholds = {
            scenario: {metric: 1.0 for metric in METRICS}
            for scenario in EXPECTED_SCENARIOS
        }
        rows = []
        for candidate_id in candidates:
            for scenario in EXPECTED_SCENARIOS:
                value = 1.2 if scenario.startswith("E3") else 1.0
                for seed in ("E726", "E727", "E728"):
                    rows.append(
                        self._row(candidate_id, scenario, seed, (value, value, value))
                    )
        result = evaluate_training_rows(rows, thresholds, candidate_profiles=candidates)
        self.assertEqual(result["selected_profiles"]["E3"]["candidate_id"], "a")
        self.assertIsNone(result["selected_profiles"]["E4"])
        self.assertFalse(result["joint_training_gate_pass"])

    def test_zero_completion_conventions_and_invalid_positive_denominator(self) -> None:
        zero = summary_metrics(
            {
                "fixed_observation_window": {
                    "completed": 0,
                    "throughput_requests_per_second": 0.0,
                },
                "latency_ms": {"mean": None},
                "simulator_internal_cost_per_completed_request": None,
            },
            "zero",
        )
        self.assertIsNone(zero["qpr_finite_only"])
        self.assertEqual(zero["qpr_zero_completed_as_zero"], 0.0)

        positive_zero_throughput = summary_metrics(
            {
                "fixed_observation_window": {
                    "completed": 1,
                    "throughput_requests_per_second": 0.0,
                },
                "latency_ms": {"mean": 2.0},
                "simulator_internal_cost_per_completed_request": 3.0,
            },
            "positive-zero-throughput",
        )
        self.assertEqual(positive_zero_throughput["qpr_finite_only"], 0.0)
        self.assertEqual(positive_zero_throughput["qpr_zero_completed_as_zero"], 0.0)

        aggregate_rows = [
            {
                "seed": "E726",
                "fixed_window_completed": 1,
                "qpr_finite_only": 2.0,
            },
            {
                "seed": "E727",
                "fixed_window_completed": 1,
                "qpr_finite_only": 4.0,
            },
            {
                "seed": "E728",
                "fixed_window_completed": 0,
                "qpr_finite_only": None,
            },
        ]
        finite_only = _aggregate(aggregate_rows, "qpr_finite_only")
        self.assertEqual(finite_only["n_total"], 3)
        self.assertEqual(finite_only["n_finite"], 2)
        self.assertEqual(finite_only["mean"], 3.0)

        with self.assertRaisesRegex(ValueError, "positive-completion"):
            summary_metrics(
                {
                    "fixed_observation_window": {
                        "completed": 1,
                        "throughput_requests_per_second": 1.0,
                    },
                    "latency_ms": {"mean": None},
                    "simulator_internal_cost_per_completed_request": 1.0,
                },
                "invalid",
            )


if __name__ == "__main__":
    unittest.main()
