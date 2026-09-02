from __future__ import annotations

import csv
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.container import ErrorbarContainer

from scripts.reviewer_experiments.analysis.stats import (
    bca_interval,
    holm_adjust,
    paired_effect_sizes,
    paired_permutation_test,
    precision_assessment,
)
from scripts.reviewer_experiments.analysis.protocol_results import (
    VARIANT_NAMES,
    _sealed_source_allowlist,
    _nse_summary_metrics,
    export_canonical_protocol_results,
    load_canonical_protocol_results,
    materialize_analysis_reuse_rows,
)
from scripts.reviewer_experiments.protocol.matrix import (
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.util import object_hash
from scripts.reviewer_experiments.analysis.summarize_runs import (
    build_extension_decisions,
    build_precision_table,
    collapse_to_run_level,
    paired_comparisons,
    run_pipeline,
    summarize_run_level,
)
from scripts.reviewer_experiments.figures.plot_figures import (
    build_fig7_ci_table,
    plot_fig5,
    plot_fig6,
    plot_fig7,
    plot_fig8,
    plot_fig9,
    plot_fig10,
)
from scripts.reviewer_experiments.figures.style import ABLATION_ORDER


def _seal_formal_manifest(payload: dict) -> dict:
    """Return a small hash-consistent formal manifest for exporter tests."""

    manifest = dict(payload)
    manifest["phase"] = "formal"
    manifest["formal_results_eligible"] = True
    manifest.pop("manifest_hash", None)
    manifest["manifest_hash"] = object_hash(manifest)
    return manifest


def _write_canonical_audit(
    directory: Path, run: dict, manifest_hash: str, result_relative_path: str
) -> None:
    inventory = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        inventory.append(
            {
                "relative_path": path.relative_to(directory).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    audit = {
        "schema_version": "NSE_RUN_AUDIT_MANIFEST_V1",
        "status": "canonical",
        "protocol_manifest": {"manifest_hash": manifest_hash},
        "run": {
            "run_id": run["run_id"],
            "run_spec_hash": run["run_spec_hash"],
            "experiment_id": run.get("experiment_id"),
            "cell_id": run.get("cell_id"),
            "method": run["method"],
            "variant": run["variant"],
            "frozen_spec": dict(run),
        },
        "final_artifacts": inventory,
    }
    audit["audit_manifest_hash"] = object_hash(audit)
    (directory / "manifest.json").write_text(json.dumps(audit), encoding="utf-8")


def _write_pairing_audit(path: Path, manifest: dict, canonical: Path) -> None:
    runtime = {
        "runtime_binary_sha256": "a" * 64,
        "runtime_git_commit": "b" * 40,
        "runtime_python_executable_sha256": "c" * 64,
        "runtime_cargo_lock_sha256": "d" * 64,
    }
    groups = []
    by_seed = {}
    for run in manifest["runs"]:
        by_seed.setdefault(str(run.get("seed")), []).append(run)
    for seed, runs in sorted(by_seed.items()):
        groups.append(
            {
                "seed": seed,
                "consensus": dict(runtime),
                "runs": [{"run_id": run["run_id"], **runtime} for run in runs],
            }
        )
    report = {
        "schema": "NSE_PAIRED_ENVIRONMENT_AUDIT_V1",
        "canonical_root": str(canonical.resolve()),
        "protocol_manifest_sha256": manifest["manifest_hash"],
        "run_count": len(manifest["runs"]),
        "runtime_identity_scope": "all_audited_runs",
        "global_runtime_consensus": dict(runtime),
        "groups": groups,
        "passed": True,
        "failures": [],
    }
    path.write_text(json.dumps(report), encoding="utf-8")


class StatisticsTests(unittest.TestCase):
    def test_bca_interval_is_deterministic_and_contains_center(self) -> None:
        sample = np.arange(1.0, 21.0)
        first = bca_interval(sample, n_resamples=2_000, seed=7)
        second = bca_interval(sample, n_resamples=2_000, seed=7)
        self.assertEqual(first["low"], second["low"])
        self.assertEqual(first["high"], second["high"])
        self.assertLess(first["low"], np.mean(sample))
        self.assertGreater(first["high"], np.mean(sample))

    def test_paired_permutation_and_effect_sizes(self) -> None:
        comparator = np.arange(10.0)
        reference = comparator + 1.0
        test = paired_permutation_test(reference, comparator, exact_threshold=16)
        effects = paired_effect_sizes(reference, comparator)
        self.assertTrue(test["exact"])
        self.assertLess(test["p_value"], 0.01)
        self.assertEqual(effects["rank_biserial"], 1.0)
        self.assertTrue(math.isinf(effects["cohen_dz"]))

    def test_paired_comparisons_export_relative_change_and_ratio_ci(self) -> None:
        rows = []
        for index in range(1, 6):
            rows.extend(
                [
                    {
                        "scenario": "middle",
                        "seed": f"E{index:02d}",
                        "algorithm": "NSESche",
                        "throughput": 2.0 * index,
                    },
                    {
                        "scenario": "middle",
                        "seed": f"E{index:02d}",
                        "algorithm": "Greedy",
                        "throughput": 1.0 * index,
                    },
                ]
            )
        result = paired_comparisons(
            rows,
            context_columns=("scenario",),
            treatment_column="algorithm",
            reference="NSESche",
            pair_column="seed",
            metrics=("throughput",),
            bootstrap_resamples=200,
            permutation_resamples=200,
            seed=3,
        )[0]
        self.assertEqual(result["relative_change_status"], "ok")
        self.assertAlmostEqual(result["paired_ratio_reference_over_comparator"], 2.0)
        self.assertAlmostEqual(
            result["relative_change_reference_minus_comparator"], 1.0
        )
        self.assertTrue(math.isfinite(result["paired_ratio_ci_low"]))
        self.assertTrue(math.isfinite(result["paired_ratio_ci_high"]))
        zero_rows = rows + [
            {
                "scenario": "zero",
                "seed": "E01",
                "algorithm": "NSESche",
                "throughput": 1.0,
            },
            {
                "scenario": "zero",
                "seed": "E01",
                "algorithm": "Greedy",
                "throughput": 0.0,
            },
        ]
        zero = paired_comparisons(
            zero_rows,
            context_columns=("scenario",),
            treatment_column="algorithm",
            reference="NSESche",
            pair_column="seed",
            metrics=("throughput",),
            bootstrap_resamples=100,
            permutation_resamples=100,
            seed=3,
        )[-1]
        self.assertEqual(zero["relative_change_status"], "undefined_zero_comparator")
        self.assertTrue(math.isnan(zero["paired_ratio_reference_over_comparator"]))
        overflow_rows = [
            {
                "scenario": "overflow",
                "seed": "E01",
                "algorithm": "NSESche",
                "throughput": 1.0e308,
            },
            {
                "scenario": "overflow",
                "seed": "E01",
                "algorithm": "Greedy",
                "throughput": 1.0e-308,
            },
        ]
        overflow = paired_comparisons(
            overflow_rows,
            context_columns=("scenario",),
            treatment_column="algorithm",
            reference="NSESche",
            pair_column="seed",
            metrics=("throughput",),
            bootstrap_resamples=100,
            permutation_resamples=100,
            seed=3,
        )[0]
        self.assertEqual(
            overflow["relative_change_status"], "undefined_nonfinite_ratio"
        )
        self.assertEqual(overflow["relative_change_nonfinite_n"], 1)

    def test_holm_adjustment(self) -> None:
        adjusted, rejected = holm_adjust([0.01, 0.03, 0.04], alpha=0.05)
        np.testing.assert_allclose(adjusted, [0.03, 0.06, 0.06])
        self.assertEqual(rejected, [True, False, False])

    def test_precision_rule_uses_width_not_outcome(self) -> None:
        precise = 100.0 + np.linspace(-0.05, 0.05, 20)
        imprecise = np.asarray([1.0, 100.0] * 10)
        precise_result = precision_assessment(
            precise, n_resamples=1_000, seed=1, target_relative_half_width=0.10
        )
        imprecise_result = precision_assessment(
            imprecise, n_resamples=1_000, seed=1, target_relative_half_width=0.10
        )
        self.assertEqual(precise_result["decision"], "stop_at_n10")
        self.assertEqual(imprecise_result["recommended_n"], 20)
        self.assertFalse(imprecise_result["precision_met_n10"])

    def test_precision_trigger_thresholds_match_frozen_protocol(self) -> None:
        rows = [
            {
                "scenario": "homogeneous",
                "algorithm": "NSESche",
                "seed": f"E{index:02d}",
                "throughput": 2.0 + index * 0.001,
                "latency_p95_ms": 10.0 + index * 0.01,
                "latency": 8.0 + index * 0.01,
            }
            for index in range(1, 11)
        ]
        table = build_precision_table(
            rows,
            group_columns=("scenario", "algorithm"),
            metrics=("throughput", "latency_p95_ms", "latency"),
            bootstrap_resamples=200,
        )
        by_metric = {row["metric"]: row for row in table}
        self.assertEqual(by_metric["throughput"]["target_relative_half_width"], 0.05)
        self.assertEqual(
            by_metric["latency_p95_ms"]["target_relative_half_width"], 0.10
        )
        self.assertFalse(by_metric["throughput"]["controls_ci_extension"])
        self.assertFalse(by_metric["latency"]["controls_ci_extension"])
        self.assertTrue(
            by_metric["throughput"]["predeclared_precision_diagnostic"]
        )
        self.assertFalse(by_metric["latency"]["predeclared_precision_diagnostic"])
        self.assertEqual(
            by_metric["latency"]["decision"],
            "fixed_n20_bank_incomplete",
        )
        decisions = build_extension_decisions(
            table,
            context_columns=("scenario",),
            treatment_column="algorithm",
        )
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decision"], "fixed_n20_bank_required")
        self.assertEqual(decisions[0]["trigger_check_count"], 0)
        self.assertEqual(
            decisions[0]["extension_scope"],
            "fixed_paired_n20_all_methods",
        )

    def test_precision_stops_at_run_cap_when_one_derived_value_is_unavailable(
        self,
    ) -> None:
        rows = [
            {
                "scenario": "homogeneous",
                "algorithm": "NSESche",
                "seed": f"E{index:02d}",
                "qpr": None if index == 20 else (1.0 if index % 2 else 100.0),
            }
            for index in range(1, 21)
        ]
        table = build_precision_table(
            rows,
            group_columns=("scenario", "algorithm"),
            metrics=("qpr",),
            bootstrap_resamples=200,
        )
        self.assertEqual(len(table), 1)
        precision = table[0]
        self.assertEqual(precision["n_total"], 20)
        self.assertEqual(precision["n_finite"], 19)
        self.assertEqual(precision["available_n"], 19)
        self.assertFalse(precision["precision_met_n10"])
        self.assertEqual(precision["recommended_n"], 20)
        self.assertEqual(
            precision["decision"],
            "fixed_n20_complete_with_insufficient_finite_values",
        )

        decisions = build_extension_decisions(
            table,
            context_columns=("scenario",),
            treatment_column="algorithm",
        )
        self.assertEqual(decisions[0]["decision"], "fixed_n20_bank_complete")


class PipelineTests(unittest.TestCase):
    def test_nse_export_uses_fixed_throughput_and_drained_cohort_latency(self) -> None:
        metrics = _nse_summary_metrics(
            {
                "observation_time_ms": 4000,
                "frame_duration_ms": 0.5,
                "arrivals": 10,
                "completed": 10,
                "completion_ratio": 1.0,
                "throughput_requests_per_second": 2.5,
                "latency_ms": {"mean": 40.0, "p50": 30.0, "p95": 90.0, "p99": 100.0},
                "fixed_observation_window": {
                    "duration_ms": 1000,
                    "arrivals": 10,
                    "completed": 8,
                    "completion_ratio": 0.8,
                    "throughput_requests_per_second": 8.0,
                },
                "drained_arrival_cohort": {
                    "drain_end_frame": 4000,
                    "arrivals": 10,
                    "completed": 10,
                    "completion_ratio": 1.0,
                    "latency_ms": {
                        "mean": 140.0,
                        "p50": 130.0,
                        "p95": 190.0,
                        "p99": 200.0,
                    },
                },
            }
        )
        self.assertEqual(metrics["throughput_physical_rps"], 8.0)
        self.assertEqual(metrics["throughput"], 0.008)
        self.assertEqual(metrics["latency_mean_ms"], 140.0)
        self.assertEqual(metrics["drain_horizon_ms"], 2000.0)
        self.assertEqual(metrics["completion_rate"], 1.0)
        self.assertEqual(metrics["fixed_window_completion_rate"], 0.8)
        self.assertEqual(metrics["legacy_final_run_throughput_physical_rps"], 2.5)
        self.assertEqual(
            metrics["cohort_metric_source"],
            "explicit_fixed_window_and_drained_cohort",
        )

    def test_protocol_export_fails_closed_for_integration_smoke_shards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, manifest in enumerate(
                (
                    {
                        "formal_results_eligible": False,
                        "runs": [],
                    },
                    {
                        "integration_smoke_shard": {
                            "schema_version": "NSE_INTEGRATION_SMOKE_SHARD_V1"
                        },
                        "formal_results_eligible": True,
                        "runs": [],
                    },
                )
            ):
                with self.subTest(case=index):
                    path = root / f"smoke-{index}.json"
                    path.write_text(json.dumps(manifest), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "formal-results eligible"):
                        load_canonical_protocol_results(path, root / "canonical")

    def test_formal_export_requires_hash_consistent_pairing_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            manifest_payload = _seal_formal_manifest({"runs": []})
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires --pairing-audit"):
                export_canonical_protocol_results(
                    manifest_path=manifest,
                    canonical_root=canonical,
                    output_csv=root / "out.csv",
                    coverage_csv=root / "coverage.csv",
                )
            pairing = root / "pairing.json"
            _write_pairing_audit(pairing, manifest_payload, canonical)
            output, coverage = export_canonical_protocol_results(
                manifest_path=manifest,
                canonical_root=canonical,
                output_csv=root / "out.csv",
                coverage_csv=root / "coverage.csv",
                pairing_audit_path=pairing,
            )
            self.assertTrue(output.exists())
            self.assertTrue(coverage.exists())
            old_pairing = json.loads(pairing.read_text(encoding="utf-8"))
            old_pairing["groups"] = [{"consensus": {}, "runs": []}]
            old_pairing_path = root / "old_pairing.json"
            old_pairing_path.write_text(json.dumps(old_pairing), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "runtime consensus"):
                load_canonical_protocol_results(
                    manifest,
                    canonical,
                    pairing_audit_path=old_pairing_path,
                )
            no_global = json.loads(pairing.read_text(encoding="utf-8"))
            no_global.pop("global_runtime_consensus")
            no_global_path = root / "no_global_pairing.json"
            no_global_path.write_text(json.dumps(no_global), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "global runtime consensus"):
                load_canonical_protocol_results(
                    manifest,
                    canonical,
                    pairing_audit_path=no_global_path,
                )
            tampered = dict(manifest_payload)
            tampered["protocol_id"] = "tampered"
            tampered_path = root / "tampered.json"
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest_hash"):
                load_canonical_protocol_results(tampered_path, canonical)

    def test_ablation_label_names_the_exact_disabled_component(self) -> None:
        self.assertEqual(
            VARIANT_NAMES["no_coordination"], "w/o Nash–Social Coordination"
        )

    def test_protocol_canonical_export_and_unit_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            runs = []
            for method in ("greedy", "sche_nash"):
                run_id = f"E1.{method}.low.E01"
                run = {
                    "experiment_id": "E1",
                    "cell_id": f"E1.{method}.low.homogeneous.n20",
                    "method": method,
                    "variant": "full",
                    "seed": "E01",
                    "run_id": run_id,
                    "run_spec_hash": f"spec-{method}",
                    "workload_spec_hash": "paired-workload-hash",
                    "common_hpa_hash": "hpa-hash",
                    "workload": {
                        "request_freq": "low",
                        "topology": "homogeneous",
                        "qos_profile": "mixed",
                        "load_scale": 1.0,
                    },
                    "cluster": {"node_count": 20, "topology": "homogeneous"},
                }
                runs.append(run)
                directory = canonical / run_id
                directory.mkdir(parents=True)
                (directory / "qc_report.json").write_text(
                    json.dumps({"passed": True, "classification": "qc_pass"}),
                    encoding="utf-8",
                )
                result = {
                    "schema_version": "summary_json_v1",
                    "completed": True,
                    "provenance": {
                        "run_id": run_id,
                        "run_spec_hash": run["run_spec_hash"],
                        "seed": "E01",
                        "workload_spec_hash": "paired-workload-hash",
                        "common_hpa_hash": "hpa-hash",
                    },
                    "metrics": {
                        "throughput_rps": 2.0,
                        "latency_mean_ms": 5.0,
                        "cost": 1.0,
                        "scheduler_wall_us": 2500.0,
                    },
                }
                (directory / "result.json").write_text(
                    json.dumps(result), encoding="utf-8"
                )
            manifest_payload = _seal_formal_manifest(
                {"execution": {"result_relative_path": "result.json"}, "runs": runs}
            )
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
            for run in runs:
                _write_canonical_audit(
                    canonical / run["run_id"],
                    run,
                    manifest_payload["manifest_hash"],
                    "result.json",
                )
            exported, coverage = load_canonical_protocol_results(manifest, canonical)
            self.assertEqual(len(exported), 2)
            self.assertTrue(
                all(row["pair_id"] == "paired-workload-hash" for row in exported)
            )
            self.assertTrue(all(row["scheduler_latency"] == 2.5 for row in exported))
            self.assertEqual(
                {row["algorithm"] for row in exported}, {"Greedy", "NSESche"}
            )
            self.assertTrue(all(row["status"] == "ok" for row in coverage))

            pairing = root / "pairing_audit.json"
            _write_pairing_audit(pairing, manifest_payload, canonical)
            output, coverage_output = export_canonical_protocol_results(
                manifest_path=manifest,
                canonical_root=canonical,
                output_csv=root / "protocol_runs.csv",
                coverage_csv=root / "coverage.csv",
                pairing_audit_path=pairing,
            )
            self.assertTrue(output.exists())
            self.assertTrue(coverage_output.exists())

    def test_canonical_export_automatically_materializes_sealed_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            full_manifest = build_manifest(load_protocol_config(), "initial")
            run = next(
                item
                for item in full_manifest["runs"]
                if item["experiment_id"] == "E1"
                and item["method"] == "greedy"
                and item["seed"] == "E01"
                and item["workload"]["request_freq"] == "low"
                and item["workload"]["topology"] == "homogeneous"
            )
            rule = next(
                item
                for item in full_manifest["reuse_analyses"]
                if item["experiment_id"] == "E2"
            )
            directory = canonical / run["run_id"]
            directory.mkdir(parents=True)
            (directory / "qc_report.json").write_text(
                json.dumps({"passed": True, "classification": "qc_pass"}),
                encoding="utf-8",
            )
            (directory / "result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "summary_json_v1",
                        "completed": True,
                        "provenance": {
                            "run_id": run["run_id"],
                            "run_spec_hash": run["run_spec_hash"],
                            "seed": run["seed"],
                            "workload_spec_hash": run["workload_spec_hash"],
                            "common_hpa_hash": run["common_hpa_hash"],
                        },
                        "metrics": {"throughput": 1.25},
                    }
                ),
                encoding="utf-8",
            )
            manifest_payload = _seal_formal_manifest(
                {
                    "execution": {"result_relative_path": "result.json"},
                    "runs": [run],
                    "reuse_analyses": [rule],
                }
            )
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
            _write_canonical_audit(
                directory, run, manifest_payload["manifest_hash"], "result.json"
            )
            rows, coverage = load_canonical_protocol_results(manifest_path, canonical)
            self.assertEqual(len(rows), 2)
            physical = next(
                row for row in rows if row["analysis_record_kind"] == "formal_run"
            )
            reused = next(
                row
                for row in rows
                if row["analysis_record_kind"] == "materialized_reuse"
            )
            self.assertEqual(reused["experiment_id"], "E2")
            self.assertEqual(reused["scenario"], "weak_scaling")
            self.assertEqual(reused["source_run_id"], physical["run_id"])
            self.assertEqual(
                reused["source_workload_spec_hash"], physical["workload_spec_hash"]
            )
            self.assertEqual([row["status"] for row in coverage], ["ok", "ok"])

    def test_rust_summary_path_units_cost_qpr_and_peak_rss(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            run_id = "E1.sche_nash.middle.E01"
            run = {
                "experiment_id": "E1",
                "cell_id": "E1.sche_nash.middle.homogeneous.n20",
                "method": "sche_nash",
                "variant": "full",
                "seed": "E01",
                "run_id": run_id,
                "run_spec_hash": "spec-nash",
                "workload_spec_hash": "paired-workload-hash",
                "common_hpa_hash": "hpa-hash",
                "workload": {
                    "request_freq": "middle",
                    "topology": "homogeneous",
                    "qos_profile": "mixed",
                    "load_scale": 1.0,
                },
                "cluster": {"node_count": 20, "topology": "homogeneous"},
            }
            directory = canonical / run_id
            result_path = directory / "reviewer_records" / run_id / "summary.json"
            result_path.parent.mkdir(parents=True)
            (directory / "qc_report.json").write_text(
                json.dumps({"passed": True, "classification": "qc_pass"}),
                encoding="utf-8",
            )
            result_path.write_text(
                json.dumps(
                    {
                        "schema": "NSE_SUMMARY_V1",
                        "run_id": run_id,
                        "protocol_version": "reviewer-v1",
                        "run_complete": True,
                        "arrivals": 2200,
                        "completed": 2000,
                        "completion_ratio": 2000 / 2200,
                        "throughput_requests_per_second": 2000.0,
                        "latency_ms": {
                            "mean": 5.0,
                            "p50": 4.0,
                            "p95": 8.0,
                            "p99": 11.0,
                        },
                        "simulator_internal_cost_total": 1000.0,
                        "simulator_internal_cost_per_completed_request": 0.5,
                        "queue_peak": 12,
                        "queue_area_request_frames": 40,
                        "node_cpu_utilization_mean": 0.4,
                        "node_cpu_utilization_p95": 0.7,
                        "node_cpu_utilization_peak": 0.9,
                        "node_memory_utilization_mean": 0.3,
                        "node_memory_utilization_p95": 0.6,
                        "node_memory_utilization_peak": 0.8,
                        "scheduler_window_count": 2,
                        "placement_policy_wall_ns": {
                            "mean": 500_000.0,
                            "p50": 400_000.0,
                            "p95": 600_000.0,
                            "p99": 600_000.0,
                            "max": 600_000,
                        },
                        "placement_policy_thread_cpu_ns": {
                            "mean": 250_000.0,
                            "p50": 200_000.0,
                            "p95": 300_000.0,
                            "p99": 300_000.0,
                            "max": 300_000,
                        },
                        "scheduler_wall_ns": {
                            "mean": 2_500_000.0,
                            "p50": 2_000_000.0,
                            "p95": 3_000_000.0,
                            "p99": 3_000_000.0,
                            "max": 3_000_000,
                        },
                        "scheduler_thread_cpu_ns": {
                            "mean": 1_250_000.0,
                            "p50": 1_000_000.0,
                            "p95": 1_500_000.0,
                            "p99": 1_500_000.0,
                            "max": 1_500_000,
                        },
                        "admission_drop": 0,
                        "admission_reject": 0,
                        "timeout": 0,
                    }
                ),
                encoding="utf-8",
            )
            (directory / "process_observation.json").write_text(
                json.dumps(
                    {
                        "schema_version": "NSE_PROCESS_OBSERVATION_V1",
                        "peak_process_tree_rss_bytes": 128 * 1024 * 1024,
                        "process_tree_cpu_seconds": 3.25,
                    }
                ),
                encoding="utf-8",
            )
            manifest_payload = _seal_formal_manifest(
                {
                    "execution": {
                        "result_relative_path": (
                            "reviewer_records/{run_id}/summary.json"
                        )
                    },
                    "runs": [run],
                }
            )
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
            _write_canonical_audit(
                directory,
                run,
                manifest_payload["manifest_hash"],
                "reviewer_records/{run_id}/summary.json",
            )

            exported, coverage = load_canonical_protocol_results(manifest, canonical)
            self.assertEqual([item["status"] for item in coverage], ["ok"])
            self.assertEqual(len(exported), 1)
            row = exported[0]
            self.assertEqual(Path(row["result_path"]), result_path.resolve())
            self.assertEqual(row["result_schema"], "NSE_SUMMARY_V1")
            self.assertAlmostEqual(row["throughput_physical_rps"], 2000.0)
            self.assertAlmostEqual(row["throughput"], 2.0)
            self.assertEqual(row["throughput_unit"], "10^3 requests/s (= requests/ms)")
            self.assertAlmostEqual(row["cost"], 0.5)
            self.assertAlmostEqual(row["simulator_internal_cost_total"], 1000.0)
            self.assertAlmostEqual(row["latency"], 5.0)
            self.assertAlmostEqual(row["scheduler_latency"], 0.5)
            self.assertAlmostEqual(row["scheduler_cpu"], 0.25)
            self.assertAlmostEqual(row["mechanism_total_wall_us"], 2500.0)
            self.assertAlmostEqual(row["mechanism_total_thread_cpu_us"], 1250.0)
            self.assertEqual(row["scheduler_latency_scope"], "placement policy only")
            self.assertAlmostEqual(row["scheduler_peak_memory"], 128.0)
            self.assertAlmostEqual(row["process_peak_rss_mb"], 128.0)

            collapsed = collapse_to_run_level(exported)
            self.assertEqual(collapsed[0]["qpr_status"], "ok")
            self.assertAlmostEqual(collapsed[0]["qpr"], 0.8)

    def test_manifest_reuse_rules_materialize_all_planned_reused_cells(self) -> None:
        manifest = build_manifest(load_protocol_config(), "initial")
        e1_runs = [run for run in manifest["runs"] if run["experiment_id"] == "E1"]
        source_rows = [
            {
                "experiment_id": "E1",
                "cell_id": run["cell_id"],
                "scenario": run["workload"]["topology"],
                "load": run["workload"]["request_freq"],
                "node_count": run["cluster"]["node_count"],
                "algorithm": run["method"],
                "variant": "",
                "seed": run["seed"],
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_spec_hash": run["workload_spec_hash"],
                "common_hpa_hash": run["common_hpa_hash"],
                "result_path": f"canonical/{run['run_id']}/result.json",
                "throughput": 1.0,
            }
            for run in e1_runs
        ]
        reused, coverage = materialize_analysis_reuse_rows(manifest, source_rows)
        counts = {
            experiment_id: sum(row["experiment_id"] == experiment_id for row in reused)
            for experiment_id in ("E2", "E5", "E6", "E7")
        }
        self.assertEqual(counts, {"E2": 300, "E5": 30, "E6": 200, "E7": 30})
        self.assertEqual(len(coverage), sum(counts.values()))
        self.assertTrue(all(row["status"] == "ok" for row in coverage))
        self.assertTrue(
            all(row["analysis_record_kind"] == "materialized_reuse" for row in reused)
        )
        self.assertTrue(
            all(row["source_run_id"] and row["source_run_spec_hash"] for row in reused)
        )
        self.assertTrue(
            all(
                row["source_workload_spec_hash"] == row["workload_spec_hash"]
                for row in reused
            )
        )
        e7_centres = [row for row in reused if row["experiment_id"] == "E7"]
        self.assertEqual(
            {row["seed"] for row in e7_centres}, {f"E{i:02d}" for i in range(1, 11)}
        )
        self.assertTrue(
            all(row["price_feedback_rate"] is not None for row in e7_centres)
        )

    def test_sealed_e5_lineage_limits_seed_all_source_to_declared_initial_rows(
        self,
    ) -> None:
        """A bound E1 seed-stage=all source must not inflate E5 projections."""

        manifest = build_manifest(load_protocol_config(), "initial")
        e5_rule = next(
            rule for rule in manifest["reuse_analyses"] if rule["experiment_id"] == "E5"
        )
        source_runs = [
            run
            for run in manifest["runs"]
            if run["experiment_id"] == "E1"
            and run["method"] == "sche_nash"
            and run["workload"]["topology"] == "heterogeneous"
            and run["workload"]["request_freq"] == "low"
            and run["seed"] in {"E01", "E02"}
        ]
        self.assertEqual({run["seed"] for run in source_runs}, {"E01", "E02"})
        selected = next(run for run in source_runs if run["seed"] == "E01")
        lineage_entry = {
            "source_experiment_id": "E1",
            "source_topology": "heterogeneous",
            "source_node_count": 20,
            "source_load_scale": 1.0,
            "target_experiment_id": "E5",
            "source_method": selected["method"],
            "source_load": selected["workload"]["request_freq"],
            "source_seed": selected["seed"],
            "source_variant": selected.get("variant", "full"),
            "source_workload_spec_hash": selected["workload_spec_hash"],
            "source_workload_tape_key": selected["workload_tape"]["key"],
            "source_cluster_sha256": object_hash(selected["cluster"]),
            "source_simulation_sha256": object_hash(selected["simulation"]),
            "source_environment_sha256": object_hash(selected["environment"]),
            "source_common_hpa_hash": selected["common_hpa_hash"],
            "reuse_rule_id": e5_rule["rule_id"],
        }
        target = {
            "formal_e5_e6_e7_initial_shard": {
                "e1_reuse_lineage": {"E5": [lineage_entry]},
                "sealed_e1_reuse_rules": {
                    "E5": {
                        "rule_id": e5_rule["rule_id"],
                        "rule_sha256": e5_rule["rule_sha256"],
                    }
                },
                "e1_reuse_projection_count": 1,
                "e1_reuse_unique_source_run_count": 1,
            }
        }
        allowlist = _sealed_source_allowlist(target, [e5_rule], source_runs)
        self.assertEqual(allowlist, {e5_rule["rule_id"]: {("sche_nash", "low", "E01")}})

        source_rows = [
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_spec_hash": run["workload_spec_hash"],
                "common_hpa_hash": run["common_hpa_hash"],
                "seed": run["seed"],
                "throughput": 1.0,
            }
            for run in source_runs
        ]
        reused, coverage = materialize_analysis_reuse_rows(
            {"manifest_hash": "target", "runs": [], "reuse_analyses": [e5_rule]},
            source_rows,
            source_runs=source_runs,
            source_allowlist_by_rule=allowlist,
        )
        self.assertEqual(len(reused), 1)
        self.assertEqual(reused[0]["seed"], "E01")
        self.assertEqual([row["status"] for row in coverage], ["ok"])

    def test_physical_e5_shard_requires_explicit_reuse_source_paths(self) -> None:
        """A physical-only shard must fail closed instead of exporting zero reuse rows."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = build_manifest(load_protocol_config(), "initial")
            target = _seal_formal_manifest(
                {
                    "execution": {"result_relative_path": "result.json"},
                    "runs": [],
                    "reuse_analyses": manifest["reuse_analyses"],
                    "formal_e5_e6_e7_initial_shard": {},
                }
            )
            path = root / "e5.json"
            path.write_text(json.dumps(target), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "supply --reuse-source-manifest"):
                load_canonical_protocol_results(path, root / "canonical")

    def test_e2_physical_export_remains_available_for_dedicated_merge(self) -> None:
        """E2's separate homogeneous-source merger must still see physical rows."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = build_manifest(load_protocol_config(), "initial")
            target = _seal_formal_manifest(
                {
                    "execution": {"result_relative_path": "result.json"},
                    "runs": [],
                    "reuse_analyses": manifest["reuse_analyses"],
                }
            )
            path = root / "e2.json"
            path.write_text(json.dumps(target), encoding="utf-8")
            rows, coverage = load_canonical_protocol_results(path, root / "canonical")
            self.assertEqual(rows, [])
            self.assertEqual(coverage, [])

    def test_reuse_rejects_incompatible_workload_without_copying_it(self) -> None:
        manifest = build_manifest(load_protocol_config(), "initial")
        source = next(
            run
            for run in manifest["runs"]
            if run["experiment_id"] == "E1"
            and run["method"] == "greedy"
            and run["seed"] == "E01"
            and run["workload"]["request_freq"] == "low"
            and run["workload"]["topology"] == "homogeneous"
        )
        source["workload_tape"]["runtime_load_scale"] = 2.0
        reduced_manifest = {
            "manifest_hash": manifest["manifest_hash"],
            "runs": [source],
            "reuse_analyses": manifest["reuse_analyses"],
        }
        source_row = {
            "run_id": source["run_id"],
            "run_spec_hash": source["run_spec_hash"],
            "workload_spec_hash": source["workload_spec_hash"],
            "common_hpa_hash": source["common_hpa_hash"],
        }
        reused, coverage = materialize_analysis_reuse_rows(
            reduced_manifest, [source_row]
        )
        self.assertEqual(reused, [])
        rejected = [
            row for row in coverage if row["status"] == "reuse_incompatible_source"
        ]
        self.assertEqual(len(rejected), 1)
        self.assertIn("runtime_load_scale", rejected[0]["detail"])

    def test_qpr_is_computed_per_run_before_the_mean(self) -> None:
        raw = [
            {
                "scenario": "homogeneous",
                "load": "low",
                "algorithm": "NSESche",
                "seed": "1",
                "run_id": "1",
                "throughput": "1",
                "cost": "1",
                "latency": "1",
            },
            {
                "scenario": "homogeneous",
                "load": "low",
                "algorithm": "NSESche",
                "seed": "2",
                "run_id": "2",
                "throughput": "9",
                "cost": "3",
                "latency": "3",
            },
        ]
        runs = collapse_to_run_level(raw)
        summary = summarize_run_level(
            runs,
            group_columns=["scenario", "load", "algorithm"],
            metrics=["qpr"],
            bootstrap_resamples=500,
            seed=3,
        )
        self.assertAlmostEqual(summary[0]["mean"], 1.0)
        ratio_of_means = 5.0 / (2.0 * 2.0)
        self.assertNotAlmostEqual(summary[0]["mean"], ratio_of_means)

    def test_invalid_qpr_is_flagged_not_silently_replaced(self) -> None:
        runs = collapse_to_run_level(
            [
                {
                    "algorithm": "NSESche",
                    "seed": "1",
                    "throughput": "inf",
                    "cost": "1",
                    "latency": "2",
                }
            ]
        )
        self.assertEqual(runs[0]["qpr_status"], "nonfinite_input")
        self.assertTrue(math.isnan(runs[0]["qpr"]))

    def test_end_to_end_csv_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "runs.csv"
            fields = [
                "scenario",
                "load",
                "algorithm",
                "seed",
                "run_id",
                "cost",
                "latency",
                "throughput",
            ]
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for seed in range(1, 21):
                    writer.writerow(
                        {
                            "scenario": "homogeneous",
                            "load": "low",
                            "algorithm": "NSESche",
                            "seed": seed,
                            "run_id": seed,
                            "cost": 1.0 + seed * 0.001,
                            "latency": 5.0 + seed * 0.01,
                            "throughput": 2.0 + seed * 0.002,
                        }
                    )
                    writer.writerow(
                        {
                            "scenario": "homogeneous",
                            "load": "low",
                            "algorithm": "Greedy",
                            "seed": seed,
                            "run_id": seed,
                            "cost": 2.0 + seed * 0.001,
                            "latency": 8.0 + seed * 0.01,
                            "throughput": 1.0 + seed * 0.002,
                        }
                    )
            outputs = run_pipeline(
                input_csv=source,
                output_dir=root / "analysis",
                group_columns=["scenario", "load", "algorithm"],
                metrics=["cost", "latency", "throughput", "qpr"],
                bootstrap_resamples=500,
                permutation_resamples=5_000,
                seed=11,
            )
            for path in outputs.values():
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)
            with outputs["comparisons"].open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                comparisons = list(csv.DictReader(handle))
            self.assertEqual(len(comparisons), 4)
            self.assertTrue(all(int(row["n_pairs"]) == 20 for row in comparisons))
            self.assertTrue(
                all(float(row["oriented_improvement"]) > 0.0 for row in comparisons)
            )


def _synthetic_run_rows() -> list[dict[str, object]]:
    rng = np.random.default_rng(42)
    rows: list[dict[str, object]] = []
    algorithms = ["Greedy", "FaaSRank", "NSESche"]
    loads = ["low", "middle", "high"]
    for scenario in ("homogeneous", "heterogeneous"):
        scenario_factor = 1.0 if scenario == "homogeneous" else 1.12
        for load_index, load in enumerate(loads, start=1):
            for algorithm_index, algorithm in enumerate(algorithms, start=1):
                advantage = (
                    0.72 if algorithm == "NSESche" else 1.0 + algorithm_index * 0.05
                )
                for seed in range(1, 11):
                    jitter = float(rng.normal(1.0, 0.015))
                    latency = 55.0 * load_index * scenario_factor * advantage * jitter
                    cost = 0.35 * load_index * scenario_factor * advantage * jitter
                    throughput = 2.1 / (load_index * advantage) * jitter
                    rows.append(
                        {
                            "scenario": scenario,
                            "load": load,
                            "algorithm": algorithm,
                            "variant": "",
                            "node_count": "",
                            "seed": seed,
                            "run_id": seed,
                            "cost": cost,
                            "latency": latency,
                            "throughput": throughput,
                            "cold_start_latency": latency * 0.30,
                            "queue_latency": latency * 0.25,
                            "execution_latency": latency * 0.45,
                            "scheduler_latency": (0.8 + algorithm_index * 0.2)
                            * load_index
                            * jitter,
                            "cpu_utilization": 0.35 + 0.08 * load_index,
                            "memory_utilization": 0.40 + 0.07 * load_index,
                        }
                    )
    for load_index, load in enumerate(loads, start=1):
        for variant_index, variant in enumerate(ABLATION_ORDER, start=1):
            advantage = 0.72 if variant == "NSESche" else 0.90 + variant_index * 0.05
            for seed in range(1, 11):
                jitter = float(rng.normal(1.0, 0.012))
                latency = 60.0 * load_index * advantage * jitter
                rows.append(
                    {
                        "scenario": "ablation",
                        "load": load,
                        "algorithm": "NSESche",
                        "variant": variant,
                        "node_count": "",
                        "seed": seed,
                        "run_id": seed,
                        "cost": 0.4 * load_index * advantage * jitter,
                        "latency": latency,
                        "throughput": 2.0 / (load_index * advantage) * jitter,
                        "cold_start_latency": latency * 0.30,
                        "queue_latency": latency * 0.25,
                        "execution_latency": latency * 0.45,
                        "scheduler_latency": 1.2 * load_index * jitter,
                        "cpu_utilization": 0.4 + 0.08 * load_index,
                        "memory_utilization": 0.45 + 0.07 * load_index,
                    }
                )
    for node_count in (20, 100, 500):
        for seed in range(1, 11):
            jitter = float(rng.normal(1.0, 0.01))
            rows.append(
                {
                    "scenario": "weak_scaling",
                    "load": "high",
                    "algorithm": "NSESche",
                    "variant": "",
                    "node_count": node_count,
                    "seed": seed,
                    "run_id": seed,
                    "cost": 0.5 * jitter,
                    "latency": 110.0 * jitter,
                    "throughput": node_count * 0.09 * jitter,
                    "cold_start_latency": 33.0 * jitter,
                    "queue_latency": 27.5 * jitter,
                    "execution_latency": 49.5 * jitter,
                    "scheduler_latency": math.log2(node_count) * 0.2 * jitter,
                    "cpu_utilization": 0.62 * jitter,
                    "memory_utilization": 0.58 * jitter,
                }
            )
    return collapse_to_run_level(rows)


class FigureTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_rows = _synthetic_run_rows()
        cls.summary = summarize_run_level(
            cls.run_rows,
            group_columns=["scenario", "load", "node_count", "algorithm", "variant"],
            metrics=[
                "cost",
                "latency",
                "throughput",
                "qpr",
                "cold_start_latency",
                "queue_latency",
                "execution_latency",
                "scheduler_latency",
                "cpu_utilization",
                "memory_utilization",
            ],
            bootstrap_resamples=300,
            seed=17,
        )

    def test_all_templates_render_with_error_bars(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plot_calls = [
                (plot_fig5, root / "fig5", {"scenario": "ablation"}, 4),
                (plot_fig6, root / "fig6", {"scenario": "homogeneous"}, 4),
                (plot_fig8, root / "fig8", {"scenario": "homogeneous"}, 1),
                (plot_fig9, root / "fig9", {"scenario": "heterogeneous"}, 4),
                (plot_fig10, root / "fig10", {"scenario": "weak_scaling"}, 6),
            ]
            for function, prefix, filters, expected_axes in plot_calls:
                figure, paths = function(self.summary, prefix, filters=filters)
                try:
                    self.assertEqual(len(figure.axes), expected_axes)
                    self.assertTrue(
                        any(
                            isinstance(container, ErrorbarContainer)
                            for axis in figure.axes
                            for container in axis.containers
                        ),
                        f"{function.__name__} did not create error bars",
                    )
                    if function in {plot_fig5, plot_fig6, plot_fig9, plot_fig10}:
                        self.assertTrue(
                            any("10^3" in axis.get_ylabel() for axis in figure.axes),
                            f"{function.__name__} does not label the 10^3 requests/s scale",
                        )
                    if function is plot_fig8:
                        self.assertIn("Placement Decision", figure.axes[0].get_ylabel())
                    if function is plot_fig5:
                        legend_labels = {
                            text.get_text()
                            for legend in figure.legends
                            for text in legend.get_texts()
                        }
                        self.assertIn("w/o Nash–Social Coordination", legend_labels)
                    for path in paths:
                        self.assertTrue(path.exists())
                        self.assertGreater(path.stat().st_size, 1_000)
                finally:
                    plt.close(figure)

    def test_fig6_falls_back_to_total_latency_when_components_are_unavailable(
        self,
    ) -> None:
        component_metrics = {
            "cold_start_latency",
            "queue_latency",
            "execution_latency",
        }
        summary = [
            {
                **row,
                **(
                    {
                        "mean": math.nan,
                        "bca_low": math.nan,
                        "bca_high": math.nan,
                        "n_finite": 0,
                    }
                    if row.get("metric") in component_metrics
                    else {}
                ),
            }
            for row in self.summary
        ]
        with tempfile.TemporaryDirectory() as temporary:
            figure, _ = plot_fig6(
                summary,
                Path(temporary) / "fig6_missing_components",
                filters={"scenario": "homogeneous"},
            )
            try:
                latency_axis = figure.axes[0]
                self.assertTrue(
                    any(patch.get_height() > 0.0 for patch in latency_axis.patches),
                    "total latency bars disappeared when component rows were unavailable",
                )
                self.assertFalse(
                    any(axis.get_legend() is not None for axis in figure.axes)
                )
                self.assertEqual(len(figure.legends), 1)
                self.assertEqual(
                    [text.get_text() for text in figure.legends[0].get_texts()],
                    ["Greedy", "FaaSRank", "NSESche"],
                )
                self.assertIn(
                    "sim. units/completed request", figure.axes[1].get_ylabel()
                )
            finally:
                plt.close(figure)

    def test_fig7_is_frozen_ten_by_three_with_explicit_na_and_ci_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prefix = Path(temporary) / "fig7"
            figure, paths, table = plot_fig7(
                self.summary,
                prefix,
                filters={"scenario": "homogeneous"},
            )
            try:
                # Two image axes plus two colorbar axes.
                self.assertEqual(len(figure.axes), 4)
                self.assertEqual(len(table), 2 * 10 * 3)
                unavailable = [
                    row for row in table if row["coverage_status"] == "unavailable"
                ]
                self.assertTrue(unavailable)
                present = [row for row in table if row["coverage_status"] == "ok"]
                self.assertTrue(present)
                self.assertTrue(
                    all(row["inference_unit"] == "run_seed" for row in table)
                )
                self.assertTrue(all(row["ci_status"] == "ok" for row in present))
                self.assertTrue(
                    any(
                        text.get_text() == "NA"
                        for axis in figure.axes
                        for text in axis.texts
                    )
                )
                for path in paths:
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 1_000)
            finally:
                plt.close(figure)

        direct = build_fig7_ci_table(self.summary, filters={"scenario": "homogeneous"})
        self.assertEqual(len(direct), 60)


if __name__ == "__main__":
    unittest.main()
