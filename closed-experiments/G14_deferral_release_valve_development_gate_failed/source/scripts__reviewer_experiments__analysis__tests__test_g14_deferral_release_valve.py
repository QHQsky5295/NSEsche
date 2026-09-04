from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.g14_deferral_release_valve import (
    ALL_TELEMETRY_VIOLATION_FIELDS,
    DEFERRAL_RELEASE_VALVE_SCHEMA,
    ZERO_VIOLATION_FIELDS,
    _release_valve_telemetry,
    evaluate_gate,
)
from scripts.reviewer_experiments.protocol.g14_deferral_release_valve import (
    G14_CANDIDATE,
    G14_CONTROL,
    G14_EFFECTIVE_METHODS,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G14_DEFERRAL_RELEASE_VALVE_SEEDS,
)


class G14DeferralReleaseValveGateTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        throughput = {G14_CONTROL: 1.00, G14_CANDIDATE: 1.10}
        qpr = {G14_CONTROL: 0.040, G14_CANDIDATE: 0.050}
        latency = {G14_CONTROL: 10.0, G14_CANDIDATE: 9.0}
        completion = {G14_CONTROL: 0.80, G14_CANDIDATE: 0.85}
        rows = []
        ordinal = 0
        for load in FORMAL_E1_LOADS:
            for seed in G14_DEFERRAL_RELEASE_VALVE_SEEDS:
                for method in G14_EFFECTIVE_METHODS:
                    ordinal += 1
                    candidate = method == G14_CANDIDATE
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
                            "g14_activation_pass": True,
                            "g14_activation_issues": [],
                            "first_overflow_bounded_window_count": (
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
                            "bound_violations": 0,
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

    def test_candidate_passes_all_nine_frozen_conditions(self) -> None:
        result = evaluate_gate(self._passing_rows())
        self.assertEqual(result["selected_candidate"], G14_CANDIDATE)
        self.assertTrue(result["candidate_development_qualified"])
        report = self._candidate_report(result)
        self.assertEqual(len(report["conditions"]), 9)
        self.assertTrue(all(report["conditions"].values()))
        self.assertTrue(report["persistent_release_summary"]["passed"])
        self.assertEqual(
            set(
                report["persistent_release_summary"][
                    "persistent_overflow_release_loads"
                ]
            ),
            set(FORMAL_E1_LOADS),
        )

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

    def test_three_of_five_joint_win_threshold_is_not_weakened(self) -> None:
        rows = self._passing_rows()
        changed = 0
        for row in rows:
            if (
                row["load"] == "low"
                and row["effective_method"] == G14_CANDIDATE
                and changed < 3
            ):
                row["throughput_requests_per_ms"] = 0.90
                row["qpr"] = 0.035
                changed += 1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "03_at_least_3_of_5_paired_throughput_qpr_joint_wins_each_load"
            ]
        )

    def test_per_seed_floor_accepts_boundary_and_rejects_below(self) -> None:
        rows = self._passing_rows()
        target = next(
            row
            for row in rows
            if row["load"] == "middle"
            and row["seed"] == G14_DEFERRAL_RELEASE_VALVE_SEEDS[0]
            and row["effective_method"] == G14_CANDIDATE
        )
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

    def test_leave_one_seed_out_detects_single_seed_dependence(self) -> None:
        rows = self._passing_rows()
        for seed, value in zip(
            G14_DEFERRAL_RELEASE_VALVE_SEEDS, [2.0, 1.01, 1.01, 1.01, 0.40]
        ):
            row = next(
                row
                for row in rows
                if row["load"] == "high"
                and row["seed"] == seed
                and row["effective_method"] == G14_CANDIDATE
            )
            row["throughput_requests_per_ms"] = value
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"]["05_every_leave_one_seed_out_mean_difference_positive"]
        )

    def test_completion_and_latency_gate_is_joint_and_directional(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "low" and row["effective_method"] == G14_CANDIDATE:
                row["completion_ratio"] = 0.79
                row["latency_mean_ms"] = 10.1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "06_completion_not_below_and_latency_below_control_each_load"
            ]
        )

    def test_activation_requires_bounded_first_overflow_in_every_load(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "middle" and row["effective_method"] == G14_CANDIDATE:
                row["first_overflow_bounded_window_count"] = 0
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "07_release_valve_activation_and_seven_zero_violation_contracts"
            ]
        )
        middle = next(
            row for row in report["activation_rows"] if row["load"] == "middle"
        )
        self.assertEqual(middle["first_overflow_bounded_seeds"], 0)

    def test_persistent_release_requires_three_runs_across_two_loads(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["effective_method"] == G14_CANDIDATE:
                row["persistent_overflow_release_window_count"] = 0
        candidates = [row for row in rows if row["effective_method"] == G14_CANDIDATE]
        for row in candidates[:3]:
            row["persistent_overflow_release_window_count"] = 1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(report["persistent_release_summary"]["passed"])
        target = next(row for row in candidates if row["load"] == "middle")
        target["persistent_overflow_release_window_count"] = 1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertTrue(report["persistent_release_summary"]["passed"])

    def test_long_deferral_and_each_zero_contract_fail_closed(self) -> None:
        rows = self._passing_rows()
        candidate = next(
            row for row in rows if row["effective_method"] == G14_CANDIDATE
        )
        candidate["longest_positive_deferral_episode_windows"] = 2
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "07_release_valve_activation_and_seven_zero_violation_contracts"
            ]
        )
        for field in ZERO_VIOLATION_FIELDS:
            rows = self._passing_rows()
            candidate = next(
                row for row in rows if row["effective_method"] == G14_CANDIDATE
            )
            candidate[field] = 1
            report = self._candidate_report(evaluate_gate(rows))
            self.assertFalse(
                report["conditions"][
                    "07_release_valve_activation_and_seven_zero_violation_contracts"
                ],
                field,
            )

    def test_runtime_and_policy_overhead_gates_fail_closed(self) -> None:
        rows = self._passing_rows()
        rows[0]["nash_runtime_pass"] = False
        for row in rows:
            if row["load"] == "middle" and row["effective_method"] == G14_CANDIDATE:
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

    def test_paired_report_restores_g14_seed_and_candidate_labels(self) -> None:
        result = evaluate_gate(self._passing_rows())
        self.assertEqual(result["candidate_reports"][0]["candidate"], G14_CANDIDATE)
        self.assertEqual(
            {row["seed"] for row in result["paired_rows"]},
            set(G14_DEFERRAL_RELEASE_VALVE_SEEDS),
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
        deferred: int,
    ) -> dict[str, object]:
        return {
            "schema": DEFERRAL_RELEASE_VALVE_SCHEMA,
            "dependency_ready_candidates": feasible + 2,
            "feasible_ready_candidates": feasible,
            "configured_node_count": 20,
            "admission_limit": admitted,
            "admitted_players": admitted,
            "deferred_feasible_players": deferred,
            "candidate_order_hash": 11,
            "admitted_order_hash": 11 if admitted == feasible else 12,
            "current_overflow": feasible > 20,
            "valve_open_before": before,
            "valve_open_after": after,
            "admission_mode": mode,
            "admitted_min_arrival_frame": 1 if admitted else None,
            "admitted_max_arrival_frame": 2 if admitted else None,
            **{field: 0 for field in ALL_TELEMETRY_VIOLATION_FIELDS},
        }

    def _valid_telemetry_records(self):
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
        return [
            (index, row, int(row["admitted_players"]))
            for index, row in enumerate(telemetry)
        ]

    def test_release_valve_state_machine_accepts_exact_sequence(self) -> None:
        result = _release_valve_telemetry(self._valid_telemetry_records(), 20)
        self.assertTrue(result["g14_activation_pass"])
        self.assertEqual(result["first_overflow_bounded_window_count"], 2)
        self.assertEqual(result["persistent_overflow_release_window_count"], 1)
        self.assertEqual(result["post_overflow_reset_window_count"], 1)
        self.assertEqual(result["longest_positive_deferral_episode_windows"], 1)
        self.assertTrue(
            all(result[field] == 0 for field in ALL_TELEMETRY_VIOLATION_FIELDS)
        )

    def test_release_valve_state_drift_and_adjacent_deferral_fail_closed(self) -> None:
        records = self._valid_telemetry_records()
        records[2][1]["valve_open_before"] = False
        records[2][1]["deferred_feasible_players"] = 1
        result = _release_valve_telemetry(records, 20)
        self.assertFalse(result["g14_activation_pass"])
        self.assertGreaterEqual(result["longest_positive_deferral_episode_windows"], 2)
        self.assertTrue(result["g14_activation_issues"])


if __name__ == "__main__":
    unittest.main()
