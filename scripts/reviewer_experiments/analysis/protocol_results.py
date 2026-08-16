"""Export canonical protocol ``result.json`` files to the run-level CSV contract.

Only entries that are present under the protocol's ``canonical`` directory, have
a passing QC report, match their manifest provenance, and contain a completed
result are exported.  Both the protocol test schema and the simulator's formal
``NSE_SUMMARY_V1`` schema are supported. Missing/invalid entries remain visible
in the separate coverage CSV; strict mode refuses a partial formal-analysis
export.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .summarize_runs import (
        ALIASES,
        _canonical_algorithm,
        _canonical_load,
        _snake_case,
        write_csv,
    )
except ImportError:
    from summarize_runs import (  # type: ignore
        ALIASES,
        _canonical_algorithm,
        _canonical_load,
        _snake_case,
        write_csv,
    )


VARIANT_NAMES = {
    "full": "NSESche",
    "no_heterogeneity": "w/o Heterogeneity Modeling",
    "no_heterogeneity_modeling": "w/o Heterogeneity Modeling",
    "no_externality": "w/o Externality Modeling",
    "no_pricing": "w/o Congestion Pricing",
    "no_congestion_pricing": "w/o Congestion Pricing",
    "no_coordination": "w/o Nash–Social Coordination",
    "no_social": "w/o Nash–Social Coordination",
    "no_social_awareness": "w/o Nash–Social Coordination",
}

SCENARIOS = {
    "E2": "weak_scaling",
    "E3": "burst",
    "E4": "qos",
    "E5": "ablation",
    "E6": "welfare",
    "E7": "sensitivity",
    "E8": "feature_validation",
    "E9": "overhead",
}


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert_formal_results_eligible(manifest: Mapping[str, Any]) -> None:
    """Fail closed before reading outputs from an integration-smoke shard."""

    if "integration_smoke_shard" in manifest or (
        "formal_results_eligible" in manifest
        and manifest.get("formal_results_eligible") is not True
    ):
        raise ValueError(
            "integration-smoke shard results are explicitly ineligible for formal analysis"
        )


def _object_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _flatten_scalars(value: Any, *, prefix: str = "") -> dict[str, Any]:
    output: dict[str, Any] = {}
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_prefix = f"{prefix}_{key}" if prefix else str(key)
            output.update(_flatten_scalars(child, prefix=child_prefix))
    elif isinstance(value, (str, int, float, bool)) or value is None:
        output[_snake_case(prefix)] = value
    return output


def _metric_name_and_scale(name: str) -> tuple[str, float]:
    normalized = _snake_case(name)
    explicit = {
        "scheduler_wall_us": ("scheduler_latency", 1.0 / 1_000.0),
        "scheduler_thread_cpu_us": ("scheduler_cpu", 1.0 / 1_000.0),
        "scheduler_peak_memory_bytes": ("scheduler_peak_memory", 1.0 / (1024.0**2)),
        "process_peak_rss_bytes": ("process_peak_rss_mb", 1.0 / (1024.0**2)),
        "latency_breakdown_cold_start_ms": ("cold_start_latency", 1.0),
        "latency_breakdown_queue_ms": ("queue_latency", 1.0),
        "latency_breakdown_execution_ms": ("execution_latency", 1.0),
    }
    if normalized in explicit:
        return explicit[normalized]
    return ALIASES.get(normalized, normalized), 1.0


def _coverage_row(
    run: Mapping[str, Any], status: str, detail: str = ""
) -> dict[str, Any]:
    return {
        "experiment_id": run.get("experiment_id", ""),
        "cell_id": run.get("cell_id", ""),
        "run_id": run.get("run_id", ""),
        "seed": run.get("seed", ""),
        "method": run.get("method", ""),
        "status": status,
        "detail": detail,
    }


def _nse_summary_metrics(result: Mapping[str, Any]) -> dict[str, Any]:
    """Map the Rust summary to the legacy figure contract without hiding units.

    The submitted figures used requests/ms (numerically equal to
    ``10^3 requests/s``).  Rust deliberately records the physical rate in
    requests/s, so conversion happens exactly once at this analysis boundary.
    """

    fixed_window = result.get("fixed_observation_window")
    if not isinstance(fixed_window, Mapping):
        fixed_window = {}
    drained_cohort = result.get("drained_arrival_cohort")
    if not isinstance(drained_cohort, Mapping):
        drained_cohort = {}
    cohort_metric_source = (
        "explicit_fixed_window_and_drained_cohort"
        if fixed_window and drained_cohort
        else "legacy_top_level_fallback"
    )
    latency = drained_cohort.get("latency_ms", result.get("latency_ms"))
    if not isinstance(latency, Mapping):
        latency = {}
    frame_duration_ms = result.get("frame_duration_ms", 1.0)
    try:
        frame_duration_ms = float(frame_duration_ms)
    except (TypeError, ValueError):
        frame_duration_ms = 1.0
    if not math.isfinite(frame_duration_ms) or frame_duration_ms <= 0:
        frame_duration_ms = 1.0
    drain_end_frame = drained_cohort.get("drain_end_frame")
    if isinstance(drain_end_frame, (int, float)) and math.isfinite(
        float(drain_end_frame)
    ):
        drain_horizon_ms = float(drain_end_frame) * frame_duration_ms
    else:
        drain_horizon_ms = result.get("observation_time_ms")
    placement_wall = result.get("placement_policy_wall_ns")
    if not isinstance(placement_wall, Mapping):
        placement_wall = {}
    placement_cpu = result.get("placement_policy_thread_cpu_ns")
    if not isinstance(placement_cpu, Mapping):
        placement_cpu = {}
    mechanism_wall = result.get("scheduler_wall_ns")
    if not isinstance(mechanism_wall, Mapping):
        mechanism_wall = {}
    mechanism_cpu = result.get("scheduler_thread_cpu_ns")
    if not isinstance(mechanism_cpu, Mapping):
        mechanism_cpu = {}
    throughput_rps = fixed_window.get(
        "throughput_requests_per_second",
        result.get("throughput_requests_per_second"),
    )
    throughput_1000_rps = (
        None if throughput_rps is None else float(throughput_rps) / 1000.0
    )
    return {
        # Figure/QPR quantity: requests/ms == 10^3 requests/s.
        "throughput": throughput_1000_rps,
        # Preserve the physical value for arrival/throughput reporting.
        "throughput_physical_rps": throughput_rps,
        "latency_mean_ms": latency.get("mean"),
        "latency_p50_ms": latency.get("p50"),
        "latency_p95_ms": latency.get("p95"),
        "latency_p99_ms": latency.get("p99"),
        # Fig. 5/6/9/10 cost is per completed request, not run-total cost.
        "cost": result.get("simulator_internal_cost_per_completed_request"),
        "simulator_internal_cost_total": result.get("simulator_internal_cost_total"),
        "completion_rate": drained_cohort.get(
            "completion_ratio", result.get("completion_ratio")
        ),
        "arrivals": drained_cohort.get("arrivals", result.get("arrivals")),
        "completed": drained_cohort.get("completed", result.get("completed")),
        "fixed_window_completed": fixed_window.get(
            "completed", result.get("completed")
        ),
        "fixed_window_completion_rate": fixed_window.get(
            "completion_ratio", result.get("completion_ratio")
        ),
        "observation_horizon_ms": fixed_window.get(
            "duration_ms", result.get("observation_time_ms")
        ),
        "drain_horizon_ms": drain_horizon_ms,
        "legacy_final_run_throughput_physical_rps": result.get(
            "throughput_requests_per_second"
        ),
        "cohort_metric_source": cohort_metric_source,
        "queue_peak": result.get("queue_peak"),
        "queue_area_request_frames": result.get("queue_area_request_frames"),
        "cpu_utilization": result.get("node_cpu_utilization_mean"),
        "cpu_utilization_p95": result.get("node_cpu_utilization_p95"),
        "cpu_utilization_peak": result.get("node_cpu_utilization_peak"),
        "memory_utilization": result.get("node_memory_utilization_mean"),
        "memory_utilization_p95": result.get("node_memory_utilization_p95"),
        "memory_utilization_peak": result.get("node_memory_utilization_peak"),
        # _metric_name_and_scale converts microseconds to figure milliseconds.
        "scheduler_wall_us": (
            None
            if placement_wall.get("mean") is None
            else float(placement_wall["mean"]) / 1000.0
        ),
        "scheduler_thread_cpu_us": (
            None
            if placement_cpu.get("mean") is None
            else float(placement_cpu["mean"]) / 1000.0
        ),
        # These are measured independently by the shared mechanism wrapper;
        # never estimate one timing scope by subtracting another.
        "mechanism_total_wall_us": (
            None
            if mechanism_wall.get("mean") is None
            else float(mechanism_wall["mean"]) / 1000.0
        ),
        "mechanism_total_thread_cpu_us": (
            None
            if mechanism_cpu.get("mean") is None
            else float(mechanism_cpu["mean"]) / 1000.0
        ),
        "drops": result.get("admission_drop"),
        "rejects": result.get("admission_reject"),
        "timeouts": result.get("timeout"),
    }


def _process_observation_metrics(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Return process-tree resource metrics in the analysis CSV contract.

    The monitor observes the adapter and simulator process tree.  Its peak RSS is
    therefore kept under an explicit process-tree name as well as the historical
    ``scheduler_peak_memory`` figure metric; both values are expressed in MiB.
    """

    peak_rss = observation.get("peak_process_tree_rss_bytes")
    process_cpu = observation.get("process_tree_cpu_seconds")
    return {
        "scheduler_peak_memory_bytes": peak_rss,
        "process_peak_rss_bytes": peak_rss,
        "process_tree_cpu_seconds": process_cpu,
    }


def _load_process_observation(
    run_directory: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    path = run_directory / "process_observation.json"
    if not path.is_file():
        return None, "process_observation.json is missing"
    try:
        observation = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(observation, Mapping):
        return None, "process observation root is not an object"
    if observation.get("schema_version") != "NSE_PROCESS_OBSERVATION_V1":
        return None, "unsupported process observation schema"
    peak_rss = observation.get("peak_process_tree_rss_bytes")
    if (
        isinstance(peak_rss, bool)
        or not isinstance(peak_rss, (int, float))
        or not math.isfinite(float(peak_rss))
        or float(peak_rss) < 0.0
    ):
        return None, "peak_process_tree_rss_bytes is not a finite non-negative number"
    return dict(observation), None


_MISSING = object()


def _nested_value(document: Mapping[str, Any], dotted_path: str) -> Any:
    value: Any = document
    for part in dotted_path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _selector_matches(run: Mapping[str, Any], selector: Mapping[str, Any]) -> bool:
    for path, expected in selector.items():
        actual = _nested_value(run, str(path))
        if actual is _MISSING:
            return False
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _validated_reuse_rules(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_rules = manifest.get("reuse_analyses", [])
    if raw_rules is None:
        return []
    if not isinstance(raw_rules, list):
        raise ValueError("manifest reuse_analyses must be an array")
    rules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, Mapping):
            raise ValueError(f"reuse_analyses[{index}] is not an object")
        if raw_rule.get("kind") != "reuse_cells":
            continue
        rule = dict(raw_rule)
        if rule.get("schema_version") != "NSE_ANALYSIS_REUSE_RULE_V1":
            raise ValueError(f"reuse_analyses[{index}] has unsupported schema")
        rule_id = rule.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id or rule_id in seen:
            raise ValueError(f"reuse_analyses[{index}] has invalid/duplicate rule_id")
        seen.add(rule_id)
        stated_hash = rule.get("rule_sha256")
        hash_payload = dict(rule)
        hash_payload.pop("rule_sha256", None)
        if stated_hash != _object_hash(hash_payload):
            raise ValueError(f"reuse rule {rule_id} failed its content-hash check")
        if rule.get("source_experiment_id") != "E1":
            raise ValueError(f"reuse rule {rule_id} must name E1 as its source")
        selector = rule.get("source_selector")
        compatibility = rule.get("compatibility")
        projection = rule.get("target_projection")
        if not isinstance(selector, Mapping) or not selector:
            raise ValueError(f"reuse rule {rule_id} has no source selector")
        if not isinstance(compatibility, Mapping):
            raise ValueError(f"reuse rule {rule_id} has no compatibility contract")
        if (
            compatibility.get("workload_transform") != "identity"
            or compatibility.get("cluster_transform") != "identity"
        ):
            raise ValueError(
                f"reuse rule {rule_id} is not an identity workload/cluster projection"
            )
        if not isinstance(projection, Mapping):
            raise ValueError(f"reuse rule {rule_id} has no target projection")
        rules.append(rule)
    return rules


def _reuse_compatibility_issues(
    run: Mapping[str, Any],
    source_row: Mapping[str, Any],
    compatibility: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    required_exact = compatibility.get("required_exact", {})
    if not isinstance(required_exact, Mapping):
        return ["compatibility.required_exact is not an object"]
    for path, expected in required_exact.items():
        actual = _nested_value(run, str(path))
        if actual is _MISSING:
            issues.append(f"{path}=<missing>, expected {expected!r}")
        elif actual != expected:
            issues.append(f"{path}={actual!r}, expected {expected!r}")

    by_load = compatibility.get("required_by_load", {})
    if by_load:
        if not isinstance(by_load, Mapping):
            issues.append("compatibility.required_by_load is not an object")
        else:
            load = _nested_value(run, "workload.request_freq")
            expected_for_load = by_load.get(load)
            if not isinstance(expected_for_load, Mapping):
                issues.append(f"no compatibility contract for load {load!r}")
            else:
                for path, expected in expected_for_load.items():
                    actual = _nested_value(run, str(path))
                    if actual is _MISSING:
                        issues.append(f"{path}=<missing>, expected {expected!r}")
                    elif actual != expected:
                        issues.append(f"{path}={actual!r}, expected {expected!r}")

    required_hashes = compatibility.get("required_hash_fields", [])
    if not isinstance(required_hashes, list):
        issues.append("compatibility.required_hash_fields is not an array")
    else:
        for field in required_hashes:
            raw_hash = run.get(str(field))
            row_hash = source_row.get(str(field))
            if not isinstance(raw_hash, str) or not raw_hash:
                issues.append(f"source {field} is missing")
            elif row_hash != raw_hash:
                issues.append(f"exported {field} does not match source manifest")
    return issues


def _target_cell_id(run: Mapping[str, Any], projection: Mapping[str, Any]) -> str:
    template = projection.get("cell_id_template")
    if not isinstance(template, str) or not template:
        raise ValueError("reuse target cell_id_template is missing")
    workload = run.get("workload")
    cluster = run.get("cluster")
    if not isinstance(workload, Mapping) or not isinstance(cluster, Mapping):
        raise ValueError("reuse source lacks workload/cluster objects")
    context = {
        "method": run.get("method", ""),
        "load": workload.get("request_freq", ""),
        "topology": workload.get("topology", cluster.get("topology", "")),
        "node_count": cluster.get("node_count", ""),
        "seed": run.get("seed", ""),
    }
    try:
        return template.format(**context)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid reuse cell_id_template: {exc}") from exc


def materialize_analysis_reuse_rows(
    manifest: Mapping[str, Any],
    source_rows: Sequence[Mapping[str, Any]],
    *,
    source_runs: Sequence[Mapping[str, Any]] | None = None,
    target_experiment_ids: set[str] | None = None,
    source_manifest_hash: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Materialize only manifest-declared, identity-compatible reused points.

    Every projected row retains the physical source run/result identifiers and
    hashes plus the sealed rule hash.  An unavailable or incompatible source is
    emitted to coverage and is never copied into the analysis table.
    """

    rules = _validated_reuse_rules(manifest)
    if not rules:
        return [], []
    runs = source_runs if source_runs is not None else manifest.get("runs")
    if not isinstance(runs, list):
        # Accept immutable tuple-like inputs while still rejecting mappings and
        # strings, which otherwise iterate with surprising semantics.
        if not isinstance(runs, Sequence) or isinstance(runs, (str, bytes)):
            raise ValueError("reuse source must contain a runs array")
    physical_source_manifest_hash = (
        source_manifest_hash
        if source_manifest_hash is not None
        else str(manifest.get("manifest_hash", ""))
    )
    rows_by_run_id: dict[str, Mapping[str, Any]] = {}
    for row in source_rows:
        run_id = str(row.get("run_id", ""))
        if not run_id or run_id in rows_by_run_id:
            raise ValueError("physical analysis rows have missing/duplicate run_id")
        rows_by_run_id[run_id] = row

    materialized: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    target_keys: set[tuple[str, str, str]] = set()
    for rule in rules:
        rule_id = str(rule["rule_id"])
        selector = rule["source_selector"]
        compatibility = rule["compatibility"]
        projection = rule["target_projection"]
        target_experiment = str(rule["experiment_id"])
        if (
            target_experiment_ids is not None
            and target_experiment not in target_experiment_ids
        ):
            continue
        for run in runs:
            if not isinstance(run, Mapping):
                continue
            if run.get("experiment_id") != rule["source_experiment_id"]:
                continue
            if not _selector_matches(run, selector):
                continue
            source_run_id = str(run.get("run_id", ""))
            target_cell = _target_cell_id(run, projection)
            coverage_base = {
                "experiment_id": target_experiment,
                "cell_id": target_cell,
                "run_id": "",
                "seed": run.get("seed", ""),
                "method": run.get("method", ""),
                "record_kind": "materialized_reuse",
                "source_experiment_id": run.get("experiment_id", ""),
                "source_cell_id": run.get("cell_id", ""),
                "source_run_id": source_run_id,
                "source_run_spec_hash": run.get("run_spec_hash", ""),
                "source_workload_spec_hash": run.get("workload_spec_hash", ""),
                "source_common_hpa_hash": run.get("common_hpa_hash", ""),
                "reuse_rule_id": rule_id,
                "reuse_rule_sha256": rule["rule_sha256"],
            }
            source_row = rows_by_run_id.get(source_run_id)
            if source_row is None:
                coverage.append(
                    {
                        **coverage_base,
                        "status": "reuse_source_unavailable",
                        "detail": "source formal run was not exported",
                    }
                )
                continue
            issues = _reuse_compatibility_issues(run, source_row, compatibility)
            if issues:
                coverage.append(
                    {
                        **coverage_base,
                        "status": "reuse_incompatible_source",
                        "detail": "; ".join(issues),
                    }
                )
                continue

            raw_variant = str(projection.get("variant", ""))
            variant = VARIANT_NAMES.get(raw_variant, raw_variant)
            if target_experiment != "E5" and raw_variant == "full":
                variant = ""
            provenance = {
                "schema_version": "NSE_ANALYSIS_REUSE_PROVENANCE_V1",
                "source_manifest_hash": physical_source_manifest_hash,
                "reuse_contract_manifest_hash": manifest.get("manifest_hash", ""),
                "source_experiment_id": run.get("experiment_id", ""),
                "source_cell_id": run.get("cell_id", ""),
                "source_run_id": source_run_id,
                "source_run_spec_hash": run.get("run_spec_hash", ""),
                "source_workload_spec_hash": run.get("workload_spec_hash", ""),
                "source_common_hpa_hash": run.get("common_hpa_hash", ""),
                "reuse_rule_id": rule_id,
                "reuse_rule_sha256": rule["rule_sha256"],
                "target_experiment_id": target_experiment,
                "target_cell_id": target_cell,
                "seed": run.get("seed", ""),
                "workload_transform": "identity",
                "cluster_transform": "identity",
            }
            materialization_hash = _object_hash(provenance)
            target_run_id = (
                f"{target_cell}.{run.get('seed', '')}.reuse-{materialization_hash[:12]}"
            )
            target_key = (
                target_experiment,
                target_cell,
                str(run.get("seed", "")),
            )
            if target_key in target_keys:
                raise ValueError(f"duplicate analysis reuse target {target_key}")
            target_keys.add(target_key)

            row = dict(source_row)
            row.update(
                {
                    "experiment_id": target_experiment,
                    "cell_id": target_cell,
                    "scenario": str(projection.get("scenario", "")),
                    "variant": variant,
                    "run_id": target_run_id,
                    "analysis_record_kind": "materialized_reuse",
                    "source_manifest_hash": physical_source_manifest_hash,
                    "reuse_contract_manifest_hash": manifest.get("manifest_hash", ""),
                    "source_experiment_id": run.get("experiment_id", ""),
                    "source_cell_id": run.get("cell_id", ""),
                    "source_run_id": source_run_id,
                    "source_run_spec_hash": run.get("run_spec_hash", ""),
                    "source_workload_spec_hash": run.get("workload_spec_hash", ""),
                    "source_common_hpa_hash": run.get("common_hpa_hash", ""),
                    "source_result_path": source_row.get("result_path", ""),
                    "reuse_rule_id": rule_id,
                    "reuse_rule_sha256": rule["rule_sha256"],
                    "reuse_rule_purpose": rule.get("purpose", ""),
                    "reuse_materialization_sha256": materialization_hash,
                    "reuse_compatibility": "verified_identity",
                }
            )
            if projection.get("copy_nash_parameters") is True:
                nash = _nested_value(run, "simulator_experiment.nash")
                if not isinstance(nash, Mapping):
                    raise ValueError(
                        f"reuse rule {rule_id} source lacks Nash parameters"
                    )
                row["price_feedback_rate"] = nash.get("price_feedback_rate")
                row["quality_weight"] = nash.get("quality_weight")
            materialized.append(row)
            coverage.append(
                {
                    **coverage_base,
                    "run_id": target_run_id,
                    "status": "ok",
                    "detail": "identity-compatible analysis reuse materialized",
                    "reuse_materialization_sha256": materialization_hash,
                }
            )
    return materialized, coverage


def load_canonical_protocol_results(
    manifest_path: str | Path,
    canonical_root: str | Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = _read_json(Path(manifest_path))
    if not isinstance(manifest, Mapping):
        raise ValueError("manifest root must be an object")
    _assert_formal_results_eligible(manifest)
    if not isinstance(manifest.get("runs"), list):
        raise ValueError("manifest must contain a runs array")
    result_relative_path = str(
        (manifest.get("execution") or {}).get("result_relative_path", "result.json")
    )
    canonical = Path(canonical_root)
    exported: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []

    for run in manifest["runs"]:
        run_directory = canonical / str(run["run_id"])
        if not run_directory.is_dir():
            coverage.append(_coverage_row(run, "missing_canonical"))
            continue
        try:
            formatted_result_path = result_relative_path.format(
                run_id=str(run["run_id"])
            )
        except (KeyError, ValueError) as exc:
            coverage.append(
                _coverage_row(run, "invalid_result_path_template", str(exc))
            )
            continue
        result_path = run_directory / formatted_result_path
        qc_path = run_directory / "qc_report.json"
        if not qc_path.is_file():
            coverage.append(_coverage_row(run, "missing_qc_report"))
            continue
        if not result_path.is_file():
            coverage.append(_coverage_row(run, "missing_result"))
            continue
        try:
            qc = _read_json(qc_path)
            result = _read_json(result_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            coverage.append(_coverage_row(run, "unreadable_json", str(exc)))
            continue
        if not isinstance(qc, Mapping) or qc.get("passed") is not True:
            coverage.append(_coverage_row(run, "qc_not_passed"))
            continue
        if not isinstance(result, Mapping):
            coverage.append(_coverage_row(run, "unsupported_result_schema"))
            continue
        result_schema: str
        if result.get("schema_version") == "summary_json_v1":
            result_schema = "summary_json_v1"
            if result.get("completed") is not True:
                coverage.append(_coverage_row(run, "result_incomplete"))
                continue
            provenance = result.get("provenance")
            expected = {
                "run_id": run.get("run_id"),
                "run_spec_hash": run.get("run_spec_hash"),
                "seed": run.get("seed"),
                "workload_spec_hash": run.get("workload_spec_hash"),
                "common_hpa_hash": run.get("common_hpa_hash"),
            }
            if not isinstance(provenance, Mapping) or any(
                provenance.get(key) != value for key, value in expected.items()
            ):
                coverage.append(_coverage_row(run, "provenance_mismatch"))
                continue
            raw_metrics = result.get("metrics")
            if not isinstance(raw_metrics, Mapping):
                coverage.append(_coverage_row(run, "missing_metrics"))
                continue
            metrics = dict(raw_metrics)
        elif result.get("schema") == "NSE_SUMMARY_V1":
            result_schema = "NSE_SUMMARY_V1"
            if result.get("run_complete") is not True:
                coverage.append(_coverage_row(run, "result_incomplete"))
                continue
            if result.get("run_id") != run.get("run_id"):
                coverage.append(_coverage_row(run, "provenance_mismatch"))
                continue
            metrics = _nse_summary_metrics(result)
            process_observation, process_error = _load_process_observation(
                run_directory
            )
            if process_observation is None:
                coverage.append(
                    _coverage_row(
                        run, "invalid_process_observation", process_error or ""
                    )
                )
                continue
            metrics.update(_process_observation_metrics(process_observation))
        else:
            coverage.append(_coverage_row(run, "unsupported_result_schema"))
            continue

        workload = run.get("workload") or {}
        cluster = run.get("cluster") or {}
        experiment_id = str(run.get("experiment_id", ""))
        topology = str(workload.get("topology", cluster.get("topology", ""))).lower()
        scenario = (
            topology
            if experiment_id == "E1"
            else SCENARIOS.get(experiment_id, experiment_id.lower())
        )
        raw_variant = str(run.get("variant", "full"))
        variant = VARIANT_NAMES.get(raw_variant, raw_variant)
        if experiment_id != "E5" and raw_variant == "full":
            variant = ""
        row: dict[str, Any] = {
            "experiment_id": experiment_id,
            "cell_id": run.get("cell_id", ""),
            "analysis_record_kind": "formal_run",
            "scenario": scenario,
            "load": _canonical_load(workload.get("request_freq", "unspecified")),
            "arrival_profile": workload.get("arrival_profile", ""),
            "topology": topology,
            "load_scale": workload.get("load_scale", 1.0),
            "node_count": cluster.get("node_count", ""),
            "burst_pattern": workload.get("burst_name", ""),
            "qos_profile": workload.get("qos_profile", ""),
            "algorithm": _canonical_algorithm(run.get("method", "")),
            "variant": variant,
            "seed": run.get("seed", ""),
            "run_id": run.get("run_id", ""),
            "pair_id": run.get("workload_spec_hash", run.get("seed", "")),
            "run_spec_hash": run.get("run_spec_hash", ""),
            "workload_spec_hash": run.get("workload_spec_hash", ""),
            "common_hpa_hash": run.get("common_hpa_hash", ""),
            "result_schema": result_schema,
            "result_path": str(result_path.resolve()),
        }
        nash = (run.get("simulator_experiment") or {}).get("nash")
        if isinstance(nash, Mapping):
            row["price_feedback_rate"] = nash.get("price_feedback_rate")
            row["quality_weight"] = nash.get("quality_weight")
        for raw_name, raw_value in _flatten_scalars(metrics).items():
            name, scale = _metric_name_and_scale(raw_name)
            if isinstance(raw_value, bool) or raw_value is None:
                row[name] = raw_value
            elif isinstance(raw_value, (int, float)):
                numeric = float(raw_value)
                row[name] = numeric * scale if math.isfinite(numeric) else numeric
            else:
                row[name] = raw_value
        if result_schema == "NSE_SUMMARY_V1":
            row.update(
                {
                    "throughput_unit": "10^3 requests/s (= requests/ms)",
                    "throughput_physical_unit": "requests/s",
                    "cost_unit": "simulator internal cost/completed request",
                    "scheduler_peak_memory_unit": "MiB (peak process-tree RSS)",
                    "scheduler_latency_scope": "placement policy only",
                    "mechanism_total_wall_unit": "microseconds",
                    "mechanism_total_thread_cpu_unit": "microseconds",
                }
            )
        exported.append(row)
        coverage.append(_coverage_row(run, "ok"))
    reused, reuse_coverage = materialize_analysis_reuse_rows(manifest, exported)
    exported.extend(reused)
    coverage.extend(reuse_coverage)
    return exported, coverage


def export_canonical_protocol_results(
    *,
    manifest_path: str | Path,
    canonical_root: str | Path,
    output_csv: str | Path,
    coverage_csv: str | Path,
    require_complete: bool = True,
) -> tuple[Path, Path]:
    rows, coverage = load_canonical_protocol_results(manifest_path, canonical_root)
    output = Path(output_csv)
    coverage_output = Path(coverage_csv)
    write_csv(output, rows)
    write_csv(coverage_output, coverage)
    incomplete = [row for row in coverage if row["status"] != "ok"]
    if require_complete and incomplete:
        counts: dict[str, int] = {}
        for row in incomplete:
            counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1
        raise RuntimeError(
            "canonical coverage is incomplete; CSVs were written for audit: "
            + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
        )
    return output, coverage_output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--canonical-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--coverage", required=True)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="export available canonical runs but retain missing entries in coverage CSV",
    )
    args = parser.parse_args(argv)
    output, coverage = export_canonical_protocol_results(
        manifest_path=args.manifest,
        canonical_root=args.canonical_root,
        output_csv=args.output,
        coverage_csv=args.coverage,
        require_complete=not args.allow_incomplete,
    )
    print(output.resolve())
    print(coverage.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
