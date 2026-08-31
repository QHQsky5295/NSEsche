from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_quota1_least_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v173 as v173,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V173Concurrent3Quota1LeastCpuBoundedTerminalDiagnosticTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v173.PLAN), v173.PLAN_SHA256)
        self.assertEqual(file_hash(v173.IMPLEMENTATION), v173.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v173.BINARY_PATH), v173.BINARY_SHA256)
        self.assertEqual(
            file_hash(v173.V170_COMPLETE_RESULT),
            v173.V170_COMPLETE_RESULT_SHA256,
        )
        plan = read_json(v173.PLAN)
        implementation = read_json(v173.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v173.SEEDS))
        change = implementation["single_scientific_change"]
        self.assertEqual(change["activation_boundary"], "strictly_above_activates")
        self.assertEqual(change["activation_threshold"], 2)
        self.assertEqual(change["minimum_active_count"], 3)
        self.assertEqual(change["inactive_behavior"], "exact_V159_terminal_admission")
        self.assertEqual(change["active_heavy_quota"], 1)
        self.assertEqual(
            change["old_quota_selection_order"],
            "ascending_request_id_then_function_id",
        )
        self.assertEqual(
            change["new_quota_selection_order"], v173.QUOTA_SELECTION_ORDER
        )
        self.assertEqual(
            v173.TERMINAL_DEFINITION,
            "admit_all_parents-completed_players;when_current_heavy_terminal_player_"
            "count_strictly_exceeds_two_admit_the_one_heavy_incomplete-parent-"
            "terminal-player_with_least_immutable_function_cpu_work_tied_by_"
            "request-id-then-function-id_and_apply_the_V168_CPU_bound_to_the_"
            "excess;otherwise_retain_V159_terminal_admission;retain_V159_"
            "nonterminal_short-work_frontier",
        )
        manifest = v173._rewrite_candidate(v173._assert_frozen_inputs(), "c" * 40)
        v173._validate_product(manifest, references_bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v173.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), len(v173.SEEDS))
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] == v173.PROFILE
                and run["metadata"]["v173_cpu_threshold"] == 1.0
                and run["metadata"]["v173_heavy_player_threshold"] == 2
                and run["metadata"]["v173_minimum_active_heavy_players"] == 3
                and run["metadata"]["v173_overload_activation_boundary"]
                == "strictly_above_activates"
                and run["metadata"]["v173_active_heavy_admission_quota"] == 1
                and run["metadata"]["v173_quota_selection_order"]
                == v173.QUOTA_SELECTION_ORDER
                and run["metadata"]["v173_remaining_fourteen_authorized"] is False
                for run in manifest["runs"]
            )
        )

    def test_hybrid_replaces_only_selected_rows_from_sealed_v170(self) -> None:
        frozen = [
            {
                "load": "low",
                "seed": f"E{index:02d}",
                "source": "V170",
                "throughput": float(index),
            }
            for index in range(1, 21)
        ]
        replacements = [
            {
                "load": "low",
                "seed": seed,
                "source": "V173",
                "throughput": 100.0 + ordinal,
            }
            for ordinal, seed in enumerate(v173.SEEDS)
        ]
        hybrid = v173._hybrid_rows_v173(frozen, replacements)
        self.assertEqual(
            [row["seed"] for row in hybrid], [f"E{i:02d}" for i in range(1, 21)]
        )
        by_seed = {row["seed"]: row for row in hybrid}
        self.assertTrue(all(by_seed[seed]["source"] == "V173" for seed in v173.SEEDS))
        self.assertTrue(
            all(
                by_seed[f"E{index:02d}"]["source"] == "V170"
                for index in range(1, 21)
                if f"E{index:02d}" not in v173.SEEDS
            )
        )
        self.assertEqual(len(v173._load_v170_candidate()), 20)

    @staticmethod
    def _run_config() -> dict:
        return {
            "kind": "run_config",
            "scheduler": "sche_nash",
            "operational_expert_proxy": v173.PROFILE,
            "reference": {"mode": "offline_required", "offline_load_ok": True},
            "operational_expert_proxy_contract": {
                "version": "V173",
                "queue_density_threshold": v173.QUEUE_THRESHOLD,
                "below_threshold_expert": v173.LOW_EXPERT,
                "at_or_above_threshold_expert": v173.HIGH_EXPERT,
                "player_frontier": v173.FRONTIER,
                "single_change_from_v155": v173.SINGLE_CHANGE,
                "terminal_pipeline_definition": v173.TERMINAL_DEFINITION,
                "short_work_pipeline_remaining_work_threshold": v173.SHORT_WORK_THRESHOLD,
                "short_work_pipeline_queue_density_threshold": v173.QUEUE_THRESHOLD,
                "short_work_pipeline_queue_boundary": "below_is_strict",
                "short_work_definition": v173.WORK_DEFINITION,
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
                        "active_heavy_admission_policy": "deterministic_least_cpu_quota_one",
                        "active_heavy_admission_quota": 1,
                        "quota_selection_order": v173.QUOTA_SELECTION_ORDER,
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
        terminal = 1
        short = 1 if low_route else 0
        heavy = 3 if guard_active else 1
        return {
            "kind": "window",
            "frame": frame,
            "decision": {
                "assignment_hash": assignment_hash,
                "player_frontier": v173.FRONTIER,
                "pipeline_players_with_incomplete_parents": terminal + short,
                "pipeline_observation_fields_drive_future_windows": False,
                "terminal_pipeline_frontier": {
                    "enabled": True,
                    "definition": v173.FRONTIER,
                    "short_work_remaining_work_threshold": v173.SHORT_WORK_THRESHOLD,
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
                            heavy - 1 if guard_active else 0
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
                            "active_heavy_admission_policy": "deterministic_least_cpu_quota_one",
                            "active_heavy_admission_quota": 1,
                            "active_heavy_quota_selected_players": (
                                1 if guard_active else 0
                            ),
                            "active_heavy_quota_admitted_players": (
                                1 if guard_active else 0
                            ),
                            "active_heavy_quota_rejected_excess_players": (
                                heavy - 1 if guard_active else 0
                            ),
                            "quota_selection_order": v173.QUOTA_SELECTION_ORDER,
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
                        v173.LOW_EXPERT if low_route else v173.HIGH_EXPERT
                    ),
                    "player_frontier": v173.FRONTIER,
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
                    activation["active_heavy_quota_selected_players"] = 1
                    activation["active_heavy_quota_admitted_players"] = 1
                    activation["active_heavy_quota_rejected_excess_players"] = 1
                    guard["rejected_heavy_incomplete_parent_terminal_players"] = 1
                    guard["rejected_normalized_cpu_min"] = None
                    guard["admitted_normalized_cpu_max"] = 2.0
                if violate_quota and active:
                    activation = event["decision"]["terminal_pipeline_frontier"][
                        "cpu_bounded_terminal_guard"
                    ]["capacity_overload_activation"]
                    activation["active_heavy_quota_admitted_players"] = 2
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
            v173, "_frozen_v170_assignment_hashes", return_value=frozen
        ):
            root = Path(directory)
            audits = []
            for seed in v173.SEEDS:
                run_id = f"synthetic-v173-{seed}"
                canonical = root / seed
                self._write_log(
                    canonical,
                    run_id,
                    first_active_frame=24,
                )
                audits.append(
                    v173._audit_nash_log(canonical, {"run_id": run_id, "seed": seed})
                )
            gate = v173._mechanism_falsification_gate(audits)
            self.assertTrue(gate["pass"])
            self.assertTrue(
                gate["deterministic_active_heavy_quota_exercised_and_bounded"]
            )
            self.assertTrue(
                gate["least_cpu_quota_selection_order_certified_in_every_active_window"]
            )
            self.assertTrue(
                gate["selected_seeds_pre_activation_exact_v170_then_diverged"]
            )
            self.assertEqual(
                gate["selected_seed_first_guard_active_frames"],
                {seed: 24 for seed in v173.SEEDS},
            )
            self.assertGreater(
                gate["cpu_guard_inactive_admitted_normalized_cpu_max"], 1.0
            )
            self.assertGreater(
                gate["cpu_guard_active_admitted_normalized_cpu_max"], 1.0
            )
            self.assertEqual(
                gate["active_heavy_quota_admitted_players"],
                gate["capacity_overload_guard_active_windows"],
            )

    def test_blind_audit_rejects_active_quota_above_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v173, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v173",
                first_active_frame=0,
                violate_quota=True,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v173._audit_nash_log(
                    canonical, {"run_id": "synthetic-v173", "seed": "E20"}
                )

    def test_blind_audit_rejects_selected_cpu_above_rejected_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v173, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v173",
                first_active_frame=0,
                active_admitted_ratio=2.2,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v173._audit_nash_log(
                    canonical, {"run_id": "synthetic-v173", "seed": "E20"}
                )

    def test_blind_audit_rejects_activation_at_exact_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v173, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v173",
                first_active_frame=None,
                violate_exact_threshold=True,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v173._audit_nash_log(
                    canonical, {"run_id": "synthetic-v173", "seed": "E02"}
                )

    def test_blind_audit_can_skip_unavailable_v159_sequence_for_remaining_seeds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v173,
            "_frozen_v170_assignment_hashes",
            side_effect=AssertionError("frozen V159 must not be read"),
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v173",
                first_active_frame=24,
            )
            evidence = v173._audit_nash_log(
                canonical,
                {"run_id": "synthetic-v173", "seed": "E01"},
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
            "least_cpu_order_certified_active_windows",
            "below_threshold_route_windows",
            "at_or_above_threshold_route_windows",
        )
        base = {key: 1 for key in count_keys}
        base.update(
            {
                "capacity_overload_heavy_incomplete_parent_terminal_players": 4,
                "active_heavy_quota_selected_players": 1,
                "active_heavy_quota_admitted_players": 1,
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
        for seed in v173.SEEDS:
            audit = {**base, "seed": seed}
            if seed == "E02":
                audit["active_heavy_quota_admitted_players"] = 0
            audits.append(audit)
        self.assertFalse(v173._mechanism_falsification_gate(audits)["pass"])


if __name__ == "__main__":
    unittest.main()
