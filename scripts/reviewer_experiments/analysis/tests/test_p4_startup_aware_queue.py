from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.p4_startup_aware_queue import (
    evaluate_gate,
)
from scripts.reviewer_experiments.protocol.p4_startup_aware_queue import (
    P4_CANDIDATE,
    P4_CONTROL,
    P4_SETTING_LABELS,
)
from scripts.reviewer_experiments.protocol.schema import (
    P4_STARTUP_AWARE_QUEUE_SEEDS,
)


def _trace(offset: int) -> list[dict]:
    return [
        {"window": index + 1, "assigned_players": 1, "assignment_hash": index + offset}
        for index in range(1_000)
    ]


def _rows() -> list[dict]:
    rows = []
    for seed in P4_STARTUP_AWARE_QUEUE_SEEDS:
        for label in P4_SETTING_LABELS:
            candidate = label == P4_CANDIDATE
            rows.append(
                {
                    "seed": seed,
                    "setting": label,
                    "qc_valid": True,
                    "throughput_requests_per_ms": 1.02 if candidate else 1.0,
                    "qpr": 1.12 if candidate else 1.0,
                    "completion_ratio": 0.8,
                    "latency_mean_ms": 100.0,
                    "cost_per_completed_request": 1.0,
                    "placement_policy_wall_mean_ns": 1_000.0,
                    "formula_method_boundary_pass": True,
                    "nash_runtime_pass": True,
                    "startup_positive_active_window_share": 0.20 if candidate else 0.0,
                    "window_assignment_trace": _trace(10 if candidate else 0),
                }
            )
    return rows


class P4StartupAwareQueueAnalysisTests(unittest.TestCase):
    def test_selects_candidate_only_when_all_ten_conditions_pass(self) -> None:
        result = evaluate_gate(_rows())
        self.assertTrue(result["qualified"])
        self.assertEqual(result["selected_setting"], P4_CANDIDATE)
        self.assertTrue(result["baseline_compatibility_preregistration_authorized"])
        self.assertEqual(result["joint_wins"], 5)
        self.assertEqual(result["activation_seed_count"], 5)
        self.assertEqual(result["assignment_change_seed_count"], 5)
        self.assertEqual(len(result["conditions"]), 10)

    def test_activation_and_assignment_change_are_conjunctive(self) -> None:
        rows = _rows()
        for row in rows:
            if row["setting"] == P4_CANDIDATE and row["seed"] in {"D126", "D127"}:
                row["startup_positive_active_window_share"] = 0.09
                row["window_assignment_trace"] = _trace(0)
        result = evaluate_gate(rows)
        self.assertFalse(result["conditions"]["condition_3_mechanism_activation"])
        self.assertIsNone(result["selected_setting"])

    def test_dual_mean_threshold_is_conjunctive(self) -> None:
        rows = _rows()
        for row in rows:
            if row["setting"] == P4_CANDIDATE:
                row["qpr"] = 1.109
        result = evaluate_gate(rows)
        self.assertFalse(result["conditions"]["condition_4_viable_dual_mean_effect"])
        self.assertIsNone(result["selected_setting"])

    def test_one_bad_seed_fails_floor(self) -> None:
        rows = _rows()
        target = next(
            row
            for row in rows
            if row["setting"] == P4_CANDIDATE and row["seed"] == "D130"
        )
        target["throughput_requests_per_ms"] = 0.79
        target["qpr"] = 0.79
        result = evaluate_gate(rows)
        self.assertFalse(result["conditions"]["condition_6_per_seed_safety"])
        self.assertFalse(result["qualified"])

    def test_boundary_or_runtime_failure_cannot_be_outvoted(self) -> None:
        rows = _rows()
        target = next(
            row
            for row in rows
            if row["setting"] == P4_CONTROL and row["seed"] == "D128"
        )
        target["formula_method_boundary_pass"] = False
        target["nash_runtime_pass"] = False
        result = evaluate_gate(rows)
        self.assertFalse(result["conditions"]["condition_2_formula_and_method_boundary"])
        self.assertFalse(result["conditions"]["condition_9_runtime_reference_integrity"])
        self.assertIsNone(result["selected_setting"])

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
