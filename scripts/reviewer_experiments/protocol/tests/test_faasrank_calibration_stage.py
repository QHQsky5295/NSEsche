from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, patch

from scripts.reviewer_experiments.protocol.faasrank_calibration_stage import (
    FaaSRankCalibrationStageError,
    _run_adapter_attempt,
    _template,
    _training_run,
    _validate_training_run,
    capture_faasrank_training_tape,
    run_faasrank_calibration,
)
from scripts.reviewer_experiments.protocol.faasrank_model import (
    create_faasrank_calibration_plan,
)
from scripts.reviewer_experiments.protocol.matrix import write_manifest
from scripts.reviewer_experiments.protocol.process_monitor import ProcessResult
from scripts.reviewer_experiments.protocol.tape import inspect_tape
from scripts.reviewer_experiments.protocol.util import write_json_atomic


WEIGHTS = {
    "cpu_headroom": 0.25,
    "memory_headroom": 0.20,
    "network_locality": 0.20,
    "warm_affinity": 0.15,
    "load_balance": 0.15,
    "diversity_penalty": -0.05,
}


class FaaSRankCalibrationStageTests(unittest.TestCase):
    def _fixture(self, root: Path):
        manifest_path = root / "manifest.json"
        manifest = write_manifest(manifest_path)
        tape_path = root / "training-tape.json"
        write_json_atomic(
            tape_path,
            {
                "version": 1,
                "workload_seed": "FAASRANK-TRAIN-W01",
                "events": [{"frame": 1, "dag_id": 0}],
            },
        )
        tape = inspect_tape(tape_path)
        plan = create_faasrank_calibration_plan(
            root / "plan.json",
            training_tape_sha256=tape.sha256,
            candidates=[
                {"weights": WEIGHTS, "epsilon": 0.0},
                {
                    "weights": {**WEIGHTS, "cpu_headroom": 0.30},
                    "epsilon": 0.1,
                },
            ],
            training_seeds=["FTR01", "FTR02"],
            preregistered_at="2026-08-11T00:00:00Z",
        )
        return manifest_path, manifest, tape_path, tape, plan

    def test_training_run_binds_independent_tape_candidate_and_rng_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, manifest, tape_path, tape, plan = self._fixture(root)
            template = _template(
                manifest, method="sche_FaaSRank", seed="E01", load="low"
            )
            candidate = plan.candidates[0]
            run, spec_hash = _training_run(
                template,
                plan,
                candidate,
                "FTR01",
                tape_path,
                tape.event_count,
            )

            experiment = run["simulator_experiment"]
            self.assertEqual(run["seed"], "FTR01")
            self.assertEqual(experiment["workload_seed"], "FAASRANK-TRAIN-W01")
            self.assertEqual(experiment["topology_seed"], "FAASRANK-TRAIN-W01")
            self.assertEqual(experiment["algorithm_seed"], "FTR01")
            self.assertEqual(run["workload_tape"]["sha256"], tape.sha256)
            self.assertEqual(
                experiment["faasrank_model"]["model_sha256"],
                candidate["candidate_sha256"],
            )
            self.assertEqual(len(spec_hash), 64)
            self.assertNotIn("reference_dependency", run)

    def test_calibration_entrypoint_passes_plan_to_training_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, manifest, tape_path, tape, plan = self._fixture(root)

            with patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage.process_monitor_available",
                return_value=True,
            ), patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage.load_and_validate_manifest",
                return_value=manifest,
            ), patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage._evaluation_tape_hashes",
                return_value=set(),
            ), patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage.load_faasrank_calibration_plan",
                return_value=plan,
            ), patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage._training_run",
                autospec=True,
                side_effect=RuntimeError("training-run-called"),
            ) as training_run:
                with self.assertRaisesRegex(RuntimeError, "training-run-called"):
                    run_faasrank_calibration(
                        manifest_path,
                        root / "calibration",
                        training_tape_path=tape_path,
                        calibration_plan_path=root / "plan.json",
                        template_seed="E01",
                        load="low",
                    )

            training_run.assert_called_once_with(
                ANY,
                plan,
                plan.candidates[0],
                plan.training_seeds[0],
                tape_path,
                tape.event_count,
            )

    def test_training_workload_seed_must_be_disjoint_from_evaluation_seeds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, _, _, _, _ = self._fixture(root)
            with self.assertRaisesRegex(FaaSRankCalibrationStageError, "disjoint"):
                capture_faasrank_training_tape(
                    manifest_path,
                    root / "calibration",
                    training_workload_seed="E01",
                )

    def test_training_capture_receipt_uses_the_published_file_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, manifest, _, _, _ = self._fixture(root)
            bound_manifest = copy.deepcopy(manifest)
            for run in bound_manifest["runs"]:
                run["workload_tape"]["sha256"] = "a" * 64
                run["workload_tape"]["event_count"] = 1

            def completed_capture(_manifest, _workspace, run, _spec_hash, **_kwargs):
                canonical = root / "canonical"
                result_dir = canonical / "reviewer_records" / run["run_id"]
                result_dir.mkdir(parents=True)
                write_json_atomic(
                    canonical / "workload_tape.json",
                    {
                        "version": 1,
                        "workload_seed": "FAASRANK-TRAIN-W01",
                        "events": [{"frame": 1, "dag_id": 0}],
                    },
                )
                write_json_atomic(
                    result_dir / "summary.json",
                    {
                        "schema": "NSE_SUMMARY_V1",
                        "run_id": run["run_id"],
                        "run_complete": True,
                        "arrivals": 1,
                    },
                )
                return canonical

            with patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage.load_and_validate_manifest",
                return_value=bound_manifest,
            ), patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage._run_adapter_attempt",
                side_effect=completed_capture,
            ):
                receipt = capture_faasrank_training_tape(
                    manifest_path,
                    root / "calibration",
                )

            published = Path(receipt["path"])
            self.assertEqual(receipt["bytes"], published.stat().st_size)
            self.assertEqual(receipt["event_count"], 1)

    def test_completed_zero_is_a_complete_scientific_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            run_id = "faasrank-cal.zero.FTR01"
            run = {
                "run_id": run_id,
                "workload_tape": {"event_count": 3},
            }
            result_dir = directory / "reviewer_records" / run_id
            result_dir.mkdir(parents=True)
            write_json_atomic(
                result_dir / "summary.json",
                {
                    "schema": "NSE_SUMMARY_V1",
                    "run_id": run_id,
                    "run_complete": True,
                    "arrivals": 3,
                    "completed": 0,
                    "throughput_requests_per_second": 0.0,
                    "simulator_internal_cost_per_completed_request": None,
                    "latency_ms": {"mean": None},
                },
            )
            write_json_atomic(result_dir / "environment.json", {})
            write_json_atomic(directory / "adapter_observation.json", {})
            for name in ("frames.jsonl", "requests.jsonl", "scheduler_windows.jsonl"):
                (result_dir / name).write_text("", encoding="utf-8")

            _validate_training_run(directory, run)

    def test_completed_zero_canonicalizes_without_result_dependent_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_id = "faasrank-cal.zero.FTR01"
            run = {
                "run_id": run_id,
                "seed": "FTR01",
                "method": "sche_FaaSRank",
                "environment": {},
                "workload_tape": {"event_count": 3},
                "simulator_experiment": {
                    "output": {"root": "__OUTPUT__"},
                    "workload": {"mode": "replay", "tape_path": "training.json"},
                },
            }
            manifest = {
                "execution": {
                    "cwd": ".",
                    "command_template": ["fake-calibration"],
                    "timeout_seconds": 1,
                }
            }

            def complete_zero_run(*args, **kwargs):
                environment = kwargs["environment"]
                attempt_dir = Path(environment["PROTOCOL_PARTIAL_DIR"])
                result_dir = attempt_dir / "reviewer_records" / run_id
                result_dir.mkdir(parents=True, exist_ok=True)
                write_json_atomic(
                    result_dir / "summary.json",
                    {
                        "schema": "NSE_SUMMARY_V1",
                        "run_id": run_id,
                        "run_complete": True,
                        "arrivals": 3,
                        "completed": 0,
                        "throughput_requests_per_second": 0.0,
                        "simulator_internal_cost_per_completed_request": None,
                        "latency_ms": {"mean": None},
                    },
                )
                write_json_atomic(result_dir / "environment.json", {})
                write_json_atomic(attempt_dir / "adapter_observation.json", {})
                for name in (
                    "frames.jsonl",
                    "requests.jsonl",
                    "scheduler_windows.jsonl",
                ):
                    (result_dir / name).write_text("", encoding="utf-8")
                return ProcessResult(
                    exit_code=0,
                    timed_out=False,
                    launch_error=None,
                    duration_seconds=0.01,
                    samples=1,
                    peak_process_tree_rss_bytes=1,
                    peak_process_tree_vms_bytes=1,
                    peak_process_tree_count=1,
                    process_tree_cpu_seconds=0.0,
                )

            with patch(
                "scripts.reviewer_experiments.protocol.faasrank_calibration_stage.run_monitored",
                side_effect=complete_zero_run,
            ) as monitored:
                canonical = _run_adapter_attempt(
                    manifest,
                    root / "training_runs",
                    run,
                    "a" * 64,
                    extra_validator=_validate_training_run,
                )

            self.assertEqual(monitored.call_count, 1)
            self.assertTrue(canonical.is_dir())
            self.assertTrue((canonical / "stage_receipt.json").is_file())
            self.assertFalse((root / "training_runs" / "quarantine").exists())


if __name__ == "__main__":
    unittest.main()
