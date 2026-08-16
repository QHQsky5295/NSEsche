from __future__ import annotations

import copy
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .process_monitor import available as process_monitor_available
from .process_monitor import run_monitored
from .schema import ProtocolValidationError, load_and_validate_manifest
from .tape import derive_capacity_tape, inspect_tape
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


class SlaPilotError(ProtocolValidationError):
    """Raised when the predeclared isolated SLA calibration cannot be completed."""


@dataclass(frozen=True)
class PilotOutcome:
    role: str
    class_assignment: str
    factor: int
    run_id: str
    directory: Path
    summary: dict[str, Any]
    final_frame: dict[str, Any]
    tape: dict[str, Any]


def _resolve_manifest_path(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (manifest_path.resolve().parent / path).resolve()


def _execution_cwd(manifest: dict[str, Any]) -> Path:
    return Path(manifest["execution"].get("cwd", ".")).resolve()


def _format_command(template: list[str], variables: dict[str, str]) -> list[str]:
    try:
        return [part.format_map(variables) for part in template]
    except KeyError as exc:
        raise SlaPilotError(f"unknown command template variable: {exc}") from exc


def _select_template(
    manifest: dict[str, Any],
    *,
    seed: str,
    method: str,
    load: str,
    topology: str,
) -> dict[str, Any]:
    # ``matrix_defaults`` belongs to the editable protocol configuration, not
    # to an expanded/bound run manifest.  The latter is deliberately
    # self-contained, so derive the frozen E1 base-node count from its bound
    # E1 run declarations instead of reaching back into a config-only field.
    e1_runs = [
        run for run in manifest.get("runs", []) if run.get("experiment_id") == "E1"
    ]
    if not e1_runs:
        raise SlaPilotError(
            "isolated SLA pilot requires an E1 template; the manifest has no E1 runs"
        )

    node_counts: set[int] = set()
    for run in e1_runs:
        cluster = run.get("cluster")
        node_count = cluster.get("node_count") if isinstance(cluster, dict) else None
        if (
            isinstance(node_count, bool)
            or not isinstance(node_count, int)
            or node_count <= 0
        ):
            raise SlaPilotError(
                "E1 template cluster.node_count must be a positive integer"
            )
        node_counts.add(node_count)
    if len(node_counts) != 1:
        raise SlaPilotError(
            "E1 template cluster.node_count is not uniquely frozen in the manifest"
        )
    base_node_count = next(iter(node_counts))

    matches = [
        run
        for run in e1_runs
        if run["experiment_id"] == "E1"
        and run["seed"] == seed
        and run["method"] == method
        and run["workload"]["request_freq"] == load
        and run["cluster"]["topology"] == topology
        and run["cluster"]["node_count"] == base_node_count
    ]
    if len(matches) != 1:
        raise SlaPilotError(
            "isolated SLA pilot requires exactly one matching tape-bound E1 template; "
            f"found {len(matches)} for method={method}, seed={seed}, load={load}, "
            f"topology={topology}"
        )
    run = matches[0]
    tape = run.get("workload_tape", {})
    if not isinstance(tape.get("sha256"), str):
        raise SlaPilotError("SLA pilots require a tape-bound manifest")
    return run


def _capacity_tapes(
    manifest_path: Path,
    template: dict[str, Any],
    workspace: Path,
    factors: tuple[int, ...],
    arrival_horizon_frames: int,
) -> dict[int, dict[str, Any]]:
    base_binding = template["workload_tape"]
    base_path = _resolve_manifest_path(manifest_path, base_binding["path"])
    base = inspect_tape(base_path)
    if base.sha256 != base_binding["sha256"]:
        raise SlaPilotError(
            "SLA pilot base tape hash differs from its manifest binding"
        )
    if base.workload_seed != template["seed"]:
        raise SlaPilotError(
            "SLA pilot base tape seed differs from the selected template"
        )
    result: dict[int, dict[str, Any]] = {}
    for factor in factors:
        if factor == 1:
            result[factor] = {
                **base.to_dict(),
                "path": str(base_path),
                "kind": "base_steady",
                "parent_path": None,
                "parent_sha256": None,
                "measured_arrival_rate_rps": base.event_count
                / (arrival_horizon_frames * 0.001),
                "transform": {"kind": "identity", "factor": 1},
            }
            continue
        output = workspace / "inputs" / f"capacity-factor-{factor}.json"
        if output.exists():
            derived = inspect_tape(output)
            document = read_json(output)
            derivation = (
                document.get("derivation") if isinstance(document, dict) else None
            )
            if (
                derived.workload_seed != base.workload_seed
                or not isinstance(derivation, dict)
                or derivation.get("kind") != "isolated_capacity_same_frame_replication"
                or derivation.get("factor") != factor
                or derivation.get("parent_sha256") != base.sha256
            ):
                raise SlaPilotError(
                    f"existing capacity tape is not the declared immutable derivation: {output}"
                )
            entry = {
                **derived.to_dict(),
                "measured_arrival_rate_rps": derived.event_count
                / (arrival_horizon_frames * 0.001),
                "kind": "isolated_capacity_tape",
                "parent_path": str(base_path),
                "parent_sha256": base.sha256,
                "transform": derivation,
            }
        else:
            entry = derive_capacity_tape(
                base_path,
                output,
                factor,
                horizon_frames=arrival_horizon_frames,
            )
        entry["path"] = str(output.resolve())
        result[factor] = entry
    return result


def _pilot_run(
    template: dict[str, Any],
    *,
    role: str,
    class_assignment: str,
    factor: int,
    tape: dict[str, Any],
    total_frame: int,
    arrival_horizon_frames: int,
) -> tuple[dict[str, Any], str]:
    run = copy.deepcopy(template)
    run.pop("reference_dependency", None)
    run.pop("reference_policy", None)
    run.pop("sla_targets", None)
    run.pop("baseline_model", None)
    run["experiment_id"] = "SLA_PILOT"
    run["cell_id"] = f"SLA_PILOT.{role}.factor{factor}"
    run["variant"] = role
    run["method"] = "greedy"
    run["environment"] = {
        "PROTOCOL_SCHEDULER": "greedy",
        "NASH_OBSERVE": "off",
    }
    run["simulation"].update(
        {
            "total_frame": total_frame,
            "arrival_horizon_frames": arrival_horizon_frames,
            "expected_final_frame": total_frame,
            "expected_frame_count": total_frame + 1,
        }
    )
    run["workload"].update(
        {
            "arrival_profile": "steady",
            "qos_profile": f"isolated_{class_assignment}",
            "load_scale": float(factor),
        }
    )
    run["workload_tape"] = copy.deepcopy(tape)
    experiment = run["simulator_experiment"]
    experiment["protocol_version"] = "reviewer-v3"
    experiment["workload"].update(
        {
            "mode": "replay",
            "tape_path": tape["path"],
            "arrival_horizon_frames": arrival_horizon_frames,
            "load_scale": 1.0,
            "burst_profile": "steady",
        }
    )
    experiment["qos"].update(
        {
            "enabled": True,
            "class_assignment": class_assignment,
            "latency_deadline_ms": None,
            "throughput_target_rps": None,
            "cost_budget_per_request": None,
        }
    )
    experiment["reference"] = {
        "mode": "sa_fallback",
        "table_path": "",
        "build_output_path": "",
    }
    experiment["nash"]["observe"] = "off"
    experiment["output"]["root"] = "__SLA_PILOT_OUTPUT_ROOT__"
    run["run_id"] = "__SLA_PILOT_RUN_ID__"
    experiment["run_id"] = "__SLA_PILOT_RUN_ID__"
    run.pop("run_spec_hash", None)
    spec_hash = object_hash(run)
    run_id = f"sla-pilot.{role}.f{factor}.{template['seed']}.{spec_hash[:16]}"
    run["run_id"] = run_id
    experiment["run_id"] = run_id
    run["run_spec_hash"] = object_hash(run)
    return run, spec_hash


def _last_jsonl_event(path: Path) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise SlaPilotError(f"blank JSONL line {line_number} in {path}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise SlaPilotError(f"non-object JSONL line {line_number} in {path}")
            last = value
    if last is None:
        raise SlaPilotError(f"empty JSONL artifact: {path}")
    return last


def _finite_number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SlaPilotError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        comparator = "positive and finite" if positive else "finite"
        raise SlaPilotError(f"{name} must be {comparator}")
    return result


def _validate_pilot_artifacts(
    directory: Path,
    run: dict[str, Any],
    tape: dict[str, Any],
    class_assignment: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result_dir = directory / "reviewer_records" / run["run_id"]
    summary_path = result_dir / "summary.json"
    frames_path = result_dir / "frames.jsonl"
    environment_path = result_dir / "environment.json"
    required = (
        summary_path,
        frames_path,
        result_dir / "requests.jsonl",
        result_dir / "scheduler_windows.jsonl",
        environment_path,
        directory / "process_observation.json",
        directory / "adapter_observation.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    partials = [str(path) for path in result_dir.rglob("*.partial")]
    if missing or partials:
        raise SlaPilotError(
            f"isolated pilot artifacts are incomplete; missing={missing}, partial={partials}"
        )
    summary = read_json(summary_path)
    if (
        not isinstance(summary, dict)
        or summary.get("schema") != "NSE_SUMMARY_V1"
        or summary.get("run_complete") is not True
        or summary.get("run_id") != run["run_id"]
    ):
        raise SlaPilotError("isolated pilot summary provenance/completion is invalid")
    expected_final = run["simulation"]["expected_final_frame"]
    if (
        summary.get("final_frame") != expected_final
        or summary.get("frames_recorded") != expected_final + 1
        or summary.get("observation_time_ms") != run["simulation"]["total_frame"]
        or summary.get("arrivals") != tape["event_count"]
    ):
        raise SlaPilotError("isolated pilot horizon/arrival counters are invalid")
    for field in ("completed", "admission_drop", "admission_reject", "timeout"):
        value = summary.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SlaPilotError(f"isolated pilot {field} counter is invalid")
    _finite_number(summary.get("completion_ratio"), "completion_ratio")
    _finite_number(
        summary.get("throughput_requests_per_second"),
        "throughput_requests_per_second",
    )
    environment = read_json(environment_path)
    observed_assignment = (
        environment.get("config", {})
        .get("experiment", {})
        .get("qos", {})
        .get("class_assignment")
        if isinstance(environment, dict)
        else None
    )
    if (
        not isinstance(environment, dict)
        or environment.get("schema") != "NSE_ENVIRONMENT_V1"
        or environment.get("run_id") != run["run_id"]
        or observed_assignment != class_assignment
    ):
        raise SlaPilotError("isolated pilot environment/QoS provenance is invalid")
    final_frame = _last_jsonl_event(frames_path)
    if final_frame.get("frame") != expected_final:
        raise SlaPilotError(
            "isolated pilot frame log does not reach the frozen horizon"
        )
    return summary, final_frame


def _run_one(
    manifest: dict[str, Any],
    workspace: Path,
    run: dict[str, Any],
    spec_hash: str,
    tape: dict[str, Any],
    class_assignment: str,
) -> PilotOutcome:
    root = workspace / "runs"
    key = run["run_id"]
    canonical = root / "canonical" / key
    if canonical.is_dir():
        receipt = read_json(canonical / "pilot_run_receipt.json")
        if (
            not isinstance(receipt, dict)
            or receipt.get("pilot_spec_sha256") != spec_hash
            or receipt.get("tape_sha256") != tape["sha256"]
        ):
            raise SlaPilotError(
                f"existing SLA pilot canonical does not match the frozen spec: {canonical}"
            )
        summary, final_frame = _validate_pilot_artifacts(
            canonical, run, tape, class_assignment
        )
        return PilotOutcome(
            role=run["variant"],
            class_assignment=class_assignment,
            factor=int(run["workload"]["load_scale"]),
            run_id=key,
            directory=canonical,
            summary=summary,
            final_frame=final_frame,
            tape=tape,
        )

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
        materialized["simulator_experiment"]["workload"]["tape_path"] = str(
            Path(tape["path"]).resolve()
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
            "experiment_id": "SLA_PILOT",
            "method": run["method"],
        }
        command = _format_command(manifest["execution"]["command_template"], variables)
        environment = os.environ.copy()
        environment.update(run["environment"])
        environment.update(
            {
                "PROTOCOL_RUN_ID": key,
                "PROTOCOL_SEED": run["seed"],
                "PROTOCOL_ATTEMPT": str(attempt),
                "PROTOCOL_RUN_CONFIG": str(run_config_path.resolve()),
                "PROTOCOL_PARTIAL_DIR": str(attempt_dir.resolve()),
                "PROTOCOL_RESULT_PATH": str(result_path),
                "PROTOCOL_REVIEWER_RECORD_ROOT": str(
                    (attempt_dir / "reviewer_records").resolve()
                ),
                "PROTOCOL_WORKLOAD_TAPE": str(Path(tape["path"]).resolve()),
            }
        )
        observation = run_monitored(
            command,
            cwd=_execution_cwd(manifest),
            environment=environment,
            stdout_path=attempt_dir / "stdout.log",
            stderr_path=attempt_dir / "stderr.log",
            timeout_seconds=float(manifest["execution"]["timeout_seconds"]),
        )
        write_json_atomic(
            attempt_dir / "process_observation.json", observation.to_observation()
        )
        issue: str | None = None
        try:
            if (
                observation.timed_out
                or observation.exit_code != 0
                or observation.launch_error
            ):
                raise SlaPilotError(
                    f"isolated pilot process failed: {observation.to_observation()}"
                )
            summary, final_frame = _validate_pilot_artifacts(
                attempt_dir, run, tape, class_assignment
            )
            receipt = {
                "schema_version": "NSE_ISOLATED_SLA_PILOT_RUN_RECEIPT_V1",
                "run_id": key,
                "role": run["variant"],
                "class_assignment": class_assignment,
                "factor": int(run["workload"]["load_scale"]),
                "pilot_spec_sha256": spec_hash,
                "run_config_sha256": file_hash(run_config_path),
                "tape_path": str(Path(tape["path"]).resolve()),
                "tape_sha256": tape["sha256"],
                "tape_event_count": tape["event_count"],
                "summary_sha256": file_hash(result_path),
                "environment_sha256": file_hash(
                    result_path.parent / "environment.json"
                ),
                "process_observation_sha256": file_hash(
                    attempt_dir / "process_observation.json"
                ),
                "completed_at": utc_now(),
            }
            write_json_atomic(attempt_dir / "pilot_run_receipt.json", receipt)
        except (OSError, ValueError, json.JSONDecodeError, SlaPilotError) as exc:
            issue = str(exc)
        write_json_atomic(
            attempt_dir / "attempt.json",
            {
                "schema_version": "NSE_STAGE_ATTEMPT_V1",
                "stage": "isolated_sla_pilot",
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
            return PilotOutcome(
                role=run["variant"],
                class_assignment=class_assignment,
                factor=int(run["workload"]["load_scale"]),
                run_id=key,
                directory=canonical,
                summary=summary,
                final_frame=final_frame,
                tape=tape,
            )
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        os.replace(attempt_dir, quarantine)
    raise SlaPilotError(f"isolated SLA pilot {key} exhausted three technical attempts")


def _is_sustainable(outcome: PilotOutcome, minimum_completion_ratio: float) -> bool:
    summary = outcome.summary
    frame = outcome.final_frame
    return (
        float(summary["completion_ratio"]) >= minimum_completion_ratio
        and summary["admission_drop"] == 0
        and summary["admission_reject"] == 0
        and summary["timeout"] == 0
        and frame.get("queue_total") == 0
        and frame.get("active_requests") == 0
        and frame.get("tasks_in_system") == 0
    )


def _write_pilot_artifact(path: Path, document: dict[str, Any]) -> None:
    if path.exists():
        existing = read_json(path)
        stable_fields = (
            "schema_version",
            "pilot_id",
            "pilot_scope",
            "class_assignment",
            "completed",
            "metrics",
            "provenance",
        )
        if not isinstance(existing, dict) or any(
            existing.get(field) != document.get(field) for field in stable_fields
        ):
            raise SlaPilotError(f"refusing to replace immutable pilot artifact {path}")
        return
    write_json_atomic(path, document)


def run_isolated_sla_pilots(
    manifest_path: Path,
    workspace: Path,
    *,
    seed: str = "E01",
    method: str = "greedy",
    load: str = "low",
    topology: str = "homogeneous",
    capacity_factors: Iterable[int] = (1, 2, 3, 4),
    total_frame: int = 4000,
    arrival_horizon_frames: int = 1000,
    minimum_completion_ratio: float = 0.99,
) -> dict[str, Any]:
    """Execute and freeze the three measured class-isolated SLA source runs.

    Capacity candidates are all executed before inspection.  The sustainable
    point must form a monotone passing prefix followed by at least one failing
    point; this prevents selecting a convenient isolated result after the fact.
    """

    if method != "greedy":
        raise SlaPilotError(
            "the frozen isolated-SLA calibration scheduler is greedy under the common HPA"
        )
    factors = tuple(capacity_factors)
    if (
        not factors
        or factors != tuple(sorted(set(factors)))
        or factors[0] != 1
        or any(
            isinstance(factor, bool) or not isinstance(factor, int)
            for factor in factors
        )
    ):
        raise SlaPilotError(
            "capacity factors must be unique increasing positive integers beginning at 1"
        )
    if total_frame < arrival_horizon_frames or arrival_horizon_frames <= 0:
        raise SlaPilotError("SLA pilot horizon must cover a positive arrival horizon")
    if not math.isfinite(minimum_completion_ratio) or not (
        0.0 < minimum_completion_ratio <= 1.0
    ):
        raise SlaPilotError("minimum completion ratio must be in (0, 1]")
    if not process_monitor_available():
        raise SlaPilotError("psutil is required for measured SLA pilot runs")
    manifest = load_and_validate_manifest(manifest_path)
    if manifest.get("all_tapes_bound") is not True:
        raise SlaPilotError("run isolated SLA pilots only after bind-tapes")
    workspace = workspace.resolve()
    template = _select_template(
        manifest,
        seed=seed,
        method=method,
        load=load,
        topology=topology,
    )
    tapes = _capacity_tapes(
        manifest_path,
        template,
        workspace,
        factors,
        arrival_horizon_frames,
    )

    outcomes: dict[str, PilotOutcome] = {}
    for role, assignment in (
        ("latency", "all_latency"),
        ("cost", "all_cost"),
    ):
        run, spec_hash = _pilot_run(
            template,
            role=role,
            class_assignment=assignment,
            factor=1,
            tape=tapes[1],
            total_frame=total_frame,
            arrival_horizon_frames=arrival_horizon_frames,
        )
        outcomes[role] = _run_one(
            manifest, workspace, run, spec_hash, tapes[1], assignment
        )

    capacity_outcomes: list[PilotOutcome] = []
    for factor in factors:
        run, spec_hash = _pilot_run(
            template,
            role="throughput_capacity",
            class_assignment="all_throughput",
            factor=factor,
            tape=tapes[factor],
            total_frame=total_frame,
            arrival_horizon_frames=arrival_horizon_frames,
        )
        capacity_outcomes.append(
            _run_one(
                manifest,
                workspace,
                run,
                spec_hash,
                tapes[factor],
                "all_throughput",
            )
        )

    flags = [
        _is_sustainable(outcome, minimum_completion_ratio)
        for outcome in capacity_outcomes
    ]
    pass_indices = [index for index, passed in enumerate(flags) if passed]
    if not pass_indices:
        raise SlaPilotError(
            "no predeclared capacity candidate was sustainable; lower the pilot base load "
            "in a new, predeclared pilot protocol"
        )
    selected_index = max(pass_indices)
    if selected_index == len(flags) - 1:
        raise SlaPilotError(
            "the highest predeclared capacity candidate was still sustainable; extend the "
            "candidate grid before freezing a throughput target"
        )
    if flags != [index <= selected_index for index in range(len(flags))]:
        raise SlaPilotError(
            "capacity outcomes are non-monotone; audit the simulator before freezing an SLA"
        )
    selected = capacity_outcomes[selected_index]

    latency_p95 = _finite_number(
        outcomes["latency"].summary.get("latency_ms", {}).get("p95"),
        "isolated latency p95",
        positive=True,
    )
    cost_per_request = _finite_number(
        outcomes["cost"].summary.get("simulator_internal_cost_per_completed_request"),
        "isolated cost per completed request",
        positive=True,
    )
    sustainable_rps = _finite_number(
        selected.tape["event_count"] / (arrival_horizon_frames * 0.001),
        "isolated sustainable throughput",
        positive=True,
    )
    artifacts = workspace / "pilot_artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    common_provenance = {
        "pilot_scope": "isolated",
        "method": "greedy",
        "common_hpa_hash": template["common_hpa_hash"],
        "seed": seed,
        "base_load": load,
        "topology": topology,
        "node_count": template["cluster"]["node_count"],
        "total_frame": total_frame,
        "arrival_horizon_frames": arrival_horizon_frames,
        "capacity_factors_predeclared": list(factors),
        "capacity_minimum_completion_ratio": minimum_completion_ratio,
        "capacity_sustainable_rule": (
            "completion_ratio_at_least_threshold_and_zero_drop_reject_timeout_and_"
            "final_queue_active_tasks_all_zero"
        ),
    }
    latency_summary_path = (
        outcomes["latency"].directory
        / "reviewer_records"
        / outcomes["latency"].run_id
        / "summary.json"
    )
    cost_summary_path = (
        outcomes["cost"].directory
        / "reviewer_records"
        / outcomes["cost"].run_id
        / "summary.json"
    )
    selected_summary_path = (
        selected.directory / "reviewer_records" / selected.run_id / "summary.json"
    )
    documents = {
        "latency": {
            "schema_version": "NSE_ISOLATED_SLA_PILOT_V1",
            "pilot_id": outcomes["latency"].run_id,
            "pilot_scope": "isolated",
            "class_assignment": "all_latency",
            "completed": True,
            "metrics": {"latency_p95_ms": latency_p95},
            "provenance": {
                **common_provenance,
                "class_assignment": "all_latency",
                "source_summary_path": str(latency_summary_path.resolve()),
                "source_summary_sha256": file_hash(latency_summary_path),
                "workload_tape_sha256": outcomes["latency"].tape["sha256"],
            },
        },
        "cost": {
            "schema_version": "NSE_ISOLATED_SLA_PILOT_V1",
            "pilot_id": outcomes["cost"].run_id,
            "pilot_scope": "isolated",
            "class_assignment": "all_cost",
            "completed": True,
            "metrics": {"cost_per_request": cost_per_request},
            "provenance": {
                **common_provenance,
                "class_assignment": "all_cost",
                "source_summary_path": str(cost_summary_path.resolve()),
                "source_summary_sha256": file_hash(cost_summary_path),
                "workload_tape_sha256": outcomes["cost"].tape["sha256"],
            },
        },
        "throughput": {
            "schema_version": "NSE_ISOLATED_SLA_PILOT_V1",
            "pilot_id": selected.run_id,
            "pilot_scope": "isolated",
            "class_assignment": "all_throughput",
            "completed": True,
            "throughput_is_sustainable": True,
            "metrics": {"sustainable_throughput_rps": sustainable_rps},
            "provenance": {
                **common_provenance,
                "class_assignment": "all_throughput",
                "throughput_is_sustainable": True,
                "selected_factor": selected.factor,
                "selection_rule": "highest_sustainable_contiguous_prefix_with_observed_failing_successor",
                "candidate_results": [
                    {
                        "factor": outcome.factor,
                        "run_id": outcome.run_id,
                        "tape_sha256": outcome.tape["sha256"],
                        "arrival_rate_rps": outcome.tape["event_count"]
                        / (arrival_horizon_frames * 0.001),
                        "completion_ratio": outcome.summary["completion_ratio"],
                        "final_queue": outcome.final_frame.get("queue_total"),
                        "final_active_requests": outcome.final_frame.get(
                            "active_requests"
                        ),
                        "final_tasks_in_system": outcome.final_frame.get(
                            "tasks_in_system"
                        ),
                        "sustainable": passed,
                        "summary_sha256": file_hash(
                            outcome.directory
                            / "reviewer_records"
                            / outcome.run_id
                            / "summary.json"
                        ),
                    }
                    for outcome, passed in zip(capacity_outcomes, flags)
                ],
                "source_summary_path": str(selected_summary_path.resolve()),
                "source_summary_sha256": file_hash(selected_summary_path),
                "workload_tape_sha256": selected.tape["sha256"],
            },
        },
    }
    paths = {
        "latency": artifacts / "isolated-latency.json",
        "throughput": artifacts / "isolated-throughput-capacity.json",
        "cost": artifacts / "isolated-cost.json",
    }
    for role, path in paths.items():
        _write_pilot_artifact(path, documents[role])
    report = {
        "schema_version": "NSE_ISOLATED_SLA_PILOT_REPORT_V1",
        "status": "completed",
        "manifest_path": str(manifest_path.resolve()),
        "manifest_hash": manifest["manifest_hash"],
        "seed": seed,
        "method": "greedy",
        "capacity_factors": list(factors),
        "selected_capacity_factor": selected.factor,
        "artifacts": {
            role: {
                "path": str(path.resolve()),
                "sha256": file_hash(path),
                "bytes": path.stat().st_size,
            }
            for role, path in paths.items()
        },
    }
    report["report_sha256"] = object_hash(report)
    report["created_at"] = utc_now()
    report_path = workspace / "sla_pilot_report.json"
    if report_path.exists():
        existing = read_json(report_path)
        if (
            not isinstance(existing, dict)
            or existing.get("report_sha256") != report["report_sha256"]
        ):
            raise SlaPilotError(
                f"refusing to replace immutable SLA pilot report {report_path}"
            )
        return existing
    else:
        write_json_atomic(report_path, report)
    return report
