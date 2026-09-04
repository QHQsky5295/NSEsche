from __future__ import annotations

import copy
import json
import tempfile
import unittest
from itertools import product
from pathlib import Path

from scripts.reviewer_experiments.analysis.feedback_trace import (
    validate_runtime_contract_config,
)
from scripts.reviewer_experiments.protocol.g10_work_conserving import (
    G10_CANDIDATES,
    G10_CONTROL,
    G10_EFFECTIVE_METHODS,
    build_g10_work_conserving_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G10_WORK_CONSERVING_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)


class G10WorkConservingRuntimeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.binary = Path(self.temporary.name) / "serverless_sim.exe"
        self.binary.write_bytes(b"g10-work-conserving-test-binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_g10_work_conserving_manifest(self.binary, "e" * 40)

    @staticmethod
    def _run_config(candidate: str) -> dict:
        bounded_frontier = candidate == "ready_remaining_work_bounded_frontier"
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 9,
            "operational_refinement": candidate,
            "player_collection": (
                "all_dependency_ready_plus_global_node_count_bounded_one_hop_frontier"
                if bounded_frontier
                else "dependency_ready_only"
            ),
            "player_order": (
                "ready_class_then_unfinished_functions_then_arrival_frame_req_id_"
                "dag_topological_rank_fn_id"
                if bounded_frontier
                else "unfinished_functions_then_arrival_frame_req_id_"
                "dag_topological_rank_fn_id"
            ),
            "initialization_semantics": "sequential_existing_candidate_selection",
            "strict_best_response": True,
            "formula_alignment": "paper_Eqs_1_20_strict_argmax",
            "eq15_selection_semantics": (
                "strict_argmax_with_current_node_preferred_on_numerical_ties"
            ),
            "utility_guard_relative_regret": None,
            "work_conserving_remaining_work": {
                "enabled": True,
                "schema": (
                    "all_ready_remaining_work_with_global_one_hop_frontier_bound_v1"
                ),
                "remaining_work_definition": (
                    "dag_function_count_minus_completed_function_count"
                ),
                "ready_players_uncapped": True,
                "bounded_frontier_enabled": bounded_frontier,
                "frontier_eligibility": (
                    "unplaced_not_ready_all_incomplete_direct_parents_placed_and_"
                    "their_parents_complete"
                    if bounded_frontier
                    else None
                ),
                "global_frontier_bound": (
                    "outstanding_parent_blocked_plus_new_frontier_at_most_"
                    "configured_node_count"
                    if bounded_frontier
                    else None
                ),
                "load_specific_branch": False,
                "baseline_expert": False,
            },
            "outer_feedback_trace_schema": "eq16_eq19_control_path_v1",
            "reference_price_basis": "immutable_window_baseline_prices",
            "feedback_nash_welfare_price_basis": "current_outer_adjusted_prices",
            "empirical_gap_price_basis": "immutable_window_baseline_prices",
            "price_feedback_update_basis": (
                "immutable_window_baseline_prices_not_recursive"
            ),
            "network_beta_source": (
                "active_transfer_remaining_time_by_directed_link_proxy"
            ),
            "network_beta_effective_domain": (
                "finite_beta_ge_1_unclipped_no_global_upper_bound"
            ),
            "network_proxy_is_physical_rtt": False,
            "r0": 0.1,
        }

    def test_runtime_contract_accepts_both_frozen_candidates(self) -> None:
        for candidate in (
            "ready_remaining_work",
            "ready_remaining_work_bounded_frontier",
        ):
            with self.subTest(candidate=candidate):
                self.assertEqual(
                    validate_runtime_contract_config(
                        self._run_config(candidate),
                        expected_candidate=candidate,
                        expected_r0=0.1,
                    ),
                    [],
                )

    def test_runtime_contract_rejects_capped_ready_players(self) -> None:
        config = self._run_config("ready_remaining_work")
        config["work_conserving_remaining_work"]["ready_players_uncapped"] = False
        self.assertTrue(validate_runtime_contract_config(config, expected_r0=0.1))

    def test_runtime_contract_rejects_frontier_identity_drift(self) -> None:
        config = self._run_config("ready_remaining_work_bounded_frontier")
        config["work_conserving_remaining_work"]["bounded_frontier_enabled"] = False
        self.assertTrue(validate_runtime_contract_config(config, expected_r0=0.1))

    def test_runtime_contract_rejects_load_specific_or_baseline_feedback(self) -> None:
        for field in ("load_specific_branch", "baseline_expert"):
            with self.subTest(field=field):
                config = copy.deepcopy(self._run_config("ready_remaining_work"))
                config["work_conserving_remaining_work"][field] = True
                self.assertTrue(
                    validate_runtime_contract_config(config, expected_r0=0.1)
                )

    def test_manifest_is_exact_three_by_three_by_five_product(self) -> None:
        manifest = self._manifest()
        validate_manifest(manifest)
        self.assertEqual(len(manifest["runs"]), 45)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 45)
        effective = {
            (
                run["metadata"]["m1_operational_candidate"],
                run["workload"]["request_freq"],
                run["seed"],
            )
            for run in manifest["runs"]
        }
        self.assertEqual(
            effective,
            set(
                product(
                    G10_EFFECTIVE_METHODS,
                    FORMAL_E1_LOADS,
                    G10_WORK_CONSERVING_SEEDS,
                )
            ),
        )

    def test_manifest_pairs_tapes_but_separates_all_mode_references(self) -> None:
        manifest = self._manifest()
        for load in FORMAL_E1_LOADS:
            for seed in G10_WORK_CONSERVING_SEEDS:
                group = [
                    run
                    for run in manifest["runs"]
                    if run["workload"]["request_freq"] == load and run["seed"] == seed
                ]
                self.assertEqual(len(group), 3)
                self.assertEqual(len({row["workload_tape"]["key"] for row in group}), 1)
                self.assertEqual(
                    len({row["reference_dependency"]["key"] for row in group}), 3
                )

    def test_manifest_rejects_gate_seed_and_strong_baseline_tampering(self) -> None:
        manifest = self._manifest()
        bad = copy.deepcopy(manifest)
        bad["g10_work_conserving_development"]["performance_gate"][
            "paired_joint_wins_at_least_each_load"
        ] = 2
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["runs"][0]["seed"] = "D95"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["g10_work_conserving_development"][
            "strong_baselines_in_initial_stage"
        ] = True
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

    def test_manifest_has_only_control_and_two_preregistered_candidates(self) -> None:
        manifest = self._manifest()
        identities = {
            run["metadata"]["m1_operational_candidate"] for run in manifest["runs"]
        }
        self.assertEqual(identities, {G10_CONTROL, *G10_CANDIDATES})
        self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})

    def test_manifest_passes_static_json_schema_with_d100(self) -> None:
        import jsonschema

        manifest = self._manifest()
        schema_path = Path(__file__).parents[1] / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)
        self.assertIn("D100", {run["seed"] for run in manifest["runs"]})


if __name__ == "__main__":
    unittest.main()
