import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_random_prefix_middle_training_v154 import (
    COMMON_ENVIRONMENT,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    SEEDS,
    SOURCE_MANIFEST,
    _random_differences,
    _rewrite_candidate,
    _validate_reference_catalog,
    _validate_product,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


class V154ProtocolTests(unittest.TestCase):
    def test_plan_and_candidate_are_frozen(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = read_json(PLAN)
        self.assertEqual(plan["frozen_candidate"]["profile"], PROFILE)
        self.assertEqual(tuple(plan["training_design"]["training_seeds"]), SEEDS)
        self.assertEqual(tuple(plan["training_design"]["fixed_execution_order"]), SEEDS)
        self.assertEqual(
            plan["frozen_candidate"]["numeric_hyperparameters_added_after_v153"],
            0,
        )
        self.assertEqual(plan["frozen_candidate"]["environment"], COMMON_ENVIRONMENT)

    def test_candidate_rewrite_is_exact_middle_e01_e20_product(self) -> None:
        manifest = _rewrite_candidate(read_json(SOURCE_MANIFEST), "1" * 40)
        _validate_product(manifest, references_bound=False)
        self.assertEqual(len(manifest["runs"]), 20)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 20)
        self.assertEqual({run["seed"] for run in manifest["runs"]}, set(SEEDS))
        for run in manifest["runs"]:
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], PROFILE
            )
            self.assertTrue(run["metadata"]["v154_exact_random_prefix_cohort"])

    def test_random_difference_gate_requires_a_primary_metric_change(self) -> None:
        candidate = [
            {
                "load": "middle",
                "seed": seed,
                "throughput": 1.0,
                "qpr_finite_only": 2.0,
                "qpr_zero_completed_as_zero": 2.0,
            }
            for seed in SEEDS
        ]
        baselines = [
            {
                "load": "middle",
                "seed": seed,
                "algorithm": "Random",
                "throughput": 1.0,
                "qpr_finite_only": 2.0,
                "qpr_zero_completed_as_zero": 2.0,
            }
            for seed in SEEDS
        ]
        rows = _random_differences(candidate, baselines)
        self.assertFalse(any(row["any_primary_metric_differs"] for row in rows))
        candidate[0]["throughput"] = 1.1
        rows = _random_differences(candidate, baselines)
        self.assertTrue(rows[0]["any_primary_metric_differs"])

    def test_reference_catalog_accepts_exact_twenty_seed_product(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dependencies = []
            entries = {}
            for index, seed in enumerate(SEEDS, start=1):
                key = f"reference-{seed}"
                table = root / f"table-{index}.jsonl"
                receipt = root / f"receipt-{index}.json"
                table.write_bytes(f"{seed}\n".encode("utf-8"))
                receipt.write_bytes(f"receipt-{seed}\n".encode("utf-8"))
                dependencies.append({"key": key})
                entries[key] = {
                    "path": str(table),
                    "sha256": file_hash(table),
                    "receipt_path": str(receipt),
                    "receipt_sha256": file_hash(receipt),
                }
            catalog = {"entries": entries}
            catalog["catalog_hash"] = object_hash(catalog)
            catalog_path = root / "catalog.json"
            write_json_atomic(catalog_path, catalog)

            evidence = _validate_reference_catalog(
                {"reference_build_dependencies": dependencies},
                catalog_path,
                expected_entry_count=20,
            )
            self.assertEqual(evidence["entry_count"], 20)


if __name__ == "__main__":
    unittest.main()
