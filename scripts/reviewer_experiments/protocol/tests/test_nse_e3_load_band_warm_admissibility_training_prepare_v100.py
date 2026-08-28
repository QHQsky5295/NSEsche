from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_prepare_v100 import (
    ARMS,
    BINARY_SHA256,
    CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUSLY_RESERVED_SEEDS,
    TRAINING_SEEDS,
    _paths,
    arm_path,
    prepare_v100,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash


class LoadBandWarmAdmissibilityTrainingPreparationV100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name) / "v100"
        cls.receipt = prepare_v100(cls.root)
        cls.paths = _paths(cls.root)
        cls.arms = {
            arm_id: json.loads(arm_path(cls.root, arm_id).read_text(encoding="utf-8"))
            for arm_id, _, _, _, _, _ in ARMS
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_arms_profiles_thresholds_and_runtime(self) -> None:
        expected = {
            arm_id: (experiment_id, role, profile, cap, count)
            for arm_id, experiment_id, role, profile, cap, count in ARMS
        }
        self.assertEqual(Counter(item[1] for item in ARMS), {"E3": 3})
        self.assertEqual(sum(item[-1] for item in ARMS), 27)
        for arm_id, manifest in self.arms.items():
            experiment_id, role, profile, cap, count = expected[arm_id]
            validate_manifest(manifest)
            self.assertEqual(len(manifest["runs"]), count)
            self.assertEqual(
                {run["experiment_id"] for run in manifest["runs"]}, {experiment_id}
            )
            self.assertEqual({run["seed"] for run in manifest["runs"]}, TRAINING_SEEDS)
            self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
            self.assertEqual(
                {
                    run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                    for run in manifest["runs"]
                },
                {profile},
            )
            self.assertEqual(
                {
                    run["metadata"]["v100_nonterminal_queue_density_floor"]
                    for run in manifest["runs"]
                },
                {8.0 if role == "candidate" else None},
            )
            self.assertEqual(
                {
                    run["metadata"]["v100_warm_admissibility"]
                    for run in manifest["runs"]
                },
                {cap},
            )
            self.assertTrue(
                all(
                    run["metadata"]["v100_load_band_warm_admissibility_guard"]
                    is (cap is not None)
                    and run["metadata"]["v100_upper_queue_density_threshold"]
                    == (64.0 if role == "candidate" else None)
                    and run["metadata"]["v100_confirmation_seeds_opened"] is False
                    and run["metadata"]["v100_previously_reserved_seeds_opened"]
                    is False
                    and run["seed"] not in CONFIRMATION_SEEDS
                    and run["seed"] not in PREVIOUSLY_RESERVED_SEEDS
                    for run in manifest["runs"]
                )
            )
            self.assertEqual(len(manifest["reference_build_dependencies"]), count)

    def test_arm_references_are_unique_and_tapes_are_paired(self) -> None:
        references = [
            {item["key"] for item in manifest["reference_build_dependencies"]}
            for manifest in self.arms.values()
        ]
        self.assertEqual(sum(map(len, references)), 27)
        self.assertEqual(len(set().union(*references)), 27)
        tape_sets = {
            arm_id: {
                key
                for run in manifest["runs"]
                for key in (
                    run["workload_tape"]["key"],
                    run["workload_tape"].get("parent_key"),
                )
                if key is not None
            }
            for arm_id, manifest in self.arms.items()
        }
        e3_sets = [keys for arm, keys in tape_sets.items() if arm.startswith("v100-e3")]
        self.assertTrue(all(keys == e3_sets[0] for keys in e3_sets[1:]))
        self.assertEqual(len(e3_sets[0]), 12)

    def test_capture_and_receipt_close_the_information_boundary(self) -> None:
        capture = json.loads(self.paths["capture"].read_text(encoding="utf-8"))
        validate_manifest(capture)
        self.assertEqual(len(capture["runs"]), 3)
        self.assertEqual({run["method"] for run in capture["runs"]}, {"greedy"})
        self.assertEqual({run["seed"] for run in capture["runs"]}, TRAINING_SEEDS)
        self.assertEqual(self.receipt["arm_online_runs"], 27)
        self.assertEqual(self.receipt["arm_reference_builds"], 27)
        self.assertEqual(self.receipt["binary_sha256"], BINARY_SHA256)
        self.assertFalse(self.receipt["confirmation_inputs_generated"])
        self.assertFalse(self.receipt["previously_reserved_inputs_generated"])
        payload = dict(self.receipt)
        receipt_hash = payload.pop("receipt_hash")
        self.assertEqual(receipt_hash, object_hash(payload))

    def test_plan_is_frozen_and_matches_exact_seed_boundary(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(set(plan["training_design"]["training_seeds"]), TRAINING_SEEDS)
        self.assertEqual(
            plan["training_design"]["sealed_confirmation_seeds"], CONFIRMATION_SEEDS
        )
        self.assertEqual(
            plan["training_design"]["other_unopened_seeds"],
            PREVIOUSLY_RESERVED_SEEDS,
        )
        self.assertEqual(plan["training_design"]["candidate_online_runs"], 27)
        self.assertFalse(
            plan["invariants"]["confirmation_inputs_generated_before_training_pass"]
        )

    def test_existing_root_is_never_overwritten(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            prepare_v100(self.root)


if __name__ == "__main__":
    unittest.main()
