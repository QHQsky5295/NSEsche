"""Regression tests for the frozen initial E3/E4 formal shard."""

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
from scripts.reviewer_experiments.protocol.formal_e3_e4_shard import (
    FORMAL_E3_E4_SHARD_MARKER,
    FORMAL_E3_E4_SHARD_SCHEMA,
    FORMAL_E3_E4_SEEDS,
    derive_formal_e3_e4_initial_shard,
    write_formal_e3_e4_initial_shard,
)
from scripts.reviewer_experiments.protocol.matrix import (
    BURSTS,
    bind_tape_catalog,
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
from scripts.reviewer_experiments.protocol.tape import (
    inspect_tape,
    project_tape_catalog_for_manifest,
    register_catalog_entry,
)


def _write_source(root: Path, seed_stage: str = "initial") -> tuple[Path, dict]:
    source = build_manifest(load_protocol_config(), seed_stage)
    path = root / f"manifest.{seed_stage}.full.json"
    write_json_atomic(path, source)
    return path, source


def _rehash(document: dict) -> None:
    document.pop("manifest_hash", None)
    document["manifest_hash"] = object_hash(document)


def _write_base_catalog(root: Path, shard: dict) -> Path:
    catalog_path = root / "balanced-base.catalog.json"
    parent_runs: dict[str, dict] = {}
    for run in shard["runs"]:
        tape = run["workload_tape"]
        key = tape["parent_key"] or tape["key"]
        parent_runs.setdefault(key, run)
    for key, run in parent_runs.items():
        tape_path = root / "base-tapes" / f"{key}.json"
        write_json_atomic(
            tape_path,
            {
                "version": 1,
                "workload_seed": run["seed"],
                "events": [
                    {"frame": 0, "dag_id": 0},
                    {"frame": 500, "dag_id": 1},
                ],
            },
        )
        info = inspect_tape(tape_path, "small")
        receipt_path = root / "base-receipts" / f"{key}.json"
        write_json_atomic(
            receipt_path,
            {
                "schema_version": "NSE_BASE_TAPE_CAPTURE_RECEIPT_V2",
                "workload_frequency_profile": copy.deepcopy(run["workload_profile"]),
            },
        )
        capture = {
            "function_dag_qos_sha256": "1" * 64,
            "node_network_sha256": "2" * 64,
            "capture_environment_sha256": "3" * 64,
            "function_count": 2,
            "node_count": 20,
        }
        capture["semantic_bundle_sha256"] = object_hash(capture)
        provenance = copy.deepcopy(run["workload_tape"]["provenance"])
        provenance["measured_arrival_rate_rps"] = 2.0
        register_catalog_entry(
            catalog_path,
            key,
            {
                **info.to_dict(),
                "kind": "base_steady",
                "parent_sha256": None,
                "transform": {"kind": "identity"},
                "measured_arrival_rate_rps": 2.0,
                "capture_environment": capture,
                "capture_receipt_path": str(receipt_path),
                "capture_receipt_sha256": file_hash(receipt_path),
                "workload_profile": copy.deepcopy(run["workload_profile"]),
                "provenance": provenance,
            },
        )
    return catalog_path


class FormalE3E4ShardTests(unittest.TestCase):
    def test_initial_shape_horizons_lineage_and_reference_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root)
            output = root / "manifest.e3-e4.initial.json"
            shard = write_formal_e3_e4_initial_shard(source_path, output)

            self.assertEqual(read_json(output), shard)
            validate_manifest(shard)
            self.assertIs(shard["formal_results_eligible"], True)
            self.assertEqual(shard["seed_stage"], "initial")
            self.assertEqual(len(shard["runs"]), 400)
            self.assertEqual(
                Counter(run["experiment_id"] for run in shard["runs"]),
                {"E3": 300, "E4": 100},
            )
            self.assertEqual(len(shard["reference_build_dependencies"]), 40)
            self.assertEqual(
                {
                    run["experiment_id"]: run["simulation"]["total_frame"]
                    for run in shard["runs"]
                },
                {"E3": 4000, "E4": 1000},
            )
            self.assertEqual(
                {
                    (run["method"], run["workload"]["burst_name"], run["seed"])
                    for run in shard["runs"]
                    if run["experiment_id"] == "E3"
                },
                {
                    (method, burst, seed)
                    for method in FORMAL_E1_METHODS
                    for burst in BURSTS
                    for seed in FORMAL_E3_E4_SEEDS
                },
            )
            self.assertTrue(
                all(
                    run["workload"]["qos_profile"] == "balanced"
                    and run["cluster"]
                    == {"node_count": 20, "topology": "heterogeneous"}
                    and run["simulation"]["arrival_horizon_frames"] == 1000
                    and run["simulation"]["observation_horizon_frames"] == 1000
                    for run in shard["runs"]
                )
            )
            reference_runs = [
                run for run in shard["runs"] if run.get("reference_dependency")
            ]
            self.assertEqual(len(reference_runs), 40)
            self.assertEqual({run["method"] for run in reference_runs}, {"sche_nash"})

            marker = shard[FORMAL_E3_E4_SHARD_MARKER]
            self.assertEqual(marker["schema_version"], FORMAL_E3_E4_SHARD_SCHEMA)
            self.assertEqual(
                marker["source_manifest"]["manifest_hash"], source["manifest_hash"]
            )
            self.assertEqual(
                marker["source_manifest"]["file_sha256"], file_hash(source_path)
            )
            self.assertEqual(len(marker["selected_source_runs"]), 400)
            self.assertEqual(marker["selected_cell_count"], 40)
            self.assertEqual(marker["selected_reference_build_count"], 40)
            self.assertEqual(marker["selected_balanced_qos_run_count"], 400)
            self.assertEqual(marker["selected_faasrank_run_count"], 40)
            without_hash = copy.deepcopy(shard)
            without_hash.pop("manifest_hash")
            self.assertEqual(shard["manifest_hash"], object_hash(without_hash))

    def test_lineage_marker_and_reference_tampering_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            shard = derive_formal_e3_e4_initial_shard(source_path)

            lineage = copy.deepcopy(shard)
            lineage[FORMAL_E3_E4_SHARD_MARKER]["selected_source_runs"][0][
                "source_method"
            ] = "not-the-current-method"
            _rehash(lineage)
            with self.assertRaisesRegex(
                ProtocolValidationError, "differs from the current run"
            ):
                validate_manifest(lineage)

            marker = copy.deepcopy(shard)
            marker[FORMAL_E3_E4_SHARD_MARKER]["selection"]["E3"]["total_frame"] = 3999
            _rehash(marker)
            with self.assertRaisesRegex(ProtocolValidationError, "selection"):
                validate_manifest(marker)

            references = copy.deepcopy(shard)
            references["reference_build_dependencies"].pop()
            _rehash(references)
            with self.assertRaisesRegex(ProtocolValidationError, "reference"):
                validate_manifest(references)

    def test_tape_projection_and_binding_preserve_formal_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            shard = derive_formal_e3_e4_initial_shard(source_path)
            source_catalog = _write_base_catalog(root, shard)
            projected_path = root / "projected" / "e3-e4-tapes.catalog.json"
            projected = project_tape_catalog_for_manifest(
                shard,
                source_catalog,
                projected_path,
                root / "projected",
                mode="small",
            )
            self.assertEqual(len(projected["entries"]), 40)
            self.assertEqual(len(projected["projection"]["projected_source_keys"]), 10)
            self.assertEqual(
                len(projected["projection"]["derived_after_projection_keys"]), 30
            )
            bound = bind_tape_catalog(shard, projected)
            validate_manifest(bound)
            self.assertIs(bound["all_tapes_bound"], True)
            self.assertEqual(
                len(bound[FORMAL_E3_E4_SHARD_MARKER]["selected_source_runs"]), 400
            )
            self.assertTrue(
                all(run["workload_tape"]["sha256"] for run in bound["runs"])
            )

    def test_non_initial_incomplete_recursive_and_same_path_sources_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for stage in ("ci_extension", "all"):
                stage_path, _ = _write_source(root, stage)
                with self.subTest(seed_stage=stage):
                    with self.assertRaisesRegex(
                        ProtocolValidationError, "source must be the initial"
                    ):
                        derive_formal_e3_e4_initial_shard(stage_path)

            source_path, source = _write_source(root)
            incomplete = copy.deepcopy(source)
            incomplete["runs"] = incomplete["runs"][:-1]
            incomplete["matrix_summary"]["new_runs"] -= 1
            _rehash(incomplete)
            incomplete_path = root / "manifest.incomplete.json"
            write_json_atomic(incomplete_path, incomplete)
            with self.assertRaisesRegex(
                ProtocolValidationError, "complete frozen E1-E7 matrix"
            ):
                derive_formal_e3_e4_initial_shard(incomplete_path)

            output = root / "manifest.e3-e4.json"
            write_formal_e3_e4_initial_shard(source_path, output)
            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e3_e4_initial_shard(output)
            with self.assertRaisesRegex(ProtocolValidationError, "must differ"):
                write_formal_e3_e4_initial_shard(source_path, source_path)

    def test_cli_is_nonselectable_and_json_schema_registers_the_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            output = root / "manifest.e3-e4.json"
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(
                    protocol_main(["shard-e3-e4", str(source_path), str(output)]), 0
                )
            self.assertIn("written_formal_e3_e4_initial_shard", captured.getvalue())
            self.assertEqual(len(read_json(output)["runs"]), 400)

            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    protocol_main(
                        [
                            "shard-e3-e4",
                            str(source_path),
                            str(root / "filtered.json"),
                            "--run-id",
                            "forbidden",
                        ]
                    )

            schema_path = Path(__file__).parents[1] / "manifest.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual(
                schema["properties"][FORMAL_E3_E4_SHARD_MARKER]["$ref"],
                "#/$defs/formalE3E4InitialShard",
            )
            definition = schema["$defs"]["formalE3E4InitialShard"]
            self.assertEqual(
                definition["properties"]["selected_run_count"], {"const": 400}
            )
            self.assertFalse(definition["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
