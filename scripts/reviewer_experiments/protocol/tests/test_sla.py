from __future__ import annotations

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.reviewer_experiments.protocol.cli import main
from scripts.reviewer_experiments.protocol.matrix import (
    bind_sla_targets,
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.sla import (
    SlaFreezeError,
    freeze_sla_targets,
    inspect_pilot_metric,
    load_frozen_sla_targets,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


def _pilot(
    *,
    pilot_id: str = "isolated-E01",
    class_assignment: str = "all_latency",
    latency_p95_ms: float = 12.0,
    sustainable_throughput_rps: float = 2000.0,
    cost_per_request: float = 0.004,
    seed: str | None = None,
) -> dict:
    document = {
        "schema_version": "NSE_ISOLATED_SLA_PILOT_V1",
        "pilot_id": pilot_id,
        "pilot_scope": "isolated",
        "class_assignment": class_assignment,
        "completed": True,
        "provenance": {
            "config_sha256": "1" * 64,
            "workload_tape_sha256": "2" * 64,
        },
        "metrics": {
            "latency_p95_ms": latency_p95_ms,
            "sustainable_throughput_rps": sustainable_throughput_rps,
            "cost_per_request": cost_per_request,
        },
    }
    if seed is not None:
        document["provenance"]["seed"] = seed
    return document


def _write_role_pilots(
    root: Path,
    *,
    latency_p95_ms: float = 12.0,
    sustainable_throughput_rps: float = 2000.0,
    cost_per_request: float = 0.004,
) -> dict[str, Path]:
    paths = {
        "latency": root / "latency.json",
        "throughput": root / "throughput.json",
        "cost": root / "cost.json",
    }
    write_json_atomic(
        paths["latency"],
        _pilot(
            pilot_id="latency-isolated-E01",
            class_assignment="all_latency",
            latency_p95_ms=latency_p95_ms,
        ),
    )
    write_json_atomic(
        paths["throughput"],
        _pilot(
            pilot_id="throughput-isolated-E01",
            class_assignment="all_throughput",
            sustainable_throughput_rps=sustainable_throughput_rps,
        ),
    )
    write_json_atomic(
        paths["cost"],
        _pilot(
            pilot_id="cost-isolated-E01",
            class_assignment="all_cost",
            cost_per_request=cost_per_request,
        ),
    )
    return paths


class SlaFreezeTests(unittest.TestCase):
    def test_three_seed_conservative_envelope_is_frozen_without_rounding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            role_paths = {role: [] for role in ("latency", "throughput", "cost")}
            values = {
                "E01": (222.0, 480.0, 1.2),
                "E02": (289.0, 477.0, 3.24),
                "E03": (236.0, 975.0, 1.62),
            }
            for seed, (latency, throughput, cost) in values.items():
                for role, assignment in (
                    ("latency", "all_latency"),
                    ("throughput", "all_throughput"),
                    ("cost", "all_cost"),
                ):
                    path = root / f"{seed}-{role}.json"
                    write_json_atomic(
                        path,
                        _pilot(
                            pilot_id=f"{seed}-{role}",
                            class_assignment=assignment,
                            latency_p95_ms=latency,
                            sustainable_throughput_rps=throughput,
                            cost_per_request=cost,
                            seed=seed,
                        ),
                    )
                    role_paths[role].append(path)

            frozen = freeze_sla_targets(
                root / "frozen.json",
                latency_pilot_path=role_paths["latency"],
                throughput_pilot_path=role_paths["throughput"],
                cost_pilot_path=role_paths["cost"],
            )

            self.assertEqual(frozen["targets"]["latency_deadline_ms"], 433.5)
            self.assertEqual(frozen["targets"]["throughput_target_rps"], 429.3)
            self.assertAlmostEqual(
                frozen["targets"]["cost_budget_per_request"], 4.05
            )
            self.assertEqual(frozen["seed_aggregation"]["pilot_seed_count"], 3)
            self.assertEqual(
                frozen["sources"]["latency_p95_ms"]["seeds"],
                ["E01", "E02", "E03"],
            )
            self.assertEqual(
                frozen["sources"]["sustainable_throughput_rps"][
                    "aggregation"
                ],
                "minimum_across_three_fixed_pilot_seeds",
            )
            loaded = load_frozen_sla_targets(root / "frozen.json")
            self.assertEqual(loaded.targets, frozen["targets"])

    def test_three_pilots_freeze_exact_declared_formulas_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = _write_role_pilots(root)
            output_path = root / "frozen.json"

            frozen = freeze_sla_targets(
                output_path,
                latency_pilot_path=paths["latency"],
                throughput_pilot_path=paths["throughput"],
                cost_pilot_path=paths["cost"],
            )

            self.assertEqual(
                frozen["targets"],
                {
                    "latency_deadline_ms": 18.0,
                    "throughput_target_rps": 1800.0,
                    "cost_budget_per_request": 0.005,
                },
            )
            self.assertEqual(frozen["targets_sha256"], object_hash(frozen["targets"]))
            self.assertEqual(
                frozen["sources"]["latency_p95_ms"]["sha256"],
                file_hash(paths["latency"]),
            )
            self.assertEqual(
                frozen["sources"]["sustainable_throughput_rps"]["json_path"],
                "metrics.sustainable_throughput_rps",
            )
            self.assertEqual(
                frozen["sources"]["cost_per_request"]["provenance"],
                _pilot(class_assignment="all_cost")["provenance"],
            )
            self.assertEqual(
                frozen["sources"]["latency_p95_ms"]["class_assignment"],
                "all_latency",
            )
            self.assertEqual(
                frozen["sources"]["sustainable_throughput_rps"]["class_assignment"],
                "all_throughput",
            )
            self.assertEqual(
                frozen["sources"]["cost_per_request"]["class_assignment"],
                "all_cost",
            )
            without_document_hash = copy.deepcopy(frozen)
            document_hash = without_document_hash.pop("document_sha256")
            self.assertEqual(document_hash, object_hash(without_document_hash))
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8")), frozen
            )
            loaded = load_frozen_sla_targets(output_path)
            self.assertEqual(loaded.targets, frozen["targets"])
            self.assertEqual(loaded.artifact_sha256, file_hash(output_path))
            self.assertEqual(loaded.document_sha256, frozen["document_sha256"])

    def test_three_role_specific_pilots_are_bound_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {
                "latency": root / "latency.json",
                "throughput": root / "throughput.json",
                "cost": root / "cost.json",
            }
            write_json_atomic(
                paths["latency"], _pilot(pilot_id="lat", latency_p95_ms=8.0)
            )
            write_json_atomic(
                paths["throughput"],
                _pilot(
                    pilot_id="capacity",
                    class_assignment="all_throughput",
                    sustainable_throughput_rps=3000.0,
                ),
            )
            write_json_atomic(
                paths["cost"],
                _pilot(
                    pilot_id="cost",
                    class_assignment="all_cost",
                    cost_per_request=0.02,
                ),
            )

            frozen = freeze_sla_targets(
                root / "frozen.json",
                latency_pilot_path=paths["latency"],
                throughput_pilot_path=paths["throughput"],
                cost_pilot_path=paths["cost"],
            )

            self.assertEqual(frozen["targets"]["latency_deadline_ms"], 12.0)
            self.assertEqual(frozen["targets"]["throughput_target_rps"], 2700.0)
            self.assertEqual(frozen["targets"]["cost_budget_per_request"], 0.025)
            self.assertEqual(frozen["sources"]["latency_p95_ms"]["artifact_id"], "lat")
            self.assertEqual(
                frozen["sources"]["sustainable_throughput_rps"]["artifact_id"],
                "capacity",
            )
            self.assertEqual(
                frozen["sources"]["cost_per_request"]["artifact_id"], "cost"
            )

    def test_frozen_targets_bind_only_balanced_qos_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = _write_role_pilots(root)
            artifact = root / "frozen.json"
            freeze_sla_targets(
                artifact,
                latency_pilot_path=paths["latency"],
                throughput_pilot_path=paths["throughput"],
                cost_pilot_path=paths["cost"],
            )
            bound = bind_sla_targets(
                build_manifest(load_protocol_config(), "initial"),
                artifact,
                manifest_artifact_path=str(artifact.resolve()),
            )
            validate_manifest(bound)
            self.assertTrue(bound["all_sla_targets_bound"])
            balanced = [
                run
                for run in bound["runs"]
                if run["workload"]["qos_profile"] == "balanced"
            ]
            mixed = [
                run
                for run in bound["runs"]
                if run["workload"]["qos_profile"] == "mixed"
            ]
            self.assertTrue(balanced)
            self.assertTrue(all("sla_targets" in run for run in balanced))
            self.assertEqual(
                {
                    run["simulator_experiment"]["qos"]["latency_deadline_ms"]
                    for run in balanced
                },
                {18.0},
            )
            self.assertTrue(
                all(
                    run["simulator_experiment"]["qos"]["latency_deadline_ms"] is None
                    for run in mixed
                )
            )

    def test_standard_summary_requires_explicit_sustainable_throughput_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            summary_path = root / "summary.json"
            summary = {
                "schema": "NSE_SUMMARY_V1",
                "run_id": "isolated-capacity-E01",
                "run_complete": True,
                "latency_ms": {"p95": 5.0},
                "throughput_requests_per_second": 1000.0,
                "simulator_internal_cost_per_completed_request": 0.5,
            }
            write_json_atomic(summary_path, summary)
            write_json_atomic(
                root / "environment.json",
                {
                    "schema": "NSE_ENVIRONMENT_V1",
                    "run_id": "isolated-capacity-E01",
                    "config": {
                        "experiment": {"qos": {"class_assignment": "all_throughput"}}
                    },
                },
            )
            with self.assertRaisesRegex(SlaFreezeError, "ordinary completed rate"):
                inspect_pilot_metric(summary_path, "sustainable_throughput_rps")

            summary["provenance"] = {"throughput_is_sustainable": True}
            write_json_atomic(summary_path, summary)
            metric = inspect_pilot_metric(summary_path, "sustainable_throughput_rps")
            self.assertEqual(metric.value, 1000.0)
            self.assertEqual(metric.json_path, "throughput_requests_per_second")
            self.assertEqual(
                metric.class_assignment_evidence[0]["kind"], "sibling_environment"
            )

    def test_null_nonfinite_zero_incomplete_and_nonisolated_are_rejected(self) -> None:
        cases = {
            "null": ("latency_p95_ms", None),
            "nan": ("latency_p95_ms", float("nan")),
            "infinity": ("sustainable_throughput_rps", float("inf")),
            "zero": ("cost_per_request", 0.0),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, (role, value) in cases.items():
                with self.subTest(name=name):
                    assignment = {
                        "latency_p95_ms": "all_latency",
                        "sustainable_throughput_rps": "all_throughput",
                        "cost_per_request": "all_cost",
                    }[role]
                    pilot = _pilot(class_assignment=assignment)
                    pilot["metrics"][role] = value
                    path = root / f"{name}.json"
                    path.write_text(json.dumps(pilot, allow_nan=True), encoding="utf-8")
                    with self.assertRaises(SlaFreezeError):
                        inspect_pilot_metric(path, role)

            incomplete = _pilot()
            incomplete["completed"] = False
            incomplete_path = root / "incomplete.json"
            write_json_atomic(incomplete_path, incomplete)
            with self.assertRaisesRegex(SlaFreezeError, "completed=true"):
                inspect_pilot_metric(incomplete_path, "latency_p95_ms")

            nonisolated = _pilot()
            nonisolated["pilot_scope"] = "formal_balanced"
            nonisolated_path = root / "nonisolated.json"
            write_json_atomic(nonisolated_path, nonisolated)
            with self.assertRaisesRegex(SlaFreezeError, "conflicting pilot scope"):
                inspect_pilot_metric(nonisolated_path, "latency_p95_ms")

            overflow = _pilot(latency_p95_ms=1.7e308)
            overflow_path = root / "overflow.json"
            write_json_atomic(overflow_path, overflow)
            paths = _write_role_pilots(root)
            with self.assertRaisesRegex(SlaFreezeError, "derived target"):
                freeze_sla_targets(
                    root / "overflow-targets.json",
                    latency_pilot_path=overflow_path,
                    throughput_pilot_path=paths["throughput"],
                    cost_pilot_path=paths["cost"],
                )

    def test_nonstandard_constants_and_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nonfinite_path = root / "nonfinite.json"
            nonfinite_path.write_text(
                '{"schema_version":"NSE_ISOLATED_SLA_PILOT_V1",'
                '"pilot_id":"x","pilot_scope":"isolated",'
                '"class_assignment":"all_latency","completed":true,'
                '"metrics":{"latency_p95_ms":NaN}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SlaFreezeError, "non-standard/nonfinite"):
                inspect_pilot_metric(nonfinite_path, "latency_p95_ms")

            duplicate_path = root / "duplicate.json"
            duplicate_path.write_text(
                '{"schema_version":"NSE_ISOLATED_SLA_PILOT_V1",'
                '"pilot_id":"x","pilot_id":"y","pilot_scope":"isolated",'
                '"class_assignment":"all_latency","completed":true,'
                '"metrics":{"latency_p95_ms":1.0}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SlaFreezeError, "duplicate JSON key"):
                inspect_pilot_metric(duplicate_path, "latency_p95_ms")

    def test_existing_target_requires_matching_optimistic_lock_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = _write_role_pilots(root)
            output_path = root / "frozen.json"
            freeze_sla_targets(
                output_path,
                latency_pilot_path=paths["latency"],
                throughput_pilot_path=paths["throughput"],
                cost_pilot_path=paths["cost"],
            )
            original_bytes = output_path.read_bytes()

            write_json_atomic(paths["latency"], _pilot(latency_p95_ms=20.0))
            with self.assertRaisesRegex(SlaFreezeError, "refusing to overwrite"):
                freeze_sla_targets(
                    output_path,
                    latency_pilot_path=paths["latency"],
                    throughput_pilot_path=paths["throughput"],
                    cost_pilot_path=paths["cost"],
                )
            self.assertEqual(output_path.read_bytes(), original_bytes)

            with self.assertRaisesRegex(SlaFreezeError, "hash mismatch"):
                freeze_sla_targets(
                    output_path,
                    latency_pilot_path=paths["latency"],
                    throughput_pilot_path=paths["throughput"],
                    cost_pilot_path=paths["cost"],
                    replace_existing_sha256="0" * 64,
                )
            self.assertEqual(output_path.read_bytes(), original_bytes)

            frozen = freeze_sla_targets(
                output_path,
                latency_pilot_path=paths["latency"],
                throughput_pilot_path=paths["throughput"],
                cost_pilot_path=paths["cost"],
                replace_existing_sha256=hashlib.sha256(original_bytes).hexdigest(),
            )
            self.assertEqual(frozen["targets"]["latency_deadline_ms"], 30.0)

    def test_missing_or_wrong_class_assignment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pilot_path = root / "pilot.json"
            pilot = _pilot(class_assignment="balanced")
            write_json_atomic(pilot_path, pilot)
            with self.assertRaisesRegex(SlaFreezeError, "must come from all_latency"):
                inspect_pilot_metric(pilot_path, "latency_p95_ms")

            pilot.pop("class_assignment")
            write_json_atomic(pilot_path, pilot)
            with self.assertRaisesRegex(SlaFreezeError, "no QoS class_assignment"):
                inspect_pilot_metric(pilot_path, "latency_p95_ms")

    def test_cli_freeze_sla(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = _write_role_pilots(root)
            output_path = root / "frozen.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "freeze-sla",
                        str(output_path),
                        "--latency-pilot",
                        str(paths["latency"]),
                        "--throughput-pilot",
                        str(paths["throughput"]),
                        "--cost-pilot",
                        str(paths["cost"]),
                    ]
                )
            self.assertEqual(exit_code, 0)
            response = json.loads(stdout.getvalue())
            self.assertEqual(response["status"], "frozen")
            self.assertTrue(output_path.is_file())


if __name__ == "__main__":
    unittest.main()
