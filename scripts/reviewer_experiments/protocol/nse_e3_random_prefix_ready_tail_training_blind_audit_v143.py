from __future__ import annotations

import gzip
import json
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
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_execute_v143 import (
    EXECUTION_RECEIPT,
    READY_SCHEDULE,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_ready_tail_training_prepare_v143 import (
    ARM_ID,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    COHORT_SOURCE,
    NEW_CONFIRMATION_SEEDS,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    PYTHON_SHA256,
    RANDOM_SHADOW_LIFECYCLE,
    READY_TAIL_PREDICATE,
    ROOT,
    RUNTIME_NATIVE_KINDS,
    SELECTION_RULE,
    SERVICE_CERTIFICATE_SCOPE,
    TRAINING_SEED_LIST,
    V142_BASELINE_PAIRING,
    V142_BASELINE_READY,
    V142_BASELINE_WORKSPACE,
    V142_BLIND,
    V142_BLIND_HASH,
    V142_BLIND_SHA256,
    V142_RESULT,
    V142_RESULT_HASH,
    V142_RESULT_SHA256,
    V142_TAPE_CATALOG,
    V142_TAPE_CATALOG_SHA256,
    V143_SERVICE_STATE_DOMAIN,
    V143_WELFARE_STATE_DOMAIN,
    _assert_frozen_inputs,
    pairing_path,
    paths,
    ready_manifest_path,
    reference_catalog_path,
    scenario_id,
    workspace_path,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_blind_audit_v142 import (
    _f32,
    _finite,
    _rank_portfolio_candidates,
    _runtime_evidence,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
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


PREPARED = ROOT / "prepared-manifest-v143.json"
OUTPUT = ROOT / "joint-blind-audit-v143-training.json"
RESULT = ROOT / "training-result-v143.json"
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
EXPECTED_RUNTIME = {
    "binary_sha256": BINARY_SHA256,
    "python_executable_sha256": PYTHON_SHA256,
    "cargo_lock_sha256": CARGO_LOCK_SHA256,
}
EXPECTED_RUN_CONFIG_CONTRACT = {
    "version": "V143",
    "prefix_source": "persistent_same_seed_unchanged_Random_Scheduler",
    "prefix_preserved_fields": ["ordered_players", "assigned_node_ids"],
    "tail_predicate": "all_parents_complete_at_window_start_and_common_placement_feasible",
    "cohort_order": "exact_Random_prefix_then_stable_All-frontier_ready-feasible_tail_without_overlap",
    "tail_experts": RUNTIME_NATIVE_KINDS,
    "default_expert": "faasrank",
    "replacement_guard": "service_max_nonworse_and_service_sum_strictly_lower_and_immutable-baseline_paper_welfare_nonworse",
    "selection_tie_break": "minimum_service_sum_then_maximum_paper_welfare_then_stable_expert_order",
    "uses_completed_request_outcomes": False,
    "reference_policy_independent": True,
}
RANDOM_RELATIVE_FIELDS = (
    "random_service_max_nonworse",
    "random_service_sum_nonworse",
    "random_service_sum_strictly_lower",
    "random_welfare_nonworse",
    "random_welfare_strictly_higher",
    "random_service_pareto_admissible",
    "random_welfare_pareto_admissible",
)


def _expected_v143_selection(candidates: list[dict[str, Any]]) -> tuple[int, str]:
    _require(
        len(candidates) == 7 and candidates[0].get("kind") == "faasrank",
        "V143 FaaSRank-default portfolio order changed",
    )
    default = candidates[0]
    epsilon = 1.0e-6
    admissible = [
        index
        for index in range(1, len(candidates))
        if float(candidates[index]["service_max"])
        <= float(default["service_max"]) + epsilon
        and float(candidates[index]["service_sum"])
        < float(default["service_sum"]) - epsilon
        and float(candidates[index]["paper_welfare"]) + epsilon
        >= float(default["paper_welfare"])
    ]
    if not admissible:
        return 0, "faasrank_default_no_strict_service_pareto_replacement"
    selected = min(
        admissible,
        key=lambda index: (
            float(candidates[index]["service_sum"]),
            -float(candidates[index]["paper_welfare"]),
            index,
        ),
    )
    return selected, "strict_service_pareto_replacement_minimum_service_sum"


def _validate_v143_native_diagnostics(
    run: dict[str, Any], canonical: Path
) -> dict[str, Any]:
    path = canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"
    _require(path.is_file(), f"missing V143 Nash diagnostics: {run['run_id']}")
    counts = Counter()
    reasons = Counter()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            event = json.loads(line)
            if event.get("kind") == "run_config":
                counts["run_config"] += 1
                _require(
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy_contract")
                    == EXPECTED_RUN_CONFIG_CONTRACT,
                    f"V143 run-config contract changed: {run['run_id']}:{line_number}",
                )
                continue
            if event.get("kind") != "window":
                continue
            counts["windows"] += 1
            decision = event.get("decision")
            _require(isinstance(decision, dict), "missing V143 decision diagnostics")
            native = decision.get("native_shadow_anchor")
            portfolio = decision.get("native_portfolio")
            prefix = decision.get("random_prefix_cohort")
            guard = decision.get("window_safe_guard")
            _require(
                all(
                    isinstance(item, dict)
                    for item in (native, portfolio, prefix, guard)
                ),
                f"missing V143 native diagnostics: {run['run_id']}:{line_number}",
            )
            players = decision.get("request_function_players")
            feasible = prefix.get("feasible_player_count")
            prefix_players = prefix.get("player_count")
            missing = prefix.get("missing_feasible_player_count")
            ready = prefix.get("ready_feasible_player_count")
            overlap = prefix.get("prefix_ready_overlap_count")
            tail = prefix.get("ready_tail_player_count")
            combined = prefix.get("combined_cohort_player_count")
            combined_hash = prefix.get("combined_cohort_ordered_hash")
            _require(
                type(players) is int
                and players >= 0
                and type(feasible) is int
                and feasible >= 0
                and type(prefix_players) is int
                and 0 <= prefix_players <= feasible
                and type(missing) is int
                and missing == feasible - prefix_players
                and type(ready) is int
                and ready >= 0
                and type(overlap) is int
                and 0 <= overlap <= min(prefix_players, ready)
                and type(tail) is int
                and tail == ready - overlap
                and type(combined) is int
                and combined == prefix_players + tail
                and players == combined
                and type(combined_hash) is int
                and prefix.get("enabled") is True
                and prefix.get("early_stop_observed") is (missing > 0)
                and type(prefix.get("ordered_command_hash")) is int
                and prefix.get("dispatch_player_count") == combined
                and prefix.get("commands_prepared") == combined
                and prefix.get("cohort_equals_dispatch") is True
                and prefix.get("tail_players_dispatched") == tail
                and prefix.get("cohort_source") == COHORT_SOURCE
                and prefix.get("ready_tail_predicate") == READY_TAIL_PREDICATE
                and prefix.get("uses_completion_outcomes") is False,
                f"V143 cohort changed: {run['run_id']}:{line_number}",
            )
            counts["random_missing_feasible_players"] += missing
            counts["ready_tail_players"] += tail
            if missing > 0:
                counts["random_early_stop_windows"] += 1
            if tail > 0:
                counts["ready_tail_windows"] += 1

            _require(
                portfolio.get("certificate_uses_completion_outcomes") is False
                and portfolio.get("configured_bandwidth_snapshot_complete") is True
                and portfolio.get("configured_bandwidth_snapshot_source")
                == "current_SimEnvObserve_configured_directed_bandwidth"
                and portfolio.get("all_player_service_definition")
                == "current_admitted_immutable_CPU_plus_prior_same_window_projected_immutable_CPU_plus_current_player_immutable_CPU_divided_by_current_node_capacity_plus_cold_start_plus_current_or_complete_assignment_parent_transfer"
                and portfolio.get("service_certificate_state_domain")
                == V143_SERVICE_STATE_DOMAIN
                and portfolio.get("paper_welfare_price_basis")
                == "immutable_pre_feedback_baseline_prices"
                and portfolio.get("paper_welfare_state_domain")
                == V143_WELFARE_STATE_DOMAIN
                and portfolio.get("random_shadow_seeded") is True
                and portfolio.get("random_shadow_seed_source") == "algorithm_seed"
                and portfolio.get("random_shadow_algorithm_seed")
                == run["simulator_experiment"]["algorithm_seed"]
                and portfolio.get("random_shadow_lifecycle") == RANDOM_SHADOW_LIFECYCLE
                and portfolio.get("random_shadow_initialization_count") == 1
                and portfolio.get("random_shadow_invocation_count") == counts["windows"]
                and portfolio.get("random_shadow_invocations_this_window") == 1
                and portfolio.get("early_stop_command_position")
                == (prefix_players if missing > 0 else None),
                f"V143 portfolio boundary changed: {run['run_id']}:{line_number}",
            )

            partitions = portfolio.get("v143_candidate_partitions")
            _require(
                isinstance(partitions, list)
                and len(partitions) == 7
                and [item.get("kind") for item in partitions] == RUNTIME_NATIVE_KINDS,
                f"V143 candidate partitions changed: {run['run_id']}:{line_number}",
            )
            for partition in partitions:
                _require(
                    partition.get("cohort_player_order_hash") == combined_hash
                    and partition.get("random_prefix_player_count") == prefix_players
                    and partition.get("random_prefix_assignment_hash")
                    == partition.get("expected_random_prefix_assignment_hash")
                    == prefix.get("ordered_command_hash")
                    and partition.get("random_prefix_nodes_preserved") is True
                    and partition.get("ready_tail_player_count") == tail
                    and type(partition.get("ready_tail_assignment_hash")) is int,
                    f"V143 hybrid partition changed: {run['run_id']}:{line_number}",
                )

            selected_candidate: dict[str, Any] | None = None
            candidates = portfolio.get("candidates")
            if players == 0:
                _require(
                    portfolio.get("enabled") is False
                    and portfolio.get("rule") is None
                    and portfolio.get("candidate_count") == 0
                    and candidates == []
                    and portfolio.get("selected_kind") is None
                    and portfolio.get("deterministic_selection_reason") is None
                    and portfolio.get("random_default_index") is None
                    and portfolio.get("default_index") is None
                    and portfolio.get("default_kind") is None,
                    f"V143 empty portfolio changed: {run['run_id']}:{line_number}",
                )
            else:
                counts["player_windows"] += 1
                _require(
                    portfolio.get("enabled") is True
                    and portfolio.get("rule") == SELECTION_RULE
                    and portfolio.get("candidate_count") == 7
                    and portfolio.get("random_default_index") is None
                    and portfolio.get("default_index") == 0
                    and portfolio.get("default_kind") == "faasrank"
                    and isinstance(candidates, list)
                    and len(candidates) == 7
                    and [item.get("kind") for item in candidates]
                    == RUNTIME_NATIVE_KINDS,
                    f"V143 active portfolio changed: {run['run_id']}:{line_number}",
                )
                default = candidates[0]
                for candidate in candidates:
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
                            for field in ("service_sum", "service_max", "paper_welfare")
                        )
                        and candidate.get("default_kind") == "faasrank"
                        and all(
                            candidate.get(field) is None
                            for field in RANDOM_RELATIVE_FIELDS
                        ),
                        f"V143 candidate invalid: {run['run_id']}:{line_number}",
                    )
                    expected = {
                        "default_service_max_nonworse": float(candidate["service_max"])
                        <= float(default["service_max"]) + 1.0e-6,
                        "default_service_sum_nonworse": float(candidate["service_sum"])
                        <= float(default["service_sum"]) + 1.0e-6,
                        "default_service_sum_strictly_lower": float(
                            candidate["service_sum"]
                        )
                        < float(default["service_sum"]) - 1.0e-6,
                        "default_welfare_nonworse": float(candidate["paper_welfare"])
                        + 1.0e-6
                        >= float(default["paper_welfare"]),
                    }
                    expected["default_service_pareto_admissible"] = (
                        expected["default_service_max_nonworse"]
                        and expected["default_service_sum_strictly_lower"]
                        and expected["default_welfare_nonworse"]
                    )
                    _require(
                        all(
                            candidate.get(field) is value
                            for field, value in expected.items()
                        ),
                        f"V143 default predicates changed: {run['run_id']}:{line_number}",
                    )
                ranks = _rank_portfolio_candidates(candidates)
                for candidate, expected_ranks in zip(candidates, ranks):
                    _require(
                        all(
                            candidate.get(field) == value
                            for field, value in expected_ranks.items()
                        ),
                        f"V143 candidate ranks changed: {run['run_id']}:{line_number}",
                    )
                selected, selection_reason = _expected_v143_selection(candidates)
                _require(
                    [item.get("selected") for item in candidates]
                    == [index == selected for index in range(7)]
                    and portfolio.get("selected_kind") == candidates[selected]["kind"]
                    and portfolio.get("deterministic_selection_reason")
                    == selection_reason,
                    f"V143 portfolio selection changed: {run['run_id']}:{line_number}",
                )
                selected_candidate = candidates[selected]
                counts[f"selected_{selected_candidate['kind']}"] += 1
                counts[f"selection_reason_{selection_reason}"] += 1

            initializer_players = native.get("initializer_readiness_service_players")
            proposal_players = native.get("proposal_readiness_service_players")
            _require(
                type(initializer_players) is int
                and initializer_players >= 0
                and type(proposal_players) is int
                and proposal_players >= 0
                and native.get("certificate_uses_completion_outcomes") is False
                and native.get("service_certificate_scope")
                == SERVICE_CERTIFICATE_SCOPE,
                f"V143 native service counts changed: {run['run_id']}:{line_number}",
            )
            reason = guard.get("reason")
            _require(isinstance(reason, str), "invalid V143 guard reason")
            if players == 0:
                _require(
                    native.get("initializer_readiness_service_complete") is False
                    and native.get("proposal_readiness_service_complete") is False
                    and initializer_players == 0
                    and proposal_players == 0
                    and guard.get("accepted") is False
                    and guard.get("evaluated") is False
                    and guard.get("fallback_applied") is False
                    and reason == "not_applicable",
                    f"V143 empty guard changed: {run['run_id']}:{line_number}",
                )
                reasons[reason] += 1
                continue
            _require(
                selected_candidate is not None
                and native.get("kind") == selected_candidate["kind"]
                and native.get("valid") is True
                and native.get("commands") == players
                and native.get("duplicate_commands") == 0
                and native.get("unexpected_messages") == 0
                and native.get("missing_players") == 0
                and native.get("extra_players") == 0
                and native.get("infeasible_commands") == 0
                and native.get("anchor_assignment_hash")
                == selected_candidate["assignment_hash"]
                and native.get("ordered_command_hash")
                == selected_candidate["ordered_command_hash"]
                and native.get("initializer_readiness_service_complete") is True
                and initializer_players == players
                and native.get("initializer_readiness_service_sum")
                == selected_candidate["service_sum"]
                and native.get("initializer_readiness_service_max")
                == selected_candidate["service_max"],
                f"V143 selected hybrid changed: {run['run_id']}:{line_number}",
            )
            initializer_complete = (
                native.get("initializer_readiness_service_complete") is True
            )
            proposal_complete = (
                native.get("proposal_readiness_service_complete") is True
            )
            if initializer_complete and proposal_complete:
                _require(
                    initializer_players == proposal_players == players
                    and all(
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
                    f"V143 service certificate changed: {run['run_id']}:{line_number}",
                )
                counts["service_windows"] += 1
                initializer_sum = float(native["initializer_readiness_service_sum"])
                proposal_sum = float(native["proposal_readiness_service_sum"])
                initializer_max = float(native["initializer_readiness_service_max"])
                proposal_max = float(native["proposal_readiness_service_max"])
                _require(
                    native.get("readiness_service_sum_delta")
                    == proposal_sum - initializer_sum
                    and native.get("readiness_service_max_delta")
                    == proposal_max - initializer_max,
                    f"V143 service deltas changed: {run['run_id']}:{line_number}",
                )
            else:
                _require(
                    initializer_complete
                    and not proposal_complete
                    and proposal_players == 0
                    and guard.get("accepted") is False
                    and reason == "proposal_readiness_service_unavailable",
                    f"V143 incomplete proposal changed: {run['run_id']}:{line_number}",
                )
                initializer_sum = float(native["initializer_readiness_service_sum"])
                initializer_max = float(native["initializer_readiness_service_max"])
                proposal_sum = float("inf")
                proposal_max = float("inf")
                counts["unavailable_service_windows"] += 1
            initializer_welfare = guard.get("initializer_baseline_welfare")
            proposal_welfare = guard.get("proposal_baseline_welfare")
            welfare_delta = guard.get("baseline_welfare_delta")
            _require(
                guard.get("evaluated") is True
                and _finite(initializer_welfare)
                and _finite(proposal_welfare)
                and _finite(welfare_delta)
                and float(initializer_welfare)
                == float(selected_candidate["paper_welfare"])
                and _f32(float(proposal_welfare) - float(initializer_welfare))
                == float(welfare_delta),
                f"V143 welfare certificate changed: {run['run_id']}:{line_number}",
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
                f"V143 guard changed: {run['run_id']}:{line_number}",
            )
            reasons[reason] += 1
            if expected_accepted:
                counts["accepted_windows"] += 1

    _require(
        counts["run_config"] == 1, f"V143 run-config count changed: {run['run_id']}"
    )
    _require(counts["windows"] == 4000, f"V143 window count changed: {run['run_id']}")
    _require(
        counts["player_windows"] > 0, f"V143 has no player windows: {run['run_id']}"
    )
    return {
        "window_count": counts["windows"],
        "native_player_window_count": counts["player_windows"],
        "service_certificate_window_count": counts["service_windows"],
        "accepted_proposal_window_count": counts["accepted_windows"],
        "random_early_stop_window_count": counts["random_early_stop_windows"],
        "random_missing_feasible_player_count": counts[
            "random_missing_feasible_players"
        ],
        "ready_tail_window_count": counts["ready_tail_windows"],
        "ready_tail_player_count": counts["ready_tail_players"],
        "guard_reasons": dict(sorted(reasons.items())),
        "native_selection_rule": SELECTION_RULE,
        "selected_native_counts": {
            kind: counts[f"selected_{kind}"] for kind in RUNTIME_NATIVE_KINDS
        },
        "selection_reason_counts": {
            key.removeprefix("selection_reason_"): value
            for key, value in sorted(counts.items())
            if key.startswith("selection_reason_")
        },
        "performance_fields_consulted": False,
    }


def _verify_v142_baselines() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _assert_frozen_inputs()
    blind = read_json(V142_BLIND)
    _require(
        file_hash(V142_BLIND) == V142_BLIND_SHA256
        and _assert_hashed_object(blind, "audit_hash", "V142 blind audit")
        == V142_BLIND_HASH,
        "frozen V142 blind audit changed",
    )
    result = read_json(V142_RESULT)
    _require(
        file_hash(V142_RESULT) == V142_RESULT_SHA256
        and _assert_hashed_object(result, "result_hash", "V142 result")
        == V142_RESULT_HASH
        and result.get("family_training_gate_pass") is False
        and result.get("selected_profile") is None
        and result.get("confirmation_inputs_generated") is False,
        "frozen V142 result changed",
    )
    manifest = load_and_validate_manifest(V142_BASELINE_READY)
    frozen_manifest = blind.get("ready_manifests", {}).get("v142-baselines", {})
    _require(
        len(manifest["runs"]) == 81
        and file_hash(V142_BASELINE_READY) == frozen_manifest.get("file_sha256")
        and manifest["manifest_hash"] == frozen_manifest.get("manifest_hash"),
        "frozen V142 baseline manifest changed",
    )
    pairing = read_json(V142_BASELINE_PAIRING)
    frozen_pairing = next(
        (
            item
            for item in blind.get("pairing", [])
            if item.get("manifest_id") == "v142-baselines"
        ),
        {},
    )
    _require(
        pairing.get("passed") is True
        and pairing.get("failed_group_count") == 0
        and pairing.get("run_count") == 81,
        "frozen V142 baseline pairing changed",
    )
    _require(
        file_hash(V142_BASELINE_PAIRING) == frozen_pairing.get("file_sha256"),
        "frozen V142 baseline pairing file changed",
    )
    expected_ids = {run["run_id"] for run in manifest["runs"]}
    actual_ids = {
        path.name
        for path in (V142_BASELINE_WORKSPACE / "canonical").iterdir()
        if path.is_dir()
    }
    _require(expected_ids == actual_ids, "frozen V142 baseline canonical set changed")
    _require(
        not list((V142_BASELINE_WORKSPACE / "quarantine").glob("**/attempt-*")),
        "frozen V142 baseline quarantine is nonempty",
    )
    ledger, last_hash = _read_ledger(V142_BASELINE_WORKSPACE / "ledger.jsonl")
    counts = Counter(row["event_type"] for row in ledger)
    _require(
        counts["attempt_started"] == 81
        and counts["attempt_canonicalized"] == 81
        and not any(
            counts[event]
            for event in (
                "attempt_failed",
                "attempt_quarantined",
                "run_blocked",
                "partial_abandoned",
            )
        ),
        f"frozen V142 baseline ledger changed: {counts}",
    )
    admitted = {
        item["run_id"]: item
        for item in blind["runs"]
        if item.get("manifest_id") == "v142-baselines"
    }
    _require(len(admitted) == 81, "V142 baseline blind evidence changed")
    evidence = []
    for run in manifest["runs"]:
        canonical = V142_BASELINE_WORKSPACE / "canonical" / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        frozen = admitted[run["run_id"]]
        _require(
            attempt.get("attempt") == 1
            and attempt.get("status") == "qc_pass"
            and attempt.get("classification") == "qc_pass"
            and attempt.get("exit_code") == 0
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
            and attempt.get("result_sha256") == frozen.get("result_sha256")
            and file_hash(canonical / "manifest.json")
            == frozen.get("audit_manifest_sha256")
            and file_hash(canonical / "qc_report.json")
            == frozen.get("qc_report_sha256"),
            f"frozen V142 baseline evidence changed: {run['run_id']}",
        )
        evidence.append(
            {
                "method_label": run["method"],
                "run_id": run["run_id"],
                "scenario": scenario_id(run),
                "seed": run["seed"],
                "result_sha256": attempt["result_sha256"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "workload_tape_key": run["workload_tape"]["key"],
                "workload_spec_hash": run["workload_spec_hash"],
                "capture_environment_sha256": run["workload_tape"][
                    "capture_environment"
                ]["capture_environment_sha256"],
                "common_hpa_hash": run["common_hpa_hash"],
                "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
                "simulation": run["simulation"],
                "ledger_last_hash": last_hash,
            }
        )
    return manifest, evidence


def _verify_tapes(candidate_manifest: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        V142_TAPE_CATALOG.is_file()
        and file_hash(V142_TAPE_CATALOG) == V142_TAPE_CATALOG_SHA256,
        "frozen V142 tape catalog changed",
    )
    catalog = read_json(V142_TAPE_CATALOG)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V142 tapes")
    entries = catalog.get("entries")
    _require(
        isinstance(entries, dict) and len(entries) == 12, "V142 tape count changed"
    )
    inspected = {}
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(
            info.sha256 == entry["sha256"]
            and info.event_count == entry["event_count"]
            and info.workload_seed == entry["workload_seed"]
            and info.dag_order_sha256 == entry["dag_order_sha256"],
            f"V142 tape evidence changed: {key}",
        )
        inspected[key] = info.sha256
    used = {}
    for run in candidate_manifest["runs"]:
        tape = run["workload_tape"]
        _require(
            tape["key"] in entries and entries[tape["key"]]["sha256"] == tape["sha256"],
            f"V143 tape binding changed: {run['run_id']}",
        )
        used[tape["key"]] = tape["sha256"]
    _require(len(used) == 9, "V143 used tape product changed")
    return {
        "path": str(V142_TAPE_CATALOG),
        "file_sha256": file_hash(V142_TAPE_CATALOG),
        "catalog_hash": catalog_hash,
        "tape_count": len(entries),
        "used_tape_count": len(used),
        "entries": inspected,
    }


def _verify_references(candidate_manifest: Mapping[str, Any]) -> dict[str, Any]:
    path = reference_catalog_path(ROOT)
    _require(path.is_file(), "missing V143 reference catalog")
    catalog = read_json(path)
    catalog_hash = _assert_hashed_object(catalog, "catalog_hash", "V143 references")
    entries = catalog.get("entries")
    expected_keys = {
        run["reference_dependency"]["key"] for run in candidate_manifest["runs"]
    }
    _require(
        isinstance(entries, dict)
        and set(entries) == expected_keys
        and len(entries) == 9
        and candidate_manifest.get("reference_catalog_hash") == catalog_hash,
        "V143 reference product changed",
    )
    stage_root = _stage_root_from_receipts(
        entries, "receipt_path", 9, "V143 references"
    )
    ledger, last_hash = _read_ledger(stage_root / "ledger.jsonl")
    counts = Counter(row["event_type"] for row in ledger)
    _require(
        counts == Counter({"reference_build_canonicalized": 9}),
        f"V143 reference ledger changed: {counts}",
    )
    _require(
        not list((stage_root / "quarantine").glob("**/attempt-*")),
        "V143 reference quarantine is nonempty",
    )
    bound = {
        run["reference_dependency"]["key"]: run["reference_dependency"]
        for run in candidate_manifest["runs"]
    }
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_reference_table(Path(entry["path"]))
        dependency = bound[key]
        fields = (
            "path",
            "sha256",
            "bytes",
            "line_count",
            "state_pair_sequence_sha256",
            "receipt_path",
            "receipt_sha256",
            "build_spec_hash",
            "build_process_observation_path",
            "build_process_observation_sha256",
        )
        _require(
            all(dependency.get(field) == entry.get(field) for field in fields)
            and info.sha256 == entry["sha256"]
            and info.bytes == entry["bytes"]
            and info.line_count == entry["line_count"]
            and info.state_pair_sequence_sha256 == entry["state_pair_sequence_sha256"]
            and file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"]
            and file_hash(Path(entry["build_process_observation_path"]))
            == entry["build_process_observation_sha256"],
            f"V143 reference evidence changed: {key}",
        )
        evidence.append(
            {
                "key": key,
                "sha256": entry["sha256"],
                "receipt_sha256": entry["receipt_sha256"],
                "build_spec_hash": entry["build_spec_hash"],
                "workload_tape_sha256": entry["workload_tape_sha256"],
            }
        )
    return {
        "path": str(path),
        "file_sha256": file_hash(path),
        "catalog_hash": catalog_hash,
        "ledger_last_hash": last_hash,
        "entries": evidence,
    }


def _validate_execution_receipt() -> dict[str, Any]:
    ready_schedule_path = ROOT / READY_SCHEDULE.name
    execution_path = ROOT / EXECUTION_RECEIPT.name
    _require(ready_schedule_path.is_file(), "missing V143 ready schedule")
    _require(execution_path.is_file(), "missing V143 execution receipt")
    schedule = read_json(ready_schedule_path)
    schedule_hash = _assert_hashed_object(
        schedule, "schedule_hash", "V143 ready schedule"
    )
    scheduled = schedule.get("schedule")
    frozen_manifest = schedule.get("ready_manifest")
    _require(
        isinstance(scheduled, list)
        and len(scheduled) == 9
        and len({item.get("run_id") for item in scheduled}) == 9
        and isinstance(frozen_manifest, dict)
        and frozen_manifest.get("run_count") == 9
        and Path(str(frozen_manifest.get("path"))).is_file()
        and file_hash(Path(str(frozen_manifest["path"])))
        == frozen_manifest.get("file_sha256"),
        "V143 ready schedule manifest binding changed",
    )
    receipt = read_json(execution_path)
    receipt_hash = _assert_hashed_object(
        receipt, "receipt_hash", "V143 execution receipt"
    )
    _require(
        receipt.get("candidate_performance_summaries_parsed") == 0
        and receipt.get("performance_results_consulted_for_mechanism_design") is True
        and receipt.get("plan_sha256") == PLAN_SHA256
        and receipt.get("ready_schedule_hash") == schedule_hash
        and receipt.get("dispatch_count") == 9
        and receipt.get("all_exit_codes_zero") is True
        and len(receipt.get("dispatches", [])) == 9,
        "V143 execution boundary changed",
    )
    for scheduled, dispatched in zip(schedule["schedule"], receipt["dispatches"]):
        _require(
            all(
                scheduled[field] == dispatched[field]
                for field in ("ordinal", "scenario", "seed", "run_id")
            )
            and dispatched.get("exit_code") == 0,
            f"V143 frozen dispatch changed: {scheduled['ordinal']}",
        )
        if dispatched.get("action") == "executed_frozen_dispatch":
            _require(
                file_hash(Path(dispatched["stdout_path"]))
                == dispatched["stdout_sha256"]
                and file_hash(Path(dispatched["stderr_path"]))
                == dispatched["stderr_sha256"],
                f"V143 dispatch logs changed: {scheduled['ordinal']}",
            )
        else:
            _require(
                dispatched.get("action") == "validated_preexisting_attempt1_canonical"
                and all(
                    isinstance(dispatched.get(field), str)
                    and len(dispatched[field]) == 64
                    for field in (
                        "attempt_file_sha256",
                        "qc_report_sha256",
                        "audit_manifest_sha256",
                    )
                ),
                f"V143 dispatch evidence changed: {scheduled['ordinal']}",
            )
    return {
        "ready_schedule_path": str(ready_schedule_path),
        "ready_schedule_file_sha256": file_hash(ready_schedule_path),
        "ready_schedule_hash": schedule_hash,
        "ready_manifest": frozen_manifest,
        "execution_receipt_path": str(execution_path),
        "execution_receipt_file_sha256": file_hash(execution_path),
        "execution_receipt_hash": receipt_hash,
    }


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V143 blind audit already exists: {output}")
    _require(not RESULT.exists(), "V143 reveal exists before blind audit")
    _require(PLAN.is_file() and file_hash(PLAN) == PLAN_SHA256, "V143 plan changed")
    _require(PREPARED.is_file(), "missing V143 prepared receipt")
    prepared = read_json(PREPARED)
    prepared_hash = _assert_hashed_object(
        prepared, "receipt_hash", "V143 prepared receipt"
    )
    unbound_path = paths(ROOT)["manifest"]
    _require(
        prepared.get("plan_sha256") == PLAN_SHA256
        and prepared.get("performance_results_consulted_for_mechanism_design") is True
        and prepared.get("candidate_performance_summaries_parsed") == 0
        and prepared.get("confirmation_inputs_generated") is False
        and prepared.get("reused_frozen_v142_baseline_runs") == 81
        and prepared.get("baseline_reruns") == 0
        and prepared.get("candidate_online_runs") == 9
        and prepared.get("candidate_reference_builds") == 9
        and prepared.get("binary_sha256") == BINARY_SHA256
        and prepared.get("arm_id") == ARM_ID
        and prepared.get("profile") == PROFILE
        and prepared.get("native_selection_rule") == SELECTION_RULE
        and prepared.get("training_seeds") == TRAINING_SEED_LIST
        and prepared.get("sealed_confirmation_seeds") == NEW_CONFIRMATION_SEEDS,
        "V143 prepared boundary changed",
    )
    _require(
        unbound_path.is_file()
        and file_hash(unbound_path) == prepared.get("manifest_file_sha256")
        and read_json(unbound_path).get("manifest_hash")
        == prepared.get("manifest_hash"),
        "V143 prepared unbound manifest changed",
    )
    execution = _validate_execution_receipt()
    baseline_manifest, baseline_evidence = _verify_v142_baselines()
    candidate_path = ready_manifest_path(ROOT)
    candidate_manifest = load_and_validate_manifest(candidate_path)
    _require(
        len(candidate_manifest["runs"]) == 9
        and candidate_manifest.get("all_tapes_bound") is True
        and candidate_manifest.get("all_sla_targets_bound") is True
        and candidate_manifest.get("all_references_bound") is True
        and candidate_manifest.get("all_faasrank_models_bound") is False,
        "V143 ready manifest boundary changed",
    )
    _require(
        execution["ready_manifest"].get("path") == str(candidate_path)
        and execution["ready_manifest"].get("file_sha256") == file_hash(candidate_path)
        and execution["ready_manifest"].get("manifest_hash")
        == candidate_manifest["manifest_hash"],
        "V143 ready schedule no longer matches the candidate manifest",
    )
    expected_cells = {
        (scenario, seed)
        for scenario in (
            "spike5x50ms",
            "sustained3x200ms",
            "pulse4x4x50ms",
        )
        for seed in TRAINING_SEED_LIST
    }
    _require(
        {(scenario_id(run), run["seed"]) for run in candidate_manifest["runs"]}
        == expected_cells,
        "V143 ready product changed",
    )
    tapes = _verify_tapes(candidate_manifest)
    references = _verify_references(candidate_manifest)
    pairing = read_json(pairing_path(ROOT))
    _require(
        pairing.get("passed") is True
        and pairing.get("failed_group_count") == 0
        and pairing.get("run_count") == 9,
        "V143 pairing changed",
    )
    workspace = workspace_path(ROOT)
    expected_ids = {run["run_id"] for run in candidate_manifest["runs"]}
    actual_ids = {
        path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
    }
    _require(actual_ids == expected_ids, "V143 canonical set changed")
    _require(
        not list((workspace / "quarantine").glob("**/attempt-*")),
        "V143 online quarantine is nonempty",
    )
    ledger, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
    ledger_counts = Counter(row["event_type"] for row in ledger)
    _require(
        ledger_counts["attempt_started"] == 9
        and ledger_counts["attempt_canonicalized"] == 9
        and not any(
            ledger_counts[event]
            for event in (
                "attempt_failed",
                "attempt_quarantined",
                "run_blocked",
                "partial_abandoned",
            )
        ),
        f"V143 online ledger changed: {ledger_counts}",
    )

    runtime_values: dict[str, set[str]] = defaultdict(set)
    candidate_evidence = []
    paired_inputs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in baseline_evidence:
        paired_inputs[(item["scenario"], item["seed"])].append(item)
    for run in candidate_manifest["runs"]:
        metadata = run.get("metadata", {})
        _require(
            run.get("method") == "sche_nash"
            and run.get("environment", {}).get("NASH_OPERATIONAL_EXPERT_PROXY")
            == PROFILE
            and metadata.get("v143_native_selection_rule") == SELECTION_RULE
            and metadata.get("v143_random_prefix_preserved") is True
            and metadata.get("v143_random_prefix_node_ids_preserved") is True
            and metadata.get("v143_ready_tail_predicate") == READY_TAIL_PREDICATE
            and metadata.get("v143_common_cohort_required") is True
            and metadata.get("v143_faasrank_default_required") is True
            and metadata.get("v143_complete_hybrid_assignments_required") is True
            and metadata.get("v143_service_certificate_scope")
            == SERVICE_CERTIFICATE_SCOPE
            and metadata.get("v143_service_certificate_state_domain")
            == V143_SERVICE_STATE_DOMAIN
            and metadata.get("v143_paper_welfare_state_domain")
            == V143_WELFARE_STATE_DOMAIN
            and metadata.get("v143_outcome_fields_drive_policy") is False
            and metadata.get("v143_confirmation_inputs_opened") is False
            and isinstance(run.get("reference_dependency"), dict),
            f"V143 candidate manifest boundary changed: {run['run_id']}",
        )
        canonical = workspace / "canonical" / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=candidate_manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        audit = read_json(canonical / "manifest.json")
        _require(
            attempt.get("attempt") == 1
            and attempt.get("status") == "qc_pass"
            and attempt.get("classification") == "qc_pass"
            and attempt.get("exit_code") == 0
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass",
            f"V143 canonical status changed: {run['run_id']}",
        )
        runtime = _runtime_evidence(audit)
        for field, value in runtime.items():
            runtime_values[field].add(value)
        diagnostics = _validate_v143_native_diagnostics(run, canonical)
        paired = {
            "method_label": ARM_ID,
            "run_id": run["run_id"],
            "scenario": scenario_id(run),
            "seed": run["seed"],
            "workload_tape_sha256": run["workload_tape"]["sha256"],
            "workload_tape_key": run["workload_tape"]["key"],
            "workload_spec_hash": run["workload_spec_hash"],
            "capture_environment_sha256": run["workload_tape"]["capture_environment"][
                "capture_environment_sha256"
            ],
            "common_hpa_hash": run["common_hpa_hash"],
            "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
            "simulation": run["simulation"],
        }
        paired_inputs[(paired["scenario"], paired["seed"])].append(paired)
        candidate_evidence.append(
            {
                "manifest_id": ARM_ID,
                "method_label": ARM_ID,
                "run_id": run["run_id"],
                "scenario": paired["scenario"],
                "seed": run["seed"],
                "run_spec_hash": run["run_spec_hash"],
                "workload_tape_sha256": run["workload_tape"]["sha256"],
                "reference_key": run["reference_dependency"]["key"],
                "result_sha256": attempt["result_sha256"],
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "attempt": 1,
                "classification": "qc_pass",
                "native_diagnostics": diagnostics,
                "ledger_last_hash": ledger_last_hash,
                "reference_ledger_last_hash": references["ledger_last_hash"],
            }
        )

    for field, expected in EXPECTED_RUNTIME.items():
        _require(
            runtime_values[field] == {expected},
            f"V143 runtime {field} changed: {runtime_values[field]}",
        )
    git_commits = runtime_values["git_commit"]
    _require(
        len(git_commits) == 1
        and len(next(iter(git_commits))) == 40
        and all(
            character in "0123456789abcdef" for character in next(iter(git_commits))
        ),
        f"V143 runtime git identity changed: {git_commits}",
    )
    _require(len(paired_inputs) == 9, "V143 paired block count changed")
    for (scenario, seed), rows in paired_inputs.items():
        _require(
            len(rows) == 10
            and {row["method_label"] for row in rows} == {*BASELINE_METHODS, ARM_ID},
            f"V143 paired product changed: {scenario}/{seed}",
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
                f"V143 paired {field} changed: {scenario}/{seed}",
            )
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V143 common HPA changed: {scenario}/{seed}",
        )

    payload = {
        "schema_version": "NSE_E3_RANDOM_PREFIX_READY_TAIL_BLIND_AUDIT_V143_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "performance_results_consulted_for_mechanism_design": True,
        "candidate_performance_results_consulted": False,
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
        "sealed_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
        "baseline_rerun_count": 0,
        "baseline_run_count": 81,
        "candidate_run_count": 9,
        "analyzed_run_count": 90,
        "reference_count": 9,
        "tape_count": 12,
        "block_count": 9,
        "execution": execution,
        "v142_baseline_manifest": {
            "path": str(V142_BASELINE_READY),
            "file_sha256": file_hash(V142_BASELINE_READY),
            "manifest_hash": baseline_manifest["manifest_hash"],
            "run_count": 81,
        },
        "v142_baseline_pairing": {
            "path": str(V142_BASELINE_PAIRING),
            "file_sha256": file_hash(V142_BASELINE_PAIRING),
        },
        "candidate_manifest": {
            "path": str(candidate_path),
            "file_sha256": file_hash(candidate_path),
            "manifest_hash": candidate_manifest["manifest_hash"],
            "run_count": 9,
        },
        "candidate_pairing": {
            "path": str(pairing_path(ROOT)),
            "file_sha256": file_hash(pairing_path(ROOT)),
            "run_count": pairing["run_count"],
            "group_count": pairing["group_count"],
        },
        "tapes": tapes,
        "references": references,
        "baseline_runs": baseline_evidence,
        "candidate_runs": candidate_evidence,
    }
    payload["audit_hash"] = object_hash(payload)
    write_json_atomic(output, payload)
    return payload


def main() -> None:
    audit = run_blind_audit()
    print(
        json.dumps(
            {
                "status": audit["status"],
                "candidate_runs": audit["candidate_run_count"],
                "audit_hash": audit["audit_hash"],
            }
        )
    )


if __name__ == "__main__":
    main()
