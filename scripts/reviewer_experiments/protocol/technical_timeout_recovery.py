"""Result-blind technical timeout recovery for formal reviewer runs.

This module deliberately keeps recovery planning and merging separate from the
normal protocol runner.  A plan is derived only from append-only ledger events
and retained QC/process evidence; result metrics are never opened or consulted.
The plan then describes a *scoped* execution override (a larger wall-clock
timeout and adapter request timeout) for the exact run IDs that have already
been blocked by two identical timeout failures.  Recovery outputs live in an
independent workspace and can be merged into a read-only composite product
without changing the source workspace.

The command-line plumbing is intentionally kept in ``cli.py``.  Public helper
names below are stable so a CLI or an external audit script can use the same
fail-closed implementation.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping

from .ledger import Ledger
from .qc import technical_failure_signature
from .schema import ProtocolValidationError, load_and_validate_manifest
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


TECHNICAL_TIMEOUT_RECOVERY_SCHEMA = "NSE_TECHNICAL_TIMEOUT_RECOVERY_V1"
TECHNICAL_TIMEOUT_RECOVERY_MANIFEST_SCHEMA = (
    "NSE_TECHNICAL_TIMEOUT_RECOVERY_MANIFEST_V1"
)
TECHNICAL_TIMEOUT_RECOVERY_COMPOSITE_SCHEMA = (
    "NSE_TECHNICAL_TIMEOUT_RECOVERY_COMPOSITE_V1"
)
TECHNICAL_TIMEOUT_RECOVERY_RECEIPT_SCHEMA = (
    "NSE_TECHNICAL_TIMEOUT_RECOVERY_MERGE_RECEIPT_V1"
)
TECHNICAL_TIMEOUT_RUNTIME_BUNDLE_SCHEMA = "NSE_TECHNICAL_TIMEOUT_RUNTIME_BUNDLE_V1"
RECOVERY_BLOCK_REASON = "repeated_technical_failure_signature"
RECOVERY_TIER_1 = 1
RECOVERY_TIER_2 = 2
_RECOVERY_PROFILES = {
    RECOVERY_TIER_1: {
        "tier": RECOVERY_TIER_1,
        "timeout_seconds": 3600.0,
        "adapter_request_timeout_seconds": 3590.0,
    },
    RECOVERY_TIER_2: {
        "tier": RECOVERY_TIER_2,
        "timeout_seconds": 7200.0,
        "adapter_request_timeout_seconds": 7190.0,
    },
}
DEFAULT_TIMEOUT_SECONDS = _RECOVERY_PROFILES[RECOVERY_TIER_1]["timeout_seconds"]
DEFAULT_ADAPTER_REQUEST_TIMEOUT_SECONDS = _RECOVERY_PROFILES[RECOVERY_TIER_1][
    "adapter_request_timeout_seconds"
]
_BATCH_TERMINAL_EVENTS = frozenset({"batch_finished"})
_RECOVERY_RESULT_STATUSES = frozenset(
    {"canonicalized", "canonical_exists", "blocked", "preflight_blocked"}
)
# Frozen identity observed in the original E2 formal batch.  Planning keeps
# this opt-in (``expected_runtime_identity``) so the helper remains testable on
# synthetic manifests, while the production CLI can pass this exact constant.
E2_ORIGINAL_RUNTIME_IDENTITY = {
    "git_commit": "42bc59e72ba239a140f58b7fd27abad4b4dc8730",
    "adapter_binary_sha256": "ee07c609f50906acdb89c805cf5ff9204d3120da11c37ca45fac404659c8e0d5",
    "python_executable_sha256": "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384",
    "cargo_lock_sha256": "548623b5a8f2a7883928d5419008bd3af4625eab80110f4280d1092356dfe975",
}


class TechnicalTimeoutRecoveryError(ValueError):
    """Raised when recovery evidence or lineage is incomplete or inconsistent."""


def _fail(message: str) -> None:
    raise TechnicalTimeoutRecoveryError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _hash_without(document: Mapping[str, Any], field: str) -> str:
    payload = copy.deepcopy(dict(document))
    payload.pop(field, None)
    return object_hash(payload)


def _self_hash(document: Mapping[str, Any], field: str) -> str:
    value = dict(document)
    claimed = value.pop(field, None)
    actual = object_hash(value)
    if claimed is not None and claimed != actual:
        _fail(f"{field} does not match document content")
    return actual


def _fixed_recovery_profile(tier: int) -> dict[str, Any]:
    try:
        profile = _RECOVERY_PROFILES[int(tier)]
    except (KeyError, TypeError, ValueError):
        _fail(f"unsupported technical timeout recovery tier: {tier!r}")
    return copy.deepcopy(profile)


def _normalise_execution_override(
    override: Mapping[str, Any],
    *,
    source_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    _require(
        isinstance(override, Mapping), "recovery plan execution_override is missing"
    )
    timeout = override.get("timeout_seconds")
    adapter_timeout = override.get("adapter_request_timeout_seconds")
    _require(
        isinstance(timeout, (int, float)) and not isinstance(timeout, bool),
        "recovery timeout must be numeric",
    )
    _require(
        isinstance(adapter_timeout, (int, float))
        and not isinstance(adapter_timeout, bool),
        "adapter request timeout must be numeric",
    )
    timeout_value = float(timeout)
    adapter_value = float(adapter_timeout)
    _require(timeout_value > 0, "recovery timeout must be positive")
    _require(adapter_value > 0, "adapter request timeout must be positive")
    _require(
        adapter_value <= timeout_value,
        "adapter request timeout must not exceed recovery timeout",
    )
    matched: dict[str, Any] | None = None
    for profile in _RECOVERY_PROFILES.values():
        if timeout_value == float(
            profile["timeout_seconds"]
        ) and adapter_value == float(profile["adapter_request_timeout_seconds"]):
            matched = copy.deepcopy(profile)
            break
    _require(
        matched is not None,
        "technical timeout recovery override must match one frozen supported profile",
    )
    if source_timeout_seconds is not None:
        _require(
            timeout_value >= float(source_timeout_seconds),
            "recovery timeout may only increase the frozen timeout",
        )
    scope = override.get("scope")
    _require(
        scope == "selected_run_ids_only",
        "technical timeout recovery scope must stay selected_run_ids_only",
    )
    result = {
        "tier": matched["tier"],
        "source_timeout_seconds": (
            float(source_timeout_seconds)
            if source_timeout_seconds is not None
            else float(override.get("source_timeout_seconds", 0))
        ),
        "timeout_seconds": timeout_value,
        "adapter_request_timeout_seconds": adapter_value,
        "scope": scope,
    }
    for key in ("command_template_change", "command_template_append"):
        if key in override:
            result[key] = copy.deepcopy(override[key])
    return result


def _absolute(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"{label} cannot be read: {path}: {exc}")
    _require(isinstance(value, dict), f"{label} must be a JSON object: {path}")
    return value


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_object(path, "source manifest")
    claimed = manifest.get("manifest_hash")
    _require(isinstance(claimed, str), "source manifest_hash is missing")
    _require(
        object_hash(
            {key: value for key, value in manifest.items() if key != "manifest_hash"}
        )
        == claimed,
        "source manifest_hash does not match manifest bytes",
    )
    runs = manifest.get("runs")
    _require(
        isinstance(runs, list) and runs,
        "source manifest runs must be a non-empty array",
    )
    run_ids: set[str] = set()
    for index, run in enumerate(runs):
        _require(
            isinstance(run, dict), f"source manifest runs[{index}] must be an object"
        )
        run_id = run.get("run_id")
        _require(
            isinstance(run_id, str) and run_id, f"source run {index} has no run_id"
        )
        _require(
            run_id not in run_ids, f"source manifest has duplicate run_id {run_id}"
        )
        run_ids.add(run_id)
        _require(
            isinstance(run.get("run_spec_hash"), str),
            f"source run {run_id} has no run_spec_hash",
        )
    execution = manifest.get("execution")
    _require(isinstance(execution, dict), "source manifest execution must be an object")
    timeout = execution.get("timeout_seconds")
    _require(
        isinstance(timeout, (int, float)) and not isinstance(timeout, bool),
        "source execution timeout is invalid",
    )
    _require(float(timeout) > 0, "source execution timeout must be positive")
    return manifest


def _validate_formal_e2_source(path: Path) -> dict[str, Any]:
    """Require the complete schema-validated formal E2 execution shard."""

    try:
        manifest = load_and_validate_manifest(path)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ProtocolValidationError,
    ) as exc:
        _fail(f"source is not a valid formal E2 manifest: {path}: {exc}")
    marker = manifest.get("formal_e2_weak_scaling_shard")
    _require(
        manifest.get("formal_results_eligible") is True,
        "technical timeout recovery requires formal_results_eligible=true",
    )
    _require(
        isinstance(marker, Mapping)
        and marker.get("schema_version") == "NSE_FORMAL_E2_WEAK_SCALING_SHARD_V1",
        "technical timeout recovery requires the sealed formal E2 shard",
    )
    _require(
        len(manifest.get("runs", [])) == 600
        and all(run.get("experiment_id") == "E2" for run in manifest["runs"]),
        "technical timeout recovery requires the exact 600-run formal E2 set",
    )
    _require(
        marker.get("selected_run_count") == 600,
        "formal E2 shard marker does not bind the exact 600-run set",
    )
    return manifest


def _resolve_formal_workspace(base_workspace: Path | str) -> Path:
    """Resolve either ``formal-runs`` itself or its parent directory."""

    candidate = _absolute(base_workspace)
    if (candidate / "ledger.jsonl").is_file() or any(
        (candidate / name).is_dir() for name in ("canonical", "quarantine", "partial")
    ):
        return candidate
    nested = candidate / "formal-runs"
    if (nested / "ledger.jsonl").is_file() or any(
        (nested / name).is_dir() for name in ("canonical", "quarantine", "partial")
    ):
        return nested
    # Keep the requested path in the plan even before the independent workspace
    # exists.  Planning will fail below if the source ledger is absent.
    return candidate


def _ledger_evidence(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(path.is_file(), f"source ledger is missing: {path}")
    try:
        ledger = Ledger(path)
        events = list(ledger.iter_events() or ())
        sequence, last_hash = ledger.verify()
    except (OSError, ProtocolValidationError) as exc:
        _fail(f"source ledger is invalid: {path}: {exc}")
    _require(
        sequence == len(events), "source ledger sequence does not match event count"
    )
    return events, {
        "path": str(path.resolve()),
        "file_sha256": file_hash(path),
        "sequence": sequence,
        "last_event_hash": last_hash,
    }


def _assert_ordinary_batch_quiescent(
    events: Iterable[Mapping[str, Any]],
    base: Path,
    manifest_hash: str,
    manifest_run_count: int,
) -> dict[str, Any]:
    """Refuse planning while an ordinary batch or partial attempt is active."""

    latest_started: Mapping[str, Any] | None = None
    terminal_after_start: Mapping[str, Any] | None = None
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if (
            event.get("event_type") == "batch_started"
            and payload.get("manifest_hash") == manifest_hash
        ):
            latest_started = event
            terminal_after_start = None
            continue
        if (
            latest_started is not None
            and event.get("event_type") in _BATCH_TERMINAL_EVENTS
            and payload.get("manifest_hash") == manifest_hash
            and int(event.get("sequence", 0)) > int(latest_started.get("sequence", 0))
        ):
            terminal_after_start = event
    _require(
        latest_started is not None,
        "source ledger has no ordinary batch_started boundary",
    )
    _require(
        terminal_after_start is not None,
        "source ordinary batch has no later successful batch_finished event; refusing to seal recovery plan",
    )
    terminal_payload = terminal_after_start.get("payload")
    _require(
        isinstance(terminal_payload, Mapping),
        "source batch_finished payload is invalid",
    )
    _require(
        terminal_payload.get("selected_run_count") == manifest_run_count,
        "source batch_finished does not cover the complete manifest run set",
    )
    counts: list[int] = []
    for field in ("canonicalized", "blocked", "preflight_blocked"):
        value = terminal_payload.get(field)
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            f"source batch_finished {field} count is invalid",
        )
        counts.append(value)
    _require(
        sum(counts) == manifest_run_count,
        "source batch_finished disposition counts do not cover every run",
    )
    _require(
        terminal_payload.get("preflight_blocked") == 0,
        "source batch_finished contains preflight blocks; ordinary work must be repaired first",
    )

    partial_root = base / "partial"
    active_entries: list[str] = []
    if partial_root.is_dir():
        for path in partial_root.iterdir():
            if path.is_file():
                active_entries.append(path.name)
                continue
            if path.is_dir() and any(path.iterdir()):
                active_entries.append(path.name)
    _require(
        not active_entries,
        "source workspace has nonempty partial attempt state: "
        + ", ".join(sorted(active_entries)[:10]),
    )
    return {
        "kind": "ordinary_batch",
        "latest_batch_started_sequence": latest_started.get("sequence"),
        "latest_batch_started_event_hash": latest_started.get("event_hash"),
        "terminal_event_type": terminal_after_start.get("event_type"),
        "terminal_sequence": terminal_after_start.get("sequence"),
        "terminal_event_hash": terminal_after_start.get("event_hash"),
        "nonempty_partial_count": 0,
    }


def _assert_recovery_batch_quiescent(
    events: list[Mapping[str, Any]],
    base: Path,
    manifest_hash: str,
    *,
    expected_recovery_plan_sha256: str | None = None,
) -> dict[str, Any]:
    starts = [
        event
        for event in events
        if event.get("event_type") == "technical_timeout_recovery_started"
    ]
    finishes = [
        event
        for event in events
        if event.get("event_type") == "technical_timeout_recovery_finished"
    ]
    _require(
        len(starts) == 1 and len(finishes) == 1,
        "source technical recovery workspace must contain exactly one sealed start/finish pair",
    )
    start = starts[0]
    finish = finishes[0]
    start_payload = start.get("payload")
    finish_payload = finish.get("payload")
    _require(
        isinstance(start_payload, Mapping) and isinstance(finish_payload, Mapping),
        "source technical recovery lifecycle payload is invalid",
    )
    for payload, label in ((start_payload, "start"), (finish_payload, "finish")):
        _require(
            payload.get("schema_version") == TECHNICAL_TIMEOUT_RECOVERY_SCHEMA,
            f"source technical recovery {label} schema is invalid",
        )
        _require(
            payload.get("source_manifest_hash") == manifest_hash,
            f"source technical recovery {label} manifest hash mismatch",
        )
        _require(
            payload.get("metrics_consulted") is False,
            f"source technical recovery {label} metrics_consulted must be false",
        )
    if expected_recovery_plan_sha256 is not None:
        _require(
            start_payload.get("plan_sha256") == expected_recovery_plan_sha256
            and finish_payload.get("plan_sha256") == expected_recovery_plan_sha256,
            "source technical recovery plan hash differs from the sealed upstream plan",
        )
    _require(
        finish_payload.get("started_event_hash") == start.get("event_hash"),
        "source technical recovery finish does not bind the unique start event",
    )
    _require(
        int(finish.get("sequence", 0)) == len(events),
        "source technical recovery finish must be the terminal ledger event",
    )
    run_ids = start_payload.get("run_ids")
    _require(
        isinstance(run_ids, list)
        and run_ids
        and all(isinstance(item, str) and item for item in run_ids)
        and len(run_ids) == len(set(run_ids)),
        "source technical recovery run_ids are invalid",
    )
    _require(
        finish_payload.get("run_ids") == sorted(run_ids),
        "source technical recovery finish run_ids differ from the unique sealed start",
    )
    selected_run_count = start_payload.get("selected_run_count")
    _require(
        isinstance(selected_run_count, int)
        and selected_run_count == len(run_ids)
        and finish_payload.get("selected_run_count") == selected_run_count,
        "source technical recovery selected_run_count is inconsistent",
    )
    profile = _normalise_execution_override(
        {
            "timeout_seconds": start_payload.get("timeout_seconds"),
            "adapter_request_timeout_seconds": start_payload.get(
                "adapter_request_timeout_seconds"
            ),
            "scope": "selected_run_ids_only",
        }
    )
    finish_profile = _normalise_execution_override(
        {
            "timeout_seconds": finish_payload.get("timeout_seconds"),
            "adapter_request_timeout_seconds": finish_payload.get(
                "adapter_request_timeout_seconds"
            ),
            "scope": "selected_run_ids_only",
        }
    )
    _require(
        finish_profile == profile,
        "source technical recovery start/finish execution overrides differ",
    )
    counts: list[int] = []
    for field in ("canonicalized", "blocked", "preflight_blocked"):
        value = finish_payload.get(field)
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            f"source technical recovery {field} count is invalid",
        )
        counts.append(value)
    _require(
        sum(counts) == selected_run_count,
        "source technical recovery disposition counts do not cover the sealed run set",
    )
    partial_root = base / "partial"
    active_entries: list[str] = []
    if partial_root.is_dir():
        for path in partial_root.iterdir():
            if path.is_file():
                active_entries.append(path.name)
                continue
            if path.is_dir() and any(path.iterdir()):
                active_entries.append(path.name)
    _require(
        not active_entries,
        "source technical recovery workspace has nonempty partial attempt state: "
        + ", ".join(sorted(active_entries)[:10]),
    )
    return {
        "kind": "technical_timeout_recovery",
        "plan_sha256": start_payload.get("plan_sha256"),
        "started_event_hash": start.get("event_hash"),
        "finished_event_hash": finish.get("event_hash"),
        "selected_run_count": selected_run_count,
        "run_ids": sorted(run_ids),
        "timeout_seconds": profile["timeout_seconds"],
        "adapter_request_timeout_seconds": profile["adapter_request_timeout_seconds"],
        "nonempty_partial_count": 0,
    }


def _assert_selection_workspace_quiescent(
    events: list[Mapping[str, Any]],
    base: Path,
    manifest_hash: str,
    manifest_run_count: int,
    *,
    expected_recovery_plan_sha256: str | None = None,
) -> dict[str, Any]:
    if any(
        event.get("event_type") == "technical_timeout_recovery_started"
        for event in events
    ):
        return _assert_recovery_batch_quiescent(
            events,
            base,
            manifest_hash,
            expected_recovery_plan_sha256=expected_recovery_plan_sha256,
        )
    return _assert_ordinary_batch_quiescent(
        events,
        base,
        manifest_hash,
        manifest_run_count,
    )


def _runtime_identity_from_audit(
    audit: Mapping[str, Any], *, require_adapter: bool = True
) -> dict[str, Any]:
    software = audit.get("software_environment")
    _require(
        isinstance(software, Mapping), "timeout evidence lacks software_environment"
    )
    git = software.get("git")
    python = software.get("python")
    cargo_lock = software.get("cargo_lock")
    adapter = audit.get("adapter_binary")
    _require(isinstance(git, Mapping), "timeout evidence lacks git provenance")
    _require(isinstance(python, Mapping), "timeout evidence lacks Python provenance")
    _require(
        isinstance(cargo_lock, Mapping), "timeout evidence lacks Cargo.lock provenance"
    )
    if require_adapter:
        _require(
            isinstance(adapter, Mapping), "timeout evidence lacks adapter provenance"
        )
    git_commit = git.get("commit")
    binary_sha = (
        (adapter.get("observed_sha256") or adapter.get("verified_sha256"))
        if isinstance(adapter, Mapping)
        else None
    )
    python_sha = python.get("executable_sha256")
    cargo_sha = cargo_lock.get("sha256")
    for name, value in (
        ("git_commit", git_commit),
        ("python_executable_sha256", python_sha),
        ("cargo_lock_sha256", cargo_sha),
    ):
        _require(isinstance(value, str) and value, f"timeout evidence has no {name}")
    # Keep both descriptive and legacy-friendly keys.  The four canonical
    # fields are what merge and downstream audit code compare.
    return {
        "git_commit": git_commit,
        "adapter_binary_sha256": binary_sha,
        "python_executable_sha256": python_sha,
        "cargo_lock_sha256": cargo_sha,
        "runtime_git_commit": git_commit,
        "runtime_binary_sha256": binary_sha,
    }


def _normalise_runtime_identity(
    value: Mapping[str, Any], *, require_binary: bool = True
) -> dict[str, Any]:
    git = value.get("git_commit", value.get("runtime_git_commit"))
    binary = value.get(
        "adapter_binary_sha256",
        value.get("runtime_binary_sha256", value.get("binary_sha256")),
    )
    python = value.get("python_executable_sha256")
    cargo = value.get("cargo_lock_sha256")
    result = {
        "git_commit": git,
        "adapter_binary_sha256": binary,
        "python_executable_sha256": python,
        "cargo_lock_sha256": cargo,
        "runtime_git_commit": git,
        "runtime_binary_sha256": binary,
    }
    required_values = (
        result["git_commit"],
        result["python_executable_sha256"],
        result["cargo_lock_sha256"],
    )
    _require(
        all(isinstance(item, str) and item for item in required_values),
        "runtime identity is incomplete",
    )
    if require_binary:
        _require(
            isinstance(result["adapter_binary_sha256"], str)
            and bool(result["adapter_binary_sha256"]),
            "runtime identity lacks adapter binary hash",
        )
    return result


def create_runtime_bundle_receipt(
    bundle_root: Path | str,
    receipt_path: Path | str,
    files: Iterable[Path | str],
    *,
    runtime_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Hash the exact implementation/runtime bytes used by recovery.

    ``files`` is deliberately explicit: a caller running from a patched clone
    must name every patch-bearing file, rather than relying on a broad mutable
    directory snapshot.  The receipt is self-hashed and can be independently
    copied into the sealed recovery workspace.
    """

    root = _absolute(bundle_root)
    target = _absolute(receipt_path)
    _require(root.is_dir(), f"runtime bundle root is missing: {root}")
    _require(
        not target.exists(), f"refusing to overwrite runtime bundle receipt: {target}"
    )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in files:
        relative = Path(raw)
        _require(
            not relative.is_absolute(),
            "runtime bundle receipt paths must be relative to bundle_root",
        )
        candidate = (root / relative).resolve()
        _require(
            candidate.is_relative_to(root) and candidate.is_file(),
            f"runtime bundle file is missing or escapes root: {raw}",
        )
        key = candidate.relative_to(root).as_posix()
        _require(key not in seen, f"runtime bundle receipt repeats {key}")
        seen.add(key)
        rows.append(
            {
                "path": key,
                "sha256": file_hash(candidate),
                "bytes": candidate.stat().st_size,
            }
        )
    _require(rows, "runtime bundle receipt must name at least one file")
    payload: dict[str, Any] = {
        "schema_version": TECHNICAL_TIMEOUT_RUNTIME_BUNDLE_SCHEMA,
        "created_at": utc_now(),
        "bundle_root": str(root),
        "files": sorted(rows, key=lambda item: item["path"]),
    }
    if runtime_identity is not None:
        payload["runtime_identity"] = _normalise_runtime_identity(runtime_identity)
    payload["receipt_sha256"] = object_hash(payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(target, payload)
    return payload


def _load_runtime_bundle_receipt(
    receipt_path: Path | str,
    *,
    expected_runtime_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    path = _absolute(receipt_path)
    receipt = _load_object(path, "runtime bundle receipt")
    _require(
        receipt.get("schema_version") == TECHNICAL_TIMEOUT_RUNTIME_BUNDLE_SCHEMA,
        "unsupported runtime bundle receipt schema",
    )
    _self_hash(receipt, "receipt_sha256")
    root = _absolute(str(receipt.get("bundle_root", "")))
    _require(root.is_dir(), f"runtime bundle root is missing: {root}")
    files = receipt.get("files")
    _require(
        isinstance(files, list) and files, "runtime bundle receipt files are missing"
    )
    seen: set[str] = set()
    for item in files:
        _require(
            isinstance(item, Mapping), "runtime bundle receipt file entry is invalid"
        )
        relative = item.get("path")
        _require(
            isinstance(relative, str) and relative,
            "runtime bundle receipt path is invalid",
        )
        candidate = (root / relative).resolve()
        key = (
            candidate.relative_to(root).as_posix()
            if candidate.is_relative_to(root)
            else ""
        )
        _require(
            key == relative.replace("\\", "/"),
            "runtime bundle receipt path escapes root",
        )
        _require(key not in seen, f"runtime bundle receipt repeats {key}")
        seen.add(key)
        _require(candidate.is_file(), f"runtime bundle file is missing: {candidate}")
        _require(
            item.get("sha256") == file_hash(candidate),
            f"runtime bundle hash mismatch: {relative}",
        )
        _require(
            item.get("bytes") == candidate.stat().st_size,
            f"runtime bundle byte count mismatch: {relative}",
        )
    if expected_runtime_identity is not None:
        recorded = receipt.get("runtime_identity")
        _require(
            isinstance(recorded, Mapping),
            "runtime bundle receipt lacks runtime identity",
        )
        _require(
            _normalise_runtime_identity(recorded)
            == _normalise_runtime_identity(expected_runtime_identity),
            "runtime bundle receipt runtime identity mismatch",
        )
    return receipt


def _runtime_bundle_binding(
    receipt_path: Path | str, receipt: Mapping[str, Any]
) -> dict[str, Any]:
    path = _absolute(receipt_path)
    return {
        "state": "bound",
        "receipt_path": str(path),
        "receipt_file_sha256": file_hash(path),
        "receipt_sha256": receipt["receipt_sha256"],
        "bundle_root": receipt["bundle_root"],
        "files": copy.deepcopy(receipt["files"]),
    }


def _attempt_number(path: Path) -> int | None:
    if not path.name.startswith("attempt-"):
        return None
    try:
        return int(path.name.removeprefix("attempt-"))
    except ValueError:
        return None


def _timeout_attempt_evidence(
    run: Mapping[str, Any], attempt_dir: Path, source_manifest_hash: str
) -> dict[str, Any]:
    attempt_number = _attempt_number(attempt_dir)
    _require(
        attempt_number is not None, f"invalid timeout attempt directory: {attempt_dir}"
    )
    qc_path = attempt_dir / "qc_report.json"
    process_path = attempt_dir / "process_observation.json"
    metadata_path = attempt_dir / "attempt.json"
    audit_path = attempt_dir / "manifest.json"
    for path, label in (
        (qc_path, "QC report"),
        (process_path, "process observation"),
        (metadata_path, "attempt metadata"),
        (audit_path, "audit manifest"),
    ):
        _require(path.is_file(), f"timeout attempt is missing {label}: {path}")
    qc = _load_object(qc_path, "timeout QC report")
    process = _load_object(process_path, "timeout process observation")
    metadata = _load_object(metadata_path, "timeout attempt metadata")
    audit = _load_object(audit_path, "timeout audit manifest")
    _require(
        qc.get("passed") is False, f"attempt {attempt_dir} is not a failed QC attempt"
    )
    _require(
        qc.get("classification") == "timeout",
        f"attempt {attempt_dir} is not classified as timeout",
    )
    issues = qc.get("issues")
    _require(
        isinstance(issues, list)
        and any(
            isinstance(issue, Mapping) and issue.get("code") == "timeout"
            for issue in issues
        ),
        f"attempt {attempt_dir} lacks a timeout QC issue",
    )
    _require(
        process.get("timed_out") is True,
        f"attempt {attempt_dir} process evidence is not timed_out",
    )
    _require(
        metadata.get("run_id") == run.get("run_id"),
        f"attempt {attempt_dir} run_id mismatch",
    )
    _require(
        metadata.get("run_spec_hash") == run.get("run_spec_hash"),
        f"attempt {attempt_dir} run_spec_hash mismatch",
    )
    _require(
        metadata.get("attempt") == attempt_number,
        f"attempt {attempt_dir} attempt number mismatch",
    )
    _require(
        audit.get("schema_version") == "NSE_RUN_AUDIT_MANIFEST_V1",
        f"attempt {attempt_dir} audit schema is invalid",
    )
    audit_hash = audit.get("audit_manifest_hash")
    _require(
        isinstance(audit_hash, str)
        and _hash_without(audit, "audit_manifest_hash") == audit_hash,
        f"attempt {attempt_dir} audit hash mismatch",
    )
    protocol = audit.get("protocol_manifest")
    _require(
        isinstance(protocol, Mapping),
        f"attempt {attempt_dir} audit protocol provenance is missing",
    )
    _require(
        protocol.get("manifest_hash") == source_manifest_hash,
        f"attempt {attempt_dir} source manifest hash mismatch",
    )
    signature = technical_failure_signature(qc)
    _require(
        isinstance(signature, str),
        f"attempt {attempt_dir} has no stable technical failure signature",
    )
    recorded_signature = qc.get("failure_signature")
    if recorded_signature is not None:
        _require(
            recorded_signature == signature,
            f"attempt {attempt_dir} recorded failure signature mismatch",
        )
    # A timed-out adapter may be killed before it can write its normal adapter
    # observation.  The immutable simulator binary identity is therefore
    # filled from a completed canonical run during selection; the timeout
    # evidence still binds git/Python/Cargo provenance here.
    identity = _runtime_identity_from_audit(audit, require_adapter=False)
    return {
        "attempt": attempt_number,
        "failure_signature": signature,
        "qc_report": {
            "path": str(qc_path.resolve()),
            "sha256": file_hash(qc_path),
        },
        "process_observation": {
            "path": str(process_path.resolve()),
            "sha256": file_hash(process_path),
            "timed_out": True,
            "duration_seconds": process.get("duration_seconds"),
            "exit_code": process.get("exit_code"),
        },
        "attempt_metadata": {
            "path": str(metadata_path.resolve()),
            "sha256": file_hash(metadata_path),
        },
        "audit_manifest": {
            "path": str(audit_path.resolve()),
            "sha256": file_hash(audit_path),
        },
        "runtime_identity": identity,
    }


def _latest_block_events(
    events: Iterable[Mapping[str, Any]]
) -> dict[str, Mapping[str, Any]]:
    """Return only runs whose latest ledger event is the sealed block event."""

    latest: dict[str, Mapping[str, Any]] = {}
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        run_id = payload.get("run_id")
        if isinstance(run_id, str):
            latest[run_id] = event
    return {
        run_id: event
        for run_id, event in latest.items()
        if event.get("event_type") == "run_blocked"
    }


def _discover_runtime_identity(
    base: Path, manifest: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Read the adapter binary hash from retained canonical audit evidence."""

    canonical_root = base / "canonical"
    if not canonical_root.is_dir():
        return None
    discovered: dict[str, Any] | None = None
    for run in manifest.get("runs", []):
        if not isinstance(run, Mapping):
            continue
        audit_path = canonical_root / str(run.get("run_id")) / "manifest.json"
        if not audit_path.is_file():
            continue
        try:
            audit = _load_object(audit_path, "canonical audit manifest")
            identity = _runtime_identity_from_audit(audit, require_adapter=True)
        except TechnicalTimeoutRecoveryError:
            continue
        normalized = _normalise_runtime_identity(identity)
        if discovered is None:
            discovered = normalized
        else:
            _require(
                normalized == discovered,
                "retained canonical audits disagree on frozen runtime identity",
            )
    return discovered


def select_repeated_timeout_blocks(
    manifest_path: Path | str,
    base_workspace: Path | str,
    *,
    expected_count: int | None = 7,
    expected_runtime_identity: Mapping[str, Any] | None = None,
    expected_recovery_plan_sha256: str | None = None,
) -> dict[str, Any]:
    """Select blocked runs using only ledger/QC/process evidence.

    The returned object is evidence, not a performance-based filter.  A run is
    eligible only when the latest ledger block has the exact repeated-failure
    reason, its two consecutive retained attempts are both timeout failures
    with the same stable signature, and neither a canonical nor partial result
    currently exists.
    """

    manifest_path = _absolute(manifest_path)
    base = _resolve_formal_workspace(base_workspace)
    manifest = _load_manifest(manifest_path)
    events, ledger = _ledger_evidence(base / "ledger.jsonl")
    quiescent = _assert_selection_workspace_quiescent(
        events,
        base,
        manifest["manifest_hash"],
        len(manifest["runs"]),
        expected_recovery_plan_sha256=expected_recovery_plan_sha256,
    )
    runs_by_id = {run["run_id"]: run for run in manifest["runs"]}
    blocks = _latest_block_events(events)
    selected: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    for run_id in sorted(blocks):
        event = blocks[run_id]
        payload = event.get("payload")
        assert isinstance(payload, Mapping)
        if payload.get("reason") != RECOVERY_BLOCK_REASON:
            continue
        run = runs_by_id.get(run_id)
        _require(
            run is not None,
            f"ledger block names run absent from source manifest: {run_id}",
        )
        _require(
            payload.get("run_spec_hash") == run.get("run_spec_hash"),
            f"ledger block run_spec_hash mismatch: {run_id}",
        )
        canonical = base / "canonical" / run_id
        partial = base / "partial" / run_id
        _require(
            not canonical.exists(),
            f"blocked run unexpectedly has canonical artifact: {run_id}",
        )
        # The runner leaves an empty per-run parent after atomically moving a
        # failed attempt to quarantine.  That bookkeeping directory is safe;
        # any retained child attempt/file is an active partial and blocks
        # result-blind recovery.
        _require(
            not partial.exists() or not any(partial.iterdir()),
            f"blocked run unexpectedly has partial attempt evidence: {run_id}",
        )
        quarantine = base / "quarantine" / run_id
        _require(
            quarantine.is_dir(),
            f"blocked run has no retained quarantine evidence: {run_id}",
        )
        attempts = sorted(
            (
                path
                for path in quarantine.iterdir()
                if path.is_dir() and _attempt_number(path) is not None
            ),
            key=lambda path: _attempt_number(path) or 0,
        )
        _require(
            len(attempts) == 2,
            f"blocked run must retain exactly two timeout attempts: {run_id}",
        )
        numbers = [_attempt_number(path) for path in attempts]
        _require(
            numbers == [1, 2], f"blocked run attempts must be consecutive 1/2: {run_id}"
        )
        evidence = [
            _timeout_attempt_evidence(run, path, manifest["manifest_hash"])
            for path in attempts
        ]
        _require(
            evidence[0]["failure_signature"] == evidence[1]["failure_signature"],
            f"blocked run timeout signatures differ: {run_id}",
        )
        event_signature = payload.get("failure_signature")
        _require(
            event_signature == evidence[0]["failure_signature"],
            f"ledger block failure signature does not match retained QC evidence: {run_id}",
        )
        identity = _normalise_runtime_identity(
            evidence[0]["runtime_identity"], require_binary=False
        )
        for item in evidence[1:]:
            other_identity = _normalise_runtime_identity(
                item["runtime_identity"], require_binary=False
            )
            _require(
                all(
                    other_identity[field] == identity[field]
                    for field in (
                        "git_commit",
                        "python_executable_sha256",
                        "cargo_lock_sha256",
                    )
                ),
                f"blocked run runtime identity differs across attempts: {run_id}",
            )
        identities.append(identity)
        selected.append(
            {
                "run_id": run_id,
                "run_spec_hash": run["run_spec_hash"],
                "seed": run.get("seed"),
                "experiment_id": run.get("experiment_id"),
                "cell_id": run.get("cell_id"),
                "failure_signature": evidence[0]["failure_signature"],
                "attempts": evidence,
                "block_event": {
                    "sequence": event.get("sequence"),
                    "event_hash": event.get("event_hash"),
                    "payload": copy.deepcopy(dict(payload)),
                },
            }
        )
    if expected_count is not None:
        _require(
            len(selected) == expected_count,
            f"expected exactly {expected_count} repeated timeout blocks, found {len(selected)}",
        )
    _require(bool(selected), "no repeated timeout blocks were selected")
    identity = identities[0]
    _require(
        all(
            all(
                item[field] == identity[field]
                for field in (
                    "git_commit",
                    "python_executable_sha256",
                    "cargo_lock_sha256",
                )
            )
            for item in identities
        ),
        "selected timeout blocks do not share one runtime identity",
    )
    # Timeout attempts frequently lack adapter_observation because the adapter
    # is killed at the wall-clock boundary.  Bind that one missing field to a
    # retained canonical audit from the same source workspace.
    if identity.get("adapter_binary_sha256") is None:
        canonical_identity = _discover_runtime_identity(base, manifest)
        _require(
            canonical_identity is not None,
            "cannot recover a frozen adapter binary hash from retained canonical evidence",
        )
        for field in (
            "git_commit",
            "python_executable_sha256",
            "cargo_lock_sha256",
        ):
            _require(
                canonical_identity[field] == identity[field],
                f"canonical runtime identity differs from timeout evidence: {field}",
            )
        identity = canonical_identity
    identity = _normalise_runtime_identity(identity)
    for selected_run in selected:
        for attempt in selected_run["attempts"]:
            attempt_identity = attempt.get("runtime_identity")
            if isinstance(attempt_identity, dict):
                observed_binary = attempt_identity.get("adapter_binary_sha256")
                if observed_binary is not None:
                    _require(
                        observed_binary == identity["adapter_binary_sha256"],
                        f"timeout evidence binary identity differs from retained canonical: {selected_run['run_id']}",
                    )
                attempt_identity["adapter_binary_sha256"] = identity[
                    "adapter_binary_sha256"
                ]
                attempt_identity["runtime_binary_sha256"] = identity[
                    "runtime_binary_sha256"
                ]
    if expected_runtime_identity is not None:
        _require(
            identity == _normalise_runtime_identity(expected_runtime_identity),
            "selected timeout runtime identity differs from the required frozen identity",
        )
    return {
        "manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
        },
        "workspace": str(base),
        "ledger": ledger,
        "quiescent_boundary": quiescent,
        "runtime_identity": identity,
        "metrics_consulted": False,
        "run_ids": [item["run_id"] for item in selected],
        "runs": selected,
    }


def _recovery_command_template(
    source_template: Any, adapter_request_timeout_seconds: float
) -> list[str]:
    _require(
        isinstance(source_template, list)
        and all(isinstance(item, str) for item in source_template),
        "source command_template must be a string array",
    )
    template = list(source_template)
    _require(
        "--request-timeout" not in template,
        "source command already contains --request-timeout; refusing ambiguous override",
    )
    rendered = (
        str(int(adapter_request_timeout_seconds))
        if float(adapter_request_timeout_seconds).is_integer()
        else str(adapter_request_timeout_seconds)
    )
    return [*template, "--request-timeout", rendered]


def build_recovery_manifest(
    source_manifest: Mapping[str, Any] | Path | str,
    plan: Mapping[str, Any],
    *,
    manifest_path: Path | str | None = None,
) -> dict[str, Any]:
    """Derive a manifest whose only execution change is the scoped timeout override."""

    source_input_path: Path | None = None
    if isinstance(source_manifest, (Path, str)):
        source_input_path = _absolute(source_manifest)
        source = _load_manifest(source_input_path)
    else:
        source = copy.deepcopy(dict(source_manifest))
    _require(
        isinstance(plan.get("plan_sha256"), str), "recovery plan has no plan_sha256"
    )
    _self_hash(plan, "plan_sha256")
    source_hash = source.get("manifest_hash")
    _require(isinstance(source_hash, str), "source manifest has no manifest_hash")
    _require(
        _hash_without(source, "manifest_hash") == source_hash,
        "source manifest content hash does not match manifest_hash",
    )
    source_path = (
        plan.get("source", {}).get("manifest_path")
        if isinstance(plan.get("source"), Mapping)
        else None
    )
    if source_path is not None:
        _require(
            source_hash == plan["source"].get("manifest_hash"),
            "recovery plan source manifest hash mismatch",
        )
        if source_input_path is not None:
            _require(
                file_hash(source_input_path)
                == plan["source"].get("manifest_file_sha256"),
                "source manifest bytes changed after recovery planning",
            )
    original_timeout = float(source["execution"]["timeout_seconds"])
    execution_override = _normalise_execution_override(
        plan.get("execution_override", {}),
        source_timeout_seconds=original_timeout,
    )
    timeout = execution_override["timeout_seconds"]
    adapter_timeout = execution_override["adapter_request_timeout_seconds"]
    execution = copy.deepcopy(source["execution"])
    execution["timeout_seconds"] = int(timeout) if timeout.is_integer() else timeout
    execution["command_template"] = _recovery_command_template(
        execution.get("command_template"), adapter_timeout
    )
    source["execution"] = execution
    source["technical_timeout_recovery"] = {
        "schema_version": TECHNICAL_TIMEOUT_RECOVERY_MANIFEST_SCHEMA,
        "source_manifest": {
            "path": plan["source"].get("manifest_path"),
            "file_sha256": plan["source"].get("manifest_file_sha256"),
            "manifest_hash": source_hash,
        },
        "source_manifest_hash": source_hash,
        "source_manifest_file_sha256": plan["source"].get("manifest_file_sha256"),
        # RecoveryRunner keeps the formal protocol provenance pointed at the
        # source manifest even though this control manifest has a different
        # content hash after applying its scoped execution settings.
        "audit_protocol_manifest": {
            "path": plan["source"].get("manifest_path"),
            "file_sha256": plan["source"].get("manifest_file_sha256"),
            "manifest_hash": source_hash,
        },
        "plan_sha256": plan["plan_sha256"],
        "scope": "selected_run_ids_only",
        "run_ids": list(plan["selection"]["run_ids"]),
        "metrics_consulted": False,
        "runtime_identity": copy.deepcopy(plan["runtime_identity"]),
        "execution_override": {
            "source_timeout_seconds": original_timeout,
            "tier": execution_override["tier"],
            "timeout_seconds": timeout,
            "adapter_request_timeout_seconds": adapter_timeout,
            "scope": "selected_run_ids_only",
            "command_template_append": [
                "--request-timeout",
                str(int(adapter_timeout))
                if adapter_timeout.is_integer()
                else str(adapter_timeout),
            ],
        },
    }
    source.pop("manifest_hash", None)
    source["manifest_hash"] = object_hash(source)
    if manifest_path is not None:
        target = _absolute(manifest_path)
        _require(
            not target.exists(),
            f"refusing to overwrite recovery control manifest: {target}",
        )
        write_json_atomic(target, source)
    return source


def _load_sealed_control_manifest(
    plan: Mapping[str, Any], manifest_path: Path | str
) -> dict[str, Any]:
    """Require byte-for-object equivalence with the deterministic control build."""

    recovery = plan.get("recovery")
    source = plan.get("source")
    _require(
        isinstance(recovery, Mapping), "recovery plan workspace binding is missing"
    )
    _require(isinstance(source, Mapping), "recovery plan source binding is missing")
    supplied_path = _absolute(manifest_path)
    sealed_path = _absolute(str(recovery.get("manifest_path", "")))
    _require(
        supplied_path == sealed_path,
        "control manifest path differs from the path sealed by the recovery plan",
    )
    source_path = _absolute(str(source.get("manifest_path", "")))
    _require(
        source_path.is_file()
        and file_hash(source_path) == source.get("manifest_file_sha256"),
        "source manifest bytes changed after recovery planning",
    )
    actual = _load_manifest(supplied_path)
    expected = build_recovery_manifest(source_path, plan)
    _require(
        actual == expected,
        "control manifest differs from the deterministic sealed recovery manifest",
    )
    return actual


def plan_timeout_recovery(
    manifest_path: Path | str,
    base_workspace: Path | str,
    plan_path: Path | str,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    adapter_request_timeout_seconds: float = DEFAULT_ADAPTER_REQUEST_TIMEOUT_SECONDS,
    expected_runtime_identity: Mapping[str, Any] | None = None,
    expected_count: int | None = 7,
    recovery_workspace: Path | str | None = None,
    require_formal_e2: bool = True,
) -> dict[str, Any]:
    """Create and persist an evidence-derived technical timeout recovery plan."""

    return _create_timeout_recovery_plan(
        manifest_path,
        base_workspace,
        plan_path,
        timeout_seconds=timeout_seconds,
        adapter_request_timeout_seconds=adapter_request_timeout_seconds,
        expected_runtime_identity=expected_runtime_identity,
        expected_count=expected_count,
        recovery_workspace=recovery_workspace,
        require_formal_e2=require_formal_e2,
    )


def _create_timeout_recovery_plan(
    manifest_path: Path | str,
    base_workspace: Path | str,
    plan_path: Path | str,
    *,
    timeout_seconds: float,
    adapter_request_timeout_seconds: float,
    expected_runtime_identity: Mapping[str, Any] | None,
    expected_count: int | None,
    recovery_workspace: Path | str | None,
    require_formal_e2: bool,
    expected_recovery_plan_sha256: str | None = None,
) -> dict[str, Any]:
    """Internal planner used by tier-1 and tier-2 sealed technical recovery."""

    manifest_path = _absolute(manifest_path)
    plan_path = _absolute(plan_path)
    _require(
        not plan_path.exists(),
        f"refusing to overwrite sealed technical recovery plan: {plan_path}",
    )
    manifest = _load_manifest(manifest_path)
    if require_formal_e2:
        formal_manifest = _validate_formal_e2_source(manifest_path)
        _require(
            formal_manifest == manifest,
            "formal E2 validation changed the source manifest representation",
        )
    execution_override = _normalise_execution_override(
        {
            "timeout_seconds": timeout_seconds,
            "adapter_request_timeout_seconds": adapter_request_timeout_seconds,
            "scope": "selected_run_ids_only",
        },
        source_timeout_seconds=float(manifest["execution"]["timeout_seconds"]),
    )
    evidence = select_repeated_timeout_blocks(
        manifest_path,
        base_workspace,
        expected_count=expected_count,
        expected_runtime_identity=expected_runtime_identity,
        expected_recovery_plan_sha256=expected_recovery_plan_sha256,
    )
    ws = (
        _absolute(recovery_workspace)
        if recovery_workspace is not None
        else plan_path.with_suffix(".workspace")
    )
    payload: dict[str, Any] = {
        "schema_version": TECHNICAL_TIMEOUT_RECOVERY_SCHEMA,
        "created_at": utc_now(),
        "kind": "technical_timeout_recovery_plan",
        "formal_e2_required": bool(require_formal_e2),
        "metrics_consulted": False,
        "source": {
            "manifest_path": evidence["manifest"]["path"],
            "manifest_file_sha256": evidence["manifest"]["file_sha256"],
            "manifest_hash": evidence["manifest"]["manifest_hash"],
            "workspace": evidence["workspace"],
            "ledger_path": evidence["ledger"]["path"],
            "ledger_file_sha256": evidence["ledger"]["file_sha256"],
            "ledger_sequence": evidence["ledger"]["sequence"],
            "ledger_last_event_hash": evidence["ledger"]["last_event_hash"],
            "quiescent_boundary": evidence["quiescent_boundary"],
        },
        "selection": {
            "rule": {
                "ledger_event_type": "run_blocked",
                "ledger_reason": RECOVERY_BLOCK_REASON,
                "evidence": (
                    "two consecutive timeout QC/process observations with "
                    "identical technical_failure_signature"
                ),
                "canonical_or_partial_absent": True,
            },
            "expected_count": expected_count,
            "run_ids": evidence["run_ids"],
            "runs": evidence["runs"],
            "metrics_consulted": False,
        },
        "runtime_identity": evidence["runtime_identity"],
        "execution_override": {
            "source_timeout_seconds": float(manifest["execution"]["timeout_seconds"]),
            "tier": execution_override["tier"],
            "timeout_seconds": execution_override["timeout_seconds"],
            "adapter_request_timeout_seconds": execution_override[
                "adapter_request_timeout_seconds"
            ],
            "scope": "selected_run_ids_only",
            "command_template_change": "append --request-timeout only in derived recovery manifest",
        },
        "recovery": {
            "workspace": str(ws),
            "manifest_path": str(ws / "manifest.json"),
            "ledger_path": str(ws / "ledger.jsonl"),
            "independent_from_source": True,
        },
    }
    payload["plan_sha256"] = object_hash(payload)
    write_json_atomic(plan_path, payload)
    return payload


def plan_timeout_recovery_tier2(
    previous_plan_path: Path | str,
    previous_recovery_workspace: Path | str,
    plan_path: Path | str,
    *,
    recovery_workspace: Path | str | None = None,
    require_formal_e2: bool = True,
) -> dict[str, Any]:
    """Derive the fixed 7200/7190 tier-2 plan from a completed tier-1 workspace."""

    upstream = revalidate_timeout_recovery_plan(previous_plan_path)
    source = upstream.get("source")
    _require(
        isinstance(source, Mapping),
        "upstream technical recovery plan source is missing",
    )
    manifest_path = source.get("manifest_path")
    _require(
        isinstance(manifest_path, str) and manifest_path,
        "upstream technical recovery plan has no source manifest path",
    )
    runtime_identity = upstream.get("runtime_identity")
    _require(
        isinstance(runtime_identity, Mapping),
        "upstream technical recovery plan has no runtime identity",
    )
    return _create_timeout_recovery_plan(
        manifest_path,
        previous_recovery_workspace,
        plan_path,
        timeout_seconds=_RECOVERY_PROFILES[RECOVERY_TIER_2]["timeout_seconds"],
        adapter_request_timeout_seconds=_RECOVERY_PROFILES[RECOVERY_TIER_2][
            "adapter_request_timeout_seconds"
        ],
        expected_runtime_identity=runtime_identity,
        expected_count=1,
        recovery_workspace=recovery_workspace,
        require_formal_e2=require_formal_e2,
        expected_recovery_plan_sha256=upstream["plan_sha256"],
    )


def _verify_plan(plan_path: Path | str) -> dict[str, Any]:
    plan = _load_object(_absolute(plan_path), "technical timeout recovery plan")
    _require(
        plan.get("schema_version") == TECHNICAL_TIMEOUT_RECOVERY_SCHEMA,
        "unsupported technical recovery plan schema",
    )
    _self_hash(plan, "plan_sha256")
    _require(
        plan.get("metrics_consulted") is False,
        "technical recovery plan metrics_consulted must be false",
    )
    _require(
        isinstance(plan.get("formal_e2_required"), bool),
        "technical recovery plan formal E2 gate is missing",
    )
    selection = plan.get("selection")
    _require(
        isinstance(selection, Mapping), "technical recovery plan selection is missing"
    )
    run_ids = selection.get("run_ids")
    _require(
        isinstance(run_ids, list)
        and bool(run_ids)
        and all(isinstance(item, str) and item for item in run_ids)
        and len(run_ids) == len(set(run_ids)),
        "technical recovery plan run_ids are invalid",
    )
    _require(
        selection.get("metrics_consulted") is False,
        "technical recovery selection metrics_consulted must be false",
    )
    return plan


def validate_timeout_recovery_plan(plan_path: Path | str) -> dict[str, Any]:
    """Load and fail-closed validate a sealed technical recovery plan."""

    return _verify_plan(plan_path)


def revalidate_timeout_recovery_plan(plan_path: Path | str) -> dict[str, Any]:
    """Recheck every sealed source-evidence byte before recovery execution."""

    plan = _verify_plan(plan_path)
    source = plan.get("source")
    selection = plan.get("selection")
    _require(isinstance(source, Mapping), "technical recovery plan source is missing")
    _require(
        isinstance(selection, Mapping),
        "technical recovery plan selection is missing",
    )
    manifest_path = _absolute(str(source.get("manifest_path", "")))
    workspace = _absolute(str(source.get("workspace", "")))
    _require(
        manifest_path.is_file()
        and file_hash(manifest_path) == source.get("manifest_file_sha256"),
        "source manifest bytes changed after recovery planning",
    )
    manifest = _load_manifest(manifest_path)
    _require(
        manifest.get("manifest_hash") == source.get("manifest_hash"),
        "source manifest hash changed after recovery planning",
    )
    if plan["formal_e2_required"]:
        _validate_formal_e2_source(manifest_path)
    ledger_path = workspace / "ledger.jsonl"
    _, ledger = _ledger_evidence(ledger_path)
    _require(
        ledger["sequence"] == source.get("ledger_sequence")
        and ledger["last_event_hash"] == source.get("ledger_last_event_hash")
        and ledger["file_sha256"] == source.get("ledger_file_sha256"),
        "source ledger changed after recovery planning",
    )
    run_ids = list(selection["run_ids"])
    quiescent = source.get("quiescent_boundary")
    expected_recovery_plan_sha256 = None
    if (
        isinstance(quiescent, Mapping)
        and quiescent.get("kind") == "technical_timeout_recovery"
    ):
        value = quiescent.get("plan_sha256")
        _require(
            isinstance(value, str) and value,
            "technical recovery plan quiescent boundary lacks the upstream plan hash",
        )
        expected_recovery_plan_sha256 = value
    evidence = select_repeated_timeout_blocks(
        manifest_path,
        workspace,
        expected_count=len(run_ids),
        expected_runtime_identity=plan.get("runtime_identity"),
        expected_recovery_plan_sha256=expected_recovery_plan_sha256,
    )
    _require(
        evidence.get("run_ids") == run_ids,
        "live timeout selection differs from the sealed recovery plan",
    )
    _require(
        evidence.get("runs") == selection.get("runs"),
        "live timeout QC/process/audit evidence differs from the sealed plan",
    )
    _require(
        evidence.get("runtime_identity") == plan.get("runtime_identity"),
        "live runtime identity differs from the sealed recovery plan",
    )
    return plan


def _lifecycle_binding(
    plan: Mapping[str, Any], control_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    source = plan.get("source")
    selection = plan.get("selection")
    _require(isinstance(source, Mapping), "recovery plan source binding is missing")
    _require(isinstance(selection, Mapping), "recovery plan selection is missing")
    run_ids = selection.get("run_ids")
    _require(isinstance(run_ids, list), "recovery plan run IDs are missing")
    override = _normalise_execution_override(plan.get("execution_override", {}))
    return {
        "schema_version": TECHNICAL_TIMEOUT_RECOVERY_SCHEMA,
        "plan_sha256": plan["plan_sha256"],
        "source_manifest_hash": source["manifest_hash"],
        "control_manifest_hash": control_manifest["manifest_hash"],
        "run_ids": sorted(run_ids),
        "selected_run_count": len(run_ids),
        "metrics_consulted": False,
        "timeout_seconds": override["timeout_seconds"],
        "adapter_request_timeout_seconds": (
            override["adapter_request_timeout_seconds"]
        ),
    }


def _require_lifecycle_binding(
    payload: Any, expected: Mapping[str, Any], event_type: str
) -> Mapping[str, Any]:
    _require(isinstance(payload, Mapping), f"{event_type} payload is invalid")
    for key, value in expected.items():
        _require(
            payload.get(key) == value,
            f"{event_type} {key} does not bind the sealed recovery plan",
        )
    return payload


def _validate_recovery_lifecycle(
    events: list[dict[str, Any]],
    plan: Mapping[str, Any],
    control_manifest: Mapping[str, Any],
    *,
    require_finished: bool,
) -> dict[str, Any]:
    """Validate the unique, sealed recovery batch lifecycle."""

    starts = [
        event
        for event in events
        if event.get("event_type") == "technical_timeout_recovery_started"
    ]
    finishes = [
        event
        for event in events
        if event.get("event_type") == "technical_timeout_recovery_finished"
    ]
    _require(len(starts) == 1, "recovery ledger must contain exactly one start event")
    _require(len(finishes) <= 1, "recovery ledger contains duplicate finish events")
    if require_finished:
        _require(
            len(finishes) == 1,
            "recovery ledger must contain exactly one finish event",
        )
    expected = _lifecycle_binding(plan, control_manifest)
    start = starts[0]
    _require(
        start.get("sequence") == 1,
        "recovery start must initialize the independent ledger",
    )
    _require_lifecycle_binding(start.get("payload"), expected, "recovery start")
    result: dict[str, Any] = {"start": start, "finish": None}
    if not finishes:
        return result
    finish = finishes[0]
    finish_payload = _require_lifecycle_binding(
        finish.get("payload"), expected, "recovery finish"
    )
    _require(
        int(finish.get("sequence", 0)) > int(start.get("sequence", 0)),
        "recovery finish must follow the start event",
    )
    _require(
        finish.get("sequence") == len(events),
        "recovery finish must be the terminal ledger event",
    )
    _require(
        finish_payload.get("started_event_hash") == start.get("event_hash"),
        "recovery finish does not bind its unique start event",
    )
    dispositions = finish_payload.get("dispositions")
    _require(
        isinstance(dispositions, list),
        "recovery finish dispositions must be an array",
    )
    disposition_by_id: dict[str, Mapping[str, Any]] = {}
    for index, disposition in enumerate(dispositions):
        _require(
            isinstance(disposition, Mapping),
            f"recovery disposition {index} is invalid",
        )
        run_id = disposition.get("run_id")
        status = disposition.get("status")
        _require(
            isinstance(run_id, str) and run_id not in disposition_by_id,
            "recovery dispositions contain a missing or duplicate run ID",
        )
        _require(
            status in _RECOVERY_RESULT_STATUSES,
            f"recovery disposition status is invalid for {run_id}",
        )
        disposition_by_id[run_id] = disposition
    _require(
        set(disposition_by_id) == set(expected["run_ids"]),
        "recovery finish does not contain a disposition for every planned run",
    )
    counts = {
        "canonicalized": sum(
            item["status"] in {"canonicalized", "canonical_exists"}
            for item in disposition_by_id.values()
        ),
        "blocked": sum(
            item["status"] == "blocked" for item in disposition_by_id.values()
        ),
        "preflight_blocked": sum(
            item["status"] == "preflight_blocked" for item in disposition_by_id.values()
        ),
    }
    for key, value in counts.items():
        _require(
            finish_payload.get(key) == value,
            f"recovery finish {key} count is inconsistent with dispositions",
        )
    result.update(
        {"finish": finish, "dispositions": disposition_by_id, "counts": counts}
    )
    return result


def _tree_digest(root: Path) -> str:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return object_hash(rows)
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": file_hash(path),
                    "bytes": path.stat().st_size,
                }
            )
    return object_hash(rows)


def _artifact_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "sha256": file_hash(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    ]


def _validate_canonical_artifact(
    run: Mapping[str, Any],
    path: Path,
    *,
    protocol_manifest_hash: str,
    recovery_plan_hash: str | None = None,
    source_manifest_hash: str | None = None,
    result_relative_path: str | None = None,
) -> None:
    _require(path.is_dir(), f"canonical artifact is missing: {path}")
    metadata = _load_object(path / "attempt.json", "canonical attempt metadata")
    report = _load_object(path / "qc_report.json", "canonical QC report")
    audit = _load_object(path / "manifest.json", "canonical audit manifest")
    _require(
        metadata.get("run_id") == run.get("run_id"),
        f"canonical run_id mismatch: {path}",
    )
    _require(
        metadata.get("run_spec_hash") == run.get("run_spec_hash"),
        f"canonical run_spec_hash mismatch: {path}",
    )
    _require(
        metadata.get("status") == "qc_pass"
        and metadata.get("classification") == "qc_pass",
        f"canonical attempt disposition is not qc_pass: {path}",
    )
    _require(
        report.get("passed") is True and report.get("classification") == "qc_pass",
        f"canonical QC is not qc_pass: {path}",
    )
    if result_relative_path is not None:
        result_path = path / result_relative_path.format(run_id=run["run_id"])
        _require(result_path.is_file(), f"canonical result is missing: {result_path}")
        _require(
            metadata.get("result_sha256") == file_hash(result_path),
            f"canonical result hash mismatch: {path}",
        )
    _require(
        audit.get("schema_version") == "NSE_RUN_AUDIT_MANIFEST_V1",
        f"canonical audit schema invalid: {path}",
    )
    _require(
        audit.get("status") == "canonical", f"canonical audit status invalid: {path}"
    )
    _require(
        _hash_without(audit, "audit_manifest_hash") == audit.get("audit_manifest_hash"),
        f"canonical audit hash mismatch: {path}",
    )
    protocol = audit.get("protocol_manifest")
    _require(
        isinstance(protocol, Mapping)
        and protocol.get("manifest_hash") == protocol_manifest_hash,
        f"canonical protocol manifest hash mismatch: {path}",
    )
    identity = audit.get("run")
    _require(
        isinstance(identity, Mapping) and identity.get("frozen_spec") == dict(run),
        f"canonical frozen run spec mismatch: {path}",
    )
    _require(
        audit.get("final_artifacts") == _artifact_inventory(path),
        f"canonical final-artifact inventory mismatch: {path}",
    )
    if recovery_plan_hash is not None:
        lineage = audit.get("technical_timeout_recovery")
        if lineage is None and isinstance(protocol, Mapping):
            lineage = protocol.get("technical_timeout_recovery")
        _require(
            isinstance(lineage, Mapping),
            f"recovery canonical lacks technical timeout lineage: {path}",
        )
        _require(
            lineage.get("plan_sha256") == recovery_plan_hash,
            f"recovery canonical plan lineage mismatch: {path}",
        )
        if source_manifest_hash is not None:
            source = lineage.get("source_manifest")
            _require(
                isinstance(source, Mapping)
                and source.get("manifest_hash") == source_manifest_hash,
                f"recovery canonical source lineage mismatch: {path}",
            )


def merge_timeout_recovery(
    manifest_path: Path | str,
    source_workspace: Path | str,
    plan_path: Path | str,
    recovery_workspace: Path | str,
    composite_workspace: Path | str,
    *,
    expected_count: int | None = None,
) -> dict[str, Any]:
    """Build a strict read-only composite canonical workspace.

    Existing source canonical artifacts always win.  Recovery artifacts are
    accepted only for the plan's selected run IDs and are copied byte-for-byte
    into a fresh composite workspace.  Neither input workspace is modified.
    """

    manifest_path = _absolute(manifest_path)
    source = _load_manifest(manifest_path)
    source_ws = _resolve_formal_workspace(source_workspace)
    plan = _verify_plan(plan_path)
    plan_source = plan.get("source")
    _require(
        isinstance(plan_source, Mapping), "recovery plan source evidence is missing"
    )
    _require(
        plan_source.get("manifest_hash") == source["manifest_hash"],
        "recovery plan does not bind the supplied source manifest",
    )
    _require(
        plan_source.get("manifest_file_sha256") == file_hash(manifest_path),
        "source manifest bytes changed since recovery planning",
    )
    # Allow the source ledger to grow after planning, but require its complete
    # planned prefix to remain byte/hash-chain identical.
    source_ledger_path = source_ws / "ledger.jsonl"
    current_events, current_ledger = _ledger_evidence(source_ledger_path)
    planned_seq = int(plan_source.get("ledger_sequence", 0))
    planned_last_hash = plan_source.get("ledger_last_event_hash")
    _require(
        planned_seq <= current_ledger["sequence"],
        "source ledger regressed after recovery planning",
    )
    if planned_seq:
        _require(
            current_events[planned_seq - 1].get("event_hash") == planned_last_hash,
            "source ledger prefix changed after recovery planning",
        )
    recovery_ws = _resolve_formal_workspace(recovery_workspace)
    sealed_recovery = plan.get("recovery")
    _require(
        isinstance(sealed_recovery, Mapping)
        and recovery_ws == _absolute(str(sealed_recovery.get("workspace", ""))),
        "recovery workspace differs from the independent workspace sealed by the plan",
    )
    recovery_ledger_path = recovery_ws / "ledger.jsonl"
    recovery_events, recovery_ledger = _ledger_evidence(recovery_ledger_path)
    _require(
        recovery_ledger_path.resolve() != source_ledger_path.resolve(),
        "recovery ledger must be independent from the source ledger",
    )
    recovery_manifest_path = recovery_ws / "manifest.json"
    recovery_manifest = _load_sealed_control_manifest(plan, recovery_manifest_path)
    marker = recovery_manifest.get("technical_timeout_recovery")
    _require(
        isinstance(marker, Mapping), "recovery manifest lacks technical timeout lineage"
    )
    _require(
        marker.get("plan_sha256") == plan["plan_sha256"],
        "recovery manifest plan lineage mismatch",
    )
    marker_source = marker.get("source_manifest")
    marker_source_hash = (
        marker_source.get("manifest_hash")
        if isinstance(marker_source, Mapping)
        else marker.get("source_manifest_hash")
    )
    _require(
        marker_source_hash == source["manifest_hash"],
        "recovery manifest source lineage mismatch",
    )
    _require(
        marker.get("metrics_consulted") is False,
        "recovery manifest metrics_consulted must be false",
    )
    marker_override = marker.get("execution_override")
    _normalise_execution_override(
        marker_override if isinstance(marker_override, Mapping) else {},
        source_timeout_seconds=float(source["execution"]["timeout_seconds"]),
    )
    selected_ids = set(plan["selection"]["run_ids"])
    source_runs = {run["run_id"]: run for run in source["runs"]}
    recovery_runs = {run["run_id"]: run for run in recovery_manifest["runs"]}
    _require(
        set(recovery_runs) == set(source_runs),
        "recovery manifest must preserve the complete source run set",
    )
    _require(
        set(marker.get("run_ids", [])) == selected_ids,
        "recovery manifest scope differs from plan",
    )
    lifecycle = _validate_recovery_lifecycle(
        recovery_events,
        plan,
        recovery_manifest,
        require_finished=True,
    )
    source_canonical = source_ws / "canonical"
    recovery_canonical = recovery_ws / "canonical"
    _require(source_canonical.is_dir(), "source canonical directory is missing")
    _require(recovery_canonical.is_dir(), "recovery canonical directory is missing")
    source_ids = {path.name for path in source_canonical.iterdir() if path.is_dir()}
    recovery_ids = {path.name for path in recovery_canonical.iterdir() if path.is_dir()}
    _require(source_ids <= set(source_runs), "source canonical contains an unknown run")
    _require(
        recovery_ids <= selected_ids,
        "recovery canonical contains a run outside the sealed plan",
    )
    dispositions = lifecycle["dispositions"]
    canonical_dispositions = {
        run_id
        for run_id, disposition in dispositions.items()
        if disposition.get("status") in {"canonicalized", "canonical_exists"}
    }
    _require(
        canonical_dispositions == recovery_ids,
        "recovery canonical set differs from the sealed finished dispositions",
    )
    strict_runner: Any = None
    if plan.get("formal_e2_required") is True:
        from .runner import ProtocolRunError, ProtocolRunner

        try:
            strict_runner = ProtocolRunner(manifest_path, source_ws)
        except (OSError, ProtocolRunError, ProtocolValidationError) as exc:
            _fail(f"strict canonical validator could not initialize: {exc}")

    def validate_canonical(
        run: Mapping[str, Any], path: Path, *, recovery: bool
    ) -> None:
        if strict_runner is not None:
            try:
                strict_runner._validate_existing_canonical(dict(run), path)
            except (OSError, ProtocolRunError, ProtocolValidationError) as exc:
                _fail(f"strict canonical validation failed for {path}: {exc}")
        _validate_canonical_artifact(
            run,
            path,
            protocol_manifest_hash=source["manifest_hash"],
            recovery_plan_hash=plan["plan_sha256"] if recovery else None,
            source_manifest_hash=source["manifest_hash"] if recovery else None,
            result_relative_path=source["execution"]["result_relative_path"],
        )

    # Validate every recovery artifact, including one shadowed by an original
    # canonical that appeared after planning.
    for run_id in sorted(recovery_ids):
        validate_canonical(
            source_runs[run_id], recovery_canonical / run_id, recovery=True
        )
    destination = _absolute(composite_workspace)
    _require(
        not destination.exists(),
        f"refusing to overwrite existing composite workspace: {destination}",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.partial-{os.getpid()}")
    _require(
        not staging.exists(),
        f"refusing to overwrite auditable composite staging workspace: {staging}",
    )
    staging.mkdir()
    staging_canonical = staging / "canonical"
    staging_canonical.mkdir()
    origins: dict[str, str] = {}
    for run_id, run in source_runs.items():
        source_path = source_canonical / run_id
        recovery_path = recovery_canonical / run_id
        if source_path.is_dir():
            validate_canonical(run, source_path, recovery=False)
            chosen_path = source_path
            origins[run_id] = "original"
        else:
            _require(
                run_id in selected_ids,
                f"source canonical is missing an unplanned run: {run_id}",
            )
            _require(
                recovery_path.is_dir(),
                f"recovery canonical is missing planned run: {run_id}",
            )
            chosen_path = recovery_path
            origins[run_id] = "technical_timeout_recovery"
        chosen_digest = _tree_digest(chosen_path)
        copied_path = staging_canonical / run_id
        shutil.copytree(chosen_path, copied_path)
        _require(
            _tree_digest(copied_path) == chosen_digest,
            f"composite copy digest mismatch for {run_id}",
        )
    count = len(origins)
    required_count = expected_count if expected_count is not None else len(source_runs)
    _require(
        count == required_count,
        f"composite canonical count is {count}, expected {required_count}",
    )
    _require(
        set(origins) == set(source_runs), "composite canonical run set is incomplete"
    )
    lineage: dict[str, Any] = {
        "schema_version": TECHNICAL_TIMEOUT_RECOVERY_COMPOSITE_SCHEMA,
        "created_at": utc_now(),
        "source_manifest": {
            "path": str(manifest_path),
            "file_sha256": file_hash(manifest_path),
            "manifest_hash": source["manifest_hash"],
        },
        "source_ledger": current_ledger,
        "recovery_plan_sha256": plan["plan_sha256"],
        "recovery_manifest": {
            "path": str(recovery_manifest_path),
            "file_sha256": file_hash(recovery_manifest_path),
            "manifest_hash": recovery_manifest["manifest_hash"],
        },
        "recovery_ledger": recovery_ledger,
        "recovery_batch": {
            "started_event_hash": lifecycle["start"]["event_hash"],
            "finished_event_hash": lifecycle["finish"]["event_hash"],
            "dispositions": [
                copy.deepcopy(dict(dispositions[run_id]))
                for run_id in sorted(dispositions)
            ],
        },
        "metrics_consulted": False,
        "selected_recovery_run_ids": sorted(selected_ids),
        "origins": origins,
        "canonical_count": count,
        "canonical_tree_sha256": _tree_digest(staging_canonical),
    }
    lineage["lineage_sha256"] = object_hash(lineage)
    write_json_atomic(staging / "composite_lineage.json", lineage)
    composite_manifest = copy.deepcopy(source)
    composite_manifest["technical_timeout_recovery_composite"] = copy.deepcopy(lineage)
    composite_manifest.pop("manifest_hash", None)
    composite_manifest["manifest_hash"] = object_hash(composite_manifest)
    write_json_atomic(staging / "composite_manifest.json", composite_manifest)
    receipt: dict[str, Any] = {
        "schema_version": TECHNICAL_TIMEOUT_RECOVERY_RECEIPT_SCHEMA,
        "created_at": utc_now(),
        "source_workspace": str(source_ws),
        "recovery_workspace": str(recovery_ws),
        "composite_workspace": str(destination),
        "source_tree_sha256": _tree_digest(source_canonical),
        "recovery_tree_sha256": _tree_digest(recovery_canonical),
        "composite_tree_sha256": _tree_digest(staging_canonical),
        "canonical_count": count,
        "origins": origins,
        "source_manifest_hash": source["manifest_hash"],
        "recovery_plan_sha256": plan["plan_sha256"],
        "metrics_consulted": False,
    }
    receipt["receipt_sha256"] = object_hash(receipt)
    write_json_atomic(staging / "merge_receipt.json", receipt)
    _require(
        set(path.name for path in staging_canonical.iterdir() if path.is_dir())
        == set(source_runs),
        "staged composite canonical run set is incomplete",
    )
    _require(
        len(origins) == required_count,
        "staged composite canonical count changed before publication",
    )
    staging.rename(destination)
    return {
        "status": "ready",
        "workspace": str(destination),
        "canonical_count": count,
        "origins": origins,
        "lineage_path": str(destination / "composite_lineage.json"),
        "receipt_path": str(destination / "merge_receipt.json"),
        "composite_manifest_path": str(destination / "composite_manifest.json"),
        "lineage_sha256": lineage["lineage_sha256"],
    }


class TechnicalTimeoutRecoveryRunner:
    """Scoped runner facade for a derived technical-recovery control manifest.

    The class is intentionally a thin adapter around :class:`ProtocolRunner`:
    normal runner behavior (QC, archival, retries, and append-only ledger
    writes) remains authoritative, while this facade enforces the recovery
    scope and rewrites only the audit *protocol provenance* back to the source
    manifest.  The control manifest may carry a different content hash because
    it contains a sealed recovery execution profile; it is never presented as a
    new formal protocol.

    A caller should construct this class with the manifest emitted by
    :func:`build_recovery_manifest`, the independent recovery workspace, and
    the sealed plan.  It must run in the frozen runtime identity recorded in
    that plan.
    """

    def __init__(
        self,
        manifest_path: Path | str,
        workspace: Path | str,
        plan_path: Path | str,
    ) -> None:
        from .runner import ProtocolRunError, ProtocolRunner, _WorkspaceLock

        self._protocol_run_error = ProtocolRunError
        self._base_runner_class = ProtocolRunner
        self._workspace_lock_class = _WorkspaceLock
        self.plan_path = _absolute(plan_path)
        self.plan = revalidate_timeout_recovery_plan(self.plan_path)
        self.manifest_path = _absolute(manifest_path)
        self.workspace = _absolute(workspace)
        plan_recovery = self.plan.get("recovery")
        if isinstance(plan_recovery, Mapping) and plan_recovery.get("workspace"):
            _require(
                self.workspace == _absolute(str(plan_recovery["workspace"])),
                "recovery runner workspace differs from the sealed plan",
            )
        source = self.plan.get("source")
        _require(isinstance(source, Mapping), "recovery plan source is missing")
        source_workspace = source.get("workspace")
        _require(
            isinstance(source_workspace, str) and source_workspace,
            "recovery plan source workspace is missing",
        )
        _require(
            self.workspace != _absolute(source_workspace),
            "recovery workspace must be independent from the source workspace",
        )
        self._source_manifest_hash = source.get("manifest_hash")
        self._source_manifest_file_sha256 = source.get("manifest_file_sha256")
        self._source_manifest_path = source.get("manifest_path")
        _require(
            isinstance(self._source_manifest_hash, str),
            "recovery plan source manifest hash is missing",
        )
        self._source_manifest = _load_manifest(
            _absolute(str(self._source_manifest_path))
        )
        control = _load_sealed_control_manifest(self.plan, self.manifest_path)
        marker = control.get("technical_timeout_recovery")
        _require(
            isinstance(marker, Mapping),
            "control manifest lacks technical timeout lineage",
        )
        _require(
            marker.get("plan_sha256") == self.plan["plan_sha256"],
            "control manifest plan lineage mismatch",
        )
        marker_source = marker.get("source_manifest")
        marker_source_hash = (
            marker_source.get("manifest_hash")
            if isinstance(marker_source, Mapping)
            else marker.get("source_manifest_hash")
        )
        _require(
            marker_source_hash == self._source_manifest_hash,
            "control manifest source lineage mismatch",
        )
        selected = self.plan.get("selection", {}).get("run_ids")
        _require(
            isinstance(selected, list) and selected,
            "recovery plan has no selected run IDs",
        )
        self._selected_run_order = tuple(str(run_id) for run_id in selected)
        self._selected_run_ids = frozenset(self._selected_run_order)
        # Import locally so importing the planning helpers does not initialize
        # psutil or the simulator runner for read-only plan audits.
        self._runner = ProtocolRunner(self.manifest_path, self.workspace)
        self.manifest = self._runner.manifest
        self.ledger = self._runner.ledger
        self._assert_frozen_runtime_identity()
        self._lineage = copy.deepcopy(dict(marker))
        self._lineage["plan_sha256"] = self.plan["plan_sha256"]
        self._lineage["source_manifest_hash"] = self._source_manifest_hash
        self._lineage["metrics_consulted"] = False
        self._audit_delegate: Any = None
        self._validate_delegate: Any = None
        self._lifecycle_active = False

    def _assert_frozen_runtime_identity(self) -> None:
        expected = _normalise_runtime_identity(self.plan["runtime_identity"])
        provenance = self._runner._runtime_provenance()
        git = provenance.get("git", {})
        python = provenance.get("python", {})
        cargo = provenance.get("cargo_lock", {})
        observed = {
            "git_commit": git.get("commit") if isinstance(git, Mapping) else None,
            "python_executable_sha256": python.get("executable_sha256")
            if isinstance(python, Mapping)
            else None,
            "cargo_lock_sha256": cargo.get("sha256")
            if isinstance(cargo, Mapping)
            else None,
            # The adapter hash is verified from adapter_observation at audit
            # time; no process launch is needed to check it here.
            "adapter_binary_sha256": expected["adapter_binary_sha256"],
        }
        for field in (
            "git_commit",
            "python_executable_sha256",
            "cargo_lock_sha256",
        ):
            _require(
                observed[field] == expected[field],
                f"recovery runtime identity mismatch for {field}",
            )

    def _execution_settings(self) -> dict[str, Any]:
        """Return the already-sealed scoped execution settings."""

        execution = copy.deepcopy(self.manifest.get("execution", {}))
        marker_override = self._lineage.get("execution_override")
        _require(
            isinstance(marker_override, Mapping),
            "recovery execution override is missing",
        )
        _require(
            float(execution.get("timeout_seconds", 0))
            == float(marker_override.get("timeout_seconds", 0)),
            "control manifest timeout differs from sealed recovery override",
        )
        return execution

    def _audit_manifest_payload(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        delegate = self._audit_delegate
        if delegate is None:
            delegate = self._runner._audit_manifest_payload
        payload = delegate(*args, **kwargs)
        protocol = payload.get("protocol_manifest")
        _require(
            isinstance(protocol, dict), "runner audit protocol provenance is missing"
        )
        protocol.update(
            {
                "path": str(self._source_manifest_path),
                "manifest_hash": self._source_manifest_hash,
                "file_sha256": self._source_manifest_file_sha256,
                "technical_timeout_recovery": copy.deepcopy(self._lineage),
            }
        )
        payload["technical_timeout_recovery"] = copy.deepcopy(self._lineage)
        payload.pop("audit_manifest_hash", None)
        payload["audit_manifest_hash"] = object_hash(payload)
        return payload

    def _validate_recovery_audit_manifest(
        self, run: dict[str, Any], canonical: Path
    ) -> None:
        """Run every base canonical check under the source protocol identity."""

        delegate = self._validate_delegate
        _require(delegate is not None, "recovery canonical validator is not bound")
        original_manifest = self._runner.manifest
        original_manifest_path = self._runner.manifest_path
        self._runner.manifest = self._source_manifest
        self._runner.manifest_path = _absolute(str(self._source_manifest_path))
        try:
            delegate(run, canonical)
        finally:
            self._runner.manifest = original_manifest
            self._runner.manifest_path = original_manifest_path
        # The base validator intentionally permits additional protocol fields;
        # enforce the recovery-specific source/plan lineage as a second layer.
        _validate_canonical_artifact(
            run,
            canonical,
            protocol_manifest_hash=self._source_manifest_hash,
            recovery_plan_hash=self.plan["plan_sha256"],
            source_manifest_hash=self._source_manifest_hash,
            result_relative_path=self._source_manifest["execution"][
                "result_relative_path"
            ],
        )

    def _run_one(
        self, run: dict[str, Any], command_override: list[str] | None = None
    ) -> dict[str, Any]:
        if not self._lifecycle_active:
            raise self._protocol_run_error(
                "technical timeout recovery run is outside the locked sealed lifecycle"
            )
        if run.get("run_id") not in self._selected_run_ids:
            raise self._protocol_run_error(
                f"technical timeout recovery run is outside sealed scope: {run.get('run_id')}"
            )
        if command_override is not None:
            raise self._protocol_run_error(
                "technical timeout recovery forbids ad-hoc command overrides"
            )
        # Bind the facade's audit hook and execute the authoritative runner.
        original_audit = self._runner._audit_manifest_payload
        original_validate = self._runner._validate_audit_manifest
        self._audit_delegate = original_audit
        self._validate_delegate = original_validate
        self._runner._audit_manifest_payload = (
            self._audit_manifest_payload
        )  # type: ignore[method-assign]
        self._runner._validate_audit_manifest = (  # type: ignore[method-assign]
            self._validate_recovery_audit_manifest
        )
        try:
            return self._runner.run_one(run)
        finally:
            self._runner._audit_manifest_payload = (  # type: ignore[method-assign]
                original_audit
            )
            self._runner._validate_audit_manifest = (  # type: ignore[method-assign]
                original_validate
            )
            self._audit_delegate = None
            self._validate_delegate = None

    def run_one(self, run_id: str) -> dict[str, Any]:
        """Reject selective execution outside the locked full-plan lifecycle."""

        raise self._protocol_run_error(
            "selective technical timeout recovery is forbidden; call run() for the full sealed plan"
        )

    @staticmethod
    def _disposition(result: Mapping[str, Any]) -> dict[str, Any]:
        disposition = {
            "run_id": result.get("run_id"),
            "status": result.get("status"),
        }
        for field in ("attempt", "attempts_used", "path", "reason"):
            if field in result:
                disposition[field] = copy.deepcopy(result[field])
        return disposition

    def run(self) -> list[dict[str, Any]]:
        selected = list(self._selected_run_order)
        requested = set(selected)
        by_id = {run["run_id"]: run for run in self._runner.manifest["runs"]}
        missing = requested - set(by_id)
        _require(
            not missing,
            "recovery plan names runs absent from control manifest: "
            + ", ".join(sorted(missing)),
        )
        expected_binding = _lifecycle_binding(self.plan, self.manifest)
        with self._workspace_lock_class(self.workspace / ".protocol.lock"):
            # Ledger caches its head, so always refresh after obtaining the
            # workspace lock before deciding whether this is a fresh/resumed run.
            self.ledger = Ledger(self.workspace / "ledger.jsonl")
            self._runner.ledger = self.ledger
            events = list(self.ledger.iter_events() or ())
            starts = [
                event
                for event in events
                if event.get("event_type") == "technical_timeout_recovery_started"
            ]
            finishes = [
                event
                for event in events
                if event.get("event_type") == "technical_timeout_recovery_finished"
            ]
            if not events:
                start = self.ledger.append(
                    "technical_timeout_recovery_started", dict(expected_binding)
                )
            else:
                _require(
                    len(starts) == 1,
                    "recovery ledger must have one sealed start event before resume",
                )
                lifecycle = _validate_recovery_lifecycle(
                    events,
                    self.plan,
                    self.manifest,
                    require_finished=bool(finishes),
                )
                start = lifecycle["start"]
                if lifecycle["finish"] is not None:
                    dispositions = lifecycle["dispositions"]
                    return [
                        copy.deepcopy(dict(dispositions[run_id])) for run_id in selected
                    ]
            self._lifecycle_active = True
            try:
                results = [self._run_one(by_id[run_id]) for run_id in selected]
            finally:
                self._lifecycle_active = False
            dispositions = [self._disposition(result) for result in results]
            for disposition in dispositions:
                _require(
                    disposition.get("run_id") in requested
                    and disposition.get("status") in _RECOVERY_RESULT_STATUSES,
                    "recovery runner returned an invalid planned disposition",
                )
            _require(
                {item["run_id"] for item in dispositions} == requested
                and len(dispositions) == len(requested),
                "recovery runner did not return one disposition for every planned run",
            )
            finish_payload = {
                **expected_binding,
                "started_event_hash": start["event_hash"],
                "dispositions": dispositions,
                "canonicalized": sum(
                    item["status"] in {"canonicalized", "canonical_exists"}
                    for item in dispositions
                ),
                "blocked": sum(item["status"] == "blocked" for item in dispositions),
                "preflight_blocked": sum(
                    item["status"] == "preflight_blocked" for item in dispositions
                ),
            }
            self.ledger.append("technical_timeout_recovery_finished", finish_payload)
            return results


# Friendly aliases used by CLI integrations and external audit scripts.
create_timeout_recovery_plan = plan_timeout_recovery
build_technical_timeout_recovery_plan = plan_timeout_recovery
create_timeout_recovery_plan_tier2 = plan_timeout_recovery_tier2
derive_recovery_manifest = build_recovery_manifest
merge_recovery_workspace = merge_timeout_recovery


__all__ = [
    "DEFAULT_ADAPTER_REQUEST_TIMEOUT_SECONDS",
    "DEFAULT_TIMEOUT_SECONDS",
    "E2_ORIGINAL_RUNTIME_IDENTITY",
    "RECOVERY_BLOCK_REASON",
    "TECHNICAL_TIMEOUT_RECOVERY_SCHEMA",
    "TechnicalTimeoutRecoveryError",
    "TechnicalTimeoutRecoveryRunner",
    "build_recovery_manifest",
    "build_technical_timeout_recovery_plan",
    "create_timeout_recovery_plan",
    "create_timeout_recovery_plan_tier2",
    "derive_recovery_manifest",
    "merge_recovery_workspace",
    "merge_timeout_recovery",
    "plan_timeout_recovery",
    "plan_timeout_recovery_tier2",
    "revalidate_timeout_recovery_plan",
    "select_repeated_timeout_blocks",
    "validate_timeout_recovery_plan",
]
