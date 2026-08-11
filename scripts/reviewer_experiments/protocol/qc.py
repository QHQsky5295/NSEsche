from __future__ import annotations

import json
import hashlib
import math
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .util import file_hash, object_hash, read_json, utc_now


@dataclass
class QCIssue:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass
class QCReport:
    passed: bool
    classification: str
    checked_at: str
    result_path: str | None
    result_sha256: str | None
    result_bytes: int | None
    issues: list[QCIssue] = field(default_factory=list)
    observations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "classification": self.classification,
            "failure_signature": technical_failure_signature(self),
            "checked_at": self.checked_at,
            "result_path": self.result_path,
            "result_sha256": self.result_sha256,
            "result_bytes": self.result_bytes,
            "issues": [issue.to_dict() for issue in self.issues],
            "observations": self.observations,
        }


class RecordStreamError(ValueError):
    pass


_STABLE_FAILURE_DETAIL_KEYS = frozenset(
    {
        "error",
        "exit_code",
        "format",
        "patterns",
    }
)


def _normalized_failure_detail(value: Any) -> Any:
    """Normalize only evidence that identifies the technical failure itself."""

    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        normalized = re.sub(
            r"(?i)(?:(?<=/)|^)attempt-\d+(?=/|$)",
            "attempt-NN",
            normalized,
        )
        return re.sub(r"0x[0-9a-fA-F]+", "0xADDR", normalized)
    if isinstance(value, list):
        return sorted(_normalized_failure_detail(child) for child in value)
    if isinstance(value, dict):
        return {
            str(key): _normalized_failure_detail(child)
            for key, child in sorted(value.items())
        }
    return value


def technical_failure_signature(report: QCReport | dict[str, Any]) -> str | None:
    """Return a stable, result-blind identity for a failed technical attempt.

    Observed counters, metric values, hashes, timestamps, and attempt paths are
    deliberately excluded.  They may legitimately vary between attempts and
    must not affect retry control.  Detailed parser/runner errors, exit codes,
    and matched crash patterns remain part of the identity so distinct
    transient failures may use the third and final same-spec attempt.
    """

    if isinstance(report, QCReport):
        passed = report.passed
        classification = report.classification
        raw_issues: list[Any] = report.issues
    else:
        passed = report.get("passed")
        classification = report.get("classification")
        raw_issues = report.get("issues", [])
    if passed is True:
        return None

    issues: list[dict[str, Any]] = []
    for raw_issue in raw_issues if isinstance(raw_issues, list) else []:
        if isinstance(raw_issue, QCIssue):
            code = raw_issue.code
            message = raw_issue.message
            details = raw_issue.details
        elif isinstance(raw_issue, dict):
            code = raw_issue.get("code")
            message = raw_issue.get("message")
            details = raw_issue.get("details", {})
        else:
            continue
        stable_details = {}
        if isinstance(details, dict):
            stable_details = {
                key: _normalized_failure_detail(details[key])
                for key in sorted(_STABLE_FAILURE_DETAIL_KEYS & details.keys())
            }
        issues.append(
            {
                "code": code,
                "message": message,
                "stable_details": stable_details,
            }
        )
    issues.sort(
        key=lambda issue: json.dumps(
            issue, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    )
    return object_hash(
        {
            "schema": "NSE_TECHNICAL_FAILURE_SIGNATURE_V1",
            "classification": classification,
            "issues": issues,
        }
    )


def _issue(issues: list[QCIssue], code: str, message: str, **details: Any) -> None:
    issues.append(QCIssue(code=code, message=message, details=details))


def _read_text_for_patterns(path: Path | None, patterns: list[str]) -> list[str]:
    if path is None or not path.exists() or not patterns:
        return []
    matches: list[str] = []
    compiled = [
        (pattern, re.compile(re.escape(pattern), re.IGNORECASE)) for pattern in patterns
    ]
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            for original, regex in compiled:
                if regex.search(line):
                    matches.append(original)
    return sorted(set(matches))


def _walk_nonfinite(value: Any, path: str = "$") -> Iterator[tuple[str, float]]:
    if isinstance(value, float) and not math.isfinite(value):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_nonfinite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_nonfinite(child, f"{path}[{index}]")


def _dot_get(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


# These paths mirror the scalar ``f32`` fields in Rust's ExperimentConfig.
# JSON has only one number type, while the frozen Python manifest is produced
# from binary64 values and Rust serializes the values after deserializing them
# to binary32.  Comparing the JSON decimals directly would therefore reject
# values such as 0.1 and 0.10000000149011612 even though they are exactly the
# same runtime f32.  Keep this list explicit so no tolerance can hide a change
# to an integer, enum, hash, seed, path, or future unreviewed config field.
_RUST_EXPERIMENT_F32_PATHS = frozenset(
    {
        ("faasrank_model", "cpu_headroom"),
        ("faasrank_model", "memory_headroom"),
        ("faasrank_model", "network_locality"),
        ("faasrank_model", "warm_affinity"),
        ("faasrank_model", "load_balance"),
        ("faasrank_model", "diversity_penalty"),
        ("faasrank_model", "epsilon"),
        ("nash", "price_feedback_rate"),
        ("nash", "quality_weight"),
        ("nash", "queue_normalizer"),
        ("hpa", "target_mem_use_rate"),
        ("hpa", "tolerance"),
        ("node_profile", "cpu_mean"),
        ("node_profile", "mem_mean"),
        ("node_profile", "cpu_cv"),
        ("node_profile", "mem_cv"),
        ("node_profile", "min_factor"),
        ("node_profile", "max_factor"),
        ("network_profile", "min_mbps"),
        ("network_profile", "max_mbps"),
        ("workload", "load_scale"),
        ("qos", "latency_weight"),
        ("qos", "throughput_weight"),
        ("qos", "cost_weight"),
        ("qos", "latency_deadline_ms"),
        ("qos", "throughput_target_rps"),
        ("qos", "cost_budget_per_request"),
    }
)


def _binary32(value: Any) -> bytes | None:
    """Return the IEEE-754 binary32 representation of a finite JSON number."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    try:
        return struct.pack("!f", numeric)
    except (OverflowError, struct.error):
        return None


def _experiment_scalar_equal(expected: Any, actual: Any, path: tuple[str, ...]) -> bool:
    if path in _RUST_EXPERIMENT_F32_PATHS:
        if expected is None or actual is None:
            return expected is None and actual is None
        expected_f32 = _binary32(expected)
        actual_f32 = _binary32(actual)
        return expected_f32 is not None and expected_f32 == actual_f32
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    return expected == actual


def _experiment_config_differences(
    expected: Any, actual: Any, path: tuple[str, ...] = ()
) -> list[dict[str, Any]]:
    """Compare ExperimentConfig while canonicalizing only declared f32 fields."""

    display_path = "$" + "".join(f".{part}" for part in path)
    if isinstance(expected, dict) or isinstance(actual, dict):
        if not isinstance(expected, dict) or not isinstance(actual, dict):
            return [
                {
                    "path": display_path,
                    "kind": "type",
                    "expected": expected,
                    "actual": actual,
                }
            ]
        differences: list[dict[str, Any]] = []
        for key in sorted(expected.keys() | actual.keys()):
            if key not in expected:
                differences.append(
                    {
                        "path": f"{display_path}.{key}",
                        "kind": "unexpected",
                        "actual": actual[key],
                    }
                )
            elif key not in actual:
                differences.append(
                    {
                        "path": f"{display_path}.{key}",
                        "kind": "missing",
                        "expected": expected[key],
                    }
                )
            else:
                differences.extend(
                    _experiment_config_differences(
                        expected[key], actual[key], (*path, key)
                    )
                )
        return differences
    if isinstance(expected, list) or isinstance(actual, list):
        if not isinstance(expected, list) or not isinstance(actual, list):
            return [
                {
                    "path": display_path,
                    "kind": "type",
                    "expected": expected,
                    "actual": actual,
                }
            ]
        differences = []
        if len(expected) != len(actual):
            differences.append(
                {
                    "path": display_path,
                    "kind": "length",
                    "expected": len(expected),
                    "actual": len(actual),
                }
            )
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            differences.extend(
                _experiment_config_differences(
                    expected_item, actual_item, (*path, str(index))
                )
            )
        return differences
    if _experiment_scalar_equal(expected, actual, path):
        return []
    return [
        {
            "path": display_path,
            "kind": "value",
            "expected": expected,
            "actual": actual,
        }
    ]


def _require_fields(
    value: Any,
    fields: tuple[str, ...],
    issues: list[QCIssue],
    *,
    scope: str,
) -> bool:
    """Require explicit keys so a missing observation cannot masquerade as null."""

    if not isinstance(value, dict):
        _issue(
            issues,
            "invalid_observation_shape",
            f"{scope} must be an object",
            scope=scope,
            value_type=type(value).__name__,
        )
        return False
    missing = [field for field in fields if field not in value]
    if missing:
        _issue(
            issues,
            "missing_observation_fields",
            f"{scope} is missing required formal observations",
            scope=scope,
            fields=missing,
        )
        return False
    return True


def _validate_numeric_metrics(
    metrics: dict[str, Any], qc: dict[str, Any], issues: list[QCIssue]
) -> None:
    for name in qc.get("required_finite_metrics", []):
        try:
            value = _dot_get(metrics, name)
        except KeyError:
            _issue(
                issues,
                "missing_metric",
                f"required metric {name!r} is missing",
                metric=name,
            )
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _issue(
                issues,
                "non_numeric_metric",
                f"required metric {name!r} is not numeric",
                metric=name,
                value_type=type(value).__name__,
            )
        elif not math.isfinite(float(value)):
            _issue(
                issues,
                "nonfinite_metric",
                f"required metric {name!r} is not finite",
                metric=name,
                value=repr(value),
            )

    for name in qc.get("required_positive_metrics", []):
        try:
            value = _dot_get(metrics, name)
        except KeyError:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if math.isfinite(float(value)) and float(value) <= 0.0:
            _issue(
                issues,
                "nonpositive_metric",
                f"required-positive metric {name!r} is not positive",
                metric=name,
                value=value,
            )


def _validate_provenance(
    provenance: Any, run: dict[str, Any], issues: list[QCIssue]
) -> None:
    if not isinstance(provenance, dict):
        _issue(issues, "missing_provenance", "result provenance object is missing")
        return
    expected = {
        "run_id": run["run_id"],
        "run_spec_hash": run["run_spec_hash"],
        "seed": run["seed"],
        "workload_spec_hash": run["workload_spec_hash"],
        "common_hpa_hash": run["common_hpa_hash"],
    }
    for key, expected_value in expected.items():
        actual = provenance.get(key)
        if actual != expected_value:
            _issue(
                issues,
                "provenance_mismatch",
                f"provenance {key!r} does not match the frozen run manifest",
                field=key,
                expected=expected_value,
                actual=actual,
            )


def _validate_summary_json(
    result_path: Path, run: dict[str, Any], qc: dict[str, Any], issues: list[QCIssue]
) -> dict[str, Any]:
    try:
        result = read_json(result_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _issue(issues, "invalid_json", "result JSON cannot be parsed", error=str(exc))
        return {}
    if not isinstance(result, dict):
        _issue(issues, "invalid_result_root", "result JSON root must be an object")
        return {}

    nonfinite = list(_walk_nonfinite(result))
    for path, value in nonfinite[:25]:
        _issue(
            issues,
            "nonfinite_value",
            "result contains NaN or infinity",
            path=path,
            value=repr(value),
        )
    if len(nonfinite) > 25:
        _issue(
            issues,
            "nonfinite_value_truncated",
            "additional nonfinite values were found",
            additional=len(nonfinite) - 25,
        )

    if result.get("schema_version") != "summary_json_v1":
        _issue(
            issues,
            "result_schema_mismatch",
            "result schema_version must be summary_json_v1",
            actual=result.get("schema_version"),
        )
    if result.get("completed") is not True:
        _issue(
            issues,
            "missing_completion_marker",
            "result does not contain completed=true",
        )
    simulation = run["simulation"]
    if result.get("final_frame") != simulation["expected_final_frame"]:
        _issue(
            issues,
            "wrong_final_frame",
            "result final_frame differs from the frozen manifest",
            expected=simulation["expected_final_frame"],
            actual=result.get("final_frame"),
        )
    if result.get("frame_count") != simulation["expected_frame_count"]:
        _issue(
            issues,
            "wrong_frame_count",
            "result frame_count differs from the frozen manifest",
            expected=simulation["expected_frame_count"],
            actual=result.get("frame_count"),
        )
    if qc.get("require_provenance", True):
        _validate_provenance(result.get("provenance"), run, issues)
    metrics = result.get("metrics")
    if not isinstance(metrics, dict):
        _issue(issues, "missing_metrics", "result metrics object is missing")
        return {}
    _validate_numeric_metrics(metrics, qc, issues)
    return {
        "metrics": metrics,
        "final_frame": result.get("final_frame"),
        "frame_count": result.get("frame_count"),
    }


def _validate_nse_summary(
    result_path: Path,
    run: dict[str, Any],
    qc: dict[str, Any],
    issues: list[QCIssue],
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        summary = read_json(result_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _issue(
            issues, "invalid_json", "NSE summary JSON cannot be parsed", error=str(exc)
        )
        return {}, {}
    if not isinstance(summary, dict):
        _issue(issues, "invalid_result_root", "NSE summary root must be an object")
        return {}, {}
    _require_fields(
        summary,
        (
            "schema",
            "run_id",
            "protocol_version",
            "run_complete",
            "final_frame",
            "frames_recorded",
            "frame_duration_ms",
            "observation_time_ms",
            "arrivals",
            "completed",
            "completion_ratio",
            "throughput_requests_per_second",
            "latency_ms",
            "fixed_observation_window",
            "drained_arrival_cohort",
            "metric_definitions",
            "simulator_internal_cost_total",
            "simulator_internal_cost_per_completed_request",
            "queue_peak",
            "queue_area_request_frames",
            "node_cpu_utilization_mean",
            "node_cpu_utilization_p95",
            "node_cpu_utilization_peak",
            "node_memory_utilization_mean",
            "node_memory_utilization_p95",
            "node_memory_utilization_peak",
            "node_utilization_unit",
            "node_utilization_definition",
            "scheduler_window_count",
            "scheduler_wall_ns",
            "scheduler_thread_cpu_ns",
            "placement_policy_wall_ns",
            "placement_policy_thread_cpu_ns",
            "posthoc_welfare_evaluation_wall_ns",
            "posthoc_welfare_evaluation_thread_cpu_ns",
            "scheduler_timing_definition",
            "placement_rejections",
            "qos_function_tasks",
            "qos_simulator_internal_cost",
            "admission_drop",
            "admission_reject",
            "timeout",
            "queue_semantics",
        ),
        issues,
        scope="NSE_SUMMARY_V1",
    )
    for path, value in list(_walk_nonfinite(summary))[:25]:
        _issue(
            issues,
            "nonfinite_value",
            "NSE summary contains NaN or infinity",
            path=path,
            value=repr(value),
        )
    summary_contract = qc.get("nse_summary_contract", {})
    expected_summary_schema = summary_contract.get("schema", "NSE_SUMMARY_V1")
    if summary.get("schema") != expected_summary_schema:
        _issue(
            issues,
            "result_schema_mismatch",
            "summary schema must be NSE_SUMMARY_V1",
            actual=summary.get("schema"),
        )
    expected_protocol_version = run.get("simulator_experiment", {}).get(
        "protocol_version"
    )
    if not isinstance(summary.get("protocol_version"), str) or not summary.get(
        "protocol_version"
    ):
        _issue(
            issues,
            "missing_provenance",
            "summary protocol_version must be a non-empty string",
            actual=summary.get("protocol_version"),
        )
    elif summary.get("protocol_version") != expected_protocol_version:
        _issue(
            issues,
            "provenance_mismatch",
            "summary protocol_version does not match the frozen ExperimentConfig",
            expected=expected_protocol_version,
            actual=summary.get("protocol_version"),
        )
    if summary.get("run_id") != run["run_id"]:
        _issue(
            issues,
            "provenance_mismatch",
            "summary run_id does not match manifest",
            expected=run["run_id"],
            actual=summary.get("run_id"),
        )
    if summary.get("run_complete") is not True:
        _issue(
            issues,
            "missing_completion_marker",
            "summary does not contain run_complete=true",
        )
    simulation = run["simulation"]
    if summary.get("final_frame") != simulation["expected_final_frame"]:
        _issue(
            issues,
            "wrong_final_frame",
            "NSE summary final_frame differs from manifest",
            expected=simulation["expected_final_frame"],
            actual=summary.get("final_frame"),
        )
    if summary.get("frames_recorded") != simulation["expected_frame_count"]:
        _issue(
            issues,
            "wrong_frame_count",
            "NSE summary frames_recorded differs from manifest",
            expected=simulation["expected_frame_count"],
            actual=summary.get("frames_recorded"),
        )
    if summary.get("frame_duration_ms") != int(
        float(simulation.get("frame_duration_seconds", 0.001)) * 1000
    ):
        _issue(
            issues,
            "frame_duration_mismatch",
            "NSE summary frame duration differs from manifest",
            actual=summary.get("frame_duration_ms"),
        )
    expected_observation_ms = int(simulation.get("total_frame", 0))
    if summary.get("observation_time_ms") != expected_observation_ms:
        _issue(
            issues,
            "observation_horizon_mismatch",
            "NSE summary throughput horizon differs from the frozen protocol",
            expected=expected_observation_ms,
            actual=summary.get("observation_time_ms"),
        )

    expected_fixed_observation_ms = int(
        simulation.get(
            "observation_horizon_frames",
            simulation.get("arrival_horizon_frames", 0),
        )
    )
    fixed_value = summary.get("fixed_observation_window")
    _require_fields(
        fixed_value,
        (
            "start_frame",
            "end_frame",
            "duration_ms",
            "arrivals",
            "completed",
            "completion_ratio",
            "throughput_requests_per_second",
        ),
        issues,
        scope="NSE_SUMMARY_V1.fixed_observation_window",
    )
    fixed = fixed_value if isinstance(fixed_value, dict) else {}
    drained_value = summary.get("drained_arrival_cohort")
    _require_fields(
        drained_value,
        (
            "arrival_start_frame",
            "arrival_end_frame",
            "drain_end_frame",
            "drain_duration_after_arrivals_ms",
            "arrivals",
            "completed",
            "completion_ratio",
            "latency_ms",
        ),
        issues,
        scope="NSE_SUMMARY_V1.drained_arrival_cohort",
    )
    drained = drained_value if isinstance(drained_value, dict) else {}
    drained_latency_value = drained.get("latency_ms")
    _require_fields(
        drained_latency_value,
        ("mean", "p50", "p95", "p99"),
        issues,
        scope="NSE_SUMMARY_V1.drained_arrival_cohort.latency_ms",
    )
    drained_latency = (
        drained_latency_value if isinstance(drained_latency_value, dict) else {}
    )
    definitions_value = summary.get("metric_definitions")
    _require_fields(
        definitions_value,
        (
            "frame_duration_ms",
            "fixed_observation_window",
            "drained_arrival_cohort",
            "legacy_top_level_fields",
        ),
        issues,
        scope="NSE_SUMMARY_V1.metric_definitions",
    )
    definitions = definitions_value if isinstance(definitions_value, dict) else {}
    fixed_definition = definitions.get("fixed_observation_window")
    drained_definition = definitions.get("drained_arrival_cohort")
    _require_fields(
        fixed_definition,
        ("arrival_cohort", "completion_deadline", "throughput", "throughput_unit"),
        issues,
        scope="NSE_SUMMARY_V1.metric_definitions.fixed_observation_window",
    )
    _require_fields(
        drained_definition,
        ("cohort", "completion_deadline", "latency_population", "latency_unit"),
        issues,
        scope="NSE_SUMMARY_V1.metric_definitions.drained_arrival_cohort",
    )
    if definitions.get("frame_duration_ms") != 1:
        _issue(
            issues,
            "unit_mismatch",
            "cohort metric frame duration must be one millisecond",
            actual=definitions.get("frame_duration_ms"),
        )
    if (
        not isinstance(fixed_definition, dict)
        or fixed_definition.get("throughput_unit") != "requests/s"
    ):
        _issue(
            issues,
            "unit_mismatch",
            "fixed-window throughput unit must be requests/s",
        )
    if (
        not isinstance(drained_definition, dict)
        or drained_definition.get("latency_unit") != "ms"
    ):
        _issue(
            issues,
            "unit_mismatch",
            "drained-cohort latency unit must be ms",
        )

    latency_value = summary.get("latency_ms")
    _require_fields(
        latency_value,
        ("mean", "p50", "p95", "p99"),
        issues,
        scope="NSE_SUMMARY_V1.latency_ms",
    )
    latency = latency_value if isinstance(latency_value, dict) else {}
    scheduler_wall = (
        summary.get("scheduler_wall_ns")
        if isinstance(summary.get("scheduler_wall_ns"), dict)
        else {}
    )
    scheduler_cpu = (
        summary.get("scheduler_thread_cpu_ns")
        if isinstance(summary.get("scheduler_thread_cpu_ns"), dict)
        else {}
    )
    scheduler_policy_wall = (
        summary.get("placement_policy_wall_ns")
        if isinstance(summary.get("placement_policy_wall_ns"), dict)
        else {}
    )
    scheduler_policy_cpu = (
        summary.get("placement_policy_thread_cpu_ns")
        if isinstance(summary.get("placement_policy_thread_cpu_ns"), dict)
        else {}
    )
    metrics = {
        "arrivals": summary.get("arrivals"),
        "completions": summary.get("completed"),
        "throughput_rps": summary.get("throughput_requests_per_second"),
        "latency_mean_ms": latency.get("mean"),
        "latency_p50_ms": latency.get("p50"),
        "latency_p95_ms": latency.get("p95"),
        "latency_p99_ms": latency.get("p99"),
        "cost": summary.get("simulator_internal_cost_total"),
        "cost_per_completed": summary.get(
            "simulator_internal_cost_per_completed_request"
        ),
        "queue_peak": summary.get("queue_peak"),
        "queue_area_request_frames": summary.get("queue_area_request_frames"),
        "scheduler_window_count": summary.get("scheduler_window_count"),
        "scheduler_wall_mean_ns": scheduler_wall.get("mean"),
        "scheduler_cpu_mean_ns": scheduler_cpu.get("mean"),
        "scheduler_policy_wall_mean_ns": scheduler_policy_wall.get("mean"),
        "scheduler_policy_cpu_mean_ns": scheduler_policy_cpu.get("mean"),
        "completion_ratio": summary.get("completion_ratio"),
        "node_cpu_utilization_mean": summary.get("node_cpu_utilization_mean"),
        "node_cpu_utilization_p95": summary.get("node_cpu_utilization_p95"),
        "node_cpu_utilization_peak": summary.get("node_cpu_utilization_peak"),
        "node_memory_utilization_mean": summary.get("node_memory_utilization_mean"),
        "node_memory_utilization_p95": summary.get("node_memory_utilization_p95"),
        "node_memory_utilization_peak": summary.get("node_memory_utilization_peak"),
        "placement_rejections": summary.get("placement_rejections"),
        "drops": summary.get("admission_drop"),
        "rejects": summary.get("admission_reject"),
        "timeouts": summary.get("timeout"),
    }
    _validate_numeric_metrics(metrics, qc, issues)
    arrivals = metrics["arrivals"]
    completed = metrics["completions"]
    for name, value in (("arrivals", arrivals), ("completed", completed)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _issue(
                issues,
                "invalid_counter",
                f"{name} must be a non-negative integer",
                metric=name,
                value=value,
            )
    if isinstance(arrivals, int) and not isinstance(arrivals, bool):
        tape_count = run.get("workload_tape", {}).get("event_count")
        if isinstance(tape_count, int) and tape_count > 0 and arrivals != tape_count:
            _issue(
                issues,
                "arrival_tape_mismatch",
                "observed arrivals differ from the immutable replay tape",
                expected=tape_count,
                actual=arrivals,
            )
    if (
        isinstance(arrivals, int)
        and not isinstance(arrivals, bool)
        and isinstance(completed, int)
        and not isinstance(completed, bool)
        and completed > arrivals
    ):
        _issue(
            issues,
            "counter_conservation",
            "completed requests exceed arrivals",
            arrivals=arrivals,
            completed=completed,
        )

    expected_fixed_shape = {
        "start_frame": 0,
        "end_frame": int(simulation.get("observation_horizon_frames", 0)),
        "duration_ms": expected_fixed_observation_ms,
    }
    for name, expected in expected_fixed_shape.items():
        if fixed.get(name) != expected:
            _issue(
                issues,
                "observation_horizon_mismatch",
                f"fixed observation {name} differs from the frozen protocol",
                field=name,
                expected=expected,
                actual=fixed.get(name),
            )
    expected_drained_shape = {
        "arrival_start_frame": 0,
        "arrival_end_frame": int(simulation.get("arrival_horizon_frames", 0)),
        "drain_end_frame": int(simulation.get("total_frame", 0)),
        "drain_duration_after_arrivals_ms": int(simulation.get("total_frame", 0))
        - int(simulation.get("arrival_horizon_frames", 0)),
    }
    for name, expected in expected_drained_shape.items():
        if drained.get(name) != expected:
            _issue(
                issues,
                "observation_horizon_mismatch",
                f"drained cohort {name} differs from the frozen protocol",
                field=name,
                expected=expected,
                actual=drained.get(name),
            )

    fixed_arrivals = fixed.get("arrivals")
    fixed_completed = fixed.get("completed")
    drained_arrivals = drained.get("arrivals")
    drained_completed = drained.get("completed")
    for name, value in (
        ("fixed_observation_window.arrivals", fixed_arrivals),
        ("fixed_observation_window.completed", fixed_completed),
        ("drained_arrival_cohort.arrivals", drained_arrivals),
        ("drained_arrival_cohort.completed", drained_completed),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _issue(
                issues,
                "invalid_counter",
                f"{name} must be a non-negative integer",
                metric=name,
                value=value,
            )
    if fixed_arrivals != arrivals or drained_arrivals != arrivals:
        _issue(
            issues,
            "cohort_counter_mismatch",
            "fixed and drained metrics must use the complete frozen arrival cohort",
            top_level_arrivals=arrivals,
            fixed_arrivals=fixed_arrivals,
            drained_arrivals=drained_arrivals,
        )
    if drained_completed != completed:
        _issue(
            issues,
            "cohort_counter_mismatch",
            "drained cohort completions must match final-run completions",
            top_level_completed=completed,
            drained_completed=drained_completed,
        )
    if (
        isinstance(fixed_completed, int)
        and not isinstance(fixed_completed, bool)
        and isinstance(drained_completed, int)
        and not isinstance(drained_completed, bool)
        and fixed_completed > drained_completed
    ):
        _issue(
            issues,
            "counter_conservation",
            "fixed-window completions exceed drained cohort completions",
            fixed_completed=fixed_completed,
            drained_completed=drained_completed,
        )

    fixed_throughput = fixed.get("throughput_requests_per_second")
    if (
        isinstance(fixed_completed, int)
        and not isinstance(fixed_completed, bool)
        and expected_fixed_observation_ms > 0
    ):
        expected_fixed_throughput = (
            fixed_completed * 1000.0 / expected_fixed_observation_ms
        )
        if (
            isinstance(fixed_throughput, bool)
            or not isinstance(fixed_throughput, (int, float))
            or not math.isfinite(float(fixed_throughput))
            or not math.isclose(
                float(fixed_throughput),
                expected_fixed_throughput,
                rel_tol=1e-9,
                abs_tol=1e-12,
            )
        ):
            _issue(
                issues,
                "metric_consistency",
                "fixed-window throughput does not equal completions by the observation deadline divided by the fixed horizon",
                expected=expected_fixed_throughput,
                actual=fixed_throughput,
                unit="requests/s",
            )

    for scope, numerator, denominator, actual in (
        (
            "fixed_observation_window",
            fixed_completed,
            fixed_arrivals,
            fixed.get("completion_ratio"),
        ),
        (
            "drained_arrival_cohort",
            drained_completed,
            drained_arrivals,
            drained.get("completion_ratio"),
        ),
    ):
        if (
            isinstance(numerator, int)
            and not isinstance(numerator, bool)
            and isinstance(denominator, int)
            and not isinstance(denominator, bool)
        ):
            expected_ratio = None if denominator == 0 else numerator / denominator
            ratio_matches = (
                actual is None
                if expected_ratio is None
                else isinstance(actual, (int, float))
                and not isinstance(actual, bool)
                and math.isfinite(float(actual))
                and math.isclose(
                    float(actual), float(expected_ratio), rel_tol=1e-9, abs_tol=1e-12
                )
            )
            if not ratio_matches:
                _issue(
                    issues,
                    "metric_consistency",
                    f"{scope} completion_ratio is inconsistent with its cohort counters",
                    expected=expected_ratio,
                    actual=actual,
                )

    throughput = metrics["throughput_rps"]
    if (
        isinstance(throughput, bool)
        or not isinstance(throughput, (int, float))
        or not math.isfinite(float(throughput))
        or throughput < 0
    ):
        _issue(
            issues,
            "invalid_metric",
            "throughput must be finite and non-negative",
            metric="throughput_rps",
            value=throughput,
        )
    elif completed == 0 and throughput != 0:
        _issue(
            issues,
            "metric_consistency",
            "throughput must be zero when no request completed",
            value=throughput,
        )
    elif isinstance(completed, int) and completed > 0 and throughput <= 0:
        _issue(
            issues,
            "metric_consistency",
            "throughput must be positive when requests completed",
            value=throughput,
        )
    elif isinstance(completed, int) and expected_observation_ms > 0:
        expected_throughput = completed * 1000.0 / expected_observation_ms
        if not math.isclose(
            float(throughput), expected_throughput, rel_tol=1e-9, abs_tol=1e-12
        ):
            _issue(
                issues,
                "metric_consistency",
                "throughput does not equal completed requests divided by the frozen observation horizon",
                expected=expected_throughput,
                actual=throughput,
                unit="requests/s",
            )

    completion_ratio = summary.get("completion_ratio")
    if arrivals == 0:
        if completion_ratio is not None:
            _issue(
                issues,
                "metric_consistency",
                "completion_ratio must be null when arrivals is zero",
                value=completion_ratio,
            )
    elif isinstance(arrivals, int) and arrivals > 0 and isinstance(completed, int):
        expected_ratio = completed / arrivals
        if (
            isinstance(completion_ratio, bool)
            or not isinstance(completion_ratio, (int, float))
            or not math.isfinite(float(completion_ratio))
            or not math.isclose(
                float(completion_ratio), expected_ratio, rel_tol=1e-9, abs_tol=1e-12
            )
        ):
            _issue(
                issues,
                "metric_consistency",
                "completion_ratio is inconsistent with counters",
                expected=expected_ratio,
                actual=completion_ratio,
            )

    latency_names = ("mean", "p50", "p95", "p99")
    if completed == 0:
        for name in latency_names:
            if latency.get(name) is not None:
                _issue(
                    issues,
                    "metric_consistency",
                    f"latency {name} must be null when completed is zero",
                    value=latency.get(name),
                )
        if metrics["cost_per_completed"] is not None:
            _issue(
                issues,
                "metric_consistency",
                "per-completed cost must be null when completed is zero",
                value=metrics["cost_per_completed"],
            )
    elif isinstance(completed, int) and completed > 0:
        for name in latency_names:
            value = latency.get(name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                _issue(
                    issues,
                    "invalid_metric",
                    f"latency {name} must be finite and non-negative when requests complete",
                    value=value,
                )
        percentiles = [latency.get(name) for name in ("p50", "p95", "p99")]
        if all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in percentiles
        ):
            if not (percentiles[0] <= percentiles[1] <= percentiles[2]):
                _issue(
                    issues,
                    "metric_consistency",
                    "latency percentiles are not ordered",
                    values=percentiles,
                )
        value = metrics["cost_per_completed"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value < 0
        ):
            _issue(
                issues,
                "invalid_metric",
                "per-completed cost must be finite and non-negative when requests complete",
                value=value,
            )

    for name in latency_names:
        legacy_value = latency.get(name)
        cohort_value = drained_latency.get(name)
        matches = (
            cohort_value is None
            if legacy_value is None
            else isinstance(cohort_value, (int, float))
            and not isinstance(cohort_value, bool)
            and math.isfinite(float(cohort_value))
            and isinstance(legacy_value, (int, float))
            and not isinstance(legacy_value, bool)
            and math.isclose(
                float(cohort_value),
                float(legacy_value),
                rel_tol=1e-9,
                abs_tol=1e-12,
            )
        )
        if not matches:
            _issue(
                issues,
                "cohort_metric_mismatch",
                f"drained cohort latency {name} differs from the compatible final-run latency",
                expected=legacy_value,
                actual=cohort_value,
            )

    cost = metrics["cost"]
    if (
        isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(float(cost))
        or cost < 0
    ):
        _issue(
            issues,
            "invalid_metric",
            "total cost must be finite and non-negative",
            value=cost,
        )

    utilization_definition = summary.get("node_utilization_definition")
    expected_utilization_unit = summary_contract.get(
        "node_utilization_unit", "fraction_of_node_capacity"
    )
    if summary.get("node_utilization_unit") != expected_utilization_unit:
        _issue(
            issues,
            "unit_mismatch",
            "normalized node utilization must be reported as fraction_of_node_capacity",
            expected=expected_utilization_unit,
            actual=summary.get("node_utilization_unit"),
        )
    if not isinstance(utilization_definition, dict):
        _issue(
            issues,
            "missing_provenance",
            "node utilization denominator and sampling definition are missing",
        )
    else:
        expected_definition = summary_contract.get("node_utilization_definition", {})
        _require_fields(
            utilization_definition,
            tuple(expected_definition)
            + (
                "cpu_valid_samples",
                "cpu_invalid_samples",
                "memory_valid_samples",
                "memory_invalid_samples",
            ),
            issues,
            scope="NSE_SUMMARY_V1.node_utilization_definition",
        )
        for field, expected in expected_definition.items():
            if utilization_definition.get(field) != expected:
                _issue(
                    issues,
                    "missing_provenance",
                    f"node utilization definition {field} is missing or changed",
                    expected=expected,
                    actual=utilization_definition.get(field),
                )
        expected_samples = int(run["cluster"]["node_count"]) * int(
            simulation["expected_frame_count"]
        )
        for resource in ("cpu", "memory"):
            valid = utilization_definition.get(f"{resource}_valid_samples")
            invalid = utilization_definition.get(f"{resource}_invalid_samples")
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in (valid, invalid)
            ):
                _issue(
                    issues,
                    "invalid_counter",
                    f"{resource} utilization valid/invalid sample counters are invalid",
                    valid=valid,
                    invalid=invalid,
                )
            elif valid + invalid != expected_samples:
                _issue(
                    issues,
                    "metric_consistency",
                    f"{resource} utilization sample counters do not cover every node-frame",
                    expected=expected_samples,
                    valid=valid,
                    invalid=invalid,
                )
            elif invalid != 0 or valid != expected_samples:
                _issue(
                    issues,
                    "invalid_observation_samples",
                    f"{resource} utilization has invalid or excluded node-frame samples",
                    expected_valid=expected_samples,
                    valid=valid,
                    invalid=invalid,
                )
            for suffix in ("mean", "p95", "peak"):
                value = summary.get(f"node_{resource}_utilization_{suffix}")
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or value < 0
                ):
                    _issue(
                        issues,
                        "invalid_metric",
                        f"node_{resource}_utilization_{suffix} must be finite and non-negative",
                        value=value,
                    )
            p95 = summary.get(f"node_{resource}_utilization_p95")
            peak = summary.get(f"node_{resource}_utilization_peak")
            mean_value = summary.get(f"node_{resource}_utilization_mean")
            if (
                isinstance(p95, (int, float))
                and not isinstance(p95, bool)
                and isinstance(peak, (int, float))
                and not isinstance(peak, bool)
                and math.isfinite(float(p95))
                and math.isfinite(float(peak))
                and p95 > peak
            ):
                _issue(
                    issues,
                    "metric_consistency",
                    f"node {resource} utilization p95 exceeds its peak",
                    p95=p95,
                    peak=peak,
                )
            if (
                isinstance(mean_value, (int, float))
                and not isinstance(mean_value, bool)
                and isinstance(peak, (int, float))
                and not isinstance(peak, bool)
                and math.isfinite(float(mean_value))
                and math.isfinite(float(peak))
                and mean_value > peak
            ):
                _issue(
                    issues,
                    "metric_consistency",
                    f"node {resource} utilization mean exceeds its peak",
                    mean=mean_value,
                    peak=peak,
                )

    scheduler_count = metrics["scheduler_window_count"]
    expected_scheduler_timing_definition = summary_contract.get(
        "scheduler_timing_definition", {}
    )
    if (
        summary.get("scheduler_timing_definition")
        != expected_scheduler_timing_definition
    ):
        _issue(
            issues,
            "missing_provenance",
            "scheduler timing boundaries differ from the frozen formal definition",
            expected=expected_scheduler_timing_definition,
            actual=summary.get("scheduler_timing_definition"),
        )
    if (
        isinstance(scheduler_count, bool)
        or not isinstance(scheduler_count, int)
        or scheduler_count < 0
    ):
        _issue(
            issues,
            "invalid_counter",
            "scheduler_window_count must be a non-negative integer",
            value=scheduler_count,
        )
    elif scheduler_count == 0:
        if any(
            summary.get(field) is not None
            for field in (
                "scheduler_wall_ns",
                "scheduler_thread_cpu_ns",
                "placement_policy_wall_ns",
                "placement_policy_thread_cpu_ns",
                "posthoc_welfare_evaluation_wall_ns",
                "posthoc_welfare_evaluation_thread_cpu_ns",
            )
        ):
            _issue(
                issues,
                "metric_consistency",
                "scheduler distributions must be null when there are no windows",
            )
    else:
        for distribution_name, distribution in (
            ("scheduler_wall_ns", summary.get("scheduler_wall_ns")),
            ("scheduler_thread_cpu_ns", summary.get("scheduler_thread_cpu_ns")),
            ("placement_policy_wall_ns", summary.get("placement_policy_wall_ns")),
            (
                "placement_policy_thread_cpu_ns",
                summary.get("placement_policy_thread_cpu_ns"),
            ),
            (
                "posthoc_welfare_evaluation_wall_ns",
                summary.get("posthoc_welfare_evaluation_wall_ns"),
            ),
            (
                "posthoc_welfare_evaluation_thread_cpu_ns",
                summary.get("posthoc_welfare_evaluation_thread_cpu_ns"),
            ),
        ):
            if not isinstance(distribution, dict):
                _issue(
                    issues,
                    "invalid_metric",
                    f"{distribution_name} must be an object when windows exist",
                )
                continue
            _require_fields(
                distribution,
                ("mean", "p50", "p95", "p99", "max"),
                issues,
                scope=f"NSE_SUMMARY_V1.{distribution_name}",
            )
            for name in ("mean", "p50", "p95", "p99", "max"):
                value = distribution.get(name)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or value < 0
                ):
                    _issue(
                        issues,
                        "invalid_metric",
                        f"{distribution_name}.{name} must be finite and non-negative",
                        value=value,
                    )
            ordered = [distribution.get(name) for name in ("p50", "p95", "p99", "max")]
            if all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                for value in ordered
            ) and not (ordered[0] <= ordered[1] <= ordered[2] <= ordered[3]):
                _issue(
                    issues,
                    "metric_consistency",
                    f"{distribution_name} percentiles/max are not ordered",
                    values=ordered,
                )
            mean_value = distribution.get("mean")
            if (
                isinstance(mean_value, (int, float))
                and not isinstance(mean_value, bool)
                and isinstance(distribution.get("max"), (int, float))
                and not isinstance(distribution.get("max"), bool)
                and mean_value > distribution["max"]
            ):
                _issue(
                    issues,
                    "metric_consistency",
                    f"{distribution_name} mean exceeds max",
                    mean=mean_value,
                    maximum=distribution.get("max"),
                )

    for name in (
        "queue_peak",
        "queue_area_request_frames",
        "placement_rejections",
        "drops",
        "rejects",
        "timeouts",
    ):
        value = metrics[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _issue(
                issues,
                "invalid_counter",
                f"{name} must be a non-negative integer",
                metric=name,
                value=value,
            )
    if summary.get("queue_semantics") != "unbounded_wait_by_design":
        _issue(
            issues,
            "queue_semantics_mismatch",
            "formal queue semantics must be explicitly declared as unbounded_wait_by_design",
            actual=summary.get("queue_semantics"),
        )
    elif any(metrics[name] != 0 for name in ("drops", "rejects", "timeouts")):
        _issue(
            issues,
            "counter_semantics_mismatch",
            "unbounded-wait runs cannot report admission drops, rejections, or timeouts",
            drops=metrics["drops"],
            rejects=metrics["rejects"],
            timeouts=metrics["timeouts"],
        )

    qos_config = run.get("simulator_experiment", {}).get("qos", {})
    qos_profile = run.get("workload", {}).get("qos_profile")
    profile_classes = summary_contract.get("qos_classes_by_profile", {})
    configured_classes = (
        profile_classes.get(qos_profile) if isinstance(profile_classes, dict) else None
    )
    expected_qos_classes = (
        set(configured_classes) if isinstance(configured_classes, list) else set()
    )
    expected_qos_enabled = qos_profile == "balanced"
    if (
        not expected_qos_classes
        or qos_config.get("enabled") is not expected_qos_enabled
    ):
        _issue(
            issues,
            "configuration_mismatch",
            "formal QoS profile does not match its frozen recorder class mapping",
            qos_profile=qos_profile,
            expected_classes=sorted(expected_qos_classes),
            expected_enabled=expected_qos_enabled,
            actual_enabled=qos_config.get("enabled"),
        )
    qos_tasks = summary.get("qos_function_tasks")
    qos_cost = summary.get("qos_simulator_internal_cost")
    if not isinstance(qos_tasks, dict):
        _issue(
            issues,
            "missing_qos_counters",
            "formal run lacks qos_function_tasks",
        )
    if not isinstance(qos_cost, dict):
        _issue(
            issues,
            "missing_qos_counters",
            "formal run lacks qos_simulator_internal_cost",
        )
    if isinstance(qos_tasks, dict):
        actual_classes = set(qos_tasks)
        if actual_classes != expected_qos_classes:
            _issue(
                issues,
                "qos_profile_mismatch",
                "QoS counters do not cover exactly the frozen class assignment",
                expected=sorted(expected_qos_classes),
                actual=sorted(actual_classes),
            )
        for qos_class, counters in qos_tasks.items():
            if qos_class not in expected_qos_classes or not isinstance(counters, dict):
                _issue(
                    issues,
                    "invalid_qos_counters",
                    "QoS task counter entry is not valid for the frozen profile",
                    qos_class=qos_class,
                )
                continue
            _require_fields(
                counters,
                ("arrived", "completed", "active", "completion_ratio"),
                issues,
                scope=f"NSE_SUMMARY_V1.qos_function_tasks.{qos_class}",
            )
            arrived = counters.get("arrived")
            function_completed = counters.get("completed")
            active = counters.get("active")
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in (arrived, function_completed, active)
            ):
                _issue(
                    issues,
                    "invalid_qos_counters",
                    "QoS arrived/completed/active counters must be non-negative integers",
                    qos_class=qos_class,
                )
                continue
            if function_completed > arrived or active != arrived - function_completed:
                _issue(
                    issues,
                    "counter_conservation",
                    "QoS function counters violate conservation",
                    qos_class=qos_class,
                    arrived=arrived,
                    completed=function_completed,
                    active=active,
                )
            ratio_value = counters.get("completion_ratio")
            expected_qos_ratio = None if arrived == 0 else function_completed / arrived
            if expected_qos_ratio is None:
                ratio_valid = ratio_value is None
            else:
                ratio_valid = (
                    isinstance(ratio_value, (int, float))
                    and not isinstance(ratio_value, bool)
                    and math.isfinite(float(ratio_value))
                    and math.isclose(
                        float(ratio_value),
                        expected_qos_ratio,
                        rel_tol=1e-9,
                        abs_tol=1e-12,
                    )
                )
            if not ratio_valid:
                _issue(
                    issues,
                    "metric_consistency",
                    "QoS completion ratio is inconsistent with function counters",
                    qos_class=qos_class,
                    expected=expected_qos_ratio,
                    actual=ratio_value,
                )
    if isinstance(qos_cost, dict):
        actual_cost_classes = set(qos_cost)
        if actual_cost_classes != expected_qos_classes:
            _issue(
                issues,
                "qos_profile_mismatch",
                "QoS cost summary does not cover exactly the frozen profile classes",
                expected=sorted(expected_qos_classes),
                actual=sorted(actual_cost_classes),
            )
        if isinstance(qos_tasks, dict) and set(qos_cost) != set(qos_tasks):
            _issue(
                issues,
                "qos_profile_mismatch",
                "QoS task and cost summaries cover different classes",
                task_classes=sorted(qos_tasks),
                cost_classes=sorted(qos_cost),
            )
        for qos_class, cost_entry in qos_cost.items():
            if qos_class not in expected_qos_classes or not isinstance(
                cost_entry, dict
            ):
                _issue(
                    issues,
                    "invalid_qos_counters",
                    "QoS cost entry is not valid for the frozen profile",
                    qos_class=qos_class,
                )
                continue
            _require_fields(
                cost_entry,
                ("unit", "total", "per_completed_function", "is_currency"),
                issues,
                scope=f"NSE_SUMMARY_V1.qos_simulator_internal_cost.{qos_class}",
            )
            total = cost_entry.get("total")
            if (
                cost_entry.get("unit") != "simulator_internal_units"
                or cost_entry.get("is_currency") is not False
                or isinstance(total, bool)
                or not isinstance(total, (int, float))
                or not math.isfinite(float(total))
                or total < 0
            ):
                _issue(
                    issues,
                    "invalid_qos_counters",
                    "QoS cost must be finite, non-negative simulator-internal units",
                    qos_class=qos_class,
                )
                continue
            completed_functions = None
            if isinstance(qos_tasks, dict) and isinstance(
                qos_tasks.get(qos_class), dict
            ):
                completed_functions = qos_tasks[qos_class].get("completed")
            per_completed = cost_entry.get("per_completed_function")
            if completed_functions == 0:
                valid_per_completed = per_completed is None
            elif isinstance(completed_functions, int) and completed_functions > 0:
                valid_per_completed = (
                    isinstance(per_completed, (int, float))
                    and not isinstance(per_completed, bool)
                    and math.isfinite(float(per_completed))
                    and math.isclose(
                        float(per_completed),
                        float(total) / completed_functions,
                        rel_tol=1e-9,
                        abs_tol=1e-12,
                    )
                )
            else:
                valid_per_completed = False
            if not valid_per_completed:
                _issue(
                    issues,
                    "metric_consistency",
                    "QoS per-completed-function cost is inconsistent with counters",
                    qos_class=qos_class,
                    actual=per_completed,
                )
    return summary, {
        "metrics": metrics,
        "final_frame": summary.get("final_frame"),
        "frame_count": summary.get("frames_recorded"),
    }


def _iter_jsonl_objects(
    path: Path, maximum_line_bytes: int
) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if len(raw_line) > maximum_line_bytes:
                raise RecordStreamError(
                    f"line {line_number} exceeds {maximum_line_bytes} bytes"
                )
            if not raw_line.strip():
                raise RecordStreamError(f"line {line_number} is blank")
            try:
                value = json.loads(raw_line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RecordStreamError(
                    f"line {line_number} is invalid JSON: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise RecordStreamError(f"line {line_number} is not a JSON object")
            nonfinite = next(_walk_nonfinite(value), None)
            if nonfinite is not None:
                raise RecordStreamError(
                    f"line {line_number} has nonfinite value at {nonfinite[0]}"
                )
            yield line_number, value


def _validate_nse_artifacts(
    result_path: Path,
    run: dict[str, Any],
    qc: dict[str, Any],
    summary: dict[str, Any],
    issues: list[QCIssue],
) -> dict[str, Any]:
    run_directory = result_path.parent
    environment_observation: dict[str, Any] = {}
    partials = sorted(run_directory.glob("*.partial"))
    if partials:
        _issue(
            issues,
            "partial_jsonl_artifact",
            "NSE reviewer directory contains unfinished partial files",
            paths=[path.name for path in partials],
        )
    environment_path = run_directory / "environment.json"
    expected_streams = {
        "frames.jsonl": "NSE_FRAME_V1",
        "requests.jsonl": "NSE_REQUEST_V1",
        "scheduler_windows.jsonl": "NSE_SCHEDULER_WINDOW_V1",
    }
    for path in [
        environment_path,
        *(run_directory / name for name in expected_streams),
    ]:
        if not path.is_file():
            _issue(
                issues,
                "missing_jsonl_artifact",
                "required NSE reviewer artifact is missing",
                path=str(path),
            )
    if not environment_path.is_file() or any(
        not (run_directory / name).is_file() for name in expected_streams
    ):
        return {}
    try:
        environment = read_json(environment_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _issue(
            issues,
            "invalid_environment",
            "environment.json cannot be parsed",
            error=str(exc),
        )
        environment = {}
    if (
        not isinstance(environment, dict)
        or environment.get("schema") != "NSE_ENVIRONMENT_V1"
    ):
        _issue(
            issues,
            "invalid_environment",
            "environment schema must be NSE_ENVIRONMENT_V1",
        )
    elif environment.get("run_id") != run["run_id"]:
        _issue(
            issues,
            "provenance_mismatch",
            "environment run_id differs from manifest",
            expected=run["run_id"],
            actual=environment.get("run_id"),
        )
    if (
        isinstance(environment, dict)
        and environment.get("schema") == "NSE_ENVIRONMENT_V1"
    ):
        functions = environment.get("functions")
        nodes = environment.get("nodes")
        network = environment.get("network_mb_per_second")
        if (
            not isinstance(functions, list)
            or not isinstance(nodes, list)
            or not isinstance(network, list)
        ):
            _issue(
                issues,
                "invalid_environment",
                "environment lacks function, node, or network arrays needed for semantic hashes",
            )
        else:
            function_hash = object_hash(functions)
            node_network_hash = object_hash(
                {"nodes": nodes, "network_mb_per_second": network}
            )
            environment_observation = {
                "environment_sha256": file_hash(environment_path),
                "function_dag_qos_sha256": function_hash,
                "node_network_sha256": node_network_hash,
                "function_count": len(functions),
                "node_count": len(nodes),
            }
            capture = run.get("workload_tape", {}).get("capture_environment", {})
            expected_function_hash = capture.get("function_dag_qos_sha256")
            if (
                isinstance(expected_function_hash, str)
                and function_hash != expected_function_hash
            ):
                _issue(
                    issues,
                    "workload_environment_mismatch",
                    "runtime function/DAG/QoS definition differs from the tape-capture environment",
                    expected=expected_function_hash,
                    actual=function_hash,
                )
            capture_node_count = capture.get("node_count")
            expected_node_network_hash = capture.get("node_network_sha256")
            if (
                capture_node_count == len(nodes)
                and isinstance(expected_node_network_hash, str)
                and node_network_hash != expected_node_network_hash
            ):
                _issue(
                    issues,
                    "topology_environment_mismatch",
                    "runtime node/network definition differs from the same-size tape-capture environment",
                    expected=expected_node_network_hash,
                    actual=node_network_hash,
                )
        arrival_generation = environment.get("arrival_generation")
        if not isinstance(arrival_generation, dict):
            _issue(
                issues,
                "missing_provenance",
                "environment arrival-generation provenance is missing",
            )
        else:
            if arrival_generation.get("frequency_profile") != run.get(
                "workload_profile"
            ):
                _issue(
                    issues,
                    "workload_profile_mismatch",
                    "runtime workload profile differs from the frozen manifest binding",
                )
            if arrival_generation.get("arrival_noise_seed") != run.get("seed"):
                _issue(
                    issues,
                    "provenance_mismatch",
                    "runtime arrival-noise seed differs from the paired workload seed",
                )
    config = environment.get("config") if isinstance(environment, dict) else None
    experiment = config.get("experiment") if isinstance(config, dict) else None
    if not isinstance(experiment, dict):
        _issue(issues, "missing_provenance", "environment config.experiment is missing")
    else:
        if experiment.get("run_id") != run["run_id"]:
            _issue(
                issues,
                "provenance_mismatch",
                "environment experiment.run_id differs from manifest",
            )
        if experiment.get("node_count") != run["cluster"]["node_count"]:
            _issue(
                issues,
                "configuration_mismatch",
                "environment node_count differs from manifest",
                expected=run["cluster"]["node_count"],
                actual=experiment.get("node_count"),
            )
        actual_hpa = experiment.get("hpa")
        for key in (
            "target_mem_use_rate",
            "tolerance",
            "check_period_frames",
            "careful_down_history",
            "min_instances_when_pending",
            "allow_scale_to_zero",
            "scale_up_placement",
        ):
            expected_hpa_value = run["common_hpa"].get(key)
            actual_hpa_value = (
                actual_hpa.get(key) if isinstance(actual_hpa, dict) else None
            )
            if not isinstance(actual_hpa, dict) or not _experiment_scalar_equal(
                expected_hpa_value, actual_hpa_value, ("hpa", key)
            ):
                _issue(
                    issues,
                    "configuration_mismatch",
                    f"environment common-HPA field {key} differs from manifest",
                    expected=expected_hpa_value,
                    actual=actual_hpa_value,
                )
        expected_experiment = json.loads(json.dumps(run["simulator_experiment"]))
        actual_experiment = json.loads(json.dumps(experiment))
        # These are execution materializations of already hash-bound inputs;
        # compare their hashes elsewhere and compare all other Rust fields here.
        for payload in (expected_experiment, actual_experiment):
            if isinstance(payload.get("workload"), dict):
                payload["workload"]["tape_path"] = "__MATERIALIZED_TAPE_PATH__"
            if isinstance(payload.get("reference"), dict):
                payload["reference"]["table_path"] = "__MATERIALIZED_REFERENCE_PATH__"
                payload["reference"][
                    "build_output_path"
                ] = "__MATERIALIZED_BUILD_PATH__"
            if isinstance(payload.get("output"), dict):
                payload["output"]["root"] = "__MATERIALIZED_OUTPUT_ROOT__"
        experiment_differences = _experiment_config_differences(
            expected_experiment, actual_experiment
        )
        if experiment_differences:
            _issue(
                issues,
                "configuration_mismatch",
                "environment ExperimentConfig differs from the frozen formal payload",
                differences=experiment_differences,
            )

    maximum_line_bytes = int(
        qc.get("jsonl_artifacts", {}).get("max_line_bytes", 16 * 1024 * 1024)
    )
    frame_count = 0
    last_frame = -1
    last_arrivals = -1
    last_completed = -1
    last_drop = -1
    last_reject = -1
    last_timeout = -1
    last_qos_tasks: dict[str, Any] | None = None
    observed_queue_peak = 0
    observed_queue_area = 0
    summary_contract = qc.get("nse_summary_contract", {})
    qos_profile = run.get("workload", {}).get("qos_profile")
    profile_classes = summary_contract.get("qos_classes_by_profile", {})
    configured_qos_classes = (
        profile_classes.get(qos_profile) if isinstance(profile_classes, dict) else None
    )
    expected_qos_classes = (
        set(configured_qos_classes)
        if isinstance(configured_qos_classes, list)
        else set()
    )
    observed_qos_cost = {qos_class: 0.0 for qos_class in expected_qos_classes}
    last_simulator_cost: float | None = None
    observed_resource_samples = {
        "cpu_valid": 0,
        "cpu_invalid": 0,
        "memory_valid": 0,
        "memory_invalid": 0,
    }
    observed_resource_weighted_sum = {"cpu": 0.0, "memory": 0.0}
    observed_resource_peak = {"cpu": 0.0, "memory": 0.0}
    try:
        for line_number, event in _iter_jsonl_objects(
            run_directory / "frames.jsonl", maximum_line_bytes
        ):
            if event.get("schema") != "NSE_FRAME_V1":
                raise RecordStreamError(
                    f"line {line_number} schema is not NSE_FRAME_V1"
                )
            if event.get("frame") != frame_count:
                raise RecordStreamError(
                    f"line {line_number} frame is {event.get('frame')}, expected {frame_count}"
                )
            arrivals = event.get("arrivals_total")
            completed = event.get("completed_total")
            active = event.get("active_requests")
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in (arrivals, completed, active)
            ):
                raise RecordStreamError(
                    f"line {line_number} contains invalid request counters"
                )
            if (
                arrivals < last_arrivals
                or completed < last_completed
                or active != arrivals - completed
            ):
                raise RecordStreamError(
                    f"line {line_number} request counters violate conservation/monotonicity"
                )
            drop = event.get("drop_total")
            reject = event.get("reject_total")
            timeout = event.get("timeout_total")
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in (drop, reject, timeout)
            ):
                raise RecordStreamError(
                    f"line {line_number} contains invalid admission/timeout counters"
                )
            if drop < last_drop or reject < last_reject or timeout < last_timeout:
                raise RecordStreamError(
                    f"line {line_number} admission/timeout counters are not monotonic"
                )
            queue = event.get("queue_total")
            if isinstance(queue, bool) or not isinstance(queue, int) or queue < 0:
                raise RecordStreamError(
                    f"line {line_number} contains an invalid queue_total"
                )
            qos_tasks = event.get("qos_function_tasks")
            if not isinstance(qos_tasks, dict):
                raise RecordStreamError(
                    f"line {line_number} lacks formal QoS function task counters"
                )
            if not set(qos_tasks).issubset(expected_qos_classes):
                raise RecordStreamError(
                    f"line {line_number} contains QoS classes outside the frozen profile"
                )
            for qos_class, counters in qos_tasks.items():
                if not isinstance(counters, dict):
                    raise RecordStreamError(
                        f"line {line_number} QoS class {qos_class!r} is not an object"
                    )
                arrived = counters.get("arrived")
                function_completed = counters.get("completed")
                function_active = counters.get("active")
                if any(
                    isinstance(value, bool) or not isinstance(value, int) or value < 0
                    for value in (arrived, function_completed, function_active)
                ):
                    raise RecordStreamError(
                        f"line {line_number} QoS class {qos_class!r} has invalid counters"
                    )
                if (
                    function_completed > arrived
                    or function_active != arrived - function_completed
                ):
                    raise RecordStreamError(
                        f"line {line_number} QoS class {qos_class!r} violates counter conservation"
                    )
                ratio_value = counters.get("completion_ratio")
                expected_ratio = None if arrived == 0 else function_completed / arrived
                ratio_matches = (
                    ratio_value is None
                    if expected_ratio is None
                    else isinstance(ratio_value, (int, float))
                    and not isinstance(ratio_value, bool)
                    and math.isfinite(float(ratio_value))
                    and math.isclose(
                        float(ratio_value),
                        expected_ratio,
                        rel_tol=1e-9,
                        abs_tol=1e-12,
                    )
                )
                if not ratio_matches:
                    raise RecordStreamError(
                        f"line {line_number} QoS class {qos_class!r} has an inconsistent completion ratio"
                    )
            qos_resources = event.get("qos_resources")
            if not isinstance(qos_resources, dict):
                raise RecordStreamError(
                    f"line {line_number} lacks formal QoS resource/cost observations"
                )
            if not set(qos_resources).issubset(expected_qos_classes):
                raise RecordStreamError(
                    f"line {line_number} contains QoS resource classes outside the frozen profile"
                )
            for qos_class, resources in qos_resources.items():
                if not isinstance(resources, dict):
                    raise RecordStreamError(
                        f"line {line_number} QoS resources for {qos_class!r} are not an object"
                    )
                values = (
                    resources.get("cpu_work"),
                    resources.get("memory"),
                    resources.get("simulator_internal_cost"),
                )
                if any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or value < 0
                    for value in values
                ):
                    raise RecordStreamError(
                        f"line {line_number} QoS resources for {qos_class!r} are invalid"
                    )
                observed_qos_cost[qos_class] += float(values[2])
            simulator_cost = event.get("simulator_cost_total")
            if (
                isinstance(simulator_cost, bool)
                or not isinstance(simulator_cost, (int, float))
                or not math.isfinite(float(simulator_cost))
                or simulator_cost < 0
            ):
                raise RecordStreamError(
                    f"line {line_number} has an invalid simulator_cost_total"
                )
            if (
                last_simulator_cost is not None
                and float(simulator_cost) < last_simulator_cost
            ):
                raise RecordStreamError(
                    f"line {line_number} simulator_cost_total is not monotonic"
                )
            last_simulator_cost = float(simulator_cost)
            expected_node_samples = int(run["cluster"]["node_count"])
            for resource in ("cpu", "memory"):
                valid = event.get(f"node_{resource}_utilization_valid_samples")
                invalid = event.get(f"node_{resource}_utilization_invalid_samples")
                if any(
                    isinstance(value, bool) or not isinstance(value, int) or value < 0
                    for value in (valid, invalid)
                ):
                    raise RecordStreamError(
                        f"line {line_number} has invalid {resource} utilization sample counters"
                    )
                if valid + invalid != expected_node_samples:
                    raise RecordStreamError(
                        f"line {line_number} {resource} utilization samples do not match node count"
                    )
                observed_resource_samples[f"{resource}_valid"] += valid
                observed_resource_samples[f"{resource}_invalid"] += invalid
                resource_values: dict[str, float] = {}
                for suffix in ("mean", "peak"):
                    value = event.get(f"node_{resource}_utilization_{suffix}")
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                        or value < 0
                    ):
                        raise RecordStreamError(
                            f"line {line_number} has invalid node_{resource}_utilization_{suffix}"
                        )
                    resource_values[suffix] = float(value)
                if resource_values["mean"] > resource_values["peak"]:
                    raise RecordStreamError(
                        f"line {line_number} node {resource} utilization mean exceeds peak"
                    )
                observed_resource_weighted_sum[resource] += (
                    resource_values["mean"] * valid
                )
                observed_resource_peak[resource] = max(
                    observed_resource_peak[resource], resource_values["peak"]
                )
            last_frame = event["frame"]
            last_arrivals = arrivals
            last_completed = completed
            last_drop = drop
            last_reject = reject
            last_timeout = timeout
            last_qos_tasks = qos_tasks
            observed_queue_peak = max(observed_queue_peak, queue)
            observed_queue_area += queue
            frame_count += 1
    except (OSError, RecordStreamError) as exc:
        _issue(
            issues,
            "invalid_jsonl_artifact",
            "frames.jsonl failed streaming schema validation",
            error=str(exc),
        )
    if (
        frame_count != run["simulation"]["expected_frame_count"]
        or last_frame != run["simulation"]["expected_final_frame"]
    ):
        _issue(
            issues,
            "wrong_frame_count",
            "frames.jsonl does not cover the exact frozen frame horizon",
            expected_count=run["simulation"]["expected_frame_count"],
            actual_count=frame_count,
            expected_final=run["simulation"]["expected_final_frame"],
            actual_final=last_frame,
        )
    if summary and (
        last_arrivals != summary.get("arrivals")
        or last_completed != summary.get("completed")
    ):
        _issue(
            issues,
            "summary_stream_mismatch",
            "summary arrivals/completed differ from final frame",
            frame_arrivals=last_arrivals,
            summary_arrivals=summary.get("arrivals"),
            frame_completed=last_completed,
            summary_completed=summary.get("completed"),
        )
    if summary and (
        observed_queue_peak != summary.get("queue_peak")
        or observed_queue_area != summary.get("queue_area_request_frames")
    ):
        _issue(
            issues,
            "summary_stream_mismatch",
            "summary queue peak/area differ from the frame stream",
            frame_peak=observed_queue_peak,
            summary_peak=summary.get("queue_peak"),
            frame_area=observed_queue_area,
            summary_area=summary.get("queue_area_request_frames"),
        )
    if summary and (
        last_drop != summary.get("admission_drop")
        or last_reject != summary.get("admission_reject")
        or last_timeout != summary.get("timeout")
    ):
        _issue(
            issues,
            "summary_stream_mismatch",
            "summary admission/timeout counters differ from the final frame",
            frame_counts={
                "drop": last_drop,
                "reject": last_reject,
                "timeout": last_timeout,
            },
        )
    if summary and (
        not isinstance(summary.get("simulator_internal_cost_total"), (int, float))
        or isinstance(summary.get("simulator_internal_cost_total"), bool)
        or last_simulator_cost is None
        or not math.isclose(
            float(summary["simulator_internal_cost_total"]),
            last_simulator_cost,
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
    ):
        _issue(
            issues,
            "summary_stream_mismatch",
            "summary total simulator cost differs from the final frame",
            frame_total=last_simulator_cost,
            summary_total=summary.get("simulator_internal_cost_total"),
        )
    if (
        summary
        and isinstance(summary.get("qos_function_tasks"), dict)
        and (
            run.get("simulator_experiment", {}).get("qos", {}).get("enabled")
            or bool(summary.get("qos_function_tasks"))
        )
        and last_qos_tasks != summary.get("qos_function_tasks")
    ):
        _issue(
            issues,
            "summary_stream_mismatch",
            "summary QoS function counters differ from the final frame",
        )
    utilization_definition = summary.get("node_utilization_definition", {})
    if summary and isinstance(utilization_definition, dict):
        for resource in ("cpu", "memory"):
            for kind in ("valid", "invalid"):
                observed = observed_resource_samples[f"{resource}_{kind}"]
                declared = utilization_definition.get(f"{resource}_{kind}_samples")
                if observed != declared:
                    _issue(
                        issues,
                        "summary_stream_mismatch",
                        f"summary {resource} {kind} sample count differs from frames",
                        observed=observed,
                        declared=declared,
                    )
            valid_samples = observed_resource_samples[f"{resource}_valid"]
            expected_mean = (
                observed_resource_weighted_sum[resource] / valid_samples
                if valid_samples > 0
                else None
            )
            for suffix, expected in (
                ("mean", expected_mean),
                (
                    "peak",
                    observed_resource_peak[resource] if valid_samples > 0 else None,
                ),
            ):
                actual = summary.get(f"node_{resource}_utilization_{suffix}")
                matches = (
                    actual is None
                    if expected is None
                    else isinstance(actual, (int, float))
                    and not isinstance(actual, bool)
                    and math.isfinite(float(actual))
                    and math.isclose(
                        float(actual),
                        float(expected),
                        rel_tol=1e-9,
                        abs_tol=1e-12,
                    )
                )
                if not matches:
                    _issue(
                        issues,
                        "summary_stream_mismatch",
                        f"summary node {resource} utilization {suffix} differs from frames",
                        expected=expected,
                        actual=actual,
                    )
    summary_qos_cost = summary.get("qos_simulator_internal_cost")
    if summary and isinstance(summary_qos_cost, dict):
        for qos_class in expected_qos_classes:
            entry = summary_qos_cost.get(qos_class)
            actual_total = entry.get("total") if isinstance(entry, dict) else None
            expected_total = observed_qos_cost[qos_class]
            if (
                isinstance(actual_total, bool)
                or not isinstance(actual_total, (int, float))
                or not math.isfinite(float(actual_total))
                or not math.isclose(
                    float(actual_total),
                    expected_total,
                    rel_tol=1e-9,
                    abs_tol=1e-12,
                )
            ):
                _issue(
                    issues,
                    "summary_stream_mismatch",
                    "summary QoS cost differs from the frame cost stream",
                    qos_class=qos_class,
                    expected=expected_total,
                    actual=actual_total,
                )

    request_count = 0
    request_ids: set[int] = set()
    request_latencies: list[int] = []
    fixed_window_completions = 0
    fixed_end_frame = int(
        run["simulation"].get(
            "observation_horizon_frames",
            run["simulation"].get("arrival_horizon_frames", 0),
        )
    )
    try:
        for line_number, event in _iter_jsonl_objects(
            run_directory / "requests.jsonl", maximum_line_bytes
        ):
            if event.get("schema") != "NSE_REQUEST_V1":
                raise RecordStreamError(
                    f"line {line_number} schema is not NSE_REQUEST_V1"
                )
            request_id = event.get("request_id")
            arrival = event.get("arrival_frame")
            completion = event.get("completion_frame")
            latency = event.get("latency_ms")
            if (
                isinstance(request_id, bool)
                or not isinstance(request_id, int)
                or request_id in request_ids
            ):
                raise RecordStreamError(
                    f"line {line_number} has invalid/duplicate request_id"
                )
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in (arrival, completion, latency)
            ):
                raise RecordStreamError(
                    f"line {line_number} has invalid request timing"
                )
            if completion < arrival or latency != completion - arrival:
                raise RecordStreamError(
                    f"line {line_number} request latency is inconsistent"
                )
            if not isinstance(event.get("functions"), list):
                raise RecordStreamError(
                    f"line {line_number} functions must be an array"
                )
            request_ids.add(request_id)
            request_latencies.append(latency)
            if arrival >= fixed_end_frame:
                raise RecordStreamError(
                    f"line {line_number} arrival falls outside the frozen arrival cohort"
                )
            if completion <= fixed_end_frame:
                fixed_window_completions += 1
            request_count += 1
    except (OSError, RecordStreamError) as exc:
        _issue(
            issues,
            "invalid_jsonl_artifact",
            "requests.jsonl failed streaming schema validation",
            error=str(exc),
        )
    if summary and request_count != summary.get("completed"):
        _issue(
            issues,
            "summary_stream_mismatch",
            "request event count differs from summary completed",
            request_lines=request_count,
            completed=summary.get("completed"),
        )
    if summary:
        fixed_summary = summary.get("fixed_observation_window")
        declared_fixed_completions = (
            fixed_summary.get("completed") if isinstance(fixed_summary, dict) else None
        )
        if fixed_window_completions != declared_fixed_completions:
            _issue(
                issues,
                "summary_stream_mismatch",
                "fixed-window completion count differs from request completion timestamps",
                observed=fixed_window_completions,
                declared=declared_fixed_completions,
            )
    if summary:
        if request_latencies:
            ordered_latencies = sorted(request_latencies)

            def request_percentile(probability: float) -> int:
                rank = max(1, math.ceil(len(ordered_latencies) * probability))
                return ordered_latencies[min(rank - 1, len(ordered_latencies) - 1)]

            expected_latency = {
                "mean": sum(ordered_latencies) / len(ordered_latencies),
                "p50": request_percentile(0.50),
                "p95": request_percentile(0.95),
                "p99": request_percentile(0.99),
            }
        else:
            expected_latency = {name: None for name in ("mean", "p50", "p95", "p99")}
        actual_latency = summary.get("latency_ms")
        latency_matches = isinstance(actual_latency, dict) and all(
            actual_latency.get(name) is None
            if expected is None
            else isinstance(actual_latency.get(name), (int, float))
            and not isinstance(actual_latency.get(name), bool)
            and math.isfinite(float(actual_latency[name]))
            and math.isclose(
                float(actual_latency[name]),
                float(expected),
                rel_tol=1e-9,
                abs_tol=1e-12,
            )
            for name, expected in expected_latency.items()
        )
        if not latency_matches:
            _issue(
                issues,
                "summary_stream_mismatch",
                "summary latency distribution differs from completed request events",
                expected=expected_latency,
                actual=actual_latency,
            )

    scheduler_count = 0
    scheduler_wall_values: list[int] = []
    scheduler_cpu_values: list[int] = []
    scheduler_policy_wall_values: list[int] = []
    scheduler_policy_cpu_values: list[int] = []
    scheduler_welfare_wall_values: list[int] = []
    scheduler_welfare_cpu_values: list[int] = []
    placement_rejections = 0
    try:
        for line_number, event in _iter_jsonl_objects(
            run_directory / "scheduler_windows.jsonl", maximum_line_bytes
        ):
            if event.get("schema") != "NSE_SCHEDULER_WINDOW_V1":
                raise RecordStreamError(
                    f"line {line_number} schema is not NSE_SCHEDULER_WINDOW_V1"
                )
            begin = event.get("begin_frame")
            end = event.get("end_frame")
            wall = event.get("wall_time_ns")
            cpu = event.get("thread_cpu_ns")
            policy_wall = event.get("policy_wall_time_ns")
            policy_cpu = event.get("policy_thread_cpu_ns")
            welfare_wall = event.get("welfare_evaluation_wall_time_ns")
            welfare_cpu = event.get("welfare_evaluation_thread_cpu_ns")
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in (
                    begin,
                    end,
                    wall,
                    cpu,
                    policy_wall,
                    policy_cpu,
                    welfare_wall,
                    welfare_cpu,
                )
            ):
                raise RecordStreamError(
                    f"line {line_number} contains invalid scheduler timing"
                )
            if end < begin:
                raise RecordStreamError(
                    f"line {line_number} scheduler window ends before it begins"
                )
            expected_timing_scope = {
                "wall_time_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
                "thread_cpu_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
                "policy_wall_time_ns": "placement_policy_call_exact_boundary",
                "policy_thread_cpu_ns": "placement_policy_call_exact_boundary",
                "welfare_evaluation_wall_time_ns": "read_only_posthoc_observer_exact_boundary",
                "welfare_evaluation_thread_cpu_ns": "read_only_posthoc_observer_exact_boundary",
                "policy_time_derived_by_subtraction": False,
            }
            if event.get("timing_scope") != expected_timing_scope:
                raise RecordStreamError(
                    f"line {line_number} scheduler timing_scope differs from the frozen boundary"
                )
            rejected = event.get("placements_rejected")
            if (
                isinstance(rejected, bool)
                or not isinstance(rejected, int)
                or rejected < 0
            ):
                raise RecordStreamError(
                    f"line {line_number} contains invalid placement rejection count"
                )
            scheduler_wall_values.append(wall)
            scheduler_cpu_values.append(cpu)
            scheduler_policy_wall_values.append(policy_wall)
            scheduler_policy_cpu_values.append(policy_cpu)
            scheduler_welfare_wall_values.append(welfare_wall)
            scheduler_welfare_cpu_values.append(welfare_cpu)
            placement_rejections += rejected
            scheduler_count += 1
    except (OSError, RecordStreamError) as exc:
        _issue(
            issues,
            "invalid_jsonl_artifact",
            "scheduler_windows.jsonl failed streaming schema validation",
            error=str(exc),
        )
    if summary and scheduler_count != summary.get("scheduler_window_count"):
        _issue(
            issues,
            "summary_stream_mismatch",
            "scheduler event count differs from summary",
            scheduler_lines=scheduler_count,
            summary_count=summary.get("scheduler_window_count"),
        )
    if summary and placement_rejections != summary.get("placement_rejections"):
        _issue(
            issues,
            "summary_stream_mismatch",
            "summary placement rejection count differs from scheduler windows",
            scheduler_total=placement_rejections,
            summary_total=summary.get("placement_rejections"),
        )

    def stream_distribution(values: list[int]) -> dict[str, float | int] | None:
        if not values:
            return None
        ordered = sorted(values)

        def nearest_rank(probability: float) -> int:
            rank = max(1, math.ceil(len(ordered) * probability))
            return ordered[min(rank - 1, len(ordered) - 1)]

        return {
            "mean": sum(ordered) / len(ordered),
            "p50": nearest_rank(0.50),
            "p95": nearest_rank(0.95),
            "p99": nearest_rank(0.99),
            "max": ordered[-1],
        }

    if summary:
        for field, values in (
            ("scheduler_wall_ns", scheduler_wall_values),
            ("scheduler_thread_cpu_ns", scheduler_cpu_values),
            ("placement_policy_wall_ns", scheduler_policy_wall_values),
            ("placement_policy_thread_cpu_ns", scheduler_policy_cpu_values),
            (
                "posthoc_welfare_evaluation_wall_ns",
                scheduler_welfare_wall_values,
            ),
            (
                "posthoc_welfare_evaluation_thread_cpu_ns",
                scheduler_welfare_cpu_values,
            ),
        ):
            expected_distribution = stream_distribution(values)
            actual_distribution = summary.get(field)
            distribution_matches = (
                actual_distribution is None
                if expected_distribution is None
                else isinstance(actual_distribution, dict)
                and all(
                    isinstance(actual_distribution.get(key), (int, float))
                    and not isinstance(actual_distribution.get(key), bool)
                    and math.isclose(
                        float(actual_distribution[key]),
                        float(expected),
                        rel_tol=1e-9,
                        abs_tol=1e-12,
                    )
                    for key, expected in expected_distribution.items()
                )
            )
            if not distribution_matches:
                _issue(
                    issues,
                    "summary_stream_mismatch",
                    f"summary {field} distribution differs from scheduler windows",
                    expected=expected_distribution,
                    actual=actual_distribution,
                )
    reference_pair_observation: dict[str, Any] = {}
    policy_observation_lines = 0
    policy_window_count = 0
    policy_path = run_directory / (
        "nash_metrics.jsonl"
        if run["method"] == "sche_nash"
        else "welfare_metrics.jsonl"
    )
    expected_window_kind = (
        "window" if run["method"] == "sche_nash" else "welfare_window"
    )
    dependency = run.get("reference_dependency")
    digest = hashlib.sha256()
    assignment_digest = hashlib.sha256()
    seen_keys: set[int] = set()
    missing_sources = 0
    welfare_run_summaries: list[dict[str, Any]] = []
    if not policy_path.is_file():
        _issue(
            issues,
            "missing_jsonl_artifact",
            "formal scheduler run is missing its policy/welfare observation stream",
            method=run["method"],
            path=str(policy_path),
        )
    else:
        try:
            for line_number, event in _iter_jsonl_objects(
                policy_path, maximum_line_bytes
            ):
                policy_observation_lines += 1
                kind = event.get("kind")
                if run["method"] != "sche_nash":
                    if kind == "welfare_run_summary":
                        if (
                            event.get("schema") != "NSE_POSTHOC_WELFARE_RUN_V1"
                            or event.get("scheduler") != run["method"]
                            or event.get("policy_commands_mutated") is not False
                        ):
                            raise RecordStreamError(
                                f"line {line_number} has an invalid post-hoc welfare run summary"
                            )
                        welfare_run_summaries.append(event)
                        continue
                    if kind != "welfare_window":
                        raise RecordStreamError(
                            f"line {line_number} has unexpected post-hoc welfare kind {kind!r}"
                        )
                    if (
                        event.get("schema") != "NSE_POSTHOC_WELFARE_WINDOW_V1"
                        or event.get("scheduler") != run["method"]
                        or event.get("policy_commands_mutated") is not False
                    ):
                        raise RecordStreamError(
                            f"line {line_number} has invalid post-hoc welfare provenance"
                        )
                elif kind != expected_window_kind:
                    continue

                policy_window_count += 1
                social = event.get("social")
                decision = event.get("decision")
                if not isinstance(social, dict) or not isinstance(decision, dict):
                    raise RecordStreamError(
                        f"line {line_number} has no social/decision object"
                    )
                initial_hash = decision.get("initial_assignment_hash")
                final_hash = decision.get("assignment_hash")
                no_player_nash_window = False
                if run["method"] == "sche_nash":
                    player_count = decision.get("request_function_players")
                    if (
                        isinstance(player_count, bool)
                        or not isinstance(player_count, int)
                        or player_count < 0
                    ):
                        raise RecordStreamError(
                            f"line {line_number} has invalid request_function_players"
                        )
                    no_player_nash_window = player_count == 0
                if no_player_nash_window:
                    # The empty assignment has fingerprint 0.  No reference is
                    # requested, so its initial reference-assignment hash is
                    # intentionally null and this window has no build/replay
                    # pair to validate.
                    if initial_hash is not None or final_hash != 0:
                        raise RecordStreamError(
                            f"line {line_number} has invalid no-player assignment hashes"
                        )
                elif any(
                    isinstance(value, bool) or not isinstance(value, int) or value < 0
                    for value in (initial_hash, final_hash)
                ):
                    raise RecordStreamError(
                        f"line {line_number} has invalid assignment hashes"
                    )
                if run["method"] != "sche_nash":
                    if not isinstance(decision.get("complete_assignment"), bool):
                        raise RecordStreamError(
                            f"line {line_number} has no complete_assignment observation"
                        )
                    welfare = social.get("final_assignment_baseline_welfare")
                    if (
                        isinstance(welfare, bool)
                        or not isinstance(welfare, (int, float))
                        or not math.isfinite(float(welfare))
                    ):
                        raise RecordStreamError(
                            f"line {line_number} has invalid evaluated welfare"
                        )

                if not isinstance(dependency, dict):
                    continue
                if no_player_nash_window:
                    continue
                state_key = social.get("reference_state_key")
                if state_key is None:
                    continue
                if (
                    isinstance(state_key, bool)
                    or not isinstance(state_key, int)
                    or state_key < 0
                ):
                    raise RecordStreamError(
                        f"line {line_number} has an invalid reference state key"
                    )
                if social.get("reference_source") == "offline_table_missing":
                    missing_sources += 1
                if state_key not in seen_keys:
                    seen_keys.add(state_key)
                    digest.update(f"{state_key}:{initial_hash}\n".encode("ascii"))
                    assignment_digest.update(
                        f"{state_key}:{initial_hash}:{final_hash}\n".encode("ascii")
                    )
        except (OSError, RecordStreamError) as exc:
            _issue(
                issues,
                "invalid_jsonl_artifact",
                f"{policy_path.name} failed policy/reference validation",
                error=str(exc),
            )

    if run["method"] != "sche_nash" and policy_path.is_file():
        if len(welfare_run_summaries) != 1:
            _issue(
                issues,
                "invalid_jsonl_artifact",
                "post-hoc welfare stream must contain exactly one run summary",
                actual=len(welfare_run_summaries),
            )
        else:
            welfare_summary = welfare_run_summaries[0]
            if welfare_summary.get("windows") != policy_window_count:
                _issue(
                    issues,
                    "summary_stream_mismatch",
                    "post-hoc welfare run-summary window count differs from its stream",
                    summary_count=welfare_summary.get("windows"),
                    stream_count=policy_window_count,
                )
            if welfare_summary.get("observation_writer_error") is not None:
                _issue(
                    issues,
                    "invalid_jsonl_artifact",
                    "post-hoc welfare writer reported an observation error",
                    error=welfare_summary.get("observation_writer_error"),
                )
        if policy_window_count != scheduler_count:
            _issue(
                issues,
                "summary_stream_mismatch",
                "post-hoc welfare windows differ from scheduler windows",
                welfare_windows=policy_window_count,
                scheduler_windows=scheduler_count,
            )

    if isinstance(dependency, dict):
        expected_digest = dependency.get("state_pair_sequence_sha256")
        expected_assignment_digest = dependency.get("assignment_sequence_sha256")
        expected_count = dependency.get("line_count")
        build_completed = dependency.get("build_completed")
        if (
            not isinstance(expected_digest, str)
            or not isinstance(expected_assignment_digest, str)
            or not isinstance(expected_count, int)
        ):
            _issue(
                issues,
                "missing_provenance",
                "formal run has no bound method-state-matched reference build receipt",
                method=run["method"],
            )
        else:
            if missing_sources:
                _issue(
                    issues,
                    "reference_pair_mismatch",
                    "offline_required replay missed reference table keys",
                    missing_windows=missing_sources,
                )
            if (
                len(seen_keys) != expected_count
                or digest.hexdigest() != expected_digest
            ):
                _issue(
                    issues,
                    "reference_pair_mismatch",
                    "build and replay (state_key, initial_assignment_hash) sequences differ",
                    expected_count=expected_count,
                    actual_count=len(seen_keys),
                    expected_sha256=expected_digest,
                    actual_sha256=digest.hexdigest(),
                )
            if assignment_digest.hexdigest() != expected_assignment_digest:
                _issue(
                    issues,
                    "reference_pair_mismatch",
                    "build and replay final assignment-hash sequences differ",
                    expected_sha256=expected_assignment_digest,
                    actual_sha256=assignment_digest.hexdigest(),
                )
            if summary and summary.get("completed") != build_completed:
                _issue(
                    issues,
                    "reference_pair_mismatch",
                    "build and replay completed counters differ",
                    build_completed=build_completed,
                    replay_completed=summary.get("completed"),
                )
        reference_pair_observation = {
            "method": run["method"],
            "policy_stream": policy_path.name,
            "policy_window_count": policy_window_count,
            "reference_unique_state_pairs": len(seen_keys),
            "reference_state_pair_sequence_sha256": digest.hexdigest(),
            "reference_assignment_sequence_sha256": assignment_digest.hexdigest(),
            "build_completed": build_completed,
            "replay_completed": summary.get("completed") if summary else None,
        }
    return {
        "jsonl_files": [
            {
                "path": name,
                "bytes": (run_directory / name).stat().st_size,
                "lines": count,
            }
            for name, count in (
                ("frames.jsonl", frame_count),
                ("requests.jsonl", request_count),
                ("scheduler_windows.jsonl", scheduler_count),
                (policy_path.name, policy_observation_lines),
            )
            if (run_directory / name).is_file()
        ],
        "environment_path": str(environment_path),
        "environment_semantic_hashes": environment_observation,
        "reference_pairing": reference_pair_observation,
    }


def _iter_legacy_frames(
    path: Path,
    *,
    chunk_chars: int = 1024 * 1024,
    max_header_chars: int = 8 * 1024 * 1024,
    max_frame_chars: int = 256 * 1024 * 1024,
) -> Iterator[list[Any]]:
    """Incrementally decode frames without loading a multi-GB record in memory."""

    decoder = json.JSONDecoder()
    header_pattern = re.compile(r'"frames"\s*:\s*\[')
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        buffer = ""
        while True:
            chunk = handle.read(chunk_chars)
            if not chunk:
                raise RecordStreamError("frames array header was not found")
            buffer += chunk
            match = header_pattern.search(buffer)
            if match:
                buffer = buffer[match.end() :]
                break
            if len(buffer) > max_header_chars:
                raise RecordStreamError(
                    "record header exceeds the configured safety limit"
                )

        eof = False
        while True:
            buffer = buffer.lstrip()
            while buffer.startswith(","):
                buffer = buffer[1:].lstrip()
            if buffer.startswith("]"):
                remainder = buffer[1:] + handle.read()
                if remainder.strip() != "}":
                    raise RecordStreamError(
                        "record lacks an exact closing ]} completion marker"
                    )
                return
            try:
                value, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError as exc:
                if eof:
                    raise RecordStreamError(
                        f"truncated or invalid frame JSON: {exc}"
                    ) from exc
                if len(buffer) > max_frame_chars:
                    raise RecordStreamError(
                        "a single frame exceeds the configured safety limit"
                    )
                chunk = handle.read(chunk_chars)
                if chunk:
                    buffer += chunk
                else:
                    eof = True
                continue
            if not isinstance(value, list):
                raise RecordStreamError("each legacy frame must be a JSON array")
            yield value
            buffer = buffer[end:]


def _validate_legacy_record(
    result_path: Path, run: dict[str, Any], qc: dict[str, Any], issues: list[QCIssue]
) -> dict[str, Any]:
    frame_count = 0
    previous_frame: int | None = None
    final_frame: list[Any] | None = None
    arrivals = 0
    completions = 0
    try:
        for frame in _iter_legacy_frames(
            result_path,
            max_frame_chars=int(qc.get("max_legacy_frame_bytes", 256 * 1024 * 1024)),
        ):
            frame_count += 1
            if not frame or isinstance(frame[0], bool) or not isinstance(frame[0], int):
                raise RecordStreamError(
                    f"frame {frame_count} has no integer frame index"
                )
            frame_index = frame[0]
            if previous_frame is not None and frame_index != previous_frame + 1:
                raise RecordStreamError(
                    f"frame sequence jumps from {previous_frame} to {frame_index}"
                )
            previous_frame = frame_index
            if len(frame) > 1 and isinstance(frame[1], list):
                arrivals += sum(
                    isinstance(request, dict) and request.get("n") is True
                    for request in frame[1]
                )
            if (
                len(frame) > 8
                and isinstance(frame[8], (int, float))
                and not isinstance(frame[8], bool)
            ):
                completions += int(frame[8])
            for index, value in enumerate(frame[3:], start=3):
                if isinstance(value, float) and not math.isfinite(value):
                    raise RecordStreamError(
                        f"frame {frame_index} scalar index {index} is not finite"
                    )
            final_frame = frame
    except (OSError, UnicodeError, RecordStreamError) as exc:
        _issue(
            issues,
            "invalid_legacy_record",
            "legacy record is incomplete or invalid",
            error=str(exc),
        )
        return {}

    expected_count = run["simulation"]["expected_frame_count"]
    expected_final = run["simulation"]["expected_final_frame"]
    if frame_count != expected_count:
        _issue(
            issues,
            "wrong_frame_count",
            "legacy frame count differs from manifest",
            expected=expected_count,
            actual=frame_count,
        )
    actual_final = final_frame[0] if final_frame else None
    if actual_final != expected_final:
        _issue(
            issues,
            "wrong_final_frame",
            "legacy final frame differs from manifest",
            expected=expected_final,
            actual=actual_final,
        )

    index_names = {
        "latency_mean_ms": 3,
        "latency_std_ms": 4,
        "latency_p90_ms": 5,
        "cost": 6,
        "score": 7,
        "wait_schedule_mean_ms": 9,
        "wait_cold_start_mean_ms": 10,
        "data_receive_mean_ms": 11,
        "execution_mean_ms": 12,
        "scheduler_mean_ms": 13,
        "container_count": 14,
    }
    metrics: dict[str, Any] = {"arrivals": arrivals, "completions": completions}
    duration = frame_count * float(run["simulation"].get("frame_duration_seconds", 1.0))
    metrics["throughput_rps"] = completions / duration if duration > 0 else float("nan")
    if final_frame is not None:
        for name, index in index_names.items():
            metrics[name] = final_frame[index] if index < len(final_frame) else None
    _validate_numeric_metrics(metrics, qc, issues)

    if qc.get("require_provenance", True):
        provenance_path = result_path.with_name("provenance.json")
        if provenance_path.exists():
            try:
                provenance = read_json(provenance_path)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                _issue(
                    issues,
                    "invalid_provenance",
                    "legacy provenance sidecar cannot be parsed",
                    error=str(exc),
                )
            else:
                _validate_provenance(provenance, run, issues)
        else:
            _issue(
                issues,
                "missing_provenance",
                "legacy record requires provenance.json sidecar",
            )
    return {"metrics": metrics, "final_frame": actual_final, "frame_count": frame_count}


def _classification(issues: list[QCIssue]) -> str:
    codes = {issue.code for issue in issues}
    if "timeout" in codes:
        return "timeout"
    if "stderr_failure_signature" in codes:
        messages = " ".join(issue.message.lower() for issue in issues)
        if "memory" in messages:
            return "oom"
        if "panic" in messages or "panicked" in messages:
            return "panic"
        return "crash_log"
    if "nonzero_exit" in codes:
        return "process_failure"
    if "missing_result" in codes:
        return "missing_result"
    if any(
        code
        in {
            "missing_jsonl_artifact",
            "partial_jsonl_artifact",
            "invalid_jsonl_artifact",
            "missing_jsonl_completion",
        }
        for code in codes
    ):
        return "invalid_jsonl_artifact"
    if any(
        code.startswith("provenance") or code == "missing_provenance" for code in codes
    ):
        return "provenance_failure"
    if "reference_pair_mismatch" in codes:
        return "reference_pair_failure"
    if any(
        code in {"nonfinite_metric", "nonfinite_value", "nonfinite_value_truncated"}
        for code in codes
    ):
        return "nonfinite_result"
    if "nonpositive_metric" in codes:
        return "invalid_zero_result"
    return "invalid_result" if issues else "qc_pass"


def _event_has_completion_marker(event: dict[str, Any]) -> bool:
    if event.get("completed") is True:
        return True
    kind = str(event.get("kind", event.get("type", event.get("event", "")))).lower()
    return kind in {
        "run_complete",
        "run_completed",
        "simulation_complete",
        "simulation_completed",
    }


def _validate_jsonl_artifacts(
    artifact_root: Path,
    run: dict[str, Any],
    qc: dict[str, Any],
    issues: list[QCIssue],
) -> dict[str, Any]:
    policy = qc.get("jsonl_artifacts", {})
    if not policy.get("required", False):
        return {}
    if not artifact_root.exists():
        _issue(
            issues,
            "missing_jsonl_artifact",
            "JSONL artifact root does not exist",
            path=str(artifact_root),
        )
        return {}
    partials = sorted(artifact_root.rglob("*.jsonl.partial"))
    if partials:
        _issue(
            issues,
            "partial_jsonl_artifact",
            "one or more JSONL writers did not perform their completion rename",
            paths=[str(path.relative_to(artifact_root)) for path in partials],
        )
    files = sorted(artifact_root.rglob("*.jsonl"))
    if not files:
        _issue(
            issues,
            "missing_jsonl_artifact",
            "attempt produced no completed .jsonl artifact",
            path=str(artifact_root),
        )
        return {}

    maximum_line_bytes = int(policy.get("max_line_bytes", 16 * 1024 * 1024))
    summaries: list[dict[str, Any]] = []
    completion_seen = False
    provenance_seen = False
    for path in files:
        line_count = 0
        try:
            with path.open("rb") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    line_count = line_number
                    if len(raw_line) > maximum_line_bytes:
                        raise RecordStreamError(
                            f"line {line_number} exceeds {maximum_line_bytes} bytes"
                        )
                    if not raw_line.strip():
                        raise RecordStreamError(f"line {line_number} is blank")
                    try:
                        event = json.loads(raw_line)
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise RecordStreamError(
                            f"line {line_number} is invalid JSON: {exc}"
                        ) from exc
                    if not isinstance(event, dict):
                        raise RecordStreamError(
                            f"line {line_number} is not a JSON object"
                        )
                    nonfinite = next(_walk_nonfinite(event), None)
                    if nonfinite is not None:
                        raise RecordStreamError(
                            f"line {line_number} contains nonfinite value at {nonfinite[0]}"
                        )
                    completion_seen = completion_seen or _event_has_completion_marker(
                        event
                    )
                    if "run_id" in event:
                        provenance_seen = True
                        if event["run_id"] != run["run_id"]:
                            raise RecordStreamError(
                                f"line {line_number} run_id does not match the manifest"
                            )
                    for key in (
                        "seed",
                        "workload_spec_hash",
                        "common_hpa_hash",
                        "run_spec_hash",
                    ):
                        if key in event and event[key] != run[key]:
                            raise RecordStreamError(
                                f"line {line_number} {key} does not match the manifest"
                            )
        except (OSError, RecordStreamError) as exc:
            _issue(
                issues,
                "invalid_jsonl_artifact",
                "completed JSONL artifact failed streaming validation",
                path=str(path.relative_to(artifact_root)),
                error=str(exc),
            )
        summaries.append(
            {
                "path": str(path.relative_to(artifact_root)),
                "bytes": path.stat().st_size if path.exists() else None,
                "lines": line_count,
            }
        )
    if policy.get("require_completed_event", True) and not completion_seen:
        _issue(
            issues,
            "missing_jsonl_completion",
            "JSONL artifacts contain no run-completion event",
        )
    if qc.get("require_provenance", True) and not provenance_seen:
        _issue(
            issues,
            "missing_provenance",
            "JSONL artifacts contain no run_id provenance field",
        )
    return {
        "jsonl_files": summaries,
        "jsonl_completion_seen": completion_seen,
        "jsonl_provenance_seen": provenance_seen,
    }


def evaluate_attempt(
    run: dict[str, Any],
    qc: dict[str, Any],
    result_path: Path,
    *,
    exit_code: int | None = 0,
    timed_out: bool = False,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    artifact_root: Path | None = None,
) -> QCReport:
    """Apply only predeclared technical checks; no comparison with business outcomes."""

    issues: list[QCIssue] = []
    observations: dict[str, Any] = {}
    nse_summary: dict[str, Any] = {}
    if timed_out:
        _issue(issues, "timeout", "attempt exceeded the frozen wall-clock timeout")
    if exit_code not in (0, None):
        _issue(
            issues,
            "nonzero_exit",
            "attempt process returned a non-zero exit code",
            exit_code=exit_code,
        )
    patterns = list(qc.get("stderr_failure_patterns", []))
    matched_patterns = _read_text_for_patterns(stderr_path, patterns)
    if matched_patterns:
        _issue(
            issues,
            "stderr_failure_signature",
            f"stderr contains technical failure signatures: {', '.join(matched_patterns)}",
            patterns=matched_patterns,
        )

    result_sha256: str | None = None
    result_bytes: int | None = None
    if not result_path.exists() or not result_path.is_file():
        _issue(
            issues,
            "missing_result",
            "attempt did not produce the declared result file",
            path=str(result_path),
        )
    else:
        result_bytes = result_path.stat().st_size
        result_sha256 = file_hash(result_path)
        if result_bytes == 0:
            _issue(issues, "empty_result", "declared result file is empty")
        elif qc.get("format") == "summary_json_v1":
            observations.update(_validate_summary_json(result_path, run, qc, issues))
        elif qc.get("format") == "serverless_record_v1":
            observations.update(_validate_legacy_record(result_path, run, qc, issues))
        elif qc.get("format") == "nse_reviewer_v1":
            nse_summary, nse_observations = _validate_nse_summary(
                result_path, run, qc, issues
            )
            observations.update(nse_observations)
        else:
            _issue(
                issues,
                "unsupported_qc_format",
                "unsupported QC result format",
                format=qc.get("format"),
            )

    if qc.get("format") == "nse_reviewer_v1" and result_path.exists():
        observations.update(
            _validate_nse_artifacts(
                result_path,
                run,
                qc,
                nse_summary,
                issues,
            )
        )
    else:
        observations.update(
            _validate_jsonl_artifacts(
                artifact_root or result_path.parent,
                run,
                qc,
                issues,
            )
        )

    classification = _classification(issues)
    return QCReport(
        passed=not issues,
        classification=classification,
        checked_at=utc_now(),
        result_path=str(result_path),
        result_sha256=result_sha256,
        result_bytes=result_bytes,
        issues=issues,
        observations=observations,
    )
