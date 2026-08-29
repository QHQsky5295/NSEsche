from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_blind_audit_v136 import (
    _assert_clean_ledger,
    _canonical_evidence,
    _validate_declared_product,
)
from scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_prepare_v136 import (
    BASELINE_METHODS,
    PLAN_SHA256,
    SCENARIOS,
    SEED_LIST,
)


def _run(method: str, scenario: str, seed: str) -> dict:
    kind = {
        "spike5x50ms": "spike",
        "sustained3x200ms": "sustained",
        "pulse4x4x50ms": "pulse",
    }[scenario]
    return {
        "run_id": f"{method}.{scenario}.{seed}",
        "run_spec_hash": "a" * 64,
        "workload_spec_hash": "b" * 64,
        "common_hpa_hash": "c" * 64,
        "method": method,
        "experiment_id": "E3",
        "seed": seed,
        "cluster": {"node_count": 20, "topology": "heterogeneous"},
        "simulation": {
            "arrival_horizon_frames": 1000,
            "observation_horizon_frames": 1000,
            "total_frame": 4000,
        },
        "workload": {
            "request_freq": "middle",
            "topology": "heterogeneous",
            "qos_profile": "balanced",
            "burst": {"kind": kind},
        },
        "reference_dependency": None,
        "metadata": {
            "v136_plan_sha256": PLAN_SHA256,
            "v136_diagnostic_only": True,
            "v136_role": "paper_baseline",
            "v136_complete_method_seed_scenario_product": True,
            "v136_baseline_performance_consulted_before_execution": False,
            "v136_NSESche_reused_not_rerun": True,
            "v136_confirmation_inputs_opened": False,
            "v136_seed_or_scenario_label_used_by_policy": False,
            "v136_outcome_fields_used_by_policy": False,
        },
    }


class AllBaselineClosureBlindAuditV136Tests(unittest.TestCase):
    def test_declared_product_accepts_only_complete_product(self) -> None:
        runs = [
            _run(method, scenario, seed)
            for method in BASELINE_METHODS
            for scenario in SCENARIOS
            for seed in SEED_LIST
        ]
        _validate_declared_product(runs)
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            _validate_declared_product(runs[:-1])

    def test_clean_ledger_rejects_retry_or_quarantine(self) -> None:
        clean = [
            {"event_type": "batch_started"},
            *[{"event_type": "attempt_started"} for _ in range(2)],
            *[{"event_type": "attempt_canonicalized"} for _ in range(2)],
            {"event_type": "batch_finished"},
        ]
        _assert_clean_ledger(clean, 2, "synthetic")
        with self.assertRaisesRegex(RuntimeError, "contract changed"):
            _assert_clean_ledger(
                [*clean, {"event_type": "attempt_quarantined"}], 2, "synthetic"
            )

    def test_canonical_evidence_never_opens_performance_summary(self) -> None:
        run = _run("greedy", "spike5x50ms", "E1448")
        run.update(
            {
                "workload_tape": {
                    "key": "tape",
                    "sha256": "d" * 64,
                    "capture_environment": {"capture_environment_sha256": "e" * 64},
                },
                "sla_targets": {"artifact_sha256": "f" * 64},
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary)
            for name in ("manifest.json", "qc_report.json"):
                (canonical / name).write_text("{}", encoding="utf-8")

            def fake_read(path: Path):
                self.assertNotEqual(path.name, "summary.json")
                if path.name == "attempt.json":
                    return {
                        "attempt": 1,
                        "status": "qc_pass",
                        "classification": "qc_pass",
                        "timed_out": False,
                        "exit_code": 0,
                        "result_sha256": "1" * 64,
                    }
                if path.name == "qc_report.json":
                    return {"passed": True, "classification": "qc_pass"}
                return {
                    "adapter_binary": {"verified_sha256": "2" * 64},
                    "software_environment": {
                        "git": {"commit": "3" * 40},
                        "python": {"executable_sha256": "4" * 64},
                        "cargo_lock": {"sha256": "5" * 64},
                    },
                }

            with mock.patch(
                "scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_blind_audit_v136.validate_canonical_run"
            ), mock.patch(
                "scripts.reviewer_experiments.protocol.nse_e3_all_baseline_closure_diagnostic_blind_audit_v136.read_json",
                side_effect=fake_read,
            ):
                evidence, _ = _canonical_evidence(
                    run, canonical, "6" * 64, "paper_baseline", "7" * 64
                )
        self.assertFalse(evidence["performance_fields_consulted"])


if __name__ == "__main__":
    unittest.main()
