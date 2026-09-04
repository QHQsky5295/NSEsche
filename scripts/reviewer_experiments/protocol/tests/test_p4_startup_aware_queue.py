from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.p4_startup_aware_queue import (
    P4_CANDIDATE,
    P4_CONTROL,
    P4_OPERATIONAL_REFINEMENT,
    P4_SETTINGS,
    build_p4_startup_aware_queue_manifest,
    write_p4_startup_aware_queue_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS,
    P4_STARTUP_AWARE_QUEUE_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import file_hash


class P4StartupAwareQueueProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.binary = Path(self.temporary.name) / "serverless_sim.exe"
        self.binary.write_bytes(b"p4-startup-aware-queue-test-binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_p4_startup_aware_queue_manifest(self.binary, "a" * 40)

    def test_exact_seed_major_two_by_five_product(self) -> None:
        manifest = self._manifest()
        self.assertEqual(len(manifest["runs"]), 10)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 10)
        observed = [
            (run["seed"], run["metadata"]["queue_pressure_setting"])
            for run in manifest["runs"]
        ]
        expected = [
            (seed, setting[0])
            for seed in P4_STARTUP_AWARE_QUEUE_SEEDS
            for setting in P4_SETTINGS
        ]
        self.assertEqual(observed, expected)

    def test_settings_and_runtime_configuration_are_exact(self) -> None:
        manifest = self._manifest()
        expected = {label: semantics for label, semantics, _ in P4_SETTINGS}
        for run in manifest["runs"]:
            label = run["metadata"]["queue_pressure_setting"]
            nash = run["simulator_experiment"]["nash"]
            self.assertEqual(nash["price_feedback_rate"], 0.6)
            self.assertEqual(nash["quality_weight"], 0.5)
            self.assertEqual(nash["operational_refinement"], P4_OPERATIONAL_REFINEMENT)
            self.assertEqual(nash["queue_pressure_semantics"], expected[label])
            self.assertEqual(
                run["environment"]["NASH_QUEUE_PRESSURE_SEMANTICS"],
                expected[label],
            )

    def test_pairing_and_reference_identity_are_exact(self) -> None:
        manifest = self._manifest()
        for seed in P4_STARTUP_AWARE_QUEUE_SEEDS:
            rows = [run for run in manifest["runs"] if run["seed"] == seed]
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({run["workload_tape"]["key"] for run in rows}), 1)
            self.assertEqual(len({run["workload_spec_hash"] for run in rows}), 1)
            self.assertEqual(
                len({run["reference_dependency"]["key"] for run in rows}), 2
            )

    def test_gate_and_stopping_rule_are_frozen(self) -> None:
        marker = self._manifest()["p4_startup_aware_queue_development"]
        self.assertEqual(marker["control_setting"], P4_CONTROL)
        self.assertEqual(marker["candidate_setting"], P4_CANDIDATE)
        self.assertEqual(marker["gate"]["activation_seed_count_at_least"], 4)
        self.assertEqual(marker["gate"]["assignment_change_seed_count_at_least"], 4)
        self.assertEqual(marker["gate"]["mean_throughput_ratio_at_least"], 1.015)
        self.assertEqual(marker["gate"]["mean_qpr_ratio_at_least"], 1.11)
        self.assertEqual(marker["reference_key_schema_version"], 15)
        self.assertFalse(marker["strong_baselines_in_screen"])

    def test_manifest_rejects_semantics_gate_seed_and_order_drift(self) -> None:
        mutations = []
        bad = self._manifest()
        bad["runs"][1]["simulator_experiment"]["nash"][
            "queue_pressure_semantics"
        ] = "execution_ready"
        mutations.append(bad)
        bad = self._manifest()
        bad["p4_startup_aware_queue_development"]["gate"][
            "mean_qpr_ratio_at_least"
        ] = 1.0
        mutations.append(bad)
        bad = self._manifest()
        bad["fixed_seed_bank"]["selected_seeds"][-1] = "D131"
        mutations.append(bad)
        bad = self._manifest()
        bad["runs"][0], bad["runs"][1] = bad["runs"][1], bad["runs"][0]
        mutations.append(bad)
        for index, manifest in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ProtocolValidationError):
                    validate_manifest(manifest, check_hash=False)

    def test_static_schema_and_prior_bank_disjointness(self) -> None:
        import jsonschema

        manifest = self._manifest()
        schema_path = Path(__file__).parents[1] / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)
        self.assertTrue(
            set(P4_STARTUP_AWARE_QUEUE_SEEDS).isdisjoint(
                P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS
            )
        )

    def test_runtime_receipt_and_write_are_immutable(self) -> None:
        output = Path(self.temporary.name) / "p4.manifest.json"
        manifest = write_p4_startup_aware_queue_manifest(
            output, self.binary, "a" * 40
        )
        receipt = manifest["p4_startup_aware_queue_development"]["runtime_binary"]
        self.assertEqual(receipt["sha256"], file_hash(self.binary))
        self.assertEqual(receipt["bytes"], self.binary.stat().st_size)
        with self.assertRaises(ProtocolValidationError):
            write_p4_startup_aware_queue_manifest(output, self.binary, "a" * 40)


if __name__ == "__main__":
    unittest.main()
