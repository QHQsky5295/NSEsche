from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3e4_qpr_recovery_training_prepare_v95 import (
    CANDIDATE_PAIRS,
    CONFIRMATION_SEEDS,
    FORMAL_RESULT,
    PLAN,
    PLAN_SHA256,
    TRAINING_SEEDS,
    _paths,
    candidate_path,
    prepare_v95,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash


class QprRecoveryTrainingPreparationV95Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name) / "v95"
        cls.receipt = prepare_v95(cls.root)
        cls.paths = _paths(cls.root)
        cls.candidates = {
            candidate_id: json.loads(
                candidate_path(cls.root, candidate_id).read_text(encoding="utf-8")
            )
            for candidate_id, _, _ in CANDIDATE_PAIRS
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_candidate_matrix_and_profile_bindings(self) -> None:
        expected_profiles = {
            candidate_id: {"E3": E3_profile, "E4": E4_profile}
            for candidate_id, E3_profile, E4_profile in CANDIDATE_PAIRS
        }
        for candidate_id, manifest in self.candidates.items():
            validate_manifest(manifest)
            self.assertEqual(len(manifest["runs"]), 12)
            self.assertEqual(
                Counter(run["experiment_id"] for run in manifest["runs"]),
                {"E3": 9, "E4": 3},
            )
            self.assertEqual({run["seed"] for run in manifest["runs"]}, TRAINING_SEEDS)
            self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
            self.assertEqual(
                {
                    run["experiment_id"]: run["environment"][
                        "NASH_OPERATIONAL_EXPERT_PROXY"
                    ]
                    for run in manifest["runs"]
                },
                expected_profiles[candidate_id],
            )
            self.assertEqual(
                {run["metadata"]["v95_candidate_id"] for run in manifest["runs"]},
                {candidate_id},
            )
            self.assertTrue(
                all(
                    run["metadata"]["v95_confirmation_seeds_opened"] is False
                    and run["seed"] not in CONFIRMATION_SEEDS
                    for run in manifest["runs"]
                )
            )
            self.assertEqual(len(manifest["reference_build_dependencies"]), 12)

    def test_reference_specs_are_candidate_specific_and_tapes_are_shared(self) -> None:
        reference_sets = [
            {item["key"] for item in manifest["reference_build_dependencies"]}
            for manifest in self.candidates.values()
        ]
        self.assertEqual(sum(map(len, reference_sets)), 36)
        self.assertEqual(len(set().union(*reference_sets)), 36)

        tape_sets = [
            {
                key
                for run in manifest["runs"]
                for key in (
                    run["workload_tape"]["key"],
                    run["workload_tape"].get("parent_key"),
                )
                if key is not None
            }
            for manifest in self.candidates.values()
        ]
        self.assertTrue(all(keys == tape_sets[0] for keys in tape_sets[1:]))
        self.assertEqual(len(tape_sets[0]), 12)

    def test_capture_and_receipt_keep_the_preregistered_boundary(self) -> None:
        capture = json.loads(self.paths["capture"].read_text(encoding="utf-8"))
        validate_manifest(capture)
        self.assertEqual(len(capture["runs"]), 3)
        self.assertEqual({run["method"] for run in capture["runs"]}, {"greedy"})
        self.assertEqual({run["seed"] for run in capture["runs"]}, TRAINING_SEEDS)
        self.assertEqual(self.receipt["candidate_online_runs"], 36)
        self.assertEqual(self.receipt["candidate_reference_builds"], 36)
        self.assertEqual(self.receipt["new_baseline_online_runs"], 0)
        self.assertEqual(self.receipt["formal_E01_E20_reexecution"], 0)
        self.assertFalse(self.receipt["confirmation_seeds_opened"])
        payload = dict(self.receipt)
        receipt_hash = payload.pop("receipt_hash")
        self.assertEqual(receipt_hash, object_hash(payload))

    def test_plan_thresholds_are_exactly_the_frozen_formal_n20_maxima(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        result = json.loads(FORMAL_RESULT.read_text(encoding="utf-8"))
        thresholds = plan["frozen_formal_n20_maximum_baseline_means"]
        for scenario, metrics in thresholds.items():
            gates = result["scenario_results"][scenario]["gates"]
            for metric, expected in metrics.items():
                self.assertEqual(expected, gates[metric]["maximum_baseline_mean"])
        self.assertFalse(plan["formal_results_eligible"])
        self.assertEqual(
            plan["scientific_boundary"]["untouched_confirmation_seeds"],
            CONFIRMATION_SEEDS,
        )

    def test_existing_root_is_never_overwritten(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            prepare_v95(self.root)


if __name__ == "__main__":
    unittest.main()
