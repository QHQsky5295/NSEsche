from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.g9_request_backpressure import evaluate_gate
from scripts.reviewer_experiments.protocol.g9_request_backpressure import (
    G9_CANDIDATE,
    G9_CONTROL,
    G9_EFFECTIVE_METHODS,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    G9_REQUEST_BACKPRESSURE_SEEDS,
)


class G9RequestBackpressureGateTests(unittest.TestCase):
    def _passing_rows(self) -> list[dict[str, object]]:
        throughput = {
            G9_CANDIDATE: 1.30,
            G9_CONTROL: 1.00,
            "load_least": 0.90,
            "sche_FaaSRank": 0.80,
            "sche_Hiku": 0.95,
        }
        qpr = {
            G9_CANDIDATE: 0.060,
            G9_CONTROL: 0.040,
            "load_least": 0.030,
            "sche_FaaSRank": 0.020,
            "sche_Hiku": 0.035,
        }
        rows = []
        ordinal = 0
        for load in FORMAL_E1_LOADS:
            for seed in G9_REQUEST_BACKPRESSURE_SEEDS:
                for method in G9_EFFECTIVE_METHODS:
                    ordinal += 1
                    is_nash = method in (G9_CANDIDATE, G9_CONTROL)
                    is_candidate = method == G9_CANDIDATE
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
                            "throughput_requests_per_ms": throughput[method],
                            "qpr": qpr[method],
                            "qpr_nonapplicability_reasons": [],
                            "placement_policy_wall_mean_ns": (
                                110.0 if is_candidate else 100.0
                            ),
                            "backpressure_activation_pass": (
                                True if is_candidate else None
                            ),
                            "backpressure_activation_issues": [],
                            "over_limit_window_count": 10 if is_candidate else 0,
                            "deferred_positive_window_count": (
                                10 if is_candidate else 0
                            ),
                            "nash_runtime_pass": True if is_nash else None,
                            "nash_runtime_issues": [],
                            "runtime_identity_pass": True,
                            "runtime_identity_issues": [],
                            "runtime_binary_sha256": "a" * 64,
                            "runtime_git_commit": "b" * 40,
                            "active_window_count": 10 if is_nash else None,
                            "strict_pne_active_windows": 10 if is_nash else None,
                            "offline_reference_hit_windows": 10 if is_nash else None,
                        }
                    )
        return rows

    def test_all_ten_conditions_pass(self) -> None:
        result = evaluate_gate(self._passing_rows())
        self.assertTrue(result["candidate_development_qualified"])
        self.assertEqual(len(result["conditions"]), 10)
        self.assertTrue(all(result["conditions"].values()))
        self.assertEqual(result["failure_reasons"], [])

    def test_zero_completion_is_retained_and_fails_defined_qpr(self) -> None:
        rows = self._passing_rows()
        rows[0]["fixed_completion_count"] = 0
        rows[0]["qpr"] = None
        rows[0]["qpr_nonapplicability_reasons"] = ["zero_completion"]
        result = evaluate_gate(rows)
        self.assertFalse(
            result["conditions"]["02_all_75_positive_completion_defined_qpr"]
        )
        self.assertEqual(len(result["positive_completion_and_qpr_rows"]), 75)
        self.assertFalse(result["candidate_development_qualified"])

    def test_control_win_threshold_is_not_weakened(self) -> None:
        rows = self._passing_rows()
        changed = 0
        for row in rows:
            if (
                row["load"] == "low"
                and row["effective_method"] == G9_CANDIDATE
                and changed < 2
            ):
                row["throughput_requests_per_ms"] = 0.90
                changed += 1
        result = evaluate_gate(rows)
        self.assertFalse(
            result["conditions"][
                "05_control_paired_wins_at_least_4_of_5_each_metric_load"
            ]
        )
        summary = next(
            row
            for row in result["paired_summaries"]
            if row["load"] == "low"
            and row["comparator"] == G9_CONTROL
            and row["metric"] == "throughput_requests_per_ms"
        )
        self.assertEqual(summary["n_defined"], 5)
        self.assertTrue(any(item["value"] < 0.0 for item in summary["values"]))

    def test_activation_failure_is_fail_closed(self) -> None:
        rows = self._passing_rows()
        candidate = next(row for row in rows if row["effective_method"] == G9_CANDIDATE)
        candidate["backpressure_activation_pass"] = False
        candidate["backpressure_activation_issues"] = ["not activated"]
        result = evaluate_gate(rows)
        self.assertFalse(
            result["conditions"]["08_request_backpressure_activation_and_integrity"]
        )

    def test_policy_overhead_ratio_is_arithmetic_mean_ratio(self) -> None:
        rows = self._passing_rows()
        for row in rows:
            if row["load"] == "middle" and row["effective_method"] == G9_CANDIDATE:
                row["placement_policy_wall_mean_ns"] = 126.0
        result = evaluate_gate(rows)
        self.assertFalse(
            result["conditions"]["10_mean_policy_wall_ratio_at_most_1_25_each_load"]
        )

    def test_missing_run_and_duplicate_spec_fail_matrix(self) -> None:
        rows = copy.deepcopy(self._passing_rows())
        rows.pop()
        rows[0]["run_spec_hash"] = rows[1]["run_spec_hash"]
        result = evaluate_gate(rows)
        self.assertFalse(result["conditions"]["01_all_75_unique_paired_qc_valid"])


if __name__ == "__main__":
    unittest.main()
