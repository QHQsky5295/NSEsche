"""Regression tests for the formal E3/E4 CI-extension shard."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.reviewer_experiments.protocol.cli import main as protocol_main
from scripts.reviewer_experiments.protocol.formal_e3_e4_extension_shard import (
    FORMAL_E3_E4_EXTENSION_SEEDS,
    FORMAL_E3_E4_EXTENSION_SHARD_MARKER,
    FORMAL_E3_E4_EXTENSION_SHARD_SCHEMA,
    derive_formal_e3_e4_ci_extension_shard,
    write_formal_e3_e4_ci_extension_shard,
)
from scripts.reviewer_experiments.protocol.formal_e3_e4_shard import (
    FORMAL_E3_E4_SHARD_MARKER,
    derive_formal_e3_e4_initial_shard,
)
from scripts.reviewer_experiments.protocol.matrix import (
    BURSTS,
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


class FormalE3E4ExtensionShardTests(unittest.TestCase):
    def test_exact_extension_product_tapes_references_and_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root, "ci_extension")
            output = root / "manifest.e3-e4.ci-extension.json"
            shard = write_formal_e3_e4_ci_extension_shard(source_path, output)

            self.assertEqual(read_json(output), shard)
            validate_manifest(shard)
            self.assertIs(shard["formal_results_eligible"], True)
            self.assertEqual(shard["seed_stage"], "ci_extension")
            self.assertEqual(len(source["runs"]), 1760)
            self.assertEqual(len(shard["runs"]), 400)
            self.assertEqual(
                Counter(run["experiment_id"] for run in shard["runs"]),
                {"E3": 300, "E4": 100},
            )
            self.assertEqual(len(shard["reference_build_dependencies"]), 40)
            self.assertEqual(shard["matrix_summary"]["new_cells"], 40)
            self.assertEqual(shard["matrix_summary"]["new_runs"], 400)

            observed_e3 = {
                (run["method"], run["workload"]["burst_name"], run["seed"])
                for run in shard["runs"]
                if run["experiment_id"] == "E3"
            }
            self.assertEqual(
                observed_e3,
                {
                    (method, burst, seed)
                    for method in FORMAL_E1_METHODS
                    for burst in BURSTS
                    for seed in FORMAL_E3_E4_EXTENSION_SEEDS
                },
            )
            observed_e4 = {
                (run["method"], run["seed"])
                for run in shard["runs"]
                if run["experiment_id"] == "E4"
            }
            self.assertEqual(
                observed_e4,
                {
                    (method, seed)
                    for method in FORMAL_E1_METHODS
                    for seed in FORMAL_E3_E4_EXTENSION_SEEDS
                },
            )

            for run in shard["runs"]:
                tape = run["workload_tape"]
                self.assertEqual(run["workload"]["qos_profile"], "balanced")
                self.assertEqual(
                    run["simulator_experiment"]["qos"]["class_assignment"],
                    "balanced",
                )
                if run["experiment_id"] == "E3":
                    self.assertEqual(tape["kind"], "derived_burst")
                    self.assertTrue(tape["parent_key"])
                    self.assertEqual(
                        tape["transform"]["scenario"],
                        run["workload"]["burst_name"],
                    )
                else:
                    self.assertEqual(tape["kind"], "base_steady")
                    self.assertIsNone(tape["parent_key"])

            reference_runs = [
                run for run in shard["runs"] if run.get("reference_dependency")
            ]
            self.assertEqual(len(reference_runs), 40)
            self.assertEqual({run["method"] for run in reference_runs}, {"sche_nash"})

            marker = shard[FORMAL_E3_E4_EXTENSION_SHARD_MARKER]
            self.assertEqual(
                marker["schema_version"], FORMAL_E3_E4_EXTENSION_SHARD_SCHEMA
            )
            self.assertEqual(
                marker["source_manifest"]["manifest_hash"], source["manifest_hash"]
            )
            self.assertEqual(
                marker["source_manifest"]["file_sha256"], file_hash(source_path)
            )
            self.assertEqual(len(marker["selected_source_runs"]), 400)
            self.assertEqual(marker["selected_e3_run_count"], 300)
            self.assertEqual(marker["selected_e4_run_count"], 100)
            self.assertEqual(marker["selected_reference_build_count"], 40)
            self.assertEqual(marker["selected_balanced_qos_run_count"], 400)
            self.assertEqual(marker["selected_faasrank_run_count"], 40)
            self.assertEqual(
                marker["sealed_reuse_rules"],
                [
                    {
                        "rule_id": rule["rule_id"],
                        "rule_sha256": rule["rule_sha256"],
                    }
                    for rule in source["reuse_analyses"]
                ],
            )
            without_hash = copy.deepcopy(shard)
            without_hash.pop("manifest_hash")
            self.assertEqual(shard["manifest_hash"], object_hash(without_hash))

    def test_wrong_stage_incomplete_recursive_and_same_path_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for stage in ("initial", "all"):
                source_path, _ = _write_source(root, stage)
                with self.subTest(seed_stage=stage):
                    with self.assertRaisesRegex(
                        ProtocolValidationError, "source must be the ci_extension"
                    ):
                        derive_formal_e3_e4_ci_extension_shard(source_path)

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
                derive_formal_e3_e4_ci_extension_shard(incomplete_path)

            output = root / "manifest.extension.json"
            write_formal_e3_e4_ci_extension_shard(source_path, output)
            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e3_e4_ci_extension_shard(output)
            with self.assertRaisesRegex(ProtocolValidationError, "must differ"):
                write_formal_e3_e4_ci_extension_shard(source_path, source_path)

    def test_selection_lineage_reference_and_reuse_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root, "ci_extension")
            shard = derive_formal_e3_e4_ci_extension_shard(source_path)

            selection = copy.deepcopy(shard)
            selection[FORMAL_E3_E4_EXTENSION_SHARD_MARKER]["selection"]["seeds"] = (
                list(FORMAL_E3_E4_EXTENSION_SEEDS[:-1])
            )
            _rehash(selection)
            with self.assertRaisesRegex(ProtocolValidationError, "selection"):
                validate_manifest(selection)

            lineage = copy.deepcopy(shard)
            lineage[FORMAL_E3_E4_EXTENSION_SHARD_MARKER]["selected_source_runs"][0][
                "source_workload_tape_key"
            ] = "tampered-tape"
            _rehash(lineage)
            with self.assertRaisesRegex(ProtocolValidationError, "current run"):
                validate_manifest(lineage)

            references = copy.deepcopy(shard)
            references["reference_build_dependencies"].pop()
            _rehash(references)
            with self.assertRaisesRegex(ProtocolValidationError, "reference"):
                validate_manifest(references)

            reuse = copy.deepcopy(shard)
            reuse[FORMAL_E3_E4_EXTENSION_SHARD_MARKER]["sealed_reuse_rules"][0][
                "rule_sha256"
            ] = "0" * 64
            _rehash(reuse)
            with self.assertRaisesRegex(ProtocolValidationError, "reuse rules"):
                validate_manifest(reuse)

    def test_cli_schema_and_initial_shard_remain_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root, "ci_extension")
            output = root / "manifest.extension.json"
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(
                    protocol_main(
                        [
                            "shard-e3-e4-ci-extension",
                            str(source_path),
                            str(output),
                        ]
                    ),
                    0,
                )
            self.assertIn(
                "written_formal_e3_e4_ci_extension_shard", captured.getvalue()
            )
            self.assertEqual(len(read_json(output)["runs"]), 400)

            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    protocol_main(
                        [
                            "shard-e3-e4-ci-extension",
                            str(source_path),
                            str(root / "filtered.json"),
                            "--run-id",
                            "forbidden",
                        ]
                    )

            schema_path = Path(__file__).parents[1] / "manifest.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual(
                schema["properties"][FORMAL_E3_E4_EXTENSION_SHARD_MARKER]["$ref"],
                "#/$defs/formalE3E4CIExtensionShard",
            )
            definition = schema["$defs"]["formalE3E4CIExtensionShard"]
            self.assertEqual(
                definition["properties"]["selected_run_count"], {"const": 400}
            )
            self.assertFalse(definition["additionalProperties"])

            initial_source_path, _ = _write_source(root, "initial")
            initial = derive_formal_e3_e4_initial_shard(initial_source_path)
            validate_manifest(initial)
            self.assertIn(FORMAL_E3_E4_SHARD_MARKER, initial)
            self.assertNotIn(FORMAL_E3_E4_EXTENSION_SHARD_MARKER, initial)


if __name__ == "__main__":
    unittest.main()
