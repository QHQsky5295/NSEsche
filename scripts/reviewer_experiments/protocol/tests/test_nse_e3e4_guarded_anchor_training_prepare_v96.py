from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3e4_guarded_anchor_training_prepare_v96 import (
    ARMS,
    CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    TRAINING_SEEDS,
    V95_RESULT_RECEIPT,
    V95_RESULT_RECEIPT_SHA256,
    _paths,
    arm_path,
    prepare_v96,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash


class GuardedAnchorTrainingPreparationV96Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name) / "v96"
        cls.receipt = prepare_v96(cls.root)
        cls.paths = _paths(cls.root)
        cls.arms = {
            arm_id: json.loads(arm_path(cls.root, arm_id).read_text(encoding="utf-8"))
            for arm_id, _, _, _, _ in ARMS
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_dimension_arms_and_guarded_profiles(self) -> None:
        expected = {
            arm_id: (experiment_id, role, profile, count)
            for arm_id, experiment_id, role, profile, count in ARMS
        }
        self.assertEqual(Counter(item[1] for item in ARMS), {"E3": 3, "E4": 2})
        for arm_id, manifest in self.arms.items():
            experiment_id, role, profile, count = expected[arm_id]
            validate_manifest(manifest)
            self.assertEqual(len(manifest["runs"]), count)
            self.assertEqual(
                {run["experiment_id"] for run in manifest["runs"]},
                {experiment_id},
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
                {run["metadata"]["v96_arm_role"] for run in manifest["runs"]},
                {role},
            )
            self.assertTrue(
                all(
                    run["metadata"]["v96_native_faithful_initializer"] is True
                    and run["metadata"]["v96_dual_window_safe_pareto"] is True
                    and run["metadata"]["v96_confirmation_seeds_opened"] is False
                    and run["seed"] not in CONFIRMATION_SEEDS
                    for run in manifest["runs"]
                )
            )
            self.assertEqual(len(manifest["reference_build_dependencies"]), count)

    def test_reference_specs_are_arm_specific_and_tapes_are_paired(self) -> None:
        reference_sets = [
            {item["key"] for item in manifest["reference_build_dependencies"]}
            for manifest in self.arms.values()
        ]
        self.assertEqual(sum(map(len, reference_sets)), 33)
        self.assertEqual(len(set().union(*reference_sets)), 33)

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
        e3_sets = [keys for arm, keys in tape_sets.items() if arm.startswith("v96-e3")]
        e4_sets = [keys for arm, keys in tape_sets.items() if arm.startswith("v96-e4")]
        self.assertTrue(all(keys == e3_sets[0] for keys in e3_sets[1:]))
        self.assertTrue(all(keys == e4_sets[0] for keys in e4_sets[1:]))
        self.assertEqual(len(e3_sets[0]), 12)
        self.assertEqual(len(e4_sets[0]), 3)
        self.assertTrue(e4_sets[0].issubset(e3_sets[0]))

    def test_capture_and_receipt_freeze_the_boundary_before_inputs(self) -> None:
        capture = json.loads(self.paths["capture"].read_text(encoding="utf-8"))
        validate_manifest(capture)
        self.assertEqual(len(capture["runs"]), 3)
        self.assertEqual({run["method"] for run in capture["runs"]}, {"greedy"})
        self.assertEqual({run["seed"] for run in capture["runs"]}, TRAINING_SEEDS)
        self.assertEqual(self.receipt["arm_online_runs"], 33)
        self.assertEqual(self.receipt["arm_reference_builds"], 33)
        self.assertEqual(self.receipt["new_baseline_method_runs"], 0)
        self.assertEqual(self.receipt["formal_E01_E20_reexecution"], 0)
        self.assertFalse(self.receipt["confirmation_inputs_generated"])
        payload = dict(self.receipt)
        receipt_hash = payload.pop("receipt_hash")
        self.assertEqual(receipt_hash, object_hash(payload))

    def test_plan_freezes_paired_gate_and_prior_failure(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        self.assertEqual(file_hash(V95_RESULT_RECEIPT), V95_RESULT_RECEIPT_SHA256)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        prior = json.loads(V95_RESULT_RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(prior["status"], "training_fail")
        self.assertFalse(prior["decision"]["authorize_confirmation_on_E729_E731"])
        self.assertEqual(
            plan["scientific_boundary"]["untouched_confirmation_seeds"],
            CONFIRMATION_SEEDS,
        )
        gate = plan["paired_selection_gate"]
        self.assertIn("at least two of three", gate["per_scenario_throughput_rule"])
        self.assertIn("at least two of three", gate["per_scenario_qpr_rule"])
        self.assertIn("diagnostics only", gate["formal_absolute_gate_role"])
        self.assertFalse(
            plan["mechanism_diagnosis"]["V95_gate_reinterpreted_or_changed"]
        )

    def test_existing_root_is_never_overwritten(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            prepare_v96(self.root)


if __name__ == "__main__":
    unittest.main()
