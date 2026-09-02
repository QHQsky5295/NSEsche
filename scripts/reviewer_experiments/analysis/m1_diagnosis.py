"""Audit and summarize the fixed decision-neutral M1 warm-path diagnosis."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..protocol.ledger import verify_ledger
from ..protocol.schema import ProtocolValidationError, load_and_validate_manifest
from ..protocol.util import file_hash, object_hash, read_json, utc_now, write_json_atomic
from .formal_inputs import validate_canonical_run


REPORT_SCHEMA = "NSE_M1_WARM_PATH_DIAGNOSIS_REPORT_V1"
DECISION_SEMANTIC_FIELDS = (
    "assigned_node_count",
    "assigned_players",
    "assignment_hash",
    "candidate_evaluations",
    "commands_prepared",
    "commands_sent",
    "complete_assignment",
    "dispatch_channel_failed",
    "initial_assignment_hash",
    "initialization_evaluations",
    "invalid_assignments",
    "no_feasible_players",
    "pending_request_function_pairs",
    "request_function_players",
    "scale_ups_prepared",
    "scale_ups_sent",
    "unique_functions",
    "waiting_for_candidate_nodes",
)
SUMMARY_TIMING_FIELDS = frozenset(
    {
        "scheduler_wall_ns",
        "scheduler_thread_cpu_ns",
        "placement_policy_wall_ns",
        "placement_policy_thread_cpu_ns",
        "posthoc_welfare_evaluation_wall_ns",
        "posthoc_welfare_evaluation_thread_cpu_ns",
    }
)
SOCIAL_TIMING_FIELDS = frozenset(
    {"reference_compute_us", "reference_lookup_us", "reference_persist_us"}
)
INTEGER_DIAGNOSTIC_FIELDS = (
    "assigned_players",
    "request_function_players",
    "selected_running_warm_players",
    "selected_starting_container_players",
    "selected_cold_or_nonrunning_players",
    "running_warm_available_players",
    "running_warm_bypassed_players",
    "selected_lower_utility_than_warm_players",
)
SUM_DIAGNOSTIC_FIELDS = (
    "warm_bypass_utility_advantage_sum",
    "warm_bypass_finish_score_delta_sum",
)


def _normalized(value: Any, run_id: str) -> Any:
    if isinstance(value, dict):
        return {key: _normalized(item, run_id) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalized(item, run_id) for item in value]
    if isinstance(value, str):
        return value.replace(run_id, "__RUN_ID__")
    return value


def _hash_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    for row in rows:
        encoded = json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
        count += 1
    return count, digest.hexdigest()


def _read_gzip_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProtocolValidationError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise ProtocolValidationError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            yield row


def _artifact_path(run_dir: Path, run_id: str, name: str) -> Path:
    path = run_dir / "reviewer_records" / run_id / name
    if not path.is_file():
        raise ProtocolValidationError(f"missing canonical artifact: {path}")
    return path


def _stream_signature(path: Path, run_id: str) -> dict[str, Any]:
    count, digest = _hash_rows(
        _normalized(row, run_id) for row in _read_gzip_jsonl(path)
    )
    return {"records": count, "semantic_sha256": digest}


def _summary_semantic_payload(summary: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    payload = copy.deepcopy(dict(summary))
    payload.pop("run_id", None)
    for field in SUMMARY_TIMING_FIELDS:
        payload.pop(field, None)
    return _normalized(payload, run_id)


def _window_semantic_payload(row: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    payload = copy.deepcopy(dict(row))
    payload.pop("overhead", None)
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        raise ProtocolValidationError("NSESche window lacks a decision object")
    # The remaining decision fields in the raw record are derived placement
    # observability (dispersion, near ties, differentiation diagnostics).  They
    # do not feed dispatch and can differ by one f32 ULP because their HashMap
    # reductions are not order-stable across processes.  Bind the actual
    # assignment, command, feasibility, and solver-work outcome explicitly.
    payload["decision"] = {
        field: decision[field]
        for field in DECISION_SEMANTIC_FIELDS
        if field in decision
    }
    social = payload.get("social")
    if isinstance(social, dict):
        for field in SOCIAL_TIMING_FIELDS:
            social.pop(field, None)
    return _normalized(payload, run_id)


def _nash_signature(
    path: Path, run_id: str, *, collect_diagnostics: bool
) -> dict[str, Any]:
    window_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    lower_utility_windows: list[dict[str, Any]] = []
    run_config_seen = False

    for row in _read_gzip_jsonl(path):
        kind = row.get("kind")
        if kind == "run_config":
            run_config_seen = True
            if collect_diagnostics and row.get("decision_neutral_diagnostics") != {
                "warm_path_schema": 1,
                "decision_feedback": False,
                "counterfactual": "selected_paper_utility_minus_best_running_warm_paper_utility_over_common_candidates",
            }:
                raise ProtocolValidationError(
                    f"diagnostic run {run_id} lacks the sealed warm-path schema"
                )
        elif kind == "function_profile":
            profile_rows.append(_normalized(row, run_id))
        elif kind == "window":
            window_rows.append(_window_semantic_payload(row, run_id))
            if not collect_diagnostics:
                continue
            decision = row.get("decision")
            solver = row.get("solver")
            if not isinstance(decision, dict) or not isinstance(solver, dict):
                raise ProtocolValidationError(
                    f"diagnostic window in {run_id} lacks decision/solver data"
                )
            for field in INTEGER_DIAGNOSTIC_FIELDS:
                value = decision.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ProtocolValidationError(
                        f"diagnostic field {field} is invalid in {run_id}"
                    )
                counters[field] += value
            for field in SUM_DIAGNOSTIC_FIELDS:
                value = decision.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ProtocolValidationError(
                        f"diagnostic field {field} is invalid in {run_id}"
                    )
                counters[field] += float(value)
            lower = int(decision["selected_lower_utility_than_warm_players"])
            if lower:
                lower_utility_windows.append(
                    {
                        "frame": row.get("frame"),
                        "window": row.get("window"),
                        "player_count": lower,
                        "warm_available_players": decision[
                            "running_warm_available_players"
                        ],
                        "warm_bypassed_players": decision[
                            "running_warm_bypassed_players"
                        ],
                        "utility_advantage_sum": decision[
                            "warm_bypass_utility_advantage_sum"
                        ],
                        "finish_score_delta_sum": decision[
                            "warm_bypass_finish_score_delta_sum"
                        ],
                        "solver": copy.deepcopy(solver),
                    }
                )

    if not run_config_seen:
        raise ProtocolValidationError(f"NSESche stream has no run_config: {path}")
    window_count, window_hash = _hash_rows(window_rows)
    profile_count, profile_hash = _hash_rows(profile_rows)
    result: dict[str, Any] = {
        "window_count": window_count,
        "window_semantic_sha256": window_hash,
        "function_profile_count": profile_count,
        "function_profile_semantic_sha256": profile_hash,
    }
    if collect_diagnostics:
        result["diagnostics"] = dict(counters)
        result["lower_utility_windows"] = lower_utility_windows
    return result


def _finalize_aggregate(counters: Mapping[str, int | float]) -> dict[str, Any]:
    result = {field: int(counters.get(field, 0)) for field in INTEGER_DIAGNOSTIC_FIELDS}
    for field in SUM_DIAGNOSTIC_FIELDS:
        result[field] = float(counters.get(field, 0.0))
    assigned = result["assigned_players"]
    selected_total = (
        result["selected_running_warm_players"]
        + result["selected_starting_container_players"]
        + result["selected_cold_or_nonrunning_players"]
    )
    available = result["running_warm_available_players"]
    bypassed = result["running_warm_bypassed_players"]
    if selected_total != assigned:
        raise ProtocolValidationError(
            f"selected path counts {selected_total} do not conserve {assigned} assignments"
        )
    if available != result["selected_running_warm_players"] + bypassed:
        raise ProtocolValidationError(
            "running-warm availability does not partition into selected plus bypassed"
        )
    if result["selected_lower_utility_than_warm_players"] > bypassed:
        raise ProtocolValidationError("lower-utility count exceeds warm bypass count")
    result.update(
        {
            "warm_availability_share_of_assigned": (
                available / assigned if assigned else None
            ),
            "warm_bypass_share_of_warm_available": (
                bypassed / available if available else None
            ),
            "selected_running_warm_share": (
                result["selected_running_warm_players"] / assigned
                if assigned
                else None
            ),
            "selected_starting_container_share": (
                result["selected_starting_container_players"] / assigned
                if assigned
                else None
            ),
            "warm_bypass_utility_advantage_mean": (
                result["warm_bypass_utility_advantage_sum"] / bypassed
                if bypassed
                else None
            ),
            "warm_bypass_finish_score_delta_mean": (
                result["warm_bypass_finish_score_delta_sum"] / bypassed
                if bypassed
                else None
            ),
        }
    )
    return result


def analyze_m1_diagnosis(
    manifest_path: Path,
    canonical_root: Path,
    source_canonical_root: Path,
    ledger_path: Path,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    canonical_root = canonical_root.resolve()
    source_canonical_root = source_canonical_root.resolve()
    ledger_path = ledger_path.resolve()
    manifest = load_and_validate_manifest(manifest_path)
    marker = manifest.get("m1_mechanism_diagnosis_shard")
    if not isinstance(marker, dict) or len(manifest["runs"]) != 30:
        raise ProtocolValidationError(
            "M1 diagnosis analysis requires the complete fixed 30-run shard"
        )
    source_receipt = marker.get("source_manifest")
    if not isinstance(source_receipt, dict):
        raise ProtocolValidationError("M1 diagnosis source receipt is missing")
    source_path = Path(str(source_receipt.get("path", ""))).resolve()
    if (
        file_hash(source_path) != source_receipt.get("file_sha256")
        or read_json(source_path).get("manifest_hash")
        != source_receipt.get("manifest_hash")
    ):
        raise ProtocolValidationError("M1 diagnosis source manifest changed")
    source = load_and_validate_manifest(source_path)
    source_runs = {run["run_id"]: run for run in source["runs"]}
    ledger_events, ledger_hash = verify_ledger(ledger_path)

    result_relative_path = manifest["execution"]["result_relative_path"]
    source_result_relative_path = source["execution"]["result_relative_path"]
    cell_counters: dict[tuple[str, str], Counter[str]] = {}
    total_counters: Counter[str] = Counter()
    lower_utility_windows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    runtime_identities: set[tuple[str, str, str]] = set()

    for run in manifest["runs"]:
        run_id = run["run_id"]
        source_run_id = run.get("metadata", {}).get("source_qualification_run_id")
        source_run = source_runs.get(source_run_id)
        if not isinstance(source_run, dict):
            raise ProtocolValidationError(f"unknown source qualification run: {source_run_id}")
        if (
            source_run.get("run_spec_hash")
            != run["metadata"].get("source_qualification_run_spec_hash")
        ):
            raise ProtocolValidationError(f"source run hash mismatch for {run_id}")
        run_dir = canonical_root / run_id
        source_dir = source_canonical_root / str(source_run_id)
        validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        validate_canonical_run(
            source_run,
            source_dir,
            expected_manifest_hash=source["manifest_hash"],
            result_relative_path=source_result_relative_path,
        )

        summary_path = run_dir / result_relative_path.format(run_id=run_id)
        source_summary_path = source_dir / source_result_relative_path.format(
            run_id=source_run_id
        )
        summary = read_json(summary_path)
        source_summary = read_json(source_summary_path)
        summary_hash = object_hash(_summary_semantic_payload(summary, run_id))
        source_summary_hash = object_hash(
            _summary_semantic_payload(source_summary, str(source_run_id))
        )
        if summary_hash != source_summary_hash:
            raise ProtocolValidationError(
                f"decision-neutral summary mismatch for {run_id}"
            )

        stream_receipts: dict[str, Any] = {}
        for artifact in ("frames.jsonl.gz", "requests.jsonl.gz"):
            current_signature = _stream_signature(
                _artifact_path(run_dir, run_id, artifact), run_id
            )
            source_signature = _stream_signature(
                _artifact_path(source_dir, str(source_run_id), artifact),
                str(source_run_id),
            )
            if current_signature != source_signature:
                raise ProtocolValidationError(
                    f"decision-neutral {artifact} mismatch for {run_id}"
                )
            stream_receipts[artifact] = current_signature

        nash = _nash_signature(
            _artifact_path(run_dir, run_id, "nash_metrics.jsonl.gz"),
            run_id,
            collect_diagnostics=True,
        )
        source_nash = _nash_signature(
            _artifact_path(source_dir, str(source_run_id), "nash_metrics.jsonl.gz"),
            str(source_run_id),
            collect_diagnostics=False,
        )
        for field in (
            "window_count",
            "window_semantic_sha256",
            "function_profile_count",
            "function_profile_semantic_sha256",
        ):
            if nash[field] != source_nash[field]:
                raise ProtocolValidationError(
                    f"decision-neutral NSESche {field} mismatch for {run_id}"
                )

        diagnostics = nash["diagnostics"]
        cell = (run["cluster"]["topology"], run["workload"]["request_freq"])
        cell_counters.setdefault(cell, Counter()).update(diagnostics)
        total_counters.update(diagnostics)
        for window in nash["lower_utility_windows"]:
            lower_utility_windows.append(
                {
                    "run_id": run_id,
                    "source_qualification_run_id": source_run_id,
                    "seed": run["seed"],
                    "topology": cell[0],
                    "load": cell[1],
                    **window,
                }
            )

        adapter_path = run_dir / "adapter_observation.json"
        audit_path = run_dir / "manifest.json"
        adapter = read_json(adapter_path)
        audit = read_json(audit_path)
        git = audit.get("software_environment", {}).get("git", {})
        runtime_identities.add(
            (
                str(adapter.get("server_executable_sha256")),
                str(git.get("commit")),
                str(adapter.get("python_helper_interpreter_sha256")),
            )
        )
        receipts.append(
            {
                "run_id": run_id,
                "source_qualification_run_id": source_run_id,
                "seed": run["seed"],
                "topology": cell[0],
                "load": cell[1],
                "summary_semantic_sha256": summary_hash,
                "streams": stream_receipts,
                "nash_window_count": nash["window_count"],
                "nash_window_semantic_sha256": nash["window_semantic_sha256"],
                "function_profile_count": nash["function_profile_count"],
                "function_profile_semantic_sha256": nash[
                    "function_profile_semantic_sha256"
                ],
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "audit_manifest_sha256": file_hash(audit_path),
                "adapter_observation_sha256": file_hash(adapter_path),
            }
        )

    if len(runtime_identities) != 1:
        raise ProtocolValidationError("diagnostic runtime identity is inconsistent")
    binary_hash, git_commit, python_hash = next(iter(runtime_identities))
    cells = []
    for topology in ("homogeneous", "heterogeneous"):
        for load in ("low", "middle", "high"):
            counters = cell_counters.get((topology, load))
            if counters is None:
                raise ProtocolValidationError(f"missing diagnostic cell {topology}/{load}")
            cells.append(
                {
                    "topology": topology,
                    "load": load,
                    "run_count": 5,
                    **_finalize_aggregate(counters),
                }
            )
    totals = _finalize_aggregate(total_counters)
    lower_player_total = totals["selected_lower_utility_than_warm_players"]
    lower_in_inner_limit = sum(
        int(window["player_count"])
        for window in lower_utility_windows
        if window["solver"].get("inner_limit_hit") is True
        and window["solver"].get("termination") == "inner_iteration_limit"
    )

    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": "complete",
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "diagnosis_has_no_performance_pass_fail_threshold": True,
        "manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "source_qualification_manifest": {
            "path": str(source_path),
            "file_sha256": file_hash(source_path),
            "manifest_hash": source["manifest_hash"],
        },
        "canonical_root": str(canonical_root),
        "source_canonical_root": str(source_canonical_root),
        "ledger": {
            "path": str(ledger_path),
            "event_count": ledger_events,
            "last_hash": ledger_hash,
        },
        "runtime_identity": {
            "server_executable_sha256": binary_hash,
            "git_commit": git_commit,
            "python_interpreter_sha256": python_hash,
        },
        "run_count": len(receipts),
        "cell_count": len(cells),
        "decision_neutrality": {
            "passed": True,
            "paired_run_count": len(receipts),
            "summary_semantic_match_count": len(receipts),
            "frame_stream_semantic_match_count": len(receipts),
            "request_stream_semantic_match_count": len(receipts),
            "nash_window_semantic_match_count": len(receipts),
            "total_paired_nash_windows": sum(
                receipt["nash_window_count"] for receipt in receipts
            ),
        },
        "cells": cells,
        "totals": totals,
        "lower_utility_windows": lower_utility_windows,
        "termination_edge": {
            "selected_lower_utility_than_warm_players": lower_player_total,
            "players_in_inner_iteration_limit_windows": lower_in_inner_limit,
            "all_lower_utility_players_in_inner_iteration_limit_windows": (
                lower_player_total > 0 and lower_player_total == lower_in_inner_limit
            ),
            "best_response_ranking_defect_established": False,
            "reason": "the observed lower-utility final assignments occur only after the bounded inner loop returns its best-social-welfare state without Nash stability",
        },
        "run_receipts": receipts,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_m1_diagnosis_report(
    manifest_path: Path,
    canonical_root: Path,
    source_canonical_root: Path,
    ledger_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite an M1 diagnosis report")
    report = analyze_m1_diagnosis(
        manifest_path, canonical_root, source_canonical_root, ledger_path
    )
    write_json_atomic(output_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("canonical_root", type=Path)
    parser.add_argument("source_canonical_root", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = write_m1_diagnosis_report(
            args.manifest,
            args.canonical_root,
            args.source_canonical_root,
            args.ledger,
            args.output,
        )
    except (OSError, ProtocolValidationError, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "status": report["status"],
                "run_count": report["run_count"],
                "cell_count": report["cell_count"],
                "decision_neutral": report["decision_neutrality"]["passed"],
                "document_sha256": report["document_sha256"],
                "output": str(args.output.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
