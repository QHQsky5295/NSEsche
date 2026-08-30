from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_prepare_v143 import (
    ARM_ID,
    NATIVE_MEMBERS,
    PLAN_SHA256,
    PROFILE,
    RUN_ORDER_SEED,
    SCENARIOS,
    TRAINING_SEED_LIST,
    V142_TEMPLATE,
    _frozen_schedule,
    _rewrite_candidate,
    prepare_v143,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import object_hash, read_json


class V143ReadyTailPrepareTests(unittest.TestCase):
    def test_rewrite_is_exact_nine_cell_ready_tail_product(self) -> None:
        manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
        validate_manifest(manifest)
        self.assertEqual(len(manifest["runs"]), 9)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 9)
        self.assertEqual(
            {(scenario_id(run), run["seed"]) for run in manifest["runs"]},
            {(scenario, seed) for scenario in SCENARIOS for seed in TRAINING_SEED_LIST},
        )
        for run in manifest["runs"]:
            self.assertEqual(run["variant"], ARM_ID)
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], PROFILE
            )
            self.assertEqual(
                run["metadata"]["v143_native_portfolio_members"], NATIVE_MEMBERS
            )
            self.assertTrue(run["metadata"]["v143_random_prefix_preserved"])
            self.assertTrue(run["metadata"]["v143_common_cohort_required"])
            self.assertFalse(run["metadata"]["v143_outcome_fields_drive_policy"])
            self.assertNotIn("v142_training_plan_sha256", run["metadata"])

    def test_schedule_is_one_seeded_permutation_without_baselines(self) -> None:
        manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
        first = _frozen_schedule(manifest)
        second = _frozen_schedule(manifest)
        first_without_time = dict(first)
        second_without_time = dict(second)
        first_without_time.pop("created_at")
        second_without_time.pop("created_at")
        first_without_time.pop("schedule_hash")
        second_without_time.pop("schedule_hash")
        self.assertEqual(first_without_time, second_without_time)
        self.assertEqual(first["run_order_seed"], RUN_ORDER_SEED)
        self.assertEqual(len(first["schedule"]), 9)
        self.assertEqual(
            len({item["source_unbound_run_id"] for item in first["schedule"]}), 9
        )
        self.assertEqual({item["manifest_id"] for item in first["schedule"]}, {ARM_ID})

    def test_prepare_seals_v142_reuse_and_generates_no_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "v143"
            receipt = prepare_v143(root)
            self.assertEqual(receipt["plan_sha256"], PLAN_SHA256)
            self.assertEqual(receipt["candidate_online_runs"], 9)
            self.assertEqual(receipt["reused_frozen_v142_baseline_runs"], 81)
            self.assertEqual(receipt["baseline_reruns"], 0)
            self.assertFalse(receipt["confirmation_inputs_generated"])
            payload = dict(receipt)
            claimed = payload.pop("receipt_hash")
            self.assertEqual(object_hash(payload), claimed)
            self.assertTrue((root / f"manifest.{ARM_ID}.unbound.json").is_file())


if __name__ == "__main__":
    unittest.main()
