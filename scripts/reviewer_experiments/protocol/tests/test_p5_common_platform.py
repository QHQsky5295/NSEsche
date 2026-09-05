from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.p5_common_platform import (
    P5_ACTIVE_REQUEST_LIMIT,
    P5_ADMISSION,
    P5_LOADS,
    P5_SIMULATION,
    build_p5_common_platform_manifest,
    write_p5_common_platform_manifest,
)
from scripts.reviewer_experiments.protocol.qc import _validate_nse_summary
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_METHODS,
    P5_COMMON_PLATFORM_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import file_hash
from scripts.reviewer_experiments.protocol.util import write_json_atomic
from scripts.reviewer_experiments.protocol.tests.test_protocol import _valid_result


class P5CommonPlatformProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.binary = Path(self.temporary.name) / "serverless_sim.exe"
        self.binary.write_bytes(b"p5-common-platform-test-binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_p5_common_platform_manifest(self.binary, "a" * 40)

    def _p5_summary_fixture(self) -> tuple[dict, dict]:
        manifest = self._manifest()
        run = copy.deepcopy(manifest["runs"][1])
        run["workload_tape"]["event_count"] = 10
        fixed_run = copy.deepcopy(run)
        fixed_run["simulation"]["expected_final_frame"] = 1_000
        fixed_run["simulation"]["expected_frame_count"] = 1_001
        summary = _valid_result(fixed_run)
        summary.update(
            {
                "final_frame": 1_000,
                "frames_recorded": 1_001,
                "arrivals": 10,
                "completed": 10,
                "completion_ratio": 1.0,
                "censored": 0,
                "censoring_ratio": 0.0,
                "throughput_requests_per_second": 10.0,
                "paper_throughput_requests_per_ms": 0.01,
                "cohort_clearance_throughput_requests_per_ms": 0.01,
                "qpr": 0.05,
                "qpr_definition": "paper_throughput_requests_per_ms/(drained_arrival_cohort.latency_ms.mean*simulator_internal_cost_per_completed_request)",
                "simulator_internal_cost_per_completed_request": 0.1,
                "queue_semantics": "external_fcfs_bounded_active_dag_plus_node_task_queue",
            }
        )
        summary["fixed_observation_window"].update(
            {
                "arrivals": 10,
                "completed": 10,
                "completion_ratio": 1.0,
                "throughput_requests_per_second": 10.0,
            }
        )
        summary["drained_arrival_cohort"].update(
            {
                "drain_end_frame": 1_000,
                "drain_duration_after_arrivals_ms": 0,
                "arrivals": 10,
                "completed": 10,
                "completion_ratio": 1.0,
            }
        )
        summary["admission"] = {
            "enabled": True,
            "policy": "fcfs_capacity",
            "arrivals": 10,
            "admitted": 10,
            "waiting": 0,
            "active": 0,
            "completed": 10,
            "censored": 0,
            "active_request_limit": 100,
            "queue_peak": 0,
            "queue_area_request_frames": 0,
            "wait_ms": {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0},
            "admissions_recorded": 10,
            "tape_event_count": 10,
            "tape_static_cpu_work": 25_000.0,
            "cluster_cpu_per_frame": 100.0,
            "static_path_allowance_frames": 0,
            "minimum_drain_frames": 1_000,
            "drain_cpu_work_multiplier": 4.0,
            "max_drain_frames": 1_000,
            "hard_end_frame": 2_000,
            "terminal_reason": "cohort_drained",
        }
        return run, summary

    def test_exact_load_seed_method_product_and_order(self) -> None:
        manifest = self._manifest()
        self.assertEqual(len(manifest["runs"]), 90)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 90)
        observed = [
            (run["workload"]["request_freq"], run["seed"], run["method"])
            for run in manifest["runs"]
        ]
        expected = [
            (load, seed, method)
            for load in P5_LOADS
            for seed in P5_COMMON_PLATFORM_SEEDS
            for method in FORMAL_E1_METHODS
        ]
        self.assertEqual(observed, expected)

    def test_every_pair_shares_one_tape_and_every_method_has_one_reference(
        self,
    ) -> None:
        manifest = self._manifest()
        for load in P5_LOADS:
            for seed in P5_COMMON_PLATFORM_SEEDS:
                rows = [
                    run
                    for run in manifest["runs"]
                    if run["workload"]["request_freq"] == load and run["seed"] == seed
                ]
                self.assertEqual(len(rows), 10)
                self.assertEqual(len({row["workload_tape"]["key"] for row in rows}), 1)
                self.assertEqual(len({row["workload_spec_hash"] for row in rows}), 1)
                self.assertEqual(
                    len({row["reference_dependency"]["key"] for row in rows}), 10
                )

    def test_common_admission_dynamic_phase_and_nash_parameters_are_exact(self) -> None:
        manifest = self._manifest()
        for run in manifest["runs"]:
            experiment = run["simulator_experiment"]
            self.assertEqual(run["simulation"], P5_SIMULATION)
            self.assertEqual(
                {
                    key: run["simulation"][key]
                    for key in ("dag_type", "cold_start", "fn_type")
                },
                {"dag_type": "mix", "cold_start": "high", "fn_type": "cpu"},
            )
            self.assertEqual(experiment["protocol_version"], "reviewer-v4")
            self.assertEqual(experiment["admission"], P5_ADMISSION)
            self.assertEqual(experiment["reference"]["mode"], "offline_required")
            if run["method"] == "sche_nash":
                expected = (
                    {"price_feedback_rate": 0.6, "quality_weight": 0.5}
                    if run["workload"]["request_freq"] == "low"
                    else {"price_feedback_rate": 0.5, "quality_weight": 0.6}
                )
                self.assertEqual(run["metadata"]["nash_parameters"], expected)
                self.assertEqual(
                    experiment["nash"]["operational_refinement"], "ready_order"
                )

        marker = manifest["p5_common_platform_pilot"]
        self.assertEqual(
            marker["admission"]["expected_active_limit"], P5_ACTIVE_REQUEST_LIMIT
        )
        self.assertTrue(marker["gate"]["result_blindness"])
        self.assertTrue(
            manifest["qc"]["p5_common_platform"][
                "scientific_zero_or_low_completion_is_qc_valid"
            ]
        )

    def test_manifest_rejects_seed_order_cap_admission_and_result_policy_drift(
        self,
    ) -> None:
        mutations = []
        bad = self._manifest()
        bad["runs"][0], bad["runs"][1] = bad["runs"][1], bad["runs"][0]
        mutations.append(bad)
        bad = self._manifest()
        bad["runs"][0]["simulator_experiment"]["admission"][
            "minimum_drain_frames"
        ] = 999
        mutations.append(bad)
        bad = self._manifest()
        bad["p5_common_platform_pilot"]["admission"]["expected_active_limit"] = 101
        mutations.append(bad)
        bad = self._manifest()
        bad["qc"]["p5_common_platform"][
            "scientific_zero_or_low_completion_is_qc_valid"
        ] = False
        mutations.append(bad)
        bad = self._manifest()
        bad["p5_common_platform_pilot"]["analysis_contract"][
            "gate_condition_count"
        ] = 11
        mutations.append(bad)
        bad = self._manifest()
        bad["p5_common_platform_pilot"]["preresult_addendum"][
            "faasrank_retraining_or_reselection"
        ] = True
        mutations.append(bad)
        bad = self._manifest()
        bad["all_faasrank_models_bound"] = True
        mutations.append(bad)
        bad = self._manifest()
        bad["all_references_bound"] = True
        mutations.append(bad)
        for field, value in (
            ("dag_type", "single"),
            ("cold_start", "low"),
            ("fn_type", "data"),
        ):
            bad = self._manifest()
            bad["runs"][0]["simulation"][field] = value
            mutations.append(bad)
        for index, manifest in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ProtocolValidationError):
                    validate_manifest(manifest, check_hash=False)

    def test_static_schema_and_write_are_immutable(self) -> None:
        import jsonschema

        manifest = self._manifest()
        schema_path = Path(__file__).parents[1] / "manifest.schema.json"
        jsonschema.validate(
            manifest, json.loads(schema_path.read_text(encoding="utf-8"))
        )
        output = Path(self.temporary.name) / "p5.manifest.json"
        written = write_p5_common_platform_manifest(output, self.binary, "a" * 40)
        self.assertEqual(
            written["p5_common_platform_pilot"]["runtime_binary"]["sha256"],
            file_hash(self.binary),
        )
        with self.assertRaises(ProtocolValidationError):
            write_p5_common_platform_manifest(output, self.binary, "a" * 40)

    def test_p5_dynamic_summary_metric_and_conservation_contract_passes(self) -> None:
        run, summary = self._p5_summary_fixture()
        path = Path(self.temporary.name) / "summary.json"
        write_json_atomic(path, summary)
        issues = []
        _validate_nse_summary(path, run, self._manifest()["qc"], issues)
        self.assertEqual(issues, [])

    def test_p5_dynamic_summary_queue_semantics_are_version_aware_and_fail_closed(
        self,
    ) -> None:
        run, summary = self._p5_summary_fixture()
        summary["queue_semantics"] = "unbounded_wait_by_design"
        path = Path(self.temporary.name) / "summary.json"
        write_json_atomic(path, summary)
        issues = []
        _validate_nse_summary(path, run, self._manifest()["qc"], issues)
        queue_issues = [
            issue for issue in issues if issue.code == "queue_semantics_mismatch"
        ]
        self.assertEqual(len(queue_issues), 1)
        self.assertEqual(
            queue_issues[0].details["expected"],
            "external_fcfs_bounded_active_dag_plus_node_task_queue",
        )

        summary[
            "queue_semantics"
        ] = "external_fcfs_bounded_active_dag_plus_node_task_queue"
        summary["admission_drop"] = 1
        write_json_atomic(path, summary)
        issues = []
        _validate_nse_summary(path, run, self._manifest()["qc"], issues)
        self.assertIn("counter_semantics_mismatch", {issue.code for issue in issues})

    def test_p5_dynamic_summary_rejects_qpr_and_admission_drift(self) -> None:
        run, summary = self._p5_summary_fixture()
        summary["qpr"] = 0.051
        summary["admission"]["waiting"] = 1
        path = Path(self.temporary.name) / "summary.json"
        write_json_atomic(path, summary)
        issues = []
        _validate_nse_summary(path, run, self._manifest()["qc"], issues)
        codes = {issue.code for issue in issues}
        self.assertIn("p5_metric_identity", codes)
        self.assertIn("admission_conservation", codes)


if __name__ == "__main__":
    unittest.main()
