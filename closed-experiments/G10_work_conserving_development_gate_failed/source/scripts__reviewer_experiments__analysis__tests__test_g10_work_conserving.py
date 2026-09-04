from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.g10_work_conserving import evaluate_gate
from scripts.reviewer_experiments.protocol.g10_work_conserving import (
    G10_CANDIDATES,
    G10_CONTROL,
    G10_EFFECTIVE_METHODS,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G10_WORK_CONSERVING_SEEDS,
)


class G10WorkConservingGateTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        throughput = {
            G10_CONTROL: 1.00,
            G10_CANDIDATES[0]: 1.10,
            G10_CANDIDATES[1]: 1.20,
        }
        qpr = {
            G10_CONTROL: 0.040,
            G10_CANDIDATES[0]: 0.050,
            G10_CANDIDATES[1]: 0.060,
        }
        latency = {
            G10_CONTROL: 10.0,
            G10_CANDIDATES[0]: 9.0,
            G10_CANDIDATES[1]: 8.0,
        }
        completion = {
            G10_CONTROL: 0.80,
            G10_CANDIDATES[0]: 0.85,
            G10_CANDIDATES[1]: 0.90,
        }
        rows = []
        ordinal = 0
        for load in FORMAL_E1_LOADS:
            for seed in G10_WORK_CONSERVING_SEEDS:
                for method in G10_EFFECTIVE_METHODS:
                    ordinal += 1
                    is_c1 = method == G10_CANDIDATES[0]
                    is_c2 = method == G10_CANDIDATES[1]
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
                                110.0 if is_c1 else 120.0 if is_c2 else 100.0
                            ),
                            "ready_set_contract_pass": not is_c2,
                            "frontier_contract_pass": True if is_c2 else None,
                            "g10_activation_issues": [],
                            "ready_omissions_total": 0,
                            "frontier_bound_violations": 0,
                            "frontier_one_hop_violations": 0,
                            "dispatch_class_violations": 0,
                            "frontier_admitted_total": 3 if is_c2 else 0,
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
    def _candidate_report(result, candidate):
        return next(
            row for row in result["candidate_reports"] if row["candidate"] == candidate
        )

    def test_both_candidates_pass_and_stronger_candidate_is_selected(self) -> None:
        result = evaluate_gate(self._passing_rows())
        self.assertEqual(result["selected_candidate"], G10_CANDIDATES[1])
        self.assertTrue(result["candidate_development_qualified"])
        for candidate in G10_CANDIDATES:
            report = self._candidate_report(result, candidate)
            self.assertEqual(len(report["conditions"]), 9)
            self.assertTrue(all(report["conditions"].values()))

    def test_exact_selection_tie_prefers_simpler_c1(self) -> None:
        rows = self._passing_rows()
        c1 = {
            (row["load"], row["seed"]): row
            for row in rows
            if row["effective_method"] == G10_CANDIDATES[0]
        }
        for row in rows:
            if row["effective_method"] != G10_CANDIDATES[1]:
                continue
            source = c1[(row["load"], row["seed"])]
            for field in (
                "throughput_requests_per_ms",
                "qpr",
                "latency_mean_ms",
                "cost_per_completed_request",
                "completion_ratio",
                "placement_policy_wall_mean_ns",
            ):
                row[field] = source[field]
        result = evaluate_gate(rows)
        self.assertEqual(result["selected_candidate"], G10_CANDIDATES[0])

    def test_zero_completion_is_retained_with_null_qpr_and_fails_both(self) -> None:
        rows = self._passing_rows()
        rows[0]["fixed_completion_count"] = 0
        rows[0]["qpr"] = None
        rows[0]["qpr_nonapplicability_reasons"] = ["zero_completion"]
        result = evaluate_gate(rows)
        self.assertEqual(len(result["positive_completion_and_qpr_rows"]), 45)
        self.assertFalse(
            result["population_integrity"]["positive_completion_defined_qpr"]
        )
        self.assertIsNone(result["selected_candidate"])
        for candidate in G10_CANDIDATES:
            report = self._candidate_report(result, candidate)
            self.assertFalse(
                report["conditions"][
                    "01_all_45_unique_paired_qc_positive_defined_qpr_one_runtime"
                ]
            )

    def test_three_of_five_joint_win_threshold_is_not_weakened(self) -> None:
        rows = self._passing_rows()
        changed = 0
        for row in rows:
            if (
                row["load"] == "low"
                and row["effective_method"] == G10_CANDIDATES[0]
                and changed < 3
            ):
                row["throughput_requests_per_ms"] = 0.90
                row["qpr"] = 0.035
                changed += 1
        report = self._candidate_report(evaluate_gate(rows), G10_CANDIDATES[0])
        self.assertFalse(
            report["conditions"][
                "03_at_least_3_of_5_paired_throughput_qpr_joint_wins_each_load"
            ]
        )

    def test_per_seed_floor_accepts_exact_boundary_and_rejects_below(self) -> None:
        rows = self._passing_rows()
        target = next(
            row
            for row in rows
            if row["load"] == "middle"
            and row["seed"] == G10_WORK_CONSERVING_SEEDS[0]
            and row["effective_method"] == G10_CANDIDATES[0]
        )
        target["throughput_requests_per_ms"] = 0.80
        target["qpr"] = 0.032
        report = self._candidate_report(evaluate_gate(rows), G10_CANDIDATES[0])
        self.assertTrue(
            report["conditions"]["04_every_seed_throughput_and_qpr_ratio_at_least_0_80"]
        )
        target["throughput_requests_per_ms"] = 0.799
        report = self._candidate_report(evaluate_gate(rows), G10_CANDIDATES[0])
        self.assertFalse(
            report["conditions"]["04_every_seed_throughput_and_qpr_ratio_at_least_0_80"]
        )

    def test_leave_one_seed_out_gate_detects_single_seed_dependence(self) -> None:
        rows = self._passing_rows()
        values = [2.0, 1.01, 1.01, 1.01, 0.40]
        for seed, value in zip(G10_WORK_CONSERVING_SEEDS, values):
            row = next(
                row
                for row in rows
                if row["load"] == "high"
                and row["seed"] == seed
                and row["effective_method"] == G10_CANDIDATES[0]
            )
            row["throughput_requests_per_ms"] = value
        report = self._candidate_report(evaluate_gate(rows), G10_CANDIDATES[0])
        self.assertFalse(
            report["conditions"]["05_every_leave_one_seed_out_mean_difference_positive"]
        )

    def test_completion_and_latency_gate_is_joint_and_directional(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "low" and row["effective_method"] == G10_CANDIDATES[0]:
                row["completion_ratio"] = 0.79
                row["latency_mean_ms"] = 10.1
        report = self._candidate_report(evaluate_gate(rows), G10_CANDIDATES[0])
        self.assertFalse(
            report["conditions"][
                "06_completion_not_below_and_latency_below_control_each_load"
            ]
        )

    def test_c1_ready_set_and_c2_frontier_activation_fail_closed(self) -> None:
        rows = self._passing_rows()
        c1 = next(row for row in rows if row["effective_method"] == G10_CANDIDATES[0])
        c1["ready_set_contract_pass"] = False
        for row in rows:
            if row["effective_method"] == G10_CANDIDATES[1]:
                row["frontier_admitted_total"] = 0
        result = evaluate_gate(rows)
        for candidate in G10_CANDIDATES:
            report = self._candidate_report(result, candidate)
            self.assertFalse(
                report["conditions"]["07_work_conserving_activation_and_integrity"]
            )

    def test_runtime_and_policy_overhead_gates_fail_closed(self) -> None:
        rows = self._passing_rows()
        rows[0]["nash_runtime_pass"] = False
        for row in rows:
            if row["load"] == "middle" and row["effective_method"] == G10_CANDIDATES[0]:
                row["placement_policy_wall_mean_ns"] = 151.0
        report = self._candidate_report(evaluate_gate(rows), G10_CANDIDATES[0])
        self.assertFalse(
            report["conditions"][
                "08_strict_eq15_pne_reference_dispatch_runtime_identity"
            ]
        )
        self.assertFalse(
            report["conditions"]["09_mean_policy_wall_ratio_at_most_1_50_each_load"]
        )

    def test_missing_run_and_duplicate_spec_fail_population(self) -> None:
        rows = copy.deepcopy(self._passing_rows())
        rows.pop()
        rows[0]["run_spec_hash"] = rows[1]["run_spec_hash"]
        result = evaluate_gate(rows)
        self.assertFalse(result["population_integrity"]["exact_matrix"])

    def test_paired_report_retains_signed_values_sd_and_interval(self) -> None:
        rows = self._passing_rows()
        first = next(
            row
            for row in rows
            if row["load"] == "low"
            and row["seed"] == G10_WORK_CONSERVING_SEEDS[0]
            and row["effective_method"] == G10_CANDIDATES[0]
        )
        first["throughput_requests_per_ms"] = 0.90
        result = evaluate_gate(rows)
        summary = next(
            row
            for row in result["paired_summaries"]
            if row["candidate"] == G10_CANDIDATES[0]
            and row["load"] == "low"
            and row["metric"] == "throughput_requests_per_ms"
        )
        self.assertTrue(any(item["value"] < 0.0 for item in summary["values"]))
        self.assertIsNotNone(summary["sd"])
        self.assertEqual(len(summary["descriptive_paired_95pct_t_interval"]), 2)


if __name__ == "__main__":
    unittest.main()
