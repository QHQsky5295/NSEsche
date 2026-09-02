"""Run/seed-level analysis for reviewer experiments E3, E4, E8, and E9.

The structured frame, request, scheduler, and ``NSE_METRIC_V2`` streams are
within-run observations.  They are reduced to one statistic per independent
run/seed before confidence intervals or tests are formed.  In particular, this
module never treats frames, requests, functions, or scheduler windows as
independent experimental repetitions.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np

try:
    from .stats import (
        bca_interval,
        holm_adjust,
        paired_permutation_test,
        spearman_correlation,
    )
    from .summarize_runs import _canonical_algorithm, paired_comparisons
    from .formal_inputs import (
        assert_formal_manifest,
        validate_canonical_run,
        validate_pairing_audit,
    )
except ImportError:
    from stats import (  # type: ignore
        bca_interval,
        holm_adjust,
        paired_permutation_test,
        spearman_correlation,
    )
    from summarize_runs import _canonical_algorithm, paired_comparisons  # type: ignore
    from formal_inputs import (  # type: ignore
        assert_formal_manifest,
        validate_canonical_run,
        validate_pairing_audit,
    )


QOS_CLASSES = ("latency", "throughput", "cost")
FEATURES = ("h_ri", "h_fc", "h_nd", "h_pi", "impact")
FEATURE_OUTCOMES = (
    "queue_pressure_mean",
    "cpu_pressure_mean",
    "communication_wait_mean_ms",
    "execution_mean_ms",
    "stage_latency_p95_ms",
    "throughput_rps",
    "throughput_shortfall_vs_run_max",
)
PRIMARY_FEATURE_PAIRS = {
    ("h_ri", "queue_pressure_mean"),
    ("h_fc", "execution_mean_ms"),
    ("h_nd", "communication_wait_mean_ms"),
    ("h_pi", "throughput_shortfall_vs_run_max"),
    ("impact", "stage_latency_p95_ms"),
}
DIFFERENTIATION_FEATURE = "active_differentiation_mean"
DIFFERENTIATION_OUTCOMES = (
    "placement_dispersion_normalized",
    "co_location_conflict_pair_ratio_proxy",
    "near_tie_player_ratio",
    "differentiation_changed_top_choice_ratio",
)
EXACT_POA_NODES = 3
EXACT_POA_STATES_PER_PLAYER_COUNT = 100
EXACT_POA_PLAYER_COUNTS = (4, 6, 8)


@dataclass(frozen=True)
class RecoveryDefinition:
    """Pre-registered joint queue/latency-recovery definition for E3.

    Primary recovery is the first point after the final burst interval at which
    both queue backlog and rolling-p95 latency are no greater than 110% of their
    respective pre-burst medians, continuously for 100 ms.  Queue-only and
    rolling-p99 variants are auxiliary diagnostics and never replace the primary
    endpoint.  Runs that end first are right-censored.
    """

    baseline_window_ms: float = 100.0
    rate_window_ms: float = 20.0
    latency_window_ms: float = 100.0
    relative_tolerance: float = 0.10
    consecutive_ms: float = 100.0


@dataclass
class RunArtifacts:
    spec: Mapping[str, Any]
    run_directory: Path
    environment: Mapping[str, Any]
    frames: list[dict[str, Any]]
    requests: list[dict[str, Any]]
    scheduler_windows: list[dict[str, Any]]
    nse_events: list[dict[str, Any]]
    summary: Mapping[str, Any] = field(default_factory=dict)
    process_observation: Mapping[str, Any] = field(default_factory=dict)
    nse_event_source: str = "in_memory"

    @property
    def run_id(self) -> str:
        return str(self.spec.get("run_id", ""))

    @property
    def seed(self) -> str:
        return str(self.spec.get("seed", ""))

    @property
    def algorithm(self) -> str:
        return _canonical_algorithm(str(self.spec.get("method", "")))


def _finite(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def _percentile(values: Iterable[float], probability: float) -> float:
    sample = np.asarray(
        [value for value in (_finite(item) for item in values) if math.isfinite(value)],
        dtype=float,
    )
    if sample.size == 0:
        return math.nan
    return float(np.quantile(sample, probability, method="linear"))


def _mean(values: Iterable[float]) -> float:
    sample = [
        value for value in (_finite(item) for item in values) if math.isfinite(value)
    ]
    return float(np.mean(sample)) if sample else math.nan


def _stable_seed(*parts: Any) -> int:
    digest = hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def _nested(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, Mapping):
            return default
        value = value.get(key, default)
    return value


def _find_unique(
    root: Path, names: Sequence[str], *, required: bool = True
) -> Path | None:
    matches: list[Path] = []
    for name in names:
        matches.extend(path for path in root.rglob(name) if path.is_file())
    unique = sorted(set(matches))
    if len(unique) > 1:
        raise ValueError(
            f"ambiguous artifacts under {root}: "
            + ", ".join(str(path.relative_to(root)) for path in unique)
        )
    if not unique:
        if required:
            raise FileNotFoundError(f"none of {list(names)} exists under {root}")
        return None
    return unique[0]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_workload_tape_events(
    run: Mapping[str, Any], manifest_directory: str | Path
) -> list[dict[str, int]]:
    """Load the hash-bound replay tape used by a formal run.

    The tape, rather than ``requests.jsonl``, is the arrival population.  The
    request stream deliberately contains completed requests only and therefore
    cannot supply a completion-ratio denominator.
    """

    plan = run.get("workload_tape")
    if not isinstance(plan, Mapping):
        raise ValueError(f"run {run.get('run_id', '')} has no workload_tape plan")
    raw_path = plan.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(f"run {run.get('run_id', '')} has no workload tape path")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(manifest_directory) / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"workload tape is unavailable: {path}")
    expected_hash = plan.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("workload tape is not hash-bound in the manifest")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != expected_hash:
        raise ValueError(f"workload tape hash mismatch: {path}")
    value = _read_json(path)
    if not isinstance(value, Mapping) or value.get("version") != 1:
        raise ValueError(f"unsupported workload tape schema: {path}")
    if str(value.get("workload_seed", "")) != str(run.get("seed", "")):
        raise ValueError(f"workload tape seed mismatch: {path}")
    raw_events = value.get("events")
    if not isinstance(raw_events, list):
        raise ValueError(f"workload tape events are missing: {path}")
    events: list[dict[str, int]] = []
    previous_frame = -1
    for index, event in enumerate(raw_events):
        if not isinstance(event, Mapping):
            raise ValueError(f"workload tape event {index} is not an object")
        frame = event.get("frame")
        dag_id = event.get("dag_id")
        if (
            isinstance(frame, bool)
            or not isinstance(frame, int)
            or frame < previous_frame
            or isinstance(dag_id, bool)
            or not isinstance(dag_id, int)
            or dag_id < 0
        ):
            raise ValueError(f"workload tape event {index} is invalid")
        previous_frame = frame
        events.append({"frame": frame, "dag_id": dag_id})
    declared_count = plan.get("event_count")
    if not isinstance(declared_count, int) or declared_count != len(events):
        raise ValueError(
            f"workload tape event count mismatch: manifest={declared_count}, tape={len(events)}"
        )
    return events


def _iter_jsonl_path(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"blank JSONL record at {path}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSONL record at {path}:{line_number}")
            yield value


def _read_stream(root: Path, name: str) -> list[dict[str, Any]]:
    path = _find_unique(root, (name, f"{name}.gz"))
    assert path is not None
    return list(_iter_jsonl_path(path))


def _parse_nse_log_events(root: Path) -> list[dict[str, Any]]:
    """Read legacy metric events from logs.

    Formal runs persist the same events in a dedicated JSONL stream.  Log
    parsing is retained only for submission-era/legacy records that predate
    that stream; it must never override an available authoritative artifact.
    """

    marker = "NSE_METRIC_V2 "
    events: list[dict[str, Any]] = []
    candidates = sorted(
        {
            path
            for filename in ("stdout.log", "stderr.log")
            for path in root.rglob(filename)
            if path.is_file()
        }
    )
    decoder = json.JSONDecoder()
    for path in candidates:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                location = line.find(marker)
                if location < 0:
                    continue
                payload = line[location + len(marker) :].lstrip()
                try:
                    value, _ = decoder.raw_decode(payload)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid NSE_METRIC_V2 JSON at {path}:{line_number}: {exc}"
                    ) from exc
                if isinstance(value, dict):
                    events.append(value)
    return events


def _load_nse_events(
    root: Path, run: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], str]:
    """Load the authoritative scheduler/welfare stream, with a log fallback."""

    stream_name = (
        "nash_metrics.jsonl"
        if str(run.get("method", "")) == "sche_nash"
        else "welfare_metrics.jsonl"
    )
    stream_path = _find_unique(root, (stream_name, f"{stream_name}.gz"), required=False)
    if stream_path is not None:
        return list(_iter_jsonl_path(stream_path)), stream_path.name
    return _parse_nse_log_events(root), "NSE_METRIC_V2_log_fallback"


def load_run_artifacts(
    run: Mapping[str, Any],
    canonical_root: str | Path,
    *,
    expected_manifest_hash: str | None = None,
    result_relative_path: str = "result.json",
) -> RunArtifacts:
    """Load one QC-passed canonical run, including lossless ``.jsonl.gz`` files."""

    run_directory = Path(canonical_root) / str(run["run_id"])
    if not run_directory.is_dir():
        raise FileNotFoundError(f"canonical run directory is missing: {run_directory}")
    qc_path = _find_unique(run_directory, ("qc_report.json",), required=True)
    assert qc_path is not None
    qc = _read_json(qc_path)
    if not isinstance(qc, Mapping) or qc.get("passed") is not True:
        raise ValueError(f"canonical run does not have passing QC: {run_directory}")
    if expected_manifest_hash is not None:
        validate_canonical_run(
            run,
            run_directory,
            expected_manifest_hash=expected_manifest_hash,
            result_relative_path=result_relative_path,
        )
    environment_path = _find_unique(run_directory, ("environment.json",))
    assert environment_path is not None
    environment = _read_json(environment_path)
    if not isinstance(environment, Mapping):
        raise ValueError(f"invalid environment object: {environment_path}")
    if str(environment.get("run_id", "")) != str(run["run_id"]):
        raise ValueError(f"environment provenance mismatch: {run_directory}")
    summary_path = _find_unique(run_directory, ("summary.json",), required=False)
    summary = _read_json(summary_path) if summary_path is not None else {}
    if not isinstance(summary, Mapping):
        raise ValueError(f"invalid summary object under {run_directory}")
    process_path = _find_unique(
        run_directory, ("process_observation.json",), required=False
    )
    process_observation = _read_json(process_path) if process_path is not None else {}
    if process_observation and (
        not isinstance(process_observation, Mapping)
        or process_observation.get("schema_version") != "NSE_PROCESS_OBSERVATION_V1"
    ):
        raise ValueError(f"invalid process observation under {run_directory}")
    nse_events, nse_event_source = _load_nse_events(run_directory, run)
    return RunArtifacts(
        spec=run,
        run_directory=run_directory,
        environment=environment,
        frames=_read_stream(run_directory, "frames.jsonl"),
        requests=_read_stream(run_directory, "requests.jsonl"),
        scheduler_windows=_read_stream(run_directory, "scheduler_windows.jsonl"),
        nse_events=nse_events,
        summary=summary,
        process_observation=process_observation,
        nse_event_source=nse_event_source,
    )


def _run_context(artifacts: RunArtifacts) -> dict[str, Any]:
    workload = artifacts.spec.get("workload", {})
    cluster = artifacts.spec.get("cluster", {})
    if not isinstance(workload, Mapping):
        workload = {}
    if not isinstance(cluster, Mapping):
        cluster = {}
    return {
        "experiment_id": artifacts.spec.get("experiment_id", ""),
        "cell_id": artifacts.spec.get("cell_id", ""),
        "run_id": artifacts.run_id,
        "seed": artifacts.seed,
        "algorithm": artifacts.algorithm,
        "variant": artifacts.spec.get("variant", ""),
        "load": workload.get("request_freq", ""),
        "node_count": cluster.get("node_count", ""),
        "topology": workload.get("topology", cluster.get("topology", "")),
        "burst_pattern": workload.get(
            "burst_name",
            workload.get("burst_profile", workload.get("arrival_profile", "")),
        ),
        "qos_profile": workload.get("qos_profile", ""),
    }


def _frame_duration_ms(artifacts: RunArtifacts) -> float:
    seconds = _nested(artifacts.spec, "simulation", "frame_duration_seconds")
    value = _finite(seconds)
    if math.isfinite(value) and value > 0.0:
        return value * 1000.0
    return 1.0


def burst_intervals_ms(spec: Mapping[str, Any]) -> list[tuple[float, float]]:
    """Return frozen E3 burst intervals; interval ends are exclusive."""

    workload = spec.get("workload", {})
    if not isinstance(workload, Mapping):
        return []
    burst = workload.get("burst", {})
    if isinstance(burst, Mapping) and isinstance(burst.get("intervals_ms"), list):
        intervals = []
        for pair in burst["intervals_ms"]:
            if isinstance(pair, Sequence) and len(pair) == 2:
                start, end = map(_finite, pair)
                if math.isfinite(start) and math.isfinite(end) and end > start:
                    intervals.append((start, end))
        if intervals:
            return sorted(intervals)
    name = (
        str(workload.get("burst_name", workload.get("burst_profile", "")))
        .strip()
        .lower()
    )
    known = {
        "spike5x50ms": [(475.0, 525.0)],
        "spike_5x_50ms": [(475.0, 525.0)],
        "sustained3x200ms": [(400.0, 600.0)],
        "sustained_3x_200ms": [(400.0, 600.0)],
        "pulse4x4x50ms": [
            (200.0, 250.0),
            (400.0, 450.0),
            (600.0, 650.0),
            (800.0, 850.0),
        ],
        "pulse_4x_4_50ms": [
            (200.0, 250.0),
            (400.0, 450.0),
            (600.0, 650.0),
            (800.0, 850.0),
        ],
    }
    return known.get(name, [])


def _rolling_rates(
    times_ms: np.ndarray,
    cumulative: np.ndarray,
    window_ms: float,
) -> np.ndarray:
    output = np.full(times_ms.size, np.nan, dtype=float)
    for index, time_ms in enumerate(times_ms):
        left = int(np.searchsorted(times_ms, time_ms - window_ms, side="left"))
        if left >= index:
            output[index] = 0.0
            continue
        elapsed_seconds = (time_ms - times_ms[left]) / 1000.0
        if elapsed_seconds > 0.0:
            output[index] = (cumulative[index] - cumulative[left]) / elapsed_seconds
    return output


def _rolling_latency_percentile(
    times_ms: np.ndarray,
    requests: Sequence[Mapping[str, Any]],
    frame_duration_ms: float,
    window_ms: float,
    probability: float,
) -> np.ndarray:
    completions = sorted(
        (
            _finite(request.get("completion_frame")) * frame_duration_ms,
            _finite(request.get("latency_ms")),
        )
        for request in requests
        if math.isfinite(_finite(request.get("completion_frame")))
        and math.isfinite(_finite(request.get("latency_ms")))
    )
    active: deque[tuple[float, float]] = deque()
    output = np.full(times_ms.size, np.nan, dtype=float)
    cursor = 0
    for index, time_ms in enumerate(times_ms):
        while cursor < len(completions) and completions[cursor][0] <= time_ms:
            active.append(completions[cursor])
            cursor += 1
        while active and active[0][0] <= time_ms - window_ms:
            active.popleft()
        if active:
            output[index] = _percentile((value for _, value in active), probability)
    return output


def _first_sustained(
    times_ms: np.ndarray,
    eligible: np.ndarray,
    start_ms: float,
    consecutive_ms: float,
) -> float:
    start_index = int(np.searchsorted(times_ms, start_ms, side="left"))
    run_start: int | None = None
    for index in range(start_index, len(times_ms)):
        if bool(eligible[index]):
            if run_start is None:
                run_start = index
            if times_ms[index] - times_ms[run_start] >= consecutive_ms:
                return float(times_ms[run_start])
        else:
            run_start = None
    return math.nan


def analyze_burst_run(
    artifacts: RunArtifacts,
    *,
    definition: RecoveryDefinition = RecoveryDefinition(),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Construct E3 time series and one censored-aware metric row for a run."""

    intervals = burst_intervals_ms(artifacts.spec)
    if not intervals:
        raise ValueError(f"run {artifacts.run_id} has no recognized burst intervals")
    frame_duration_ms = _frame_duration_ms(artifacts)
    frames = sorted(artifacts.frames, key=lambda row: int(row.get("frame", -1)))
    times = np.asarray(
        [_finite(row.get("frame")) * frame_duration_ms for row in frames], dtype=float
    )
    if times.size == 0 or np.any(~np.isfinite(times)):
        raise ValueError(f"run {artifacts.run_id} has invalid frame times")
    arrivals = np.asarray([_finite(row.get("arrivals_total")) for row in frames])
    completed = np.asarray([_finite(row.get("completed_total")) for row in frames])
    queue = np.asarray([_finite(row.get("queue_total")) for row in frames])
    arrival_rps = _rolling_rates(times, arrivals, definition.rate_window_ms)
    throughput_rps = _rolling_rates(times, completed, definition.rate_window_ms)
    rolling_p95 = _rolling_latency_percentile(
        times,
        artifacts.requests,
        frame_duration_ms,
        definition.latency_window_ms,
        0.95,
    )
    rolling_p99 = _rolling_latency_percentile(
        times,
        artifacts.requests,
        frame_duration_ms,
        definition.latency_window_ms,
        0.99,
    )
    burst_start = intervals[0][0]
    burst_end = intervals[-1][1]
    active = np.asarray(
        [any(start <= time < end for start, end in intervals) for time in times],
        dtype=bool,
    )
    baseline_mask = (times >= burst_start - definition.baseline_window_ms) & (
        times < burst_start
    )
    baseline_queue = _percentile(queue[baseline_mask], 0.50)
    baseline_p95 = _percentile(rolling_p95[baseline_mask], 0.50)
    baseline_p99 = _percentile(rolling_p99[baseline_mask], 0.50)
    queue_threshold = baseline_queue * (1.0 + definition.relative_tolerance)
    queue_eligible = np.isfinite(queue) & (queue <= queue_threshold)
    queue_recovery_at = _first_sustained(
        times,
        queue_eligible,
        burst_end,
        definition.consecutive_ms,
    )
    if math.isfinite(baseline_p95):
        latency_threshold_p95 = baseline_p95 * (1.0 + definition.relative_tolerance)
        primary_eligible = (
            queue_eligible
            & np.isfinite(rolling_p95)
            & (rolling_p95 <= latency_threshold_p95)
        )
        recovery_at = _first_sustained(
            times,
            primary_eligible,
            burst_end,
            definition.consecutive_ms,
        )
        recovery_status = (
            "recovered" if math.isfinite(recovery_at) else "right_censored"
        )
    else:
        latency_threshold_p95 = math.nan
        recovery_at = math.nan
        recovery_status = "unavailable_no_preburst_p95_samples"

    if math.isfinite(baseline_p99):
        latency_threshold_p99 = baseline_p99 * (1.0 + definition.relative_tolerance)
        p99_recovery_at = _first_sustained(
            times,
            queue_eligible
            & np.isfinite(rolling_p99)
            & (rolling_p99 <= latency_threshold_p99),
            burst_end,
            definition.consecutive_ms,
        )
        p99_recovery_status = (
            "recovered" if math.isfinite(p99_recovery_at) else "right_censored"
        )
    else:
        latency_threshold_p99 = math.nan
        p99_recovery_at = math.nan
        p99_recovery_status = "unavailable_no_preburst_p99_samples"

    analysis_end = recovery_at if math.isfinite(recovery_at) else times[-1]
    response_mask = (times >= burst_start) & (times <= analysis_end)
    burst_latencies = [
        _finite(request.get("latency_ms"))
        for request in artifacts.requests
        if any(
            start <= _finite(request.get("arrival_frame")) * frame_duration_ms < end
            for start, end in intervals
        )
    ]
    all_latencies = [
        _finite(request.get("latency_ms")) for request in artifacts.requests
    ]
    context = _run_context(artifacts)
    series: list[dict[str, Any]] = []
    for index, time_ms in enumerate(times):
        series.append(
            {
                **context,
                "time_ms": float(time_ms),
                "time_relative_ms": float(time_ms - burst_start),
                "burst_active": bool(active[index]),
                "arrival_rps": float(arrival_rps[index]),
                "queue_total": float(queue[index]),
                "throughput_rps": float(throughput_rps[index]),
                "rolling_p95_ms": float(rolling_p95[index]),
                "rolling_p99_ms": float(rolling_p99[index]),
            }
        )
    observation_after_burst = max(0.0, float(times[-1] - burst_end))
    metrics = {
        **context,
        "burst_start_ms": burst_start,
        "burst_end_ms": burst_end,
        "burst_interval_count": len(intervals),
        "baseline_queue_median": baseline_queue,
        "queue_recovery_threshold": queue_threshold,
        "recovery_time_ms": (
            recovery_at - burst_end if math.isfinite(recovery_at) else math.nan
        ),
        "recovery_status": recovery_status,
        "recovery_observed": (
            float(math.isfinite(recovery_at))
            if recovery_status != "unavailable_no_preburst_p95_samples"
            else math.nan
        ),
        "recovery_censor_time_ms": observation_after_burst,
        "restricted_recovery_time_ms": (
            recovery_at - burst_end
            if math.isfinite(recovery_at)
            else (
                observation_after_burst
                if recovery_status == "right_censored"
                else math.nan
            )
        ),
        "recovery_endpoint": "queue_and_rolling_p95_within_110pct_for_100ms",
        "baseline_rolling_p95_ms": baseline_p95,
        "recovery_threshold_p95_ms": latency_threshold_p95,
        "queue_only_recovery_time_ms": (
            queue_recovery_at - burst_end
            if math.isfinite(queue_recovery_at)
            else math.nan
        ),
        "queue_only_recovery_status": (
            "recovered" if math.isfinite(queue_recovery_at) else "right_censored"
        ),
        "queue_only_recovery_observed": float(math.isfinite(queue_recovery_at)),
        "baseline_rolling_p99_ms": baseline_p99,
        "p99_recovery_threshold_ms": latency_threshold_p99,
        "p99_recovery_time_ms": (
            p99_recovery_at - burst_end if math.isfinite(p99_recovery_at) else math.nan
        ),
        "p99_recovery_status": p99_recovery_status,
        "p99_recovery_observed": (
            float(math.isfinite(p99_recovery_at))
            if p99_recovery_status != "unavailable_no_preburst_p99_samples"
            else math.nan
        ),
        # Compatibility aliases: "joint" now means the frozen queue+p95
        # endpoint.  The explicit endpoint field prevents a legacy p99 reading.
        "joint_recovery_threshold_p95_ms": latency_threshold_p95,
        "joint_recovery_time_ms": (
            recovery_at - burst_end if math.isfinite(recovery_at) else math.nan
        ),
        "joint_recovery_status": recovery_status,
        "joint_recovery_observed": (
            float(math.isfinite(recovery_at))
            if recovery_status != "unavailable_no_preburst_p95_samples"
            else math.nan
        ),
        "peak_queue": _percentile(queue[response_mask], 1.0),
        "admission_drop": _finite(artifacts.summary.get("admission_drop")),
        "admission_reject": _finite(artifacts.summary.get("admission_reject")),
        "timeout": _finite(artifacts.summary.get("timeout")),
        "latency_p95_ms": _percentile(all_latencies, 0.95),
        "latency_p99_ms": _percentile(all_latencies, 0.99),
        "burst_arrival_latency_p95_ms": _percentile(burst_latencies, 0.95),
        "burst_arrival_latency_p99_ms": _percentile(burst_latencies, 0.99),
        "request_latency_samples": sum(math.isfinite(value) for value in all_latencies),
        "burst_request_latency_samples": sum(
            math.isfinite(value) for value in burst_latencies
        ),
    }
    return series, metrics


def _function_environment(artifacts: RunArtifacts) -> dict[int, Mapping[str, Any]]:
    functions = artifacts.environment.get("functions", [])
    output: dict[int, Mapping[str, Any]] = {}
    if isinstance(functions, list):
        for function in functions:
            if not isinstance(function, Mapping):
                continue
            identifier = function.get("function_id")
            if isinstance(identifier, int) and not isinstance(identifier, bool):
                output[identifier] = function
    return output


def _canonical_qos_class(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", "_")
    aliases = {
        "latency_sensitive": "latency",
        "throughput_sensitive": "throughput",
        "cost_sensitive": "cost",
    }
    return aliases.get(normalized, normalized)


def _recorder_qos_counts(
    artifacts: RunArtifacts,
) -> dict[str, dict[str, float]] | None:
    """Read the cumulative arrived/completed function counters at final frame."""

    if not artifacts.frames:
        return None
    final_frame = max(
        artifacts.frames,
        key=lambda row: _finite(row.get("frame")),
    )
    raw = final_frame.get("qos_function_tasks")
    if not isinstance(raw, Mapping):
        return None
    output: dict[str, dict[str, float]] = {}
    for raw_class, value in raw.items():
        qos_class = _canonical_qos_class(raw_class)
        if qos_class not in QOS_CLASSES or not isinstance(value, Mapping):
            continue
        arrived = value.get("arrived")
        completed = value.get("completed")
        active = value.get("active")
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in (arrived, completed, active)
        ):
            raise ValueError(f"invalid qos_function_tasks counters for {raw_class}")
        if completed > arrived or active != arrived - completed:
            raise ValueError(
                f"inconsistent qos_function_tasks counters for {raw_class}"
            )
        ratio = _finite(value.get("completion_ratio"))
        expected_ratio = completed / arrived if arrived else math.nan
        if arrived and (
            not math.isfinite(ratio)
            or not math.isclose(ratio, expected_ratio, rel_tol=1e-12, abs_tol=1e-12)
        ):
            raise ValueError(
                f"invalid qos_function_tasks completion ratio for {raw_class}"
            )
        if qos_class in output:
            raise ValueError(f"duplicate normalized QoS counter class {qos_class}")
        output[qos_class] = {
            "arrived": float(arrived),
            "completed": float(completed),
            "active": float(active),
            "completion_ratio": expected_ratio,
        }
    return output if output else None


def _summary_qos_cost(artifacts: RunArtifacts, qos_class: str) -> float:
    raw = artifacts.summary.get("qos_simulator_internal_cost")
    if not isinstance(raw, Mapping):
        return math.nan
    for raw_class, value in raw.items():
        if _canonical_qos_class(raw_class) != qos_class or not isinstance(
            value, Mapping
        ):
            continue
        if (
            value.get("unit") != "simulator_internal_units"
            or value.get("is_currency") is not False
        ):
            return math.nan
        return _finite(value.get("per_completed_function"))
    return math.nan


def _function_profiles(artifacts: RunArtifacts) -> dict[int, Mapping[str, Any]]:
    output: dict[int, Mapping[str, Any]] = {}
    for event in artifacts.nse_events:
        if event.get("kind") != "function_profile":
            continue
        identifier = event.get("fn_id")
        if isinstance(identifier, int) and not isinstance(identifier, bool):
            output[identifier] = event
    return output


def _duration(event: Mapping[str, Any], end: str, start: str) -> float:
    end_value = _finite(event.get(end))
    start_value = _finite(event.get(start))
    if not math.isfinite(end_value) or not math.isfinite(start_value):
        return math.nan
    return max(0.0, end_value - start_value)


def _invocation_rows(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    environment = _function_environment(artifacts)
    profiles = _function_profiles(artifacts)
    frame_by_id = {
        int(frame["frame"]): frame
        for frame in artifacts.frames
        if isinstance(frame.get("frame"), int)
    }
    rows: list[dict[str, Any]] = []
    context = _run_context(artifacts)
    for request in artifacts.requests:
        functions = request.get("functions", [])
        if not isinstance(functions, list):
            continue
        for event in functions:
            if not isinstance(event, Mapping):
                continue
            function_id = event.get("function_id")
            if not isinstance(function_id, int) or isinstance(function_id, bool):
                continue
            config = environment.get(function_id, {})
            profile = profiles.get(function_id, {})
            qos_class = _canonical_qos_class(
                event.get("qos_class", config.get("qos_class", "shared"))
            )
            schedule_frame = event.get("scheduled_frame")
            pressure = (
                frame_by_id.get(schedule_frame, {})
                if isinstance(schedule_frame, int)
                else {}
            )
            stage_latency = _duration(
                event, "function_done_frame", "ready_schedule_frame"
            )
            execution = _duration(event, "function_done_frame", "cold_start_done_frame")
            communication = _duration(event, "data_received_frame", "scheduled_frame")
            direct_cost = _finite(
                event.get(
                    "cost_internal_units", event.get("simulator_cost_internal_units")
                )
            )
            cpu_work = _finite(config.get("cpu_work"))
            memory = _finite(config.get("memory"))
            resource_proxy = math.nan
            if all(
                math.isfinite(value)
                for value in (cpu_work, memory, execution, stage_latency)
            ):
                resource_proxy = (
                    cpu_work * execution + (memory / 1024.0) * stage_latency
                )
            heterogeneity = profile.get("heterogeneity", {})
            if not isinstance(heterogeneity, Mapping):
                heterogeneity = {}
            rows.append(
                {
                    **context,
                    "request_id": request.get("request_id", ""),
                    "function_id": function_id,
                    "qos_class": qos_class,
                    "quality_weight": _finite(
                        event.get("quality_weight", config.get("quality_weight"))
                    ),
                    "stage_latency_ms": stage_latency,
                    "schedule_wait_ms": _duration(
                        event, "scheduled_frame", "ready_schedule_frame"
                    ),
                    "communication_wait_ms": communication,
                    "cold_start_wait_ms": _duration(
                        event, "cold_start_done_frame", "data_received_frame"
                    ),
                    "execution_ms": execution,
                    "direct_cost_internal_units": direct_cost,
                    "resource_cost_proxy": resource_proxy,
                    "queue_pressure": _finite(pressure.get("queue_total")),
                    "cpu_pressure": _finite(pressure.get("node_cpu_mean")),
                    "output_mb": _finite(config.get("output_mb")),
                    "h_ri": _finite(heterogeneity.get("h_ri")),
                    "h_fc": _finite(heterogeneity.get("h_fc")),
                    "h_nd": _finite(heterogeneity.get("h_nd")),
                    "h_pi": _finite(heterogeneity.get("h_pi")),
                    "impact": _finite(heterogeneity.get("impact")),
                }
            )
    return rows


def _normalize_target(
    qos_class: str, targets: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    if targets is None or qos_class not in targets:
        return None
    value = targets[qos_class]
    defaults = {
        "latency": ("stage_latency_p95_ms", "lower"),
        "throughput": ("throughput_rps", "higher"),
        "cost": ("direct_cost_mean", "lower"),
    }
    metric, direction = defaults[qos_class]
    if isinstance(value, Mapping):
        target = _finite(value.get("target"))
        metric = str(value.get("metric", metric))
        direction = str(value.get("direction", direction)).lower()
    else:
        target = _finite(value)
    if not math.isfinite(target) or target <= 0.0:
        raise ValueError(f"SLA target for {qos_class} must be finite and positive")
    if direction not in {"lower", "higher"}:
        raise ValueError(f"SLA direction for {qos_class} must be lower or higher")
    return {"target": target, "metric": metric, "direction": direction}


def _sla_targets_for_run(
    run: Mapping[str, Any], supplied: Mapping[str, Any] | None
) -> Mapping[str, Any] | None:
    """Prefer SLA thresholds frozen into the semantic run specification."""

    qos = _nested(run, "simulator_experiment", "qos", default={})
    if not isinstance(qos, Mapping):
        return supplied
    frozen_values = {
        "latency": qos.get("latency_deadline_ms"),
        "throughput": qos.get("throughput_target_rps"),
        "cost": qos.get("cost_budget_per_request"),
    }
    if not all(
        math.isfinite(_finite(value)) and _finite(value) > 0.0
        for value in frozen_values.values()
    ):
        return supplied
    frozen: dict[str, Any] = {
        "latency": {
            "metric": "stage_latency_p95_ms",
            "direction": "lower",
            "target": _finite(frozen_values["latency"]),
        },
        "throughput": {
            "metric": "throughput_rps",
            "direction": "higher",
            "target": _finite(frozen_values["throughput"]),
        },
        "cost": {
            "metric": "direct_cost_mean",
            "direction": "lower",
            "target": _finite(frozen_values["cost"]),
        },
    }
    if supplied is not None:
        for qos_class in QOS_CLASSES:
            supplied_target = _normalize_target(qos_class, supplied)
            frozen_target = _normalize_target(qos_class, frozen)
            if supplied_target != frozen_target:
                raise ValueError(
                    f"supplied SLA target for {qos_class} differs from the run manifest"
                )
    return frozen


def _normalized_satisfaction(value: float, target: float, direction: str) -> float:
    if not math.isfinite(value) or value < 0.0 or target <= 0.0:
        return math.nan
    if direction == "lower":
        if value <= 0.0:
            return 1.0
        return min(1.0, target / value)
    return min(1.0, value / target)


def _jain(values: Sequence[float]) -> float:
    sample = np.asarray(
        [value for value in values if math.isfinite(value)], dtype=float
    )
    if sample.size == 0:
        return math.nan
    denominator = float(sample.size * np.sum(sample**2))
    if denominator == 0.0:
        return 1.0
    return float(np.sum(sample) ** 2 / denominator)


def analyze_qos_run(
    artifacts: RunArtifacts,
    *,
    sla_targets: Mapping[str, Any] | None,
    workload_events: Sequence[Mapping[str, Any]] | None = None,
    require_arrival_coverage: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Return class performance, class fairness, and a function sample audit.

    ``requests.jsonl`` contains completed requests only.  It is used for latency
    samples, never for arrived/completed counts.  Formal completion ratios and
    throughput numerators come from the final frame's cumulative
    ``qos_function_tasks`` counters and are cross-checked against the immutable
    workload tape mapped through environment DAG/function metadata.  Missing old
    counters are an analysis blocker, not an implicit 100% completion rate.
    """

    invocations = _invocation_rows(artifacts)
    context = _run_context(artifacts)
    environment_functions = _function_environment(artifacts)
    observation_seconds = max(
        1e-12,
        max((_finite(frame.get("frame")) for frame in artifacts.frames), default=0.0)
        * _frame_duration_ms(artifacts)
        / 1000.0,
    )

    by_function: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in invocations:
        if row["qos_class"] in QOS_CLASSES:
            by_function[int(row["function_id"])].append(row)

    expected_by_function: dict[int, int] = defaultdict(int)
    tape_status = "coverage_unavailable_no_tape"
    if workload_events is not None:
        functions_by_dag: dict[int, list[int]] = defaultdict(list)
        for function_id, function in environment_functions.items():
            dag_id = function.get("dag_id")
            if isinstance(dag_id, int) and not isinstance(dag_id, bool):
                functions_by_dag[dag_id].append(function_id)
        missing_dags: set[int] = set()
        for event in workload_events:
            dag_id = event.get("dag_id")
            if not isinstance(dag_id, int) or isinstance(dag_id, bool):
                missing_dags.add(-1)
                continue
            function_ids = functions_by_dag.get(dag_id)
            if not function_ids:
                missing_dags.add(dag_id)
                continue
            for function_id in function_ids:
                expected_by_function[function_id] += 1
        tape_status = (
            "coverage_unavailable_missing_dag_mapping:"
            + ",".join(map(str, sorted(missing_dags)))
            if missing_dags
            else "ok_tape_dag_to_function_class"
        )

    recorder_counts = _recorder_qos_counts(artifacts)
    if recorder_counts is None:
        arrival_coverage_status = "coverage_unavailable_missing_qos_function_tasks"
    elif tape_status != "ok_tape_dag_to_function_class":
        arrival_coverage_status = tape_status
    else:
        expected_by_class = {
            qos_class: sum(
                expected_by_function.get(function_id, 0)
                for function_id, function in environment_functions.items()
                if _canonical_qos_class(function.get("qos_class", "")) == qos_class
            )
            for qos_class in QOS_CLASSES
        }
        mismatch = [
            qos_class
            for qos_class in QOS_CLASSES
            if int(recorder_counts.get(qos_class, {}).get("arrived", 0))
            != expected_by_class[qos_class]
        ]
        arrival_coverage_status = (
            "coverage_unavailable_tape_recorder_mismatch:" + ",".join(mismatch)
            if mismatch
            else "ok_recorder_crosschecked_by_tape"
        )
    if (
        require_arrival_coverage
        and arrival_coverage_status != "ok_recorder_crosschecked_by_tape"
    ):
        raise ValueError(
            f"QoS arrival coverage is required but unavailable: {arrival_coverage_status}"
        )

    # Function rows are the normalized satisfaction audit used for fairness.
    # The request stream is still a completed-invocation sample, but the tape
    # supplies the denominator when recorder counters have been cross-checked.
    # A missing denominator or missing target remains NA; no completion is
    # inferred from the number of rows in requests.jsonl.
    function_rows: list[dict[str, Any]] = []
    function_satisfactions: list[float] = []
    all_function_ids = sorted(
        set(environment_functions) | set(by_function) | set(expected_by_function)
    )
    for function_id in all_function_ids:
        rows = by_function.get(function_id, [])
        config = environment_functions.get(function_id, {})
        qos_class = (
            str(rows[0]["qos_class"])
            if rows
            else _canonical_qos_class(config.get("qos_class", ""))
        )
        expected = _finite(expected_by_function.get(function_id, math.nan))
        completed_samples = len(rows)
        if (
            arrival_coverage_status == "ok_recorder_crosschecked_by_tape"
            and math.isfinite(expected)
        ):
            completion_ratio = (
                completed_samples / expected
                if expected > 0.0
                else (1.0 if completed_samples == 0 else math.nan)
            )
            completion_status = "ok_function_tape_crosscheck"
        else:
            completion_ratio = math.nan
            completion_status = "coverage_unavailable_function_denominator"

        metrics = {
            "stage_latency_mean_ms": _mean(row["stage_latency_ms"] for row in rows),
            "stage_latency_p95_ms": _percentile(
                (row["stage_latency_ms"] for row in rows), 0.95
            ),
            "stage_latency_p99_ms": _percentile(
                (row["stage_latency_ms"] for row in rows), 0.99
            ),
            "throughput_rps": completed_samples / observation_seconds,
            "direct_cost_mean": _mean(
                row["direct_cost_internal_units"] for row in rows
            ),
            "resource_cost_proxy_mean": _mean(
                row["resource_cost_proxy"] for row in rows
            ),
            "schedule_wait_mean_ms": _mean(row["schedule_wait_ms"] for row in rows),
            "schedule_wait_p95_ms": _percentile(
                (row["schedule_wait_ms"] for row in rows), 0.95
            ),
            "data_wait_mean_ms": _mean(row["communication_wait_ms"] for row in rows),
            "data_wait_p95_ms": _percentile(
                (row["communication_wait_ms"] for row in rows), 0.95
            ),
            "cold_start_wait_mean_ms": _mean(row["cold_start_wait_ms"] for row in rows),
            "cold_start_wait_p95_ms": _percentile(
                (row["cold_start_wait_ms"] for row in rows), 0.95
            ),
        }
        target = (
            _normalize_target(qos_class, sla_targets)
            if qos_class in QOS_CLASSES
            else None
        )
        if target is None:
            target_metric = ""
            target_direction = ""
            target_value = math.nan
            observed = math.nan
            satisfaction = math.nan
            violation = math.nan
            violation_numerator = math.nan
            violation_denominator = math.nan
            violation_unit = "target_missing_or_unknown_qos"
            sla_status = "target_missing_or_unknown_qos"
        else:
            target_metric = str(target["metric"])
            target_direction = str(target["direction"])
            target_value = float(target["target"])
            observed = _finite(metrics.get(target_metric))
            satisfaction = _normalized_satisfaction(
                observed, target_value, target_direction
            )
            if qos_class == "latency":
                latency_values = [
                    _finite(row["stage_latency_ms"])
                    for row in rows
                    if math.isfinite(_finite(row["stage_latency_ms"]))
                ]
                violation_denominator = float(len(latency_values))
                violation_numerator = float(
                    sum(value > target_value for value in latency_values)
                )
                violation = (
                    violation_numerator / violation_denominator
                    if violation_denominator > 0.0
                    else math.nan
                )
                violation_unit = "completed_function_invocation"
            elif math.isfinite(satisfaction):
                violation = float(satisfaction < 1.0 - 1e-12)
                violation_numerator = violation
                violation_denominator = 1.0
                violation_unit = "function_run"
            else:
                violation = math.nan
                violation_numerator = math.nan
                violation_denominator = math.nan
                violation_unit = "function_run"
            sla_status = "ok" if math.isfinite(satisfaction) else "metric_unavailable"
            if completion_status == "ok_function_tape_crosscheck" and math.isfinite(
                satisfaction
            ):
                function_satisfactions.append(satisfaction)

        function_rows.append(
            {
                **context,
                "function_id": function_id,
                "qos_class": qos_class,
                "completed_request_log_samples": completed_samples,
                "completed_function_invocation_samples": completed_samples,
                "expected_invocation_arrivals": expected,
                "completion_ratio": completion_ratio,
                "completion_coverage_status": completion_status,
                "sample_throughput_rps_not_for_completion_inference": (
                    completed_samples / observation_seconds
                ),
                **metrics,
                "sla_metric": target_metric,
                "sla_direction": target_direction,
                "sla_target": target_value,
                "sla_observed": observed,
                "sla_violation_rate": violation,
                "sla_violation_numerator": violation_numerator,
                "sla_violation_denominator": violation_denominator,
                "satisfaction": satisfaction,
                "normalized_satisfaction": satisfaction,
                "satisfaction_mean": satisfaction,
                "sla_evaluation_unit": violation_unit,
                "sla_status": sla_status,
            }
        )

    class_rows: list[dict[str, Any]] = []
    class_satisfactions: list[float] = []
    for qos_class in QOS_CLASSES:
        selected = [row for row in invocations if row["qos_class"] == qos_class]
        counter = recorder_counts.get(qos_class, {}) if recorder_counts else {}
        arrived = _finite(counter.get("arrived"))
        completed = _finite(counter.get("completed"))
        completion_ratio = _finite(counter.get("completion_ratio"))
        direct_cost_mean = _summary_qos_cost(artifacts, qos_class)
        metrics = {
            "stage_latency_mean_ms": _mean(row["stage_latency_ms"] for row in selected),
            "stage_latency_p95_ms": _percentile(
                (row["stage_latency_ms"] for row in selected), 0.95
            ),
            "stage_latency_p99_ms": _percentile(
                (row["stage_latency_ms"] for row in selected), 0.99
            ),
            "throughput_rps": (
                completed / observation_seconds
                if math.isfinite(completed)
                else math.nan
            ),
            "offered_invocation_rps": (
                arrived / observation_seconds if math.isfinite(arrived) else math.nan
            ),
            "direct_cost_mean": direct_cost_mean,
            "resource_cost_proxy_mean": _mean(
                row["resource_cost_proxy"] for row in selected
            ),
        }
        target = _normalize_target(qos_class, sla_targets)
        if target is None:
            target_metric = ""
            target_direction = ""
            target_value = math.nan
            observed = math.nan
            satisfaction = math.nan
            violation = math.nan
            violation_numerator = math.nan
            violation_denominator = math.nan
            violation_unit = "target_missing"
            sla_status = "target_missing"
        else:
            target_metric = str(target["metric"])
            target_direction = str(target["direction"])
            target_value = float(target["target"])
            observed = _finite(metrics.get(target_metric))
            satisfaction = _normalized_satisfaction(
                observed, target_value, target_direction
            )
            violation = (
                float(satisfaction < 1.0 - 1e-12)
                if math.isfinite(satisfaction)
                else math.nan
            )
            violation_numerator = violation
            violation_denominator = 1.0 if math.isfinite(violation) else math.nan
            violation_unit = "qos_class_run"
            if qos_class == "latency":
                invocation_latencies = [
                    _finite(row["stage_latency_ms"])
                    for row in selected
                    if math.isfinite(_finite(row["stage_latency_ms"]))
                ]
                violation_denominator = float(len(invocation_latencies))
                violation_numerator = float(
                    sum(value > target_value for value in invocation_latencies)
                )
                violation = (
                    violation_numerator / violation_denominator
                    if violation_denominator > 0.0
                    else math.nan
                )
                violation_unit = "completed_function_invocation"
            sla_status = "ok" if math.isfinite(satisfaction) else "metric_unavailable"
            if math.isfinite(satisfaction):
                class_satisfactions.append(satisfaction)
        latency_sample_coverage = (
            len(selected) / completed
            if math.isfinite(completed) and completed > 0.0
            else math.nan
        )
        class_rows.append(
            {
                **context,
                "qos_class": qos_class,
                "arrived_function_invocations": arrived,
                "completed_function_invocations": completed,
                "active_function_invocations": _finite(counter.get("active")),
                "completion_ratio": completion_ratio,
                "arrival_coverage_status": arrival_coverage_status,
                "completion_ratio_numerator": "recorder_completed_function_invocations",
                "completion_ratio_denominator": "recorder_arrived_function_invocations_crosschecked_by_tape",
                "latency_sample_count": len(selected),
                "latency_sample_coverage": latency_sample_coverage,
                "latency_sample_coverage_status": (
                    "complete"
                    if math.isfinite(latency_sample_coverage)
                    and math.isclose(latency_sample_coverage, 1.0)
                    else "partial_completed_requests_only"
                ),
                **metrics,
                "throughput_numerator": "recorder_completed_function_invocations",
                "throughput_denominator": "observed_simulation_seconds",
                "cost_unit": "simulator_internal_units_not_currency",
                "sla_metric": target_metric,
                "sla_direction": target_direction,
                "sla_target": target_value,
                "sla_observed": observed,
                "sla_violation_rate": violation,
                "sla_violation_numerator": violation_numerator,
                "sla_violation_denominator": violation_denominator,
                "satisfaction_mean": satisfaction,
                "sla_evaluation_unit": violation_unit,
                "sla_status": sla_status,
            }
        )

    finite_function_satisfaction = [
        value for value in function_satisfactions if math.isfinite(value)
    ]
    fairness_function_rows = [
        row
        for row in function_rows
        if row.get("completion_coverage_status") == "ok_function_tape_crosscheck"
        and math.isfinite(_finite(row.get("satisfaction")))
        and _finite(row.get("expected_invocation_arrivals")) > 0.0
    ]
    fairness_complete = bool(fairness_function_rows) and len(
        fairness_function_rows
    ) == sum(
        1
        for row in function_rows
        if row.get("completion_coverage_status") == "ok_function_tape_crosscheck"
        and _finite(row.get("expected_invocation_arrivals")) > 0.0
    )
    if not fairness_complete:
        finite_function_satisfaction = []
    worst_count = (
        max(1, math.ceil(0.10 * len(finite_function_satisfaction)))
        if finite_function_satisfaction
        else 0
    )
    fairness = {
        **context,
        "fairness_unit": "function",
        "satisfaction_definition": "directional_target_ratio_clipped_0_1",
        "satisfaction_source": "e4_function_sla_audit_normalized_satisfaction",
        "satisfaction_class_count": len(class_satisfactions),
        "satisfaction_function_count": len(finite_function_satisfaction),
        "jain_satisfaction": _jain(finite_function_satisfaction),
        "worst10_satisfaction": (
            _mean(sorted(finite_function_satisfaction)[:worst_count])
            if finite_function_satisfaction
            else math.nan
        ),
        "worst10_class_count": math.nan,
        "worst10_function_count": worst_count,
        "fairness_status": (
            "ok_function_level"
            if fairness_complete
            else "unavailable_function_satisfaction"
        ),
        "sla_target_status": (
            "complete"
            if fairness_complete
            else "incomplete_function_level_targets_or_coverage"
        ),
        "arrival_coverage_status": arrival_coverage_status,
    }
    return class_rows, fairness, function_rows


def function_runtime_rows(artifacts: RunArtifacts) -> list[dict[str, Any]]:
    """Reduce request-level function events to one descriptive row per function."""

    invocations = _invocation_rows(artifacts)
    context = _run_context(artifacts)
    observation_seconds = max(
        1e-12,
        max((_finite(frame.get("frame")) for frame in artifacts.frames), default=0.0)
        * _frame_duration_ms(artifacts)
        / 1000.0,
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in invocations:
        grouped[int(row["function_id"])].append(row)
    output: list[dict[str, Any]] = []
    for function_id, rows in sorted(grouped.items()):
        throughput = len(rows) / observation_seconds
        output.append(
            {
                **context,
                "function_id": function_id,
                "qos_class": rows[0]["qos_class"],
                "invocations": len(rows),
                **{feature: _finite(rows[0].get(feature)) for feature in FEATURES},
                "queue_pressure_mean": _mean(row["queue_pressure"] for row in rows),
                "cpu_pressure_mean": _mean(row["cpu_pressure"] for row in rows),
                "schedule_wait_mean_ms": _mean(row["schedule_wait_ms"] for row in rows),
                "schedule_wait_p95_ms": _percentile(
                    (row["schedule_wait_ms"] for row in rows), 0.95
                ),
                "communication_wait_mean_ms": _mean(
                    row["communication_wait_ms"] for row in rows
                ),
                "communication_wait_p95_ms": _percentile(
                    (row["communication_wait_ms"] for row in rows), 0.95
                ),
                "data_wait_mean_ms": _mean(
                    row["communication_wait_ms"] for row in rows
                ),
                "data_wait_p95_ms": _percentile(
                    (row["communication_wait_ms"] for row in rows), 0.95
                ),
                "cold_start_wait_mean_ms": _mean(
                    row["cold_start_wait_ms"] for row in rows
                ),
                "cold_start_wait_p95_ms": _percentile(
                    (row["cold_start_wait_ms"] for row in rows), 0.95
                ),
                "execution_mean_ms": _mean(row["execution_ms"] for row in rows),
                "execution_p95_ms": _percentile(
                    (row["execution_ms"] for row in rows), 0.95
                ),
                "stage_latency_p95_ms": _percentile(
                    (row["stage_latency_ms"] for row in rows), 0.95
                ),
                "throughput_rps": throughput,
            }
        )
    maximum = max(
        (_finite(row["throughput_rps"]) for row in output),
        default=math.nan,
    )
    for row in output:
        throughput = _finite(row["throughput_rps"])
        row["throughput_shortfall_vs_run_max"] = (
            1.0 - throughput / maximum
            if math.isfinite(maximum) and maximum > 0.0 and math.isfinite(throughput)
            else math.nan
        )
    return output


def stage_wait_run_metrics(artifacts: RunArtifacts) -> dict[str, Any]:
    """Aggregate lifecycle-stage waits once per independent run.

    The request stream contains completed function invocations only.  Every
    exported value therefore carries an explicit sample count and coverage
    status; an empty/partial stream yields NA rather than a synthetic zero.
    """

    rows = _invocation_rows(artifacts)

    def metric(name: str, probability: float | None = None) -> float:
        values = (row[name] for row in rows)
        return (
            _mean(values) if probability is None else _percentile(values, probability)
        )

    count = len(rows)
    status = "ok" if count else "unavailable_no_completed_function_invocations"
    return {
        **_run_context(artifacts),
        "run_id": artifacts.run_id,
        "seed": artifacts.seed,
        "algorithm": artifacts.algorithm,
        "completed_function_invocation_samples": count,
        "stage_wait_coverage_status": status,
        "schedule_wait_mean_ms": metric("schedule_wait_ms"),
        "schedule_wait_p95_ms": metric("schedule_wait_ms", 0.95),
        "cold_start_wait_mean_ms": metric("cold_start_wait_ms"),
        "cold_start_wait_p95_ms": metric("cold_start_wait_ms", 0.95),
        "data_wait_mean_ms": metric("communication_wait_ms"),
        "data_wait_p95_ms": metric("communication_wait_ms", 0.95),
        "execution_mean_ms": metric("execution_ms"),
        "execution_p95_ms": metric("execution_ms", 0.95),
        "stage_latency_mean_ms": metric("stage_latency_ms"),
        "stage_latency_p95_ms": metric("stage_latency_ms", 0.95),
    }


def window_differentiation_rows(
    artifacts: RunArtifacts,
) -> list[dict[str, Any]]:
    """Extract the active differentiation diagnostics once per scheduler window.

    The scheduler window is only a within-run observation.  Windows with no
    evaluated players, missing decision fields, or out-of-range ratios remain
    in the audit table with ``NaN`` values and an explicit coverage status; they
    are never converted to zero or treated as independent repetitions.
    """

    context = _run_context(artifacts)
    rows: list[dict[str, Any]] = []
    for window_index, event in enumerate(
        event for event in artifacts.nse_events if event.get("kind") == "window"
    ):
        decision = event.get("decision")
        if not isinstance(decision, Mapping):
            decision = {}
        evaluated = _finite(decision.get("ranking_diagnostic_players"))
        eligible = math.isfinite(evaluated) and evaluated > 0.0
        values: dict[str, float] = {}
        invalid_fields: list[str] = []
        missing_fields: list[str] = []
        for field_name in (DIFFERENTIATION_FEATURE, *DIFFERENTIATION_OUTCOMES):
            value = _finite(decision.get(field_name))
            if not math.isfinite(value):
                values[field_name] = math.nan
                missing_fields.append(field_name)
            elif not 0.0 <= value <= 1.0:
                values[field_name] = math.nan
                invalid_fields.append(field_name)
            elif not eligible:
                # Rust deliberately emits zeros when there are no ranked
                # players.  They are structural placeholders, not measured
                # differentiation/placement outcomes.
                values[field_name] = math.nan
            else:
                values[field_name] = value
        finite_fields = sum(math.isfinite(value) for value in values.values())
        if invalid_fields:
            status = "invalid_out_of_range:" + ",".join(invalid_fields)
        elif not math.isfinite(evaluated):
            status = "unavailable_missing_ranking_diagnostic_players"
        elif not eligible:
            status = "not_applicable_no_evaluated_players"
        elif missing_fields:
            status = "partial_missing_fields:" + ",".join(missing_fields)
        else:
            status = "ok"
        rows.append(
            {
                **context,
                "window_index": window_index,
                "frame": event.get("frame", math.nan),
                "ranking_diagnostic_players": evaluated,
                **values,
                "finite_diagnostic_fields": finite_fields,
                "window_coverage_status": status,
                "within_run_observation_unit": "scheduler_window",
                "inference_unit": "run_seed",
            }
        )
    return rows


def per_run_differentiation_correlations(
    window_rows: Sequence[Mapping[str, Any]],
    *,
    expected_runs: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Reduce window diagnostics to one Spearman rho per run and outcome.

    ``expected_runs`` makes absent diagnostics visible: every expected NSESche
    run receives four rows even when the corresponding log fields are missing.
    """

    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    context_keys = (
        "experiment_id",
        "cell_id",
        "run_id",
        "seed",
        "algorithm",
        "variant",
        "load",
        "node_count",
        "topology",
        "burst_pattern",
        "qos_profile",
    )
    for row in window_rows:
        key = (str(row.get("run_id", "")), str(row.get("seed", "")))
        grouped[key].append(row)
        contexts.setdefault(key, {name: row.get(name, "") for name in context_keys})
    for run in expected_runs:
        key = (str(run.get("run_id", "")), str(run.get("seed", "")))
        contexts.setdefault(key, {name: run.get(name, "") for name in context_keys})

    output: list[dict[str, Any]] = []
    for key, context in sorted(contexts.items()):
        selected = grouped.get(key, [])
        eligible_windows = sum(
            math.isfinite(_finite(row.get(DIFFERENTIATION_FEATURE))) for row in selected
        )
        for outcome in DIFFERENTIATION_OUTCOMES:
            correlation = spearman_correlation(
                (row.get(DIFFERENTIATION_FEATURE, math.nan) for row in selected),
                (row.get(outcome, math.nan) for row in selected),
            )
            status = str(correlation["status"])
            if not selected:
                status = "unavailable_no_window_events"
            elif eligible_windows == 0:
                status = "unavailable_no_eligible_windows"
            output.append(
                {
                    **context,
                    "feature": DIFFERENTIATION_FEATURE,
                    "outcome": outcome,
                    "primary_pair": True,
                    "rho": correlation["rho"],
                    "window_pairs": correlation["n"],
                    "total_windows": len(selected),
                    "eligible_feature_windows": eligible_windows,
                    "missing_or_inapplicable_windows": len(selected)
                    - int(correlation["n"]),
                    "status": status,
                    "within_run_observation_unit": "scheduler_window",
                    "inference_unit": "run_seed",
                }
            )
    return output


def per_run_feature_correlations(
    function_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in function_rows:
        grouped[(str(row.get("run_id", "")), str(row.get("seed", "")))].append(row)
    output: list[dict[str, Any]] = []
    for (_, _), rows in sorted(grouped.items()):
        context = {
            key: rows[0].get(key, "")
            for key in (
                "experiment_id",
                "cell_id",
                "run_id",
                "seed",
                "algorithm",
                "variant",
                "load",
                "node_count",
                "topology",
                "burst_pattern",
                "qos_profile",
            )
        }
        for feature in FEATURES:
            for outcome in FEATURE_OUTCOMES:
                correlation = spearman_correlation(
                    (row.get(feature, math.nan) for row in rows),
                    (row.get(outcome, math.nan) for row in rows),
                )
                output.append(
                    {
                        **context,
                        "feature": feature,
                        "outcome": outcome,
                        "primary_pair": (feature, outcome) in PRIMARY_FEATURE_PAIRS,
                        "rho": correlation["rho"],
                        "function_pairs": correlation["n"],
                        "status": correlation["status"],
                    }
                )
    return output


def summarize_feature_correlations(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_columns: Sequence[str] = (
        "experiment_id",
        "algorithm",
        "variant",
        "load",
        "node_count",
        "topology",
        "burst_pattern",
        "qos_profile",
        "feature",
        "outcome",
        "primary_pair",
    ),
    holm_family_columns: Sequence[str] = (
        "experiment_id",
        "algorithm",
        "variant",
        "load",
        "node_count",
        "topology",
        "burst_pattern",
        "qos_profile",
    ),
    bootstrap_resamples: int = 10_000,
    permutation_resamples: int = 100_000,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    """Bootstrap and test per-run Spearman rho values.

    When ``holm_family_columns`` is empty, every tested row belongs to one
    declared family (the legacy function-feature analysis).  Supplying columns
    creates a separate family per frozen experimental cell, as required for the
    active-differentiation window analysis.
    """

    groups: dict[tuple[str, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row.get(column, "")) for column in group_columns)].append(row)
    summaries: list[dict[str, Any]] = []
    raw_p: list[float] = []
    p_indices: list[int] = []
    for key, selected in sorted(groups.items()):
        values = [
            _finite(row.get("rho"))
            for row in selected
            if math.isfinite(_finite(row.get("rho")))
        ]
        summary: dict[str, Any] = {
            **dict(zip(group_columns, key)),
            "total_runs": len(selected),
            "applicable_runs": len(values),
            "applicability_rate": len(values) / len(selected) if selected else math.nan,
            "mean_rho": _mean(values),
            "median_rho": _percentile(values, 0.50),
            "bca_low": math.nan,
            "bca_high": math.nan,
            "p_raw": math.nan,
            "p_holm": math.nan,
            "reject_holm": False,
            "coverage_status": (
                "ok"
                if len(values) == len(selected) and len(values) >= 3
                else ("partial" if values else "unavailable")
            ),
            "status_counts": json.dumps(
                dict(
                    sorted(
                        {
                            str(status): sum(
                                str(row.get("status", "")) == str(status)
                                for row in selected
                            )
                            for status in {row.get("status", "") for row in selected}
                        }.items()
                    )
                )
            ),
            "inference_unit": "run_seed",
        }
        if len(values) >= 3:
            interval = bca_interval(
                values,
                n_resamples=bootstrap_resamples,
                seed=_stable_seed(seed, *key, "feature_ci"),
            )
            summary["bca_low"] = interval["low"]
            summary["bca_high"] = interval["high"]
        if values:
            test = paired_permutation_test(
                values,
                np.zeros(len(values)),
                n_resamples=permutation_resamples,
                seed=_stable_seed(seed, *key, "feature_test"),
            )
            summary["p_raw"] = test["p_value"]
            raw_p.append(float(test["p_value"]))
            p_indices.append(len(summaries))
        summaries.append(summary)
    if raw_p:
        families: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for index in p_indices:
            family = tuple(
                str(summaries[index].get(column, "")) for column in holm_family_columns
            )
            families[family].append(index)
        for indices in families.values():
            adjusted, rejected = holm_adjust(
                [float(summaries[index]["p_raw"]) for index in indices]
            )
            for index, p_holm, reject in zip(indices, adjusted, rejected):
                summaries[index]["p_holm"] = p_holm
                summaries[index]["reject_holm"] = reject
    return summaries


def summarize_differentiation_correlations(
    rows: Sequence[Mapping[str, Any]],
    *,
    bootstrap_resamples: int = 10_000,
    permutation_resamples: int = 100_000,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    """Aggregate per-run differentiation rhos across paired seed cells."""

    cell_columns = (
        "experiment_id",
        "algorithm",
        "variant",
        "load",
        "node_count",
        "topology",
        "burst_pattern",
        "qos_profile",
    )
    return summarize_feature_correlations(
        rows,
        group_columns=(*cell_columns, "feature", "outcome", "primary_pair"),
        holm_family_columns=cell_columns,
        bootstrap_resamples=bootstrap_resamples,
        permutation_resamples=permutation_resamples,
        seed=seed,
    )


def load_exact_poa_results(
    path: str | Path, *, require_frozen_design: bool = True
) -> list[dict[str, Any]]:
    """Validate constructed-state exact pure-PoA JSONL results.

    The formal E6 input is a deliberately separate constructed-state design:
    three nodes, 4/6/8 players, and 100 states at each player count.  Enforcing
    that coverage here prevents a partial exact enumeration from being plotted
    as if it were the frozen experiment.
    """

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"exact PoA result file is missing: {source}")
    rows: list[dict[str, Any]] = []
    state_ids: set[str] = set()
    for line_number, value in enumerate(_iter_jsonl_path(source), start=1):
        if value.get("schema") != "NSE_EXACT_POA_RESULT_V1":
            raise ValueError(f"exact PoA line {line_number} has an invalid schema")
        state_id = value.get("state_id")
        players = value.get("players")
        nodes = value.get("nodes")
        applicable = value.get("poa_applicable")
        pure_nash_exists = value.get("pure_nash_exists")
        pure_nash_equilibria = value.get("pure_nash_equilibria")
        if not isinstance(state_id, str) or not state_id or state_id in state_ids:
            raise ValueError(
                f"exact PoA line {line_number} has a duplicate/invalid state_id"
            )
        if (
            isinstance(players, bool)
            or not isinstance(players, int)
            or players <= 0
            or isinstance(nodes, bool)
            or not isinstance(nodes, int)
            or nodes <= 0
            or not isinstance(applicable, bool)
            or not isinstance(pure_nash_exists, bool)
            or isinstance(pure_nash_equilibria, bool)
            or not isinstance(pure_nash_equilibria, int)
            or pure_nash_equilibria < 0
        ):
            raise ValueError(f"exact PoA line {line_number} has invalid dimensions")
        if pure_nash_exists != (pure_nash_equilibria > 0):
            raise ValueError(
                f"exact PoA line {line_number} has inconsistent equilibrium counts"
            )
        exact_poa = _finite(value.get("exact_poa"))
        optimum = _finite(value.get("optimal_welfare"))
        worst = _finite(value.get("worst_nash_welfare"))
        relative_gap = _finite(value.get("relative_welfare_gap"))
        if applicable:
            if not (
                pure_nash_exists
                and math.isfinite(exact_poa)
                and exact_poa >= 1.0 - 1e-10
                and math.isfinite(optimum)
                and math.isfinite(worst)
                and optimum > 0.0
                and worst > 0.0
                and math.isclose(
                    exact_poa, optimum / worst, rel_tol=1e-9, abs_tol=1e-10
                )
            ):
                raise ValueError(
                    f"exact PoA line {line_number} is formula-inconsistent"
                )
        elif math.isfinite(exact_poa):
            raise ValueError(
                f"exact PoA line {line_number} marks a finite ratio inapplicable"
            )
        if not pure_nash_exists and (
            math.isfinite(worst) or math.isfinite(relative_gap) or applicable
        ):
            raise ValueError(
                f"exact PoA line {line_number} reports a worst equilibrium without one"
            )
        if math.isfinite(relative_gap) and not (
            math.isfinite(optimum)
            and math.isfinite(worst)
            and optimum > 0.0
            and math.isclose(
                relative_gap,
                (optimum - worst) / optimum,
                rel_tol=1e-9,
                abs_tol=1e-10,
            )
        ):
            raise ValueError(
                f"exact PoA line {line_number} has an invalid relative gap"
            )
        if value.get("poa_definition") != (
            "optimal_social_welfare/worst_pure_nash_social_welfare"
        ):
            raise ValueError(f"exact PoA line {line_number} changes the PoA definition")
        if value.get("formula_alignment") != (
            "NSESche individual utility and social-welfare aggregation"
        ):
            raise ValueError(f"exact PoA line {line_number} changes formula alignment")
        state_ids.add(state_id)
        rows.append(
            {
                "state_id": state_id,
                "nodes": nodes,
                "players": players,
                "pure_nash_exists": pure_nash_exists,
                "pure_nash_equilibria": pure_nash_equilibria,
                "exact_poa": exact_poa,
                "relative_welfare_gap": relative_gap,
                "poa_applicable": applicable,
                "inference_unit": "constructed_state",
                "scope": "constructed_small_exact_game_not_azure_trace_run",
            }
        )
    if not rows:
        raise ValueError("exact PoA result file is empty")
    if require_frozen_design:
        unexpected = [
            row
            for row in rows
            if row["nodes"] != EXACT_POA_NODES
            or row["players"] not in EXACT_POA_PLAYER_COUNTS
        ]
        if unexpected:
            raise ValueError(
                "exact PoA input does not match the frozen 3-node, 4/6/8-player design"
            )
        counts = {
            players: sum(row["players"] == players for row in rows)
            for players in EXACT_POA_PLAYER_COUNTS
        }
        expected = {
            players: EXACT_POA_STATES_PER_PLAYER_COUNT
            for players in EXACT_POA_PLAYER_COUNTS
        }
        if counts != expected or len(rows) != sum(expected.values()):
            raise ValueError(
                f"exact PoA frozen design coverage mismatch: observed={counts}, "
                f"expected={expected}"
            )
    return rows


def summarize_exact_poa(
    rows: Sequence[Mapping[str, Any]],
    *,
    bootstrap_resamples: int = 10_000,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    """Summarize exact pure PoA separately by constructed player count."""

    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        players = row.get("players")
        if isinstance(players, int) and not isinstance(players, bool):
            grouped[players].append(row)
    output: list[dict[str, Any]] = []
    for players, selected in sorted(grouped.items()):
        applicable = [
            _finite(row.get("exact_poa"))
            for row in selected
            if bool(row.get("poa_applicable"))
            and math.isfinite(_finite(row.get("exact_poa")))
        ]
        gaps = [
            _finite(row.get("relative_welfare_gap"))
            for row in selected
            if math.isfinite(_finite(row.get("relative_welfare_gap")))
        ]
        poa_low = poa_high = gap_low = gap_high = math.nan
        if len(applicable) >= 3:
            interval = bca_interval(
                applicable,
                statistic=np.median,
                n_resamples=bootstrap_resamples,
                seed=_stable_seed(seed, players, "exact_poa_median"),
            )
            poa_low, poa_high = float(interval["low"]), float(interval["high"])
        if len(gaps) >= 3:
            interval = bca_interval(
                gaps,
                statistic=np.median,
                n_resamples=bootstrap_resamples,
                seed=_stable_seed(seed, players, "exact_gap_median"),
            )
            gap_low, gap_high = float(interval["low"]), float(interval["high"])
        output.append(
            {
                "nodes": selected[0].get("nodes", ""),
                "players": players,
                "total_states": len(selected),
                "pure_nash_exists_states": sum(
                    bool(row.get("pure_nash_exists")) for row in selected
                ),
                "pure_nash_exists_ratio": _mean(
                    float(bool(row.get("pure_nash_exists"))) for row in selected
                ),
                "poa_applicable_states": len(applicable),
                "poa_applicable_ratio": len(applicable) / len(selected),
                "exact_poa_median": _percentile(applicable, 0.50),
                "exact_poa_bca_low": poa_low,
                "exact_poa_bca_high": poa_high,
                "relative_welfare_gap_median": _percentile(gaps, 0.50),
                "relative_welfare_gap_bca_low": gap_low,
                "relative_welfare_gap_bca_high": gap_high,
                "inference_unit": "constructed_state",
                "scope": "constructed_small_exact_game_not_azure_trace_run",
                "poa_definition": (
                    "optimal_social_welfare/worst_pure_nash_social_welfare"
                ),
            }
        )
    return output


def analyze_scheduler_run(artifacts: RunArtifacts) -> dict[str, Any]:
    """Reduce generic scheduler timing and NSE solver windows to one run row."""

    context = _run_context(artifacts)

    # `policy_*` is measured around the placement-policy call itself and is the
    # per-window source of the Rust summary's `placement_policy_*_ns` fields.
    # `wall_time_ns`/`thread_cpu_ns` cover the broader common-HPA mechanism.
    # They are intentionally retained under separate names and are never used
    # as a fallback for the primary policy metric or subtracted from it.
    wall_us = [
        _finite(row.get("policy_wall_time_ns")) / 1000.0
        for row in artifacts.scheduler_windows
    ]
    cpu_us = [
        _finite(row.get("policy_thread_cpu_ns")) / 1000.0
        for row in artifacts.scheduler_windows
    ]
    mechanism_wall_us = [
        _finite(row.get("wall_time_ns")) / 1000.0 for row in artifacts.scheduler_windows
    ]
    mechanism_cpu_us = [
        _finite(row.get("thread_cpu_ns")) / 1000.0
        for row in artifacts.scheduler_windows
    ]
    welfare_evaluation_wall_us = [
        _finite(row.get("welfare_evaluation_wall_time_ns")) / 1000.0
        for row in artifacts.scheduler_windows
    ]
    welfare_evaluation_cpu_us = [
        _finite(row.get("welfare_evaluation_thread_cpu_ns")) / 1000.0
        for row in artifacts.scheduler_windows
    ]
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    run_configs = [
        event for event in artifacts.nse_events if event.get("kind") == "run_config"
    ]
    run_summaries = [
        event for event in artifacts.nse_events if event.get("kind") == "run_summary"
    ]
    welfare_run_summaries = [
        event
        for event in artifacts.nse_events
        if event.get("kind") == "welfare_run_summary"
    ]
    run_summary = (
        run_summaries[-1]
        if run_summaries
        else (welfare_run_summaries[-1] if welfare_run_summaries else {})
    )
    reference_mode = str(
        _nested(
            artifacts.spec,
            "simulator_experiment",
            "reference",
            "mode",
            default=(
                _nested(run_configs[0], "reference", "mode", default="")
                if run_configs
                else ""
            ),
        )
    )
    solver_windows = [
        event
        for event in windows
        if isinstance(event.get("solver"), Mapping)
        and isinstance(event.get("decision"), Mapping)
    ]
    timing_source = "scheduler_windows.policy_wall_time_ns"
    welfare_windows = [
        event
        for event in artifacts.nse_events
        if event.get("kind") in {"window", "welfare_window"}
        and isinstance(event.get("social"), Mapping)
        and isinstance(event.get("decision"), Mapping)
    ]
    inner = [
        _finite(_nested(event, "solver", "inner_rounds")) for event in solver_windows
    ]
    outer = [
        _finite(_nested(event, "solver", "outer_rounds")) for event in solver_windows
    ]
    inner_hits = [
        bool(_nested(event, "solver", "inner_limit_hit", default=False))
        for event in solver_windows
    ]
    outer_hits = [
        bool(_nested(event, "solver", "outer_limit_hit", default=False))
        for event in solver_windows
    ]
    oscillations = [
        _finite(_nested(event, "solver", "oscillations")) for event in solver_windows
    ]
    nonconverged = [
        not (
            bool(_nested(event, "solver", "inner_stable", default=False))
            and bool(_nested(event, "solver", "outer_stable", default=False))
        )
        for event in solver_windows
    ]
    feedback_control_gaps: list[float] = []
    feedback_gammas: list[float] = []
    feedback_price_multipliers: list[float] = []
    feedback_assignment_changes: list[float] = []
    feedback_trace_rounds = 0
    feedback_applied_rounds = 0
    feedback_trace_invalid_rows = 0
    for event in solver_windows:
        raw_trace = _nested(event, "solver", "outer_feedback_trace")
        if raw_trace is None:
            continue
        if not isinstance(raw_trace, list):
            feedback_trace_invalid_rows += 1
            continue
        previous_hash: int | None = None
        previous_next_multiplier = math.nan
        network_beta = _finite(_nested(event, "pricing", "network_beta"))
        for expected_round, raw_round in enumerate(raw_trace, start=1):
            if not isinstance(raw_round, Mapping):
                feedback_trace_invalid_rows += 1
                continue
            round_number = raw_round.get("outer_round")
            assignment_hash = raw_round.get("assignment_hash")
            applied = raw_round.get("feedback_applied")
            current_multiplier = _finite(
                raw_round.get("price_multiplier_for_current_round")
            )
            if not (
                isinstance(round_number, int)
                and not isinstance(round_number, bool)
                and round_number == expected_round
                and isinstance(assignment_hash, int)
                and not isinstance(assignment_hash, bool)
                and assignment_hash >= 0
                and isinstance(applied, bool)
                and math.isfinite(current_multiplier)
                and current_multiplier > 0.0
            ):
                feedback_trace_invalid_rows += 1
                continue
            if math.isfinite(previous_next_multiplier) and not math.isclose(
                current_multiplier,
                previous_next_multiplier,
                rel_tol=1e-5,
                abs_tol=1e-8,
            ):
                feedback_trace_invalid_rows += 1
                continue

            reference = _finite(raw_round.get("reference_welfare_at_baseline_prices"))
            nash_welfare = _finite(raw_round.get("nash_welfare_at_current_prices"))
            gap = _finite(raw_round.get("feedback_gap"))
            expected_gap = math.nan
            if (
                math.isfinite(reference)
                and reference > 1e-12
                and math.isfinite(nash_welfare)
                and nash_welfare <= reference + 1e-8 * max(1.0, abs(reference))
            ):
                expected_gap = max(0.0, (reference - nash_welfare) / reference)
            if math.isfinite(expected_gap):
                if not (
                    math.isfinite(gap)
                    and math.isclose(gap, expected_gap, rel_tol=1e-5, abs_tol=1e-8)
                ):
                    feedback_trace_invalid_rows += 1
                    continue
                feedback_control_gaps.append(gap)
            elif math.isfinite(gap):
                feedback_trace_invalid_rows += 1
                continue

            gamma = _finite(raw_round.get("gamma"))
            if math.isfinite(gamma):
                if gamma < 0.0:
                    feedback_trace_invalid_rows += 1
                    continue
                feedback_gammas.append(gamma)
            next_multiplier = _finite(raw_round.get("price_multiplier_for_next_round"))
            if applied:
                if not (
                    math.isfinite(gap)
                    and math.isfinite(gamma)
                    and math.isfinite(next_multiplier)
                    and next_multiplier > 0.0
                ):
                    feedback_trace_invalid_rows += 1
                    continue
                if math.isfinite(network_beta):
                    expected_multiplier = 1.0 + gamma * network_beta * gap
                    if not math.isclose(
                        next_multiplier,
                        expected_multiplier,
                        rel_tol=1e-5,
                        abs_tol=1e-8,
                    ):
                        feedback_trace_invalid_rows += 1
                        continue
                feedback_applied_rounds += 1
                previous_next_multiplier = next_multiplier
                feedback_price_multipliers.append(next_multiplier)
            else:
                if math.isfinite(next_multiplier):
                    feedback_trace_invalid_rows += 1
                    continue
                previous_next_multiplier = math.nan
            feedback_price_multipliers.append(current_multiplier)
            if previous_hash is not None:
                feedback_assignment_changes.append(
                    float(assignment_hash != previous_hash)
                )
            previous_hash = assignment_hash
            feedback_trace_rounds += 1

    feedback_trace_status = (
        "invalid_trace_rows"
        if feedback_trace_invalid_rows
        else ("ok" if feedback_trace_rounds else "unavailable_legacy_stream")
    )
    compute_us = [
        _finite(_nested(event, "social", "reference_compute_us"))
        for event in welfare_windows
    ]
    lookup_us = [
        _finite(_nested(event, "social", "reference_lookup_us"))
        for event in welfare_windows
    ]
    refresh_us = [
        _finite(_nested(event, "overhead", "reference_table_refresh_us"))
        for event in solver_windows
    ]
    solve_us = [
        _finite(_nested(event, "overhead", "solve_us")) for event in solver_windows
    ]
    cache_hits = [
        _nested(event, "social", "reference_cache_hit")
        for event in welfare_windows
        if isinstance(_nested(event, "social", "reference_cache_hit"), bool)
    ]

    valid_gaps: list[float] = []
    gap_invalid = 0
    reference_present = 0
    sources: dict[str, int] = defaultdict(int)
    for event in welfare_windows:
        source = str(_nested(event, "social", "reference_source", default=""))
        if source:
            sources[source] += 1
        welfare = _finite(_nested(event, "social", "final_assignment_baseline_welfare"))
        if not math.isfinite(welfare):
            welfare = _finite(_nested(event, "social", "welfare"))
        reference = _finite(_nested(event, "social", "reference"))
        reported = _finite(_nested(event, "social", "empirical_gap"))
        if not math.isfinite(reported):
            reported = _finite(_nested(event, "social", "gap"))
        if math.isfinite(reference):
            reference_present += 1
        if not (
            math.isfinite(welfare)
            and math.isfinite(reference)
            and reference > 1e-12
            and welfare <= reference + 1e-8 * max(1.0, abs(reference))
        ):
            if math.isfinite(reference) or math.isfinite(reported):
                gap_invalid += 1
            continue
        empirical = max(0.0, (reference - welfare) / reference)
        if math.isfinite(reported) and not math.isclose(
            empirical, reported, rel_tol=1e-5, abs_tol=1e-8
        ):
            gap_invalid += 1
            continue
        valid_gaps.append(empirical)

    count = len(welfare_windows)
    compute_total = sum(value for value in compute_us if math.isfinite(value))
    lookup_total = sum(value for value in lookup_us if math.isfinite(value))
    compute_windows = sum(math.isfinite(value) and value > 0.0 for value in compute_us)
    lookup_windows = sum(math.isfinite(value) and value > 0.0 for value in lookup_us)

    process_peak_rss = _finite(
        artifacts.process_observation.get("peak_process_tree_rss_bytes")
    )
    process_cpu_seconds = _finite(
        artifacts.process_observation.get("process_tree_cpu_seconds")
    )
    process_status = (
        "ok"
        if math.isfinite(process_peak_rss) and process_peak_rss >= 0.0
        else "unavailable_missing_process_observation"
    )

    dependency = artifacts.spec.get("reference_dependency")
    reference_table_bytes = math.nan
    build_wall_ms = build_cpu_ms = build_peak_rss_mib = math.nan
    build_status = "not_applicable"
    if isinstance(dependency, Mapping):
        reference_table_bytes = _finite(dependency.get("bytes"))
        raw_process_path = dependency.get("build_process_observation_path")
        expected_process_hash = dependency.get("build_process_observation_sha256")
        build_status = "unavailable_missing_build_process_observation"
        if isinstance(raw_process_path, str) and raw_process_path:
            process_path = Path(raw_process_path)
            if process_path.is_file():
                digest = hashlib.sha256(process_path.read_bytes()).hexdigest()
                if (
                    isinstance(expected_process_hash, str)
                    and digest != expected_process_hash
                ):
                    build_status = "unavailable_build_process_hash_mismatch"
                else:
                    try:
                        build_process = _read_json(process_path)
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        build_status = "unavailable_invalid_build_process_observation"
                    else:
                        if (
                            isinstance(build_process, Mapping)
                            and build_process.get("schema_version")
                            == "NSE_PROCESS_OBSERVATION_V1"
                        ):
                            duration = _finite(build_process.get("duration_seconds"))
                            cpu = _finite(build_process.get("process_tree_cpu_seconds"))
                            rss = _finite(
                                build_process.get("peak_process_tree_rss_bytes")
                            )
                            build_wall_ms = duration * 1000.0
                            build_cpu_ms = cpu * 1000.0
                            build_peak_rss_mib = rss / (1024.0 * 1024.0)
                            build_status = (
                                "ok"
                                if all(
                                    math.isfinite(value) and value >= 0.0
                                    for value in (
                                        build_wall_ms,
                                        build_cpu_ms,
                                        build_peak_rss_mib,
                                    )
                                )
                                else "unavailable_invalid_build_process_metrics"
                            )
                        else:
                            build_status = (
                                "unavailable_invalid_build_process_observation"
                            )

    reference_load_us = _finite(run_summary.get("reference_load_us_total"))
    if not math.isfinite(reference_load_us) and run_configs:
        reference_load_us = _finite(
            _nested(run_configs[-1], "reference", "offline_load_us")
        )
    reference_load_status = (
        "ok"
        if math.isfinite(reference_load_us) and reference_load_us >= 0.0
        else (
            "not_applicable"
            if not isinstance(dependency, Mapping)
            else "unavailable_not_recorded"
        )
    )
    reference_load_cpu_us = _finite(
        run_summary.get("reference_load_thread_cpu_us_total")
    )
    reference_load_cpu_status = (
        "ok"
        if math.isfinite(reference_load_cpu_us) and reference_load_cpu_us >= 0.0
        else (
            "not_applicable"
            if not isinstance(dependency, Mapping)
            else "unavailable_not_recorded"
        )
    )
    reference_validation = (
        run_summary.get("reference_validation")
        if isinstance(run_summary.get("reference_validation"), Mapping)
        else {}
    )
    reference_applicable = isinstance(dependency, Mapping) or reference_mode not in {
        "",
        "not_required",
    }
    reference_unavailable = _finite(reference_validation.get("unavailable"))
    reference_unavailable_ratio = _finite(reference_validation.get("unavailable_ratio"))
    reference_persist_failures = _finite(reference_validation.get("persist_failures"))
    reference_windows = _finite(reference_validation.get("windows"))
    reference_persist_failure_ratio = (
        reference_persist_failures / reference_windows
        if math.isfinite(reference_persist_failures)
        and math.isfinite(reference_windows)
        and reference_windows > 0.0
        else math.nan
    )
    raw_offline_required_ok = reference_validation.get("offline_required_ok")
    reference_offline_required_ok = (
        float(raw_offline_required_ok)
        if isinstance(raw_offline_required_ok, bool)
        else math.nan
    )
    if not reference_applicable:
        reference_validation_status = "not_applicable_no_reference_dependency"
    elif not reference_validation:
        reference_validation_status = "unavailable_not_recorded"
    else:
        observed_status: list[str] = []
        if math.isfinite(reference_unavailable) and reference_unavailable > 0.0:
            observed_status.append("reference_unavailable_observed")
        if (
            math.isfinite(reference_persist_failures)
            and reference_persist_failures > 0.0
        ):
            observed_status.append("reference_persist_failure_observed")
        if raw_offline_required_ok is False:
            observed_status.append("offline_required_not_ok_observed")
        reference_validation_status = ";".join(observed_status) or "ok"
    placement_wall_mean_us = _mean(wall_us)
    placement_wall_p95_us = _percentile(wall_us, 0.95)
    placement_wall_p99_us = _percentile(wall_us, 0.99)
    placement_wall_max_us = _percentile(wall_us, 1.0)
    placement_cpu_mean_us = _mean(cpu_us)
    placement_cpu_p95_us = _percentile(cpu_us, 0.95)
    placement_cpu_p99_us = _percentile(cpu_us, 0.99)
    placement_cpu_max_us = _percentile(cpu_us, 1.0)
    return {
        **context,
        "scheduler_window_count": len(artifacts.scheduler_windows),
        "placement_policy_wall_mean_us": placement_wall_mean_us,
        "placement_policy_wall_p95_us": placement_wall_p95_us,
        "placement_policy_wall_p99_us": placement_wall_p99_us,
        "placement_policy_wall_max_us": placement_wall_max_us,
        "placement_policy_cpu_mean_us": placement_cpu_mean_us,
        "placement_policy_cpu_p95_us": placement_cpu_p95_us,
        "placement_policy_cpu_p99_us": placement_cpu_p99_us,
        "placement_policy_cpu_max_us": placement_cpu_max_us,
        # Backward-compatible analysis names.  These aliases are exactly the
        # placement-policy measurements above, never the common mechanism total.
        "scheduler_wall_mean_us": placement_wall_mean_us,
        "scheduler_wall_p95_us": placement_wall_p95_us,
        "scheduler_wall_p99_us": placement_wall_p99_us,
        "scheduler_wall_max_us": placement_wall_max_us,
        "scheduler_cpu_mean_us": placement_cpu_mean_us,
        "scheduler_cpu_p95_us": placement_cpu_p95_us,
        "scheduler_cpu_p99_us": placement_cpu_p99_us,
        "scheduler_cpu_max_us": placement_cpu_max_us,
        "mechanism_total_wall_mean_us": _mean(mechanism_wall_us),
        "mechanism_total_wall_p95_us": _percentile(mechanism_wall_us, 0.95),
        "mechanism_total_cpu_mean_us": _mean(mechanism_cpu_us),
        "mechanism_total_cpu_p95_us": _percentile(mechanism_cpu_us, 0.95),
        "welfare_evaluation_wall_mean_us": _mean(welfare_evaluation_wall_us),
        "welfare_evaluation_wall_p95_us": _percentile(welfare_evaluation_wall_us, 0.95),
        "welfare_evaluation_cpu_mean_us": _mean(welfare_evaluation_cpu_us),
        "welfare_evaluation_cpu_p95_us": _percentile(welfare_evaluation_cpu_us, 0.95),
        "policy_timing_derived_by_subtraction": False,
        "policy_timing_source": timing_source,
        "nse_event_source": artifacts.nse_event_source,
        "process_peak_rss_mib": (
            process_peak_rss / (1024.0 * 1024.0)
            if math.isfinite(process_peak_rss)
            else math.nan
        ),
        "process_tree_cpu_seconds": process_cpu_seconds,
        "process_observation_status": process_status,
        "nse_solver_window_count": len(solver_windows),
        "welfare_evaluation_window_count": count,
        "inner_rounds_mean": _mean(inner),
        "inner_rounds_median": _percentile(inner, 0.50),
        "inner_rounds_p95": _percentile(inner, 0.95),
        "inner_rounds_max": _percentile(inner, 1.0),
        "outer_rounds_mean": _mean(outer),
        "outer_rounds_median": _percentile(outer, 0.50),
        "outer_rounds_p95": _percentile(outer, 0.95),
        "outer_rounds_max": _percentile(outer, 1.0),
        "inner_limit_hit_rate": _mean(float(value) for value in inner_hits),
        "outer_limit_hit_rate": _mean(float(value) for value in outer_hits),
        "oscillation_window_rate": _mean(
            float(value > 0.0) for value in oscillations if math.isfinite(value)
        ),
        "oscillation_count_total": sum(
            value for value in oscillations if math.isfinite(value)
        ),
        "nonconvergence_rate": _mean(float(value) for value in nonconverged),
        "feedback_trace_rounds": feedback_trace_rounds,
        "feedback_applied_rounds": feedback_applied_rounds,
        "feedback_trace_invalid_rows": feedback_trace_invalid_rows,
        "feedback_trace_status": feedback_trace_status,
        "feedback_gap_control_mean": _mean(feedback_control_gaps),
        "feedback_gap_control_p95": _percentile(feedback_control_gaps, 0.95),
        "feedback_gamma_mean": _mean(feedback_gammas),
        "feedback_price_multiplier_max": _percentile(feedback_price_multipliers, 1.0),
        "outer_assignment_change_rate": _mean(feedback_assignment_changes),
        "reference_mode": reference_mode,
        "reference_compute_total_us": compute_total,
        "reference_compute_mean_us": _mean(compute_us),
        "reference_compute_windows": compute_windows,
        "reference_lookup_total_us": lookup_total,
        "reference_lookup_mean_us": _mean(lookup_us),
        "reference_lookup_windows": lookup_windows,
        "offline_reference_build_total_us": (
            compute_total if reference_mode == "build" else math.nan
        ),
        "online_fallback_compute_total_us": (
            compute_total if reference_mode and reference_mode != "build" else math.nan
        ),
        "reference_table_refresh_total_us": sum(
            value for value in refresh_us if math.isfinite(value)
        ),
        "offline_build_wall_ms": build_wall_ms,
        "offline_build_cpu_ms": build_cpu_ms,
        "offline_build_peak_rss_mib": build_peak_rss_mib,
        "offline_build_observation_status": build_status,
        "reference_table_bytes": (
            reference_table_bytes
            if math.isfinite(reference_table_bytes) and reference_table_bytes >= 0.0
            else math.nan
        ),
        "reference_table_size_mib": (
            reference_table_bytes / (1024.0 * 1024.0)
            if math.isfinite(reference_table_bytes) and reference_table_bytes >= 0.0
            else math.nan
        ),
        "reference_table_load_us": reference_load_us,
        "reference_table_load_status": reference_load_status,
        "reference_table_load_thread_cpu_us": reference_load_cpu_us,
        "reference_table_load_thread_cpu_status": reference_load_cpu_status,
        "reference_missing_ratio": _finite(reference_validation.get("missing_ratio")),
        "reference_zero_ratio": _finite(reference_validation.get("zero_ratio")),
        "reference_negative_ratio": _finite(reference_validation.get("negative_ratio")),
        "reference_feedback_eligible_windows": _finite(
            reference_validation.get("feedback_eligible")
        ),
        "reference_feedback_eligible_ratio": _finite(
            reference_validation.get("feedback_eligible_ratio")
        ),
        "reference_below_current_windows": _finite(
            reference_validation.get("below_current")
        ),
        "reference_below_current_ratio": _finite(
            reference_validation.get("below_current_ratio")
        ),
        "reference_search_suboptimal_windows": _finite(
            reference_validation.get("search_suboptimal")
        ),
        "reference_search_suboptimal_ratio": _finite(
            reference_validation.get("search_suboptimal_ratio")
        ),
        "reference_unavailable_windows": reference_unavailable,
        "reference_unavailable_ratio": reference_unavailable_ratio,
        "reference_persist_failures": reference_persist_failures,
        "reference_persist_failure_ratio": reference_persist_failure_ratio,
        "reference_offline_required_ok": reference_offline_required_ok,
        "reference_validation_status": reference_validation_status,
        "solve_mean_us": _mean(solve_us),
        "reference_cache_hit_rate": _mean(float(value) for value in cache_hits),
        "welfare_gap_mean": _mean(valid_gaps),
        "welfare_gap_median": _percentile(valid_gaps, 0.50),
        "welfare_gap_p95": _percentile(valid_gaps, 0.95),
        "welfare_gap_max": _percentile(valid_gaps, 1.0),
        "welfare_gap_valid_windows": len(valid_gaps),
        "welfare_reference_present_windows": reference_present,
        "welfare_gap_invalid_windows": gap_invalid,
        "welfare_gap_applicability": len(valid_gaps) / count if count else math.nan,
        "reference_source_counts": json.dumps(dict(sorted(sources.items()))),
        "inference_unit": "run_seed",
    }


def summarize_long(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_columns: Sequence[str],
    metrics: Sequence[str],
    bootstrap_resamples: int = 10_000,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    """Summarize run rows; each finite input is one independent run/seed."""

    grouped: dict[tuple[str, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(column, "")) for column in group_columns)].append(row)
    output: list[dict[str, Any]] = []
    for key, selected in sorted(grouped.items()):
        context = dict(zip(group_columns, key))
        unique_runs = {
            (str(row.get("run_id", "")), str(row.get("seed", ""))) for row in selected
        }
        if len(unique_runs) != len(selected):
            raise ValueError(f"duplicate run/seed rows in summary group {context}")
        for metric in metrics:
            values = [
                _finite(row.get(metric))
                for row in selected
                if math.isfinite(_finite(row.get(metric)))
            ]
            summary = {
                **context,
                "metric": metric,
                "mean": _mean(values),
                "median": _percentile(values, 0.50),
                "bca_low": math.nan,
                "bca_high": math.nan,
                "n_runs": len(values),
                "total_runs": len(selected),
                "missing_runs": len(selected) - len(values),
                "coverage_rate": len(values) / len(selected) if selected else math.nan,
                "coverage_status": (
                    "ok"
                    if len(values) == len(selected)
                    else ("partial" if values else "unavailable")
                ),
                "ci_status": (
                    "ok"
                    if len(values) >= 3
                    else ("insufficient_runs" if values else "unavailable")
                ),
                "inference_unit": "run_seed",
            }
            if len(values) >= 3:
                interval = bca_interval(
                    values,
                    n_resamples=bootstrap_resamples,
                    seed=_stable_seed(seed, *key, metric),
                )
                summary["bca_low"] = interval["low"]
                summary["bca_high"] = interval["high"]
            output.append(summary)
    return output


def summarize_timeseries(
    rows: Sequence[Mapping[str, Any]],
    *,
    metrics: Sequence[str] = (
        "arrival_rps",
        "queue_total",
        "throughput_rps",
        "rolling_p95_ms",
        "rolling_p99_ms",
    ),
    bootstrap_resamples: int = 2_000,
    seed: int = 20260809,
) -> list[dict[str, Any]]:
    """Pointwise run-bootstrap curves without frame-level pseudoreplication."""

    curve_groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for row in rows:
        curve_groups[
            (
                str(row.get("algorithm", "")),
                str(row.get("burst_pattern", "")),
                str(row.get("run_id", "")),
            )
        ].append(row)
    by_cell: dict[
        tuple[str, str], list[tuple[str, list[Mapping[str, Any]]]]
    ] = defaultdict(list)
    for (algorithm, pattern, run_id), curve in curve_groups.items():
        by_cell[(algorithm, pattern)].append(
            (
                run_id,
                sorted(curve, key=lambda row: _finite(row.get("time_relative_ms"))),
            )
        )
    output: list[dict[str, Any]] = []
    for (algorithm, pattern), curves in sorted(by_cell.items()):
        reference_times = np.asarray(
            [_finite(row.get("time_relative_ms")) for row in curves[0][1]], dtype=float
        )
        for run_id, curve in curves[1:]:
            times = np.asarray(
                [_finite(row.get("time_relative_ms")) for row in curve], dtype=float
            )
            if times.shape != reference_times.shape or not np.allclose(
                times, reference_times, equal_nan=False
            ):
                raise ValueError(
                    f"time grid mismatch for {algorithm}/{pattern}, run {run_id}"
                )
        active = np.asarray(
            [bool(row.get("burst_active")) for row in curves[0][1]], dtype=bool
        )
        n_runs = len(curves)
        for metric in metrics:
            matrix = np.asarray(
                [[_finite(row.get(metric)) for row in curve] for _, curve in curves],
                dtype=float,
            )
            counts = np.sum(np.isfinite(matrix), axis=0)
            sums = np.nansum(matrix, axis=0)
            means = np.divide(
                sums,
                counts,
                out=np.full(matrix.shape[1], np.nan),
                where=counts > 0,
            )
            low = np.full(matrix.shape[1], np.nan)
            high = np.full(matrix.shape[1], np.nan)
            if n_runs >= 2:
                rng = np.random.default_rng(
                    _stable_seed(seed, algorithm, pattern, metric, "curve")
                )
                indices = rng.integers(
                    0, n_runs, size=(bootstrap_resamples, n_runs), endpoint=False
                )
                sampled = matrix[indices]
                sampled_counts = np.sum(np.isfinite(sampled), axis=1)
                sampled_means = np.divide(
                    np.nansum(sampled, axis=1),
                    sampled_counts,
                    out=np.full((bootstrap_resamples, matrix.shape[1]), np.nan),
                    where=sampled_counts > 0,
                )
                for column in range(matrix.shape[1]):
                    finite = sampled_means[:, column]
                    finite = finite[np.isfinite(finite)]
                    if finite.size:
                        low[column], high[column] = np.quantile(
                            finite, (0.025, 0.975), method="linear"
                        )
            for index, time_ms in enumerate(reference_times):
                output.append(
                    {
                        "algorithm": algorithm,
                        "burst_pattern": pattern,
                        "time_relative_ms": float(time_ms),
                        "burst_active": bool(active[index]),
                        "metric": metric,
                        "mean": float(means[index]),
                        "ci_low": float(low[index]),
                        "ci_high": float(high[index]),
                        "n_runs": int(counts[index]),
                        "total_runs": n_runs,
                        "ci_method": "pointwise_run_bootstrap_percentile_95",
                        "inference_unit": "run_seed",
                    }
                )
    return output


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(str(key))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)
    return path


def _load_sla_targets(path: str | Path | None) -> Mapping[str, Any] | None:
    if path is None:
        return None
    value = _read_json(Path(path))
    if not isinstance(value, Mapping):
        raise ValueError("SLA targets JSON must be an object")
    unknown = set(value) - set(QOS_CLASSES)
    if unknown:
        raise ValueError(f"unknown SLA classes: {sorted(unknown)}")
    return value


def build_observability_comparisons(
    *,
    burst_runs: Sequence[Mapping[str, Any]],
    qos_runs: Sequence[Mapping[str, Any]],
    fairness_runs: Sequence[Mapping[str, Any]],
    diagnostic_runs: Sequence[Mapping[str, Any]],
    bootstrap_resamples: int = 10_000,
    permutation_resamples: int = 100_000,
    seed: int = 20260809,
) -> dict[str, list[dict[str, Any]]]:
    """Create predeclared paired/Holm tables for every observability bar family."""

    common = {
        "treatment_column": "algorithm",
        "reference": "NSESche",
        "pair_column": "seed",
        "bootstrap_resamples": bootstrap_resamples,
        "permutation_resamples": permutation_resamples,
        "seed": seed,
    }
    return {
        "e3": paired_comparisons(
            burst_runs,
            context_columns=("burst_pattern",),
            metrics=(
                "peak_queue",
                "recovery_time_ms",
                "restricted_recovery_time_ms",
                "recovery_observed",
                "admission_drop",
                "admission_reject",
                "timeout",
                "latency_p95_ms",
                "latency_p99_ms",
            ),
            **common,
        ),
        "e4_qos": paired_comparisons(
            qos_runs,
            context_columns=("qos_class",),
            metrics=(
                "stage_latency_p95_ms",
                "stage_latency_p99_ms",
                "throughput_rps",
                "completion_ratio",
                "direct_cost_mean",
                "sla_violation_rate",
            ),
            **common,
        ),
        "e4_fairness": paired_comparisons(
            fairness_runs,
            context_columns=(),
            metrics=("jain_satisfaction", "worst10_satisfaction"),
            **common,
        ),
        "e9": paired_comparisons(
            diagnostic_runs,
            context_columns=(
                "experiment_id",
                "variant",
                "load",
                "node_count",
                "topology",
                "burst_pattern",
                "qos_profile",
            ),
            metrics=(
                "placement_policy_wall_mean_us",
                "placement_policy_cpu_mean_us",
                "solve_mean_us",
                "process_peak_rss_mib",
                "inner_rounds_mean",
                "outer_rounds_mean",
                "inner_limit_hit_rate",
                "outer_limit_hit_rate",
                "oscillation_window_rate",
                "nonconvergence_rate",
                "reference_lookup_mean_us",
                "offline_build_wall_ms",
                "offline_build_cpu_ms",
                "offline_build_peak_rss_mib",
                "reference_table_bytes",
                "reference_table_load_us",
                "reference_table_load_thread_cpu_us",
                "reference_missing_ratio",
                "reference_zero_ratio",
                "reference_negative_ratio",
                "reference_feedback_eligible_ratio",
                "reference_below_current_ratio",
                "reference_search_suboptimal_ratio",
                "reference_unavailable_ratio",
                "reference_persist_failure_ratio",
                "reference_offline_required_ok",
                "welfare_gap_mean",
                "welfare_gap_p95",
                "welfare_gap_applicability",
                "reference_cache_hit_rate",
            ),
            **common,
        ),
    }


def run_observability_pipeline(
    *,
    manifest_path: str | Path,
    canonical_root: str | Path,
    output_dir: str | Path,
    sla_targets: Mapping[str, Any] | None = None,
    exact_poa_results_path: str | Path | None = None,
    pairing_audit_path: str | Path | None = None,
    strict: bool = True,
    bootstrap_resamples: int = 10_000,
    time_bootstrap_resamples: int = 2_000,
    permutation_resamples: int = 100_000,
    seed: int = 20260809,
) -> dict[str, Path]:
    manifest = _read_json(Path(manifest_path))
    assert_formal_manifest(manifest)
    canonical_path = Path(canonical_root).resolve()
    if strict and pairing_audit_path is None:
        raise ValueError(
            "formal observability export requires --pairing-audit in strict mode"
        )
    if pairing_audit_path is not None:
        validate_pairing_audit(
            Path(pairing_audit_path).resolve(), manifest, canonical_path
        )
    result_relative_path = str(
        (manifest.get("execution") or {}).get("result_relative_path", "result.json")
    )
    output = Path(output_dir)
    manifest_directory = Path(manifest_path).resolve().parent
    output.mkdir(parents=True, exist_ok=True)
    burst_series: list[dict[str, Any]] = []
    burst_runs: list[dict[str, Any]] = []
    qos_runs: list[dict[str, Any]] = []
    fairness_runs: list[dict[str, Any]] = []
    qos_function_rows: list[dict[str, Any]] = []
    function_rows: list[dict[str, Any]] = []
    stage_wait_runs: list[dict[str, Any]] = []
    differentiation_windows: list[dict[str, Any]] = []
    differentiation_expected_runs: list[dict[str, Any]] = []
    diagnostic_runs: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []

    for run in manifest["runs"]:
        if not isinstance(run, Mapping):
            continue
        run_id = str(run.get("run_id", ""))
        try:
            artifacts = load_run_artifacts(
                run,
                canonical_path,
                expected_manifest_hash=str(manifest["manifest_hash"]),
                result_relative_path=result_relative_path,
            )
            experiment_id = str(run.get("experiment_id", ""))
            if experiment_id == "E3":
                series, metrics = analyze_burst_run(artifacts)
                burst_series.extend(series)
                burst_runs.append(metrics)
            if experiment_id == "E4":
                workload_events = load_workload_tape_events(run, manifest_directory)
                class_rows, fairness, functions = analyze_qos_run(
                    artifacts,
                    sla_targets=_sla_targets_for_run(run, sla_targets),
                    workload_events=workload_events,
                    require_arrival_coverage=True,
                )
                qos_runs.extend(class_rows)
                fairness_runs.append(fairness)
                qos_function_rows.extend(functions)
            if any(
                event.get("kind") == "function_profile"
                for event in artifacts.nse_events
            ):
                current_function_rows = function_runtime_rows(artifacts)
                if any(
                    math.isfinite(_finite(row.get(feature)))
                    for row in current_function_rows
                    for feature in FEATURES
                ):
                    function_rows.extend(current_function_rows)
            stage_wait_runs.append(stage_wait_run_metrics(artifacts))
            if artifacts.algorithm == "NSESche" and experiment_id in {"E1", "E3", "E4"}:
                differentiation_expected_runs.append(_run_context(artifacts))
                differentiation_windows.extend(window_differentiation_rows(artifacts))
            diagnostic_runs.append(analyze_scheduler_run(artifacts))
            coverage.append({"run_id": run_id, "status": "ok", "detail": ""})
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            coverage.append(
                {"run_id": run_id, "status": "unavailable", "detail": str(exc)}
            )

    failures = [row for row in coverage if row["status"] != "ok"]
    outputs: dict[str, Path] = {}
    outputs["coverage"] = _write_csv(output / "coverage.csv", coverage)
    if strict and failures:
        raise ValueError(
            f"{len(failures)} canonical runs could not be analyzed; see {outputs['coverage']}"
        )

    burst_metrics = (
        "recovery_time_ms",
        "recovery_observed",
        "restricted_recovery_time_ms",
        "queue_only_recovery_time_ms",
        "queue_only_recovery_observed",
        "p99_recovery_time_ms",
        "p99_recovery_observed",
        "joint_recovery_time_ms",
        "joint_recovery_observed",
        "peak_queue",
        "admission_drop",
        "admission_reject",
        "timeout",
        "latency_p95_ms",
        "latency_p99_ms",
        "burst_arrival_latency_p95_ms",
        "burst_arrival_latency_p99_ms",
    )
    qos_metrics = (
        "stage_latency_mean_ms",
        "stage_latency_p95_ms",
        "stage_latency_p99_ms",
        "throughput_rps",
        "offered_invocation_rps",
        "completion_ratio",
        "direct_cost_mean",
        "resource_cost_proxy_mean",
        "sla_violation_rate",
        "satisfaction_mean",
    )
    fairness_metrics = ("jain_satisfaction", "worst10_satisfaction")
    stage_wait_metrics = (
        "schedule_wait_mean_ms",
        "schedule_wait_p95_ms",
        "cold_start_wait_mean_ms",
        "cold_start_wait_p95_ms",
        "data_wait_mean_ms",
        "data_wait_p95_ms",
        "execution_mean_ms",
        "execution_p95_ms",
        "stage_latency_mean_ms",
        "stage_latency_p95_ms",
    )
    diagnostic_metrics = (
        "placement_policy_wall_mean_us",
        "placement_policy_wall_p95_us",
        "placement_policy_cpu_mean_us",
        "placement_policy_cpu_p95_us",
        "mechanism_total_wall_mean_us",
        "mechanism_total_wall_p95_us",
        "mechanism_total_cpu_mean_us",
        "mechanism_total_cpu_p95_us",
        "welfare_evaluation_wall_mean_us",
        "welfare_evaluation_wall_p95_us",
        "welfare_evaluation_cpu_mean_us",
        "welfare_evaluation_cpu_p95_us",
        "process_peak_rss_mib",
        "process_tree_cpu_seconds",
        "inner_rounds_mean",
        "inner_rounds_p95",
        "outer_rounds_mean",
        "outer_rounds_p95",
        "inner_limit_hit_rate",
        "outer_limit_hit_rate",
        "oscillation_window_rate",
        "nonconvergence_rate",
        "feedback_trace_rounds",
        "feedback_applied_rounds",
        "feedback_trace_invalid_rows",
        "feedback_gap_control_mean",
        "feedback_gap_control_p95",
        "feedback_gamma_mean",
        "feedback_price_multiplier_max",
        "outer_assignment_change_rate",
        "reference_compute_total_us",
        "offline_reference_build_total_us",
        "online_fallback_compute_total_us",
        "reference_lookup_total_us",
        "reference_lookup_mean_us",
        "reference_table_refresh_total_us",
        "offline_build_wall_ms",
        "offline_build_cpu_ms",
        "offline_build_peak_rss_mib",
        "reference_table_bytes",
        "reference_table_size_mib",
        "reference_table_load_us",
        "reference_table_load_thread_cpu_us",
        "reference_missing_ratio",
        "reference_zero_ratio",
        "reference_negative_ratio",
        "reference_feedback_eligible_windows",
        "reference_feedback_eligible_ratio",
        "reference_below_current_windows",
        "reference_below_current_ratio",
        "reference_search_suboptimal_windows",
        "reference_search_suboptimal_ratio",
        "reference_unavailable_windows",
        "reference_unavailable_ratio",
        "reference_persist_failures",
        "reference_persist_failure_ratio",
        "reference_offline_required_ok",
        "reference_cache_hit_rate",
        "solve_mean_us",
        "welfare_gap_mean",
        "welfare_gap_p95",
        "welfare_gap_applicability",
    )

    correlations = per_run_feature_correlations(function_rows)
    correlation_summary = summarize_feature_correlations(
        correlations,
        bootstrap_resamples=bootstrap_resamples,
        permutation_resamples=permutation_resamples,
        seed=seed,
    )
    differentiation_correlations = per_run_differentiation_correlations(
        differentiation_windows,
        expected_runs=differentiation_expected_runs,
    )
    differentiation_summary = summarize_differentiation_correlations(
        differentiation_correlations,
        bootstrap_resamples=bootstrap_resamples,
        permutation_resamples=permutation_resamples,
        seed=seed,
    )
    comparison_tables = build_observability_comparisons(
        burst_runs=burst_runs,
        qos_runs=qos_runs,
        fairness_runs=fairness_runs,
        diagnostic_runs=diagnostic_runs,
        bootstrap_resamples=bootstrap_resamples,
        permutation_resamples=permutation_resamples,
        seed=seed,
    )
    diagnostic_coverage: list[dict[str, Any]] = []
    diagnostic_coverage_metrics = diagnostic_metrics
    for row in diagnostic_runs:
        for metric in diagnostic_coverage_metrics:
            value = _finite(row.get(metric))
            status = "ok" if math.isfinite(value) else "unavailable"
            if metric == "process_peak_rss_mib":
                detail = row.get("process_observation_status", "")
            elif metric.startswith("offline_build_"):
                detail = row.get("offline_build_observation_status", "")
            elif metric == "reference_table_load_us":
                detail = row.get("reference_table_load_status", "")
            elif metric == "reference_table_load_thread_cpu_us":
                detail = row.get("reference_table_load_thread_cpu_status", "")
            elif metric in {
                "reference_missing_ratio",
                "reference_zero_ratio",
                "reference_negative_ratio",
                "reference_feedback_eligible_windows",
                "reference_feedback_eligible_ratio",
                "reference_below_current_windows",
                "reference_below_current_ratio",
                "reference_search_suboptimal_windows",
                "reference_search_suboptimal_ratio",
                "reference_unavailable_windows",
                "reference_unavailable_ratio",
                "reference_persist_failures",
                "reference_persist_failure_ratio",
                "reference_offline_required_ok",
            }:
                detail = row.get("reference_validation_status", "")
            elif (
                metric.startswith("reference_")
                or metric.startswith("offline_reference_")
                or metric.startswith("online_fallback_")
            ) and row.get("reference_mode") in {"", "not_required"}:
                detail = "not_applicable_no_reference_dependency"
            elif (
                metric
                in {
                    "inner_rounds_mean",
                    "inner_rounds_p95",
                    "outer_rounds_mean",
                    "outer_rounds_p95",
                    "inner_limit_hit_rate",
                    "outer_limit_hit_rate",
                    "oscillation_window_rate",
                    "nonconvergence_rate",
                    "solve_mean_us",
                    "welfare_gap_mean",
                    "welfare_gap_p95",
                    "welfare_gap_applicability",
                    "reference_cache_hit_rate",
                }
                and row.get("algorithm") != "NSESche"
            ):
                detail = "not_applicable_non_nsesche_solver"
            else:
                detail = "not_applicable_or_not_recorded" if status != "ok" else ""
            if str(detail).startswith("not_applicable"):
                status = "not_applicable"
            elif str(detail).startswith("unavailable"):
                status = "unavailable"
            diagnostic_coverage.append(
                {
                    **{
                        key: row.get(key, "")
                        for key in (
                            "experiment_id",
                            "algorithm",
                            "variant",
                            "load",
                            "node_count",
                            "run_id",
                            "seed",
                        )
                    },
                    "metric": metric,
                    "status": status,
                    "detail": detail,
                    "value": value,
                }
            )
    outputs.update(
        {
            "e3_timeseries_run": _write_csv(
                output / "e3_timeseries_run.csv", burst_series
            ),
            "e3_timeseries_summary": _write_csv(
                output / "e3_timeseries_summary.csv",
                summarize_timeseries(
                    burst_series,
                    bootstrap_resamples=time_bootstrap_resamples,
                    seed=seed,
                ),
            ),
            "e3_run_metrics": _write_csv(output / "e3_run_metrics.csv", burst_runs),
            "e3_run_summary": _write_csv(
                output / "e3_run_summary.csv",
                summarize_long(
                    burst_runs,
                    group_columns=("algorithm", "burst_pattern"),
                    metrics=burst_metrics,
                    bootstrap_resamples=bootstrap_resamples,
                    seed=seed,
                ),
            ),
            "e3_comparisons": _write_csv(
                output / "e3_comparisons.csv", comparison_tables["e3"]
            ),
            "e4_qos_run": _write_csv(output / "e4_qos_run.csv", qos_runs),
            "e4_qos_summary": _write_csv(
                output / "e4_qos_summary.csv",
                summarize_long(
                    qos_runs,
                    group_columns=("algorithm", "qos_class"),
                    metrics=qos_metrics,
                    bootstrap_resamples=bootstrap_resamples,
                    seed=seed,
                ),
            ),
            "e4_qos_comparisons": _write_csv(
                output / "e4_qos_comparisons.csv", comparison_tables["e4_qos"]
            ),
            "e4_fairness_run": _write_csv(
                output / "e4_fairness_run.csv", fairness_runs
            ),
            "e4_fairness_summary": _write_csv(
                output / "e4_fairness_summary.csv",
                summarize_long(
                    fairness_runs,
                    group_columns=("algorithm",),
                    metrics=fairness_metrics,
                    bootstrap_resamples=bootstrap_resamples,
                    seed=seed,
                ),
            ),
            "e4_fairness_comparisons": _write_csv(
                output / "e4_fairness_comparisons.csv",
                comparison_tables["e4_fairness"],
            ),
            "e4_function_sla_audit": _write_csv(
                output / "e4_function_sla_audit.csv", qos_function_rows
            ),
            "stage_wait_run": _write_csv(
                output / "stage_wait_run.csv", stage_wait_runs
            ),
            "stage_wait_summary": _write_csv(
                output / "stage_wait_summary.csv",
                summarize_long(
                    stage_wait_runs,
                    group_columns=(
                        "experiment_id",
                        "algorithm",
                        "variant",
                        "load",
                        "node_count",
                        "topology",
                        "burst_pattern",
                        "qos_profile",
                    ),
                    metrics=stage_wait_metrics,
                    bootstrap_resamples=bootstrap_resamples,
                    seed=seed,
                ),
            ),
            "e8_function_observations": _write_csv(
                output / "e8_function_observations.csv", function_rows
            ),
            "e8_correlations_run": _write_csv(
                output / "e8_correlations_run.csv", correlations
            ),
            "e8_correlations_summary": _write_csv(
                output / "e8_correlations_summary.csv", correlation_summary
            ),
            "e8_differentiation_windows": _write_csv(
                output / "e8_differentiation_windows.csv",
                differentiation_windows,
            ),
            "e8_differentiation_correlations_run": _write_csv(
                output / "e8_differentiation_correlations_run.csv",
                differentiation_correlations,
            ),
            "e8_differentiation_correlations_summary": _write_csv(
                output / "e8_differentiation_correlations_summary.csv",
                differentiation_summary,
            ),
            "e8_differentiation_coverage": _write_csv(
                output / "e8_differentiation_coverage.csv",
                [
                    {
                        **{
                            key: row.get(key, "")
                            for key in (
                                "experiment_id",
                                "algorithm",
                                "variant",
                                "load",
                                "node_count",
                                "topology",
                                "burst_pattern",
                                "qos_profile",
                                "run_id",
                                "seed",
                            )
                        },
                        "feature": row.get("feature", ""),
                        "outcome": row.get("outcome", ""),
                        "total_windows": row.get("total_windows", 0),
                        "finite_window_pairs": row.get("window_pairs", 0),
                        "missing_or_inapplicable_windows": row.get(
                            "missing_or_inapplicable_windows", 0
                        ),
                        "status": row.get("status", ""),
                        "rho": row.get("rho", math.nan),
                    }
                    for row in differentiation_correlations
                ],
            ),
            "e9_diagnostics_run": _write_csv(
                output / "e9_diagnostics_run.csv", diagnostic_runs
            ),
            "e9_diagnostics_summary": _write_csv(
                output / "e9_diagnostics_summary.csv",
                summarize_long(
                    diagnostic_runs,
                    group_columns=(
                        "experiment_id",
                        "algorithm",
                        "variant",
                        "load",
                        "node_count",
                        "topology",
                        "burst_pattern",
                        "qos_profile",
                    ),
                    metrics=diagnostic_metrics,
                    bootstrap_resamples=bootstrap_resamples,
                    seed=seed,
                ),
            ),
            "e9_comparisons": _write_csv(
                output / "e9_comparisons.csv", comparison_tables["e9"]
            ),
            "e9_metric_coverage": _write_csv(
                output / "e9_metric_coverage.csv", diagnostic_coverage
            ),
        }
    )
    if exact_poa_results_path is not None:
        exact_poa_rows = load_exact_poa_results(exact_poa_results_path)
        outputs["e9_exact_poa_state_audit"] = _write_csv(
            output / "e9_exact_poa_state_audit.csv", exact_poa_rows
        )
        outputs["e9_exact_poa_summary"] = _write_csv(
            output / "e9_exact_poa_summary.csv",
            summarize_exact_poa(
                exact_poa_rows,
                bootstrap_resamples=bootstrap_resamples,
                seed=seed,
            ),
        )
    analysis_manifest = {
        "schema": "NSE_REVIEWER_OBSERVABILITY_ANALYSIS_V1",
        "inference_unit": "run_seed",
        "within_run_units_not_independent": [
            "frame",
            "request",
            "function",
            "scheduler_window",
        ],
        "recovery_definition": asdict(RecoveryDefinition()),
        "sla_targets": sla_targets,
        "sla_target_source": "run_manifest_preferred_then_cli",
        "exact_poa_results_path": (
            str(Path(exact_poa_results_path).resolve())
            if exact_poa_results_path is not None
            else None
        ),
        "pairing_audit_path": (
            str(Path(pairing_audit_path).resolve())
            if pairing_audit_path is not None
            else None
        ),
        "exact_poa_scope": "constructed_small_exact_games_kept_separate_from_empirical_sa_gap",
        "exact_poa_inference_unit": "constructed_state",
        "exact_poa_frozen_design": {
            "nodes": EXACT_POA_NODES,
            "player_counts": list(EXACT_POA_PLAYER_COUNTS),
            "states_per_player_count": EXACT_POA_STATES_PER_PLAYER_COUNT,
        },
        "feature_primary_pairs": sorted([list(pair) for pair in PRIMARY_FEATURE_PAIRS]),
        "stage_wait_metrics": {
            "run_level_unit": "completed_function_invocation_sample_within_run",
            "metrics": list(stage_wait_metrics),
            "output": "stage_wait_run.csv and stage_wait_summary.csv",
        },
        "differentiation_window_analysis": {
            "feature": DIFFERENTIATION_FEATURE,
            "outcomes": list(DIFFERENTIATION_OUTCOMES),
            "within_run_unit": "scheduler_window",
            "inference_unit": "run_seed",
            "method": "within-run Spearman rho, then cross-seed BCa CI and sign-flip test",
            "holm_family": "four outcomes within each frozen experimental cell",
        },
        "bootstrap_resamples": bootstrap_resamples,
        "time_bootstrap_resamples": time_bootstrap_resamples,
        "permutation_resamples": permutation_resamples,
        "seed": seed,
        "outputs": {key: str(path.resolve()) for key, path in outputs.items()},
    }
    manifest_output = output / "observability_analysis_manifest.json"
    with manifest_output.open("w", encoding="utf-8") as handle:
        json.dump(analysis_manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    outputs["manifest"] = manifest_output
    return outputs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--canonical-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--sla-targets",
        help="pre-registered JSON targets; absent targets remain explicitly unavailable",
    )
    parser.add_argument(
        "--exact-poa-results",
        help="optional NSE_EXACT_POA_RESULT_V1 JSONL from constructed small games",
    )
    parser.add_argument(
        "--pairing-audit",
        help=(
            "passing pairing-audit.json bound to this manifest/root "
            "(required unless --allow-incomplete is used)"
        ),
    )
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--bootstrap-resamples", type=int, default=10_000)
    parser.add_argument("--time-bootstrap-resamples", type=int, default=2_000)
    parser.add_argument("--permutation-resamples", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args(argv)
    outputs = run_observability_pipeline(
        manifest_path=args.manifest,
        canonical_root=args.canonical_root,
        output_dir=args.output_dir,
        sla_targets=_load_sla_targets(args.sla_targets),
        exact_poa_results_path=args.exact_poa_results,
        pairing_audit_path=args.pairing_audit,
        strict=not args.allow_incomplete,
        bootstrap_resamples=args.bootstrap_resamples,
        time_bootstrap_resamples=args.time_bootstrap_resamples,
        permutation_resamples=args.permutation_resamples,
        seed=args.seed,
    )
    for path in outputs.values():
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
