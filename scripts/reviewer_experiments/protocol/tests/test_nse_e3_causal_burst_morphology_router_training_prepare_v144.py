from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_burst_morphology_router_training_prepare_v144 import (
    ARM_ID,
    NATIVE_MEMBERS,
    PLAN_SHA256,
    PROFILE,
    RUN_ORDER_SEED,
    SCENARIOS,
    SERVICE_CERTIFICATE_SCOPE,
    TECHNICAL_DISPOSITION_SHA256,
    TECHNICAL_DISPOSITION_R1_SHA256,
    TRAINING_SEED_LIST,
    V144_REVISION,
    V142_TEMPLATE,
    _frozen_schedule,
    _rewrite_candidate,
    prepare_v144,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import object_hash, read_json


class V144CausalMorphologyPrepareTests(unittest.TestCase):
    def test_rewrite_is_exact_nine_cell_morphology_product(self) -> None:
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
                run["metadata"]["v144_native_portfolio_members"], NATIVE_MEMBERS
            )
            self.assertTrue(
                run["metadata"]["v144_all_four_experts_advanced_every_window"]
            )
            self.assertFalse(run["metadata"]["v144_outcome_fields_drive_policy"])
            self.assertEqual(
                run["metadata"]["v144_service_certificate_scope"],
                SERVICE_CERTIFICATE_SCOPE,
            )
            self.assertNotIn("v142_training_plan_sha256", run["metadata"])

    def test_schedule_is_one_seeded_permutation_without_baselines(self) -> None:
        manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
        first = _frozen_schedule(manifest)
        second = _frozen_schedule(manifest)
        for document in (first, second):
            document.pop("created_at")
            document.pop("schedule_hash")
        self.assertEqual(first, second)
        self.assertEqual(first["run_order_seed"], RUN_ORDER_SEED)
        self.assertEqual(len(first["schedule"]), 9)
        self.assertEqual(
            len({item["source_unbound_run_id"] for item in first["schedule"]}), 9
        )
        self.assertEqual({item["manifest_id"] for item in first["schedule"]}, {ARM_ID})

    def test_prepare_seals_parent_failures_and_generates_no_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "v144"
            receipt = prepare_v144(root)
            self.assertEqual(receipt["plan_sha256"], PLAN_SHA256)
            self.assertEqual(receipt["candidate_online_runs"], 9)
            self.assertEqual(receipt["v144_revision"], V144_REVISION)
            self.assertEqual(
                receipt["technical_disposition_file_sha256"],
                TECHNICAL_DISPOSITION_SHA256,
            )
            self.assertEqual(
                receipt["technical_disposition_r1_file_sha256"],
                TECHNICAL_DISPOSITION_R1_SHA256,
            )
            self.assertEqual(receipt["reused_frozen_v142_baseline_runs"], 81)
            self.assertEqual(receipt["baseline_reruns"], 0)
            self.assertFalse(receipt["confirmation_inputs_generated"])
            payload = dict(receipt)
            claimed = payload.pop("receipt_hash")
            self.assertEqual(object_hash(payload), claimed)
            self.assertTrue((root / f"manifest.{ARM_ID}.unbound.json").is_file())


if __name__ == "__main__":
    unittest.main()
