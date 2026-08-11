from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.stages import _welfare_pair_digest


class WelfareReferencePairingTests(unittest.TestCase):
    def test_posthoc_welfare_stream_uses_same_build_replay_pair_digest(self) -> None:
        events = [
            {
                "kind": "welfare_window",
                "decision": {"initial_assignment_hash": 11, "assignment_hash": 11},
                "social": {"reference_state_key": 101},
            },
            {
                "kind": "welfare_window",
                "decision": {"initial_assignment_hash": 12, "assignment_hash": 12},
                "social": {"reference_state_key": 102},
            },
            # A repeated state key is intentionally represented once in the
            # immutable reference table and therefore once in the digest.
            {
                "kind": "welfare_window",
                "decision": {"initial_assignment_hash": 11, "assignment_hash": 11},
                "social": {"reference_state_key": 101},
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "welfare_metrics.jsonl"
            path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            count, state_digest, assignment_digest = _welfare_pair_digest(
                path, window_kind="welfare_window"
            )

        expected_state = hashlib.sha256(b"101:11\n102:12\n").hexdigest()
        expected_assignment = hashlib.sha256(b"101:11:11\n102:12:12\n").hexdigest()
        self.assertEqual(count, 2)
        self.assertEqual(state_digest, expected_state)
        self.assertEqual(assignment_digest, expected_assignment)


if __name__ == "__main__":
    unittest.main()
