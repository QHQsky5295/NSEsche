from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.qc import QCReport
from scripts.reviewer_experiments.protocol.runner import (
    ProtocolRunError,
    ProtocolRunner,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


class RunAuditManifestTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[ProtocolRunner, dict, Path]:
        protocol_path = root / "protocol.json"
        write_json_atomic(protocol_path, {"fixture": "exact protocol bytes"})
        runner = ProtocolRunner.__new__(ProtocolRunner)
        runner.manifest_path = protocol_path.resolve()
        runner.manifest = {
            "schema_version": "1.0",
            "protocol_id": "audit-test",
            "manifest_hash": "a" * 64,
            "execution": {
                "cwd": ".",
                "result_relative_path": "reviewer_records/{run_id}/summary.json",
            },
            "qc": {"jsonl_artifacts": {"required": True}},
        }
        runner._adapter_binary_hash_cache = {}
        runner._verified_tapes = {}
        runner._verified_workload_packages = {}
        runner._static_runtime_provenance = {
            "captured_at": "2026-08-10T00:00:00Z",
            "git": {
                "available": True,
                "commit": "1" * 40,
                "dirty": True,
                "dirty_entry_count": 2,
                "dirty_listing_sha256": "2" * 64,
                "repository_root": str(root),
                "error": None,
            },
            "python": {
                "version": "3.test",
                "implementation": "CPython",
                "full_version": "3.test fixture",
                "executable": "python-fixture",
            },
            "cargo_lock": {"path": "Cargo.lock", "sha256": "3" * 64, "bytes": 10},
            "cargo_locks": [{"path": "Cargo.lock", "sha256": "3" * 64, "bytes": 10}],
        }

        run_id = "E1.audit.E01"
        hpa = {"target_mem_use_rate": 0.5, "scale_up_placement": "least_task"}
        faasrank_model = {
            "state": "frozen",
            "model_sha256": "4" * 64,
            "training_tape_sha256": "5" * 64,
        }
        experiment = {
            "workload_seed": "E01",
            "topology_seed": "E01",
            "algorithm_seed": "E01",
            "node_count": 20,
            "node_profile": {"kind": "heterogeneous", "cpu_mean": 150.0},
            "qos": {"enabled": True, "latency_weight": 0.9},
            "ablation": {
                "heterogeneity": True,
                "externality": True,
                "congestion_pricing": True,
                "nash_social_coordination": True,
            },
            "faasrank_model": faasrank_model,
        }
        tape_path = root / "tapes" / "test.json"
        write_json_atomic(
            tape_path,
            {
                "version": 1,
                "workload_seed": "E01",
                "events": [
                    {"frame": index, "dag_id": 0, "sequence": index}
                    for index in range(9)
                ],
            },
        )
        capture_directory = root / "capture"
        environment_path = capture_directory / "environment.json"
        write_json_atomic(
            environment_path,
            {
                "schema": "NSE_ENVIRONMENT_V1",
                "run_id": "capture.audit",
                "functions": [{"function_id": 0, "dag_id": 0, "qos_class": "shared"}],
                "nodes": [
                    {"node_id": 0, "cpu_capacity": 150.0, "memory_capacity": 5000.0}
                ],
                "network_mb_per_second": [[0.0]],
            },
        )
        environment = json.loads(environment_path.read_text(encoding="utf-8"))
        capture_environment = {
            "function_dag_qos_sha256": object_hash(environment["functions"]),
            "node_network_sha256": object_hash(
                {
                    "nodes": environment["nodes"],
                    "network_mb_per_second": environment["network_mb_per_second"],
                }
            ),
            "capture_environment_sha256": file_hash(environment_path),
            "function_count": 1,
            "node_count": 1,
        }
        capture_environment["semantic_bundle_sha256"] = object_hash(capture_environment)
        receipt_path = capture_directory / "capture_receipt.json"
        receipt = {
            "schema_version": "NSE_BASE_TAPE_CAPTURE_RECEIPT_V2",
            "key": "audit-base-E01",
            "seed": "E01",
            "tape_sha256": file_hash(tape_path),
            "tape_event_count": 9,
            "source_kind": "azure_trace_derived_empirical_cdf",
            "source_is_direct_raw_trace": False,
            **capture_environment,
        }
        write_json_atomic(receipt_path, receipt)
        run = {
            "run_id": run_id,
            "run_spec_hash": "6" * 64,
            "experiment_id": "E1",
            "cell_id": "E1.audit",
            "method": "sche_FaaSRank",
            "variant": "full",
            "seed": "E01",
            "workload_spec_hash": "7" * 64,
            "workload_tape": {
                "path": "tapes/test.json",
                "sha256": file_hash(tape_path),
                "event_count": 9,
                "kind": "base_steady",
                "key": "audit-base-E01",
                "parent_key": None,
                "parent_sha256": None,
                "capture_environment": capture_environment,
                "capture_receipt_path": "capture/capture_receipt.json",
                "capture_receipt_sha256": file_hash(receipt_path),
            },
            "reference_dependency": {
                "path": "references/test.jsonl",
                "sha256": "b" * 64,
                "bytes": 123,
                "receipt_sha256": "c" * 64,
                "build_spec_hash": "d" * 64,
            },
            "common_hpa_hash": "e" * 64,
            "common_hpa": hpa,
            "cluster": {"node_count": 20, "topology": "heterogeneous"},
            "simulator_experiment": experiment,
        }
        package_key = runner._workload_package_cache_key(
            tape_path,
            run["workload_tape"]["sha256"],
            receipt_path,
            run["workload_tape"]["capture_receipt_sha256"],
        )
        runner._verified_workload_packages[
            package_key
        ] = runner._validate_workload_package(run, tape_path, receipt_path)

        canonical = root / "canonical" / run_id
        result_path = canonical / "reviewer_records" / run_id / "summary.json"
        write_json_atomic(
            result_path, {"schema": "NSE_SUMMARY_V1", "run_complete": True}
        )
        write_json_atomic(canonical / "run_config.json", {"run": run_id})
        process = {
            "schema_version": "NSE_PROCESS_OBSERVATION_V1",
            "duration_seconds": 1.25,
            "sample_interval_seconds": 0.05,
            "samples": 25,
            "peak_process_tree_rss_bytes": 123456,
            "peak_process_tree_vms_bytes": 456789,
            "peak_process_tree_count": 2,
            "process_tree_cpu_seconds": 0.75,
            "timed_out": False,
            "exit_code": 0,
        }
        write_json_atomic(canonical / "process_observation.json", process)
        adapter_binary = root / "serverless_sim.exe"
        adapter_binary.write_bytes(b"audited simulator binary")
        write_json_atomic(
            canonical / "adapter_observation.json",
            {
                "schema_version": "NSE_SERVERLESS_ADAPTER_LIFECYCLE_V1",
                "server_executable": str(adapter_binary.resolve()),
                "server_executable_sha256": file_hash(adapter_binary),
            },
        )
        stream = canonical / "reviewer_records" / run_id / "frames.jsonl"
        stream.parent.mkdir(parents=True, exist_ok=True)
        stream.write_text('{"schema":"NSE_FRAME_V1"}\n', encoding="utf-8")
        archive = runner._archive_jsonl(canonical)
        environment_hashes = {
            "environment_sha256": "f" * 64,
            "function_dag_qos_sha256": "0" * 64,
            "node_network_sha256": "1" * 64,
            "function_count": 3,
            "node_count": 20,
        }
        report = QCReport(
            passed=True,
            classification="valid",
            checked_at="2026-08-10T00:00:01Z",
            result_path=str(result_path),
            result_sha256=file_hash(result_path),
            result_bytes=result_path.stat().st_size,
            issues=[],
            observations={
                "environment_semantic_hashes": environment_hashes,
                "jsonl_archive": archive,
            },
        )
        write_json_atomic(canonical / "qc_report.json", report.to_dict())
        write_json_atomic(
            canonical / "attempt.json",
            {
                "run_id": run_id,
                "run_spec_hash": run["run_spec_hash"],
                "seed": run["seed"],
                "workload_spec_hash": run["workload_spec_hash"],
                "common_hpa_hash": run["common_hpa_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": run["reference_dependency"]["sha256"],
                "attempt": 1,
                "run_config_sha256": file_hash(canonical / "run_config.json"),
                "result_sha256": file_hash(result_path),
                "jsonl_archive_summary_sha256": file_hash(
                    canonical / "jsonl_archive_summary.json"
                ),
                "process_observation_sha256": file_hash(
                    canonical / "process_observation.json"
                ),
            },
        )
        runner._write_audit_manifest(
            run, 1, canonical, status="canonical", report=report
        )
        return runner, run, canonical

    def test_manifest_records_complete_result_blind_provenance_and_validates(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner, run, canonical = self._fixture(Path(temporary))
            runner._validate_existing_canonical(run, canonical)
            audit = json.loads(
                (canonical / "manifest.json").read_text(encoding="utf-8")
            )

            self.assertEqual(
                audit["protocol_manifest"]["file_sha256"],
                file_hash(runner.manifest_path),
            )
            self.assertEqual(audit["run"]["frozen_spec"], run)
            self.assertEqual(set(audit["seeds"].values()), {"E01"})
            self.assertEqual(
                audit["configuration"]["faasrank_model"]["state"], "frozen"
            )
            self.assertTrue(audit["software_environment"]["git"]["dirty"])
            self.assertEqual(
                audit["process_observation"]["measurements"][
                    "peak_process_tree_rss_bytes"
                ],
                123456,
            )
            self.assertEqual(
                audit["qc"]["environment_semantic_hashes"]["function_dag_qos_sha256"],
                "0" * 64,
            )
            self.assertTrue(audit["adapter_binary"]["observed_hash_matches_file"])
            self.assertEqual(
                audit["compressed_jsonl"]["directories"],
                [f"reviewer_records/{run['run_id']}"],
            )
            self.assertFalse(any(canonical.glob(".manifest.json.*.tmp")))

    def test_canonical_validation_rejects_final_artifact_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner, run, canonical = self._fixture(Path(temporary))
            result = canonical / "reviewer_records" / run["run_id"] / "summary.json"
            result.write_text('{"tampered":true}\n', encoding="utf-8")
            with self.assertRaisesRegex(ProtocolRunError, "final-artifact|result hash"):
                runner._validate_existing_canonical(run, canonical)

    def test_canonical_validation_rejects_protocol_file_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner, run, canonical = self._fixture(Path(temporary))
            write_json_atomic(runner.manifest_path, {"fixture": "changed bytes"})
            with self.assertRaisesRegex(
                ProtocolRunError, "protocol file_sha256 mismatch"
            ):
                runner._validate_existing_canonical(run, canonical)


if __name__ == "__main__":
    unittest.main()
