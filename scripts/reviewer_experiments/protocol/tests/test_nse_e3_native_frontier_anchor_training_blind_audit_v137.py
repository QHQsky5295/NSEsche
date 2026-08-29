from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_native_frontier_anchor_training_blind_audit_v137 import (
    _validate_native_diagnostics,
)


def window_event(frame: int, *, extra_players: int = 0) -> dict:
    return {
        "kind": "window",
        "frame": frame,
        "decision": {
            "request_function_players": 1,
            "native_shadow_anchor": {
                "kind": "greedy",
                "valid": True,
                "commands": 1,
                "duplicate_commands": 0,
                "unexpected_messages": 0,
                "missing_players": 0,
                "extra_players": extra_players,
                "infeasible_commands": 0,
                "anchor_assignment_hash": 11,
                "ordered_command_hash": 22,
                "certificate_uses_completion_outcomes": False,
                "initializer_readiness_service_players": 1,
                "proposal_readiness_service_players": 1,
                "initializer_readiness_service_complete": True,
                "proposal_readiness_service_complete": True,
                "initializer_readiness_service_sum": 2.0,
                "proposal_readiness_service_sum": 1.0,
                "initializer_readiness_service_max": 1.0,
                "proposal_readiness_service_max": 1.0,
                "readiness_service_sum_delta": -1.0,
                "readiness_service_max_delta": 0.0,
            },
            "window_safe_guard": {
                "accepted": True,
                "reason": "accepted_native_readiness_service_and_welfare",
                "baseline_welfare_delta": 0.5,
            },
        },
    }


class NativeFrontierAnchorBlindAuditV137Tests(unittest.TestCase):
    def _write(self, root: Path, run_id: str, *, corrupt: bool) -> Path:
        canonical = root / "canonical"
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        with gzip.open(record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8") as out:
            for frame in range(4000):
                out.write(
                    json.dumps(
                        window_event(
                            frame, extra_players=1 if corrupt and frame == 7 else 0
                        )
                    )
                    + "\n"
                )
        return canonical

    def test_valid_native_shadow_and_service_certificates_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v137"
            canonical = self._write(Path(temporary), run_id, corrupt=False)
            evidence = _validate_native_diagnostics(
                {"run_id": run_id}, canonical, "greedy"
            )
            self.assertEqual(evidence["window_count"], 4000)
            self.assertEqual(evidence["native_player_window_count"], 4000)
            self.assertEqual(evidence["service_certificate_window_count"], 4000)
            self.assertEqual(evidence["accepted_proposal_window_count"], 4000)
            self.assertFalse(evidence["performance_fields_consulted"])

    def test_any_shadow_alignment_error_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v137-corrupt"
            canonical = self._write(Path(temporary), run_id, corrupt=True)
            with self.assertRaisesRegex(RuntimeError, "native anchor mismatch"):
                _validate_native_diagnostics({"run_id": run_id}, canonical, "greedy")

    def test_unavailable_proposal_certificate_is_audited_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v137-unavailable-proposal"
            canonical = Path(temporary) / "canonical"
            record = canonical / "reviewer_records" / run_id
            record.mkdir(parents=True)
            with gzip.open(
                record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8"
            ) as out:
                for frame in range(4000):
                    event = window_event(frame)
                    native = event["decision"]["native_shadow_anchor"]
                    native.update(
                        {
                            "proposal_readiness_service_players": 0,
                            "proposal_readiness_service_complete": False,
                            "proposal_readiness_service_sum": None,
                            "proposal_readiness_service_max": None,
                            "readiness_service_sum_delta": None,
                            "readiness_service_max_delta": None,
                        }
                    )
                    event["decision"]["window_safe_guard"].update(
                        {
                            "accepted": False,
                            "reason": "proposal_readiness_service_unavailable",
                        }
                    )
                    out.write(json.dumps(event) + "\n")
            evidence = _validate_native_diagnostics(
                {"run_id": run_id}, canonical, "greedy"
            )
            self.assertEqual(evidence["service_certificate_window_count"], 0)
            self.assertEqual(evidence["accepted_proposal_window_count"], 0)

    def test_empty_window_not_applicable_diagnostics_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_id = "synthetic-v137-empty-window"
            canonical = Path(temporary) / "canonical"
            record = canonical / "reviewer_records" / run_id
            record.mkdir(parents=True)
            with gzip.open(
                record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8"
            ) as out:
                for frame in range(4000):
                    event = window_event(frame)
                    if frame == 0:
                        event["decision"]["request_function_players"] = 0
                        native = event["decision"]["native_shadow_anchor"]
                        native.update(
                            {
                                "kind": None,
                                "valid": False,
                                "commands": 0,
                                "anchor_assignment_hash": None,
                                "ordered_command_hash": None,
                                "initializer_readiness_service_players": 0,
                                "proposal_readiness_service_players": 0,
                                "initializer_readiness_service_complete": False,
                                "proposal_readiness_service_complete": False,
                            }
                        )
                        event["decision"]["window_safe_guard"].update(
                            {
                                "accepted": False,
                                "evaluated": False,
                                "reason": "not_applicable",
                            }
                        )
                    out.write(json.dumps(event) + "\n")
            evidence = _validate_native_diagnostics(
                {"run_id": run_id}, canonical, "greedy"
            )
            self.assertEqual(evidence["native_player_window_count"], 3999)
            self.assertEqual(evidence["guard_reasons"]["not_applicable"], 1)


if __name__ == "__main__":
    unittest.main()
