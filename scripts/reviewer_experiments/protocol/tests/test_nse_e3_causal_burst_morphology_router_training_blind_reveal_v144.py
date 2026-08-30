from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol.nse_e3_causal_burst_morphology_router_training_blind_audit_v144 import (
    _expected_route,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_burst_morphology_router_training_prepare_v144 import (
    ARM_ID,
    TRAINING_SEED_LIST,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_burst_morphology_router_training_reveal_v144 import (
    _validate_blind_audit,
    evaluate_training_rows,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
    SCENARIOS,
)


class V144CausalMorphologyBlindRevealTests(unittest.TestCase):
    def test_causal_route_is_exact_preregistered_state_machine(self) -> None:
        self.assertEqual(
            _expected_route(True, 0, False),
            ("hash", "quiet_before_first_episode_hash"),
        )
        self.assertEqual(
            _expected_route(True, 1, False),
            ("greedy", "first_short_episode_or_post_episode_greedy"),
        )
        self.assertEqual(
            _expected_route(True, 1, True),
            ("faasrank", "first_sustained_episode_retained_faasrank"),
        )
        self.assertEqual(
            _expected_route(True, 2, True),
            ("load_least", "recurrent_episode_retained_load_least"),
        )
        self.assertEqual(
            _expected_route(False, 2, True),
            ("hash", "arrival_history_discontinuity_fail_closed_hash"),
        )

    def test_reveal_fails_closed_before_blind_hash_freeze(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "has not been frozen"):
            _validate_blind_audit()

    def test_all_nine_gates_are_required(self) -> None:
        rows = []
        for method_index, method in enumerate([*BASELINE_METHODS, ARM_ID]):
            for scenario in SCENARIOS:
                for seed in TRAINING_SEED_LIST:
                    candidate = method == ARM_ID
                    value = 20.0 if candidate else 10.0 + method_index / 100.0
                    rows.append(
                        {
                            "method_label": method,
                            "scenario": scenario,
                            "seed": seed,
                            "run_id": f"{method}-{scenario}-{seed}",
                            "fixed_window_completed": 1,
                            "throughput_requests_per_ms": value,
                            "qpr_finite_only": value,
                            "qpr_zero_completed_as_zero": value,
                        }
                    )
        evaluation = evaluate_training_rows(rows)
        self.assertTrue(evaluation["family_training_gate_pass"])
        self.assertEqual(
            evaluation["candidate_result"]["score"]["passed_gate_count"], 9
        )
        for row in rows:
            if row["method_label"] == ARM_ID and row["scenario"] == SCENARIOS[-1]:
                row["throughput_requests_per_ms"] = 0.0
        evaluation = evaluate_training_rows(rows)
        self.assertFalse(evaluation["family_training_gate_pass"])


if __name__ == "__main__":
    unittest.main()
