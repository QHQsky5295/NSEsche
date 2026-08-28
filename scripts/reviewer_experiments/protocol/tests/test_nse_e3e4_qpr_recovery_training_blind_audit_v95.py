from __future__ import annotations

import copy
import unittest
from collections import Counter

from scripts.reviewer_experiments.protocol.nse_e3e4_qpr_recovery_training_blind_audit_v95 import (
    CANDIDATES,
    CONFIRMATION_SEEDS,
    EXPECTED_RUNTIME,
    PLAN_FILE_SHA256,
    TRAINING_SEEDS,
    _assert_hashed_object,
    _assert_ledger_contract,
)
from scripts.reviewer_experiments.protocol.util import object_hash


class V95QprRecoveryTrainingBlindAuditTests(unittest.TestCase):
    def test_frozen_candidate_matrix_and_runtime(self) -> None:
        self.assertEqual(TRAINING_SEEDS, {"E726", "E727", "E728"})
        self.assertEqual(CONFIRMATION_SEEDS, {"E729", "E730", "E731"})
        self.assertEqual(len(CANDIDATES), 3)
        self.assertEqual(
            {item["E3_profile"] for item in CANDIDATES.values()},
            {
                "srpt_ready_hiku_load_faithful",
                "srpt_ready_hiku2_ocs_borda",
                "srpt_ready_hiku_ocs3_borda",
            },
        )
        self.assertEqual(
            {item["E4_profile"] for item in CANDIDATES.values()},
            {
                "srpt_ready_load_least_current_demand",
                "srpt_ready_faasrank_load_least_borda",
                "srpt_ready_hiku2_ocs_borda",
            },
        )
        self.assertEqual(len(PLAN_FILE_SHA256), 64)
        self.assertEqual(len(EXPECTED_RUNTIME["git_commit"]), 40)
        self.assertEqual(len(EXPECTED_RUNTIME["binary_sha256"]), 64)

    def test_hashed_object_rejects_content_tampering(self) -> None:
        payload = {"performance_results_consulted": False, "runs": 36}
        expected = object_hash(payload)
        value = dict(payload, receipt_hash=expected)
        _assert_hashed_object(value, "receipt_hash", expected, "fixture")

        tampered = copy.deepcopy(value)
        tampered["runs"] = 35
        with self.assertRaisesRegex(RuntimeError, "self-hash mismatch"):
            _assert_hashed_object(tampered, "receipt_hash", expected, "fixture")

    def test_ledger_contract_is_exact(self) -> None:
        rows = [
            {"event_type": "batch_started"},
            *({"event_type": "attempt_started"} for _ in range(12)),
            *({"event_type": "attempt_canonicalized"} for _ in range(12)),
            {"event_type": "batch_finished"},
        ]
        expected = Counter(
            {
                "batch_started": 1,
                "attempt_started": 12,
                "attempt_canonicalized": 12,
                "batch_finished": 1,
            }
        )
        _assert_ledger_contract(rows, expected, "fixture")
        rows.append({"event_type": "attempt_quarantined"})
        with self.assertRaisesRegex(RuntimeError, "event contract changed"):
            _assert_ledger_contract(rows, expected, "fixture")


if __name__ == "__main__":
    unittest.main()
