from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

import scripts.reviewer_experiments.protocol.nse_e3_causal_arrival_shock_training_reveal_v107 as reveal_module
from scripts.reviewer_experiments.protocol.nse_e3_causal_arrival_shock_training_reveal_v107 import (
    ARMS,
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


class CausalArrivalShockRevealV107Tests(unittest.TestCase):
    def test_reveal_hashes_match_frozen_joint_blind_audit(self) -> None:
        self.assertEqual(
            reveal_module.BLIND_AUDIT_FILE_SHA256,
            "5ff8fcd4dadd0a5c84a3f5365482ab637205b947180b446fb705e0795c7e48d3",
        )
        self.assertEqual(
            reveal_module.BLIND_AUDIT_HASH,
            "d8ea009593005647deda425253c8a8410658db5f5dcc71cc6f6d04ff4ac440a5",
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

    def test_joint_gate_uses_frozen_stricter_shock_tie_break(self) -> None:
        result = evaluate_training_rows(rows_fixture(), THRESHOLDS)
        self.assertTrue(result["joint_training_gate_pass"])
        self.assertEqual(
            result["selected_profiles"]["E3"]["arm_id"],
            "v107-e3-causal-arrival-shock20-resource-pareto-initializer-only",
        )
        self.assertEqual(len(result["passing_candidate_rankings"]["E3"]), 2)
        diagnostic = result["arm_aggregates"][
            "v107-e3-causal-arrival-shock20-resource-pareto-initializer-only"
        ]["E3.spike5x50ms"]["formal_absolute_diagnostics"]["qpr_finite_only"]
        self.assertFalse(diagnostic["used_for_V107_selection"])

    def test_one_large_outlier_cannot_satisfy_two_of_three_rule(self) -> None:
        rows = rows_fixture()
        for row in rows:
            if (
                row["arm_id"]
                == "v107-e3-causal-arrival-shock15-resource-pareto-initializer-only"
                and row["scenario_id"] == "E3.spike5x50ms"
            ):
                value = 10.0 if row["seed"] == "E892" else 0.9
                row["qpr_finite_only"] = value
                row["qpr_zero_completed_as_zero"] = value
        result = evaluate_training_rows(rows, THRESHOLDS)
        gate = result["paired_candidate_results"][
            "v107-e3-causal-arrival-shock15-resource-pareto-initializer-only"
        ]["E3.spike5x50ms"]["gates"]["qpr_finite_only"]
        self.assertGreater(gate["candidate_mean"], gate["anchor_mean"])
        self.assertEqual(gate["direction_consistent_seed_count"], 1)
        self.assertFalse(gate["passed"])

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
