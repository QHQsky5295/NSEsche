from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.reviewer_experiments.protocol.stages import (
    _materialize_capture_run,
    _promote_attempt_directory,
)


class StagePromotionTests(unittest.TestCase):
    @staticmethod
    def _source_run(protocol_version: str) -> dict:
        admission = {
            "enabled": protocol_version == "reviewer-v4",
            "policy": (
                "fcfs_capacity" if protocol_version == "reviewer-v4" else "disabled"
            ),
            "drain_cpu_work_multiplier": 4.0,
            "minimum_drain_frames": 1_000,
            "stop_when_drained": True,
        }
        return {
            "run_id": "formal.P5P01",
            "method": "sche_nash",
            "environment": {"PROTOCOL_SCHEDULER": "sche_nash"},
            "simulator_experiment": {
                "protocol_version": protocol_version,
                "run_id": "formal.P5P01",
                "admission": admission,
                "workload": {
                    "mode": "replay",
                    "tape_path": "formal-tape.json",
                    "load_scale": 1.0,
                    "burst_profile": "steady",
                },
                "reference": {
                    "mode": "offline_required",
                    "table_path": "formal-reference.json",
                    "build_output_path": "",
                },
                "nash": {"observe": "formal"},
                "output": {"root": "formal-output"},
            },
        }

    def test_reviewer_v4_capture_clone_normalizes_without_mutating_source(self) -> None:
        source = self._source_run("reviewer-v4")
        before = json.loads(json.dumps(source))
        attempt = Path("capture") / "attempt-01"

        capture, identity = _materialize_capture_run(source, "capture.example", attempt)

        self.assertEqual(source, before)
        self.assertEqual(capture["run_id"], "capture.example")
        self.assertEqual(capture["method"], "random")
        experiment = capture["simulator_experiment"]
        self.assertEqual(experiment["protocol_version"], "reviewer-v3")
        self.assertEqual(
            experiment["admission"],
            {
                "enabled": False,
                "policy": "disabled",
                "drain_cpu_work_multiplier": 4.0,
                "minimum_drain_frames": 1_000,
                "stop_when_drained": True,
            },
        )
        self.assertEqual(experiment["workload"]["mode"], "capture")
        self.assertEqual(experiment["reference"]["mode"], "sa_fallback")
        self.assertEqual(experiment["nash"]["observe"], "off")
        self.assertEqual(
            identity,
            {
                "source_protocol_version": "reviewer-v4",
                "capture_protocol_version": "reviewer-v3",
                "capture_admission_enabled": False,
                "reviewer_v4_capture_normalized": True,
            },
        )

    def test_reviewer_v3_capture_clone_retains_disabled_protocol_contract(self) -> None:
        source = self._source_run("reviewer-v3")
        source_admission = json.loads(
            json.dumps(source["simulator_experiment"]["admission"])
        )

        capture, identity = _materialize_capture_run(
            source, "capture.example", Path("capture") / "attempt-01"
        )

        experiment = capture["simulator_experiment"]
        self.assertEqual(experiment["protocol_version"], "reviewer-v3")
        self.assertEqual(experiment["admission"], source_admission)
        self.assertFalse(identity["reviewer_v4_capture_normalized"])
        self.assertFalse(identity["capture_admission_enabled"])

    def test_recovers_verified_windows_destination_placement_anomaly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            key = "steady.low.homogeneous.mixed.D61.example"
            attempt = root / "partial" / key / "attempt-01"
            attempt.mkdir(parents=True)
            (attempt / "attempt.json").write_text(
                json.dumps({"key": key, "status": "pass"}), encoding="utf-8"
            )
            (attempt / "artifact.bin").write_bytes(b"immutable experiment data")
            canonical = root / "canonical" / key

            def misplaced_replace(source: Path, destination: Path) -> None:
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.rename(destination.parent / source.name)

            with patch(
                "scripts.reviewer_experiments.protocol.stages.promote_directory_exact",
                side_effect=misplaced_replace,
            ):
                promotion = _promote_attempt_directory(
                    attempt, canonical, expected_key=key
                )

            self.assertEqual(Path(promotion["source_path"]).name, "attempt-01")
            self.assertEqual(promotion["mode"], "recovered_misplaced_directory")
            self.assertEqual(
                (canonical / "artifact.bin").read_bytes(),
                b"immutable experiment data",
            )
            self.assertTrue((canonical.parent / "attempt-01").is_dir())


if __name__ == "__main__":
    unittest.main()
