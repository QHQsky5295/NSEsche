from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.reviewer_experiments.analysis.p2_homogeneous import (
    METHOD_LABELS,
    analyze_middle_rows,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_METHODS,
    G1_FORMAL_QUALIFICATION_SEEDS,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
OLD_SPEC = json.loads(
    (
        REPO_ROOT
        / "scripts"
        / "reviewer_experiments"
        / "analysis"
        / "old_fig6_homogeneous_middle_v1.json"
    ).read_text(encoding="utf-8")
)


def _rows(nash_value: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for method_index, method in enumerate(FORMAL_E1_METHODS):
        primary = nash_value if method == "sche_nash" else 10.0 - method_index * 0.5
        for seed_index, seed in enumerate(G1_FORMAL_QUALIFICATION_SEEDS):
            value = primary + seed_index * 0.001
            rows.append(
                {
                    "run_id": f"{method}-{seed}",
                    "run_spec_hash": f"hash-{method}-{seed}",
                    "seed": seed,
                    "topology": "homogeneous",
                    "load": "middle",
                    "method": method,
                    "throughput_requests_per_ms": value,
                    "qpr": value / 100.0,
                    "completion_ratio": 0.9,
                    "latency_mean_ms": 100.0,
                    "cost_per_completed_request": value / (100.0 * (value / 100.0)),
                    "qpr_applicable": True,
                }
            )
    return rows


class P2HomogeneousAnalysisTests(unittest.TestCase):
    def test_confirms_stop_only_when_both_fifth_place_intervals_are_negative(
        self,
    ) -> None:
        result = analyze_middle_rows(
            _rows(1.0), OLD_SPEC, bca_resamples=200, permutation_resamples=1_000
        )
        gate = result["v4_continuation"]
        self.assertEqual(gate["nash_ranks"]["throughput_requests_per_ms"], 10)
        self.assertEqual(gate["nash_ranks"]["qpr"], 10)
        self.assertTrue(gate["possible_stop_branch_entered"])
        self.assertTrue(gate["both_fifth_place_bca_high_strictly_below_zero"])
        self.assertEqual(gate["disposition"], "pause_for_resubmission_value_review")
        self.assertFalse(gate["high_load_directly_authorized"])
        self.assertEqual(len(result["paired_comparisons"]), 18)
        self.assertTrue(result["analysis_gate"]["holm_family_complete"])

    def test_nonbottom_nash_allows_only_separate_high_preregistration(self) -> None:
        result = analyze_middle_rows(
            _rows(9.0), OLD_SPEC, bca_resamples=200, permutation_resamples=1_000
        )
        gate = result["v4_continuation"]
        self.assertLessEqual(gate["nash_ranks"]["throughput_requests_per_ms"], 5)
        self.assertFalse(gate["possible_stop_branch_entered"])
        self.assertEqual(
            gate["disposition"],
            "eligible_for_separate_homogeneous_high_preregistration_after_result_audit",
        )
        self.assertFalse(gate["high_load_directly_authorized"])

    def test_missing_qpr_is_retained_and_blocks_progression(self) -> None:
        rows = _rows(9.0)
        target = next(row for row in rows if row["method"] == "hash")
        target["qpr"] = None
        target["qpr_applicable"] = False
        target["latency_mean_ms"] = None
        target["cost_per_completed_request"] = None
        result = analyze_middle_rows(
            rows, OLD_SPEC, bca_resamples=200, permutation_resamples=1_000
        )
        self.assertEqual(len(result["run_rows"]), 200)
        self.assertFalse(result["analysis_gate"]["all_methods_full_qpr_coverage"])
        self.assertEqual(
            result["v4_continuation"]["disposition"],
            "blocked_incomplete_full_qpr_gate",
        )

    def test_manuscript_order_breaks_exact_mean_ties(self) -> None:
        rows = _rows(9.0)
        for row in rows:
            if row["method"] in {"greedy", "random"}:
                row["throughput_requests_per_ms"] = 10.0
                row["qpr"] = 10.0 / (
                    float(row["latency_mean_ms"])
                    * float(row["cost_per_completed_request"])
                )
        result = analyze_middle_rows(
            rows, OLD_SPEC, bca_resamples=200, permutation_resamples=1_000
        )
        ranks = result["v4_continuation"]["nash_ranks"]
        self.assertIsInstance(ranks["throughput_requests_per_ms"], int)
        summaries = {
            row["method_label"]: row["rank"]
            for row in result["method_summaries"]
            if row["metric"] == "throughput_requests_per_ms"
        }
        self.assertLess(
            summaries[METHOD_LABELS["greedy"]], summaries[METHOD_LABELS["random"]]
        )


if __name__ == "__main__":
    unittest.main()
