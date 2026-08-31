from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_prepare_v146 import (
    ARM_ID,
    NATIVE_MEMBERS,
    PLAN_SHA256,
    PLAYER_FRONTIER,
    PROFILE,
    RUN_ORDER_SEED,
    SCENARIOS,
    SERVICE_CERTIFICATE_SCOPE,
    TRAINING_SEED_LIST,
    V145_RESULT_SHA256,
    V146_REVISION,
    V142_TEMPLATE,
    _frozen_schedule,
    _rewrite_candidate,
    prepare_v146,
    scenario_id,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import object_hash, read_json


class V146FullFrontierPrepareTests(unittest.TestCase):
    def test_rewrite_is_exact_nine_cell_full_frontier_product(self) -> None:
        manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
        validate_manifest(manifest)
        self.assertEqual(len(manifest["runs"]), 9)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 9)
        self.assertEqual(
            {(scenario_id(run), run["seed"]) for run in manifest["runs"]},
            {(scenario, seed) for scenario in SCENARIOS for seed in TRAINING_SEED_LIST},
        )
        for run in manifest["runs"]:
            metadata = run["metadata"]
            self.assertEqual(run["variant"], ARM_ID)
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], PROFILE
            )
            self.assertEqual(metadata["v146_native_portfolio_members"], NATIVE_MEMBERS)
            self.assertTrue(metadata["v146_all_three_experts_advanced_every_window"])
            self.assertEqual(metadata["v146_quiet_route"], "greedy")
            self.assertFalse(metadata["v146_outcome_fields_drive_policy"])
            self.assertEqual(
                metadata["v146_service_certificate_scope"],
                SERVICE_CERTIFICATE_SCOPE,
            )
            self.assertEqual(metadata["v146_player_frontier"], PLAYER_FRONTIER)
            self.assertEqual(
                metadata["v146_single_factor_change"],
                "parents_completed_to_all_unscheduled_functions",
            )
            self.assertTrue(
                metadata["v146_source_and_projected_native_command_evidence_required"]
            )

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

    def test_prepare_seals_v145_failure_and_single_factor_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "v146"
            receipt = prepare_v146(root)
            self.assertEqual(receipt["plan_sha256"], PLAN_SHA256)
            self.assertEqual(receipt["candidate_online_runs"], 9)
            self.assertEqual(receipt["v146_revision"], V146_REVISION)
            self.assertEqual(receipt["v145_result_file_sha256"], V145_RESULT_SHA256)
            self.assertEqual(receipt["player_frontier"], PLAYER_FRONTIER)
            self.assertEqual(
                receipt["single_factor_change"],
                "parents_completed_to_all_unscheduled_functions",
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
