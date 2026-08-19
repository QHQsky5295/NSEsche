from __future__ import annotations

import copy
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.ledger import Ledger
from scripts.reviewer_experiments.protocol.qc import technical_failure_signature
from scripts.reviewer_experiments.protocol.technical_timeout_recovery import (
    E2_ORIGINAL_RUNTIME_IDENTITY,
    RECOVERY_BLOCK_REASON,
    TechnicalTimeoutRecoveryError,
    TechnicalTimeoutRecoveryRunner,
    build_recovery_manifest,
    merge_timeout_recovery,
    plan_timeout_recovery,
    plan_timeout_recovery_tier2,
    revalidate_timeout_recovery_plan,
    select_repeated_timeout_blocks,
)
import scripts.reviewer_experiments.protocol.technical_timeout_recovery as recovery_mod
from scripts.reviewer_experiments.protocol.cli import main as protocol_main
from scripts.reviewer_experiments.protocol.util import (
    object_hash,
    write_json_atomic,
)


class TechnicalTimeoutRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source_manifest_path = self.root / "manifest.json"
        self.source_workspace = self.root / "source" / "formal-runs"
        self.source_workspace.mkdir(parents=True)
        for name in ("canonical", "quarantine", "partial"):
            (self.source_workspace / name).mkdir()
        self.runs = [
            {
                "run_id": "E2.test.canonical",
                "run_spec_hash": "1" * 64,
                "seed": "E01",
                "experiment_id": "E2",
                "cell_id": "cell-canonical",
            },
            {
                "run_id": "E2.test.timeout-a",
                "run_spec_hash": "2" * 64,
                "seed": "E02",
                "experiment_id": "E2",
                "cell_id": "cell-timeout",
            },
            {
                "run_id": "E2.test.timeout-b",
                "run_spec_hash": "3" * 64,
                "seed": "E03",
                "experiment_id": "E2",
                "cell_id": "cell-timeout",
            },
        ]
        manifest = {
            "schema_version": "1.0",
            "protocol_id": "test-protocol",
            "execution": {
                "timeout_seconds": 1800,
                "max_attempts": 3,
                "command_template": ["python", "-m", "adapter"],
                "result_relative_path": "summary.json",
            },
            "runs": copy.deepcopy(self.runs),
        }
        manifest["manifest_hash"] = object_hash(manifest)
        write_json_atomic(self.source_manifest_path, manifest)
        self.manifest = manifest
        self.ledger = Ledger(self.source_workspace / "ledger.jsonl")
        self.ledger.append(
            "batch_started", {"manifest_hash": self.manifest["manifest_hash"]}
        )
        self.identity = copy.deepcopy(E2_ORIGINAL_RUNTIME_IDENTITY)
        self._write_canonical(
            self.runs[0], self.source_workspace / "canonical" / self.runs[0]["run_id"]
        )
        for index, run in enumerate(self.runs[1:], start=1):
            run_root = self.source_workspace / "quarantine" / run["run_id"]
            run_root.mkdir(parents=True)
            for attempt in (1, 2):
                self._write_timeout_attempt(
                    run, run_root / f"attempt-{attempt:02d}", attempt
                )
            # Empty parent directories left by the real runner are allowed.
            (self.source_workspace / "partial" / run["run_id"]).mkdir()
            self.ledger.append(
                "run_blocked",
                {
                    "run_id": run["run_id"],
                    "run_spec_hash": run["run_spec_hash"],
                    "seed": run["seed"],
                    "attempts_used": [1, 2],
                    "reason": "repeated_technical_failure_signature",
                    "failure_signature": technical_failure_signature(
                        {
                            "passed": False,
                            "classification": "timeout",
                            "issues": [
                                {
                                    "code": "timeout",
                                    "message": "wall timeout",
                                    "details": {},
                                }
                            ],
                        }
                    ),
                },
            )
        self.ledger.append(
            "batch_finished",
            {
                "manifest_hash": self.manifest["manifest_hash"],
                "selected_run_count": len(self.runs),
                "canonicalized": 1,
                "blocked": 2,
                "preflight_blocked": 0,
            },
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _audit(self, run: dict, *, status: str, lineage: dict | None = None) -> dict:
        audit = {
            "schema_version": "NSE_RUN_AUDIT_MANIFEST_V1",
            "status": status,
            "protocol_manifest": {
                "manifest_hash": self.manifest["manifest_hash"],
                "path": str(self.source_manifest_path),
            },
            "run": {"run_id": run["run_id"], "frozen_spec": copy.deepcopy(run)},
            "software_environment": {
                "git": {"commit": self.identity["git_commit"]},
                "python": {
                    "executable_sha256": self.identity["python_executable_sha256"]
                },
                "cargo_lock": {"sha256": self.identity["cargo_lock_sha256"]},
            },
            "adapter_binary": {
                "observed_sha256": self.identity["adapter_binary_sha256"]
            },
        }
        if lineage is not None:
            audit["technical_timeout_recovery"] = copy.deepcopy(lineage)
        audit["audit_manifest_hash"] = object_hash(audit)
        return audit

    def _write_canonical(
        self, run: dict, path: Path, *, lineage: dict | None = None
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            path / "attempt.json",
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "attempt": 1,
                "status": "qc_pass",
                "classification": "qc_pass",
                "result_sha256": None,
            },
        )
        write_json_atomic(path / "summary.json", {"run_id": run["run_id"]})
        metadata = __import__("json").loads((path / "attempt.json").read_text())
        metadata["result_sha256"] = (
            __import__("hashlib")
            .sha256((path / "summary.json").read_bytes())
            .hexdigest()
        )
        write_json_atomic(path / "attempt.json", metadata)
        write_json_atomic(
            path / "qc_report.json",
            {"passed": True, "classification": "qc_pass", "issues": []},
        )
        audit = self._audit(run, status="canonical", lineage=lineage)
        audit["final_artifacts"] = [
            {
                "relative_path": item.relative_to(path).as_posix(),
                "sha256": __import__("hashlib").sha256(item.read_bytes()).hexdigest(),
                "bytes": item.stat().st_size,
            }
            for item in sorted(path.rglob("*"))
            if item.is_file()
        ]
        audit["audit_manifest_hash"] = object_hash(
            {key: value for key, value in audit.items() if key != "audit_manifest_hash"}
        )
        write_json_atomic(path / "manifest.json", audit)

    def _write_timeout_attempt(self, run: dict, path: Path, attempt: int) -> None:
        path.mkdir(parents=True, exist_ok=True)
        qc = {
            "passed": False,
            "classification": "timeout",
            "issues": [{"code": "timeout", "message": "wall timeout", "details": {}}],
        }
        qc["failure_signature"] = technical_failure_signature(qc)
        write_json_atomic(path / "qc_report.json", qc)
        write_json_atomic(
            path / "process_observation.json",
            {
                "timed_out": True,
                "duration_seconds": 1800.01,
                "exit_code": 15,
            },
        )
        write_json_atomic(
            path / "attempt.json",
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "attempt": attempt,
            },
        )
        write_json_atomic(
            path / "manifest.json", self._audit(run, status="quarantined")
        )

    def test_selection_is_evidence_derived_and_does_not_read_result_metrics(
        self,
    ) -> None:
        evidence = select_repeated_timeout_blocks(
            self.source_manifest_path,
            self.source_workspace,
            expected_count=2,
            expected_runtime_identity=self.identity,
        )
        self.assertEqual(evidence["run_ids"], [run["run_id"] for run in self.runs[1:]])
        self.assertFalse(evidence["metrics_consulted"])
        self.assertEqual(
            evidence["runtime_identity"],
            {
                **self.identity,
                "runtime_git_commit": self.identity["git_commit"],
                "runtime_binary_sha256": self.identity["adapter_binary_sha256"],
            },
        )

    def test_selection_rejects_a_live_partial(self) -> None:
        partial = (
            self.source_workspace / "partial" / self.runs[1]["run_id"] / "attempt-03"
        )
        partial.mkdir(parents=True)
        with self.assertRaises(TechnicalTimeoutRecoveryError):
            select_repeated_timeout_blocks(
                self.source_manifest_path,
                self.source_workspace,
                expected_count=2,
            )

    def test_selection_rejects_an_unterminated_ordinary_batch(self) -> None:
        self.ledger.append(
            "batch_started", {"manifest_hash": self.manifest["manifest_hash"]}
        )
        with self.assertRaisesRegex(
            TechnicalTimeoutRecoveryError, "no later successful batch_finished event"
        ):
            select_repeated_timeout_blocks(
                self.source_manifest_path,
                self.source_workspace,
                expected_count=2,
            )

    def test_plan_self_hash_and_scoped_manifest(self) -> None:
        plan_path = self.root / "recovery-plan.json"
        plan = plan_timeout_recovery(
            self.source_manifest_path,
            self.source_workspace,
            plan_path,
            expected_count=2,
            expected_runtime_identity=self.identity,
            require_formal_e2=False,
        )
        self.assertEqual(plan["source"]["ledger_sequence"], 4)
        self.assertEqual(plan["execution_override"]["tier"], 1)
        self.assertEqual(plan["execution_override"]["timeout_seconds"], 3600.0)
        recovery_manifest = build_recovery_manifest(self.manifest, plan)
        self.assertEqual(recovery_manifest["execution"]["timeout_seconds"], 3600)
        self.assertEqual(
            recovery_manifest["execution"]["command_template"][-2:],
            ["--request-timeout", "3590"],
        )
        marker = recovery_manifest["technical_timeout_recovery"]
        self.assertEqual(marker["source_manifest_hash"], self.manifest["manifest_hash"])
        self.assertFalse(marker["metrics_consulted"])

    def test_tier2_plan_reuses_original_manifest_and_selects_only_remaining_block(
        self,
    ) -> None:
        tier1_plan_path = self.root / "tier1-plan.json"
        tier1_workspace = self.root / "tier1-recovery" / "formal-runs"
        tier1_workspace.mkdir(parents=True)
        for name in ("canonical", "quarantine", "partial"):
            (tier1_workspace / name).mkdir()
        tier1_plan = plan_timeout_recovery(
            self.source_manifest_path,
            self.source_workspace,
            tier1_plan_path,
            expected_count=2,
            expected_runtime_identity=self.identity,
            recovery_workspace=tier1_workspace,
            require_formal_e2=False,
        )
        tier1_control = build_recovery_manifest(
            self.source_manifest_path,
            tier1_plan,
            manifest_path=tier1_workspace / "manifest.json",
        )
        tier1_ledger = Ledger(tier1_workspace / "ledger.jsonl")
        binding = recovery_mod._lifecycle_binding(tier1_plan, tier1_control)
        started = tier1_ledger.append("technical_timeout_recovery_started", binding)
        lineage = tier1_control["technical_timeout_recovery"]
        self._write_canonical(
            self.runs[1],
            tier1_workspace / "canonical" / self.runs[1]["run_id"],
            lineage=lineage,
        )
        blocked_run = self.runs[2]
        blocked_root = tier1_workspace / "quarantine" / blocked_run["run_id"]
        blocked_root.mkdir(parents=True)
        for attempt in (1, 2):
            self._write_timeout_attempt(
                blocked_run, blocked_root / f"attempt-{attempt:02d}", attempt
            )
        timeout_qc = {
            "passed": False,
            "classification": "timeout",
            "issues": [{"code": "timeout", "message": "wall timeout", "details": {}}],
        }
        tier1_ledger.append(
            "run_blocked",
            {
                "run_id": blocked_run["run_id"],
                "run_spec_hash": blocked_run["run_spec_hash"],
                "seed": blocked_run["seed"],
                "attempts_used": [1, 2],
                "reason": RECOVERY_BLOCK_REASON,
                "failure_signature": technical_failure_signature(timeout_qc),
            },
        )
        tier1_ledger.append(
            "technical_timeout_recovery_finished",
            {
                **binding,
                "started_event_hash": started["event_hash"],
                "dispositions": [
                    {"run_id": self.runs[1]["run_id"], "status": "canonicalized"},
                    {"run_id": blocked_run["run_id"], "status": "blocked"},
                ],
                "canonicalized": 1,
                "blocked": 1,
                "preflight_blocked": 0,
            },
        )
        tier2_plan_path = self.root / "tier2-plan.json"
        tier2_plan = plan_timeout_recovery_tier2(
            tier1_plan_path,
            tier1_workspace,
            tier2_plan_path,
            require_formal_e2=False,
        )
        self.assertEqual(tier2_plan["selection"]["run_ids"], [blocked_run["run_id"]])
        self.assertEqual(
            tier2_plan["source"]["manifest_hash"], self.manifest["manifest_hash"]
        )
        self.assertEqual(
            tier2_plan["source"]["quiescent_boundary"]["kind"],
            "technical_timeout_recovery",
        )
        self.assertEqual(tier2_plan["execution_override"]["tier"], 2)
        self.assertEqual(tier2_plan["execution_override"]["timeout_seconds"], 7200.0)
        tier2_manifest = build_recovery_manifest(self.manifest, tier2_plan)
        self.assertEqual(tier2_manifest["execution"]["timeout_seconds"], 7200)
        self.assertEqual(
            tier2_manifest["execution"]["command_template"][-2:],
            ["--request-timeout", "7190"],
        )
        self.assertEqual(
            revalidate_timeout_recovery_plan(tier2_plan_path)["plan_sha256"],
            tier2_plan["plan_sha256"],
        )

    def test_merge_original_wins_and_requires_all_runs(self) -> None:
        plan_path = self.root / "recovery-plan.json"
        recovery_workspace = self.root / "recovery" / "formal-runs"
        recovery_workspace.mkdir(parents=True)
        for name in ("canonical", "quarantine", "partial"):
            (recovery_workspace / name).mkdir()
        plan = plan_timeout_recovery(
            self.source_manifest_path,
            self.source_workspace,
            plan_path,
            expected_count=2,
            expected_runtime_identity=self.identity,
            recovery_workspace=recovery_workspace,
            require_formal_e2=False,
        )
        recovery_manifest = build_recovery_manifest(
            self.manifest, plan, manifest_path=recovery_workspace / "manifest.json"
        )
        recovery_ledger = Ledger(recovery_workspace / "ledger.jsonl")
        recovery_ledger.append(
            "technical_timeout_recovery_started",
            recovery_mod._lifecycle_binding(plan, recovery_manifest),
        )
        lineage = recovery_manifest["technical_timeout_recovery"]
        # Recovery audits retain the original protocol hash while carrying the
        # plan lineage; this is what strict source exporters consume.
        for run in self.runs[1:]:
            self._write_canonical(
                run,
                recovery_workspace / "canonical" / run["run_id"],
                lineage=lineage,
            )
        # Simulate the original finishing one planned run later: original wins.
        self._write_canonical(
            self.runs[1],
            self.source_workspace / "canonical" / self.runs[1]["run_id"],
        )
        with self.assertRaisesRegex(
            TechnicalTimeoutRecoveryError, "exactly one finish event"
        ):
            merge_timeout_recovery(
                self.source_manifest_path,
                self.source_workspace,
                plan_path,
                recovery_workspace,
                self.root / "composite-before-finish" / "formal-runs",
                expected_count=3,
            )
        dispositions = [
            {"run_id": run["run_id"], "status": "canonicalized"}
            for run in self.runs[1:]
        ]
        recovery_ledger.append(
            "technical_timeout_recovery_finished",
            {
                **recovery_mod._lifecycle_binding(plan, recovery_manifest),
                "started_event_hash": list(recovery_ledger.iter_events())[-1][
                    "event_hash"
                ],
                "dispositions": dispositions,
                "canonicalized": 2,
                "blocked": 0,
                "preflight_blocked": 0,
            },
        )
        composite = merge_timeout_recovery(
            self.source_manifest_path,
            self.source_workspace,
            plan_path,
            recovery_workspace,
            self.root / "composite" / "formal-runs",
            expected_count=3,
        )
        self.assertEqual(composite["canonical_count"], 3)
        self.assertEqual(composite["origins"][self.runs[1]["run_id"]], "original")
        self.assertEqual(
            composite["origins"][self.runs[2]["run_id"]], "technical_timeout_recovery"
        )
        self.assertTrue(
            (Path(composite["workspace"]) / "composite_lineage.json").is_file()
        )

    def test_runner_audit_hook_keeps_source_protocol_hash_and_lineage(self) -> None:
        class Delegate:
            @staticmethod
            def audit(*args, **kwargs):
                return {
                    "protocol_manifest": {
                        "path": "control.json",
                        "manifest_hash": "control-hash",
                        "file_sha256": "control-file",
                    },
                    "audit_manifest_hash": "stale",
                }

        facade = TechnicalTimeoutRecoveryRunner.__new__(TechnicalTimeoutRecoveryRunner)
        facade._audit_delegate = Delegate.audit
        facade._source_manifest_path = "source.json"
        facade._source_manifest_hash = "source-hash"
        facade._source_manifest_file_sha256 = "source-file"
        facade._lineage = {
            "schema_version": "NSE_TECHNICAL_TIMEOUT_RECOVERY_MANIFEST_V1",
            "plan_sha256": "plan-hash",
            "metrics_consulted": False,
        }
        audited = facade._audit_manifest_payload("ignored")
        self.assertEqual(audited["protocol_manifest"]["manifest_hash"], "source-hash")
        self.assertEqual(audited["protocol_manifest"]["path"], "source.json")
        self.assertEqual(
            audited["technical_timeout_recovery"]["plan_sha256"], "plan-hash"
        )
        self.assertFalse(audited["technical_timeout_recovery"]["metrics_consulted"])
        self.assertEqual(
            audited["audit_manifest_hash"],
            object_hash(
                {
                    key: value
                    for key, value in audited.items()
                    if key != "audit_manifest_hash"
                }
            ),
        )

    def test_formal_plan_gate_rejects_synthetic_manifest(self) -> None:
        with self.assertRaisesRegex(TechnicalTimeoutRecoveryError, "formal E2"):
            plan_timeout_recovery(
                self.source_manifest_path,
                self.source_workspace,
                self.root / "formal-plan.json",
                expected_count=2,
                expected_runtime_identity=self.identity,
            )

    def test_cli_exposes_fixed_sealed_recovery_arguments(self) -> None:
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(
            captured
        ):
            protocol_main(["run-timeout-recovery", "--help"])
        self.assertEqual(raised.exception.code, 0)
        help_text = captured.getvalue()
        self.assertNotIn("--run-id", help_text)
        self.assertNotIn("--timeout", help_text)
        self.assertNotIn("--adapter-request", help_text)
        captured = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(
            captured
        ):
            protocol_main(["plan-timeout-recovery-tier2", "--help"])
        self.assertEqual(raised.exception.code, 0)
        help_text = captured.getvalue()
        self.assertNotIn("--timeout", help_text)
        self.assertNotIn("--adapter-request", help_text)

    def _synthetic_plan_and_control(self):
        plan_path = self.root / "lifecycle-plan.json"
        recovery_workspace = self.root / "lifecycle-recovery" / "formal-runs"
        recovery_workspace.mkdir(parents=True)
        for name in ("canonical", "quarantine", "partial"):
            (recovery_workspace / name).mkdir()
        plan = plan_timeout_recovery(
            self.source_manifest_path,
            self.source_workspace,
            plan_path,
            expected_count=2,
            expected_runtime_identity=self.identity,
            recovery_workspace=recovery_workspace,
            require_formal_e2=False,
        )
        control_path = recovery_workspace / "manifest.json"
        control = build_recovery_manifest(
            self.source_manifest_path, plan, manifest_path=control_path
        )
        return plan, plan_path, recovery_workspace, control_path, control

    def test_control_manifest_is_deterministic_and_tamper_evident(self) -> None:
        plan, _, workspace, control_path, control = self._synthetic_plan_and_control()
        self.assertEqual(
            recovery_mod._load_sealed_control_manifest(plan, control_path), control
        )
        tampered = copy.deepcopy(control)
        tampered["execution"]["max_attempts"] = 99
        tampered["manifest_hash"] = object_hash(
            {key: value for key, value in tampered.items() if key != "manifest_hash"}
        )
        write_json_atomic(control_path, tampered)
        with self.assertRaisesRegex(TechnicalTimeoutRecoveryError, "deterministic"):
            recovery_mod._load_sealed_control_manifest(plan, control_path)

    def test_execution_revalidation_rejects_source_ledger_growth(self) -> None:
        plan, plan_path, _, _, _ = self._synthetic_plan_and_control()
        self.assertEqual(
            revalidate_timeout_recovery_plan(plan_path)["plan_sha256"],
            plan["plan_sha256"],
        )
        self.ledger.append(
            "batch_finished",
            {
                "manifest_hash": self.manifest["manifest_hash"],
                "selected_run_count": len(self.runs),
                "canonicalized": 1,
                "blocked": 2,
                "preflight_blocked": 0,
            },
        )
        with self.assertRaisesRegex(TechnicalTimeoutRecoveryError, "ledger changed"):
            revalidate_timeout_recovery_plan(plan_path)

    def test_facade_lifecycle_lock_resume_and_terminal_idempotence(self) -> None:
        plan, _, workspace, _, control = self._synthetic_plan_and_control()
        recovery_ledger = Ledger(workspace / "ledger.jsonl")

        class FakeRunner:
            def __init__(self) -> None:
                self.manifest = control
                self.ledger = recovery_ledger

        facade = TechnicalTimeoutRecoveryRunner.__new__(TechnicalTimeoutRecoveryRunner)
        from scripts.reviewer_experiments.protocol.runner import _WorkspaceLock

        facade.plan = plan
        facade.workspace = workspace
        facade.manifest = control
        facade._runner = FakeRunner()
        facade.ledger = recovery_ledger
        facade._workspace_lock_class = _WorkspaceLock
        facade._selected_run_order = tuple(plan["selection"]["run_ids"])
        facade._selected_run_ids = frozenset(facade._selected_run_order)
        facade._protocol_run_error = RuntimeError
        facade._lifecycle_active = False
        facade._execution_settings = lambda: control["execution"]
        facade._run_one = lambda run: {
            "run_id": run["run_id"],
            "status": "blocked" if run["run_id"].endswith("b") else "canonicalized",
        }
        results = facade.run()
        self.assertEqual(len(results), 2)
        events = list(recovery_ledger.iter_events())
        self.assertEqual(
            [event["event_type"] for event in events],
            [
                "technical_timeout_recovery_started",
                "technical_timeout_recovery_finished",
            ],
        )
        second = facade.run()
        self.assertEqual(
            [item["run_id"] for item in second], list(facade._selected_run_order)
        )
        self.assertEqual(len(list(recovery_ledger.iter_events())), 2)

    def test_recovery_validator_calls_full_base_validator_on_resume(self) -> None:
        plan, _, workspace, _, control = self._synthetic_plan_and_control()
        lineage = control["technical_timeout_recovery"]
        canonical = workspace / "canonical" / self.runs[1]["run_id"]
        self._write_canonical(self.runs[1], canonical, lineage=lineage)
        calls = []

        class FakeRunner:
            manifest = control
            manifest_path = workspace / "manifest.json"

            def validate(self, run, path):
                calls.append((run["run_id"], path))

        facade = TechnicalTimeoutRecoveryRunner.__new__(TechnicalTimeoutRecoveryRunner)
        facade._runner = FakeRunner()
        facade._validate_delegate = facade._runner.validate
        facade._source_manifest = self.manifest
        facade._source_manifest_path = str(self.source_manifest_path)
        facade._source_manifest_hash = self.manifest["manifest_hash"]
        facade._source_manifest_file_sha256 = recovery_mod.file_hash(
            self.source_manifest_path
        )
        facade.plan = plan
        facade._lineage = lineage
        facade._validate_recovery_audit_manifest(self.runs[1], canonical)
        self.assertEqual(calls, [(self.runs[1]["run_id"], canonical)])


if __name__ == "__main__":
    unittest.main()
