from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v168 as v168,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V168CpuBoundedTerminalDiagnosticTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v168.PLAN), v168.PLAN_SHA256)
        self.assertEqual(file_hash(v168.IMPLEMENTATION), v168.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v168.BINARY_PATH), v168.BINARY_SHA256)
        plan = read_json(v168.PLAN)
        implementation = read_json(v168.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v168.SEEDS))
        self.assertEqual(
            implementation["single_scientific_change"]["to_player_frontier"],
            v168.FRONTIER,
        )
        self.assertEqual(
            implementation["single_scientific_change"]["normalized_cpu_threshold"],
            1.0,
        )
        manifest = v168._rewrite_candidate(v168._assert_frozen_inputs(), "c" * 40)
        v168._validate_product(manifest, references_bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v168.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] == v168.PROFILE
                and run["metadata"]["v168_cpu_threshold"] == 1.0
                and run["metadata"]["v168_remaining_seventeen_authorized"] is False
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _run_config() -> dict:
        return {
            "kind": "run_config",
            "scheduler": "sche_nash",
            "operational_expert_proxy": v168.PROFILE,
            "reference": {"mode": "offline_required", "offline_load_ok": True},
            "operational_expert_proxy_contract": {
                "version": "V168",
                "queue_density_threshold": v168.QUEUE_THRESHOLD,
                "below_threshold_expert": v168.LOW_EXPERT,
                "at_or_above_threshold_expert": v168.HIGH_EXPERT,
                "player_frontier": v168.FRONTIER,
                "single_change_from_v155": v168.SINGLE_CHANGE,
                "terminal_pipeline_definition": v168.TERMINAL_DEFINITION,
                "short_work_pipeline_remaining_work_threshold": (
                    v168.SHORT_WORK_THRESHOLD
                ),
                "short_work_pipeline_queue_density_threshold": v168.QUEUE_THRESHOLD,
                "short_work_pipeline_queue_boundary": "below_is_strict",
                "short_work_definition": v168.WORK_DEFINITION,
                "cpu_bounded_terminal_guard": {
                    "normalized_cpu_threshold": 1.0,
                    "boundary": "at_or_below_is_admitted",
                    "numerator": "immutable_function_cpu_work",
                    "denominator": "current_cluster_mean_node_cpu_capacity",
                    "parents_completed_bypass": True,
                    "uses_completion_or_performance_outcomes": False,
                },
                "uses_completed_request_outcomes": False,
                "reference_policy_independent": True,
            },
        }

    @staticmethod
    def _window(frame: int, *, admitted_ratio: float = 1.0) -> dict:
        low = frame % 2 == 0
        density = 7.0 if low else 8.0
        terminal = 1 if low else 0
        short = 1 if low else 0
        return {
            "kind": "window",
            "frame": frame,
            "decision": {
                "assignment_hash": frame,
                "player_frontier": v168.FRONTIER,
                "pipeline_players_with_incomplete_parents": terminal + short,
                "pipeline_observation_fields_drive_future_windows": False,
                "terminal_pipeline_frontier": {
                    "enabled": True,
                    "definition": v168.FRONTIER,
                    "short_work_remaining_work_threshold": v168.SHORT_WORK_THRESHOLD,
                    "terminal_topology_source": "immutable_function_children_is_empty",
                    "uses_completion_or_performance_outcomes": False,
                    "admitted_terminal_players_with_incomplete_parents": terminal,
                    "admitted_short_work_nonterminal_players_with_incomplete_parents": short,
                    "rejected_nonterminal_players_with_incomplete_parents": (
                        0 if low else 2
                    ),
                    "admitted_short_work_remaining_work_max": 5.0 if low else None,
                    "rejected_nonterminal_remaining_work_min": None if low else 6.0,
                    "cpu_bounded_terminal_guard": {
                        "enabled": True,
                        "normalized_cpu_threshold": 1.0,
                        "boundary": "at_or_below_is_admitted",
                        "admitted_incomplete_parent_terminal_players": terminal,
                        "rejected_heavy_incomplete_parent_terminal_players": (
                            0 if low else 1
                        ),
                        "parents_completed_heavy_terminal_bypass_players": 1,
                        "admitted_normalized_cpu_max": (
                            admitted_ratio if low else None
                        ),
                        "rejected_normalized_cpu_min": None if low else 2.1,
                        "numerator": "immutable_function_cpu_work",
                        "denominator": "current_cluster_mean_node_cpu_capacity",
                        "uses_completion_or_performance_outcomes": False,
                    },
                    "short_work_queue_gate": {
                        "enabled": True,
                        "threshold": 8.0,
                        "boundary": "below_is_strict",
                        "rejected_short_work_at_or_above_threshold": (0 if low else 1),
                        "admitted_short_work_queue_density_max": 7.0 if low else None,
                        "rejected_short_work_queue_density_min": None if low else 8.0,
                    },
                },
                "srpt_hiku2_ocs_queue_router": {
                    "enabled": True,
                    "queue_density": density,
                    "queue_density_threshold": 8.0,
                    "selected_expert": v168.LOW_EXPERT if low else v168.HIGH_EXPERT,
                    "player_frontier": v168.FRONTIER,
                    "dependency_pipeline_frontier": True,
                    "uses_completion_outcomes": False,
                },
            },
            "social": {
                "reference_state_key": f"key-{frame}",
                "reference_source": "offline_table",
            },
        }

    def _write_log(self, canonical: Path, *, admitted_ratio: float = 1.0) -> None:
        run_id = "synthetic-v168"
        path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
        path.parent.mkdir(parents=True)
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            stream.write(json.dumps(self._run_config()) + "\n")
            for frame in range(1000):
                stream.write(
                    json.dumps(
                        self._window(frame, admitted_ratio=admitted_ratio),
                        sort_keys=True,
                    )
                    + "\n"
                )
            stream.write(
                json.dumps(
                    {
                        "kind": "run_summary",
                        "scheduler": "sche_nash",
                        "windows": 1000,
                        "observation_writer_error": None,
                    }
                )
                + "\n"
            )

    def test_blind_audit_accepts_closed_cpu_boundary_and_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical)
            evidence = v168._audit_nash_log(
                canonical, {"run_id": "synthetic-v168", "seed": "E09"}
            )
            gate = v168._mechanism_falsification_gate([evidence])
            self.assertTrue(gate["pass"])
            self.assertEqual(evidence["cpu_guard_admitted_normalized_cpu_max"], 1.0)
            self.assertGreater(evidence["cpu_guard_rejected_normalized_cpu_min"], 1.0)
            self.assertGreater(
                evidence["cpu_guard_parent_completed_heavy_terminal_bypass_players"],
                0,
            )
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)

    def test_blind_audit_rejects_admitted_ratio_above_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, admitted_ratio=1.0001)
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v168._audit_nash_log(
                    canonical, {"run_id": "synthetic-v168", "seed": "E09"}
                )


if __name__ == "__main__":
    unittest.main()
