"""Regression tests for the formal E5/E6 CI-extension shard."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.cli import main as protocol_main
from scripts.reviewer_experiments.protocol.formal_e1_shard import (
    derive_formal_e1_heterogeneous_shard,
)
from scripts.reviewer_experiments.protocol.formal_e5_e6_extension_shard import (
    FORMAL_CI_EXTENSION_SEEDS,
    FORMAL_E5_E6_EXTENSION_SHARD_MARKER,
    derive_formal_e5_e6_ci_extension_shard,
    validate_e1_ci_extension_reuse_lineage,
    write_formal_e5_e6_ci_extension_shard,
)
from scripts.reviewer_experiments.protocol.matrix import (
    ABLATIONS,
    LOADS,
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_METHODS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


def _write_source(root: Path, seed_stage: str) -> tuple[Path, dict]:
    source = build_manifest(load_protocol_config(), seed_stage)
    path = root / f"manifest.{seed_stage}.full.json"
    write_json_atomic(path, source)
    return path, source


def _rehash(document: dict) -> None:
    document.pop("manifest_hash", None)
    document["manifest_hash"] = object_hash(document)


class FormalE5E6ExtensionShardTests(unittest.TestCase):
    def test_exact_extension_product_references_and_reuse_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root, "ci_extension")
            output = root / "manifest.e5-e6.ci-extension.json"
            shard = write_formal_e5_e6_ci_extension_shard(source_path, output)

            self.assertEqual(read_json(output), shard)
            self.assertIs(shard["formal_results_eligible"], True)
            self.assertEqual(shard["seed_stage"], "ci_extension")
            self.assertEqual(len(shard["runs"]), 160)
            self.assertEqual(len(shard["reference_build_dependencies"]), 130)
            self.assertEqual(shard["matrix_summary"]["new_cells"], 16)
            self.assertEqual(shard["matrix_summary"]["new_runs"], 160)

            observed_e5 = {
                (
                    run["variant"],
                    run["workload"]["request_freq"],
                    run["seed"],
                )
                for run in shard["runs"]
                if run["experiment_id"] == "E5"
            }
            expected_e5 = {
                (variant, load, seed)
                for variant in ABLATIONS
                for load in LOADS
                for seed in FORMAL_CI_EXTENSION_SEEDS
            }
            observed_e6 = {
                (
                    run["method"],
                    run["workload"]["request_freq"],
                    run["seed"],
                )
                for run in shard["runs"]
                if run["experiment_id"] == "E6"
            }
            expected_e6 = {
                (method, load, seed)
                for method in ("cp_br", "onsocmax")
                for load in ("middle", "high")
                for seed in FORMAL_CI_EXTENSION_SEEDS
            }
            self.assertEqual(observed_e5, expected_e5)
            self.assertEqual(observed_e6, expected_e6)
            self.assertFalse(any(run["experiment_id"] == "E7" for run in shard["runs"]))
            self.assertEqual(
                sum(
                    run.get("reference_dependency") is not None
                    for run in shard["runs"]
                    if run["experiment_id"] == "E5"
                ),
                90,
            )

            marker = shard[FORMAL_E5_E6_EXTENSION_SHARD_MARKER]
            self.assertEqual(
                marker["source_manifest"]["manifest_hash"], source["manifest_hash"]
            )
            self.assertEqual(
                marker["source_manifest"]["file_sha256"], file_hash(source_path)
            )
            self.assertEqual(marker["selected_physical_run_count"], 160)
            self.assertEqual(marker["selected_physical_cell_count"], 16)
            self.assertEqual(marker["reference_build_count"], 130)
            self.assertEqual(marker["e1_reuse_projection_count"], 230)
            self.assertEqual(marker["e1_reuse_unique_source_run_count"], 210)
            self.assertEqual(set(marker["e1_reuse_lineage"]), {"E5", "E6"})
            self.assertEqual(len(marker["e1_reuse_lineage"]["E5"]), 30)
            self.assertEqual(len(marker["e1_reuse_lineage"]["E6"]), 200)
            without_hash = copy.deepcopy(shard)
            without_hash.pop("manifest_hash")
            self.assertEqual(shard["manifest_hash"], object_hash(without_hash))

    def test_reuse_lineage_matches_ci_extension_e1_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root, "ci_extension")
            shard = derive_formal_e5_e6_ci_extension_shard(source_path)
            e1 = derive_formal_e1_heterogeneous_shard(source_path)
            validate_e1_ci_extension_reuse_lineage(shard, e1)

            marker = shard[FORMAL_E5_E6_EXTENSION_SHARD_MARKER]
            all_role_ids = {
                row["source_run_id"]
                for rows in marker["e1_reuse_lineage"].values()
                for row in rows
            }
            self.assertEqual(len(all_role_ids), 210)
            self.assertEqual(
                {row["source_seed"] for row in marker["e1_reuse_lineage"]["E5"]},
                set(FORMAL_CI_EXTENSION_SEEDS),
            )

            tampered = copy.deepcopy(shard)
            tampered[FORMAL_E5_E6_EXTENSION_SHARD_MARKER]["e1_reuse_lineage"]["E5"][0][
                "source_workload_spec_hash"
            ] = ("0" * 64)
            _rehash(tampered)
            with self.assertRaisesRegex(
                ProtocolValidationError, "differs in source_workload_spec_hash"
            ):
                validate_e1_ci_extension_reuse_lineage(tampered, e1)

            initial_path, _ = _write_source(root, "initial")
            initial_e1 = derive_formal_e1_heterogeneous_shard(initial_path)
            with self.assertRaisesRegex(ProtocolValidationError, "CI-extension stage"):
                validate_e1_ci_extension_reuse_lineage(shard, initial_e1)

    def test_wrong_stage_incomplete_recursive_and_same_path_sources_fail_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for stage in ("initial", "all"):
                stage_path, _ = _write_source(root, stage)
                with self.subTest(seed_stage=stage):
                    with self.assertRaisesRegex(
                        ProtocolValidationError, "source must be the ci_extension"
                    ):
                        derive_formal_e5_e6_ci_extension_shard(stage_path)

            source_path, source = _write_source(root, "ci_extension")
            incomplete = copy.deepcopy(source)
            incomplete["runs"] = incomplete["runs"][:-1]
            incomplete["matrix_summary"]["new_runs"] -= 1
            _rehash(incomplete)
            incomplete_path = root / "manifest.incomplete.json"
            write_json_atomic(incomplete_path, incomplete)
            with self.assertRaisesRegex(
                ProtocolValidationError, "complete frozen E1-E7 matrix"
            ):
                derive_formal_e5_e6_ci_extension_shard(incomplete_path)

            output = root / "manifest.extension.json"
            write_formal_e5_e6_ci_extension_shard(source_path, output)
            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e5_e6_ci_extension_shard(output)
            with self.assertRaisesRegex(ProtocolValidationError, "must differ"):
                write_formal_e5_e6_ci_extension_shard(source_path, source_path)

    def test_marker_tampering_and_e7_insertion_fail_schema_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root, "ci_extension")
            shard = derive_formal_e5_e6_ci_extension_shard(source_path)

            changed_selection = copy.deepcopy(shard)
            changed_selection[FORMAL_E5_E6_EXTENSION_SHARD_MARKER]["selection"][
                "physical_runs"
            ]["E5"]["seeds"] = list(FORMAL_CI_EXTENSION_SEEDS[:-1])
            _rehash(changed_selection)
            with self.assertRaisesRegex(ProtocolValidationError, "selection"):
                validate_manifest(changed_selection)

            changed_rule = copy.deepcopy(shard)
            changed_rule[FORMAL_E5_E6_EXTENSION_SHARD_MARKER]["sealed_e1_reuse_rules"][
                "E5"
            ]["rule_sha256"] = ("0" * 64)
            _rehash(changed_rule)
            with self.assertRaisesRegex(ProtocolValidationError, "reuse rule"):
                validate_manifest(changed_rule)

            e7_source_run = next(
                (run for run in source["runs"] if run["experiment_id"] == "E7"),
                None,
            )
            self.assertIsNone(e7_source_run)
            wrong_role = copy.deepcopy(shard)
            wrong_role[FORMAL_E5_E6_EXTENSION_SHARD_MARKER]["e1_reuse_lineage"][
                "E7"
            ] = []
            _rehash(wrong_role)
            with self.assertRaisesRegex(ProtocolValidationError, "roles differ"):
                validate_manifest(wrong_role)

    def test_cli_is_nonselectable_and_json_schema_registers_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root, "ci_extension")
            output = root / "manifest.extension.json"
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(
                    protocol_main(
                        [
                            "shard-e5-e6-ci-extension",
                            str(source_path),
                            str(output),
                        ]
                    ),
                    0,
                )
            self.assertIn(
                "written_formal_e5_e6_ci_extension_shard", captured.getvalue()
            )
            self.assertEqual(len(read_json(output)["runs"]), 160)

            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    protocol_main(
                        [
                            "shard-e5-e6-ci-extension",
                            str(source_path),
                            str(root / "filtered.json"),
                            "--run-id",
                            "forbidden",
                        ]
                    )

            schema_path = Path(__file__).parents[1] / "manifest.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual(
                schema["properties"][FORMAL_E5_E6_EXTENSION_SHARD_MARKER]["$ref"],
                "#/$defs/formalE5E6CIExtensionShard",
            )
            definition = schema["$defs"]["formalE5E6CIExtensionShard"]
            self.assertEqual(
                definition["properties"]["selected_physical_run_count"],
                {"const": 160},
            )
            self.assertFalse(definition["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
