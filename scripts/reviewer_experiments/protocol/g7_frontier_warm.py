"""Five-run G7 bounded-frontier lookahead plus warm-start development protocol."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..analysis.feedback_trace import validate_runtime_contract_config
from ..analysis.formal_inputs import validate_canonical_run
from ..analysis.observability import RunArtifacts, load_run_artifacts
from .g1_corrected_runtime import _runtime_execution
from .g3_e0_operational import G3_E0_OPERATIONAL_BASELINES
from .g6_lookahead import (
    FROZEN_BEST_QPR,
    FROZEN_BEST_THROUGHPUT,
    _evaluate_gate as _evaluate_g6_gate,
    _finite,
    _load_g3_source,
    _metric_row,
    _nonnegative_int,
    _source_binding,
    _source_rows,
)
from .m1_completion_guard import _runtime_receipt
from .m1_development import _bind_candidate, _matrix_summary
from .m1_qualification import _canonical_summary_path
from .matrix import (
    _base_workload,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    load_protocol_config,
)
from .schema import (
    G7_FRONTIER_WARM_SAMPLE_POLICY,
    G7_FRONTIER_WARM_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G7_CANDIDATE = "lookahead_frontier1_warm_init"
G7_SELECTION_SCHEMA = "NSE_G7_FRONTIER_WARM_SELECTION_V1"
G7_MANIFEST_SCHEMA = "NSE_G7_FRONTIER_WARM_DEVELOPMENT_V1"
G7_PLAYER_COLLECTION = "ready_plus_one_executable_frontier_hop"
G7_INITIALIZATION = (
    "running_warm_if_available_min_dynamic_finish_then_higher_utility_"
    "then_node_id_else_strict_utility"
)


def _candidate_cell(node_count: int) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G7.sche_nash.{G7_CANDIDATE}.low.homogeneous.n{node_count}",
        "sche_nash",
        _base_workload("low", "homogeneous", "mixed"),
        {"node_count": node_count, "topology": "homogeneous"},
        metadata={
            "m1_operational_candidate": G7_CANDIDATE,
            "g7_frontier_warm_role": "bounded_frontier_warm_strict_eq15_candidate",
            "paper_equations_changed": False,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
            "player_collection": G7_PLAYER_COLLECTION,
            "initialization_semantics": G7_INITIALIZATION,
        },
    )


def build_g7_frontier_warm_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    g3_manifest_path: Path,
    g3_selection_path: Path,
    g3_canonical_root: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact five-run candidate-only, non-formal G7 manifest."""

    source, selection, source_runs = _load_g3_source(
        g3_manifest_path, g3_selection_path
    )
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
    if (
        source["common_hpa_hash"] != common_hpa_hash
        or source["workload_profile_set_hash"] != object_hash(workload_profile_set)
        or source["simulation"] != config["simulation"]
    ):
        raise ProtocolValidationError(
            "G7 current protocol differs from frozen G3 inputs"
        )

    cell = _candidate_cell(node_count)
    source_c0 = {
        run["seed"]: run for run in source_runs if run["method"] == "sche_nash"
    }
    runs = []
    for seed in G7_FRONTIER_WARM_SEEDS:
        run = _make_run(config, cell, seed, common_hpa_hash, profiles["low"])
        _bind_candidate(run, G7_CANDIDATE)
        control = source_c0.get(seed)
        if control is None or any(
            run[field] != control[field]
            for field in (
                "workload",
                "cluster",
                "workload_spec_hash",
                "workload_profile",
                "common_hpa",
                "common_hpa_hash",
                "simulation",
            )
        ):
            raise ProtocolValidationError(f"G7 input mismatch against G3 C0 for {seed}")
        if run["workload_tape"]["key"] != control["workload_tape"]["key"]:
            raise ProtocolValidationError(f"G7 workload-tape key mismatch for {seed}")
        runs.append(run)

    activation_gate = {
        "completed_functions_only": True,
        "per_seed_pre_ready_bound_count_at_least": 1,
        "per_seed_startup_overlap_ms_sum_strictly_above": 0.0,
        "per_seed_initialization_refined_choices_at_least": 1,
        "per_seed_initialization_running_warm_choices_at_least": 1,
        "per_seed_frontier_hop_violation_count_at_most": 0,
        "complete_dispatch_accounting": True,
        "offline_reference_required": True,
    }
    performance_gate = {
        "mean_throughput_strictly_above": FROZEN_BEST_THROUGHPUT,
        "mean_qpr_strictly_above": FROZEN_BEST_QPR,
        "paired_throughput_improvements_at_least": 3,
        "paired_qpr_improvements_at_least": 4,
        "paired_joint_improvements_at_least": 3,
        "per_seed_throughput_control_floor_ratio": 0.80,
        "per_seed_qpr_control_floor_ratio": 0.80,
        "mean_completion_not_below_control": True,
        "mean_latency_strictly_below_control": True,
        "mean_solve_time_ratio_at_most": 3.0,
    }
    marker = {
        "schema_version": G7_MANIFEST_SCHEMA,
        "purpose": "bounded-frontier warm-start strict-Eq15 homogeneous-low development gate",
        "candidate": G7_CANDIDATE,
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "utility_guard_relative_regret": 0.0,
        "player_collection": G7_PLAYER_COLLECTION,
        "player_order": "arrival_frame_req_id_dag_topological_rank_fn_id",
        "initialization_semantics": G7_INITIALIZATION,
        "frontier_integrity": {
            "completed_functions_only": True,
            "maximum_executable_frontier_hops_ahead": 1,
            "missing_topology_or_parent_timing_fails_closed": True,
        },
        "development_seeds": list(G7_FRONTIER_WARM_SEEDS),
        "all_valid_runs_retained": True,
        "result_conditioned_extension": False,
        "first_valid_canonical_result_retained": True,
        "source_g3_product": _source_binding(
            g3_manifest_path,
            g3_selection_path,
            g3_canonical_root,
            source,
            selection,
            source_runs,
        ),
        "activation_gate": activation_gate,
        "performance_gate": performance_gate,
        "runtime_binary": runtime,
        "workload_tape_count": 5,
        "candidate_run_count": 5,
        "reference_build_count": len(_reference_build_dependencies(runs)),
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.G7.frontier-warm.D71-D75",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G7_FRONTIER_WARM_SAMPLE_POLICY,
            "all_seeds": list(G7_FRONTIER_WARM_SEEDS),
            "selected_seeds": list(G7_FRONTIER_WARM_SEEDS),
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
        "g7_frontier_warm_development": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g7_frontier_warm_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    g3_manifest_path: Path,
    g3_selection_path: Path,
    g3_canonical_root: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G7 frontier-warm manifest")
    manifest = build_g7_frontier_warm_manifest(
        simulator_exe,
        source_git_commit,
        g3_manifest_path,
        g3_selection_path,
        g3_canonical_root,
        config_path,
    )
    write_json_atomic(output_path, manifest)
    return manifest


def _environment_parents(artifacts: RunArtifacts) -> dict[int, tuple[int, ...]]:
    rows = artifacts.environment.get("functions")
    if not isinstance(rows, list) or not rows:
        raise ProtocolValidationError("G7 environment has no function topology")
    parents: dict[int, tuple[int, ...]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ProtocolValidationError("G7 environment function row is invalid")
        function_id = _nonnegative_int(row.get("function_id"), "function_id")
        raw_parents = row.get("parents")
        if function_id in parents or not isinstance(raw_parents, list):
            raise ProtocolValidationError("G7 environment function topology is invalid")
        parent_ids = tuple(
            _nonnegative_int(parent, "parent function_id") for parent in raw_parents
        )
        if len(set(parent_ids)) != len(parent_ids):
            raise ProtocolValidationError("G7 environment has duplicate parent edges")
        parents[function_id] = parent_ids
    if any(parent not in parents for values in parents.values() for parent in values):
        raise ProtocolValidationError(
            "G7 environment topology references an unknown parent"
        )
    return parents


def _unfinished_ancestor_depth(
    function_id: int,
    scheduled_frame: int,
    parents: Mapping[int, Sequence[int]],
    timings: Mapping[int, Mapping[str, int]],
    visiting: frozenset[int] = frozenset(),
) -> int:
    if function_id in visiting:
        raise ProtocolValidationError("G7 environment topology contains a cycle")
    depths = []
    for parent in parents[function_id]:
        timing = timings.get(parent)
        if timing is None:
            raise ProtocolValidationError("G7 completed request lacks parent timing")
        if timing["done"] > scheduled_frame:
            depths.append(
                1
                + _unfinished_ancestor_depth(
                    parent,
                    scheduled_frame,
                    parents,
                    timings,
                    visiting | {function_id},
                )
            )
    return max(depths, default=0)


def _activation_metrics(artifacts: RunArtifacts) -> dict[str, Any]:
    parents = _environment_parents(artifacts)
    completed_requests = set()
    completed_functions = 0
    early_bound = 0
    overlap_sum = 0.0
    violation_count = 0
    maximum_depth = 0
    for request in artifacts.requests:
        request_id = str(request.get("request_id", ""))
        functions = request.get("functions")
        if not request_id or request_id in completed_requests:
            raise ProtocolValidationError("G7 request stream has invalid request IDs")
        if not isinstance(functions, list) or not functions:
            raise ProtocolValidationError("G7 completed request has no functions")
        completed_requests.add(request_id)
        timings: dict[int, dict[str, int]] = {}
        cold_done_by_function: dict[int, int | None] = {}
        ready_by_function: dict[int, int] = {}
        for function in functions:
            if not isinstance(function, Mapping):
                raise ProtocolValidationError("G7 function timing row is invalid")
            function_id = _nonnegative_int(function.get("function_id"), "function_id")
            if function_id in timings or function_id not in parents:
                raise ProtocolValidationError("G7 function timing identity is invalid")
            ready = _nonnegative_int(
                function.get("ready_schedule_frame"), "ready_schedule_frame"
            )
            scheduled = _nonnegative_int(
                function.get("scheduled_frame"), "scheduled_frame"
            )
            done = _nonnegative_int(
                function.get("function_done_frame"), "function_done_frame"
            )
            cold_raw = function.get("cold_start_done_frame")
            cold_done = (
                None
                if cold_raw is None
                else _nonnegative_int(cold_raw, "cold_start_done_frame")
            )
            timings[function_id] = {"scheduled": scheduled, "done": done}
            ready_by_function[function_id] = ready
            cold_done_by_function[function_id] = cold_done
        for function_id, timing in timings.items():
            scheduled = timing["scheduled"]
            ready = ready_by_function[function_id]
            completed_functions += 1
            early_bound += int(scheduled < ready)
            cold_done = cold_done_by_function[function_id]
            if cold_done is not None:
                overlap_sum += max(min(cold_done, ready) - scheduled, 0)
            parent_placement_violation = any(
                parent not in timings or timings[parent]["scheduled"] > scheduled
                for parent in parents[function_id]
            )
            depth = _unfinished_ancestor_depth(function_id, scheduled, parents, timings)
            maximum_depth = max(maximum_depth, depth)
            violation_count += int(parent_placement_violation or depth > 1)
    expected = _nonnegative_int(
        artifacts.summary.get("fixed_observation_window", {}).get("completed"),
        "fixed completed requests",
    )
    if len(completed_requests) != expected or completed_functions == 0:
        raise ProtocolValidationError("G7 request stream/summary completion mismatch")
    return {
        "completed_request_count": len(completed_requests),
        "completed_function_count": completed_functions,
        "pre_ready_bound_count": early_bound,
        "pre_ready_bound_share": early_bound / completed_functions,
        "startup_overlap_ms_sum": overlap_sum,
        "mean_startup_overlap_ms": overlap_sum / completed_functions,
        "maximum_executable_frontier_hops_ahead": maximum_depth,
        "frontier_hop_violation_count": violation_count,
    }


def _candidate_runtime(
    run: Mapping[str, Any], artifacts: RunArtifacts
) -> dict[str, Any]:
    configs = [
        event for event in artifacts.nse_events if event.get("kind") == "run_config"
    ]
    if len(configs) != 1:
        raise ProtocolValidationError("G7 candidate lacks exactly one run_config")
    config = configs[0]
    errors = validate_runtime_contract_config(
        config,
        expected_candidate=G7_CANDIDATE,
        expected_r0=float(run["simulator_experiment"]["nash"]["price_feedback_rate"]),
    )
    expected_selector = {
        "schema": None,
        "semantics": "single_ready_order_path",
        "orders": None,
        "eligibility": None,
        "ranking": None,
        "welfare_tolerance": None,
        "dispatch_feedback": False,
    }
    reference = config.get("reference")
    if (
        errors
        or config.get("operational_refinement_schema_version") != 7
        or config.get("player_collection") != G7_PLAYER_COLLECTION
        or config.get("initialization_semantics") != G7_INITIALIZATION
        or config.get("operational_equilibrium_selection") != expected_selector
        or config.get("decision_neutral_diagnostics", {}).get(
            "order_counterfactual_enabled"
        )
        is not False
        or not isinstance(reference, Mapping)
        or reference.get("mode") != "offline_required"
        or reference.get("offline_load_ok") is not True
        or _nonnegative_int(reference.get("offline_entries"), "offline entries") <= 0
    ):
        raise ProtocolValidationError(f"G7 runtime contract failed: {errors}")

    active_windows = 0
    assigned_total = 0
    solve_us = 0
    reference_hits = 0
    unreferenced_active_windows = 0
    initialization = {
        "initialization_refined_choices": 0,
        "initialization_lower_utility_choices": 0,
        "initialization_running_warm_choices": 0,
    }
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError("G7 candidate has no policy windows")
    for window in windows:
        decision = window.get("decision")
        overhead = window.get("overhead")
        if not isinstance(decision, Mapping) or not isinstance(overhead, Mapping):
            raise ProtocolValidationError("G7 candidate window is incomplete")
        for name in initialization:
            initialization[name] += _nonnegative_int(decision.get(name), name)
        assigned = _nonnegative_int(
            decision.get("assigned_players"), "assigned players"
        )
        if assigned == 0:
            continue
        active_windows += 1
        assigned_total += assigned
        solve_us += _nonnegative_int(overhead.get("solve_us"), "solve time")
        social = window.get("social")
        if not isinstance(social, Mapping):
            raise ProtocolValidationError("G7 active window has no social object")
        if (
            decision.get("complete_assignment") is not True
            or _nonnegative_int(decision.get("commands_prepared"), "commands prepared")
            != assigned
            or _nonnegative_int(decision.get("commands_sent"), "commands sent")
            != assigned
            or _nonnegative_int(
                decision.get("invalid_assignments"), "invalid assignments"
            )
            != 0
            or decision.get("dispatch_channel_failed") is not False
            or window.get("operational_equilibrium_selection") is not None
            or window.get("order_counterfactual") is not None
        ):
            raise ProtocolValidationError("G7 dispatch accounting failed")
        reference_source = social.get("reference_source")
        if reference_source == "offline_table":
            _nonnegative_int(social.get("reference_state_key"), "reference state key")
            _finite(social.get("reference"), "offline reference")
            reference_hits += 1
        elif reference_source == "not_requested":
            required_null_fields = {"reference_state_key", "reference"}
            required_false_fields = {"reference_cache_hit", "feedback_eligible"}
            if (
                not required_null_fields.issubset(social)
                or not required_false_fields.issubset(social)
                or any(social[name] is not None for name in required_null_fields)
                or any(social[name] is not False for name in required_false_fields)
            ):
                raise ProtocolValidationError(
                    "G7 not-requested reference shape is inconsistent"
                )
            unreferenced_active_windows += 1
        else:
            raise ProtocolValidationError(
                "G7 active-window reference source is invalid"
            )
    if active_windows == 0 or assigned_total == 0 or solve_us <= 0:
        raise ProtocolValidationError("G7 candidate has no active scheduling work")
    return {
        "active_window_count": active_windows,
        "assigned_players": assigned_total,
        "commands_prepared": assigned_total,
        "commands_sent": assigned_total,
        "invalid_assignments": 0,
        "dispatch_channel_failures": 0,
        "offline_reference_hit_windows": reference_hits,
        "unreferenced_active_window_count": unreferenced_active_windows,
        "aggregate_active_window_solve_us": solve_us,
        **initialization,
    }


def _evaluate_gate(
    candidate_rows: Sequence[Mapping[str, Any]],
    control_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    result = _evaluate_g6_gate(candidate_rows, control_rows, baseline_rows)
    activation_rows = []
    reference_coverage_rows = []
    for row in sorted(
        candidate_rows,
        key=lambda item: G7_FRONTIER_WARM_SEEDS.index(str(item["seed"])),
    ):
        passed = (
            int(row["pre_ready_bound_count"]) >= 1
            and float(row["startup_overlap_ms_sum"]) > 0.0
            and int(row["initialization_refined_choices"]) >= 1
            and int(row["initialization_running_warm_choices"]) >= 1
            and int(row["frontier_hop_violation_count"]) == 0
            and int(row["maximum_executable_frontier_hops_ahead"]) <= 1
        )
        activation_rows.append(
            {
                "seed": row["seed"],
                "pre_ready_bound_count": row["pre_ready_bound_count"],
                "pre_ready_bound_share": row["pre_ready_bound_share"],
                "startup_overlap_ms_sum": row["startup_overlap_ms_sum"],
                "mean_startup_overlap_ms": row["mean_startup_overlap_ms"],
                "initialization_refined_choices": row["initialization_refined_choices"],
                "initialization_running_warm_choices": row[
                    "initialization_running_warm_choices"
                ],
                "maximum_executable_frontier_hops_ahead": row[
                    "maximum_executable_frontier_hops_ahead"
                ],
                "frontier_hop_violation_count": row["frontier_hop_violation_count"],
                "passed": passed,
            }
        )
        active_windows = int(row["active_window_count"])
        reference_hits = int(row["offline_reference_hit_windows"])
        unreferenced = int(row["unreferenced_active_window_count"])
        reference_coverage_rows.append(
            {
                "seed": row["seed"],
                "active_window_count": active_windows,
                "offline_reference_hit_windows": reference_hits,
                "unreferenced_active_window_count": unreferenced,
                "passed": (reference_hits == active_windows and unreferenced == 0),
            }
        )
    result["activation_rows"] = activation_rows
    result["reference_coverage_rows"] = reference_coverage_rows
    result["conditions"]["activation_all_seeds"] = all(
        row["passed"] for row in activation_rows
    )
    result["conditions"]["offline_reference_all_active_windows"] = all(
        row["passed"] for row in reference_coverage_rows
    )
    passed = all(result["conditions"].values())
    result["status"] = (
        "complete_g7_development_confirmation_preregistration_authorized"
        if passed
        else "complete_g7_development_gate_failed"
    )
    result["candidate_development_qualified"] = passed
    result["confirmation_preregistration_authorized"] = passed
    result["confirmation_sampling_authorized"] = False
    result["formal_progression_authorized"] = False
    return result


def analyze_g7_frontier_warm(
    manifest_path: Path, candidate_canonical_root: Path
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    candidate_canonical_root = candidate_canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("g7_frontier_warm_development")
    if (
        not isinstance(marker, dict)
        or manifest.get("all_tapes_bound") is not True
        or manifest.get("all_references_bound") is not True
        or len(manifest["runs"]) != 5
    ):
        raise ProtocolValidationError(
            "G7 analysis requires the complete ready manifest"
        )
    source_info = marker["source_g3_product"]
    source, selection, source_runs = _load_g3_source(
        Path(source_info["manifest_path"]), Path(source_info["selection_path"])
    )
    expected_binding = _source_binding(
        Path(source_info["manifest_path"]),
        Path(source_info["selection_path"]),
        Path(source_info["canonical_root"]),
        source,
        selection,
        source_runs,
    )
    if source_info != expected_binding:
        raise ProtocolValidationError("G7 source G3 binding changed after freeze")
    source_rows, source_receipts = _source_rows(
        source,
        selection,
        source_runs,
        Path(source_info["canonical_root"]).resolve(),
    )
    source_c0 = {
        row["seed"]: row for row in source_rows if row["method"] == "sche_nash"
    }
    source_runs_c0 = {
        run["seed"]: run for run in source_runs if run["method"] == "sche_nash"
    }

    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    candidate_rows = []
    candidate_receipts = []
    for run in manifest["runs"]:
        control_run = source_runs_c0.get(run["seed"])
        if control_run is None or run["workload_tape"].get("sha256") != control_run[
            "workload_tape"
        ].get("sha256"):
            raise ProtocolValidationError("G7 candidate/control tape pairing failed")
        run_dir = candidate_canonical_root / run["run_id"]
        qc = validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        contract = qc.get("observations", {}).get("nash_runtime_contract")
        if (
            not isinstance(contract, Mapping)
            or contract.get("strict_eq15_ready") is not True
            or contract.get("stream_contract_ready") is not True
        ):
            raise ProtocolValidationError("G7 candidate failed strict runtime QC")
        artifacts = load_run_artifacts(
            run,
            candidate_canonical_root,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        row = _metric_row(run, artifacts.summary)
        row.update(_candidate_runtime(run, artifacts))
        row.update(_activation_metrics(artifacts))
        candidate_rows.append(row)
        summary_path = _canonical_summary_path(candidate_canonical_root, run["run_id"])
        candidate_receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "offline_reference_sha256": run["reference_dependency"]["sha256"],
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "summary_sha256": file_hash(summary_path),
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
            }
        )
    gate = _evaluate_gate(
        candidate_rows,
        list(source_c0.values()),
        [row for row in source_rows if row["method"] != "sche_nash"],
    )
    report: dict[str, Any] = {
        "schema_version": G7_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": gate["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "development_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "runtime_binary": copy.deepcopy(marker["runtime_binary"]),
        "source_g3_product": copy.deepcopy(source_info),
        "definitions": {
            "independent_unit": "run/seed",
            "all_valid_runs_retained": True,
            "completed_functions_only_for_activation_and_frontier_audit": True,
            "paired_by_identical_workload_tape": True,
            "development_results_are_paper_evidence": False,
        },
        "activation_gate": copy.deepcopy(marker["activation_gate"]),
        "performance_gate": copy.deepcopy(marker["performance_gate"]),
        "candidate_run_metrics": candidate_rows,
        "source_control_run_metrics": source_rows,
        "gate_result": gate,
        "candidate_artifact_receipts": candidate_receipts,
        "source_artifact_receipts": source_receipts,
        "candidate_run_count": len(candidate_rows),
        "source_control_run_count": len(source_rows),
        "confirmation_preregistration_authorized": gate[
            "confirmation_preregistration_authorized"
        ],
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_g7_frontier_warm_selection(
    manifest_path: Path, candidate_canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError(
            "refusing to overwrite G7 frontier-warm selection"
        )
    report = analyze_g7_frontier_warm(manifest_path, candidate_canonical_root)
    write_json_atomic(output_path, report)
    return report
