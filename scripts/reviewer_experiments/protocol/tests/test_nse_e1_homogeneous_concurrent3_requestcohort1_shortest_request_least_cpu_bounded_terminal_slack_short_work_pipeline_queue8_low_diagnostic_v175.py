from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent3_requestcohort1_shortest_request_least_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v175 as v175,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V175Concurrent3RequestCohort1ShortestRequestLeastCpuBoundedTerminalDiagnosticTests(
    unittest.TestCase
):
    def test_frozen_inputs_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v175.PLAN), v175.PLAN_SHA256)
        self.assertEqual(file_hash(v175.IMPLEMENTATION), v175.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v175.BINARY_PATH), v175.BINARY_SHA256)
        self.assertEqual(
            file_hash(v175.V170_COMPLETE_RESULT),
            v175.V170_COMPLETE_RESULT_SHA256,
        )
        plan = read_json(v175.PLAN)
        implementation = read_json(v175.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v175.SEEDS))
        change = implementation["single_scientific_change"]
        self.assertEqual(change["activation_boundary"], "strictly_above_activates")
        self.assertEqual(change["activation_threshold"], 2)
        self.assertEqual(change["minimum_active_count"], 3)
        self.assertEqual(change["inactive_behavior"], "exact_V159_terminal_admission")
        self.assertEqual(change["active_heavy_quota"], 1)
        self.assertEqual(change["active_heavy_quota_unit"], "request_cohort")
        self.assertEqual(
            change["request_cohort_selection_order"],
            "ascending_current_request_remaining_work_then_request_minimum_immutable_terminal_function_cpu_work_then_request_id",
        )
        self.assertEqual(
            change["selected_cohort_admission"],
            "all_current_heavy_incomplete_parent_terminal_players_in_selected_request",
        )
        self.assertEqual(
            v175.TERMINAL_DEFINITION,
            "admit_all_parents-completed_players;when_current_heavy_terminal_player_"
            "count_strictly_exceeds_two_select_one_request_by_shortest_current_request_"
            "remaining_work_then_request_minimum_immutable_terminal_function_CPU_work_"
            "then_request-id_and_admit_all_current_heavy_incomplete-parent-terminal_"
            "players_in_that_request_while_applying_the_V168_CPU_bound_to_heavy_players_"
            "in_other_requests;otherwise_retain_V159_terminal_admission;retain_V159_"
            "nonterminal_short-work_frontier",
        )
        manifest = v175._rewrite_candidate(v175._assert_frozen_inputs(), "c" * 40)
        v175._validate_product(manifest, references_bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v175.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), len(v175.SEEDS))
        self.assertTrue(
            all(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] == v175.PROFILE
                and run["metadata"]["v175_cpu_threshold"] == 1.0
                and run["metadata"]["v175_heavy_player_threshold"] == 2
                and run["metadata"]["v175_minimum_active_heavy_players"] == 3
                and run["metadata"]["v175_overload_activation_boundary"]
                == "strictly_above_activates"
                and run["metadata"]["v175_active_heavy_admission_quota"] == 1
                and run["metadata"]["v175_active_heavy_admission_quota_unit"]
                == "request_cohort"
                and run["metadata"]["v175_quota_selection_order"]
                == v175.QUOTA_SELECTION_ORDER
                and run["metadata"]["v175_remaining_fourteen_authorized"] is False
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
                "source": "V175",
                "throughput": 100.0 + ordinal,
            }
            for ordinal, seed in enumerate(v175.SEEDS)
        ]
        hybrid = v175._hybrid_rows_v175(frozen, replacements)
        self.assertEqual(
            [row["seed"] for row in hybrid], [f"E{i:02d}" for i in range(1, 21)]
        )
        by_seed = {row["seed"]: row for row in hybrid}
        self.assertTrue(all(by_seed[seed]["source"] == "V175" for seed in v175.SEEDS))
        self.assertTrue(
            all(
                by_seed[f"E{index:02d}"]["source"] == "V170"
                for index in range(1, 21)
                if f"E{index:02d}" not in v175.SEEDS
            )
        )
        self.assertEqual(len(v175._load_v170_candidate()), 20)

    @staticmethod
    def _run_config() -> dict:
        return {
            "kind": "run_config",
            "scheduler": "sche_nash",
            "operational_expert_proxy": v175.PROFILE,
            "reference": {"mode": "offline_required", "offline_load_ok": True},
            "operational_expert_proxy_contract": {
                "version": "V175",
                "queue_density_threshold": v175.QUEUE_THRESHOLD,
                "below_threshold_expert": v175.LOW_EXPERT,
                "at_or_above_threshold_expert": v175.HIGH_EXPERT,
                "player_frontier": v175.FRONTIER,
                "single_change_from_v155": v175.SINGLE_CHANGE,
                "terminal_pipeline_definition": v175.TERMINAL_DEFINITION,
                "short_work_pipeline_remaining_work_threshold": v175.SHORT_WORK_THRESHOLD,
                "short_work_pipeline_queue_density_threshold": v175.QUEUE_THRESHOLD,
                "short_work_pipeline_queue_boundary": "below_is_strict",
                "short_work_definition": v175.WORK_DEFINITION,
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
                        "active_heavy_admission_policy": "deterministic_shortest_request_cohort_one",
                        "active_heavy_admission_quota": 1,
                        "active_heavy_admission_quota_unit": "request_cohort",
                        "quota_selection_order": v175.QUOTA_SELECTION_ORDER,
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
        active_admitted_request_work: float = 4.0,
        active_rejected_request_work: float = 5.0,
        active_cohort_size: int = 2,
    ) -> dict:
        low_route = frame % 2 == 0
        density = 7.0 if low_route else 8.0
        terminal = active_cohort_size if guard_active else 1
        short = 1 if low_route else 0
        heavy = 3 if guard_active else 1
        return {
            "kind": "window",
            "frame": frame,
            "decision": {
                "assignment_hash": assignment_hash,
                "player_frontier": v175.FRONTIER,
                "pipeline_players_with_incomplete_parents": terminal + short,
                "pipeline_observation_fields_drive_future_windows": False,
                "terminal_pipeline_frontier": {
                    "enabled": True,
                    "definition": v175.FRONTIER,
                    "short_work_remaining_work_threshold": v175.SHORT_WORK_THRESHOLD,
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
                            heavy - active_cohort_size if guard_active else 0
                        ),
                        "parents_completed_heavy_terminal_bypass_players": 1,
                        "admitted_normalized_cpu_max": (
                            active_admitted_ratio if guard_active else 1.0001
                        ),
                        "rejected_normalized_cpu_min": (
                            2.1 if guard_active and heavy > active_cohort_size else None
                        ),
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
                            "active_heavy_admission_policy": "deterministic_shortest_request_cohort_one",
                            "active_heavy_admission_quota": 1,
                            "active_heavy_admission_quota_unit": "request_cohort",
                            "active_heavy_selected_request_count": (
                                1 if guard_active else 0
                            ),
                            "active_heavy_selected_request_candidate_players": (
                                active_cohort_size if guard_active else 0
                            ),
                            "active_heavy_quota_selected_players": (
                                active_cohort_size if guard_active else 0
                            ),
                            "active_heavy_quota_admitted_players": (
                                active_cohort_size if guard_active else 0
                            ),
                            "active_heavy_quota_rejected_excess_players": (
                                heavy - active_cohort_size if guard_active else 0
                            ),
                            "active_heavy_quota_admitted_request_remaining_work_max": (
                                active_admitted_request_work if guard_active else None
                            ),
                            "active_heavy_quota_rejected_request_remaining_work_min": (
                                active_rejected_request_work
                                if guard_active and heavy > active_cohort_size
                                else None
                            ),
                            "quota_selection_order": v175.QUOTA_SELECTION_ORDER,
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
                        v175.LOW_EXPERT if low_route else v175.HIGH_EXPERT
                    ),
                    "player_frontier": v175.FRONTIER,
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
        active_admitted_request_work: float = 4.0,
        active_rejected_request_work: float = 5.0,
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
                    active_admitted_request_work=active_admitted_request_work,
                    active_rejected_request_work=active_rejected_request_work,
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
                    activation["active_heavy_quota_admitted_players"] = 1
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

    def test_blind_gate_requires_complete_expanded_cohort_and_selected_seed_divergence(
        self,
    ) -> None:
        frozen = tuple(range(1000))
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v175, "_frozen_v170_assignment_hashes", return_value=frozen
        ):
            root = Path(directory)
            audits = []
            for ordinal, seed in enumerate(v175.SEEDS):
                run_id = f"synthetic-v175-{seed}"
                canonical = root / seed
                self._write_log(
                    canonical,
                    run_id,
                    first_active_frame=24,
                    active_admitted_request_work=4.0 + ordinal,
                    active_rejected_request_work=5.0 + ordinal,
                )
                audits.append(
                    v175._audit_nash_log(canonical, {"run_id": run_id, "seed": seed})
                )
            gate = v175._mechanism_falsification_gate(audits)
            self.assertTrue(gate["pass"])
            self.assertTrue(
                gate["deterministic_active_heavy_request_cohort_exercised_and_complete"]
            )
            self.assertTrue(gate["request_cohort_expansion_exercised"])
            self.assertTrue(
                gate[
                    "shortest_request_cohort_selection_order_certified_in_every_active_window"
                ]
            )
            self.assertTrue(
                gate["selected_seeds_pre_activation_exact_v170_then_diverged"]
            )
            self.assertEqual(
                gate["selected_seed_first_guard_active_frames"],
                {seed: 24 for seed in v175.SEEDS},
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
            self.assertEqual(
                gate["active_heavy_selected_request_count"],
                gate["capacity_overload_guard_active_windows"],
            )

    def test_blind_audit_rejects_incomplete_selected_request_cohort(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v175, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v175",
                first_active_frame=0,
                violate_quota=True,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v175._audit_nash_log(
                    canonical, {"run_id": "synthetic-v175", "seed": "E20"}
                )

    def test_blind_audit_rejects_selected_request_work_above_rejected_minimum(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v175, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v175",
                first_active_frame=0,
                active_admitted_request_work=6.0,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v175._audit_nash_log(
                    canonical, {"run_id": "synthetic-v175", "seed": "E20"}
                )

    def test_blind_audit_rejects_activation_at_exact_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v175, "_frozen_v170_assignment_hashes", return_value=tuple(range(1000))
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v175",
                first_active_frame=None,
                violate_exact_threshold=True,
            )
            with self.assertRaisesRegex(RuntimeError, "frontier evidence changed"):
                v175._audit_nash_log(
                    canonical, {"run_id": "synthetic-v175", "seed": "E02"}
                )

    def test_blind_audit_can_skip_unavailable_v159_sequence_for_remaining_seeds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            v175,
            "_frozen_v170_assignment_hashes",
            side_effect=AssertionError("frozen V159 must not be read"),
        ):
            canonical = Path(directory)
            self._write_log(
                canonical,
                "synthetic-v175",
                first_active_frame=24,
            )
            evidence = v175._audit_nash_log(
                canonical,
                {"run_id": "synthetic-v175", "seed": "E01"},
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
            "active_heavy_selected_request_count",
            "active_heavy_selected_request_candidate_players",
            "active_heavy_request_cohort_expansion_windows",
            "shortest_request_order_certified_active_windows",
            "below_threshold_route_windows",
            "at_or_above_threshold_route_windows",
        )
        base = {key: 1 for key in count_keys}
        base.update(
            {
                "capacity_overload_heavy_incomplete_parent_terminal_players": 4,
                "active_heavy_quota_selected_players": 2,
                "active_heavy_quota_admitted_players": 2,
                "active_heavy_selected_request_count": 1,
                "active_heavy_selected_request_candidate_players": 2,
                "active_heavy_request_cohort_expansion_windows": 1,
                "cpu_guard_admitted_normalized_cpu_max": 2.0,
                "cpu_guard_active_admitted_normalized_cpu_max": 2.0,
                "cpu_guard_inactive_admitted_normalized_cpu_max": 1.1,
                "cpu_guard_rejected_normalized_cpu_min": 2.0,
                "active_heavy_quota_admitted_request_remaining_work_max": 4.0,
                "active_heavy_quota_rejected_request_remaining_work_min": 5.0,
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
        for seed in v175.SEEDS:
            audit = {**base, "seed": seed}
            if seed == "E02":
                audit["active_heavy_quota_admitted_players"] = 0
            audits.append(audit)
        self.assertFalse(v175._mechanism_falsification_gate(audits)["pass"])

    def test_mechanism_gate_rejects_unexercised_multi_sibling_expansion(self) -> None:
        audits = []
        for seed in v175.SEEDS:
            audits.append(
                {
                    "seed": seed,
                    "admitted_terminal_players_with_incomplete_parents": 1,
                    "admitted_slack_short_work_nonterminal_players": 1,
                    "rejected_frontier_players_with_incomplete_parents": 1,
                    "rejected_short_work_at_or_above_queue_threshold": 1,
                    "cpu_guard_admitted_incomplete_parent_terminal_players": 1,
                    "cpu_guard_rejected_heavy_incomplete_parent_terminal_players": 2,
                    "cpu_guard_parent_completed_heavy_terminal_bypass_players": 1,
                    "capacity_overload_heavy_incomplete_parent_terminal_players": 4,
                    "capacity_overload_guard_active_windows": 1,
                    "capacity_overload_guard_inactive_windows": 1,
                    "capacity_overload_guard_inactive_heavy_terminal_admissions": 1,
                    "active_heavy_quota_selected_players": 1,
                    "active_heavy_quota_admitted_players": 1,
                    "active_heavy_quota_rejected_excess_players": 2,
                    "active_heavy_selected_request_count": 1,
                    "active_heavy_selected_request_candidate_players": 1,
                    "active_heavy_request_cohort_expansion_windows": 0,
                    "shortest_request_order_certified_active_windows": 1,
                    "below_threshold_route_windows": 1,
                    "at_or_above_threshold_route_windows": 1,
                    "cpu_guard_admitted_normalized_cpu_max": 2.0,
                    "cpu_guard_active_admitted_normalized_cpu_max": 2.0,
                    "cpu_guard_inactive_admitted_normalized_cpu_max": 1.1,
                    "cpu_guard_rejected_normalized_cpu_min": 2.0,
                    "active_heavy_quota_admitted_request_remaining_work_max": 4.0,
                    "active_heavy_quota_rejected_request_remaining_work_min": 5.0,
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
        gate = v175._mechanism_falsification_gate(audits)
        self.assertFalse(gate["request_cohort_expansion_exercised"])
        self.assertFalse(gate["pass"])


if __name__ == "__main__":
    unittest.main()
