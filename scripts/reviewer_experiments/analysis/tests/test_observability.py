from __future__ import annotations

import gzip
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt

from scripts.reviewer_experiments.analysis.observability import (
    RunArtifacts,
    _load_nse_events,
    analyze_burst_run,
    analyze_qos_run,
    analyze_scheduler_run,
    build_observability_comparisons,
    function_runtime_rows,
    load_exact_poa_results,
    load_run_artifacts,
    load_workload_tape_events,
    per_run_feature_correlations,
    per_run_differentiation_correlations,
    summarize_exact_poa,
    summarize_differentiation_correlations,
    summarize_feature_correlations,
    summarize_timeseries,
    stage_wait_run_metrics,
    window_differentiation_rows,
)
from scripts.reviewer_experiments.analysis.stats import spearman_correlation
from scripts.reviewer_experiments.figures.plot_observability import (
    plot_fig11,
    plot_fig12,
    plot_fig12_burst,
    plot_fig13,
)


def _synthetic_artifacts(seed: str = "E01") -> RunArtifacts:
    spec = {
        "experiment_id": "E3",
        "cell_id": "E3.sche_nash.spike5x50ms",
        "run_id": f"synthetic-{seed}",
        "seed": seed,
        "method": "sche_nash",
        "workload": {
            "request_freq": "middle",
            "topology": "heterogeneous",
            "qos_profile": "mixed",
            "burst_name": "spike5x50ms",
            "burst_profile": "spike_5x_50ms",
        },
        "cluster": {"node_count": 20, "topology": "heterogeneous"},
        "simulation": {"frame_duration_seconds": 0.001},
    }
    arrivals = 0
    arrivals_by_frame: list[int] = []
    frames = []
    for frame in range(1001):
        increment = int(frame % (2 if 475 <= frame < 525 else 10) == 0)
        arrivals += increment
        arrivals_by_frame.append(arrivals)
        completed = arrivals_by_frame[max(0, frame - 5)]
        if 475 <= frame < 525:
            queue = 20
        elif 525 <= frame < 560:
            queue = max(1, 20 - (frame - 525))
        else:
            queue = 1
        frames.append(
            {
                "schema": "NSE_FRAME_V1",
                "frame": frame,
                "arrivals_total": arrivals,
                "completed_total": completed,
                "active_requests": arrivals - completed,
                "queue_total": queue,
                "node_cpu_mean": 0.2 + 0.01 * queue,
            }
        )

    functions = []
    qos_classes = ("latency", "throughput", "cost")
    for function_id in range(6):
        functions.append(
            {
                "function_id": function_id,
                "dag_id": 0,
                "qos_class": qos_classes[function_id % 3],
                "quality_weight": 0.9 - function_id * 0.05,
                "cpu_work": 0.2 + function_id * 0.1,
                "memory": 128.0 + function_id * 32.0,
                "output_mb": 1.0 + function_id,
            }
        )
    frames[-1]["qos_function_tasks"] = {
        "latency": {
            "arrived": 20,
            "completed": 13,
            "active": 7,
            "completion_ratio": 13 / 20,
        },
        "throughput": {
            "arrived": 20,
            "completed": 15,
            "active": 5,
            "completion_ratio": 15 / 20,
        },
        "cost": {
            "arrived": 20,
            "completed": 17,
            "active": 3,
            "completion_ratio": 17 / 20,
        },
    }
    environment = {
        "schema": "NSE_ENVIRONMENT_V1",
        "run_id": spec["run_id"],
        "functions": functions,
    }

    requests = []
    for request_id in range(10):
        arrival = 100 + request_id * 80
        function_events = []
        for function_id in range(6):
            # Different invocation counts give function-level throughput variance.
            if request_id >= 5 + function_id:
                continue
            start = arrival + function_id
            communication = 1 + function_id
            execution = 2 + function_id
            function_events.append(
                {
                    "function_id": function_id,
                    "qos_class": qos_classes[function_id % 3],
                    "quality_weight": 0.9 - function_id * 0.05,
                    "ready_schedule_frame": start,
                    "scheduled_frame": start + 1,
                    "data_received_frame": start + 1 + communication,
                    "cold_start_done_frame": start + 2 + communication,
                    "function_done_frame": start + 2 + communication + execution,
                }
            )
        latency = 12 + request_id % 3
        requests.append(
            {
                "schema": "NSE_REQUEST_V1",
                "request_id": request_id,
                "arrival_frame": arrival,
                "completion_frame": arrival + latency,
                "latency_ms": latency,
                "functions": function_events,
            }
        )

    nse_events = []
    for function_id in range(6):
        value = 0.1 + function_id * 0.1
        nse_events.append(
            {
                "kind": "function_profile",
                "fn_id": function_id,
                "heterogeneity": {
                    "h_ri": value,
                    "h_fc": value,
                    "h_nd": value,
                    "h_pi": value,
                    "impact": value,
                },
            }
        )
    for window in range(5):
        outer_rounds = 1 + window % 2
        outer_feedback_trace = []
        for outer_round in range(outer_rounds):
            gap = 0.10 + outer_round * 0.01
            gamma = 0.20
            applied = outer_round + 1 < outer_rounds
            outer_feedback_trace.append(
                {
                    "outer_round": outer_round + 1,
                    "assignment_hash": 100 + window,
                    "nash_welfare_at_current_prices": 100.0 * (1.0 - gap),
                    "reference_welfare_at_baseline_prices": 100.0,
                    "feedback_gap": gap,
                    "gamma": gamma,
                    "price_multiplier_for_current_round": 1.0 + outer_round * 0.02,
                    "price_multiplier_for_next_round": 1.02 if applied else None,
                    "feedback_applied": applied,
                }
            )
        nse_events.append(
            {
                "kind": "window",
                "frame": window * 10,
                "decision": {
                    "request_function_players": 6,
                    "ranking_diagnostic_players": 6,
                    "active_differentiation_mean": 0.10 + window * 0.10,
                    "placement_dispersion_normalized": 0.20 + window * 0.08,
                    "co_location_conflict_pair_ratio_proxy": 0.70 - window * 0.10,
                    "near_tie_player_ratio": 0.15 + window * 0.05,
                    "differentiation_changed_top_choice_ratio": 0.05 + window * 0.08,
                },
                "solver": {
                    "inner_rounds": 2 + window,
                    "outer_rounds": outer_rounds,
                    "inner_stable": window != 4,
                    "outer_stable": window != 4,
                    "inner_limit_hit": window == 4,
                    "outer_limit_hit": False,
                    "oscillations": int(window == 3),
                    "termination": "stable" if window != 4 else "inner_limit",
                    "outer_feedback_trace": outer_feedback_trace,
                },
                "social": {
                    "welfare": 90.0,
                    "reference": 100.0,
                    "gap": 0.1,
                    "reference_source": "offline_table",
                    "reference_cache_hit": True,
                    "reference_compute_us": 0,
                    "reference_lookup_us": 3,
                },
                "pricing": {"network_beta": 1.0},
                "overhead": {
                    "reference_table_refresh_us": 0,
                    "solve_us": 20 + window,
                },
            }
        )
    scheduler = [
        {
            "schema": "NSE_SCHEDULER_WINDOW_V1",
            "begin_frame": window,
            "end_frame": window + 1,
            "policy_wall_time_ns": 50_000 + window * 1_000,
            "policy_thread_cpu_ns": 40_000 + window * 1_000,
            "wall_time_ns": 100_000 + window * 1_000,
            "thread_cpu_ns": 80_000 + window * 1_000,
        }
        for window in range(5)
    ]
    return RunArtifacts(
        spec=spec,
        run_directory=Path("synthetic"),
        environment=environment,
        frames=frames,
        requests=requests,
        scheduler_windows=scheduler,
        nse_events=nse_events,
        summary={
            "qos_simulator_internal_cost": {
                qos_class: {
                    "unit": "simulator_internal_units",
                    "total": 10.0,
                    "per_completed_function": 0.5,
                    "is_currency": False,
                }
                for qos_class in qos_classes
            }
        },
        process_observation={
            "schema_version": "NSE_PROCESS_OBSERVATION_V1",
            "peak_process_tree_rss_bytes": 256 * 1024 * 1024,
            "process_tree_cpu_seconds": 0.25,
        },
    )


class ObservabilityAnalysisTests(unittest.TestCase):
    def test_hash_bound_workload_tape_is_arrival_population(self) -> None:
        artifact = _synthetic_artifacts()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tape = root / "tape.json"
            tape.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "workload_seed": artifact.seed,
                        "events": [
                            {"frame": index, "dag_id": 0} for index in range(10)
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            spec = dict(artifact.spec)
            spec["workload_tape"] = {
                "path": "tape.json",
                "sha256": hashlib.sha256(tape.read_bytes()).hexdigest(),
                "event_count": 10,
            }
            events = load_workload_tape_events(spec, root)
            self.assertEqual(len(events), 10)
            self.assertTrue(all(event["dag_id"] == 0 for event in events))

    def test_canonical_gzip_artifacts_and_legacy_nse_logs_are_loaded(self) -> None:
        artifact = _synthetic_artifacts()
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary)
            run_directory = canonical / artifact.run_id
            records = run_directory / "reviewer_records" / artifact.run_id
            records.mkdir(parents=True)
            (run_directory / "qc_report.json").write_text(
                json.dumps({"passed": True}), encoding="utf-8"
            )
            (records / "environment.json").write_text(
                json.dumps(artifact.environment), encoding="utf-8"
            )
            for name, rows in (
                ("frames.jsonl", artifact.frames),
                ("requests.jsonl", artifact.requests),
                ("scheduler_windows.jsonl", artifact.scheduler_windows),
            ):
                with gzip.open(
                    records / f"{name}.gz", "wt", encoding="utf-8"
                ) as handle:
                    for row in rows:
                        handle.write(json.dumps(row) + "\n")
            with (run_directory / "stdout.log").open("w", encoding="utf-8") as handle:
                for event in artifact.nse_events:
                    handle.write(f"INFO NSE_METRIC_V2 {json.dumps(event)}\n")
            loaded = load_run_artifacts(artifact.spec, canonical)
            self.assertEqual(len(loaded.frames), 1001)
            self.assertEqual(len(loaded.requests), 10)
            self.assertEqual(len(loaded.scheduler_windows), 5)
            self.assertEqual(len(loaded.nse_events), len(artifact.nse_events))
            self.assertEqual(loaded.nse_event_source, "NSE_METRIC_V2_log_fallback")

    def test_authoritative_nash_stream_precedes_conflicting_log_fallback(self) -> None:
        artifact = _synthetic_artifacts()
        authoritative = [
            {
                "kind": "run_summary",
                "schema": "NSE_NASH_RUN_SUMMARY_V2",
                "reference_validation": {
                    "windows": 1,
                    "missing_ratio": 0.0,
                    "zero_ratio": 0.0,
                    "negative_ratio": 0.0,
                    "unavailable": 0,
                    "unavailable_ratio": 0.0,
                    "persist_failures": 0,
                    "offline_required_ok": True,
                },
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary)
            run_directory = canonical / artifact.run_id
            records = run_directory / "reviewer_records" / artifact.run_id
            records.mkdir(parents=True)
            (run_directory / "qc_report.json").write_text(
                json.dumps({"passed": True}), encoding="utf-8"
            )
            (records / "environment.json").write_text(
                json.dumps(artifact.environment), encoding="utf-8"
            )
            for name, rows in (
                ("frames.jsonl", artifact.frames),
                ("requests.jsonl", artifact.requests),
                ("scheduler_windows.jsonl", artifact.scheduler_windows),
                ("nash_metrics.jsonl", authoritative),
            ):
                with gzip.open(
                    records / f"{name}.gz", "wt", encoding="utf-8"
                ) as handle:
                    for row in rows:
                        handle.write(json.dumps(row) + "\n")
            (run_directory / "stdout.log").write_text(
                "INFO NSE_METRIC_V2 "
                + json.dumps({"kind": "run_summary", "source": "conflicting_log"})
                + "\n",
                encoding="utf-8",
            )

            loaded = load_run_artifacts(artifact.spec, canonical)

            self.assertEqual(loaded.nse_events, authoritative)
            self.assertEqual(loaded.nse_event_source, "nash_metrics.jsonl.gz")

    def test_authoritative_welfare_stream_precedes_conflicting_log_fallback(
        self,
    ) -> None:
        authoritative = [
            {
                "kind": "welfare_run_summary",
                "schema": "NSE_POSTHOC_WELFARE_RUN_V1",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with gzip.open(
                root / "welfare_metrics.jsonl.gz", "wt", encoding="utf-8"
            ) as handle:
                handle.write(json.dumps(authoritative[0]) + "\n")
            (root / "stdout.log").write_text(
                "INFO NSE_METRIC_V2 "
                + json.dumps({"kind": "welfare_run_summary", "source": "log"})
                + "\n",
                encoding="utf-8",
            )

            events, source = _load_nse_events(root, {"method": "greedy"})

            self.assertEqual(events, authoritative)
            self.assertEqual(source, "welfare_metrics.jsonl.gz")

    def test_spearman_ties_and_undefined_status(self) -> None:
        result = spearman_correlation([1, 2, 2, 4], [2, 3, 3, 8])
        self.assertAlmostEqual(float(result["rho"]), 1.0)
        undefined = spearman_correlation([1, 1, 1], [1, 2, 3])
        self.assertEqual(undefined["status"], "constant_feature")

    def test_burst_series_and_preregistered_recovery(self) -> None:
        series, metrics = analyze_burst_run(_synthetic_artifacts())
        self.assertEqual(len(series), 1001)
        self.assertEqual(metrics["recovery_status"], "recovered")
        self.assertEqual(
            metrics["recovery_endpoint"],
            "queue_and_rolling_p95_within_110pct_for_100ms",
        )
        # Queue backlog alone recovers after 19 ms, but the frozen endpoint
        # also requires rolling p95 latency to remain within 110% for 100 ms.
        self.assertAlmostEqual(float(metrics["recovery_time_ms"]), 89.0)
        self.assertAlmostEqual(float(metrics["queue_only_recovery_time_ms"]), 19.0)
        self.assertEqual(metrics["peak_queue"], 20.0)
        summaries = summarize_timeseries(series, bootstrap_resamples=100, seed=5)
        self.assertEqual(len(summaries), 1001 * 5)
        self.assertTrue(all(row["inference_unit"] == "run_seed" for row in summaries))

    def test_qos_completion_denominator_and_class_fairness(self) -> None:
        targets = {
            "latency": {
                "metric": "stage_latency_p95_ms",
                "direction": "lower",
                "target": 12.0,
            },
            "throughput": {
                "metric": "throughput_rps",
                "direction": "higher",
                "target": 5.0,
            },
            "cost": {
                "metric": "resource_cost_proxy_mean",
                "direction": "lower",
                "target": 20.0,
            },
        }
        classes, fairness, functions = analyze_qos_run(
            _synthetic_artifacts(),
            sla_targets=targets,
            workload_events=[{"frame": index, "dag_id": 0} for index in range(10)],
            require_arrival_coverage=True,
        )
        self.assertEqual({row["qos_class"] for row in classes}, set(targets))
        self.assertEqual(fairness["fairness_unit"], "function")
        self.assertEqual(fairness["satisfaction_function_count"], 6)
        self.assertEqual(fairness["fairness_status"], "ok_function_level")
        self.assertEqual(len(functions), 6)
        self.assertTrue(
            all(
                row["normalized_satisfaction"] == row["satisfaction"]
                for row in functions
            )
        )
        self.assertTrue(
            all(
                row["arrival_coverage_status"] == "ok_recorder_crosschecked_by_tape"
                for row in classes
            )
        )
        self.assertAlmostEqual(
            next(row for row in classes if row["qos_class"] == "latency")[
                "completion_ratio"
            ],
            13 / 20,
        )
        self.assertGreaterEqual(float(fairness["jain_satisfaction"]), 0.0)
        self.assertLessEqual(float(fairness["jain_satisfaction"]), 1.0)

        _, unavailable_fairness, unavailable_functions = analyze_qos_run(
            _synthetic_artifacts(),
            sla_targets=None,
            workload_events=[{"frame": index, "dag_id": 0} for index in range(10)],
            require_arrival_coverage=True,
        )
        self.assertEqual(
            unavailable_fairness["fairness_status"],
            "unavailable_function_satisfaction",
        )
        self.assertTrue(math.isnan(unavailable_fairness["jain_satisfaction"]))
        self.assertTrue(
            all(
                math.isnan(row["normalized_satisfaction"])
                for row in unavailable_functions
            )
        )

        missing = _synthetic_artifacts()
        missing.frames[-1].pop("qos_function_tasks")
        with self.assertRaisesRegex(ValueError, "coverage is required but unavailable"):
            analyze_qos_run(
                missing,
                sla_targets=targets,
                workload_events=[{"frame": index, "dag_id": 0} for index in range(10)],
                require_arrival_coverage=True,
            )

    def test_features_and_scheduler_diagnostics_remain_run_level(self) -> None:
        function_rows = []
        for seed_index in range(1, 4):
            artifact = _synthetic_artifacts(f"E{seed_index:02d}")
            function_rows.extend(function_runtime_rows(artifact))
        correlations = per_run_feature_correlations(function_rows)
        self.assertEqual(len(correlations), 3 * 5 * 7)
        primary = [row for row in correlations if row["primary_pair"]]
        self.assertTrue(all(row["function_pairs"] == 6 for row in primary))
        summary = summarize_feature_correlations(
            correlations,
            bootstrap_resamples=200,
            permutation_resamples=2_000,
            seed=9,
        )
        self.assertTrue(all(row["total_runs"] == 3 for row in summary))
        diagnostics = analyze_scheduler_run(_synthetic_artifacts())
        self.assertAlmostEqual(float(diagnostics["welfare_gap_mean"]), 0.1)
        self.assertEqual(diagnostics["welfare_gap_applicability"], 1.0)
        self.assertEqual(diagnostics["inner_limit_hit_rate"], 0.2)
        self.assertEqual(diagnostics["nonconvergence_rate"], 0.2)
        self.assertEqual(diagnostics["process_peak_rss_mib"], 256.0)
        self.assertEqual(diagnostics["feedback_trace_status"], "ok")
        self.assertEqual(diagnostics["feedback_trace_rounds"], 7)
        self.assertEqual(diagnostics["feedback_applied_rounds"], 2)
        self.assertEqual(diagnostics["feedback_trace_invalid_rows"], 0)
        self.assertAlmostEqual(diagnostics["feedback_gap_control_mean"], 0.72 / 7)
        self.assertAlmostEqual(diagnostics["feedback_gap_control_p95"], 0.11)
        self.assertAlmostEqual(diagnostics["feedback_gamma_mean"], 0.2)
        self.assertAlmostEqual(diagnostics["feedback_price_multiplier_max"], 1.02)
        self.assertAlmostEqual(diagnostics["outer_assignment_change_rate"], 0.0)

    def test_stage_wait_metrics_are_exported_once_per_run(self) -> None:
        metrics = stage_wait_run_metrics(_synthetic_artifacts())
        self.assertEqual(metrics["completed_function_invocation_samples"], 45)
        self.assertEqual(metrics["stage_wait_coverage_status"], "ok")
        self.assertAlmostEqual(metrics["schedule_wait_mean_ms"], 1.0)
        self.assertAlmostEqual(metrics["cold_start_wait_mean_ms"], 1.0)
        self.assertAlmostEqual(metrics["data_wait_mean_ms"], 175.0 / 45.0)
        self.assertAlmostEqual(metrics["execution_mean_ms"], 220.0 / 45.0)
        empty = _synthetic_artifacts()
        empty.requests = []
        empty_metrics = stage_wait_run_metrics(empty)
        self.assertEqual(
            empty_metrics["stage_wait_coverage_status"],
            "unavailable_no_completed_function_invocations",
        )
        self.assertTrue(math.isnan(empty_metrics["schedule_wait_p95_ms"]))

    def test_active_differentiation_is_correlated_within_run_then_across_seeds(
        self,
    ) -> None:
        windows: list[dict[str, object]] = []
        expected: list[dict[str, object]] = []
        for seed_index in range(1, 4):
            artifact = _synthetic_artifacts(f"E{seed_index:02d}")
            current = window_differentiation_rows(artifact)
            self.assertEqual(len(current), 5)
            self.assertTrue(
                all(row["window_coverage_status"] == "ok" for row in current)
            )
            windows.extend(current)
            expected.append(
                {
                    key: current[0][key]
                    for key in (
                        "experiment_id",
                        "cell_id",
                        "run_id",
                        "seed",
                        "algorithm",
                        "load",
                        "node_count",
                        "topology",
                        "burst_pattern",
                        "qos_profile",
                    )
                }
            )

        correlations = per_run_differentiation_correlations(
            windows, expected_runs=expected
        )
        self.assertEqual(len(correlations), 3 * 4)
        self.assertTrue(all(row["window_pairs"] == 5 for row in correlations))
        self.assertTrue(all(math.isfinite(float(row["rho"])) for row in correlations))
        summary = summarize_differentiation_correlations(
            correlations,
            bootstrap_resamples=200,
            permutation_resamples=2_000,
            seed=29,
        )
        self.assertEqual(len(summary), 4)
        self.assertTrue(all(row["total_runs"] == 3 for row in summary))
        self.assertTrue(all(row["coverage_status"] == "ok" for row in summary))

        missing = _synthetic_artifacts("E99")
        for event in missing.nse_events:
            if event.get("kind") == "window":
                event["decision"].pop("active_differentiation_mean")
        missing_windows = window_differentiation_rows(missing)
        missing_correlations = per_run_differentiation_correlations(
            missing_windows,
            expected_runs=[
                {
                    key: missing_windows[0][key]
                    for key in (
                        "experiment_id",
                        "cell_id",
                        "run_id",
                        "seed",
                        "algorithm",
                        "load",
                        "node_count",
                        "topology",
                        "burst_pattern",
                        "qos_profile",
                    )
                }
            ],
        )
        self.assertTrue(
            all(
                row["status"] == "unavailable_no_eligible_windows"
                and math.isnan(float(row["rho"]))
                for row in missing_correlations
            )
        )

    def test_offline_reference_resource_observations_are_auditable(self) -> None:
        artifact = _synthetic_artifacts()
        with tempfile.TemporaryDirectory() as temporary:
            process_path = Path(temporary) / "build-process.json"
            process_path.write_text(
                json.dumps(
                    {
                        "schema_version": "NSE_PROCESS_OBSERVATION_V1",
                        "duration_seconds": 1.25,
                        "process_tree_cpu_seconds": 0.75,
                        "peak_process_tree_rss_bytes": 384 * 1024 * 1024,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            artifact.spec = {
                **artifact.spec,
                "reference_dependency": {
                    "bytes": 123456,
                    "build_process_observation_path": str(process_path),
                    "build_process_observation_sha256": hashlib.sha256(
                        process_path.read_bytes()
                    ).hexdigest(),
                },
            }
            artifact.summary = {
                **artifact.summary,
                "reference_load_us_total": 44,
            }
            artifact.nse_events.append(
                {
                    "kind": "run_summary",
                    "reference_load_us_total": 44,
                    "reference_load_thread_cpu_us_total": 31,
                    "reference_validation": {
                        "windows": 100,
                        "missing_ratio": 0.01,
                        "zero_ratio": 0.02,
                        "negative_ratio": 0.03,
                        "unavailable": 4,
                        "unavailable_ratio": 0.04,
                        "persist_failures": 5,
                        "offline_required_ok": False,
                    },
                }
            )
            diagnostics = analyze_scheduler_run(artifact)
            self.assertEqual(diagnostics["offline_build_wall_ms"], 1250.0)
            self.assertEqual(diagnostics["offline_build_cpu_ms"], 750.0)
            self.assertEqual(diagnostics["offline_build_peak_rss_mib"], 384.0)
            self.assertEqual(diagnostics["reference_table_bytes"], 123456.0)
            self.assertEqual(diagnostics["reference_table_load_us"], 44.0)
            self.assertEqual(diagnostics["reference_table_load_thread_cpu_us"], 31.0)
            self.assertEqual(diagnostics["reference_missing_ratio"], 0.01)
            self.assertEqual(diagnostics["reference_zero_ratio"], 0.02)
            self.assertEqual(diagnostics["reference_negative_ratio"], 0.03)
            self.assertEqual(diagnostics["reference_unavailable_windows"], 4.0)
            self.assertEqual(diagnostics["reference_unavailable_ratio"], 0.04)
            self.assertEqual(diagnostics["reference_persist_failures"], 5.0)
            self.assertEqual(diagnostics["reference_persist_failure_ratio"], 0.05)
            self.assertEqual(diagnostics["reference_offline_required_ok"], 0.0)
            self.assertEqual(
                diagnostics["reference_validation_status"],
                "reference_unavailable_observed;"
                "reference_persist_failure_observed;"
                "offline_required_not_ok_observed",
            )

    def test_nonpositive_reference_counts_are_observed_not_analysis_failures(
        self,
    ) -> None:
        artifact = _synthetic_artifacts()
        artifact.spec = {
            **artifact.spec,
            "reference_dependency": {"bytes": 64},
        }
        artifact.nse_events.append(
            {
                "kind": "run_summary",
                "reference_validation": {
                    "windows": 10,
                    "missing_ratio": 0.0,
                    "zero_ratio": 0.2,
                    "negative_ratio": 0.1,
                    "search_suboptimal": 1,
                    "search_suboptimal_ratio": 0.1,
                    "unavailable": 0,
                    "unavailable_ratio": 0.0,
                    "persist_failures": 0,
                    "offline_required_ok": True,
                },
            }
        )

        diagnostics = analyze_scheduler_run(artifact)

        self.assertEqual(diagnostics["reference_zero_ratio"], 0.2)
        self.assertEqual(diagnostics["reference_negative_ratio"], 0.1)
        self.assertEqual(diagnostics["reference_search_suboptimal_windows"], 1.0)
        self.assertEqual(diagnostics["reference_search_suboptimal_ratio"], 0.1)
        self.assertEqual(diagnostics["reference_validation_status"], "ok")

    def test_e3_e4_e9_bar_families_are_seed_paired_and_holm_adjusted(self) -> None:
        burst_runs = []
        qos_runs = []
        fairness_runs = []
        diagnostics = []
        for seed_index in range(1, 4):
            seed = f"E{seed_index:02d}"
            for algorithm_index, algorithm in enumerate(("Greedy", "NSESche")):
                shift = float(algorithm_index)
                common = {"algorithm": algorithm, "seed": seed}
                burst_runs.append(
                    {
                        **common,
                        "burst_pattern": "spike5x50ms",
                        "peak_queue": 20.0 - shift,
                        "recovery_time_ms": 100.0 - shift,
                        "restricted_recovery_time_ms": 100.0 - shift,
                        "recovery_observed": 0.8 + shift * 0.1,
                        "admission_drop": 2.0 - shift,
                        "admission_reject": 2.0 - shift,
                        "timeout": 2.0 - shift,
                        "latency_p95_ms": 30.0 - shift,
                        "latency_p99_ms": 40.0 - shift,
                    }
                )
                for qos_class in ("latency", "throughput", "cost"):
                    qos_runs.append(
                        {
                            **common,
                            "qos_class": qos_class,
                            "stage_latency_p95_ms": 30.0 - shift,
                            "stage_latency_p99_ms": 40.0 - shift,
                            "throughput_rps": 8.0 + shift,
                            "completion_ratio": 0.8 + shift * 0.1,
                            "direct_cost_mean": 1.2 - shift * 0.1,
                            "sla_violation_rate": 0.2 - shift * 0.05,
                        }
                    )
                fairness_runs.append(
                    {
                        **common,
                        "jain_satisfaction": 0.8 + shift * 0.1,
                        "worst10_satisfaction": 0.6 + shift * 0.1,
                    }
                )
                diagnostics.append(
                    {
                        **common,
                        "experiment_id": "E1",
                        "variant": "full",
                        "load": "high",
                        "node_count": 20,
                        "topology": "heterogeneous",
                        "burst_pattern": "steady",
                        "qos_profile": "mixed",
                        "placement_policy_wall_mean_us": 10.0 - shift,
                        "placement_policy_cpu_mean_us": 8.0 - shift,
                        "solve_mean_us": 6.0 - shift,
                        "process_peak_rss_mib": 100.0 - shift,
                        "inner_rounds_mean": 4.0 - shift,
                        "outer_rounds_mean": 3.0 - shift,
                        "inner_limit_hit_rate": 0.2 - shift * 0.1,
                        "outer_limit_hit_rate": 0.2 - shift * 0.1,
                        "oscillation_window_rate": 0.2 - shift * 0.1,
                        "nonconvergence_rate": 0.2 - shift * 0.1,
                        "reference_lookup_mean_us": 2.0 - shift,
                        "offline_build_wall_ms": 20.0 - shift,
                        "offline_build_cpu_ms": 18.0 - shift,
                        "offline_build_peak_rss_mib": 120.0 - shift,
                        "reference_table_bytes": 1000.0 - shift,
                        "reference_table_load_us": 3.0 - shift,
                        "reference_table_load_thread_cpu_us": 2.0 - shift,
                        "reference_missing_ratio": 0.1 - shift * 0.05,
                        "reference_zero_ratio": 0.1 - shift * 0.05,
                        "reference_negative_ratio": 0.1 - shift * 0.05,
                        "reference_feedback_eligible_ratio": 0.7 + shift * 0.1,
                        "reference_below_current_ratio": 0.1 - shift * 0.05,
                        "reference_search_suboptimal_ratio": 0.08 - shift * 0.04,
                        "reference_unavailable_ratio": 0.1 - shift * 0.05,
                        "reference_persist_failure_ratio": 0.1 - shift * 0.05,
                        "reference_offline_required_ok": 0.8 + shift * 0.1,
                        "welfare_gap_mean": 0.2 - shift * 0.05,
                        "welfare_gap_p95": 0.3 - shift * 0.05,
                        "welfare_gap_applicability": 0.8 + shift * 0.1,
                        "reference_cache_hit_rate": 0.8 + shift * 0.1,
                    }
                )
        tables = build_observability_comparisons(
            burst_runs=burst_runs,
            qos_runs=qos_runs,
            fairness_runs=fairness_runs,
            diagnostic_runs=diagnostics,
            bootstrap_resamples=200,
            permutation_resamples=2_000,
            seed=41,
        )
        for family in ("e3", "e4_qos", "e4_fairness", "e9"):
            self.assertTrue(tables[family], family)
            self.assertTrue(all(row["n_pairs"] == 3 for row in tables[family]))
            self.assertTrue(
                all(math.isfinite(float(row["p_holm"])) for row in tables[family])
            )

    def test_exact_poa_frozen_design_and_constructed_state_summary(self) -> None:
        raw_rows = []
        for players in (4, 6, 8):
            for state_index in range(100):
                pure_nash_exists = state_index >= 20
                optimum = 100.0
                ratio = (
                    1.0 + players / 100.0 + state_index / 10_000.0
                    if pure_nash_exists
                    else None
                )
                worst = optimum / ratio if ratio is not None else None
                raw_rows.append(
                    {
                        "schema": "NSE_EXACT_POA_RESULT_V1",
                        "state_id": f"p{players}-state-{state_index:03d}",
                        "nodes": 3,
                        "players": players,
                        "feasible_assignments": 27,
                        "pure_nash_equilibria": 2 if pure_nash_exists else 0,
                        "pure_nash_exists": pure_nash_exists,
                        "optimal_welfare": optimum,
                        "worst_nash_welfare": worst,
                        "exact_poa": ratio,
                        "relative_welfare_gap": (
                            (optimum - worst) / optimum if worst is not None else None
                        ),
                        "poa_applicable": pure_nash_exists,
                        "poa_definition": (
                            "optimal_social_welfare/" "worst_pure_nash_social_welfare"
                        ),
                        "formula_alignment": (
                            "NSESche individual utility and "
                            "social-welfare aggregation"
                        ),
                    }
                )
        with tempfile.TemporaryDirectory() as temporary:
            result_path = Path(temporary) / "exact-poa-results.jsonl"
            result_path.write_text(
                "".join(json.dumps(row) + "\n" for row in raw_rows),
                encoding="utf-8",
            )
            loaded = load_exact_poa_results(result_path)
            self.assertEqual(len(loaded), 300)
            self.assertTrue(
                all(row["inference_unit"] == "constructed_state" for row in loaded)
            )
            summary = summarize_exact_poa(loaded, bootstrap_resamples=100, seed=17)
            self.assertEqual([row["players"] for row in summary], [4, 6, 8])
            self.assertTrue(all(row["total_states"] == 100 for row in summary))
            self.assertTrue(all(row["poa_applicable_states"] == 80 for row in summary))
            self.assertTrue(
                all(
                    math.isfinite(float(row["exact_poa_bca_low"]))
                    and math.isfinite(float(row["exact_poa_bca_high"]))
                    for row in summary
                )
            )

            malformed = dict(raw_rows[0])
            malformed["poa_applicable"] = True
            malformed_path = Path(temporary) / "malformed.jsonl"
            malformed_path.write_text(json.dumps(malformed) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "formula-inconsistent"):
                load_exact_poa_results(malformed_path)


class ObservabilityFigureTests(unittest.TestCase):
    def test_fig11_to_fig13_visual_templates(self) -> None:
        algorithms = ("Greedy", "NSESche")
        timeseries = []
        for algorithm_index, algorithm in enumerate(algorithms):
            for time_ms in range(-20, 81, 5):
                active = 0 <= time_ms < 20
                for metric, base in (
                    ("arrival_rps", 100.0),
                    ("queue_total", 5.0),
                    ("throughput_rps", 90.0),
                    ("rolling_p95_ms", 20.0),
                    ("rolling_p99_ms", 22.0),
                ):
                    value = base * (1.0 + 0.5 * active) * (1.0 - algorithm_index * 0.1)
                    timeseries.append(
                        {
                            "algorithm": algorithm,
                            "burst_pattern": "spike5x50ms",
                            "time_relative_ms": time_ms,
                            "burst_active": active,
                            "metric": metric,
                            "mean": value,
                            "ci_low": value * 0.95,
                            "ci_high": value * 1.05,
                        }
                    )
        qos = []
        fairness = []
        burst_summary = []
        for algorithm_index, algorithm in enumerate(algorithms):
            for metric, value in (
                ("peak_queue", 20.0 - algorithm_index * 4.0),
                ("restricted_recovery_time_ms", 150.0 - algorithm_index * 20.0),
                ("recovery_observed", 0.8 + algorithm_index * 0.1),
                ("admission_drop", 0.0),
                ("admission_reject", 0.0),
                ("timeout", 1.0 - algorithm_index),
                ("latency_p95_ms", 35.0 - algorithm_index * 4.0),
                ("latency_p99_ms", 45.0 - algorithm_index * 5.0),
            ):
                burst_summary.append(
                    {
                        "algorithm": algorithm,
                        "burst_pattern": "spike5x50ms",
                        "metric": metric,
                        "mean": value,
                        "bca_low": max(0.0, value * 0.9),
                        "bca_high": value * 1.1,
                    }
                )
            for qos_class in ("latency", "throughput", "cost"):
                for metric, value in (
                    ("stage_latency_p95_ms", 30.0 - algorithm_index * 5.0),
                    ("throughput_rps", 8.0 + algorithm_index),
                    ("direct_cost_mean", 1.2 - algorithm_index * 0.1),
                    ("completion_ratio", 0.80 + algorithm_index * 0.08),
                    ("sla_violation_rate", 0.20 - algorithm_index * 0.05),
                ):
                    qos.append(
                        {
                            "algorithm": algorithm,
                            "qos_class": qos_class,
                            "metric": metric,
                            "mean": value,
                            "bca_low": value * 0.9,
                            "bca_high": value * 1.1,
                        }
                    )
            for metric, value in (
                ("jain_satisfaction", 0.85 + algorithm_index * 0.05),
                ("worst10_satisfaction", 0.65 + algorithm_index * 0.08),
            ):
                fairness.append(
                    {
                        "algorithm": algorithm,
                        "metric": metric,
                        "mean": value,
                        "bca_low": value - 0.03,
                        "bca_high": value + 0.03,
                    }
                )
        features = []
        for index, (feature, outcome) in enumerate(
            (
                ("h_ri", "queue_pressure_mean"),
                ("h_fc", "execution_mean_ms"),
                ("h_nd", "communication_wait_mean_ms"),
                ("h_pi", "throughput_shortfall_vs_run_max"),
                ("impact", "stage_latency_p95_ms"),
            )
        ):
            features.append(
                {
                    "feature": feature,
                    "outcome": outcome,
                    "primary_pair": True,
                    "mean_rho": 0.2 + index * 0.1,
                    "bca_low": 0.1 + index * 0.1,
                    "bca_high": 0.3 + index * 0.1,
                    "reject_holm": index > 1,
                }
            )
        differentiation = []
        for index, outcome in enumerate(
            (
                "placement_dispersion_normalized",
                "co_location_conflict_pair_ratio_proxy",
                "near_tie_player_ratio",
                "differentiation_changed_top_choice_ratio",
            )
        ):
            differentiation.append(
                {
                    "feature": "active_differentiation_mean",
                    "outcome": outcome,
                    "primary_pair": True,
                    "mean_rho": 0.15 + index * 0.1,
                    "bca_low": 0.05 + index * 0.1,
                    "bca_high": 0.25 + index * 0.1,
                    "reject_holm": index > 1,
                }
            )
        diagnostics = []
        diagnostic_metrics = (
            "inner_rounds_mean",
            "outer_rounds_mean",
            "inner_limit_hit_rate",
            "outer_limit_hit_rate",
            "oscillation_window_rate",
            "nonconvergence_rate",
            "placement_policy_wall_mean_us",
            "placement_policy_cpu_mean_us",
            "solve_mean_us",
            "reference_lookup_total_us",
            "welfare_gap_mean",
            "welfare_gap_p95",
            "welfare_gap_applicability",
            "reference_cache_hit_rate",
            "process_peak_rss_mib",
            "offline_build_wall_ms",
            "offline_build_cpu_ms",
            "offline_build_peak_rss_mib",
            "reference_table_bytes",
            "reference_table_load_us",
            "reference_table_load_thread_cpu_us",
            "reference_lookup_mean_us",
            "reference_missing_ratio",
            "reference_zero_ratio",
            "reference_negative_ratio",
            "reference_unavailable_ratio",
            "reference_persist_failure_ratio",
            "reference_offline_required_ok",
        )
        for algorithm_index, algorithm in enumerate(algorithms):
            for metric_index, metric in enumerate(diagnostic_metrics):
                if (
                    metric.endswith("_rate")
                    or metric.endswith("_ratio")
                    or metric
                    in {
                        "welfare_gap_mean",
                        "welfare_gap_p95",
                        "welfare_gap_applicability",
                        "reference_cache_hit_rate",
                        "reference_offline_required_ok",
                    }
                ):
                    value = 0.10 + algorithm_index * 0.08 + metric_index * 0.005
                else:
                    value = 0.1 * (metric_index + 1) * (algorithm_index + 1)
                diagnostics.append(
                    {
                        "experiment_id": "E1",
                        "load": "high",
                        "node_count": "20",
                        "algorithm": algorithm,
                        "metric": metric,
                        "mean": value,
                        "bca_low": value * 0.9,
                        "bca_high": value * 1.1,
                    }
                )
        burst_comparisons = [
            {
                "burst_pattern": "spike5x50ms",
                "metric": metric,
                "reference": "NSESche",
                "comparator": "Greedy",
                "p_holm": 0.01,
                "reject_holm": True,
            }
            for metric in (
                "peak_queue",
                "restricted_recovery_time_ms",
                "recovery_observed",
                "admission_drop",
                "admission_reject",
                "timeout",
                "latency_p95_ms",
                "latency_p99_ms",
            )
        ]
        qos_comparisons = [
            {
                "qos_class": qos_class,
                "metric": metric,
                "reference": "NSESche",
                "comparator": "Greedy",
                "p_holm": 0.01,
                "reject_holm": True,
            }
            for qos_class in ("latency", "throughput", "cost")
            for metric in (
                "stage_latency_p95_ms",
                "throughput_rps",
                "direct_cost_mean",
                "completion_ratio",
                "sla_violation_rate",
            )
        ]
        fairness_comparisons = [
            {
                "metric": metric,
                "reference": "NSESche",
                "comparator": "Greedy",
                "p_holm": 0.01,
                "reject_holm": True,
            }
            for metric in ("jain_satisfaction", "worst10_satisfaction")
        ]
        diagnostic_comparisons = [
            {
                "experiment_id": "E1",
                "load": "high",
                "node_count": "20",
                "metric": metric,
                "reference": "NSESche",
                "comparator": "Greedy",
                "p_holm": 0.01,
                "reject_holm": True,
            }
            for metric in diagnostic_metrics
        ]
        exact_poa = [
            {
                "nodes": 3,
                "players": players,
                "total_states": 100,
                "poa_applicable_states": 90 - index * 5,
                "poa_applicable_ratio": (90 - index * 5) / 100.0,
                "exact_poa_median": 1.05 + index * 0.04,
                "exact_poa_bca_low": 1.03 + index * 0.04,
                "exact_poa_bca_high": 1.08 + index * 0.04,
            }
            for index, players in enumerate((4, 6, 8))
        ]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = (
                (plot_fig11, (timeseries, root / "fig11"), 4),
                (
                    plot_fig12_burst,
                    (
                        burst_summary,
                        root / "fig12_burst",
                    ),
                    8,
                ),
                (plot_fig12, (qos, fairness, root / "fig12"), 6),
                (
                    plot_fig13,
                    (features, diagnostics, root / "fig13"),
                    10,
                ),
            )
            for function, arguments, expected_axes in calls:
                figure, paths = function(*arguments)
                try:
                    self.assertEqual(len(figure.axes), expected_axes)
                    for path in paths:
                        self.assertTrue(path.exists())
                        self.assertGreater(path.stat().st_size, 1_000)
                finally:
                    plt.close(figure)

            figure, _ = plot_fig13(
                features,
                diagnostics,
                root / "fig13_layout_audit",
            )
            try:
                reference_axis = next(
                    axis
                    for axis in figure.axes
                    if any(
                        "(i) Reference Status" in text.get_text() for text in axis.texts
                    )
                )
                self.assertIn(
                    "Offline-required\nOK",
                    [label.get_text() for label in reference_axis.get_xticklabels()],
                )
                figure.canvas.draw()
                legend_box = figure.legends[0].get_window_extent()
                note = next(
                    text
                    for text in figure.texts
                    if text.get_text().startswith("Error bars:")
                )
                self.assertFalse(legend_box.overlaps(note.get_window_extent()))
            finally:
                plt.close(figure)

            figure, _ = plot_fig11(
                timeseries,
                root / "fig11_censor_audit",
                run_metrics=[
                    {
                        "burst_pattern": "spike5x50ms",
                        "recovery_status": "right_censored",
                    }
                ],
                filters={"burst_pattern": "spike5x50ms"},
            )
            try:
                self.assertTrue(
                    any(
                        "right-censored: 1" in text.get_text()
                        for axis in figure.axes
                        for text in axis.texts
                    )
                )
            finally:
                plt.close(figure)

            figure, _ = plot_fig12_burst(
                burst_summary,
                root / "fig12_burst_significance",
                comparisons=burst_comparisons,
                filters={"burst_pattern": "spike5x50ms"},
            )
            try:
                self.assertTrue(
                    any(
                        "*" in text.get_text()
                        for axis in figure.axes
                        for text in axis.texts
                    )
                )
            finally:
                plt.close(figure)

            figure, _ = plot_fig12(
                qos,
                fairness,
                root / "fig12_significance",
                qos_comparisons=qos_comparisons,
                fairness_comparisons=fairness_comparisons,
            )
            try:
                self.assertTrue(
                    any(
                        "*" in text.get_text()
                        for axis in figure.axes
                        for text in axis.texts
                    )
                )
            finally:
                plt.close(figure)

            figure, paths = plot_fig13(
                features,
                diagnostics,
                root / "fig13_with_exact_poa",
                differentiation_summary=differentiation,
                diagnostic_comparisons=diagnostic_comparisons,
                exact_poa_summary=exact_poa,
            )
            try:
                self.assertEqual(len(figure.axes), 12)
                self.assertTrue(
                    any(
                        "Exact Pure PoA" in text.get_text()
                        for axis in figure.axes
                        for text in axis.texts
                    )
                )
                self.assertTrue(
                    any(
                        "*" in text.get_text()
                        for axis in figure.axes
                        for text in axis.texts
                    )
                )
                for path in paths:
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 1_000)
            finally:
                plt.close(figure)


if __name__ == "__main__":
    unittest.main()
