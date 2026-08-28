from __future__ import annotations

import copy
import unittest
from collections import Counter

from scripts.reviewer_experiments.protocol.nse_e3e4_guarded_anchor_training_blind_audit_v96 import (
    ARMS,
    CONFIRMATION_SEEDS,
    EXPECTED_RUNTIME,
    PLAN_FILE_SHA256,
    TRAINING_SEEDS,
    _assert_hashed_object,
    _assert_ledger_contract,
)
from scripts.reviewer_experiments.protocol.util import object_hash


class GuardedAnchorTrainingBlindAuditV96Tests(unittest.TestCase):
    def test_frozen_arm_matrix_and_runtime(self) -> None:
        self.assertEqual(TRAINING_SEEDS, {"E746", "E747", "E748"})
        self.assertEqual(CONFIRMATION_SEEDS, {f"E{i}" for i in range(766, 786)})
        self.assertEqual(len(ARMS), 5)
        self.assertEqual(
            Counter(item["experiment_id"] for item in ARMS.values()),
            {"E3": 3, "E4": 2},
        )
        self.assertEqual(sum(item["run_count"] for item in ARMS.values()), 33)
        self.assertTrue(
            all("dual_window_safe_pareto" in item["profile"] for item in ARMS.values())
        )
        self.assertEqual(len(PLAN_FILE_SHA256), 64)
        self.assertEqual(len(EXPECTED_RUNTIME["git_commit"]), 40)
        self.assertEqual(len(EXPECTED_RUNTIME["binary_sha256"]), 64)

    def test_hashed_object_rejects_tampering(self) -> None:
        payload = {"performance_results_consulted": False, "runs": 33}
        expected = object_hash(payload)
        value = dict(payload, audit_hash=expected)
        _assert_hashed_object(value, "audit_hash", expected, "fixture")
        tampered = copy.deepcopy(value)
        tampered["runs"] = 32
        with self.assertRaisesRegex(RuntimeError, "self-hash mismatch"):
            _assert_hashed_object(tampered, "audit_hash", expected, "fixture")

    def test_online_ledger_contract_is_exact(self) -> None:
        rows = [
            {"event_type": "batch_started"},
            *({"event_type": "attempt_started"} for _ in range(9)),
            *({"event_type": "attempt_canonicalized"} for _ in range(9)),
            {"event_type": "batch_finished"},
        ]
        expected = Counter(
            {
                "batch_started": 1,
                "attempt_started": 9,
                "attempt_canonicalized": 9,
                "batch_finished": 1,
            }
        )
        _assert_ledger_contract(rows, expected, "fixture")
        rows.append({"event_type": "attempt_quarantined"})
        with self.assertRaisesRegex(RuntimeError, "event contract changed"):
            _assert_ledger_contract(rows, expected, "fixture")


if __name__ == "__main__":
    unittest.main()
