from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

from .ledger import Ledger
from .process_monitor import available as process_monitor_available
from .process_monitor import run_monitored
from .reference import inspect_reference_table, register_reference_build
from .schema import ProtocolValidationError, load_and_validate_manifest
from .tape import inspect_tape, register_catalog_entry
from .util import (
    directory_tree_inventory,
    file_hash,
    object_hash,
    promote_directory_exact,
    read_json,
    utc_now,
    write_json_atomic,
)


class StageError(RuntimeError):
    pass


def _promote_attempt_directory(
    attempt_dir: Path, canonical: Path, *, expected_key: str
) -> dict[str, Any]:
    """Promote an attempt and recover a Windows destination-placement anomaly.

    On the experiment host, a small fraction of successful directory replaces
    have placed the source under ``canonical.parent`` using its old basename
    (for example, ``attempt-01``) instead of the requested key.  The move is
    accepted only when the embedded attempt metadata identifies exactly one
    such directory.  The unexpected directory is retained as recovery
    evidence; the exact canonical path receives a byte-for-byte tree copy.
    """

    promotion = promote_directory_exact(attempt_dir, canonical)
    if canonical.is_dir():
        metadata = read_json(canonical / "attempt.json")
        if not isinstance(metadata, dict) or metadata.get("key") != expected_key:
            raise StageError(
                f"promoted canonical attempt metadata differs for {expected_key!r}"
            )
        return promotion

    matches: list[Path] = []
    for candidate in canonical.parent.iterdir():
        if not candidate.is_dir() or not candidate.name.startswith("attempt-"):
            continue
        metadata_path = candidate / "attempt.json"
        if not metadata_path.is_file():
            continue
        try:
            metadata = read_json(metadata_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(metadata, dict) and metadata.get("key") == expected_key:
            matches.append(candidate)
    if len(matches) != 1:
        raise StageError(
            "attempt promotion did not create the requested canonical directory "
            f"and found {len(matches)} recovery candidates for {expected_key!r}"
        )

    recovery_source = matches[0]
    try:
        shutil.copytree(recovery_source, canonical)
    except OSError as exc:
        raise StageError(
            f"could not recover misplaced attempt for {expected_key!r}: {exc}"
        ) from exc
    recovered_metadata = read_json(canonical / "attempt.json")
    if (
        not isinstance(recovered_metadata, dict)
        or recovered_metadata.get("key") != expected_key
    ):
        raise StageError(
            f"recovered canonical attempt metadata differs for {expected_key!r}"
        )
    recovery_inventory = directory_tree_inventory(recovery_source)
    canonical_inventory = directory_tree_inventory(canonical)
    if recovery_inventory != canonical_inventory:
        raise StageError(
            f"recovered canonical attempt tree differs for {expected_key!r}"
        )
    return {
        "mode": "recovered_misplaced_directory",
        "source_tree_sha256": object_hash(recovery_inventory),
        "file_count": len(recovery_inventory),
        "bytes": sum(item["bytes"] for item in recovery_inventory),
        "source_retained": True,
        "source_path": str(recovery_source.resolve()),
        "cleanup_error": None,
    }


def _format_command(template: list[str], variables: dict[str, str]) -> list[str]:
    try:
        return [part.format_map(variables) for part in template]
    except KeyError as exc:
        raise StageError(f"unknown command template variable: {exc}") from exc


def _execution_cwd(manifest: dict[str, Any]) -> Path:
    path = Path(manifest["execution"].get("cwd", "."))
    return path.resolve()


def _resolve_manifest_path(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    return (
        path.resolve()
        if path.is_absolute()
        else (manifest_path.resolve().parent / path).resolve()
    )


def _used_attempts(root: Path, key: str) -> set[int]:
    attempts: set[int] = set()
    for category in ("partial", "quarantine"):
        directory = root / category / key
        if not directory.is_dir():
            continue
        for child in directory.iterdir():
            if child.is_dir() and child.name.startswith("attempt-"):
                try:
                    attempts.add(int(child.name.removeprefix("attempt-")))
                except ValueError:
                    pass
    return attempts


def _semantic_environment(environment_path: Path) -> dict[str, Any]:
    environment = read_json(environment_path)
    if (
        not isinstance(environment, dict)
        or environment.get("schema") != "NSE_ENVIRONMENT_V1"
    ):
        raise StageError("capture environment schema is invalid")
    functions = environment.get("functions")
    nodes = environment.get("nodes")
    network = environment.get("network_mb_per_second")
    if (
        not isinstance(functions, list)
        or not isinstance(nodes, list)
        or not isinstance(network, list)
    ):
        raise StageError("capture environment lacks functions/nodes/network")
    function_dag_qos_hash = object_hash(functions)
    node_network_hash = object_hash({"nodes": nodes, "network_mb_per_second": network})
    bundle = {
        "function_dag_qos_sha256": function_dag_qos_hash,
        "node_network_sha256": node_network_hash,
        "capture_environment_sha256": file_hash(environment_path),
        "function_count": len(functions),
        "node_count": len(nodes),
    }
    bundle["semantic_bundle_sha256"] = object_hash(bundle)
    return bundle


def _capture_candidates(
    manifest: dict[str, Any]
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    candidates: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for run in manifest["runs"]:
        plan = run["workload_tape"]
        if plan["kind"] == "base_steady":
            candidates.setdefault(plan["key"], []).append((run, plan))
    selected: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for key, values in candidates.items():
        values.sort(
            key=lambda value: (
                value[0]["method"] != "random",
                value[0]["experiment_id"] not in {"E1", "E4"},
                value[0]["cell_id"],
            )
        )
        selected[key] = values[0]
    return selected


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
            "PROTOCOL_RUN_CONFIG": str(run_config_path),
            "PROTOCOL_PARTIAL_DIR": str(attempt_dir),
            "PROTOCOL_RESULT_PATH": str(result_path),
            "PROTOCOL_REVIEWER_RECORD_ROOT": str(attempt_dir / "reviewer_records"),
        }
    )
    return environment


def capture_base_tapes(
    manifest_path: Path,
    workspace: Path,
    catalog_path: Path,
    *,
    keys: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    if not process_monitor_available():
        raise StageError("psutil is required for measured capture runs")
    manifest = load_and_validate_manifest(manifest_path)
    root = workspace.resolve() / "capture_base_tapes"
    ledger = Ledger(root / "ledger.jsonl")
    selected_keys = set(keys) if keys is not None else None
    candidates = _capture_candidates(manifest)
    if selected_keys is not None:
        missing = selected_keys - candidates.keys()
        if missing:
            raise StageError(f"unknown base tape keys: {sorted(missing)}")
    results: list[dict[str, Any]] = []
    for key in sorted(candidates):
        if selected_keys is not None and key not in selected_keys:
            continue
        run, plan = candidates[key]
        canonical = root / "canonical" / key
        if canonical.is_dir():
            results.append(
                {"key": key, "status": "canonical_exists", "path": str(canonical)}
            )
            continue
        used = _used_attempts(root, key)
        passed = False
        for attempt in range(1, 4):
            if attempt in used:
                continue
            attempt_dir = root / "partial" / key / f"attempt-{attempt:02d}"
            attempt_dir.mkdir(parents=True)
            capture_run = copy.deepcopy(run)
            capture_id = f"capture.{key}"
            capture_run["run_id"] = capture_id
            capture_run["method"] = "random"
            capture_run["environment"] = {
                "PROTOCOL_SCHEDULER": "random",
                "NASH_OBSERVE": "off",
            }
            tape_path = attempt_dir / "workload_tape.json"
            experiment = capture_run["simulator_experiment"]
            experiment["run_id"] = capture_id
            experiment["workload"].update(
                {
                    "mode": "capture",
                    "tape_path": str(tape_path.resolve()),
                    "load_scale": 1.0,
                    "burst_profile": "steady",
                }
            )
            experiment["reference"] = {
                "mode": "sa_fallback",
                "table_path": "",
                "build_output_path": "",
            }
            experiment["nash"]["observe"] = "off"
            experiment["output"]["root"] = str(
                (attempt_dir / "reviewer_records").resolve()
            )
            run_config_path = attempt_dir / "run_config.json"
            write_json_atomic(run_config_path, capture_run)
            result_path = attempt_dir / "reviewer_records" / capture_id / "summary.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            variables = {
                "python": sys.executable,
                "run_config": str(run_config_path),
                "result_path": str(result_path),
                "partial_dir": str(attempt_dir),
                "run_id": capture_id,
                "attempt": str(attempt),
                "seed": run["seed"],
                "experiment_id": "CAPTURE",
                "method": "random",
            }
            command = _format_command(
                manifest["execution"]["command_template"], variables
            )
            environment = _stage_environment(
                capture_run, attempt_dir, run_config_path, result_path, attempt
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
                    raise StageError(
                        f"capture process failed: {observation.to_observation()}"
                    )
                tape = inspect_tape(tape_path)
                if tape.workload_seed != run["seed"]:
                    raise StageError("captured tape seed differs from the manifest")
                summary = read_json(result_path)
                if (
                    not isinstance(summary, dict)
                    or summary.get("run_complete") is not True
                ):
                    raise StageError("capture summary is incomplete")
                if summary.get("arrivals") != tape.event_count:
                    raise StageError(
                        "capture summary arrivals differ from tape event count"
                    )
                environment_path = result_path.parent / "environment.json"
                bundle = _semantic_environment(environment_path)
                duration = int(
                    experiment["workload"]["arrival_horizon_frames"]
                ) * float(run["simulation"]["frame_duration_seconds"])
                entry = {
                    **tape.to_dict(),
                    "kind": "base_steady",
                    "parent_sha256": None,
                    "transform": {"kind": "identity"},
                    "measured_arrival_rate_rps": tape.event_count / duration,
                    "capture_environment": bundle,
                    "capture_run_config_sha256": file_hash(run_config_path),
                    "capture_process_observation_sha256": file_hash(
                        attempt_dir / "process_observation.json"
                    ),
                    "workload_profile": copy.deepcopy(plan["workload_profile"]),
                    "provenance": copy.deepcopy(plan["provenance"]),
                }
                entry["provenance"]["measured_arrival_rate_rps"] = entry[
                    "measured_arrival_rate_rps"
                ]
                receipt = {
                    "schema_version": "NSE_BASE_TAPE_CAPTURE_RECEIPT_V2",
                    "key": key,
                    "seed": run["seed"],
                    "tape_sha256": tape.sha256,
                    "tape_event_count": tape.event_count,
                    "measured_arrival_rate_rps": entry["measured_arrival_rate_rps"],
                    "source_kind": "azure_trace_derived_empirical_cdf",
                    "source_is_direct_raw_trace": False,
                    "workload_frequency_profile": copy.deepcopy(
                        plan["workload_profile"]
                    ),
                    **bundle,
                    "run_config_sha256": file_hash(run_config_path),
                    "process_observation_sha256": entry[
                        "capture_process_observation_sha256"
                    ],
                }
                write_json_atomic(attempt_dir / "capture_receipt.json", receipt)
                entry["capture_receipt_path"] = str(
                    (canonical / "capture_receipt.json").resolve()
                )
                entry["capture_receipt_sha256"] = file_hash(
                    attempt_dir / "capture_receipt.json"
                )
            except (OSError, ValueError, StageError, ProtocolValidationError) as exc:
                issue = str(exc)

            metadata = {
                "schema_version": "NSE_STAGE_ATTEMPT_V1",
                "stage": "capture_base_tape",
                "key": key,
                "seed": run["seed"],
                "attempt": attempt,
                "status": "pass" if issue is None else "fail",
                "issue": issue,
                "command": command,
                "ended_at": utc_now(),
            }
            write_json_atomic(attempt_dir / "attempt.json", metadata)
            if issue is None:
                promotion = _promote_attempt_directory(
                    attempt_dir, canonical, expected_key=key
                )
                entry["path"] = str((canonical / "workload_tape.json").resolve())
                register_catalog_entry(catalog_path, key, entry)
                ledger.append(
                    "capture_canonicalized",
                    {
                        "key": key,
                        "attempt": attempt,
                        "path": str(canonical),
                        "tape_sha256": entry["sha256"],
                        "promotion": promotion,
                    },
                )
                results.append(
                    {
                        "key": key,
                        "status": "canonicalized",
                        "attempt": attempt,
                        "path": str(canonical),
                        "promotion": promotion,
                    }
                )
                passed = True
                break
            target = root / "quarantine" / key / f"attempt-{attempt:02d}"
            target.parent.mkdir(parents=True, exist_ok=True)
            promote_directory_exact(attempt_dir, target)
            ledger.append(
                "capture_quarantined",
                {"key": key, "attempt": attempt, "issue": issue, "path": str(target)},
            )
        if not passed:
            ledger.append("capture_blocked", {"key": key, "attempts_used": [1, 2, 3]})
            results.append(
                {"key": key, "status": "blocked", "attempts_used": [1, 2, 3]}
            )
    return results


def _welfare_pair_digest(path: Path, *, window_kind: str) -> tuple[int, str, str]:
    initial_digest = hashlib.sha256()
    final_digest = hashlib.sha256()
    seen: set[int] = set()
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                raise StageError(f"welfare metrics line {line_number} is blank")
            event = json.loads(raw)
            if not isinstance(event, dict) or event.get("kind") != window_kind:
                continue
            social = event.get("social")
            decision = event.get("decision")
            if not isinstance(social, dict) or not isinstance(decision, dict):
                raise StageError(
                    f"welfare metrics line {line_number} lacks pairing fields"
                )
            key = social.get("reference_state_key")
            if key is None:
                continue
            initial = decision.get("initial_assignment_hash")
            final = decision.get("assignment_hash")
            if (
                isinstance(key, bool)
                or not isinstance(key, int)
                or key < 0
                or isinstance(initial, bool)
                or not isinstance(initial, int)
                or initial < 0
                or isinstance(final, bool)
                or not isinstance(final, int)
                or final < 0
            ):
                raise StageError(
                    f"welfare metrics line {line_number} has invalid assignment pairing fields"
                )
            if key not in seen:
                seen.add(key)
                initial_digest.update(f"{key}:{initial}\n".encode("ascii"))
                final_digest.update(f"{key}:{initial}:{final}\n".encode("ascii"))
    return len(seen), initial_digest.hexdigest(), final_digest.hexdigest()


def build_references(
    manifest_path: Path,
    workspace: Path,
    catalog_path: Path,
    *,
    keys: Iterable[str] | None = None,
    run_ids: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    if not process_monitor_available():
        raise StageError("psutil is required for measured reference builds")
    manifest = load_and_validate_manifest(manifest_path)
    selected_keys = set(keys) if keys is not None else None
    selected_run_ids = set(run_ids) if run_ids is not None else None
    representatives: dict[str, dict[str, Any]] = {}
    for run in manifest["runs"]:
        dependency = run.get("reference_dependency")
        if dependency is None:
            continue
        if selected_keys is not None and dependency["key"] not in selected_keys:
            continue
        if selected_run_ids is not None and run["run_id"] not in selected_run_ids:
            continue
        representatives.setdefault(dependency["key"], run)
    if selected_keys is not None:
        missing = selected_keys - representatives.keys()
        if missing:
            raise StageError(f"unknown/unselected reference keys: {sorted(missing)}")
    if selected_run_ids is not None:
        found_ids = {run["run_id"] for run in representatives.values()}
        missing_ids = selected_run_ids - found_ids
        if missing_ids:
            raise StageError(
                f"run IDs have no reference dependency: {sorted(missing_ids)}"
            )

    root = workspace.resolve() / "reference_builds"
    ledger = Ledger(root / "ledger.jsonl")
    results: list[dict[str, Any]] = []
    for key in sorted(representatives):
        run = representatives[key]
        dependency = run["reference_dependency"]
        tape_hash = run["workload_tape"].get("sha256")
        if not isinstance(tape_hash, str):
            results.append(
                {
                    "key": key,
                    "status": "preflight_blocked",
                    "reason": "workload tape is not bound",
                }
            )
            continue
        qos = run["simulator_experiment"]["qos"]
        if qos.get("enabled") and any(
            qos.get(field) is None
            for field in (
                "latency_deadline_ms",
                "throughput_target_rps",
                "cost_budget_per_request",
            )
        ):
            results.append(
                {
                    "key": key,
                    "status": "preflight_blocked",
                    "reason": "balanced-QoS SLA thresholds are not frozen",
                }
            )
            continue
        tape_path = _resolve_manifest_path(manifest_path, run["workload_tape"]["path"])
        if not tape_path.is_file() or file_hash(tape_path) != tape_hash:
            results.append(
                {
                    "key": key,
                    "status": "preflight_blocked",
                    "reason": "workload tape is missing or changed",
                }
            )
            continue
        canonical = root / "canonical" / key
        if canonical.is_dir():
            results.append(
                {"key": key, "status": "canonical_exists", "path": str(canonical)}
            )
            continue
        used = _used_attempts(root, key)
        passed = False
        for attempt in range(1, 4):
            if attempt in used:
                continue
            attempt_dir = root / "partial" / key / f"attempt-{attempt:02d}"
            attempt_dir.mkdir(parents=True)
            build_run = copy.deepcopy(run)
            build_id = f"reference-build.{key}"
            build_run["run_id"] = build_id
            experiment = build_run["simulator_experiment"]
            experiment["run_id"] = build_id
            experiment["workload"]["tape_path"] = str(tape_path)
            experiment["output"]["root"] = str(
                (attempt_dir / "reviewer_records").resolve()
            )
            table_path = attempt_dir / "offline_social_reference_build.jsonl"
            experiment["reference"] = {
                "mode": "build",
                "table_path": "",
                "build_output_path": str(table_path.resolve()),
            }
            run_config_path = attempt_dir / "run_config.json"
            write_json_atomic(run_config_path, build_run)
            result_path = attempt_dir / "reviewer_records" / build_id / "summary.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            variables = {
                "python": sys.executable,
                "run_config": str(run_config_path),
                "result_path": str(result_path),
                "partial_dir": str(attempt_dir),
                "run_id": build_id,
                "attempt": str(attempt),
                "seed": run["seed"],
                "experiment_id": "REFERENCE_BUILD",
                "method": run["method"],
            }
            command = _format_command(
                manifest["execution"]["command_template"], variables
            )
            environment = _stage_environment(
                build_run, attempt_dir, run_config_path, result_path, attempt
            )
            environment["PROTOCOL_WORKLOAD_TAPE"] = str(tape_path)
            observation = run_monitored(
                command,
                cwd=_execution_cwd(manifest),
                environment=environment,
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
                    raise StageError(
                        f"reference build process failed: {observation.to_observation()}"
                    )
                if table_path.with_name(table_path.name + ".partial").exists():
                    raise StageError("reference build retained a partial table")
                table = inspect_reference_table(table_path)
                summary = read_json(result_path)
                if (
                    not isinstance(summary, dict)
                    or summary.get("run_complete") is not True
                ):
                    raise StageError("reference build summary is incomplete")
                if summary.get("arrivals") != run["workload_tape"]["event_count"]:
                    raise StageError("reference build arrivals differ from the tape")
                metrics_name = (
                    "nash_metrics.jsonl"
                    if run["method"] == "sche_nash"
                    else "welfare_metrics.jsonl"
                )
                window_kind = (
                    "window" if run["method"] == "sche_nash" else "welfare_window"
                )
                welfare_path = result_path.parent / metrics_name
                if not welfare_path.is_file():
                    raise StageError(f"reference build did not produce {metrics_name}")
                pair_count, pair_digest, assignment_digest = _welfare_pair_digest(
                    welfare_path, window_kind=window_kind
                )
                if (
                    pair_count != table.line_count
                    or pair_digest != table.state_pair_sequence_sha256
                ):
                    raise StageError(
                        "reference table and build-window state/assignment sequences differ"
                    )
                receipt = {
                    "schema_version": "NSE_REFERENCE_BUILD_RECEIPT_V1",
                    "reference_key": key,
                    "build_spec_hash": dependency["build_spec_hash"],
                    "workload_tape_sha256": tape_hash,
                    "table_sha256": table.sha256,
                    "table_bytes": table.bytes,
                    "table_line_count": table.line_count,
                    "state_pair_sequence_sha256": table.state_pair_sequence_sha256,
                    "assignment_sequence_sha256": assignment_digest,
                    "completed": summary.get("completed"),
                    "summary_sha256": file_hash(result_path),
                    "welfare_observation_file": metrics_name,
                    "welfare_observation_sha256": file_hash(welfare_path),
                    "process_observation_sha256": file_hash(observation_path),
                    "run_config_sha256": file_hash(run_config_path),
                    "built_at": utc_now(),
                }
                receipt_path = attempt_dir / "reference_build_receipt.json"
                write_json_atomic(receipt_path, receipt)
            except (
                OSError,
                ValueError,
                StageError,
                ProtocolValidationError,
                json.JSONDecodeError,
            ) as exc:
                issue = str(exc)
            write_json_atomic(
                attempt_dir / "attempt.json",
                {
                    "schema_version": "NSE_STAGE_ATTEMPT_V1",
                    "stage": "reference_build",
                    "key": key,
                    "seed": run["seed"],
                    "attempt": attempt,
                    "status": "pass" if issue is None else "fail",
                    "issue": issue,
                    "command": command,
                    "ended_at": utc_now(),
                },
            )
            if issue is None:
                promotion = _promote_attempt_directory(
                    attempt_dir, canonical, expected_key=key
                )
                register_reference_build(
                    catalog_path,
                    key,
                    canonical / "offline_social_reference_build.jsonl",
                    canonical / "reference_build_receipt.json",
                )
                ledger.append(
                    "reference_build_canonicalized",
                    {
                        "key": key,
                        "attempt": attempt,
                        "path": str(canonical),
                        "table_sha256": table.sha256,
                        "promotion": promotion,
                    },
                )
                results.append(
                    {
                        "key": key,
                        "status": "canonicalized",
                        "attempt": attempt,
                        "path": str(canonical),
                        "promotion": promotion,
                    }
                )
                passed = True
                break
            target = root / "quarantine" / key / f"attempt-{attempt:02d}"
            target.parent.mkdir(parents=True, exist_ok=True)
            promote_directory_exact(attempt_dir, target)
            ledger.append(
                "reference_build_quarantined",
                {"key": key, "attempt": attempt, "issue": issue, "path": str(target)},
            )
        if not passed:
            ledger.append(
                "reference_build_blocked", {"key": key, "attempts_used": [1, 2, 3]}
            )
            results.append(
                {"key": key, "status": "blocked", "attempts_used": [1, 2, 3]}
            )
    return results
