from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

from .faasrank_model import (
    CALIBRATION_RESULTS_SCHEMA,
    FaaSRankCalibrationPlan,
    load_faasrank_calibration_plan,
)
from .process_monitor import available as process_monitor_available
from .process_monitor import run_monitored
from .schema import ProtocolValidationError, load_and_validate_manifest
from .tape import inspect_tape
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


class FaaSRankCalibrationStageError(ProtocolValidationError):
    pass


def _evaluation_tape_hashes(manifest: dict[str, Any]) -> set[str]:
    hashes: set[str] = set()
    for run in manifest["runs"]:
        value = run.get("workload_tape", {}).get("sha256")
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise FaaSRankCalibrationStageError(
                "bind every formal evaluation tape before FaaSRank calibration"
            )
        hashes.add(value)
    return hashes


def _format_command(template: list[str], variables: dict[str, str]) -> list[str]:
    try:
        return [part.format_map(variables) for part in template]
    except KeyError as exc:
        raise FaaSRankCalibrationStageError(
            f"unknown command template variable: {exc}"
        ) from exc


def _execution_cwd(manifest: dict[str, Any]) -> Path:
    setting = Path(manifest["execution"].get("cwd", "."))
    return setting.resolve()


def _template(
    manifest: dict[str, Any], *, method: str, seed: str, load: str
) -> dict[str, Any]:
    matches = [
        run
        for run in manifest["runs"]
        if run["experiment_id"] == "E1"
        and run["method"] == method
        and run["seed"] == seed
        and run["workload"]["request_freq"] == load
        and run["cluster"]["topology"] == "homogeneous"
    ]
    if len(matches) != 1:
        raise FaaSRankCalibrationStageError(
            f"expected one E1 {method}/{seed}/{load}/homogeneous template, found {len(matches)}"
        )
    return matches[0]


def _stage_environment(
    run: dict[str, Any],
    attempt_dir: Path,
    run_config_path: Path,
    result_path: Path,
    attempt: int,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(run.get("environment", {}))
    environment.update(
        {
            "PROTOCOL_RUN_ID": run["run_id"],
            "PROTOCOL_SEED": run["seed"],
            "PROTOCOL_ATTEMPT": str(attempt),
            "PROTOCOL_RUN_CONFIG": str(run_config_path.resolve()),
            "PROTOCOL_PARTIAL_DIR": str(attempt_dir.resolve()),
            "PROTOCOL_RESULT_PATH": str(result_path.resolve()),
            "PROTOCOL_REVIEWER_RECORD_ROOT": str(
                (attempt_dir / "reviewer_records").resolve()
            ),
        }
    )
    return environment


def _run_adapter_attempt(
    manifest: dict[str, Any],
    root: Path,
    run: dict[str, Any],
    spec_sha256: str,
    *,
    extra_validator: Any,
) -> Path:
    key = run["run_id"]
    canonical = root / "canonical" / key
    if canonical.is_dir():
        receipt = read_json(canonical / "stage_receipt.json")
        if (
            not isinstance(receipt, dict)
            or receipt.get("spec_sha256") != spec_sha256
            or receipt.get("run_id") != key
        ):
            raise FaaSRankCalibrationStageError(
                f"existing canonical calibration run conflicts with the frozen spec: {canonical}"
            )
        extra_validator(canonical, run)
        return canonical

    for attempt in range(1, 4):
        attempt_dir = root / "partial" / key / f"attempt-{attempt:02d}"
        quarantine = root / "quarantine" / key / f"attempt-{attempt:02d}"
        if attempt_dir.exists() or quarantine.exists():
            continue
        attempt_dir.mkdir(parents=True)
        materialized = copy.deepcopy(run)
        materialized["simulator_experiment"]["output"]["root"] = str(
            (attempt_dir / "reviewer_records").resolve()
        )
        if materialized["simulator_experiment"]["workload"]["mode"] == "capture":
            materialized["simulator_experiment"]["workload"]["tape_path"] = str(
                (attempt_dir / "workload_tape.json").resolve()
            )
        run_config_path = attempt_dir / "run_config.json"
        write_json_atomic(run_config_path, materialized)
        result_path = (
            attempt_dir / "reviewer_records" / key / "summary.json"
        ).resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        variables = {
            "python": sys.executable,
            "run_config": str(run_config_path.resolve()),
            "result_path": str(result_path),
            "partial_dir": str(attempt_dir.resolve()),
            "run_id": key,
            "attempt": str(attempt),
            "seed": run["seed"],
            "experiment_id": "FAASRANK_CALIBRATION",
            "method": run["method"],
        }
        command = _format_command(manifest["execution"]["command_template"], variables)
        observation = run_monitored(
            command,
            cwd=_execution_cwd(manifest),
            environment=_stage_environment(
                materialized, attempt_dir, run_config_path, result_path, attempt
            ),
            stdout_path=attempt_dir / "stdout.log",
            stderr_path=attempt_dir / "stderr.log",
            timeout_seconds=float(manifest["execution"]["timeout_seconds"]),
        )
        observation_path = attempt_dir / "process_observation.json"
        write_json_atomic(observation_path, observation.to_observation())
        issue: str | None = None
        try:
            if (
                observation.timed_out
                or observation.exit_code != 0
                or observation.launch_error
            ):
                raise FaaSRankCalibrationStageError(
                    f"calibration process failed: {observation.to_observation()}"
                )
            extra_validator(attempt_dir, materialized)
            write_json_atomic(
                attempt_dir / "stage_receipt.json",
                {
                    "schema_version": "NSE_FAASRANK_CALIBRATION_RUN_RECEIPT_V1",
                    "run_id": key,
                    "spec_sha256": spec_sha256,
                    "run_config_sha256": file_hash(run_config_path),
                    "summary_sha256": file_hash(result_path),
                    "process_observation_sha256": file_hash(observation_path),
                    "completed_at": utc_now(),
                },
            )
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            ProtocolValidationError,
        ) as exc:
            issue = str(exc)
        write_json_atomic(
            attempt_dir / "attempt.json",
            {
                "schema_version": "NSE_STAGE_ATTEMPT_V1",
                "stage": "faasrank_calibration",
                "run_id": key,
                "attempt": attempt,
                "status": "pass" if issue is None else "fail",
                "issue": issue,
                "command": command,
                "ended_at": utc_now(),
            },
        )
        if issue is None:
            canonical.parent.mkdir(parents=True, exist_ok=True)
            os.replace(attempt_dir, canonical)
            return canonical
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        os.replace(attempt_dir, quarantine)
    raise FaaSRankCalibrationStageError(
        f"calibration run {key} exhausted three same-spec technical attempts"
    )


def _validate_capture(directory: Path, run: dict[str, Any]) -> None:
    result_dir = directory / "reviewer_records" / run["run_id"]
    summary_path = result_dir / "summary.json"
    tape_path = directory / "workload_tape.json"
    required = (
        summary_path,
        result_dir / "environment.json",
        result_dir / "frames.jsonl",
        result_dir / "requests.jsonl",
        result_dir / "scheduler_windows.jsonl",
        tape_path,
        directory / "adapter_observation.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    partials = [str(path) for path in directory.rglob("*.partial")]
    if missing or partials:
        raise FaaSRankCalibrationStageError(
            f"training capture is incomplete; missing={missing}, partial={partials}"
        )
    summary = read_json(summary_path)
    tape = inspect_tape(tape_path)
    if (
        not isinstance(summary, dict)
        or summary.get("schema") != "NSE_SUMMARY_V1"
        or summary.get("run_complete") is not True
        or summary.get("run_id") != run["run_id"]
        or summary.get("arrivals") != tape.event_count
        or tape.workload_seed != run["simulator_experiment"]["workload_seed"]
    ):
        raise FaaSRankCalibrationStageError(
            "training capture summary/tape provenance is invalid"
        )


def capture_faasrank_training_tape(
    manifest_path: Path,
    workspace: Path,
    *,
    training_workload_seed: str = "FAASRANK-TRAIN-W01",
    template_seed: str = "E01",
    load: str = "low",
) -> dict[str, Any]:
    """Capture one workload that is cryptographically disjoint from E1--E9 tapes."""

    if not process_monitor_available():
        raise FaaSRankCalibrationStageError("psutil is required for calibration")
    manifest = load_and_validate_manifest(manifest_path)
    if training_workload_seed in {run["seed"] for run in manifest["runs"]}:
        raise FaaSRankCalibrationStageError(
            "training workload seed must be disjoint from all evaluation seeds"
        )
    evaluation_hashes = _evaluation_tape_hashes(manifest)
    source = _template(manifest, method="random", seed=template_seed, load=load)
    workspace = workspace.resolve()
    published_tape_path = workspace / "training_input" / "faasrank_training_tape.json"
    run = copy.deepcopy(source)
    run.pop("reference_dependency", None)
    run.pop("reference_policy", None)
    run["experiment_id"] = "FAASRANK_CALIBRATION_CAPTURE"
    run["cell_id"] = "FAASRANK_CALIBRATION_CAPTURE.low.homogeneous"
    run["seed"] = training_workload_seed
    run["method"] = "random"
    run["variant"] = "training_capture"
    run["workload_tape"] = {
        "key": "faasrank-independent-training",
        "kind": "calibration_capture",
        "path": "__FAASRANK_CAPTURE_TAPE__",
        "sha256": None,
        "event_count": None,
    }
    run["environment"] = {"PROTOCOL_SCHEDULER": "random", "NASH_OBSERVE": "off"}
    experiment = run["simulator_experiment"]
    experiment.update(
        {
            "protocol_version": "reviewer-v3",
            "workload_seed": training_workload_seed,
            "topology_seed": training_workload_seed,
            "algorithm_seed": training_workload_seed,
        }
    )
    experiment["workload"].update(
        {"mode": "capture", "tape_path": "__FAASRANK_CAPTURE_TAPE__"}
    )
    experiment["reference"] = {
        "mode": "sa_fallback",
        "table_path": "",
        "build_output_path": "",
    }
    experiment["nash"]["observe"] = "off"
    experiment["output"]["root"] = "__FAASRANK_CAPTURE_OUTPUT__"
    run["run_id"] = "__FAASRANK_CAPTURE_RUN_ID__"
    experiment["run_id"] = "__FAASRANK_CAPTURE_RUN_ID__"
    run.pop("run_spec_hash", None)
    spec_hash = object_hash(run)
    run_id = f"faasrank-training-capture.{training_workload_seed}.{spec_hash[:16]}"
    run["run_id"] = run_id
    experiment["run_id"] = run_id
    run["run_spec_hash"] = object_hash(run)
    canonical = _run_adapter_attempt(
        manifest,
        workspace / "training_capture",
        run,
        spec_hash,
        extra_validator=_validate_capture,
    )
    captured_tape_path = canonical / "workload_tape.json"
    tape = inspect_tape(captured_tape_path)
    if tape.sha256 in evaluation_hashes:
        raise FaaSRankCalibrationStageError(
            "captured FaaSRank training tape collides with an evaluation tape"
        )
    published_tape_path.parent.mkdir(parents=True, exist_ok=True)
    if published_tape_path.exists():
        published = inspect_tape(published_tape_path)
        if published.sha256 != tape.sha256:
            raise FaaSRankCalibrationStageError(
                "refusing to replace a different published FaaSRank training tape"
            )
    else:
        temporary = published_tape_path.with_name(published_tape_path.name + ".partial")
        temporary.write_bytes(captured_tape_path.read_bytes())
        if file_hash(temporary) != tape.sha256:
            raise FaaSRankCalibrationStageError(
                "copied FaaSRank training tape failed its SHA-256 check"
            )
        os.replace(temporary, published_tape_path)
    result = {
        "schema_version": "NSE_FAASRANK_TRAINING_TAPE_RECEIPT_V1",
        "status": "captured",
        "path": str(published_tape_path.resolve()),
        "sha256": tape.sha256,
        "bytes": tape.bytes,
        "event_count": tape.event_count,
        "workload_seed": tape.workload_seed,
        "capture_run_id": run_id,
        "capture_directory": str(canonical),
        "capture_summary_sha256": file_hash(
            canonical / "reviewer_records" / run_id / "summary.json"
        ),
        "evaluation_tape_hashes_checked": len(evaluation_hashes),
        "captured_at": utc_now(),
    }
    receipt_path = workspace / "training_input" / "training_tape_receipt.json"
    if receipt_path.exists():
        existing = read_json(receipt_path)
        stable = dict(result)
        stable.pop("captured_at", None)
        if not isinstance(existing, dict):
            raise FaaSRankCalibrationStageError("training tape receipt is invalid")
        observed = dict(existing)
        observed.pop("captured_at", None)
        if observed != stable:
            raise FaaSRankCalibrationStageError(
                "refusing to replace a different training tape receipt"
            )
        return existing
    write_json_atomic(receipt_path, result)
    return result


def _training_run(
    template: dict[str, Any],
    plan: FaaSRankCalibrationPlan,
    candidate: dict[str, Any],
    seed: str,
    tape_path: Path,
    tape_event_count: int,
) -> tuple[dict[str, Any], str]:
    run = copy.deepcopy(template)
    run.pop("reference_dependency", None)
    run.pop("reference_policy", None)
    run.pop("baseline_model", None)
    run["experiment_id"] = "FAASRANK_CALIBRATION"
    run["cell_id"] = f"FAASRANK_CALIBRATION.{candidate['candidate_sha256'][:12]}"
    run["seed"] = seed
    run["method"] = "sche_FaaSRank"
    run["variant"] = candidate["candidate_sha256"]
    run["environment"] = {
        "PROTOCOL_SCHEDULER": "sche_FaaSRank",
        "NASH_OBSERVE": "off",
    }
    run["workload_tape"] = {
        "path": str(tape_path.resolve()),
        "sha256": plan.training_tape_sha256,
        "event_count": tape_event_count,
        "kind": "faasrank_training",
    }
    experiment = run["simulator_experiment"]
    experiment["protocol_version"] = "reviewer-v3"
    experiment["workload_seed"] = inspect_tape(tape_path).workload_seed
    experiment["topology_seed"] = inspect_tape(tape_path).workload_seed
    experiment["algorithm_seed"] = seed
    experiment["workload"].update(
        {"mode": "replay", "tape_path": str(tape_path.resolve())}
    )
    experiment["faasrank_model"] = {
        "state": "frozen",
        "model_sha256": candidate["candidate_sha256"],
        "training_tape_sha256": plan.training_tape_sha256,
        **candidate["weights"],
        "epsilon": candidate["epsilon"],
    }
    experiment["reference"] = {
        "mode": "sa_fallback",
        "table_path": "",
        "build_output_path": "",
    }
    experiment["nash"]["observe"] = "off"
    experiment["output"]["root"] = "__FAASRANK_CALIBRATION_OUTPUT__"
    run["run_id"] = "__FAASRANK_CALIBRATION_RUN_ID__"
    experiment["run_id"] = "__FAASRANK_CALIBRATION_RUN_ID__"
    run.pop("run_spec_hash", None)
    spec_hash = object_hash(run)
    run_id = (
        f"faasrank-cal.{candidate['candidate_sha256'][:16]}.{seed}.{spec_hash[:12]}"
    )
    run["run_id"] = run_id
    experiment["run_id"] = run_id
    run["run_spec_hash"] = object_hash(run)
    return run, spec_hash


def _validate_training_run(directory: Path, run: dict[str, Any]) -> None:
    result_dir = directory / "reviewer_records" / run["run_id"]
    summary_path = result_dir / "summary.json"
    required = (
        summary_path,
        result_dir / "environment.json",
        result_dir / "frames.jsonl",
        result_dir / "requests.jsonl",
        result_dir / "scheduler_windows.jsonl",
        directory / "adapter_observation.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    partials = [str(path) for path in directory.rglob("*.partial")]
    if missing or partials:
        raise FaaSRankCalibrationStageError(
            f"training run artifacts are incomplete; missing={missing}, partial={partials}"
        )
    summary = read_json(summary_path)
    arrivals = summary.get("arrivals") if isinstance(summary, dict) else None
    completed = summary.get("completed") if isinstance(summary, dict) else None
    if (
        not isinstance(summary, dict)
        or summary.get("schema") != "NSE_SUMMARY_V1"
        or summary.get("run_complete") is not True
        or summary.get("run_id") != run["run_id"]
        or isinstance(arrivals, bool)
        or not isinstance(arrivals, int)
        or arrivals != run["workload_tape"]["event_count"]
        or isinstance(completed, bool)
        or not isinstance(completed, int)
        or completed < 0
        or completed > arrivals
    ):
        raise FaaSRankCalibrationStageError(
            "training run summary provenance/counters are invalid"
        )


def run_faasrank_calibration(
    manifest_path: Path,
    workspace: Path,
    *,
    training_tape_path: Path,
    calibration_plan_path: Path,
    template_seed: str = "E01",
    load: str = "low",
) -> dict[str, Any]:
    """Execute the complete preregistered candidate×seed matrix, result-blind."""

    if not process_monitor_available():
        raise FaaSRankCalibrationStageError("psutil is required for calibration")
    manifest = load_and_validate_manifest(manifest_path)
    evaluation_hashes = _evaluation_tape_hashes(manifest)
    plan = load_faasrank_calibration_plan(calibration_plan_path)
    tape = inspect_tape(training_tape_path)
    if tape.sha256 != plan.training_tape_sha256:
        raise FaaSRankCalibrationStageError(
            "training tape differs from the preregistered calibration plan"
        )
    if tape.sha256 in evaluation_hashes:
        raise FaaSRankCalibrationStageError(
            "FaaSRank training tape is also an evaluation tape"
        )
    template = _template(
        manifest, method="sche_FaaSRank", seed=template_seed, load=load
    )
    workspace = workspace.resolve()
    records: list[dict[str, Any]] = []
    semantic_hash: str | None = None
    for candidate in plan.candidates:
        candidate = dict(candidate)
        for seed in plan.training_seeds:
            run, spec_hash = _training_run(
                template, candidate, seed, training_tape_path, tape.event_count
            )
            canonical = _run_adapter_attempt(
                manifest,
                workspace / "training_runs",
                run,
                spec_hash,
                extra_validator=_validate_training_run,
            )
            result_dir = canonical / "reviewer_records" / run["run_id"]
            config_path = canonical / "run_config.json"
            summary_path = result_dir / "summary.json"
            environment = read_json(result_dir / "environment.json")
            if not isinstance(environment, dict):
                raise FaaSRankCalibrationStageError(
                    "training environment is not a JSON object"
                )
            observed_semantic_hash = object_hash(
                {
                    "functions": environment.get("functions"),
                    "nodes": environment.get("nodes"),
                    "network_mb_per_second": environment.get("network_mb_per_second"),
                }
            )
            if semantic_hash is None:
                semantic_hash = observed_semantic_hash
            elif semantic_hash != observed_semantic_hash:
                raise FaaSRankCalibrationStageError(
                    "candidate runs did not share one immutable training environment"
                )
            records.append(
                {
                    "candidate_sha256": candidate["candidate_sha256"],
                    "seed": seed,
                    "run_id": run["run_id"],
                    "run_config_path": str(config_path.resolve()),
                    "run_config_sha256": file_hash(config_path),
                    "summary_path": str(summary_path.resolve()),
                    "summary_sha256": file_hash(summary_path),
                }
            )
    records.sort(key=lambda item: (item["candidate_sha256"], item["seed"]))
    results = {
        "schema_version": CALIBRATION_RESULTS_SCHEMA,
        "completed_at": utc_now(),
        "plan_sha256": plan.artifact_sha256,
        "training_tape_sha256": tape.sha256,
        "runs": records,
    }
    output = workspace / "faasrank_calibration_results.json"
    if output.exists():
        existing = read_json(output)
        expected = dict(results)
        expected.pop("completed_at", None)
        observed = dict(existing) if isinstance(existing, dict) else {}
        observed.pop("completed_at", None)
        if observed != expected:
            raise FaaSRankCalibrationStageError(
                f"refusing to replace different calibration results {output}"
            )
        return existing
    write_json_atomic(output, results)
    return results
