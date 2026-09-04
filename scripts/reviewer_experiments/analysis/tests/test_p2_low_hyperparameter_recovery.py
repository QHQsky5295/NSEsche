from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.p2_low_hyperparameter_recovery import (
    evaluate_gate,
)
from scripts.reviewer_experiments.protocol.p2_low_hyperparameter_recovery import (
    P2_LOW_SETTING_LABELS,
)
from scripts.reviewer_experiments.protocol.schema import (
    P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS,
)


def _rows() -> list[dict]:
    rows = []
    for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS:
        for label in P2_LOW_SETTING_LABELS:
            if label == "centre":
                throughput, qpr = 1.0, 1.0
            elif label == "r0_minus":
                throughput, qpr = 1.02, 1.12
            else:
                throughput, qpr = 0.99, 0.99
            rows.append(
                {
                    "seed": seed,
                    "setting": label,
                    "qc_valid": True,
                    "throughput_requests_per_ms": throughput,
                    "qpr": qpr,
                    "completion_ratio": 0.8,
                    "latency_mean_ms": 100.0,
                    "cost_per_completed_request": 1.0,
                    "placement_policy_wall_mean_ns": 1000.0,
                    "nash_runtime_pass": True,
                }
            )
    return rows


class P2LowHyperparameterRecoveryAnalysisTests(unittest.TestCase):
    def test_selects_only_all_pass_neighbour(self) -> None:
        result = evaluate_gate(_rows())
        self.assertEqual(result["selected_setting"], "r0_minus")
        self.assertTrue(result["formal_confirmation_preregistration_authorized"])
        report = next(
            row for row in result["candidate_reports"] if row["setting"] == "r0_minus"
        )
        self.assertTrue(report["qualified"])
        self.assertEqual(report["joint_wins"], 5)
        self.assertEqual(report["joint_nonlosses"], 5)

    def test_viability_threshold_is_conjunctive(self) -> None:
        rows = _rows()
        for row in rows:
            if row["setting"] == "r0_minus":
                row["qpr"] = 1.109
        result = evaluate_gate(rows)
        self.assertIsNone(result["selected_setting"])
        report = next(
            row for row in result["candidate_reports"] if row["setting"] == "r0_minus"
        )
        self.assertFalse(report["conditions"]["condition_2_viable_dual_mean_effect"])

    def test_one_bad_seed_fails_floor_and_robustness(self) -> None:
        rows = _rows()
        target = next(
            row
            for row in rows
            if row["setting"] == "r0_minus" and row["seed"] == "D125"
        )
        target["throughput_requests_per_ms"] = 0.79
        target["qpr"] = 0.79
        result = evaluate_gate(rows)
        report = next(
            row for row in result["candidate_reports"] if row["setting"] == "r0_minus"
        )
        self.assertFalse(report["conditions"]["condition_4_per_seed_safety"])
        self.assertFalse(report["qualified"])

    def test_runtime_failure_cannot_be_outvoted_by_performance(self) -> None:
        rows = _rows()
        target = next(
            row for row in rows if row["setting"] == "centre" and row["seed"] == "D123"
        )
        target["nash_runtime_pass"] = False
        result = evaluate_gate(rows)
        report = next(
            row for row in result["candidate_reports"] if row["setting"] == "r0_minus"
        )
        self.assertFalse(
            report["conditions"]["condition_7_runtime_reference_integrity"]
        )
        self.assertIsNone(result["selected_setting"])

    def test_fixed_label_order_breaks_exact_score_tie(self) -> None:
        rows = _rows()
        for row in rows:
            if row["setting"] == "r0_plus":
                row["throughput_requests_per_ms"] = 1.02
                row["qpr"] = 1.12
        result = evaluate_gate(rows)
        self.assertEqual(result["eligible_settings"], ["r0_minus", "r0_plus"])
        self.assertEqual(result["selected_setting"], "r0_minus")

    def test_incomplete_or_duplicate_population_fails_closed(self) -> None:
        incomplete = _rows()[:-1]
        result = evaluate_gate(incomplete)
        self.assertFalse(result["population_pass"])
        self.assertIsNone(result["selected_setting"])
        duplicate = _rows()
        duplicate.append(copy.deepcopy(duplicate[0]))
        result = evaluate_gate(duplicate)
        self.assertFalse(result["population_pass"])
        self.assertTrue(result["duplicate_identities"])
        self.assertIsNone(result["selected_setting"])


if __name__ == "__main__":
    unittest.main()
