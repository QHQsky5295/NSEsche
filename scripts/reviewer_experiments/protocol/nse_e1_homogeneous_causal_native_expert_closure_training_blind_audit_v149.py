from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.formal_inputs import (
    validate_canonical_run,
    validate_pairing_audit,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_execute_v149 import (
    EXECUTION_RECEIPT_NAME,
    READY_SCHEDULE_NAME,
    _assert_hashed,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_prepare_v149 import (
    AMENDMENT_SHA256,
    BINARY_SHA256,
    CARGO_LOCK_SHA256,
    LOADS,
    PLAN_SHA256,
    PROFILE,
    PYTHON_SHA256,
    ROOT,
    SEEDS,
    paths,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


OUTPUT_NAME = "joint-blind-audit-v149-training.json"
EPSILON = 1e-6


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _expected_route(load: str, frame: int) -> tuple[str, str, int]:
    if load == "high" and frame >= 19:
        return "jiagu", "high", 1
    if load == "middle" and frame >= 99:
        return "faasrank", "middle", 1
    if load == "low" and frame >= 99:
        return "ocs", "low", 1
    return "ocs", "unclassified", 0


def _validate_candidate_selection(
    candidates: list[Mapping[str, Any]], route: str, player_count: int
) -> None:
    if player_count == 0:
        if candidates:
            raise RuntimeError(
                "empty V149 window unexpectedly selected a native candidate"
            )
        return
    expected_kinds = ["ocs", "orion"] if route == "ocs" else [route]
    if [item.get("kind") for item in candidates] != expected_kinds:
        raise RuntimeError("V149 native candidate order or membership changed")
    if sum(item.get("selected") is True for item in candidates) != 1:
        raise RuntimeError(
            "V149 native portfolio did not select exactly one initializer"
        )
    for item in candidates:
        if (
            item.get("valid") is not True
            or item.get("service_complete") is not True
            or not _finite(item.get("service_sum"))
            or not _finite(item.get("service_max"))
            or not _finite(item.get("paper_welfare"))
        ):
            raise RuntimeError("V149 native candidate is incomplete or non-finite")
    if route != "ocs":
        if candidates[0].get("selected") is not True:
            raise RuntimeError("V149 single selected native route changed")
        return
    ocs, orion = candidates
    strict_orion = (
        orion["service_max"] <= ocs["service_max"] + EPSILON
        and orion["service_sum"] < ocs["service_sum"] - EPSILON
        and orion["paper_welfare"] + EPSILON >= ocs["paper_welfare"]
    )
    if orion.get("selected") is not strict_orion:
        raise RuntimeError(
            "V149 Orion advisory selection violated the frozen certificate"
        )


def _validate_nash_certificate(decision: Mapping[str, Any]) -> None:
    anchor = decision.get("native_shadow_anchor")
    if not isinstance(anchor, Mapping):
        raise RuntimeError("V149 native shadow anchor observation is missing")
    accepted = decision.get("window_safe_guard", {}).get("accepted") is True
    if accepted:
        values = {
            key: anchor.get(key)
            for key in (
                "initializer_readiness_service_sum",
                "proposal_readiness_service_sum",
                "initializer_readiness_service_max",
                "proposal_readiness_service_max",
            )
        }
        if not all(_finite(value) for value in values.values()):
            raise RuntimeError(
                "accepted V149 Nash proposal lacks finite service evidence"
            )
        if not (
            values["proposal_readiness_service_max"]
            <= values["initializer_readiness_service_max"] + EPSILON
            and values["proposal_readiness_service_sum"]
            < values["initializer_readiness_service_sum"] - EPSILON
        ):
            raise RuntimeError(
                "accepted V149 Nash proposal violated the service certificate"
            )
        guard = decision["window_safe_guard"]
        initial_welfare = guard.get("initializer_baseline_welfare")
        proposal_welfare = guard.get("proposal_baseline_welfare")
        if not (
            _finite(initial_welfare)
            and _finite(proposal_welfare)
            and proposal_welfare + EPSILON >= initial_welfare
        ):
            raise RuntimeError(
                "accepted V149 Nash proposal violated the welfare certificate"
            )


def _validate_window(event: Mapping[str, Any], load: str, frame: int) -> dict[str, int]:
    if event.get("kind") != "window" or event.get("frame") != frame:
        raise RuntimeError("V149 scheduler window sequence changed")
    decision = event.get("decision")
    if not isinstance(decision, Mapping):
        raise RuntimeError("V149 decision observation is missing")
    portfolio = decision.get("native_portfolio")
    if (
        not isinstance(portfolio, Mapping)
        or portfolio.get("rule") != "causal_steady_load_closure"
    ):
        raise RuntimeError("V149 native portfolio rule changed")
    closure = portfolio.get("v149_causal_steady_load_closure")
    if not isinstance(closure, Mapping) or closure.get("enabled") is not True:
        raise RuntimeError("V149 causal closure observation is missing")
    route, band, switches = _expected_route(load, frame)
    if (
        closure.get("frame") != frame
        or closure.get("history_valid") is not True
        or closure.get("frame_reset_this_window") is not False
        or closure.get("history_discontinuity_this_window") is not False
        or closure.get("route_selected_kind") != route
        or closure.get("frozen_band") != band
        or closure.get("route_switch_count") != switches
        or closure.get("selected_state_invocations_this_window") != 1
        or closure.get("request_freq_scenario_seed_tape_future_or_outcome_inputs_used")
        is not False
    ):
        raise RuntimeError("V149 causal route/history invariant failed")
    initializations = closure.get("selected_state_initializations", {})
    expected_initializations = {
        "ocs": 1,
        "faasrank": int(load == "middle" and frame >= 99),
        "jiagu": int(load == "high" and frame >= 19),
    }
    if initializations != expected_initializations:
        raise RuntimeError("V149 selected expert initialization count changed")
    totals = closure.get("selected_state_invocations_total", {})
    if load == "high":
        expected_totals = {
            "ocs": min(frame + 1, 19),
            "faasrank": 0,
            "jiagu": max(0, frame - 18),
        }
    elif load == "middle":
        expected_totals = {
            "ocs": min(frame + 1, 99),
            "faasrank": max(0, frame - 98),
            "jiagu": 0,
        }
    else:
        expected_totals = {"ocs": frame + 1, "faasrank": 0, "jiagu": 0}
    if totals != expected_totals:
        raise RuntimeError("V149 selected expert invocation count changed")
    advisory = closure.get("orion_advisory", {})
    ocs_this_window = route == "ocs"
    if (
        advisory.get("fresh_stateless_each_ocs_window") is not True
        or advisory.get("counterfactual_persistent_state_committed") is not False
        or advisory.get("invocations_this_window") != int(ocs_this_window)
        or advisory.get("invocations_total") != expected_totals["ocs"]
    ):
        raise RuntimeError("V149 Orion stateless advisory lifecycle changed")
    if route == "ocs" and (
        closure.get("ocs_expected_feasible_player_count")
        != closure.get("selected_native_frontier_player_count")
    ):
        raise RuntimeError("V149 OCS cohort was not preserved exactly")
    player_count = closure.get("selected_native_frontier_player_count")
    if (
        not isinstance(player_count, int)
        or isinstance(player_count, bool)
        or player_count < 0
    ):
        raise RuntimeError("V149 selected native frontier player count is invalid")
    _validate_candidate_selection(portfolio.get("candidates", []), route, player_count)
    accepted = decision.get("window_safe_guard", {}).get("accepted") is True
    if accepted:
        if closure.get("accepted_nash_proposal_dispatched_exactly") is not True:
            raise RuntimeError("accepted V149 Nash proposal was not dispatched exactly")
    elif closure.get("selected_initializer_dispatched_exactly") is not True:
        raise RuntimeError("V149 selected initializer was not dispatched exactly")
    _validate_nash_certificate(decision)
    return {
        "windows": 1,
        "nash_accepts": int(accepted),
        "orion_accepts": int(advisory.get("projection_selected") is True),
    }


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    path = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    if not path.is_file():
        raise RuntimeError(f"V149 Nash log is missing: {run_id}")
    run_config_count = 0
    frame = 0
    counters = {"windows": 0, "nash_accepts": 0, "orion_accepts": 0}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for raw in stream:
            event = json.loads(raw)
            kind = event.get("kind")
            if kind == "run_config":
                run_config_count += 1
                if (
                    event.get("scheduler") != "sche_nash"
                    or event.get("operational_expert_proxy") != PROFILE
                ):
                    raise RuntimeError("V149 run_config scheduler/profile changed")
            elif kind == "window":
                observed = _validate_window(
                    event, run["workload"]["request_freq"], frame
                )
                for key, value in observed.items():
                    counters[key] += value
                frame += 1
            elif kind not in {"function_profile", "run_summary"}:
                raise RuntimeError(f"unexpected V149 Nash observation kind: {kind}")
    if run_config_count != 1 or frame != 1000:
        raise RuntimeError("V149 Nash log does not contain one config and 1000 windows")
    return {"run_id": run_id, "nash_metrics_sha256": file_hash(path), **counters}


def _validate_reference_catalog(
    manifest: Mapping[str, Any], catalog_path: Path
) -> dict[str, Any]:
    catalog = read_json(catalog_path)
    payload = dict(catalog)
    claimed = payload.pop("catalog_hash", None)
    if not isinstance(claimed, str) or object_hash(payload) != claimed:
        raise RuntimeError("V149 reference catalog self-hash changed")
    entries = catalog.get("entries")
    if not isinstance(entries, Mapping) or len(entries) != 60:
        raise RuntimeError("V149 reference catalog is not an exact 60-entry product")
    for dependency in manifest["reference_build_dependencies"]:
        entry = entries.get(dependency["key"])
        if not isinstance(entry, Mapping):
            raise RuntimeError("V149 reference catalog entry is missing")
        for field in (
            "sha256",
            "receipt_sha256",
            "state_pair_sequence_sha256",
            "assignment_sequence_sha256",
            "build_spec_hash",
        ):
            if entry.get(field) != dependency.get(field):
                raise RuntimeError(f"V149 bound reference {field} changed")
        if file_hash(Path(entry["path"])) != entry["sha256"]:
            raise RuntimeError("V149 reference table content hash changed")
        if file_hash(Path(entry["receipt_path"])) != entry["receipt_sha256"]:
            raise RuntimeError("V149 reference receipt content hash changed")
    return {"catalog_hash": claimed, "entry_count": len(entries)}


def run_blind_audit(root: Path = ROOT) -> dict[str, Any]:
    output = root / OUTPUT_NAME
    if output.exists():
        raise RuntimeError(f"V149 blind audit already exists: {output}")
    prepared = read_json(root / "prepared-manifest-v149.json")
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V149 prepared receipt")
    execution = read_json(root / EXECUTION_RECEIPT_NAME)
    execution_hash = _assert_hashed(execution, "receipt_hash", "V149 execution receipt")
    ready_schedule = read_json(root / READY_SCHEDULE_NAME)
    schedule_hash = _assert_hashed(
        ready_schedule, "schedule_hash", "V149 ready schedule"
    )
    manifest_path = paths(root)["ready"]
    manifest = load_and_validate_manifest(manifest_path)
    if (
        len(manifest["runs"]) != 60
        or manifest.get("all_references_bound") is not True
        or manifest.get("all_tapes_bound") is not True
        or {run["method"] for run in manifest["runs"]} != {"sche_nash"}
        or {(run["workload"]["request_freq"], run["seed"]) for run in manifest["runs"]}
        != {(load, seed) for load in LOADS for seed in SEEDS}
    ):
        raise RuntimeError("V149 ready product changed")
    ledger_count, ledger_hash = verify_ledger(paths(root)["workspace"] / "ledger.jsonl")
    pairing = validate_pairing_audit(
        paths(root)["pairing"], manifest, paths(root)["workspace"] / "canonical"
    )
    reference = _validate_reference_catalog(manifest, paths(root)["catalog"])
    by_id = {run["run_id"]: run for run in manifest["runs"]}
    expected_order = [item["run_id"] for item in ready_schedule["schedule"]]
    if [item["run_id"] for item in execution["dispatches"]] != expected_order:
        raise RuntimeError("V149 execution order changed after freezing")
    audits = []
    runtime_identity: set[tuple[str, str, str, str]] = set()
    for run_id in expected_order:
        run = by_id[run_id]
        canonical = paths(root)["workspace"] / "canonical" / run_id
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit_manifest = read_json(canonical / "manifest.json")
        software = audit_manifest.get("software_environment", {})
        git = software.get("git", {})
        python = software.get("python", {})
        cargo_lock = software.get("cargo_lock", {})
        binary = audit_manifest.get("adapter_binary", {})
        identity = (
            binary.get("verified_sha256"),
            git.get("commit"),
            python.get("executable_sha256"),
            cargo_lock.get("sha256"),
        )
        runtime_identity.add(identity)
        audits.append(_audit_nash_log(canonical, run))
    if len(runtime_identity) != 1:
        raise RuntimeError("V149 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(runtime_identity))
    if (
        binary != BINARY_SHA256
        or python != PYTHON_SHA256
        or cargo != CARGO_LOCK_SHA256
        or git_commit != prepared.get("protocol_source_commit")
    ):
        raise RuntimeError("V149 runtime identity changed from the frozen preparation")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CAUSAL_NATIVE_EXPERT_CLOSURE_BLIND_AUDIT_V149_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "candidate_performance_summaries_parsed": 0,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "amendment_sha256": AMENDMENT_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "prepared_receipt_file_sha256": file_hash(root / "prepared-manifest-v149.json"),
        "execution_receipt_hash": execution_hash,
        "execution_receipt_file_sha256": file_hash(root / EXECUTION_RECEIPT_NAME),
        "ready_schedule_hash": schedule_hash,
        "ready_schedule_file_sha256": file_hash(root / READY_SCHEDULE_NAME),
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(manifest_path),
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "ledger_file_sha256": file_hash(paths(root)["workspace"] / "ledger.jsonl"),
        "pairing_audit_path": str(paths(root)["pairing"]),
        "pairing_audit_file_sha256": file_hash(paths(root)["pairing"]),
        "run_count": len(audits),
        "window_count": sum(item["windows"] for item in audits),
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": PROFILE,
        "all_causal_native_cohort_certificate_dispatch_invariants_passed": True,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output, document)
    return document


def main() -> None:
    document = run_blind_audit()
    print(json.dumps({"blind_audit_hash": document["blind_audit_hash"], "runs": 60}))


if __name__ == "__main__":
    main()
