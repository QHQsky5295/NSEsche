from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.g13_deferral_persistence_diagnosis import (
    VIOLATION_FIELDS,
    _episode_metrics,
    _spearman,
    evaluate_successor,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G12_GLOBAL_READY_ADMISSION_SEEDS,
)


class G13DeferralPersistenceDiagnosisTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        rows = []
        ordinal = 0
        for load_index, load in enumerate(FORMAL_E1_LOADS):
            for seed_index, seed in enumerate(G12_GLOBAL_READY_ADMISSION_SEEDS):
                ordinal += 1
                isolated = seed_index < 2
                persistent = 2 <= seed_index < 4
                log_t = 0.05 + 0.001 * load_index if isolated else -0.05
                log_q = 0.04 + 0.001 * load_index if isolated else -0.04
                row: dict[str, object] = {
                    "run_id": f"run-{ordinal}",
                    "load": load,
                    "seed": seed,
                    "isolated_only_activation": isolated,
                    "persistent_activation": persistent,
                    "joint_win": isolated,
                    "log_throughput_ratio": log_t,
                    "log_qpr_ratio": log_q,
                    "g12_activation_pass": True,
                    "runtime_identity_pass": True,
                }
                row.update({field: 0 for field in VIOLATION_FIELDS})
                rows.append(row)
        return rows

    def test_episode_metrics_use_adjacent_windows_and_keep_isolated_events(
        self,
    ) -> None:
        metrics = _episode_metrics([0, 2, 0, 1, 3, 4, 0, 5])
        self.assertEqual(metrics["positive_deferral_windows"], 5)
        self.assertEqual(metrics["deferral_episode_count"], 3)
        self.assertEqual(metrics["isolated_deferral_windows"], 2)
        self.assertEqual(metrics["persistent_deferral_transitions"], 2)
        self.assertEqual(metrics["longest_positive_episode"], 3)

    def test_spearman_uses_average_tie_ranks_and_fails_undefined_constant(self) -> None:
        self.assertAlmostEqual(_spearman([0, 0, 1, 2], [0, 0, 1, 2]), 1.0)
        self.assertAlmostEqual(_spearman([0, 0, 1, 2], [2, 2, 1, 0]), -1.0)
        self.assertIsNone(_spearman([1, 1, 1], [1, 2, 3]))

    def test_exact_conjunction_authorizes_only_preregistration(self) -> None:
        result = evaluate_successor(self._passing_rows())
        self.assertTrue(result["deferral_release_valve_preregistration_authorized"])
        self.assertFalse(result["implementation_authorized"])
        self.assertFalse(result["sampling_authorized"])
        self.assertTrue(all(result["conditions"].values()))

    def test_integrity_fails_on_missing_pair_identity_or_any_violation(self) -> None:
        rows = self._passing_rows()
        rows.pop()
        rows[0][VIOLATION_FIELDS[-1]] = 1
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "01_exact_15_pair_integrity_and_zero_structural_violations"
            ]
        )
        self.assertFalse(result["deferral_release_valve_preregistration_authorized"])

    def test_group_size_and_load_coverage_are_both_required(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] != FORMAL_E1_LOADS[0]:
                row["isolated_only_activation"] = False
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"]["02_isolated_and_persistent_groups_each_n3_two_loads"]
        )

    def test_joint_win_rate_condition_is_directional(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["persistent_activation"]:
                row["joint_win"] = True
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"]["03_isolated_joint_win_rate_above_persistent"]
        )

    def test_both_primary_mean_log_contrasts_are_required(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["isolated_only_activation"]:
                row["log_qpr_ratio"] = -0.10
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"]["04_isolated_mean_log_primary_ratios_above_persistent"]
        )

    def test_leave_one_out_condition_detects_single_run_dependence(self) -> None:
        rows = self._passing_rows()
        isolated = [row for row in rows if row["isolated_only_activation"]]
        for row in isolated:
            row["log_throughput_ratio"] = -0.06
            row["log_qpr_ratio"] = -0.05
        isolated[0]["log_throughput_ratio"] = 1.0
        isolated[0]["log_qpr_ratio"] = 1.0
        result = evaluate_successor(rows)
        self.assertTrue(
            result["conditions"]["04_isolated_mean_log_primary_ratios_above_persistent"]
        )
        self.assertFalse(
            result["conditions"][
                "05_both_mean_log_contrast_signs_positive_every_defined_loo"
            ]
        )

    def test_duplicate_run_id_fails_integrity_even_with_complete_matrix(self) -> None:
        rows = copy.deepcopy(self._passing_rows())
        rows[0]["run_id"] = rows[1]["run_id"]
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "01_exact_15_pair_integrity_and_zero_structural_violations"
            ]
        )


if __name__ == "__main__":
    unittest.main()
