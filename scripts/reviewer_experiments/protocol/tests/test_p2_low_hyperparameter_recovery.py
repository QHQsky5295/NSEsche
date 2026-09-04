from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.p2_low_hyperparameter_recovery import (
    P2_LOW_CONTROL,
    P2_LOW_OPERATIONAL_REFINEMENT,
    P2_LOW_SETTINGS,
    build_p2_low_hyperparameter_recovery_manifest,
    write_p2_low_hyperparameter_recovery_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    G18_OVERFLOW_SOFT_CAP_VALVE_SEEDS,
    P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import file_hash


class P2LowHyperparameterRecoveryProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.binary = Path(self.temporary.name) / "serverless_sim.exe"
        self.binary.write_bytes(b"p2-low-hyperparameter-test-binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_p2_low_hyperparameter_recovery_manifest(self.binary, "a" * 40)

    def test_exact_seed_major_five_by_five_product(self) -> None:
        manifest = self._manifest()
        self.assertEqual(len(manifest["runs"]), 25)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 25)
        observed = [
            (run["seed"], run["metadata"]["parameter_setting"])
            for run in manifest["runs"]
        ]
        expected = [
            (seed, setting[0])
            for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS
            for setting in P2_LOW_SETTINGS
        ]
        self.assertEqual(observed, expected)

    def test_settings_and_runtime_configuration_are_exact(self) -> None:
        manifest = self._manifest()
        expected = {
            label: (price, quality) for label, price, quality in P2_LOW_SETTINGS
        }
        for run in manifest["runs"]:
            label = run["metadata"]["parameter_setting"]
            price, quality = expected[label]
            nash = run["simulator_experiment"]["nash"]
            self.assertEqual(nash["price_feedback_rate"], price)
            self.assertEqual(nash["quality_weight"], quality)
            self.assertEqual(
                nash["operational_refinement"], P2_LOW_OPERATIONAL_REFINEMENT
            )
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_REFINEMENT"],
                P2_LOW_OPERATIONAL_REFINEMENT,
            )

    def test_all_settings_share_one_tape_per_seed_and_distinct_references(self) -> None:
        manifest = self._manifest()
        for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS:
            rows = [run for run in manifest["runs"] if run["seed"] == seed]
            self.assertEqual(len(rows), 5)
            self.assertEqual(len({run["workload_tape"]["key"] for run in rows}), 1)
            self.assertEqual(len({run["workload_spec_hash"] for run in rows}), 1)
            self.assertEqual(
                len({run["reference_dependency"]["key"] for run in rows}), 5
            )

    def test_gate_and_selection_are_frozen(self) -> None:
        marker = self._manifest()["p2_low_hyperparameter_recovery_screen"]
        self.assertEqual(marker["control_setting"], P2_LOW_CONTROL)
        self.assertEqual(marker["gate"]["mean_throughput_ratio_at_least"], 1.015)
        self.assertEqual(marker["gate"]["mean_qpr_ratio_at_least"], 1.11)
        self.assertEqual(marker["gate"]["paired_joint_wins_at_least"], 3)
        self.assertEqual(marker["gate"]["paired_joint_nonlosses_at_least"], 4)
        self.assertEqual(
            marker["selection_rule"]["final_label_order"],
            ["r0_minus", "r0_plus", "wq_minus", "wq_plus"],
        )
        self.assertFalse(marker["strong_baselines_in_screen"])

    def test_manifest_rejects_setting_gate_seed_and_order_drift(self) -> None:
        mutations = []
        bad = self._manifest()
        bad["p2_low_hyperparameter_recovery_screen"]["settings"][1][
            "price_feedback_rate"
        ] = 0.54
        mutations.append(bad)
        bad = self._manifest()
        bad["p2_low_hyperparameter_recovery_screen"]["gate"][
            "mean_qpr_ratio_at_least"
        ] = 1.0
        mutations.append(bad)
        bad = self._manifest()
        bad["fixed_seed_bank"]["selected_seeds"][-1] = "D126"
        mutations.append(bad)
        bad = self._manifest()
        bad["runs"][0], bad["runs"][1] = bad["runs"][1], bad["runs"][0]
        mutations.append(bad)
        for index, manifest in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ProtocolValidationError):
                    validate_manifest(manifest, check_hash=False)

    def test_static_json_schema_and_prior_bank_disjointness(self) -> None:
        import jsonschema

        manifest = self._manifest()
        schema_path = Path(__file__).parents[1] / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)
        self.assertTrue(
            set(P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS).isdisjoint(
                G18_OVERFLOW_SOFT_CAP_VALVE_SEEDS
            )
        )

    def test_runtime_receipt_and_write_are_immutable(self) -> None:
        output = Path(self.temporary.name) / "p2-low.manifest.json"
        manifest = write_p2_low_hyperparameter_recovery_manifest(
            output, self.binary, "a" * 40
        )
        receipt = manifest["p2_low_hyperparameter_recovery_screen"]["runtime_binary"]
        self.assertEqual(receipt["sha256"], file_hash(self.binary))
        self.assertEqual(receipt["bytes"], self.binary.stat().st_size)
        with self.assertRaises(ProtocolValidationError):
            write_p2_low_hyperparameter_recovery_manifest(output, self.binary, "a" * 40)


if __name__ == "__main__":
    unittest.main()
