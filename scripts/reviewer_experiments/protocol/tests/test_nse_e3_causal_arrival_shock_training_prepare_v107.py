from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_arrival_shock_training_prepare_v107 import (
    ARMS,
    BINARY_SHA256,
    CONFIRMATION_SEEDS,
    OTHER_UNOPENED_SEEDS,
    PREVIOUS_CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    TRAINING_SEEDS,
    _paths,
    arm_path,
    prepare_v107,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash


class CausalArrivalShockPreparationV107Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name) / "v107"
        cls.receipt = prepare_v107(cls.root)
        cls.paths = _paths(cls.root)
        cls.arms = {
            arm_id: json.loads(arm_path(cls.root, arm_id).read_text(encoding="utf-8"))
            for arm_id, _, _, _, _, _ in ARMS
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_arms_profiles_density_bounds_and_runtime(self) -> None:
        expected = {
            arm_id: (
                experiment_id,
                role,
                profile,
                shock_rate_ratio,
                count,
            )
            for arm_id, experiment_id, role, profile, shock_rate_ratio, count in ARMS
        }
        self.assertEqual(Counter(item[1] for item in ARMS), {"E3": 3})
        self.assertEqual(sum(item[-1] for item in ARMS), 27)
        for arm_id, manifest in self.arms.items():
            (
                experiment_id,
                role,
                profile,
                shock_rate_ratio,
                count,
            ) = expected[arm_id]
            validate_manifest(manifest)
            self.assertEqual(len(manifest["runs"]), count)
            self.assertEqual(
                {run["experiment_id"] for run in manifest["runs"]}, {experiment_id}
            )
            self.assertEqual({run["seed"] for run in manifest["runs"]}, TRAINING_SEEDS)
            self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
            self.assertEqual(
                {
                    run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                    for run in manifest["runs"]
                },
                {profile},
            )
            self.assertEqual(
                {run["metadata"]["v107_shock_rate_ratio"] for run in manifest["runs"]},
                {shock_rate_ratio},
            )
            self.assertTrue(
                all(
                    run["metadata"]["v107_nonterminal_queue_density_floor"]
                    == (8.0 if role == "candidate" else None)
                    and run["metadata"]["v107_warm_admissibility"]
                    == ("preserve_anchor_warmness" if role == "candidate" else None)
                    and run["metadata"]["v107_causal_arrival_shock_initializer_guard"]
                    is (role == "candidate")
                    and run["metadata"]["v107_load_least_window_certificate_mode"]
                    == ("disabled" if role == "candidate" else "not_applicable")
                    and run["metadata"]["v107_arrival_signal"]
                    == (
                        "first_seen_request_ids_only"
                        if role == "candidate"
                        else "not_applicable"
                    )
                    and run["metadata"]["v107_cpu_memory_individual_noninferiority"]
                    is (role == "candidate")
                    and run["metadata"]["v107_resource_bottleneck_sum_noninferiority"]
                    is False
                    and run["metadata"]["v107_shock_threshold_numerator"]
                    == ({"3/2": 3, "2/1": 2}.get(shock_rate_ratio))
                    and run["metadata"]["v107_shock_threshold_denominator"]
                    == ({"3/2": 2, "2/1": 1}.get(shock_rate_ratio))
                    and run["metadata"]["v107_arrival_history_baseline_frames"]
                    == (80 if role == "candidate" else None)
                    and run["metadata"]["v107_arrival_history_recent_frames"]
                    == (20 if role == "candidate" else None)
                    and run["metadata"]["v107_arrival_min_requests_per_window"]
                    == (20 if role == "candidate" else None)
                    and run["metadata"]["v107_shock_activation_horizon_frames"]
                    == (100 if role == "candidate" else None)
                    and run["metadata"]["v107_resource_inputs_finite_fail_closed"]
                    is (role == "candidate")
                    and run["metadata"]["v107_scalar_faasrank_noninferiority"]
                    is (role == "candidate")
                    and run["metadata"]["v107_input_locality_component_noninferiority"]
                    is (role == "candidate")
                    and run["metadata"]["v107_componentwise_faasrank_noninferiority"]
                    is False
                    and run["metadata"][
                        "v107_per_child_current_warm_downstream_locality_noninferiority"
                    ]
                    is (role == "candidate")
                    and run["metadata"][
                        "v107_downstream_locality_aggregate_compensation_allowed"
                    ]
                    is False
                    and run["metadata"][
                        "v107_future_child_placement_or_feasibility_used"
                    ]
                    is False
                    and run["metadata"]["v107_critical_frontier_protection"]
                    is (role == "candidate")
                    and run["metadata"]["v107_critical_frontier_rank_source"]
                    == (
                        "immutable_srpt_remaining_critical_path_rank"
                        if role == "candidate"
                        else "not_applicable"
                    )
                    and run["metadata"]["v107_critical_frontier_tie_rule"]
                    == (
                        "protect_missing_nonfinite_singleton_or_rank_plus_epsilon_ge_request_frontier_maximum"
                        if role == "candidate"
                        else "not_applicable"
                    )
                    and run["metadata"][
                        "v107_only_strictly_lower_rank_parallel_players_may_substitute"
                    ]
                    is (role == "candidate")
                    and run["metadata"]["v107_outcome_fields_drive_policy"] is False
                    and run["metadata"]["v107_scenario_or_burst_label_used_by_policy"]
                    is False
                    and run["metadata"][
                        "v107_completion_or_performance_fields_used_by_policy"
                    ]
                    is False
                    and run["metadata"]["v107_future_arrivals_used_by_policy"] is False
                    and run["metadata"]["v107_substitution_cap"] is None
                    and run["metadata"]["v107_confirmation_seeds_opened"] is False
                    and run["metadata"]["v107_other_unopened_seeds_opened"] is False
                    and run["seed"] not in CONFIRMATION_SEEDS
                    and run["seed"] not in OTHER_UNOPENED_SEEDS
                    for run in manifest["runs"]
                )
            )
            self.assertEqual(len(manifest["reference_build_dependencies"]), count)

    def test_arm_references_are_unique_and_tapes_are_paired(self) -> None:
        references = [
            {item["key"] for item in manifest["reference_build_dependencies"]}
            for manifest in self.arms.values()
        ]
        self.assertEqual(sum(map(len, references)), 27)
        self.assertEqual(len(set().union(*references)), 27)
        tape_sets = {
            arm_id: {
                key
                for run in manifest["runs"]
                for key in (
                    run["workload_tape"]["key"],
                    run["workload_tape"].get("parent_key"),
                )
                if key is not None
            }
            for arm_id, manifest in self.arms.items()
        }
        sets = list(tape_sets.values())
        self.assertTrue(all(keys == sets[0] for keys in sets[1:]))
        self.assertEqual(len(sets[0]), 12)

    def test_capture_and_receipt_close_information_boundary(self) -> None:
        capture = json.loads(self.paths["capture"].read_text(encoding="utf-8"))
        validate_manifest(capture)
        self.assertEqual(len(capture["runs"]), 3)
        self.assertEqual({run["method"] for run in capture["runs"]}, {"greedy"})
        self.assertEqual({run["seed"] for run in capture["runs"]}, TRAINING_SEEDS)
        self.assertEqual(self.receipt["arm_online_runs"], 27)
        self.assertEqual(self.receipt["arm_reference_builds"], 27)
        self.assertEqual(self.receipt["binary_sha256"], BINARY_SHA256)
        self.assertFalse(self.receipt["confirmation_inputs_generated"])
        self.assertFalse(self.receipt["other_unopened_inputs_generated"])
        self.assertEqual(
            self.receipt["previous_confirmation_seeds_remaining_sealed"],
            PREVIOUS_CONFIRMATION_SEEDS,
        )
        payload = dict(self.receipt)
        receipt_hash = payload.pop("receipt_hash")
        self.assertEqual(receipt_hash, object_hash(payload))

    def test_plan_is_frozen_and_matches_exact_seed_boundary(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(set(plan["training_design"]["training_seeds"]), TRAINING_SEEDS)
        self.assertEqual(
            plan["training_design"]["sealed_confirmation_seeds"],
            CONFIRMATION_SEEDS,
        )
        self.assertEqual(
            plan["training_design"][
                "previous_confirmation_seed_range_remaining_sealed"
            ],
            "E926-E1025",
        )
        self.assertEqual(
            PREVIOUS_CONFIRMATION_SEEDS, [f"E{i}" for i in range(926, 1026)]
        )
        self.assertEqual(plan["training_design"]["candidate_online_runs"], 18)
        self.assertEqual(plan["training_design"]["anchor_online_runs"], 9)
        self.assertEqual(plan["training_design"]["total_online_runs"], 27)
        self.assertEqual(
            {
                (item["arm_id"], item["role"], item["profile"], item["run_count"])
                for item in plan["arms"]
            },
            {
                (arm_id, role, profile, count)
                for arm_id, _, role, profile, _, count in ARMS
            },
        )
        self.assertFalse(
            plan["invariants"]["confirmation_inputs_generated_before_training_pass"]
        )

    def test_existing_root_is_never_overwritten(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            prepare_v107(self.root)


if __name__ == "__main__":
    unittest.main()
