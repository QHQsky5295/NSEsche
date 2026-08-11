from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.faasrank_calibration_stage import (
    FaaSRankCalibrationStageError,
    _template,
    _training_run,
    capture_faasrank_training_tape,
)
from scripts.reviewer_experiments.protocol.faasrank_model import (
    create_faasrank_calibration_plan,
)
from scripts.reviewer_experiments.protocol.matrix import write_manifest
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


if __name__ == "__main__":
    unittest.main()
