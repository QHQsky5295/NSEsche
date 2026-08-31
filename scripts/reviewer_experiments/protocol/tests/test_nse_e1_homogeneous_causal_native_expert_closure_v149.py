from __future__ import annotations

import unittest

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_blind_audit_v149 import (
    _expected_route,
    _validate_candidate_selection,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_prepare_v149 import (
    ARM_ID,
    LOADS,
    PROFILE,
    SEEDS,
    SOURCE_MANIFEST,
    _classifier_input_evidence,
    _rewrite_candidate,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    BASELINE_LABELS,
    _evaluate_load,
    _metrics,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import read_json


class V149ProtocolTests(unittest.TestCase):
    def test_causal_route_boundaries_are_frozen(self) -> None:
        self.assertEqual(_expected_route("high", 18), ("ocs", "unclassified", 0))
        self.assertEqual(_expected_route("high", 19), ("jiagu", "high", 1))
        self.assertEqual(_expected_route("middle", 98), ("ocs", "unclassified", 0))
        self.assertEqual(_expected_route("middle", 99), ("faasrank", "middle", 1))
        self.assertEqual(_expected_route("low", 98), ("ocs", "unclassified", 0))
        self.assertEqual(_expected_route("low", 99), ("ocs", "low", 1))

    def test_native_candidate_certificate_and_empty_window(self) -> None:
        _validate_candidate_selection([], "ocs", 0)
        with self.assertRaisesRegex(RuntimeError, "empty V149 window"):
            _validate_candidate_selection([{"kind": "ocs"}], "ocs", 0)
        candidates = [
            {
                "kind": "ocs",
                "selected": False,
                "valid": True,
                "service_complete": True,
                "service_sum": 10.0,
                "service_max": 6.0,
                "paper_welfare": 4.0,
            },
            {
                "kind": "orion",
                "selected": True,
                "valid": True,
                "service_complete": True,
                "service_sum": 9.0,
                "service_max": 6.0,
                "paper_welfare": 4.0,
            },
        ]
        _validate_candidate_selection(candidates, "ocs", 2)
        candidates[1]["paper_welfare"] = 3.0
        with self.assertRaisesRegex(RuntimeError, "Orion advisory selection"):
            _validate_candidate_selection(candidates, "ocs", 2)

    def test_metric_conventions_and_frozen_training_gate(self) -> None:
        self.assertEqual(
            _metrics(1.0, 2.0, 4.0, 1.0),
            {
                "throughput": 1.0,
                "qpr_finite_only": 0.125,
                "qpr_zero_completed_as_zero": 0.125,
            },
        )
        self.assertEqual(
            _metrics(0.0, None, None, 0.0),
            {
                "throughput": 0.0,
                "qpr_finite_only": None,
                "qpr_zero_completed_as_zero": 0.0,
            },
        )
        for load in LOADS:
            candidate = [
                {
                    "load": load,
                    "seed": seed,
                    "throughput": 3.0,
                    "qpr_finite_only": 3.0,
                    "qpr_zero_completed_as_zero": 3.0,
                }
                for seed in SEEDS
            ]
            throughput_ceiling = {
                "low": "Orion",
                "middle": "FaaSRank",
                "high": "Jiagu",
            }[load]
            qpr_ceiling = {"low": "OCS", "middle": "FaaSRank", "high": "Jiagu"}[load]
            baselines = []
            for algorithm in BASELINE_LABELS:
                for seed in SEEDS:
                    baselines.append(
                        {
                            "load": load,
                            "seed": seed,
                            "algorithm": algorithm,
                            "throughput": 2.0
                            if algorithm == throughput_ceiling
                            else 1.0,
                            "qpr_finite_only": 2.0 if algorithm == qpr_ceiling else 1.0,
                            "qpr_zero_completed_as_zero": (
                                2.0 if algorithm == qpr_ceiling else 1.0
                            ),
                        }
                    )
            result = _evaluate_load(load, candidate, baselines)
            self.assertTrue(result["all_three_metric_gates_pass"])
            for gate in result["gates"].values():
                self.assertEqual(gate["paired_positive_wins"], 20)

    @unittest.skipUnless(
        SOURCE_MANIFEST.is_file(), "frozen E1 source manifest is not present"
    )
    def test_candidate_rewrite_is_exact_and_result_blind(self) -> None:
        source = read_json(SOURCE_MANIFEST)
        evidence = _classifier_input_evidence(source)
        self.assertEqual(len(evidence), 60)
        manifest = _rewrite_candidate(source, "a" * 40)
        validate_manifest(manifest)
        self.assertEqual(len(manifest["runs"]), 60)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 60)
        self.assertFalse(manifest["all_references_bound"])
        self.assertEqual(
            {
                (run["workload"]["request_freq"], run["seed"])
                for run in manifest["runs"]
            },
            {(load, seed) for load in LOADS for seed in SEEDS},
        )
        self.assertEqual({run["method"] for run in manifest["runs"]}, {"sche_nash"})
        self.assertEqual({run["variant"] for run in manifest["runs"]}, {ARM_ID})
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"]
                for run in manifest["runs"]
            },
            {PROFILE},
        )
        self.assertEqual(
            {
                run["environment"]["NASH_OPERATIONAL_DIRECT_INITIALIZATION"]
                for run in manifest["runs"]
            },
            {"1"},
        )
        marker = manifest["integration_smoke_shard"]
        self.assertEqual(marker["v149_baseline_rerun_count"], 0)
        self.assertEqual(marker["v149_candidate_performance_summaries_parsed"], 0)


if __name__ == "__main__":
    unittest.main()
