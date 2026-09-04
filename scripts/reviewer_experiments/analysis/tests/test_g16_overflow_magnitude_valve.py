from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.g16_overflow_magnitude_valve import (
    OVERFLOW_MAGNITUDE_RELEASE_VALVE_SCHEMA,
    ZERO_VIOLATION_FIELDS,
    _overflow_magnitude_telemetry,
    evaluate_gate,
)
from scripts.reviewer_experiments.protocol.g16_overflow_magnitude_valve import (
    G16_CANDIDATE,
    G16_CONTROL,
    G16_EFFECTIVE_METHODS,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS,
)


class G16OverflowMagnitudeValveGateTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        throughput = {G16_CONTROL: 1.00, G16_CANDIDATE: 1.10}
        qpr = {G16_CONTROL: 0.040, G16_CANDIDATE: 0.050}
        latency = {G16_CONTROL: 10.0, G16_CANDIDATE: 10.4}
        completion = {G16_CONTROL: 0.80, G16_CANDIDATE: 0.85}
        rows = []
        ordinal = 0
        for load in FORMAL_E1_LOADS:
            for seed in G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS:
                for method in G16_EFFECTIVE_METHODS:
                    ordinal += 1
                    candidate = method == G16_CANDIDATE
                    cost = throughput[method] / (latency[method] * qpr[method])
                    rows.append(
                        {
                            "run_id": f"run-{ordinal}",
                            "run_spec_hash": f"{ordinal:064x}",
                            "load": load,
                            "seed": seed,
                            "effective_method": method,
                            "workload_tape_sha256": f"{load}-{seed}",
                            "qc_valid": True,
                            "fixed_completion_count": 100,
                            "completion_ratio": completion[method],
                            "throughput_requests_per_ms": throughput[method],
                            "latency_mean_ms": latency[method],
                            "cost_per_completed_request": cost,
                            "qpr": qpr[method],
                            "qpr_nonapplicability_reasons": [],
                            "placement_policy_wall_mean_ns": (
                                120.0 if candidate else 100.0
                            ),
                            "g16_activation_pass": True,
                            "g16_activation_issues": [],
                            "first_overflow_magnitude_bounded_window_count": (
                                1 if candidate else 0
                            ),
                            "first_overflow_below_magnitude_release_window_count": (
                                1 if candidate else 0
                            ),
                            "persistent_overflow_release_window_count": (
                                1 if candidate else 0
                            ),
                            "longest_positive_deferral_episode_windows": (
                                1 if candidate else 0
                            ),
                            "deferred_feasible_players_total": 3 if candidate else 0,
                            **{field: 0 for field in ZERO_VIOLATION_FIELDS},
                            "nash_runtime_pass": True,
                            "nash_runtime_issues": [],
                            "runtime_identity_pass": True,
                            "runtime_identity_issues": [],
                            "runtime_binary_sha256": "a" * 64,
                            "runtime_git_commit": "b" * 40,
                        }
                    )
        return rows

    @staticmethod
    def _candidate_report(result):
        return result["candidate_reports"][0]

    def _candidate(self, rows, load, seed):
        return next(
            row
            for row in rows
            if row["load"] == load
            and row["seed"] == seed
            and row["effective_method"] == G16_CANDIDATE
        )

    def test_candidate_passes_all_nine_frozen_conditions(self) -> None:
        result = evaluate_gate(self._passing_rows())
        self.assertEqual(result["selected_candidate"], G16_CANDIDATE)
        self.assertTrue(result["candidate_development_qualified"])
        report = self._candidate_report(result)
        self.assertEqual(len(report["conditions"]), 9)
        self.assertTrue(all(report["conditions"].values()))
        self.assertTrue(report["below_threshold_release_summary"]["passed"])
        self.assertTrue(report["persistent_release_summary"]["passed"])

    def test_zero_completion_is_retained_with_null_qpr_and_fails(self) -> None:
        rows = self._passing_rows()
        rows[0]["fixed_completion_count"] = 0
        rows[0]["qpr"] = None
        rows[0]["qpr_nonapplicability_reasons"] = ["zero_completion"]
        result = evaluate_gate(rows)
        self.assertEqual(len(result["positive_completion_and_qpr_rows"]), 30)
        self.assertFalse(
            result["population_integrity"]["positive_completion_defined_qpr"]
        )
        self.assertIsNone(result["selected_candidate"])

    def test_one_joint_win_and_four_joint_nonlosses_pass(self) -> None:
        rows = self._passing_rows()
        for seed in G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS[1:]:
            row = self._candidate(rows, "low", seed)
            row["throughput_requests_per_ms"] = 1.00
            row["qpr"] = 0.040
        report = self._candidate_report(evaluate_gate(rows))
        low = next(row for row in report["paired_win_rows"] if row["load"] == "low")
        self.assertEqual(low["joint_wins"], 1)
        self.assertEqual(low["joint_nonlosses"], 5)
        self.assertTrue(
            report["conditions"][
                "03_at_least_1_joint_win_and_4_joint_nonlosses_each_load"
            ]
        )

    def test_two_joint_losses_fail_nonloss_gate(self) -> None:
        rows = self._passing_rows()
        for seed in G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS[:2]:
            row = self._candidate(rows, "low", seed)
            row["throughput_requests_per_ms"] = 0.99
            row["qpr"] = 0.039
        report = self._candidate_report(evaluate_gate(rows))
        low = next(row for row in report["paired_win_rows"] if row["load"] == "low")
        self.assertEqual(low["joint_nonlosses"], 3)
        self.assertFalse(
            report["conditions"][
                "03_at_least_1_joint_win_and_4_joint_nonlosses_each_load"
            ]
        )

    def test_per_seed_floor_accepts_boundary_and_rejects_below(self) -> None:
        rows = self._passing_rows()
        target = self._candidate(rows, "middle", G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS[0])
        target["throughput_requests_per_ms"] = 0.80
        target["qpr"] = 0.032
        report = self._candidate_report(evaluate_gate(rows))
        self.assertTrue(
            report["conditions"]["04_every_seed_throughput_and_qpr_ratio_at_least_0_80"]
        )
        target["throughput_requests_per_ms"] = 0.799
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"]["04_every_seed_throughput_and_qpr_ratio_at_least_0_80"]
        )

    def test_leave_one_out_allows_one_zero_but_not_one_negative(self) -> None:
        rows = self._passing_rows()
        differences = [0.50, 0.25, 0.25, -0.25, -0.25]
        for seed, difference in zip(G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS, differences):
            self._candidate(rows, "high", seed)["throughput_requests_per_ms"] = (
                1.0 + difference
            )
        report = self._candidate_report(evaluate_gate(rows))
        high_throughput = next(
            row
            for row in report["leave_one_seed_out_rows"]
            if row["load"] == "high" and row["metric"] == "throughput_requests_per_ms"
        )
        self.assertEqual(high_throughput["nonnegative_count"], 5)
        self.assertEqual(high_throughput["strictly_positive_count"], 4)
        self.assertTrue(high_throughput["passed"])

        self._candidate(rows, "high", G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS[3])[
            "throughput_requests_per_ms"
        ] = 0.74
        report = self._candidate_report(evaluate_gate(rows))
        high_throughput = next(
            row
            for row in report["leave_one_seed_out_rows"]
            if row["load"] == "high" and row["metric"] == "throughput_requests_per_ms"
        )
        self.assertFalse(high_throughput["passed"])
        self.assertFalse(
            report["conditions"][
                "05_every_leave_one_seed_out_nonnegative_and_at_least_4_positive"
            ]
        )

    def test_completion_and_latency_accept_exact_1_05_boundary(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "low" and row["effective_method"] == G16_CANDIDATE:
                row["completion_ratio"] = 0.80
                row["latency_mean_ms"] = 10.5
        report = self._candidate_report(evaluate_gate(rows))
        low = next(
            row for row in report["completion_latency_rows"] if row["load"] == "low"
        )
        self.assertAlmostEqual(low["latency_ratio"], 1.05)
        self.assertTrue(low["passed"])
        for row in rows:
            if row["load"] == "low" and row["effective_method"] == G16_CANDIDATE:
                row["latency_mean_ms"] = 10.501
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "06_completion_not_below_and_latency_ratio_at_most_1_05_each_load"
            ]
        )

    def test_activation_requires_material_bounded_seed_in_every_load(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "middle" and row["effective_method"] == G16_CANDIDATE:
                row["first_overflow_magnitude_bounded_window_count"] = 0
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "07_magnitude_valve_activation_and_nine_zero_violation_contracts"
            ]
        )

    def test_cross_load_release_evidence_requires_three_runs_and_two_loads(
        self,
    ) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["effective_method"] == G16_CANDIDATE:
                row["first_overflow_below_magnitude_release_window_count"] = 0
        low_candidates = [
            row
            for row in rows
            if row["load"] == "low" and row["effective_method"] == G16_CANDIDATE
        ]
        for row in low_candidates[:3]:
            row["first_overflow_below_magnitude_release_window_count"] = 1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(report["below_threshold_release_summary"]["passed"])
        target = self._candidate(rows, "middle", G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS[0])
        target["first_overflow_below_magnitude_release_window_count"] = 1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertTrue(report["below_threshold_release_summary"]["passed"])

    def test_each_zero_violation_contract_and_long_deferral_fail_closed(self) -> None:
        for field in ZERO_VIOLATION_FIELDS:
            rows = self._passing_rows()
            candidate = next(
                row for row in rows if row["effective_method"] == G16_CANDIDATE
            )
            candidate[field] = 1
            report = self._candidate_report(evaluate_gate(rows))
            self.assertFalse(
                report["conditions"][
                    "07_magnitude_valve_activation_and_nine_zero_violation_contracts"
                ],
                field,
            )
        rows = self._passing_rows()
        next(row for row in rows if row["effective_method"] == G16_CANDIDATE)[
            "longest_positive_deferral_episode_windows"
        ] = 2
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "07_magnitude_valve_activation_and_nine_zero_violation_contracts"
            ]
        )

    def test_runtime_and_policy_overhead_gates_fail_closed(self) -> None:
        rows = self._passing_rows()
        rows[0]["nash_runtime_pass"] = False
        for row in rows:
            if row["load"] == "middle" and row["effective_method"] == G16_CANDIDATE:
                row["placement_policy_wall_mean_ns"] = 151.0
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "08_strict_eq15_pne_reference_dispatch_runtime_identity"
            ]
        )
        self.assertFalse(
            report["conditions"]["09_mean_policy_wall_ratio_at_most_1_50_each_load"]
        )

    def test_missing_run_duplicate_spec_and_unpaired_tape_fail_population(self) -> None:
        rows = copy.deepcopy(self._passing_rows())
        rows.pop()
        rows[0]["run_spec_hash"] = rows[1]["run_spec_hash"]
        rows[2]["workload_tape_sha256"] = "different"
        result = evaluate_gate(rows)
        self.assertFalse(result["population_integrity"]["exact_matrix"])
        self.assertFalse(result["population_integrity"]["paired_tapes"])

    def test_paired_report_restores_g16_seed_and_candidate_labels(self) -> None:
        result = evaluate_gate(self._passing_rows())
        self.assertEqual(result["candidate_reports"][0]["candidate"], G16_CANDIDATE)
        self.assertEqual(
            {row["seed"] for row in result["paired_rows"]},
            set(G16_OVERFLOW_MAGNITUDE_VALVE_SEEDS),
        )
        self.assertTrue(
            all(
                row["qpr_factor_identity_absolute_error"] is not None
                and row["qpr_factor_identity_absolute_error"] < 1.0e-12
                for row in result["paired_rows"]
            )
        )

    @staticmethod
    def _telemetry(
        *,
        feasible: int,
        admitted: int,
        mode: str,
        before: bool,
        after: bool,
        applicable: bool,
        gate_pass: bool,
    ) -> dict[str, object]:
        return {
            "schema": OVERFLOW_MAGNITUDE_RELEASE_VALVE_SCHEMA,
            "dependency_ready_candidates": feasible + 2,
            "feasible_ready_candidates": feasible,
            "configured_node_count": 20,
            "admission_limit": admitted,
            "admitted_players": admitted,
            "deferred_feasible_players": feasible - admitted,
            "candidate_order_hash": 11,
            "admitted_order_hash": 11 if admitted == feasible else 12,
            "current_overflow": feasible > 20,
            "valve_open_before": before,
            "valve_open_after": after,
            "magnitude_gate_applicable": applicable,
            "magnitude_gate_pass": gate_pass,
            "magnitude_threshold_numerator": 5,
            "magnitude_threshold_denominator": 4,
            "magnitude_comparison_lhs": 4 * feasible,
            "magnitude_comparison_rhs": 100,
            "admission_mode": mode,
            "admitted_min_arrival_frame": 1 if admitted else None,
            "admitted_max_arrival_frame": 2 if admitted else None,
            **{field: 0 for field in ZERO_VIOLATION_FIELDS},
        }

    def _valid_telemetry_records(self):
        telemetry = [
            self._telemetry(
                feasible=10,
                admitted=10,
                mode="below_limit",
                before=False,
                after=False,
                applicable=False,
                gate_pass=False,
            ),
            self._telemetry(
                feasible=24,
                admitted=24,
                mode="first_overflow_below_magnitude_release",
                before=False,
                after=True,
                applicable=True,
                gate_pass=False,
            ),
            self._telemetry(
                feasible=30,
                admitted=30,
                mode="persistent_overflow_release",
                before=True,
                after=True,
                applicable=False,
                gate_pass=False,
            ),
            self._telemetry(
                feasible=12,
                admitted=12,
                mode="post_overflow_reset",
                before=True,
                after=False,
                applicable=False,
                gate_pass=False,
            ),
            self._telemetry(
                feasible=25,
                admitted=20,
                mode="first_overflow_magnitude_bounded",
                before=False,
                after=True,
                applicable=True,
                gate_pass=True,
            ),
            self._telemetry(
                feasible=23,
                admitted=23,
                mode="persistent_overflow_release",
                before=True,
                after=True,
                applicable=False,
                gate_pass=False,
            ),
        ]
        return [
            (index, row, int(row["admitted_players"]))
            for index, row in enumerate(telemetry)
        ]

    def test_magnitude_valve_accepts_exact_state_and_boundary_sequence(self) -> None:
        result = _overflow_magnitude_telemetry(self._valid_telemetry_records(), 20)
        self.assertTrue(result["g16_activation_pass"])
        self.assertEqual(
            result["first_overflow_below_magnitude_release_window_count"], 1
        )
        self.assertEqual(result["first_overflow_magnitude_bounded_window_count"], 1)
        self.assertEqual(result["persistent_overflow_release_window_count"], 2)
        self.assertEqual(result["magnitude_gate_applicable_window_count"], 2)
        self.assertEqual(result["magnitude_gate_pass_window_count"], 1)
        self.assertEqual(result["longest_positive_deferral_episode_windows"], 1)
        self.assertTrue(all(result[field] == 0 for field in ZERO_VIOLATION_FIELDS))

    def test_magnitude_comparison_and_state_drift_fail_closed(self) -> None:
        records = self._valid_telemetry_records()
        records[1][1]["magnitude_comparison_lhs"] = 97
        records[2][1]["valve_open_before"] = False
        result = _overflow_magnitude_telemetry(records, 20)
        self.assertFalse(result["g16_activation_pass"])
        self.assertTrue(result["g16_activation_issues"])


if __name__ == "__main__":
    unittest.main()
