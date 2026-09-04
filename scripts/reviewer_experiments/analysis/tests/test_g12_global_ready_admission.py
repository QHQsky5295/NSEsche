from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.g12_global_ready_admission import (
    evaluate_gate,
)
from scripts.reviewer_experiments.protocol.g12_global_ready_admission import (
    G12_CANDIDATE,
    G12_CONTROL,
    G12_EFFECTIVE_METHODS,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G12_GLOBAL_READY_ADMISSION_SEEDS,
)


class G12GlobalReadyAdmissionGateTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        throughput = {G12_CONTROL: 1.00, G12_CANDIDATE: 1.10}
        qpr = {G12_CONTROL: 0.040, G12_CANDIDATE: 0.050}
        latency = {G12_CONTROL: 10.0, G12_CANDIDATE: 9.0}
        completion = {G12_CONTROL: 0.80, G12_CANDIDATE: 0.85}
        rows = []
        ordinal = 0
        for load in FORMAL_E1_LOADS:
            for seed in G12_GLOBAL_READY_ADMISSION_SEEDS:
                for method in G12_EFFECTIVE_METHODS:
                    ordinal += 1
                    candidate = method == G12_CANDIDATE
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
                            "placement_policy_wall_mean_ns": 120.0
                            if candidate
                            else 100.0,
                            "g12_activation_pass": True,
                            "g12_activation_issues": [],
                            "deferred_feasible_players_total": 3 if candidate else 0,
                            "readiness_violations": 0,
                            "feasibility_violations": 0,
                            "legacy_order_violations": 0,
                            "prefix_violations": 0,
                            "bound_violations": 0,
                            "dispatch_set_violations": 0,
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
        self.assertEqual(result["selected_candidate"], G12_CANDIDATE)
        self.assertTrue(result["candidate_development_qualified"])
        report = self._candidate_report(result)
        self.assertEqual(len(report["conditions"]), 9)
        self.assertTrue(all(report["conditions"].values()))

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
                and row["effective_method"] == G12_CANDIDATE
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
            and row["seed"] == G12_GLOBAL_READY_ADMISSION_SEEDS[0]
            and row["effective_method"] == G12_CANDIDATE
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
            G12_GLOBAL_READY_ADMISSION_SEEDS, [2.0, 1.01, 1.01, 1.01, 0.40]
        ):
            row = next(
                row
                for row in rows
                if row["load"] == "high"
                and row["seed"] == seed
                and row["effective_method"] == G12_CANDIDATE
            )
            row["throughput_requests_per_ms"] = value
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"]["05_every_leave_one_seed_out_mean_difference_positive"]
        )

    def test_completion_and_latency_gate_is_joint_and_directional(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "low" and row["effective_method"] == G12_CANDIDATE:
                row["completion_ratio"] = 0.79
                row["latency_mean_ms"] = 10.1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "06_completion_not_below_and_latency_below_control_each_load"
            ]
        )

    def test_activation_requires_three_positive_deferred_seeds_each_load(self) -> None:
        rows = self._passing_rows()
        changed = 0
        for row in rows:
            if (
                row["load"] == "middle"
                and row["effective_method"] == G12_CANDIDATE
                and changed < 3
            ):
                row["deferred_feasible_players_total"] = 0
                changed += 1
        report = self._candidate_report(evaluate_gate(rows))
        self.assertFalse(
            report["conditions"][
                "07_global_ready_activation_and_six_zero_violation_contracts"
            ]
        )

    def test_each_zero_violation_contract_fails_closed(self) -> None:
        for field in (
            "readiness_violations",
            "feasibility_violations",
            "legacy_order_violations",
            "prefix_violations",
            "bound_violations",
            "dispatch_set_violations",
        ):
            rows = self._passing_rows()
            candidate = next(
                row for row in rows if row["effective_method"] == G12_CANDIDATE
            )
            candidate[field] = 1
            report = self._candidate_report(evaluate_gate(rows))
            self.assertFalse(
                report["conditions"][
                    "07_global_ready_activation_and_six_zero_violation_contracts"
                ],
                field,
            )

    def test_runtime_and_policy_overhead_gates_fail_closed(self) -> None:
        rows = self._passing_rows()
        rows[0]["nash_runtime_pass"] = False
        for row in rows:
            if row["load"] == "middle" and row["effective_method"] == G12_CANDIDATE:
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

    def test_paired_report_retains_signed_values_sd_interval_and_factorization(
        self,
    ) -> None:
        rows = self._passing_rows()
        first = next(
            row
            for row in rows
            if row["load"] == "low"
            and row["seed"] == G12_GLOBAL_READY_ADMISSION_SEEDS[0]
            and row["effective_method"] == G12_CANDIDATE
        )
        first["throughput_requests_per_ms"] = 0.90
        first["qpr"] = 0.90 / (
            first["latency_mean_ms"] * first["cost_per_completed_request"]
        )
        result = evaluate_gate(rows)
        summary = next(
            row
            for row in result["paired_summaries"]
            if row["load"] == "low" and row["metric"] == "throughput_requests_per_ms"
        )
        self.assertTrue(any(item["value"] < 0.0 for item in summary["values"]))
        self.assertIsNotNone(summary["sd"])
        self.assertEqual(len(summary["descriptive_paired_95pct_t_interval"]), 2)
        self.assertTrue(
            all(
                row["qpr_factor_identity_absolute_error"] is not None
                and row["qpr_factor_identity_absolute_error"] < 1.0e-12
                for row in result["paired_rows"]
            )
        )


if __name__ == "__main__":
    unittest.main()
