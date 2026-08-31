from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    BINARY_PATH,
    BINARY_SHA256,
    BINARY_SOURCE_COMMIT,
    CARGO_LOCK_SHA256,
    MODULE_CONF_SHA256,
    PYTHON_PATH,
    PYTHON_SHA256,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_HASH,
    SOURCE_MANIFEST_SHA256,
    SOURCE_PAIRING,
    SOURCE_PAIRING_SHA256,
    _assert_file,
    _assert_hashed,
    _validate_reference_catalog,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import (
    load_and_validate_manifest,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
    derive_integration_smoke_shard,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e1_homogeneous_random_prefix_diagnostic_20260831_v153")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_random_prefix_diagnostic_plan_v153.json"
)
PLAN_SHA256 = "d016b4bb78f72b37088ba8248f6f8259a0d1980ae47d5472f82e0b354a96f319"
V152_RESULT = Path(
    "tmp/nse_e1_homogeneous_container_affinity_diagnostic_20260831_v152/"
    "diagnostic-result-v152.json"
)
V152_RESULT_SHA256 = "77ae361ea4acc515d10d3d9915ac161dde44bf4b598ca8f0c0075e406b16519a"
V152_RESULT_HASH = "86349af749b6ce8eb638bb75986e6699b59d6a36e2768917d61bacde02ed50f9"
SOURCE_WORKSPACE = SOURCE_MANIFEST.parent / "formal-runs"

ARM_ID = "v153-middle-exact-random-prefix-service-safe-nash"
PROFILE = "random_prefix_native_faithful_service_window_safe_pareto"
SEEDS = ("E09", "E17")
PORT = "3204"
COMMON_ENVIRONMENT = {
    "NASH_OPERATIONAL_DIRECT_INITIALIZATION": "1",
    "NASH_OPERATIONAL_INDIFFERENCE_EPSILON": "15.0",
    "NASH_OPERATIONAL_SWITCH_THRESHOLD": "0.0",
    "NASH_OPERATIONAL_ADAPTIVE_PROXY": "0",
    "NASH_OPERATIONAL_STRUCTURAL_PROXY": "0",
    "NASH_OPERATIONAL_HYBRID_PROXY": "1",
    "NASH_OPERATIONAL_BOUNDED_PROXY": "0",
    "NASH_OPERATIONAL_QUEUE_WEIGHT": "0.20",
    "NASH_OPERATIONAL_COLD_START_WEIGHT": "0.55",
    "NASH_OPERATIONAL_PROJECTED_LOAD_WEIGHT": "1.0",
    "NASH_OPERATIONAL_RESOURCE_WEIGHT": "0.15",
    "NASH_OPERATIONAL_UNRESTRICTED_INITIALIZATION": "1",
}
COHORT_SOURCE = "exact_persistent_same_seed_native_Random_ScheCmd_prefix_with_unchanged_early_stop_semantics"
RANDOM_LIFECYCLE = "one_persistent_RandomScheduler_per_algorithm_seed_advanced_once_per_scheduling_window"
LEGAL_NOT_REQUESTED_TERMINATIONS = {
    "no_players",
    "inner_iteration_limit",
    "oscillation_guard",
}


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v153.json",
        "schedule": root / "frozen-run-order-v153.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v153.json",
        "pairing": root / "pairing-audit-v153.json",
        "blind": root / "joint-blind-audit-v153.json",
        "result": root / "diagnostic-result-v153.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V153 plan"),
        (SOURCE_MANIFEST, SOURCE_MANIFEST_SHA256, "frozen E1 manifest"),
        (SOURCE_PAIRING, SOURCE_PAIRING_SHA256, "frozen E1 pairing"),
        (V152_RESULT, V152_RESULT_SHA256, "V152 retained result"),
        (BINARY_PATH, BINARY_SHA256, "V153 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
        (
            Path("serverless_sim/module_conf_es.json"),
            MODULE_CONF_SHA256,
            "frozen module_conf_es.json",
        ),
    ):
        _assert_file(path, sha256, label)
    source = read_json(SOURCE_MANIFEST)
    if not (
        source.get("manifest_hash") == SOURCE_MANIFEST_HASH
        and source.get("formal_results_eligible") is True
        and source.get("seed_stage") == "all"
        and len(source.get("runs", [])) == 600
    ):
        raise RuntimeError("frozen E1 source boundary changed")
    pairing = read_json(SOURCE_PAIRING)
    if pairing.get("passed") is not True or pairing.get("run_count") != 600:
        raise RuntimeError("frozen E1 pairing boundary changed")
    v152 = read_json(V152_RESULT)
    if not (
        _assert_hashed(v152, "result_hash", "V152 result") == V152_RESULT_HASH
        and v152.get("joint_mechanism_gate_pass") is False
        and v152.get("candidate_run_count") == 2
        and v152.get("valid_seed_deletion_replacement_relabeling_or_selective_rerun")
        is False
    ):
        raise RuntimeError("V152 retained-result boundary changed")
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V153 protocol source commit is invalid")
    selected = [
        run
        for run in source["runs"]
        if run.get("method") == "sche_nash"
        and run.get("seed") in SEEDS
        and run.get("workload", {}).get("request_freq") == "middle"
        and run.get("cluster") == {"node_count": 20, "topology": "homogeneous"}
    ]
    if len(selected) != 2 or {run["seed"] for run in selected} != set(SEEDS):
        raise RuntimeError("frozen source no longer has the V153 two-cell product")
    by_seed = {run["seed"]: run for run in selected}
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        [by_seed[seed]["run_id"] for seed in SEEDS],
        purpose=(
            "V153 adaptive two-point exact-Random-prefix mechanism diagnostic; "
            "never a formal result or paper superiority claim"
        ),
    )
    rewritten["created_at"] = utc_now()
    rewritten["execution"]["command_template"] = [
        "{python}",
        "-m",
        "scripts.reviewer_experiments.protocol.serverless_adapter",
        "--run-config",
        "{run_config}",
        "--simulator-exe",
        str(BINARY_PATH.resolve()),
    ]
    rewritten["all_references_bound"] = False
    rewritten.pop("reference_catalog_hash", None)
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": (
                "V153 adaptive two-point exact-Random-prefix mechanism diagnostic; "
                "never a formal result or paper superiority claim"
            ),
            "v153_role": "result_blind_mechanism_diagnostic",
            "v153_plan_sha256": PLAN_SHA256,
            "v153_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v153_protocol_source_commit": protocol_source_commit,
            "v153_binary_sha256": BINARY_SHA256,
            "v153_arm_id": ARM_ID,
            "v153_profile": PROFILE,
            "v153_environment": COMMON_ENVIRONMENT,
            "v153_expected_run_count": 2,
            "v153_expected_reference_build_count": 2,
            "v153_fixed_order": list(SEEDS),
            "v153_performance_results_consulted_for_design": True,
            "v153_candidate_performance_summaries_parsed": 0,
            "v153_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"].update(COMMON_ENVIRONMENT)
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v153_training_only": True,
            "v153_role": "result_blind_mechanism_diagnostic",
            "v153_plan_sha256": PLAN_SHA256,
            "v153_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v153_protocol_source_commit": protocol_source_commit,
            "v153_binary_sha256": BINARY_SHA256,
            "v153_arm_id": ARM_ID,
            "v153_profile": PROFILE,
            "v153_source_e1_run_id": source_run_id,
            "v153_source_e1_run_spec_hash": source_run_spec_hash,
            "v153_exact_random_prefix_cohort": True,
            "v153_numeric_hyperparameters_added": 0,
            "v153_candidate_performance_summaries_parsed_before_run": 0,
            "v153_confirmation_inputs_generated": False,
        }
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
        _assign_run_identity(run)
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    marker["selected_run_count"] = 2
    marker["selected_reference_build_count"] = 2
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == 2
        and {run["seed"] for run in manifest["runs"]} == set(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and {
            (run["workload"]["request_freq"], run["cluster"]["node_count"])
            for run in manifest["runs"]
        }
        == {("middle", 20)}
        and len(manifest.get("reference_build_dependencies", [])) == 2
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V153 exact two-cell product changed")
    for run in manifest["runs"]:
        expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
        if (
            run["experiment_id"] != "E1"
            or run["cluster"]["topology"] != "homogeneous"
            or any(
                run["environment"].get(key) != value for key, value in expected.items()
            )
            or run.get("metadata", {}).get("v153_profile") != PROFILE
        ):
            raise RuntimeError(f"V153 run contract changed: {run.get('run_id')}")


def prepare_v153(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V153 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_RUN_ORDER_V153_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "schedule": [
            {"ordinal": ordinal, "seed": seed}
            for ordinal, seed in enumerate(SEEDS, start=1)
        ],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_PREPARED_V153_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "performance_results_consulted_for_design": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_sha256": MODULE_CONF_SHA256,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "v152_result_file_sha256": V152_RESULT_SHA256,
        "v152_result_hash": V152_RESULT_HASH,
        "candidate_online_runs": 2,
        "candidate_reference_builds": 2,
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v153(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V153 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V153 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    dispatches = []
    log_root = root / "execution-logs"
    log_root.mkdir(parents=True, exist_ok=True)
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = log_root / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = log_root / f"{ordinal:02d}-{seed}.stderr.log"
        command = [
            str(PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "run",
            str(output["ready"]),
            str(output["workspace"]),
            "--run-id",
            run["run_id"],
        ]
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(f"V153 dispatch {seed} failed: {completed.returncode}")
        canonical = output["workspace"] / "canonical" / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        if not (
            attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
        ):
            raise RuntimeError(f"V153 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "exit_code": completed.returncode,
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "stdout_path": str(stdout_path),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_path": str(stderr_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_EXECUTION_V153_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": 2,
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _audit_random_prefix_window(event: Mapping[str, Any]) -> dict[str, int]:
    decision = event.get("decision")
    if not isinstance(decision, Mapping):
        raise RuntimeError("V153 decision observation is missing")
    cohort = decision.get("random_prefix_cohort")
    portfolio = decision.get("native_portfolio")
    anchor = decision.get("native_shadow_anchor")
    guard = decision.get("window_safe_guard")
    if not all(
        isinstance(item, Mapping) for item in (cohort, portfolio, anchor, guard)
    ):
        raise RuntimeError("V153 Random-prefix telemetry is incomplete")
    feasible = cohort.get("feasible_player_count")
    prefix = cohort.get("player_count")
    missing = cohort.get("missing_feasible_player_count")
    if not (
        cohort.get("enabled") is True
        and cohort.get("cohort_source") == COHORT_SOURCE
        and cohort.get("uses_completion_outcomes") is False
        and cohort.get("cohort_equals_dispatch") is True
        and isinstance(feasible, int)
        and isinstance(prefix, int)
        and isinstance(missing, int)
        and 0 <= prefix <= feasible
        and missing == feasible - prefix
        and cohort.get("dispatch_player_count") == prefix
        and cohort.get("commands_prepared") == prefix
        and portfolio.get("random_shadow_lifecycle") == RANDOM_LIFECYCLE
        and portfolio.get("random_shadow_invocations_this_window") == 1
        and portfolio.get("certificate_uses_completion_outcomes") is False
        and anchor.get("kind") == "random"
        and anchor.get("valid") is True
        and anchor.get("certificate_uses_completion_outcomes") is False
        and guard.get("certificate_uses_completion_outcomes") is False
    ):
        raise RuntimeError("V153 exact Random-prefix contract changed")
    early = cohort.get("early_stop_observed") is True
    if early and not prefix < feasible:
        raise RuntimeError("V153 early-stop prefix is not strict")
    accepted = guard.get("accepted") is True
    evaluated = guard.get("evaluated") is True
    if accepted:
        initializer_welfare = guard.get("initializer_baseline_welfare")
        proposal_welfare = guard.get("proposal_baseline_welfare")
        initializer_sum = anchor.get("initializer_readiness_service_sum")
        proposal_sum = anchor.get("proposal_readiness_service_sum")
        initializer_max = anchor.get("initializer_readiness_service_max")
        proposal_max = anchor.get("proposal_readiness_service_max")
        values = (
            initializer_welfare,
            proposal_welfare,
            initializer_sum,
            proposal_sum,
            initializer_max,
            proposal_max,
        )
        if not all(
            isinstance(value, (int, float)) and math.isfinite(value) for value in values
        ):
            raise RuntimeError("V153 accepted certificate is nonfinite")
        if not (
            anchor.get("initializer_readiness_service_complete") is True
            and anchor.get("proposal_readiness_service_complete") is True
            and anchor.get("initializer_readiness_service_players") == prefix
            and anchor.get("proposal_readiness_service_players") == prefix
            and proposal_welfare + 1e-6 >= initializer_welfare
            and proposal_max <= initializer_max + 1e-6
            and proposal_sum + 1e-6 < initializer_sum
        ):
            raise RuntimeError("V153 accepted service/welfare certificate changed")
    if accepted and not evaluated:
        raise RuntimeError("V153 unevaluated guard cannot be accepted")
    return {
        "early_stop": int(early),
        "guard_evaluated": int(evaluated),
        "guard_accepted": int(accepted),
        "prefix_players": prefix,
        "feasible_players": feasible,
    }


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    run_configs = 0
    windows = 0
    summaries = 0
    offline = 0
    not_requested = 0
    early_stop = 0
    guard_evaluated = 0
    guard_accepted = 0
    prefix_players = 0
    feasible_players = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for raw in stream:
            event = json.loads(raw)
            kind = event.get("kind")
            if kind == "run_config":
                run_configs += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("operational_direct_initialization") is True
                    and event.get("operational_unrestricted_initialization") is True
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                ):
                    raise RuntimeError("V153 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != windows:
                    raise RuntimeError("V153 window sequence changed")
                social = event.get("social", {})
                solver = event.get("solver", {})
                if social.get("reference_state_key") is None:
                    if not (
                        social.get("reference_source") == "not_requested"
                        and solver.get("termination")
                        in LEGAL_NOT_REQUESTED_TERMINATIONS
                    ):
                        raise RuntimeError(
                            "V153 reference-not-requested reason changed"
                        )
                    not_requested += 1
                elif social.get("reference_source") in {
                    "offline_table",
                    "offline_table_nonpositive",
                }:
                    offline += 1
                else:
                    raise RuntimeError("V153 offline reference replay changed")
                evidence = _audit_random_prefix_window(event)
                early_stop += evidence["early_stop"]
                guard_evaluated += evidence["guard_evaluated"]
                guard_accepted += evidence["guard_accepted"]
                prefix_players += evidence["prefix_players"]
                feasible_players += evidence["feasible_players"]
                windows += 1
            elif kind == "run_summary":
                summaries += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V153 terminal marker changed")
            elif kind != "function_profile":
                raise RuntimeError(f"unexpected V153 Nash event: {kind}")
    if (
        run_configs != 1
        or windows != 1000
        or summaries != 1
        or offline == 0
        or early_stop == 0
    ):
        raise RuntimeError("V153 log cardinality, reference, or prefix gate changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "nash_metrics_sha256": file_hash(log),
        "windows": windows,
        "offline_reference_windows": offline,
        "legitimate_not_requested_windows": not_requested,
        "early_stop_windows": early_stop,
        "guard_evaluated_windows": guard_evaluated,
        "guard_accepted_windows": guard_accepted,
        "prefix_players_total": prefix_players,
        "feasible_players_total": feasible_players,
    }


def blind_audit_v153(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V153 blind audit already exists")
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V153 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V153 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed") is True
        and pairing.get("run_count") == 2
        and pairing.get("group_count") == 2
    ):
        raise RuntimeError("V153 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_path = output["workspace"] / "ledger.jsonl"
    ledger_count, ledger_hash = verify_ledger(ledger_path)
    reference = _validate_reference_catalog(manifest, output["catalog"])
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V153 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V153 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V153 has unexplained quarantined attempts")
    audits = []
    identities = set()
    for seed in SEEDS:
        run = by_seed[seed]
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit = read_json(canonical / "manifest.json")
        software = audit.get("software_environment", {})
        identities.add(
            (
                audit.get("adapter_binary", {}).get("verified_sha256"),
                software.get("git", {}).get("commit"),
                software.get("python", {}).get("executable_sha256"),
                software.get("cargo_lock", {}).get("sha256"),
            )
        )
        audits.append(_audit_nash_log(canonical, run))
    if len(identities) != 1:
        raise RuntimeError("V153 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V153 runtime identity changed")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_BLIND_AUDIT_V153_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "performance_results_consulted_for_design": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "aggregate_runtime_breadth_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_path": str(output["pairing"]),
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "run_count": 2,
        "window_count": sum(item["windows"] for item in audits),
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": PROFILE,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _revealed_metrics(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    record_root = canonical / "reviewer_records" / run_id
    summary = read_json(record_root / "summary.json")
    fixed = summary.get("fixed_observation_window", {})
    completed = fixed.get("completed")
    throughput = fixed.get("throughput_requests_per_second")
    if not (
        isinstance(completed, int)
        and isinstance(throughput, (int, float))
        and math.isfinite(throughput)
    ):
        raise RuntimeError("V153 fixed-window metrics are invalid")
    running_tasks = []
    ready_unscheduled = []
    memory = []
    frames_path = record_root / "frames.jsonl.gz"
    with gzip.open(frames_path, "rt", encoding="utf-8") as stream:
        for raw in stream:
            event = json.loads(raw)
            running_tasks.append(float(event["running_tasks"]))
            ready_unscheduled.append(float(event["ready_unscheduled_tasks"]))
            memory.append(float(event["node_memory_utilization_mean"]))
    if len(running_tasks) != 1001:
        raise RuntimeError("V153 frame telemetry product changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "fixed_window_completed": completed,
        "fixed_window_throughput_requests_per_second": float(throughput),
        "mean_running_tasks": statistics.fmean(running_tasks),
        "mean_ready_unscheduled_tasks": statistics.fmean(ready_unscheduled),
        "mean_node_memory_utilization": statistics.fmean(memory),
    }


def reveal_v153(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V153 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V153 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("aggregate_runtime_breadth_fields_parsed") == 0
    ):
        raise RuntimeError("V153 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    source = load_and_validate_manifest(SOURCE_MANIFEST)
    candidate_by_seed = {run["seed"]: run for run in manifest["runs"]}
    random_by_seed = {
        run["seed"]: run
        for run in source["runs"]
        if run["method"] == "random"
        and run["workload"]["request_freq"] == "middle"
        and run["seed"] in SEEDS
    }
    if set(candidate_by_seed) != set(SEEDS) or set(random_by_seed) != set(SEEDS):
        raise RuntimeError("V153 reveal comparison product changed")
    comparisons = {}
    for seed in SEEDS:
        candidate_run = candidate_by_seed[seed]
        random_run = random_by_seed[seed]
        comparisons[seed] = {
            "candidate": _revealed_metrics(
                output["workspace"] / "canonical" / candidate_run["run_id"],
                candidate_run,
            ),
            "frozen_random_anchor": _revealed_metrics(
                SOURCE_WORKSPACE / "canonical" / random_run["run_id"], random_run
            ),
        }
    e17 = comparisons["E17"]["candidate"]
    e09 = comparisons["E09"]["candidate"]
    e17_gates = {
        "fixed_window_completed_at_least_28": e17["fixed_window_completed"] >= 28,
        "fixed_window_throughput_at_least_28": (
            e17["fixed_window_throughput_requests_per_second"] >= 28.0
        ),
    }
    e09_gates = {
        "fixed_window_completed_strictly_positive": e09["fixed_window_completed"] > 0,
        "fixed_window_throughput_at_least_923": (
            e09["fixed_window_throughput_requests_per_second"] >= 923.0
        ),
    }
    joint_pass = all(e17_gates.values()) and all(e09_gates.values())
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_DIAGNOSTIC_RESULT_V153_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_hash": blind_hash,
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "candidate_run_count": 2,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "comparisons": comparisons,
        "E17_gates": e17_gates,
        "E09_gates": e09_gates,
        "joint_mechanism_gate_pass": joint_pass,
        "disposition": (
            "eligible_only_for_separately_preregistered_complete_middle_E01_E20_training_block"
            if joint_pass
            else "retain_both_runs_and_retire_random_prefix_mechanism_without_threshold_tuning"
        ),
        "full_middle_training_inputs_generated": False,
        "fresh_confirmation_inputs_opened": False,
        "homogeneous_claim_closed": False,
        "later_experiment_execution_authorized": False,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("prepare", "execute", "blind-audit", "reveal")
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    if action == "prepare":
        document = prepare_v153()
        key = "receipt_hash"
    elif action == "execute":
        document = execute_v153()
        key = "receipt_hash"
    elif action == "blind-audit":
        document = blind_audit_v153()
        key = "blind_audit_hash"
    else:
        document = reveal_v153()
        key = "result_hash"
    print(json.dumps({key: document[key], "runs": 2}))


if __name__ == "__main__":
    main()
