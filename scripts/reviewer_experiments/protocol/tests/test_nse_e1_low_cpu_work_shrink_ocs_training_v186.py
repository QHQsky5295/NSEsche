from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_cpu_work_shrink_ocs_training_v186 as v186,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V186CpuWorkShrinkOcsTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load_and_validate_manifest(v186.SOURCE_READY)
        cls.control = read_json(v186.SOURCE_RESULT)["complete_confirmation_rows"]

    def test_plan_runtime_and_complete_v184_control_are_exact(self) -> None:
        plan, result = v186._assert_source_evidence()
        self.assertEqual(plan["plan_hash"], v186.PLAN_HASH)
        self.assertEqual(plan["candidate"]["profile"], v186.PROFILE)
        self.assertEqual(tuple(plan["candidate"]["seed_order"]), v186.SEEDS)
        self.assertEqual(plan["candidate"]["baseline_online_runs"], 0)
        self.assertEqual(result["result_hash"], v186.SOURCE_RESULT_HASH)
        self.assertEqual(len(result["complete_confirmation_rows"]), 20)
        self.assertEqual(file_hash(v186.BINARY_PATH), v186.BINARY_SHA256)
        self.assertEqual(file_hash(v186.SCHEDULER_SOURCE), v186.SCHEDULER_SOURCE_SHA256)

    def test_rewrite_is_exact_nash_only_same_tape_product(self) -> None:
        rewritten = v186._rewrite_training(self.source)
        v186._validate_product(rewritten, references_bound=False)
        self.assertEqual(len(rewritten["runs"]), 20)
        self.assertEqual(len(rewritten["reference_build_dependencies"]), 20)
        self.assertEqual(
            [(run["method"], run["seed"]) for run in rewritten["runs"]],
            [("sche_nash", seed) for seed in v186.SEEDS],
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
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] == v186.PROFILE
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
            str(v186.BINARY_PATH.resolve()),
        )

    def test_prepare_atomically_writes_the_reused_tape_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "v186"
            receipt = v186.prepare_v186(root)
            output = v186.paths(root)
            manifest = load_and_validate_manifest(output["tapes"])
            v186._validate_product(manifest, references_bound=False)
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
        evaluation = v186._evaluate_training(rows, self.control)
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
        evaluation = v186._evaluate_training(rows, self.control)
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
            v186._evaluate_training(rows, self.control)
        with self.assertRaisesRegex(RuntimeError, "exact paired"):
            v186._evaluate_training(rows[1:], self.control)

    def test_paired_permutation_is_deterministic_and_report_only(self) -> None:
        differences = [0.001 * (index - 9) for index in range(20)]
        first = v186._paired_permutation(differences, seed=186999)
        second = v186._paired_permutation(differences, seed=186999)
        self.assertEqual(first, second)
        self.assertFalse(first["used_as_gate"])
        self.assertGreaterEqual(first["two_sided_p_value"], 0.0)
        self.assertLessEqual(first["two_sided_p_value"], 1.0)

    def test_blind_audit_runtime_identity_is_bound_to_v186_binary(self) -> None:
        audit = {
            "adapter_binary": {"verified_sha256": v186.BINARY_SHA256},
            "software_environment": {
                "git": {"commit": "a" * 40},
                "python": {"executable_sha256": v186.PYTHON_SHA256},
                "cargo_lock": {"sha256": v186.CARGO_LOCK_SHA256},
            },
        }
        identity = v186._runtime_identity_v186([audit, copy.deepcopy(audit)])
        self.assertEqual(identity["runtime_binary_sha256"], v186.BINARY_SHA256)
        changed = copy.deepcopy(audit)
        changed["adapter_binary"]["verified_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "not unanimous"):
            v186._runtime_identity_v186([audit, changed])


if __name__ == "__main__":
    unittest.main()
