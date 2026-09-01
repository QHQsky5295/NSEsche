from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_v179_all_nine_preunblinding_analysis_v180 as v180,
)


class V180PreUnblindingTests(unittest.TestCase):
    def test_frozen_inputs_remain_blinded_and_complete(self) -> None:
        failure, blind = v180._assert_inputs()

        self.assertTrue(failure["disposition"]["retain_all_nine_valid_v179_runs"])
        self.assertFalse(
            failure["disposition"]["performance_reveal_or_gate_evaluation"]
        )
        self.assertEqual(
            blind["throughput_completion_latency_cost_qpr_fields_parsed"], 0
        )
        self.assertEqual(blind["run_count"], 9)

    def test_corrected_parent_control_mechanism_gate_passes_all_nine(self) -> None:
        _, blind = v180._assert_inputs()
        gate = v180._mechanism_gate(blind["per_run_result_blind_audits"])

        self.assertTrue(gate["pass"])
        self.assertEqual(gate["reachable_seed_set"], list(v180.REACHABLE_SEEDS))
        self.assertEqual(
            gate["no_activation_control_seed_set"], list(v180.NO_ACTIVATION_SEEDS)
        )

    def test_no_activation_control_tamper_fails_closed(self) -> None:
        _, blind = v180._assert_inputs()
        audits = copy.deepcopy(blind["per_run_result_blind_audits"])
        e10 = next(item for item in audits if item["seed"] == "E10")
        e10["bounded_single_activation_windows"] = 1

        self.assertFalse(v180._mechanism_gate(audits)["pass"])


if __name__ == "__main__":
    unittest.main()
