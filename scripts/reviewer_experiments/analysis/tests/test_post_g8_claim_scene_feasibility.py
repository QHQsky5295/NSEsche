from __future__ import annotations

import unittest

from scripts.reviewer_experiments.analysis.post_g8_claim_scene_feasibility import (
    CELLS,
    FAMILIES,
    _formal_rows,
    evaluate_candidates,
    summarize,
)


class PostG8ClaimSceneFeasibilityTests(unittest.TestCase):
    def test_summary_supports_five_and_twenty_seed_products(self) -> None:
        five = summarize([1.0, 2.0, 3.0, 4.0, 5.0])
        twenty = summarize([float(index) for index in range(20)])
        self.assertEqual(five["n"], 5)
        self.assertEqual(five["leave_one_seed_out_means"][0], 3.5)
        self.assertEqual(twenty["n"], 20)
        self.assertEqual(len(twenty["leave_one_seed_out_means"]), 20)

    def test_candidate_gate_is_exact_conjunction(self) -> None:
        cell_rows = []
        baseline_rows = []
        passing_name = ("g2", "ready_warm_init")
        for family, config in FAMILIES.items():
            for candidate in config["candidates"]:
                if candidate == config["control"]:
                    continue
                intended = (family, candidate) == passing_name
                for load, topology in CELLS:
                    cell_rows.append(
                        {
                            "family": family,
                            "candidate": candidate,
                            "load": load,
                            "topology": topology,
                            "delta_throughput_mean": 1.0 if intended else -1.0,
                            "delta_qpr_mean": 1.0 if intended else -1.0,
                            "throughput_control_ratio": 1.01 if intended else 0.89,
                            "qpr_control_ratio": 1.01 if intended else 0.89,
                        }
                    )
                for index in range(9):
                    baseline_rows.append(
                        {
                            "family": family,
                            "candidate": candidate,
                            "baseline": f"b{index}",
                            "dual_mean_above": intended,
                            "baseline_within_five_percent_of_either_leader": index == 0,
                            "delta_throughput_positive": 3 if intended else 2,
                            "delta_qpr_positive": 4 if intended else 2,
                            "joint_win_count": 3 if intended else 2,
                            "baseline_mean_throughput": 10.0 - index,
                            "baseline_mean_qpr": 10.0 - index,
                            "delta_throughput_leave_one_seed_out_means": (
                                [1.0] * 5 if intended else [-1.0] * 5
                            ),
                            "delta_qpr_leave_one_seed_out_means": (
                                [1.0] * 5 if intended else [-1.0] * 5
                            ),
                        }
                    )
        result = evaluate_candidates(cell_rows, baseline_rows, {"g2": True, "g3": True})
        self.assertTrue(
            result["existing_candidate_confirmation_preregistration_supported"]
        )
        self.assertEqual(
            result["selected_existing_candidate"],
            {"family": "g2", "candidate": "ready_warm_init"},
        )

        baseline_rows[0]["joint_win_count"] = 2
        result = evaluate_candidates(cell_rows, baseline_rows, {"g2": True, "g3": True})
        self.assertFalse(
            result["existing_candidate_confirmation_preregistration_supported"]
        )

    def test_formal_label_requires_both_primary_ranks(self) -> None:
        methods = ["sche_nash", "leader"] + [f"m{index}" for index in range(8)]
        raw = []
        for method in methods:
            for index in range(20):
                if method == "leader":
                    throughput = 2.0
                    qpr = 2.0
                elif method == "sche_nash":
                    throughput = 1.9
                    qpr = 1.9
                else:
                    throughput = 1.0
                    qpr = 1.0
                raw.append(
                    {
                        "method": method,
                        "seed": f"Q{index}",
                        "throughput_requests_per_ms": throughput,
                        "qpr": qpr,
                        "latency_mean_ms": 10.0,
                        "completion_ratio": 0.9,
                        "cost_per_completed_request": 1.0,
                    }
                )
        rows, labels = _formal_rows({"run_metrics": raw})
        nash = next(row for row in rows if row["method"] == "sche_nash")
        self.assertEqual(nash["throughput_rank"], 2)
        self.assertEqual(nash["qpr_rank"], 2)
        self.assertEqual(labels["formal_homogeneous_low_label"], "not_leading")


if __name__ == "__main__":
    unittest.main()
