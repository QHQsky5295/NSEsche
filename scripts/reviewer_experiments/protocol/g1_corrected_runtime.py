"""Corrected-runtime technical gate and D61--D65 strict-Eq.15 screen.

The G0 executor correction changes every post-cold-start state trajectory, so
none of the D01--D60 references can be promoted.  This module deliberately
keeps the D44 replay technical-only and opens the fresh D61--D65 development
bank only after that replay passes the runtime-contract, reference-pairing,
and analysis gates.
"""

from __future__ import annotations

import copy
import math
from itertools import product
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping

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
    G1_CORRECTED_SCREEN_SAMPLE_POLICY,
    G1_CORRECTED_SCREEN_SEEDS,
    G1_CORRECTED_TECHNICAL_SAMPLE_POLICY,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic
from .workload_profile import load_profile_set


G1_STRICT_CANDIDATES = ("ready_order", "ready_finish_tie", "formula")
G1_LOADS = ("low", "middle", "high")
G1_TOPOLOGIES = ("homogeneous", "heterogeneous")
G1_TECHNICAL_SEED = "D44"
G1_TECHNICAL_CANDIDATE = "ready_order"
G1_TECHNICAL_GATE_SCHEMA = "NSE_G1_CORRECTED_RUNTIME_TECHNICAL_GATE_V1"
G1_SELECTION_SCHEMA = "NSE_G1_CORRECTED_RUNTIME_SELECTION_V1"


def _runtime_execution(
    execution: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(dict(execution))
    command = list(result.get("command_template", []))
    if len(command) >= 2 and command[-2] == "--simulator-exe":
        command = command[:-2]
    command.extend(("--simulator-exe", str(runtime["path"])))
    result["command_template"] = command
    return result


def _strict_metadata(candidate: str, role: str) -> dict[str, Any]:
    return {
        "m1_operational_candidate": candidate,
        "g1_corrected_runtime_role": role,
        "paper_equations_changed": False,
        "strict_best_response": True,
        "utility_guard_relative_regret": 0.0,
    }


def _source_receipt(source_path: Path, source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": str(source_path.resolve()),
        "manifest_hash": source["manifest_hash"],
        "file_sha256": file_hash(source_path),
        "run_count": len(source["runs"]),
    }


def build_g1_corrected_runtime_technical_manifest(
    source_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
) -> dict[str, Any]:
    """Rebind the historical D44 tape to a one-run technical-only replay."""

    source_path = source_path.resolve()
    source = load_and_validate_manifest(source_path)
    runtime = _runtime_receipt(simulator_exe, source_git_commit)
    matches = [
        run
        for run in source["runs"]
        if run["method"] == "sche_nash"
        and run["seed"] == G1_TECHNICAL_SEED
        and run["cluster"].get("topology") == "homogeneous"
        and run["workload"].get("request_freq") == "high"
        and run.get("metadata", {}).get("m1_operational_candidate")
        == G1_TECHNICAL_CANDIDATE
    ]
    if len(matches) != 1:
        raise ProtocolValidationError(
            "G1 technical replay requires exactly one D44 homogeneous/high ready_order source"
        )
    run = copy.deepcopy(matches[0])
    tape = run.get("workload_tape")
    if (
        not isinstance(tape, dict)
        or not isinstance(tape.get("path"), str)
        or not tape["path"]
        or not isinstance(tape.get("sha256"), str)
    ):
        raise ProtocolValidationError("G1 technical source D44 tape must be hash-bound")
    source_run_receipt = {
        "run_id": run["run_id"],
        "run_spec_hash": run["run_spec_hash"],
        "workload_tape_sha256": tape["sha256"],
    }
    run["cell_id"] = "G1TECH.sche_nash.ready_order.high.homogeneous.n20"
    run["metadata"] = _strict_metadata(G1_TECHNICAL_CANDIDATE, "technical_replay")
    _bind_candidate(run, G1_TECHNICAL_CANDIDATE)

    marker = {
        "schema_version": "NSE_G1_CORRECTED_RUNTIME_TECHNICAL_REPLAY_V1",
        "purpose": "D44 same-tape corrected-runtime reference and feedback-contract gate",
        "technical_only": True,
        "selection_eligible": False,
        "formal_results_eligible": False,
        "source_manifest": _source_receipt(source_path, source),
        "source_run": source_run_receipt,
        "candidate": G1_TECHNICAL_CANDIDATE,
        "seed": G1_TECHNICAL_SEED,
        "strict_eq15_required": True,
        "utility_guard_relative_regret": 0.0,
        "runtime_binary": runtime,
        "run_count": 1,
        "cell_count": 1,
        "reference_build_count": 1,
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": source["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.technical.G1.corrected-runtime.D44",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G1_CORRECTED_TECHNICAL_SAMPLE_POLICY,
            "all_seeds": [G1_TECHNICAL_SEED],
            "selected_seeds": [G1_TECHNICAL_SEED],
            "paired_across_methods": True,
            "result_conditioned_extension": False,
        },
        "method_versions": copy.deepcopy(source["method_versions"]),
        "old_pdf_alignment": copy.deepcopy(source["old_pdf_alignment"]),
        "runtime_identity_policy": copy.deepcopy(source["runtime_identity_policy"]),
        "seed_stage": "development",
        "ci_extension_requires_trigger": False,
        "common_hpa": copy.deepcopy(source["common_hpa"]),
        "common_hpa_hash": source["common_hpa_hash"],
        "workload_profile_set": copy.deepcopy(source["workload_profile_set"]),
        "workload_profile_set_hash": source["workload_profile_set_hash"],
        "simulation": copy.deepcopy(source["simulation"]),
        "execution": _runtime_execution(source["execution"], runtime),
        "qc": copy.deepcopy(source["qc"]),
        "matrix_summary": _matrix_summary([run]),
        "runs": [run],
        "reference_build_dependencies": _reference_build_dependencies([run]),
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": [],
        "g1_corrected_runtime_technical_replay": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g1_corrected_runtime_technical_manifest(
    source_path: Path,
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G1 technical manifest")
    manifest = build_g1_corrected_runtime_technical_manifest(
        source_path, simulator_exe, source_git_commit
    )
    write_json_atomic(output_path, manifest)
    return manifest


def _audit_runtime_identity(audit: Mapping[str, Any]) -> dict[str, Any]:
    software = audit.get("software_environment")
    adapter = audit.get("adapter_binary")
    git = software.get("git") if isinstance(software, Mapping) else None
    if not isinstance(git, Mapping) or not isinstance(adapter, Mapping):
        raise ProtocolValidationError("technical replay lacks runtime audit evidence")
    return {
        "source_git_commit": git.get("commit"),
        "sha256": adapter.get("verified_sha256"),
        "bytes": adapter.get("bytes"),
        "path": adapter.get("path"),
    }


def admit_g1_corrected_runtime_technical_replay(
    manifest_path: Path, canonical_root: Path
) -> dict[str, Any]:
    """Validate the real D44 replay and return a hash-sealed gate receipt."""

    from ..analysis.formal_inputs import validate_canonical_run
    from ..analysis.observability import analyze_scheduler_run, load_run_artifacts

    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("g1_corrected_runtime_technical_replay")
    if not isinstance(marker, dict) or len(manifest["runs"]) != 1:
        raise ProtocolValidationError("technical gate requires the one-run G1 manifest")
    run = manifest["runs"][0]
    run_dir = canonical_root / run["run_id"]
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    qc = validate_canonical_run(
        run,
        run_dir,
        expected_manifest_hash=manifest["manifest_hash"],
        result_relative_path=result_relative_path,
    )
    contract = qc.get("observations", {}).get("nash_runtime_contract")
    if (
        not isinstance(contract, Mapping)
        or contract.get("declared") is not True
        or contract.get("strict_eq15_ready") is not True
        or contract.get("stream_contract_ready") is not True
        or not isinstance(contract.get("feedback_trace_rounds"), int)
        or contract["feedback_trace_rounds"] <= 0
    ):
        raise ProtocolValidationError(
            "technical replay failed the real-stream formula contract"
        )
    pairing = qc.get("observations", {}).get("reference_pairing")
    if (
        not isinstance(pairing, Mapping)
        or pairing.get("policy_window_count") != contract.get("policy_windows")
        or pairing.get("build_completed") != pairing.get("replay_completed")
    ):
        raise ProtocolValidationError("technical replay failed reference pairing")

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
        or not isinstance(diagnostics.get("feedback_trace_rounds"), int)
        or diagnostics["feedback_trace_rounds"] <= 0
    ):
        raise ProtocolValidationError("technical replay failed feedback-trace analysis")

    audit_path = run_dir / "manifest.json"
    audit = read_json(audit_path)
    if not isinstance(audit, Mapping):
        raise ProtocolValidationError("technical replay audit manifest is invalid")
    runtime = _audit_runtime_identity(audit)
    expected_runtime = marker["runtime_binary"]
    if any(runtime.get(key) != expected_runtime.get(key) for key in runtime):
        raise ProtocolValidationError(
            "technical replay runtime differs from frozen binary"
        )

    summary_path = _canonical_summary_path(canonical_root, run["run_id"])
    receipt: dict[str, Any] = {
        "schema_version": G1_TECHNICAL_GATE_SCHEMA,
        "created_at": utc_now(),
        "status": "technical_gate_passed",
        "technical_only": True,
        "selection_eligible": False,
        "formal_results_eligible": False,
        "technical_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "canonical_run": {
            "path": str(run_dir),
            "run_id": run["run_id"],
            "run_spec_hash": run["run_spec_hash"],
            "summary_sha256": file_hash(summary_path),
            "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
            "audit_manifest_sha256": file_hash(audit_path),
        },
        "runtime_binary": copy.deepcopy(expected_runtime),
        "nash_runtime_contract": copy.deepcopy(dict(contract)),
        "reference_pairing": copy.deepcopy(dict(pairing)),
        "analysis": {
            key: diagnostics.get(key)
            for key in (
                "feedback_trace_status",
                "feedback_trace_rounds",
                "feedback_applied_rounds",
                "feedback_trace_invalid_rows",
                "nonconvergence_rate",
                "inner_limit_hit_rate",
                "outer_limit_hit_rate",
            )
        },
    }
    receipt["document_sha256"] = object_hash(receipt)
    return receipt


def write_g1_corrected_runtime_technical_gate(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G1 technical gate")
    receipt = admit_g1_corrected_runtime_technical_replay(manifest_path, canonical_root)
    write_json_atomic(output_path, receipt)
    return receipt


def _load_technical_gate(
    path: Path, expected_runtime: Mapping[str, Any]
) -> dict[str, Any]:
    value = read_json(path)
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != G1_TECHNICAL_GATE_SCHEMA
    ):
        raise ProtocolValidationError("invalid G1 technical gate schema")
    claimed = value.get("document_sha256")
    payload = {key: item for key, item in value.items() if key != "document_sha256"}
    if claimed != object_hash(payload):
        raise ProtocolValidationError("G1 technical gate document hash mismatch")
    if (
        value.get("status") != "technical_gate_passed"
        or value.get("technical_only") is not True
        or value.get("selection_eligible") is not False
        or value.get("formal_results_eligible") is not False
        or value.get("runtime_binary") != dict(expected_runtime)
    ):
        raise ProtocolValidationError("G1 technical gate does not admit this runtime")
    contract = value.get("nash_runtime_contract")
    if (
        not isinstance(contract, dict)
        or contract.get("stream_contract_ready") is not True
    ):
        raise ProtocolValidationError(
            "G1 technical gate lacks stream_contract_ready=true"
        )
    return value


def _candidate_cell(
    candidate: str, load: str, topology: str, node_count: int
) -> dict[str, Any]:
    return _make_cell(
        "E1",
        f"G1SCREEN.sche_nash.{candidate}.{load}.{topology}.n{node_count}",
        "sche_nash",
        _base_workload(load, topology, "mixed"),
        {"node_count": node_count, "topology": topology},
        metadata=_strict_metadata(candidate, "candidate_screen"),
    )


def build_g1_corrected_runtime_screen_manifest(
    simulator_exe: Path,
    source_git_commit: str,
    technical_gate_path: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    config = load_protocol_config(config_path)
    runtime = _runtime_receipt(simulator_exe, source_git_commit)
    technical_gate_path = technical_gate_path.resolve()
    gate = _load_technical_gate(technical_gate_path, runtime)
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

    cells = [
        _candidate_cell(candidate, load, topology, node_count)
        for candidate, load, topology in product(
            G1_STRICT_CANDIDATES, G1_LOADS, G1_TOPOLOGIES
        )
    ]
    runs: list[dict[str, Any]] = []
    for cell in cells:
        candidate = str(cell["metadata"]["m1_operational_candidate"])
        for seed in G1_CORRECTED_SCREEN_SEEDS:
            run = _make_run(
                config,
                cell,
                seed,
                common_hpa_hash,
                profiles[cell["workload"]["request_freq"]],
            )
            _bind_candidate(run, candidate)
            runs.append(run)

    marker = {
        "schema_version": "NSE_G1_CORRECTED_RUNTIME_SCREEN_V1",
        "purpose": "fresh-bank strict-Eq.15 corrected-runtime candidate screen",
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "utility_guard_relative_regret": 0.0,
        "candidates": list(G1_STRICT_CANDIDATES),
        "control_candidate": "ready_order",
        "loads": list(G1_LOADS),
        "topologies": list(G1_TOPOLOGIES),
        "screen_seeds": list(G1_CORRECTED_SCREEN_SEEDS),
        "technical_gate": {
            "path": str(technical_gate_path),
            "file_sha256": file_hash(technical_gate_path),
            "document_sha256": gate["document_sha256"],
            "technical_manifest_hash": gate["technical_manifest"]["manifest_hash"],
        },
        "runtime_binary": runtime,
        "selection_rule": {
            "primary": "maximize minimum candidate/control mean ratio across throughput and QPR in all six cells",
            "secondary": "maximize mean of the same twelve candidate/control ratios",
            "tertiary": "maximize six-cell joint throughput-and-QPR first places",
            "final_tie_break": "prefer declared C0-C1-C2 simplicity order",
            "result_conditioned_seed_removal_or_replacement": False,
        },
        "run_count": len(runs),
        "cell_count": len(cells),
        "reference_build_count": len(_reference_build_dependencies(runs)),
    }
    execution = _runtime_execution(config["execution"], runtime)
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": config["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.development.G1.corrected-runtime.screen.D61-D65",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G1_CORRECTED_SCREEN_SAMPLE_POLICY,
            "all_seeds": list(G1_CORRECTED_SCREEN_SEEDS),
            "selected_seeds": list(G1_CORRECTED_SCREEN_SEEDS),
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
        "g1_corrected_runtime_screen": marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g1_corrected_runtime_screen_manifest(
    output_path: Path,
    simulator_exe: Path,
    source_git_commit: str,
    technical_gate_path: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G1 screen manifest")
    manifest = build_g1_corrected_runtime_screen_manifest(
        simulator_exe, source_git_commit, technical_gate_path, config_path
    )
    write_json_atomic(output_path, manifest)
    return manifest


def _choose_g1_candidate(
    aggregates: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in aggregates:
        by_cell.setdefault((row["load"], row["topology"]), []).append(row)
    expected_cells = set(product(G1_LOADS, G1_TOPOLOGIES))
    if set(by_cell) != expected_cells:
        raise ProtocolValidationError("G1 aggregates do not cover all six cells")
    scores: list[dict[str, Any]] = []
    for candidate in G1_STRICT_CANDIDATES:
        ratios: list[float] = []
        dual_first = 0
        for cell in sorted(expected_cells):
            rows = by_cell[cell]
            if {row["candidate"] for row in rows} != set(G1_STRICT_CANDIDATES):
                raise ProtocolValidationError(f"G1 aggregate is incomplete for {cell}")
            control = next(row for row in rows if row["candidate"] == "ready_order")
            current = next(row for row in rows if row["candidate"] == candidate)
            for metric in (
                "mean_throughput_requests_per_ms",
                "mean_qpr",
            ):
                denominator = float(control[metric])
                if not math.isfinite(denominator) or denominator <= 0.0:
                    raise ProtocolValidationError("G1 control metric is not applicable")
                ratios.append(float(current[metric]) / denominator)
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
                "simplicity_order": G1_STRICT_CANDIDATES.index(candidate),
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


def analyze_g1_corrected_runtime_screen(
    manifest_path: Path, canonical_root: Path
) -> dict[str, Any]:
    from ..analysis.observability import analyze_scheduler_run, load_run_artifacts

    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("g1_corrected_runtime_screen")
    if not isinstance(marker, dict) or len(manifest["runs"]) != 90:
        raise ProtocolValidationError("G1 analysis requires the complete 90-run screen")

    raw_rows: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    for run in manifest["runs"]:
        run_dir = canonical_root / run["run_id"]
        qc_path = run_dir / "qc_report.json"
        summary_path = _canonical_summary_path(canonical_root, run["run_id"])
        if not qc_path.is_file() or not summary_path.is_file():
            raise ProtocolValidationError(f"G1 run {run['run_id']} is incomplete")
        qc = read_json(qc_path)
        summary_sha = file_hash(summary_path)
        contract = (
            qc.get("observations", {}).get("nash_runtime_contract")
            if isinstance(qc, dict)
            else None
        )
        if (
            not isinstance(qc, dict)
            or qc.get("passed") is not True
            or qc.get("result_sha256") != summary_sha
            or not isinstance(contract, dict)
            or contract.get("strict_eq15_ready") is not True
            or contract.get("stream_contract_ready") is not True
        ):
            raise ProtocolValidationError(f"G1 run {run['run_id']} failed QC/contract")
        summary = read_json(summary_path)
        if (
            not isinstance(summary, dict)
            or summary.get("schema") != "NSE_SUMMARY_V1"
            or summary.get("run_id") != run["run_id"]
            or summary.get("run_complete") is not True
        ):
            raise ProtocolValidationError(f"G1 run {run['run_id']} has invalid summary")
        throughput, qpr, latency, cost = _screen_metrics(summary)
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
                f"G1 run {run['run_id']} failed trace analysis"
            )
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
                "completion_ratio": summary.get("completion_ratio"),
                "queue_peak": summary.get("queue_peak"),
                "queue_area_request_frames": summary.get("queue_area_request_frames"),
                "nonconvergence_rate": diagnostics.get("nonconvergence_rate"),
                "inner_limit_hit_rate": diagnostics.get("inner_limit_hit_rate"),
                "outer_limit_hit_rate": diagnostics.get("outer_limit_hit_rate"),
                "feedback_trace_rounds": diagnostics.get("feedback_trace_rounds"),
                "feedback_applied_rounds": diagnostics.get("feedback_applied_rounds"),
            }
        )
        artifacts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "qc_report_sha256": file_hash(qc_path),
                "summary_sha256": summary_sha,
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
            }
        )

    aggregates: list[dict[str, Any]] = []
    for candidate, load, topology in product(
        G1_STRICT_CANDIDATES, G1_LOADS, G1_TOPOLOGIES
    ):
        group = [
            row
            for row in raw_rows
            if row["candidate"] == candidate
            and row["load"] == load
            and row["topology"] == topology
        ]
        if len(group) != 5 or {row["seed"] for row in group} != set(
            G1_CORRECTED_SCREEN_SEEDS
        ):
            raise ProtocolValidationError(
                f"G1 group {candidate}/{load}/{topology} is incomplete"
            )
        aggregates.append(
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
                "mean_queue_peak": fmean(float(row["queue_peak"]) for row in group),
                "mean_nonconvergence_rate": fmean(
                    float(row["nonconvergence_rate"]) for row in group
                ),
            }
        )
    selected, scores = _choose_g1_candidate(aggregates)
    receipt: dict[str, Any] = {
        "schema_version": G1_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": "complete_corrected_runtime_screen_selected",
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "screen_manifest": {
            "path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "file_sha256": file_hash(manifest_path),
        },
        "technical_gate": copy.deepcopy(marker["technical_gate"]),
        "runtime_binary": copy.deepcopy(marker["runtime_binary"]),
        "selection_rule": copy.deepcopy(marker["selection_rule"]),
        "selected_candidate": selected,
        "qualification_authorized_by_screen": True,
        "candidate_scores": scores,
        "cell_aggregates": aggregates,
        "run_metrics": raw_rows,
        "artifact_receipts": artifacts,
        "run_count": len(raw_rows),
    }
    receipt["document_sha256"] = object_hash(receipt)
    return receipt


def write_g1_corrected_runtime_selection(
    manifest_path: Path, canonical_root: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite G1 selection receipt")
    receipt = analyze_g1_corrected_runtime_screen(manifest_path, canonical_root)
    write_json_atomic(output_path, receipt)
    return receipt
