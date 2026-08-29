from __future__ import annotations

import gzip
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_blind_audit_v100 import (
    _assert_hashed_object,
    _assert_ledger_contract,
    _read_ledger,
    _require,
    _stage_root_from_receipts,
)
from scripts.reviewer_experiments.protocol.nse_e3_arrival_phase_training_prepare_v116 import (
    ARMS as PREPARED_ARMS,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    CONFIRMATION_SEEDS,
    OTHER_UNOPENED_SEEDS,
    PLAN,
    PLAN_SHA256,
    PREVIOUS_CONFIRMATION_SEEDS,
    PYTHON_SHA256,
    ROOT,
    TRAINING_SEEDS,
)
from scripts.reviewer_experiments.protocol.reference import inspect_reference_table
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.tape import inspect_tape
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


PREPARED = ROOT / "prepared-manifests-v116.json"
TAPES = ROOT / "tapes.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v116-training.json"
RESULT = ROOT / "training-result-v116.json"
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
ADMITTED_WORK_SOURCE = (
    "admitted_pending_plus_all_resident_remaining_and_same_window_projected_cpu_v1"
)
ADMITTED_INTERFERENCE_SOURCE = (
    "admitted_processor_sharing_interference_pending_resident_and_projected_cpu_v1"
)
LEGACY_WORK_SOURCE = "legacy_task_count_times_current_player_cpu_v108"
ARMS = {
    arm_id: {
        "experiment_id": "E3",
        "role": role,
        "profile": profile,
        "shock_rate_ratio": "3/2" if role == "candidate" else None,
        "shock_threshold_numerator": 3 if role == "candidate" else None,
        "shock_threshold_denominator": 2 if role == "candidate" else None,
        "shock_activation_horizon_frames": 50 if role == "candidate" else None,
        "diagnostic_activation_horizon_frames": 50 if role == "candidate" else 100,
        "critical_service_threshold_numerator": 9 if role == "candidate" else None,
        "critical_service_threshold_denominator": 10 if role == "candidate" else None,
        "work_source": ADMITTED_WORK_SOURCE
        if role == "candidate"
        else LEGACY_WORK_SOURCE,
        "interference_source": ADMITTED_INTERFERENCE_SOURCE
        if role == "candidate"
        else "not_applicable",
        "componentwise_interference_gate": False,
        "arrival_phase_guard": role == "candidate",
        "run_count": count,
    }
    for arm_id, role, profile, count in PREPARED_ARMS
}


def _arm_paths(arm_id: str) -> dict[str, Path]:
    workspace = ROOT / "runs" / arm_id
    return {
        "ready": ROOT / f"manifest.{arm_id}.ready.json",
        "references": ROOT / f"references.{arm_id}.catalog.json",
        "pairing": ROOT / f"pairing-audit.{arm_id}.json",
        "workspace": workspace,
    }


def _scenario(run: dict[str, Any]) -> str:
    return f"E3.{run['workload']['burst_name']}"


def _finite_nonnegative(value: Any) -> bool:
    return (
        type(value) in (int, float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0.0
    )


def _validate_admitted_work_diagnostics(
    run: dict[str, Any], canonical: Path, expected: dict[str, Any]
) -> dict[str, Any]:
    """Validate V116 mechanism evidence without opening any performance summary."""

    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V116 Nash diagnostics: {run['run_id']}")
    candidate = expected["role"] == "candidate"
    counts = Counter()
    exact_pending_total_sum = 0.0
    resident_remaining_total_sum = 0.0
    arrival_history: deque[tuple[int, int]] = deque(maxlen=100)
    arrival_last_frame: int | None = None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            counts["windows"] += 1
            frame = event.get("frame")
            _require(
                type(frame) is int and frame >= 0 and frame == counts["windows"] - 1,
                "invalid V116 window frame",
            )

            cluster = event.get("cluster")
            _require(isinstance(cluster, dict), "missing V116 cluster diagnostics")
            admitted_fields = (
                "queue_pending_cpu_work_total",
                "queue_pending_cpu_work_max",
                "queue_resident_remaining_cpu_work_total",
                "queue_resident_remaining_cpu_work_max",
            )
            frozen_v110_fields = (
                "queue_runnable_cpu_work_total",
                "queue_runnable_cpu_work_max",
            )
            if candidate:
                _require(
                    cluster.get("queue_cpu_work_observation_complete") is True
                    and cluster.get("queue_admitted_work_observation_complete") is True
                    and all(
                        _finite_nonnegative(cluster.get(field))
                        for field in (*admitted_fields, *frozen_v110_fields)
                    ),
                    f"V116 admitted-work observation changed: {run['run_id']}:{line_number}",
                )
                pending_count = cluster.get("queue_pending_cpu_value_count")
                resident_count = cluster.get("queue_resident_remaining_cpu_value_count")
                _require(
                    type(pending_count) is int
                    and pending_count >= 0
                    and pending_count == cluster.get("queue_pending_total")
                    and type(resident_count) is int
                    and resident_count >= 0
                    and resident_count == cluster.get("queue_resident_total"),
                    f"V116 admitted-work snapshot counts changed: "
                    f"{run['run_id']}:{line_number}",
                )
                _require(
                    float(cluster["queue_pending_cpu_work_total"]) + 1.0e-9
                    >= float(cluster["queue_pending_cpu_work_max"])
                    and float(cluster["queue_resident_remaining_cpu_work_total"])
                    + 1.0e-9
                    >= float(cluster["queue_resident_remaining_cpu_work_max"]),
                    f"V116 admitted-work aggregate changed: {run['run_id']}:{line_number}",
                )
                exact_pending_total_sum += float(
                    cluster["queue_pending_cpu_work_total"]
                )
                resident_remaining_total_sum += float(
                    cluster["queue_resident_remaining_cpu_work_total"]
                )
                counts["admitted_work_complete_windows"] += 1
                counts["pending_cpu_value_count"] += pending_count
                counts["resident_remaining_cpu_value_count"] += resident_count

            dominance = event.get("decision", {}).get("load_least_dominance_gate", {})
            gate = dominance.get("causal_arrival_shock")
            _require(
                isinstance(gate, dict)
                and gate.get("gate_enabled") is candidate
                and gate.get("baseline_frames") == 80
                and gate.get("recent_frames") == 20
                and gate.get("min_requests_per_window") == 20
                and gate.get("threshold_numerator")
                == expected["shock_threshold_numerator"]
                and gate.get("threshold_denominator")
                == expected["shock_threshold_denominator"]
                and gate.get("active_frames")
                == expected["diagnostic_activation_horizon_frames"]
                and gate.get("uses_first_seen_request_ids_only") is True,
                f"V116 causal contract changed: {run['run_id']}:{line_number}",
            )
            for field in ("first_seen_current_frame", "baseline_count", "recent_count"):
                _require(
                    type(gate.get(field)) is int and gate[field] >= 0,
                    f"V116 causal {field} changed: {run['run_id']}:{line_number}",
                )
            _require(
                type(gate.get("history_complete")) is bool
                and type(gate.get("active")) is bool,
                f"V116 causal types changed: {run['run_id']}:{line_number}",
            )
            until_frame = gate.get("until_frame")
            _require(
                until_frame is None or (type(until_frame) is int and until_frame >= 0),
                f"V116 causal deadline changed: {run['run_id']}:{line_number}",
            )
            _require(
                gate["active"] is (until_frame is not None and frame <= until_frame),
                f"V116 causal active flag changed: {run['run_id']}:{line_number}",
            )

            phase = gate.get("non_decreasing_phase")
            _require(
                isinstance(phase, dict)
                and phase.get("gate_enabled") is candidate
                and phase.get("window_frames") == 20
                and phase.get("comparison")
                == "current_greater_than_or_equal_to_previous"
                and phase.get("windows_are_adjacent_and_disjoint") is True
                and phase.get("uses_first_seen_request_ids_only") is True
                and type(phase.get("history_complete")) is bool
                and type(phase.get("non_decreasing")) is bool,
                f"V116 arrival-phase contract changed: {run['run_id']}:{line_number}",
            )
            if candidate:
                if arrival_last_frame is not None and frame != arrival_last_frame + 1:
                    arrival_history.clear()
                arrival_history.append((frame, gate["first_seen_current_frame"]))
                arrival_last_frame = frame
                phase_complete = (
                    len(arrival_history) == 100
                    and arrival_history[0][0] + 99 == arrival_history[-1][0]
                )
                previous_count = (
                    sum(count for _, count in list(arrival_history)[60:80])
                    if phase_complete
                    else None
                )
                current_count = (
                    sum(count for _, count in list(arrival_history)[80:100])
                    if phase_complete
                    else None
                )
                non_decreasing = bool(
                    phase_complete and current_count >= previous_count
                )
                _require(
                    phase["history_complete"] is phase_complete
                    and phase.get("previous_count") == previous_count
                    and phase.get("current_count") == current_count
                    and phase["non_decreasing"] is non_decreasing,
                    f"V116 arrival-phase reconstruction changed: "
                    f"{run['run_id']}:{line_number}",
                )
                counts["phase_complete_windows"] += int(phase_complete)
                counts["phase_non_decreasing_windows"] += int(non_decreasing)
                counts["phase_declining_windows"] += int(
                    phase_complete and not non_decreasing
                )
                counts["phase_declining_active_windows"] += int(
                    phase_complete and not non_decreasing and gate["active"]
                )
            else:
                _require(
                    phase["history_complete"] is False
                    and phase.get("previous_count") is None
                    and phase.get("current_count") is None
                    and phase["non_decreasing"] is False,
                    f"V116 anchor used arrival-phase state: "
                    f"{run['run_id']}:{line_number}",
                )

            critical = dominance.get("critical_service_proxy")
            _require(isinstance(critical, dict), "missing V116 critical diagnostics")
            solver_termination = event.get("solver", {}).get("termination")
            invoked = candidate and solver_termination != "no_players"
            _require(
                critical.get("gate_enabled") is invoked
                and type(critical.get("evaluated")) is bool
                and type(critical.get("accepted")) is bool
                and critical.get("threshold_numerator")
                == (
                    expected["critical_service_threshold_numerator"]
                    if invoked
                    else None
                )
                and critical.get("threshold_denominator")
                == (
                    expected["critical_service_threshold_denominator"]
                    if invoked
                    else None
                )
                and critical.get("work_source") == expected["work_source"]
                and critical.get("noncritical_players_preserve_exact_anchor") is True
                and critical.get("proxy_uses_completion_outcomes") is False,
                f"V116 critical-service contract changed: {run['run_id']}:{line_number}",
            )
            for field in (
                "critical_player_count",
                "candidate_evaluation_count",
                "substitution_count",
                "proxy_input_unavailable_count",
            ):
                _require(
                    type(critical.get(field)) is int and critical[field] >= 0,
                    f"V116 critical {field} changed: {run['run_id']}:{line_number}",
                )
            _require(
                not critical["accepted"] or critical["evaluated"],
                f"V116 accepted without evaluation: {run['run_id']}:{line_number}",
            )
            interference = critical.get("admitted_interference_pareto")
            _require(
                isinstance(interference, dict)
                and interference.get("gate_enabled") is invoked
                and interference.get("componentwise_gate_enabled")
                is expected["componentwise_interference_gate"]
                and type(interference.get("rejected_candidate_count")) is int
                and interference["rejected_candidate_count"] == 0
                and type(interference.get("input_unavailable_count")) is int
                and interference["input_unavailable_count"] >= 0
                and interference.get("source")
                == (expected["interference_source"] if invoked else "not_applicable"),
                f"V116 admitted-interference contract changed: "
                f"{run['run_id']}:{line_number}",
            )
            interference_values = tuple(
                interference.get(field)
                for field in (
                    "anchor_sum",
                    "alternative_sum",
                    "alternative_minus_anchor",
                )
            )
            if invoked and all(value is not None for value in interference_values):
                _require(
                    _finite_nonnegative(interference_values[0])
                    and _finite_nonnegative(interference_values[1])
                    and type(interference_values[2]) in (int, float)
                    and not isinstance(interference_values[2], bool)
                    and math.isfinite(float(interference_values[2]))
                    and math.isclose(
                        float(interference_values[2]),
                        float(interference_values[1]) - float(interference_values[0]),
                        rel_tol=1.0e-12,
                        abs_tol=1.0e-9,
                    ),
                    f"V116 admitted-interference evidence changed: "
                    f"{run['run_id']}:{line_number}",
                )
                counts["interference_finite_windows"] += 1
                counts["interference_anchor_sum"] += float(interference_values[0])
                counts["interference_alternative_sum"] += float(interference_values[1])
            else:
                _require(
                    all(value is None for value in interference_values),
                    f"V116 partial admitted-interference evidence: "
                    f"{run['run_id']}:{line_number}",
                )
            if critical["accepted"]:
                _require(
                    all(value is not None for value in interference_values)
                    and float(interference_values[1])
                    <= float(interference_values[0]) + 1.0e-9,
                    f"V116 accepted worse admitted interference: "
                    f"{run['run_id']}:{line_number}",
                )
                _require(
                    phase["history_complete"] is True
                    and phase["non_decreasing"] is True,
                    f"V116 accepted outside non-decreasing arrival phase: "
                    f"{run['run_id']}:{line_number}",
                )
                counts["interference_accepted_windows"] += 1
            counts["interference_rejected_candidates"] += interference[
                "rejected_candidate_count"
            ]
            counts["interference_input_unavailable"] += interference[
                "input_unavailable_count"
            ]
            if not invoked:
                _require(
                    critical["evaluated"] is False
                    and critical["accepted"] is False
                    and critical["critical_player_count"] == 0
                    and critical["candidate_evaluation_count"] == 0
                    and critical["substitution_count"] == 0
                    and critical["proxy_input_unavailable_count"] == 0,
                    f"V116 non-invoked critical state changed: {run['run_id']}:{line_number}",
                )
                _require(
                    interference["rejected_candidate_count"] == 0
                    and interference["input_unavailable_count"] == 0,
                    f"V116 non-invoked interference state changed: "
                    f"{run['run_id']}:{line_number}",
                )
            if critical["accepted"]:
                values = tuple(
                    critical.get(field)
                    for field in (
                        "anchor_sum",
                        "alternative_sum",
                        "alternative_minus_anchor",
                        "minimum_individually_accepted_ratio",
                        "maximum_individually_accepted_ratio",
                    )
                )
                _require(
                    all(_finite_nonnegative(value) for value in values[:2])
                    and all(
                        type(value) in (int, float)
                        and not isinstance(value, bool)
                        and math.isfinite(float(value))
                        for value in values[2:]
                    ),
                    f"V116 accepted evidence is nonfinite: {run['run_id']}:{line_number}",
                )
                anchor_sum, alternative_sum, delta, minimum_ratio, maximum_ratio = (
                    float(value) for value in values
                )
                _require(
                    critical["substitution_count"] > 0
                    and alternative_sum < anchor_sum
                    and math.isclose(
                        delta,
                        alternative_sum - anchor_sum,
                        rel_tol=1.0e-12,
                        abs_tol=1.0e-9,
                    )
                    and 0.0 <= minimum_ratio <= maximum_ratio <= 0.900001,
                    f"V116 accepted admitted-work certificate changed: "
                    f"{run['run_id']}:{line_number}",
                )
            counts["active_windows"] += int(gate["active"])
            counts["critical_evaluated_windows"] += int(critical["evaluated"])
            counts["critical_accepted_windows"] += int(critical["accepted"])
            counts["critical_players"] += critical["critical_player_count"]
            counts["candidate_evaluations"] += critical["candidate_evaluation_count"]
            counts["substitutions"] += critical["substitution_count"]
            counts["proxy_input_unavailable"] += critical[
                "proxy_input_unavailable_count"
            ]

            if not candidate:
                _require(
                    gate["history_complete"] is False
                    and gate["baseline_count"] == 0
                    and gate["recent_count"] == 0
                    and gate["active"] is False
                    and until_frame is None,
                    f"V116 anchor used causal state: {run['run_id']}:{line_number}",
                )
                continue
            if not gate["history_complete"]:
                _require(
                    gate["baseline_count"] == 0 and gate["recent_count"] == 0,
                    f"V116 incomplete history leaked counts: {run['run_id']}:{line_number}",
                )
                continue
            sufficient = (
                gate["baseline_count"] >= gate["min_requests_per_window"]
                and gate["recent_count"] >= gate["min_requests_per_window"]
            )
            recent_scaled = (
                gate["recent_count"]
                * gate["baseline_frames"]
                * gate["threshold_denominator"]
            )
            baseline_scaled = (
                gate["baseline_count"]
                * gate["recent_frames"]
                * gate["threshold_numerator"]
            )
            if sufficient and recent_scaled >= baseline_scaled:
                counts["threshold_met_windows"] += 1
                _require(
                    gate["active"] is True
                    and until_frame
                    >= frame + expected["diagnostic_activation_horizon_frames"] - 1,
                    f"V116 exact threshold did not activate: "
                    f"{run['run_id']}:{line_number}",
                )

    _require(
        counts["windows"] == run["simulation"]["total_frame"],
        f"V116 diagnostic window count changed: {run['run_id']}",
    )
    if candidate:
        _require(
            counts["admitted_work_complete_windows"] == counts["windows"]
            and counts["threshold_met_windows"] > 0
            and counts["active_windows"] > 0
            and counts["critical_evaluated_windows"] > 0,
            f"V116 mechanism was not exercised: {run['run_id']}",
        )
    return {
        "file_sha256": file_hash(path),
        "window_count": counts["windows"],
        "admitted_work_complete_window_count": counts["admitted_work_complete_windows"],
        "pending_cpu_value_count": counts["pending_cpu_value_count"],
        "resident_remaining_cpu_value_count": counts[
            "resident_remaining_cpu_value_count"
        ],
        "exact_pending_cpu_work_total_sum": exact_pending_total_sum,
        "resident_remaining_cpu_work_total_sum": resident_remaining_total_sum,
        "active_window_count": counts["active_windows"],
        "threshold_met_window_count": counts["threshold_met_windows"],
        "arrival_phase_complete_window_count": counts["phase_complete_windows"],
        "arrival_phase_non_decreasing_window_count": counts[
            "phase_non_decreasing_windows"
        ],
        "arrival_phase_declining_window_count": counts["phase_declining_windows"],
        "arrival_phase_declining_active_window_count": counts[
            "phase_declining_active_windows"
        ],
        "critical_evaluated_window_count": counts["critical_evaluated_windows"],
        "critical_accepted_window_count": counts["critical_accepted_windows"],
        "critical_player_count": counts["critical_players"],
        "critical_candidate_evaluation_count": counts["candidate_evaluations"],
        "critical_substitution_count": counts["substitutions"],
        "proxy_input_unavailable_count": counts["proxy_input_unavailable"],
        "work_source": expected["work_source"],
        "admitted_interference_source": expected["interference_source"],
        "componentwise_admitted_interference_gate_enabled": expected[
            "componentwise_interference_gate"
        ],
        "admitted_interference_finite_window_count": counts[
            "interference_finite_windows"
        ],
        "admitted_interference_accepted_window_count": counts[
            "interference_accepted_windows"
        ],
        "admitted_interference_rejected_candidate_count": counts[
            "interference_rejected_candidates"
        ],
        "admitted_interference_input_unavailable_count": counts[
            "interference_input_unavailable"
        ],
        "admitted_interference_anchor_total": counts["interference_anchor_sum"],
        "admitted_interference_alternative_total": counts[
            "interference_alternative_sum"
        ],
        "performance_fields_consulted": False,
    }


def _verify_tape_catalog() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(TAPES.is_file(), f"missing V116 tape catalog: {TAPES}")
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V116 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12, "V116 tape count changed"
    )
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(info.sha256 == entry["sha256"], f"tape hash changed: {key}")
        _require(info.workload_seed in TRAINING_SEEDS, f"unexpected tape seed: {key}")
        evidence.append(
            {
                "key": key,
                "sha256": info.sha256,
                "event_count": info.event_count,
                "dag_order_sha256": info.dag_order_sha256,
                "workload_seed": info.workload_seed,
                "kind": entry["kind"],
            }
        )
    _require(
        Counter(item["kind"] for item in evidence)
        == Counter({"base_steady": 3, "derived_burst": 9}),
        "V116 tape kind boundary changed",
    )
    _require(
        Counter(item["workload_seed"] for item in evidence)
        == Counter({seed: 4 for seed in TRAINING_SEEDS}),
        "V116 paired tape seed product changed",
    )
    base_entries = {
        key: entry for key, entry in entries.items() if entry["kind"] == "base_steady"
    }
    capture_root = _stage_root_from_receipts(
        base_entries, "capture_receipt_path", 3, "V116 tape capture"
    )
    rows, last_hash = _read_ledger(capture_root / "ledger.jsonl")
    _assert_ledger_contract(
        rows, Counter({"capture_canonicalized": 3}), "V116 tape capture"
    )
    _require(
        not list((capture_root / "quarantine").glob("**/attempt-*")),
        "V116 tape capture has quarantined attempts",
    )
    return evidence, {
        "catalog_path": str(TAPES),
        "catalog_file_sha256": file_hash(TAPES),
        "catalog_hash": catalog_hash,
        "capture_stage_root": str(capture_root),
        "capture_ledger_last_hash": last_hash,
    }


def _verify_reference_stage_ledgers() -> tuple[dict[str, Path], dict[Path, str]]:
    roots: dict[str, Path] = {}
    expected_by_root: Counter[Path] = Counter()
    for arm_id, expected in ARMS.items():
        catalog_path = ROOT / f"references.{arm_id}.catalog.json"
        _require(catalog_path.is_file(), f"missing reference catalog: {arm_id}")
        entries = read_json(catalog_path).get("entries")
        _require(isinstance(entries, dict), f"reference catalog malformed: {arm_id}")
        root = _stage_root_from_receipts(
            entries, "receipt_path", expected["run_count"], f"V116 reference {arm_id}"
        )
        roots[arm_id] = root
        expected_by_root[root] += expected["run_count"]
    hashes: dict[Path, str] = {}
    for root, expected_count in expected_by_root.items():
        rows, last_hash = _read_ledger(root / "ledger.jsonl")
        _assert_ledger_contract(
            rows,
            Counter({"reference_build_canonicalized": expected_count}),
            f"V116 reference stage {root}",
        )
        _require(
            not list((root / "quarantine").glob("**/attempt-*")),
            f"V116 reference quarantine is nonempty: {root}",
        )
        hashes[root] = last_hash
    return roots, hashes


def _validate_run_boundary(
    run: dict[str, Any], arm_id: str, expected: dict[str, Any]
) -> None:
    candidate = expected["role"] == "candidate"
    metadata = run.get("metadata", {})
    required = {
        "v116_training_plan_sha256": PLAN_SHA256,
        "v116_training_only": True,
        "v116_training_seed_metrics_previously_revealed": False,
        "v116_confirmation_seeds_opened": False,
        "v116_other_unopened_seeds_opened": False,
        "v116_formal_E01_E20_reexecution": False,
        "v116_arm_id": arm_id,
        "v116_arm_role": expected["role"],
        "v116_candidate_profile": expected["profile"],
        "v116_candidate_experiment": "E3",
        "v116_shock_rate_ratio": expected["shock_rate_ratio"],
        "v116_shock_threshold_numerator": expected["shock_threshold_numerator"],
        "v116_shock_threshold_denominator": expected["shock_threshold_denominator"],
        "v116_arrival_history_baseline_frames": 80 if candidate else None,
        "v116_arrival_history_recent_frames": 20 if candidate else None,
        "v116_arrival_min_requests_per_window": 20 if candidate else None,
        "v116_shock_activation_horizon_frames": expected[
            "shock_activation_horizon_frames"
        ],
        "v116_nonterminal_queue_density_floor": 8.0 if candidate else None,
        "v116_warm_admissibility": "preserve_anchor_warmness" if candidate else None,
        "v116_load_least_window_certificate_mode": (
            "disabled" if candidate else "not_applicable"
        ),
        "v116_critical_service_ratio_numerator": expected[
            "critical_service_threshold_numerator"
        ],
        "v116_critical_service_ratio_denominator": expected[
            "critical_service_threshold_denominator"
        ],
        "v116_critical_service_proxy": (
            "remote_parent_transfer_plus_cold_start_plus_admitted_queue_cpu_work"
            if candidate
            else "not_applicable"
        ),
        "v116_service_proxy_work_source": (
            ADMITTED_WORK_SOURCE if candidate else "not_applicable"
        ),
        "v116_admitted_work_includes_all_blocked_resident": candidate,
        "v116_admitted_work_deterministic_f64_sum": candidate,
        "v116_admitted_interference_pareto": candidate,
        "v116_componentwise_admitted_interference_pareto": False,
        "v116_admitted_interference_source": (
            ADMITTED_INTERFERENCE_SOURCE if candidate else "not_applicable"
        ),
        "v116_admitted_interference_inputs_finite_fail_closed": candidate,
        "v116_complete_admitted_interference_nonworse": candidate,
        "v116_arrival_phase_guard": candidate,
        "v116_arrival_phase_window_frames": 20 if candidate else None,
        "v116_arrival_phase_previous_history_offsets": (
            [60, 79] if candidate else None
        ),
        "v116_arrival_phase_current_history_offsets": ([80, 99] if candidate else None),
        "v116_arrival_phase_comparison": (
            "current_greater_than_or_equal_to_previous"
            if candidate
            else "not_applicable"
        ),
        "v116_arrival_phase_windows_adjacent_and_disjoint": candidate,
        "v116_arrival_phase_incomplete_or_overflow_fail_closed": candidate,
        "v116_critical_service_proxy_inputs_finite_fail_closed": candidate,
        "v116_cpu_memory_individual_noninferiority": candidate,
        "v116_scalar_faasrank_noninferiority": candidate,
        "v116_input_locality_component_noninferiority": candidate,
        "v116_per_child_current_warm_downstream_locality_noninferiority": candidate,
        "v116_critical_frontier_substitution": candidate,
        "v116_critical_frontier_rank_source": (
            "immutable_srpt_remaining_critical_path_rank"
            if candidate
            else "not_applicable"
        ),
        "v116_noncritical_exact_anchor": candidate,
        "v116_complete_summed_critical_service_proxy_strictly_lower": candidate,
        "v116_complete_routed_score_nonworse": candidate,
        "v116_complete_exact_ocs_score_nonworse": candidate,
        "v116_complete_immutable_baseline_welfare_nonworse": candidate,
        "v116_outcome_fields_drive_policy": False,
        "v116_scenario_or_burst_label_used_by_policy": False,
        "v116_completion_or_performance_fields_used_by_policy": False,
        "v116_future_arrivals_used_by_policy": False,
    }
    _require(
        run["experiment_id"] == "E3"
        and run["method"] == "sche_nash"
        and run["seed"] in TRAINING_SEEDS
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced"
        and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
        and run["environment"].get("NASH_OPERATIONAL_EXPERT_PROXY")
        == expected["profile"]
        and all(metadata.get(key) == value for key, value in required.items()),
        f"V116 run boundary changed: {run['run_id']}",
    )


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V116 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V116 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V116 plan changed")
    plan = read_json(PLAN)
    _require(plan.get("formal_results_eligible") is False, "V116 eligibility changed")
    _require(PREPARED.is_file(), f"missing V116 prepared receipt: {PREPARED}")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V116 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("other_unopened_inputs_generated") is False
        and set(prepared.get("training_seeds", [])) == TRAINING_SEEDS
        and prepared.get("untouched_confirmation_seeds") == CONFIRMATION_SEEDS
        and prepared.get("previous_confirmation_seeds_remaining_sealed")
        == PREVIOUS_CONFIRMATION_SEEDS
        and prepared.get("other_unopened_seeds_untouched") == OTHER_UNOPENED_SEEDS
        and prepared.get("arm_online_runs") == 18
        and prepared.get("arm_reference_builds") == 18,
        "V116 prepared scientific boundary changed",
    )
    tape_evidence, tape_catalog_evidence = _verify_tape_catalog()
    reference_roots, reference_ledger_hashes = _verify_reference_stage_ledgers()

    run_evidence: list[dict[str, Any]] = []
    reference_evidence: list[dict[str, Any]] = []
    pairing_evidence: list[dict[str, Any]] = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    paired_inputs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    ready_manifests: dict[str, dict[str, Any]] = {}

    for arm_id, expected in ARMS.items():
        paths = _arm_paths(arm_id)
        _require(paths["ready"].is_file(), f"missing V116 ready manifest: {arm_id}")
        manifest = load_and_validate_manifest(paths["ready"])
        _require(
            len(manifest["runs"]) == expected["run_count"]
            and manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_faasrank_models_bound") is False
            and manifest.get("all_references_bound") is True,
            f"V116 ready boundary changed: {arm_id}",
        )
        ready_manifests[arm_id] = {
            "path": str(paths["ready"]),
            "file_sha256": file_hash(paths["ready"]),
            "manifest_hash": manifest["manifest_hash"],
        }

        references = read_json(paths["references"])
        reference_catalog_hash = _assert_hashed_object(
            references, "catalog_hash", f"V116 references {arm_id}"
        )
        entries = references.get("entries")
        declared_keys = {
            item["key"] for item in manifest["reference_build_dependencies"]
        }
        _require(
            isinstance(entries, dict)
            and set(entries) == declared_keys
            and len(entries) == expected["run_count"],
            f"V116 reference key set changed: {arm_id}",
        )
        for key, entry in sorted(entries.items()):
            info = inspect_reference_table(Path(entry["path"]))
            _require(
                all(
                    getattr(info, field) == entry[field]
                    for field in (
                        "sha256",
                        "bytes",
                        "line_count",
                        "state_pair_sequence_sha256",
                    )
                )
                and file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"]
                and file_hash(Path(entry["build_process_observation_path"]))
                == entry["build_process_observation_sha256"],
                f"V116 reference evidence changed: {key}",
            )
            reference_evidence.append(
                {
                    "arm_id": arm_id,
                    "key": key,
                    "sha256": entry["sha256"],
                    "receipt_sha256": entry["receipt_sha256"],
                    "build_spec_hash": entry["build_spec_hash"],
                    "workload_tape_sha256": entry["workload_tape_sha256"],
                    "catalog_hash": reference_catalog_hash,
                }
            )
        reference_last_hash = reference_ledger_hashes[reference_roots[arm_id]]

        pairing = read_json(paths["pairing"])
        _require(
            pairing.get("passed") is True
            and pairing.get("failed_group_count") == 0
            and pairing.get("run_count") == expected["run_count"]
            and pairing.get("group_count") == expected["run_count"],
            f"V116 pairing changed: {arm_id}",
        )
        pairing_evidence.append(
            {
                "arm_id": arm_id,
                "file_sha256": file_hash(paths["pairing"]),
                "run_count": pairing["run_count"],
                "group_count": pairing["group_count"],
                "passed": True,
            }
        )

        workspace = paths["workspace"]
        expected_ids = {run["run_id"] for run in manifest["runs"]}
        actual_ids = {
            path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
        }
        _require(actual_ids == expected_ids, f"V116 canonical set changed: {arm_id}")
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V116 online quarantine is nonempty: {arm_id}",
        )
        ledger_rows, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
        _assert_ledger_contract(
            ledger_rows,
            Counter(
                {
                    "batch_started": 1,
                    "attempt_started": expected["run_count"],
                    "attempt_canonicalized": expected["run_count"],
                    "batch_finished": 1,
                }
            ),
            f"V116 online {arm_id}",
        )

        for run in manifest["runs"]:
            _validate_run_boundary(run, arm_id, expected)
            canonical = workspace / "canonical" / run["run_id"]
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            diagnostics = _validate_admitted_work_diagnostics(run, canonical, expected)
            attempt = read_json(canonical / "attempt.json")
            qc = read_json(canonical / "qc_report.json")
            audit_manifest = read_json(canonical / "manifest.json")
            _require(
                attempt.get("attempt") == 1
                and attempt.get("status") == "qc_pass"
                and attempt.get("classification") == "qc_pass"
                and attempt.get("timed_out") is False
                and attempt.get("exit_code") == 0
                and qc.get("passed") is True
                and qc.get("classification") == "qc_pass",
                f"V116 canonical status changed: {run['run_id']}",
            )
            runtime = {
                "binary_sha256": audit_manifest["adapter_binary"]["verified_sha256"],
                "git_commit": audit_manifest["software_environment"]["git"]["commit"],
                "python_executable_sha256": audit_manifest["software_environment"][
                    "python"
                ]["executable_sha256"],
                "cargo_lock_sha256": audit_manifest["software_environment"][
                    "cargo_lock"
                ]["sha256"],
            }
            for field, value in runtime.items():
                runtime_values[field].add(str(value))
            scenario = _scenario(run)
            paired_inputs[(scenario, run["seed"])].append(
                {
                    "arm_id": arm_id,
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "workload_tape_key": run["workload_tape"]["key"],
                    "workload_spec_hash": run["workload_spec_hash"],
                    "capture_environment_sha256": run["workload_tape"][
                        "capture_environment"
                    ]["capture_environment_sha256"],
                    "common_hpa_hash": run["common_hpa_hash"],
                    "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
                    "faasrank_model": run["simulator_experiment"]["faasrank_model"],
                    "simulation": run["simulation"],
                }
            )
            run_evidence.append(
                {
                    "arm_id": arm_id,
                    "run_id": run["run_id"],
                    "experiment_id": "E3",
                    "scenario": scenario,
                    "seed": run["seed"],
                    "run_spec_hash": run["run_spec_hash"],
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "reference_key": run["reference_dependency"]["key"],
                    "result_sha256": attempt["result_sha256"],
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "attempt": 1,
                    "classification": "qc_pass",
                    "admitted_work_diagnostics": diagnostics,
                    "ledger_last_hash": ledger_last_hash,
                    "reference_ledger_last_hash": reference_last_hash,
                }
            )

    _require(len(run_evidence) == 18, "V116 run evidence count must be 18")
    _require(len(reference_evidence) == 18, "V116 reference evidence count must be 18")
    _require(len(tape_evidence) == 12, "V116 tape evidence count must be 12")
    candidate_diagnostics = [
        item["admitted_work_diagnostics"]
        for item in run_evidence
        if ARMS[item["arm_id"]]["role"] == "candidate"
    ]
    _require(
        sum(
            item["arrival_phase_complete_window_count"]
            for item in candidate_diagnostics
        )
        > 0
        and sum(
            item["arrival_phase_non_decreasing_window_count"]
            for item in candidate_diagnostics
        )
        > 0
        and sum(
            item["arrival_phase_declining_active_window_count"]
            for item in candidate_diagnostics
        )
        > 0,
        "V116 arrival-phase guard was not exercised on both causal sides",
    )
    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V116 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V116 runtime git identity is not singular: {git_commits}",
    )
    _require(len(paired_inputs) == 9, "V116 paired input product changed")
    for (scenario, seed), rows in paired_inputs.items():
        _require(len(rows) == 2, f"V116 paired arm count changed: {scenario}/{seed}")
        for field in (
            "workload_tape_sha256",
            "workload_tape_key",
            "workload_spec_hash",
            "capture_environment_sha256",
            "common_hpa_hash",
            "sla_artifact_sha256",
            "faasrank_model",
            "simulation",
        ):
            _require(
                len({object_hash(row[field]) for row in rows}) == 1,
                f"V116 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V116 common HPA changed: {scenario}/{seed}",
        )

    output_payload = {
        "schema_version": "NSE_E3_ARRIVAL_PHASE_BLIND_AUDIT_V116_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "mechanism_diagnostic_windows_parsed": sum(
            run["admitted_work_diagnostics"]["window_count"] for run in run_evidence
        ),
        "mechanism_diagnostics_consulted_for_performance_selection": False,
        "performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "other_unopened_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "runtime_identity": {
            **EXPECTED_RUNTIME,
            "git_commit": next(iter(runtime_values["git_commit"])),
        },
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "previous_confirmation_seeds_remaining_sealed": PREVIOUS_CONFIRMATION_SEEDS,
        "other_unopened_seeds_untouched": OTHER_UNOPENED_SEEDS,
        "arm_count": len(ARMS),
        "run_count": len(run_evidence),
        "reference_count": len(reference_evidence),
        "tape_count": len(tape_evidence),
        "ready_manifests": ready_manifests,
        "tape_catalog": tape_catalog_evidence,
        "pairing_audits": pairing_evidence,
        "tapes": tape_evidence,
        "references": reference_evidence,
        "runs": run_evidence,
    }
    output_payload["audit_hash"] = object_hash(output_payload)
    write_json_atomic(output, output_payload)
    return output_payload


def main() -> None:
    audit = run_blind_audit()
    print(OUTPUT)
    print(file_hash(OUTPUT))
    print(audit["audit_hash"])


if __name__ == "__main__":
    main()
