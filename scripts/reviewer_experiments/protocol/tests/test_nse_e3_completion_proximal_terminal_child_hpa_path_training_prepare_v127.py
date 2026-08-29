from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_completion_proximal_terminal_child_hpa_path_training_prepare_v127 import (
    ARMS,
    BINARY_SHA256,
    CONFIRMATION_SEEDS,
    OTHER_UNOPENED_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUS_CONFIRMATION_SEEDS,
    TRAINING_SEEDS,
    _paths,
    arm_path,
    prepare_v127,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash


class CompletionProximalHpaPathPreparationV127Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name) / "v127"
        cls.receipt = prepare_v127(cls.root)
        cls.paths = _paths(cls.root)
        cls.arms = {
            arm_id: json.loads(arm_path(cls.root, arm_id).read_text(encoding="utf-8"))
            for arm_id, _, _, _ in ARMS
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_two_arms_lock_exact_profiles_runtime_and_seed_product(self) -> None:
        self.assertEqual(len(ARMS), 2)
        self.assertEqual(sum(item[-1] for item in ARMS), 18)
        for arm_id, role, profile, count in ARMS:
            manifest = self.arms[arm_id]
            validate_manifest(manifest)
            self.assertEqual(len(manifest["runs"]), count)
            self.assertEqual({run["seed"] for run in manifest["runs"]}, TRAINING_SEEDS)
            self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
            self.assertEqual(
                {
                    run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                    for run in manifest["runs"]
                },
                {profile},
            )
            for run in manifest["runs"]:
                metadata = run["metadata"]
                candidate = role == "candidate"
                self.assertEqual(metadata["v127_arm_id"], arm_id)
                self.assertEqual(metadata["v127_arm_role"], role)
                self.assertEqual(
                    metadata["v127_shock_activation_horizon_frames"],
                    50 if candidate else None,
                )
                self.assertEqual(
                    metadata["v127_critical_service_ratio_numerator"],
                    9 if candidate else None,
                )
                self.assertEqual(
                    metadata["v127_critical_service_ratio_denominator"],
                    10 if candidate else None,
                )
                self.assertEqual(
                    metadata["v127_service_proxy_work_source"],
                    (
                        "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
                        if candidate
                        else "not_applicable"
                    ),
                )
                self.assertIs(
                    metadata["v127_admitted_work_includes_all_blocked_resident"],
                    candidate,
                )
                self.assertIs(
                    metadata["v127_completion_proximal_depth1_substitution_scope"],
                    candidate,
                )
                self.assertEqual(
                    metadata["v127_completion_proximal_definition"],
                    (
                        "terminal_function_or_nonterminal_function_whose_immutable_DAG_children_are_all_terminal"
                        if candidate
                        else "not_applicable"
                    ),
                )
                self.assertEqual(
                    metadata["v127_maximum_remaining_child_depth"],
                    1 if candidate else None,
                )
                self.assertIs(
                    metadata["v127_completion_proximal_critical_frontier_substitution"],
                    candidate,
                )
                self.assertIs(metadata["v127_deeper_player_exact_anchor"], candidate)
                self.assertIs(
                    metadata["v127_complete_componentwise_service_pareto"],
                    candidate,
                )
                self.assertEqual(
                    metadata["v127_componentwise_service_scope"],
                    (
                        "all_current_critical_frontier_players"
                        if candidate
                        else "not_applicable"
                    ),
                )
                self.assertEqual(
                    metadata["v127_componentwise_service_comparison"],
                    (
                        "every_current_critical_player_alternative_less_than_or_equal_to_anchor"
                        if candidate
                        else "not_applicable"
                    ),
                )
                self.assertIs(
                    metadata[
                        "v127_complete_terminal_child_hpa_container_path_service_pareto"
                    ],
                    candidate,
                )
                self.assertEqual(
                    metadata["v127_terminal_child_hpa_container_path_scope"],
                    (
                        "every_immutable_immediate_child_of_each_actually_changed_completion_proximal_player"
                        if candidate
                        else "not_applicable"
                    ),
                )
                self.assertEqual(
                    metadata["v127_terminal_child_hpa_container_path_proxy"],
                    (
                        "parent_output_transfer_plus_full_cold_start_if_starting_plus_child_node_admitted_cpu_service"
                        if candidate
                        else "not_applicable"
                    ),
                )
                self.assertIs(
                    metadata[
                        "v127_terminal_child_hpa_container_path_input_fail_closed"
                    ],
                    candidate,
                )
                self.assertFalse(metadata["v127_outcome_fields_drive_policy"])
                self.assertNotIn(run["seed"], CONFIRMATION_SEEDS)
                self.assertNotIn(run["seed"], OTHER_UNOPENED_SEEDS)

    def test_arm_references_are_unique_and_tapes_are_paired(self) -> None:
        reference_sets = [
            {item["key"] for item in manifest["reference_build_dependencies"]}
            for manifest in self.arms.values()
        ]
        self.assertEqual(sum(map(len, reference_sets)), 18)
        self.assertEqual(len(set().union(*reference_sets)), 18)
        tape_sets = [
            {
                key
                for run in manifest["runs"]
                for key in (
                    run["workload_tape"]["key"],
                    run["workload_tape"].get("parent_key"),
                )
                if key is not None
            }
            for manifest in self.arms.values()
        ]
        self.assertEqual(tape_sets[0], tape_sets[1])
        self.assertEqual(len(tape_sets[0]), 12)

    def test_capture_receipt_and_hashes_close_information_boundary(self) -> None:
        capture = json.loads(self.paths["capture"].read_text(encoding="utf-8"))
        validate_manifest(capture)
        self.assertEqual(len(capture["runs"]), 3)
        self.assertEqual({run["seed"] for run in capture["runs"]}, TRAINING_SEEDS)
        self.assertEqual(self.receipt["arm_online_runs"], 18)
        self.assertEqual(self.receipt["arm_reference_builds"], 18)
        self.assertEqual(self.receipt["binary_sha256"], BINARY_SHA256)
        self.assertFalse(self.receipt["performance_results_consulted"])
        self.assertFalse(self.receipt["confirmation_inputs_generated"])
        payload = dict(self.receipt)
        receipt_hash = payload.pop("receipt_hash")
        self.assertEqual(receipt_hash, object_hash(payload))

    def test_plan_is_frozen_and_seed_boundaries_remain_sealed(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(
            set(plan["information_boundary"]["training_seeds"]), TRAINING_SEEDS
        )
        self.assertEqual(
            plan["information_boundary"]["untouched_confirmation_seeds"],
            [f"E{i}" for i in range(1267, 1287)],
        )
        self.assertEqual(
            PREVIOUS_CONFIRMATION_SEEDS, [f"E{i}" for i in range(1244, 1264)]
        )
        self.assertEqual(plan["paired_design"]["online_runs_per_arm"], 9)
        self.assertEqual(plan["paired_design"]["reference_builds_per_arm"], 9)
        self.assertEqual(plan["paired_design"]["candidate_profile"], ARMS[1][2])
        self.assertEqual(
            plan["sole_changed_axis"]["name"],
            "complete_per_changed_parent_terminal_child_hpa_container_path_service_pareto",
        )

    def test_existing_root_is_never_overwritten(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            prepare_v127(self.root)


if __name__ == "__main__":
    unittest.main()
