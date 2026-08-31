from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_quota2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_remaining17_v171 as v171r,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V171Remaining17Tests(unittest.TestCase):
    def test_frozen_inputs_and_exact_remaining_product(self) -> None:
        self.assertEqual(file_hash(v171r.PLAN), v171r.PLAN_SHA256)
        self.assertEqual(
            file_hash(v171r.DIAGNOSTIC_SUCCESS), v171r.DIAGNOSTIC_SUCCESS_SHA256
        )
        manifest = v171r._rewrite_remaining17(v171r._assert_frozen_inputs(), "c" * 40)
        v171r._validate_product(manifest, references_bound=False)
        self.assertEqual(
            [run["seed"] for run in manifest["runs"]], list(v171r.REMAINING_SEEDS)
        )
        self.assertEqual(len(manifest["runs"]), 17)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 17)
        self.assertFalse(set(v171r.DIAGNOSTIC_SEEDS) & set(v171r.REMAINING_SEEDS))
        self.assertEqual(
            set(v171r.DIAGNOSTIC_SEEDS) | set(v171r.REMAINING_SEEDS),
            set(v171r.v155.SEEDS),
        )
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                == v171r.v171.PROFILE
                and run["metadata"]["v171_diagnostic_seed"] is False
                and run["metadata"]["v171_active_heavy_admission_quota"] == 2
                and run["metadata"]["v171_quota_selection_order"]
                == "ascending_request_id_then_function_id"
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _audits() -> list[dict]:
        count_keys = (
            "admitted_terminal_players_with_incomplete_parents",
            "admitted_slack_short_work_nonterminal_players",
            "rejected_frontier_players_with_incomplete_parents",
            "rejected_short_work_at_or_above_queue_threshold",
            "cpu_guard_admitted_incomplete_parent_terminal_players",
            "cpu_guard_rejected_heavy_incomplete_parent_terminal_players",
            "cpu_guard_parent_completed_heavy_terminal_bypass_players",
            "capacity_overload_heavy_incomplete_parent_terminal_players",
            "capacity_overload_guard_active_windows",
            "capacity_overload_guard_inactive_windows",
            "capacity_overload_guard_inactive_heavy_terminal_admissions",
            "active_heavy_quota_selected_players",
            "active_heavy_quota_admitted_players",
            "active_heavy_quota_rejected_excess_players",
            "below_threshold_route_windows",
            "at_or_above_threshold_route_windows",
        )
        audits = []
        for seed in v171r.REMAINING_SEEDS:
            audit = {key: 1 for key in count_keys}
            audit.update(
                {
                    "seed": seed,
                    "windows": 1000,
                    "performance_outcome_fields_parsed": 0,
                    "frozen_v170_comparison_applicable": False,
                    "active_heavy_quota_selected_players": 2,
                    "active_heavy_quota_admitted_players": 2,
                    "cpu_guard_active_admitted_normalized_cpu_max": 2.0,
                    "cpu_guard_rejected_normalized_cpu_min": 1.1,
                }
            )
            audits.append(audit)
        return audits

    def test_combined_blind_gate_accepts_fixed_product(self) -> None:
        diagnostic = read_json(v171r.v171.paths(v171r.DIAGNOSTIC_ROOT)["blind"])
        gate = v171r._remaining17_mechanism_gate(self._audits(), diagnostic)
        self.assertTrue(gate["pass"])
        self.assertEqual(gate["combined_twenty_active_windows"], 258)
        self.assertEqual(gate["combined_twenty_inactive_windows"], 2776)
        self.assertEqual(
            gate["combined_twenty_active_heavy_quota_admitted_players"], 516
        )

    def test_combined_blind_gate_rejects_quota_violation(self) -> None:
        diagnostic = read_json(v171r.v171.paths(v171r.DIAGNOSTIC_ROOT)["blind"])
        audits = self._audits()
        audits[0]["active_heavy_quota_selected_players"] = 3
        audits[0]["active_heavy_quota_admitted_players"] = 3
        self.assertFalse(v171r._remaining17_mechanism_gate(audits, diagnostic)["pass"])


if __name__ == "__main__":
    unittest.main()
