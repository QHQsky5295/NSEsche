from __future__ import annotations

import unittest

from scripts.reviewer_experiments.analysis.g11_state_regime_diagnosis import (
    RUN_LEVEL_STATE_FIELDS,
    _coherence,
    _confusion,
    _distribution,
    _paired_outcomes,
    _percentile,
    _ranks,
    _spearman,
    _state_feature_names,
    _threshold_diagnostics,
)
from scripts.reviewer_experiments.protocol.g10_work_conserving import (
    G10_CANDIDATES,
    G10_CONTROL,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G10_WORK_CONSERVING_SEEDS,
    ProtocolValidationError,
)


class G11StateRegimeDiagnosisTests(unittest.TestCase):
    def test_percentile_interpolates_and_rejects_empty_input(self) -> None:
        self.assertEqual(_percentile([4.0, 1.0, 3.0, 2.0], 0.0), 1.0)
        self.assertEqual(_percentile([4.0, 1.0, 3.0, 2.0], 1.0), 4.0)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 0.50), 2.5)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 0.90), 3.7)
        with self.assertRaises(ProtocolValidationError):
            _percentile([], 0.5)

    def test_tied_ranks_and_spearman_are_deterministic(self) -> None:
        self.assertEqual(_ranks([10.0, 20.0, 20.0, 40.0]), [1.0, 2.5, 2.5, 4.0])
        self.assertAlmostEqual(
            _spearman([1.0, 2.0, 3.0, 4.0], [8.0, 6.0, 4.0, 2.0]), -1.0
        )
        self.assertIsNone(_spearman([1.0, 1.0], [2.0, 3.0]))

    def test_distribution_contains_every_frozen_saturation_fraction(self) -> None:
        result = _distribution("ready_per_node", [0.0, 1.0, 2.0, 8.0])
        self.assertEqual(result["ready_per_node_mean"], 2.75)
        self.assertEqual(result["ready_per_node_ge_1x_fraction"], 0.75)
        self.assertEqual(result["ready_per_node_ge_2x_fraction"], 0.50)
        self.assertEqual(result["ready_per_node_ge_4x_fraction"], 0.25)
        self.assertEqual(result["ready_per_node_ge_8x_fraction"], 0.25)

    def test_confusion_gate_uses_run_level_observations(self) -> None:
        rows = []
        for index in range(10):
            rows.append(
                {
                    "load": "low",
                    "seed": f"S{index}",
                    "active_ready_ge_2x_fraction": 1.0 if index < 5 else 0.0,
                    "joint_favorable": index in {0, 1, 2, 3, 5, 6},
                }
            )
        result = _confusion(rows, 2)
        self.assertEqual(
            {key: result[key] for key in ("tp", "tn", "fp", "fn")},
            {"tp": 4, "tn": 3, "fp": 1, "fn": 2},
        )
        self.assertAlmostEqual(result["sensitivity"], 4.0 / 6.0)
        self.assertAlmostEqual(result["specificity"], 3.0 / 4.0)
        self.assertTrue(result["passed_full_threshold"])

    def test_threshold_and_coherence_are_stable_under_every_seed_omission(self) -> None:
        rows = []
        ordinal = 0
        for seed_index, seed in enumerate(G10_WORK_CONSERVING_SEEDS):
            for load_index, load in enumerate(FORMAL_E1_LOADS):
                ordinal += 1
                favorable = load_index < 2
                saturation = 0.75 if favorable else 0.25
                benefit = float(load_index + 3 * seed_index)
                rows.append(
                    {
                        "load": load,
                        "seed": seed,
                        "active_ready_ge_2x_fraction": saturation,
                        "joint_favorable": favorable,
                        "log_throughput_ratio": benefit,
                        "log_qpr_ratio": benefit * 2.0,
                    }
                )
        threshold = _threshold_diagnostics(rows, 2)
        self.assertEqual(len(rows), 15)
        self.assertTrue(threshold["passed_full_threshold"])
        self.assertTrue(threshold["all_leave_one_seed_out_pass"])
        self.assertEqual(len(threshold["leave_one_seed_out"]), 5)

        coherent_rows = []
        for ordinal, row in enumerate(rows):
            coherent_rows.append(
                {
                    **row,
                    "active_ready_ge_2x_fraction": float(ordinal),
                    "log_throughput_ratio": float(ordinal),
                    "log_qpr_ratio": float(ordinal) * 3.0,
                }
            )
        coherence = _coherence(coherent_rows, 2)
        self.assertTrue(
            coherence["positive_for_both_outcomes_full_and_every_leave_one_seed_out"]
        )

    def test_paired_table_retains_all_prespecified_run_level_features(self) -> None:
        rows = []
        for load in FORMAL_E1_LOADS:
            for seed in G10_WORK_CONSERVING_SEEDS:
                for method in (G10_CONTROL, G10_CANDIDATES[1]):
                    candidate = method == G10_CANDIDATES[1]
                    row = {
                        "run_id": f"{load}-{seed}-{method}",
                        "load": load,
                        "seed": seed,
                        "effective_method": method,
                        "throughput_requests_per_ms": 1.1 if candidate else 1.0,
                        "qpr": 1.1 if candidate else 1.0,
                        "latency_mean_ms": 0.9 if candidate else 1.0,
                        "cost_per_completed_request": 1.0,
                        "completion_ratio": 1.0,
                        "active_ready_ge_2x_fraction": 0.75,
                    }
                    for field in RUN_LEVEL_STATE_FIELDS:
                        row.setdefault(field, 1.0)
                    rows.append(row)
        paired = _paired_outcomes(rows, G10_CANDIDATES[1])
        self.assertEqual(len(paired), 15)
        self.assertTrue(all(row["joint_favorable"] for row in paired))
        for field in RUN_LEVEL_STATE_FIELDS:
            self.assertIn(field, paired[0])
        selected = _state_feature_names(paired)
        for field in RUN_LEVEL_STATE_FIELDS:
            self.assertIn(field, selected)
        self.assertNotIn("throughput_ratio", selected)


if __name__ == "__main__":
    unittest.main()
