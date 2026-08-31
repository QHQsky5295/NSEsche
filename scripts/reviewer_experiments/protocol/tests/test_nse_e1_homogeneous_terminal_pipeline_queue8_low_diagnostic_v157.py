from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_pipeline_queue8_low_diagnostic_v156 import (
    _assert_frozen_inputs as _assert_v156_frozen_inputs,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_terminal_pipeline_queue8_low_diagnostic_v157 import (
    BINARY_PATH,
    BINARY_SHA256,
    FRONTIER,
    HIGH_EXPERT,
    IMPLEMENTATION,
    IMPLEMENTATION_SHA256,
    LOW_EXPERT,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    SEEDS,
    _audit_nash_log,
    _rewrite_candidate,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V157ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        self.assertEqual(file_hash(IMPLEMENTATION), IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(BINARY_PATH), BINARY_SHA256)
        plan = read_json(PLAN)
        implementation = read_json(IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(SEEDS))
        self.assertEqual(plan["candidate"]["player_frontier"], FRONTIER)
        self.assertTrue(
            implementation["single_scientific_change"][
                "nonterminal_pipeline_players_rejected"
            ]
        )

    def test_rewrite_is_exact_three_seed_terminal_pipeline_product(self) -> None:
        manifest = _rewrite_candidate(_assert_v156_frozen_inputs(), "b" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {PROFILE},
        )
        self.assertEqual(
            {run["metadata"]["v157_player_frontier"] for run in manifest["runs"]},
            {FRONTIER},
        )
        self.assertTrue(
            all(
                not any(key.startswith("v156_") for key in run["metadata"])
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _write_log(canonical: Path, run_id: str, *, corrupt_terminal: bool) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        path = record / "nash_metrics.jsonl.gz"
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V157",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": LOW_EXPERT,
                    "at_or_above_threshold_expert": HIGH_EXPERT,
                    "player_frontier": FRONTIER,
                    "single_change_from_v155": "parents_completed_to_parents_completed_or_terminal_parents_scheduled",
                    "terminal_pipeline_definition": "admit_all_parents-completed_players_plus_only_immutable-DAG-terminal_players_whose_parents_are_all_assigned",
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            },
            {"kind": "function_profile", "throughput": 999, "qpr": 999},
        ]
        for frame in range(1000):
            low = frame % 2 == 0
            admitted = 0 if corrupt_terminal and frame == 700 else 2
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {
                        "assignment_hash": frame,
                        "player_frontier": FRONTIER,
                        "pipeline_players_with_incomplete_parents": 1,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": FRONTIER,
                            "admitted_terminal_players_with_incomplete_parents": admitted,
                            "rejected_nonterminal_players_with_incomplete_parents": 3,
                            "terminal_topology_source": "immutable_function_children_is_empty",
                            "uses_completion_or_performance_outcomes": False,
                        },
                        "srpt_hiku2_ocs_queue_router": {
                            "enabled": True,
                            "queue_density": 7.0 if low else 9.0,
                            "queue_density_threshold": 8.0,
                            "selected_expert": LOW_EXPERT if low else HIGH_EXPERT,
                            "player_frontier": FRONTIER,
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
        with gzip.open(path, "wt", encoding="utf-8", newline="\n") as stream:
            for event in events:
                stream.write(json.dumps(event, sort_keys=True) + "\n")

    def test_blind_log_proves_terminal_admission_and_nonterminal_rejection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v157", corrupt_terminal=False)
            evidence = _audit_nash_log(
                canonical, {"run_id": "synthetic-v157", "seed": "E09"}
            )
            self.assertEqual(
                evidence["admitted_terminal_players_with_incomplete_parents"], 2000
            )
            self.assertEqual(
                evidence["rejected_nonterminal_players_with_incomplete_parents"],
                3000,
            )
            self.assertEqual(evidence["below_threshold_route_windows"], 500)
            self.assertEqual(evidence["at_or_above_threshold_route_windows"], 500)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)

    def test_blind_log_rejects_more_feasible_pipeline_than_terminal_admitted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v157-bad", corrupt_terminal=True)
            with self.assertRaisesRegex(
                RuntimeError, "terminal-pipeline evidence changed"
            ):
                _audit_nash_log(
                    canonical, {"run_id": "synthetic-v157-bad", "seed": "E09"}
                )


if __name__ == "__main__":
    unittest.main()
