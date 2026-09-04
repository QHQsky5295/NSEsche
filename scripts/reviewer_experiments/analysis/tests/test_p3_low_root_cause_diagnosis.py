from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.analysis.p3_low_root_cause_diagnosis import (
    DiagnosisError,
    EXPECTED_WINDOW_COUNT,
    centre_path_row,
    evaluate_direction,
    _pair_row,
)


def _window(*, changed: int = 1, nonrunning: int = 3) -> dict:
    assigned = 10
    return {
        "window": 1,
        "frame": 0,
        "assigned": assigned,
        "running": assigned - nonrunning,
        "starting": nonrunning,
        "cold": 0,
        "warm_available": 5,
        "warm_bypassed": 1,
        "ranking_players": 10,
        "changed_players": changed,
        "near_tie_players": 1,
        "assignment_hash": 7,
        "commands_prepared": assigned,
        "strict_pne_status": "strict_pne",
        "outer_adjustments": 1,
        "price_signature": ((1.0, 1.1, True),),
        "feedback_applied_rounds": 1,
        "warm_bypass_utility_advantage_sum": 0.5,
        "warm_bypass_finish_score_delta_sum": 2.0,
        "utility_components": {
            "baseline_reward": 2.0,
            "contribution": 1.0,
            "cost": 0.5,
            "externality": 0.25,
            "quality": 0.75,
        },
        "partition_invariant": True,
        "warm_invariant": True,
        "differentiation_invariant": True,
    }


def _d1_rows(dormant: bool = True) -> list[dict]:
    return [
        {
            "seed": f"D{121 + seed}",
            "candidate": candidate,
            "aligned_windows": EXPECTED_WINDOW_COUNT,
            "operationally_dormant": dormant,
        }
        for seed in range(5)
        for candidate in ("r0_minus", "r0_plus")
    ]


def _d3_rows() -> list[dict]:
    return [
        {
            "differentiation_change_share": 0.10,
            "nonrunning_share": 0.30,
            "both_groups_defined": True,
            "changed_group_nonrunning_nondecrease": True,
            "all_invariants_pass": True,
        }
        for _ in range(5)
    ]


def _gate() -> dict:
    return {
        "selected_setting": None,
        "gate_result": {
            "candidate_reports": [
                {"setting": "wq_minus", "qualified": False},
                {"setting": "wq_plus", "qualified": False},
            ]
        },
    }


class P3LowRootCauseDiagnosisTests(unittest.TestCase):
    def test_centre_path_uses_player_weighted_group_shares(self) -> None:
        changed = _window(changed=1, nonrunning=5)
        unchanged = _window(changed=0, nonrunning=1)
        unchanged["window"] = 2
        row = centre_path_row("D121", "run", [changed, unchanged])
        self.assertEqual(row["assigned"], 20)
        self.assertEqual(row["nonrunning_players"], 6)
        self.assertAlmostEqual(row["nonrunning_share"], 0.3)
        self.assertAlmostEqual(row["changed_group_nonrunning_share"], 0.5)
        self.assertAlmostEqual(row["unchanged_group_nonrunning_share"], 0.1)
        self.assertTrue(row["changed_group_nonrunning_nondecrease"])
        self.assertTrue(row["all_invariants_pass"])

    def test_all_six_conditions_are_conjunctive(self) -> None:
        result = evaluate_direction(_d1_rows(), _d3_rows(), _gate())
        self.assertTrue(result["contribution_tempering_preregistration_authorized"])
        self.assertTrue(all(result["conditions"].values()))
        self.assertFalse(result["implementation_authorized"])
        self.assertFalse(result["sampling_authorized"])

    def test_four_of_five_thresholds_but_three_cooccurrence(self) -> None:
        rows = _d3_rows()
        rows[4]["differentiation_change_share"] = 0.049
        rows[4]["nonrunning_share"] = 0.19
        rows[3]["changed_group_nonrunning_nondecrease"] = False
        rows[4]["changed_group_nonrunning_nondecrease"] = False
        result = evaluate_direction(_d1_rows(), rows, _gate())
        self.assertTrue(result["contribution_tempering_preregistration_authorized"])

    def test_missing_fourth_defined_group_fails_condition_four(self) -> None:
        rows = _d3_rows()
        rows[3]["both_groups_defined"] = False
        rows[4]["both_groups_defined"] = False
        result = evaluate_direction(_d1_rows(), rows, _gate())
        self.assertFalse(
            result["conditions"][
                "04_changed_choice_nonrunning_share_nondecrease_in_three_seeds"
            ]
        )
        self.assertFalse(result["contribution_tempering_preregistration_authorized"])

    def test_dormancy_failure_cannot_be_outvoted(self) -> None:
        rows = _d1_rows()
        rows[0]["operationally_dormant"] = False
        result = evaluate_direction(rows, _d3_rows(), _gate())
        self.assertFalse(
            result["conditions"]["05_both_r0_neighbours_operationally_dormant"]
        )
        self.assertFalse(result["contribution_tempering_preregistration_authorized"])

    def test_wq_relabelling_fails_closed(self) -> None:
        gate = _gate()
        gate["gate_result"]["candidate_reports"][0]["qualified"] = True
        result = evaluate_direction(_d1_rows(), _d3_rows(), gate)
        self.assertFalse(result["conditions"]["06_failed_wq_neighbours_not_relabelled"])

    def test_pair_dormancy_requires_hash_and_command_equality(self) -> None:
        centre = [_window(changed=0) for _ in range(EXPECTED_WINDOW_COUNT)]
        candidate = copy.deepcopy(centre)
        metrics = {}
        for setting in ("centre", "r0_minus"):
            metrics[("D121", setting)] = {
                "throughput_requests_per_ms": 1.0,
                "qpr": 1.0,
                "completion_ratio": 0.5,
                "latency_mean_ms": 100.0,
            }
        row = _pair_row("D121", "r0_minus", centre, candidate, metrics)
        self.assertTrue(row["operationally_dormant"])
        candidate[9]["commands_prepared"] = 9
        row = _pair_row("D121", "r0_minus", centre, candidate, metrics)
        self.assertFalse(row["operationally_dormant"])

    def test_pair_rejects_two_equally_truncated_window_series(self) -> None:
        centre = [_window(changed=0)] * (EXPECTED_WINDOW_COUNT - 1)
        metrics = {
            ("D121", setting): {
                "throughput_requests_per_ms": 1.0,
                "qpr": 1.0,
                "completion_ratio": 0.5,
                "latency_mean_ms": 100.0,
            }
            for setting in ("centre", "r0_minus")
        }
        with self.assertRaises(DiagnosisError):
            _pair_row("D121", "r0_minus", centre, centre, metrics)


if __name__ == "__main__":
    unittest.main()
