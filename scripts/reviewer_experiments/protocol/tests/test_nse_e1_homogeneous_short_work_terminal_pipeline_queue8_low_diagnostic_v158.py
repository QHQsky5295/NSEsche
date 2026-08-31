from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_terminal_pipeline_queue8_low_diagnostic_v157 import (
    _assert_frozen_inputs as _assert_v157_frozen_inputs,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_short_work_terminal_pipeline_queue8_low_diagnostic_v158 import (
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
    SHORT_WORK_THRESHOLD,
    SINGLE_CHANGE,
    TERMINAL_DEFINITION,
    WORK_DEFINITION,
    _audit_nash_log,
    _rewrite_candidate,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V158ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        self.assertEqual(file_hash(IMPLEMENTATION), IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(BINARY_PATH), BINARY_SHA256)
        plan = read_json(PLAN)
        implementation = read_json(IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(SEEDS))
        self.assertEqual(plan["candidate"]["player_frontier"], FRONTIER)
        self.assertEqual(plan["threshold_derivation"]["frozen_threshold"], 5.5)
        self.assertEqual(
            implementation["single_scientific_change"][
                "short_work_remaining_work_threshold"
            ],
            SHORT_WORK_THRESHOLD,
        )

    def test_rewrite_is_exact_three_seed_short_work_pipeline_product(self) -> None:
        manifest = _rewrite_candidate(_assert_v157_frozen_inputs(), "c" * 40)
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
            {run["metadata"]["v158_player_frontier"] for run in manifest["runs"]},
            {FRONTIER},
        )
        self.assertEqual(
            {run["metadata"]["v158_short_work_threshold"] for run in manifest["runs"]},
            {SHORT_WORK_THRESHOLD},
        )
        self.assertTrue(
            all(
                not any(key.startswith("v157_") for key in run["metadata"])
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _write_log(canonical: Path, run_id: str, *, corrupt_work: bool) -> None:
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
                    "version": "V158",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": LOW_EXPERT,
                    "at_or_above_threshold_expert": HIGH_EXPERT,
                    "player_frontier": FRONTIER,
                    "single_change_from_v155": SINGLE_CHANGE,
                    "terminal_pipeline_definition": TERMINAL_DEFINITION,
                    "short_work_pipeline_remaining_work_threshold": 5.5,
                    "short_work_definition": WORK_DEFINITION,
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            },
            {"kind": "function_profile", "throughput": 999, "qpr": 999},
        ]
        for frame in range(1000):
            low = frame % 2 == 0
            admitted_max = 5.6 if corrupt_work and frame == 700 else 5.5
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {
                        "assignment_hash": frame,
                        "player_frontier": FRONTIER,
                        "pipeline_players_with_incomplete_parents": 3,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": FRONTIER,
                            "admitted_terminal_players_with_incomplete_parents": 1,
                            "rejected_nonterminal_players_with_incomplete_parents": 3,
                            "short_work_remaining_work_threshold": 5.5,
                            "admitted_short_work_nonterminal_players_with_incomplete_parents": 2,
                            "admitted_short_work_remaining_work_max": admitted_max,
                            "rejected_nonterminal_remaining_work_min": 5.501,
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

    def test_blind_log_proves_thresholded_admission_and_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v158", corrupt_work=False)
            evidence = _audit_nash_log(
                canonical, {"run_id": "synthetic-v158", "seed": "E09"}
            )
            self.assertEqual(
                evidence[
                    "admitted_short_work_nonterminal_players_with_incomplete_parents"
                ],
                2000,
            )
            self.assertEqual(evidence["admitted_short_work_remaining_work_max"], 5.5)
            self.assertEqual(evidence["rejected_nonterminal_remaining_work_min"], 5.501)
            self.assertEqual(evidence["below_threshold_route_windows"], 500)
            self.assertEqual(evidence["at_or_above_threshold_route_windows"], 500)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)

    def test_blind_log_rejects_admitted_work_above_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v158-bad", corrupt_work=True)
            with self.assertRaisesRegex(
                RuntimeError, "short-work pipeline evidence changed"
            ):
                _audit_nash_log(
                    canonical, {"run_id": "synthetic-v158-bad", "seed": "E09"}
                )


if __name__ == "__main__":
    unittest.main()
