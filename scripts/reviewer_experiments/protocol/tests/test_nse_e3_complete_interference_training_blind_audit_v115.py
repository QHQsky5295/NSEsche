from __future__ import annotations

import copy
import gzip
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_complete_interference_training_blind_audit_v115 import (
    ADMITTED_INTERFERENCE_SOURCE,
    ADMITTED_WORK_SOURCE,
    ARMS,
    CONFIRMATION_SEEDS,
    EXPECTED_RUNTIME,
    OTHER_UNOPENED_SEEDS,
    PREVIOUS_CONFIRMATION_SEEDS,
    TRAINING_SEEDS,
    _assert_hashed_object,
    _assert_ledger_contract,
    _validate_admitted_work_diagnostics,
)
from scripts.reviewer_experiments.protocol.util import object_hash


def _critical(invoked: bool, *, work_source: str) -> dict:
    return {
        "gate_enabled": invoked,
        "evaluated": invoked,
        "accepted": invoked,
        "reason": "accepted" if invoked else "not_applicable",
        "critical_player_count": 1 if invoked else 0,
        "candidate_evaluation_count": 2 if invoked else 0,
        "substitution_count": 1 if invoked else 0,
        "proxy_input_unavailable_count": 0,
        "anchor_sum": 10.0 if invoked else None,
        "alternative_sum": 8.5 if invoked else None,
        "alternative_minus_anchor": -1.5 if invoked else None,
        "minimum_individually_accepted_ratio": 0.85 if invoked else None,
        "maximum_individually_accepted_ratio": 0.85 if invoked else None,
        "threshold_numerator": 9 if invoked else None,
        "threshold_denominator": 10 if invoked else None,
        "work_source": work_source,
        "noncritical_players_preserve_exact_anchor": True,
        "proxy_uses_completion_outcomes": False,
        "admitted_interference_pareto": {
            "gate_enabled": invoked,
            "componentwise_gate_enabled": False,
            "rejected_candidate_count": 0,
            "input_unavailable_count": 0,
            "anchor_sum": 4.0 if invoked else None,
            "alternative_sum": 3.5 if invoked else None,
            "alternative_minus_anchor": -0.5 if invoked else None,
            "source": ADMITTED_INTERFERENCE_SOURCE if invoked else "not_applicable",
        },
    }


class CompleteInterferenceBlindAuditV115Tests(unittest.TestCase):
    def test_frozen_arm_seed_and_runtime_boundary(self) -> None:
        self.assertEqual(TRAINING_SEEDS, {"E914", "E915", "E916"})
        self.assertEqual(CONFIRMATION_SEEDS, [f"E{i}" for i in range(1106, 1126)])
        self.assertEqual(
            PREVIOUS_CONFIRMATION_SEEDS, [f"E{i}" for i in range(926, 1106)]
        )
        self.assertEqual(
            OTHER_UNOPENED_SEEDS,
            [f"E{i}" for i in range(766, 786)]
            + [f"E{i}" for i in range(806, 826)]
            + [f"E{i}" for i in range(846, 866)]
            + [f"E{i}" for i in range(917, 926)],
        )
        self.assertEqual(len(ARMS), 2)
        self.assertEqual(sum(item["run_count"] for item in ARMS.values()), 18)
        self.assertEqual(
            {item["work_source"] for item in ARMS.values()},
            {
                ADMITTED_WORK_SOURCE,
                "legacy_task_count_times_current_player_cpu_v108",
            },
        )
        self.assertTrue(all(len(value) == 64 for value in EXPECTED_RUNTIME.values()))

    def test_hashed_object_rejects_tampering(self) -> None:
        payload = {"performance_results_consulted": False, "runs": 18}
        value = dict(payload, audit_hash=object_hash(payload))
        self.assertEqual(
            _assert_hashed_object(value, "audit_hash", "fixture"), value["audit_hash"]
        )
        tampered = copy.deepcopy(value)
        tampered["runs"] = 17
        with self.assertRaisesRegex(RuntimeError, "self-hash mismatch"):
            _assert_hashed_object(tampered, "audit_hash", "fixture")

    def test_online_ledger_contract_rejects_retry(self) -> None:
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

    def test_diagnostics_require_admitted_snapshot_and_ratio_certificate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = "fixture"
            canonical = Path(temp_dir)
            path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
            path.parent.mkdir(parents=True)
            windows = []
            for frame in range(2):
                invoked = frame == 1
                windows.append(
                    {
                        "kind": "window",
                        "frame": frame,
                        "solver": {
                            "termination": "social_gap_zero"
                            if invoked
                            else "no_players"
                        },
                        "cluster": {
                            "queue_pending_cpu_work_total": 4.0,
                            "queue_pending_cpu_work_max": 3.0,
                            "queue_resident_remaining_cpu_work_total": 5.0,
                            "queue_resident_remaining_cpu_work_max": 4.0,
                            "queue_admitted_work_observation_complete": True,
                            "queue_pending_cpu_value_count": 2,
                            "queue_resident_remaining_cpu_value_count": 3,
                            "queue_pending_total": 2,
                            "queue_runnable_total": 1,
                            "queue_resident_total": 3,
                            "queue_runnable_cpu_work_total": 3.0,
                            "queue_runnable_cpu_work_max": 2.5,
                            "queue_cpu_work_observation_complete": True,
                        },
                        "decision": {
                            "load_least_dominance_gate": {
                                "causal_arrival_shock": {
                                    "gate_enabled": True,
                                    "active": invoked,
                                    "history_complete": invoked,
                                    "first_seen_current_frame": 2,
                                    "baseline_frames": 80,
                                    "recent_frames": 20,
                                    "min_requests_per_window": 20,
                                    "baseline_count": 80 if invoked else 0,
                                    "recent_count": 30 if invoked else 0,
                                    "threshold_numerator": 3,
                                    "threshold_denominator": 2,
                                    "active_frames": 50,
                                    "until_frame": 50 if invoked else None,
                                    "uses_first_seen_request_ids_only": True,
                                },
                                "critical_service_proxy": _critical(
                                    invoked,
                                    work_source=ADMITTED_WORK_SOURCE,
                                ),
                            }
                        },
                    }
                )
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                for event in windows:
                    handle.write(json.dumps(event) + "\n")
            expected = next(
                item for item in ARMS.values() if item["role"] == "candidate"
            )
            evidence = _validate_admitted_work_diagnostics(
                {"run_id": run_id, "simulation": {"total_frame": 2}},
                canonical,
                expected,
            )
            self.assertEqual(evidence["window_count"], 2)
            self.assertEqual(evidence["admitted_work_complete_window_count"], 2)
            self.assertEqual(evidence["pending_cpu_value_count"], 4)
            self.assertEqual(evidence["resident_remaining_cpu_value_count"], 6)
            self.assertEqual(evidence["threshold_met_window_count"], 1)
            self.assertEqual(evidence["critical_accepted_window_count"], 1)
            self.assertEqual(evidence["work_source"], ADMITTED_WORK_SOURCE)
            self.assertEqual(
                evidence["admitted_interference_source"],
                ADMITTED_INTERFERENCE_SOURCE,
            )
            self.assertEqual(evidence["admitted_interference_finite_window_count"], 1)
            self.assertEqual(evidence["admitted_interference_accepted_window_count"], 1)
            self.assertEqual(
                evidence["admitted_interference_rejected_candidate_count"], 0
            )
            self.assertFalse(
                evidence["componentwise_admitted_interference_gate_enabled"]
            )
            self.assertFalse(evidence["performance_fields_consulted"])

            windows[1]["decision"]["load_least_dominance_gate"][
                "critical_service_proxy"
            ]["admitted_interference_pareto"].update(
                {
                    "alternative_sum": 4.1,
                    "alternative_minus_anchor": 0.1,
                }
            )
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                for event in windows:
                    handle.write(json.dumps(event) + "\n")
            with self.assertRaisesRegex(
                RuntimeError, "accepted worse admitted interference"
            ):
                _validate_admitted_work_diagnostics(
                    {"run_id": run_id, "simulation": {"total_frame": 2}},
                    canonical,
                    expected,
                )

    def test_diagnostics_reject_legacy_or_incomplete_admitted_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = "fixture"
            canonical = Path(temp_dir)
            path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
            path.parent.mkdir(parents=True)
            event = {
                "kind": "window",
                "frame": 0,
                "solver": {"termination": "social_gap_zero"},
                "cluster": {
                    "queue_pending_cpu_work_total": None,
                    "queue_pending_cpu_work_max": None,
                    "queue_resident_remaining_cpu_work_total": None,
                    "queue_resident_remaining_cpu_work_max": None,
                    "queue_admitted_work_observation_complete": False,
                    "queue_pending_cpu_value_count": None,
                    "queue_resident_remaining_cpu_value_count": None,
                    "queue_pending_total": 0,
                    "queue_runnable_total": 0,
                    "queue_resident_total": 0,
                    "queue_runnable_cpu_work_total": 0.0,
                    "queue_runnable_cpu_work_max": 0.0,
                    "queue_cpu_work_observation_complete": True,
                },
                "decision": {
                    "load_least_dominance_gate": {
                        "causal_arrival_shock": {
                            "gate_enabled": True,
                            "active": True,
                            "history_complete": True,
                            "first_seen_current_frame": 20,
                            "baseline_frames": 80,
                            "recent_frames": 20,
                            "min_requests_per_window": 20,
                            "baseline_count": 80,
                            "recent_count": 30,
                            "threshold_numerator": 3,
                            "threshold_denominator": 2,
                            "active_frames": 50,
                            "until_frame": 49,
                            "uses_first_seen_request_ids_only": True,
                        },
                        "critical_service_proxy": _critical(
                            True,
                            work_source="legacy_task_count_times_current_player_cpu_v108",
                        ),
                    }
                },
            }
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps(event) + "\n")
            expected = next(
                item for item in ARMS.values() if item["role"] == "candidate"
            )
            with self.assertRaisesRegex(
                RuntimeError, "admitted-work observation changed"
            ):
                _validate_admitted_work_diagnostics(
                    {"run_id": run_id, "simulation": {"total_frame": 1}},
                    canonical,
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
