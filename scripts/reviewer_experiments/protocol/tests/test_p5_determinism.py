from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.protocol.p5_determinism import (
    p5_policy_action_sequence_hash,
)


class P5PolicyActionDeterminismTests(unittest.TestCase):
    @staticmethod
    def _decision() -> dict[str, object]:
        return {
            "initial_assignment_hash": "a" * 64,
            "assignment_hash": "b" * 64,
            "complete_assignment": True,
            "assigned_players": 7,
            "assigned_node_count": 4,
            "commands_prepared": 7,
            "commands_sent": 7,
            "scale_ups_prepared": 1,
            "scale_ups_sent": 1,
            "dispatch_channel_failed": False,
            "invalid_assignments": 0,
            "no_feasible_players": 0,
            "waiting_for_candidate_nodes": 0,
            "placement_dispersion_normalized": 0.9,
        }

    def test_decision_neutral_float_drift_is_excluded(self) -> None:
        canonical = self._decision()
        duplicate = copy.deepcopy(canonical)
        duplicate["placement_dispersion_normalized"] = 0.9000000596046448
        self.assertEqual(
            p5_policy_action_sequence_hash([canonical]),
            p5_policy_action_sequence_hash([duplicate]),
        )

    def test_action_field_drift_changes_digest(self) -> None:
        canonical = self._decision()
        duplicate = copy.deepcopy(canonical)
        duplicate["assignment_hash"] = "c" * 64
        self.assertNotEqual(
            p5_policy_action_sequence_hash([canonical]),
            p5_policy_action_sequence_hash([duplicate]),
        )

    def test_window_order_is_bound(self) -> None:
        first = self._decision()
        second = copy.deepcopy(first)
        second["assignment_hash"] = "d" * 64
        self.assertNotEqual(
            p5_policy_action_sequence_hash([first, second]),
            p5_policy_action_sequence_hash([second, first]),
        )


if __name__ == "__main__":
    unittest.main()
