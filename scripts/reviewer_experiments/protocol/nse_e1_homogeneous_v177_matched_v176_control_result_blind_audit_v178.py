from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v176 as v176,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_severe_queue32_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v177 as v177,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_queue8_low_training_v155 as v155base,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    _evaluate_load,
    _load_baselines,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    PYTHON_PATH,
    PYTHON_SHA256,
    _assert_file,
    _assert_hashed,
    _validate_reference_catalog,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_legacy_profile_training_prepare_v150 import (
    COMMON_ENVIRONMENT,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_queue8_low_training_v155 import (
    CARGO_LOCK_SHA256,
    MODULE_CONF_SEMANTIC_HASH,
    _assert_json_semantic,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import (
    load_and_validate_manifest,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path(
    "tmp/nse_e1_homogeneous_v177_matched_v176_control_result_blind_audit_20260901_v178"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_v177_matched_v176_control_result_blind_audit_plan_v178.json"
)
PLAN_SHA256 = "8b17d6393fb63d982204239965edc5576fce6b07efa86d4cad248ec859c4be1a"
V177_FAILURE = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_severe_queue32_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_failure_v177.json"
)
V177_FAILURE_SHA256 = "03e6678a88fc46845efdd0260d7fab4de156138e7d8ed1361b8cd56a143faacc"
V177_FAILURE_HASH = "81304704bff6ef7328d883f809051956b2f8e5945436bc19362916008e13af14"
CONTROL_SEEDS = ("E06", "E11", "E12", "E15", "E18")
MATCHED_SEEDS = v177.SEEDS
REUSED_CONTROL_SEED = "E10"
ARM_ID = "v178-low-matched-v176-concurrent2-cpu-bounded-terminal-control"
PROFILE = v176.PROFILE
FRONTIER = v176.FRONTIER
PORT = v176.PORT
BINARY_PATH = v176.BINARY_PATH
BINARY_SHA256 = v176.BINARY_SHA256
BINARY_SOURCE_COMMIT = v176.BINARY_SOURCE_COMMIT
V176_E10_RUN_ID = "E1.sche_nash.low.homogeneous.n20.E10.1db84dd7e7d81aa4"
V176_E10_RUN_SPEC_HASH = (
    "2e0d1dd3d60890412e9ab0d7a7fcfcaeecda382f6bf49cbbde8d2b61b4b33a98"
)
V176_E10_NASH_SHA256 = (
    "980afb572ba83018554594a53d6404c7baa0a10168caff955a61dabf8d60ba3c"
)


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v178.json",
        "schedule": root / "frozen-control-order-v178.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "control-runs",
        "execution": root / "control-execution-receipt-v178.json",
        "pairing": root / "control-pairing-audit-v178.json",
        "blind": root / "matched-control-blind-audit-v178.json",
        "result": root / "diagnostic-result-v178.json",
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    source = v177._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V178 matched-control plan"),
        (V177_FAILURE, V177_FAILURE_SHA256, "V177 result-blind failure receipt"),
        (BINARY_PATH, BINARY_SHA256, "frozen V176 release binary"),
        (
            v176.paths()["ready"],
            "692b5071a3aba324cfb6ee518635c07f52ca8c750e022cf7ae964b0eb457b7bc",
            "frozen V176 ready manifest",
        ),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    failure = read_json(V177_FAILURE)
    if not (
        _assert_hashed(failure, "receipt_hash", "V177 result-blind failure receipt")
        == V177_FAILURE_HASH
        and failure.get("performance_reveal_performed") is False
        and failure.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and failure.get("disposition", {}).get("retain_all_six_valid_v177_runs") is True
        and failure.get("disposition", {}).get("v177_performance_reveal_authorized")
        is False
        and failure.get("disposition", {}).get(
            "new_preregistered_matched_v176_control_replication_required"
        )
        is True
    ):
        raise RuntimeError("V177 frozen result-blind failure boundary changed")
    v176_manifest = load_and_validate_manifest(v176.paths()["ready"])
    run = next(
        (
            item
            for item in v176_manifest["runs"]
            if item.get("seed") == REUSED_CONTROL_SEED
        ),
        None,
    )
    if not (
        v176_manifest.get("manifest_hash")
        == "f0d817861a96a62ebe5866e30529c794b10a63af81198ad48f5537489b98a7a8"
        and run is not None
        and run.get("run_id") == V176_E10_RUN_ID
        and run.get("run_spec_hash") == V176_E10_RUN_SPEC_HASH
    ):
        raise RuntimeError("frozen V176 E10 control changed")
    canonical = v176.paths()["workspace"] / "canonical" / V176_E10_RUN_ID
    validate_canonical_run(
        run,
        canonical,
        expected_manifest_hash=v176_manifest["manifest_hash"],
        result_relative_path="reviewer_records/{run_id}/summary.json",
    )
    _assert_file(
        canonical / "reviewer_records" / V176_E10_RUN_ID / "nash_metrics.jsonl.gz",
        V176_E10_NASH_SHA256,
        "frozen V176 E10 Nash telemetry",
    )
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    return source


def _metadata(protocol_source_commit: str, source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "v178_training_only": True,
        "v178_role": "result_blind_matched_v176_control",
        "v178_plan_sha256": PLAN_SHA256,
        "v178_protocol_source_commit": protocol_source_commit,
        "v178_binary_source_commit": BINARY_SOURCE_COMMIT,
        "v178_binary_sha256": BINARY_SHA256,
        "v178_profile": PROFILE,
        "v178_player_frontier": FRONTIER,
        "v178_control_for_profile": v177.PROFILE,
        "v178_performance_fields_to_parse": 0,
        "v178_source_e1_run_id": source.get("v155_source_e1_run_id"),
        "v178_source_e1_run_spec_hash": source.get("v155_source_e1_run_spec_hash"),
        "v178_candidate_rerun": False,
    }


def _rewrite_control(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    rewritten = v155base._rewrite_candidate(source, protocol_source_commit)
    by_seed = {run["seed"]: run for run in rewritten["runs"]}
    if set(by_seed) != {f"E{index:02d}" for index in range(1, 21)}:
        raise RuntimeError("V155 complete low source product changed")
    rewritten["runs"] = [by_seed[seed] for seed in CONTROL_SEEDS]
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    lineage = {item["source_seed"]: item for item in marker["selected_source_runs"]}
    marker["selected_source_runs"] = [lineage[seed] for seed in CONTROL_SEEDS]
    for key in list(marker):
        if key.startswith("v155_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": "V178 result-blind matched V176 controls; no performance interpretation",
            "v178_role": "result_blind_matched_v176_control",
            "v178_plan_sha256": PLAN_SHA256,
            "v178_protocol_source_commit": protocol_source_commit,
            "v178_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v178_binary_sha256": BINARY_SHA256,
            "v178_profile": PROFILE,
            "v178_player_frontier": FRONTIER,
            "v178_control_for_profile": v177.PROFILE,
            "v178_expected_run_count": len(CONTROL_SEEDS),
            "v178_expected_reference_build_count": len(CONTROL_SEEDS),
            "v178_fixed_order": list(CONTROL_SEEDS),
            "v178_performance_fields_to_parse": 0,
            "v178_candidate_rerun": False,
            "v178_environment": COMMON_ENVIRONMENT,
        }
    )
    for run in rewritten["runs"]:
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = _metadata(protocol_source_commit, run.get("metadata", {}))
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
    marker["selected_run_count"] = len(CONTROL_SEEDS)
    marker["selected_reference_build_count"] = len(CONTROL_SEEDS)
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == len(CONTROL_SEEDS)
        and [run["seed"] for run in manifest["runs"]] == list(CONTROL_SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and len(manifest.get("reference_build_dependencies", [])) == len(CONTROL_SEEDS)
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V178 exact five-control product changed")
    expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and all(
                run["environment"].get(key) == value for key, value in expected.items()
            )
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v178_profile") == PROFILE
            and metadata.get("v178_player_frontier") == FRONTIER
            and metadata.get("v178_control_for_profile") == v177.PROFILE
            and metadata.get("v178_performance_fields_to_parse") == 0
            and metadata.get("v178_candidate_rerun") is False
        ):
            raise RuntimeError(f"V178 control contract changed: {run.get('run_id')}")


def prepare_v178(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V178 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_control(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_MATCHED_V176_CONTROL_SCHEDULE_V178_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(CONTROL_SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_MATCHED_V176_CONTROL_PREPARED_V178_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "performance_fields_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "binary_source_commit": BINARY_SOURCE_COMMIT,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": MODULE_CONF_SEMANTIC_HASH,
        "v177_failure_file_sha256": V177_FAILURE_SHA256,
        "v177_failure_hash": V177_FAILURE_HASH,
        "new_control_online_runs": len(CONTROL_SEEDS),
        "new_control_reference_builds": len(CONTROL_SEEDS),
        "reused_v176_e10_control_runs": 1,
        "v177_candidate_reruns": 0,
        "fixed_order": list(CONTROL_SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "player_frontier": FRONTIER,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v178(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V178 control execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V178 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    logs = root / "execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
    dispatches = []
    for ordinal, seed in enumerate(CONTROL_SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = logs / f"{ordinal:02d}-{seed}.stderr.log"
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
            raise RuntimeError(
                f"V178 control dispatch {seed} failed: {completed.returncode}"
            )
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
            raise RuntimeError(f"V178 control is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_MATCHED_V176_CONTROL_EXECUTION_V178_V1",
        "created_at": utc_now(),
        "performance_fields_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(CONTROL_SEEDS),
        "dispatch_count": len(CONTROL_SEEDS),
        "v177_candidate_reruns": 0,
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _assignment_hashes(canonical: Path, run_id: str) -> tuple[int, ...]:
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    values: list[int] = []
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("kind") != "window":
                continue
            value = event.get("decision", {}).get("assignment_hash")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise RuntimeError("matched-control assignment hash changed")
            values.append(value)
    if len(values) != 1000:
        raise RuntimeError("matched-control assignment cardinality changed")
    return tuple(values)


def _assignment_sequence_sha256(values: Sequence[int]) -> str:
    return hashlib.sha256("\n".join(map(str, values)).encode("utf-8")).hexdigest()


def _compare_sequences(
    candidate: Sequence[int], control: Sequence[int], first_severe_frame: int
) -> dict[str, Any]:
    if len(candidate) != 1000 or len(control) != 1000:
        raise RuntimeError("matched-control sequence cardinality changed")
    if not 0 <= first_severe_frame < 1000:
        raise RuntimeError("matched-control severe frame changed")
    mismatch = next(
        (
            index
            for index, pair in enumerate(zip(candidate, control))
            if pair[0] != pair[1]
        ),
        None,
    )
    prefix_matches = tuple(candidate[:first_severe_frame]) == tuple(
        control[:first_severe_frame]
    )
    severe_differs = candidate[first_severe_frame] != control[first_severe_frame]
    return {
        "first_assignment_mismatch_frame": mismatch,
        "pre_first_severe_assignment_prefix_matches": prefix_matches,
        "first_severe_assignment_differs": severe_differs,
        "first_mismatch_is_first_severe": mismatch == first_severe_frame,
        "candidate_assignment_sequence_sha256": _assignment_sequence_sha256(candidate),
        "control_assignment_sequence_sha256": _assignment_sequence_sha256(control),
        "pass": prefix_matches and severe_differs and mismatch == first_severe_frame,
    }


def _assert_matched_inputs(
    candidate: Mapping[str, Any], control: Mapping[str, Any]
) -> None:
    for key in (
        "seed",
        "cell_id",
        "workload_spec_hash",
        "cluster",
        "simulation",
        "common_hpa_hash",
    ):
        if candidate.get(key) != control.get(key):
            raise RuntimeError(f"V178 candidate/control input mismatch: {key}")
    candidate_tape = candidate.get("workload_tape", {})
    control_tape = control.get("workload_tape", {})
    for key in ("sha256", "receipt_sha256", "event_count", "seed"):
        if candidate_tape.get(key) != control_tape.get(key):
            raise RuntimeError(f"V178 candidate/control tape mismatch: {key}")


def blind_audit_v178(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V178 matched-control blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V178 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V178 execution receipt")
    control_manifest = load_and_validate_manifest(output["ready"])
    _validate_product(control_manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        control_manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed")
        and pairing.get("run_count") == len(CONTROL_SEEDS)
        and pairing.get("group_count") == len(CONTROL_SEEDS)
    ):
        raise RuntimeError("V178 exact control pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        control_manifest, output["catalog"], expected_entry_count=len(CONTROL_SEEDS)
    )
    if [item["seed"] for item in execution["dispatches"]] != list(CONTROL_SEEDS):
        raise RuntimeError("V178 control execution order changed")

    candidate_manifest = load_and_validate_manifest(v177.paths()["ready"])
    v177._validate_product(candidate_manifest, references_bound=True)
    candidate_pairing = audit_manifest_pairing(
        candidate_manifest,
        v177.paths()["workspace"],
        expected_methods={"*": ["sche_nash"]},
    )
    if not (
        candidate_pairing.get("passed")
        and candidate_pairing.get("run_count") == len(MATCHED_SEEDS)
        and candidate_pairing.get("group_count") == len(MATCHED_SEEDS)
    ):
        raise RuntimeError("frozen V177 candidate pairing changed")

    v176_manifest = load_and_validate_manifest(v176.paths()["ready"])
    controls = {run["seed"]: run for run in control_manifest["runs"]}
    controls[REUSED_CONTROL_SEED] = next(
        run for run in v176_manifest["runs"] if run["seed"] == REUSED_CONTROL_SEED
    )
    candidates = {run["seed"]: run for run in candidate_manifest["runs"]}
    if set(controls) != set(MATCHED_SEEDS) or set(candidates) != set(MATCHED_SEEDS):
        raise RuntimeError("V178 matched seed product changed")

    matched_evidence: dict[str, Any] = {}
    candidate_audits: list[dict[str, Any]] = []
    control_identities: set[tuple[Any, ...]] = set()
    for seed in MATCHED_SEEDS:
        candidate_run = candidates[seed]
        control_run = controls[seed]
        _assert_matched_inputs(candidate_run, control_run)
        candidate_canonical = (
            v177.paths()["workspace"] / "canonical" / candidate_run["run_id"]
        )
        validate_canonical_run(
            candidate_run,
            candidate_canonical,
            expected_manifest_hash=candidate_manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        candidate_audit = v177._audit_nash_log(
            candidate_canonical, candidate_run, frozen_base=None
        )
        first_severe = candidate_audit["first_severe_exact_one_frame"]
        if first_severe is None:
            raise RuntimeError(f"V177 candidate did not exercise severe-single: {seed}")

        if seed == REUSED_CONTROL_SEED:
            control_canonical = (
                v176.paths()["workspace"] / "canonical" / control_run["run_id"]
            )
            control_manifest_hash = v176_manifest["manifest_hash"]
        else:
            control_canonical = (
                output["workspace"] / "canonical" / control_run["run_id"]
            )
            control_manifest_hash = control_manifest["manifest_hash"]
        validate_canonical_run(
            control_run,
            control_canonical,
            expected_manifest_hash=control_manifest_hash,
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        v176._audit_nash_log(control_canonical, control_run, frozen_v170=None)
        control_manifest_json = read_json(control_canonical / "manifest.json")
        software = control_manifest_json.get("software_environment", {})
        control_identities.add(
            (
                control_manifest_json.get("adapter_binary", {}).get("verified_sha256"),
                software.get("python", {}).get("executable_sha256"),
                software.get("cargo_lock", {}).get("sha256"),
            )
        )
        candidate_sequence = _assignment_hashes(
            candidate_canonical, candidate_run["run_id"]
        )
        control_sequence = _assignment_hashes(control_canonical, control_run["run_id"])
        comparison = _compare_sequences(
            candidate_sequence, control_sequence, first_severe
        )
        matched_evidence[seed] = {
            "candidate_run_id": candidate_run["run_id"],
            "control_run_id": control_run["run_id"],
            "control_source": "frozen_v176_e10"
            if seed == REUSED_CONTROL_SEED
            else "new_v178_control",
            "first_severe_exact_one_frame": first_severe,
            **comparison,
        }
        candidate_audit = dict(candidate_audit)
        candidate_audit["frozen_base_assignment_sequence_sha256"] = comparison[
            "control_assignment_sequence_sha256"
        ]
        candidate_audit["assignment_mismatch_count_vs_base"] = sum(
            current != frozen
            for current, frozen in zip(candidate_sequence, control_sequence)
        )
        candidate_audit["first_assignment_mismatch_frame_vs_base"] = comparison[
            "first_assignment_mismatch_frame"
        ]
        candidate_audit[
            "pre_first_severe_exact_one_assignment_prefix_matches_base"
        ] = comparison["pre_first_severe_assignment_prefix_matches"]
        candidate_audit[
            "first_severe_exact_one_frame_assignment_differs_from_base"
        ] = comparison["first_severe_assignment_differs"]
        candidate_audits.append(candidate_audit)

    mechanism = v177._mechanism_falsification_gate(candidate_audits)
    matched_pass = all(item["pass"] for item in matched_evidence.values())
    expected_identity = (BINARY_SHA256, PYTHON_SHA256, CARGO_LOCK_SHA256)
    identity_pass = control_identities == {expected_identity}
    passed = matched_pass and identity_pass and mechanism["pass"]
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_MATCHED_V176_CONTROL_BLIND_AUDIT_V178_V1",
        "created_at": utc_now(),
        "status": "pass" if passed else "fail",
        "performance_reveal_authorized": passed,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "aggregate_runtime_breadth_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "v177_failure_file_sha256": V177_FAILURE_SHA256,
        "v177_failure_hash": V177_FAILURE_HASH,
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "control_ready_manifest_hash": control_manifest["manifest_hash"],
        "control_reference_catalog": reference,
        "control_ledger_event_count": ledger_count,
        "control_ledger_last_hash": ledger_hash,
        "control_pairing_audit_file_sha256": file_hash(output["pairing"]),
        "control_pairing_passed": True,
        "candidate_pairing_passed": True,
        "new_control_run_count": len(CONTROL_SEEDS),
        "reused_control_run_count": 1,
        "candidate_rerun_count": 0,
        "matched_seed_count": len(MATCHED_SEEDS),
        "matched_sequence_gate_pass": matched_pass,
        "control_runtime_identity_pass": identity_pass,
        "matched_per_seed_evidence": matched_evidence,
        "mechanism_gate": mechanism,
        "pass": passed,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def reveal_v178(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V178 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V178 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("matched_sequence_gate_pass") is True
        and blind.get("control_runtime_identity_pass") is True
        and blind.get("mechanism_gate", {}).get("pass") is True
        and blind.get("pass") is True
    ):
        raise RuntimeError("V178 blind audit did not authorize reveal")
    candidate_manifest = load_and_validate_manifest(v177.paths()["ready"])
    candidate = v177._load_candidate(candidate_manifest, v177.ROOT)
    v170_rows = v177.v175._load_v170_candidate()
    v176_manifest = load_and_validate_manifest(v176.paths()["ready"])
    v176_rows = v176._load_candidate(v176_manifest, v176.ROOT)
    hybrid = v177._hybrid_rows(v170_rows, v176_rows, candidate)
    evaluation = _evaluate_load("low", hybrid, _load_baselines())
    throughput_sum = sum(float(row["throughput"]) for row in candidate)
    qpr_values = [float(row["qpr_finite_only"]) for row in candidate]
    qpr_sum = sum(qpr_values)
    throughput_wins = sum(
        row["difference"] > 0
        for row in evaluation["gates"]["throughput"]["paired_rows"]
        if row["seed"] in MATCHED_SEEDS
    )
    qpr_wins = sum(
        row["difference"] > 0
        for row in evaluation["gates"]["qpr_finite_only"]["paired_rows"]
        if row["seed"] in MATCHED_SEEDS
    )
    diagnostic = {
        "throughput_six_seed_sum": throughput_sum,
        "throughput_six_seed_sum_pass": throughput_sum
        > v177.THROUGHPUT_SIX_SEED_SUM_GATE,
        "throughput_six_seed_paired_wins": throughput_wins,
        "throughput_six_seed_paired_wins_pass": throughput_wins
        >= v177.THROUGHPUT_SIX_SEED_PAIRED_WIN_GATE,
        "qpr_six_seed_sum": qpr_sum,
        "qpr_six_seed_sum_pass": qpr_sum > v177.QPR_SIX_SEED_SUM_GATE,
        "qpr_six_seed_paired_wins": qpr_wins,
        "qpr_six_seed_paired_wins_pass": qpr_wins >= v177.QPR_SIX_SEED_PAIRED_WIN_GATE,
        "qpr_six_seed_all_finite": all(math.isfinite(value) for value in qpr_values),
    }
    passed = (
        evaluation["all_three_metric_gates_pass"]
        and diagnostic["throughput_six_seed_sum_pass"]
        and diagnostic["throughput_six_seed_paired_wins_pass"]
        and diagnostic["qpr_six_seed_sum_pass"]
        and diagnostic["qpr_six_seed_paired_wins_pass"]
        and diagnostic["qpr_six_seed_all_finite"]
    )
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_V177_MATCHED_V176_CONTROL_DIAGNOSTIC_RESULT_V178_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "new_control_run_count": len(CONTROL_SEEDS),
        "reused_control_run_count": 1,
        "v177_candidate_rerun_count": 0,
        "reused_v177_candidate_run_count": len(MATCHED_SEEDS),
        "reused_v176_candidate_run_count": len(v177.V176_REUSE_SEEDS),
        "reused_v170_candidate_run_count": len(v177.V170_REUSE_SEEDS),
        "reused_frozen_baseline_run_count": 180,
        "baseline_rerun_count": 0,
        "profile": v177.PROFILE,
        "hybrid_low_evaluation": evaluation,
        "diagnostic_six_seed_gates": diagnostic,
        "matched_control_mechanism_gate": blind["mechanism_gate"],
        "joint_diagnostic_pass": passed,
        "disposition": (
            "authorize_separately_committed_remaining_nine_V177_confirmation_plan_without_rerunning_existing_candidate_or_control_runs"
            if passed
            else "retain_all_valid_V176_controls_and_V177_candidates_and_retire_V177"
        ),
        "remaining_nine_training_runs": list(v177.V170_REUSE_SEEDS),
        "remaining_nine_training_runs_authorized": passed,
        "confirmation_inputs_generated": False,
        "homogeneous_low_claim_closed": False,
        "middle_or_later_execution_authorized": False,
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
        document, key = prepare_v178(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v178(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v178(), "blind_audit_hash"
    else:
        document, key = reveal_v178(), "result_hash"
    print(json.dumps({key: document[key], "new_controls": len(CONTROL_SEEDS)}))


if __name__ == "__main__":
    main()
