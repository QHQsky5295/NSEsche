"""Read-only G13 diagnosis of isolated versus persistent G12 deferral."""

from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping, Sequence

from ..protocol.g12_global_ready_admission import G12_CANDIDATE, G12_CONTROL
from ..protocol.schema import FORMAL_E1_LOADS, G12_GLOBAL_READY_ADMISSION_SEEDS
from ..protocol.util import (
    directory_tree_inventory,
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from .formal_inputs import validate_canonical_run
from .g12_global_ready_admission import (
    GLOBAL_READY_SCHEMA,
    _finite_int,
    _validate_ready_manifest,
    _validate_selection,
)
from .observability import load_run_artifacts


REPORT_SCHEMA = "NSE_G13_DEFERRAL_PERSISTENCE_DIAGNOSIS_V1"
EXPECTED_ROOT_FILES = 1092
EXPECTED_ROOT_BYTES = 390090635
EXPECTED_ROOT_HASH = "5a41481e09fa159364741b8158e385367c81920350e3a1231ffe3baaf1f1b20a"
EXPECTED_MANIFEST_FILE = (
    "4c0140a0a9c92ebe0fe4afb8167b380e7a3a512560534694690d4439fa704209"
)
EXPECTED_MANIFEST_DOCUMENT = (
    "ec5708cc4e7661d2efce1570bc6a2a6d617a82df8a34a5fb25dda5add4eabb96"
)
EXPECTED_SELECTION_FILE = (
    "784f40c3e97ed75d018a948c2f5f1a23c1f46428f77217d48b8fc237e640a7fd"
)
EXPECTED_SELECTION_DOCUMENT = (
    "3e5665dca85af7e86cd3dd4e0b0bacbf33c3f323ccacf3ac4f0db854f6cd014f"
)
EXPECTED_GATE_FILE = "6c5e0882248a5c0078e0c7f0221fefdfd88d2e2c931b8d4342b7fd41bf78f5a5"
EXPECTED_GATE_DOCUMENT = (
    "7fc6f143cef017e785077b939c27c62b3eb0197f56ec498b9cc1132e22b20e52"
)
EXPECTED_LEDGER_FILE = (
    "14a6621715c373fb71adb1723f234c2e1ac69930431755f7853abb2dee22326e"
)
EXPECTED_LEDGER_EVENTS = 62
EXPECTED_LEDGER_TIP = "bf0832f6439c79e2a2b292e1febbc270119cf5f91a3066397642e271c41ec60b"
VIOLATION_FIELDS = (
    "readiness_violations",
    "feasibility_violations",
    "legacy_order_violations",
    "prefix_violations",
    "bound_violations",
    "dispatch_set_violations",
)
ASSOCIATION_FEATURES = (
    "deferred_total",
    "deferred_max",
    "positive_deferral_fraction",
    "persistent_transition_fraction",
    "longest_positive_episode",
    "admitted_feasible_ratio",
    "queue_pending_mean",
    "queue_pending_max",
    "queue_resident_mean",
    "queue_resident_max",
    "queue_total_mean",
    "queue_total_max",
    "positive_queue_total_mean",
    "positive_queue_total_max",
)


class DiagnosisError(RuntimeError):
    pass


def _number(value: Any, *, nonnegative: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or (nonnegative and number < 0.0):
        return None
    return number


def _mean(values: Sequence[float]) -> float | None:
    return fmean(values) if values else None


def _rank(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        rank = (start + 1 + stop) / 2.0
        for position in order[start:stop]:
            ranks[position] = rank
        start = stop
    return ranks


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_rank = _rank(left)
    right_rank = _rank(right)
    left_mean = fmean(left_rank)
    right_mean = fmean(right_rank)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left_rank, right_rank)
    )
    left_ss = sum((x - left_mean) ** 2 for x in left_rank)
    right_ss = sum((y - right_mean) ** 2 for y in right_rank)
    denominator = math.sqrt(left_ss * right_ss)
    return numerator / denominator if denominator > 0.0 else None


def _episode_metrics(deferred: Sequence[int]) -> dict[str, int]:
    positive = [value > 0 for value in deferred]
    episodes = 0
    transitions = 0
    isolated = 0
    longest = 0
    current = 0
    for index, active in enumerate(positive):
        if active:
            current += 1
            longest = max(longest, current)
            if index == 0 or not positive[index - 1]:
                episodes += 1
            else:
                transitions += 1
            previous_active = index > 0 and positive[index - 1]
            next_active = index + 1 < len(positive) and positive[index + 1]
            if not previous_active and not next_active:
                isolated += 1
        else:
            current = 0
    return {
        "positive_deferral_windows": sum(positive),
        "deferral_episode_count": episodes,
        "isolated_deferral_windows": isolated,
        "persistent_deferral_transitions": transitions,
        "longest_positive_episode": longest,
    }


def _ledger_identity(path: Path) -> dict[str, Any]:
    previous = "0" * 64
    count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        event = read_json_line(raw)
        if event.get("sequence") != count + 1 or event.get("previous_hash") != previous:
            raise DiagnosisError("G12 online ledger chain is invalid")
        payload = dict(event)
        stored = payload.pop("event_hash", None)
        if stored != object_hash(payload):
            raise DiagnosisError("G12 online ledger event hash is invalid")
        previous = stored
        count += 1
    if count != EXPECTED_LEDGER_EVENTS or previous != EXPECTED_LEDGER_TIP:
        raise DiagnosisError("G12 online ledger identity differs from closure")
    return {"events": count, "last_hash": previous, "file_sha256": file_hash(path)}


def read_json_line(raw: str) -> dict[str, Any]:
    import json

    value = json.loads(raw)
    if not isinstance(value, dict):
        raise DiagnosisError("ledger row is not an object")
    return value


def _validated_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = directory_tree_inventory(root)
    if (
        len(inventory) != EXPECTED_ROOT_FILES
        or sum(row["bytes"] for row in inventory) != EXPECTED_ROOT_BYTES
        or object_hash(inventory) != EXPECTED_ROOT_HASH
    ):
        raise DiagnosisError("G12 run-root inventory differs from closure")
    manifest_path = root / "g12.references.json"
    selection_path = root / "g12.online.selection.json"
    report_path = root / "g12.gate.report.json"
    ledger_path = root / "online" / "ledger.jsonl"
    if (
        file_hash(manifest_path) != EXPECTED_MANIFEST_FILE
        or file_hash(selection_path) != EXPECTED_SELECTION_FILE
        or file_hash(report_path) != EXPECTED_GATE_FILE
        or file_hash(ledger_path) != EXPECTED_LEDGER_FILE
    ):
        raise DiagnosisError("one or more frozen G12 file hashes differ")
    manifest = _validate_ready_manifest(manifest_path)
    if manifest.get("manifest_hash") != EXPECTED_MANIFEST_DOCUMENT:
        raise DiagnosisError("G12 manifest document hash differs")
    selection = _validate_selection(
        selection_path, manifest_path, root / "online" / "canonical", manifest
    )
    if selection.get("document_sha256") != EXPECTED_SELECTION_DOCUMENT:
        raise DiagnosisError("G12 selection document hash differs")
    report = read_json(report_path)
    if not isinstance(report, dict):
        raise DiagnosisError("G12 gate report is not an object")
    payload = dict(report)
    stored = payload.pop("document_sha256", None)
    if stored != EXPECTED_GATE_DOCUMENT or object_hash(payload) != stored:
        raise DiagnosisError("G12 gate report document hash differs")
    gate = report.get("gate_result")
    if (
        report.get("status") != "complete_g12_development_gate_failed"
        or not isinstance(gate, Mapping)
        or gate.get("selected_candidate") is not None
        or gate.get("all_valid_runs_retained") is not True
        or len(report.get("run_metrics", ())) != 30
        or len(gate.get("paired_rows", ())) != 15
    ):
        raise DiagnosisError("G12 gate report is not the closed retained product")
    ledger = _ledger_identity(ledger_path)
    if ledger["file_sha256"] != EXPECTED_LEDGER_FILE:
        raise DiagnosisError("G12 ledger file hash differs")
    return manifest, report


def _queue_summary(values: Sequence[int], positive: Sequence[bool]) -> dict[str, Any]:
    positive_values = [value for value, selected in zip(values, positive) if selected]
    return {
        "mean": _mean([float(value) for value in values]),
        "max": max(values) if values else None,
        "positive_mean": _mean([float(value) for value in positive_values]),
        "positive_max": max(positive_values) if positive_values else None,
    }


def _feature_row(
    run: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    paired: Mapping[str, Any],
    run_metric: Mapping[str, Any],
) -> dict[str, Any]:
    deferred = []
    admitted = []
    feasible = []
    pending_queue = []
    resident_queue = []
    total_queue = []
    violations = {field: 0 for field in VIOLATION_FIELDS}
    active_windows = 0
    for index, event in enumerate(events):
        telemetry = event.get("global_ready_player_admission")
        decision = event.get("decision")
        cluster = event.get("cluster")
        if not isinstance(telemetry, Mapping) or not isinstance(decision, Mapping):
            raise DiagnosisError(f"candidate window {index} lacks G12 evidence")
        if telemetry.get("schema") != GLOBAL_READY_SCHEMA:
            raise DiagnosisError(f"candidate window {index} has wrong G12 schema")
        d = _finite_int(telemetry.get("deferred_feasible_players"))
        a = _finite_int(telemetry.get("admitted_players"))
        f = _finite_int(telemetry.get("feasible_ready_candidates"))
        limit = _finite_int(telemetry.get("admission_limit"))
        assigned = _finite_int(decision.get("assigned_players"))
        if None in (d, a, f, limit, assigned):
            raise DiagnosisError(f"candidate window {index} has invalid counts")
        if a != min(f, limit) or d != f - a or assigned != a:
            raise DiagnosisError(f"candidate window {index} violates prefix accounting")
        if not isinstance(cluster, Mapping):
            raise DiagnosisError(f"candidate window {index} lacks queue context")
        q_pending = _finite_int(cluster.get("queue_pending_total"))
        q_resident = _finite_int(cluster.get("queue_resident_total"))
        q_total = _finite_int(cluster.get("queue_total"))
        if (
            None in (q_pending, q_resident, q_total)
            or q_total != q_pending + q_resident
        ):
            raise DiagnosisError(f"candidate window {index} has invalid queue context")
        deferred.append(int(d))
        admitted.append(int(a))
        feasible.append(int(f))
        pending_queue.append(int(q_pending))
        resident_queue.append(int(q_resident))
        total_queue.append(int(q_total))
        active_windows += int(int(assigned) > 0)
        for field in VIOLATION_FIELDS:
            value = _finite_int(telemetry.get(field))
            if value is None:
                raise DiagnosisError(f"candidate window {index} has invalid {field}")
            violations[field] += value
    episodes = _episode_metrics(deferred)
    positive = [value > 0 for value in deferred]
    pending = _queue_summary(pending_queue, positive)
    resident = _queue_summary(resident_queue, positive)
    total = _queue_summary(total_queue, positive)
    throughput_ratio = _number(paired.get("throughput_ratio"), nonnegative=True)
    qpr_ratio = _number(paired.get("qpr_ratio"), nonnegative=True)
    if (
        throughput_ratio is None
        or throughput_ratio <= 0.0
        or qpr_ratio is None
        or qpr_ratio <= 0.0
    ):
        raise DiagnosisError("paired primary ratio is undefined")
    window_count = len(events)
    feasible_total = sum(feasible)
    return {
        "run_id": run["run_id"],
        "run_spec_hash": run["run_spec_hash"],
        "load": run["workload"]["request_freq"],
        "seed": run["seed"],
        "workload_tape_sha256": run["workload_tape"]["sha256"],
        "window_count": window_count,
        "active_window_count": active_windows,
        **episodes,
        "deferred_total": sum(deferred),
        "deferred_max": max(deferred) if deferred else 0,
        "positive_deferred_mean": _mean(
            [float(value) for value in deferred if value > 0]
        ),
        "positive_deferral_fraction": episodes["positive_deferral_windows"]
        / window_count,
        "isolated_deferral_fraction": episodes["isolated_deferral_windows"]
        / window_count,
        "persistent_transition_fraction": episodes["persistent_deferral_transitions"]
        / window_count,
        "admitted_total": sum(admitted),
        "feasible_ready_total": feasible_total,
        "admitted_feasible_ratio": sum(admitted) / feasible_total
        if feasible_total
        else None,
        "queue_pending_mean": pending["mean"],
        "queue_pending_max": pending["max"],
        "positive_queue_pending_mean": pending["positive_mean"],
        "positive_queue_pending_max": pending["positive_max"],
        "queue_resident_mean": resident["mean"],
        "queue_resident_max": resident["max"],
        "positive_queue_resident_mean": resident["positive_mean"],
        "positive_queue_resident_max": resident["positive_max"],
        "queue_total_mean": total["mean"],
        "queue_total_max": total["max"],
        "positive_queue_total_mean": total["positive_mean"],
        "positive_queue_total_max": total["positive_max"],
        **violations,
        "g12_activation_pass": run_metric.get("g12_activation_pass"),
        "runtime_identity_pass": run_metric.get("runtime_identity_pass"),
        "nash_runtime_pass": run_metric.get("nash_runtime_pass"),
        "strict_pne_active_windows": run_metric.get("strict_pne_active_windows"),
        "offline_reference_hit_windows": run_metric.get(
            "offline_reference_hit_windows"
        ),
        "throughput_ratio": throughput_ratio,
        "qpr_ratio": qpr_ratio,
        "latency_ratio": paired.get("latency_ratio"),
        "cost_ratio": paired.get("cost_ratio"),
        "completion_ratio_difference": paired.get("completion_ratio_difference"),
        "log_throughput_ratio": math.log(throughput_ratio),
        "log_qpr_ratio": math.log(qpr_ratio),
        "joint_win": throughput_ratio > 1.0 and qpr_ratio > 1.0,
        "joint_nonwin": not (throughput_ratio > 1.0 and qpr_ratio > 1.0),
        "isolated_only_activation": episodes["positive_deferral_windows"] > 0
        and episodes["longest_positive_episode"] == 1,
        "persistent_activation": episodes["longest_positive_episode"] >= 2,
    }


def _associations(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    reports = []
    for feature in ASSOCIATION_FEATURES:
        for outcome in ("log_throughput_ratio", "log_qpr_ratio"):
            overall_pairs = [
                (row.get(feature), row.get(outcome))
                for row in rows
                if _number(row.get(feature)) is not None
                and _number(row.get(outcome)) is not None
            ]
            overall = _spearman(
                [float(pair[0]) for pair in overall_pairs],
                [float(pair[1]) for pair in overall_pairs],
            )
            by_load = []
            for load in FORMAL_E1_LOADS:
                pairs = [
                    (row.get(feature), row.get(outcome))
                    for row in rows
                    if row["load"] == load
                    and _number(row.get(feature)) is not None
                    and _number(row.get(outcome)) is not None
                ]
                by_load.append(
                    {
                        "load": load,
                        "n": len(pairs),
                        "spearman": _spearman(
                            [float(pair[0]) for pair in pairs],
                            [float(pair[1]) for pair in pairs],
                        ),
                    }
                )
            loo = []
            for omitted in rows:
                retained = [row for row in rows if row["run_id"] != omitted["run_id"]]
                pairs = [
                    (row.get(feature), row.get(outcome))
                    for row in retained
                    if _number(row.get(feature)) is not None
                    and _number(row.get(outcome)) is not None
                ]
                loo.append(
                    {
                        "omitted_run_id": omitted["run_id"],
                        "spearman": _spearman(
                            [float(pair[0]) for pair in pairs],
                            [float(pair[1]) for pair in pairs],
                        ),
                    }
                )
            reports.append(
                {
                    "feature": feature,
                    "outcome": outcome,
                    "n": len(overall_pairs),
                    "overall_spearman": overall,
                    "by_load": by_load,
                    "leave_one_run_out": loo,
                }
            )
    return reports


def _group_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def summary(group: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "n": len(group),
            "loads": sorted({str(row["load"]) for row in group}),
            "joint_wins": sum(bool(row["joint_win"]) for row in group),
            "joint_win_rate": (
                sum(bool(row["joint_win"]) for row in group) / len(group)
                if group
                else None
            ),
            "mean_log_throughput_ratio": _mean(
                [float(row["log_throughput_ratio"]) for row in group]
            ),
            "mean_log_qpr_ratio": _mean([float(row["log_qpr_ratio"]) for row in group]),
            "run_ids": [row["run_id"] for row in group],
        }

    isolated = [row for row in rows if row["isolated_only_activation"]]
    persistent = [row for row in rows if row["persistent_activation"]]
    isolated_summary = summary(isolated)
    persistent_summary = summary(persistent)

    def difference(left: Any, right: Any) -> float | None:
        lhs = _number(left)
        rhs = _number(right)
        return lhs - rhs if lhs is not None and rhs is not None else None

    contrast = {
        "joint_win_rate_difference": difference(
            isolated_summary["joint_win_rate"], persistent_summary["joint_win_rate"]
        ),
        "mean_log_throughput_ratio_difference": difference(
            isolated_summary["mean_log_throughput_ratio"],
            persistent_summary["mean_log_throughput_ratio"],
        ),
        "mean_log_qpr_ratio_difference": difference(
            isolated_summary["mean_log_qpr_ratio"],
            persistent_summary["mean_log_qpr_ratio"],
        ),
    }
    loo = []
    for omitted in rows:
        retained = [row for row in rows if row["run_id"] != omitted["run_id"]]
        iso = summary([row for row in retained if row["isolated_only_activation"]])
        per = summary([row for row in retained if row["persistent_activation"]])
        loo.append(
            {
                "omitted_run_id": omitted["run_id"],
                "isolated_n": iso["n"],
                "persistent_n": per["n"],
                "joint_win_rate_difference": difference(
                    iso["joint_win_rate"], per["joint_win_rate"]
                ),
                "mean_log_throughput_ratio_difference": difference(
                    iso["mean_log_throughput_ratio"], per["mean_log_throughput_ratio"]
                ),
                "mean_log_qpr_ratio_difference": difference(
                    iso["mean_log_qpr_ratio"], per["mean_log_qpr_ratio"]
                ),
            }
        )
    return {
        "isolated_only": isolated_summary,
        "persistent": persistent_summary,
        "isolated_minus_persistent": contrast,
        "leave_one_run_out": loo,
    }


def evaluate_successor(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {
        (load, seed)
        for load in FORMAL_E1_LOADS
        for seed in G12_GLOBAL_READY_ADMISSION_SEEDS
    }
    identities = {(str(row.get("load")), str(row.get("seed"))) for row in rows}
    integrity = (
        len(rows) == 15
        and len(identities) == 15
        and identities == expected
        and len({str(row.get("run_id", "")) for row in rows}) == 15
        and all(row.get("g12_activation_pass") is True for row in rows)
        and all(row.get("runtime_identity_pass") is True for row in rows)
        and all(
            (_finite_int(row.get(field)) or 0) == 0
            for row in rows
            for field in VIOLATION_FIELDS
        )
    )
    groups = _group_summary(rows)
    isolated = groups["isolated_only"]
    persistent = groups["persistent"]
    contrast = groups["isolated_minus_persistent"]
    condition_2 = (
        isolated["n"] >= 3
        and persistent["n"] >= 3
        and len(isolated["loads"]) >= 2
        and len(persistent["loads"]) >= 2
    )
    condition_3 = (
        contrast["joint_win_rate_difference"] is not None
        and contrast["joint_win_rate_difference"] > 0.0
    )
    condition_4 = all(
        contrast[field] is not None and contrast[field] > 0.0
        for field in (
            "mean_log_throughput_ratio_difference",
            "mean_log_qpr_ratio_difference",
        )
    )
    defined_loo = [
        row
        for row in groups["leave_one_run_out"]
        if row["isolated_n"] > 0
        and row["persistent_n"] > 0
        and row["mean_log_throughput_ratio_difference"] is not None
        and row["mean_log_qpr_ratio_difference"] is not None
    ]
    condition_5 = len(defined_loo) == 15 and all(
        row["mean_log_throughput_ratio_difference"] > 0.0
        and row["mean_log_qpr_ratio_difference"] > 0.0
        for row in defined_loo
    )
    conditions = {
        "01_exact_15_pair_integrity_and_zero_structural_violations": integrity,
        "02_isolated_and_persistent_groups_each_n3_two_loads": condition_2,
        "03_isolated_joint_win_rate_above_persistent": condition_3,
        "04_isolated_mean_log_primary_ratios_above_persistent": condition_4,
        "05_both_mean_log_contrast_signs_positive_every_defined_loo": condition_5,
    }
    authorized = all(conditions.values())
    return {
        "status": (
            "complete_deferral_release_valve_preregistration_authorized"
            if authorized
            else "complete_no_deferral_release_valve_authorized"
        ),
        "deferral_release_valve_preregistration_authorized": authorized,
        "implementation_authorized": False,
        "sampling_authorized": False,
        "conditions": conditions,
        "failure_reasons": [name for name, passed in conditions.items() if not passed],
        "group_comparison": groups,
    }


def analyze(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest, g12_report = _validated_inputs(root)
    canonical = root / "online" / "canonical"
    result_relative_path = manifest["execution"].get(
        "result_relative_path", "result.json"
    )
    paired_index = {
        (row["load"], row["seed"]): row
        for row in g12_report["gate_result"]["paired_rows"]
    }
    metric_index = {
        row["run_id"]: row
        for row in g12_report["run_metrics"]
        if row["effective_method"] == G12_CANDIDATE
    }
    rows = []
    receipts = []
    for run in manifest["runs"]:
        method = run["metadata"]["m1_operational_candidate"]
        if method != G12_CANDIDATE:
            continue
        run_dir = canonical / run["run_id"]
        validate_canonical_run(
            run,
            run_dir,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        artifacts = load_run_artifacts(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative_path,
        )
        windows = [
            event for event in artifacts.nse_events if event.get("kind") == "window"
        ]
        key = (run["workload"]["request_freq"], run["seed"])
        paired = paired_index.get(key)
        metric = metric_index.get(run["run_id"])
        if not isinstance(paired, Mapping) or not isinstance(metric, Mapping):
            raise DiagnosisError("G12 report lacks a candidate pair or run metric")
        rows.append(_feature_row(run, windows, paired, metric))
        receipts.append(
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "tape_sha256": run["workload_tape"]["sha256"],
                "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
                "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
            }
        )
    decision = evaluate_successor(rows)
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "created_at": utc_now(),
        "status": decision["status"],
        "formal_results_eligible": False,
        "paper_claim_eligible": False,
        "source_root": {
            "path": str(root),
            "files": EXPECTED_ROOT_FILES,
            "bytes": EXPECTED_ROOT_BYTES,
            "inventory_sha256": EXPECTED_ROOT_HASH,
        },
        "definitions": {
            "independent_unit": "G12 candidate run/seed paired with same-tape C0",
            "deferral_episode": "maximal consecutive scheduler-window sequence with deferred_feasible_players>0",
            "isolated_only_activation": "positive deferral exists and longest episode equals one window",
            "persistent_activation": "longest positive-deferral episode is at least two adjacent windows",
            "joint_win": "throughput_ratio>1 and qpr_ratio>1",
            "ties_retained_as_nonwins": True,
            "threshold_estimated_from_outcomes": False,
        },
        "feature_rows": rows,
        "associations": _associations(rows),
        "decision": decision,
        "artifact_receipts": receipts,
        "run_count": len(rows),
        "implementation_authorized": False,
        "sampling_authorized": False,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
    }
    report["document_sha256"] = object_hash(report)
    return report


def write_analysis(root: Path, output: Path) -> dict[str, Any]:
    if output.exists() or output.parent.exists():
        raise DiagnosisError("G13 output workspace must be absent before analysis")
    report = analyze(root)
    output.parent.mkdir(parents=True)
    write_json_atomic(output, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("g12_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    write_analysis(args.g12_root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
