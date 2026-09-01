from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_v177_matched_v176_control_result_blind_audit_v178 as v178,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V178MatchedV176ControlTests(unittest.TestCase):
    def test_frozen_inputs_and_exact_control_product(self) -> None:
        self.assertEqual(file_hash(v178.PLAN), v178.PLAN_SHA256)
        self.assertEqual(file_hash(v178.V177_FAILURE), v178.V177_FAILURE_SHA256)
        self.assertEqual(file_hash(v178.BINARY_PATH), v178.BINARY_SHA256)
        plan = read_json(v178.PLAN)
        self.assertFalse(plan["v177_performance_results_consulted_for_design"])
        self.assertEqual(
            plan["matched_v176_control"]["new_control_seeds"],
            list(v178.CONTROL_SEEDS),
        )
        self.assertEqual(plan["matched_v176_control"]["new_online_runs"], 5)
        self.assertEqual(plan["matched_v176_control"]["new_reference_builds"], 5)
        self.assertEqual(
            plan["matched_v176_control"]["reused_control_seed"],
            v178.REUSED_CONTROL_SEED,
        )
        source = v178._assert_frozen_inputs()
        manifest = v178._rewrite_control(source, "c" * 40)
        v178._validate_product(manifest, references_bound=False)
        self.assertEqual(
            [run["seed"] for run in manifest["runs"]], list(v178.CONTROL_SEEDS)
        )
        self.assertEqual(len(manifest["reference_build_dependencies"]), 5)
        for run in manifest["runs"]:
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], v178.PROFILE
            )
            self.assertEqual(run["metadata"]["v178_performance_fields_to_parse"], 0)
            self.assertFalse(run["metadata"]["v178_candidate_rerun"])

    def test_matched_sequence_gate_requires_first_difference_at_severe_frame(
        self,
    ) -> None:
        control = tuple(range(1000))
        candidate = list(control)
        candidate[20] += 10_000
        candidate[21] += 10_000
        evidence = v178._compare_sequences(tuple(candidate), control, 20)
        self.assertTrue(evidence["pass"])
        self.assertEqual(evidence["first_assignment_mismatch_frame"], 20)
        self.assertTrue(evidence["pre_first_severe_assignment_prefix_matches"])
        self.assertTrue(evidence["first_severe_assignment_differs"])

    def test_matched_sequence_gate_rejects_earlier_primary_difference(self) -> None:
        control = tuple(range(1000))
        candidate = list(control)
        candidate[6] += 10_000
        candidate[20] += 10_000
        evidence = v178._compare_sequences(tuple(candidate), control, 20)
        self.assertFalse(evidence["pass"])
        self.assertEqual(evidence["first_assignment_mismatch_frame"], 6)
        self.assertFalse(evidence["pre_first_severe_assignment_prefix_matches"])

    def test_matched_input_gate_rejects_tape_drift(self) -> None:
        candidate = {
            "seed": "E06",
            "cell_id": "cell",
            "workload_spec_hash": "w",
            "cluster": {"node_count": 20},
            "simulation": {"total_frame": 1000},
            "common_hpa_hash": "h",
            "workload_tape": {
                "sha256": "t",
                "receipt_sha256": "r",
                "event_count": 1,
                "seed": 6,
            },
        }
        control = copy.deepcopy(candidate)
        v178._assert_matched_inputs(candidate, control)
        control["workload_tape"]["sha256"] = "changed"
        with self.assertRaisesRegex(RuntimeError, "tape mismatch"):
            v178._assert_matched_inputs(candidate, control)


if __name__ == "__main__":
    unittest.main()
