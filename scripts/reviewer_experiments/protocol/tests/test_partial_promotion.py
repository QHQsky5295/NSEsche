from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.ledger import Ledger, verify_ledger
from scripts.reviewer_experiments.protocol.runner import (
    ProtocolRunError,
    ProtocolRunner,
)
from scripts.reviewer_experiments.protocol.tests import test_protocol as _protocol_tests
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


class CompletedPartialPromotionTests(unittest.TestCase):
    """Exercise promotion against a protocol-produced synthetic result.

    The helper writes deterministic protocol records but is not a simulator;
    this keeps the test focused on provenance and recovery, not scientific
    execution.
    """

    def test_portable_archive_basename_and_large_integer_are_safe(self) -> None:
        self.assertEqual(
            ProtocolRunner._portable_archive_basename(
                r"C:\reviewer_records\run\requests.jsonl"
            ),
            "requests.jsonl",
        )
        self.assertEqual(
            list(ProtocolRunner._walk_json_numbers({"counter": 10**10000})),
            [0.0],
        )

    def _make_partial(self, root: Path) -> tuple[Path, Path, dict]:
        helper_tests = _protocol_tests.RunnerTests()
        helper = root / "helper.py"
        helper_tests._write_helper(helper, succeed_at=1)
        manifest_path, run = helper_tests._manifest_and_run(root, helper)
        workspace = root / "workspace"
        completed = ProtocolRunner(manifest_path, workspace).run(
            run_ids=[run["run_id"]]
        )
        self.assertEqual(completed[0]["status"], "canonicalized")

        canonical = workspace / "canonical" / run["run_id"]
        partial = workspace / "partial" / run["run_id"] / "attempt-01"
        partial.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(canonical), str(partial))

        runner = ProtocolRunner(manifest_path, workspace)
        tape_path, reference_path = runner._assert_run_ready(run)
        run_config = runner._materialize_run_config(
            run, partial, tape_path, reference_path
        )
        run_config_path = partial / "run_config.json"
        write_json_atomic(run_config_path, run_config)

        metadata_path = partial / "attempt.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["run_config_sha256"] = file_hash(run_config_path)
        write_json_atomic(metadata_path, metadata)
        final_metadata = copy.deepcopy(metadata)
        final_metadata["failure_signature"] = None
        final_metadata["jsonl_archive_summary_sha256"] = file_hash(
            partial / "jsonl_archive_summary.json"
        )
        write_json_atomic(partial / ".attempt.json.9900.tmp", final_metadata)

        interpreter = Path(sys.executable).resolve()
        write_json_atomic(
            partial / "adapter_observation.json",
            {
                "schema_version": "NSE_SERVERLESS_ADAPTER_LIFECYCLE_V1",
                "status": "completed",
                "run_id": run["run_id"],
                "server_pid": 1,
                "server_executable": str(interpreter),
                "server_executable_sha256": file_hash(interpreter),
                "python_helper_interpreter": str(interpreter),
                "python_helper_interpreter_sha256": file_hash(interpreter),
                "python_helper_version": sys.version,
                "started_at": "2020-01-01T00:00:00Z",
                "ended_at": "2020-01-01T00:00:01Z",
                "shutdown": {"method": "synthetic", "exit_code": 0},
            },
        )

        audit_path = partial / "manifest.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["status"] = "running"
        audit.pop("audit_manifest_hash", None)
        audit["audit_manifest_hash"] = object_hash(audit)
        write_json_atomic(audit_path, audit)

        ledger_path = workspace / "ledger.jsonl"
        ledger_path.unlink()
        ledger = Ledger(ledger_path)
        ledger.append("batch_started", {"batch_id": "synthetic-promotion-test"})
        ledger.append(
            "attempt_started",
            {
                "run_id": run["run_id"],
                "attempt": 1,
                "seed": run["seed"],
                "run_spec_hash": run["run_spec_hash"],
                "partial_path": str(partial.resolve()),
            },
        )
        return manifest_path, workspace, run

    def test_completed_partial_promotes_with_receipt_and_forensic_prestate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path, workspace, run = self._make_partial(Path(temporary))
            runner = ProtocolRunner(manifest_path, workspace)
            promoted = runner.promote_completed_partial(run["run_id"], 1)

            self.assertEqual(promoted["status"], "canonicalized_from_completed_partial")
            canonical = workspace / "canonical" / run["run_id"]
            self.assertTrue(canonical.is_dir())
            self.assertFalse(
                (workspace / "partial" / run["run_id"] / "attempt-01").exists()
            )
            receipt_path = canonical / "completed_partial_promotion_receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["receipt_hash"], promoted["receipt_hash"])
            self.assertEqual(
                receipt["original_software_environment"],
                json.loads((canonical / "manifest.json").read_text(encoding="utf-8"))[
                    "software_environment"
                ],
            )
            evidence = canonical / "promotion_evidence" / "prestate"
            self.assertTrue((evidence / "attempt.before-promotion.json").is_file())
            self.assertTrue(
                (evidence / "attempt.finalization-temporary.json").is_file()
            )
            self.assertTrue(
                (evidence / "manifest.running.before-promotion.json").is_file()
            )
            audit = json.loads(
                (canonical / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                audit["recovery_operation"]["receipt_hash"], receipt["receipt_hash"]
            )
            self.assertEqual(verify_ledger(workspace / "ledger.jsonl")[0], 3)

            # A retry is idempotent and cannot append a duplicate disposition.
            retried = ProtocolRunner(
                manifest_path, workspace
            ).promote_completed_partial(run["run_id"], 1)
            self.assertEqual(retried["status"], "canonical_exists_promoted")
            self.assertEqual(verify_ledger(workspace / "ledger.jsonl")[0], 3)

    def test_incomplete_adapter_is_refused_without_mutating_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path, workspace, run = self._make_partial(Path(temporary))
            partial = workspace / "partial" / run["run_id"] / "attempt-01"
            write_json_atomic(
                partial / "adapter_observation.json",
                {
                    "schema_version": "NSE_SERVERLESS_ADAPTER_LIFECYCLE_V1",
                    "status": "running",
                },
            )
            before = sorted(
                path.relative_to(partial).as_posix() for path in partial.rglob("*")
            )
            with self.assertRaisesRegex(ProtocolRunError, "adapter lifecycle"):
                ProtocolRunner(manifest_path, workspace).promote_completed_partial(
                    run["run_id"], 1
                )
            after = sorted(
                path.relative_to(partial).as_posix() for path in partial.rglob("*")
            )
            self.assertEqual(before, after)
            self.assertFalse((workspace / "canonical" / run["run_id"]).exists())


if __name__ == "__main__":
    unittest.main()
