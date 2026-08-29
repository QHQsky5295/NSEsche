from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_prepare_v136 import (
    BASELINE_METHODS,
    SCENARIOS,
    SEED_LIST,
)
from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_reveal_v136 import (
    evaluate_closure_rows,
)


def rows(anchor: float = 10.0, baseline: float = 5.0) -> list[dict]:
    output = []
    for method in [*BASELINE_METHODS, "sche_nash"]:
        value = anchor if method == "sche_nash" else baseline
        for scenario in SCENARIOS:
            for seed in SEED_LIST:
                output.append(
                    {
                        "run_id": f"{method}.{scenario}.{seed}",
                        "method": method,
                        "scenario": scenario,
                        "seed": seed,
                        "fixed_window_completed": 1,
                        "throughput_requests_per_ms": value,
                        "qpr_finite_only": value,
                        "qpr_zero_completed_as_zero": value,
                    }
                )
    return output


class AllBaselineClosureRevealV136Tests(unittest.TestCase):
    def test_complete_strictly_dominant_anchor_passes_all_nine_gates(self) -> None:
        result = evaluate_closure_rows(rows())
        self.assertTrue(result["joint_all_baseline_closure_pass"])
        self.assertEqual(result["passed_gate_count"], 9)
        self.assertEqual(result["failing_gaps"], [])

    def test_tie_fails_strict_mean_rule(self) -> None:
        synthetic = rows()
        for row in synthetic:
            if row["method"] == BASELINE_METHODS[0]:
                for metric in (
                    "throughput_requests_per_ms",
                    "qpr_finite_only",
                    "qpr_zero_completed_as_zero",
                ):
                    row[metric] = 10.0
        result = evaluate_closure_rows(synthetic)
        self.assertFalse(result["joint_all_baseline_closure_pass"])
        self.assertEqual(result["passed_gate_count"], 0)

    def test_one_of_three_positive_paired_directions_fails(self) -> None:
        synthetic = rows(anchor=10.0, baseline=1.0)
        target = BASELINE_METHODS[0]
        for row in synthetic:
            if row["method"] == target and row["seed"] in ("E1448", "E1449"):
                row["throughput_requests_per_ms"] = 11.0
        result = evaluate_closure_rows(synthetic)
        gate = result["closure_gates"][SCENARIOS[0]]["throughput_requests_per_ms"]
        self.assertTrue(gate["strict_mean_rule_pass"])
        self.assertFalse(gate["paired_direction_comparisons"][target]["passed"])
        self.assertFalse(result["joint_all_baseline_closure_pass"])

    def test_zero_completion_is_honest_for_both_qpr_conventions(self) -> None:
        synthetic = rows()
        target = synthetic[0]
        target["fixed_window_completed"] = 0
        target["qpr_finite_only"] = None
        target["qpr_zero_completed_as_zero"] = 0.0
        result = evaluate_closure_rows(synthetic)
        method = str(target["method"])
        scenario = str(target["scenario"])
        finite = result["method_scenario_aggregates"][method][scenario][
            "qpr_finite_only"
        ]
        zero = result["method_scenario_aggregates"][method][scenario][
            "qpr_zero_completed_as_zero"
        ]
        self.assertEqual(finite["n_finite"], 2)
        self.assertIsNone(finite["mean"])
        self.assertEqual(zero["n_finite"], 3)
        self.assertEqual(zero["n_zero_completed"], 1)
        self.assertFalse(result["joint_all_baseline_closure_pass"])


if __name__ == "__main__":
    unittest.main()
