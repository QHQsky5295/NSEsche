from __future__ import annotations

import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.cli import main as protocol_main
from scripts.reviewer_experiments.protocol.formal_e2_shard import (
    derive_formal_e2_weak_scaling_shard,
    write_formal_e2_weak_scaling_shard,
)
from scripts.reviewer_experiments.protocol.matrix import (
    bind_tape_catalog,
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_LOADS,
    FORMAL_E1_METHODS,
    FORMAL_E1_SEEDS_BY_STAGE,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.tape import (
    inspect_tape,
    project_tape_catalog_for_manifest,
    register_catalog_entry,
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


def _write_e1_base_catalog(root: Path, shard: dict) -> Path:
    catalog_path = root / "e1-base.catalog.json"
    parent_runs: dict[str, dict] = {}
    for run in shard["runs"]:
        parent_runs.setdefault(run["workload_tape"]["parent_key"], run)
    for key, run in parent_runs.items():
        seed = run["seed"]
        tape_path = root / "e1-tapes" / f"{key}.json"
        write_json_atomic(
            tape_path,
            {
                "version": 1,
                "workload_seed": seed,
                "events": [{"frame": 0, "dag_id": 0}],
            },
        )
        info = inspect_tape(tape_path, "small")
        receipt_path = root / "e1-receipts" / f"{key}.json"
        write_json_atomic(
            receipt_path,
            {
                "schema_version": "NSE_BASE_TAPE_CAPTURE_RECEIPT_V2",
                "workload_frequency_profile": copy.deepcopy(
                    run["workload_profile"]
                ),
            },
        )
        capture = {
            "function_dag_qos_sha256": "1" * 64,
            "node_network_sha256": "2" * 64,
            "capture_environment_sha256": "3" * 64,
            "function_count": 1,
            "node_count": 20,
        }
        capture["semantic_bundle_sha256"] = object_hash(capture)
        provenance = copy.deepcopy(run["workload_tape"]["provenance"])
        provenance["measured_arrival_rate_rps"] = 1.0
        register_catalog_entry(
            catalog_path,
            key,
            {
                **info.to_dict(),
                "kind": "base_steady",
                "parent_sha256": None,
                "transform": {"kind": "identity"},
                "measured_arrival_rate_rps": 1.0,
                "capture_environment": capture,
                "capture_receipt_path": str(receipt_path),
                "capture_receipt_sha256": file_hash(receipt_path),
                "workload_profile": copy.deepcopy(run["workload_profile"]),
                "provenance": provenance,
            },
        )
    return catalog_path


class FormalE2ShardTests(unittest.TestCase):
    def test_seed_stage_fixes_complete_physical_and_reuse_products(self) -> None:
        expected = {
            "initial": (600, 60, 300),
            "ci_extension": (600, 60, 300),
            "all": (1200, 120, 600),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for stage, counts in expected.items():
                with self.subTest(stage=stage):
                    source_path, _ = _write_source(root, stage)
                    shard = derive_formal_e2_weak_scaling_shard(source_path)
                    validate_manifest(shard)
                    marker = shard["formal_e2_weak_scaling_shard"]
                    self.assertEqual(
                        (
                            len(shard["runs"]),
                            len(shard["reference_build_dependencies"]),
                            len(marker["e1_reuse_source_runs"]),
                        ),
                        counts,
                    )
                    observed = {
                        (
                            run["method"],
                            run["workload"]["request_freq"],
                            run["cluster"]["node_count"],
                            run["seed"],
                        )
                        for run in shard["runs"]
                    }
                    expected_product = {
                        (method, load, nodes, seed)
                        for method in FORMAL_E1_METHODS
                        for load in FORMAL_E1_LOADS
                        for nodes in (100, 500)
                        for seed in FORMAL_E1_SEEDS_BY_STAGE[stage]
                    }
                    self.assertEqual(observed, expected_product)

    def test_lineage_rule_and_product_tampering_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            shard = derive_formal_e2_weak_scaling_shard(source_path)

            tampered = copy.deepcopy(shard)
            tampered["formal_e2_weak_scaling_shard"]["selected_source_runs"][0][
                "source_method"
            ] = "not-the-current-method"
            tampered.pop("manifest_hash")
            tampered["manifest_hash"] = object_hash(tampered)
            with self.assertRaisesRegex(
                ProtocolValidationError, "differs from the current run"
            ):
                validate_manifest(tampered)

            changed_reuse = copy.deepcopy(shard)
            changed_reuse["formal_e2_weak_scaling_shard"]["sealed_e1_reuse_rule"][
                "rule_sha256"
            ] = "0" * 64
            changed_reuse.pop("manifest_hash")
            changed_reuse["manifest_hash"] = object_hash(changed_reuse)
            with self.assertRaisesRegex(ProtocolValidationError, "reuse rule"):
                validate_manifest(changed_reuse)

            incomplete = copy.deepcopy(shard)
            incomplete["runs"].pop()
            incomplete.pop("manifest_hash")
            incomplete["manifest_hash"] = object_hash(incomplete)
            with self.assertRaisesRegex(ProtocolValidationError, "complete E2"):
                validate_manifest(incomplete)

    def test_project_catalog_derives_missing_scales_and_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            shard = derive_formal_e2_weak_scaling_shard(source_path)
            source_catalog = _write_e1_base_catalog(root, shard)
            projected_path = root / "projected" / "e2-tapes.catalog.json"
            projected = project_tape_catalog_for_manifest(
                shard,
                source_catalog,
                projected_path,
                root / "projected",
                mode="small",
            )
            required = {
                key
                for run in shard["runs"]
                for key in (
                    run["workload_tape"]["key"],
                    run["workload_tape"]["parent_key"],
                )
            }
            self.assertEqual(set(projected["entries"]), required)
            self.assertEqual(len(projected["entries"]), 90)
            self.assertEqual(
                projected["projection"]["source_catalog"]["file_sha256"],
                file_hash(source_catalog),
            )
            self.assertEqual(
                len(projected["projection"]["derived_after_projection_keys"]), 60
            )
            bound = bind_tape_catalog(shard, projected)
            validate_manifest(bound)

            with self.assertRaisesRegex(ProtocolValidationError, "refusing to replace"):
                project_tape_catalog_for_manifest(
                    shard,
                    source_catalog,
                    projected_path,
                    root / "projected",
                    mode="small",
                )

    def test_cli_is_nonselectable_and_recursive_sources_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            output = root / "manifest.e2.json"
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(
                    protocol_main(["shard-e2", str(source_path), str(output)]), 0
                )
            self.assertIn("written_formal_e2_weak_scaling_shard", captured.getvalue())
            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e2_weak_scaling_shard(output)
            with self.assertRaisesRegex(ProtocolValidationError, "must differ"):
                write_formal_e2_weak_scaling_shard(source_path, source_path)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    protocol_main(
                        [
                            "shard-e2",
                            str(source_path),
                            str(root / "filtered.json"),
                            "--run-id",
                            "forbidden",
                        ]
                    )

            document = read_json(output)
            document["formal_e1_homogeneous_shard"] = copy.deepcopy(
                document["formal_e2_weak_scaling_shard"]
            )
            document.pop("manifest_hash")
            document["manifest_hash"] = object_hash(document)
            with self.assertRaisesRegex(ProtocolValidationError, "multiple formal"):
                validate_manifest(document)


if __name__ == "__main__":
    unittest.main()
