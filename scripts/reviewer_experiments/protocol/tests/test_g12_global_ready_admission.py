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
from scripts.reviewer_experiments.protocol.g12_global_ready_admission import (
    G12_CANDIDATE,
    G12_CONTROL,
    G12_EFFECTIVE_METHODS,
    build_g12_global_ready_admission_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G12_GLOBAL_READY_ADMISSION_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)


class G12GlobalReadyAdmissionProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.binary = Path(self.temporary.name) / "serverless_sim.exe"
        self.binary.write_bytes(b"g12-global-ready-admission-test-binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_g12_global_ready_admission_manifest(self.binary, "f" * 40)

    @staticmethod
    def _run_config() -> dict:
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 10,
            "operational_refinement": G12_CANDIDATE,
            "player_collection": (
                "all_dependency_ready_feasible_then_global_node_count_prefix"
            ),
            "player_order": "arrival_frame_req_id_dag_topological_rank_fn_id",
            "initialization_semantics": "sequential_existing_candidate_selection",
            "strict_best_response": True,
            "formula_alignment": "paper_Eqs_1_20_strict_argmax",
            "eq15_selection_semantics": (
                "strict_argmax_with_current_node_preferred_on_numerical_ties"
            ),
            "utility_guard_relative_regret": None,
            "global_ready_player_admission": {
                "enabled": True,
                "schema": "global_feasible_ready_legacy_order_prefix_node_count_v1",
                "candidate_order": ("arrival_frame_req_id_dag_topological_rank_fn_id"),
                "admission_scope": (
                    "globally_collected_dependency_ready_players_after_"
                    "individual_feasibility_filter"
                ),
                "admission_limit": "configured_node_count_per_scheduler_window",
                "deferred_behavior": "remain_unplaced_and_reconsider_next_window",
                "load_specific_branch": False,
                "baseline_expert": False,
            },
            "outer_feedback_trace_schema": "eq16_eq19_control_path_v1",
            "reference_price_basis": "immutable_window_baseline_prices",
            "feedback_nash_welfare_price_basis": ("current_outer_adjusted_prices"),
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

    def test_runtime_contract_accepts_exact_candidate(self) -> None:
        self.assertEqual(
            validate_runtime_contract_config(
                self._run_config(), expected_candidate=G12_CANDIDATE, expected_r0=0.1
            ),
            [],
        )

    def test_runtime_contract_rejects_each_identity_drift(self) -> None:
        mutations = {
            "schema": ("operational_refinement_schema_version", 9),
            "collection": ("player_collection", "dependency_ready_only"),
            "order": ("player_order", "unfinished_functions_then_arrival"),
        }
        for name, (field, value) in mutations.items():
            with self.subTest(name=name):
                config = self._run_config()
                config[field] = value
                self.assertTrue(validate_runtime_contract_config(config))
        for field, value in (
            ("enabled", False),
            ("admission_limit", "twice_configured_node_count"),
            ("deferred_behavior", "dispatch_immediately"),
            ("load_specific_branch", True),
            ("baseline_expert", True),
        ):
            with self.subTest(contract_field=field):
                config = self._run_config()
                config["global_ready_player_admission"][field] = value
                self.assertTrue(validate_runtime_contract_config(config))

    def test_manifest_is_exact_two_by_three_by_five_product(self) -> None:
        manifest = self._manifest()
        validate_manifest(manifest)
        self.assertEqual(len(manifest["runs"]), 30)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 30)
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
                    G12_EFFECTIVE_METHODS,
                    FORMAL_E1_LOADS,
                    G12_GLOBAL_READY_ADMISSION_SEEDS,
                )
            ),
        )

    def test_manifest_pairs_tapes_but_separates_mode_references(self) -> None:
        manifest = self._manifest()
        for load in FORMAL_E1_LOADS:
            for seed in G12_GLOBAL_READY_ADMISSION_SEEDS:
                group = [
                    run
                    for run in manifest["runs"]
                    if run["workload"]["request_freq"] == load and run["seed"] == seed
                ]
                self.assertEqual(len(group), 2)
                self.assertEqual(len({row["workload_tape"]["key"] for row in group}), 1)
                self.assertEqual(
                    len({row["reference_dependency"]["key"] for row in group}), 2
                )

    def test_manifest_rejects_gate_seed_and_baseline_tampering(self) -> None:
        manifest = self._manifest()
        bad = copy.deepcopy(manifest)
        bad["g12_global_ready_admission_development"]["performance_gate"][
            "paired_joint_wins_at_least_each_load"
        ] = 2
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["runs"][0]["seed"] = "D106"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["g12_global_ready_admission_development"][
            "strong_baselines_in_initial_stage"
        ] = True
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

    def test_manifest_has_only_control_and_fixed_candidate(self) -> None:
        manifest = self._manifest()
        identities = {
            run["metadata"]["m1_operational_candidate"] for run in manifest["runs"]
        }
        self.assertEqual(identities, {G12_CONTROL, G12_CANDIDATE})
        self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})

    def test_manifest_rejects_cross_mode_reference_reuse(self) -> None:
        manifest = self._manifest()
        bad = copy.deepcopy(manifest)
        first_group = [
            run
            for run in bad["runs"]
            if run["workload"]["request_freq"] == FORMAL_E1_LOADS[0]
            and run["seed"] == G12_GLOBAL_READY_ADMISSION_SEEDS[0]
        ]
        first_group[1]["reference_dependency"] = copy.deepcopy(
            first_group[0]["reference_dependency"]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

    def test_manifest_passes_static_json_schema_with_d105(self) -> None:
        import jsonschema

        manifest = self._manifest()
        schema_path = Path(__file__).parents[1] / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)
        self.assertIn("D105", {run["seed"] for run in manifest["runs"]})


if __name__ == "__main__":
    unittest.main()
