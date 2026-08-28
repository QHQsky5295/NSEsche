from __future__ import annotations

import copy
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_critical_frontier_safety_training_blind_audit_v105 import (
    ARMS,
    CANONICAL_RENAME_RECEIPT,
    CONFIRMATION_SEEDS,
    EXPECTED_RUNTIME,
    OTHER_UNOPENED_SEEDS,
    PREVIOUS_CONFIRMATION_SEEDS,
    TRAINING_SEEDS,
    _assert_hashed_object,
    _assert_ledger_contract,
    _stage_root_from_receipts,
)
from scripts.reviewer_experiments.protocol.util import object_hash


class CriticalFrontierSafetyBlindAuditV105Tests(unittest.TestCase):
    def test_frozen_arm_seed_density_and_runtime_boundary(self) -> None:
        self.assertEqual(TRAINING_SEEDS, {"E884", "E885", "E886"})
        self.assertEqual(CONFIRMATION_SEEDS, [f"E{i}" for i in range(986, 1006)])
        self.assertEqual(
            PREVIOUS_CONFIRMATION_SEEDS, [f"E{i}" for i in range(926, 986)]
        )
        self.assertEqual(
            OTHER_UNOPENED_SEEDS,
            [f"E{i}" for i in range(766, 786)]
            + [f"E{i}" for i in range(806, 826)]
            + [f"E{i}" for i in range(846, 866)]
            + [f"E{i}" for i in range(887, 926)],
        )
        self.assertEqual(len(ARMS), 3)
        self.assertEqual(
            Counter(item["experiment_id"] for item in ARMS.values()),
            {"E3": 3},
        )
        self.assertEqual(sum(item["run_count"] for item in ARMS.values()), 27)
        self.assertEqual(CANONICAL_RENAME_RECEIPT, "canonical_rename_receipt_v105.json")
        self.assertEqual(
            {item["upper_queue_density_threshold"] for item in ARMS.values()},
            {None, 24.0},
        )
        self.assertEqual(
            {item["warm_admissibility"] for item in ARMS.values()},
            {None, "preserve_anchor_warmness"},
        )
        self.assertEqual(
            {item["load_least_window_certificate_mode"] for item in ARMS.values()},
            {"not_applicable", "disabled"},
        )
        self.assertEqual(
            {item["component_safety_mode"] for item in ARMS.values()},
            {
                "not_applicable",
                "input_and_per_child_current_warm_downstream_locality_noninferiority",
                "componentwise_cpu_memory_locality_warm_diversity_plus_per_child_current_warm_downstream_locality_noninferiority",
            },
        )
        self.assertEqual(
            {item["critical_frontier_protection"] for item in ARMS.values()},
            {False, True},
        )
        self.assertTrue(all(len(value) == 64 for value in EXPECTED_RUNTIME.values()))

    def test_hashed_object_rejects_tampering(self) -> None:
        payload = {"performance_results_consulted": False, "runs": 27}
        value = dict(payload, audit_hash=object_hash(payload))
        self.assertEqual(
            _assert_hashed_object(value, "audit_hash", "fixture"), value["audit_hash"]
        )
        tampered = copy.deepcopy(value)
        tampered["runs"] = 26
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

    def test_stage_root_is_derived_from_sealed_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stage = Path(temp_dir) / "custom_stage"
            entries = {
                f"key-{index}": {
                    "receipt_path": str(
                        stage / "canonical" / f"key-{index}" / "receipt.json"
                    )
                }
                for index in range(3)
            }
            self.assertEqual(
                _stage_root_from_receipts(entries, "receipt_path", 3, "fixture"),
                stage.resolve(),
            )
            entries["key-2"]["receipt_path"] = str(
                Path(temp_dir) / "other_stage" / "canonical" / "key-2" / "receipt.json"
            )
            with self.assertRaisesRegex(RuntimeError, "stage roots changed"):
                _stage_root_from_receipts(entries, "receipt_path", 3, "fixture")


if __name__ == "__main__":
    unittest.main()
