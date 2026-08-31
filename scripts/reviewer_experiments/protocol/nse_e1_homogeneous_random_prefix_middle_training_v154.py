from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    _evaluate_load,
    _load_baselines,
    _metrics,
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
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_random_prefix_diagnostic_v153 import (
    COMMON_ENVIRONMENT,
    PROFILE,
    _audit_nash_log,
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


ROOT = Path("tmp/nse_e1_homogeneous_random_prefix_middle_training_20260831_v154")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_random_prefix_middle_training_plan_v154.json"
)
PLAN_SHA256 = "a120650ba56fcc9bdf421e823f66c4ff6f4218177337d303a515ef24cdadd02b"
V153_ROOT = Path("tmp/nse_e1_homogeneous_random_prefix_diagnostic_20260831_v153")
V153_RESULT = V153_ROOT / "diagnostic-result-v153.json"
V153_RESULT_SHA256 = "82e9b024a0745d499cfa191af47046207859fbfdb97ad9fdcccb70ad1a236b96"
V153_RESULT_HASH = "cbc9b3fa3717e16018a7c72f94cb01117a4666d3ff9a48016dd4faa54f739cc9"
V153_BLIND = V153_ROOT / "joint-blind-audit-v153.json"
V153_BLIND_SHA256 = "d233d9e81aacbc4b8546579bd66f7ae8a331b7b06fcb483f4653dff79498db19"
V153_BLIND_HASH = "acf7273a5fc74e738283411f3c1beb6ef60d4428a5080381a564c10ef71760b0"

ARM_ID = "v154-middle-exact-random-prefix-service-safe-nash"
SEEDS = tuple(f"E{index:02d}" for index in range(1, 21))
PORT = "3205"
SOURCE_WORKSPACE = SOURCE_MANIFEST.parent / "formal-runs"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v154.json",
        "schedule": root / "frozen-run-order-v154.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v154.json",
        "pairing": root / "pairing-audit-v154.json",
        "blind": root / "joint-blind-audit-v154.json",
        "result": root / "training-result-v154.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V154 plan"),
        (SOURCE_MANIFEST, SOURCE_MANIFEST_SHA256, "frozen E1 manifest"),
        (SOURCE_PAIRING, SOURCE_PAIRING_SHA256, "frozen E1 pairing"),
        (V153_RESULT, V153_RESULT_SHA256, "V153 result"),
        (V153_BLIND, V153_BLIND_SHA256, "V153 blind audit"),
        (BINARY_PATH, BINARY_SHA256, "V154 release binary"),
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
    v153 = read_json(V153_RESULT)
    blind = read_json(V153_BLIND)
    if not (
        _assert_hashed(v153, "result_hash", "V153 result") == V153_RESULT_HASH
        and v153.get("joint_mechanism_gate_pass") is True
        and v153.get("candidate_run_count") == 2
        and v153.get("fresh_confirmation_inputs_opened") is False
        and _assert_hashed(blind, "blind_audit_hash", "V153 blind audit")
        == V153_BLIND_HASH
        and blind.get("status") == "pass"
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
    ):
        raise RuntimeError("V153 qualification boundary changed")
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V154 protocol source commit is invalid")
    selected = [
        run
        for run in source["runs"]
        if run.get("method") == "sche_nash"
        and run.get("seed") in SEEDS
        and run.get("workload", {}).get("request_freq") == "middle"
        and run.get("cluster") == {"node_count": 20, "topology": "homogeneous"}
    ]
    if len(selected) != 20 or {run["seed"] for run in selected} != set(SEEDS):
        raise RuntimeError("frozen source no longer has the V154 middle product")
    by_seed = {run["seed"]: run for run in selected}
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        [by_seed[seed]["run_id"] for seed in SEEDS],
        purpose=(
            "V154 adaptive complete middle E01-E20 exact-Random-prefix training; "
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
                "V154 adaptive complete middle E01-E20 exact-Random-prefix training; "
                "never a formal result or paper superiority claim"
            ),
            "v154_role": "result_blind_complete_middle_training",
            "v154_plan_sha256": PLAN_SHA256,
            "v154_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v154_protocol_source_commit": protocol_source_commit,
            "v154_binary_sha256": BINARY_SHA256,
            "v154_arm_id": ARM_ID,
            "v154_profile": PROFILE,
            "v154_environment": COMMON_ENVIRONMENT,
            "v154_expected_run_count": 20,
            "v154_expected_reference_build_count": 20,
            "v154_fixed_order": list(SEEDS),
            "v154_candidate_performance_summaries_parsed": 0,
            "v154_confirmation_inputs_generated": False,
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
            "v154_training_only": True,
            "v154_role": "result_blind_complete_middle_training",
            "v154_plan_sha256": PLAN_SHA256,
            "v154_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v154_protocol_source_commit": protocol_source_commit,
            "v154_binary_sha256": BINARY_SHA256,
            "v154_arm_id": ARM_ID,
            "v154_profile": PROFILE,
            "v154_source_e1_run_id": source_run_id,
            "v154_source_e1_run_spec_hash": source_run_spec_hash,
            "v154_exact_random_prefix_cohort": True,
            "v154_numeric_hyperparameters_added_after_v153": 0,
            "v154_candidate_performance_summaries_parsed_before_run": 0,
            "v154_confirmation_inputs_generated": False,
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
    marker["selected_run_count"] = 20
    marker["selected_reference_build_count"] = 20
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == 20
        and {run["seed"] for run in manifest["runs"]} == set(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and {
            (run["workload"]["request_freq"], run["cluster"]["node_count"])
            for run in manifest["runs"]
        }
        == {("middle", 20)}
        and len(manifest.get("reference_build_dependencies", [])) == 20
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V154 exact middle E01-E20 product changed")
    expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        if (
            run["experiment_id"] != "E1"
            or run["cluster"]["topology"] != "homogeneous"
            or any(
                run["environment"].get(key) != value for key, value in expected.items()
            )
            or run.get("metadata", {}).get("v154_profile") != PROFILE
        ):
            raise RuntimeError(f"V154 run contract changed: {run.get('run_id')}")


def prepare_v154(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V154 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_MIDDLE_SCHEDULE_V154_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [
            next(run["run_id"] for run in manifest["runs"] if run["seed"] == seed)
            for seed in SEEDS
        ],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_MIDDLE_PREPARED_V154_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
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
        "v153_result_file_sha256": V153_RESULT_SHA256,
        "v153_result_hash": V153_RESULT_HASH,
        "candidate_online_runs": 20,
        "candidate_reference_builds": 20,
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


def execute_v154(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V154 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V154 prepared receipt")
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
            raise RuntimeError(f"V154 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V154 canonical is not a QC pass: {run['run_id']}")
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
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_MIDDLE_EXECUTION_V154_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": 20,
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def blind_audit_v154(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V154 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V154 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V154 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed") is True
        and pairing.get("run_count") == 20
        and pairing.get("group_count") == 20
    ):
        raise RuntimeError("V154 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=20
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V154 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V154 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V154 has unexplained quarantined attempts")
    by_seed = {run["seed"]: run for run in manifest["runs"]}
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
        raise RuntimeError("V154 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V154 runtime identity changed")
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_MIDDLE_BLIND_AUDIT_V154_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
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
        "run_count": 20,
        "window_count": sum(item["windows"] for item in audits),
        "guard_accepted_window_count": sum(
            item["guard_accepted_windows"] for item in audits
        ),
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


def _load_candidate(
    manifest: Mapping[str, Any], root: Path = ROOT
) -> list[dict[str, Any]]:
    rows = []
    for run in manifest["runs"]:
        summary_path = (
            paths(root)["workspace"]
            / "canonical"
            / run["run_id"]
            / "reviewer_records"
            / run["run_id"]
            / "summary.json"
        )
        values = _nse_summary_metrics(read_json(summary_path))
        rows.append(
            {
                "load": "middle",
                "seed": run["seed"],
                "run_id": run["run_id"],
                **_metrics(
                    values.get("throughput"),
                    values.get("latency_mean_ms"),
                    values.get("cost"),
                    values.get("completed"),
                ),
            }
        )
    if len(rows) != 20 or {row["seed"] for row in rows} != set(SEEDS):
        raise RuntimeError("V154 candidate result product changed")
    return rows


def _random_differences(
    candidate: Sequence[Mapping[str, Any]], baselines: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    random_by_seed = {
        row["seed"]: row
        for row in baselines
        if row["load"] == "middle" and row["algorithm"] == "Random"
    }
    candidate_by_seed = {row["seed"]: row for row in candidate}
    rows = []
    for seed in SEEDS:
        payload: dict[str, Any] = {"seed": seed, "metrics": {}}
        differs = False
        for metric in (
            "throughput",
            "qpr_finite_only",
            "qpr_zero_completed_as_zero",
        ):
            left = candidate_by_seed[seed].get(metric)
            right = random_by_seed[seed].get(metric)
            difference = None if left is None or right is None else left - right
            if difference is not None and difference != 0.0:
                differs = True
            payload["metrics"][metric] = {
                "candidate": left,
                "random": right,
                "difference": difference,
            }
        payload["any_primary_metric_differs"] = differs
        rows.append(payload)
    return rows


def reveal_v154(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V154 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V154 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("aggregate_runtime_breadth_fields_parsed") == 0
    ):
        raise RuntimeError("V154 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = _load_candidate(manifest, root)
    baselines = _load_baselines()
    evaluation = _evaluate_load("middle", candidate, baselines)
    random_differences = _random_differences(candidate, baselines)
    mechanism_gate = {
        "accepted_nash_proposal_window_count": blind["guard_accepted_window_count"],
        "accepted_nash_proposal_exists": blind["guard_accepted_window_count"] > 0,
        "runs_differing_from_exact_random_in_primary_metric": sum(
            row["any_primary_metric_differs"] for row in random_differences
        ),
        "at_least_one_run_differs_from_exact_random": any(
            row["any_primary_metric_differs"] for row in random_differences
        ),
        "per_seed_random_differences": random_differences,
    }
    mechanism_gate["pass"] = (
        mechanism_gate["accepted_nash_proposal_exists"]
        and mechanism_gate["at_least_one_run_differs_from_exact_random"]
    )
    passed = evaluation["all_three_metric_gates_pass"] and mechanism_gate["pass"]
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_RANDOM_PREFIX_MIDDLE_TRAINING_RESULT_V154_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "candidate_run_count": 20,
        "reused_frozen_baseline_run_count": 180,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "middle_evaluation": evaluation,
        "mechanism_gate": mechanism_gate,
        "joint_training_pass": passed,
        "disposition": (
            "training_pass_requires_separate_confirmation_plan_and_unopened_inputs"
            if passed
            else "retain_all_v154_runs_and_retire_profile_without_confirmation_inputs_or_threshold_tuning"
        ),
        "confirmation_inputs_generated": False,
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
        document = prepare_v154()
        key = "receipt_hash"
    elif action == "execute":
        document = execute_v154()
        key = "receipt_hash"
    elif action == "blind-audit":
        document = blind_audit_v154()
        key = "blind_audit_hash"
    else:
        document = reveal_v154()
        key = "result_hash"
    print(json.dumps({key: document[key], "runs": 20}))


if __name__ == "__main__":
    main()
