from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.serverless_adapter import (
    AdapterError,
    _server_environment,
    _observation_stream_complete,
    _wait_for_completed_artifacts,
)


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
