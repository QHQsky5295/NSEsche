"""Regression tests for the isolated initial E5/E6/E7 formal shard core."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.formal_e1_shard import (
    derive_formal_e1_heterogeneous_shard,
)
from scripts.reviewer_experiments.protocol.formal_e5_e6_e7_shard import (
    FORMAL_E5_E6_E7_SHARD_MARKER,
    FORMAL_E6_METHODS,
    FORMAL_E7_AXIAL_VARIANTS,
    FORMAL_E7_CENTRE_SEEDS,
    FORMAL_INITIAL_SEEDS,
    derive_formal_e5_e6_e7_initial_shard,
    validate_e1_reuse_lineage,
    write_formal_e5_e6_e7_initial_shard,
)
from scripts.reviewer_experiments.protocol.matrix import (
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.schema import (
    ProtocolValidationError,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


def _write_source(root: Path, seed_stage: str = "initial") -> tuple[Path, dict]:
    source = build_manifest(load_protocol_config(), seed_stage)
    path = root / f"manifest.{seed_stage}.full.json"
    write_json_atomic(path, source)
    return path, source


class FormalE5E6E7ShardTests(unittest.TestCase):
    def test_initial_shape_counts_references_and_reuse_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root)
            output = root / "manifest.e5-e6-e7.initial.json"
            shard = write_formal_e5_e6_e7_initial_shard(source_path, output)

            self.assertEqual(read_json(output), shard)
            self.assertIs(shard["formal_results_eligible"], True)
            self.assertEqual(shard["seed_stage"], "initial")
            self.assertEqual(len(shard["runs"]), 220)
            self.assertEqual(len(shard["reference_build_dependencies"]), 190)
            self.assertEqual(shard["matrix_summary"]["new_cells"], 28)
            self.assertEqual(shard["matrix_summary"]["new_runs"], 220)

            by_experiment = {
                experiment_id: [
                    run
                    for run in shard["runs"]
                    if run["experiment_id"] == experiment_id
                ]
                for experiment_id in ("E5", "E6", "E7")
            }
            self.assertEqual(
                {key: len(value) for key, value in by_experiment.items()},
                {"E5": 120, "E6": 40, "E7": 60},
            )
            self.assertEqual(
                sum(
                    1
                    for run in by_experiment["E5"]
                    if run.get("variant") == "no_coordination"
                ),
                30,
            )
            self.assertEqual(
                sum(
                    1
                    for run in shard["runs"]
                    if run.get("reference_dependency") is not None
                ),
                190,
            )
            self.assertEqual(
                sum(
                    1
                    for run in by_experiment["E5"]
                    if run.get("reference_dependency") is not None
                ),
                90,
            )
            self.assertEqual(
                {run["method"] for run in by_experiment["E6"]},
                set(FORMAL_E6_METHODS),
            )
            self.assertEqual(
                {run["variant"] for run in by_experiment["E7"]},
                set(FORMAL_E7_AXIAL_VARIANTS),
            )
            self.assertEqual(
                {run["seed"] for run in by_experiment["E7"]},
                set(FORMAL_E7_CENTRE_SEEDS),
            )

            marker = shard[FORMAL_E5_E6_E7_SHARD_MARKER]
            self.assertEqual(
                marker["source_manifest"]["manifest_hash"], source["manifest_hash"]
            )
            self.assertEqual(
                marker["source_manifest"]["file_sha256"], file_hash(source_path)
            )
            self.assertEqual(marker["selected_physical_run_count"], 220)
            self.assertEqual(marker["reference_build_count"], 190)
            self.assertEqual(marker["e1_reuse_projection_count"], 245)
            self.assertEqual(marker["e1_reuse_unique_source_run_count"], 210)
            self.assertEqual(len(marker["e1_reuse_lineage"]["E5"]), 30)
            self.assertEqual(len(marker["e1_reuse_lineage"]["E6"]), 200)
            self.assertEqual(len(marker["e1_reuse_lineage"]["E7"]), 15)
            without_hash = copy.deepcopy(shard)
            without_hash.pop("manifest_hash")
            self.assertEqual(shard["manifest_hash"], object_hash(without_hash))

    def test_reuse_lineage_matches_the_formal_heterogeneous_e1_shard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            combined = derive_formal_e5_e6_e7_initial_shard(source_path)
            completed_e1_path, _ = _write_source(root, "all")
            e1 = derive_formal_e1_heterogeneous_shard(completed_e1_path)

            e1_lineage = {
                (
                    run["method"],
                    run["workload"]["request_freq"],
                    run["seed"],
                ): run
                for run in e1["runs"]
                if run["seed"] in FORMAL_INITIAL_SEEDS
            }
            self.assertEqual(len(e1_lineage), 300)
            marker = combined[FORMAL_E5_E6_E7_SHARD_MARKER]
            for role, rows in marker["e1_reuse_lineage"].items():
                for row in rows:
                    key = (row["source_method"], row["source_load"], row["source_seed"])
                    self.assertIn(key, e1_lineage)
                    current = e1_lineage[key]
                    self.assertEqual(row["source_cell_id"], current["cell_id"])
                    self.assertEqual(
                        row["source_workload_spec_hash"], current["workload_spec_hash"]
                    )
                    self.assertEqual(
                        row["source_workload_tape_key"], current["workload_tape"]["key"]
                    )
                    self.assertEqual(
                        row["source_common_hpa_hash"], current["common_hpa_hash"]
                    )
                    self.assertEqual(row["source_topology"], "heterogeneous")
                    self.assertEqual(row["target_experiment_id"], role)
            validate_e1_reuse_lineage(combined, e1)

    def test_non_initial_incomplete_and_same_path_sources_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for stage in ("ci_extension", "all"):
                stage_path, _ = _write_source(root, stage)
                with self.subTest(seed_stage=stage):
                    with self.assertRaisesRegex(
                        ProtocolValidationError, "source must be the initial"
                    ):
                        derive_formal_e5_e6_e7_initial_shard(stage_path)

            source_path, source = _write_source(root)
            incomplete = copy.deepcopy(source)
            incomplete["runs"] = incomplete["runs"][:-1]
            incomplete["matrix_summary"]["new_runs"] -= 1
            incomplete.pop("manifest_hash")
            incomplete["manifest_hash"] = object_hash(incomplete)
            incomplete_path = root / "manifest.incomplete.json"
            write_json_atomic(incomplete_path, incomplete)
            with self.assertRaisesRegex(
                ProtocolValidationError, "complete frozen E1-E7 matrix"
            ):
                derive_formal_e5_e6_e7_initial_shard(incomplete_path)

            with self.assertRaisesRegex(ProtocolValidationError, "must differ"):
                write_formal_e5_e6_e7_initial_shard(source_path, source_path)

    def test_lineage_tampering_is_not_silently_accepted_by_local_shape_audit(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            shard = derive_formal_e5_e6_e7_initial_shard(source_path)
            tampered = copy.deepcopy(shard)
            tampered[FORMAL_E5_E6_E7_SHARD_MARKER]["e1_reuse_lineage"]["E5"][0][
                "source_workload_spec_hash"
            ] = ("0" * 64)
            # Recompute the outer hash to model an adversarial but syntactically
            # valid file; the role lineage must still expose the mismatch to the
            # later E1 merge audit rather than being treated as an opaque blob.
            tampered.pop("manifest_hash")
            tampered["manifest_hash"] = object_hash(tampered)
            _, e1 = _write_source(root)
            e1_shard = derive_formal_e1_heterogeneous_shard(
                root / "manifest.initial.full.json"
            )
            with self.assertRaisesRegex(
                ProtocolValidationError, "differs in source_workload_spec_hash"
            ):
                validate_e1_reuse_lineage(tampered, e1_shard)


if __name__ == "__main__":
    unittest.main()
