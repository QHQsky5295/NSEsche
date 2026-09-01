from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_20node_low_native_clearance_response_training_v188 as v188,
)


class NativeClearanceResponseTrainingV188Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = v188._build_tape_bound_manifest("a" * 40)

    def test_plan_and_v187_failure_are_frozen(self) -> None:
        plan = v188._assert_plan()
        self.assertEqual(plan["plan_hash"], v188.PLAN_HASH)
        self.assertEqual(tuple(plan["cohort"]["seed_order"]), v188.SEEDS)
        self.assertEqual(plan["cohort"]["new_candidate_runs"], 20)
        self.assertEqual(plan["cohort"]["new_control_runs"], 0)
        self.assertEqual(plan["cohort"]["new_base_tapes"], 0)
        self.assertFalse(
            plan["method_identity_boundary"]["external_baseline_expert_scores_allowed"]
        )
        self.assertEqual(
            v188.BINARY_SOURCE_COMMIT,
            "ea369809b608c0a2955a7405f1157a5c7fe11344",
        )

    def test_manifest_is_exact_candidate_only_tape_reuse_product(self) -> None:
        v188._validate_candidate(self.manifest, references_bound=False)
        self.assertEqual(len(self.manifest["runs"]), 20)
        self.assertEqual(
            [run["seed"] for run in self.manifest["runs"]], list(v188.SEEDS)
        )
        self.assertEqual(
            {run["method"] for run in self.manifest["runs"]}, {"sche_nash"}
        )
        self.assertFalse(self.manifest["formal_results_eligible"])
        self.assertTrue(self.manifest["all_tapes_bound"])
        self.assertFalse(self.manifest["all_references_bound"])

    def test_profile_has_no_external_expert_and_reuses_exact_v187_tapes(self) -> None:
        control, source = v188._source_manifests()
        control_by_seed = {run["seed"]: run for run in control["runs"]}
        source_by_seed = {run["seed"]: run for run in source["runs"]}
        candidate_by_seed = {run["seed"]: run for run in self.manifest["runs"]}
        for seed in v188.SEEDS:
            candidate = candidate_by_seed[seed]
            self.assertEqual(
                candidate["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"],
                v188.CANDIDATE_PROFILE,
            )
            self.assertFalse(
                candidate["metadata"]["v188_external_baseline_scores_allowed"]
            )
            self.assertEqual(
                candidate["metadata"]["v188_new_control_or_baseline_runs"], 0
            )
            self.assertEqual(
                candidate["workload_tape"], source_by_seed[seed]["workload_tape"]
            )
            self.assertEqual(
                candidate["workload_tape"], control_by_seed[seed]["workload_tape"]
            )
            self.assertNotEqual(
                candidate["reference_dependency"]["key"],
                source_by_seed[seed]["reference_dependency"]["key"],
            )

    @staticmethod
    def _rows(candidate_t: float, candidate_qpr: float) -> list[dict[str, object]]:
        rows = []
        for arm in ("control", "candidate"):
            for seed in v188.SEEDS:
                rows.append(
                    {
                        "arm": arm,
                        "seed": seed,
                        "throughput_requests_per_ms": (
                            candidate_t if arm == "candidate" else 1.45
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
            v188.v187, "bca_interval", return_value={"low": 0.0, "high": 0.0}
        ), mock.patch.object(
            v188.v187.v186,
            "_paired_permutation",
            return_value={"used_as_gate": False},
        ):
            return v188._evaluate_training(rows)

    def test_training_gate_passes_only_absolute_and_paired_requirements(self) -> None:
        evaluation = self._evaluate(self._rows(1.55, 0.065))
        self.assertTrue(
            evaluation["all_six_preregistered_performance_requirements_pass"]
        )

    def test_training_gate_fails_throughput_below_frozen_orion(self) -> None:
        evaluation = self._evaluate(self._rows(1.47, 0.065))
        self.assertFalse(
            evaluation["all_six_preregistered_performance_requirements_pass"]
        )
        self.assertFalse(
            evaluation["gates"]["throughput_requests_per_ms"][
                "candidate_strictly_exceeds_frozen_baseline_mean"
            ]
        )

    def test_nonfinite_qpr_fails_closed(self) -> None:
        rows = self._rows(1.55, 0.065)
        rows[0]["qpr_finite_only"] = None
        with self.assertRaisesRegex(RuntimeError, "nonfinite"):
            self._evaluate(rows)

    def test_cli_has_no_tape_capture_or_control_action(self) -> None:
        parser = v188.build_parser()
        for action in (
            "prepare",
            "build-references",
            "execute",
            "blind-audit",
            "reveal",
        ):
            self.assertEqual(parser.parse_args([action]).action, action)
        for forbidden in ("capture-tapes", "execute-control", "run-baselines"):
            with self.assertRaises(SystemExit):
                parser.parse_args([forbidden])

    def test_prepare_refuses_to_overwrite_existing_root(self) -> None:
        with tempfile.TemporaryDirectory(dir="tmp") as directory:
            with mock.patch.object(v188, "_assert_frozen_inputs"):
                with self.assertRaisesRegex(RuntimeError, "overwrite"):
                    v188.prepare_v188(Path(directory))


if __name__ == "__main__":
    unittest.main()
