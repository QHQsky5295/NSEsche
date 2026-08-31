from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_remaining17_v170 as v170r,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V170Remaining17Tests(unittest.TestCase):
    def test_frozen_inputs_and_exact_remaining_product(self) -> None:
        self.assertEqual(file_hash(v170r.PLAN), v170r.PLAN_SHA256)
        self.assertEqual(
            file_hash(v170r.DIAGNOSTIC_SUCCESS), v170r.DIAGNOSTIC_SUCCESS_SHA256
        )
        manifest = v170r._rewrite_remaining17(v170r._assert_frozen_inputs(), "c" * 40)
        v170r._validate_product(manifest, references_bound=False)
        self.assertEqual(
            [run["seed"] for run in manifest["runs"]], list(v170r.REMAINING_SEEDS)
        )
        self.assertEqual(len(manifest["runs"]), 17)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 17)
        self.assertFalse(set(v170r.DIAGNOSTIC_SEEDS) & set(v170r.REMAINING_SEEDS))
        self.assertEqual(
            set(v170r.DIAGNOSTIC_SEEDS) | set(v170r.REMAINING_SEEDS),
            set(v170r.v155.SEEDS),
        )
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                == v170r.v170.PROFILE
                and run["metadata"]["v170_diagnostic_seed"] is False
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
            "below_threshold_route_windows",
            "at_or_above_threshold_route_windows",
        )
        audits = []
        for seed in v170r.REMAINING_SEEDS:
            audit = {key: 1 for key in count_keys}
            audit.update(
                {
                    "seed": seed,
                    "windows": 1000,
                    "performance_outcome_fields_parsed": 0,
                    "frozen_v159_comparison_applicable": False,
                    "cpu_guard_active_admitted_normalized_cpu_max": 1.0,
                    "cpu_guard_rejected_normalized_cpu_min": 1.1,
                }
            )
            audits.append(audit)
        return audits

    def test_combined_blind_gate_accepts_fixed_product(self) -> None:
        diagnostic = read_json(v170r.v170.paths(v170r.DIAGNOSTIC_ROOT)["blind"])
        gate = v170r._remaining17_mechanism_gate(self._audits(), diagnostic)
        self.assertTrue(gate["pass"])
        self.assertEqual(gate["combined_twenty_active_windows"], 993)
        self.assertEqual(gate["combined_twenty_inactive_windows"], 2041)

    def test_combined_blind_gate_rejects_cpu_boundary_violation(self) -> None:
        diagnostic = read_json(v170r.v170.paths(v170r.DIAGNOSTIC_ROOT)["blind"])
        audits = self._audits()
        audits[0]["cpu_guard_active_admitted_normalized_cpu_max"] = 1.0001
        self.assertFalse(v170r._remaining17_mechanism_gate(audits, diagnostic)["pass"])


if __name__ == "__main__":
    unittest.main()
