from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_relative_load_ocs_training_v185 as v185,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V185RelativeLoadOcsTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load_and_validate_manifest(v185.SOURCE_READY)
        cls.control = read_json(v185.SOURCE_RESULT)["complete_confirmation_rows"]

    def test_plan_runtime_and_complete_v184_control_are_exact(self) -> None:
        plan, result = v185._assert_source_evidence()
        self.assertEqual(plan["plan_hash"], v185.PLAN_HASH)
        self.assertEqual(plan["candidate"]["profile"], v185.PROFILE)
        self.assertEqual(tuple(plan["candidate"]["seed_order"]), v185.SEEDS)
        self.assertEqual(plan["candidate"]["baseline_online_runs"], 0)
        self.assertEqual(result["result_hash"], v185.SOURCE_RESULT_HASH)
        self.assertEqual(len(result["complete_confirmation_rows"]), 20)
        self.assertEqual(file_hash(v185.BINARY_PATH), v185.BINARY_SHA256)
        self.assertEqual(file_hash(v185.SCHEDULER_SOURCE), v185.SCHEDULER_SOURCE_SHA256)

    def test_rewrite_is_exact_nash_only_same_tape_product(self) -> None:
        rewritten = v185._rewrite_training(self.source)
        v185._validate_product(rewritten, references_bound=False)
        self.assertEqual(len(rewritten["runs"]), 20)
        self.assertEqual(len(rewritten["reference_build_dependencies"]), 20)
        self.assertEqual(
            [(run["method"], run["seed"]) for run in rewritten["runs"]],
            [("sche_nash", seed) for seed in v185.SEEDS],
        )
        source_by_seed = {
            run["seed"]: run
            for run in self.source["runs"]
            if run["method"] == "sche_nash"
        }
        self.assertTrue(
            all(
                run["workload_tape"] == source_by_seed[run["seed"]]["workload_tape"]
                for run in rewritten["runs"]
            )
        )
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] == v185.PROFILE
                for run in rewritten["runs"]
            )
        )
        self.assertTrue(
            all(
                run["reference_dependency"]["build_required"]
                for run in rewritten["runs"]
            )
        )
        self.assertEqual(
            rewritten["execution"]["command_template"][-1],
            str(v185.BINARY_PATH.resolve()),
        )

    def test_prepare_atomically_writes_the_reused_tape_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "v185"
            receipt = v185.prepare_v185(root)
            output = v185.paths(root)
            manifest = load_and_validate_manifest(output["tapes"])
            v185._validate_product(manifest, references_bound=False)
            self.assertEqual(receipt["new_tape_captures"], 0)
            self.assertEqual(receipt["reused_tape_count"], 20)
            self.assertEqual(receipt["candidate_online_runs_planned"], 20)
            self.assertTrue(output["prepared"].is_file())

    def test_training_gate_passes_only_absolute_and_same_tape_improvements(
        self,
    ) -> None:
        rows = []
        for control in self.control:
            row = copy.deepcopy(control)
            row["method"] = "sche_nash"
            row["throughput_requests_per_ms"] += 0.01
            row["qpr_finite_only"] += 0.01
            row["qpr_zero_completed_as_zero"] += 0.01
            rows.append(row)
        evaluation = v185._evaluate_training(rows, self.control)
        self.assertTrue(
            evaluation["all_five_preregistered_performance_requirements_pass"]
        )
        self.assertTrue(all(gate["passed"] for gate in evaluation["gates"].values()))
        self.assertTrue(
            all(
                gate["two_sided_paired_permutation"]["used_as_gate"] is False
                for gate in evaluation["gates"].values()
            )
        )

    def test_qpr_ties_and_throughput_regression_fail_closed(self) -> None:
        rows = []
        for control in self.control:
            row = copy.deepcopy(control)
            row["method"] = "sche_nash"
            row["throughput_requests_per_ms"] -= 0.001
            rows.append(row)
        evaluation = v185._evaluate_training(rows, self.control)
        self.assertFalse(
            evaluation["all_five_preregistered_performance_requirements_pass"]
        )
        self.assertFalse(
            evaluation["gates"]["throughput_requests_per_ms"]["paired_requirement_pass"]
        )
        self.assertFalse(
            evaluation["gates"]["qpr_finite_only"]["paired_requirement_pass"]
        )
        self.assertFalse(
            evaluation["gates"]["qpr_zero_completed_as_zero"]["paired_requirement_pass"]
        )

    def test_nonfinite_or_incomplete_rows_are_rejected(self) -> None:
        rows = [copy.deepcopy(row) for row in self.control]
        for row in rows:
            row["method"] = "sche_nash"
        rows[0]["qpr_finite_only"] = float("nan")
        with self.assertRaisesRegex(RuntimeError, "nonfinite"):
            v185._evaluate_training(rows, self.control)
        with self.assertRaisesRegex(RuntimeError, "exact paired"):
            v185._evaluate_training(rows[1:], self.control)

    def test_paired_permutation_is_deterministic_and_report_only(self) -> None:
        differences = [0.001 * (index - 9) for index in range(20)]
        first = v185._paired_permutation(differences, seed=185999)
        second = v185._paired_permutation(differences, seed=185999)
        self.assertEqual(first, second)
        self.assertFalse(first["used_as_gate"])
        self.assertGreaterEqual(first["two_sided_p_value"], 0.0)
        self.assertLessEqual(first["two_sided_p_value"], 1.0)


if __name__ == "__main__":
    unittest.main()
