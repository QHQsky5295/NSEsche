from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.feedback_trace import (
    validate_runtime_contract_config,
)


G14_CANDIDATE = "ready_global_deferral_release_valve"


class G14DeferralReleaseValveContractTests(unittest.TestCase):
    @staticmethod
    def _run_config() -> dict:
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 11,
            "operational_refinement": G14_CANDIDATE,
            "player_collection": (
                "all_dependency_ready_feasible_then_first_overflow_node_count_"
                "prefix_else_full_release"
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
                "schema": (
                    "global_feasible_ready_first_overflow_prefix_then_"
                    "persistent_full_release_v1"
                ),
                "candidate_order": ("arrival_frame_req_id_dag_topological_rank_fn_id"),
                "admission_scope": (
                    "globally_collected_dependency_ready_players_after_"
                    "individual_feasibility_filter"
                ),
                "admission_limit": (
                    "configured_node_count_only_on_first_window_of_"
                    "consecutive_overflow_else_all_feasible"
                ),
                "deferred_behavior": (
                    "only_first_overflow_window_defers_then_full_release_"
                    "while_overflow_persists"
                ),
                "release_valve_enabled": True,
                "release_valve_initial_state": "closed",
                "release_valve_state_update": (
                    "next_state_equals_current_feasible_ready_count_greater_"
                    "than_configured_node_count"
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

    def test_runtime_contract_accepts_exact_candidate(self) -> None:
        self.assertEqual(
            validate_runtime_contract_config(
                self._run_config(), expected_candidate=G14_CANDIDATE, expected_r0=0.1
            ),
            [],
        )

    def test_runtime_contract_rejects_state_machine_or_identity_drift(self) -> None:
        mutations = (
            ("operational_refinement_schema_version", 10),
            ("player_collection", "dependency_ready_only"),
            ("player_order", "unfinished_functions_then_arrival"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                config = self._run_config()
                config[field] = value
                self.assertTrue(validate_runtime_contract_config(config))

        contract_mutations = (
            ("release_valve_enabled", False),
            ("release_valve_initial_state", "open"),
            ("release_valve_state_update", "learned_from_qpr"),
            ("admission_limit", "fitted_multiplier"),
            ("deferred_behavior", "always_defer"),
            ("load_specific_branch", True),
            ("baseline_expert", True),
        )
        for field, value in contract_mutations:
            with self.subTest(contract_field=field):
                config = copy.deepcopy(self._run_config())
                config["global_ready_player_admission"][field] = value
                self.assertTrue(validate_runtime_contract_config(config))


if __name__ == "__main__":
    unittest.main()
