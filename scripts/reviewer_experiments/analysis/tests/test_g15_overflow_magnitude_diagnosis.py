from __future__ import annotations

import copy
import math
import unittest

from scripts.reviewer_experiments.analysis.g15_overflow_magnitude_diagnosis import (
    TELEMETRY_COMPARE_FIELDS,
    THRESHOLD_KEYS,
    VIOLATION_FIELDS,
    _classifier_report,
    _feature_row,
    _percentile,
    _select_classifier,
    evaluate_successor,
)
from scripts.reviewer_experiments.analysis.g14_deferral_release_valve import (
    DEFERRAL_RELEASE_VALVE_SCHEMA,
    _release_valve_telemetry,
)
from scripts.reviewer_experiments.protocol.g14_deferral_release_valve import (
    G14_CANDIDATE,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G14_DEFERRAL_RELEASE_VALVE_SEEDS,
)


class G15OverflowMagnitudeDiagnosisTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        rows = []
        ordinal = 0
        for load in FORMAL_E1_LOADS:
            for seed_index, seed in enumerate(G14_DEFERRAL_RELEASE_VALVE_SEEDS):
                ordinal += 1
                positive = seed_index < 2
                p90 = (2.0 if positive else 1.30) + ordinal * 0.001
                throughput_ratio = (1.05 if positive else 0.98) + ordinal * 0.0001
                qpr_ratio = (1.08 if positive else 0.97) + ordinal * 0.0001
                fractions = {
                    THRESHOLD_KEYS[0]: 1.0,
                    THRESHOLD_KEYS[1]: 1.0 if positive else 0.0,
                    THRESHOLD_KEYS[2]: 0.5 if positive else 0.0,
                    THRESHOLD_KEYS[3]: 0.0,
                }
                rows.append(
                    {
                        "run_id": f"run-{ordinal}",
                        "load": load,
                        "seed": seed,
                        "joint_win": positive,
                        "first_overflow_window_count": 2,
                        "first_overflow_ratio_fraction_ge": fractions,
                        "first_overflow_ratio_p90": p90,
                        "persistent_episode_fraction": (
                            0.70 + ordinal * 0.001
                            if positive
                            else 0.10 + ordinal * 0.001
                        ),
                        "log_throughput_ratio": math.log(throughput_ratio),
                        "log_qpr_ratio": math.log(qpr_ratio),
                        "g14_activation_pass": True,
                        "runtime_identity_pass": True,
                        **{field: 0 for field in VIOLATION_FIELDS},
                    }
                )
        return rows

    @staticmethod
    def _telemetry(
        *,
        feasible: int,
        admitted: int,
        mode: str,
        before: bool,
        after: bool,
        deferred: int,
    ) -> dict[str, object]:
        return {
            "schema": DEFERRAL_RELEASE_VALVE_SCHEMA,
            "dependency_ready_candidates": feasible + 1,
            "feasible_ready_candidates": feasible,
            "configured_node_count": 20,
            "admission_limit": admitted,
            "admitted_players": admitted,
            "deferred_feasible_players": deferred,
            "candidate_order_hash": 10,
            "admitted_order_hash": 10 if admitted == feasible else 11,
            "current_overflow": feasible > 20,
            "valve_open_before": before,
            "valve_open_after": after,
            "admission_mode": mode,
            "admitted_min_arrival_frame": 1 if admitted else None,
            "admitted_max_arrival_frame": 2 if admitted else None,
            **{field: 0 for field in VIOLATION_FIELDS},
        }

    def _events_and_metric(self):
        telemetry = [
            self._telemetry(
                feasible=10,
                admitted=10,
                mode="below_limit",
                before=False,
                after=False,
                deferred=0,
            ),
            self._telemetry(
                feasible=25,
                admitted=20,
                mode="first_overflow_bounded",
                before=False,
                after=True,
                deferred=5,
            ),
            self._telemetry(
                feasible=24,
                admitted=24,
                mode="persistent_overflow_release",
                before=True,
                after=True,
                deferred=0,
            ),
            self._telemetry(
                feasible=12,
                admitted=12,
                mode="post_overflow_reset",
                before=True,
                after=False,
                deferred=0,
            ),
            self._telemetry(
                feasible=21,
                admitted=20,
                mode="first_overflow_bounded",
                before=False,
                after=True,
                deferred=1,
            ),
        ]
        events = [
            {
                "global_ready_player_admission": row,
                "decision": {"assigned_players": row["admitted_players"]},
                "cluster": {
                    "queue_pending_total": index + 1,
                    "queue_resident_total": 2,
                    "queue_total": index + 3,
                },
            }
            for index, row in enumerate(telemetry)
        ]
        raw = _release_valve_telemetry(
            [
                (index, row, int(row["admitted_players"]))
                for index, row in enumerate(telemetry)
            ],
            20,
        )
        metric = {field: raw[field] for field in TELEMETRY_COMPARE_FIELDS}
        metric.update(
            {
                "g14_activation_pass": True,
                "runtime_identity_pass": True,
                "nash_runtime_pass": False,
                "nash_runtime_issues": ["retained synthetic exception"],
                "active_window_count": 5,
                "strict_pne_active_windows": 4,
                "offline_reference_hit_windows": 4,
            }
        )
        return events, metric

    def test_type7_percentile(self) -> None:
        self.assertEqual(_percentile([], 0.9), None)
        self.assertEqual(_percentile([1.0], 0.9), 1.0)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 0.9), 3.7)

    def test_feature_row_reconstructs_episodes_and_first_overflow_ratios(self) -> None:
        events, metric = self._events_and_metric()
        run = {
            "run_id": "candidate-run",
            "run_spec_hash": "a" * 64,
            "seed": "D106",
            "workload": {"request_freq": "low"},
            "workload_tape": {"sha256": "b" * 64},
            "metadata": {"m1_operational_candidate": G14_CANDIDATE},
        }
        paired = {
            "throughput_ratio": 1.1,
            "qpr_ratio": 1.2,
            "latency_ratio": 0.9,
            "cost_ratio": 1.0,
            "completion_ratio_difference": 0.01,
        }
        row = _feature_row(run, events, paired, metric, 20)
        self.assertEqual(row["overflow_episode_count"], 2)
        self.assertEqual(row["persistent_episode_count"], 1)
        self.assertEqual(row["episode_lengths"], [2, 1])
        self.assertEqual(row["first_overflow_ratios"], [1.25, 1.05])
        self.assertAlmostEqual(row["persistent_episode_fraction"], 0.5)
        self.assertEqual(row["deferred_total"], 6)
        self.assertFalse(row["nash_runtime_pass"])

    def test_classifier_reports_complete_confusion_and_loo(self) -> None:
        report = _classifier_report(self._passing_rows(), 1.5)
        self.assertEqual(report["confusion"], {"tp": 6, "fp": 0, "tn": 9, "fn": 0})
        self.assertEqual(report["balanced_accuracy"], 1.0)
        self.assertEqual(report["predicted_positive"]["n"], 6)
        self.assertEqual(len(report["leave_one_run_out"]), 15)

    def test_classifier_selection_uses_accuracy_balance_then_smaller_threshold(
        self,
    ) -> None:
        rows = self._passing_rows()
        reports = [_classifier_report(rows, value) for value in (1.25, 1.5, 2.0, 4.0)]
        selected = _select_classifier(reports)
        self.assertEqual(selected["threshold"], 1.5)

    def test_passing_successor_requires_all_five_conditions(self) -> None:
        result = evaluate_successor(self._passing_rows())
        self.assertTrue(result["magnitude_gated_valve_preregistration_authorized"])
        self.assertEqual(result["selected_threshold_report"]["threshold"], 1.5)
        self.assertTrue(all(result["conditions"].values()))

    def test_missing_identity_or_structural_violation_fails_integrity(self) -> None:
        rows = self._passing_rows()
        rows.pop()
        rows[0][VIOLATION_FIELDS[0]] = 1
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "01_exact_15_pair_activation_identity_zero_violation_integrity"
            ]
        )

    def test_classifier_floor_failure_blocks_successor(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            row["joint_win"] = not bool(row["joint_win"])
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "02_selected_fixed_threshold_meets_classifier_and_group_floors"
            ]
        )

    def test_dual_effect_or_association_reversal_blocks_successor(self) -> None:
        rows = copy.deepcopy(self._passing_rows())
        for row in rows:
            if row["joint_win"]:
                row["log_qpr_ratio"] = math.log(0.5)
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "03_predicted_positive_mean_log_primary_effects_are_better"
            ]
        )
        rows = self._passing_rows()
        for row in rows:
            row["persistent_episode_fraction"] = -float(row["first_overflow_ratio_p90"])
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "05_p90_magnitude_positive_persistence_and_throughput_associations_all_loo"
            ]
        )


if __name__ == "__main__":
    unittest.main()
