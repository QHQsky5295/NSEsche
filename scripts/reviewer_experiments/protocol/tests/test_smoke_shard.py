from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.matrix import (
    bind_tape_catalog,
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.reference import (
    bind_reference_catalog,
    inspect_reference_table,
    register_reference_build,
)
from scripts.reviewer_experiments.protocol.schema import (
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.smoke_shard import (
    derive_integration_smoke_shard,
    write_integration_smoke_shard,
)
from scripts.reviewer_experiments.protocol.tape import (
    inspect_tape,
    register_catalog_entry,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


def _selected_runs(manifest: dict) -> tuple[dict, dict]:
    selector = {
        "experiment_id": "E1",
        "seed": "E01",
        "request_freq": "low",
        "topology": "homogeneous",
    }

    def selected(method: str) -> dict:
        return next(
            run
            for run in manifest["runs"]
            if run["experiment_id"] == selector["experiment_id"]
            and run["seed"] == selector["seed"]
            and run["method"] == method
            and run["workload"]["request_freq"] == selector["request_freq"]
            and run["workload"]["topology"] == selector["topology"]
        )

    return selected("greedy"), selected("sche_nash")


class SmokeShardTests(unittest.TestCase):
    def _source(self, root: Path) -> tuple[Path, dict, dict, dict]:
        manifest = build_manifest(load_protocol_config(), "initial")
        greedy_run, nash_run = _selected_runs(manifest)
        path = root / "manifest.full.json"
        write_json_atomic(path, manifest)
        return path, manifest, greedy_run, nash_run

    def test_shard_seals_source_lineage_and_recomputes_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source, greedy_run, nash_run = self._source(root)
            output = root / "manifest.smoke.json"
            shard = write_integration_smoke_shard(
                source_path,
                output,
                [nash_run["run_id"], greedy_run["run_id"]],
                purpose="capture-bind-run-QC integration check",
            )

            validate_manifest(shard)
            self.assertEqual(read_json(output), shard)
            self.assertIs(shard["formal_results_eligible"], False)
            self.assertEqual(len(shard["runs"]), 2)
            self.assertEqual(shard["reuse_analyses"], source["reuse_analyses"])
            self.assertEqual(len(shard["reference_build_dependencies"]), 1)
            self.assertEqual(shard["matrix_summary"]["new_runs"], 2)
            self.assertEqual(shard["matrix_summary"]["new_cells"], 2)
            marker = shard["integration_smoke_shard"]
            self.assertEqual(marker["source_manifest"]["path"], str(source_path))
            self.assertEqual(
                marker["source_manifest"]["manifest_hash"], source["manifest_hash"]
            )
            self.assertEqual(
                marker["source_manifest"]["file_sha256"], file_hash(source_path)
            )
            self.assertEqual(
                {item["source_run_id"] for item in marker["selected_source_runs"]},
                {greedy_run["run_id"], nash_run["run_id"]},
            )
            self.assertEqual(
                {
                    item["source_run_spec_hash"]
                    for item in marker["selected_source_runs"]
                },
                {greedy_run["run_spec_hash"], nash_run["run_spec_hash"]},
            )

    def test_shard_rejects_unknown_duplicate_and_recursive_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _, greedy_run, _ = self._source(root)
            with self.assertRaisesRegex(ProtocolValidationError, "no selected run"):
                derive_integration_smoke_shard(source_path, ["does-not-exist"])
            with self.assertRaisesRegex(
                ProtocolValidationError, "must not be repeated"
            ):
                derive_integration_smoke_shard(
                    source_path, [greedy_run["run_id"], greedy_run["run_id"]]
                )
            shard_path = root / "smoke.json"
            write_integration_smoke_shard(
                source_path, shard_path, [greedy_run["run_id"]]
            )
            with self.assertRaisesRegex(ProtocolValidationError, "cannot be used"):
                derive_integration_smoke_shard(
                    shard_path, [read_json(shard_path)["runs"][0]["run_id"]]
                )

    def test_tape_and_reference_binders_accept_only_selected_shard_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _, greedy_run, nash_run = self._source(root)
            shard = derive_integration_smoke_shard(
                source_path, [greedy_run["run_id"], nash_run["run_id"]]
            )
            plan = shard["runs"][0]["workload_tape"]
            self.assertEqual(
                {run["workload_tape"]["key"] for run in shard["runs"]},
                {plan["key"]},
            )

            tape_path = root / "smoke-tape.json"
            write_json_atomic(
                tape_path,
                {
                    "version": 1,
                    "workload_seed": "E01",
                    "events": [{"frame": 0, "dag_id": 0}],
                },
            )
            info = inspect_tape(tape_path, "small")
            receipt_path = root / "capture-receipt.json"
            write_json_atomic(receipt_path, {"fixture": "smoke capture receipt"})
            capture = {
                "function_dag_qos_sha256": "1" * 64,
                "node_network_sha256": "2" * 64,
                "capture_environment_sha256": "3" * 64,
                "function_count": 1,
                "node_count": 20,
            }
            capture["semantic_bundle_sha256"] = object_hash(capture)
            entry = {
                **info.to_dict(),
                "kind": "base_steady",
                "parent_sha256": None,
                "transform": {"kind": "identity"},
                "measured_arrival_rate_rps": 1.0,
                "capture_environment": capture,
                "capture_receipt_path": str(receipt_path),
                "capture_receipt_sha256": file_hash(receipt_path),
                "provenance": copy.deepcopy(plan["provenance"]),
            }
            tape_catalog_path = root / "tape-catalog.json"
            tape_catalog = register_catalog_entry(tape_catalog_path, plan["key"], entry)
            tape_bound = bind_tape_catalog(shard, tape_catalog)
            validate_manifest(tape_bound)
            self.assertIs(tape_bound["all_tapes_bound"], True)
            self.assertEqual(len(tape_bound["reference_build_dependencies"]), 1)

            dependency = tape_bound["reference_build_dependencies"][0]
            reference_dir = root / "reference"
            reference_dir.mkdir()
            table_path = reference_dir / "table.jsonl"
            table_path.write_text(
                '{"kind":"offline_social_reference_build",'
                '"state_key_u64":1,"initial_assignment_hash":2,"reference":3.0}\n',
                encoding="utf-8",
            )
            table = inspect_reference_table(table_path)
            process_path = reference_dir / "process_observation.json"
            write_json_atomic(process_path, {"fixture": "measured process"})
            receipt_path = reference_dir / "reference_build_receipt.json"
            write_json_atomic(
                receipt_path,
                {
                    "schema_version": "NSE_REFERENCE_BUILD_RECEIPT_V1",
                    "reference_key": dependency["key"],
                    "build_spec_hash": dependency["build_spec_hash"],
                    "workload_tape_sha256": tape_bound["runs"][0]["workload_tape"][
                        "sha256"
                    ],
                    "table_sha256": table.sha256,
                    "table_bytes": table.bytes,
                    "table_line_count": table.line_count,
                    "state_pair_sequence_sha256": table.state_pair_sequence_sha256,
                    "assignment_sequence_sha256": "4" * 64,
                    "completed": 1,
                    "process_observation_sha256": file_hash(process_path),
                },
            )
            reference_catalog_path = root / "reference-catalog.json"
            register_reference_build(
                reference_catalog_path,
                dependency["key"],
                table_path,
                receipt_path,
            )
            reference_bound = bind_reference_catalog(
                tape_bound, read_json(reference_catalog_path)
            )
            validate_manifest(reference_bound)
            self.assertIs(reference_bound["all_references_bound"], True)
            self.assertEqual(len(reference_bound["runs"]), 2)
            self.assertIs(reference_bound["formal_results_eligible"], False)


if __name__ == "__main__":
    unittest.main()
