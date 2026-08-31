from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_pipeline_queue8_low_diagnostic_v156 import (
    BINARY_PATH,
    BINARY_SHA256,
    HIGH_EXPERT,
    IMPLEMENTATION,
    IMPLEMENTATION_SHA256,
    LOW_EXPERT,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    SEEDS,
    _audit_nash_log,
    _hybrid_rows,
    _rewrite_candidate,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_queue8_low_training_v155 import (
    _assert_frozen_inputs,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V156ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_binary_contract(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        self.assertEqual(file_hash(IMPLEMENTATION), IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(BINARY_PATH), BINARY_SHA256)
        plan = read_json(PLAN)
        implementation = read_json(IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(SEEDS))
        self.assertEqual(plan["candidate"]["profile"], PROFILE)
        self.assertEqual(
            implementation["single_scientific_change"]["to_player_frontier"],
            "parents_scheduled",
        )
        self.assertTrue(
            implementation["single_scientific_change"]["unchanged_v155_router"]
        )

    def test_rewrite_is_exact_three_seed_nse_product(self) -> None:
        manifest = _rewrite_candidate(_assert_frozen_inputs(), "a" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(SEEDS))
        self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertFalse(manifest["all_references_bound"])
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {PROFILE},
        )
        self.assertEqual(
            {run["metadata"]["v156_player_frontier"] for run in manifest["runs"]},
            {"parents_scheduled"},
        )

    @staticmethod
    def _write_log(canonical: Path, run_id: str, *, corrupt_frontier: bool) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        path = record / "nash_metrics.jsonl.gz"
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": PROFILE,
                "operational_direct_initialization": True,
                "operational_unrestricted_initialization": True,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V156",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": LOW_EXPERT,
                    "at_or_above_threshold_expert": HIGH_EXPERT,
                    "player_frontier": "parents_scheduled",
                    "single_change_from_v155": "parents_completed_to_parents_scheduled",
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            },
            {
                "kind": "function_profile",
                "throughput": 999999,
                "latency": -999999,
                "qpr": 123456,
            },
        ]
        for frame in range(1000):
            low = frame % 2 == 0
            frontier = (
                "parents_completed"
                if corrupt_frontier and frame == 700
                else "parents_scheduled"
            )
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {
                        "assignment_hash": frame,
                        "request_function_players": 3,
                        "player_frontier": frontier,
                        "dependency_pipeline_player_count": 3,
                        "pipeline_players_with_incomplete_parents": 1,
                        "ready_players_with_all_parents_done": 2,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "srpt_hiku2_ocs_queue_router": {
                            "enabled": True,
                            "queue_density": 7.0 if low else 9.0,
                            "queue_density_threshold": 8.0,
                            "selected_expert": LOW_EXPERT if low else HIGH_EXPERT,
                            "player_frontier": "parents_scheduled",
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

    def test_blind_log_audit_proves_pipeline_ahead_and_both_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v156", corrupt_frontier=False)
            evidence = _audit_nash_log(
                canonical, {"run_id": "synthetic-v156", "seed": "E09"}
            )
            self.assertEqual(evidence["windows"], 1000)
            self.assertEqual(evidence["pipeline_players_with_incomplete_parents"], 1000)
            self.assertEqual(evidence["below_threshold_route_windows"], 500)
            self.assertEqual(evidence["at_or_above_threshold_route_windows"], 500)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)
            self.assertEqual(
                evidence["function_profile_records_seen_without_payload_access"], 1
            )

    def test_blind_log_audit_rejects_nonpipeline_frontier_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v156-bad", corrupt_frontier=True)
            with self.assertRaisesRegex(
                RuntimeError, "dependency-pipeline frontier evidence changed"
            ):
                _audit_nash_log(
                    canonical, {"run_id": "synthetic-v156-bad", "seed": "E09"}
                )

    def test_hybrid_replaces_only_diagnostic_seeds(self) -> None:
        v155 = [
            {"seed": f"E{index:02d}", "run_id": f"v155-{index}", "throughput": index}
            for index in range(1, 21)
        ]
        v156 = [
            {"seed": seed, "run_id": f"v156-{seed}", "throughput": 999}
            for seed in SEEDS
        ]
        hybrid = _hybrid_rows(v155, v156)
        self.assertEqual(len(hybrid), 20)
        for row in hybrid:
            self.assertEqual(row["run_id"].startswith("v156-"), row["seed"] in SEEDS)


if __name__ == "__main__":
    unittest.main()
