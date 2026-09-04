from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.feedback_trace import (
    validate_runtime_contract_config,
)


G18_CANDIDATE = "ready_global_overflow_soft_cap_release_valve"


class G18OverflowSoftCapImplementationContractTests(unittest.TestCase):
    @staticmethod
    def _run_config() -> dict:
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 13,
            "operational_refinement": G18_CANDIDATE,
            "player_collection": (
                "all_dependency_ready_feasible_then_material_first_overflow_"
                "ceil_5n_over_4_prefix_else_full_release"
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
                    "global_feasible_ready_material_first_overflow_ceil_5n_over_4_"
                    "prefix_then_persistent_full_release_v1"
                ),
                "candidate_order": ("arrival_frame_req_id_dag_topological_rank_fn_id"),
                "admission_scope": (
                    "globally_collected_dependency_ready_players_after_"
                    "individual_feasibility_filter"
                ),
                "admission_limit": (
                    "ceil_5_times_node_count_over_4_only_on_material_first_"
                    "overflow_else_all_feasible"
                ),
                "deferred_behavior": (
                    "only_material_first_overflow_above_soft_cap_defers_then_"
                    "full_release_while_overflow_persists"
                ),
                "soft_cap_numerator": 5,
                "soft_cap_denominator": 4,
                "soft_cap_rounding": (
                    "ceil_5_times_configured_node_count_over_4_using_checked_"
                    "widened_integer_arithmetic"
                ),
                "material_comparison": (
                    "feasible_ready_strictly_greater_than_rounded_soft_cap"
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

    def test_runtime_contract_accepts_exact_g18_identity(self) -> None:
        self.assertEqual(
            validate_runtime_contract_config(
                self._run_config(),
                expected_candidate=G18_CANDIDATE,
                expected_r0=0.1,
            ),
            [],
        )

    def test_runtime_contract_rejects_soft_cap_or_state_drift(self) -> None:
        top_level_mutations = (
            ("operational_refinement_schema_version", 12),
            ("player_collection", "dependency_ready_only"),
            ("strict_best_response", False),
            ("formula_alignment", "changed_formula"),
        )
        for field, value in top_level_mutations:
            with self.subTest(field=field):
                config = self._run_config()
                config[field] = value
                self.assertTrue(validate_runtime_contract_config(config))

        contract_mutations = (
            ("soft_cap_numerator", 6),
            ("soft_cap_denominator", 5),
            ("soft_cap_rounding", "floating_point"),
            ("material_comparison", "at_or_above"),
            ("release_valve_enabled", False),
            ("release_valve_initial_state", "open"),
            ("release_valve_state_update", "learned_from_qpr"),
            ("admission_limit", "load_specific_multiplier"),
            ("deferred_behavior", "persistent_deferral"),
            ("load_specific_branch", True),
            ("baseline_expert", True),
        )
        for field, value in contract_mutations:
            with self.subTest(contract_field=field):
                config = copy.deepcopy(self._run_config())
                config["global_ready_player_admission"][field] = value
                self.assertTrue(validate_runtime_contract_config(config))

    def test_candidate_mismatch_fails_closed(self) -> None:
        self.assertTrue(
            validate_runtime_contract_config(
                self._run_config(), expected_candidate="ready_order", expected_r0=0.1
            )
        )


if __name__ == "__main__":
    unittest.main()
