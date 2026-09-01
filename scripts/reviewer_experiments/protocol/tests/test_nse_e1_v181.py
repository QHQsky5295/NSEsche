from __future__ import annotations

import hashlib
import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_v177_equivalence_complete_training_v181 as v181,
)


class V181EquivalenceCompletionTests(unittest.TestCase):
    def test_plan_and_result_blind_partition_are_frozen(self) -> None:
        self.assertEqual(
            hashlib.sha256(v181.PLAN.read_bytes()).hexdigest(), v181.PLAN_SHA256
        )
        source = v181._assert_frozen_inputs()
        self.assertEqual(len(source["runs"]), 600)
        evidence = v181._verify_branch_partition(v181.read_json(v181.PLAN))
        self.assertEqual(evidence["source_window_count"], 20000)
        self.assertEqual(evidence["performance_fields_parsed"], 0)
        self.assertEqual(
            evidence["role_counts"],
            {
                "actual_v177_existing": 6,
                "v176_branch_equivalent": 5,
                "v170_branch_equivalent": 4,
                "new_v181_v177_required": 5,
            },
        )

    def test_rewrite_is_exact_fixed_five_run_v177_product(self) -> None:
        source = v181._assert_frozen_inputs()
        manifest = v181._rewrite_candidate(source, "1" * 40)
        v181._validate_product(manifest, bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v181.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 5)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v181.PROFILE},
        )
        self.assertEqual(
            {
                run["metadata"]["v181_performance_summaries_parsed_before_run"]
                for run in manifest["runs"]
            },
            {0},
        )

    def test_complete_profile_composition_is_disjoint_and_exhaustive(self) -> None:
        def rows(seeds: tuple[str, ...], label: str) -> list[dict[str, object]]:
            return [
                {
                    "seed": seed,
                    "run_id": f"{label}.{seed}",
                    "throughput": float(index),
                    "qpr_finite_only": float(index) / 100.0,
                }
                for index, seed in enumerate(seeds, start=1)
            ]

        complete, lineage = v181._compose_complete_profile(
            rows(v181.V170_EQUIVALENT, "v170"),
            rows(v181.V176_EQUIVALENT, "v176"),
            rows(v181.V177_EXISTING, "v177"),
            rows(v181.SEEDS, "v181"),
        )
        self.assertEqual(
            [row["seed"] for row in complete], [f"E{i:02d}" for i in range(1, 21)]
        )
        self.assertEqual(len({item["seed"] for item in lineage}), 20)
        self.assertEqual(
            {item["source_role"] for item in lineage},
            {
                "actual_v177_existing",
                "v176_branch_equivalent",
                "v170_branch_equivalent",
                "new_v181_v177_required",
            },
        )

    def test_plan_freezes_unchanged_full_twenty_gates(self) -> None:
        plan = v181.read_json(v181.PLAN)
        gate = plan["single_reveal_full_twenty_gate"]
        self.assertEqual(gate["throughput"]["comparator"], "Orion")
        self.assertEqual(gate["throughput"]["comparator_mean"], 1.4741)
        self.assertEqual(gate["throughput"]["paired_positive_wins_minimum"], 12)
        self.assertEqual(gate["qpr_finite_only"]["comparator"], "OCS")
        self.assertEqual(gate["qpr_finite_only"]["comparator_mean"], 0.055577160345697)
        self.assertEqual(gate["qpr_finite_only"]["paired_positive_wins_minimum"], 12)
        self.assertTrue(gate["qpr_finite_only"]["all_twenty_candidate_values_finite"])
        self.assertTrue(gate["joint_pass_requires_all_three_gates"])
        self.assertTrue(gate["posthoc_subset_reporting_forbidden"])


if __name__ == "__main__":
    unittest.main()
