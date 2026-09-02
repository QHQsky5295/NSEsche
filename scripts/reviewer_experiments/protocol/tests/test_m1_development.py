from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.m1_development import (
    M1_DEVELOPMENT_SEEDS,
    M1_OPERATIONAL_CANDIDATES,
    M1_SCREEN_SEEDS,
    build_m1_development_manifest,
    derive_m1_candidate_screen_shard,
)
from scripts.reviewer_experiments.protocol.schema import (
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.m1_qualification import (
    SCREEN_SELECTION_SCHEMA,
    _choose_candidate,
    derive_m1_qualification_shard,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


class M1DevelopmentManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = build_m1_development_manifest()

    def test_complete_development_product_is_fixed_and_nonformal(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["phase"], "development")
        self.assertFalse(manifest["formal_results_eligible"])
        self.assertEqual(len(manifest["runs"]), 1440)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 360)
        self.assertEqual(
            manifest["fixed_seed_bank"]["selected_seeds"],
            list(M1_DEVELOPMENT_SEEDS),
        )
        self.assertEqual(
            manifest["m1_development_matrix"]["candidates"],
            list(M1_OPERATIONAL_CANDIDATES),
        )

    def test_candidate_binding_changes_run_and_reference_identity(self) -> None:
        runs = [
            run
            for run in self.manifest["runs"]
            if run["method"] == "sche_nash"
            and run["seed"] == "D01"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"]["topology"] == "homogeneous"
        ]
        self.assertEqual(len(runs), 3)
        self.assertEqual(
            {run["metadata"]["m1_operational_candidate"] for run in runs},
            set(M1_OPERATIONAL_CANDIDATES),
        )
        self.assertEqual(len({run["run_spec_hash"] for run in runs}), 3)
        self.assertEqual(
            len({run["reference_dependency"]["build_spec_hash"] for run in runs}), 3
        )

    def test_screen_is_exact_three_by_six_by_five_product(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "m1-development.json"
            write_json_atomic(source, self.manifest)
            screen = derive_m1_candidate_screen_shard(source)
        self.assertEqual(len(screen["runs"]), 90)
        self.assertEqual(len(screen["reference_build_dependencies"]), 90)
        self.assertEqual(
            screen["fixed_seed_bank"]["selected_seeds"], list(M1_SCREEN_SEEDS)
        )
        self.assertEqual({run["method"] for run in screen["runs"]}, {"sche_nash"})

    def test_candidate_tampering_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.manifest)
        run = next(
            run
            for run in tampered["runs"]
            if run.get("metadata", {}).get("m1_operational_candidate") == "ready_order"
        )
        run["simulator_experiment"]["nash"]["operational_refinement"] = "formula"
        run["artifact_hashes"]["simulator_config_sha256"] = object_hash(
            run["simulator_experiment"]
        )
        run["run_spec_hash"] = object_hash(
            {key: value for key, value in run.items() if key != "run_spec_hash"}
        )
        tampered["manifest_hash"] = object_hash(
            {key: value for key, value in tampered.items() if key != "manifest_hash"}
        )
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(tampered)

    def test_screen_selection_uses_the_frozen_global_maximin_rule(self) -> None:
        aggregates = []
        for load in ("low", "middle", "high"):
            for topology in ("homogeneous", "heterogeneous"):
                for candidate, throughput, qpr in (
                    ("formula", 1.0, 1.0),
                    ("ready_order", 1.1, 0.9),
                    ("ready_finish_tie", 1.05, 1.05),
                ):
                    aggregates.append(
                        {
                            "candidate": candidate,
                            "load": load,
                            "topology": topology,
                            "mean_throughput_requests_per_ms": throughput,
                            "mean_qpr": qpr,
                        }
                    )
        selected, scores = _choose_candidate(aggregates)
        self.assertEqual(selected, "ready_finish_tie")
        self.assertEqual(scores[0]["candidate"], selected)

    def test_selection_receipt_derives_exact_qualification_product(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "m1-development.json"
            selection_path = root / "selection.json"
            write_json_atomic(source, self.manifest)
            selection = {
                "schema_version": SCREEN_SELECTION_SCHEMA,
                "selected_candidate": "ready_finish_tie",
                "development_source_manifest": {
                    "manifest_hash": self.manifest["manifest_hash"],
                    "file_sha256": file_hash(source),
                },
            }
            selection["document_sha256"] = object_hash(selection)
            write_json_atomic(selection_path, selection)
            qualification = derive_m1_qualification_shard(source, selection_path)
        self.assertEqual(qualification["phase"], "qualification")
        self.assertEqual(len(qualification["runs"]), 1200)
        self.assertEqual(len(qualification["reference_build_dependencies"]), 120)
        self.assertEqual(
            {
                run.get("metadata", {}).get("m1_operational_candidate")
                for run in qualification["runs"]
                if run["method"] == "sche_nash"
            },
            {"ready_finish_tie"},
        )


if __name__ == "__main__":
    unittest.main()
