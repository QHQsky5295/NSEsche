from __future__ import annotations

import copy
import unittest
from collections import Counter

from scripts.reviewer_experiments.protocol.nse_e3e4_low_density_load_pareto_training_blind_audit_v97 import (
    ARMS,
    CONFIRMATION_SEEDS,
    EXPECTED_RUNTIME,
    PREVIOUSLY_RESERVED_SEEDS,
    TRAINING_SEEDS,
    _assert_hashed_object,
    _assert_ledger_contract,
)
from scripts.reviewer_experiments.protocol.util import object_hash


class LowDensityLoadParetoTrainingBlindAuditV97Tests(unittest.TestCase):
    def test_frozen_arm_seed_and_runtime_boundary(self) -> None:
        self.assertEqual(TRAINING_SEEDS, {"E786", "E787", "E788"})
        self.assertEqual(CONFIRMATION_SEEDS, [f"E{i}" for i in range(806, 826)])
        self.assertEqual(PREVIOUSLY_RESERVED_SEEDS, [f"E{i}" for i in range(766, 786)])
        self.assertEqual(len(ARMS), 6)
        self.assertEqual(
            Counter(item["experiment_id"] for item in ARMS.values()),
            {"E3": 3, "E4": 3},
        )
        self.assertEqual(sum(item["run_count"] for item in ARMS.values()), 36)
        self.assertEqual(
            {item["queue_density_threshold"] for item in ARMS.values()},
            {None, 32.0, 64.0},
        )
        self.assertTrue(all(len(value) == 64 for value in EXPECTED_RUNTIME.values()))

    def test_hashed_object_rejects_tampering(self) -> None:
        payload = {"performance_results_consulted": False, "runs": 36}
        value = dict(payload, audit_hash=object_hash(payload))
        self.assertEqual(
            _assert_hashed_object(value, "audit_hash", "fixture"), value["audit_hash"]
        )
        tampered = copy.deepcopy(value)
        tampered["runs"] = 35
        with self.assertRaisesRegex(RuntimeError, "self-hash mismatch"):
            _assert_hashed_object(tampered, "audit_hash", "fixture")

    def test_online_ledger_contract_rejects_any_retry_or_quarantine(self) -> None:
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
