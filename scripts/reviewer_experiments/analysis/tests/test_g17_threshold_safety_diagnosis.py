from __future__ import annotations

import copy
import math
import unittest

from scripts.reviewer_experiments.analysis.g17_threshold_safety_diagnosis import (
    DOSE_BUDGETS,
    TELEMETRY_COMPARE_FIELDS,
    THRESHOLD_KEYS,
    VIOLATION_FIELDS,
    _classifier_report,
    _feature_row,
    _percentile,
    _select_threshold,
    evaluate_successor,
)
from scripts.reviewer_experiments.analysis.g16_overflow_magnitude_valve import (
    OVERFLOW_MAGNITUDE_RELEASE_VALVE_SCHEMA,
    _overflow_magnitude_telemetry,
)
from scripts.reviewer_experiments.protocol.g16_overflow_magnitude_valve import (
    G16_CANDIDATE,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS,
)


class G17ThresholdSafetyDiagnosisTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        rows = []
        ordinal = 0
        for load in FORMAL_E1_LOADS:
            for seed_index, seed in enumerate(G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS):
                ordinal += 1
                safe = seed_index < 2
                candidate_ratio = 1.05 if safe else 0.90
                fractions = {
                    THRESHOLD_KEYS[0]: 1.0,
                    THRESHOLD_KEYS[1]: 1.0 if safe else 0.0,
                    THRESHOLD_KEYS[2]: 1.0 if seed_index == 0 else 0.0,
                    THRESHOLD_KEYS[3]: 0.0,
                }
                dose = {
                    str(budget): {
                        "retained_bounded_events": min(budget, 2),
                        "retained_deferred_players": min(budget, 2) * 3,
                        "bounded_event_coverage": min(budget, 2) / 2,
                        "deferred_player_coverage": min(budget, 2) / 2,
                    }
                    for budget in DOSE_BUDGETS
                }
                rows.append(
                    {
                        "run_id": f"run-{ordinal}",
                        "load": load,
                        "seed": seed,
                        "first_overflow_window_count": 2,
                        "first_overflow_ratio_fraction_ge": fractions,
                        "actual_bounded_window_count": 2,
                        "dose_budget_trace_coverage": dose,
                        "candidate_throughput": candidate_ratio,
                        "control_throughput": 1.0,
                        "candidate_qpr": candidate_ratio,
                        "control_qpr": 1.0,
                        "throughput_ratio": candidate_ratio,
                        "qpr_ratio": candidate_ratio,
                        "log_throughput_ratio": math.log(candidate_ratio),
                        "log_qpr_ratio": math.log(candidate_ratio),
                        "joint_nonloss": safe,
                        "joint_win": safe,
                        "g16_activation_pass": True,
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
        applicable: bool,
        passed: bool,
        deferred: int,
    ) -> dict[str, object]:
        return {
            "schema": OVERFLOW_MAGNITUDE_RELEASE_VALVE_SCHEMA,
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
            "magnitude_gate_applicable": applicable,
            "magnitude_gate_pass": passed,
            "magnitude_threshold_numerator": 5,
            "magnitude_threshold_denominator": 4,
            "magnitude_comparison_lhs": 4 * feasible,
            "magnitude_comparison_rhs": 100,
            "admission_mode": mode,
            "admitted_min_arrival_frame": 1 if admitted else None,
            "admitted_max_arrival_frame": 2 if admitted else None,
            **{field: 0 for field in VIOLATION_FIELDS},
        }

    def _events_and_metrics(self):
        telemetry = [
            self._telemetry(
                feasible=10,
                admitted=10,
                mode="below_limit",
                before=False,
                after=False,
                applicable=False,
                passed=False,
                deferred=0,
            ),
            self._telemetry(
                feasible=22,
                admitted=22,
                mode="first_overflow_below_magnitude_release",
                before=False,
                after=True,
                applicable=True,
                passed=False,
                deferred=0,
            ),
            self._telemetry(
                feasible=24,
                admitted=24,
                mode="persistent_overflow_release",
                before=True,
                after=True,
                applicable=False,
                passed=False,
                deferred=0,
            ),
            self._telemetry(
                feasible=12,
                admitted=12,
                mode="post_overflow_reset",
                before=True,
                after=False,
                applicable=False,
                passed=False,
                deferred=0,
            ),
            self._telemetry(
                feasible=30,
                admitted=20,
                mode="first_overflow_magnitude_bounded",
                before=False,
                after=True,
                applicable=True,
                passed=True,
                deferred=10,
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
        raw = _overflow_magnitude_telemetry(
            [
                (index, row, int(row["admitted_players"]))
                for index, row in enumerate(telemetry)
            ],
            20,
        )
        candidate = {field: raw[field] for field in TELEMETRY_COMPARE_FIELDS}
        candidate.update(
            {
                "g16_activation_pass": True,
                "runtime_identity_pass": True,
                "nash_runtime_pass": False,
                "nash_runtime_issues": ["retained synthetic exception"],
                "active_window_count": 5,
                "assigned_players": 88,
                "strict_pne_active_windows": 4,
                "offline_reference_hit_windows": 4,
                "throughput_requests_per_ms": 1.1,
                "qpr": 1.2,
            }
        )
        control = {"throughput_requests_per_ms": 1.0, "qpr": 1.0}
        return events, candidate, control

    def test_type7_percentile(self) -> None:
        self.assertEqual(_percentile([], 0.9), None)
        self.assertEqual(_percentile([1.0], 0.9), 1.0)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
        self.assertAlmostEqual(_percentile([1.0, 2.0, 3.0, 4.0], 0.9), 3.7)

    def test_feature_row_reconstructs_modes_thresholds_episodes_and_dose(self) -> None:
        events, candidate, control = self._events_and_metrics()
        run = {
            "run_id": "candidate-run",
            "run_spec_hash": "a" * 64,
            "seed": "D111",
            "workload": {"request_freq": "low"},
            "workload_tape": {"sha256": "b" * 64},
            "metadata": {"m1_operational_candidate": G16_CANDIDATE},
        }
        paired = {
            "throughput_ratio": 1.1,
            "qpr_ratio": 1.2,
            "latency_ratio": 0.9,
            "cost_ratio": 1.0,
            "completion_ratio_difference": 0.01,
        }
        row = _feature_row(run, events, paired, candidate, control, 20)
        self.assertEqual(row["overflow_episode_count"], 2)
        self.assertEqual(row["persistent_episode_count"], 1)
        self.assertEqual(row["episode_lengths"], [2, 1])
        self.assertEqual(row["first_overflow_ratios"], [1.1, 1.5])
        self.assertEqual(row["first_overflow_count_ge"]["1.25"], 1)
        self.assertEqual(row["actual_bounded_window_count"], 1)
        self.assertEqual(row["actual_deferred_player_total"], 10)
        self.assertEqual(
            row["dose_budget_trace_coverage"]["1"]["retained_deferred_players"],
            10,
        )
        self.assertFalse(row["nash_runtime_pass"])

    def test_classifier_reports_both_labels_envelope_and_complete_loo(self) -> None:
        report = _classifier_report(self._passing_rows(), 1.5)
        self.assertEqual(
            report["joint_nonloss_classifier"]["confusion"],
            {"tp": 6, "fp": 0, "tn": 9, "fn": 0},
        )
        self.assertEqual(report["balanced_accuracy"], 1.0)
        self.assertEqual(report["predicted_safe"]["n"], 6)
        self.assertEqual(len(report["leave_one_run_out"]), 15)
        self.assertTrue(
            all(
                row["throughput_mean_ratio"] > 1.0 and row["qpr_mean_ratio"] > 1.0
                for row in report["optimistic_screening_envelope"]["by_load"]
            )
        )

    def test_threshold_selection_uses_envelope_before_classifier(self) -> None:
        rows = self._passing_rows()
        reports = [_classifier_report(rows, value) for value in (1.25, 1.5, 2.0, 4.0)]
        selected = _select_threshold(reports)
        self.assertEqual(selected["threshold"], 1.5)

    def test_threshold_selection_prefers_larger_final_tie(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            row["first_overflow_ratio_fraction_ge"]["2"] = row[
                "first_overflow_ratio_fraction_ge"
            ]["1.5"]
        reports = [_classifier_report(rows, value) for value in (1.5, 2.0)]
        self.assertEqual(_select_threshold(reports)["threshold"], 2.0)

    def test_passing_successor_requires_all_six_conditions(self) -> None:
        result = evaluate_successor(self._passing_rows())
        self.assertTrue(result["stricter_threshold_successor_preregistration_eligible"])
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

    def test_all_load_envelope_failure_blocks_successor(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "middle" and row["joint_nonloss"]:
                row["candidate_throughput"] = 0.70
                row["throughput_ratio"] = 0.70
                row["log_throughput_ratio"] = math.log(0.70)
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "04_all_load_optimistic_envelope_primary_and_pair_floors"
            ]
        )

    def test_loo_classifier_effect_failure_blocks_successor(self) -> None:
        rows = copy.deepcopy(self._passing_rows())
        safe_rows = [row for row in rows if row["joint_nonloss"]]
        for row in safe_rows:
            row["log_qpr_ratio"] = math.log(0.89)
        safe_rows[0]["log_qpr_ratio"] = math.log(1.5)
        result = evaluate_successor(rows)
        self.assertFalse(
            result["conditions"][
                "06_classifier_and_dual_effect_floors_survive_every_loo"
            ]
        )


if __name__ == "__main__":
    unittest.main()
