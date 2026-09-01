from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_severe_queue32_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v177 as v177,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V177Concurrent2SevereQueue32CpuBoundedTerminalDiagnosticTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v177.PLAN), v177.PLAN_SHA256)
        self.assertEqual(file_hash(v177.IMPLEMENTATION), v177.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v177.BINARY_PATH), v177.BINARY_SHA256)
        plan = read_json(v177.PLAN)
        implementation = read_json(v177.IMPLEMENTATION)
        self.assertEqual(
            plan["diagnostic_design"]["fixed_execution_order"], list(v177.SEEDS)
        )
        self.assertEqual(
            plan["mechanism_only_seed_selection"]["selected_set"],
            ["E06", "E10", "E11", "E12", "E15", "E18"],
        )
        change = implementation["single_scientific_change"]
        self.assertEqual(
            change["unchanged_primary_activation"],
            "heavy_incomplete_parent_terminal_player_count_strictly_above_one",
        )
        self.assertEqual(
            change["new_severe_single_activation"],
            "heavy_incomplete_parent_terminal_player_count_equals_one_and_current_operational_queue_density_at_least_32",
        )
        self.assertEqual(change["severe_queue_density_threshold"], 32.0)
        self.assertEqual(change["severe_queue_boundary"], "at_or_above_activates")
        self.assertIn("incomplete-parent-terminal_CPU_bound", v177.TERMINAL_DEFINITION)
        self.assertEqual(
            change["active_heavy_behavior"],
            "exact_V168_all_or_none_CPU_guard_rejection",
        )
        self.assertEqual(change["active_heavy_admissions"], 0)
        manifest = v177._rewrite_candidate(v177._assert_frozen_inputs(), "c" * 40)
        v177._validate_product(manifest, references_bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v177.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 6)
        for run in manifest["runs"]:
            metadata = run["metadata"]
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], v177.PROFILE
            )
            self.assertEqual(metadata["v177_heavy_player_threshold"], 1)
            self.assertEqual(metadata["v177_minimum_active_heavy_players"], 1)
            self.assertEqual(metadata["v177_severe_queue_density_threshold"], 32.0)
            self.assertEqual(
                metadata["v177_severe_queue_density_source"],
                "current_pending_plus_runnable_tasks_per_node",
            )
            self.assertIsNone(metadata["v177_active_heavy_admission_quota"])
            self.assertFalse(metadata["v177_remaining_nine_authorized"])

    def test_hybrid_replaces_only_the_six_preregistered_rows(self) -> None:
        frozen = [
            {"load": "low", "seed": f"E{i:02d}", "source": "V170"} for i in range(1, 21)
        ]
        replacements = [
            {"load": "low", "seed": seed, "source": "V177"} for seed in v177.SEEDS
        ]
        v176_rows = [
            {"load": "low", "seed": seed, "source": "V176"}
            for seed in v177.v176base.SEEDS
        ]
        hybrid = v177._hybrid_rows(frozen, v176_rows, replacements)
        by_seed = {row["seed"]: row for row in hybrid}
        self.assertEqual(len(hybrid), 20)
        self.assertTrue(all(by_seed[seed]["source"] == "V177" for seed in v177.SEEDS))
        self.assertTrue(
            all(by_seed[seed]["source"] == "V176" for seed in v177.V176_REUSE_SEEDS)
        )
        self.assertTrue(
            all(by_seed[seed]["source"] == "V170" for seed in v177.V170_REUSE_SEEDS)
        )

    @staticmethod
    def _run_config(*, forbidden_policy: bool = False) -> dict:
        return {
            "kind": "run_config",
            "scheduler": "sche_nash",
            "operational_expert_proxy": v177.PROFILE,
            "reference": {"mode": "offline_required", "offline_load_ok": True},
            "operational_expert_proxy_contract": {
                "version": "V177",
                "queue_density_threshold": v177.QUEUE_THRESHOLD,
                "below_threshold_expert": v177.LOW_EXPERT,
                "at_or_above_threshold_expert": v177.HIGH_EXPERT,
                "player_frontier": v177.FRONTIER,
                "single_change_from_v155": v177.SINGLE_CHANGE,
                "terminal_pipeline_definition": v177.TERMINAL_DEFINITION,
                "short_work_pipeline_remaining_work_threshold": v177.SHORT_WORK_THRESHOLD,
                "short_work_pipeline_queue_density_threshold": v177.QUEUE_THRESHOLD,
                "short_work_pipeline_queue_boundary": "below_is_strict",
                "short_work_definition": v177.WORK_DEFINITION,
                "cpu_bounded_terminal_guard": {
                    "normalized_cpu_threshold": 1.0,
                    "boundary": "at_or_below_is_admitted",
                    "numerator": "immutable_function_cpu_work",
                    "denominator": "current_cluster_mean_node_cpu_capacity",
                    "parents_completed_bypass": True,
                    "uses_completion_or_performance_outcomes": False,
                    "capacity_overload_activation": {
                        "heavy_player_definition": "collectable_incomplete-parent_terminal_player_with_immutable_function_cpu_work_over_current_cluster_mean_node_cpu_capacity_strictly_above_one",
                        "capacity_threshold": "fixed_one_current_heavy_player",
                        "fixed_heavy_player_count_threshold": 1,
                        "minimum_active_heavy_player_count": 1,
                        "activation_boundary": "heavy_player_count_strictly_above_one_or_exactly_one_with_operational_queue_density_at_least_32",
                        "severe_single_queue_density_threshold": 32.0,
                        "severe_single_queue_density_source": "current_pending_plus_runnable_tasks_per_node",
                        "severe_single_queue_boundary": "at_or_above_activates",
                        "inactive_behavior": "V159_terminal_admission",
                        "active_heavy_admission_policy": (
                            "forbidden" if forbidden_policy else None
                        ),
                        "active_heavy_admission_quota": None,
                        "active_heavy_admission_quota_unit": None,
                        "quota_selection_order": None,
                        "uses_seed_load_dag_function_or_performance_labels": False,
                    },
                },
                "uses_completed_request_outcomes": False,
                "reference_policy_independent": True,
            },
        }

    @staticmethod
    def _window(frame: int, *, violate_boundary: bool = False) -> dict:
        if frame == 0:
            heavy, density = 0, 7.0
        elif frame == 1:
            heavy, density = 1, 31.999
        elif frame == 2:
            heavy, density = 1, 32.0
        else:
            heavy, density = 2, 7.0 if frame % 2 == 0 else 8.0
        primary_active = heavy > 1
        severe_single_active = heavy == 1 and density >= 32.0
        active = primary_active or severe_single_active
        if violate_boundary and frame == 1:
            active = True
        low_route = density < 8.0
        terminal = 1
        short = 1 if low_route else 0
        rejected = 0 if low_route else 1
        return {
            "kind": "window",
            "frame": frame,
            "decision": {
                "assignment_hash": frame if frame < 2 else frame + 10_000,
                "player_frontier": v177.FRONTIER,
                "pipeline_players_with_incomplete_parents": terminal + short,
                "pipeline_observation_fields_drive_future_windows": False,
                "terminal_pipeline_frontier": {
                    "enabled": True,
                    "definition": v177.FRONTIER,
                    "short_work_remaining_work_threshold": v177.SHORT_WORK_THRESHOLD,
                    "terminal_topology_source": "immutable_function_children_is_empty",
                    "uses_completion_or_performance_outcomes": False,
                    "admitted_terminal_players_with_incomplete_parents": terminal,
                    "admitted_short_work_nonterminal_players_with_incomplete_parents": short,
                    "rejected_nonterminal_players_with_incomplete_parents": rejected,
                    "admitted_short_work_remaining_work_max": 5.0
                    if low_route
                    else None,
                    "rejected_nonterminal_remaining_work_min": (
                        None if low_route else 6.0
                    ),
                    "cpu_bounded_terminal_guard": {
                        "enabled": True,
                        "normalized_cpu_threshold": 1.0,
                        "boundary": "at_or_below_is_admitted",
                        "admitted_incomplete_parent_terminal_players": terminal,
                        "rejected_heavy_incomplete_parent_terminal_players": (
                            heavy if active else 0
                        ),
                        "parents_completed_heavy_terminal_bypass_players": 1,
                        "admitted_normalized_cpu_max": (
                            0.5 if active or heavy == 0 else 2.0
                        ),
                        "rejected_normalized_cpu_min": 2.1 if active else None,
                        "numerator": "immutable_function_cpu_work",
                        "denominator": "current_cluster_mean_node_cpu_capacity",
                        "uses_completion_or_performance_outcomes": False,
                        "capacity_overload_activation": {
                            "enabled": True,
                            "heavy_incomplete_parent_terminal_players": heavy,
                            "node_count_threshold": 20,
                            "heavy_player_count_threshold": 1,
                            "minimum_active_heavy_player_count": 1,
                            "threshold_kind": "fixed_one_current_heavy_player",
                            "activation_boundary": "heavy_count_strictly_above_one_or_exactly_one_with_queue_density_at_or_above_32_activates",
                            "operational_queue_density": density,
                            "operational_queue_density_source": "current_pending_plus_runnable_tasks_per_node",
                            "primary_heavy_count_activation": primary_active,
                            "severe_single_queue_density_threshold": 32.0,
                            "severe_single_queue_boundary": "at_or_above_activates",
                            "severe_single_activation": severe_single_active,
                            "guard_active": active,
                            "guard_inactive": not active,
                            "guard_inactive_heavy_terminal_admissions": (
                                0 if active else heavy
                            ),
                            "active_heavy_admission_policy": None,
                            "active_heavy_admission_quota": None,
                            "active_heavy_admission_quota_unit": None,
                            "active_heavy_quota_selected_players": None,
                            "active_heavy_quota_admitted_players": None,
                            "active_heavy_quota_rejected_excess_players": None,
                            "active_heavy_selected_request_count": None,
                            "active_heavy_selected_request_candidate_players": None,
                            "quota_selection_order": None,
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
                        v177.LOW_EXPERT if low_route else v177.HIGH_EXPERT
                    ),
                    "player_frontier": v177.FRONTIER,
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
        violate_boundary: bool = False,
        forbidden_policy: bool = False,
    ) -> None:
        path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
        path.parent.mkdir(parents=True)
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            stream.write(
                json.dumps(self._run_config(forbidden_policy=forbidden_policy)) + "\n"
            )
            for frame in range(1000):
                stream.write(
                    json.dumps(
                        self._window(frame, violate_boundary=violate_boundary),
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

    def test_result_blind_audit_locks_severe_single_and_primary_boundaries(
        self,
    ) -> None:
        frozen = tuple(range(1000))
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "run")
            audit = v177._audit_nash_log(
                canonical,
                {"run_id": "run", "seed": "E01"},
                frozen_base=frozen,
            )
        self.assertEqual(audit["first_severe_exact_one_frame"], 2)
        self.assertEqual(audit["first_assignment_mismatch_frame_vs_base"], 2)
        self.assertTrue(
            audit["pre_first_severe_exact_one_assignment_prefix_matches_base"]
        )
        self.assertTrue(
            audit["first_severe_exact_one_frame_assignment_differs_from_base"]
        )
        self.assertEqual(audit["capacity_overload_exact_one_windows"], 2)
        self.assertEqual(
            audit["capacity_overload_severe_exact_one_heavy_terminal_rejections"], 1
        )
        self.assertEqual(
            audit["capacity_overload_ordinary_exact_one_heavy_terminal_admissions"], 1
        )
        self.assertEqual(audit["capacity_overload_exact_two_windows"], 997)
        self.assertEqual(
            audit["capacity_overload_exact_two_heavy_terminal_rejections"], 1994
        )
        audits = [{**audit, "seed": seed} for seed in v177.SEEDS]
        mechanism = v177._mechanism_falsification_gate(audits)
        self.assertTrue(mechanism["pass"])
        self.assertTrue(
            mechanism[
                "severe_exact_one_and_exact_two_rejected_ordinary_exact_one_admitted"
            ]
        )

    def test_result_blind_audit_rejects_active_exact_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "run", violate_boundary=True)
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v177._audit_nash_log(
                    canonical,
                    {"run_id": "run", "seed": "E01"},
                    frozen_base=tuple(range(1000)),
                )

    def test_result_blind_audit_rejects_any_active_admission_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "run", forbidden_policy=True)
            with self.assertRaisesRegex(RuntimeError, "run_config contract changed"):
                v177._audit_nash_log(
                    canonical,
                    {"run_id": "run", "seed": "E01"},
                    frozen_base=tuple(range(1000)),
                )


if __name__ == "__main__":
    unittest.main()
