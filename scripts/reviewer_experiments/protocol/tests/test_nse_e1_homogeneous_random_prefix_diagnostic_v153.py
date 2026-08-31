import unittest

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_random_prefix_diagnostic_v153 import (
    COMMON_ENVIRONMENT,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    SEEDS,
    SOURCE_MANIFEST,
    _audit_random_prefix_window,
    _rewrite_candidate,
    _validate_product,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V153ProtocolTests(unittest.TestCase):
    def test_plan_and_candidate_are_frozen_without_new_numeric_tuning(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = read_json(PLAN)
        self.assertEqual(plan["candidate"]["profile"], PROFILE)
        self.assertEqual(tuple(plan["diagnostic_design"]["fixed_order"]), SEEDS)
        self.assertEqual(plan["candidate"]["numeric_hyperparameters_added"], 0)
        self.assertEqual(plan["environment"], COMMON_ENVIRONMENT)

    def test_candidate_rewrite_is_exact_two_cell_product(self) -> None:
        manifest = _rewrite_candidate(read_json(SOURCE_MANIFEST), "1" * 40)
        _validate_product(manifest, references_bound=False)
        self.assertEqual(len(manifest["runs"]), 2)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 2)
        self.assertEqual({run["seed"] for run in manifest["runs"]}, set(SEEDS))
        for run in manifest["runs"]:
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], PROFILE
            )
            self.assertTrue(run["metadata"]["v153_exact_random_prefix_cohort"])
            self.assertEqual(run["metadata"]["v153_numeric_hyperparameters_added"], 0)

    def test_random_prefix_window_requires_exact_cohort_and_safe_acceptance(
        self,
    ) -> None:
        event = {
            "decision": {
                "random_prefix_cohort": {
                    "enabled": True,
                    "cohort_source": "exact_persistent_same_seed_native_Random_ScheCmd_prefix_with_unchanged_early_stop_semantics",
                    "uses_completion_outcomes": False,
                    "cohort_equals_dispatch": True,
                    "feasible_player_count": 5,
                    "player_count": 2,
                    "missing_feasible_player_count": 3,
                    "dispatch_player_count": 2,
                    "commands_prepared": 2,
                    "early_stop_observed": True,
                },
                "native_portfolio": {
                    "random_shadow_lifecycle": "one_persistent_RandomScheduler_per_algorithm_seed_advanced_once_per_scheduling_window",
                    "random_shadow_invocations_this_window": 1,
                    "certificate_uses_completion_outcomes": False,
                },
                "native_shadow_anchor": {
                    "kind": "random",
                    "valid": True,
                    "certificate_uses_completion_outcomes": False,
                    "initializer_readiness_service_complete": True,
                    "proposal_readiness_service_complete": True,
                    "initializer_readiness_service_players": 2,
                    "proposal_readiness_service_players": 2,
                    "initializer_readiness_service_sum": 7.0,
                    "proposal_readiness_service_sum": 6.0,
                    "initializer_readiness_service_max": 4.0,
                    "proposal_readiness_service_max": 4.0,
                },
                "window_safe_guard": {
                    "evaluated": True,
                    "accepted": True,
                    "certificate_uses_completion_outcomes": False,
                    "initializer_baseline_welfare": 10.0,
                    "proposal_baseline_welfare": 10.5,
                },
            }
        }
        evidence = _audit_random_prefix_window(event)
        self.assertEqual(evidence["early_stop"], 1)
        self.assertEqual(evidence["prefix_players"], 2)
        event["decision"]["random_prefix_cohort"]["commands_prepared"] = 3
        with self.assertRaises(RuntimeError):
            _audit_random_prefix_window(event)

    def test_random_prefix_window_accepts_only_exact_empty_certificate(self) -> None:
        event = {
            "decision": {
                "random_prefix_cohort": {
                    "enabled": True,
                    "cohort_source": "exact_persistent_same_seed_native_Random_ScheCmd_prefix_with_unchanged_early_stop_semantics",
                    "uses_completion_outcomes": False,
                    "cohort_equals_dispatch": True,
                    "feasible_player_count": 0,
                    "player_count": 0,
                    "missing_feasible_player_count": 0,
                    "dispatch_player_count": 0,
                    "commands_prepared": 0,
                    "early_stop_observed": False,
                },
                "native_portfolio": {
                    "enabled": False,
                    "random_shadow_lifecycle": "one_persistent_RandomScheduler_per_algorithm_seed_advanced_once_per_scheduling_window",
                    "random_shadow_invocations_this_window": 1,
                    "certificate_uses_completion_outcomes": False,
                },
                "native_shadow_anchor": {
                    "kind": None,
                    "valid": False,
                    "commands": 0,
                    "certificate_uses_completion_outcomes": False,
                },
                "window_safe_guard": {
                    "evaluated": False,
                    "accepted": False,
                    "certificate_uses_completion_outcomes": False,
                },
            }
        }
        evidence = _audit_random_prefix_window(event)
        self.assertEqual(evidence["prefix_players"], 0)
        event["decision"]["window_safe_guard"]["accepted"] = True
        with self.assertRaises(RuntimeError):
            _audit_random_prefix_window(event)

    def test_random_prefix_window_accepts_exact_zero_command_early_stop(self) -> None:
        event = {
            "decision": {
                "random_prefix_cohort": {
                    "enabled": True,
                    "cohort_source": "exact_persistent_same_seed_native_Random_ScheCmd_prefix_with_unchanged_early_stop_semantics",
                    "uses_completion_outcomes": False,
                    "cohort_equals_dispatch": True,
                    "feasible_player_count": 4,
                    "player_count": 0,
                    "missing_feasible_player_count": 4,
                    "dispatch_player_count": 0,
                    "commands_prepared": 0,
                    "early_stop_observed": True,
                },
                "native_portfolio": {
                    "enabled": False,
                    "random_shadow_lifecycle": "one_persistent_RandomScheduler_per_algorithm_seed_advanced_once_per_scheduling_window",
                    "random_shadow_invocations_this_window": 1,
                    "certificate_uses_completion_outcomes": False,
                },
                "native_shadow_anchor": {
                    "kind": None,
                    "valid": False,
                    "commands": 0,
                    "certificate_uses_completion_outcomes": False,
                },
                "window_safe_guard": {
                    "evaluated": False,
                    "accepted": False,
                    "certificate_uses_completion_outcomes": False,
                },
            }
        }
        evidence = _audit_random_prefix_window(event)
        self.assertEqual(evidence["early_stop"], 1)
        self.assertEqual(evidence["prefix_players"], 0)
        self.assertEqual(evidence["feasible_players"], 4)

        event["decision"]["random_prefix_cohort"]["early_stop_observed"] = False
        with self.assertRaises(RuntimeError):
            _audit_random_prefix_window(event)


if __name__ == "__main__":
    unittest.main()
