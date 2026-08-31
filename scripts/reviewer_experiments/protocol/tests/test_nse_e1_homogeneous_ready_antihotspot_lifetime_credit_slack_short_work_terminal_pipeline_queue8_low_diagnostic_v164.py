from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_ready_antihotspot_lifetime_credit_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v164 as v164,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V164ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(v164.PLAN), v164.PLAN_SHA256)
        self.assertEqual(file_hash(v164.IMPLEMENTATION), v164.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v164.BINARY_PATH), v164.BINARY_SHA256)
        plan = read_json(v164.PLAN)
        implementation = read_json(v164.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v164.SEEDS))
        self.assertEqual(plan["candidate"]["player_frontier"], "identical_to_v163")
        self.assertEqual(plan["candidate"]["profile"], v164.PROFILE)
        self.assertEqual(
            plan["ready_antihotspot_definition"]["history"],
            "the last at most 64 successfully sent placement decisions for the same function, plus projected assignments in the current solver state",
        )
        change = implementation["single_scientific_change"]
        self.assertEqual(change["short_work_remaining_work_threshold"], 5.5)
        self.assertEqual(change["short_work_queue_density_threshold"], 8.0)
        self.assertTrue(change["v163_lifetime_credit_definition_unchanged"])
        self.assertEqual(
            change["ready_player_definition"], "all_direct_parents_completed"
        )
        self.assertEqual(change["nonready_operational_penalty"], "exact_V163_router")
        self.assertEqual(
            change["history_update_point"],
            "only_after_the_actual_scheduling_command_batch_is_successfully_sent",
        )
        self.assertFalse(
            change[
                "uses_seed_load_tape_future_arrival_aggregate_completion_or_performance_outcomes"
            ]
        )

    def test_rewrite_is_exact_three_seed_ready_antihotspot_product(self) -> None:
        manifest = v164._rewrite_candidate(v164._assert_frozen_inputs(), "c" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v164.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v164.PROFILE},
        )
        self.assertEqual(
            {run["metadata"]["v164_player_frontier"] for run in manifest["runs"]},
            {v164.FRONTIER},
        )
        self.assertTrue(
            all(
                run["metadata"]["v164_lifetime_credit_definition"]
                == v164.LIFETIME_CREDIT_DEFINITION
                and run["metadata"]["v164_lifetime_credit_limit_per_request"] == 1
                and run["metadata"]["v164_ready_antihotspot_history_limit"] == 64
                and run["metadata"]["v164_nonready_score"] == "exact_V163_router"
                and run["metadata"][
                    "v164_credit_reuse_after_parent_or_function_completion"
                ]
                is False
                for run in manifest["runs"]
            )
        )
        self.assertTrue(
            all(
                not any(key.startswith("v163_") for key in run["metadata"])
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
                "operational_expert_proxy": v164.PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V164",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": v164.LOW_EXPERT,
                    "at_or_above_threshold_expert": v164.HIGH_EXPERT,
                    "player_frontier": v164.FRONTIER,
                    "single_change_from_v155": v164.SINGLE_CHANGE,
                    "terminal_pipeline_definition": v164.TERMINAL_DEFINITION,
                    "short_work_pipeline_remaining_work_threshold": 5.5,
                    "short_work_pipeline_queue_density_threshold": 8.0,
                    "short_work_pipeline_queue_boundary": "below_is_strict",
                    "short_work_definition": v164.WORK_DEFINITION,
                    "jit_parent_tail_short_work_required": False,
                    "jit_parent_tail_definition": None,
                    "one_outstanding_short_work_credit_required": False,
                    "one_outstanding_short_work_credit_definition": None,
                    "lifetime_short_work_credit_required": True,
                    "lifetime_short_work_credit_definition": (
                        v164.LIFETIME_CREDIT_DEFINITION
                        + ";when_unused_select_"
                        + v164.SELECTION_ORDER
                    ),
                    "ready_antihotspot_required": True,
                    "ready_antihotspot_definition": {
                        "eligible_players": "direct_parents_all_completed_only",
                        "history": "last_at_most_64_successfully_sent_same-function_placement_decisions_plus_current_projected_assignments",
                        "candidate_penalty": "same-function_candidate_share_ascending_then_node_id",
                        "below_queue8_votes": [
                            "hiku",
                            "hiku",
                            "ocs",
                            "ready_antihotspot",
                        ],
                        "at_or_above_queue8_votes": [
                            "ocs",
                            "ready_antihotspot",
                        ],
                        "nonready_score": "exact_V163_router",
                        "history_update": "only_after_successful_command_batch_send",
                        "uses_completed_request_outcomes": False,
                    },
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
                        "player_frontier": v164.FRONTIER,
                        "pipeline_players_with_incomplete_parents": 2
                        if admitted
                        else 1,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": v164.FRONTIER,
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
                                "definition": v164.LIFETIME_CREDIT_DEFINITION,
                                "credit_limit_per_request_lifetime": 1,
                                "selection_order": (
                                    "bad"
                                    if corrupt_selection_order and frame == 700
                                    else v164.SELECTION_ORDER
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
                            "ready_antihotspot": {
                                "enabled": True,
                                "eligible_ready_players": 2,
                                "dispatched_ready_players": 1,
                                "dispatched_with_nonempty_history": 1,
                                "v163_anchor_substitutions": 1,
                                "history_length_max_before_update": 64,
                                "history_limit": 64,
                                "history_updates_after_successful_send": True,
                                "uses_completion_or_performance_outcomes": False,
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
                                v164.LOW_EXPERT if admitted else v164.HIGH_EXPERT
                            ),
                            "player_frontier": v164.FRONTIER,
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

    def test_blind_log_proves_lifetime_credit_and_ready_antihotspot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v164")
            evidence = v164._audit_nash_log(
                canonical, {"run_id": "synthetic-v164", "seed": "E09"}
            )
            self.assertEqual(evidence["first_lifetime_credit_admissions"], 500)
            self.assertEqual(evidence["rejected_already_credited"], 1000)
            self.assertEqual(evidence["rejected_same_window_not_selected"], 1000)
            self.assertEqual(evidence["repeat_admission_violations"], 0)
            self.assertEqual(evidence["credited_request_observations_before"], 1000)
            self.assertEqual(evidence["credited_request_observations_after"], 1500)
            self.assertEqual(evidence["credited_requests_max"], 2)
            self.assertEqual(evidence["ready_antihotspot_eligible_players"], 2000)
            self.assertEqual(
                evidence["ready_antihotspot_v163_anchor_substitutions"], 1000
            )
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)
            gate = v164._mechanism_falsification_gate([evidence])
            self.assertTrue(gate["passed"])
            self.assertEqual(gate["failure_reasons"], [])

            no_same_window_evidence = dict(evidence)
            no_same_window_evidence["rejected_same_window_not_selected"] = 0
            no_choice = v164._mechanism_falsification_gate([no_same_window_evidence])
            self.assertTrue(no_choice["passed"])
            self.assertFalse(no_choice["same_window_choice_observed"])

    def test_blind_log_rejects_limit_or_selection_tamper(self) -> None:
        for repeat_or_after, order in ((True, False), (False, True)):
            with self.subTest(repeat_or_after=repeat_or_after, order=order):
                with tempfile.TemporaryDirectory() as tmp:
                    canonical = Path(tmp)
                    self._write_log(
                        canonical,
                        "synthetic-v164-bad",
                        corrupt_repeat_or_after=repeat_or_after,
                        corrupt_selection_order=order,
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "lifetime-credit slack short-work evidence changed",
                    ):
                        v164._audit_nash_log(
                            canonical,
                            {"run_id": "synthetic-v164-bad", "seed": "E09"},
                        )


if __name__ == "__main__":
    unittest.main()
