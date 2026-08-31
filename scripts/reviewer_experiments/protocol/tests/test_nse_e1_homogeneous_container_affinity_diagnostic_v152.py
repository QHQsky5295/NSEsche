import unittest

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    COMMON_ENVIRONMENT,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    SEEDS,
    SOURCE_MANIFEST,
    _p95_type7,
    _rewrite_candidate,
    _validate_product,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V152ProtocolTests(unittest.TestCase):
    def test_plan_and_aggregation_boundary_are_frozen(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = read_json(PLAN)
        self.assertEqual(plan["candidate"]["profile"], PROFILE)
        self.assertEqual(tuple(plan["diagnostic_design"]["fixed_order"]), SEEDS)
        self.assertEqual(plan["environment"], COMMON_ENVIRONMENT)
        self.assertFalse(
            plan["diagnosis"]["negative_control_selection"][
                "selection_used_outcome_metrics"
            ]
        )
        self.assertEqual(_p95_type7([0, 10, 20]), 19.0)

    def test_candidate_rewrite_is_exact_two_cell_input_only_product(self) -> None:
        manifest = _rewrite_candidate(read_json(SOURCE_MANIFEST), "1" * 40)
        _validate_product(manifest, references_bound=False)
        self.assertEqual(len(manifest["runs"]), 2)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 2)
        self.assertEqual({run["seed"] for run in manifest["runs"]}, set(SEEDS))
        for run in manifest["runs"]:
            self.assertEqual(run["workload"]["request_freq"], "middle")
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], PROFILE
            )
            self.assertTrue(run["metadata"]["v152_seed_selected_by_input_only_extreme"])
            self.assertEqual(
                run["metadata"][
                    "v152_candidate_performance_summaries_parsed_before_run"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main()
