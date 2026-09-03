"""Fresh D71--D75 operational E0 development protocol.

The complete result-blind product compares unchanged ready-order C0 with the
preregistered first-round and every-round applications of the corrected G3 E0
strict-PNE selector. Development observations can authorize a disjoint formal
confirmation bank but can never be reused as formal evidence.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from itertools import product
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping

from ..analysis.feedback_trace import validate_runtime_contract_config
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
    G3_E0_OPERATIONAL_SAMPLE_POLICY,
    G3_E0_OPERATIONAL_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G3_E0_OPERATIONAL_CANDIDATES = (
    "ready_order",
    "ready_pne_envelope_first",
    "ready_pne_envelope_each",
)
G3_E0_OPERATIONAL_LOADS = ("low", "middle", "high")
G3_E0_OPERATIONAL_TOPOLOGIES = ("homogeneous", "heterogeneous")
G3_E0_OPERATIONAL_BASELINES = tuple(
    method for method in FORMAL_E1_METHODS if method != "sche_nash"
)
G3_E0_OPERATIONAL_SELECTION_SCHEMA = "NSE_G3_E0_OPERATIONAL_SELECTION_V1"
G3_E0_SCHEMA = "strict_pne_cold_envelope_operational_v1"
G3_E0_ORDERS = (
    "ready_order",
    "reverse_ready_order",
    "service_scarcity_first",
    "capacity_scarcity_first",
    "resource_impact_first",
)
G3_E0_TIE_ORDER = (
    "startup_burden_then_projected_finish_then_welfare_then_O0_O2_O3_O4_O1"
)
G3_E0_ELIGIBILITY = (
    "complete_and_stable_and_independent_strict_pne_and_"
    "welfare_noninferior_to_same_price_o0"
)
G3_E0_SEMANTICS = {
    "ready_order": "single_ready_order_path",
    "ready_pne_envelope_first": "nonworse_welfare_cold_envelope_first_outer_round",
    "ready_pne_envelope_each": "nonworse_welfare_cold_envelope_every_outer_round",
}


def _candidate_cell(
    candidate: str, load: str, topology: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G3E0.sche_nash.{candidate}.{load}.{topology}.n{node_count}",
        "sche_nash",
        _base_workload(load, topology, "mixed"),
        {"node_count": node_count, "topology": topology},
        metadata={
            "m1_operational_candidate": candidate,
            "g3_e0_operational_role": "strict_pne_operational_candidate",
            "paper_equations_changed": False,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
            "equilibrium_selection_schema": (
                G3_E0_SCHEMA if candidate != "ready_order" else None
            ),
        },
    )


def _baseline_cell(method: str, node_count: int) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G3E0.{method}.low.homogeneous.n{node_count}",
        method,
        _base_workload("low", "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={"g3_e0_operational_role": "homogeneous_low_baseline_control"},
    )


def build_g3_e0_operational_manifest(
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
            G3_E0_OPERATIONAL_CANDIDATES,
            G3_E0_OPERATIONAL_LOADS,
            G3_E0_OPERATIONAL_TOPOLOGIES,
        )
    ]
    baseline_cells = [
        _baseline_cell(method, node_count) for method in G3_E0_OPERATIONAL_BASELINES
    ]
    runs: list[dict[str, Any]] = []
    for cell in candidate_cells:
        candidate = str(cell["metadata"]["m1_operational_candidate"])
        for seed in G3_E0_OPERATIONAL_SEEDS:
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
        for seed in G3_E0_OPERATIONAL_SEEDS:
            runs.append(_make_run(config, cell, seed, common_hpa_hash, profiles["low"]))

    selection_rule = {
        "primary": "maximize_minimum_of_twelve_candidate_over_control_mean_ratios",
        "secondary": "maximize_mean_of_twelve_candidate_over_control_mean_ratios",
        "tertiary": "maximize_six_cell_joint_throughput_and_qpr_first_places",
        "final_tie_break": "C0_then_C1_then_C2",
        "result_conditioned_seed_removal_or_replacement": False,
    }
    admission_gate = {
        "selected_candidate_must_be_noncontrol": True,
        "all_twelve_control_ratios_strictly_above": 1.0,
        "homogeneous_low_strictly_above_all_nine_baselines": True,
        "complete_qpr_required": True,
        "active_window_aggregate_solve_us_ratio_cap": 9.0,
        "result_conditioned_extension": False,
        "old_pdf_alignment_is_selection_criterion": False,
    }
    marker = {
        "schema_version": "NSE_G3_E0_OPERATIONAL_DEVELOPMENT_V1",
        "purpose": "fresh-bank operational strict-PNE equilibrium-selection screen",
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "utility_guard_relative_regret": 0.0,
        "equilibrium_selection_schema": G3_E0_SCHEMA,
        "candidates": list(G3_E0_OPERATIONAL_CANDIDATES),
        "control_candidate": "ready_order",
        "baseline_methods": list(G3_E0_OPERATIONAL_BASELINES),
        "loads": list(G3_E0_OPERATIONAL_LOADS),
        "topologies": list(G3_E0_OPERATIONAL_TOPOLOGIES),
        "development_seeds": list(G3_E0_OPERATIONAL_SEEDS),
        "selection_rule": selection_rule,
        "admission_gate": admission_gate,
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
        "bank_id": "TSCv1.development.G3.E0-operational.D71-D75",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G3_E0_OPERATIONAL_SAMPLE_POLICY,
            "all_seeds": list(G3_E0_OPERATIONAL_SEEDS),
            "selected_seeds": list(G3_E0_OPERATIONAL_SEEDS),
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
        "g3_e0_operational_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g3_e0_operational_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G3 E0 manifest")
    manifest = build_g3_e0_operational_manifest(
        simulator_exe, source_git_commit, config_path
    )
    write_json_atomic(output_path, manifest)
    return manifest


def _choose_candidate(
    aggregates: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in aggregates:
        by_cell.setdefault((row["load"], row["topology"]), []).append(row)
    expected_cells = set(product(G3_E0_OPERATIONAL_LOADS, G3_E0_OPERATIONAL_TOPOLOGIES))
    if set(by_cell) != expected_cells:
        raise ProtocolValidationError("G3 E0 aggregates do not cover all six cells")
    scores: list[dict[str, Any]] = []
    for candidate in G3_E0_OPERATIONAL_CANDIDATES:
        ratios: list[float] = []
        dual_first = 0
        for cell in sorted(expected_cells):
            rows = by_cell[cell]
            if {row["candidate"] for row in rows} != set(G3_E0_OPERATIONAL_CANDIDATES):
                raise ProtocolValidationError(
                    f"G3 E0 aggregate is incomplete for {cell}"
                )
            control = next(row for row in rows if row["candidate"] == "ready_order")
            current = next(row for row in rows if row["candidate"] == candidate)
            for metric in ("mean_throughput_requests_per_ms", "mean_qpr"):
                denominator = float(control[metric])
                numerator = float(current[metric])
                if not all(
                    math.isfinite(value) and value > 0.0
                    for value in (denominator, numerator)
                ):
                    raise ProtocolValidationError(
                        "G3 E0 primary metric is not complete"
                    )
                ratios.append(numerator / denominator)
            if all(
                math.isclose(
                    float(current[metric]),
                    max(float(row[metric]) for row in rows),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
                for metric in ("mean_throughput_requests_per_ms", "mean_qpr")
            ):
                dual_first += 1
        scores.append(
            {
                "candidate": candidate,
                "worst_control_relative_ratio": min(ratios),
                "mean_control_relative_ratio": fmean(ratios),
                "dual_first_cells": dual_first,
                "simplicity_order": G3_E0_OPERATIONAL_CANDIDATES.index(candidate),
                "all_twelve_ratios_strictly_above_one": all(
                    ratio > 1.0 for ratio in ratios
                ),
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
    selected = [
        row
        for row in candidate_aggregates
        if row["candidate"] == selected_candidate
        and row["load"] == "low"
        and row["topology"] == "homogeneous"
    ]
    if len(selected) != 1 or {row["method"] for row in baseline_aggregates} != set(
        G3_E0_OPERATIONAL_BASELINES
    ):
        raise ProtocolValidationError("G3 E0 low-load baseline product is incomplete")
    rows = []
    for method in G3_E0_OPERATIONAL_BASELINES:
        baseline = next(row for row in baseline_aggregates if row["method"] == method)
        throughput_margin = float(
            selected[0]["mean_throughput_requests_per_ms"]
        ) - float(baseline["mean_throughput_requests_per_ms"])
        qpr_margin = float(selected[0]["mean_qpr"]) - float(baseline["mean_qpr"])
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


def _evaluate_timing_gate(
    selected_candidate: str, aggregates: list[dict[str, Any]]
) -> tuple[bool, list[dict[str, Any]]]:
    rows = []
    for load, topology in product(
        G3_E0_OPERATIONAL_LOADS, G3_E0_OPERATIONAL_TOPOLOGIES
    ):
        control = next(
            row
            for row in aggregates
            if row["candidate"] == "ready_order"
            and row["load"] == load
            and row["topology"] == topology
        )
        selected = next(
            row
            for row in aggregates
            if row["candidate"] == selected_candidate
            and row["load"] == load
            and row["topology"] == topology
        )
        denominator = int(control["aggregate_active_window_solve_us"])
        numerator = int(selected["aggregate_active_window_solve_us"])
        if denominator <= 0 or numerator < 0:
            raise ProtocolValidationError("G3 E0 timing denominator is not positive")
        ratio = numerator / denominator
        rows.append(
            {
                "load": load,
                "topology": topology,
                "selected_aggregate_active_window_solve_us": numerator,
                "control_aggregate_active_window_solve_us": denominator,
                "ratio": ratio,
                "cap": 9.0,
                "passed": ratio <= 9.0,
            }
        )
    return all(row["passed"] for row in rows), rows


def _nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProtocolValidationError(f"invalid G3 E0 {field}")
    return value


def _finite(value: Any, field: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"invalid G3 E0 {field}")
    converted = float(value)
    if not math.isfinite(converted) or (nonnegative and converted < 0.0):
        raise ProtocolValidationError(f"invalid G3 E0 {field}")
    return converted


def _validate_runtime_stream(run: Mapping[str, Any], artifacts: Any) -> dict[str, Any]:
    candidate = str(run["metadata"]["m1_operational_candidate"])
    configs = [
        event for event in artifacts.nse_events if event.get("kind") == "run_config"
    ]
    if len(configs) != 1:
        raise ProtocolValidationError(f"G3 E0 run {run['run_id']} lacks one run_config")
    config = configs[0]
    contract_errors = validate_runtime_contract_config(
        config,
        expected_candidate=candidate,
        expected_r0=float(run["simulator_experiment"]["nash"]["price_feedback_rate"]),
    )
    if contract_errors:
        raise ProtocolValidationError(
            f"G3 E0 run {run['run_id']} failed runtime contract: {contract_errors}"
        )
    expected_schema = 4 if candidate == "ready_order" else 5
    expected_config = {
        "schema": None if candidate == "ready_order" else G3_E0_SCHEMA,
        "semantics": G3_E0_SEMANTICS[candidate],
        "orders": None if candidate == "ready_order" else list(G3_E0_ORDERS),
        "eligibility": None if candidate == "ready_order" else G3_E0_ELIGIBILITY,
        "ranking": None if candidate == "ready_order" else G3_E0_TIE_ORDER,
        "welfare_tolerance": (
            None if candidate == "ready_order" else "EPSILON*max(1,abs(O0_welfare))"
        ),
        "dispatch_feedback": candidate != "ready_order",
    }
    if (
        config.get("operational_refinement_schema_version") != expected_schema
        or config.get("operational_equilibrium_selection") != expected_config
        or config.get("player_order")
        != (
            "arrival_frame_req_id_dag_topological_rank_fn_id"
            if candidate == "ready_order"
            else "preregistered_O0_O4_order_set"
        )
        or config.get("decision_neutral_diagnostics", {}).get(
            "order_counterfactual_enabled"
        )
        is not False
    ):
        raise ProtocolValidationError(
            f"G3 E0 run {run['run_id']} has the wrong operational selector config"
        )

    totals: Counter[str] = Counter()
    selected_orders: Counter[str] = Counter()
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError(f"G3 E0 run {run['run_id']} has no windows")
    for window in windows:
        decision = window.get("decision")
        solver = window.get("solver")
        overhead = window.get("overhead")
        if not all(
            isinstance(value, Mapping) for value in (decision, solver, overhead)
        ):
            raise ProtocolValidationError(
                f"G3 E0 run {run['run_id']} has an incomplete window"
            )
        assigned = _nonnegative_int(
            decision.get("assigned_players"), "assigned_players"
        )
        outer_rounds = _nonnegative_int(solver.get("outer_rounds"), "outer_rounds")
        feedback = solver.get("outer_feedback_trace")
        termination = solver.get("termination")
        terminal_inner_failure = termination in {
            "inner_iteration_limit",
            "infeasible_players",
            "oscillation_guard",
        }
        expected_feedback_rows = outer_rounds - int(terminal_inner_failure)
        if (
            not isinstance(termination, str)
            or expected_feedback_rows < 0
            or not isinstance(feedback, list)
            or len(feedback) != expected_feedback_rows
        ):
            raise ProtocolValidationError("G3 E0 outer-feedback trace length mismatch")
        solve_us = _nonnegative_int(overhead.get("solve_us"), "solve_us")
        e0_us = _nonnegative_int(
            overhead.get("operational_envelope_us"), "operational_envelope_us"
        )
        if solve_us < e0_us or window.get("order_counterfactual") is not None:
            raise ProtocolValidationError("G3 E0 timing or diagnostic isolation failed")
        active = assigned > 0
        totals["policy_windows"] += 1
        if active:
            totals["active_windows"] += 1
            totals["assigned_players"] += assigned
            totals["solve_us"] += solve_us
            totals["operational_envelope_us"] += e0_us
            totals["scheduler_wall_us"] += _nonnegative_int(
                overhead.get("scheduler_wall_us"), "scheduler_wall_us"
            )
            totals["scheduler_thread_cpu_us"] += _nonnegative_int(
                overhead.get("scheduler_thread_cpu_us"), "scheduler_thread_cpu_us"
            )
            totals["outer_rounds"] += outer_rounds
            totals["inner_limit_hits"] += int(solver.get("inner_limit_hit") is True)
            totals["outer_limit_hits"] += int(solver.get("outer_limit_hit") is True)

        selection = window.get("operational_equilibrium_selection")
        if candidate == "ready_order":
            if selection is not None or e0_us != 0:
                raise ProtocolValidationError("G3 E0 C0 emitted operational selection")
            continue
        if not isinstance(selection, Mapping):
            raise ProtocolValidationError("G3 E0 candidate lacks operational selection")
        rounds = selection.get("rounds")
        expected_rounds = (
            0
            if not active
            else 1
            if candidate == "ready_pne_envelope_first"
            else outer_rounds
        )
        if (
            selection.get("schema") != G3_E0_SCHEMA
            or selection.get("decision_feedback") is not True
            or not isinstance(rounds, list)
            or len(rounds) != expected_rounds
            or _nonnegative_int(selection.get("evaluated_orders"), "evaluated_orders")
            != expected_rounds * len(G3_E0_ORDERS)
            or _nonnegative_int(
                selection.get("selected_path_inner_rounds"),
                "selected_path_inner_rounds",
            )
            != _nonnegative_int(solver.get("inner_rounds"), "inner_rounds")
        ):
            raise ProtocolValidationError("G3 E0 window selector envelope mismatch")
        eligible_total = 0
        selected_non_o0 = 0
        fallback_total = 0
        evaluation_us = 0
        for index, trace in enumerate(rounds):
            if not isinstance(trace, Mapping):
                raise ProtocolValidationError("G3 E0 round trace is not an object")
            expected_outer = 1 if candidate.endswith("first") else index + 1
            order = trace.get("selected_order")
            selected_hash = trace.get("selected_assignment_hash")
            certificate = trace.get("selected_strict_pne")
            complete = trace.get("selected_complete")
            stable = trace.get("selected_stable")
            if (
                trace.get("outer_round") != expected_outer
                or trace.get("evaluated_orders") != len(G3_E0_ORDERS)
                or order not in G3_E0_ORDERS
                or not isinstance(selected_hash, int)
                or isinstance(selected_hash, bool)
                or selected_hash < 0
                or not isinstance(complete, bool)
                or not isinstance(stable, bool)
                or not isinstance(certificate, Mapping)
                or not isinstance(certificate.get("certified"), bool)
            ):
                raise ProtocolValidationError("G3 E0 selected state identity failed")
            eligible = _nonnegative_int(
                trace.get("eligible_outcomes"), "eligible_outcomes"
            )
            fallback = trace.get("fallback_to_o0")
            non_o0 = trace.get("selected_non_o0")
            if (
                not isinstance(fallback, bool)
                or not isinstance(non_o0, bool)
                or non_o0 != (order != "ready_order")
                or (fallback and (eligible != 0 or order != "ready_order"))
                or (not fallback and eligible == 0)
            ):
                raise ProtocolValidationError("G3 E0 eligibility/fallback trace failed")
            has_feedback = expected_outer <= len(feedback)
            if has_feedback:
                feedback_row = feedback[expected_outer - 1]
                if (
                    not isinstance(feedback_row, Mapping)
                    or stable is not True
                    or feedback_row.get("assignment_hash") != selected_hash
                ):
                    raise ProtocolValidationError(
                        "G3 E0 selected state/feedback identity failed"
                    )
            elif not (
                fallback
                and expected_outer == outer_rounds
                and terminal_inner_failure
                and stable is False
                and _nonnegative_int(
                    decision.get("assignment_hash"), "decision_assignment_hash"
                )
                == selected_hash
            ):
                raise ProtocolValidationError(
                    "G3 E0 terminal fallback/dispatch identity failed"
                )
            if not fallback and (
                complete is not True
                or stable is not True
                or certificate.get("certified") is not True
            ):
                raise ProtocolValidationError(
                    "G3 E0 eligible selected state is not a strict PNE"
                )
            _finite(
                trace.get("welfare_tolerance"),
                "welfare_tolerance",
                nonnegative=True,
            )
            _finite(trace.get("selected_welfare"), "selected_welfare")
            _finite(
                trace.get("selected_startup_burden_sum"),
                "selected_startup_burden_sum",
                nonnegative=True,
            )
            _finite(
                trace.get("selected_projected_finish_sum"),
                "selected_projected_finish_sum",
                nonnegative=True,
            )
            evaluation_us += _nonnegative_int(
                trace.get("evaluation_us"), "evaluation_us"
            )
            eligible_total += eligible
            selected_non_o0 += int(non_o0)
            fallback_total += int(fallback)
            selected_orders[str(order)] += 1
        if (
            _nonnegative_int(selection.get("eligible_outcomes"), "eligible_outcomes")
            != eligible_total
            or _nonnegative_int(
                selection.get("selected_non_o0_rounds"), "selected_non_o0_rounds"
            )
            != selected_non_o0
            or _nonnegative_int(selection.get("fallback_rounds"), "fallback_rounds")
            != fallback_total
            or e0_us != evaluation_us
        ):
            raise ProtocolValidationError("G3 E0 aggregate trace counters mismatch")
        for field in (
            "evaluated_total_inner_rounds",
            "evaluated_total_assignment_moves",
            "evaluated_total_candidate_evaluations",
            "evaluated_total_initialization_evaluations",
        ):
            _nonnegative_int(selection.get(field), field)
        totals["selection_rounds"] += expected_rounds
        totals["selected_non_o0_rounds"] += selected_non_o0
        totals["fallback_rounds"] += fallback_total

    process_observation = artifacts.process_observation
    peak_rss = None
    if isinstance(process_observation, Mapping):
        value = process_observation.get("peak_process_tree_rss_bytes")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            converted = float(value)
            if math.isfinite(converted) and converted >= 0.0:
                peak_rss = converted
    return {
        "operational_refinement_schema_version": expected_schema,
        "policy_windows": totals["policy_windows"],
        "active_windows": totals["active_windows"],
        "assigned_players": totals["assigned_players"],
        "aggregate_active_window_solve_us": totals["solve_us"],
        "aggregate_active_window_operational_envelope_us": totals[
            "operational_envelope_us"
        ],
        "aggregate_active_window_scheduler_wall_us": totals["scheduler_wall_us"],
        "aggregate_active_window_scheduler_thread_cpu_us": totals[
            "scheduler_thread_cpu_us"
        ],
        "aggregate_outer_rounds": totals["outer_rounds"],
        "inner_limit_active_windows": totals["inner_limit_hits"],
        "outer_limit_active_windows": totals["outer_limit_hits"],
        "selection_rounds": totals["selection_rounds"],
        "selected_non_o0_rounds": totals["selected_non_o0_rounds"],
        "fallback_rounds": totals["fallback_rounds"],
        "selected_order_counts": dict(sorted(selected_orders.items())),
        "process_peak_rss_bytes": peak_rss,
    }


def _candidate_aggregate(
    candidate: str, load: str, topology: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    group = [
        row
        for row in rows
        if row.get("candidate") == candidate
        and row["load"] == load
        and row["topology"] == topology
    ]
    if len(group) != 5 or {row["seed"] for row in group} != set(
        G3_E0_OPERATIONAL_SEEDS
    ):
        raise ProtocolValidationError(
            f"G3 E0 candidate group {candidate}/{load}/{topology} is incomplete"
        )
    active_windows = sum(row["runtime"]["active_windows"] for row in group)
    selection_rounds = sum(row["runtime"]["selection_rounds"] for row in group)
    order_counts: Counter[str] = Counter()
    for row in group:
        order_counts.update(row["runtime"]["selected_order_counts"])
    peak_values = [
        row["runtime"]["process_peak_rss_bytes"]
        for row in group
        if row["runtime"]["process_peak_rss_bytes"] is not None
    ]
    return {
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
        "mean_completion_ratio": fmean(float(row["completion_ratio"]) for row in group),
        "active_windows": active_windows,
        "aggregate_active_window_solve_us": sum(
            row["runtime"]["aggregate_active_window_solve_us"] for row in group
        ),
        "aggregate_active_window_operational_envelope_us": sum(
            row["runtime"]["aggregate_active_window_operational_envelope_us"]
            for row in group
        ),
        "mean_scheduler_wall_us_per_active_window": (
            sum(
                row["runtime"]["aggregate_active_window_scheduler_wall_us"]
                for row in group
            )
            / active_windows
            if active_windows
            else None
        ),
        "mean_scheduler_thread_cpu_us_per_active_window": (
            sum(
                row["runtime"]["aggregate_active_window_scheduler_thread_cpu_us"]
                for row in group
            )
            / active_windows
            if active_windows
            else None
        ),
        "mean_outer_rounds_per_active_window": (
            sum(row["runtime"]["aggregate_outer_rounds"] for row in group)
            / active_windows
            if active_windows
            else None
        ),
        "inner_limit_active_share": (
            sum(row["runtime"]["inner_limit_active_windows"] for row in group)
            / active_windows
            if active_windows
            else None
        ),
        "outer_limit_active_share": (
            sum(row["runtime"]["outer_limit_active_windows"] for row in group)
            / active_windows
            if active_windows
            else None
        ),
        "selection_rounds": selection_rounds,
        "selected_non_o0_share": (
            sum(row["runtime"]["selected_non_o0_rounds"] for row in group)
            / selection_rounds
            if selection_rounds
            else None
        ),
        "fallback_share": (
            sum(row["runtime"]["fallback_rounds"] for row in group) / selection_rounds
            if selection_rounds
            else None
        ),
        "selected_order_fractions": {
            order: order_counts[order] / selection_rounds
            for order in G3_E0_ORDERS
            if selection_rounds
        },
        "max_process_peak_rss_mib": (
            max(peak_values) / (1024.0 * 1024.0) if peak_values else None
        ),
    }


def analyze_g3_e0_operational(
    manifest_path: Path, canonical_root: Path
) -> dict[str, Any]:
    from ..analysis.observability import analyze_scheduler_run, load_run_artifacts

    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("g3_e0_operational_development")
    if not isinstance(marker, dict) or len(manifest["runs"]) != 135:
        raise ProtocolValidationError("G3 E0 analysis requires the complete product")
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
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
            raise ProtocolValidationError(f"G3 E0 run {run['run_id']} lacks summary")
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
                    f"G3 E0 run {run['run_id']} failed strict runtime QC"
                )
            artifacts = load_run_artifacts(
                run,
                canonical_root,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path=result_relative_path,
            )
            diagnostics = analyze_scheduler_run(artifacts)
            if (
                diagnostics.get("feedback_trace_status") != "ok"
                or diagnostics.get("feedback_trace_invalid_rows") != 0
            ):
                raise ProtocolValidationError(
                    f"G3 E0 run {run['run_id']} failed feedback validation"
                )
            row["candidate"] = run["metadata"]["m1_operational_candidate"]
            row["runtime"] = _validate_runtime_stream(run, artifacts)
        rows.append(row)
        receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "summary_sha256": file_hash(summary_path),
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
            }
        )

    candidate_aggregates = [
        _candidate_aggregate(candidate, load, topology, rows)
        for candidate, load, topology in product(
            G3_E0_OPERATIONAL_CANDIDATES,
            G3_E0_OPERATIONAL_LOADS,
            G3_E0_OPERATIONAL_TOPOLOGIES,
        )
    ]
    baseline_aggregates = []
    for method in G3_E0_OPERATIONAL_BASELINES:
        group = [
            row
            for row in rows
            if row["method"] == method
            and row["load"] == "low"
            and row["topology"] == "homogeneous"
        ]
        if len(group) != 5 or {row["seed"] for row in group} != set(
            G3_E0_OPERATIONAL_SEEDS
        ):
            raise ProtocolValidationError(f"G3 E0 baseline {method} is incomplete")
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

    selected, scores = _choose_candidate(candidate_aggregates)
    selected_score = next(row for row in scores if row["candidate"] == selected)
    control_gate = selected != "ready_order" and bool(
        selected_score["all_twelve_ratios_strictly_above_one"]
    )
    baseline_passed, baseline_rows = _evaluate_baseline_gate(
        selected, candidate_aggregates, baseline_aggregates
    )
    timing_passed, timing_rows = _evaluate_timing_gate(selected, candidate_aggregates)
    authorized = control_gate and baseline_passed and timing_passed
    receipt: dict[str, Any] = {
        "schema_version": G3_E0_OPERATIONAL_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": (
            "complete_g3_e0_development_formal_confirmation_authorized"
            if authorized
            else "complete_g3_e0_development_gate_failed"
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
        "admission_gate": copy.deepcopy(marker["admission_gate"]),
        "selected_candidate": selected,
        "candidate_scores": scores,
        "candidate_cell_aggregates": candidate_aggregates,
        "baseline_low_aggregates": baseline_aggregates,
        "control_improvement_gate_passed": control_gate,
        "baseline_gate_rows": baseline_rows,
        "baseline_gate_passed": baseline_passed,
        "solve_time_gate_rows": timing_rows,
        "solve_time_gate_passed": timing_passed,
        "formal_confirmation_authorized": authorized,
        "run_metrics": rows,
        "artifact_receipts": receipts,
        "run_count": len(rows),
    }
    receipt["document_sha256"] = object_hash(receipt)
    return receipt


def write_g3_e0_operational_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G3 E0 selection")
    receipt = analyze_g3_e0_operational(manifest_path, canonical_root)
    write_json_atomic(output_path, receipt)
    return receipt
