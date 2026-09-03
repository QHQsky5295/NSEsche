from __future__ import annotations

import math
import unittest

from scripts.reviewer_experiments.analysis.g3_postfail_diagnosis import (
    _adjust_family,
    _loo_sign_stable,
    _pair_row,
    _spearman_row,
    _t_summary,
)


def run_row(*, scale: float, seed: str = "D71") -> dict[str, object]:
    throughput = 2.0 * scale
    latency = 4.0 / scale
    cost = 5.0 / scale
    qpr = throughput / (latency * cost)
    row: dict[str, object] = {
        "run_id": f"run-{scale}",
        "seed": seed,
        "load": "low",
        "topology": "homogeneous",
        "method": "sche_nash",
        "candidate": "ready_pne_envelope_first",
        "throughput_requests_per_ms": throughput,
        "latency_mean_ms": latency,
        "cost_per_completed_request": cost,
        "qpr": qpr,
        "log_throughput": math.log(throughput),
        "log_latency": math.log(latency),
        "log_cost": math.log(cost),
        "log_qpr": math.log(qpr),
        "intervention_active_window_share": 0.5,
        "selected_cold_or_nonrunning_share_active_mean": 0.25,
    }
    for field in (
        "completion_ratio",
        "queue_area_per_arrival",
        "starting_container_frames_per_arrival",
        "ready_unscheduled_tasks_mean",
        "running_containers_mean",
        "node_cpu_utilization_mean_mean",
        "cross_node_placement_ratio_active_mean",
    ):
        row[field] = scale
    return row


class G3PostfailDiagnosisTests(unittest.TestCase):
    def test_qpr_log_identity_is_exact(self) -> None:
        treatment = run_row(scale=2.0)
        control = run_row(scale=1.0)
        control["candidate"] = "ready_order"
        result = _pair_row(treatment, control, "candidate_vs_c0")
        self.assertAlmostEqual(result["identity_residual"], 0.0, places=12)
        expected = math.log(2.0) * 3.0
        self.assertAlmostEqual(result["delta_log_qpr"], expected, places=12)
        self.assertAlmostEqual(result["throughput_contribution"], math.log(2.0))
        self.assertAlmostEqual(result["latency_contribution"], math.log(2.0))
        self.assertAlmostEqual(result["cost_contribution"], math.log(2.0))

    def test_t_summary_retains_all_signs(self) -> None:
        result = _t_summary([-2.0, -1.0, 0.0, 1.0, 2.0])
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["negative"], 2)
        self.assertEqual(result["neutral"], 1)
        self.assertEqual(result["positive"], 2)
        self.assertAlmostEqual(result["mean"], 0.0)

    def test_spearman_and_leave_one_seed_out_are_run_level(self) -> None:
        rows = []
        for seed_index, seed in enumerate(("D71", "D72", "D73", "D74", "D75")):
            for cell_index in range(6):
                value = seed_index * 6 + cell_index
                rows.append({"seed": seed, "x": value, "y": value * 2.0 + 1.0})
        result = _spearman_row(rows, "x", "y")
        self.assertEqual(result["n"], 30)
        self.assertAlmostEqual(result["rho"], 1.0)
        self.assertEqual(len(result["leave_one_seed_out"]), 5)
        self.assertTrue(_loo_sign_stable(result))

    def test_holm_counts_undefined_test_in_family(self) -> None:
        rows = [
            {"nominal_p": 0.01},
            {"nominal_p": 0.04},
            {"nominal_p": None},
        ]
        _adjust_family(rows, alpha=0.10)
        self.assertAlmostEqual(rows[0]["holm_adjusted_p"], 0.03)
        self.assertAlmostEqual(rows[1]["holm_adjusted_p"], 0.08)
        self.assertEqual(rows[2]["holm_adjusted_p"], 1.0)


if __name__ == "__main__":
    unittest.main()
