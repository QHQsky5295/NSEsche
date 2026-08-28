from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol.nse_e3e4_guarded_anchor_training_reveal_v96 import (
    ARMS,
    EXPECTED_SCENARIOS,
    EXPECTED_SEEDS,
    evaluate_training_rows,
    summary_metrics,
)


THRESHOLDS = {
    scenario: {
        "throughput_requests_per_ms": 2.0,
        "qpr_finite_only": 2.0,
        "qpr_zero_completed_as_zero": 2.0,
    }
    for scenario in EXPECTED_SCENARIOS
}


def rows_fixture() -> list[dict]:
    rows = []
    for arm_id, arm in ARMS.items():
        scenarios = [
            scenario
            for scenario in EXPECTED_SCENARIOS
            if scenario.startswith(arm["experiment_id"] + ".")
        ]
        for scenario in scenarios:
            for index, seed in enumerate(EXPECTED_SEEDS):
                if arm["role"] == "anchor":
                    throughput, qpr = 1.0, 1.0
                elif arm_id in {
                    "v96-e3-idle-warm-srpt",
                    "v96-e4-idle-warm-no-srpt",
                }:
                    throughput = (1.01, 1.01, 0.99)[index]
                    qpr = (1.1, 1.1, 0.9)[index]
                else:
                    throughput = (0.9, 0.9, 1.4)[index]
                    qpr = (0.9, 0.9, 1.4)[index]
                rows.append(
                    {
                        "arm_id": arm_id,
                        "scenario_id": scenario,
                        "seed": seed,
                        "run_id": f"{arm_id}.{scenario}.{seed}",
                        "fixed_window_completed": 1,
                        "throughput_requests_per_ms": throughput,
                        "qpr_finite_only": qpr,
                        "qpr_zero_completed_as_zero": qpr,
                    }
                )
    return rows


class GuardedAnchorTrainingRevealV96Tests(unittest.TestCase):
    def test_summary_metrics_preserve_both_qpr_conventions(self) -> None:
        positive = summary_metrics(
            {
                "fixed_observation_window": {
                    "completed": 10,
                    "throughput_requests_per_second": 1000.0,
                },
                "latency_ms": {"mean": 2.0},
                "simulator_internal_cost_per_completed_request": 4.0,
            },
            "positive",
        )
        self.assertEqual(positive["throughput_requests_per_ms"], 1.0)
        self.assertEqual(positive["qpr_finite_only"], 0.125)
        self.assertEqual(positive["qpr_zero_completed_as_zero"], 0.125)
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

    def test_joint_paired_gate_selects_only_direction_consistent_arms(self) -> None:
        result = evaluate_training_rows(rows_fixture(), THRESHOLDS)
        self.assertTrue(result["joint_training_gate_pass"])
        self.assertEqual(
            result["selected_profiles"]["E3"]["arm_id"],
            "v96-e3-idle-warm-srpt",
        )
        self.assertEqual(
            result["selected_profiles"]["E4"]["arm_id"],
            "v96-e4-idle-warm-no-srpt",
        )
        self.assertFalse(
            result["dimension_scores"]["E3"]["v96-e3-idle-warm-no-srpt"][
                "all_required_gates_pass"
            ]
        )
        diagnostic = result["arm_aggregates"]["v96-e3-idle-warm-srpt"][
            "E3.spike5x50ms"
        ]["formal_absolute_diagnostics"]["qpr_finite_only"]
        self.assertFalse(diagnostic["used_for_V96_selection"])

    def test_one_large_outlier_cannot_satisfy_two_of_three_rule(self) -> None:
        rows = rows_fixture()
        for row in rows:
            if (
                row["arm_id"] == "v96-e3-idle-warm-srpt"
                and row["scenario_id"] == "E3.spike5x50ms"
            ):
                value = 10.0 if row["seed"] == "E748" else 0.9
                row["qpr_finite_only"] = value
                row["qpr_zero_completed_as_zero"] = value
        result = evaluate_training_rows(rows, THRESHOLDS)
        gate = result["paired_candidate_results"]["v96-e3-idle-warm-srpt"][
            "E3.spike5x50ms"
        ]["gates"]["qpr_finite_only"]
        self.assertGreater(gate["candidate_mean"], gate["anchor_mean"])
        self.assertEqual(gate["direction_consistent_seed_count"], 1)
        self.assertFalse(gate["passed"])
        self.assertIsNone(result["selected_profiles"]["E3"])


if __name__ == "__main__":
    unittest.main()
