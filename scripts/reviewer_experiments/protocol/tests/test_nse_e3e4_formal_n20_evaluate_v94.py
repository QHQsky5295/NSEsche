from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol.nse_e3e4_formal_n20_evaluate_v94 import (
    evaluate_rows,
)


class FormalN20EvaluationV94Tests(unittest.TestCase):
    @staticmethod
    def _row(method: str, seed: str, *, completed: int, qpr: float) -> dict[str, str]:
        throughput = qpr if completed else 0.0
        return {
            "experiment_id": "E4",
            "burst_pattern": "",
            "algorithm": method,
            "seed": seed,
            "run_id": f"{method}.{seed}",
            "completed": str(completed),
            "throughput": str(throughput),
            "cost": "1" if completed else "",
            "latency": "1" if completed else "",
        }

    def test_zero_completion_convention_is_distinct_and_auditable(self) -> None:
        rows = [
            self._row("NSESche", "E01", completed=1, qpr=0.8),
            self._row("NSESche", "E02", completed=1, qpr=0.8),
            self._row("Baseline", "E01", completed=1, qpr=1.0),
            self._row("Baseline", "E02", completed=0, qpr=0.0),
        ]
        result = evaluate_rows(
            rows,
            expected_scenarios=("E4.steady",),
            expected_methods=("NSESche", "Baseline"),
            expected_seeds=("E01", "E02"),
        )
        gates = result["scenario_results"]["E4.steady"]["gates"]
        self.assertFalse(gates["qpr_finite_only"]["strictly_greater"])
        self.assertTrue(gates["qpr_zero_completed_as_zero"]["strictly_greater"])
        self.assertEqual(
            result["scenario_results"]["E4.steady"]["methods"]["Baseline"][
                "qpr_finite_only"
            ]["n_finite"],
            1,
        )

    def test_tie_is_not_strict_dominance(self) -> None:
        rows = [
            self._row(method, seed, completed=1, qpr=1.0)
            for method in ("NSESche", "Baseline")
            for seed in ("E01", "E02")
        ]
        result = evaluate_rows(
            rows,
            expected_scenarios=("E4.steady",),
            expected_methods=("NSESche", "Baseline"),
            expected_seeds=("E01", "E02"),
        )
        self.assertFalse(result["all_four_scenarios_pass"])
        gates = result["scenario_results"]["E4.steady"]["gates"]
        self.assertTrue(all(not gate["strictly_greater"] for gate in gates.values()))


if __name__ == "__main__":
    unittest.main()
