from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_one_outstanding_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v162 as v162,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V162ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(v162.PLAN), v162.PLAN_SHA256)
        self.assertEqual(file_hash(v162.IMPLEMENTATION), v162.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v162.BINARY_PATH), v162.BINARY_SHA256)
        plan = read_json(v162.PLAN)
        implementation = read_json(v162.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v162.SEEDS))
        self.assertEqual(plan["candidate"]["player_frontier"], v162.FRONTIER)
        self.assertEqual(plan["frozen_thresholds"]["remaining_work_max"], 5.5)
        self.assertEqual(plan["frozen_thresholds"]["queue_density_exclusive_max"], 8.0)
        change = implementation["single_scientific_change"]
        self.assertEqual(change["short_work_remaining_work_threshold"], 5.5)
        self.assertEqual(change["short_work_queue_density_threshold"], 8.0)
        self.assertEqual(change["outstanding_limit_per_request"], 1)
        self.assertEqual(
            change["outstanding_definition"],
            "assigned_and_unfinished_nonterminal_function_with_at_least_one_unfinished_direct_parent",
        )
        self.assertEqual(change["selection_order"], v162.SELECTION_ORDER)
        self.assertTrue(
            change["occupied_credit_and_same_window_extra_candidates_fail_closed"]
        )
        self.assertFalse(
            change[
                "uses_seed_load_tape_future_arrival_aggregate_completion_or_performance_outcomes"
            ]
        )

    def test_rewrite_is_exact_three_seed_one_outstanding_product(self) -> None:
        manifest = v162._rewrite_candidate(v162._assert_frozen_inputs(), "c" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v162.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v162.PROFILE},
        )
        self.assertEqual(
            {run["metadata"]["v162_player_frontier"] for run in manifest["runs"]},
            {v162.FRONTIER},
        )
        self.assertTrue(
            all(
                run["metadata"]["v162_one_outstanding_definition"]
                == v162.ONE_OUTSTANDING_DEFINITION
                and run["metadata"]["v162_outstanding_limit_per_request"] == 1
                and run["metadata"]["v162_occupied_and_same_window_extra_fail_closed"]
                for run in manifest["runs"]
            )
        )
        self.assertTrue(
            all(
                not any(key.startswith("v159_") for key in run["metadata"])
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _write_log(
        canonical: Path,
        run_id: str,
        *,
        corrupt_projected_limit: bool = False,
        corrupt_selection_order: bool = False,
    ) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": v162.PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V162",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": v162.LOW_EXPERT,
                    "at_or_above_threshold_expert": v162.HIGH_EXPERT,
                    "player_frontier": v162.FRONTIER,
                    "single_change_from_v155": v162.SINGLE_CHANGE,
                    "terminal_pipeline_definition": v162.TERMINAL_DEFINITION,
                    "short_work_pipeline_remaining_work_threshold": 5.5,
                    "short_work_pipeline_queue_density_threshold": 8.0,
                    "short_work_pipeline_queue_boundary": "below_is_strict",
                    "short_work_definition": v162.WORK_DEFINITION,
                    "jit_parent_tail_short_work_required": False,
                    "jit_parent_tail_definition": None,
                    "one_outstanding_short_work_credit_required": True,
                    "one_outstanding_short_work_credit_definition": (
                        v162.ONE_OUTSTANDING_DEFINITION
                        + ";when_free_select_"
                        + v162.SELECTION_ORDER
                    ),
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            }
        ]
        for frame in range(1000):
            admitted = frame % 2 == 0
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {
                        "assignment_hash": frame,
                        "player_frontier": v162.FRONTIER,
                        "pipeline_players_with_incomplete_parents": 2
                        if admitted
                        else 1,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": v162.FRONTIER,
                            "admitted_terminal_players_with_incomplete_parents": 1,
                            "rejected_nonterminal_players_with_incomplete_parents": 5,
                            "short_work_remaining_work_threshold": 5.5,
                            "admitted_short_work_nonterminal_players_with_incomplete_parents": (
                                1 if admitted else 0
                            ),
                            "admitted_short_work_remaining_work_max": (
                                5.5 if admitted else None
                            ),
                            "rejected_nonterminal_remaining_work_min": 5.501,
                            "short_work_queue_gate": {
                                "enabled": True,
                                "threshold": 8.0,
                                "boundary": "below_is_strict",
                                "admitted_short_work_queue_density_max": (
                                    7.0 if admitted else None
                                ),
                                "rejected_short_work_at_or_above_threshold": (
                                    0 if admitted else 2
                                ),
                                "rejected_short_work_queue_density_min": (
                                    None if admitted else 9.0
                                ),
                            },
                            "one_outstanding_short_work_credit": {
                                "enabled": True,
                                "definition": v162.ONE_OUTSTANDING_DEFINITION,
                                "credit_limit_per_request": 1,
                                "selection_order": (
                                    "bad"
                                    if corrupt_selection_order and frame == 700
                                    else v162.SELECTION_ORDER
                                ),
                                "terminal_players_consume_credit": False,
                                "uses_completion_or_performance_outcomes": False,
                                "requests_observed": 4,
                                "occupied_requests": 1,
                                "released_requests": 1,
                                "outstanding_max_before": 1,
                                "requests_over_limit_before": 0,
                                "admitted_new_players": 1 if admitted else 0,
                                "rejected_while_occupied": 1,
                                "rejected_same_window_not_selected": 1,
                                "projected_outstanding_max": (
                                    2 if corrupt_projected_limit and frame == 700 else 1
                                ),
                                "projected_requests_over_limit": (
                                    1 if corrupt_projected_limit and frame == 700 else 0
                                ),
                            },
                            "terminal_topology_source": (
                                "immutable_function_children_is_empty"
                            ),
                            "uses_completion_or_performance_outcomes": False,
                        },
                        "srpt_hiku2_ocs_queue_router": {
                            "enabled": True,
                            "queue_density": 7.0 if admitted else 9.0,
                            "queue_density_threshold": 8.0,
                            "selected_expert": (
                                v162.LOW_EXPERT if admitted else v162.HIGH_EXPERT
                            ),
                            "player_frontier": v162.FRONTIER,
                            "dependency_pipeline_frontier": True,
                            "uses_completion_outcomes": False,
                        },
                    },
                    "social": {
                        "reference_state_key": None,
                        "reference_source": "not_requested",
                    },
                }
            )
        events.append(
            {
                "kind": "run_summary",
                "scheduler": "sche_nash",
                "windows": 1000,
                "observation_writer_error": None,
            }
        )
        with gzip.open(
            record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8", newline="\n"
        ) as stream:
            for event in events:
                stream.write(json.dumps(event, sort_keys=True) + "\n")

    def test_blind_log_proves_one_outstanding_admission_and_rejections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v162")
            evidence = v162._audit_nash_log(
                canonical, {"run_id": "synthetic-v162", "seed": "E09"}
            )
            self.assertEqual(
                evidence["admitted_one_outstanding_short_work_players"], 500
            )
            self.assertEqual(evidence["rejected_while_credit_occupied"], 1000)
            self.assertEqual(evidence["rejected_same_window_not_selected"], 1000)
            self.assertEqual(evidence["released_request_credits"], 1000)
            self.assertEqual(evidence["outstanding_max_before"], 1)
            self.assertEqual(evidence["projected_outstanding_max"], 1)
            self.assertEqual(evidence["requests_over_limit_before"], 0)
            self.assertEqual(evidence["projected_requests_over_limit"], 0)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)

    def test_blind_log_rejects_limit_or_selection_tamper(self) -> None:
        for projected, order in ((True, False), (False, True)):
            with self.subTest(projected=projected, order=order):
                with tempfile.TemporaryDirectory() as tmp:
                    canonical = Path(tmp)
                    self._write_log(
                        canonical,
                        "synthetic-v162-bad",
                        corrupt_projected_limit=projected,
                        corrupt_selection_order=order,
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "one-outstanding slack short-work evidence changed",
                    ):
                        v162._audit_nash_log(
                            canonical,
                            {"run_id": "synthetic-v162-bad", "seed": "E09"},
                        )


if __name__ == "__main__":
    unittest.main()
