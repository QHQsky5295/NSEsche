"""Fresh D66--D70 strict-initialization development protocol.

G2 changes only construction of Algorithm 1's feasible initial assignment.
Every subsequent player update remains a strict published-utility best
response.  This module freezes the complete candidate/baseline product and the
result-blind selection and feasibility gates before any D66 workload capture.
"""

from __future__ import annotations

import copy
import math
from itertools import product
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping

from ..analysis.formal_inputs import validate_canonical_run
from .g1_corrected_runtime import _runtime_execution
from .m1_completion_guard import _runtime_receipt
from .m1_development import _bind_candidate, _matrix_summary
from .m1_qualification import _canonical_summary_path, _screen_metrics
from .matrix import (
    _base_workload,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    load_protocol_config,
)
from .schema import (
    FORMAL_E1_METHODS,
    G2_INITIALIZATION_SAMPLE_POLICY,
    G2_INITIALIZATION_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G2_INITIALIZATION_CANDIDATES = (
    "ready_order",
    "ready_warm_init",
    "ready_finish_init",
)
G2_INITIALIZATION_LOADS = ("low", "middle", "high")
G2_INITIALIZATION_TOPOLOGIES = ("homogeneous", "heterogeneous")
G2_INITIALIZATION_BASELINES = tuple(
    method for method in FORMAL_E1_METHODS if method != "sche_nash"
)
G2_INITIALIZATION_SELECTION_SCHEMA = "NSE_G2_STRICT_INITIALIZATION_SELECTION_V1"
G2_DYNAMIC_FINISH_SCORE = (
    "startup_remaining+runnable+starting_resident+pressure+"
    "state_so_far_assigned_request_count"
)
G2_INITIALIZATION_SEMANTICS = {
    "ready_order": "sequential_existing_candidate_selection",
    "ready_warm_init": (
        "running_warm_if_available_min_dynamic_finish_then_higher_utility_"
        "then_node_id_else_strict_utility"
    ),
    "ready_finish_init": "minimum_dynamic_finish_then_higher_utility_then_node_id",
}


def _candidate_cell(
    candidate: str, load: str, topology: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G2INIT.sche_nash.{candidate}.{load}.{topology}.n{node_count}",
        "sche_nash",
        _base_workload(load, topology, "mixed"),
        {"node_count": node_count, "topology": topology},
        metadata={
            "m1_operational_candidate": candidate,
            "g2_initialization_role": "strict_initialization_candidate",
            "paper_equations_changed": False,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
            "initialization_only_change": candidate != "ready_order",
        },
    )


def _baseline_cell(method: str, node_count: int) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G2INIT.{method}.low.homogeneous.n{node_count}",
        method,
        _base_workload("low", "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={"g2_initialization_role": "homogeneous_low_baseline_control"},
    )


def build_g2_initialization_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact non-formal 90-candidate plus 45-baseline product."""

    config = load_protocol_config(config_path)
    runtime = _runtime_receipt(simulator_exe, source_git_commit)
    node_count = int(config["matrix_defaults"]["base_node_count"])
    common_hpa_hash = object_hash(config["common_hpa"])
    repository = Path(__file__).resolve().parents[3]
    profiles = load_profile_set(config["workload_profiles"], repository=repository)
    profile_bindings = {
        load: profile.to_binding() for load, profile in profiles.items()
    }
    workload_profile_set = {
        "schema_version": config["workload_profiles"]["schema_version"],
        "profile_set_id": config["workload_profiles"]["profile_set_id"],
        "formal_required": True,
        "profiles": profile_bindings,
    }

    candidate_cells = [
        _candidate_cell(candidate, load, topology, node_count)
        for candidate, load, topology in product(
            G2_INITIALIZATION_CANDIDATES,
            G2_INITIALIZATION_LOADS,
            G2_INITIALIZATION_TOPOLOGIES,
        )
    ]
    baseline_cells = [
        _baseline_cell(method, node_count) for method in G2_INITIALIZATION_BASELINES
    ]
    runs: list[dict[str, Any]] = []
    for cell in candidate_cells:
        candidate = str(cell["metadata"]["m1_operational_candidate"])
        for seed in G2_INITIALIZATION_SEEDS:
            run = _make_run(
                config,
                cell,
                seed,
                common_hpa_hash,
                profiles[cell["workload"]["request_freq"]],
            )
            _bind_candidate(run, candidate)
            runs.append(run)
    for cell in baseline_cells:
        for seed in G2_INITIALIZATION_SEEDS:
            runs.append(
                _make_run(
                    config,
                    cell,
                    seed,
                    common_hpa_hash,
                    profiles["low"],
                )
            )

    selection_rule = {
        "primary": (
            "maximize minimum candidate/control mean ratio across throughput "
            "and QPR in all six cells"
        ),
        "secondary": "maximize mean of the same twelve candidate/control ratios",
        "tertiary": "maximize six-cell joint throughput-and-QPR first places",
        "final_tie_break": "prefer declared C0-C1-C2 simplicity order",
        "result_conditioned_seed_removal_or_replacement": False,
    }
    baseline_gate = {
        "cell": {"load": "low", "topology": "homogeneous", "node_count": 20},
        "metrics": ["mean_throughput_requests_per_ms", "mean_qpr"],
        "relation": "selected_candidate_strictly_greater_than_every_baseline",
        "all_nine_baselines_required": True,
        "complete_qpr_required": True,
        "old_pdf_alignment_is_selection_criterion": False,
    }
    marker = {
        "schema_version": "NSE_G2_STRICT_INITIALIZATION_DEVELOPMENT_V1",
        "purpose": "fresh-bank strict-Eq.15 feasible-initialization successor screen",
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "utility_guard_relative_regret": 0.0,
        "initialization_scope": "Algorithm_1_line_8_feasible_start_only",
        "dynamic_finish_score": G2_DYNAMIC_FINISH_SCORE,
        "candidates": list(G2_INITIALIZATION_CANDIDATES),
        "control_candidate": "ready_order",
        "baseline_methods": list(G2_INITIALIZATION_BASELINES),
        "loads": list(G2_INITIALIZATION_LOADS),
        "topologies": list(G2_INITIALIZATION_TOPOLOGIES),
        "development_seeds": list(G2_INITIALIZATION_SEEDS),
        "selection_rule": selection_rule,
        "baseline_feasibility_gate": baseline_gate,
        "runtime_binary": runtime,
        "workload_tape_count": 30,
        "candidate_run_count": 90,
        "baseline_run_count": 45,
        "run_count": len(runs),
        "cell_count": len(candidate_cells) + len(baseline_cells),
        "reference_build_count": len(_reference_build_dependencies(runs)),
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.G2.strict-initialization.D66-D70",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G2_INITIALIZATION_SAMPLE_POLICY,
            "all_seeds": list(G2_INITIALIZATION_SEEDS),
            "selected_seeds": list(G2_INITIALIZATION_SEEDS),
            "paired_across_methods": True,
            "result_conditioned_extension": False,
        },
        "method_versions": copy.deepcopy(
            config["manifest_governance"]["method_versions"]
        ),
        "old_pdf_alignment": copy.deepcopy(
            config["manifest_governance"]["old_pdf_alignment"]
        ),
        "runtime_identity_policy": copy.deepcopy(
            config["manifest_governance"]["runtime_identity"]
        ),
        "seed_stage": "development",
        "ci_extension_requires_trigger": False,
        "common_hpa": copy.deepcopy(config["common_hpa"]),
        "common_hpa_hash": common_hpa_hash,
        "workload_profile_set": workload_profile_set,
        "workload_profile_set_hash": object_hash(workload_profile_set),
        "simulation": copy.deepcopy(config["simulation"]),
        "execution": _runtime_execution(config["execution"], runtime),
        "qc": copy.deepcopy(config["qc"]),
        "matrix_summary": _matrix_summary(runs),
        "runs": runs,
        "reference_build_dependencies": _reference_build_dependencies(runs),
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": [],
        "g2_strict_initialization_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g2_initialization_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError(
            "refusing to overwrite G2 initialization manifest"
        )
    manifest = build_g2_initialization_manifest(
        simulator_exe, source_git_commit, config_path
    )
    write_json_atomic(output_path, manifest)
    return manifest


def _choose_g2_candidate(
    aggregates: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in aggregates:
        by_cell.setdefault((row["load"], row["topology"]), []).append(row)
    expected_cells = set(product(G2_INITIALIZATION_LOADS, G2_INITIALIZATION_TOPOLOGIES))
    if set(by_cell) != expected_cells:
        raise ProtocolValidationError(
            "G2 candidate aggregates do not cover all six cells"
        )

    scores: list[dict[str, Any]] = []
    for candidate in G2_INITIALIZATION_CANDIDATES:
        ratios: list[float] = []
        dual_first = 0
        for cell in sorted(expected_cells):
            rows = by_cell[cell]
            if {row["candidate"] for row in rows} != set(G2_INITIALIZATION_CANDIDATES):
                raise ProtocolValidationError(
                    f"G2 candidate aggregate is incomplete for {cell}"
                )
            control = next(row for row in rows if row["candidate"] == "ready_order")
            current = next(row for row in rows if row["candidate"] == candidate)
            for metric in (
                "mean_throughput_requests_per_ms",
                "mean_qpr",
            ):
                denominator = float(control[metric])
                numerator = float(current[metric])
                if not all(
                    math.isfinite(value) and value > 0.0
                    for value in (denominator, numerator)
                ):
                    raise ProtocolValidationError(
                        "G2 candidate metric is not applicable"
                    )
                ratios.append(numerator / denominator)
            if all(
                math.isclose(
                    float(current[metric]),
                    max(float(row[metric]) for row in rows),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
                for metric in (
                    "mean_throughput_requests_per_ms",
                    "mean_qpr",
                )
            ):
                dual_first += 1
        scores.append(
            {
                "candidate": candidate,
                "worst_control_relative_ratio": min(ratios),
                "mean_control_relative_ratio": fmean(ratios),
                "dual_first_cells": dual_first,
                "simplicity_order": G2_INITIALIZATION_CANDIDATES.index(candidate),
            }
        )
    scores.sort(
        key=lambda row: (
            -row["worst_control_relative_ratio"],
            -row["mean_control_relative_ratio"],
            -row["dual_first_cells"],
            row["simplicity_order"],
        )
    )
    return str(scores[0]["candidate"]), scores


def _evaluate_baseline_gate(
    selected_candidate: str,
    candidate_aggregates: list[dict[str, Any]],
    baseline_aggregates: list[dict[str, Any]],
) -> tuple[bool, list[dict[str, Any]]]:
    selected_rows = [
        row
        for row in candidate_aggregates
        if row["candidate"] == selected_candidate
        and row["load"] == "low"
        and row["topology"] == "homogeneous"
    ]
    if len(selected_rows) != 1:
        raise ProtocolValidationError(
            "G2 selected low-load candidate aggregate is missing"
        )
    if {row["method"] for row in baseline_aggregates} != set(
        G2_INITIALIZATION_BASELINES
    ):
        raise ProtocolValidationError("G2 baseline aggregate product is incomplete")
    selected = selected_rows[0]
    rows: list[dict[str, Any]] = []
    for method in G2_INITIALIZATION_BASELINES:
        baseline = next(row for row in baseline_aggregates if row["method"] == method)
        throughput_margin = float(selected["mean_throughput_requests_per_ms"]) - float(
            baseline["mean_throughput_requests_per_ms"]
        )
        qpr_margin = float(selected["mean_qpr"]) - float(baseline["mean_qpr"])
        rows.append(
            {
                "baseline": method,
                "throughput_margin_requests_per_ms": throughput_margin,
                "qpr_margin": qpr_margin,
                "throughput_strictly_greater": throughput_margin > 0.0,
                "qpr_strictly_greater": qpr_margin > 0.0,
                "passed": throughput_margin > 0.0 and qpr_margin > 0.0,
            }
        )
    return all(row["passed"] for row in rows), rows


def _validate_g2_runtime_stream(
    run: Mapping[str, Any], artifacts: Any
) -> dict[str, Any]:
    candidate = str(run["metadata"]["m1_operational_candidate"])
    run_configs = [
        event for event in artifacts.nse_events if event.get("kind") == "run_config"
    ]
    if len(run_configs) != 1:
        raise ProtocolValidationError(f"G2 run {run['run_id']} lacks one run_config")
    run_config = run_configs[0]
    if (
        run_config.get("operational_refinement") != candidate
        or run_config.get("operational_refinement_schema_version") != 4
        or run_config.get("initialization_semantics")
        != G2_INITIALIZATION_SEMANTICS[candidate]
    ):
        raise ProtocolValidationError(
            f"G2 run {run['run_id']} has the wrong initialization runtime contract"
        )
    counter_totals = {
        "initialization_refined_choices": 0,
        "initialization_lower_utility_choices": 0,
        "initialization_running_warm_choices": 0,
    }
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError(f"G2 run {run['run_id']} has no policy windows")
    for event in windows:
        decision = event.get("decision")
        if not isinstance(decision, Mapping):
            raise ProtocolValidationError(f"G2 run {run['run_id']} lacks decision data")
        for name in counter_totals:
            value = decision.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ProtocolValidationError(
                    f"G2 run {run['run_id']} has invalid {name}"
                )
            counter_totals[name] += value
    return {
        "operational_refinement_schema_version": 4,
        "initialization_semantics": run_config["initialization_semantics"],
        "policy_windows": len(windows),
        **counter_totals,
    }


def analyze_g2_initialization(
    manifest_path: Path, canonical_root: Path
) -> dict[str, Any]:
    from ..analysis.observability import analyze_scheduler_run, load_run_artifacts

    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("g2_strict_initialization_development")
    if not isinstance(marker, dict) or len(manifest["runs"]) != 135:
        raise ProtocolValidationError(
            "G2 analysis requires the complete 135-run product"
        )

    raw_rows: list[dict[str, Any]] = []
    artifacts_receipts: list[dict[str, Any]] = []
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    for run in manifest["runs"]:
        run_dir = canonical_root / run["run_id"]
        qc = validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        summary_path = _canonical_summary_path(canonical_root, run["run_id"])
        summary = read_json(summary_path)
        if not isinstance(summary, dict):
            raise ProtocolValidationError(f"G2 run {run['run_id']} has no summary")
        throughput, qpr, latency, cost = _screen_metrics(summary)
        row: dict[str, Any] = {
            "run_id": run["run_id"],
            "seed": run["seed"],
            "method": run["method"],
            "load": run["workload"]["request_freq"],
            "topology": run["cluster"]["topology"],
            "throughput_requests_per_ms": throughput,
            "qpr": qpr,
            "latency_mean_ms": latency,
            "cost_per_completed_request": cost,
            "completion_ratio": summary.get("completion_ratio"),
        }
        if run["method"] == "sche_nash":
            contract = qc.get("observations", {}).get("nash_runtime_contract")
            if (
                not isinstance(contract, Mapping)
                or contract.get("strict_eq15_ready") is not True
                or contract.get("stream_contract_ready") is not True
            ):
                raise ProtocolValidationError(
                    f"G2 run {run['run_id']} failed the strict runtime contract"
                )
            run_artifacts = load_run_artifacts(
                run,
                canonical_root,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path=result_relative_path,
            )
            diagnostics = analyze_scheduler_run(run_artifacts)
            if (
                diagnostics.get("feedback_trace_status") != "ok"
                or diagnostics.get("feedback_trace_invalid_rows") != 0
            ):
                raise ProtocolValidationError(
                    f"G2 run {run['run_id']} failed feedback-trace analysis"
                )
            row["candidate"] = run["metadata"]["m1_operational_candidate"]
            row["initialization"] = _validate_g2_runtime_stream(run, run_artifacts)
            row["nonconvergence_rate"] = diagnostics.get("nonconvergence_rate")
        raw_rows.append(row)
        artifacts_receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "summary_sha256": file_hash(summary_path),
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
            }
        )

    candidate_aggregates: list[dict[str, Any]] = []
    for candidate, load, topology in product(
        G2_INITIALIZATION_CANDIDATES,
        G2_INITIALIZATION_LOADS,
        G2_INITIALIZATION_TOPOLOGIES,
    ):
        group = [
            row
            for row in raw_rows
            if row.get("candidate") == candidate
            and row["load"] == load
            and row["topology"] == topology
        ]
        if len(group) != 5 or {row["seed"] for row in group} != set(
            G2_INITIALIZATION_SEEDS
        ):
            raise ProtocolValidationError(
                f"G2 candidate group {candidate}/{load}/{topology} is incomplete"
            )
        candidate_aggregates.append(
            {
                "candidate": candidate,
                "load": load,
                "topology": topology,
                "n": 5,
                "mean_throughput_requests_per_ms": fmean(
                    row["throughput_requests_per_ms"] for row in group
                ),
                "mean_qpr": fmean(row["qpr"] for row in group),
                "mean_latency_ms": fmean(row["latency_mean_ms"] for row in group),
                "mean_cost_per_completed_request": fmean(
                    row["cost_per_completed_request"] for row in group
                ),
                "mean_completion_ratio": fmean(
                    float(row["completion_ratio"]) for row in group
                ),
            }
        )

    baseline_aggregates: list[dict[str, Any]] = []
    for method in G2_INITIALIZATION_BASELINES:
        group = [
            row
            for row in raw_rows
            if row["method"] == method
            and row["load"] == "low"
            and row["topology"] == "homogeneous"
        ]
        if len(group) != 5 or {row["seed"] for row in group} != set(
            G2_INITIALIZATION_SEEDS
        ):
            raise ProtocolValidationError(f"G2 baseline group {method} is incomplete")
        baseline_aggregates.append(
            {
                "method": method,
                "load": "low",
                "topology": "homogeneous",
                "n": 5,
                "mean_throughput_requests_per_ms": fmean(
                    row["throughput_requests_per_ms"] for row in group
                ),
                "mean_qpr": fmean(row["qpr"] for row in group),
                "mean_latency_ms": fmean(row["latency_mean_ms"] for row in group),
                "mean_cost_per_completed_request": fmean(
                    row["cost_per_completed_request"] for row in group
                ),
                "mean_completion_ratio": fmean(
                    float(row["completion_ratio"]) for row in group
                ),
            }
        )

    selected, candidate_scores = _choose_g2_candidate(candidate_aggregates)
    gate_passed, baseline_gate_rows = _evaluate_baseline_gate(
        selected, candidate_aggregates, baseline_aggregates
    )
    receipt: dict[str, Any] = {
        "schema_version": G2_INITIALIZATION_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": (
            "complete_g2_development_formal_confirmation_authorized"
            if gate_passed
            else "complete_g2_development_failed_baseline_gate"
        ),
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "development_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "runtime_binary": copy.deepcopy(marker["runtime_binary"]),
        "selection_rule": copy.deepcopy(marker["selection_rule"]),
        "baseline_feasibility_gate": copy.deepcopy(marker["baseline_feasibility_gate"]),
        "selected_candidate": selected,
        "candidate_scores": candidate_scores,
        "candidate_cell_aggregates": candidate_aggregates,
        "baseline_low_aggregates": baseline_aggregates,
        "baseline_gate_rows": baseline_gate_rows,
        "baseline_gate_passed": gate_passed,
        "formal_confirmation_authorized": gate_passed,
        "run_metrics": raw_rows,
        "artifact_receipts": artifacts_receipts,
        "run_count": len(raw_rows),
    }
    receipt["document_sha256"] = object_hash(receipt)
    return receipt


def write_g2_initialization_selection(
    manifest_path: Path,
    canonical_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G2 selection receipt")
    receipt = analyze_g2_initialization(manifest_path, canonical_root)
    write_json_atomic(output_path, receipt)
    return receipt
