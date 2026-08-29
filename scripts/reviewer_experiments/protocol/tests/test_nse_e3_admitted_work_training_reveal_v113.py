from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

import scripts.reviewer_experiments.protocol.nse_e3_admitted_work_training_reveal_v113 as reveal_module
from scripts.reviewer_experiments.protocol.nse_e3_admitted_work_training_reveal_v113 import (
    ARMS,
    CANDIDATE_ID,
    EXPECTED_SCENARIOS,
    EXPECTED_SEEDS,
    evaluate_training_rows,
    main,
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
        for scenario in EXPECTED_SCENARIOS:
            for index, seed in enumerate(EXPECTED_SEEDS):
                if arm["role"] == "anchor":
                    throughput, qpr = 1.0, 1.0
                else:
                    throughput = (1.01, 1.01, 0.99)[index]
                    qpr = (1.1, 1.1, 0.9)[index]
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


class AdmittedWorkRevealV113Tests(unittest.TestCase):
    def test_reveal_is_locked_to_the_frozen_joint_blind_audit(self) -> None:
        self.assertEqual(
            reveal_module.BLIND_AUDIT_FILE_SHA256,
            "e232780e70b300aabce6c659b34ac5f598c476379262806ab07dcb728918cf06",
        )
        self.assertEqual(
            reveal_module.BLIND_AUDIT_HASH,
            "a7dda9405bd804e2ee08ca94bf336361e394551d697b9321658fccf153b63acd",
        )

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

    def test_single_candidate_must_pass_all_nine_frozen_gates(self) -> None:
        result = evaluate_training_rows(rows_fixture(), THRESHOLDS)
        self.assertTrue(result["joint_training_gate_pass"])
        self.assertEqual(result["selected_profiles"]["E3"]["arm_id"], CANDIDATE_ID)
        self.assertEqual(len(result["passing_candidate_rankings"]["E3"]), 1)
        self.assertEqual(result["candidate_score"]["required_gate_count"], 9)
        diagnostic = result["arm_aggregates"][CANDIDATE_ID]["E3.spike5x50ms"][
            "formal_absolute_diagnostics"
        ]["qpr_finite_only"]
        self.assertFalse(diagnostic["used_for_V113_selection"])

    def test_one_large_outlier_cannot_satisfy_two_of_three_rule(self) -> None:
        rows = rows_fixture()
        for row in rows:
            if row["arm_id"] == CANDIDATE_ID and row["scenario_id"] == "E3.spike5x50ms":
                value = 10.0 if row["seed"] == "E910" else 0.9
                row["qpr_finite_only"] = value
                row["qpr_zero_completed_as_zero"] = value
        result = evaluate_training_rows(rows, THRESHOLDS)
        gate = result["paired_candidate_results"][CANDIDATE_ID]["E3.spike5x50ms"][
            "gates"
        ]["qpr_finite_only"]
        self.assertGreater(gate["candidate_mean"], gate["anchor_mean"])
        self.assertEqual(gate["direction_consistent_seed_count"], 1)
        self.assertFalse(gate["passed"])
        self.assertFalse(result["joint_training_gate_pass"])

    def test_help_and_incomplete_command_can_never_reveal(self) -> None:
        with patch.object(reveal_module, "execute_reveal") as execute:
            with self.assertRaises(SystemExit) as help_exit, contextlib.redirect_stdout(
                io.StringIO()
            ):
                main(["--help"])
            self.assertEqual(help_exit.exception.code, 0)
            execute.assert_not_called()
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(
                io.StringIO()
            ):
                main(["reveal"])
            execute.assert_not_called()
            main(["reveal", "--execute"])
            execute.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
