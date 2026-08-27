from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.reviewer_experiments.protocol.pairing import (
    audit_manifest_pairing,
    audit_pairing_runs,
)
from scripts.reviewer_experiments.protocol.util import object_hash


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64


def _run(method: str, *, node_count: int = 20, tape_hash: str = HEX_A) -> dict:
    return {
        "run_id": f"E1.{method}.low.homogeneous.n{node_count}.E01.deadbeefdeadbeef",
        "experiment_id": "E1",
        "method": method,
        "variant": "full",
        "seed": "E01",
        "workload": {
            "request_freq": "low",
            "arrival_profile": "steady",
            "topology": "homogeneous",
            "qos_profile": "mixed",
            "load_scale": 1.0,
        },
        "workload_tape": {"sha256": tape_hash},
        "cluster": {"node_count": node_count, "topology": "homogeneous"},
        "common_hpa_hash": HEX_D,
        "simulation": {
            "total_frame": 1000,
            "expected_final_frame": 1000,
            "expected_frame_count": 1001,
            "frame_duration_seconds": 0.001,
        },
        "simulator_experiment": {
            "workload_seed": "E01",
            "topology_seed": "E01",
            "algorithm_seed": "E01",
        },
    }


def _write_qc(
    root: Path, run: dict, *, function_hash: str = HEX_B, node_hash: str = HEX_C
) -> None:
    directory = root / run["run_id"]
    directory.mkdir(parents=True)
    (directory / "qc_report.json").write_text(
        json.dumps(
            {
                "passed": True,
                "classification": "qc_pass",
                "observations": {
                    "environment_semantic_hashes": {
                        "function_dag_qos_sha256": function_hash,
                        "node_network_sha256": node_hash,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


class PairingAuditTests(unittest.TestCase):
    def test_manifest_pairing_can_audit_an_exact_method_subset(self) -> None:
        runs = [_run("greedy"), _run("random")]
        manifest = {
            "protocol_id": "test-protocol",
            "manifest_hash": HEX_A,
            "formal_results_eligible": False,
            "runs": runs,
        }
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            _write_qc(workspace / "canonical", runs[0])
            with mock.patch(
                "scripts.reviewer_experiments.protocol.pairing.validate_manifest"
            ):
                report = audit_manifest_pairing(
                    manifest,
                    workspace,
                    expected_methods=["greedy"],
                    methods=["greedy"],
                )
                with self.assertRaisesRegex(ValueError, "absent from manifest"):
                    audit_manifest_pairing(
                        manifest,
                        workspace,
                        methods=["not_a_declared_method"],
                    )
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["run_count"], 1)
        self.assertEqual(report["selected_methods"], ["greedy"])

    def test_consistent_pair_passes(self) -> None:
        runs = [_run("greedy"), _run("random")]
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            for run in runs:
                _write_qc(canonical, run)
            report = audit_pairing_runs(
                runs, canonical, expected_methods=["greedy", "random"]
            )
        self.assertTrue(report["passed"])
        self.assertEqual(report["group_count"], 1)
        self.assertEqual(report["groups"][0]["missing_methods"], [])
        self.assertIsNotNone(
            report["groups"][0]["consensus"]["workload_function_dag_qos_sha256"]
        )

    def test_missing_method_and_missing_canonical_are_explicit(self) -> None:
        runs = [_run("greedy")]
        with tempfile.TemporaryDirectory() as temporary:
            report = audit_pairing_runs(
                runs,
                Path(temporary) / "canonical",
                expected_methods=["greedy", "random"],
            )
        codes = {failure["code"] for failure in report["failures"]}
        self.assertFalse(report["passed"])
        self.assertIn("missing_methods", codes)
        self.assertIn("missing_canonical_run", codes)

    def test_hash_mismatch_fails_and_e2_sizes_are_not_merged(self) -> None:
        first = _run("greedy")
        second = _run("random", tape_hash=HEX_B)
        scaled = copy.deepcopy(_run("greedy", node_count=100))
        scaled["experiment_id"] = "E2"
        scaled["run_id"] = "E2.greedy.low.homogeneous.n100.E01.deadbeefdeadbeef"
        scaled["workload"]["load_scale"] = 5.0
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            for run in (first, second, scaled):
                _write_qc(canonical, run)
            report = audit_pairing_runs([first, second, scaled], canonical)
        self.assertFalse(report["passed"])
        self.assertEqual(report["group_count"], 2)
        mismatch_fields = {
            failure["details"].get("field")
            for failure in report["failures"]
            if failure["code"] == "pairing_hash_mismatch"
        }
        self.assertIn("workload_tape_sha256", mismatch_fields)
        self.assertIn("workload_function_dag_qos_sha256", mismatch_fields)

    def test_function_and_node_hash_mismatches_fail(self) -> None:
        runs = [_run("greedy"), _run("random")]
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            _write_qc(canonical, runs[0])
            _write_qc(canonical, runs[1], function_hash=HEX_C, node_hash=HEX_D)
            report = audit_pairing_runs(runs, canonical)
        mismatch_fields = {
            failure["details"].get("field")
            for failure in report["failures"]
            if failure["code"] == "pairing_hash_mismatch"
        }
        self.assertEqual(
            mismatch_fields,
            {
                "function_dag_qos_sha256",
                "workload_function_dag_qos_sha256",
                "node_network_sha256",
            },
        )

    def test_hpa_simulation_and_seed_mismatches_fail(self) -> None:
        runs = [_run("greedy"), _run("random")]
        runs[1]["common_hpa_hash"] = HEX_C
        runs[1]["simulation"]["total_frame"] = 4000
        runs[1]["simulator_experiment"]["topology_seed"] = "E02"
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            for run in runs:
                _write_qc(canonical, run)
            report = audit_pairing_runs(runs, canonical)
        mismatch_fields = {
            failure["details"].get("field")
            for failure in report["failures"]
            if failure["code"] == "pairing_hash_mismatch"
        }
        self.assertTrue(
            {
                "common_hpa_sha256",
                "simulation_sha256",
                "seed_tuple_sha256",
            }.issubset(mismatch_fields)
        )

    def test_formal_pairing_checks_runtime_identity(self) -> None:
        runs = [_run("greedy"), _run("random")]
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            for run in runs:
                _write_qc(canonical, run)
                audit = {
                    "status": "canonical",
                    "software_environment": {
                        "git": {"commit": "1" * 40},
                        "python": {"executable_sha256": HEX_A},
                        "cargo_lock": {"sha256": HEX_B},
                    },
                    "adapter_binary": {"verified_sha256": HEX_C},
                }
                audit["audit_manifest_hash"] = object_hash(audit)
                (canonical / run["run_id"] / "manifest.json").write_text(
                    json.dumps(audit), encoding="utf-8"
                )
            report = audit_pairing_runs(
                runs,
                canonical,
                expected_methods=["greedy", "random"],
                require_runtime_identity=True,
            )
            self.assertTrue(report["passed"], report)

            changed = json.loads(
                (canonical / runs[1]["run_id"] / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            changed["adapter_binary"]["verified_sha256"] = HEX_D
            changed["audit_manifest_hash"] = object_hash(
                {
                    key: value
                    for key, value in changed.items()
                    if key != "audit_manifest_hash"
                }
            )
            (canonical / runs[1]["run_id"] / "manifest.json").write_text(
                json.dumps(changed), encoding="utf-8"
            )
            mismatch = audit_pairing_runs(
                runs,
                canonical,
                expected_methods=["greedy", "random"],
                require_runtime_identity=True,
            )
            self.assertFalse(mismatch["passed"])
            self.assertIn(
                "runtime_binary_sha256",
                {
                    failure["details"].get("field")
                    for failure in mismatch["failures"]
                    if failure["code"] == "pairing_hash_mismatch"
                },
            )


if __name__ == "__main__":
    unittest.main()
