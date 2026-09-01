from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_queue8_cpu2_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v179 as v179,
)


class V179ProtocolTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_unbound_product(self) -> None:
        source = v179._assert_frozen_inputs()
        manifest = v179._rewrite_candidate(source, "0" * 40)
        v179._validate_product(manifest, bound=False)

        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v179.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 9)
        self.assertFalse(manifest["all_references_bound"])
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {v179.PROFILE},
        )
        self.assertEqual(
            {
                run["metadata"][
                    "v179_candidate_performance_summaries_parsed_before_run"
                ]
                for run in manifest["runs"]
            },
            {0},
        )

    def test_hybrid_partition_is_complete_disjoint_and_result_independent(self) -> None:
        v170 = [{"seed": f"E{index:02d}", "source": "v170"} for index in range(1, 21)]
        v176 = [{"seed": seed, "source": "v176"} for seed in v179.v176.SEEDS]
        candidate = [{"seed": seed, "source": "v179"} for seed in v179.SEEDS]

        hybrid = v179._hybrid_rows(v170, v176, candidate)
        by_seed = {row["seed"]: row["source"] for row in hybrid}

        self.assertEqual(len(hybrid), 20)
        self.assertEqual(
            [row["seed"] for row in hybrid], [f"E{i:02d}" for i in range(1, 21)]
        )
        self.assertEqual(
            {seed for seed, source in by_seed.items() if source == "v179"},
            set(v179.SEEDS),
        )
        self.assertEqual(
            {seed for seed, source in by_seed.items() if source == "v176"},
            set(v179.V176_REUSE_SEEDS),
        )
        self.assertEqual(
            {seed for seed, source in by_seed.items() if source == "v170"},
            set(v179.V170_REUSE_SEEDS),
        )

    def test_frozen_assignment_controls_have_exact_window_cardinality(self) -> None:
        self.assertEqual(len(v179._frozen_assignment_hashes("E01")), 1000)
        self.assertEqual(len(v179._frozen_assignment_hashes("E09")), 1000)

    def test_prepare_writes_only_the_sealed_unbound_product(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "v179"
            receipt = v179.prepare_v179(root)
            output = v179.paths(root)

            manifest = v179.load_and_validate_manifest(output["manifest"])
            v179._validate_product(manifest, bound=False)
            self.assertEqual(receipt["candidate_online_runs"], 9)
            self.assertEqual(receipt["candidate_reference_builds"], 9)
            self.assertEqual(receipt["baseline_reruns"], 0)
            self.assertTrue(output["prepared"].is_file())
            self.assertTrue(output["schedule"].is_file())
            self.assertFalse(output["workspace"].exists())


if __name__ == "__main__":
    unittest.main()
