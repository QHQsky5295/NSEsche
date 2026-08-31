from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_lifetime_credit_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v163 as v163,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V163ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(v163.PLAN), v163.PLAN_SHA256)
        self.assertEqual(file_hash(v163.IMPLEMENTATION), v163.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v163.BINARY_PATH), v163.BINARY_SHA256)
        plan = read_json(v163.PLAN)
        implementation = read_json(v163.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v163.SEEDS))
        self.assertEqual(plan["candidate"]["player_frontier"], v163.FRONTIER)
        self.assertEqual(plan["frozen_thresholds"]["remaining_work_max"], 5.5)
        self.assertEqual(plan["frozen_thresholds"]["queue_density_exclusive_max"], 8.0)
        change = implementation["single_scientific_change"]
        self.assertEqual(change["short_work_remaining_work_threshold"], 5.5)
        self.assertEqual(change["short_work_queue_density_threshold"], 8.0)
        self.assertEqual(change["credit_limit_per_request_lifetime"], 1)
        self.assertEqual(change["credit_definition"], v163.LIFETIME_CREDIT_DEFINITION)
        self.assertEqual(change["selection_order"], v163.SELECTION_ORDER)
        self.assertEqual(
            change["credit_consumption_point"],
            "only_after_the_actual_scheduling_command_batch_is_successfully_sent",
        )
        self.assertFalse(
            change["candidate_collection_or_infeasibility_consumes_credit"]
        )
        self.assertFalse(change["credit_reuse_after_parent_or_function_completion"])
        self.assertFalse(
            change[
                "uses_seed_load_tape_future_arrival_aggregate_completion_or_performance_outcomes"
            ]
        )

    def test_rewrite_is_exact_three_seed_lifetime_credit_product(self) -> None:
        manifest = v163._rewrite_candidate(v163._assert_frozen_inputs(), "c" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v163.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v163.PROFILE},
        )
        self.assertEqual(
            {run["metadata"]["v163_player_frontier"] for run in manifest["runs"]},
            {v163.FRONTIER},
        )
        self.assertTrue(
            all(
                run["metadata"]["v163_lifetime_credit_definition"]
                == v163.LIFETIME_CREDIT_DEFINITION
                and run["metadata"]["v163_lifetime_credit_limit_per_request"] == 1
                and run["metadata"][
                    "v163_credit_reuse_after_parent_or_function_completion"
                ]
                is False
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
        corrupt_repeat_or_after: bool = False,
        corrupt_selection_order: bool = False,
    ) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": v163.PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V163",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": v163.LOW_EXPERT,
                    "at_or_above_threshold_expert": v163.HIGH_EXPERT,
                    "player_frontier": v163.FRONTIER,
                    "single_change_from_v155": v163.SINGLE_CHANGE,
                    "terminal_pipeline_definition": v163.TERMINAL_DEFINITION,
                    "short_work_pipeline_remaining_work_threshold": 5.5,
                    "short_work_pipeline_queue_density_threshold": 8.0,
                    "short_work_pipeline_queue_boundary": "below_is_strict",
                    "short_work_definition": v163.WORK_DEFINITION,
                    "jit_parent_tail_short_work_required": False,
                    "jit_parent_tail_definition": None,
                    "one_outstanding_short_work_credit_required": False,
                    "one_outstanding_short_work_credit_definition": None,
                    "lifetime_short_work_credit_required": True,
                    "lifetime_short_work_credit_definition": (
                        v163.LIFETIME_CREDIT_DEFINITION
                        + ";when_unused_select_"
                        + v163.SELECTION_ORDER
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
                        "player_frontier": v163.FRONTIER,
                        "pipeline_players_with_incomplete_parents": 2
                        if admitted
                        else 1,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": v163.FRONTIER,
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
                            "lifetime_short_work_credit": {
                                "enabled": True,
                                "definition": v163.LIFETIME_CREDIT_DEFINITION,
                                "credit_limit_per_request_lifetime": 1,
                                "selection_order": (
                                    "bad"
                                    if corrupt_selection_order and frame == 700
                                    else v163.SELECTION_ORDER
                                ),
                                "terminal_players_consume_credit": False,
                                "ready_players_consume_credit": False,
                                "credit_reuse_after_parent_or_function_completion": False,
                                "uses_completion_or_performance_outcomes": False,
                                "requests_observed": 4,
                                "credited_requests_before": 1,
                                "credited_requests_after": (
                                    99
                                    if corrupt_repeat_or_after and frame == 700
                                    else (2 if admitted else 1)
                                ),
                                "first_admissions": 1 if admitted else 0,
                                "rejected_already_credited": 1,
                                "rejected_same_window_not_selected": 1,
                                "repeat_admission_violations": (
                                    1 if corrupt_repeat_or_after and frame == 700 else 0
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
                                v163.LOW_EXPERT if admitted else v163.HIGH_EXPERT
                            ),
                            "player_frontier": v163.FRONTIER,
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

    def test_blind_log_proves_lifetime_credit_admission_and_rejections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v163")
            evidence = v163._audit_nash_log(
                canonical, {"run_id": "synthetic-v163", "seed": "E09"}
            )
            self.assertEqual(evidence["first_lifetime_credit_admissions"], 500)
            self.assertEqual(evidence["rejected_already_credited"], 1000)
            self.assertEqual(evidence["rejected_same_window_not_selected"], 1000)
            self.assertEqual(evidence["repeat_admission_violations"], 0)
            self.assertEqual(evidence["credited_request_observations_before"], 1000)
            self.assertEqual(evidence["credited_request_observations_after"], 1500)
            self.assertEqual(evidence["credited_requests_max"], 2)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)
            gate = v163._mechanism_falsification_gate([evidence])
            self.assertTrue(gate["passed"])
            self.assertEqual(gate["failure_reasons"], [])

            no_same_window_evidence = dict(evidence)
            no_same_window_evidence["rejected_same_window_not_selected"] = 0
            no_choice = v163._mechanism_falsification_gate([no_same_window_evidence])
            self.assertTrue(no_choice["passed"])
            self.assertFalse(no_choice["same_window_choice_observed"])

    def test_blind_log_rejects_limit_or_selection_tamper(self) -> None:
        for repeat_or_after, order in ((True, False), (False, True)):
            with self.subTest(repeat_or_after=repeat_or_after, order=order):
                with tempfile.TemporaryDirectory() as tmp:
                    canonical = Path(tmp)
                    self._write_log(
                        canonical,
                        "synthetic-v163-bad",
                        corrupt_repeat_or_after=repeat_or_after,
                        corrupt_selection_order=order,
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "lifetime-credit slack short-work evidence changed",
                    ):
                        v163._audit_nash_log(
                            canonical,
                            {"run_id": "synthetic-v163-bad", "seed": "E09"},
                        )


if __name__ == "__main__":
    unittest.main()
