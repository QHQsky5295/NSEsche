from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_native_frontier_anchor_training_prepare_v137 import (
    ARMS,
    ARM_IDS,
    BASELINE_METHODS,
    BINARY_SHA256,
    METHOD_LABELS,
    NEW_CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUS_CONFIRMATION_SEEDS,
    RUN_ORDER_SEED,
    SCENARIOS,
    TRAINING_SEED_LIST,
    TRAINING_SEEDS,
    arm_path,
    paths,
    prepare_v137,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash


class NativeFrontierAnchorPreparationV137Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name) / "v137"
        cls.receipt = prepare_v137(cls.root)
        cls.output = paths(cls.root)
        cls.baselines = json.loads(cls.output["baselines"].read_text(encoding="utf-8"))
        cls.arms = {
            arm_id: json.loads(arm_path(cls.root, arm_id).read_text(encoding="utf-8"))
            for arm_id in ARM_IDS
        }
        cls.schedule = json.loads(cls.output["schedule"].read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_complete_products_and_profiles(self) -> None:
        validate_manifest(self.baselines)
        self.assertEqual(len(self.baselines["runs"]), 81)
        self.assertEqual(
            {
                (run["method"], scenario_id(run), run["seed"])
                for run in self.baselines["runs"]
            },
            {
                (method, scenario, seed)
                for method in BASELINE_METHODS
                for scenario in SCENARIOS
                for seed in TRAINING_SEED_LIST
            },
        )
        self.assertFalse(self.baselines["reference_build_dependencies"])

        all_reference_keys: set[str] = set()
        for arm_id, profile, native_baseline in ARMS:
            manifest = self.arms[arm_id]
            validate_manifest(manifest)
            self.assertEqual(len(manifest["runs"]), 9)
            self.assertEqual(len(manifest["reference_build_dependencies"]), 9)
            self.assertEqual({run["seed"] for run in manifest["runs"]}, TRAINING_SEEDS)
            self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
            self.assertEqual(
                {
                    run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                    for run in manifest["runs"]
                },
                {profile},
            )
            for run in manifest["runs"]:
                self.assertEqual(run["metadata"]["v137_arm_id"], arm_id)
                self.assertEqual(
                    run["metadata"]["v137_native_anchor_baseline"], native_baseline
                )
                self.assertTrue(
                    run["metadata"]["v137_native_shadow_exactness_required"]
                )
                self.assertFalse(run["metadata"]["v137_outcome_fields_drive_policy"])
            keys = {item["key"] for item in manifest["reference_build_dependencies"]}
            self.assertFalse(all_reference_keys & keys)
            all_reference_keys.update(keys)
        self.assertEqual(len(all_reference_keys), 27)

    def test_frozen_rcbd_schedule_is_exact_and_deterministic(self) -> None:
        self.assertEqual(self.schedule["run_order_seed"], RUN_ORDER_SEED)
        self.assertEqual(len(self.schedule["block_orders"]), 9)
        self.assertEqual(len(self.schedule["schedule"]), 108)
        self.assertEqual(
            [item["ordinal"] for item in self.schedule["schedule"]],
            list(range(1, 109)),
        )
        for block in self.schedule["block_orders"]:
            self.assertEqual(set(block["order"]), set(METHOD_LABELS))
            self.assertEqual(len(block["order"]), 12)
        self.assertEqual(
            len({item["run_id"] for item in self.schedule["schedule"]}), 108
        )
        payload = dict(self.schedule)
        claimed = payload.pop("schedule_hash")
        self.assertEqual(claimed, object_hash(payload))

    def test_pairing_and_confirmation_information_boundary(self) -> None:
        tape_sets = []
        for manifest in [self.baselines, *self.arms.values()]:
            tape_sets.append({run["workload_tape"]["key"] for run in manifest["runs"]})
        self.assertTrue(all(items == tape_sets[0] for items in tape_sets[1:]))
        self.assertEqual(len(tape_sets[0]), 9)
        all_runs = [
            *self.baselines["runs"],
            *(run for manifest in self.arms.values() for run in manifest["runs"]),
        ]
        sealed = set(PREVIOUS_CONFIRMATION_SEEDS + NEW_CONFIRMATION_SEEDS)
        self.assertFalse({run["seed"] for run in all_runs} & sealed)
        self.assertFalse(self.receipt["confirmation_inputs_generated"])
        self.assertFalse(self.receipt["performance_results_consulted"])
        self.assertEqual(self.receipt["total_online_runs"], 108)
        self.assertEqual(self.receipt["candidate_reference_builds"], 27)

    def test_plan_binary_receipt_and_capture_are_frozen(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        self.assertEqual(self.receipt["binary_sha256"], BINARY_SHA256)
        capture = json.loads(self.output["capture"].read_text(encoding="utf-8"))
        validate_manifest(capture)
        self.assertEqual(len(capture["runs"]), 3)
        self.assertEqual({run["seed"] for run in capture["runs"]}, TRAINING_SEEDS)
        payload = dict(self.receipt)
        claimed = payload.pop("receipt_hash")
        self.assertEqual(claimed, object_hash(payload))

    def test_existing_root_is_never_overwritten(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            prepare_v137(self.root)


if __name__ == "__main__":
    unittest.main()
