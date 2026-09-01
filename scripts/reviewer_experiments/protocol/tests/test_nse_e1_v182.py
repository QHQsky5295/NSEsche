from __future__ import annotations

import hashlib
import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_queue8_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_equivalence_complete_training_v182 as v182,
)


class V182EquivalenceCompletionTests(unittest.TestCase):
    def test_plan_implementation_and_result_blind_partition_are_frozen(self) -> None:
        self.assertEqual(
            hashlib.sha256(v182.PLAN.read_bytes()).hexdigest(), v182.PLAN_SHA256
        )
        self.assertEqual(
            hashlib.sha256(v182.IMPLEMENTATION.read_bytes()).hexdigest(),
            v182.IMPLEMENTATION_SHA256,
        )
        source = v182._assert_frozen_inputs()
        self.assertEqual(len(source["runs"]), 600)
        evidence = v182._verify_equivalence_partition(v182.read_json(v182.PLAN))
        self.assertEqual(evidence["source_window_count"], 25000)
        self.assertEqual(evidence["performance_fields_parsed"], 0)
        self.assertEqual(
            evidence["role_counts"],
            {
                "v179_behavior_equivalent": 4,
                "v168_behavior_equivalent": 1,
                "v177_behavior_equivalent": 11,
                "new_v182_required": 4,
            },
        )

    def test_rewrite_is_exact_fixed_four_run_v182_product(self) -> None:
        source = v182._assert_frozen_inputs()
        manifest = v182._rewrite_candidate(dict(source), "1" * 40)
        v182._validate_product(manifest, bound=False)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v182.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 4)
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v182.PROFILE},
        )
        self.assertEqual(
            {
                run["metadata"]["v182_performance_summaries_parsed_before_run"]
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

        v181_rows = rows(tuple(f"E{i:02d}" for i in range(1, 21)), "v181")
        complete, lineage = v182._compose_complete_profile(
            rows(v182.V179_EQUIVALENT, "v179"),
            rows(v182.V168_EQUIVALENT, "v168"),
            v181_rows,
            rows(v182.SEEDS, "v182"),
        )
        self.assertEqual(
            [row["seed"] for row in complete], [f"E{i:02d}" for i in range(1, 21)]
        )
        self.assertEqual(len({item["seed"] for item in lineage}), 20)
        self.assertEqual(
            {item["source_role"] for item in lineage},
            {
                "v179_behavior_equivalent",
                "v168_behavior_equivalent",
                "v177_behavior_equivalent",
                "new_v182_required",
            },
        )

    def test_plan_freezes_unchanged_full_twenty_gates(self) -> None:
        plan = v182.read_json(v182.PLAN)
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
