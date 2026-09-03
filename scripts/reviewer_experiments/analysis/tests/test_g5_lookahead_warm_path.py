from __future__ import annotations

import unittest
from types import SimpleNamespace

from scripts.reviewer_experiments.protocol.schema import ProtocolValidationError
from scripts.reviewer_experiments.analysis.g5_lookahead_warm_path import (
    _decision,
    _function_timing,
    _lookahead_condition,
    _pair_row,
    _warm_accounting,
)


class G5LookaheadWarmPathTests(unittest.TestCase):
    def test_function_timing_separates_overlap_from_residual_wait(self) -> None:
        timing = _function_timing(
            {
                "ready_schedule_frame": 10,
                "scheduled_frame": 4,
                "cold_start_done_frame": 13,
            }
        )
        self.assertEqual(timing["pre_ready_bound"], 1.0)
        self.assertEqual(timing["pre_ready_lead_ms"], 6.0)
        self.assertEqual(timing["startup_overlap_ms"], 6.0)
        self.assertEqual(timing["post_ready_cold_wait_ms"], 3.0)

    def test_pair_orients_lookahead_and_cold_advantages(self) -> None:
        def row(method: str, lead: float, overlap: float, cold: float):
            function = {
                "pre_ready_bound": float(lead > 0),
                "pre_ready_lead_ms": lead,
                "startup_overlap_ms": overlap,
                "post_ready_cold_wait_ms": cold,
            }
            return {
                "seed": "D71",
                "run_id": method,
                "method": method,
                "pre_ready_bound_mean": function["pre_ready_bound"],
                "pre_ready_lead_ms_mean": lead,
                "startup_overlap_ms_mean": overlap,
                "post_ready_cold_wait_ms_mean": cold,
                "_functions": {("1", "2"): function},
            }

        pair = _pair_row(
            row("sche_nash", 0.0, 0.0, 8.0), row("sche_Hiku", 4.0, 3.0, 2.0)
        )
        self.assertEqual(pair["full_pre_ready_lead_ms_advantage"], 4.0)
        self.assertEqual(pair["common_startup_overlap_ms_advantage"], 3.0)
        self.assertEqual(pair["full_nash_post_ready_cold_disadvantage_ms"], 6.0)
        self.assertTrue(pair["full_overlap_cold_cooccurrence"])

    def test_lookahead_condition_requires_full_and_common_evidence(self) -> None:
        def summary(positive: int) -> dict[str, int]:
            return {"positive": positive}

        row = {
            "metrics": {
                "full_pre_ready_bound_share_advantage": summary(4),
                "full_pre_ready_lead_ms_advantage": summary(4),
                "common_pre_ready_bound_advantage": summary(3),
                "common_pre_ready_lead_ms_advantage": summary(3),
                "full_startup_overlap_ms_advantage": summary(4),
                "common_startup_overlap_ms_advantage": summary(3),
            },
            "full_overlap_cold_cooccurrence_count": 3,
        }
        self.assertTrue(_lookahead_condition(row)["qualifies"])
        row["metrics"]["common_startup_overlap_ms_advantage"] = summary(2)
        self.assertFalse(_lookahead_condition(row)["qualifies"])

    def test_warm_accounting_partitions_nonwarm_and_fails_closed(self) -> None:
        decision = {
            "assigned_players": 4,
            "selected_running_warm_players": 2,
            "selected_starting_container_players": 2,
            "selected_cold_or_nonrunning_players": 0,
            "running_warm_available_players": 3,
            "running_warm_bypassed_players": 1,
            "selected_lower_utility_than_warm_players": 0,
            "complete_assignment": True,
            "commands_prepared": 4,
            "commands_sent": 4,
            "invalid_assignments": 0,
            "dispatch_channel_failed": False,
            "warm_bypass_utility_advantage_sum": 0.4,
            "warm_bypass_finish_score_delta_sum": 3.0,
        }
        artifacts = SimpleNamespace(
            run_id="nash",
            seed="D71",
            nse_events=[{"kind": "window", "frame": 7, "decision": decision}],
        )
        functions = {
            ("1", "1"): {"scheduled_frame": 7.0, "cold_event": 1.0},
            ("2", "1"): {"scheduled_frame": 7.0, "cold_event": 0.0},
        }
        result = _warm_accounting(artifacts, functions)
        self.assertEqual(result["selected_nonwarm_players"], 2)
        self.assertEqual(result["capacity_absence_nonwarm_players"], 1)
        self.assertEqual(result["nonwarm_bypass_contribution"], 0.5)
        self.assertEqual(result["completed_only_command_coverage"], 0.5)

        decision["selected_lower_utility_than_warm_players"] = 1
        with self.assertRaises(ProtocolValidationError):
            _warm_accounting(artifacts, functions)

    def test_decision_keeps_candidate_authorization_narrow(self) -> None:
        def aggregate(name: str, qualifies: bool) -> dict[str, object]:
            positive = 5 if qualifies else 0
            metrics = {
                key: {"positive": positive}
                for key in (
                    "full_pre_ready_bound_share_advantage",
                    "full_pre_ready_lead_ms_advantage",
                    "common_pre_ready_bound_advantage",
                    "common_pre_ready_lead_ms_advantage",
                    "full_startup_overlap_ms_advantage",
                    "common_startup_overlap_ms_advantage",
                )
            }
            return {
                "baseline": name,
                "metrics": metrics,
                "full_overlap_cold_cooccurrence_count": positive,
            }

        run_rows = [
            {"method": "sche_nash", "pre_ready_bound_mean": 0.0} for _ in range(5)
        ]
        aggregates = [
            aggregate("sche_OCS", True),
            aggregate("sche_Hiku", True),
            aggregate("sche_jiagu", True),
            aggregate("sche_orion", False),
            aggregate("sche_FaaSRank", False),
        ]
        warm_rows = [
            {
                "selected_nonwarm_players": 10,
                "running_warm_bypassed_players": 2,
                "nonwarm_bypass_contribution": 0.2,
                "warm_bypass_utility_advantage_mean": 1.0,
                "completed_only_command_coverage": 0.9,
                "bypass_active_rate_higher": True,
            }
            for _ in range(5)
        ]
        decision = _decision(run_rows, aggregates, warm_rows)
        self.assertTrue(decision["lookahead_supported"])
        self.assertFalse(decision["warm_bypass_dominant"])
        self.assertEqual(
            decision["candidate_preregistration_authorized"],
            "pre_all_scheduled_strict_eq15",
        )
        self.assertFalse(decision["source_change_authorized"])
        self.assertFalse(decision["new_sampling_authorized"])


if __name__ == "__main__":
    unittest.main()
