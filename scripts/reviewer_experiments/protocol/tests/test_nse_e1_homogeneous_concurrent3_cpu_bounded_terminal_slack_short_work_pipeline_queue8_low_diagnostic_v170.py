from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v170 as v170,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V170Concurrent3CpuBoundedTerminalDiagnosticTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v170.PLAN), v170.PLAN_SHA256)
        self.assertEqual(file_hash(v170.IMPLEMENTATION), v170.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v170.BINARY_PATH), v170.BINARY_SHA256)
        plan = read_json(v170.PLAN)
        implementation = read_json(v170.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v170.SEEDS))
        change = implementation["single_scientific_change"]
        self.assertEqual(change["activation_boundary"], "strictly_above_activates")
        self.assertEqual(change["new_activation_threshold"], 2)
        self.assertEqual(change["minimum_active_count"], 3)
        self.assertEqual(change["inactive_behavior"], "exact_V159_terminal_admission")
        self.assertEqual(
            v170.TERMINAL_DEFINITION,
            "admit_all_parents-completed_players;activate_the_V168_incomplete-"
            "parent_terminal_CPU_bound_only_when_current_heavy_terminal_player_"
            "count_strictly_exceeds_two;otherwise_retain_V159_terminal_admission;"
            "retain_V159_nonterminal_short-work_frontier",
        )
        manifest = v170._rewrite_candidate(v170._assert_frozen_inputs(), "c" * 40)
        v170._validate_product(manifest, references_bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v170.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] == v170.PROFILE
                and run["metadata"]["v170_cpu_threshold"] == 1.0
                and run["metadata"]["v170_heavy_player_threshold"] == 2
                and run["metadata"]["v170_minimum_active_heavy_players"] == 3
                and run["metadata"]["v170_overload_activation_boundary"]
                == "strictly_above_activates"
                and run["metadata"]["v170_remaining_seventeen_authorized"] is False
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _run_config() -> dict:
        return {
            "kind": "run_config",
            "scheduler": "sche_nash",
            "operational_expert_proxy": v170.PROFILE,
            "reference": {"mode": "offline_required", "offline_load_ok": True},
            "operational_expert_proxy_contract": {
                "version": "V170",
                "queue_density_threshold": v170.QUEUE_THRESHOLD,
                "below_threshold_expert": v170.LOW_EXPERT,
                "at_or_above_threshold_expert": v170.HIGH_EXPERT,
                "player_frontier": v170.FRONTIER,
                "single_change_from_v155": v170.SINGLE_CHANGE,
                "terminal_pipeline_definition": v170.TERMINAL_DEFINITION,
                "short_work_pipeline_remaining_work_threshold": v170.SHORT_WORK_THRESHOLD,
                "short_work_pipeline_queue_density_threshold": v170.QUEUE_THRESHOLD,
                "short_work_pipeline_queue_boundary": "below_is_strict",
                "short_work_definition": v170.WORK_DEFINITION,
                "cpu_bounded_terminal_guard": {
                    "normalized_cpu_threshold": 1.0,
                    "boundary": "at_or_below_is_admitted",
                    "numerator": "immutable_function_cpu_work",
                    "denominator": "current_cluster_mean_node_cpu_capacity",
                    "parents_completed_bypass": True,
                    "uses_completion_or_performance_outcomes": False,
                    "capacity_overload_activation": {
                        "heavy_player_definition": "collectable_incomplete-parent_terminal_player_with_immutable_function_cpu_work_over_current_cluster_mean_node_cpu_capacity_strictly_above_one",
                        "capacity_threshold": "fixed_two_current_heavy_players",
                        "fixed_heavy_player_count_threshold": 2,
                        "minimum_active_heavy_player_count": 3,
                        "activation_boundary": "heavy_player_count_strictly_above_two",
                        "inactive_behavior": "V159_terminal_admission",
                        "uses_seed_load_dag_function_or_performance_labels": False,
                    },
                },
                "uses_completed_request_outcomes": False,
                "reference_policy_independent": True,
            },
        }

    @staticmethod
    def _window(
        frame: int,
        *,
        guard_active: bool,
        assignment_hash: int,
        active_admitted_ratio: float = 1.0,
    ) -> dict:
        low_route = frame % 2 == 0
        density = 7.0 if low_route else 8.0
        terminal = 1
        short = 1 if low_route else 0
        heavy = 3 if guard_active else 1
        return {
            "kind": "window",
            "frame": frame,
            "decision": {
                "assignment_hash": assignment_hash,
                "player_frontier": v170.FRONTIER,
                "pipeline_players_with_incomplete_parents": terminal + short,
                "pipeline_observation_fields_drive_future_windows": False,
                "terminal_pipeline_frontier": {
                    "enabled": True,
                    "definition": v170.FRONTIER,
                    "short_work_remaining_work_threshold": v170.SHORT_WORK_THRESHOLD,
                    "terminal_topology_source": "immutable_function_children_is_empty",
                    "uses_completion_or_performance_outcomes": False,
                    "admitted_terminal_players_with_incomplete_parents": terminal,
                    "admitted_short_work_nonterminal_players_with_incomplete_parents": short,
                    "rejected_nonterminal_players_with_incomplete_parents": (
                        0 if low_route else 2
                    ),
                    "admitted_short_work_remaining_work_max": (
                        5.0 if low_route else None
                    ),
                    "rejected_nonterminal_remaining_work_min": (
                        None if low_route else 6.0
                    ),
                    "cpu_bounded_terminal_guard": {
                        "enabled": True,
                        "normalized_cpu_threshold": 1.0,
                        "boundary": "at_or_below_is_admitted",
                        "admitted_incomplete_parent_terminal_players": terminal,
                        "rejected_heavy_incomplete_parent_terminal_players": (
                            heavy if guard_active else 0
                        ),
                        "parents_completed_heavy_terminal_bypass_players": 1,
                        "admitted_normalized_cpu_max": (
                            active_admitted_ratio if guard_active else 1.0001
                        ),
                        "rejected_normalized_cpu_min": 2.1 if guard_active else None,
                        "numerator": "immutable_function_cpu_work",
                        "denominator": "current_cluster_mean_node_cpu_capacity",
                        "uses_completion_or_performance_outcomes": False,
                        "capacity_overload_activation": {
                            "enabled": True,
                            "heavy_incomplete_parent_terminal_players": heavy,
                            "node_count_threshold": 20,
                            "heavy_player_count_threshold": 2,
                            "minimum_active_heavy_player_count": 3,
                            "threshold_kind": "fixed_two_current_heavy_players",
                            "activation_boundary": "strictly_above_activates",
                            "guard_active": guard_active,
                            "guard_inactive": not guard_active,
                            "guard_inactive_heavy_terminal_admissions": (
                                0 if guard_active else heavy
                            ),
                            "uses_seed_load_dag_function_or_performance_labels": False,
                        },
                    },
                    "short_work_queue_gate": {
                        "enabled": True,
                        "threshold": 8.0,
                        "boundary": "below_is_strict",
                        "rejected_short_work_at_or_above_threshold": (
                            0 if low_route else 1
                        ),
                        "admitted_short_work_queue_density_max": (
                            7.0 if low_route else None
                        ),
                        "rejected_short_work_queue_density_min": (
                            None if low_route else 8.0
                        ),
                    },
                },
                "srpt_hiku2_ocs_queue_router": {
                    "enabled": True,
                    "queue_density": density,
                    "queue_density_threshold": 8.0,
                    "selected_expert": (
                        v170.LOW_EXPERT if low_route else v170.HIGH_EXPERT
                    ),
                    "player_frontier": v170.FRONTIER,
                    "dependency_pipeline_frontier": True,
                    "uses_completion_outcomes": False,
                },
            },
            "social": {
                "reference_state_key": f"key-{frame}",
                "reference_source": "offline_table",
            },
        }

    def _write_log(
        self,
        canonical: Path,
        run_id: str,
        *,
        first_active_frame: int | None,
        active_admitted_ratio: float = 1.0,
        violate_exact_threshold: bool = False,
    ) -> None:
        path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
        path.parent.mkdir(parents=True)
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            stream.write(json.dumps(self._run_config()) + "\n")
            for frame in range(1000):
                active = first_active_frame is not None and frame >= first_active_frame
                assignment_hash = frame if not active else frame + 10_000
                event = self._window(
                    frame,
                    guard_active=active,
                    assignment_hash=assignment_hash,
                    active_admitted_ratio=active_admitted_ratio,
                )
                if violate_exact_threshold and frame == 0:
                    guard = event["decision"]["terminal_pipeline_frontier"][
                        "cpu_bounded_terminal_guard"
                    ]
                    activation = guard["capacity_overload_activation"]
                    activation["heavy_incomplete_parent_terminal_players"] = 2
                    activation["guard_active"] = True
                    activation["guard_inactive"] = False
                    activation["guard_inactive_heavy_terminal_admissions"] = 0
                    guard["rejected_heavy_incomplete_parent_terminal_players"] = 2
                    guard["rejected_normalized_cpu_min"] = 2.1
                    guard["admitted_normalized_cpu_max"] = 1.0
                stream.write(json.dumps(event, sort_keys=True) + "\n")
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

    def test_blind_gate_requires_exact_inactive_sequences_and_e20_divergence(
        self,
    ) -> None:
        frozen = tuple(range(1000))
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v170, "_frozen_v159_assignment_hashes", return_value=frozen
        ):
            root = Path(directory)
            audits = []
            for seed in v170.SEEDS:
                run_id = f"synthetic-v170-{seed}"
                canonical = root / seed
                self._write_log(
                    canonical,
                    run_id,
                    first_active_frame=24 if seed == "E20" else None,
                )
                audits.append(
                    v170._audit_nash_log(canonical, {"run_id": run_id, "seed": seed})
                )
            gate = v170._mechanism_falsification_gate(audits)
            self.assertTrue(gate["pass"])
            self.assertTrue(gate["e09_e18_exact_v159_inactive_assignment_sequences"])
            self.assertTrue(gate["e20_pre_activation_exact_v159_then_diverged"])
            self.assertEqual(gate["e20_first_guard_active_frame"], 24)
            self.assertGreater(
                gate["e20_post_activation_assignment_mismatch_count_vs_v159"], 0
            )
            self.assertGreater(
                gate["cpu_guard_inactive_admitted_normalized_cpu_max"], 1.0
            )
            self.assertEqual(gate["cpu_guard_active_admitted_normalized_cpu_max"], 1.0)

    def test_blind_audit_rejects_active_admitted_ratio_above_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v170, "_frozen_v159_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v170",
                first_active_frame=0,
                active_admitted_ratio=1.0001,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v170._audit_nash_log(
                    canonical, {"run_id": "synthetic-v170", "seed": "E20"}
                )

    def test_blind_audit_rejects_activation_at_exact_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v170, "_frozen_v159_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v170",
                first_active_frame=None,
                violate_exact_threshold=True,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v170._audit_nash_log(
                    canonical, {"run_id": "synthetic-v170", "seed": "E09"}
                )

    def test_mechanism_gate_rejects_any_e09_activation(self) -> None:
        count_keys = (
            "admitted_terminal_players_with_incomplete_parents",
            "admitted_slack_short_work_nonterminal_players",
            "rejected_frontier_players_with_incomplete_parents",
            "rejected_short_work_at_or_above_queue_threshold",
            "cpu_guard_admitted_incomplete_parent_terminal_players",
            "cpu_guard_rejected_heavy_incomplete_parent_terminal_players",
            "cpu_guard_parent_completed_heavy_terminal_bypass_players",
            "capacity_overload_heavy_incomplete_parent_terminal_players",
            "capacity_overload_guard_active_windows",
            "capacity_overload_guard_inactive_windows",
            "capacity_overload_guard_inactive_heavy_terminal_admissions",
            "below_threshold_route_windows",
            "at_or_above_threshold_route_windows",
        )
        base = {key: 1 for key in count_keys}
        base.update(
            {
                "cpu_guard_admitted_normalized_cpu_max": 1.1,
                "cpu_guard_active_admitted_normalized_cpu_max": 1.0,
                "cpu_guard_inactive_admitted_normalized_cpu_max": 1.1,
                "cpu_guard_rejected_normalized_cpu_min": 2.0,
                "admitted_short_work_remaining_work_max": 5.0,
                "rejected_over_threshold_remaining_work_min": 6.0,
                "admitted_short_work_queue_density_max": 7.0,
                "rejected_short_work_queue_density_min": 8.0,
                "assignment_sequence_sha256": "same",
                "frozen_v159_assignment_sequence_sha256": "same",
                "assignment_mismatch_count_vs_v159": 0,
                "first_guard_active_frame": None,
                "pre_activation_assignment_prefix_matches_v159": True,
                "post_activation_assignment_mismatch_count_vs_v159": 0,
            }
        )
        audits = []
        for seed in v170.SEEDS:
            audit = {**base, "seed": seed}
            if seed == "E20":
                audit.update(
                    {
                        "first_guard_active_frame": 24,
                        "post_activation_assignment_mismatch_count_vs_v159": 1,
                    }
                )
            audits.append(audit)
        self.assertFalse(v170._mechanism_falsification_gate(audits)["pass"])


if __name__ == "__main__":
    unittest.main()
