from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_prepare_v136 import (
    BASELINE_METHODS,
    PLAN,
    PLAN_SHA256,
    SCENARIOS,
    SEEDS,
    _validate_product,
    paths,
    prepare_v136,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash


class AllBaselineClosurePreparationV136Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name) / "v136"
        cls.receipt = prepare_v136(cls.root)
        cls.manifest = json.loads(
            paths(cls.root)["unbound"].read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_nine_method_scenario_seed_product_and_no_nash_references(
        self,
    ) -> None:
        validate_manifest(self.manifest)
        _validate_product(self.manifest["runs"])
        self.assertEqual(len(self.manifest["runs"]), 81)
        self.assertEqual(
            {run["method"] for run in self.manifest["runs"]}, set(BASELINE_METHODS)
        )
        self.assertNotIn("sche_nash", {run["method"] for run in self.manifest["runs"]})
        self.assertEqual(
            {scenario_id(run) for run in self.manifest["runs"]}, set(SCENARIOS)
        )
        self.assertEqual({run["seed"] for run in self.manifest["runs"]}, SEEDS)
        self.assertEqual(self.manifest["reference_build_dependencies"], [])

    def test_metadata_closes_outcome_and_confirmation_boundaries(self) -> None:
        for run in self.manifest["runs"]:
            metadata = run["metadata"]
            self.assertEqual(metadata["v136_plan_sha256"], PLAN_SHA256)
            self.assertTrue(metadata["v136_diagnostic_only"])
            self.assertEqual(metadata["v136_role"], "paper_baseline")
            self.assertFalse(
                metadata["v136_baseline_performance_consulted_before_execution"]
            )
            self.assertTrue(metadata["v136_NSESche_reused_not_rerun"])
            self.assertFalse(metadata["v136_confirmation_inputs_opened"])
            self.assertFalse(metadata["v136_seed_or_scenario_label_used_by_policy"])
            self.assertFalse(metadata["v136_outcome_fields_used_by_policy"])

    def test_plan_and_preparation_receipt_are_self_hash_bound(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        self.assertEqual(self.receipt["new_baseline_run_count"], 81)
        self.assertEqual(self.receipt["reused_NSESche_run_count"], 9)
        self.assertEqual(self.receipt["NSESche_rerun_count"], 0)
        self.assertEqual(self.receipt["new_reference_build_count"], 0)
        payload = dict(self.receipt)
        claimed = payload.pop("receipt_hash")
        self.assertEqual(claimed, object_hash(payload))

    def test_product_tamper_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "product changed"):
            _validate_product(self.manifest["runs"][:-1])

    def test_existing_root_is_never_overwritten(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            prepare_v136(self.root)


if __name__ == "__main__":
    unittest.main()
