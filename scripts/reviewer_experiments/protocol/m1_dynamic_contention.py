"""Final fresh-bank dynamic-contention guard protocol."""

from __future__ import annotations

import copy
from itertools import product
from pathlib import Path
from statistics import fmean
from typing import Any

from .m1_completion_guard import _runtime_receipt
from .m1_development import _bind_candidate, _matrix_summary
from .m1_qualification import (
    _canonical_summary_path,
    _choose_candidate,
    _screen_metrics,
    analyze_m1_qualification,
)
from .matrix import (
    _base_workload,
    _make_cell,
    _make_run,
    _reference_build_dependencies,
    load_protocol_config,
)
from .schema import (
    FORMAL_E1_METHODS,
    M1_DYNAMIC_SAMPLE_POLICY,
    M1_DYNAMIC_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic
from .workload_profile import load_profile_set


M1_DYNAMIC_CANDIDATES = (
    "ready_order",
    "guarded_dynamic_finish_05",
    "guarded_dynamic_finish_15",
)
M1_DYNAMIC_SCREEN_SEEDS = M1_DYNAMIC_SEEDS[:5]
M1_DYNAMIC_LOADS = ("low", "middle", "high")
M1_DYNAMIC_TOPOLOGIES = ("homogeneous", "heterogeneous")
M1_DYNAMIC_BASELINES = tuple(
    method for method in FORMAL_E1_METHODS if method != "sche_nash"
)
M1_DYNAMIC_SELECTION_SCHEMA = "NSE_M1_DYNAMIC_CONTENTION_SELECTION_V1"


def _candidate_cell(
    candidate: str, load: str, topology: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"M1DYNAMIC.sche_nash.{candidate}.{load}.{topology}.n{node_count}",
        "sche_nash",
        _base_workload(load, topology, "mixed"),
        {"node_count": node_count, "topology": topology},
        metadata={
            "m1_operational_candidate": candidate,
            "m1_dynamic_contention_family": True,
            "paper_equations_changed": False,
        },
    )


def _baseline_cell(
    method: str, load: str, topology: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"M1DYNAMIC.{method}.{load}.{topology}.n{node_count}",
        method,
        _base_workload(load, topology, "mixed"),
        {"node_count": node_count, "topology": topology},
        metadata={"m1_role": "dynamic_contention_qualification_baseline"},
    )


def build_m1_dynamic_contention_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
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

    cells: list[dict[str, Any]] = []
    for method, load, topology in product(
        M1_DYNAMIC_BASELINES, M1_DYNAMIC_LOADS, M1_DYNAMIC_TOPOLOGIES
    ):
        cells.append(_baseline_cell(method, load, topology, node_count))
    for candidate, load, topology in product(
        M1_DYNAMIC_CANDIDATES, M1_DYNAMIC_LOADS, M1_DYNAMIC_TOPOLOGIES
    ):
        cells.append(_candidate_cell(candidate, load, topology, node_count))

    runs: list[dict[str, Any]] = []
    for cell in cells:
        for seed in M1_DYNAMIC_SEEDS:
            run = _make_run(
                config,
                cell,
                seed,
                common_hpa_hash,
                profiles[cell["workload"]["request_freq"]],
            )
            candidate = cell.get("metadata", {}).get("m1_operational_candidate")
            if candidate is not None:
                _bind_candidate(run, str(candidate))
            runs.append(run)

    execution = copy.deepcopy(config["execution"])
    execution["command_template"] = [
        *execution["command_template"],
        "--simulator-exe",
        runtime["path"],
    ]
    marker = {
        "schema_version": "NSE_M1_DYNAMIC_CONTENTION_MATRIX_V1",
        "purpose": "fresh-bank dynamic-contention completion guard screening",
        "paper_equations_changed": False,
        "formal_seed_overlap": [],
        "prior_development_seed_overlap": [],
        "candidates": list(M1_DYNAMIC_CANDIDATES),
        "control_candidate": "ready_order",
        "qualification_requires_dynamic_winner": True,
        "dynamic_contention_term": "state_without_player_assigned_request_count",
        "baseline_methods": list(M1_DYNAMIC_BASELINES),
        "loads": list(M1_DYNAMIC_LOADS),
        "topologies": list(M1_DYNAMIC_TOPOLOGIES),
        "node_count": node_count,
        "development_seeds": list(M1_DYNAMIC_SEEDS),
        "screen_seeds": list(M1_DYNAMIC_SCREEN_SEEDS),
        "runtime_binary": runtime,
        "run_count": len(runs),
        "cell_count": len(cells),
        "reference_build_count": len(_reference_build_dependencies(runs)),
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.M1.dynamic.D41-D60",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": M1_DYNAMIC_SAMPLE_POLICY,
            "all_seeds": list(M1_DYNAMIC_SEEDS),
            "selected_seeds": list(M1_DYNAMIC_SEEDS),
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
        "execution": execution,
        "qc": copy.deepcopy(config["qc"]),
        "matrix_summary": _matrix_summary(runs),
        "runs": runs,
        "reference_build_dependencies": _reference_build_dependencies(runs),
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": [],
        "m1_dynamic_contention_matrix": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_m1_dynamic_contention_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    manifest = build_m1_dynamic_contention_manifest(
        simulator_exe, source_git_commit, config_path
    )
    write_json_atomic(output_path, manifest)
    return manifest


def derive_m1_dynamic_contention_screen_shard(
    source_path: Path,
) -> dict[str, Any]:
    source_path = source_path.resolve()
    source = load_and_validate_manifest(source_path)
    source_marker = source.get("m1_dynamic_contention_matrix")
    if not isinstance(source_marker, dict):
        raise ProtocolValidationError("dynamic screen requires the complete matrix")
    selected = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["method"] == "sche_nash" and run["seed"] in M1_DYNAMIC_SCREEN_SEEDS
    ]
    if len(selected) != 90:
        raise ProtocolValidationError("dynamic screen is not the frozen 3x6x5 product")
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["bank_id"] = "TSCv1.development.M1.dynamic.screen.D41-D45"
    shard["fixed_seed_bank"]["selected_seeds"] = list(M1_DYNAMIC_SCREEN_SEEDS)
    shard["runs"] = selected
    shard["reference_build_dependencies"] = _reference_build_dependencies(selected)
    shard["matrix_summary"] = _matrix_summary(selected)
    shard.pop("m1_dynamic_contention_matrix", None)
    shard["m1_dynamic_contention_screen_shard"] = {
        "schema_version": "NSE_M1_DYNAMIC_CONTENTION_SCREEN_SHARD_V1",
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "run_count": len(source["runs"]),
        },
        "selection": {
            "method": "sche_nash",
            "candidates": list(M1_DYNAMIC_CANDIDATES),
            "loads": list(M1_DYNAMIC_LOADS),
            "topologies": list(M1_DYNAMIC_TOPOLOGIES),
            "seeds": list(M1_DYNAMIC_SCREEN_SEEDS),
        },
        "runtime_binary": copy.deepcopy(source_marker["runtime_binary"]),
        "paper_equations_changed": False,
        "run_count": len(selected),
        "cell_count": len({run["cell_id"] for run in selected}),
        "reference_build_count": len(_reference_build_dependencies(selected)),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_m1_dynamic_contention_screen_shard(
    source_path: Path, output_path: Path
) -> dict[str, Any]:
    if source_path.resolve() == output_path.resolve():
        raise ProtocolValidationError("dynamic screen output must differ from source")
    shard = derive_m1_dynamic_contention_screen_shard(source_path)
    write_json_atomic(output_path, shard)
    return shard


def analyze_m1_dynamic_contention_screen(
    manifest_path: Path, canonical_root: Path
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("m1_dynamic_contention_screen_shard")
    if not isinstance(marker, dict) or len(manifest["runs"]) != 90:
        raise ProtocolValidationError("dynamic analysis requires the complete screen")

    raw_rows: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for run in manifest["runs"]:
        run_dir = canonical_root / run["run_id"]
        qc_path = run_dir / "qc_report.json"
        summary_path = _canonical_summary_path(canonical_root, run["run_id"])
        if not qc_path.is_file() or not summary_path.is_file():
            raise ProtocolValidationError(f"dynamic run {run['run_id']} is incomplete")
        qc = read_json(qc_path)
        summary_sha = file_hash(summary_path)
        if (
            not isinstance(qc, dict)
            or qc.get("passed") is not True
            or qc.get("result_sha256") != summary_sha
        ):
            raise ProtocolValidationError(f"dynamic run {run['run_id']} failed QC")
        summary = read_json(summary_path)
        if (
            not isinstance(summary, dict)
            or summary.get("schema") != "NSE_SUMMARY_V1"
            or summary.get("run_id") != run["run_id"]
            or summary.get("run_complete") is not True
        ):
            raise ProtocolValidationError(f"dynamic run {run['run_id']} is invalid")
        throughput, qpr, latency, cost = _screen_metrics(summary)
        raw_rows.append(
            {
                "run_id": run["run_id"],
                "seed": run["seed"],
                "candidate": run["metadata"]["m1_operational_candidate"],
                "load": run["workload"]["request_freq"],
                "topology": run["cluster"]["topology"],
                "throughput_requests_per_ms": throughput,
                "qpr": qpr,
                "latency_mean_ms": latency,
                "cost_per_completed_request": cost,
            }
        )
        artifacts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "qc_report_sha256": file_hash(qc_path),
                "summary_sha256": summary_sha,
            }
        )

    aggregates: list[dict[str, Any]] = []
    for candidate, load, topology in product(
        M1_DYNAMIC_CANDIDATES, M1_DYNAMIC_LOADS, M1_DYNAMIC_TOPOLOGIES
    ):
        group = [
            row
            for row in raw_rows
            if row["candidate"] == candidate
            and row["load"] == load
            and row["topology"] == topology
        ]
        if len(group) != 5 or {row["seed"] for row in group} != set(
            M1_DYNAMIC_SCREEN_SEEDS
        ):
            raise ProtocolValidationError(
                f"dynamic group {candidate}/{load}/{topology} is incomplete"
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
    selected, scores = _choose_candidate(
        aggregates,
        candidates=M1_DYNAMIC_CANDIDATES,
        loads=M1_DYNAMIC_LOADS,
        topologies=M1_DYNAMIC_TOPOLOGIES,
    )
    admitted = selected != "ready_order"
    receipt: dict[str, Any] = {
        "schema_version": M1_DYNAMIC_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": (
            "complete_dynamic_screen_family_admitted"
            if admitted
            else "complete_dynamic_screen_family_rejected"
        ),
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "screen_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "development_source_manifest": copy.deepcopy(marker["source_manifest"]),
        "runtime_binary": copy.deepcopy(marker["runtime_binary"]),
        "canonical_root": str(canonical_root),
        "selection_rule": {
            "primary": "maximize minimum candidate-relative mean ratio across throughput and QPR in all six cells",
            "secondary": "maximize mean of the same twelve ratios",
            "tertiary": "maximize cells jointly first in throughput and QPR",
            "final_tie_break": "prefer declared simplicity order",
            "result_conditioned_seed_removal_or_replacement": False,
        },
        "selected_candidate": selected,
        "dynamic_contention_family_admitted": admitted,
        "qualification_authorized": admitted,
        "candidate_scores": scores,
        "cell_aggregates": aggregates,
        "run_metrics": raw_rows,
        "artifact_receipts": artifacts,
        "run_count": len(raw_rows),
    }
    receipt["document_sha256"] = object_hash(receipt)
    return receipt


def write_m1_dynamic_contention_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite dynamic selection")
    receipt = analyze_m1_dynamic_contention_screen(manifest_path, canonical_root)
    write_json_atomic(output_path, receipt)
    return receipt


def _load_selection(path: Path) -> dict[str, Any]:
    selection = read_json(path)
    if (
        not isinstance(selection, dict)
        or selection.get("schema_version") != M1_DYNAMIC_SELECTION_SCHEMA
    ):
        raise ProtocolValidationError("invalid dynamic-contention selection")
    expected = object_hash(
        {key: value for key, value in selection.items() if key != "document_sha256"}
    )
    if selection.get("document_sha256") != expected:
        raise ProtocolValidationError("dynamic selection hash mismatch")
    candidate = selection.get("selected_candidate")
    if candidate not in M1_DYNAMIC_CANDIDATES:
        raise ProtocolValidationError("dynamic selection names an unknown candidate")
    if (
        candidate == "ready_order"
        or selection.get("qualification_authorized") is not True
    ):
        raise ProtocolValidationError(
            "dynamic-contention family was rejected; qualification is forbidden"
        )
    return selection


def derive_m1_dynamic_contention_qualification_shard(
    source_path: Path, selection_path: Path
) -> dict[str, Any]:
    source_path = source_path.resolve()
    selection_path = selection_path.resolve()
    source = load_and_validate_manifest(source_path)
    source_marker = source.get("m1_dynamic_contention_matrix")
    if not isinstance(source_marker, dict):
        raise ProtocolValidationError("dynamic qualification requires complete matrix")
    selection = _load_selection(selection_path)
    source_receipt = selection.get("development_source_manifest")
    if (
        not isinstance(source_receipt, dict)
        or source_receipt.get("manifest_hash") != source["manifest_hash"]
        or source_receipt.get("file_sha256") != file_hash(source_path)
    ):
        raise ProtocolValidationError("dynamic selection does not bind source")
    candidate = str(selection["selected_candidate"])
    selected = [
        copy.deepcopy(run)
        for run in source["runs"]
        if run["method"] in M1_DYNAMIC_BASELINES
        or run.get("metadata", {}).get("m1_operational_candidate") == candidate
    ]
    if len(selected) != 1200:
        raise ProtocolValidationError("dynamic qualification product is incomplete")
    shard = copy.deepcopy(source)
    shard["created_at"] = utc_now()
    shard["phase"] = "qualification"
    shard["bank_id"] = "TSCv1.qualification.M1.dynamic.D41-D60"
    shard["runs"] = selected
    shard["reference_build_dependencies"] = _reference_build_dependencies(selected)
    shard["matrix_summary"] = _matrix_summary(selected)
    shard.pop("m1_dynamic_contention_matrix", None)
    shard["m1_dynamic_contention_qualification_shard"] = {
        "schema_version": "NSE_M1_DYNAMIC_CONTENTION_QUALIFICATION_SHARD_V1",
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
            "loads": list(M1_DYNAMIC_LOADS),
            "topologies": list(M1_DYNAMIC_TOPOLOGIES),
            "seeds": list(M1_DYNAMIC_SEEDS),
        },
        "runtime_binary": copy.deepcopy(source_marker["runtime_binary"]),
        "paper_equations_changed": False,
        "run_count": len(selected),
        "cell_count": len({run["cell_id"] for run in selected}),
        "reference_build_count": len(_reference_build_dependencies(selected)),
    }
    shard.pop("manifest_hash", None)
    shard["manifest_hash"] = object_hash(shard)
    validate_manifest(shard)
    return shard


def write_m1_dynamic_contention_qualification_shard(
    source_path: Path, selection_path: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.resolve() in {source_path.resolve(), selection_path.resolve()}:
        raise ProtocolValidationError("dynamic qualification output must be new")
    shard = derive_m1_dynamic_contention_qualification_shard(
        source_path, selection_path
    )
    write_json_atomic(output_path, shard)
    return shard


def write_m1_dynamic_contention_qualification_report(
    manifest_path: Path,
    canonical_root: Path,
    pairing_audit_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError(
            "refusing to overwrite dynamic qualification report"
        )
    report = analyze_m1_qualification(manifest_path, canonical_root, pairing_audit_path)
    write_json_atomic(output_path, report)
    return report
