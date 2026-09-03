from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.g3_order_counterfactual import (
    G3_STRATA,
    MECHANISMS,
    _validate_counterfactual,
    apply_frozen_eligibility,
)


def _aggregate(
    *,
    welfare: float = 10.0,
    startup: float = 10.0,
    finish: float = 10.0,
    different: float = 0.02,
    bad: int = 0,
    envelope_violations: int = 0,
) -> dict[str, object]:
    return {
        "run_count": 5,
        "welfare_per_player": welfare,
        "startup_burden_per_player": startup,
        "projected_finish_per_player": finish,
        "different_assignment_fraction": different,
        "additional_bad_windows": bad,
        "envelope_welfare_violations": envelope_violations,
    }


def _good_outcome(order: str, assignment_hash: int = 7) -> dict[str, object]:
    return {
        "order": order,
        "order_hash": 1,
        "candidate_set_hash": 2,
        "players": 1,
        "assigned_players": 1,
        "assignment_hash": assignment_hash,
        "complete": True,
        "stable": True,
        "inner_limit_hit": False,
        "oscillations": 0,
        "strict_pne": {
            "certified": True,
            "violating_players": 0,
            "missing_current_utility_players": 0,
            "maximum_profitable_gain": 0.0,
        },
        "welfare": {"total": 10.0},
        "startup_burden_sum": 5.0,
        "projected_finish_sum": 9.0,
    }


class CounterfactualSchemaTests(unittest.TestCase):
    def test_complete_payload_passes(self) -> None:
        orders = (
            "ready_order",
            "reverse_ready_order",
            "service_scarcity_first",
            "capacity_scarcity_first",
            "resource_impact_first",
        )
        outcomes = [_good_outcome(order) for order in orders]
        payload = {
            "schema": "strict_pne_scarcity_order_v1",
            "decision_feedback": False,
            "candidate_set_hash": 2,
            "live_first_inner_assignment_hash": 7,
            "o0_first_inner_hash_match": True,
            "outcomes": outcomes,
            "envelope": {
                "name": "nonworse_welfare_cold_envelope",
                "selected_order": "ready_order",
                "selected_assignment_hash": 7,
                "selected_non_o0": False,
                "eligible_outcomes": 5,
                "welfare_tolerance": 1e-5,
            },
        }
        selected, envelope, errors = _validate_counterfactual(
            "run", {"order_counterfactual": payload}
        )
        self.assertEqual(set(selected), set(orders))
        self.assertEqual(envelope["selected_order"], "ready_order")
        self.assertEqual(errors, [])

    def test_missing_order_fails_closed(self) -> None:
        payload = {
            "schema": "strict_pne_scarcity_order_v1",
            "decision_feedback": False,
            "candidate_set_hash": 2,
            "outcomes": [_good_outcome("ready_order")],
            "envelope": {
                "name": "nonworse_welfare_cold_envelope",
                "selected_order": "ready_order",
                "selected_assignment_hash": 7,
                "selected_non_o0": False,
                "welfare_tolerance": 1e-5,
            },
        }
        _, _, errors = _validate_counterfactual(
            "run", {"order_counterfactual": payload}
        )
        self.assertTrue(any("order_set" in error for error in errors))

    def test_stable_complete_o0_with_failed_certificate_fails(self) -> None:
        orders = (
            "ready_order",
            "reverse_ready_order",
            "service_scarcity_first",
            "capacity_scarcity_first",
            "resource_impact_first",
        )
        outcomes = [_good_outcome(order) for order in orders]
        outcomes[0]["strict_pne"]["certified"] = False
        payload = {
            "schema": "strict_pne_scarcity_order_v1",
            "decision_feedback": False,
            "candidate_set_hash": 2,
            "live_first_inner_assignment_hash": 7,
            "o0_first_inner_hash_match": True,
            "outcomes": outcomes,
            "envelope": {
                "name": "nonworse_welfare_cold_envelope",
                "selected_order": "reverse_ready_order",
                "selected_assignment_hash": 7,
                "selected_non_o0": True,
                "welfare_tolerance": 1e-5,
            },
        }
        _, _, errors = _validate_counterfactual(
            "run", {"order_counterfactual": payload}
        )
        self.assertTrue(any("o0_strict_pne_certificate" in error for error in errors))

    def test_capped_o0_without_live_stable_trace_is_retained(self) -> None:
        orders = (
            "ready_order",
            "reverse_ready_order",
            "service_scarcity_first",
            "capacity_scarcity_first",
            "resource_impact_first",
        )
        outcomes = [_good_outcome(order) for order in orders]
        outcomes[0].update(
            stable=False,
            inner_limit_hit=True,
            termination="inner_iteration_limit",
        )
        outcomes[0]["strict_pne"]["certified"] = False
        payload = {
            "schema": "strict_pne_scarcity_order_v1",
            "decision_feedback": False,
            "candidate_set_hash": 2,
            "live_first_inner_assignment_hash": None,
            "o0_first_inner_hash_match": None,
            "outcomes": outcomes,
            "envelope": {
                "name": "nonworse_welfare_cold_envelope",
                "selected_order": "ready_order",
                "selected_assignment_hash": 7,
                "selected_non_o0": False,
                "eligible_outcomes": 0,
                "welfare_tolerance": 1e-5,
            },
        }
        _, _, errors = _validate_counterfactual(
            "run", {"order_counterfactual": payload}
        )
        self.assertEqual(errors, [])

    def test_envelope_guard_uses_frozen_binary32_addition(self) -> None:
        orders = (
            "ready_order",
            "reverse_ready_order",
            "service_scarcity_first",
            "capacity_scarcity_first",
            "resource_impact_first",
        )
        outcomes = [_good_outcome(order) for order in orders]
        outcomes[0]["welfare"]["total"] = 359.379150390625
        outcomes[1]["welfare"]["total"] = 359.3787841796875
        outcomes[1]["assignment_hash"] = 8
        payload = {
            "schema": "strict_pne_scarcity_order_v1",
            "decision_feedback": False,
            "candidate_set_hash": 2,
            "live_first_inner_assignment_hash": 7,
            "o0_first_inner_hash_match": True,
            "outcomes": outcomes,
            "envelope": {
                "name": "nonworse_welfare_cold_envelope",
                "selected_order": "reverse_ready_order",
                "selected_assignment_hash": 8,
                "selected_non_o0": True,
                "eligible_outcomes": 5,
                "welfare_tolerance": 0.00035937916254624724,
            },
        }
        _, _, errors = _validate_counterfactual(
            "run", {"order_counterfactual": payload}
        )
        self.assertEqual(errors, [])


class FrozenEligibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        baseline = _aggregate(different=0.0)
        self.overall = {mechanism: copy.deepcopy(baseline) for mechanism in MECHANISMS}
        self.strata = {
            stratum: {mechanism: copy.deepcopy(baseline) for mechanism in MECHANISMS}
            for stratum in G3_STRATA
        }
        for mechanism in ("O2", "E0"):
            self.overall[mechanism] = _aggregate(welfare=10.01, startup=9.0, finish=9.0)
            for stratum in G3_STRATA:
                self.strata[stratum][mechanism] = _aggregate(
                    welfare=10.01, startup=9.0, finish=9.0
                )

    def test_qualifying_raw_order_and_envelope_are_ranked(self) -> None:
        result = apply_frozen_eligibility(
            self.overall, self.strata, integrity_passed=True
        )
        self.assertTrue(result["decisions"]["O2"]["eligible"])
        self.assertTrue(result["decisions"]["E0"]["eligible"])
        self.assertEqual(result["eligible_ranked"][:2], ["O2", "E0"])
        self.assertFalse(result["D71_authorized"])

    def test_integrity_failure_rejects_every_mechanism(self) -> None:
        result = apply_frozen_eligibility(
            self.overall, self.strata, integrity_passed=False
        )
        self.assertFalse(any(item["eligible"] for item in result["decisions"].values()))

    def test_welfare_stratum_regression_above_point_one_percent_rejects(self) -> None:
        self.strata[G3_STRATA[0]]["O2"]["welfare_per_player"] = 9.98
        result = apply_frozen_eligibility(
            self.overall, self.strata, integrity_passed=True
        )
        self.assertFalse(result["decisions"]["O2"]["eligible"])
        self.assertFalse(
            result["decisions"]["O2"]["gates"]["welfare_max_stratum_regression"]
        )

    def test_proxy_regression_above_one_percent_rejects(self) -> None:
        self.strata[G3_STRATA[0]]["O2"]["startup_burden_per_player"] = 10.2
        result = apply_frozen_eligibility(
            self.overall, self.strata, integrity_passed=True
        )
        self.assertFalse(result["decisions"]["O2"]["eligible"])
        self.assertFalse(result["decisions"]["O2"]["gates"]["startup_max_regression"])

    def test_assignment_difference_requires_four_strata(self) -> None:
        for stratum in G3_STRATA[3:]:
            self.strata[stratum]["O2"]["different_assignment_fraction"] = 0.0
        result = apply_frozen_eligibility(
            self.overall, self.strata, integrity_passed=True
        )
        self.assertFalse(result["decisions"]["O2"]["eligible"])
        self.assertEqual(result["decisions"]["O2"]["distinct_strata"], 3)


if __name__ == "__main__":
    unittest.main()
