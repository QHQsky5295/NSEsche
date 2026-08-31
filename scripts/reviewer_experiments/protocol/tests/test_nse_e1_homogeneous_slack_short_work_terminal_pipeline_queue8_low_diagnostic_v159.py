from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v159 as v159,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V159ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(v159.PLAN), v159.PLAN_SHA256)
        self.assertEqual(file_hash(v159.IMPLEMENTATION), v159.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v159.BINARY_PATH), v159.BINARY_SHA256)
        plan = read_json(v159.PLAN)
        implementation = read_json(v159.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v159.SEEDS))
        self.assertEqual(plan["candidate"]["player_frontier"], v159.FRONTIER)
        self.assertEqual(plan["frozen_thresholds"]["remaining_work_max"], 5.5)
        self.assertEqual(plan["frozen_thresholds"]["queue_density_exclusive_max"], 8.0)
        change = implementation["single_scientific_change"]
        self.assertEqual(change["short_work_remaining_work_threshold"], 5.5)
        self.assertEqual(change["short_work_queue_density_threshold"], 8.0)
        self.assertEqual(change["queue_boundary"], "below_is_strict")

    def test_rewrite_is_exact_three_seed_slack_short_work_product(self) -> None:
        manifest = v159._rewrite_candidate(v159._assert_frozen_inputs(), "c" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v159.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v159.PROFILE},
        )
        self.assertEqual(
            {run["metadata"]["v159_player_frontier"] for run in manifest["runs"]},
            {v159.FRONTIER},
        )
        self.assertEqual(
            {
                run["metadata"]["v159_queue_density_threshold"]
                for run in manifest["runs"]
            },
            {8.0},
        )
        self.assertTrue(
            all(
                not any(key.startswith("v158_") for key in run["metadata"])
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _write_log(canonical: Path, run_id: str, *, corrupt_density: bool) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": v159.PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V159",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": v159.LOW_EXPERT,
                    "at_or_above_threshold_expert": v159.HIGH_EXPERT,
                    "player_frontier": v159.FRONTIER,
                    "single_change_from_v155": v159.SINGLE_CHANGE,
                    "terminal_pipeline_definition": v159.TERMINAL_DEFINITION,
                    "short_work_pipeline_remaining_work_threshold": 5.5,
                    "short_work_pipeline_queue_density_threshold": 8.0,
                    "short_work_pipeline_queue_boundary": "below_is_strict",
                    "short_work_definition": v159.WORK_DEFINITION,
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            },
            {"kind": "function_profile", "throughput": 999, "qpr": 999},
        ]
        for frame in range(1000):
            slack = frame % 2 == 0
            admitted_density = 8.0 if corrupt_density and frame == 700 else 7.0
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {
                        "assignment_hash": frame,
                        "player_frontier": v159.FRONTIER,
                        "pipeline_players_with_incomplete_parents": 3 if slack else 1,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": v159.FRONTIER,
                            "admitted_terminal_players_with_incomplete_parents": 1,
                            "rejected_nonterminal_players_with_incomplete_parents": 3
                            if slack
                            else 5,
                            "short_work_remaining_work_threshold": 5.5,
                            "admitted_short_work_nonterminal_players_with_incomplete_parents": 2
                            if slack
                            else 0,
                            "admitted_short_work_remaining_work_max": 5.5
                            if slack
                            else None,
                            "rejected_nonterminal_remaining_work_min": 5.501,
                            "short_work_queue_gate": {
                                "enabled": True,
                                "threshold": 8.0,
                                "boundary": "below_is_strict",
                                "admitted_short_work_queue_density_max": admitted_density
                                if slack
                                else None,
                                "rejected_short_work_at_or_above_threshold": 0
                                if slack
                                else 2,
                                "rejected_short_work_queue_density_min": None
                                if slack
                                else 9.0,
                            },
                            "terminal_topology_source": "immutable_function_children_is_empty",
                            "uses_completion_or_performance_outcomes": False,
                        },
                        "srpt_hiku2_ocs_queue_router": {
                            "enabled": True,
                            "queue_density": 7.0 if slack else 9.0,
                            "queue_density_threshold": 8.0,
                            "selected_expert": v159.LOW_EXPERT
                            if slack
                            else v159.HIGH_EXPERT,
                            "player_frontier": v159.FRONTIER,
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

    def test_blind_log_proves_slack_admission_and_congestion_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v159", corrupt_density=False)
            evidence = v159._audit_nash_log(
                canonical, {"run_id": "synthetic-v159", "seed": "E09"}
            )
            self.assertEqual(
                evidence["admitted_slack_short_work_nonterminal_players"], 1000
            )
            self.assertEqual(
                evidence["rejected_short_work_at_or_above_queue_threshold"], 1000
            )
            self.assertEqual(evidence["admitted_short_work_queue_density_max"], 7.0)
            self.assertEqual(evidence["rejected_short_work_queue_density_min"], 9.0)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)

    def test_blind_log_rejects_admission_at_queue_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v159-bad", corrupt_density=True)
            with self.assertRaisesRegex(
                RuntimeError, "slack short-work evidence changed"
            ):
                v159._audit_nash_log(
                    canonical, {"run_id": "synthetic-v159-bad", "seed": "E09"}
                )


if __name__ == "__main__":
    unittest.main()
