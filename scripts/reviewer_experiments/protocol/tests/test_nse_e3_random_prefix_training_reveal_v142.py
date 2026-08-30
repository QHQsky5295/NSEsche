from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e3_random_prefix_training_reveal_v142 as reveal_v142,
)

from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    ARM_IDS,
    BASELINE_METHODS,
    RETIRED_OPENED_V141_TRAINING_SEEDS,
    SCENARIOS,
    TRAINING_SEED_LIST,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_reveal_v142 import (
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


class RandomAnchorRevealV142Tests(unittest.TestCase):
    def test_v141_training_seeds_remain_retired(self) -> None:
        self.assertEqual(
            RETIRED_OPENED_V141_TRAINING_SEEDS, ["E1523", "E1524", "E1525"]
        )

    def test_complete_all_baseline_gate_selects_only_strict_winner(self) -> None:
        result = evaluate_training_rows(synthetic_rows())
        self.assertTrue(result["family_training_gate_pass"])
        self.assertEqual(result["selected_profile"]["arm_id"], ARM_IDS[0])
        self.assertEqual(
            result["selected_profile"]["native_selection_rule"],
            "exact_random_prefix",
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

    def test_reveal_is_bound_to_this_rounds_passing_blind_audit(self) -> None:
        self.assertEqual(
            reveal_v142.BLIND_AUDIT_FILE_SHA256,
            "d30551d98cca78681f165c60991354d7950c7dbe5ce8352a54f641434591fabc",
        )
        self.assertEqual(
            reveal_v142.BLIND_AUDIT_HASH,
            "23d6e417f067fa75296d92b61b85dfafdf3ff2f979dbea9774a2bd7a3ae3df15",
        )


if __name__ == "__main__":
    unittest.main()
