from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_quota2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v171 as v171,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V171Concurrent3Quota2CpuBoundedTerminalDiagnosticTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v171.PLAN), v171.PLAN_SHA256)
        self.assertEqual(file_hash(v171.IMPLEMENTATION), v171.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v171.BINARY_PATH), v171.BINARY_SHA256)
        plan = read_json(v171.PLAN)
        implementation = read_json(v171.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v171.SEEDS))
        change = implementation["single_scientific_change"]
        self.assertEqual(change["activation_boundary"], "strictly_above_activates")
        self.assertEqual(change["activation_threshold"], 2)
        self.assertEqual(change["minimum_active_count"], 3)
        self.assertEqual(change["inactive_behavior"], "exact_V159_terminal_admission")
        self.assertEqual(change["active_heavy_quota"], 2)
        self.assertEqual(
            change["quota_selection_order"], "ascending_request_id_then_function_id"
        )
        self.assertEqual(
            v171.TERMINAL_DEFINITION,
            "admit_all_parents-completed_players;when_current_heavy_terminal_player_"
            "count_strictly_exceeds_two_admit_at_most_two_heavy_incomplete-parent-"
            "terminal_players_in_ascending_request-id-then-function-id_order_and_"
            "apply_the_V168_CPU_bound_to_the_excess;otherwise_retain_V159_terminal_"
            "admission;retain_V159_nonterminal_short-work_frontier",
        )
        manifest = v171._rewrite_candidate(v171._assert_frozen_inputs(), "c" * 40)
        v171._validate_product(manifest, references_bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v171.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] == v171.PROFILE
                and run["metadata"]["v171_cpu_threshold"] == 1.0
                and run["metadata"]["v171_heavy_player_threshold"] == 2
                and run["metadata"]["v171_minimum_active_heavy_players"] == 3
                and run["metadata"]["v171_overload_activation_boundary"]
                == "strictly_above_activates"
                and run["metadata"]["v171_active_heavy_admission_quota"] == 2
                and run["metadata"]["v171_quota_selection_order"]
                == "ascending_request_id_then_function_id"
                and run["metadata"]["v171_remaining_seventeen_authorized"] is False
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _run_config() -> dict:
        return {
            "kind": "run_config",
            "scheduler": "sche_nash",
            "operational_expert_proxy": v171.PROFILE,
            "reference": {"mode": "offline_required", "offline_load_ok": True},
            "operational_expert_proxy_contract": {
                "version": "V171",
                "queue_density_threshold": v171.QUEUE_THRESHOLD,
                "below_threshold_expert": v171.LOW_EXPERT,
                "at_or_above_threshold_expert": v171.HIGH_EXPERT,
                "player_frontier": v171.FRONTIER,
                "single_change_from_v155": v171.SINGLE_CHANGE,
                "terminal_pipeline_definition": v171.TERMINAL_DEFINITION,
                "short_work_pipeline_remaining_work_threshold": v171.SHORT_WORK_THRESHOLD,
                "short_work_pipeline_queue_density_threshold": v171.QUEUE_THRESHOLD,
                "short_work_pipeline_queue_boundary": "below_is_strict",
                "short_work_definition": v171.WORK_DEFINITION,
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
                        "active_heavy_admission_policy": "deterministic_quota_two",
                        "active_heavy_admission_quota": 2,
                        "quota_selection_order": "ascending_request_id_then_function_id",
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
        active_admitted_ratio: float = 2.0,
    ) -> dict:
        low_route = frame % 2 == 0
        density = 7.0 if low_route else 8.0
        terminal = 2 if guard_active else 1
        short = 1 if low_route else 0
        heavy = 3 if guard_active else 1
        return {
            "kind": "window",
            "frame": frame,
            "decision": {
                "assignment_hash": assignment_hash,
                "player_frontier": v171.FRONTIER,
                "pipeline_players_with_incomplete_parents": terminal + short,
                "pipeline_observation_fields_drive_future_windows": False,
                "terminal_pipeline_frontier": {
                    "enabled": True,
                    "definition": v171.FRONTIER,
                    "short_work_remaining_work_threshold": v171.SHORT_WORK_THRESHOLD,
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
                            heavy - 2 if guard_active else 0
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
                            "active_heavy_admission_policy": "deterministic_quota_two",
                            "active_heavy_admission_quota": 2,
                            "active_heavy_quota_selected_players": (
                                2 if guard_active else 0
                            ),
                            "active_heavy_quota_admitted_players": (
                                2 if guard_active else 0
                            ),
                            "active_heavy_quota_rejected_excess_players": (
                                heavy - 2 if guard_active else 0
                            ),
                            "quota_selection_order": "ascending_request_id_then_function_id",
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
                        v171.LOW_EXPERT if low_route else v171.HIGH_EXPERT
                    ),
                    "player_frontier": v171.FRONTIER,
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
        active_admitted_ratio: float = 2.0,
        violate_exact_threshold: bool = False,
        violate_quota: bool = False,
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
                    activation["active_heavy_quota_selected_players"] = 2
                    activation["active_heavy_quota_admitted_players"] = 2
                    activation["active_heavy_quota_rejected_excess_players"] = 0
                    guard["rejected_heavy_incomplete_parent_terminal_players"] = 0
                    guard["rejected_normalized_cpu_min"] = None
                    guard["admitted_normalized_cpu_max"] = 2.0
                if violate_quota and active:
                    activation = event["decision"]["terminal_pipeline_frontier"][
                        "cpu_bounded_terminal_guard"
                    ]["capacity_overload_activation"]
                    activation["active_heavy_quota_admitted_players"] = 3
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

    def test_blind_gate_requires_quota_and_selected_seed_divergence(self) -> None:
        frozen = tuple(range(1000))
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v171, "_frozen_v170_assignment_hashes", return_value=frozen
        ):
            root = Path(directory)
            audits = []
            for seed in v171.SEEDS:
                run_id = f"synthetic-v171-{seed}"
                canonical = root / seed
                self._write_log(
                    canonical,
                    run_id,
                    first_active_frame=24,
                )
                audits.append(
                    v171._audit_nash_log(canonical, {"run_id": run_id, "seed": seed})
                )
            gate = v171._mechanism_falsification_gate(audits)
            self.assertTrue(gate["pass"])
            self.assertTrue(
                gate["deterministic_active_heavy_quota_exercised_and_bounded"]
            )
            self.assertTrue(
                gate["selected_seeds_pre_activation_exact_v170_then_diverged"]
            )
            self.assertEqual(
                gate["selected_seed_first_guard_active_frames"],
                {seed: 24 for seed in v171.SEEDS},
            )
            self.assertGreater(
                gate["cpu_guard_inactive_admitted_normalized_cpu_max"], 1.0
            )
            self.assertGreater(
                gate["cpu_guard_active_admitted_normalized_cpu_max"], 1.0
            )
            self.assertEqual(
                gate["active_heavy_quota_admitted_players"],
                2 * gate["capacity_overload_guard_active_windows"],
            )

    def test_blind_audit_rejects_active_quota_above_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v171, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v171",
                first_active_frame=0,
                violate_quota=True,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v171._audit_nash_log(
                    canonical, {"run_id": "synthetic-v171", "seed": "E20"}
                )

    def test_blind_audit_rejects_activation_at_exact_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v171, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v171",
                first_active_frame=None,
                violate_exact_threshold=True,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v171._audit_nash_log(
                    canonical, {"run_id": "synthetic-v171", "seed": "E02"}
                )

    def test_blind_audit_can_skip_unavailable_v159_sequence_for_remaining_seeds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v171,
            "_frozen_v170_assignment_hashes",
            side_effect=AssertionError("frozen V159 must not be read"),
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v171",
                first_active_frame=24,
            )
            evidence = v171._audit_nash_log(
                canonical,
                {"run_id": "synthetic-v171", "seed": "E01"},
                compare_to_frozen_v170=False,
            )
            self.assertFalse(evidence["frozen_v170_comparison_applicable"])
            self.assertIsNone(evidence["frozen_v170_assignment_sequence_sha256"])
            self.assertIsNone(evidence["assignment_mismatch_count_vs_v170"])
            self.assertEqual(evidence["first_guard_active_frame"], 24)

    def test_mechanism_gate_rejects_incomplete_active_quota(self) -> None:
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
            "active_heavy_quota_selected_players",
            "active_heavy_quota_admitted_players",
            "active_heavy_quota_rejected_excess_players",
            "below_threshold_route_windows",
            "at_or_above_threshold_route_windows",
        )
        base = {key: 1 for key in count_keys}
        base.update(
            {
                "capacity_overload_heavy_incomplete_parent_terminal_players": 4,
                "active_heavy_quota_selected_players": 2,
                "active_heavy_quota_admitted_players": 2,
                "cpu_guard_admitted_normalized_cpu_max": 2.0,
                "cpu_guard_active_admitted_normalized_cpu_max": 2.0,
                "cpu_guard_inactive_admitted_normalized_cpu_max": 1.1,
                "cpu_guard_rejected_normalized_cpu_min": 2.0,
                "admitted_short_work_remaining_work_max": 5.0,
                "rejected_over_threshold_remaining_work_min": 6.0,
                "admitted_short_work_queue_density_max": 7.0,
                "rejected_short_work_queue_density_min": 8.0,
                "assignment_sequence_sha256": "different",
                "frozen_v170_assignment_sequence_sha256": "frozen",
                "assignment_mismatch_count_vs_v170": 1,
                "first_guard_active_frame": 24,
                "pre_activation_assignment_prefix_matches_v170": True,
                "post_activation_assignment_mismatch_count_vs_v170": 1,
            }
        )
        audits = []
        for seed in v171.SEEDS:
            audit = {**base, "seed": seed}
            if seed == "E02":
                audit["active_heavy_quota_admitted_players"] = 1
            audits.append(audit)
        self.assertFalse(v171._mechanism_falsification_gate(audits)["pass"])


if __name__ == "__main__":
    unittest.main()
