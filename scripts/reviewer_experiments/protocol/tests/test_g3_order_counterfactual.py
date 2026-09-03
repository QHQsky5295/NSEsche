from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol.g3_order_counterfactual import (
    _select_g1_runs,
    _select_g2_runs,
)


def _run(seed: str, topology: str, load: str, candidate: str = "ready_order") -> dict:
    return {
        "method": "sche_nash",
        "seed": seed,
        "cluster": {"node_count": 20, "topology": topology},
        "workload": {"request_freq": load},
        "metadata": {"m1_operational_candidate": candidate},
    }


class SourceSelectionTests(unittest.TestCase):
    def test_g1_selects_complete_q_bank_in_seed_order(self) -> None:
        runs = [
            _run(f"Q{index:02d}", "homogeneous", "low")
            for index in reversed(range(61, 81))
        ]
        runs.append(_run("Q61", "heterogeneous", "low"))
        selected = _select_g1_runs({"runs": runs})
        self.assertEqual(
            [run["seed"] for run in selected],
            [f"Q{index:02d}" for index in range(61, 81)],
        )

    def test_g2_selects_only_c0_complete_six_cells(self) -> None:
        runs = [
            _run(f"D{index:02d}", topology, load)
            for topology in ("heterogeneous", "homogeneous")
            for load in ("high", "middle", "low")
            for index in reversed(range(66, 71))
        ]
        runs.append(_run("D66", "homogeneous", "low", "ready_warm_init"))
        selected = _select_g2_runs({"runs": runs})
        self.assertEqual(len(selected), 30)
        self.assertTrue(
            all(
                run["metadata"]["m1_operational_candidate"] == "ready_order"
                for run in selected
            )
        )

    def test_incomplete_source_bank_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly the 30"):
            _select_g2_runs({"runs": [_run("D66", "homogeneous", "low")]})


if __name__ == "__main__":
    unittest.main()
