from __future__ import annotations

import gzip
import json
import math
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.nse_e3_load_band_warm_admissibility_training_blind_audit_v100 import (
    _assert_hashed_object,
    _read_ledger,
    _require,
    _stage_root_from_receipts,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_execute_v142 import (
    EXECUTION_RECEIPT,
    READY_SCHEDULE,
    ready_manifest_path,
    workspace_path,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    ARMS as PREPARED_ARMS,
    ARM_IDS,
    BASELINE_METHODS,
    BINARY_SOURCE_COMMIT,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    METHOD_LABELS,
    NEW_CONFIRMATION_SEEDS,
    PAPER_WELFARE_STATE_DOMAIN,
    PLAN,
    PLAN_SHA256,
    PYTHON_SHA256,
    RANDOM_PREFIX_COHORT_SOURCE,
    RANDOM_SHADOW_LIFECYCLE,
    RETIRED_OPENED_V138_TRAINING_SEEDS,
    RETIRED_OPENED_V139_TRAINING_SEEDS,
    RETIRED_OPENED_V140_TRAINING_SEEDS,
    RETIRED_OPENED_V141_TRAINING_SEEDS,
    RETIRED_V137_CONFIRMATION_SEEDS,
    ROOT,
    SCENARIOS,
    SERVICE_CERTIFICATE_SCOPE,
    SERVICE_CERTIFICATE_STATE_DOMAIN,
    TRAINING_SEED_LIST,
    TRAINING_SEEDS,
    native_members,
    paths,
    scenario_id,
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


PREPARED = ROOT / "prepared-manifests-v142.json"
TAPES = ROOT / "tapes.catalog.json"
OUTPUT = ROOT / "joint-blind-audit-v142-training.json"
RESULT = ROOT / "training-result-v142.json"
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
ARMS = {
    arm_id: {"profile": profile, "selection_rule": rule, "run_count": 9}
    for arm_id, profile, rule in PREPARED_ARMS
}
NATIVE_KINDS = ["random", "greedy", "hiku", "jiagu", "orion", "load_least"]


def pairing_path(root: Path, manifest_id: str) -> Path:
    return root / f"pairing-audit.{manifest_id}.json"


def reference_catalog_path(root: Path, arm_id: str) -> Path:
    return root / f"references.{arm_id}.catalog.json"


def _finite(value: Any) -> bool:
    return (
        type(value) in (int, float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _f32(value: Any) -> float:
    return struct.unpack("!f", struct.pack("!f", float(value)))[0]


def _metric_key(value: Any, *, descending: bool = False) -> tuple[float, int]:
    number = float(value)
    sign_tiebreak = 0 if math.copysign(1.0, number) < 0.0 else 1
    if descending:
        return (-number, 1 - sign_tiebreak)
    return (number, sign_tiebreak)


def _metric_equal(left: Any, right: Any) -> bool:
    return _metric_key(left) == _metric_key(right)


def _verify_tapes() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(TAPES.is_file(), f"missing V142 tape catalog: {TAPES}")
    catalog = read_json(TAPES)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V142 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12, "V142 tape count changed"
    )
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(info.sha256 == entry["sha256"], f"V142 tape hash changed: {key}")
        _require(info.workload_seed in TRAINING_SEEDS, f"V142 tape seed changed: {key}")
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
        "V142 tape kinds changed",
    )
    _require(
        Counter(item["workload_seed"] for item in evidence)
        == Counter({seed: 4 for seed in TRAINING_SEEDS}),
        "V142 tape seed product changed",
    )
    base = {
        key: value for key, value in entries.items() if value["kind"] == "base_steady"
    }
    capture_root = _stage_root_from_receipts(
        base, "capture_receipt_path", 3, "V142 tape capture"
    )
    rows, last_hash = _read_ledger(capture_root / "ledger.jsonl")
    counts = Counter(row["event_type"] for row in rows)
    _require(
        counts == Counter({"capture_canonicalized": 3}),
        f"V142 capture ledger changed: {counts}",
    )
    _require(
        not list((capture_root / "quarantine").glob("**/attempt-*")),
        "V142 tape capture quarantine is nonempty",
    )
    return evidence, {
        "catalog_path": str(TAPES),
        "catalog_file_sha256": file_hash(TAPES),
        "catalog_hash": catalog_hash,
        "capture_stage_root": str(capture_root),
        "capture_ledger_last_hash": last_hash,
    }


def _verify_references() -> tuple[list[dict[str, Any]], dict[str, str]]:
    evidence = []
    ledger_hashes = {}
    for arm_id in ARM_IDS:
        path = reference_catalog_path(ROOT, arm_id)
        _require(path.is_file(), f"missing V142 reference catalog: {arm_id}")
        catalog = read_json(path)
        catalog_hash = _assert_hashed_object(
            catalog, "catalog_hash", f"V142 references {arm_id}"
        )
        entries = catalog.get("entries")
        _require(
            isinstance(entries, dict) and len(entries) == 9,
            f"V142 reference count changed: {arm_id}",
        )
        root = _stage_root_from_receipts(
            entries, "receipt_path", 9, f"V142 references {arm_id}"
        )
        rows, last_hash = _read_ledger(root / "ledger.jsonl")
        counts = Counter(row["event_type"] for row in rows)
        _require(
            counts == Counter({"reference_build_canonicalized": 9}),
            f"V142 reference ledger changed: {arm_id}/{counts}",
        )
        _require(
            not list((root / "quarantine").glob("**/attempt-*")),
            f"V142 reference quarantine is nonempty: {arm_id}",
        )
        ledger_hashes[arm_id] = last_hash
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
                f"V142 reference evidence changed: {key}",
            )
            evidence.append(
                {
                    "arm_id": arm_id,
                    "key": key,
                    "sha256": entry["sha256"],
                    "receipt_sha256": entry["receipt_sha256"],
                    "build_spec_hash": entry["build_spec_hash"],
                    "workload_tape_sha256": entry["workload_tape_sha256"],
                    "catalog_hash": catalog_hash,
                }
            )
    _require(len(evidence) == 27, "V142 reference evidence count changed")
    return evidence, ledger_hashes


def _rank_portfolio_candidates(
    candidates: list[dict[str, Any]]
) -> list[dict[str, int]]:
    ranks = [dict() for _ in candidates]
    for field, rank_field, reverse in (
        ("service_max", "service_max_rank", False),
        ("service_sum", "service_sum_rank", False),
        ("paper_welfare", "paper_welfare_rank", True),
    ):
        order = sorted(
            range(len(candidates)),
            key=lambda index: (
                _metric_key(candidates[index][field], descending=reverse),
                index,
            ),
        )
        for rank, index in enumerate(order, start=1):
            ranks[index][rank_field] = rank
    for item in ranks:
        item["rank_sum"] = (
            item["service_max_rank"]
            + item["service_sum_rank"]
            + item["paper_welfare_rank"]
        )
    return ranks


def _expected_portfolio_selection(
    rule: str, candidates: list[dict[str, Any]], ranks: list[dict[str, int]]
) -> tuple[int, str]:
    del ranks
    _require(
        len(candidates) == 6 and candidates[0].get("kind") == "random",
        "V142 Random-default portfolio order changed",
    )
    random = candidates[0]
    epsilon = 1.0e-6
    if rule == "random_prefix_service_pareto":
        admissible = [
            index
            for index in range(1, len(candidates))
            if float(candidates[index]["service_max"])
            <= float(random["service_max"]) + epsilon
            and float(candidates[index]["service_sum"])
            < float(random["service_sum"]) - epsilon
            and float(candidates[index]["paper_welfare"]) + epsilon
            >= float(random["paper_welfare"])
        ]
        if not admissible:
            return 0, "random_default_no_strict_service_pareto_replacement"
        selected = min(
            admissible,
            key=lambda index: (
                _metric_key(candidates[index]["service_sum"]),
                _metric_key(candidates[index]["paper_welfare"], descending=True),
                index,
            ),
        )
        return selected, "strict_service_pareto_replacement_minimum_service_sum"
    _require(
        rule == "random_prefix_welfare_pareto",
        f"unknown V142 portfolio rule: {rule}",
    )
    admissible = [
        index
        for index in range(1, len(candidates))
        if float(candidates[index]["service_max"])
        <= float(random["service_max"]) + epsilon
        and float(candidates[index]["service_sum"])
        <= float(random["service_sum"]) + epsilon
        and float(candidates[index]["paper_welfare"])
        > float(random["paper_welfare"]) + epsilon
    ]
    if not admissible:
        return 0, "random_default_no_strict_welfare_pareto_replacement"
    selected = min(
        admissible,
        key=lambda index: (
            _metric_key(candidates[index]["paper_welfare"], descending=True),
            _metric_key(candidates[index]["service_sum"]),
            index,
        ),
    )
    return selected, "strict_welfare_pareto_replacement_maximum_paper_welfare"


def _validate_native_diagnostics(
    run: dict[str, Any], canonical: Path, selection_rule: str
) -> dict[str, Any]:
    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V142 Nash diagnostics: {run['run_id']}")
    counts = Counter()
    reasons = Counter()
    portfolio_enabled = selection_rule != "exact_random_prefix"
    expected_kinds = native_members(selection_rule)
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            counts["windows"] += 1
            decision = event.get("decision")
            _require(isinstance(decision, dict), "missing V142 decision diagnostics")
            native = decision.get("native_shadow_anchor")
            _require(isinstance(native, dict), "missing V142 native shadow diagnostics")
            portfolio = decision.get("native_portfolio")
            _require(isinstance(portfolio, dict), "missing V142 portfolio diagnostics")
            prefix = decision.get("random_prefix_cohort")
            _require(isinstance(prefix, dict), "missing V142 Random-prefix diagnostics")
            players = decision.get("request_function_players")
            _require(
                type(players) is int and players >= 0,
                f"invalid V142 player count: {run['run_id']}:{line_number}",
            )
            feasible_players = prefix.get("feasible_player_count")
            prefix_players = prefix.get("player_count")
            missing_players = prefix.get("missing_feasible_player_count")
            _require(
                prefix.get("enabled") is True
                and type(feasible_players) is int
                and feasible_players >= 0
                and type(prefix_players) is int
                and prefix_players == players
                and type(missing_players) is int
                and missing_players == feasible_players - players
                and feasible_players >= players
                and prefix.get("early_stop_observed") is (missing_players > 0)
                and type(prefix.get("ordered_command_hash")) is int
                and prefix.get("dispatch_player_count") == players
                and prefix.get("commands_prepared") == players
                and prefix.get("cohort_equals_dispatch") is True
                and prefix.get("tail_players_dispatched") == 0
                and prefix.get("cohort_source") == RANDOM_PREFIX_COHORT_SOURCE
                and prefix.get("uses_completion_outcomes") is False,
                f"V142 Random-prefix cohort changed: {run['run_id']}:{line_number}",
            )
            if missing_players > 0:
                counts["early_stop_windows"] += 1
            counts["missing_feasible_players"] += missing_players
            _require(
                portfolio.get("certificate_uses_completion_outcomes") is False,
                f"V142 portfolio boundary changed: {run['run_id']}:{line_number}",
            )
            _require(
                portfolio.get("all_player_service_definition")
                == "current_admitted_immutable_CPU_plus_prior_same_window_projected_immutable_CPU_plus_current_player_immutable_CPU_divided_by_current_node_capacity_plus_cold_start_plus_current_or_complete_assignment_parent_transfer"
                and portfolio.get("service_certificate_state_domain")
                == SERVICE_CERTIFICATE_STATE_DOMAIN
                and portfolio.get("paper_welfare_price_basis")
                == "immutable_pre_feedback_baseline_prices"
                and portfolio.get("paper_welfare_state_domain")
                == PAPER_WELFARE_STATE_DOMAIN,
                f"V142 portfolio certificate definition changed: {run['run_id']}:{line_number}",
            )
            _require(
                portfolio.get("configured_bandwidth_snapshot_complete") is True
                and portfolio.get("configured_bandwidth_snapshot_source")
                == "current_SimEnvObserve_configured_directed_bandwidth",
                f"V142 configured bandwidth snapshot changed: {run['run_id']}:{line_number}",
            )
            _require(
                portfolio.get("random_shadow_seeded") is True
                and portfolio.get("random_shadow_seed_source") == "algorithm_seed"
                and portfolio.get("random_shadow_algorithm_seed")
                == run["simulator_experiment"]["algorithm_seed"]
                and portfolio.get("random_shadow_lifecycle") == RANDOM_SHADOW_LIFECYCLE,
                f"V142 Random shadow lifecycle changed: {run['run_id']}:{line_number}",
            )
            _require(
                portfolio.get("random_shadow_initialization_count") == 1
                and portfolio.get("random_shadow_invocation_count") == counts["windows"]
                and portfolio.get("random_shadow_invocations_this_window") == 1
                and portfolio.get("early_stop_command_position")
                == (players if missing_players > 0 else None),
                f"V142 Random shadow invocation trace changed: {run['run_id']}:{line_number}",
            )
            selected_candidate: dict[str, Any] | None = None
            if players > 0:
                counts["player_windows"] += 1
                if portfolio_enabled:
                    _require(
                        portfolio.get("enabled") is True
                        and portfolio.get("rule") == selection_rule
                        and portfolio.get("random_default_index") == 0,
                        f"V142 active portfolio boundary changed: {run['run_id']}:{line_number}",
                    )
                    candidates = portfolio.get("candidates")
                    _require(
                        portfolio.get("candidate_count") == 6
                        and isinstance(candidates, list)
                        and len(candidates) == 6
                        and [item.get("kind") for item in candidates] == expected_kinds,
                        f"V142 portfolio members changed: {run['run_id']}:{line_number}",
                    )
                    for index, candidate in enumerate(candidates):
                        _require(
                            candidate.get("valid") is True
                            and candidate.get("commands") == players
                            and candidate.get("duplicate_commands") == 0
                            and candidate.get("unexpected_messages") == 0
                            and candidate.get("missing_players") == 0
                            and candidate.get("extra_players") == 0
                            and candidate.get("infeasible_commands") == 0
                            and type(candidate.get("ordered_command_hash")) is int
                            and type(candidate.get("assignment_hash")) is int
                            and candidate.get("service_complete") is True
                            and candidate.get("service_players") == players
                            and all(
                                _finite(candidate.get(field))
                                for field in (
                                    "service_sum",
                                    "service_max",
                                    "paper_welfare",
                                )
                            ),
                            f"V142 portfolio candidate invalid: {run['run_id']}:{line_number}",
                        )
                        random = candidates[0]
                        expected_predicates = {
                            "random_service_max_nonworse": float(
                                candidate["service_max"]
                            )
                            <= float(random["service_max"]) + 1.0e-6,
                            "random_service_sum_nonworse": float(
                                candidate["service_sum"]
                            )
                            <= float(random["service_sum"]) + 1.0e-6,
                            "random_service_sum_strictly_lower": float(
                                candidate["service_sum"]
                            )
                            < float(random["service_sum"]) - 1.0e-6,
                            "random_welfare_nonworse": float(candidate["paper_welfare"])
                            + 1.0e-6
                            >= float(random["paper_welfare"]),
                            "random_welfare_strictly_higher": float(
                                candidate["paper_welfare"]
                            )
                            > float(random["paper_welfare"]) + 1.0e-6,
                        }
                        expected_predicates["random_service_pareto_admissible"] = (
                            expected_predicates["random_service_max_nonworse"]
                            and expected_predicates["random_service_sum_strictly_lower"]
                            and expected_predicates["random_welfare_nonworse"]
                        )
                        expected_predicates["random_welfare_pareto_admissible"] = (
                            expected_predicates["random_service_max_nonworse"]
                            and expected_predicates["random_service_sum_nonworse"]
                            and expected_predicates["random_welfare_strictly_higher"]
                        )
                        _require(
                            all(
                                candidate.get(field) is value
                                for field, value in expected_predicates.items()
                            ),
                            f"V142 Random-relative predicates changed: {run['run_id']}:{line_number}:{index}",
                        )
                    ranks = _rank_portfolio_candidates(candidates)
                    for candidate, expected_ranks in zip(candidates, ranks):
                        _require(
                            all(
                                candidate.get(field) == value
                                for field, value in expected_ranks.items()
                            ),
                            f"V142 portfolio ranks changed: {run['run_id']}:{line_number}",
                        )
                    selected, reason = _expected_portfolio_selection(
                        selection_rule, candidates, ranks
                    )
                    _require(
                        [item.get("selected") for item in candidates]
                        == [index == selected for index in range(6)]
                        and portfolio.get("selected_kind")
                        == candidates[selected]["kind"]
                        and portfolio.get("deterministic_selection_reason") == reason,
                        f"V142 portfolio selection changed: {run['run_id']}:{line_number}",
                    )
                    selected_candidate = candidates[selected]
                    counts[f"selected_{selected_candidate['kind']}"] += 1
                    counts[f"selection_reason_{reason}"] += 1
                else:
                    _require(
                        portfolio.get("enabled") is False
                        and portfolio.get("rule") is None
                        and portfolio.get("selected_kind") is None
                        and portfolio.get("deterministic_selection_reason") is None
                        and portfolio.get("candidate_count") == 0
                        and portfolio.get("random_default_index") is None
                        and portfolio.get("candidates") == [],
                        f"V142 exact Random anchor unexpectedly used a portfolio: {run['run_id']}:{line_number}",
                    )
                    counts["selected_random"] += 1
                _require(
                    native.get("kind")
                    == (selected_candidate["kind"] if selected_candidate else "random")
                    and native.get("valid") is True
                    and native.get("commands") == players
                    and native.get("duplicate_commands") == 0
                    and native.get("unexpected_messages") == 0
                    and native.get("missing_players") == 0
                    and native.get("extra_players") == 0
                    and native.get("infeasible_commands") == 0
                    and type(native.get("anchor_assignment_hash")) is int
                    and type(native.get("ordered_command_hash")) is int
                    and (
                        selected_candidate is None
                        or native.get("anchor_assignment_hash")
                        == selected_candidate["assignment_hash"]
                    )
                    and (
                        selected_candidate is None
                        or native.get("ordered_command_hash")
                        == selected_candidate["ordered_command_hash"]
                    )
                    and native.get("service_certificate_scope")
                    == SERVICE_CERTIFICATE_SCOPE
                    and native.get("initializer_readiness_service_complete") is True
                    and native.get("initializer_readiness_service_players") == players
                    and (
                        selected_candidate is None
                        or native.get("initializer_readiness_service_sum")
                        == selected_candidate["service_sum"]
                    )
                    and (
                        selected_candidate is None
                        or native.get("initializer_readiness_service_max")
                        == selected_candidate["service_max"]
                    ),
                    f"V142 selected native mismatch: {run['run_id']}:{line_number}",
                )
                _require(
                    prefix.get("ordered_command_hash")
                    == (
                        candidates[0]["ordered_command_hash"]
                        if portfolio_enabled
                        else native.get("ordered_command_hash")
                    ),
                    f"V142 Random-prefix hash changed: {run['run_id']}:{line_number}",
                )
            _require(
                native.get("certificate_uses_completion_outcomes") is False,
                f"V142 native certificate consulted outcomes: {run['run_id']}",
            )
            initializer_players = native.get("initializer_readiness_service_players")
            proposal_players = native.get("proposal_readiness_service_players")
            _require(
                type(initializer_players) is int
                and initializer_players >= 0
                and type(proposal_players) is int
                and proposal_players >= 0,
                f"V142 native service cohort count invalid: {run['run_id']}:{line_number}",
            )
            guard = decision.get("window_safe_guard")
            _require(isinstance(guard, dict), "missing V142 native guard diagnostics")
            reason = guard.get("reason")
            _require(isinstance(reason, str), "invalid V142 native guard reason")
            if players == 0:
                _require(
                    portfolio.get("enabled") is False
                    and portfolio.get("rule") is None
                    and portfolio.get("candidate_count") == 0
                    and portfolio.get("candidates") == []
                    and portfolio.get("selected_kind") is None
                    and portfolio.get("deterministic_selection_reason") is None
                    and native.get("initializer_readiness_service_complete") is False
                    and native.get("proposal_readiness_service_complete") is False
                    and initializer_players == 0
                    and proposal_players == 0
                    and guard.get("accepted") is False
                    and guard.get("evaluated") is False
                    and guard.get("fallback_applied") is False
                    and reason == "not_applicable",
                    f"V142 empty-window diagnostics mismatch: {run['run_id']}:{line_number}",
                )
                reasons[reason] += 1
                continue
            initializer_complete = (
                native.get("initializer_readiness_service_complete") is True
            )
            proposal_complete = (
                native.get("proposal_readiness_service_complete") is True
            )
            if initializer_complete and proposal_complete:
                _require(
                    initializer_players == players
                    and initializer_players == proposal_players,
                    f"V142 native service cohort mismatch: {run['run_id']}:{line_number}",
                )
                counts["service_windows"] += 1
                _require(
                    all(
                        _finite(native.get(field))
                        for field in (
                            "initializer_readiness_service_sum",
                            "proposal_readiness_service_sum",
                            "initializer_readiness_service_max",
                            "proposal_readiness_service_max",
                            "readiness_service_sum_delta",
                            "readiness_service_max_delta",
                        )
                    ),
                    f"V142 native service certificate incomplete: {run['run_id']}:{line_number}",
                )
                initializer_sum = float(native["initializer_readiness_service_sum"])
                proposal_sum = float(native["proposal_readiness_service_sum"])
                initializer_max = float(native["initializer_readiness_service_max"])
                proposal_max = float(native["proposal_readiness_service_max"])
                _require(
                    native.get("readiness_service_sum_delta")
                    == proposal_sum - initializer_sum
                    and native.get("readiness_service_max_delta")
                    == proposal_max - initializer_max,
                    f"V142 native service deltas changed: {run['run_id']}:{line_number}",
                )
            else:
                _require(
                    guard.get("accepted") is False,
                    f"V142 unavailable native service certificate was accepted: {run['run_id']}:{line_number}",
                )
                if not initializer_complete:
                    _require(
                        initializer_players == 0
                        and reason == "initializer_readiness_service_unavailable",
                        f"V142 initializer service fallback mismatch: {run['run_id']}:{line_number}",
                    )
                else:
                    _require(
                        not proposal_complete
                        and proposal_players == 0
                        and reason == "proposal_readiness_service_unavailable",
                        f"V142 proposal service fallback mismatch: {run['run_id']}:{line_number}",
                    )
                counts["unavailable_service_windows"] += 1
            initializer_welfare = guard.get("initializer_baseline_welfare")
            proposal_welfare = guard.get("proposal_baseline_welfare")
            welfare_delta = guard.get("baseline_welfare_delta")
            _require(
                guard.get("evaluated") is True
                and _finite(initializer_welfare)
                and _finite(proposal_welfare)
                and _finite(welfare_delta)
                and (
                    selected_candidate is None
                    or float(initializer_welfare)
                    == float(selected_candidate["paper_welfare"])
                )
                and _f32(float(proposal_welfare) - float(initializer_welfare))
                == float(welfare_delta),
                f"V142 native welfare certificate changed: {run['run_id']}:{line_number}",
            )
            if not proposal_complete:
                expected_reason = "proposal_readiness_service_unavailable"
            elif _f32(float(proposal_welfare) + _f32(1.0e-6)) < float(
                initializer_welfare
            ):
                expected_reason = "paper_welfare_worse"
            elif proposal_max > initializer_max + 1.0e-6:
                expected_reason = "readiness_service_max_worse"
            elif proposal_sum + 1.0e-6 >= initializer_sum:
                expected_reason = "readiness_service_sum_not_strictly_improved"
            else:
                expected_reason = "accepted"
            expected_accepted = expected_reason == "accepted"
            _require(
                reason == expected_reason
                and guard.get("accepted") is expected_accepted
                and guard.get("fallback_applied") is (not expected_accepted),
                f"V142 native guard decision changed: {run['run_id']}:{line_number}",
            )
            reasons[reason] += 1
            if guard.get("accepted") is True:
                counts["accepted_windows"] += 1
                _require(
                    initializer_players > 0
                    and float(native["readiness_service_sum_delta"]) < -1.0e-6
                    and float(native["readiness_service_max_delta"]) <= 1.000001e-6
                    and _finite(guard.get("baseline_welfare_delta"))
                    and float(guard["baseline_welfare_delta"]) >= -1.000001e-6,
                    f"V142 native accepted window violated certificate: {run['run_id']}:{line_number}",
                )
    _require(counts["windows"] == 4000, f"V142 window count changed: {run['run_id']}")
    _require(
        counts["player_windows"] > 0,
        f"V142 has no native player windows: {run['run_id']}",
    )
    return {
        "window_count": counts["windows"],
        "native_player_window_count": counts["player_windows"],
        "service_certificate_window_count": counts["service_windows"],
        "accepted_proposal_window_count": counts["accepted_windows"],
        "random_early_stop_window_count": counts["early_stop_windows"],
        "random_missing_feasible_player_count": counts["missing_feasible_players"],
        "guard_reasons": dict(sorted(reasons.items())),
        "native_selection_rule": selection_rule,
        "selected_native_counts": {
            kind: counts[f"selected_{kind}"] for kind in NATIVE_KINDS
        },
        "selection_reason_counts": {
            key.removeprefix("selection_reason_"): value
            for key, value in sorted(counts.items())
            if key.startswith("selection_reason_")
        },
        "performance_fields_consulted": False,
    }


def _runtime_evidence(audit: Mapping[str, Any]) -> dict[str, str]:
    return {
        "binary_sha256": str(audit["adapter_binary"]["verified_sha256"]),
        "git_commit": str(audit["software_environment"]["git"]["commit"]),
        "python_executable_sha256": str(
            audit["software_environment"]["python"]["executable_sha256"]
        ),
        "cargo_lock_sha256": str(audit["software_environment"]["cargo_lock"]["sha256"]),
    }


def _validate_execution_receipt() -> dict[str, Any]:
    ready_schedule_path = ROOT / READY_SCHEDULE.name
    execution_path = ROOT / EXECUTION_RECEIPT.name
    _require(ready_schedule_path.is_file(), "missing V142 ready schedule")
    _require(execution_path.is_file(), "missing V142 execution receipt")
    schedule = read_json(ready_schedule_path)
    schedule_hash = _assert_hashed_object(
        schedule, "schedule_hash", "V142 ready schedule"
    )
    receipt = read_json(execution_path)
    receipt_hash = _assert_hashed_object(
        receipt, "receipt_hash", "V142 execution receipt"
    )
    _require(
        receipt.get("performance_results_consulted") is False
        and receipt.get("plan_sha256") == PLAN_SHA256
        and receipt.get("ready_schedule_hash") == schedule_hash
        and receipt.get("dispatch_count") == 108
        and receipt.get("all_exit_codes_zero") is True
        and len(receipt.get("dispatches", [])) == 108,
        "V142 execution receipt boundary changed",
    )
    for scheduled, dispatched in zip(schedule["schedule"], receipt["dispatches"]):
        common_valid = (
            all(
                scheduled[field] == dispatched[field]
                for field in (
                    "ordinal",
                    "block_id",
                    "within_block_index",
                    "method_label",
                    "manifest_id",
                    "run_id",
                )
            )
            and dispatched["exit_code"] == 0
        )
        if dispatched.get("action") == "executed_frozen_dispatch":
            evidence_valid = (
                file_hash(Path(dispatched["stdout_path"]))
                == dispatched["stdout_sha256"]
                and file_hash(Path(dispatched["stderr_path"]))
                == dispatched["stderr_sha256"]
            )
        elif dispatched.get("action") == "validated_preexisting_attempt1_canonical":
            evidence_valid = all(
                isinstance(dispatched.get(field), str) and len(dispatched[field]) == 64
                for field in (
                    "attempt_file_sha256",
                    "qc_report_sha256",
                    "audit_manifest_sha256",
                )
            )
        else:
            evidence_valid = False
        _require(
            common_valid and evidence_valid,
            f"V142 frozen dispatch changed: {scheduled['ordinal']}",
        )
    return {
        "ready_schedule_path": str(ready_schedule_path),
        "ready_schedule_file_sha256": file_hash(ready_schedule_path),
        "ready_schedule_hash": schedule_hash,
        "execution_receipt_path": str(execution_path),
        "execution_receipt_file_sha256": file_hash(execution_path),
        "execution_receipt_hash": receipt_hash,
    }


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V142 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V142 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V142 plan changed")
    _require(PREPARED.is_file(), "missing V142 prepared receipt")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V142 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("plan_sha256") == PLAN_SHA256
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("training_seeds") == TRAINING_SEED_LIST
        and prepared.get("retired_unmaterialized_v137_confirmation_seeds")
        == RETIRED_V137_CONFIRMATION_SEEDS
        and prepared.get("retired_opened_v138_training_seeds")
        == RETIRED_OPENED_V138_TRAINING_SEEDS
        and prepared.get("retired_opened_v139_training_seeds")
        == RETIRED_OPENED_V139_TRAINING_SEEDS
        and prepared.get("retired_opened_v140_training_seeds")
        == RETIRED_OPENED_V140_TRAINING_SEEDS
        and prepared.get("retired_opened_v141_training_seeds")
        == RETIRED_OPENED_V141_TRAINING_SEEDS
        and prepared.get("sealed_new_confirmation_seeds") == NEW_CONFIRMATION_SEEDS
        and prepared.get("v141_disposition")
        == "technical_reference_build_failure_before_online_execution_no_reveal"
        and prepared.get("v141_performance_summaries_parsed") == 0
        and prepared.get("v141_performance_results_consulted") is False
        and prepared.get("v141_online_runs_started") == 0
        and prepared.get("v141_online_runs_canonicalized") == 0
        and prepared.get("total_online_runs") == 108
        and prepared.get("candidate_reference_builds") == 27,
        "V142 prepared scientific boundary changed",
    )
    _require(
        prepared.get("binary_sha256") == BINARY_SHA256
        and prepared.get("binary_source_commit") == BINARY_SOURCE_COMMIT
        and prepared.get("arms")
        == [
            {
                "arm_id": arm_id,
                "profile": profile,
                "native_selection_rule": rule,
                "native_portfolio_enabled": rule != "exact_random_prefix",
                "native_portfolio_members": native_members(rule),
                "run_count": 9,
                "reference_build_count": 9,
            }
            for arm_id, profile, rule in PREPARED_ARMS
        ],
        "V142 prepared treatment boundary changed",
    )
    execution = _validate_execution_receipt()
    tapes, tape_catalog = _verify_tapes()
    references, reference_ledger_hashes = _verify_references()

    run_evidence = []
    pairing_evidence = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    paired_inputs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    ready_manifests = {}
    products = [
        ("v142-baselines", 81, None),
        *[(arm_id, 9, ARMS[arm_id]) for arm_id in ARM_IDS],
    ]
    for manifest_id, expected_count, arm in products:
        manifest_path = ready_manifest_path(ROOT, manifest_id)
        manifest = load_and_validate_manifest(manifest_path)
        candidate = arm is not None
        _require(
            len(manifest["runs"]) == expected_count
            and manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_references_bound") is True
            and manifest.get("all_faasrank_models_bound") is (not candidate),
            f"V142 ready boundary changed: {manifest_id}",
        )
        ready_manifests[manifest_id] = {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "run_count": expected_count,
        }
        pairing_file = pairing_path(ROOT, manifest_id)
        pairing = read_json(pairing_file)
        _require(
            pairing.get("passed") is True
            and pairing.get("failed_group_count") == 0
            and pairing.get("run_count") == expected_count,
            f"V142 pairing changed: {manifest_id}",
        )
        pairing_evidence.append(
            {
                "manifest_id": manifest_id,
                "path": str(pairing_file),
                "file_sha256": file_hash(pairing_file),
                "run_count": pairing["run_count"],
                "group_count": pairing["group_count"],
            }
        )
        workspace = workspace_path(ROOT, manifest_id)
        expected_ids = {run["run_id"] for run in manifest["runs"]}
        actual_ids = {
            path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
        }
        _require(
            actual_ids == expected_ids, f"V142 canonical set changed: {manifest_id}"
        )
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V142 online quarantine is nonempty: {manifest_id}",
        )
        ledger_rows, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
        counts = Counter(row["event_type"] for row in ledger_rows)
        _require(
            counts["attempt_started"] == expected_count
            and counts["attempt_canonicalized"] == expected_count
            and not any(
                counts[event]
                for event in (
                    "attempt_failed",
                    "attempt_quarantined",
                    "run_blocked",
                    "partial_abandoned",
                )
            ),
            f"V142 online ledger changed: {manifest_id}/{counts}",
        )
        for run in manifest["runs"]:
            if candidate:
                _require(
                    run.get("method") == "sche_nash"
                    and run.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
                    == arm["profile"]
                    and run.get("metadata", {}).get("v142_native_selection_rule")
                    == arm["selection_rule"]
                    and run.get("metadata", {}).get("v142_native_portfolio_enabled")
                    is (arm["selection_rule"] != "exact_random_prefix")
                    and run.get("metadata", {}).get("v142_native_portfolio_members")
                    == native_members(arm["selection_rule"])
                    and run.get("metadata", {}).get("v142_random_default_required")
                    is True
                    and run.get("metadata", {}).get(
                        "v142_nonrandom_native_sources_complete_all_frontier"
                    )
                    is True
                    and run.get("metadata", {}).get(
                        "v142_native_candidates_projected_to_random_prefix"
                    )
                    is True
                    and run.get("metadata", {}).get(
                        "v142_random_prefix_cohort_required"
                    )
                    is True
                    and run.get("metadata", {}).get("v142_random_shadow_lifecycle")
                    == RANDOM_SHADOW_LIFECYCLE
                    and run.get("metadata", {}).get(
                        "v142_exact_random_command_count_required"
                    )
                    is True
                    and run.get("metadata", {}).get("v142_tail_dispatch_forbidden")
                    is True
                    and run.get("metadata", {}).get("v142_service_certificate_scope")
                    == SERVICE_CERTIFICATE_SCOPE
                    and run.get("metadata", {}).get(
                        "v142_service_certificate_state_domain"
                    )
                    == SERVICE_CERTIFICATE_STATE_DOMAIN
                    and run.get("metadata", {}).get("v142_paper_welfare_state_domain")
                    == PAPER_WELFARE_STATE_DOMAIN
                    and run.get("metadata", {}).get(
                        "v142_selected_welfare_equals_guard_initializer_required"
                    )
                    is True
                    and run.get("metadata", {}).get("v142_outcome_fields_drive_policy")
                    is False
                    and isinstance(run.get("reference_dependency"), dict),
                    f"V142 candidate manifest boundary changed: {run['run_id']}",
                )
            else:
                _require(
                    run.get("method") in BASELINE_METHODS
                    and run.get("reference_dependency") is None,
                    f"V142 baseline manifest boundary changed: {run['run_id']}",
                )
            canonical = workspace / "canonical" / run["run_id"]
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            attempt = read_json(canonical / "attempt.json")
            qc = read_json(canonical / "qc_report.json")
            audit = read_json(canonical / "manifest.json")
            _require(
                attempt.get("attempt") == 1
                and attempt.get("status") == "qc_pass"
                and attempt.get("classification") == "qc_pass"
                and attempt.get("timed_out") is False
                and attempt.get("exit_code") == 0
                and qc.get("passed") is True
                and qc.get("classification") == "qc_pass",
                f"V142 canonical status changed: {run['run_id']}",
            )
            runtime = _runtime_evidence(audit)
            for field, value in runtime.items():
                runtime_values[field].add(value)
            scenario = scenario_id(run)
            label = manifest_id if candidate else run["method"]
            diagnostics = (
                _validate_native_diagnostics(run, canonical, str(arm["selection_rule"]))
                if candidate
                else None
            )
            paired_inputs[(scenario, run["seed"])].append(
                {
                    "method_label": label,
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "workload_tape_key": run["workload_tape"]["key"],
                    "workload_spec_hash": run["workload_spec_hash"],
                    "capture_environment_sha256": run["workload_tape"][
                        "capture_environment"
                    ]["capture_environment_sha256"],
                    "common_hpa_hash": run["common_hpa_hash"],
                    "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
                    "simulation": run["simulation"],
                }
            )
            run_evidence.append(
                {
                    "manifest_id": manifest_id,
                    "method_label": label,
                    "run_id": run["run_id"],
                    "scenario": scenario,
                    "seed": run["seed"],
                    "run_spec_hash": run["run_spec_hash"],
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "reference_key": (
                        run["reference_dependency"]["key"] if candidate else None
                    ),
                    "result_sha256": attempt["result_sha256"],
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "attempt": 1,
                    "classification": "qc_pass",
                    "native_diagnostics": diagnostics,
                    "ledger_last_hash": ledger_last_hash,
                    "reference_ledger_last_hash": (
                        reference_ledger_hashes[manifest_id] if candidate else None
                    ),
                }
            )

    _require(len(run_evidence) == 108, "V142 run evidence count changed")
    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V142 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(c in "0123456789abcdef" for c in next(iter(git_commits))),
        f"V142 runtime git identity changed: {git_commits}",
    )
    _require(len(paired_inputs) == 9, "V142 paired block count changed")
    for (scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 12
            and {row["method_label"] for row in rows} == set(METHOD_LABELS),
            f"V142 block product changed: {scenario}/{seed}",
        )
        for field in (
            "workload_tape_sha256",
            "workload_tape_key",
            "workload_spec_hash",
            "capture_environment_sha256",
            "common_hpa_hash",
            "sla_artifact_sha256",
            "simulation",
        ):
            _require(
                len({object_hash(row[field]) for row in rows}) == 1,
                f"V142 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V142 common HPA changed: {scenario}/{seed}",
        )

    payload = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_BLIND_AUDIT_V142_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": file_hash(PREPARED),
        "prepared_receipt_hash": prepared_hash,
        "runtime_identity": {**EXPECTED_RUNTIME, "git_commit": next(iter(git_commits))},
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": TRAINING_SEED_LIST,
        "retired_unmaterialized_v137_confirmation_seeds": RETIRED_V137_CONFIRMATION_SEEDS,
        "retired_opened_v138_training_seeds": RETIRED_OPENED_V138_TRAINING_SEEDS,
        "retired_opened_v139_training_seeds": RETIRED_OPENED_V139_TRAINING_SEEDS,
        "retired_opened_v140_training_seeds": RETIRED_OPENED_V140_TRAINING_SEEDS,
        "retired_opened_v141_training_seeds": RETIRED_OPENED_V141_TRAINING_SEEDS,
        "sealed_new_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        "manifest_count": 4,
        "baseline_run_count": 81,
        "candidate_run_count": 27,
        "run_count": 108,
        "reference_count": 27,
        "tape_count": 12,
        "block_count": 9,
        "execution": execution,
        "tape_catalog": tape_catalog,
        "ready_manifests": ready_manifests,
        "pairing": pairing_evidence,
        "tapes": tapes,
        "references": references,
        "runs": run_evidence,
    }
    payload["audit_hash"] = object_hash(payload)
    write_json_atomic(output, payload)
    return payload


def main() -> None:
    audit = run_blind_audit()
    print(json.dumps({"status": audit["status"], "audit_hash": audit["audit_hash"]}))


if __name__ == "__main__":
    main()
