from __future__ import annotations

import copy
import tempfile
import unittest
from itertools import product
from pathlib import Path

from scripts.reviewer_experiments.analysis.feedback_trace import (
    validate_runtime_contract_config,
)
from scripts.reviewer_experiments.protocol.g9_request_backpressure import (
    G9_BASELINES,
    G9_CANDIDATE,
    G9_CONTROL,
    build_g9_request_backpressure_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G9_REQUEST_BACKPRESSURE_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)


class G9RequestBackpressureContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.binary = Path(self.temporary.name) / "serverless_sim.exe"
        self.binary.write_bytes(b"g9-request-backpressure-test-binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_g9_request_backpressure_manifest(self.binary, "d" * 40)

    @staticmethod
    def _run_config() -> dict:
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 8,
            "operational_refinement": "ready_request_backpressure",
            "player_collection": (
                "dependency_ready_with_oldest_node_count_live_request_cohort"
            ),
            "player_order": "arrival_frame_req_id_dag_topological_rank_fn_id",
            "initialization_semantics": "sequential_existing_candidate_selection",
            "strict_best_response": True,
            "formula_alignment": "paper_Eqs_1_20_strict_argmax",
            "eq15_selection_semantics": (
                "strict_argmax_with_current_node_preferred_on_numerical_ties"
            ),
            "utility_guard_relative_regret": None,
            "request_backpressure": {
                "enabled": True,
                "schema": "oldest_live_request_cohort_node_count_v1",
                "cohort_order": "arrival_frame_then_request_id",
                "cohort_limit": "configured_node_count",
                "scope": "dependency_ready_not_yet_placed_request_function_players",
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

    def test_runtime_contract_accepts_only_the_frozen_g9_identity(self) -> None:
        config = self._run_config()
        self.assertEqual(
            validate_runtime_contract_config(
                config,
                expected_candidate="ready_request_backpressure",
                expected_r0=0.1,
            ),
            [],
        )

    def test_runtime_contract_rejects_schema_drift(self) -> None:
        config = copy.deepcopy(self._run_config())
        config["operational_refinement_schema_version"] = 7
        self.assertTrue(validate_runtime_contract_config(config, expected_r0=0.1))

    def test_runtime_contract_rejects_disabled_backpressure(self) -> None:
        config = copy.deepcopy(self._run_config())
        config["request_backpressure"]["enabled"] = False
        self.assertTrue(validate_runtime_contract_config(config, expected_r0=0.1))

    def test_manifest_is_exact_five_by_three_by_five_product(self) -> None:
        manifest = self._manifest()
        validate_manifest(manifest)
        self.assertEqual(len(manifest["runs"]), 75)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 30)
        effective = {
            (
                (
                    run["metadata"]["m1_operational_candidate"]
                    if run["method"] == "sche_nash"
                    else run["method"]
                ),
                run["workload"]["request_freq"],
                run["seed"],
            )
            for run in manifest["runs"]
        }
        self.assertEqual(
            effective,
            set(
                product(
                    (G9_CONTROL, G9_CANDIDATE, *G9_BASELINES),
                    FORMAL_E1_LOADS,
                    G9_REQUEST_BACKPRESSURE_SEEDS,
                )
            ),
        )

    def test_manifest_tampering_fails_closed(self) -> None:
        manifest = self._manifest()
        bad = copy.deepcopy(manifest)
        bad["g9_request_backpressure_development"]["performance_gate"][
            "rank_first_qpr_each_load"
        ] = False
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["runs"][0]["seed"] = "D80"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)


if __name__ == "__main__":
    unittest.main()
