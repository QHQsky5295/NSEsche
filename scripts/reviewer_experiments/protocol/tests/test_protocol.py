from __future__ import annotations

import copy
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.faasrank_model import (
    create_frozen_faasrank_model,
)
from scripts.reviewer_experiments.protocol.matrix import (
    bind_faasrank_model,
    bind_tape_catalog,
    build_manifest,
    expand_cells,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.qc import (
    evaluate_attempt,
    technical_failure_signature,
)
from scripts.reviewer_experiments.protocol.runner import (
    ProtocolRunError,
    ProtocolRunner,
)
from scripts.reviewer_experiments.protocol.schema import (
    ProtocolValidationError,
    validate_manifest,
    validate_protocol_config,
)
from scripts.reviewer_experiments.protocol.tape import (
    derive_burst_tape,
    derive_scaled_tape,
    inspect_tape,
    register_base_tape,
)
from scripts.reviewer_experiments.protocol.util import write_json_atomic


def _frozen_config() -> dict:
    return load_protocol_config()


def _qos_observations(run: dict) -> tuple[dict, dict]:
    enabled = run.get("simulator_experiment", {}).get("qos", {}).get("enabled")
    if enabled is True:
        task_template = {
            "arrived": 3,
            "completed": 2,
            "active": 1,
            "completion_ratio": 2.0 / 3.0,
        }
        classes = ("latency", "throughput", "cost")
    else:
        task_template = {
            "arrived": 10,
            "completed": 9,
            "active": 1,
            "completion_ratio": 0.9,
        }
        classes = ("shared",)
    tasks = {qos_class: copy.deepcopy(task_template) for qos_class in classes}
    costs = {
        qos_class: {
            "unit": "simulator_internal_units",
            "total": 0.2,
            "per_completed_function": 0.2 / tasks[qos_class]["completed"],
            "is_currency": False,
        }
        for qos_class in tasks
    }
    return tasks, costs


def _valid_result(run: dict) -> dict:
    qos_tasks, qos_costs = _qos_observations(run)
    return {
        "schema": "NSE_SUMMARY_V1",
        "run_id": run["run_id"],
        "protocol_version": run["simulator_experiment"]["protocol_version"],
        "run_complete": True,
        "final_frame": run["simulation"]["expected_final_frame"],
        "frames_recorded": run["simulation"]["expected_frame_count"],
        "frame_duration_ms": 1,
        "observation_time_ms": run["simulation"]["total_frame"],
        "arrivals": 10,
        "completed": 9,
        "completion_ratio": 0.9,
        "throughput_requests_per_second": 9.0
        * 1000.0
        / run["simulation"]["total_frame"],
        "latency_ms": {"mean": 2.0, "p50": 2.0, "p95": 2.0, "p99": 2.0},
        "fixed_observation_window": {
            "start_frame": 0,
            "end_frame": run["simulation"]["observation_horizon_frames"],
            "duration_ms": run["simulation"]["observation_horizon_frames"],
            "arrivals": 10,
            "completed": 9,
            "completion_ratio": 0.9,
            "throughput_requests_per_second": 9.0,
        },
        "drained_arrival_cohort": {
            "arrival_start_frame": 0,
            "arrival_end_frame": run["simulation"]["arrival_horizon_frames"],
            "drain_end_frame": run["simulation"]["total_frame"],
            "drain_duration_after_arrivals_ms": run["simulation"]["total_frame"]
            - run["simulation"]["arrival_horizon_frames"],
            "arrivals": 10,
            "completed": 9,
            "completion_ratio": 0.9,
            "latency_ms": {"mean": 2.0, "p50": 2.0, "p95": 2.0, "p99": 2.0},
        },
        "metric_definitions": {
            "frame_duration_ms": 1,
            "fixed_observation_window": {
                "arrival_cohort": "request arrival_frame is in [0, end_frame)",
                "completion_deadline": "request completion_frame is in [0, end_frame]",
                "throughput": "completed requests at or before end_frame divided by duration_ms",
                "throughput_unit": "requests/s",
            },
            "drained_arrival_cohort": {
                "cohort": "the fixed-observation-window arrival cohort",
                "completion_deadline": "request completion_frame is at or before drain_end_frame",
                "latency_population": "completed requests from that cohort by drain_end_frame",
                "latency_unit": "ms",
            },
            "legacy_top_level_fields": "preserved for compatibility; completed, completion_ratio, throughput_requests_per_second, and latency_ms retain final-run semantics with observation_time_ms as denominator",
        },
        "simulator_internal_cost_total": 1.0,
        "simulator_internal_cost_per_completed_request": 1.0 / 9.0,
        "queue_peak": 1,
        "queue_area_request_frames": run["simulation"]["expected_frame_count"],
        "node_cpu_mean": 1.0,
        "node_cpu_peak": 2.0,
        "node_memory_mean": 1.0,
        "node_memory_peak": 2.0,
        "node_cpu_utilization_mean": 0.1,
        "node_cpu_utilization_p95": 0.2,
        "node_cpu_utilization_peak": 0.3,
        "node_memory_utilization_mean": 0.1,
        "node_memory_utilization_p95": 0.2,
        "node_memory_utilization_peak": 0.3,
        "node_utilization_unit": "fraction_of_node_capacity",
        "node_utilization_definition": {
            "sampling": "one_sample_per_node_per_recorded_frame",
            "cpu_numerator": "node.cpu",
            "cpu_denominator": "node.rsc_limit.cpu",
            "memory_numerator": "node.unready_mem()",
            "memory_denominator": "node.rsc_limit.mem",
            "clipping": "none",
            "invalid_sample_policy": "exclude_non_finite_usage_or_capacity_negative_usage_or_non_positive_capacity",
            "cpu_valid_samples": run["cluster"]["node_count"]
            * run["simulation"]["expected_frame_count"],
            "cpu_invalid_samples": 0,
            "memory_valid_samples": run["cluster"]["node_count"]
            * run["simulation"]["expected_frame_count"],
            "memory_invalid_samples": 0,
        },
        "scheduler_window_count": 1,
        "scheduler_wall_ns": {
            "mean": 10.0,
            "p50": 10.0,
            "p95": 10.0,
            "p99": 10.0,
            "max": 10,
        },
        "scheduler_thread_cpu_ns": {
            "mean": 5.0,
            "p50": 5.0,
            "p95": 5.0,
            "p99": 5.0,
            "max": 5,
        },
        "placement_policy_wall_ns": {
            "mean": 6.0,
            "p50": 6.0,
            "p95": 6.0,
            "p99": 6.0,
            "max": 6,
        },
        "placement_policy_thread_cpu_ns": {
            "mean": 3.0,
            "p50": 3.0,
            "p95": 3.0,
            "p99": 3.0,
            "max": 3,
        },
        "posthoc_welfare_evaluation_wall_ns": {
            "mean": 4.0,
            "p50": 4.0,
            "p95": 4.0,
            "p99": 4.0,
            "max": 4,
        },
        "posthoc_welfare_evaluation_thread_cpu_ns": {
            "mean": 2.0,
            "p50": 2.0,
            "p95": 2.0,
            "p99": 2.0,
            "max": 2,
        },
        "scheduler_timing_definition": {
            "primary_policy_metric": "placement_policy_wall_ns",
            "mechanism_total_metric": "scheduler_wall_ns",
            "posthoc_welfare_excluded_from_policy_boundary": True,
            "policy_time_derived_by_subtraction": False,
        },
        "placement_rejections": 0,
        "qos_function_tasks": qos_tasks,
        "qos_simulator_internal_cost": qos_costs,
        "admission_drop": 0,
        "admission_reject": 0,
        "timeout": 0,
        "queue_semantics": "unbounded_wait_by_design",
    }


class MatrixTests(unittest.TestCase):
    def test_formal_qc_policy_forbids_outcome_based_acceptance_gates(self) -> None:
        config = load_protocol_config()
        config["qc"]["required_positive_metrics"] = ["throughput_rps"]
        with self.assertRaisesRegex(
            ProtocolValidationError, "scientific zero outcomes remain valid"
        ):
            validate_protocol_config(config)

        config = load_protocol_config()
        config["qc"]["nse_summary_contract"][
            "scientific_zero_completions_are_valid"
        ] = False
        with self.assertRaisesRegex(
            ProtocolValidationError, "preserve zero completions"
        ):
            validate_protocol_config(config)

    def test_simulation_frame_and_arrival_horizon_invariants(self) -> None:
        config_cases = (
            (
                "expected_final_frame",
                999,
                "expected_final_frame must equal total_frame",
            ),
            (
                "expected_frame_count",
                1000,
                r"expected_frame_count must equal total_frame \+ 1",
            ),
            ("frame_duration_seconds", 0.01, "frame_duration_seconds must equal 0.001"),
            ("arrival_horizon_frames", 1001, "arrival_horizon_frames must be between"),
            (
                "observation_horizon_frames",
                999,
                "arrival_horizon_frames must equal observation_horizon_frames",
            ),
        )
        for field, value, message in config_cases:
            with self.subTest(config_field=field):
                config = load_protocol_config()
                config["simulation"][field] = value
                with self.assertRaisesRegex(ProtocolValidationError, message):
                    validate_protocol_config(config)

        manifest = build_manifest(load_protocol_config(), "initial")
        manifest["runs"][0]["simulator_experiment"]["workload"][
            "arrival_horizon_frames"
        ] = 999
        with self.assertRaisesRegex(
            ProtocolValidationError, "must match run simulation"
        ):
            validate_manifest(manifest, check_hash=False)

    def test_initial_matrix_counts_and_reuse(self) -> None:
        config = load_protocol_config()
        cells, reuse = expand_cells(config)
        manifest = build_manifest(config, "initial")
        validate_manifest(manifest)
        expected_cells = {
            "E1": 60,
            "E2": 60,
            "E3": 30,
            "E4": 10,
            "E5": 12,
            "E6": 4,
            "E7": 12,
        }
        expected_runs = {
            "E1": 600,
            "E2": 600,
            "E3": 300,
            "E4": 100,
            "E5": 120,
            "E6": 40,
            "E7": 60,
        }
        self.assertEqual(len(cells), 188)
        self.assertEqual(len(manifest["runs"]), 1820)
        for experiment_id, count in expected_cells.items():
            self.assertEqual(
                sum(cell["experiment_id"] == experiment_id for cell in cells), count
            )
        for experiment_id, count in expected_runs.items():
            self.assertEqual(
                sum(run["experiment_id"] == experiment_id for run in manifest["runs"]),
                count,
            )
        self.assertFalse(
            any(run["experiment_id"] in {"E8", "E9"} for run in manifest["runs"])
        )
        self.assertTrue(any(entry["experiment_id"] == "E8" for entry in reuse))
        self.assertTrue(any(entry["experiment_id"] == "E9" for entry in reuse))
        reuse_cells = {
            entry["experiment_id"]: entry
            for entry in reuse
            if entry["kind"] == "reuse_cells"
        }
        self.assertEqual(set(reuse_cells), {"E2", "E5", "E6", "E7"})
        self.assertEqual(
            reuse_cells["E6"]["source_selector"]["workload.request_freq"],
            ["middle", "high"],
        )
        self.assertEqual(
            reuse_cells["E6"]["source_selector"]["method"], config["methods"]
        )
        self.assertTrue(
            all(
                entry["schema_version"] == "NSE_ANALYSIS_REUSE_RULE_V1"
                and len(entry["rule_sha256"]) == 64
                for entry in reuse
            )
        )

    def test_manifest_rejects_tampered_analysis_reuse_rule(self) -> None:
        manifest = build_manifest(load_protocol_config(), "initial")
        rule = next(
            entry
            for entry in manifest["reuse_analyses"]
            if entry["experiment_id"] == "E2"
        )
        rule["source_selector"]["workload.load_scale"] = 25.0
        with self.assertRaisesRegex(
            ProtocolValidationError, "rule_sha256 does not match"
        ):
            validate_manifest(manifest, check_hash=False)

    def test_paired_workload_hashes_and_scaling(self) -> None:
        manifest = build_manifest(load_protocol_config(), "initial")
        paired = [
            run
            for run in manifest["runs"]
            if run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["workload"]["topology"] == "homogeneous"
            and run["seed"] == "E01"
        ]
        self.assertEqual(len(paired), 10)
        self.assertEqual(len({run["workload_spec_hash"] for run in paired}), 1)
        e2 = [run for run in manifest["runs"] if run["experiment_id"] == "E2"]
        self.assertEqual({run["cluster"]["node_count"] for run in e2}, {100, 500})
        scales = {
            (run["cluster"]["node_count"], run["workload"]["load_scale"]) for run in e2
        }
        self.assertEqual(scales, {(100, 5.0), (500, 25.0)})
        self.assertTrue(
            all(run["workload_tape"]["runtime_load_scale"] == 1.0 for run in e2)
        )
        self.assertTrue(
            all(
                run["simulator_experiment"]["workload"]["load_scale"] == 1.0
                for run in e2
            )
        )

    def test_ci_extension_does_not_expand_e7(self) -> None:
        manifest = build_manifest(load_protocol_config(), "ci_extension")
        self.assertEqual(len(manifest["runs"]), 1760)
        self.assertFalse(any(run["experiment_id"] == "E7" for run in manifest["runs"]))
        self.assertEqual(
            {run["seed"] for run in manifest["runs"]},
            {f"E{i:02d}" for i in range(11, 21)},
        )

    def test_e5_workload_exactly_matches_e1_full(self) -> None:
        manifest = build_manifest(load_protocol_config(), "initial")
        for load in ("low", "middle", "high"):
            full = next(
                run
                for run in manifest["runs"]
                if run["experiment_id"] == "E1"
                and run["method"] == "sche_nash"
                and run["seed"] == "E01"
                and run["workload"]["request_freq"] == load
                and run["workload"]["topology"] == "heterogeneous"
            )
            ablations = [
                run
                for run in manifest["runs"]
                if run["experiment_id"] == "E5"
                and run["seed"] == "E01"
                and run["workload"]["request_freq"] == load
            ]
            self.assertEqual(len(ablations), 4)
            self.assertTrue(
                all(run["workload"] == full["workload"] for run in ablations)
            )
            self.assertTrue(
                all(
                    run["workload_spec_hash"] == full["workload_spec_hash"]
                    for run in ablations
                )
            )

    def test_formal_fields_and_reference_build_budget_are_frozen(self) -> None:
        manifest = build_manifest(load_protocol_config(), "initial")
        # 310 coordinated-NSESche builds plus 40 method-state-matched E6
        # comparator builds.  CP-BR/OnSocMax cannot reuse NSESche tables
        # because their prior placements create different window states.
        self.assertEqual(len(manifest["reference_build_dependencies"]), 350)
        self.assertEqual(
            sum(
                run["experiment_id"] == "E5" and "reference_dependency" in run
                for run in manifest["runs"]
            ),
            90,
        )
        self.assertEqual(
            sum(
                run["experiment_id"] == "E6"
                and run["method"] in {"cp_br", "onsocmax"}
                and "reference_dependency" in run
                for run in manifest["runs"]
            ),
            40,
        )
        no_coordination = next(
            run
            for run in manifest["runs"]
            if run["experiment_id"] == "E5" and run["variant"] == "no_coordination"
        )
        self.assertNotIn("reference_dependency", no_coordination)
        self.assertEqual(no_coordination["reference_policy"]["status"], "not_required")
        self.assertEqual(
            no_coordination["simulator_experiment"]["reference"]["mode"], "not_required"
        )
        e7 = next(run for run in manifest["runs"] if run["experiment_id"] == "E7")
        self.assertEqual(
            e7["simulator_experiment"]["nash"]["price_feedback_rate"],
            e7["metadata"]["nash_parameters"]["price_feedback_rate"],
        )
        self.assertEqual(
            e7["simulator_experiment"]["nash"]["quality_weight"],
            e7["metadata"]["nash_parameters"]["quality_weight"],
        )


class TapeTests(unittest.TestCase):
    def test_burst_and_weak_scaling_derivations_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            parent = directory / "base.json"
            events = [
                {"frame": index * 10, "dag_id": index % 3} for index in range(100)
            ]
            write_json_atomic(
                parent, {"version": 1, "workload_seed": "E01", "events": events}
            )
            parent_info = inspect_tape(parent, "stream")

            burst = directory / "burst.json"
            burst_entry = derive_burst_tape(parent, burst, "spike5x50ms", mode="stream")
            self.assertEqual(burst_entry["event_count"], parent_info.event_count)
            self.assertEqual(
                burst_entry["dag_order_sha256"], parent_info.dag_order_sha256
            )
            self.assertEqual(burst_entry["parent_sha256"], parent_info.sha256)

            scaled = directory / "scaled.json"
            scaled_entry = derive_scaled_tape(parent, scaled, 5, mode="stream")
            self.assertEqual(scaled_entry["event_count"], parent_info.event_count * 5)
            scaled_events = json.loads(scaled.read_text(encoding="utf-8"))["events"]
            for parent_index, parent_event in enumerate(events):
                replicas = scaled_events[parent_index * 5 : (parent_index + 1) * 5]
                self.assertEqual(
                    [(event["frame"], event["dag_id"]) for event in replicas],
                    [(parent_event["frame"], parent_event["dag_id"])] * 5,
                )
                self.assertEqual(
                    [event["sequence"] for event in replicas],
                    list(range(parent_index * 5, parent_index * 5 + 5)),
                )


class QCTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = build_manifest(_frozen_config(), "initial")
        self.run = self.manifest["runs"][0]

    def test_failure_signature_is_result_blind_but_error_specific(self) -> None:
        first = {
            "passed": False,
            "classification": "invalid_jsonl_artifact",
            "issues": [
                {
                    "code": "invalid_jsonl_artifact",
                    "message": "nash_metrics.jsonl failed policy/reference validation",
                    "details": {"error": "line 2 has invalid assignment hashes"},
                },
                {
                    "code": "reference_pair_mismatch",
                    "message": "build and replay completed counters differ",
                    "details": {"build_completed": 953, "replay_completed": 924},
                },
            ],
        }
        second = copy.deepcopy(first)
        second["issues"][1]["details"]["replay_completed"] = 929
        self.assertEqual(
            technical_failure_signature(first),
            technical_failure_signature(second),
        )
        second["issues"][0]["details"]["error"] = "line 3 is invalid JSON"
        self.assertNotEqual(
            technical_failure_signature(first),
            technical_failure_signature(second),
        )

    def _write_nse_artifacts(self, root: Path, run: dict | None = None) -> Path:
        run = run or self.run
        qos_tasks, qos_costs = _qos_observations(run)
        directory = root / "reviewer_records" / run["run_id"]
        directory.mkdir(parents=True, exist_ok=True)
        environment = {
            "schema": "NSE_ENVIRONMENT_V1",
            "run_id": run["run_id"],
            "config": {"experiment": copy.deepcopy(run["simulator_experiment"])},
            "arrival_generation": {
                "frequency_profile": copy.deepcopy(run["workload_profile"]),
                "arrival_noise_seed": run["seed"],
            },
            "nodes": [],
            "network_mb_per_second": [],
            "functions": [],
        }
        write_json_atomic(directory / "environment.json", environment)
        with (directory / "frames.jsonl").open(
            "w", encoding="utf-8", newline="\n"
        ) as handle:
            for frame in range(run["simulation"]["expected_frame_count"]):
                event = {
                    "schema": "NSE_FRAME_V1",
                    "frame": frame,
                    "arrivals_total": 10,
                    "completed_total": 9,
                    "active_requests": 1,
                    "pending_tasks": 1,
                    "running_tasks": 0,
                    "queue_total": 1,
                    "running_containers": 1,
                    "starting_containers": 0,
                    "node_cpu_mean": 1.0,
                    "node_cpu_peak": 2.0,
                    "node_memory_mean": 1.0,
                    "node_memory_peak": 2.0,
                    "node_cpu_utilization_mean": 0.1,
                    "node_cpu_utilization_peak": 0.3,
                    "node_cpu_utilization_valid_samples": run["cluster"]["node_count"],
                    "node_cpu_utilization_invalid_samples": 0,
                    "node_memory_utilization_mean": 0.1,
                    "node_memory_utilization_peak": 0.3,
                    "node_memory_utilization_valid_samples": run["cluster"][
                        "node_count"
                    ],
                    "node_memory_utilization_invalid_samples": 0,
                    "simulator_cost_total": 1.0,
                    "drop_total": 0,
                    "reject_total": 0,
                    "timeout_total": 0,
                    "qos_function_tasks": qos_tasks,
                    "qos_resources": {
                        qos_class: {
                            "cpu_work": 0.0,
                            "memory": 0.0,
                            "simulator_internal_cost": cost["total"]
                            / run["simulation"]["expected_frame_count"],
                        }
                        for qos_class, cost in qos_costs.items()
                    },
                }
                handle.write(json.dumps(event) + "\n")
        with (directory / "requests.jsonl").open(
            "w", encoding="utf-8", newline="\n"
        ) as handle:
            for request_id in range(9):
                handle.write(
                    json.dumps(
                        {
                            "schema": "NSE_REQUEST_V1",
                            "request_id": request_id,
                            "dag_id": 0,
                            "arrival_frame": 0,
                            "completion_frame": 2,
                            "latency_ms": 2,
                            "functions": [],
                        }
                    )
                    + "\n"
                )
        (directory / "scheduler_windows.jsonl").write_text(
            json.dumps(
                {
                    "schema": "NSE_SCHEDULER_WINDOW_V1",
                    "begin_frame": 0,
                    "end_frame": 0,
                    "wall_time_ns": 10,
                    "thread_cpu_ns": 5,
                    "timing_scope": {
                        "wall_time_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
                        "thread_cpu_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
                        "policy_wall_time_ns": "placement_policy_call_exact_boundary",
                        "policy_thread_cpu_ns": "placement_policy_call_exact_boundary",
                        "welfare_evaluation_wall_time_ns": "read_only_posthoc_observer_exact_boundary",
                        "welfare_evaluation_thread_cpu_ns": "read_only_posthoc_observer_exact_boundary",
                        "policy_time_derived_by_subtraction": False,
                    },
                    "policy_wall_time_ns": 6,
                    "policy_thread_cpu_ns": 3,
                    "welfare_evaluation_wall_time_ns": 4,
                    "welfare_evaluation_thread_cpu_ns": 2,
                    "placements_accepted": 1,
                    "placements_rejected": 0,
                    "common_hpa_scale_up_commands": 1,
                    "common_hpa_scale_down_commands": 0,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        if run["method"] != "sche_nash":
            welfare_events = [
                {
                    "v": 1,
                    "kind": "welfare_window",
                    "schema": "NSE_POSTHOC_WELFARE_WINDOW_V1",
                    "scheduler": run["method"],
                    "window": 1,
                    "frame": 0,
                    "policy_commands_mutated": False,
                    "decision": {
                        "complete_assignment": True,
                        "initial_assignment_hash": 0,
                        "assignment_hash": 0,
                    },
                    "social": {
                        "reference_state_key": None,
                        "reference_source": "not_required",
                        "reference": None,
                        "final_assignment_baseline_welfare": 0.0,
                        "empirical_gap": None,
                    },
                },
                {
                    "v": 1,
                    "kind": "welfare_run_summary",
                    "schema": "NSE_POSTHOC_WELFARE_RUN_V1",
                    "scheduler": run["method"],
                    "windows": 1,
                    "policy_commands_mutated": False,
                    "observation_writer_error": None,
                },
            ]
            (directory / "welfare_metrics.jsonl").write_text(
                "".join(json.dumps(event) + "\n" for event in welfare_events),
                encoding="utf-8",
            )
        summary_path = directory / "summary.json"
        write_json_atomic(summary_path, _valid_result(run))
        return summary_path

    def test_valid_summary_passes_with_legal_zero_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result_path = self._write_nse_artifacts(Path(directory))
            report = evaluate_attempt(
                self.run,
                self.manifest["qc"],
                result_path,
                artifact_root=Path(directory),
            )
            self.assertTrue(report.passed, report.to_dict())

    def test_atomic_common_hpa_rejects_nonzero_placement_commit_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = self._write_nse_artifacts(root)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["placement_rejections"] = 1
            write_json_atomic(result_path, result)

            scheduler_path = result_path.parent / "scheduler_windows.jsonl"
            scheduler_event = json.loads(scheduler_path.read_text(encoding="utf-8"))
            scheduler_event["placements_accepted"] = 0
            scheduler_event["placements_rejected"] = 1
            scheduler_path.write_text(
                json.dumps(scheduler_event) + "\n", encoding="utf-8"
            )

            report = evaluate_attempt(
                self.run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(report.passed)
            self.assertIn(
                "placement_commit_violation",
                {issue.code for issue in report.issues},
            )

    def test_fixed_window_completions_are_bound_to_request_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = self._write_nse_artifacts(root)
            result = _valid_result(self.run)
            result["fixed_observation_window"].update(
                {
                    "completed": 8,
                    "completion_ratio": 0.8,
                    "throughput_requests_per_second": 8.0,
                }
            )
            write_json_atomic(result_path, result)
            report = evaluate_attempt(
                self.run,
                self.manifest["qc"],
                result_path,
                artifact_root=root,
            )
            self.assertFalse(report.passed)
            self.assertIn(
                "summary_stream_mismatch", {issue.code for issue in report.issues}
            )

    def test_e3_fixed_throughput_horizon_is_not_extended_by_drain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = next(
                run
                for run in self.manifest["runs"]
                if run["experiment_id"] == "E3" and run["method"] != "sche_nash"
            )
            result_path = self._write_nse_artifacts(root, run)
            result = _valid_result(run)
            self.assertEqual(result["fixed_observation_window"]["duration_ms"], 1000)
            self.assertEqual(result["drained_arrival_cohort"]["drain_end_frame"], 4000)
            self.assertEqual(
                result["fixed_observation_window"]["throughput_requests_per_second"],
                9.0,
            )
            self.assertEqual(result["throughput_requests_per_second"], 2.25)
            report = evaluate_attempt(
                run,
                self.manifest["qc"],
                result_path,
                artifact_root=root,
            )
            self.assertTrue(report.passed, report.to_dict())

    def test_experiment_config_accepts_only_runtime_equivalent_f32_values(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = self._write_nse_artifacts(root)
            environment_path = result_path.parent / "environment.json"
            environment = json.loads(environment_path.read_text(encoding="utf-8"))
            experiment = environment["config"]["experiment"]

            def f32(value: float) -> float:
                return struct.unpack("!f", struct.pack("!f", value))[0]

            for section, field in (
                ("faasrank_model", "diversity_penalty"),
                ("faasrank_model", "epsilon"),
                ("faasrank_model", "load_balance"),
                ("faasrank_model", "memory_headroom"),
                ("faasrank_model", "network_locality"),
                ("hpa", "tolerance"),
                ("nash", "price_feedback_rate"),
                ("node_profile", "cpu_cv"),
                ("qos", "cost_weight"),
                ("qos", "latency_weight"),
                ("qos", "throughput_weight"),
            ):
                value = experiment[section][field]
                if value is not None:
                    experiment[section][field] = f32(value)

            # These values are intentionally materialized by the runner after
            # the run spec has already hash-bound the corresponding artifacts.
            experiment["workload"]["tape_path"] = "runtime/tape.json"
            experiment["reference"]["table_path"] = "runtime/reference.json"
            experiment["reference"]["build_output_path"] = "runtime/build.jsonl"
            experiment["output"]["root"] = "runtime/records"
            write_json_atomic(environment_path, environment)

            report = evaluate_attempt(
                self.run,
                self.manifest["qc"],
                result_path,
                artifact_root=root,
            )
            self.assertTrue(report.passed, report.to_dict())

    def test_experiment_config_rejects_material_f32_and_non_path_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = self._write_nse_artifacts(root)
            environment_path = result_path.parent / "environment.json"
            environment = json.loads(environment_path.read_text(encoding="utf-8"))
            experiment = environment["config"]["experiment"]
            experiment["hpa"]["tolerance"] = 0.1001
            experiment["reference"]["mode"] = "changed-after-freeze"
            write_json_atomic(environment_path, environment)

            report = evaluate_attempt(
                self.run,
                self.manifest["qc"],
                result_path,
                artifact_root=root,
            )
            self.assertFalse(report.passed)
            config_issues = [
                issue
                for issue in report.issues
                if issue.code == "configuration_mismatch"
            ]
            self.assertTrue(config_issues, report.to_dict())
            detailed = next(
                issue for issue in config_issues if "differences" in issue.details
            )
            difference_paths = {
                difference["path"] for difference in detailed.details["differences"]
            }
            self.assertIn("$.hpa.tolerance", difference_paths)
            self.assertIn("$.reference.mode", difference_paths)

    def test_workload_multiplier_accepts_one_f64_ulp_but_rejects_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = next(
                item
                for item in self.manifest["runs"]
                if item["workload_profile"]["load"] == "high"
            )
            result_path = self._write_nse_artifacts(root, run)
            environment_path = result_path.parent / "environment.json"
            environment = json.loads(environment_path.read_text(encoding="utf-8"))
            expected = run["workload_profile"]["source"]["uniform_mean_multiplier"]

            def add_ulp(value: float, count: int) -> float:
                bits = struct.unpack("!Q", struct.pack("!d", value))[0]
                return struct.unpack("!d", struct.pack("!Q", bits + count))[0]

            for profile in (
                environment["arrival_generation"]["frequency_profile"],
                environment["config"]["experiment"]["workload"]["frequency_profile"],
            ):
                profile["source"]["uniform_mean_multiplier"] = add_ulp(expected, 1)
            write_json_atomic(environment_path, environment)
            report = evaluate_attempt(
                run,
                self.manifest["qc"],
                result_path,
                artifact_root=root,
            )
            self.assertTrue(report.passed, report.to_dict())

            for profile in (
                environment["arrival_generation"]["frequency_profile"],
                environment["config"]["experiment"]["workload"]["frequency_profile"],
            ):
                profile["source"]["uniform_mean_multiplier"] = add_ulp(expected, 2)
            write_json_atomic(environment_path, environment)
            report = evaluate_attempt(
                run,
                self.manifest["qc"],
                result_path,
                artifact_root=root,
            )
            self.assertFalse(report.passed)
            codes = {issue.code for issue in report.issues}
            self.assertIn("workload_profile_mismatch", codes)
            self.assertIn("configuration_mismatch", codes)

    def test_required_observation_fields_and_sample_counts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = self._write_nse_artifacts(root)
            result = _valid_result(self.run)
            result.pop("node_memory_utilization_p95")
            result["node_utilization_definition"]["cpu_valid_samples"] -= 1
            result["node_utilization_definition"]["cpu_invalid_samples"] += 1
            result["placement_rejections"] = 1
            write_json_atomic(result_path, result)
            report = evaluate_attempt(
                self.run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(report.passed)
            codes = {issue.code for issue in report.issues}
            self.assertIn("invalid_metric", codes)
            self.assertIn("invalid_observation_samples", codes)
            self.assertIn("summary_stream_mismatch", codes)

    def test_balanced_qos_counters_are_required_and_conserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = copy.deepcopy(self.run)
            run["workload"]["qos_profile"] = "balanced"
            run["simulator_experiment"]["qos"]["enabled"] = True
            run["simulator_experiment"]["qos"]["class_assignment"] = "balanced"
            result_path = self._write_nse_artifacts(root, run)
            valid = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertTrue(valid.passed, valid.to_dict())

            result = _valid_result(run)
            result["qos_function_tasks"]["latency"]["active"] = 0
            write_json_atomic(result_path, result)
            invalid = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(invalid.passed)
            self.assertIn(
                "counter_conservation", {issue.code for issue in invalid.issues}
            )

    def test_zero_completions_is_preserved_as_a_valid_scientific_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = self._write_nse_artifacts(root)
            result = _valid_result(self.run)
            result.update(
                {
                    "completed": 0,
                    "completion_ratio": 0.0,
                    "throughput_requests_per_second": 0.0,
                    "latency_ms": {"mean": None, "p50": None, "p95": None, "p99": None},
                    "simulator_internal_cost_per_completed_request": None,
                }
            )
            result["fixed_observation_window"].update(
                {
                    "completed": 0,
                    "completion_ratio": 0.0,
                    "throughput_requests_per_second": 0.0,
                }
            )
            result["drained_arrival_cohort"].update(
                {
                    "completed": 0,
                    "completion_ratio": 0.0,
                    "latency_ms": {
                        "mean": None,
                        "p50": None,
                        "p95": None,
                        "p99": None,
                    },
                }
            )
            write_json_atomic(result_path, result)
            record_dir = result_path.parent
            (record_dir / "requests.jsonl").write_text("", encoding="utf-8")
            qos_tasks, qos_costs = _qos_observations(self.run)
            with (record_dir / "frames.jsonl").open(
                "w", encoding="utf-8", newline="\n"
            ) as handle:
                for frame in range(self.run["simulation"]["expected_frame_count"]):
                    handle.write(
                        json.dumps(
                            {
                                "schema": "NSE_FRAME_V1",
                                "frame": frame,
                                "arrivals_total": 10,
                                "completed_total": 0,
                                "active_requests": 10,
                                "pending_tasks": 1,
                                "running_tasks": 0,
                                "queue_total": 1,
                                "running_containers": 1,
                                "starting_containers": 0,
                                "node_cpu_mean": 1.0,
                                "node_cpu_peak": 2.0,
                                "node_memory_mean": 1.0,
                                "node_memory_peak": 2.0,
                                "node_cpu_utilization_mean": 0.1,
                                "node_cpu_utilization_peak": 0.3,
                                "node_cpu_utilization_valid_samples": self.run[
                                    "cluster"
                                ]["node_count"],
                                "node_cpu_utilization_invalid_samples": 0,
                                "node_memory_utilization_mean": 0.1,
                                "node_memory_utilization_peak": 0.3,
                                "node_memory_utilization_valid_samples": self.run[
                                    "cluster"
                                ]["node_count"],
                                "node_memory_utilization_invalid_samples": 0,
                                "simulator_cost_total": 1.0,
                                "drop_total": 0,
                                "reject_total": 0,
                                "timeout_total": 0,
                                "qos_function_tasks": qos_tasks,
                                "qos_resources": {
                                    qos_class: {
                                        "cpu_work": 0.0,
                                        "memory": 0.0,
                                        "simulator_internal_cost": cost["total"]
                                        / self.run["simulation"][
                                            "expected_frame_count"
                                        ],
                                    }
                                    for qos_class, cost in qos_costs.items()
                                },
                            }
                        )
                        + "\n"
                    )
            report = evaluate_attempt(
                self.run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertTrue(report.passed, report.to_dict())
            self.assertEqual(report.classification, "qc_pass")

            result["latency_ms"].pop("p99")
            result.pop("simulator_internal_cost_per_completed_request")
            write_json_atomic(result_path, result)
            missing_fields = evaluate_attempt(
                self.run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(missing_fields.passed)
            self.assertIn(
                "missing_observation_fields",
                {issue.code for issue in missing_fields.issues},
            )

    def test_summary_distributions_and_costs_are_bound_to_streams(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = self._write_nse_artifacts(root)
            result = _valid_result(self.run)
            result["latency_ms"]["mean"] = 2.5
            result["node_cpu_utilization_mean"] = 0.11
            result["qos_simulator_internal_cost"]["shared"]["total"] = 0.3
            result["qos_simulator_internal_cost"]["shared"][
                "per_completed_function"
            ] = (0.3 / 9.0)
            write_json_atomic(result_path, result)
            report = evaluate_attempt(
                self.run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(report.passed)
            mismatches = [
                issue
                for issue in report.issues
                if issue.code == "summary_stream_mismatch"
            ]
            self.assertGreaterEqual(len(mismatches), 3, report.to_dict())

    def test_e6_welfare_reference_build_and_replay_are_paired(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = copy.deepcopy(
                next(
                    run
                    for run in self.manifest["runs"]
                    if run["experiment_id"] == "E6" and run["method"] == "cp_br"
                )
            )
            state_key, initial_hash, final_hash = 7, 11, 13
            run["reference_dependency"].update(
                {
                    "line_count": 1,
                    "build_completed": 9,
                    "state_pair_sequence_sha256": hashlib.sha256(
                        f"{state_key}:{initial_hash}\n".encode("ascii")
                    ).hexdigest(),
                    "assignment_sequence_sha256": hashlib.sha256(
                        f"{state_key}:{initial_hash}:{final_hash}\n".encode("ascii")
                    ).hexdigest(),
                }
            )
            result_path = self._write_nse_artifacts(root, run)
            welfare_path = result_path.with_name("welfare_metrics.jsonl")
            welfare_window = {
                "v": 1,
                "kind": "welfare_window",
                "schema": "NSE_POSTHOC_WELFARE_WINDOW_V1",
                "scheduler": "cp_br",
                "window": 1,
                "frame": 0,
                "policy_commands_mutated": False,
                "decision": {
                    "complete_assignment": True,
                    "initial_assignment_hash": initial_hash,
                    "assignment_hash": final_hash,
                },
                "social": {
                    "reference_state_key": state_key,
                    "reference_source": "offline_table",
                    "reference": 2.0,
                    "final_assignment_baseline_welfare": 1.0,
                    "empirical_gap": 0.5,
                },
            }
            welfare_summary = {
                "v": 1,
                "kind": "welfare_run_summary",
                "schema": "NSE_POSTHOC_WELFARE_RUN_V1",
                "scheduler": "cp_br",
                "windows": 1,
                "policy_commands_mutated": False,
                "observation_writer_error": None,
            }
            welfare_path.write_text(
                json.dumps(welfare_window) + "\n" + json.dumps(welfare_summary) + "\n",
                encoding="utf-8",
            )
            valid = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertTrue(valid.passed, valid.to_dict())
            self.assertEqual(valid.observations["reference_pairing"]["method"], "cp_br")

            welfare_window["social"]["reference_source"] = "offline_table_missing"
            welfare_path.write_text(
                json.dumps(welfare_window) + "\n" + json.dumps(welfare_summary) + "\n",
                encoding="utf-8",
            )
            invalid = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(invalid.passed)
            self.assertIn(
                "reference_pair_mismatch",
                {issue.code for issue in invalid.issues},
            )

    def test_nash_windows_without_reference_have_no_reference_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = copy.deepcopy(
                next(
                    run
                    for run in self.manifest["runs"]
                    if run["experiment_id"] == "E1" and run["method"] == "sche_nash"
                )
            )
            empty_digest = hashlib.sha256(b"").hexdigest()
            run["reference_dependency"].update(
                {
                    "line_count": 0,
                    "build_completed": 9,
                    "state_pair_sequence_sha256": empty_digest,
                    "assignment_sequence_sha256": empty_digest,
                }
            )
            result_path = self._write_nse_artifacts(root, run)
            nash_path = result_path.with_name("nash_metrics.jsonl")
            event = {
                "v": 2,
                "kind": "window",
                "scheduler": "sche_nash",
                "decision": {
                    "request_function_players": 0,
                    "complete_assignment": True,
                    "initial_assignment_hash": None,
                    "assignment_hash": 0,
                },
                "social": {
                    "reference_state_key": None,
                    "reference_source": "not_requested",
                },
                "solver": {
                    "termination": "no_players",
                    "inner_limit_hit": False,
                    "oscillations": 0,
                },
            }
            nash_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

            valid = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertTrue(valid.passed, valid.to_dict())
            self.assertEqual(
                valid.observations["reference_pairing"]["reference_unique_state_pairs"],
                0,
            )

            # A non-empty solver window may terminate before requesting the
            # social reference.  It remains a valid policy observation and is
            # intentionally absent from the build/replay pair sequence.
            event["decision"]["request_function_players"] = 1
            event["decision"]["complete_assignment"] = False
            event["decision"]["assignment_hash"] = 13
            event["solver"] = {
                "termination": "inner_iteration_limit",
                "inner_limit_hit": True,
                "oscillations": 0,
            }
            nash_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            reference_not_requested = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertTrue(
                reference_not_requested.passed, reference_not_requested.to_dict()
            )
            self.assertEqual(
                reference_not_requested.observations["reference_pairing"][
                    "reference_unique_state_pairs"
                ],
                0,
            )

            event["decision"]["initial_assignment_hash"] = 11
            nash_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            unexpected_initial = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(unexpected_initial.passed)
            errors = [
                issue.details.get("error", "")
                for issue in unexpected_initial.issues
                if issue.code == "invalid_jsonl_artifact"
            ]
            self.assertTrue(
                any(
                    "invalid reference-not-requested state" in error for error in errors
                ),
                unexpected_initial.to_dict(),
            )

            event["decision"]["initial_assignment_hash"] = None
            event["social"]["reference_source"] = "offline_table_missing"
            nash_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            invalid = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(invalid.passed)
            errors = [
                issue.details.get("error", "")
                for issue in invalid.issues
                if issue.code == "invalid_jsonl_artifact"
            ]
            self.assertTrue(
                any(
                    "invalid reference-not-requested state" in error for error in errors
                ),
                invalid.to_dict(),
            )

            event["social"]["reference_source"] = "offline_table"
            event["social"]["reference_state_key"] = 7
            nash_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            missing_initial = evaluate_attempt(
                run, self.manifest["qc"], result_path, artifact_root=root
            )
            self.assertFalse(missing_initial.passed)
            errors = [
                issue.details.get("error", "")
                for issue in missing_initial.issues
                if issue.code == "invalid_jsonl_artifact"
            ]
            self.assertTrue(
                any("invalid initial assignment hash" in error for error in errors),
                missing_initial.to_dict(),
            )

    def test_nonfinite_and_required_zero_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result_path = self._write_nse_artifacts(Path(directory))
            result = _valid_result(self.run)
            result["throughput_requests_per_second"] = 0
            result["simulator_internal_cost_total"] = float("nan")
            with result_path.open("w", encoding="utf-8") as handle:
                json.dump(result, handle, allow_nan=True)
            report = evaluate_attempt(
                self.run,
                self.manifest["qc"],
                result_path,
                artifact_root=Path(directory),
            )
            self.assertFalse(report.passed)
            codes = {issue.code for issue in report.issues}
            self.assertIn("metric_consistency", codes)
            self.assertTrue({"nonfinite_value", "nonfinite_metric"} & codes)

    def test_provenance_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result_path = self._write_nse_artifacts(Path(directory))
            result = _valid_result(self.run)
            result["run_id"] = "wrong-run"
            write_json_atomic(result_path, result)
            report = evaluate_attempt(
                self.run,
                self.manifest["qc"],
                result_path,
                artifact_root=Path(directory),
            )
            self.assertFalse(report.passed)
            self.assertEqual(report.classification, "provenance_failure")


class RunnerTests(unittest.TestCase):
    def _write_helper(
        self,
        path: Path,
        succeed_at: int | None,
        *,
        distinct_failures: bool = False,
    ) -> None:
        source = f"""import json, os, sys
attempt = int(os.environ["PROTOCOL_ATTEMPT"])
succeed_at = {succeed_at!r}
if succeed_at is None or attempt < succeed_at:
    print("predeclared technical failure", file=sys.stderr)
    raise SystemExit(6 + attempt if {distinct_failures!r} else 7)
with open(os.environ["PROTOCOL_RUN_CONFIG"], "r", encoding="utf-8") as handle:
    run = json.load(handle)
result = {{
    "schema": "NSE_SUMMARY_V1", "run_id": run["run_id"],
    "protocol_version": run["simulator_experiment"]["protocol_version"],
    "run_complete": True,
    "final_frame": run["simulation"]["expected_final_frame"],
    "frames_recorded": run["simulation"]["expected_frame_count"],
    "frame_duration_ms": 1,
    "observation_time_ms": run["simulation"]["total_frame"],
    "arrivals": 10, "completed": 9,
    "completion_ratio": 0.9,
    "throughput_requests_per_second": 9.0 * 1000.0 / run["simulation"]["total_frame"],
    "latency_ms": {{"mean": 2.0, "p50": 2.0, "p95": 2.0, "p99": 2.0}},
    "fixed_observation_window": {{
        "start_frame": 0,
        "end_frame": run["simulation"]["observation_horizon_frames"],
        "duration_ms": run["simulation"]["observation_horizon_frames"],
        "arrivals": 10, "completed": 9, "completion_ratio": 0.9,
        "throughput_requests_per_second": 9.0
    }},
    "drained_arrival_cohort": {{
        "arrival_start_frame": 0,
        "arrival_end_frame": run["simulation"]["arrival_horizon_frames"],
        "drain_end_frame": run["simulation"]["total_frame"],
        "drain_duration_after_arrivals_ms": run["simulation"]["total_frame"] - run["simulation"]["arrival_horizon_frames"],
        "arrivals": 10, "completed": 9, "completion_ratio": 0.9,
        "latency_ms": {{"mean": 2.0, "p50": 2.0, "p95": 2.0, "p99": 2.0}}
    }},
    "metric_definitions": {{
        "frame_duration_ms": 1,
        "fixed_observation_window": {{
            "arrival_cohort": "request arrival_frame is in [0, end_frame)",
            "completion_deadline": "request completion_frame is in [0, end_frame]",
            "throughput": "completed requests at or before end_frame divided by duration_ms",
            "throughput_unit": "requests/s"
        }},
        "drained_arrival_cohort": {{
            "cohort": "the fixed-observation-window arrival cohort",
            "completion_deadline": "request completion_frame is at or before drain_end_frame",
            "latency_population": "completed requests from that cohort by drain_end_frame",
            "latency_unit": "ms"
        }},
        "legacy_top_level_fields": "preserved for compatibility; completed, completion_ratio, throughput_requests_per_second, and latency_ms retain final-run semantics with observation_time_ms as denominator"
    }},
    "simulator_internal_cost_total": 1.0,
    "simulator_internal_cost_per_completed_request": 1.0 / 9.0,
    "queue_peak": 1,
    "queue_area_request_frames": run["simulation"]["expected_frame_count"],
    "node_cpu_mean": 1.0, "node_cpu_peak": 2.0,
    "node_memory_mean": 1.0, "node_memory_peak": 2.0,
    "node_cpu_utilization_mean": 0.1,
    "node_cpu_utilization_p95": 0.2,
    "node_cpu_utilization_peak": 0.3,
    "node_memory_utilization_mean": 0.1,
    "node_memory_utilization_p95": 0.2,
    "node_memory_utilization_peak": 0.3,
    "node_utilization_unit": "fraction_of_node_capacity",
    "node_utilization_definition": {{
        "sampling": "one_sample_per_node_per_recorded_frame",
        "cpu_numerator": "node.cpu", "cpu_denominator": "node.rsc_limit.cpu",
        "memory_numerator": "node.unready_mem()", "memory_denominator": "node.rsc_limit.mem",
        "clipping": "none",
        "invalid_sample_policy": "exclude_non_finite_usage_or_capacity_negative_usage_or_non_positive_capacity",
        "cpu_valid_samples": run["cluster"]["node_count"] * run["simulation"]["expected_frame_count"],
        "cpu_invalid_samples": 0,
        "memory_valid_samples": run["cluster"]["node_count"] * run["simulation"]["expected_frame_count"],
        "memory_invalid_samples": 0
    }},
    "scheduler_window_count": 1,
    "scheduler_wall_ns": {{"mean": 10.0, "p50": 10.0, "p95": 10.0, "p99": 10.0, "max": 10}},
    "scheduler_thread_cpu_ns": {{"mean": 5.0, "p50": 5.0, "p95": 5.0, "p99": 5.0, "max": 5}},
    "placement_policy_wall_ns": {{"mean": 6.0, "p50": 6.0, "p95": 6.0, "p99": 6.0, "max": 6}},
    "placement_policy_thread_cpu_ns": {{"mean": 3.0, "p50": 3.0, "p95": 3.0, "p99": 3.0, "max": 3}},
    "posthoc_welfare_evaluation_wall_ns": {{"mean": 4.0, "p50": 4.0, "p95": 4.0, "p99": 4.0, "max": 4}},
    "posthoc_welfare_evaluation_thread_cpu_ns": {{"mean": 2.0, "p50": 2.0, "p95": 2.0, "p99": 2.0, "max": 2}},
    "scheduler_timing_definition": {{"primary_policy_metric": "placement_policy_wall_ns",
        "mechanism_total_metric": "scheduler_wall_ns",
        "posthoc_welfare_excluded_from_policy_boundary": True,
        "policy_time_derived_by_subtraction": False}},
    "placement_rejections": 0,
    "qos_function_tasks": {{"shared": {{"arrived": 10, "completed": 9,
        "active": 1, "completion_ratio": 0.9}}}},
    "qos_simulator_internal_cost": {{"shared": {{
        "unit": "simulator_internal_units", "total": 0.2,
        "per_completed_function": 0.2 / 9.0, "is_currency": False}}}},
    "admission_drop": 0,
    "admission_reject": 0, "timeout": 0,
    "queue_semantics": "unbounded_wait_by_design"
}}
record_dir = os.path.join(os.environ["PROTOCOL_REVIEWER_RECORD_ROOT"], run["run_id"])
os.makedirs(record_dir, exist_ok=True)
environment = {{
    "schema": "NSE_ENVIRONMENT_V1", "run_id": run["run_id"],
    "config": {{"experiment": run["simulator_experiment"]}},
    "arrival_generation": {{
        "frequency_profile": run["workload_profile"],
        "arrival_noise_seed": run["seed"]
    }},
    "nodes": [{{"node_id": 0, "cpu": 150.0, "memory": 5000.0}}],
    "network_mb_per_second": [[0.0]],
    "functions": [{{"function_id": 0, "qos_class": "latency_sensitive"}}]
}}
with open(os.path.join(record_dir, "environment.json"), "w", encoding="utf-8") as handle:
    json.dump(environment, handle)
with open(os.path.join(record_dir, "frames.jsonl"), "w", encoding="utf-8") as handle:
    for frame in range(run["simulation"]["expected_frame_count"]):
        event = {{
            "schema": "NSE_FRAME_V1", "frame": frame,
            "arrivals_total": 10, "completed_total": 9, "active_requests": 1,
            "pending_tasks": 1, "running_tasks": 0, "queue_total": 1,
            "running_containers": 1, "starting_containers": 0,
            "node_cpu_mean": 1.0, "node_cpu_peak": 2.0,
            "node_memory_mean": 1.0, "node_memory_peak": 2.0,
            "node_cpu_utilization_mean": 0.1,
            "node_cpu_utilization_peak": 0.3,
            "node_cpu_utilization_valid_samples": run["cluster"]["node_count"],
            "node_cpu_utilization_invalid_samples": 0,
            "node_memory_utilization_mean": 0.1,
            "node_memory_utilization_peak": 0.3,
            "node_memory_utilization_valid_samples": run["cluster"]["node_count"],
            "node_memory_utilization_invalid_samples": 0,
            "simulator_cost_total": 1.0,
            "drop_total": 0, "reject_total": 0, "timeout_total": 0,
            "qos_function_tasks": {{"shared": {{"arrived": 10,
                "completed": 9, "active": 1, "completion_ratio": 0.9}}}},
            "qos_resources": {{"shared": {{"cpu_work": 0.0, "memory": 0.0,
                "simulator_internal_cost": 0.2 / run["simulation"]["expected_frame_count"]}}}}
        }}
        handle.write(json.dumps(event) + "\\n")
with open(os.path.join(record_dir, "requests.jsonl"), "w", encoding="utf-8") as handle:
    for request_id in range(9):
        event = {{"schema": "NSE_REQUEST_V1", "request_id": request_id,
            "dag_id": 0, "arrival_frame": 0, "completion_frame": 2,
            "latency_ms": 2, "functions": []}}
        handle.write(json.dumps(event) + "\\n")
with open(os.path.join(record_dir, "scheduler_windows.jsonl"), "w", encoding="utf-8") as handle:
    event = {{"schema": "NSE_SCHEDULER_WINDOW_V1", "begin_frame": 0,
        "end_frame": 0, "wall_time_ns": 10, "thread_cpu_ns": 5,
        "timing_scope": {{
            "wall_time_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
            "thread_cpu_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
            "policy_wall_time_ns": "placement_policy_call_exact_boundary",
            "policy_thread_cpu_ns": "placement_policy_call_exact_boundary",
            "welfare_evaluation_wall_time_ns": "read_only_posthoc_observer_exact_boundary",
            "welfare_evaluation_thread_cpu_ns": "read_only_posthoc_observer_exact_boundary",
            "policy_time_derived_by_subtraction": False}},
        "policy_wall_time_ns": 6, "policy_thread_cpu_ns": 3,
        "welfare_evaluation_wall_time_ns": 4,
        "welfare_evaluation_thread_cpu_ns": 2,
        "placements_accepted": 1, "placements_rejected": 0,
        "common_hpa_scale_up_commands": 1, "common_hpa_scale_down_commands": 0}}
    handle.write(json.dumps(event) + "\\n")
with open(os.path.join(record_dir, "welfare_metrics.jsonl"), "w", encoding="utf-8") as handle:
    event = {{"v": 1, "kind": "welfare_window",
        "schema": "NSE_POSTHOC_WELFARE_WINDOW_V1", "scheduler": run["method"],
        "window": 1, "frame": 0, "policy_commands_mutated": False,
        "decision": {{"complete_assignment": True, "initial_assignment_hash": 0,
            "assignment_hash": 0}},
        "social": {{"reference_state_key": None, "reference_source": "not_required",
            "reference": None, "final_assignment_baseline_welfare": 0.0,
            "empirical_gap": None}}}}
    handle.write(json.dumps(event) + "\\n")
    event = {{"v": 1, "kind": "welfare_run_summary",
        "schema": "NSE_POSTHOC_WELFARE_RUN_V1", "scheduler": run["method"],
        "windows": 1, "policy_commands_mutated": False,
        "observation_writer_error": None}}
    handle.write(json.dumps(event) + "\\n")
with open(os.environ["PROTOCOL_RESULT_PATH"], "w", encoding="utf-8") as handle:
    json.dump(result, handle)
"""
        path.write_text(source, encoding="utf-8")

    def _manifest_and_run(
        self,
        directory: Path,
        helper: Path,
        *,
        method: str = "greedy",
        bind_model: bool = True,
    ) -> tuple[Path, dict]:
        config = _frozen_config()
        config["execution"]["command_template"] = [sys.executable, str(helper)]
        manifest = build_manifest(config, "initial")
        manifest["runs"] = [
            next(run for run in manifest["runs"] if run["method"] == method)
        ]
        manifest["reference_build_dependencies"] = []
        # Recompute the manifest hash after deliberately selecting a one-run test shard.
        manifest.pop("manifest_hash")
        from scripts.reviewer_experiments.protocol.util import object_hash

        manifest["manifest_hash"] = object_hash(manifest)
        unbound_path = directory / "manifest.unbound.json"
        write_json_atomic(unbound_path, manifest)
        run = manifest["runs"][0]
        tape_path = directory / "tape.json"
        write_json_atomic(
            tape_path,
            {
                "version": 1,
                "workload_seed": run["seed"],
                "events": [{"frame": 0, "dag_id": 0} for _ in range(10)],
            },
        )
        catalog_path = directory / "tape_catalog.json"
        register_base_tape(catalog_path, run["workload_tape"]["key"], tape_path)
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        from scripts.reviewer_experiments.protocol.util import file_hash

        entry = catalog["entries"][run["workload_tape"]["key"]]
        capture_root = directory / "capture"
        capture_environment_path = (
            capture_root / "reviewer_records" / "capture-run" / "environment.json"
        )
        capture_functions = [{"function_id": 0, "qos_class": "latency_sensitive"}]
        capture_nodes = [{"node_id": 0, "cpu": 150.0, "memory": 5000.0}]
        capture_network = [[0.0]]
        write_json_atomic(
            capture_environment_path,
            {
                "schema": "NSE_ENVIRONMENT_V1",
                "run_id": "capture-run",
                "functions": capture_functions,
                "nodes": capture_nodes,
                "network_mb_per_second": capture_network,
            },
        )
        function_hash = object_hash(capture_functions)
        node_network_hash = object_hash(
            {"nodes": capture_nodes, "network_mb_per_second": capture_network}
        )
        capture_bundle = {
            "function_dag_qos_sha256": function_hash,
            "node_network_sha256": node_network_hash,
            "capture_environment_sha256": file_hash(capture_environment_path),
            "function_count": 1,
            "node_count": 1,
        }
        capture_bundle["semantic_bundle_sha256"] = object_hash(capture_bundle)
        capture_receipt = capture_root / "capture_receipt.json"
        write_json_atomic(
            capture_receipt,
            {
                "schema_version": "NSE_BASE_TAPE_CAPTURE_RECEIPT_V2",
                "key": run["workload_tape"]["key"],
                "seed": run["seed"],
                "tape_sha256": entry["sha256"],
                "tape_event_count": entry["event_count"],
                "measured_arrival_rate_rps": entry["measured_arrival_rate_rps"],
                "source_kind": "azure_trace_derived_empirical_cdf",
                "source_is_direct_raw_trace": False,
                "workload_frequency_profile": copy.deepcopy(run["workload_profile"]),
                **capture_bundle,
                "run_config_sha256": "a" * 64,
                "process_observation_sha256": "b" * 64,
            },
        )
        entry.update(
            {
                "capture_environment": capture_bundle,
                "capture_receipt_path": str(capture_receipt.resolve()),
                "capture_receipt_sha256": file_hash(capture_receipt),
                "workload_profile": copy.deepcopy(run["workload_profile"]),
                "provenance": copy.deepcopy(run["workload_tape"]["provenance"]),
            }
        )
        entry["provenance"]["measured_arrival_rate_rps"] = entry[
            "measured_arrival_rate_rps"
        ]
        catalog.pop("catalog_hash")
        catalog["catalog_hash"] = object_hash(catalog)
        manifest = bind_tape_catalog(manifest, catalog)
        if method == "sche_FaaSRank" and bind_model:
            model_path = directory / "faasrank-model.json"
            create_frozen_faasrank_model(
                model_path,
                training_tape_sha256="a" * 64,
                weights={
                    "cpu_headroom": 0.25,
                    "memory_headroom": 0.20,
                    "network_locality": 0.15,
                    "warm_affinity": 0.25,
                    "load_balance": 0.15,
                    "diversity_penalty": 0.05,
                },
                epsilon=0.1,
                calibration_provenance={"method": "test-only calibration"},
                selection_provenance={"criterion": "test-only validation"},
            )
            manifest = bind_faasrank_model(
                manifest,
                model_path,
                manifest_artifact_path=str(model_path.resolve()),
            )
        manifest_path = directory / "manifest.json"
        write_json_atomic(manifest_path, manifest)
        return manifest_path, manifest["runs"][0]

    def test_workload_package_snapshot_is_verified_before_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            helper = directory / "helper.py"
            self._write_helper(helper, succeed_at=1)
            manifest_path, run = self._manifest_and_run(directory, helper)
            runner = ProtocolRunner(manifest_path, directory / "workspace")
            tape_path, _ = runner._assert_run_ready(run)
            self.assertTrue(tape_path.is_file())

            capture_root = Path(run["workload_tape"]["capture_receipt_path"]).parent
            environment_path = next(capture_root.rglob("environment.json"))
            environment_path.write_text(
                '{"schema":"NSE_ENVIRONMENT_V1","functions":[],"nodes":[],"network_mb_per_second":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ProtocolRunError, "immutable environment snapshot"
            ):
                # A prior successful verification in this same runner must not
                # turn the workload package into a trust-on-first-use cache.
                runner._assert_run_ready(run)
            fresh_runner = ProtocolRunner(manifest_path, directory / "fresh-workspace")
            with self.assertRaisesRegex(
                ProtocolRunError, "immutable environment snapshot"
            ):
                fresh_runner._assert_run_ready(run)

    def test_distinct_same_seed_failures_then_canonicalizes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            helper = directory / "helper.py"
            self._write_helper(helper, succeed_at=3, distinct_failures=True)
            manifest_path, run = self._manifest_and_run(directory, helper)
            workspace = directory / "workspace"
            results = ProtocolRunner(manifest_path, workspace).run(
                run_ids=[run["run_id"]]
            )
            self.assertEqual(results[0]["status"], "canonicalized")
            self.assertEqual(results[0]["attempt"], 3)
            self.assertTrue(
                (workspace / "quarantine" / run["run_id"] / "attempt-01").is_dir()
            )
            self.assertTrue(
                (workspace / "quarantine" / run["run_id"] / "attempt-02").is_dir()
            )
            canonical = workspace / "canonical" / run["run_id"]
            self.assertTrue(canonical.is_dir())
            archive_summary = json.loads(
                (canonical / "jsonl_archive_summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                archive_summary["total_raw_lines"],
                run["simulation"]["expected_frame_count"] + 12,
            )
            self.assertEqual(archive_summary["archive_count"], 4)
            self.assertFalse(any(canonical.rglob("*.jsonl")))
            self.assertEqual(len(list(canonical.rglob("*.jsonl.gz"))), 4)
            metadata = json.loads(
                (canonical / "attempt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["seed"], run["seed"])
            self.assertEqual(metadata["run_spec_hash"], run["run_spec_hash"])
            events, _ = verify_ledger(workspace / "ledger.jsonl")
            self.assertGreaterEqual(events, 8)

    def test_repeated_failure_signature_blocks_after_two_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            helper = directory / "helper.py"
            self._write_helper(helper, succeed_at=None)
            manifest_path, run = self._manifest_and_run(directory, helper)
            workspace = directory / "workspace"
            results = ProtocolRunner(manifest_path, workspace).run(
                run_ids=[run["run_id"]]
            )
            self.assertEqual(results[0]["status"], "blocked")
            self.assertEqual(results[0]["attempts_used"], [1, 2])
            self.assertEqual(
                results[0]["reason"], "repeated_technical_failure_signature"
            )
            self.assertFalse((workspace / "canonical" / run["run_id"]).exists())
            self.assertFalse(
                (workspace / "quarantine" / run["run_id"] / "attempt-03").exists()
            )
            for attempt in range(1, 3):
                metadata_path = (
                    workspace
                    / "quarantine"
                    / run["run_id"]
                    / f"attempt-{attempt:02d}"
                    / "attempt.json"
                )
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["seed"], run["seed"])
                self.assertEqual(
                    metadata["failure_signature"], results[0]["failure_signature"]
                )

    def test_three_distinct_failures_exhaust_attempt_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            helper = directory / "helper.py"
            self._write_helper(helper, succeed_at=None, distinct_failures=True)
            manifest_path, run = self._manifest_and_run(directory, helper)
            workspace = directory / "workspace"
            results = ProtocolRunner(manifest_path, workspace).run(
                run_ids=[run["run_id"]]
            )
            self.assertEqual(results[0]["status"], "blocked")
            self.assertEqual(results[0]["attempts_used"], [1, 2, 3])
            self.assertNotIn("failure_signature", results[0])

    def test_faasrank_is_fail_closed_until_frozen_model_is_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            helper = directory / "helper.py"
            self._write_helper(helper, succeed_at=1)
            unbound_path, unbound_run = self._manifest_and_run(
                directory / "unbound",
                helper,
                method="sche_FaaSRank",
                bind_model=False,
            )
            blocked = ProtocolRunner(unbound_path, directory / "unbound-workspace").run(
                run_ids=[unbound_run["run_id"]]
            )
            self.assertEqual(blocked[0]["status"], "preflight_blocked")
            self.assertIn("frozen model", blocked[0]["reason"])

            bound_path, bound_run = self._manifest_and_run(
                directory / "bound",
                helper,
                method="sche_FaaSRank",
            )
            completed = ProtocolRunner(bound_path, directory / "bound-workspace").run(
                run_ids=[bound_run["run_id"]]
            )
            self.assertEqual(completed[0]["status"], "canonicalized")
            self.assertEqual(
                bound_run["simulator_experiment"]["faasrank_model"]["state"],
                "frozen",
            )


if __name__ == "__main__":
    unittest.main()
