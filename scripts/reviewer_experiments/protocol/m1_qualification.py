"""Analyze the fixed M1 screen and derive the selected qualification shard."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from statistics import fmean
from typing import Any

from ..analysis.formal_inputs import validate_canonical_run
from .pairing import REPORT_SCHEMA as PAIRING_REPORT_SCHEMA

from .m1_development import (
    M1_BASELINE_METHODS,
    M1_DEVELOPMENT_SEEDS,
    M1_LOADS,
    M1_OPERATIONAL_CANDIDATES,
    M1_TOPOLOGIES,
    _matrix_summary,
)
from .matrix import _reference_build_dependencies
from .schema import (
    FORMAL_E1_METHODS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


SCREEN_SELECTION_SCHEMA = "NSE_M1_CANDIDATE_SELECTION_V1"
QUALIFICATION_REPORT_SCHEMA = "NSE_M1_QUALIFICATION_REPORT_V1"


def _canonical_summary_path(canonical_root: Path, run_id: str) -> Path:
    return canonical_root / run_id / "reviewer_records" / run_id / "summary.json"


def _screen_metrics(summary: dict[str, Any]) -> tuple[float, float, float, float]:
    fixed = summary.get("fixed_observation_window")
    drained = summary.get("drained_arrival_cohort")
    if not isinstance(fixed, dict) or not isinstance(drained, dict):
        raise ProtocolValidationError("screen summary lacks explicit cohort metrics")
    throughput_rps = fixed.get("throughput_requests_per_second")
    latency = drained.get("latency_ms", {}).get("mean")
    cost = summary.get("simulator_internal_cost_per_completed_request")
    for name, value in (
        ("throughput", throughput_rps),
        ("latency", latency),
        ("cost", cost),
    ):
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) <= 0.0
        ):
            raise ProtocolValidationError(
                f"screen summary has non-applicable {name}; candidate screen cannot rank it"
            )
    throughput = float(throughput_rps) / 1000.0
    latency_value = float(latency)
    cost_value = float(cost)
    qpr = throughput / (latency_value * cost_value)
    return throughput, qpr, latency_value, cost_value


def _choose_candidate(
    aggregates: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in aggregates:
        by_cell.setdefault((row["load"], row["topology"]), []).append(row)
    expected_cells = set((load, topology) for load in M1_LOADS for topology in M1_TOPOLOGIES)
    if set(by_cell) != expected_cells:
        raise ProtocolValidationError("candidate aggregates do not cover all six E1 cells")

    scores: list[dict[str, Any]] = []
    for candidate in M1_OPERATIONAL_CANDIDATES:
        ratios: list[float] = []
        dual_wins = 0
        for cell in sorted(expected_cells):
            rows = by_cell[cell]
            if {row["candidate"] for row in rows} != set(M1_OPERATIONAL_CANDIDATES):
                raise ProtocolValidationError(f"candidate aggregate is incomplete for {cell}")
            current = next(row for row in rows if row["candidate"] == candidate)
            max_throughput = max(row["mean_throughput_requests_per_ms"] for row in rows)
            max_qpr = max(row["mean_qpr"] for row in rows)
            throughput_ratio = current["mean_throughput_requests_per_ms"] / max_throughput
            qpr_ratio = current["mean_qpr"] / max_qpr
            ratios.extend((throughput_ratio, qpr_ratio))
            if math.isclose(throughput_ratio, 1.0, rel_tol=0.0, abs_tol=1e-12) and math.isclose(
                qpr_ratio, 1.0, rel_tol=0.0, abs_tol=1e-12
            ):
                dual_wins += 1
        scores.append(
            {
                "candidate": candidate,
                "worst_cell_metric_ratio": min(ratios),
                "mean_cell_metric_ratio": fmean(ratios),
                "dual_first_cells": dual_wins,
                "simplicity_order": M1_OPERATIONAL_CANDIDATES.index(candidate),
            }
        )
    scores.sort(
        key=lambda row: (
            -row["worst_cell_metric_ratio"],
            -row["mean_cell_metric_ratio"],
            -row["dual_first_cells"],
            row["simplicity_order"],
        )
    )
    return str(scores[0]["candidate"]), scores


def analyze_m1_candidate_screen(
    manifest_path: Path, canonical_root: Path
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("m1_candidate_screen_shard")
    if not isinstance(marker, dict):
        raise ProtocolValidationError("screen analysis requires an M1 screen shard")

    raw_rows: list[dict[str, Any]] = []
    artifact_receipts: list[dict[str, Any]] = []
    for run in manifest["runs"]:
        run_dir = canonical_root / run["run_id"]
        qc_path = run_dir / "qc_report.json"
        summary_path = _canonical_summary_path(canonical_root, run["run_id"])
        if not qc_path.is_file() or not summary_path.is_file():
            raise ProtocolValidationError(
                f"screen run {run['run_id']} is missing canonical QC or summary"
            )
        qc = read_json(qc_path)
        if not isinstance(qc, dict) or qc.get("passed") is not True:
            raise ProtocolValidationError(f"screen run {run['run_id']} did not pass QC")
        summary_sha = file_hash(summary_path)
        if qc.get("result_sha256") != summary_sha:
            raise ProtocolValidationError(
                f"screen run {run['run_id']} summary differs from its QC receipt"
            )
        summary = read_json(summary_path)
        if (
            not isinstance(summary, dict)
            or summary.get("schema") != "NSE_SUMMARY_V1"
            or summary.get("run_id") != run["run_id"]
            or summary.get("run_complete") is not True
        ):
            raise ProtocolValidationError(f"screen run {run['run_id']} summary is invalid")
        throughput, qpr, latency, cost = _screen_metrics(summary)
        candidate = run["metadata"]["m1_operational_candidate"]
        raw_rows.append(
            {
                "run_id": run["run_id"],
                "seed": run["seed"],
                "candidate": candidate,
                "load": run["workload"]["request_freq"],
                "topology": run["cluster"]["topology"],
                "throughput_requests_per_ms": throughput,
                "qpr": qpr,
                "latency_mean_ms": latency,
                "cost_per_completed_request": cost,
            }
        )
        artifact_receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "qc_report_sha256": file_hash(qc_path),
                "summary_sha256": summary_sha,
            }
        )

    aggregates: list[dict[str, Any]] = []
    for candidate, load, topology in (
        (candidate, load, topology)
        for candidate in M1_OPERATIONAL_CANDIDATES
        for load in M1_LOADS
        for topology in M1_TOPOLOGIES
    ):
        group = [
            row
            for row in raw_rows
            if row["candidate"] == candidate
            and row["load"] == load
            and row["topology"] == topology
        ]
        if len(group) != 5 or {row["seed"] for row in group} != {
            f"D{index:02d}" for index in range(1, 6)
        }:
            raise ProtocolValidationError(
                f"screen group {candidate}/{load}/{topology} is incomplete"
            )
        aggregates.append(
            {
                "candidate": candidate,
                "load": load,
                "topology": topology,
                "n": len(group),
                "mean_throughput_requests_per_ms": fmean(
                    row["throughput_requests_per_ms"] for row in group
                ),
                "mean_qpr": fmean(row["qpr"] for row in group),
                "mean_latency_ms": fmean(row["latency_mean_ms"] for row in group),
                "mean_cost_per_completed_request": fmean(
                    row["cost_per_completed_request"] for row in group
                ),
            }
        )
    selected, scores = _choose_candidate(aggregates)
    receipt: dict[str, Any] = {
        "schema_version": SCREEN_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": "complete_nonformal_candidate_screen",
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "screen_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "development_source_manifest": copy.deepcopy(marker["source_manifest"]),
        "canonical_root": str(canonical_root),
        "selection_rule": {
            "primary": "maximize minimum candidate-relative mean ratio across throughput and QPR in all six cells",
            "secondary": "maximize mean of the same twelve ratios",
            "tertiary": "maximize number of six cells with joint throughput-and-QPR first",
            "final_tie_break": "prefer simpler preregistered candidate order",
            "result_conditioned_seed_removal_or_replacement": False,
        },
        "selected_candidate": selected,
        "candidate_scores": scores,
        "cell_aggregates": aggregates,
        "run_metrics": raw_rows,
        "artifact_receipts": artifact_receipts,
        "run_count": len(raw_rows),
    }
    receipt["document_sha256"] = object_hash(receipt)
    return receipt


def write_m1_candidate_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite an M1 selection receipt")
    receipt = analyze_m1_candidate_screen(manifest_path, canonical_root)
    write_json_atomic(output_path, receipt)
    return receipt


def _load_selection(path: Path) -> dict[str, Any]:
    selection = read_json(path)
    if not isinstance(selection, dict) or selection.get("schema_version") != SCREEN_SELECTION_SCHEMA:
        raise ProtocolValidationError("invalid M1 candidate-selection receipt")
    expected = object_hash(
        {key: value for key, value in selection.items() if key != "document_sha256"}
    )
    if selection.get("document_sha256") != expected:
        raise ProtocolValidationError("M1 candidate-selection receipt hash mismatch")
    candidate = selection.get("selected_candidate")
    if candidate not in M1_OPERATIONAL_CANDIDATES:
        raise ProtocolValidationError("M1 selection names an unknown candidate")
    return selection


def derive_m1_qualification_shard(
    source_path: Path, selection_path: Path
) -> dict[str, Any]:
    source_path = source_path.resolve()
    selection_path = selection_path.resolve()
    source = load_and_validate_manifest(source_path)
    if "m1_development_matrix" not in source:
        raise ProtocolValidationError(
            "M1 qualification requires the complete development matrix"
        )
    selection = _load_selection(selection_path)
    source_receipt = selection.get("development_source_manifest")
    if (
        not isinstance(source_receipt, dict)
        or source_receipt.get("manifest_hash") != source["manifest_hash"]
        or source_receipt.get("file_sha256") != file_hash(source_path)
    ):
        raise ProtocolValidationError(
            "M1 candidate selection does not bind this development manifest"
        )
    candidate = str(selection["selected_candidate"])
    selected = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["method"] in M1_BASELINE_METHODS
        or run.get("metadata", {}).get("m1_operational_candidate") == candidate
    ]
    if len(selected) != 1200:
        raise ProtocolValidationError("M1 qualification source product is incomplete")
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["phase"] = "qualification"
    shard["bank_id"] = "TSCv1.qualification.M1.D01-D20"
    shard["runs"] = selected
    shard["reference_build_dependencies"] = _reference_build_dependencies(selected)
    shard["matrix_summary"] = _matrix_summary(selected)
    shard.pop("m1_development_matrix", None)
    shard["m1_qualification_shard"] = {
        "schema_version": "NSE_M1_QUALIFICATION_SHARD_V1",
        "source_manifest": {
            "path": str(source_path),
            "file_sha256": file_hash(source_path),
            "manifest_hash": source["manifest_hash"],
            "run_count": len(source["runs"]),
        },
        "candidate_selection": {
            "path": str(selection_path),
            "file_sha256": file_hash(selection_path),
            "document_sha256": selection["document_sha256"],
        },
        "selection": {
            "selected_candidate": candidate,
            "methods": list(FORMAL_E1_METHODS),
            "loads": list(M1_LOADS),
            "topologies": list(M1_TOPOLOGIES),
            "seeds": list(M1_DEVELOPMENT_SEEDS),
        },
        "paper_equations_changed": False,
        "run_count": len(selected),
        "cell_count": len({run["cell_id"] for run in selected}),
        "reference_build_count": len(_reference_build_dependencies(selected)),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_m1_qualification_shard(
    source_path: Path, selection_path: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.resolve() in {source_path.resolve(), selection_path.resolve()}:
        raise ProtocolValidationError("M1 qualification output must be a new path")
    shard = derive_m1_qualification_shard(source_path, selection_path)
    write_json_atomic(output_path, shard)
    return shard


def _qualification_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    fixed = summary.get("fixed_observation_window")
    drained = summary.get("drained_arrival_cohort")
    if not isinstance(fixed, dict) or not isinstance(drained, dict):
        raise ProtocolValidationError(
            "qualification summary lacks explicit fixed and drained cohorts"
        )
    throughput_rps = fixed.get("throughput_requests_per_second")
    completion = drained.get("completion_ratio")
    latency = drained.get("latency_ms", {}).get("mean")
    cost = summary.get("simulator_internal_cost_per_completed_request")
    if (
        isinstance(throughput_rps, bool)
        or not isinstance(throughput_rps, (int, float))
        or not math.isfinite(float(throughput_rps))
        or float(throughput_rps) < 0.0
    ):
        raise ProtocolValidationError("qualification throughput is invalid")
    if (
        isinstance(completion, bool)
        or not isinstance(completion, (int, float))
        or not math.isfinite(float(completion))
        or not 0.0 <= float(completion) <= 1.0
    ):
        raise ProtocolValidationError("qualification completion ratio is invalid")
    throughput = float(throughput_rps) / 1000.0
    applicable = all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0
        for value in (throughput, latency, cost)
    )
    qpr = throughput / (float(latency) * float(cost)) if applicable else None
    if qpr is not None and (not math.isfinite(qpr) or qpr <= 0.0):
        applicable = False
        qpr = None
    if applicable:
        reason = None
    elif throughput <= 0.0:
        reason = "nonpositive_throughput"
    elif latency is None or cost is None:
        reason = "no_completed_request_latency_or_cost"
    else:
        reason = "nonpositive_or_nonfinite_latency_or_cost"
    return {
        "throughput_requests_per_ms": throughput,
        "completion_ratio": float(completion),
        "latency_mean_ms": float(latency) if latency is not None else None,
        "cost_per_completed_request": float(cost) if cost is not None else None,
        "qpr_applicable": applicable,
        "qpr": qpr,
        "qpr_non_applicability_reason": reason,
    }


def _aggregate_qualification_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aggregates: list[dict[str, Any]] = []
    for topology in M1_TOPOLOGIES:
        for load in M1_LOADS:
            for method in FORMAL_E1_METHODS:
                group = [
                    row
                    for row in rows
                    if row["topology"] == topology
                    and row["load"] == load
                    and row["method"] == method
                ]
                if len(group) != 20 or {row["seed"] for row in group} != set(
                    M1_DEVELOPMENT_SEEDS
                ):
                    raise ProtocolValidationError(
                        f"qualification group {topology}/{load}/{method} is incomplete"
                    )
                applicable = [row for row in group if row["qpr_applicable"]]
                aggregates.append(
                    {
                        "topology": topology,
                        "load": load,
                        "method": method,
                        "n_total": len(group),
                        "mean_throughput_requests_per_ms": fmean(
                            row["throughput_requests_per_ms"] for row in group
                        ),
                        "mean_completion_ratio": fmean(
                            row["completion_ratio"] for row in group
                        ),
                        "qpr_applicable_n": len(applicable),
                        "qpr_undefined_n": len(group) - len(applicable),
                        "mean_applicable_qpr": (
                            fmean(row["qpr"] for row in applicable)
                            if applicable
                            else None
                        ),
                    }
                )
    return aggregates


def _qualification_cell_decisions(
    aggregates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for topology in M1_TOPOLOGIES:
        for load in M1_LOADS:
            cell = [
                row
                for row in aggregates
                if row["topology"] == topology and row["load"] == load
            ]
            if {row["method"] for row in cell} != set(FORMAL_E1_METHODS):
                raise ProtocolValidationError(
                    f"qualification decision cell {topology}/{load} is incomplete"
                )
            nash = next(row for row in cell if row["method"] == "sche_nash")
            baselines = [row for row in cell if row["method"] != "sche_nash"]
            best_throughput = max(
                baselines, key=lambda row: row["mean_throughput_requests_per_ms"]
            )
            qpr_ranked = sorted(
                [row for row in baselines if row["mean_applicable_qpr"] is not None],
                key=lambda row: row["mean_applicable_qpr"],
                reverse=True,
            )
            best_qpr = qpr_ranked[0] if qpr_ranked else None
            full_qpr_coverage = all(row["qpr_applicable_n"] == 20 for row in cell)
            throughput_first = (
                nash["mean_throughput_requests_per_ms"]
                > best_throughput["mean_throughput_requests_per_ms"]
            )
            qpr_first = bool(
                full_qpr_coverage
                and best_qpr is not None
                and nash["mean_applicable_qpr"] is not None
                and nash["mean_applicable_qpr"] > best_qpr["mean_applicable_qpr"]
            )
            decisions.append(
                {
                    "topology": topology,
                    "load": load,
                    "nash": copy.deepcopy(nash),
                    "best_baseline_throughput": copy.deepcopy(best_throughput),
                    "best_baseline_applicable_qpr": copy.deepcopy(best_qpr),
                    "all_methods_full_qpr_coverage": full_qpr_coverage,
                    "nash_throughput_margin": nash[
                        "mean_throughput_requests_per_ms"
                    ]
                    - best_throughput["mean_throughput_requests_per_ms"],
                    "nash_applicable_qpr_margin": (
                        nash["mean_applicable_qpr"] - best_qpr["mean_applicable_qpr"]
                        if nash["mean_applicable_qpr"] is not None
                        and best_qpr is not None
                        else None
                    ),
                    "nash_throughput_strictly_first": throughput_first,
                    "nash_qpr_strictly_first": qpr_first,
                    "dual_metric_gate_passed": throughput_first and qpr_first,
                }
            )
    return decisions


def analyze_m1_qualification(
    manifest_path: Path, canonical_root: Path, pairing_audit_path: Path
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    pairing_audit_path = pairing_audit_path.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("m1_qualification_shard")
    if (
        not isinstance(marker, dict)
        or manifest.get("phase") != "qualification"
        or manifest.get("formal_results_eligible") is not False
        or len(manifest["runs"]) != 1200
    ):
        raise ProtocolValidationError(
            "qualification analysis requires the complete nonformal M1 shard"
        )
    pairing = read_json(pairing_audit_path)
    if (
        not isinstance(pairing, dict)
        or pairing.get("schema") != PAIRING_REPORT_SCHEMA
        or pairing.get("passed") is not True
        or pairing.get("run_count") != 1200
        or pairing.get("protocol_manifest_sha256") != manifest["manifest_hash"]
        or Path(str(pairing.get("canonical_root", ""))).resolve() != canonical_root
    ):
        raise ProtocolValidationError(
            "qualification analysis requires the passing paired-environment audit"
        )

    rows: list[dict[str, Any]] = []
    artifact_receipts: list[dict[str, Any]] = []
    result_relative_path = manifest["execution"]["result_relative_path"]
    for run in manifest["runs"]:
        directory = canonical_root / run["run_id"]
        qc = validate_canonical_run(
            run,
            directory,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        result_path = directory / result_relative_path.format(run_id=run["run_id"])
        summary = read_json(result_path)
        if (
            not isinstance(summary, dict)
            or summary.get("schema") != "NSE_SUMMARY_V1"
            or summary.get("run_id") != run["run_id"]
            or summary.get("run_complete") is not True
            or qc.get("result_sha256") != file_hash(result_path)
        ):
            raise ProtocolValidationError(
                f"qualification summary is invalid for {run['run_id']}"
            )
        metrics = _qualification_metrics(summary)
        rows.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "seed": run["seed"],
                "topology": run["cluster"]["topology"],
                "load": run["workload"]["request_freq"],
                "method": run["method"],
                **metrics,
            }
        )
        artifact_receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "audit_manifest_sha256": file_hash(directory / "manifest.json"),
                "qc_report_sha256": file_hash(directory / "qc_report.json"),
                "summary_sha256": file_hash(result_path),
            }
        )
    aggregates = _aggregate_qualification_rows(rows)
    decisions = _qualification_cell_decisions(aggregates)
    passed = all(item["dual_metric_gate_passed"] for item in decisions)
    receipt: dict[str, Any] = {
        "schema_version": QUALIFICATION_REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": (
            "complete_qualification_passed"
            if passed
            else "complete_qualification_failed_gate"
        ),
        "qualification_gate_passed": passed,
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "selected_candidate": marker["selection"]["selected_candidate"],
        "protocol_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "canonical_root": str(canonical_root),
        "pairing_audit": {
            "path": str(pairing_audit_path),
            "file_sha256": file_hash(pairing_audit_path),
            "passed": True,
        },
        "gate_definition": {
            "run_level_qpr": "throughput[requests/ms]/(cost_per_completed_request*drained_mean_latency_ms)",
            "fixed_seed_count": 20,
            "all_valid_runs_retained": True,
            "full_qpr_coverage_required": True,
            "throughput_rule": "NSESche arithmetic mean strictly exceeds every baseline in each cell",
            "qpr_rule": "NSESche arithmetic mean of 20 applicable run-level QPR values strictly exceeds every baseline in each cell",
            "result_conditioned_seed_removal_or_replacement": False,
        },
        "run_count": len(rows),
        "cell_count": len(decisions),
        "cell_decisions": decisions,
        "aggregates": aggregates,
        "run_metrics": rows,
        "artifact_receipts": artifact_receipts,
    }
    receipt["document_sha256"] = object_hash(receipt)
    return receipt


def write_m1_qualification_report(
    manifest_path: Path,
    canonical_root: Path,
    pairing_audit_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite an M1 qualification report")
    report = analyze_m1_qualification(
        manifest_path, canonical_root, pairing_audit_path
    )
    write_json_atomic(output_path, report)
    return report
