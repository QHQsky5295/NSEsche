from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_jit_parent_tail_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v161 as v161,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V161ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(v161.PLAN), v161.PLAN_SHA256)
        self.assertEqual(file_hash(v161.IMPLEMENTATION), v161.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v161.BINARY_PATH), v161.BINARY_SHA256)
        plan = read_json(v161.PLAN)
        implementation = read_json(v161.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v161.SEEDS))
        self.assertEqual(plan["candidate"]["player_frontier"], v161.FRONTIER)
        self.assertEqual(plan["frozen_thresholds"]["remaining_work_max"], 5.5)
        self.assertEqual(plan["frozen_thresholds"]["queue_density_exclusive_max"], 8.0)
        change = implementation["single_scientific_change"]
        self.assertEqual(change["short_work_remaining_work_threshold"], 5.5)
        self.assertEqual(change["short_work_queue_density_threshold"], 8.0)
        self.assertEqual(change["queue_boundary"], "below_is_strict")
        self.assertTrue(change["all_unfinished_direct_parents_must_pass"])
        self.assertTrue(
            change[
                "missing_inactive_nonconsecutive_invalid_zero_service_or_zero_cold_start_fail_closed"
            ]
        )

    def test_rewrite_is_exact_three_seed_jit_parent_tail_product(self) -> None:
        manifest = v161._rewrite_candidate(v161._assert_frozen_inputs(), "c" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v161.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v161.PROFILE},
        )
        self.assertEqual(
            {run["metadata"]["v161_player_frontier"] for run in manifest["runs"]},
            {v161.FRONTIER},
        )
        self.assertTrue(
            all(
                run["metadata"]["v161_all_unfinished_direct_parents_must_pass"]
                and run["metadata"]["v161_parent_tail_fail_closed"]
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
        corrupt_admission_ratio: bool = False,
        corrupt_history_boundary: bool = False,
    ) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": v161.PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V161",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": v161.LOW_EXPERT,
                    "at_or_above_threshold_expert": v161.HIGH_EXPERT,
                    "player_frontier": v161.FRONTIER,
                    "single_change_from_v155": v161.SINGLE_CHANGE,
                    "terminal_pipeline_definition": v161.TERMINAL_DEFINITION,
                    "short_work_pipeline_remaining_work_threshold": 5.5,
                    "short_work_pipeline_queue_density_threshold": 8.0,
                    "short_work_pipeline_queue_boundary": "below_is_strict",
                    "short_work_definition": v161.WORK_DEFINITION,
                    "jit_parent_tail_short_work_required": True,
                    "jit_parent_tail_definition": v161.JIT_PARENT_TAIL_DEFINITION,
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
                        "player_frontier": v161.FRONTIER,
                        "pipeline_players_with_incomplete_parents": (
                            3 if admitted else 1
                        ),
                        "pipeline_observation_fields_drive_future_windows": True,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": v161.FRONTIER,
                            "admitted_terminal_players_with_incomplete_parents": 1,
                            "rejected_nonterminal_players_with_incomplete_parents": 5,
                            "short_work_remaining_work_threshold": 5.5,
                            "admitted_short_work_nonterminal_players_with_incomplete_parents": (
                                2 if admitted else 0
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
                            "jit_parent_tail_short_work_gate": {
                                "enabled": True,
                                "definition": v161.JIT_PARENT_TAIL_DEFINITION,
                                "admitted_nonterminal_incomplete_parent_players": (
                                    2 if admitted else 0
                                ),
                                "admitted_deeper_than_completion_proximal_players": (
                                    1 if admitted else 0
                                ),
                                "rejected_missing_or_nonconsecutive_observation": 1,
                                "rejected_inactive_parent": 0,
                                "rejected_invalid_or_zero_service": 0,
                                "rejected_parent_tail_over_child_cold_start": 1,
                                "admitted_max_predicted_parent_remaining_frames": (
                                    2.0 if admitted else None
                                ),
                                "admitted_max_parent_tail_to_child_cold_start_ratio": (
                                    1.1
                                    if corrupt_admission_ratio and frame == 700
                                    else (0.5 if admitted else None)
                                ),
                                "rejected_over_cold_start_min_ratio": 2.0,
                                "current_observation_map_size": 4,
                                "history_boundary": (
                                    "bad"
                                    if corrupt_history_boundary and frame == 700
                                    else "previous_frame_plus_one_equals_current_frame_and_node_assignment_unchanged"
                                ),
                                "uses_completed_request_outcomes": False,
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
                                v161.LOW_EXPERT if admitted else v161.HIGH_EXPERT
                            ),
                            "player_frontier": v161.FRONTIER,
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

    def test_blind_log_proves_jit_admission_rejection_and_ratios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v161")
            evidence = v161._audit_nash_log(
                canonical, {"run_id": "synthetic-v161", "seed": "E09"}
            )
            self.assertEqual(
                evidence["admitted_jit_parent_tail_short_work_players"], 1000
            )
            self.assertEqual(
                evidence["admitted_deeper_than_completion_proximal_players"], 500
            )
            self.assertEqual(
                evidence["rejected_missing_or_nonconsecutive_observation"], 1000
            )
            self.assertEqual(
                evidence["rejected_parent_tail_over_child_cold_start"], 1000
            )
            self.assertEqual(
                evidence["admitted_max_parent_tail_to_child_cold_start_ratio"],
                0.5,
            )
            self.assertEqual(evidence["rejected_over_cold_start_min_ratio"], 2.0)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)

    def test_blind_log_rejects_invalid_ratio_or_history(self) -> None:
        for ratio, history in ((True, False), (False, True)):
            with self.subTest(ratio=ratio, history=history):
                with tempfile.TemporaryDirectory() as tmp:
                    canonical = Path(tmp)
                    self._write_log(
                        canonical,
                        "synthetic-v161-bad",
                        corrupt_admission_ratio=ratio,
                        corrupt_history_boundary=history,
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "jit-parent-tail slack short-work evidence changed",
                    ):
                        v161._audit_nash_log(
                            canonical,
                            {"run_id": "synthetic-v161-bad", "seed": "E09"},
                        )


if __name__ == "__main__":
    unittest.main()
