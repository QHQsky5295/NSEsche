#!/usr/bin/env python3
"""Audit and summarize the preregistered P1-A retained NSESche evidence."""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import statistics
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from .stats import bca_interval


EXPECTED_SEEDS = tuple(f"Q{index}" for index in range(61, 81))
EXPECTED_BINARY_SHA256 = (
    "7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4"
)
EXPECTED_READY_FILE_SHA256 = (
    "d8892c7226c0cd91757659f7a6ea61c5a095af6eee51045b2a31551f7ea8a38a"
)
EXPECTED_READY_DOCUMENT_SHA256 = (
    "5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b"
)
RUN_NAME = re.compile(
    r"^TSCv1\.E1\.homogeneous\.n20\.low\.sche_nash\.F(Q(?:6[1-9]|7[0-9]|80))\.[0-9a-f]{8}$"
)
REFERENCE_KEY = re.compile(
    r"^nse-reference\.E1\.sche_nash\.(low|middle|high)\."
    r"(homogeneous|heterogeneous)\.n20\.(Q(?:6[1-9]|7[0-9]|80))\.[0-9a-f]{16}$"
)


class RetainedEvidenceError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RetainedEvidenceError(f"{path} is not a JSON object")
    return value


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RetainedEvidenceError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise RetainedEvidenceError(f"{name} must be finite")
    return result


def _read_gzip_jsonl(path: Path, archive_entry: dict[str, Any]) -> list[dict[str, Any]]:
    if _sha256(path) != archive_entry.get("gzip_sha256"):
        raise RetainedEvidenceError(f"gzip SHA-256 mismatch: {path}")
    rows: list[dict[str, Any]] = []
    raw_digest = hashlib.sha256()
    raw_bytes = 0
    with gzip.open(path, "rb") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw_digest.update(line)
            raw_bytes += len(line)
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RetainedEvidenceError(f"{path}:{line_number} is not an object")
            rows.append(value)
    if raw_digest.hexdigest() != archive_entry.get("raw_sha256"):
        raise RetainedEvidenceError(f"raw SHA-256 mismatch after decompression: {path}")
    if raw_bytes != int(archive_entry.get("raw_bytes", -1)):
        raise RetainedEvidenceError(f"raw byte count mismatch: {path}")
    if len(rows) != int(archive_entry.get("raw_lines", -1)):
        raise RetainedEvidenceError(f"raw line count mismatch: {path}")
    return rows


def _collect_run_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "run_id" and isinstance(child, str):
                found.add(child)
            found.update(_collect_run_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_collect_run_ids(child))
    return found


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return float(statistics.fmean(materialized)) if materialized else math.nan


def _validate_trace(window: dict[str, Any], seed: str) -> None:
    solver = window.get("solver")
    social = window.get("social")
    pricing = window.get("pricing")
    if (
        not isinstance(solver, dict)
        or not isinstance(social, dict)
        or not isinstance(pricing, dict)
    ):
        raise RetainedEvidenceError(f"{seed}: malformed solver/social/pricing window")
    network_beta = _finite(pricing.get("network_beta"), f"{seed}: pricing.network_beta")
    for field in ("inner_stable", "outer_stable", "inner_limit_hit", "outer_limit_hit"):
        if not isinstance(solver.get(field), bool):
            raise RetainedEvidenceError(f"{seed}: solver.{field} is not boolean")
    trace = solver.get("outer_feedback_trace")
    if not isinstance(trace, list) or len(trace) != int(solver.get("outer_rounds", -1)):
        raise RetainedEvidenceError(f"{seed}: outer trace length mismatch")
    for item in trace:
        if not isinstance(item, dict) or not isinstance(
            item.get("feedback_applied"), bool
        ):
            raise RetainedEvidenceError(f"{seed}: malformed outer feedback trace")
        for field in ("gamma", "price_multiplier_for_current_round"):
            _finite(item.get(field), f"{seed}: trace.{field}")
        reference = item.get("reference_welfare_at_baseline_prices")
        nash = item.get("nash_welfare_at_current_prices")
        gap = item.get("feedback_gap")
        if reference is not None:
            reference = _finite(reference, f"{seed}: trace.reference")
        if nash is not None:
            nash = _finite(nash, f"{seed}: trace.nash")
        if gap is not None:
            gap = _finite(gap, f"{seed}: trace.gap")
        if reference is not None and reference > 1.0e-6 and nash is not None:
            expected_gap = (reference - nash) / reference
            if gap is not None and abs(gap - expected_gap) > 2.0e-6 * max(
                1.0, abs(gap), abs(expected_gap)
            ):
                raise RetainedEvidenceError(f"{seed}: Eq. (16) gap mismatch")
        if item["feedback_applied"]:
            if gap is None or gap <= 0.0:
                raise RetainedEvidenceError(
                    f"{seed}: feedback applied without positive gap"
                )
            next_multiplier = _finite(
                item.get("price_multiplier_for_next_round"),
                f"{seed}: trace.next_multiplier",
            )
            expected_multiplier = 1.0 + float(item["gamma"]) * network_beta * gap
            if abs(next_multiplier - expected_multiplier) > 2.0e-6 * max(
                1.0, abs(next_multiplier), abs(expected_multiplier)
            ):
                raise RetainedEvidenceError(f"{seed}: Eqs. (19)-(20) mismatch")


def aggregate_seed(
    seed: str,
    run_id: str,
    windows: Sequence[dict[str, Any]],
    scheduler_windows: Sequence[dict[str, Any]],
    process: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(windows) != 1000 or len(scheduler_windows) != 1000:
        raise RetainedEvidenceError(f"{seed}: expected 1,000 policy/timing windows")
    active = [
        window
        for window in windows
        if int(window["decision"]["request_function_players"]) > 0
    ]
    no_player = [
        window
        for window in windows
        if int(window["decision"]["request_function_players"]) == 0
    ]
    if len(active) + len(no_player) != 1000:
        raise RetainedEvidenceError(f"{seed}: invalid player-window partition")
    for window in active:
        _validate_trace(window, seed)

    active_n = len(active)
    inner_stable = sum(bool(window["solver"]["inner_stable"]) for window in active)
    outer_stable = sum(bool(window["solver"]["outer_stable"]) for window in active)
    nonconverged = sum(
        not (
            bool(window["solver"]["inner_stable"])
            and bool(window["solver"]["outer_stable"])
        )
        for window in active
    )
    limit_hit = sum(
        bool(window["solver"]["inner_limit_hit"])
        or bool(window["solver"]["outer_limit_hit"])
        for window in active
    )
    oscillation = sum(int(window["solver"]["oscillations"]) > 0 for window in active)
    trace_items = [
        item for window in active for item in window["solver"]["outer_feedback_trace"]
    ]
    eligible_trace = [
        item for item in trace_items if item.get("feedback_gap") is not None
    ]
    feedback_applied = sum(bool(item["feedback_applied"]) for item in eligible_trace)
    eligible_windows = sum(
        bool(window["social"]["feedback_eligible"]) for window in active
    )

    source_counts = collections.Counter(
        str(window["social"]["reference_source"]) for window in active
    )
    termination_counts = collections.Counter(
        str(window["solver"]["termination"]) for window in active
    )
    references = [window["social"].get("reference") for window in active]
    positive = sum(value is not None and float(value) > 0.0 for value in references)
    zero = sum(value is not None and float(value) == 0.0 for value in references)
    negative = sum(value is not None and float(value) < 0.0 for value in references)
    missing = sum(
        window["social"]["reference_source"] == "offline_table_missing"
        for window in active
    )
    unavailable = sum(
        window["social"].get("reference") is None
        and window["social"].get("reference_state_key") is not None
        and window["social"]["reference_source"] != "offline_table_missing"
        for window in active
    )
    below_current = sum(
        bool(window["social"]["reference_below_current"]) for window in active
    )
    search_suboptimal = sum(
        bool(window["social"]["reference_search_suboptimal"]) for window in active
    )

    timing_fields = (
        "wall_time_ns",
        "thread_cpu_ns",
        "policy_wall_time_ns",
        "policy_thread_cpu_ns",
        "welfare_evaluation_wall_time_ns",
        "welfare_evaluation_thread_cpu_ns",
    )
    for timing in scheduler_windows:
        if timing.get("schema") != "NSE_SCHEDULER_WINDOW_V1":
            raise RetainedEvidenceError(f"{seed}: wrong scheduler-window schema")
        if not isinstance(timing.get("timing_scope"), dict):
            raise RetainedEvidenceError(f"{seed}: missing timing scope")
        for field in timing_fields:
            _finite(timing.get(field), f"{seed}: scheduler.{field}")

    def rate(numerator: int, denominator: int = active_n) -> float:
        return numerator / denominator if denominator else math.nan

    row: dict[str, Any] = {
        "seed": seed,
        "run_id": run_id,
        "active_windows": active_n,
        "no_player_windows": len(no_player),
        "inner_stable_count": inner_stable,
        "inner_stable_rate": rate(inner_stable),
        "outer_stable_count": outer_stable,
        "outer_stable_rate": rate(outer_stable),
        "nonconverged_count": nonconverged,
        "nonconverged_rate": rate(nonconverged),
        "limit_hit_count": limit_hit,
        "limit_hit_rate": rate(limit_hit),
        "oscillation_window_count": oscillation,
        "oscillation_rate": rate(oscillation),
        "reference_eligible_window_count": eligible_windows,
        "reference_eligible_window_rate": rate(eligible_windows),
        "feedback_eligible_trace_rounds": len(eligible_trace),
        "feedback_applied_rounds": feedback_applied,
        "feedback_applied_rate": rate(feedback_applied, len(eligible_trace)),
        "reference_positive_count": positive,
        "reference_positive_rate": rate(positive),
        "reference_zero_count": zero,
        "reference_negative_count": negative,
        "reference_missing_count": missing,
        "reference_unavailable_count": unavailable,
        "reference_below_current_count": below_current,
        "reference_below_current_rate": rate(below_current),
        "reference_search_suboptimal_count": search_suboptimal,
        "reference_search_suboptimal_rate": rate(search_suboptimal),
        "inner_rounds_mean_active": _mean(
            float(window["solver"]["inner_rounds"]) for window in active
        ),
        "outer_rounds_mean_active": _mean(
            float(window["solver"]["outer_rounds"]) for window in active
        ),
        "solve_us_mean_active": _mean(
            float(window["overhead"]["solve_us"]) for window in active
        ),
        "reference_lookup_us_mean_active": _mean(
            float(window["social"]["reference_lookup_us"]) for window in active
        ),
        "scheduler_wall_ns_mean": _mean(
            float(row["wall_time_ns"]) for row in scheduler_windows
        ),
        "scheduler_thread_cpu_ns_mean": _mean(
            float(row["thread_cpu_ns"]) for row in scheduler_windows
        ),
        "policy_wall_ns_mean": _mean(
            float(row["policy_wall_time_ns"]) for row in scheduler_windows
        ),
        "policy_thread_cpu_ns_mean": _mean(
            float(row["policy_thread_cpu_ns"]) for row in scheduler_windows
        ),
        "welfare_evaluation_wall_ns_mean": _mean(
            float(row["welfare_evaluation_wall_time_ns"]) for row in scheduler_windows
        ),
        "welfare_evaluation_thread_cpu_ns_mean": _mean(
            float(row["welfare_evaluation_thread_cpu_ns"]) for row in scheduler_windows
        ),
        "process_duration_seconds": _finite(
            process.get("duration_seconds"), "duration_seconds"
        ),
        "process_tree_cpu_seconds": _finite(
            process.get("process_tree_cpu_seconds"), "process_tree_cpu_seconds"
        ),
        "peak_process_tree_rss_bytes": int(
            _finite(
                process.get("peak_process_tree_rss_bytes"),
                "peak_process_tree_rss_bytes",
            )
        ),
        "process_timed_out": bool(process.get("timed_out")),
        "process_exit_code": int(process.get("exit_code")),
    }
    if row["process_timed_out"] or row["process_exit_code"] != 0:
        raise RetainedEvidenceError(f"{seed}: invalid process completion")

    count_rows: list[dict[str, Any]] = []
    for stratum, stratum_windows in (("active", active), ("no_player", no_player)):
        for dimension, field_path in (
            ("termination", ("solver", "termination")),
            ("reference_source", ("social", "reference_source")),
        ):
            counts = collections.Counter(
                str(window[field_path[0]][field_path[1]]) for window in stratum_windows
            )
            for label, count in sorted(counts.items()):
                count_rows.append(
                    {
                        "seed": seed,
                        "stratum": stratum,
                        "dimension": dimension,
                        "label": label,
                        "count": count,
                    }
                )
    return row, count_rows


def _seeded_metric_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "inner_stable_rate",
        "outer_stable_rate",
        "nonconverged_rate",
        "limit_hit_rate",
        "oscillation_rate",
        "reference_eligible_window_rate",
        "feedback_applied_rate",
        "reference_positive_rate",
        "reference_below_current_rate",
        "reference_search_suboptimal_rate",
        "inner_rounds_mean_active",
        "outer_rounds_mean_active",
        "solve_us_mean_active",
        "reference_lookup_us_mean_active",
        "scheduler_wall_ns_mean",
        "scheduler_thread_cpu_ns_mean",
        "policy_wall_ns_mean",
        "policy_thread_cpu_ns_mean",
        "welfare_evaluation_wall_ns_mean",
        "welfare_evaluation_thread_cpu_ns_mean",
        "process_duration_seconds",
        "process_tree_cpu_seconds",
        "peak_process_tree_rss_bytes",
    )
    result: dict[str, Any] = {}
    for metric in metrics:
        values = [float(row[metric]) for row in rows]
        if any(not math.isfinite(value) for value in values):
            raise RetainedEvidenceError(f"nonfinite seed-level metric: {metric}")
        seed_bytes = hashlib.sha256(f"NSE-P1-BCA-V1|{metric}".encode("utf-8")).digest()
        ci = bca_interval(
            values,
            statistic=np.mean,
            confidence=0.95,
            n_resamples=10_000,
            seed=int.from_bytes(seed_bytes[:8], "big", signed=False),
        )
        result[metric] = {
            "points": values,
            "mean": statistics.fmean(values),
            "sample_sd": statistics.stdev(values),
            "median": statistics.median(values),
            "bca_95": ci,
        }
    return result


def _reference_rows(catalog_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = _json(catalog_path)
    entries = catalog.get("entries")
    if not isinstance(entries, dict) or len(entries) != 120:
        raise RetainedEvidenceError(
            "reference catalog must contain exactly 120 entries"
        )
    coverage: collections.Counter[tuple[str, str, str]] = collections.Counter()
    rows: list[dict[str, Any]] = []
    for key, entry in sorted(entries.items()):
        if not isinstance(entry, dict) or entry.get("key") != key:
            raise RetainedEvidenceError(f"malformed catalog entry: {key}")
        match = REFERENCE_KEY.fullmatch(key)
        if match is None:
            raise RetainedEvidenceError(f"unexpected reference key: {key}")
        load, topology, seed = match.groups()
        coverage[(load, topology, seed)] += 1
        table_path = Path(entry["path"])
        receipt_path = Path(entry["receipt_path"])
        process_path = Path(entry["build_process_observation_path"])
        if (
            not table_path.is_file()
            or not receipt_path.is_file()
            or not process_path.is_file()
        ):
            raise RetainedEvidenceError(f"missing reference artifact: {key}")
        if (
            _sha256(table_path) != entry["sha256"]
            or table_path.stat().st_size != entry["bytes"]
        ):
            raise RetainedEvidenceError(f"reference table identity mismatch: {key}")
        if _sha256(receipt_path) != entry["receipt_sha256"]:
            raise RetainedEvidenceError(f"reference receipt identity mismatch: {key}")
        if _sha256(process_path) != entry["build_process_observation_sha256"]:
            raise RetainedEvidenceError(f"reference process identity mismatch: {key}")
        receipt = _json(receipt_path)
        process = _json(process_path)
        if (
            receipt.get("reference_key") != key
            or receipt.get("table_sha256") != entry["sha256"]
        ):
            raise RetainedEvidenceError(f"reference receipt binding mismatch: {key}")
        positive = 0
        nonpositive = 0
        compute_us = 0
        line_count = 0
        with table_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                value = _finite(item.get("reference"), f"{key}: reference")
                positive += int(value > 0.0)
                nonpositive += int(value <= 0.0)
                compute_us += int(_finite(item.get("compute_us"), f"{key}: compute_us"))
                line_count += 1
        if line_count != int(entry["line_count"]) or line_count != int(
            receipt["table_line_count"]
        ):
            raise RetainedEvidenceError(f"reference line count mismatch: {key}")
        rows.append(
            {
                "reference_key": key,
                "load": load,
                "topology": topology,
                "seed": seed,
                "state_rows": line_count,
                "positive_rows": positive,
                "nonpositive_rows": nonpositive,
                "build_completed_requests": int(entry["build_completed"]),
                "reference_compute_us_total": compute_us,
                "build_wall_seconds": _finite(
                    process["duration_seconds"], f"{key}: duration"
                ),
                "build_process_tree_cpu_seconds": _finite(
                    process["process_tree_cpu_seconds"], f"{key}: cpu"
                ),
                "build_peak_process_tree_rss_bytes": int(
                    _finite(process["peak_process_tree_rss_bytes"], f"{key}: rss")
                ),
                "table_bytes": int(entry["bytes"]),
                "table_sha256": entry["sha256"],
                "receipt_sha256": entry["receipt_sha256"],
                "process_observation_sha256": entry["build_process_observation_sha256"],
            }
        )
    expected = {
        (load, topology, seed)
        for load in ("low", "middle", "high")
        for topology in ("homogeneous", "heterogeneous")
        for seed in EXPECTED_SEEDS
    }
    if set(coverage) != expected or any(value != 1 for value in coverage.values()):
        raise RetainedEvidenceError(
            "reference catalog does not have exact 2x3x20 coverage"
        )
    totals = {
        "entries": len(rows),
        "state_rows": sum(row["state_rows"] for row in rows),
        "positive_rows": sum(row["positive_rows"] for row in rows),
        "nonpositive_rows": sum(row["nonpositive_rows"] for row in rows),
        "build_wall_seconds": sum(row["build_wall_seconds"] for row in rows),
        "build_process_tree_cpu_seconds": sum(
            row["build_process_tree_cpu_seconds"] for row in rows
        ),
        "max_build_peak_process_tree_rss_bytes": max(
            row["build_peak_process_tree_rss_bytes"] for row in rows
        ),
        "table_bytes": sum(row["table_bytes"] for row in rows),
    }
    return rows, totals


def _csv_text(rows: Sequence[dict[str, Any]]) -> str:
    if not rows:
        raise RetainedEvidenceError("cannot write an empty CSV")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RetainedEvidenceError(f"refusing to overwrite {path}")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".partial", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def analyze(formal_root: Path, output_dir: Path) -> dict[str, Any]:
    ready_path = formal_root / "q61-q80.formal.ready.json"
    catalog_path = formal_root / "q61-q80.reference.catalog.json"
    if _sha256(ready_path) != EXPECTED_READY_FILE_SHA256:
        raise RetainedEvidenceError("formal ready-manifest file hash mismatch")
    ready_document = _json(ready_path)
    if ready_document.get("manifest_hash") != EXPECTED_READY_DOCUMENT_SHA256:
        raise RetainedEvidenceError("formal ready-manifest document hash mismatch")
    ready_run_ids = _collect_run_ids(ready_document)

    canonical = formal_root / "online" / "homogeneous-low" / "canonical"
    selected: dict[str, Path] = {}
    for directory in canonical.iterdir():
        if not directory.is_dir():
            continue
        match = RUN_NAME.fullmatch(directory.name)
        if match is None:
            continue
        seed = match.group(1)
        if seed in selected:
            raise RetainedEvidenceError(f"duplicate retained seed: {seed}")
        selected[seed] = directory
    if tuple(sorted(selected, key=lambda value: int(value[1:]))) != EXPECTED_SEEDS:
        raise RetainedEvidenceError("retained run selection is not exactly Q61-Q80")

    seed_rows: list[dict[str, Any]] = []
    count_rows: list[dict[str, Any]] = []
    integrity_runs: list[dict[str, Any]] = []
    run_spec_hashes: set[str] = set()
    for seed in EXPECTED_SEEDS:
        run_dir = selected[seed]
        run_id = run_dir.name
        if run_id not in ready_run_ids:
            raise RetainedEvidenceError(f"{seed}: run absent from ready manifest")
        config = _json(run_dir / "run_config.json")
        qc = _json(run_dir / "qc_report.json")
        manifest = _json(run_dir / "manifest.json")
        process = _json(run_dir / "process_observation.json")
        archive = _json(run_dir / "jsonl_archive_summary.json")
        expected_config = {
            "experiment_id": "E1",
            "method": "sche_nash",
            "variant": "full",
            "seed": seed,
        }
        if any(config.get(key) != value for key, value in expected_config.items()):
            raise RetainedEvidenceError(f"{seed}: run config selection mismatch")
        if config.get("workload", {}).get("request_freq") != "low":
            raise RetainedEvidenceError(f"{seed}: wrong load")
        if (
            config.get("cluster", {}).get("node_count") != 20
            or config.get("cluster", {}).get("topology") != "homogeneous"
        ):
            raise RetainedEvidenceError(f"{seed}: wrong cluster cell")
        if (
            config.get("environment", {}).get("NASH_OPERATIONAL_REFINEMENT")
            != "ready_order"
        ):
            raise RetainedEvidenceError(f"{seed}: wrong operational refinement")
        if config.get("metadata", {}).get("strict_best_response") is not True:
            raise RetainedEvidenceError(f"{seed}: strict best response not declared")
        if qc.get("passed") is not True or qc.get("classification") != "qc_pass":
            raise RetainedEvidenceError(f"{seed}: canonical QC failed")
        run_spec_hash = str(config.get("run_spec_hash"))
        if run_spec_hash in run_spec_hashes:
            raise RetainedEvidenceError(f"{seed}: duplicate run-spec hash")
        run_spec_hashes.add(run_spec_hash)
        protocol_manifest = manifest.get("protocol_manifest", {})
        if (
            protocol_manifest.get("file_sha256") != EXPECTED_READY_FILE_SHA256
            or protocol_manifest.get("manifest_hash") != EXPECTED_READY_DOCUMENT_SHA256
        ):
            raise RetainedEvidenceError(f"{seed}: ready-manifest binding mismatch")
        adapter = manifest.get("adapter_binary", {})
        if adapter.get("observed_sha256") != EXPECTED_BINARY_SHA256:
            raise RetainedEvidenceError(f"{seed}: binary hash mismatch")
        binary_path = Path(adapter.get("path", ""))
        if not binary_path.is_file() or _sha256(binary_path) != EXPECTED_BINARY_SHA256:
            raise RetainedEvidenceError(
                f"{seed}: anchor executable unavailable/mismatched"
            )
        dependency = config.get("reference_dependency", {})
        dependency_path = Path(dependency.get("path", ""))
        if not dependency_path.is_file() or _sha256(dependency_path) != dependency.get(
            "sha256"
        ):
            raise RetainedEvidenceError(f"{seed}: offline reference binding mismatch")

        archive_entries = {
            Path(item["gzip_relative_path"]).name: item
            for item in archive.get("artifacts", [])
        }
        expected_archives = {
            "frames.jsonl.gz",
            "nash_metrics.jsonl.gz",
            "requests.jsonl.gz",
            "scheduler_windows.jsonl.gz",
        }
        if set(archive_entries) != expected_archives:
            raise RetainedEvidenceError(f"{seed}: compressed artifact set mismatch")
        record_dirs = [
            path for path in (run_dir / "reviewer_records").iterdir() if path.is_dir()
        ]
        if len(record_dirs) != 1 or record_dirs[0].name != run_id:
            raise RetainedEvidenceError(f"{seed}: reviewer-record directory mismatch")
        record_dir = record_dirs[0]
        nash_rows = _read_gzip_jsonl(
            record_dir / "nash_metrics.jsonl.gz",
            archive_entries["nash_metrics.jsonl.gz"],
        )
        scheduler_rows = _read_gzip_jsonl(
            record_dir / "scheduler_windows.jsonl.gz",
            archive_entries["scheduler_windows.jsonl.gz"],
        )
        request_rows = _read_gzip_jsonl(
            record_dir / "requests.jsonl.gz", archive_entries["requests.jsonl.gz"]
        )
        _read_gzip_jsonl(
            record_dir / "frames.jsonl.gz", archive_entries["frames.jsonl.gz"]
        )
        kinds = collections.Counter(row.get("kind") for row in nash_rows)
        if (
            kinds["run_config"] != 1
            or kinds["window"] != 1000
            or kinds["run_summary"] != 1
        ):
            raise RetainedEvidenceError(
                f"{seed}: NSESche stream record counts mismatch"
            )
        stream_config = next(
            row for row in nash_rows if row.get("kind") == "run_config"
        )
        if (
            stream_config.get("strict_best_response") is not True
            or stream_config.get("operational_refinement") != "ready_order"
            or stream_config.get("g0_semantics_contract_schema")
            != "eq14_eq16_eq19_semantics_v1"
        ):
            raise RetainedEvidenceError(f"{seed}: NSESche stream contract mismatch")
        if not request_rows:
            raise RetainedEvidenceError(f"{seed}: empty request stream")
        windows = [row for row in nash_rows if row.get("kind") == "window"]
        row, counts = aggregate_seed(seed, run_id, windows, scheduler_rows, process)
        seed_rows.append(row)
        count_rows.extend(counts)
        integrity_runs.append(
            {
                "seed": seed,
                "run_id": run_id,
                "run_spec_hash": run_spec_hash,
                "audit_manifest_hash": manifest.get("audit_manifest_hash"),
                "reference_dependency_sha256": dependency.get("sha256"),
                "gzip_artifact_sha256": {
                    name: archive_entries[name]["gzip_sha256"]
                    for name in sorted(archive_entries)
                },
            }
        )

    reference_rows, reference_totals = _reference_rows(catalog_path)
    metric_summary = _seeded_metric_summary(seed_rows)
    pooled_counts = {
        field: sum(int(row[field]) for row in seed_rows)
        for field in (
            "active_windows",
            "no_player_windows",
            "inner_stable_count",
            "outer_stable_count",
            "nonconverged_count",
            "limit_hit_count",
            "oscillation_window_count",
            "reference_eligible_window_count",
            "feedback_eligible_trace_rounds",
            "feedback_applied_rounds",
            "reference_positive_count",
            "reference_zero_count",
            "reference_negative_count",
            "reference_missing_count",
            "reference_unavailable_count",
            "reference_below_current_count",
            "reference_search_suboptimal_count",
        )
    }
    active_total = pooled_counts["active_windows"]
    trace_total = pooled_counts["feedback_eligible_trace_rounds"]
    pooled_fractions = {
        "inner_stable": {
            "numerator": pooled_counts["inner_stable_count"],
            "denominator": active_total,
        },
        "outer_stable": {
            "numerator": pooled_counts["outer_stable_count"],
            "denominator": active_total,
        },
        "nonconverged": {
            "numerator": pooled_counts["nonconverged_count"],
            "denominator": active_total,
        },
        "limit_hit": {
            "numerator": pooled_counts["limit_hit_count"],
            "denominator": active_total,
        },
        "oscillation_window": {
            "numerator": pooled_counts["oscillation_window_count"],
            "denominator": active_total,
        },
        "reference_eligible_window": {
            "numerator": pooled_counts["reference_eligible_window_count"],
            "denominator": active_total,
        },
        "feedback_applied_trace_round": {
            "numerator": pooled_counts["feedback_applied_rounds"],
            "denominator": trace_total,
        },
    }
    for item in pooled_fractions.values():
        item["fraction"] = item["numerator"] / item["denominator"]

    evidence: dict[str, Any] = {
        "schema": "NSE_P1_RETAINED_EVIDENCE_V1",
        "status": "pass",
        "interpretation_gate": "complete_structural_integrity_no_favorable_rate_required",
        "definitions": {
            "active_window": "decision.request_function_players > 0",
            "no_player_window": "decision.request_function_players == 0; excluded from nonconvergence",
            "nonconverged": "active and either inner_stable=false or outer_stable=false",
            "feedback_applied_rate": "feedback_applied eligible trace rounds / eligible trace rounds",
            "inferential_unit": "seed",
            "seed_n": 20,
            "bca": "95% BCa, 10000 resamples, SHA256-derived NSE-P1-BCA-V1|metric seed",
            "timer_resolution": "observed zero thread-CPU values remain zero and are not replaced",
        },
        "integrity": {
            "analyzer_source_sha256": _sha256(Path(__file__)),
            "formal_ready_file_sha256": EXPECTED_READY_FILE_SHA256,
            "formal_ready_document_sha256": EXPECTED_READY_DOCUMENT_SHA256,
            "reference_catalog_sha256": _sha256(catalog_path),
            "binary_sha256": EXPECTED_BINARY_SHA256,
            "run_count": len(seed_rows),
            "run_spec_unique": len(run_spec_hashes) == 20,
            "runs": integrity_runs,
            "reference_totals": reference_totals,
        },
        "seed_rows": seed_rows,
        "seed_level_statistics": metric_summary,
        "pooled_counts": pooled_counts,
        "pooled_fractions": pooled_fractions,
    }

    if output_dir.exists():
        raise RetainedEvidenceError(
            f"refusing to use existing output directory: {output_dir}"
        )
    output_dir.mkdir(parents=True)
    seed_path = output_dir / "p1_retained_seed_rows.csv"
    count_path = output_dir / "p1_retained_window_counts.csv"
    reference_path = output_dir / "p1_reference_build_rows.csv"
    evidence_path = output_dir / "p1_retained_evidence.json"
    _atomic_text(seed_path, _csv_text(seed_rows))
    _atomic_text(count_path, _csv_text(count_rows))
    _atomic_text(reference_path, _csv_text(reference_rows))
    evidence["output_sha256"] = {
        seed_path.name: _sha256(seed_path),
        count_path.name: _sha256(count_path),
        reference_path.name: _sha256(reference_path),
    }
    _atomic_text(
        evidence_path,
        json.dumps(
            evidence, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True
        )
        + "\n",
    )
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        analyze(args.formal_root, args.output_dir)
    except (OSError, json.JSONDecodeError, RetainedEvidenceError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
