from __future__ import annotations

import copy
import gzip
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_arrival_shock_training_blind_audit_v107 import (
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
    _validate_causal_arrival_shock_diagnostics,
)
from scripts.reviewer_experiments.protocol.util import object_hash


class CausalArrivalShockBlindAuditV107Tests(unittest.TestCase):
    def test_frozen_arm_seed_density_and_runtime_boundary(self) -> None:
        self.assertEqual(TRAINING_SEEDS, {"E890", "E891", "E892"})
        self.assertEqual(CONFIRMATION_SEEDS, [f"E{i}" for i in range(1026, 1046)])
        self.assertEqual(
            PREVIOUS_CONFIRMATION_SEEDS, [f"E{i}" for i in range(926, 1026)]
        )
        self.assertEqual(
            OTHER_UNOPENED_SEEDS,
            [f"E{i}" for i in range(766, 786)]
            + [f"E{i}" for i in range(806, 826)]
            + [f"E{i}" for i in range(846, 866)]
            + [f"E{i}" for i in range(893, 926)],
        )
        self.assertEqual(len(ARMS), 3)
        self.assertEqual(
            Counter(item["experiment_id"] for item in ARMS.values()),
            {"E3": 3},
        )
        self.assertEqual(sum(item["run_count"] for item in ARMS.values()), 27)
        self.assertEqual(CANONICAL_RENAME_RECEIPT, "canonical_rename_receipt_v107.json")
        self.assertEqual(
            {item["shock_rate_ratio"] for item in ARMS.values()},
            {None, "3/2", "2/1"},
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
            {item["arrival_signal"] for item in ARMS.values()},
            {"not_applicable", "first_seen_request_ids_only"},
        )
        self.assertEqual(
            {item["cpu_memory_individual_noninferiority"] for item in ARMS.values()},
            {False, True},
        )
        self.assertEqual(
            {item["resource_bottleneck_sum_noninferiority"] for item in ARMS.values()},
            {False},
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

    def test_causal_diagnostics_use_exact_rate_cross_product(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = "fixture"
            canonical = Path(temp_dir)
            path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
            path.parent.mkdir(parents=True)
            windows = []
            for frame in range(2):
                gate = {
                    "gate_enabled": True,
                    "active": frame == 1,
                    "history_complete": frame == 1,
                    "first_seen_current_frame": 2,
                    "baseline_frames": 80,
                    "recent_frames": 20,
                    "min_requests_per_window": 20,
                    "baseline_count": 80 if frame == 1 else 0,
                    "recent_count": 30 if frame == 1 else 0,
                    "threshold_numerator": 3,
                    "threshold_denominator": 2,
                    "active_frames": 100,
                    "until_frame": 100 if frame == 1 else None,
                    "uses_first_seen_request_ids_only": True,
                }
                windows.append(
                    {
                        "kind": "window",
                        "frame": frame,
                        "decision": {
                            "load_least_dominance_gate": {"causal_arrival_shock": gate}
                        },
                    }
                )
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                for event in windows:
                    handle.write(json.dumps(event) + "\n")
            evidence = _validate_causal_arrival_shock_diagnostics(
                {"run_id": run_id, "simulation": {"total_frame": 2}},
                canonical,
                {
                    "role": "candidate",
                    "shock_threshold_numerator": 3,
                    "shock_threshold_denominator": 2,
                },
            )
            self.assertEqual(evidence["window_count"], 2)
            self.assertEqual(evidence["active_window_count"], 1)
            self.assertEqual(evidence["threshold_met_window_count"], 1)
            self.assertFalse(evidence["performance_fields_consulted"])


if __name__ == "__main__":
    unittest.main()
