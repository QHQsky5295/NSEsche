from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e3_all_native_portfolio_training_reveal_v139 as reveal_v139,
)

from scripts.reviewer_experiments.protocol.nse_e3_all_native_portfolio_training_prepare_v139 import (
    ARM_IDS,
    BASELINE_METHODS,
    SCENARIOS,
    TRAINING_SEED_LIST,
)
from scripts.reviewer_experiments.protocol.nse_e3_all_native_portfolio_training_reveal_v139 import (
    METRICS,
    evaluate_training_rows,
)


def synthetic_rows() -> list[dict]:
    rows = []
    labels = [*BASELINE_METHODS, *ARM_IDS]
    for label_index, label in enumerate(labels):
        for scenario_index, scenario in enumerate(SCENARIOS):
            for seed_index, seed in enumerate(TRAINING_SEED_LIST):
                baseline_value = 1.0 + 0.01 * label_index + 0.001 * seed_index
                if label == ARM_IDS[0]:
                    value = 2.0 + 0.01 * scenario_index + 0.001 * seed_index
                elif label == ARM_IDS[1]:
                    value = 1.05 + 0.001 * seed_index
                elif label == ARM_IDS[2]:
                    value = 0.5 + 0.001 * seed_index
                else:
                    value = baseline_value
                rows.append(
                    {
                        "run_id": f"{label}.{scenario}.{seed}",
                        "method_label": label,
                        "scenario": scenario,
                        "seed": seed,
                        "fixed_window_completed": 1,
                        **{metric: value for metric in METRICS},
                    }
                )
    return rows


class AllNativePortfolioRevealV139Tests(unittest.TestCase):
    def test_complete_all_baseline_gate_selects_only_strict_winner(self) -> None:
        result = evaluate_training_rows(synthetic_rows())
        self.assertTrue(result["family_training_gate_pass"])
        self.assertEqual(result["selected_profile"]["arm_id"], ARM_IDS[0])
        self.assertEqual(
            result["selected_profile"]["portfolio_rule"], "minimax_service"
        )
        self.assertEqual(len(result["passing_candidate_rankings"]), 1)
        self.assertEqual(
            result["arm_results"][ARM_IDS[0]]["score"]["passed_gate_count"], 9
        )
        self.assertFalse(result["paper_claim_authorized"])
        self.assertTrue(result["confirmation_required_for_any_claim"])

    def test_mean_win_without_two_positive_paired_seeds_fails(self) -> None:
        rows = synthetic_rows()
        target = ARM_IDS[0]
        scenario = SCENARIOS[0]
        metric = METRICS[0]
        candidate = [
            row
            for row in rows
            if row["method_label"] == target and row["scenario"] == scenario
        ]
        candidate[0][metric] = 10.0
        candidate[1][metric] = 0.0
        candidate[2][metric] = 0.0
        result = evaluate_training_rows(rows)
        gate = result["arm_results"][target]["gates"][scenario][metric]
        self.assertTrue(gate["strict_mean_rule_pass"])
        self.assertFalse(gate["all_nine_paired_direction_rules_pass"])
        self.assertFalse(gate["passed"])
        self.assertFalse(result["family_training_gate_pass"])

    def test_missing_run_and_nonfinite_qpr_fail_closed(self) -> None:
        rows = synthetic_rows()
        with self.assertRaisesRegex(ValueError, "product mismatch"):
            evaluate_training_rows(rows[:-1])
        corrupted = copy.deepcopy(rows)
        corrupted[0]["qpr_finite_only"] = None
        result = evaluate_training_rows(corrupted)
        for arm_id in ARM_IDS:
            self.assertFalse(
                result["arm_results"][arm_id]["score"]["all_required_gates_pass"]
            )

    def test_reveal_remains_sealed_until_this_rounds_blind_hash_is_frozen(self) -> None:
        self.assertIsNone(reveal_v139.BLIND_AUDIT_FILE_SHA256)
        self.assertIsNone(reveal_v139.BLIND_AUDIT_HASH)
        with self.assertRaisesRegex(RuntimeError, "has not been frozen"):
            reveal_v139._validate_blind_audit()


if __name__ == "__main__":
    unittest.main()
