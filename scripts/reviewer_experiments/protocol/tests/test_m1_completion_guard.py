from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.m1_completion_guard import (
    M1_GUARD_CANDIDATES,
    M1_GUARD_SCREEN_SEEDS,
    M1_GUARD_SELECTION_SCHEMA,
    build_m1_completion_guard_manifest,
    derive_m1_completion_guard_qualification_shard,
    derive_m1_completion_guard_screen_shard,
)
from scripts.reviewer_experiments.protocol.m1_qualification import _choose_candidate
from scripts.reviewer_experiments.protocol.schema import (
    M1_DEVELOPMENT_SEEDS,
    M1_GUARD_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


class M1CompletionGuardProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.binary = cls.root / "serverless_sim.exe"
        cls.binary.write_bytes(b"frozen-completion-guard-test-runtime")
        cls.manifest = build_m1_completion_guard_manifest(cls.binary)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_fresh_complete_product_and_runtime_are_frozen(self) -> None:
        manifest = self.manifest
        self.assertEqual(len(manifest["runs"]), 1440)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 360)
        self.assertEqual(
            manifest["fixed_seed_bank"]["selected_seeds"], list(M1_GUARD_SEEDS)
        )
        self.assertTrue(set(M1_DEVELOPMENT_SEEDS).isdisjoint(M1_GUARD_SEEDS))
        marker = manifest["m1_completion_guard_matrix"]
        self.assertEqual(marker["candidates"], list(M1_GUARD_CANDIDATES))
        self.assertEqual(marker["runtime_binary"]["sha256"], file_hash(self.binary))
        self.assertEqual(
            manifest["execution"]["command_template"][-2:],
            ["--simulator-exe", str(self.binary.resolve())],
        )

    def test_candidate_binding_changes_run_and_reference_identity(self) -> None:
        runs = [
            run
            for run in self.manifest["runs"]
            if run["method"] == "sche_nash"
            and run["seed"] == "D21"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"]["topology"] == "homogeneous"
        ]
        self.assertEqual(len(runs), 3)
        self.assertEqual(
            {run["metadata"]["m1_operational_candidate"] for run in runs},
            set(M1_GUARD_CANDIDATES),
        )
        self.assertEqual(len({run["run_spec_hash"] for run in runs}), 3)
        self.assertEqual(
            len({run["reference_dependency"]["build_spec_hash"] for run in runs}),
            3,
        )

    def test_screen_is_exact_three_by_six_by_five_product(self) -> None:
        source = self.root / "guard-development.json"
        write_json_atomic(source, self.manifest)
        screen = derive_m1_completion_guard_screen_shard(source)
        self.assertEqual(len(screen["runs"]), 90)
        self.assertEqual(len(screen["reference_build_dependencies"]), 90)
        self.assertEqual(
            screen["fixed_seed_bank"]["selected_seeds"],
            list(M1_GUARD_SCREEN_SEEDS),
        )
        self.assertEqual({run["method"] for run in screen["runs"]}, {"sche_nash"})

    def test_guard_selection_uses_same_global_maximin_rule(self) -> None:
        aggregates = []
        for load in ("low", "middle", "high"):
            for topology in ("homogeneous", "heterogeneous"):
                for candidate, throughput, qpr in (
                    ("ready_order", 1.0, 1.0),
                    ("guarded_finish_05", 1.1, 0.9),
                    ("guarded_finish_15", 1.05, 1.05),
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
        selected, scores = _choose_candidate(
            aggregates, candidates=M1_GUARD_CANDIDATES
        )
        self.assertEqual(selected, "guarded_finish_15")
        self.assertEqual(scores[0]["candidate"], selected)

    def _selection(self, source: Path, candidate: str) -> dict[str, object]:
        authorized = candidate != "ready_order"
        receipt: dict[str, object] = {
            "schema_version": M1_GUARD_SELECTION_SCHEMA,
            "selected_candidate": candidate,
            "qualification_authorized": authorized,
            "development_source_manifest": {
                "manifest_hash": self.manifest["manifest_hash"],
                "file_sha256": file_hash(source),
            },
        }
        receipt["document_sha256"] = object_hash(receipt)
        return receipt

    def test_control_winner_cannot_authorize_qualification(self) -> None:
        source = self.root / "guard-control-source.json"
        selection_path = self.root / "guard-control-selection.json"
        write_json_atomic(source, self.manifest)
        write_json_atomic(selection_path, self._selection(source, "ready_order"))
        with self.assertRaises(ProtocolValidationError):
            derive_m1_completion_guard_qualification_shard(source, selection_path)

    def test_guard_winner_derives_exact_qualification_product(self) -> None:
        source = self.root / "guard-winner-source.json"
        selection_path = self.root / "guard-winner-selection.json"
        write_json_atomic(source, self.manifest)
        write_json_atomic(
            selection_path, self._selection(source, "guarded_finish_05")
        )
        qualification = derive_m1_completion_guard_qualification_shard(
            source, selection_path
        )
        self.assertEqual(len(qualification["runs"]), 1200)
        self.assertEqual(len(qualification["reference_build_dependencies"]), 120)
        self.assertEqual(
            {
                run.get("metadata", {}).get("m1_operational_candidate")
                for run in qualification["runs"]
                if run["method"] == "sche_nash"
            },
            {"guarded_finish_05"},
        )

    def test_candidate_tampering_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.manifest)
        run = next(
            run
            for run in tampered["runs"]
            if run.get("metadata", {}).get("m1_operational_candidate")
            == "guarded_finish_05"
        )
        run["simulator_experiment"]["nash"]["operational_refinement"] = "ready_order"
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


if __name__ == "__main__":
    unittest.main()
