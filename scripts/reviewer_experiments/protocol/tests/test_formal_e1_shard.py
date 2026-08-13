from __future__ import annotations

import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.cli import main as protocol_main
from scripts.reviewer_experiments.protocol.formal_e1_shard import (
    derive_formal_e1_heterogeneous_shard,
    derive_formal_e1_homogeneous_shard,
    write_formal_e1_heterogeneous_shard,
    write_formal_e1_homogeneous_shard,
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
from scripts.reviewer_experiments.protocol.smoke_shard import (
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


def _write_source(root: Path, seed_stage: str = "initial") -> tuple[Path, dict]:
    source = build_manifest(load_protocol_config(), seed_stage)
    path = root / f"manifest.{seed_stage}.full.json"
    write_json_atomic(path, source)
    return path, source


def _bind_fixture_tapes(
    root: Path, shard: dict
) -> tuple[Path, dict, dict]:
    catalog_path = root / "tapes.catalog.json"
    plans = {run["workload_tape"]["key"]: run for run in shard["runs"]}
    for key, run in plans.items():
        seed = run["seed"]
        tape_path = root / "tapes" / f"{key}.json"
        write_json_atomic(
            tape_path,
            {
                "version": 1,
                "workload_seed": seed,
                "events": [{"frame": 0, "dag_id": 0}],
            },
        )
        info = inspect_tape(tape_path, "small")
        receipt_path = root / "receipts" / f"{key}.json"
        write_json_atomic(
            receipt_path,
            {
                "fixture": key,
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
        entry = {
            **info.to_dict(),
            "kind": "base_steady",
            "parent_sha256": None,
            "transform": {"kind": "identity"},
            "measured_arrival_rate_rps": 1.0,
            "capture_environment": capture,
            "capture_receipt_path": str(receipt_path),
            "capture_receipt_sha256": file_hash(receipt_path),
            "workload_profile": copy.deepcopy(run["workload_profile"]),
            "provenance": copy.deepcopy(run["workload_tape"]["provenance"]),
        }
        register_catalog_entry(catalog_path, key, entry)

    catalog = read_json(catalog_path)
    bound = bind_tape_catalog(shard, catalog)
    return catalog_path, catalog, bound


class FormalE1HomogeneousShardTests(unittest.TestCase):
    def test_initial_shard_is_the_complete_sealed_formal_product(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root)
            output = root / "manifest.e1-homogeneous.json"
            shard = write_formal_e1_homogeneous_shard(source_path, output)

            validate_manifest(shard)
            self.assertEqual(read_json(output), shard)
            self.assertIs(shard["formal_results_eligible"], True)
            self.assertNotIn("integration_smoke_shard", shard)
            self.assertEqual(len(shard["runs"]), 300)
            self.assertEqual(len(shard["reference_build_dependencies"]), 30)
            self.assertEqual(shard["matrix_summary"]["new_cells"], 30)
            self.assertEqual(shard["matrix_summary"]["new_runs"], 300)

            observed = {
                (
                    run["method"],
                    run["workload"]["request_freq"],
                    run["seed"],
                )
                for run in shard["runs"]
            }
            expected = {
                (method, load, seed)
                for method in FORMAL_E1_METHODS
                for load in FORMAL_E1_LOADS
                for seed in FORMAL_E1_SEEDS_BY_STAGE["initial"]
            }
            self.assertEqual(observed, expected)
            self.assertTrue(
                all(
                    run["experiment_id"] == "E1"
                    and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
                    for run in shard["runs"]
                )
            )

            marker = shard["formal_e1_homogeneous_shard"]
            self.assertEqual(marker["source_manifest"]["path"], str(source_path))
            self.assertEqual(
                marker["source_manifest"]["manifest_hash"], source["manifest_hash"]
            )
            self.assertEqual(
                marker["source_manifest"]["file_sha256"], file_hash(source_path)
            )
            self.assertEqual(marker["selected_run_count"], 300)
            self.assertEqual(marker["selected_cell_count"], 30)
            self.assertEqual(marker["selected_reference_build_count"], 30)
            self.assertEqual(
                marker["sealed_reuse_rules"],
                [
                    {
                        "rule_id": entry["rule_id"],
                        "rule_sha256": entry["rule_sha256"],
                    }
                    for entry in source["reuse_analyses"]
                ],
            )

    def test_seed_stage_uniquely_determines_shard_size_and_seeds(self) -> None:
        expected_sizes = {"initial": 300, "ci_extension": 300, "all": 600}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for seed_stage, expected_size in expected_sizes.items():
                with self.subTest(seed_stage=seed_stage):
                    source_path, _ = _write_source(root, seed_stage)
                    shard = derive_formal_e1_homogeneous_shard(source_path)
                    self.assertEqual(len(shard["runs"]), expected_size)
                    self.assertEqual(
                        {run["seed"] for run in shard["runs"]},
                        set(FORMAL_E1_SEEDS_BY_STAGE[seed_stage]),
                    )
                    self.assertEqual(
                        shard["formal_e1_homogeneous_shard"]["selection"]["seeds"],
                        list(FORMAL_E1_SEEDS_BY_STAGE[seed_stage]),
                    )

    def test_incomplete_arbitrary_and_recursive_sources_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root)

            incomplete = copy.deepcopy(source)
            incomplete["runs"] = incomplete["runs"][:-1]
            incomplete.pop("manifest_hash")
            incomplete["manifest_hash"] = object_hash(incomplete)
            incomplete_path = root / "manifest.incomplete.json"
            write_json_atomic(incomplete_path, incomplete)
            with self.assertRaisesRegex(
                ProtocolValidationError, "not the complete frozen E1-E7 matrix"
            ):
                derive_formal_e1_homogeneous_shard(incomplete_path)

            formal_path = root / "manifest.formal-shard.json"
            write_formal_e1_homogeneous_shard(source_path, formal_path)
            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e1_homogeneous_shard(formal_path)

            greedy = next(
                run
                for run in source["runs"]
                if run["experiment_id"] == "E1"
                and run["method"] == "greedy"
                and run["workload"]["request_freq"] == "low"
                and run["cluster"]["topology"] == "homogeneous"
                and run["seed"] == "E01"
            )
            smoke_path = root / "manifest.smoke.json"
            write_integration_smoke_shard(
                source_path,
                smoke_path,
                [greedy["run_id"]],
            )
            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e1_homogeneous_shard(smoke_path)

            with self.assertRaisesRegex(ProtocolValidationError, "must differ"):
                write_formal_e1_homogeneous_shard(source_path, source_path)

    def test_lineage_survives_tape_binding_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            shard = derive_formal_e1_homogeneous_shard(source_path)

            catalog_path, catalog, bound = _bind_fixture_tapes(root, shard)
            validate_manifest(bound)
            source_ids = {
                entry["source_run_id"]
                for entry in bound["formal_e1_homogeneous_shard"][
                    "selected_source_runs"
                ]
            }
            self.assertNotEqual(
                source_ids,
                {run["run_id"] for run in bound["runs"]},
            )

            tampered = copy.deepcopy(bound)
            tampered["formal_e1_homogeneous_shard"]["selected_source_runs"][0][
                "source_method"
            ] = "random"
            tampered.pop("manifest_hash")
            tampered["manifest_hash"] = object_hash(tampered)
            with self.assertRaisesRegex(
                ProtocolValidationError, "differs from the current run after binding"
            ):
                validate_manifest(tampered)

            incomplete = copy.deepcopy(bound)
            incomplete["runs"] = incomplete["runs"][:-1]
            incomplete.pop("manifest_hash")
            incomplete["manifest_hash"] = object_hash(incomplete)
            with self.assertRaisesRegex(
                ProtocolValidationError, "complete E1 homogeneous Cartesian product"
            ):
                validate_manifest(incomplete)

            catalog_with_extra = copy.deepcopy(catalog)
            catalog_with_extra["entries"]["unexpected-tape"] = copy.deepcopy(
                next(iter(catalog_with_extra["entries"].values()))
            )
            catalog_with_extra.pop("catalog_hash")
            catalog_with_extra["catalog_hash"] = object_hash(catalog_with_extra)
            with self.assertRaisesRegex(
                ProtocolValidationError, "extra=.*unexpected-tape"
            ):
                bind_tape_catalog(shard, catalog_with_extra)

            changed_catalog = copy.deepcopy(catalog)
            changed_entry = next(iter(changed_catalog["entries"].values()))
            changed_path = Path(changed_entry["path"])
            changed_path.write_bytes(changed_path.read_bytes() + b" ")
            with self.assertRaisesRegex(
                ProtocolValidationError, "differs from the actual file"
            ):
                bind_tape_catalog(shard, changed_catalog)

    def test_cli_has_a_dedicated_nonselectable_formal_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            output = root / "manifest.e1.json"
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                code = protocol_main(
                    [
                        "shard-e1-homogeneous",
                        str(source_path),
                        str(output),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("written_formal_e1_homogeneous_shard", captured.getvalue())
            self.assertIs(read_json(output)["formal_results_eligible"], True)

            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    protocol_main(
                        [
                            "shard-e1-homogeneous",
                            str(source_path),
                            str(root / "filtered.json"),
                            "--run-id",
                            "E1.greedy.low.homogeneous.n20.E01.fake",
                        ]
                    )


class FormalE1HeterogeneousShardTests(unittest.TestCase):
    def test_all_shard_is_complete_formal_product_with_sealed_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source = _write_source(root, "all")
            output = root / "manifest.e1-heterogeneous.json"
            shard = write_formal_e1_heterogeneous_shard(source_path, output)

            validate_manifest(shard)
            self.assertEqual(read_json(output), shard)
            self.assertIs(shard["formal_results_eligible"], True)
            self.assertNotIn("integration_smoke_shard", shard)
            self.assertNotIn("formal_e1_homogeneous_shard", shard)
            self.assertEqual(len(shard["runs"]), 600)
            self.assertEqual(len(shard["reference_build_dependencies"]), 60)
            self.assertEqual(shard["matrix_summary"]["new_cells"], 30)
            self.assertEqual(shard["matrix_summary"]["new_runs"], 600)

            observed = {
                (
                    run["method"],
                    run["workload"]["request_freq"],
                    run["seed"],
                )
                for run in shard["runs"]
            }
            expected = {
                (method, load, seed)
                for method in FORMAL_E1_METHODS
                for load in FORMAL_E1_LOADS
                for seed in FORMAL_E1_SEEDS_BY_STAGE["all"]
            }
            self.assertEqual(observed, expected)
            self.assertTrue(
                all(
                    run["experiment_id"] == "E1"
                    and run["cluster"]
                    == {"node_count": 20, "topology": "heterogeneous"}
                    and run["workload"]["topology"] == "heterogeneous"
                    and ".heterogeneous.n20" in run["cell_id"]
                    and ".heterogeneous.mixed." in run["workload_tape"]["key"]
                    for run in shard["runs"]
                )
            )

            marker = shard["formal_e1_heterogeneous_shard"]
            self.assertEqual(
                marker["schema_version"],
                "NSE_FORMAL_E1_HETEROGENEOUS_SHARD_V1",
            )
            self.assertEqual(marker["source_manifest"]["path"], str(source_path))
            self.assertEqual(
                marker["source_manifest"]["manifest_hash"], source["manifest_hash"]
            )
            self.assertEqual(
                marker["source_manifest"]["file_sha256"], file_hash(source_path)
            )
            self.assertEqual(
                marker["selection"],
                {
                    "experiment_id": "E1",
                    "cluster_topology": "heterogeneous",
                    "node_count": 20,
                    "methods": list(FORMAL_E1_METHODS),
                    "loads": list(FORMAL_E1_LOADS),
                    "seeds": list(FORMAL_E1_SEEDS_BY_STAGE["all"]),
                },
            )
            self.assertEqual(marker["selected_run_count"], 600)
            self.assertEqual(marker["selected_cell_count"], 30)
            self.assertEqual(marker["selected_reference_build_count"], 60)
            self.assertEqual(len(marker["selected_source_runs"]), 600)

    def test_binding_and_tampering_checks_cover_heterogeneous_shard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            shard = derive_formal_e1_heterogeneous_shard(source_path)
            _, _, bound = _bind_fixture_tapes(root, shard)
            validate_manifest(bound)

            source_ids = {
                entry["source_run_id"]
                for entry in bound["formal_e1_heterogeneous_shard"][
                    "selected_source_runs"
                ]
            }
            self.assertNotEqual(source_ids, {run["run_id"] for run in bound["runs"]})

            tampered_lineage = copy.deepcopy(bound)
            tampered_lineage["formal_e1_heterogeneous_shard"][
                "selected_source_runs"
            ][0]["source_cluster_sha256"] = "0" * 64
            tampered_lineage.pop("manifest_hash")
            tampered_lineage["manifest_hash"] = object_hash(tampered_lineage)
            with self.assertRaisesRegex(
                ProtocolValidationError, "differs from the current run after binding"
            ):
                validate_manifest(tampered_lineage)

            missing_dependency = copy.deepcopy(bound)
            missing_dependency["reference_build_dependencies"].pop()
            missing_dependency.pop("manifest_hash")
            missing_dependency["manifest_hash"] = object_hash(missing_dependency)
            with self.assertRaisesRegex(
                ProtocolValidationError, "reference dependencies were not recomputed"
            ):
                validate_manifest(missing_dependency)

    def test_recursive_mixed_marker_and_same_path_sources_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            hetero_path = root / "manifest.e1-heterogeneous.json"
            hetero = write_formal_e1_heterogeneous_shard(source_path, hetero_path)

            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e1_heterogeneous_shard(hetero_path)
            with self.assertRaisesRegex(ProtocolValidationError, "derived shard"):
                derive_formal_e1_homogeneous_shard(hetero_path)
            with self.assertRaisesRegex(ProtocolValidationError, "must differ"):
                write_formal_e1_heterogeneous_shard(source_path, source_path)

            mixed = copy.deepcopy(hetero)
            mixed["formal_e1_homogeneous_shard"] = copy.deepcopy(
                mixed["formal_e1_heterogeneous_shard"]
            )
            mixed.pop("manifest_hash")
            mixed["manifest_hash"] = object_hash(mixed)
            with self.assertRaisesRegex(
                ProtocolValidationError, "multiple formal E1 shard markers"
            ):
                validate_manifest(mixed)

    def test_cli_has_dedicated_nonselectable_heterogeneous_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, _ = _write_source(root)
            output = root / "manifest.e1-heterogeneous.json"
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                code = protocol_main(
                    ["shard-e1-heterogeneous", str(source_path), str(output)]
                )
            self.assertEqual(code, 0)
            self.assertIn(
                "written_formal_e1_heterogeneous_shard", captured.getvalue()
            )
            self.assertIs(read_json(output)["formal_results_eligible"], True)

            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    protocol_main(
                        [
                            "shard-e1-heterogeneous",
                            str(source_path),
                            str(root / "filtered.json"),
                            "--run-id",
                            "E1.greedy.low.heterogeneous.n20.E01.fake",
                        ]
                    )


if __name__ == "__main__":
    unittest.main()
