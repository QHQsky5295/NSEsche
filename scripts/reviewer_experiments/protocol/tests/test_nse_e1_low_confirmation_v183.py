from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_fresh_seed_confirmation_v183 as v183,
)


class V183FreshSeedConfirmationTests(unittest.TestCase):
    def test_plan_and_training_freeze_are_exact(self) -> None:
        self.assertEqual(
            hashlib.sha256(v183.PLAN.read_bytes()).hexdigest(), v183.PLAN_SHA256
        )
        plan = v183._assert_plan_and_training()
        self.assertEqual(
            tuple(plan["scientific_boundary"]["confirmation_seeds"]), v183.SEEDS
        )
        self.assertEqual(plan["confirmation_matrix"]["total_online_runs"], 60)
        self.assertEqual(
            plan["confirmation_matrix"]["candidate_specific_reference_builds"], 20
        )
        self.assertEqual(
            plan["comparison_scope"]["throughput_primary_comparator"],
            "sche_orion",
        )
        self.assertFalse(
            plan["single_reveal_joint_confirmation_gate"]["training_rows_pooled"]
        )

    def test_dummy_manifest_generation_is_exact_three_by_twenty(self) -> None:
        seeds = tuple(f"E{index}" for index in range(9001, 9021))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest = v183._build_unbound_product(root, seeds, "1" * 40)
            v183._validate_product(
                manifest, seeds, tapes_bound=False, references_bound=False
            )
            self.assertEqual(len(manifest["runs"]), 60)
            self.assertEqual(len(manifest["reference_build_dependencies"]), 20)
            self.assertTrue(
                all(
                    ("reference_dependency" in run) is (run["method"] == "sche_nash")
                    for run in manifest["runs"]
                )
            )
            self.assertEqual(
                [(run["method"], run["seed"]) for run in manifest["runs"]],
                [(method, seed) for method in v183.METHODS for seed in seeds],
            )

    @staticmethod
    def _rows(
        *, candidate_shift: float = 0.2, candidate_win_count: int = 20
    ) -> list[dict[str, object]]:
        rows = []
        for index, seed in enumerate(v183.SEEDS):
            orion = 1.0 + index / 100.0
            ocs = 0.9 + index / 100.0
            candidate = max(orion, ocs) + (
                candidate_shift if index < candidate_win_count else -candidate_shift
            )
            for method, throughput in (
                ("sche_orion", orion),
                ("sche_OCS", ocs),
                ("sche_nash", candidate),
            ):
                rows.append(
                    {
                        "method": method,
                        "seed": seed,
                        "throughput_requests_per_ms": throughput,
                        "qpr_finite_only": throughput / 10.0,
                        "qpr_zero_completed_as_zero": throughput / 10.0,
                    }
                )
        return rows

    def test_joint_gate_passes_only_complete_strict_product(self) -> None:
        evaluation = v183._evaluate_confirmation(self._rows())
        self.assertTrue(evaluation["all_three_metric_gates_pass"])
        for metric in v183.METRICS:
            gate = evaluation["gates"][metric]
            self.assertEqual(gate["paired_positive_wins_against_primary"], 20)
            self.assertTrue(gate["candidate_strictly_exceeds_both_baseline_means"])
            self.assertEqual(
                gate["paired_candidate_minus_primary_BCa_95_percent_interval"][
                    "method"
                ],
                "BCa",
            )

    def test_mean_advantage_does_not_override_win_gate(self) -> None:
        rows = self._rows(candidate_shift=0.01, candidate_win_count=11)
        for row in rows:
            if row["method"] == "sche_nash" and row["seed"] == v183.SEEDS[0]:
                row["throughput_requests_per_ms"] = 10.0
                row["qpr_finite_only"] = 1.0
                row["qpr_zero_completed_as_zero"] = 1.0
        evaluation = v183._evaluate_confirmation(rows)
        self.assertFalse(evaluation["all_three_metric_gates_pass"])
        self.assertLess(
            evaluation["gates"]["throughput_requests_per_ms"][
                "paired_positive_wins_against_primary"
            ],
            12,
        )

    def test_ties_and_nonfinite_candidate_fail_closed(self) -> None:
        tied = self._rows(candidate_shift=0.0)
        self.assertFalse(
            v183._evaluate_confirmation(tied)["all_three_metric_gates_pass"]
        )
        broken = self._rows()
        next(
            row
            for row in broken
            if row["method"] == "sche_nash" and row["seed"] == v183.SEEDS[-1]
        )["qpr_finite_only"] = None
        with self.assertRaisesRegex(RuntimeError, "nonfinite"):
            v183._evaluate_confirmation(broken)

    def test_qpr_uses_frozen_drained_cohort_latency_definition(self) -> None:
        metrics = v183._summary_metrics(
            {
                "fixed_observation_window": {
                    "completed": 1,
                    "throughput_requests_per_second": 1000.0,
                },
                "drained_arrival_cohort": {
                    "completed": 1,
                    "latency_ms": {"mean": 2.0},
                },
                "latency_ms": {"mean": 200.0},
                "simulator_internal_cost_per_completed_request": 2.0,
            }
        )
        self.assertEqual(metrics["throughput_requests_per_ms"], 1.0)
        self.assertEqual(metrics["latency_mean_ms"], 2.0)
        self.assertEqual(metrics["qpr_finite_only"], 0.25)


if __name__ == "__main__":
    unittest.main()
