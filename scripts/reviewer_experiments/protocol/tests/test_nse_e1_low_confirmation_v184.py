from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_disjoint_unpaired_confirmation_v184 as v184,
)
from scripts.reviewer_experiments.protocol.ledger import Ledger


class V184FreshSeedConfirmationTests(unittest.TestCase):
    def test_plan_and_training_freeze_are_exact(self) -> None:
        self.assertEqual(
            hashlib.sha256(v184.PLAN.read_bytes()).hexdigest(), v184.PLAN_SHA256
        )
        self.assertEqual(
            hashlib.sha256(v184.FAILURE_RECEIPT.read_bytes()).hexdigest(),
            v184.FAILURE_RECEIPT_FILE_SHA256,
        )
        plan = v184._assert_frozen_inputs()
        boundary = plan["scientific_boundary"]
        self.assertEqual(tuple(boundary["confirmation_seeds"]), v184.SEEDS)
        self.assertEqual(boundary["candidate_online_runs"], 20)
        self.assertEqual(boundary["baseline_online_runs"], 0)
        self.assertEqual(
            plan["frozen_baseline_evidence"]["throughput_primary"]["method"],
            "sche_orion",
        )
        self.assertFalse(boundary["training_rows_pooled"])
        self.assertFalse(boundary["V183_rows_pooled"])
        self.assertEqual(v184.EXECUTION_METHODS, ("sche_nash",))

    def test_clean_ledger_reads_event_type_and_nested_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            ledger = Ledger(path)
            ledger.append("attempt_started", {"run_id": "run-1", "attempt": 1})
            ledger.append("attempt_canonicalized", {"run_id": "run-1", "attempt": 1})
            count, last_hash = v184._assert_clean_ledger(path, {"run-1"})
            self.assertEqual(count, 2)
            self.assertEqual(len(last_hash), 64)
            ledger.append("attempt_quarantined", {"run_id": "run-2", "attempt": 1})
            with self.assertRaisesRegex(RuntimeError, "failure events"):
                v184._assert_clean_ledger(path, {"run-1"})

    def test_dummy_manifest_generation_is_exact_three_by_twenty(self) -> None:
        seeds = tuple(f"E{index}" for index in range(9001, 9021))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest = v184._build_unbound_product(root, seeds, "1" * 40)
            v184._validate_product(
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
                [(method, seed) for method in v184.METHODS for seed in seeds],
            )

    @staticmethod
    def _rows(
        *, candidate_shift: float = 0.2, candidate_win_count: int = 20
    ) -> list[dict[str, object]]:
        rows = []
        for index, seed in enumerate(v184.SEEDS):
            direction = (
                candidate_shift if index < candidate_win_count else -candidate_shift
            )
            rows.append(
                {
                    "method": "sche_nash",
                    "seed": seed,
                    "throughput_requests_per_ms": v184.FROZEN_BASELINES[
                        "throughput_requests_per_ms"
                    ]["mean"]
                    + direction,
                    "qpr_finite_only": v184.FROZEN_BASELINES["qpr_finite_only"]["mean"]
                    + direction / 10.0,
                    "qpr_zero_completed_as_zero": v184.FROZEN_BASELINES[
                        "qpr_zero_completed_as_zero"
                    ]["mean"]
                    + direction / 10.0,
                }
            )
        return rows

    def test_joint_gate_passes_only_complete_strict_product(self) -> None:
        evaluation = v184._evaluate_confirmation(self._rows())
        self.assertTrue(evaluation["all_three_metric_gates_pass"])
        for metric in v184.METRICS:
            gate = evaluation["gates"][metric]
            self.assertEqual(
                gate["individual_candidate_values_above_global_comparator_mean"][
                    "count"
                ],
                20,
            )
            self.assertFalse(
                gate["individual_candidate_values_above_global_comparator_mean"][
                    "used_as_gate"
                ]
            )
            self.assertTrue(gate["candidate_strictly_exceeds_frozen_baseline_mean"])
            self.assertEqual(
                gate[
                    "unpaired_candidate_minus_frozen_comparator_BCa_95_percent_interval"
                ]["method"],
                "independent_two_sample_BCa_mean_difference",
            )
            self.assertEqual(
                gate["two_sided_unpaired_permutation"]["alternative"], "two-sided"
            )

    def test_mean_advantage_is_not_confounded_by_global_mean_count(self) -> None:
        rows = self._rows(candidate_shift=0.01, candidate_win_count=11)
        row = rows[0]
        row["throughput_requests_per_ms"] = 10.0
        row["qpr_finite_only"] = 1.0
        row["qpr_zero_completed_as_zero"] = 1.0
        evaluation = v184._evaluate_confirmation(rows)
        self.assertTrue(evaluation["all_three_metric_gates_pass"])
        self.assertLess(
            evaluation["gates"]["throughput_requests_per_ms"][
                "individual_candidate_values_above_global_comparator_mean"
            ]["count"],
            12,
        )

    def test_frozen_comparator_rows_are_complete_and_mean_bound(self) -> None:
        for metric in v184.METRICS:
            values = v184._frozen_comparator_values(metric)
            self.assertEqual(len(values), 20)
            self.assertAlmostEqual(
                sum(values) / len(values),
                v184.FROZEN_BASELINES[metric]["mean"],
                places=15,
            )

    def test_unpaired_uncertainty_routines_report_independent_cohorts(self) -> None:
        candidate = [float(index) + 1.0 for index in range(20)]
        comparator = [float(index) for index in range(20)]
        interval = v184._two_sample_bca_mean_difference(candidate, comparator, seed=184)
        permutation = v184._unpaired_permutation_mean_difference(
            candidate, comparator, seed=184, n_resamples=1_000
        )
        self.assertAlmostEqual(interval["estimate"], 1.0)
        self.assertEqual(interval["candidate_n"], 20)
        self.assertEqual(interval["comparator_n"], 20)
        self.assertAlmostEqual(permutation["mean_difference"], 1.0)
        self.assertGreater(permutation["p_value"], 0.0)

    def test_ties_and_nonfinite_candidate_fail_closed(self) -> None:
        tied = self._rows(candidate_shift=0.0)
        self.assertFalse(
            v184._evaluate_confirmation(tied)["all_three_metric_gates_pass"]
        )
        broken = self._rows()
        next(row for row in broken if row["seed"] == v184.SEEDS[-1])[
            "qpr_finite_only"
        ] = None
        with self.assertRaisesRegex(RuntimeError, "nonfinite"):
            v184._evaluate_confirmation(broken)

    def test_qpr_uses_frozen_drained_cohort_latency_definition(self) -> None:
        metrics = v184._summary_metrics(
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
