"""Result-blind gate analysis for the P5 common-platform protocol pilot."""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping, Sequence

from ..protocol.p5_common_platform import P5_LOADS, P5_MANIFEST_SCHEMA
from ..protocol.p5_determinism import p5_policy_action_sequence_hash
from ..protocol.schema import (
    FORMAL_E1_METHODS,
    P5_COMMON_PLATFORM_MARKER,
    P5_COMMON_PLATFORM_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
)
from ..protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from .formal_inputs import validate_canonical_run


REPORT_SCHEMA = "NSE_P5_COMMON_PLATFORM_GATE_REPORT_V1"
DUPLICATE_SCHEMA = "NSE_P5_DETERMINISM_DUPLICATE_EVIDENCE_V2"
SELECTION_SCHEMA = "NSE_P5_COMMON_PLATFORM_ONLINE_SELECTION_V1"
EXPECTED_RUN_COUNT = 90
EXPECTED_TAPE_COUNT = 9
EXPECTED_REFERENCE_COUNT = 90
TOLERANCE = 1.0e-9
DETERMINISM_TARGET = "P5P01-low-sche_nash"
DETERMINISM_HASH_FIELDS = (
    "workload_semantic_sha256",
    "policy_action_semantic_sha256",
    "terminal_count_semantic_sha256",
    "scientific_result_semantic_sha256",
)


def _number(value: Any, *, nonnegative: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    if not math.isfinite(converted) or (nonnegative and converted < 0.0):
        return None
    return converted


def _expected_identities() -> set[tuple[str, str, str]]:
    return {
        (load, seed, method)
        for load in P5_LOADS
        for seed in P5_COMMON_PLATFORM_SEEDS
        for method in FORMAL_E1_METHODS
    }


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("load", "")),
        str(row.get("seed", "")),
        str(row.get("method", "")),
    )


def _group_arrival_identity(rows: Sequence[Mapping[str, Any]]) -> bool:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("load")), str(row.get("seed")))].append(row)
    if len(groups) != EXPECTED_TAPE_COUNT:
        return False
    for members in groups.values():
        if len(members) != len(FORMAL_E1_METHODS):
            return False
        signatures = {
            (
                member.get("workload_tape_sha256"),
                member.get("arrival_event_sequence_sha256"),
                member.get("arrivals"),
                member.get("tape_static_cpu_work"),
                member.get("cluster_cpu_per_frame"),
                member.get("static_path_allowance_frames"),
                member.get("max_drain_frames"),
                member.get("hard_end_frame"),
            )
            for member in members
        }
        if len(signatures) != 1 or any(
            value is None for value in next(iter(signatures))
        ):
            return False
    return True


def _determinism_pass(evidence: Mapping[str, Any] | None) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    canonical = evidence.get("canonical")
    duplicate = evidence.get("duplicate")
    payload = dict(evidence)
    stored_hash = payload.pop("document_sha256", None)
    return (
        evidence.get("schema_version") == DUPLICATE_SCHEMA
        and isinstance(stored_hash, str)
        and object_hash(payload) == stored_hash
        and evidence.get("target") == DETERMINISM_TARGET
        and evidence.get("predeclared") is True
        and evidence.get("additional_observation") is False
        and isinstance(canonical, Mapping)
        and isinstance(duplicate, Mapping)
        and canonical.get("qc_valid") is True
        and duplicate.get("qc_valid") is True
        and canonical.get("run_spec_hash") == duplicate.get("run_spec_hash")
        and all(
            isinstance(canonical.get(field), str)
            and len(str(canonical[field])) == 64
            and duplicate.get(field) == canonical.get(field)
            for field in DETERMINISM_HASH_FIELDS
        )
    )


def _relative_appendix(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    aggregates = []
    for load in P5_LOADS:
        load_rows = [row for row in rows if row.get("load") == load]
        load_aggregates = []
        for method in FORMAL_E1_METHODS:
            method_rows = [row for row in load_rows if row.get("method") == method]
            throughput = [
                value
                for row in method_rows
                if (
                    value := _number(
                        row.get("paper_throughput_requests_per_ms"), nonnegative=True
                    )
                )
                is not None
            ]
            qpr = [
                value
                for row in method_rows
                if (value := _number(row.get("qpr"), nonnegative=True)) is not None
            ]
            load_aggregates.append(
                {
                    "method": method,
                    "run_count": len(method_rows),
                    "throughput_n": len(throughput),
                    "throughput_mean": fmean(throughput) if throughput else None,
                    "qpr_n": len(qpr),
                    "qpr_mean": fmean(qpr) if qpr else None,
                }
            )
        for metric in ("throughput_mean", "qpr_mean"):
            ranked = sorted(
                [row for row in load_aggregates if row[metric] is not None],
                key=lambda row: (
                    -float(row[metric]),
                    FORMAL_E1_METHODS.index(row["method"]),
                ),
            )
            for rank, row in enumerate(ranked, start=1):
                row[f"{metric}_rank"] = rank
        aggregates.append({"load": load, "methods": load_aggregates})
    return {
        "sealed_after_conditions_1_to_11": True,
        "excluded_from_pass_fail": True,
        "loads": aggregates,
    }


def evaluate_gate(
    rows: Sequence[Mapping[str, Any]],
    traffic_rows: Sequence[Mapping[str, Any]],
    duplicate_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate only the twelve preregistered method-neutral conditions."""

    identities = [_identity(row) for row in rows]
    expected = _expected_identities()
    duplicate_identities = sorted(
        identity for identity in set(identities) if identities.count(identity) > 1
    )
    runtime_sources = {row.get("runtime_source_commit") for row in rows}
    runtime_binaries = {row.get("runtime_binary_sha256") for row in rows}
    tape_hashes = {row.get("workload_tape_sha256") for row in rows}
    reference_hashes = {row.get("offline_reference_sha256") for row in rows}
    population_pass = (
        len(rows) == EXPECTED_RUN_COUNT
        and set(identities) == expected
        and not duplicate_identities
        and all(row.get("qc_valid") is True for row in rows)
        and all(row.get("identity_pass") is True for row in rows)
        and len(runtime_sources) == 1
        and None not in runtime_sources
        and len(runtime_binaries) == 1
        and None not in runtime_binaries
        and len(tape_hashes) == EXPECTED_TAPE_COUNT
        and None not in tape_hashes
        and len(reference_hashes) == EXPECTED_REFERENCE_COUNT
        and None not in reference_hashes
    )
    traffic_identities = {
        (str(row.get("load")), str(row.get("seed"))) for row in traffic_rows
    }
    expected_traffic_identities = {
        (load, seed) for load in P5_LOADS for seed in P5_COMMON_PLATFORM_SEEDS
    }
    traffic_pass = (
        len(traffic_rows) == EXPECTED_TAPE_COUNT
        and traffic_identities == expected_traffic_identities
        and all(
            row.get("all_preregistered_tapes_reported") is True
            and all(
                _number(row.get(field), nonnegative=True) is not None
                for field in (
                    "measured_request_rate_rps",
                    "arrivals_per_frame_p50",
                    "arrivals_per_frame_p95",
                    "arrivals_per_frame_p99",
                    "arrivals_per_frame_max",
                    "static_cpu_work_rate_per_second",
                    "rho_ideal",
                )
            )
            for row in traffic_rows
        )
    )
    conditions = {
        "condition_1_population_and_identity": population_pass,
        "condition_2_arrival_identity": population_pass
        and _group_arrival_identity(rows),
        "condition_3_conservation": len(rows) == EXPECTED_RUN_COUNT
        and all(row.get("conservation_pass") is True for row in rows),
        "condition_4_fcfs": len(rows) == EXPECTED_RUN_COUNT
        and all(row.get("fcfs_pass") is True for row in rows),
        "condition_5_capacity": len(rows) == EXPECTED_RUN_COUNT
        and all(row.get("capacity_pass") is True for row in rows),
        "condition_6_timing": len(rows) == EXPECTED_RUN_COUNT
        and all(row.get("timing_pass") is True for row in rows),
        "condition_7_metric_identity": len(rows) == EXPECTED_RUN_COUNT
        and all(row.get("metric_identity_pass") is True for row in rows),
        "condition_8_usable_cohort": len(rows) == EXPECTED_RUN_COUNT
        and all(
            isinstance(row.get("fixed_window_completed"), int)
            and not isinstance(row.get("fixed_window_completed"), bool)
            and row["fixed_window_completed"] >= 1
            and (
                _number(row.get("terminal_completion_ratio"), nonnegative=True) or -1.0
            )
            >= 0.95
            for row in rows
        ),
        "condition_9_traffic_interpretation": traffic_pass,
        "condition_10_reference_and_nash_integrity": len(rows) == EXPECTED_RUN_COUNT
        and all(row.get("reference_integrity_pass") is True for row in rows)
        and all(row.get("nash_integrity_pass") is True for row in rows),
        "condition_11_determinism_duplicate": _determinism_pass(duplicate_evidence),
        "condition_12_result_blindness": True,
    }
    qualified = all(conditions.values())
    return {
        "status": (
            "complete_p5_common_platform_pass_formal_preregistration_authorized"
            if qualified
            else "complete_p5_common_platform_failed_formal_sampling_blocked"
        ),
        "population_pass": population_pass,
        "observed_identity_count": len(set(identities)),
        "duplicate_identities": duplicate_identities,
        "conditions": conditions,
        "qualified": qualified,
        "failure_reasons": [name for name, passed in conditions.items() if not passed],
        "formal_preregistration_authorized": qualified,
        "formal_sampling_authorized": False,
        "conditions_1_to_11_decided_before_relative_outcomes": True,
        "relative_outcomes": _relative_appendix(rows),
    }


def _isclose(actual: Any, expected: float | None) -> bool:
    if expected is None:
        return actual is None
    value = _number(actual)
    return value is not None and math.isclose(
        value, expected, rel_tol=0.0, abs_tol=TOLERANCE
    )


def _scientific_result(summary: Mapping[str, Any]) -> dict[str, Any]:
    admission = summary.get("admission")
    admission = admission if isinstance(admission, Mapping) else {}
    return {
        "final_frame": summary.get("final_frame"),
        "arrivals": summary.get("arrivals"),
        "completed": summary.get("completed"),
        "censored": summary.get("censored"),
        "paper_throughput_requests_per_ms": summary.get(
            "paper_throughput_requests_per_ms"
        ),
        "cohort_clearance_throughput_requests_per_ms": summary.get(
            "cohort_clearance_throughput_requests_per_ms"
        ),
        "latency_ms": summary.get("latency_ms"),
        "simulator_internal_cost_total": summary.get("simulator_internal_cost_total"),
        "simulator_internal_cost_per_completed_request": summary.get(
            "simulator_internal_cost_per_completed_request"
        ),
        "qpr": summary.get("qpr"),
        "admission": {
            key: admission.get(key)
            for key in (
                "admitted",
                "waiting",
                "active",
                "queue_peak",
                "queue_area_request_frames",
                "wait_ms",
                "terminal_reason",
            )
        },
    }


def _semantic_hashes(
    summary: Mapping[str, Any], qc: Mapping[str, Any]
) -> dict[str, str | None]:
    observations = qc.get("observations")
    observations = observations if isinstance(observations, Mapping) else {}
    admission_observation = observations.get("p5_admission_protocol")
    admission_observation = (
        admission_observation if isinstance(admission_observation, Mapping) else {}
    )
    reference_observation = observations.get("reference_pairing")
    reference_observation = (
        reference_observation if isinstance(reference_observation, Mapping) else {}
    )
    admission = summary.get("admission")
    admission = admission if isinstance(admission, Mapping) else {}
    terminal_counts = {
        "final_frame": summary.get("final_frame"),
        "arrivals": summary.get("arrivals"),
        "admitted": admission.get("admitted"),
        "waiting": admission.get("waiting"),
        "active": admission.get("active"),
        "completed": summary.get("completed"),
        "censored": summary.get("censored"),
    }
    return {
        "workload_semantic_sha256": admission_observation.get(
            "arrival_event_sequence_sha256"
        ),
        "command_semantic_sha256": reference_observation.get(
            "policy_decision_sequence_sha256"
        ),
        "terminal_count_semantic_sha256": object_hash(terminal_counts),
        "scientific_result_semantic_sha256": object_hash(_scientific_result(summary)),
    }


def _policy_action_semantic_hash(
    run_root: Path,
    result_relative_path: str,
    run_id: str,
) -> str:
    summary_path = run_root / result_relative_path.format(run_id=run_id)
    policy_path = summary_path.with_name("nash_metrics.jsonl.gz")
    if not policy_path.is_file():
        raise ProtocolValidationError(
            f"P5 policy action stream is missing: {policy_path}"
        )
    decisions: list[Mapping[str, Any]] = []
    try:
        with gzip.open(policy_path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                event = json.loads(line)
                if not isinstance(event, Mapping):
                    raise ProtocolValidationError(
                        f"P5 policy line {line_number} is not an object"
                    )
                if event.get("kind") != "window":
                    continue
                decision = event.get("decision")
                if not isinstance(decision, Mapping):
                    raise ProtocolValidationError(
                        f"P5 policy line {line_number} has no decision object"
                    )
                decisions.append(decision)
    except (
        OSError,
        EOFError,
        gzip.BadGzipFile,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ProtocolValidationError(
            f"P5 policy action stream cannot be read: {policy_path}: {exc}"
        ) from exc
    try:
        return p5_policy_action_sequence_hash(decisions)
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc


def _canonical_row(
    manifest: Mapping[str, Any], run: Mapping[str, Any], canonical_root: Path
) -> dict[str, Any]:
    run_id = str(run["run_id"])
    run_dir = canonical_root / run_id
    result_relative_path = str(
        manifest.get("execution", {}).get(
            "result_relative_path", "reviewer_records/{run_id}/summary.json"
        )
    )
    qc = validate_canonical_run(
        run,
        run_dir,
        expected_manifest_hash=str(manifest["manifest_hash"]),
        result_relative_path=result_relative_path,
    )
    summary_path = run_dir / result_relative_path.format(run_id=run_id)
    summary = read_json(summary_path)
    if not isinstance(summary, Mapping):
        raise ProtocolValidationError(f"P5 summary is not an object: {summary_path}")
    observations = qc.get("observations")
    observations = observations if isinstance(observations, Mapping) else {}
    admission_observation = observations.get("p5_admission_protocol")
    admission_observation = (
        admission_observation if isinstance(admission_observation, Mapping) else {}
    )
    reference_observation = observations.get("reference_pairing")
    reference_observation = (
        reference_observation if isinstance(reference_observation, Mapping) else {}
    )
    nash_observation = observations.get("nash_runtime_contract")
    nash_observation = nash_observation if isinstance(nash_observation, Mapping) else {}
    admission = summary.get("admission")
    admission = admission if isinstance(admission, Mapping) else {}
    fixed = summary.get("fixed_observation_window")
    fixed = fixed if isinstance(fixed, Mapping) else {}
    latency = summary.get("drained_arrival_cohort", {})
    latency = latency if isinstance(latency, Mapping) else {}
    latency = latency.get("latency_ms")
    latency = latency if isinstance(latency, Mapping) else {}
    fixed_completed = fixed.get("completed")
    paper_throughput = summary.get("paper_throughput_requests_per_ms")
    cost_per_completed = summary.get("simulator_internal_cost_per_completed_request")
    expected_qpr = (
        float(paper_throughput) / (float(latency["mean"]) * float(cost_per_completed))
        if _number(paper_throughput, nonnegative=True) not in (None, 0.0)
        and _number(latency.get("mean"), nonnegative=True) not in (None, 0.0)
        and _number(cost_per_completed, nonnegative=True) not in (None, 0.0)
        else None
    )
    completed = summary.get("completed")
    final_frame = summary.get("final_frame")
    expected_clearance = (
        float(completed) / float(final_frame)
        if isinstance(completed, int)
        and not isinstance(completed, bool)
        and isinstance(final_frame, int)
        and not isinstance(final_frame, bool)
        and final_frame > 0
        else None
    )
    qc_valid = qc.get("passed") is True and qc.get("classification") == "qc_pass"
    runtime = manifest[P5_COMMON_PLATFORM_MARKER]["runtime_binary"]
    dependency = run.get("reference_dependency")
    dependency = dependency if isinstance(dependency, Mapping) else {}
    workload_tape = run.get("workload_tape")
    workload_tape = workload_tape if isinstance(workload_tape, Mapping) else {}
    semantic_hashes = _semantic_hashes(summary, qc)
    if run.get("method") == "sche_nash":
        semantic_hashes["policy_action_semantic_sha256"] = _policy_action_semantic_hash(
            run_dir,
            result_relative_path,
            run_id,
        )
    conservation_pass = (
        qc_valid
        and admission.get("admitted")
        == admission.get("active", -1) + admission.get("completed", -2)
        and admission.get("waiting", -1) + admission.get("admitted", -2)
        == summary.get("arrivals")
        and summary.get("censored")
        == admission.get("waiting", -1) + admission.get("active", -2)
        and summary.get("censored")
        == summary.get("arrivals", -1) - summary.get("completed", -2)
        and summary.get("admission_drop") == 0
        and summary.get("admission_reject") == 0
        and summary.get("timeout") == 0
    )
    timing_pass = (
        qc_valid
        and isinstance(final_frame, int)
        and final_frame >= 1_000
        and final_frame <= admission.get("hard_end_frame", -1)
        and admission.get("terminal_reason")
        in {"cohort_drained", "hard_drain_deadline"}
    )
    metric_pass = (
        qc_valid
        and _isclose(
            paper_throughput,
            float(fixed_completed) / 1_000.0
            if isinstance(fixed_completed, int)
            and not isinstance(fixed_completed, bool)
            else None,
        )
        and _isclose(
            summary.get("cohort_clearance_throughput_requests_per_ms"),
            expected_clearance,
        )
        and _isclose(summary.get("qpr"), expected_qpr)
    )
    return {
        "run_id": run_id,
        "load": run.get("workload", {}).get("request_freq"),
        "seed": run.get("seed"),
        "method": run.get("method"),
        "qc_valid": qc_valid,
        "identity_pass": True,
        "runtime_source_commit": runtime.get("source_git_commit"),
        "runtime_binary_sha256": runtime.get("sha256"),
        "workload_tape_sha256": workload_tape.get("sha256"),
        "offline_reference_sha256": dependency.get("sha256"),
        "arrival_event_sequence_sha256": admission_observation.get(
            "arrival_event_sequence_sha256"
        ),
        "admission_event_sequence_sha256": admission_observation.get(
            "admission_event_sequence_sha256"
        ),
        "frame_conservation_sequence_sha256": admission_observation.get(
            "frame_conservation_sequence_sha256"
        ),
        "arrivals": summary.get("arrivals"),
        "tape_static_cpu_work": admission.get("tape_static_cpu_work"),
        "cluster_cpu_per_frame": admission.get("cluster_cpu_per_frame"),
        "static_path_allowance_frames": admission.get("static_path_allowance_frames"),
        "max_drain_frames": admission.get("max_drain_frames"),
        "hard_end_frame": admission.get("hard_end_frame"),
        "conservation_pass": conservation_pass,
        "fcfs_pass": qc_valid
        and admission_observation.get("arrival_event_count") == summary.get("arrivals")
        and admission_observation.get("admission_event_count")
        == admission.get("admitted"),
        "capacity_pass": qc_valid
        and admission.get("active_request_limit") == 100
        and (
            _number(
                admission_observation.get("maximum_active_requests"), nonnegative=True
            )
            or 0.0
        )
        <= 100.0,
        "timing_pass": timing_pass,
        "metric_identity_pass": metric_pass,
        "fixed_window_completed": fixed_completed,
        "terminal_completion_ratio": summary.get("completion_ratio"),
        "reference_integrity_pass": qc_valid
        and reference_observation.get("method") == run.get("method"),
        "nash_integrity_pass": qc_valid
        and (
            run.get("method") != "sche_nash"
            or (
                nash_observation.get("strict_eq15_ready") is True
                and nash_observation.get("stream_contract_ready") is True
            )
        ),
        "paper_throughput_requests_per_ms": paper_throughput,
        "qpr": summary.get("qpr"),
        **semantic_hashes,
        "arrival_per_frame": admission_observation.get("arrival_per_frame"),
        "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
        "summary_sha256": file_hash(summary_path),
    }


def _traffic_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("load")), str(row.get("seed")))].append(row)
    output = []
    for load in P5_LOADS:
        for seed in P5_COMMON_PLATFORM_SEEDS:
            members = grouped.get((load, seed), [])
            representative = members[0] if members else {}
            per_frame = representative.get("arrival_per_frame")
            per_frame = per_frame if isinstance(per_frame, Mapping) else {}
            work = _number(representative.get("tape_static_cpu_work"), nonnegative=True)
            capacity = _number(
                representative.get("cluster_cpu_per_frame"), nonnegative=True
            )
            output.append(
                {
                    "load": load,
                    "seed": seed,
                    "all_preregistered_tapes_reported": len(members)
                    == len(FORMAL_E1_METHODS),
                    "measured_request_rate_rps": representative.get("arrivals"),
                    "arrivals_per_frame_p50": per_frame.get("p50"),
                    "arrivals_per_frame_p95": per_frame.get("p95"),
                    "arrivals_per_frame_p99": per_frame.get("p99"),
                    "arrivals_per_frame_max": per_frame.get("max"),
                    "static_cpu_work_rate_per_second": work,
                    "rho_ideal": (
                        work / (capacity * 1_000.0)
                        if work is not None and capacity not in (None, 0.0)
                        else None
                    ),
                }
            )
    return output


def _validate_ready_manifest(path: Path) -> dict[str, Any]:
    manifest = load_and_validate_manifest(path)
    marker = manifest.get(P5_COMMON_PLATFORM_MARKER)
    if (
        not isinstance(marker, Mapping)
        or marker.get("schema_version") != P5_MANIFEST_SCHEMA
        or manifest.get("phase") != "pilot"
        or manifest.get("formal_results_eligible") is not False
        or manifest.get("all_tapes_bound") is not True
        or manifest.get("all_references_bound") is not True
        or manifest.get("all_faasrank_models_bound") is not True
        or len(manifest.get("runs", ())) != EXPECTED_RUN_COUNT
    ):
        raise ProtocolValidationError(
            "P5 analysis requires the complete tape/reference-bound pilot manifest"
        )
    return manifest


def _selection_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for ordinal, run in enumerate(manifest["runs"], start=1):
        dependency = run["reference_dependency"]
        rows.append(
            {
                "ordinal": ordinal,
                "execution_order": "load_major_then_seed_major_then_method_ordinal",
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "load": run["workload"]["request_freq"],
                "seed": run["seed"],
                "method": run["method"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": dependency["sha256"],
            }
        )
    return rows


def build_online_selection(manifest_path: Path, canonical_root: Path) -> dict[str, Any]:
    """Freeze the exact P5 population without reading a result or metric."""

    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    if canonical_root.parent.exists():
        raise ProtocolValidationError(
            "P5 online result parent must not exist at selection freeze"
        )
    report: dict[str, Any] = {
        "schema_version": SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": "frozen_before_online_execution",
        "online_results_present_at_freeze": False,
        "canonical_parent_present_at_freeze": False,
        "pilot_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "canonical_root": str(canonical_root),
        "execution_order": "load_major_then_seed_major_then_method_ordinal",
        "run_count": EXPECTED_RUN_COUNT,
        "result_conditioned_seed_method_or_run_selection": False,
        "all_valid_runs_retained": True,
        "technical_retry_only": True,
        "scientific_outcome_retryable": False,
        "relative_performance_excluded_from_gate": True,
        "analysis_contract": {
            "path": str(Path(__file__).resolve()),
            "sha256": file_hash(Path(__file__).resolve()),
            "gate_condition_count": 12,
            "conditions_1_to_11_before_relative_appendix": True,
        },
        "runs": _selection_rows(manifest),
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_online_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite P5 online selection")
    report = build_online_selection(manifest_path, canonical_root)
    write_json_atomic(output_path, report)
    return report


def _validate_selection(
    selection_path: Path,
    manifest_path: Path,
    canonical_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    selection = read_json(selection_path)
    if not isinstance(selection, dict):
        raise ProtocolValidationError("P5 selection is not an object")
    stored = selection.get("document_sha256")
    payload = dict(selection)
    payload.pop("document_sha256", None)
    contract = selection.get("analysis_contract")
    frozen_manifest = selection.get("pilot_manifest")
    if (
        not isinstance(stored, str)
        or object_hash(payload) != stored
        or selection.get("schema_version") != SELECTION_SCHEMA
        or selection.get("status") != "frozen_before_online_execution"
        or selection.get("online_results_present_at_freeze") is not False
        or selection.get("canonical_parent_present_at_freeze") is not False
        or selection.get("result_conditioned_seed_method_or_run_selection") is not False
        or selection.get("all_valid_runs_retained") is not True
        or selection.get("technical_retry_only") is not True
        or selection.get("scientific_outcome_retryable") is not False
        or selection.get("relative_performance_excluded_from_gate") is not True
        or selection.get("execution_order")
        != "load_major_then_seed_major_then_method_ordinal"
        or selection.get("run_count") != EXPECTED_RUN_COUNT
        or not isinstance(contract, Mapping)
        or Path(str(contract.get("path", ""))).resolve() != Path(__file__).resolve()
        or contract.get("sha256") != file_hash(Path(__file__).resolve())
        or contract.get("gate_condition_count") != 12
        or contract.get("conditions_1_to_11_before_relative_appendix") is not True
        or not isinstance(frozen_manifest, Mapping)
        or Path(str(frozen_manifest.get("path", ""))).resolve()
        != manifest_path.resolve()
        or frozen_manifest.get("manifest_hash") != manifest.get("manifest_hash")
        or frozen_manifest.get("file_sha256") != file_hash(manifest_path)
        or Path(str(selection.get("canonical_root", ""))).resolve()
        != canonical_root.resolve()
        or selection.get("runs") != _selection_rows(manifest)
    ):
        raise ProtocolValidationError("P5 selection no longer matches inputs")
    return selection


def validate_online_selection(
    selection_path: Path, manifest_path: Path, canonical_root: Path
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    return _validate_selection(
        selection_path.resolve(), manifest_path, canonical_root, manifest
    )


def build_duplicate_evidence(
    manifest_path: Path,
    canonical_root: Path,
    duplicate_root: Path,
) -> dict[str, Any]:
    """Bind the predeclared duplicate to semantic, timing-free result hashes."""

    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    duplicate_root = duplicate_root.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    targets = [
        run
        for run in manifest["runs"]
        if run.get("seed") == "P5P01"
        and run.get("workload", {}).get("request_freq") == "low"
        and run.get("method") == "sche_nash"
    ]
    if len(targets) != 1:
        raise ProtocolValidationError("P5 determinism target is not unique")
    run = targets[0]
    canonical = _canonical_row(manifest, run, canonical_root)
    run_id = str(run["run_id"])
    duplicate_qc_path = duplicate_root / "qc_report.json"
    result_relative_path = str(
        manifest.get("execution", {}).get(
            "result_relative_path", "reviewer_records/{run_id}/summary.json"
        )
    )
    duplicate_summary_path = duplicate_root / result_relative_path.format(run_id=run_id)
    duplicate_qc = read_json(duplicate_qc_path)
    duplicate_summary = read_json(duplicate_summary_path)
    if (
        not isinstance(duplicate_qc, Mapping)
        or duplicate_qc.get("passed") is not True
        or duplicate_qc.get("classification") != "qc_pass"
        or not isinstance(duplicate_summary, Mapping)
        or duplicate_qc.get("result_sha256") != file_hash(duplicate_summary_path)
    ):
        raise ProtocolValidationError("P5 duplicate does not have matching passing QC")
    canonical_hashes = {
        "qc_valid": True,
        "run_spec_hash": run["run_spec_hash"],
        **{field: canonical.get(field) for field in DETERMINISM_HASH_FIELDS},
    }
    duplicate_hashes = {
        "qc_valid": True,
        "run_spec_hash": run["run_spec_hash"],
        **_semantic_hashes(duplicate_summary, duplicate_qc),
    }
    duplicate_hashes["policy_action_semantic_sha256"] = _policy_action_semantic_hash(
        duplicate_root,
        result_relative_path,
        run_id,
    )
    for label, hashes in (
        ("canonical", canonical_hashes),
        ("duplicate", duplicate_hashes),
    ):
        if any(
            not isinstance(hashes.get(field), str) or len(str(hashes[field])) != 64
            for field in DETERMINISM_HASH_FIELDS
        ):
            raise ProtocolValidationError(
                f"P5 {label} lacks complete determinism semantic hashes"
            )
    evidence: dict[str, Any] = {
        "schema_version": DUPLICATE_SCHEMA,
        "created_at": utc_now(),
        "target": DETERMINISM_TARGET,
        "predeclared": True,
        "additional_observation": False,
        "canonical": canonical_hashes,
        "duplicate": duplicate_hashes,
        "receipts": {
            "manifest_hash": manifest["manifest_hash"],
            "canonical_qc_sha256": canonical["qc_report_sha256"],
            "canonical_summary_sha256": canonical["summary_sha256"],
            "duplicate_qc_sha256": file_hash(duplicate_qc_path),
            "duplicate_summary_sha256": file_hash(duplicate_summary_path),
        },
    }
    evidence["document_sha256"] = object_hash(evidence)
    return evidence


def write_duplicate_evidence(
    manifest_path: Path,
    canonical_root: Path,
    duplicate_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite P5 duplicate evidence")
    evidence = build_duplicate_evidence(manifest_path, canonical_root, duplicate_root)
    write_json_atomic(output_path, evidence)
    return evidence


def analyze(
    manifest_path: Path,
    canonical_root: Path,
    duplicate_evidence_path: Path,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    duplicate_evidence_path = duplicate_evidence_path.resolve()
    manifest = _validate_ready_manifest(manifest_path)
    rows = [_canonical_row(manifest, run, canonical_root) for run in manifest["runs"]]
    traffic_rows = _traffic_rows(rows)
    duplicate_evidence = read_json(duplicate_evidence_path)
    if not isinstance(duplicate_evidence, Mapping):
        raise ProtocolValidationError("P5 duplicate evidence is not an object")
    gate = evaluate_gate(rows, traffic_rows, duplicate_evidence)
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": gate["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "pilot_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "canonical_root": str(canonical_root),
        "duplicate_evidence": {
            "path": str(duplicate_evidence_path),
            "file_sha256": file_hash(duplicate_evidence_path),
        },
        "gate": copy.deepcopy(manifest[P5_COMMON_PLATFORM_MARKER]["gate"]),
        "run_protocol_evidence": rows,
        "traffic_interpretation": traffic_rows,
        "gate_result": gate,
        "run_count": len(rows),
        "formal_preregistration_authorized": gate["formal_preregistration_authorized"],
        "formal_sampling_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_analysis(
    manifest_path: Path,
    canonical_root: Path,
    duplicate_evidence_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite P5 gate report")
    report = analyze(manifest_path, canonical_root, duplicate_evidence_path)
    write_json_atomic(output_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze_parser = commands.add_parser("freeze-selection")
    freeze_parser.add_argument("manifest", type=Path)
    freeze_parser.add_argument("canonical_root", type=Path)
    freeze_parser.add_argument("output", type=Path)
    validate_parser = commands.add_parser("validate-selection")
    validate_parser.add_argument("selection", type=Path)
    validate_parser.add_argument("manifest", type=Path)
    validate_parser.add_argument("canonical_root", type=Path)
    duplicate_parser = commands.add_parser("duplicate-evidence")
    duplicate_parser.add_argument("manifest", type=Path)
    duplicate_parser.add_argument("canonical_root", type=Path)
    duplicate_parser.add_argument("duplicate_root", type=Path)
    duplicate_parser.add_argument("output", type=Path)
    analyze_parser = commands.add_parser("analyze")
    analyze_parser.add_argument("manifest", type=Path)
    analyze_parser.add_argument("canonical_root", type=Path)
    analyze_parser.add_argument("duplicate_evidence", type=Path)
    analyze_parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "freeze-selection":
        write_online_selection(args.manifest, args.canonical_root, args.output)
    elif args.command == "validate-selection":
        validate_online_selection(args.selection, args.manifest, args.canonical_root)
    elif args.command == "duplicate-evidence":
        write_duplicate_evidence(
            args.manifest,
            args.canonical_root,
            args.duplicate_root,
            args.output,
        )
    else:
        write_analysis(
            args.manifest,
            args.canonical_root,
            args.duplicate_evidence,
            args.output,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
