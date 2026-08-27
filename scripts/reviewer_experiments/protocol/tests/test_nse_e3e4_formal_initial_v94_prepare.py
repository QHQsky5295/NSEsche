from __future__ import annotations

import copy
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3e4_formal_initial_v94_prepare import (
    OVERLAY_MARKER,
    derive_formal_e3_e4_v94_manifest,
    write_formal_e3_e4_v94_manifest,
)
from scripts.reviewer_experiments.protocol.matrix import _assign_run_identity
from scripts.reviewer_experiments.protocol.schema import (
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


PLAN_PATH = Path(
    "scripts/reviewer_experiments/protocol/nse_e3e4_formal_initial_v94_plan.json"
)


def _rehash(manifest: dict) -> None:
    manifest.pop("manifest_hash", None)
    manifest["manifest_hash"] = object_hash(manifest)


class FormalE3E4V94PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = read_json(PLAN_PATH)
        source_path = Path(cls.plan["immutable_prepared_source"]["path"])
        if not source_path.is_file():
            raise unittest.SkipTest(
                "local immutable formal E3/E4 source is unavailable"
            )
        cls.source_path = source_path
        cls.source_file_sha256 = file_hash(source_path)
        cls.manifest = derive_formal_e3_e4_v94_manifest(PLAN_PATH)

    def test_complete_matrix_profiles_and_source_immutability(self) -> None:
        manifest = self.manifest
        validate_manifest(copy.deepcopy(manifest))
        self.assertEqual(file_hash(self.source_path), self.source_file_sha256)
        self.assertEqual(len(manifest["runs"]), 400)
        self.assertEqual(
            Counter(run["experiment_id"] for run in manifest["runs"]),
            {"E3": 300, "E4": 100},
        )
        self.assertEqual(
            Counter(run["method"] for run in manifest["runs"]),
            {
                "greedy": 40,
                "random": 40,
                "hash": 40,
                "load_least": 40,
                "sche_FaaSRank": 40,
                "sche_OCS": 40,
                "sche_Hiku": 40,
                "sche_jiagu": 40,
                "sche_orion": 40,
                "sche_nash": 40,
            },
        )
        candidates = [run for run in manifest["runs"] if run["method"] == "sche_nash"]
        self.assertEqual(len(candidates), 40)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 40)
        self.assertEqual(
            {run["environment"]["SERVERLESS_SIM_PORT"] for run in manifest["runs"]},
            {"3130"},
        )
        self.assertTrue(
            all(
                Path(run["sla_targets"]["artifact_path"]).is_absolute()
                and Path(run["sla_targets"]["artifact_path"]).is_file()
                for run in manifest["runs"]
            )
        )
        self.assertTrue(
            all(
                Path(run["baseline_model"]["artifact_path"]).is_absolute()
                and Path(run["baseline_model"]["artifact_path"]).is_file()
                for run in manifest["runs"]
                if run["method"] == "sche_FaaSRank"
            )
        )
        self.assertEqual(
            {
                run["experiment_id"]: run["environment"][
                    "NASH_OPERATIONAL_EXPERT_PROXY"
                ]
                for run in candidates
            },
            {
                "E3": self.plan["frozen_candidate"]["E3_profile"],
                "E4": self.plan["frozen_candidate"]["E4_profile"],
            },
        )
        self.assertTrue(
            all(
                run["simulator_experiment"]["faasrank_model"]["model_sha256"]
                == self.plan["frozen_candidate"]["faasrank_model_sha256"]
                for run in candidates
            )
        )
        marker = manifest[OVERLAY_MARKER]
        self.assertFalse(marker["performance_results_consulted"])
        self.assertFalse(marker["training_rows_pooled"])
        self.assertEqual(len(marker["candidate_bindings"]), 40)

    def test_candidate_and_baseline_tampering_fail_closed(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        target = next(run for run in candidate["runs"] if run["method"] == "sche_nash")
        target["environment"]["NASH_OPERATIONAL_QUEUE_WEIGHT"] = "9.9"
        _assign_run_identity(target)
        lineage = candidate["formal_e3_e4_initial_shard"]["selected_source_runs"]
        entry = next(
            item
            for item in lineage
            if item["source_cell_id"] == target["cell_id"]
            and item["source_seed"] == target["seed"]
        )
        entry["source_environment_sha256"] = object_hash(target["environment"])
        _rehash(candidate)
        with self.assertRaisesRegex(ProtocolValidationError, "differs from frozen V94"):
            validate_manifest(candidate)

        baseline = copy.deepcopy(self.manifest)
        baseline[OVERLAY_MARKER]["baseline_derived_identity_sha256"] = "0" * 64
        _rehash(baseline)
        with self.assertRaisesRegex(ProtocolValidationError, "baseline identity"):
            validate_manifest(baseline)

    def test_plan_source_hash_tampering_and_output_overwrite_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            changed_plan = copy.deepcopy(self.plan)
            changed_plan["immutable_prepared_source"]["file_sha256"] = "0" * 64
            changed_plan_path = root / "changed-plan.json"
            write_json_atomic(changed_plan_path, changed_plan)
            with self.assertRaisesRegex(ProtocolValidationError, "missing or changed"):
                derive_formal_e3_e4_v94_manifest(changed_plan_path)

            output = root / "manifest.json"
            first = write_formal_e3_e4_v94_manifest(PLAN_PATH, output)
            self.assertEqual(read_json(output), first)
            with self.assertRaisesRegex(
                ProtocolValidationError, "refusing to overwrite"
            ):
                write_formal_e3_e4_v94_manifest(PLAN_PATH, output)


if __name__ == "__main__":
    unittest.main()
