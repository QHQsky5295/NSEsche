"""Read-only P3 diagnosis of the complete retained P2 low-load population."""

from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..protocol.m1_qualification import _canonical_summary_path
from ..protocol.p2_low_hyperparameter_recovery import P2_LOW_SETTING_LABELS
from ..protocol.schema import (
    P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS,
    ProtocolValidationError,
)
from ..protocol.util import (
    directory_tree_inventory,
    file_hash,
    object_hash,
    read_json,
    replace_atomic,
    utc_now,
    write_json_atomic,
)
from . import p2_low_hyperparameter_recovery as p2
from .formal_inputs import validate_canonical_run
from .observability import load_run_artifacts


SELECTION_SCHEMA = "NSE_P3_LOW_ROOT_CAUSE_SELECTION_V1"
REPORT_SCHEMA = "NSE_P3_LOW_ROOT_CAUSE_DIAGNOSIS_V1"
EXPECTED_RUN_COUNT = 25
EXPECTED_WINDOW_COUNT = 1000
CENTRE = "centre"
R0_NEIGHBOURS = ("r0_minus", "r0_plus")
WQ_NEIGHBOURS = ("wq_minus", "wq_plus")
METRIC_FIELDS = (
    "throughput_requests_per_ms",
    "qpr",
    "completion_ratio",
    "latency_mean_ms",
)
UTILITY_COMPONENTS = (
    "baseline_reward",
    "contribution",
    "cost",
    "externality",
    "quality",
)

EXPECTED_READY_FILE = "544d884bdb4d990115213ef13fce19de24ab20f899588e5666e96de375823568"
EXPECTED_READY_DOCUMENT = (
    "8e89bca4604f17ef9dc28e2e09887b6070fed971e6a560903c00cf7281320758"
)
EXPECTED_P2_SELECTION_FILE = (
    "97a8fed754a2980726e5eb6984b36f279a72fbd17cecc7b788639e4dc62586be"
)
EXPECTED_P2_SELECTION_DOCUMENT = (
    "d6daefea4e7a49df6a6a71285aeab461591329555748df921ae85c0cc2d482e3"
)
EXPECTED_GATE_FILE = "02cf7e36cdccc3969bc690ac028069d3de7870cdc06759dc6b1b0aad25d5a1a9"
EXPECTED_GATE_DOCUMENT = (
    "7f6a074926580f548b224e595df0739cb8a7f7af5d0d6615fd11ddb2ddcbb1c3"
)
EXPECTED_CANONICAL_FILES = 375
EXPECTED_CANONICAL_BYTES = 23_386_180
EXPECTED_CANONICAL_INVENTORY = (
    "7a06b6a3ce83ef8c4beea21f0f26b1f486c1a87a671c075c3e46565383fd1e98"
)
EXPECTED_P2_ANALYZER = (
    "cd67e563e1c64a7195d0c0f5c3061f11eb57fedb9297c4131e24758fee626d5f"
)
EXPECTED_SCHEDULER_SOURCE = (
    "8423e3bdffbe18aaf72faa39926e099cc99fc7eda3b7b3759a45c3e26f0aa949"
)
PREREG_COMMIT = "5dca3a21acad8281db9fce69c6ac2097e0394805"
EXPECTED_PREREG_FILE = (
    "a4c565889c55f489c5aba2f8b92c6b837d571956b8fbce1b53214370338ed492"
)
CONTEXT_AUDITS = {
    "G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md": (
        "9376c7202a01de1b3706ed92d68f90580ef576ab7b780c8e74cad5028e9b5c16"
    ),
    "G3_EXISTING_LOG_DIAGNOSIS_AUDIT.md": (
        "c56a3b5d2ba51667f8871555097b565bbd49a1d2a2678a2a0137141c93e22ed3"
    ),
    "G4_HOM_LOW_LATENCY_RESULT_AND_SOURCE_AUDIT.md": (
        "36212b99bb8eeb62c83886c17ec2d0973c2cdc8381dd8fefce29cb8ae00cb4b9"
    ),
    "G5_LOOKAHEAD_WARM_PATH_RESULT_AUDIT.md": (
        "d975149d4d062d3950bead38f575bbdbc9264bebf0f626a07153cad17a2f2c95"
    ),
}


class DiagnosisError(RuntimeError):
    """Raised when frozen inputs or P3 structural invariants differ."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiagnosisError(f"expected a finite number, observed {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise DiagnosisError(f"expected a finite number, observed {value!r}")
    return result


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DiagnosisError(f"{field} is not a nonnegative integer: {value!r}")
    return value


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    return float(numerator) / float(denominator) if denominator > 0 else None


def _verified_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_hash(path) != expected:
        raise DiagnosisError(f"{label} file identity differs: {path}")


def _validated_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    ready_path = root / "p2-low.ready.json"
    p2_selection_path = root / "p2-low.online.selection.json"
    gate_path = root / "p2-low.gate.report.json"
    canonical_root = root / "online" / "canonical"
    _verified_file(ready_path, EXPECTED_READY_FILE, "P2 ready manifest")
    _verified_file(p2_selection_path, EXPECTED_P2_SELECTION_FILE, "P2 selection")
    _verified_file(gate_path, EXPECTED_GATE_FILE, "P2 gate report")
    _verified_file(Path(p2.__file__).resolve(), EXPECTED_P2_ANALYZER, "P2 analyzer")
    repo = _repo_root()
    _verified_file(
        repo / "serverless_sim" / "src" / "sche" / "sche_nash.rs",
        EXPECTED_SCHEDULER_SOURCE,
        "scheduler source",
    )
    _verified_file(
        repo / "refine-logs" / "P3_LOW_ROOT_CAUSE_DIAGNOSIS_PREREGISTRATION.md",
        EXPECTED_PREREG_FILE,
        "P3 preregistration",
    )
    for name, digest in CONTEXT_AUDITS.items():
        _verified_file(repo / "refine-logs" / name, digest, f"context audit {name}")

    manifest = p2._validate_ready_manifest(ready_path)
    if manifest.get("manifest_hash") != EXPECTED_READY_DOCUMENT:
        raise DiagnosisError("P2 ready manifest document hash differs")
    p2_selection = p2._validate_selection(
        p2_selection_path, ready_path, canonical_root, manifest
    )
    if p2_selection.get("document_sha256") != EXPECTED_P2_SELECTION_DOCUMENT:
        raise DiagnosisError("P2 selection document hash differs")
    gate = read_json(gate_path)
    if not isinstance(gate, dict):
        raise DiagnosisError("P2 gate report is not an object")
    payload = dict(gate)
    stored = payload.pop("document_sha256", None)
    gate_result = gate.get("gate_result")
    run_metrics = gate.get("run_metrics")
    if (
        stored != EXPECTED_GATE_DOCUMENT
        or object_hash(payload) != stored
        or gate.get("status")
        != "complete_p2_low_parameter_recovery_failed_formal_blocked"
        or gate.get("selected_setting") is not None
        or gate.get("run_count") != EXPECTED_RUN_COUNT
        or not isinstance(gate_result, Mapping)
        or gate_result.get("population_pass") is not True
        or gate_result.get("selected_setting") is not None
        or gate_result.get("eligible_settings") != []
        or not isinstance(run_metrics, list)
        or len(run_metrics) != EXPECTED_RUN_COUNT
        or any(row.get("qc_valid") is not True for row in run_metrics)
    ):
        raise DiagnosisError("P2 gate report is not the complete failed population")
    identities = {(row.get("seed"), row.get("setting")) for row in run_metrics}
    expected_identities = {
        (seed, setting)
        for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS
        for setting in P2_LOW_SETTING_LABELS
    }
    if identities != expected_identities:
        raise DiagnosisError("P2 gate report metric identities differ")

    inventory = directory_tree_inventory(canonical_root)
    if (
        len(inventory) != EXPECTED_CANONICAL_FILES
        or sum(row["bytes"] for row in inventory) != EXPECTED_CANONICAL_BYTES
        or object_hash(inventory) != EXPECTED_CANONICAL_INVENTORY
    ):
        raise DiagnosisError("P2 online canonical inventory differs from closure")
    return manifest, gate


def _setting(run: Mapping[str, Any]) -> str:
    metadata = run.get("metadata")
    value = metadata.get("parameter_setting") if isinstance(metadata, Mapping) else None
    if value not in P2_LOW_SETTING_LABELS:
        raise DiagnosisError(f"unknown P2 setting: {value!r}")
    return str(value)


def _nash_stream_path(run_dir: Path, run_id: str) -> Path:
    path = run_dir / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    if not path.is_file():
        raise DiagnosisError(f"canonical Nash stream is missing: {path}")
    return path


def _selection_rows(root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    canonical = root / "online" / "canonical"
    result_relative = manifest["execution"].get("result_relative_path", "result.json")
    rows: list[dict[str, Any]] = []
    expected_order = [
        (seed, setting)
        for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS
        for setting in P2_LOW_SETTING_LABELS
    ]
    observed_order: list[tuple[str, str]] = []
    for ordinal, run in enumerate(manifest["runs"], start=1):
        run_id = str(run["run_id"])
        seed = str(run["seed"])
        setting = _setting(run)
        observed_order.append((seed, setting))
        run_dir = canonical / run_id
        qc = validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=result_relative,
        )
        claimed_windows = (
            qc.get("observations", {})
            .get("nash_runtime_contract", {})
            .get("policy_windows")
        )
        if claimed_windows != EXPECTED_WINDOW_COUNT:
            raise DiagnosisError(f"{run_id} does not claim exactly 1,000 windows")
        nash_path = _nash_stream_path(run_dir, run_id)
        rows.append(
            {
                "ordinal": ordinal,
                "run_id": run_id,
                "run_spec_hash": run["run_spec_hash"],
                "seed": seed,
                "setting": setting,
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "process_observation_sha256": file_hash(
                    run_dir / "process_observation.json"
                ),
                "summary_sha256": file_hash(_canonical_summary_path(canonical, run_id)),
                "nash_metrics_gzip_sha256": file_hash(nash_path),
                "claimed_policy_windows": claimed_windows,
            }
        )
    if observed_order != expected_order or len(rows) != EXPECTED_RUN_COUNT:
        raise DiagnosisError("P2 run order/product differs from preregistration")
    return rows


def build_selection(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve()
    output = output.resolve()
    manifest, _ = _validated_inputs(root)
    report: dict[str, Any] = {
        "schema_version": SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": "frozen_before_reduced_metric_extraction",
        "p3_results_present_at_freeze": False,
        "p2_root": str(root),
        "p3_output_root": str(output.parent),
        "run_count": EXPECTED_RUN_COUNT,
        "window_count_per_run_claim": EXPECTED_WINDOW_COUNT,
        "execution_order": "seed_major_then_setting_ordinal",
        "all_valid_runs_retained": True,
        "result_conditioned_seed_setting_or_run_selection": False,
        "preregistration": {
            "commit": PREREG_COMMIT,
            "file_sha256": EXPECTED_PREREG_FILE,
        },
        "analysis_contract": {
            "path": str(Path(__file__).resolve()),
            "sha256": file_hash(Path(__file__).resolve()),
            "condition_count": 6,
        },
        "runs": _selection_rows(root, manifest),
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_selection(root: Path, output: Path) -> dict[str, Any]:
    if output.exists() or output.parent.exists():
        raise DiagnosisError("P3 selection output workspace must be absent")
    report = build_selection(root, output)
    write_json_atomic(output, report)
    return report


def _validate_selection(
    root: Path,
    selection_path: Path,
    manifest: Mapping[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    selection = read_json(selection_path)
    if not isinstance(selection, dict):
        raise DiagnosisError("P3 selection is not an object")
    payload = dict(selection)
    stored = payload.pop("document_sha256", None)
    contract = selection.get("analysis_contract")
    prereg = selection.get("preregistration")
    if (
        not isinstance(stored, str)
        or object_hash(payload) != stored
        or selection.get("schema_version") != SELECTION_SCHEMA
        or selection.get("status") != "frozen_before_reduced_metric_extraction"
        or selection.get("p3_results_present_at_freeze") is not False
        or Path(str(selection.get("p2_root", ""))).resolve() != root.resolve()
        or Path(str(selection.get("p3_output_root", ""))).resolve()
        != selection_path.resolve().parent
        or report_path.resolve().parent != selection_path.resolve().parent
        or selection.get("run_count") != EXPECTED_RUN_COUNT
        or selection.get("window_count_per_run_claim") != EXPECTED_WINDOW_COUNT
        or selection.get("all_valid_runs_retained") is not True
        or selection.get("result_conditioned_seed_setting_or_run_selection")
        is not False
        or not isinstance(prereg, Mapping)
        or prereg.get("commit") != PREREG_COMMIT
        or prereg.get("file_sha256") != EXPECTED_PREREG_FILE
        or not isinstance(contract, Mapping)
        or Path(str(contract.get("path", ""))).resolve() != Path(__file__).resolve()
        or contract.get("sha256") != file_hash(Path(__file__).resolve())
        or contract.get("condition_count") != 6
        or selection.get("runs") != _selection_rows(root, manifest)
    ):
        raise DiagnosisError("P3 selection no longer matches the frozen inputs")
    if report_path.exists():
        raise DiagnosisError("P3 report already exists; refusing repeated extraction")
    return selection


def _strict_pne_status(assigned: int, solver: Mapping[str, Any]) -> str:
    if assigned == 0:
        return "inactive"
    oscillations = _nonnegative_int(solver.get("oscillations"), "oscillations")
    if (
        solver.get("inner_stable") is True
        and solver.get("inner_limit_hit") is False
        and oscillations == 0
    ):
        return "strict_pne"
    return "failed"


def _price_signature(solver: Mapping[str, Any]) -> tuple[Any, ...]:
    trace = solver.get("outer_feedback_trace")
    if not isinstance(trace, list) or not trace:
        raise DiagnosisError("window lacks an outer feedback trace")
    signature: list[Any] = []
    for item in trace:
        if not isinstance(item, Mapping):
            raise DiagnosisError("outer feedback trace item is not an object")
        current = _finite_number(item.get("price_multiplier_for_current_round"))
        raw_next = item.get("price_multiplier_for_next_round")
        next_value = None if raw_next is None else _finite_number(raw_next)
        signature.append((current, next_value, item.get("feedback_applied")))
    return tuple(signature)


def _normalized_windows(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    windows = [event for event in events if event.get("kind") == "window"]
    if len(windows) != EXPECTED_WINDOW_COUNT:
        raise DiagnosisError(
            f"expected {EXPECTED_WINDOW_COUNT} policy windows, observed {len(windows)}"
        )
    result: list[dict[str, Any]] = []
    for ordinal, window in enumerate(windows, start=1):
        if window.get("window") != ordinal:
            raise DiagnosisError("policy window indices are not exactly 1..1000")
        decision = window.get("decision")
        solver = window.get("solver")
        pricing = window.get("pricing")
        social = window.get("social")
        if not all(
            isinstance(value, Mapping) for value in (decision, solver, pricing, social)
        ):
            raise DiagnosisError(
                f"window {ordinal} lacks decision/solver/pricing/social"
            )
        assert isinstance(decision, Mapping)
        assert isinstance(solver, Mapping)
        assert isinstance(pricing, Mapping)
        assert isinstance(social, Mapping)
        values = {
            "assigned": _nonnegative_int(decision.get("assigned_players"), "A"),
            "running": _nonnegative_int(
                decision.get("selected_running_warm_players"), "R"
            ),
            "starting": _nonnegative_int(
                decision.get("selected_starting_container_players"), "S"
            ),
            "cold": _nonnegative_int(
                decision.get("selected_cold_or_nonrunning_players"), "C"
            ),
            "warm_available": _nonnegative_int(
                decision.get("running_warm_available_players"), "W"
            ),
            "warm_bypassed": _nonnegative_int(
                decision.get("running_warm_bypassed_players"), "B"
            ),
            "ranking_players": _nonnegative_int(
                decision.get("ranking_diagnostic_players"), "P"
            ),
            "changed_players": _nonnegative_int(
                decision.get("differentiation_changed_top_choice_players"), "D"
            ),
            "near_tie_players": _nonnegative_int(
                decision.get("near_tie_players"), "near_tie_players"
            ),
        }
        utility = social.get("utility_components")
        if not isinstance(utility, Mapping):
            raise DiagnosisError(f"window {ordinal} lacks utility components")
        row: dict[str, Any] = {
            "window": ordinal,
            "frame": _nonnegative_int(window.get("frame"), "frame"),
            **values,
            "assignment_hash": _nonnegative_int(
                decision.get("assignment_hash"), "assignment_hash"
            ),
            "commands_prepared": _nonnegative_int(
                decision.get("commands_prepared"), "commands_prepared"
            ),
            "strict_pne_status": _strict_pne_status(values["assigned"], solver),
            "outer_adjustments": _nonnegative_int(
                pricing.get("adjustments"), "pricing.adjustments"
            ),
            "price_signature": _price_signature(solver),
            "feedback_applied_rounds": sum(
                item.get("feedback_applied") is True
                for item in solver["outer_feedback_trace"]
            ),
            "warm_bypass_utility_advantage_sum": _finite_number(
                decision.get("warm_bypass_utility_advantage_sum")
            ),
            "warm_bypass_finish_score_delta_sum": _finite_number(
                decision.get("warm_bypass_finish_score_delta_sum")
            ),
            "utility_components": {
                field: _finite_number(utility.get(field))
                for field in UTILITY_COMPONENTS
            },
        }
        row["partition_invariant"] = (
            row["assigned"] == row["running"] + row["starting"] + row["cold"]
        )
        row["warm_invariant"] = (
            0 <= row["warm_bypassed"] <= row["warm_available"] <= row["assigned"]
        )
        row["differentiation_invariant"] = (
            0 <= row["changed_players"] <= row["ranking_players"] <= row["assigned"]
        )
        result.append(row)
    return result


def _metric_index(gate: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in gate["run_metrics"]:
        key = (str(row["seed"]), str(row["setting"]))
        if key in result:
            raise DiagnosisError(f"duplicate P2 metric identity: {key}")
        result[key] = row
    return result


def _pair_row(
    seed: str,
    candidate: str,
    centre_windows: Sequence[Mapping[str, Any]],
    candidate_windows: Sequence[Mapping[str, Any]],
    metrics: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        len(centre_windows) != EXPECTED_WINDOW_COUNT
        or len(candidate_windows) != EXPECTED_WINDOW_COUNT
        or len(centre_windows) != len(candidate_windows)
    ):
        raise DiagnosisError("paired window lengths differ")
    pairs = list(zip(centre_windows, candidate_windows))
    active = [
        pair for pair in pairs if pair[0]["assigned"] > 0 or pair[1]["assigned"] > 0
    ]
    row: dict[str, Any] = {
        "seed": seed,
        "candidate": candidate,
        "aligned_windows": len(pairs),
        "aligned_active_windows": len(active),
        "assignment_hash_equal_windows": sum(
            left["assignment_hash"] == right["assignment_hash"] for left, right in pairs
        ),
        "assigned_players_equal_windows": sum(
            left["assigned"] == right["assigned"] for left, right in pairs
        ),
        "commands_prepared_equal_windows": sum(
            left["commands_prepared"] == right["commands_prepared"]
            for left, right in pairs
        ),
        "strict_pne_status_equal_windows": sum(
            left["strict_pne_status"] == right["strict_pne_status"]
            for left, right in pairs
        ),
        "outer_adjustments_equal_windows": sum(
            left["outer_adjustments"] == right["outer_adjustments"]
            for left, right in pairs
        ),
        "price_signature_changed_assignment_equal_windows": sum(
            left["price_signature"] != right["price_signature"]
            and left["assignment_hash"] == right["assignment_hash"]
            for left, right in pairs
        ),
        "active_assignment_hash_changed_windows": sum(
            left["assignment_hash"] != right["assignment_hash"]
            for left, right in active
        ),
    }
    row["active_assignment_hash_changed_share"] = _ratio(
        row["active_assignment_hash_changed_windows"], row["aligned_active_windows"]
    )
    row["operationally_dormant"] = (
        row["assignment_hash_equal_windows"] == EXPECTED_WINDOW_COUNT
        and row["commands_prepared_equal_windows"] == EXPECTED_WINDOW_COUNT
    )
    centre_metric = metrics[(seed, CENTRE)]
    candidate_metric = metrics[(seed, candidate)]
    for field in METRIC_FIELDS:
        centre_value = _finite_number(centre_metric.get(field))
        candidate_value = _finite_number(candidate_metric.get(field))
        row[f"centre_{field}"] = centre_value
        row[f"candidate_{field}"] = candidate_value
        row[f"difference_{field}"] = candidate_value - centre_value
        row[f"equal_{field}"] = candidate_value == centre_value
    return row


def centre_path_row(
    seed: str, run_id: str, windows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    totals = {
        field: sum(int(window[field]) for window in windows)
        for field in (
            "assigned",
            "running",
            "starting",
            "cold",
            "warm_available",
            "warm_bypassed",
            "ranking_players",
            "changed_players",
            "near_tie_players",
            "outer_adjustments",
            "feedback_applied_rounds",
        )
    }
    active = [window for window in windows if window["assigned"] > 0]
    changed = [window for window in active if window["changed_players"] > 0]
    unchanged = [window for window in active if window["changed_players"] == 0]

    def _group(group: Sequence[Mapping[str, Any]]) -> tuple[int, int, float | None]:
        assigned = sum(int(window["assigned"]) for window in group)
        nonrunning = sum(
            int(window["starting"]) + int(window["cold"]) for window in group
        )
        return assigned, nonrunning, _ratio(nonrunning, assigned)

    changed_a, changed_nr, changed_share = _group(changed)
    unchanged_a, unchanged_nr, unchanged_share = _group(unchanged)
    utility_totals = {
        field: sum(float(window["utility_components"][field]) for window in windows)
        for field in UTILITY_COMPONENTS
    }
    partition_failures = sum(not window["partition_invariant"] for window in windows)
    warm_failures = sum(not window["warm_invariant"] for window in windows)
    differentiation_failures = sum(
        not window["differentiation_invariant"] for window in windows
    )
    nonrunning = totals["starting"] + totals["cold"]
    row: dict[str, Any] = {
        "seed": seed,
        "run_id": run_id,
        "window_count": len(windows),
        "active_window_count": len(active),
        **totals,
        "nonrunning_players": nonrunning,
        "nonrunning_share": _ratio(nonrunning, totals["assigned"]),
        "warm_available_share": _ratio(totals["warm_available"], totals["assigned"]),
        "warm_bypass_share": _ratio(totals["warm_bypassed"], totals["warm_available"]),
        "differentiation_change_share": _ratio(
            totals["changed_players"], totals["ranking_players"]
        ),
        "changed_group_window_count": len(changed),
        "changed_group_assigned_players": changed_a,
        "changed_group_nonrunning_players": changed_nr,
        "changed_group_nonrunning_share": changed_share,
        "unchanged_group_window_count": len(unchanged),
        "unchanged_group_assigned_players": unchanged_a,
        "unchanged_group_nonrunning_players": unchanged_nr,
        "unchanged_group_nonrunning_share": unchanged_share,
        "both_groups_defined": changed_share is not None
        and unchanged_share is not None,
        "changed_group_nonrunning_nondecrease": (
            changed_share is not None
            and unchanged_share is not None
            and changed_share >= unchanged_share
        ),
        "partition_invariant_failures": partition_failures,
        "warm_invariant_failures": warm_failures,
        "differentiation_invariant_failures": differentiation_failures,
        "all_invariants_pass": (
            partition_failures == 0
            and warm_failures == 0
            and differentiation_failures == 0
        ),
        "warm_bypass_utility_advantage_sum": sum(
            float(window["warm_bypass_utility_advantage_sum"]) for window in windows
        ),
        "warm_bypass_finish_score_delta_sum": sum(
            float(window["warm_bypass_finish_score_delta_sum"]) for window in windows
        ),
        "utility_component_totals": utility_totals,
        "window_contribution_sha256": object_hash(list(windows)),
    }
    return row


def evaluate_direction(
    d1_rows: Sequence[Mapping[str, Any]],
    d3_rows: Sequence[Mapping[str, Any]],
    gate: Mapping[str, Any],
    *,
    population_integrity: bool = True,
) -> dict[str, Any]:
    differentiation_seed_passes = sum(
        row.get("differentiation_change_share") is not None
        and float(row["differentiation_change_share"]) >= 0.05
        for row in d3_rows
    )
    nonrunning_seed_passes = sum(
        row.get("nonrunning_share") is not None
        and float(row["nonrunning_share"]) >= 0.20
        for row in d3_rows
    )
    both_groups_defined = sum(row.get("both_groups_defined") is True for row in d3_rows)
    cooccurrence_seed_passes = sum(
        row.get("changed_group_nonrunning_nondecrease") is True for row in d3_rows
    )
    candidate_reports = gate["gate_result"].get("candidate_reports", [])
    failed_wq = {
        str(row.get("setting")): row.get("qualified") is False
        for row in candidate_reports
        if row.get("setting") in WQ_NEIGHBOURS
    }
    conditions = {
        "01_population_identity_alignment_and_invariants": (
            population_integrity
            and len(d1_rows) == 10
            and len(d3_rows) == 5
            and all(
                row.get("aligned_windows") == EXPECTED_WINDOW_COUNT for row in d1_rows
            )
            and all(row.get("all_invariants_pass") is True for row in d3_rows)
        ),
        "02_differentiation_changes_at_least_five_percent_in_four_seeds": (
            differentiation_seed_passes >= 4
        ),
        "03_nonrunning_share_at_least_twenty_percent_in_four_seeds": (
            nonrunning_seed_passes >= 4
        ),
        "04_changed_choice_nonrunning_share_nondecrease_in_three_seeds": (
            both_groups_defined >= 4 and cooccurrence_seed_passes >= 3
        ),
        "05_both_r0_neighbours_operationally_dormant": (
            len(d1_rows) == 10
            and all(row.get("operationally_dormant") is True for row in d1_rows)
        ),
        "06_failed_wq_neighbours_not_relabelled": (
            failed_wq == {"wq_minus": True, "wq_plus": True}
            and gate.get("selected_setting") is None
        ),
    }
    authorized = all(conditions.values())
    return {
        "status": (
            "complete_contribution_tempering_preregistration_authorized"
            if authorized
            else "complete_no_p3_successor_authorized"
        ),
        "conditions": conditions,
        "failure_reasons": [name for name, passed in conditions.items() if not passed],
        "condition_counts": {
            "differentiation_seed_passes": differentiation_seed_passes,
            "nonrunning_seed_passes": nonrunning_seed_passes,
            "both_groups_defined_seeds": both_groups_defined,
            "cooccurrence_seed_passes": cooccurrence_seed_passes,
        },
        "contribution_tempering_preregistration_authorized": authorized,
        "implementation_authorized": False,
        "sampling_authorized": False,
        "formal_progression_authorized": False,
    }


def analyze(root: Path, selection_path: Path, report_path: Path) -> dict[str, Any]:
    root = root.resolve()
    selection_path = selection_path.resolve()
    report_path = report_path.resolve()
    manifest, gate = _validated_inputs(root)
    selection = _validate_selection(root, selection_path, manifest, report_path)
    canonical = root / "online" / "canonical"
    result_relative = manifest["execution"].get("result_relative_path", "result.json")
    metrics = _metric_index(gate)
    window_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    run_receipts: list[dict[str, Any]] = []
    for run in manifest["runs"]:
        run_id = str(run["run_id"])
        seed = str(run["seed"])
        setting = _setting(run)
        run_dir = canonical / run_id
        validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=result_relative,
        )
        artifacts = load_run_artifacts(
            run,
            canonical,
            expected_manifest_hash=str(manifest["manifest_hash"]),
            result_relative_path=result_relative,
        )
        windows = _normalized_windows(artifacts.nse_events)
        key = (seed, setting)
        if key in window_index:
            raise DiagnosisError(f"duplicate window identity: {key}")
        window_index[key] = windows
        run_receipts.append(
            {
                "run_id": run_id,
                "run_spec_hash": run["run_spec_hash"],
                "seed": seed,
                "setting": setting,
                "window_count": len(windows),
                "window_contribution_sha256": object_hash(windows),
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                "nash_metrics_gzip_sha256": file_hash(
                    _nash_stream_path(run_dir, run_id)
                ),
            }
        )
    expected_keys = {
        (seed, setting)
        for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS
        for setting in P2_LOW_SETTING_LABELS
    }
    if set(window_index) != expected_keys:
        raise DiagnosisError("analyzed window population differs from all 25 runs")

    d1_rows: list[dict[str, Any]] = []
    d2_rows: list[dict[str, Any]] = []
    d3_rows: list[dict[str, Any]] = []
    run_ids = {
        (str(run["seed"]), _setting(run)): str(run["run_id"])
        for run in manifest["runs"]
    }
    for seed in P2_LOW_HYPERPARAMETER_RECOVERY_SEEDS:
        centre_windows = window_index[(seed, CENTRE)]
        for candidate in R0_NEIGHBOURS:
            d1_rows.append(
                _pair_row(
                    seed,
                    candidate,
                    centre_windows,
                    window_index[(seed, candidate)],
                    metrics,
                )
            )
        for candidate in WQ_NEIGHBOURS:
            d2_rows.append(
                _pair_row(
                    seed,
                    candidate,
                    centre_windows,
                    window_index[(seed, candidate)],
                    metrics,
                )
            )
        d3_rows.append(centre_path_row(seed, run_ids[(seed, CENTRE)], centre_windows))

    pooled_totals = {
        field: sum(int(row[field]) for row in d3_rows)
        for field in (
            "assigned",
            "running",
            "starting",
            "cold",
            "warm_available",
            "warm_bypassed",
            "ranking_players",
            "changed_players",
            "near_tie_players",
            "outer_adjustments",
            "feedback_applied_rounds",
        )
    }
    pooled_nonrunning = pooled_totals["starting"] + pooled_totals["cold"]
    pooled = {
        **pooled_totals,
        "nonrunning_players": pooled_nonrunning,
        "nonrunning_share": _ratio(pooled_nonrunning, pooled_totals["assigned"]),
        "warm_available_share": _ratio(
            pooled_totals["warm_available"], pooled_totals["assigned"]
        ),
        "warm_bypass_share": _ratio(
            pooled_totals["warm_bypassed"], pooled_totals["warm_available"]
        ),
        "differentiation_change_share": _ratio(
            pooled_totals["changed_players"], pooled_totals["ranking_players"]
        ),
        "utility_component_totals": {
            field: sum(float(row["utility_component_totals"][field]) for row in d3_rows)
            for field in UTILITY_COMPONENTS
        },
    }
    decision = evaluate_direction(d1_rows, d3_rows, gate)
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": decision["status"],
        "formal_results_eligible": False,
        "paper_claim_eligible": False,
        "paper_equations_changed": False,
        "p2_root": str(root),
        "frozen_selection": {
            "path": str(selection_path),
            "file_sha256": file_hash(selection_path),
            "document_sha256": selection["document_sha256"],
        },
        "input_receipts": {
            "ready_file_sha256": EXPECTED_READY_FILE,
            "ready_document_sha256": EXPECTED_READY_DOCUMENT,
            "p2_selection_file_sha256": EXPECTED_P2_SELECTION_FILE,
            "p2_selection_document_sha256": EXPECTED_P2_SELECTION_DOCUMENT,
            "p2_gate_file_sha256": EXPECTED_GATE_FILE,
            "p2_gate_document_sha256": EXPECTED_GATE_DOCUMENT,
            "canonical_files": EXPECTED_CANONICAL_FILES,
            "canonical_bytes": EXPECTED_CANONICAL_BYTES,
            "canonical_inventory_sha256": EXPECTED_CANONICAL_INVENTORY,
            "p2_analyzer_sha256": EXPECTED_P2_ANALYZER,
            "scheduler_source_sha256": EXPECTED_SCHEDULER_SOURCE,
            "preregistration_commit": PREREG_COMMIT,
            "preregistration_file_sha256": EXPECTED_PREREG_FILE,
            "context_audit_sha256": dict(CONTEXT_AUDITS),
        },
        "definitions": {
            "independent_unit": "run/seed",
            "aligned_window": "same one-based scheduler window ordinal within a shared-tape seed",
            "active_pair_window": "centre assigned_players>0 or neighbour assigned_players>0",
            "strict_pne_status": "inactive, or inner_stable and not inner_limit_hit and zero oscillations",
            "nonrunning": "selected_starting_container_players+selected_cold_or_nonrunning_players",
            "differentiation": "logged counterfactual ranking that removes only the h_pi contribution term over common candidates",
            "group_share": "player-weighted sum(nonrunning)/sum(assigned), not a mean of window percentages",
            "r0_dormancy": "all 1,000 assignment hashes and command counts equal centre in every seed",
            "development_fit_not_validation": True,
            "all_valid_runs_retained": True,
            "result_conditioned_selection": False,
        },
        "d1_r0_pair_rows": d1_rows,
        "d2_wq_pair_rows": d2_rows,
        "d3_centre_path_rows": d3_rows,
        "d3_pooled": pooled,
        "d4_direction_decision": decision,
        "run_window_receipts": run_receipts,
        "run_count": len(window_index),
        "window_count": sum(len(windows) for windows in window_index.values()),
        "contribution_tempering_preregistration_authorized": decision[
            "contribution_tempering_preregistration_authorized"
        ],
        "implementation_authorized": False,
        "sampling_authorized": False,
        "formal_progression_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def _csv_value(value: Any) -> Any:
    if isinstance(value, Mapping) or isinstance(value, (list, tuple)):
        return object_hash(value)
    return value


def _write_csv_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise DiagnosisError(f"refusing to write empty CSV: {path.name}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fields})
        handle.flush()
        os.fsync(handle.fileno())
    replace_atomic(temporary, path)


def write_analysis(root: Path, selection: Path, output: Path) -> dict[str, Any]:
    outputs = {
        output,
        output.parent / "p3.d1-r0-pairs.csv",
        output.parent / "p3.d2-wq-pairs.csv",
        output.parent / "p3.d3-centre-path.csv",
        output.parent / "p3.d4-conditions.csv",
    }
    if any(path.exists() for path in outputs):
        raise DiagnosisError("P3 output already exists; refusing repeated extraction")
    report = analyze(root, selection, output)
    decision_rows = [
        {"condition": name, "passed": passed}
        for name, passed in report["d4_direction_decision"]["conditions"].items()
    ]
    _write_csv_atomic(output.parent / "p3.d1-r0-pairs.csv", report["d1_r0_pair_rows"])
    _write_csv_atomic(output.parent / "p3.d2-wq-pairs.csv", report["d2_wq_pair_rows"])
    _write_csv_atomic(
        output.parent / "p3.d3-centre-path.csv", report["d3_centre_path_rows"]
    )
    _write_csv_atomic(output.parent / "p3.d4-conditions.csv", decision_rows)
    write_json_atomic(output, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-selection")
    freeze.add_argument("p2_root", type=Path)
    freeze.add_argument("output", type=Path)
    diagnose = commands.add_parser("analyze")
    diagnose.add_argument("p2_root", type=Path)
    diagnose.add_argument("selection", type=Path)
    diagnose.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "freeze-selection":
        write_selection(args.p2_root, args.output)
    else:
        write_analysis(args.p2_root, args.selection, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
