from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v176 as v176,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V176Concurrent2CpuBoundedTerminalDiagnosticTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v176.PLAN), v176.PLAN_SHA256)
        self.assertEqual(file_hash(v176.IMPLEMENTATION), v176.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v176.BINARY_PATH), v176.BINARY_SHA256)
        plan = read_json(v176.PLAN)
        implementation = read_json(v176.IMPLEMENTATION)
        self.assertEqual(
            plan["diagnostic_design"]["fixed_execution_order"], list(v176.SEEDS)
        )
        self.assertEqual(
            plan["mechanism_only_seed_selection"]["ranked_selected_set"],
            ["E01", "E07", "E14", "E05", "E08", "E10"],
        )
        change = implementation["single_scientific_change"]
        self.assertEqual(change["new_activation_threshold"], 1)
        self.assertEqual(change["new_minimum_active_count"], 2)
        self.assertEqual(
            change["active_heavy_behavior"],
            "exact_V168_all_or_none_CPU_guard_rejection",
        )
        self.assertEqual(change["active_heavy_admissions"], 0)
        manifest = v176._rewrite_candidate(v176._assert_frozen_inputs(), "c" * 40)
        v176._validate_product(manifest, references_bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v176.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 6)
        for run in manifest["runs"]:
            metadata = run["metadata"]
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], v176.PROFILE
            )
            self.assertEqual(metadata["v176_heavy_player_threshold"], 1)
            self.assertEqual(metadata["v176_minimum_active_heavy_players"], 2)
            self.assertIsNone(metadata["v176_active_heavy_admission_quota"])
            self.assertFalse(metadata["v176_remaining_fourteen_authorized"])

    def test_hybrid_replaces_only_the_six_preregistered_rows(self) -> None:
        frozen = [
            {"load": "low", "seed": f"E{i:02d}", "source": "V170"} for i in range(1, 21)
        ]
        replacements = [
            {"load": "low", "seed": seed, "source": "V176"} for seed in v176.SEEDS
        ]
        hybrid = v176._hybrid_rows(frozen, replacements)
        by_seed = {row["seed"]: row for row in hybrid}
        self.assertEqual(len(hybrid), 20)
        self.assertTrue(all(by_seed[seed]["source"] == "V176" for seed in v176.SEEDS))
        self.assertTrue(
            all(
                by_seed[f"E{i:02d}"]["source"] == "V170"
                for i in range(1, 21)
                if f"E{i:02d}" not in v176.SEEDS
            )
        )

    @staticmethod
    def _run_config(*, forbidden_policy: bool = False) -> dict:
        return {
            "kind": "run_config",
            "scheduler": "sche_nash",
            "operational_expert_proxy": v176.PROFILE,
            "reference": {"mode": "offline_required", "offline_load_ok": True},
            "operational_expert_proxy_contract": {
                "version": "V176",
                "queue_density_threshold": v176.QUEUE_THRESHOLD,
                "below_threshold_expert": v176.LOW_EXPERT,
                "at_or_above_threshold_expert": v176.HIGH_EXPERT,
                "player_frontier": v176.FRONTIER,
                "single_change_from_v155": v176.SINGLE_CHANGE,
                "terminal_pipeline_definition": v176.TERMINAL_DEFINITION,
                "short_work_pipeline_remaining_work_threshold": v176.SHORT_WORK_THRESHOLD,
                "short_work_pipeline_queue_density_threshold": v176.QUEUE_THRESHOLD,
                "short_work_pipeline_queue_boundary": "below_is_strict",
                "short_work_definition": v176.WORK_DEFINITION,
                "cpu_bounded_terminal_guard": {
                    "normalized_cpu_threshold": 1.0,
                    "boundary": "at_or_below_is_admitted",
                    "numerator": "immutable_function_cpu_work",
                    "denominator": "current_cluster_mean_node_cpu_capacity",
                    "parents_completed_bypass": True,
                    "uses_completion_or_performance_outcomes": False,
                    "capacity_overload_activation": {
                        "heavy_player_definition": "collectable_incomplete-parent-terminal_player_with_immutable_function_cpu_work_over_current_cluster_mean_node_cpu_capacity_strictly_above_one",
                        "capacity_threshold": "fixed_one_current_heavy_player",
                        "fixed_heavy_player_count_threshold": 1,
                        "minimum_active_heavy_player_count": 2,
                        "activation_boundary": "heavy_player_count_strictly_above_one",
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
        active = frame >= 2
        heavy = 2 if active else frame
        if violate_boundary and frame == 1:
            active = True
        low_route = frame % 2 == 0
        terminal = 1
        short = 1 if low_route else 0
        rejected = 0 if low_route else 1
        return {
            "kind": "window",
            "frame": frame,
            "decision": {
                "assignment_hash": frame if frame < 2 else frame + 10_000,
                "player_frontier": v176.FRONTIER,
                "pipeline_players_with_incomplete_parents": terminal + short,
                "pipeline_observation_fields_drive_future_windows": False,
                "terminal_pipeline_frontier": {
                    "enabled": True,
                    "definition": v176.FRONTIER,
                    "short_work_remaining_work_threshold": v176.SHORT_WORK_THRESHOLD,
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
                            "minimum_active_heavy_player_count": 2,
                            "threshold_kind": "fixed_one_current_heavy_player",
                            "activation_boundary": "strictly_above_activates",
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
                    "queue_density": 7.0 if low_route else 8.0,
                    "queue_density_threshold": 8.0,
                    "selected_expert": (
                        v176.LOW_EXPERT if low_route else v176.HIGH_EXPERT
                    ),
                    "player_frontier": v176.FRONTIER,
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

    def test_result_blind_audit_locks_exact_one_and_exact_two_boundaries(self) -> None:
        frozen = tuple(range(1000))
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "run")
            audit = v176._audit_nash_log(
                canonical,
                {"run_id": "run", "seed": "E01"},
                frozen_v170=frozen,
            )
        self.assertEqual(audit["first_exact_two_frame"], 2)
        self.assertEqual(audit["first_assignment_mismatch_frame_vs_v170"], 2)
        self.assertTrue(audit["pre_first_exact_two_assignment_prefix_matches_v170"])
        self.assertTrue(audit["first_exact_two_frame_assignment_differs_from_v170"])
        self.assertEqual(audit["capacity_overload_exact_one_windows"], 1)
        self.assertEqual(
            audit["capacity_overload_exact_one_heavy_terminal_admissions"], 1
        )
        self.assertEqual(audit["capacity_overload_exact_two_windows"], 998)
        self.assertEqual(
            audit["capacity_overload_exact_two_heavy_terminal_rejections"], 1996
        )
        audits = [{**audit, "seed": seed} for seed in v176.SEEDS]
        mechanism = v176._mechanism_falsification_gate(audits)
        self.assertTrue(mechanism["pass"])
        self.assertTrue(mechanism["exact_one_inactive_and_exact_two_all_rejected"])

    def test_result_blind_audit_rejects_active_exact_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "run", violate_boundary=True)
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v176._audit_nash_log(
                    canonical,
                    {"run_id": "run", "seed": "E01"},
                    frozen_v170=tuple(range(1000)),
                )

    def test_result_blind_audit_rejects_any_active_admission_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "run", forbidden_policy=True)
            with self.assertRaisesRegex(RuntimeError, "run_config contract changed"):
                v176._audit_nash_log(
                    canonical,
                    {"run_id": "run", "seed": "E01"},
                    frozen_v170=tuple(range(1000)),
                )


if __name__ == "__main__":
    unittest.main()
