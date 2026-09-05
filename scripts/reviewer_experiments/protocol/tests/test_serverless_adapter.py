from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.p5_common_platform import (
    build_p5_common_platform_manifest,
)
from scripts.reviewer_experiments.protocol.serverless_adapter import (
    AdapterError,
    _verify_workload_frequency_profile,
    _restore_module_inventory,
    _server_environment,
    _snapshot_module_inventory,
    _observation_stream_complete,
    _wait_for_completed_artifacts,
)


class WorkloadProfileProtocolVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        binary = Path(self.temporary.name) / "serverless_sim.exe"
        binary.write_bytes(b"p5-adapter-version-test")
        self.run = build_p5_common_platform_manifest(binary, "a" * 40)["runs"][0]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_reviewer_v4_profile_binding_is_accepted(self) -> None:
        self.assertEqual(
            _verify_workload_frequency_profile(self.run), self.run["workload_profile"]
        )

    def test_reviewer_v3_profile_binding_remains_accepted(self) -> None:
        self.run["simulator_experiment"]["protocol_version"] = "reviewer-v3"
        self.assertEqual(
            _verify_workload_frequency_profile(self.run), self.run["workload_profile"]
        )

    def test_unknown_profile_protocol_version_is_rejected(self) -> None:
        self.run["simulator_experiment"]["protocol_version"] = "reviewer-v5"
        with self.assertRaisesRegex(AdapterError, "reviewer-v3 or reviewer-v4"):
            _verify_workload_frequency_profile(self.run)


class ModuleInventoryPreservationTests(unittest.TestCase):
    def test_restore_preserves_exact_pre_run_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module_path = root / "module_conf_es.json"
            original = b'{\r\n  "sche": {"greedy": null}\r\n}'
            module_path.write_bytes(original)

            observed_path, snapshot, digest = _snapshot_module_inventory(root)
            module_path.write_text('{"sche":{"sche_nash":null}}\n', encoding="utf-8")
            _restore_module_inventory(observed_path, snapshot)

            self.assertEqual(module_path.read_bytes(), original)
            self.assertEqual(digest, hashlib.sha256(original).hexdigest())


class ServerEnvironmentTests(unittest.TestCase):
    def test_rust_python_helper_is_pinned_to_adapter_interpreter(self) -> None:
        environment, interpreter = _server_environment()

        self.assertEqual(interpreter, Path(sys.executable).resolve())
        self.assertEqual(environment["SERVERLESS_SIM_PYTHON"], str(interpreter))
        self.assertEqual(environment["SERVERLESS_SIM_LOG_LEVEL"], "warn")
        self.assertTrue(interpreter.is_file())


class ObservationCompletionTests(unittest.TestCase):
    def test_window_prefix_is_not_complete_until_terminal_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = root / "summary.json"
            result.write_text("{}\n", encoding="utf-8")
            for name in ("frames.jsonl", "requests.jsonl", "scheduler_windows.jsonl"):
                (root / name).write_text("{}\n", encoding="utf-8")
            stream = root / "nash_metrics.jsonl"
            stream.write_text(
                json.dumps({"kind": "window", "frame": 0}) + "\n",
                encoding="utf-8",
            )
            run = {
                "method": "sche_nash",
                "simulator_experiment": {"reference": {"mode": "offline_required"}},
            }
            self.assertFalse(_observation_stream_complete(stream, run))
            with self.assertRaises(AdapterError):
                _wait_for_completed_artifacts(run, result, _LiveProcess(), timeout=0.02)

            with stream.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "v": 2,
                            "kind": "run_summary",
                            "scheduler": "sche_nash",
                            "windows": 1,
                            "observation_writer_error": None,
                        }
                    )
                    + "\n"
                )
            _wait_for_completed_artifacts(run, result, _LiveProcess(), timeout=0.2)

    def test_terminal_summary_must_match_stream_and_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stream = root / "nash_metrics.jsonl"
            stream.write_text(
                json.dumps({"kind": "window", "frame": 0})
                + "\n"
                + json.dumps(
                    {
                        "v": 2,
                        "kind": "run_summary",
                        "scheduler": "sche_nash",
                        "windows": 0,
                        "observation_writer_error": None,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            run = {
                "method": "sche_nash",
                "simulation": {"expected_final_frame": 1},
            }
            self.assertFalse(_observation_stream_complete(stream, run))

            welfare_stream = root / "welfare_metrics.jsonl"
            welfare_run = {
                "method": "greedy",
                "simulation": {"expected_final_frame": 1},
            }
            welfare_stream.write_text(
                json.dumps({"kind": "welfare_window", "frame": 0})
                + "\n"
                + json.dumps(
                    {
                        "v": 1,
                        "kind": "welfare_run_summary",
                        "schema": "NSE_POSTHOC_WELFARE_RUN_V1",
                        "scheduler": "greedy",
                        "windows": 1,
                        "observation_writer_error": None,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertTrue(_observation_stream_complete(welfare_stream, welfare_run))

            lines = stream.read_text(encoding="utf-8").replace(
                '"windows": 0', '"windows": 1'
            )
            stream.write_text(lines, encoding="utf-8")
            self.assertTrue(_observation_stream_complete(stream, run))

            stream.write_text(
                lines.replace('"scheduler": "sche_nash"', '"scheduler": "wrong"'),
                encoding="utf-8",
            )
            self.assertFalse(_observation_stream_complete(stream, run))


class _LiveProcess:
    returncode = None

    @staticmethod
    def poll() -> None:
        return None


if __name__ == "__main__":
    unittest.main()
