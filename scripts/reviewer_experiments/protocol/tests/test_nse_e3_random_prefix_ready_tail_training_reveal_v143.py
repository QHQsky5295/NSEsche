from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.reviewer_experiments.protocol import (
    nse_e3_random_prefix_ready_tail_training_reveal_v143 as reveal_v143,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_prepare_v143 import (
    ARM_ID,
    NEW_CONFIRMATION_SEEDS,
    PLAN_SHA256,
    TRAINING_SEED_LIST,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_reveal_v143 import (
    METRICS,
    _validate_blind_audit,
    _validate_blind_document,
    evaluate_training_rows,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
    SCENARIOS,
)
from scripts.reviewer_experiments.protocol.util import object_hash


def _rows() -> list[dict]:
    rows = []
    for method_index, method in enumerate(BASELINE_METHODS):
        for scenario in SCENARIOS:
            for seed in TRAINING_SEED_LIST:
                value = 1.0 + method_index / 100.0
                rows.append(
                    {
                        "method_label": method,
                        "scenario": scenario,
                        "seed": seed,
                        "run_id": f"baseline-{method}-{scenario}-{seed}",
                        "fixed_window_completed": 1,
                        **{metric: value for metric in METRICS},
                    }
                )
    for scenario in SCENARIOS:
        for seed in TRAINING_SEED_LIST:
            rows.append(
                {
                    "method_label": ARM_ID,
                    "scenario": scenario,
                    "seed": seed,
                    "run_id": f"candidate-{scenario}-{seed}",
                    "fixed_window_completed": 1,
                    **{metric: 2.0 for metric in METRICS},
                }
            )
    return rows


def _blind() -> dict:
    payload = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_READY_TAIL_BLIND_AUDIT_V143_V1",
        "status": "pass",
        "plan_file_sha256": PLAN_SHA256,
        "performance_summaries_parsed": 0,
        "performance_results_consulted_for_mechanism_design": True,
        "candidate_performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "baseline_rerun_count": 0,
        "baseline_run_count": 81,
        "candidate_run_count": 9,
        "analyzed_run_count": 90,
        "reference_count": 9,
        "tape_count": 12,
        "block_count": 9,
        "training_seeds": TRAINING_SEED_LIST,
        "sealed_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
    }
    payload["audit_hash"] = object_hash(payload)
    return payload


class ReadyTailRevealV143Tests(unittest.TestCase):
    def test_all_nine_strict_gates_authorize_only_confirmation_generation(self) -> None:
        result = evaluate_training_rows(_rows())
        self.assertTrue(result["family_training_gate_pass"])
        self.assertEqual(result["candidate_result"]["score"]["passed_gate_count"], 9)
        self.assertTrue(result["confirmation_input_generation_authorized"])
        self.assertFalse(result["confirmation_inputs_generated"])
        self.assertFalse(result["paper_claim_authorized"])

    def test_one_failed_metric_falsifies_the_candidate(self) -> None:
        rows = _rows()
        for row in rows:
            if row["method_label"] == ARM_ID and row["scenario"] == SCENARIOS[0]:
                row[METRICS[0]] = 0.0
        result = evaluate_training_rows(rows)
        self.assertFalse(result["family_training_gate_pass"])
        self.assertEqual(result["passing_candidate_rankings"], [])
        self.assertIsNone(result["selected_profile"])
        self.assertFalse(result["confirmation_input_generation_authorized"])

    def test_blind_document_rejects_candidate_performance_access(self) -> None:
        blind = _blind()
        _validate_blind_document(blind, blind["audit_hash"])
        tampered = dict(blind)
        tampered["candidate_performance_results_consulted"] = True
        tampered.pop("audit_hash")
        tampered["audit_hash"] = object_hash(tampered)
        with self.assertRaisesRegex(RuntimeError, "does not authorize"):
            _validate_blind_document(tampered, tampered["audit_hash"])

    def test_reveal_accepts_only_the_frozen_blind_hash(self) -> None:
        blind = _validate_blind_audit()
        self.assertEqual(blind["audit_hash"], reveal_v143.BLIND_AUDIT_HASH)
        with patch.object(reveal_v143, "BLIND_AUDIT_HASH", "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "does not authorize"):
                _validate_blind_audit()


if __name__ == "__main__":
    unittest.main()
