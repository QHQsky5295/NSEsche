from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_response_time_ocs_training_v187 as v187,
)
from scripts.reviewer_experiments.protocol.util import read_json


class ResponseTimeOcsTrainingV187Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(dir="tmp")
        cls.root = Path(cls._temporary.name)
        cls.source, cls.manifests = v187._build_unbound_products(cls.root, "a" * 40)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def test_plan_and_v186_failure_are_frozen(self) -> None:
        plan = v187._assert_plan()
        self.assertEqual(plan["plan_hash"], v187.PLAN_HASH)
        self.assertEqual(tuple(plan["cohort"]["seed_order"]), v187.SEEDS)
        self.assertEqual(plan["cohort"]["online_runs"], 40)
        self.assertEqual(plan["cohort"]["new_base_tapes"], 20)
        self.assertEqual(plan["cohort"]["non_NSESche_online_runs"], 0)

    def test_counterbalanced_order_is_exact_and_deterministic(self) -> None:
        order = v187._counterbalanced_order()
        self.assertEqual(len(order), 40)
        for index, seed in enumerate(v187.SEEDS):
            pair = order[index * 2 : index * 2 + 2]
            expected = (
                ["control", "candidate"]
                if int(seed[1:]) % 2 == 0
                else ["candidate", "control"]
            )
            self.assertEqual([item["seed"] for item in pair], [seed, seed])
            self.assertEqual([item["arm"] for item in pair], expected)

    def test_two_manifests_are_exact_nash_only_products(self) -> None:
        self.assertGreater(len(self.source["runs"]), 40)
        for arm in v187.ARMS:
            manifest = self.manifests[arm]
            v187._validate_arm(manifest, arm, tapes_bound=False, references_bound=False)
            self.assertEqual(len(manifest["runs"]), 20)
            self.assertEqual(
                [run["seed"] for run in manifest["runs"]], list(v187.SEEDS)
            )
            self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
            self.assertFalse(manifest["formal_results_eligible"])

    def test_arm_profiles_and_references_are_distinct_but_tapes_are_shared(
        self,
    ) -> None:
        by_arm = {
            arm: {run["seed"]: run for run in self.manifests[arm]["runs"]}
            for arm in v187.ARMS
        }
        for seed in v187.SEEDS:
            control = by_arm["control"][seed]
            candidate = by_arm["candidate"][seed]
            self.assertEqual(
                control["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"],
                v187.CONTROL_PROFILE,
            )
            self.assertEqual(
                candidate["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"],
                v187.CANDIDATE_PROFILE,
            )
            self.assertEqual(
                control["workload_tape"]["key"], candidate["workload_tape"]["key"]
            )
            self.assertNotEqual(
                control["reference_dependency"]["key"],
                candidate["reference_dependency"]["key"],
            )
            self.assertNotEqual(control["run_id"], candidate["run_id"])

    def test_written_manifests_round_trip(self) -> None:
        output = v187.paths(self.root)
        for arm in v187.ARMS:
            written = read_json(output[f"{arm}_unbound"])
            self.assertEqual(
                written["manifest_hash"], self.manifests[arm]["manifest_hash"]
            )

    @staticmethod
    def _rows(candidate_t: float, candidate_qpr: float) -> list[dict[str, object]]:
        rows = []
        for arm in v187.ARMS:
            for seed in v187.SEEDS:
                rows.append(
                    {
                        "arm": arm,
                        "seed": seed,
                        "throughput_requests_per_ms": (
                            candidate_t if arm == "candidate" else 1.50
                        ),
                        "qpr_finite_only": (
                            candidate_qpr if arm == "candidate" else 0.060
                        ),
                        "qpr_zero_completed_as_zero": (
                            candidate_qpr if arm == "candidate" else 0.060
                        ),
                    }
                )
        return rows

    def _evaluate(self, rows: list[dict[str, object]]) -> dict[str, object]:
        with mock.patch.object(
            v187, "bca_interval", return_value={"low": 0.0, "high": 0.0}
        ), mock.patch.object(
            v187.v186,
            "_paired_permutation",
            return_value={"used_as_gate": False},
        ):
            return v187._evaluate_training(rows)

    def test_training_gate_passes_only_absolute_and_paired_requirements(self) -> None:
        evaluation = self._evaluate(self._rows(1.55, 0.065))
        self.assertTrue(
            evaluation["all_six_preregistered_performance_requirements_pass"]
        )
        for gate in evaluation["gates"].values():
            self.assertTrue(gate["candidate_strictly_exceeds_frozen_baseline_mean"])
            self.assertTrue(gate["paired_requirement_pass"])

    def test_training_gate_fails_candidate_qpr_below_paired_control(self) -> None:
        evaluation = self._evaluate(self._rows(1.55, 0.059))
        self.assertFalse(
            evaluation["all_six_preregistered_performance_requirements_pass"]
        )
        self.assertFalse(
            evaluation["gates"]["qpr_finite_only"]["paired_requirement_pass"]
        )

    def test_nonfinite_qpr_fails_closed(self) -> None:
        rows = self._rows(1.55, 0.065)
        rows[0]["qpr_finite_only"] = None
        with self.assertRaisesRegex(RuntimeError, "nonfinite"):
            self._evaluate(rows)

    def test_cli_actions_are_sealed(self) -> None:
        parser = v187.build_parser()
        for action in (
            "prepare",
            "capture-tapes",
            "build-references",
            "execute",
            "blind-audit",
            "reveal",
        ):
            self.assertEqual(parser.parse_args([action]).action, action)


if __name__ == "__main__":
    unittest.main()
