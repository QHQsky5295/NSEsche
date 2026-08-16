"""Fail-closed admission checks for formal analysis inputs.

The protocol runner is responsible for producing canonical attempts.  Analysis
must still verify the small, immutable contract at its boundary: a manifest is
explicitly formal, every run has a passing QC report, and the canonical audit
inventory still describes the files on disk.  Keeping these checks here avoids
having the CSV and observability exporters quietly accept a smoke or partial
tree when invoked independently.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


CANONICAL_AUDIT_SCHEMA = "NSE_RUN_AUDIT_MANIFEST_V1"
PAIRING_AUDIT_SCHEMA = "NSE_PAIRED_ENVIRONMENT_AUDIT_V1"
RUNTIME_CONSENSUS_FIELDS = (
    "runtime_binary_sha256",
    "runtime_git_commit",
    "runtime_python_executable_sha256",
    "runtime_cargo_lock_sha256",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def object_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def assert_formal_manifest(manifest: Mapping[str, Any]) -> None:
    """Reject manifests that are not explicitly admitted to formal analysis."""

    if not isinstance(manifest, Mapping) or not isinstance(manifest.get("runs"), list):
        raise ValueError("formal analysis manifest must contain a runs array")
    if (
        "integration_smoke_shard" in manifest
        or manifest.get("formal_results_eligible") is not True
    ):
        raise ValueError(
            "manifest is not explicitly formal-results eligible; refusing analysis"
        )
    manifest_hash = manifest.get("manifest_hash")
    if not isinstance(manifest_hash, str) or len(manifest_hash) != 64:
        raise ValueError("formal analysis manifest is missing manifest_hash")
    payload = dict(manifest)
    payload.pop("manifest_hash", None)
    if object_hash(payload) != manifest_hash:
        raise ValueError("formal analysis manifest_hash does not match content")


def _canonical_inventory(directory: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        inventory.append(
            {
                "relative_path": path.relative_to(directory).as_posix(),
                "sha256": file_hash(path),
                "bytes": path.stat().st_size,
            }
        )
    return inventory


def validate_canonical_run(
    run: Mapping[str, Any],
    directory: Path,
    *,
    expected_manifest_hash: str | None = None,
    result_relative_path: str = "result.json",
) -> dict[str, Any]:
    """Validate one immutable canonical directory and return its QC report.

    ``expected_manifest_hash`` is supplied by the formal exporters.  The
    optional ``None`` mode is retained for low-level stream-loader unit tests;
    the public manifest-driven pipelines always pass the hash.
    """

    if not directory.is_dir():
        raise FileNotFoundError(f"canonical run directory is missing: {directory}")

    qc_path = directory / "qc_report.json"
    if not qc_path.is_file():
        raise ValueError(f"canonical run is missing qc_report.json: {directory}")
    qc = read_json(qc_path)
    if not isinstance(qc, Mapping) or qc.get("passed") is not True:
        raise ValueError(f"canonical run does not have passing QC: {directory}")
    if qc.get("classification") not in (None, "qc_pass"):
        raise ValueError(f"canonical QC classification is not qc_pass: {directory}")
    if expected_manifest_hash is not None and qc.get("classification") != "qc_pass":
        raise ValueError(f"formal canonical QC classification is missing: {directory}")

    audit_path = directory / "manifest.json"
    if expected_manifest_hash is not None and not audit_path.is_file():
        raise ValueError(f"canonical run is missing audit manifest: {directory}")
    if not audit_path.is_file():
        return dict(qc)
    audit = read_json(audit_path)
    if not isinstance(audit, Mapping):
        raise ValueError(f"canonical audit manifest is not an object: {audit_path}")
    if audit.get("schema_version") != CANONICAL_AUDIT_SCHEMA:
        raise ValueError(f"canonical audit schema is invalid: {audit_path}")
    if audit.get("status") != "canonical":
        raise ValueError(f"canonical audit status is not canonical: {audit_path}")
    claimed_hash = audit.get("audit_manifest_hash")
    unhashed = dict(audit)
    unhashed.pop("audit_manifest_hash", None)
    if not isinstance(claimed_hash, str) or object_hash(unhashed) != claimed_hash:
        raise ValueError(f"canonical audit manifest hash mismatch: {audit_path}")

    identity = audit.get("run")
    if not isinstance(identity, Mapping):
        raise ValueError(f"canonical audit run identity is missing: {audit_path}")
    for key in ("run_id", "run_spec_hash", "method", "variant"):
        if identity.get(key) != run.get(key):
            raise ValueError(f"canonical audit {key} mismatch: {directory}")
    if identity.get("frozen_spec") != dict(run):
        raise ValueError(f"canonical audit frozen spec mismatch: {directory}")

    protocol = audit.get("protocol_manifest")
    if not isinstance(protocol, Mapping):
        raise ValueError(f"canonical audit protocol provenance is missing: {directory}")
    if (
        expected_manifest_hash is not None
        and protocol.get("manifest_hash") != expected_manifest_hash
    ):
        raise ValueError(f"canonical audit protocol manifest mismatch: {directory}")

    inventory = audit.get("final_artifacts")
    if not isinstance(inventory, list):
        raise ValueError(f"canonical audit artifact inventory is missing: {directory}")
    normalized_expected = sorted(
        [dict(item) for item in inventory if isinstance(item, Mapping)],
        key=lambda item: str(item.get("relative_path", "")),
    )
    if len(normalized_expected) != len(inventory):
        raise ValueError(
            f"canonical audit artifact inventory is malformed: {directory}"
        )
    actual = _canonical_inventory(directory)
    if actual != normalized_expected:
        raise ValueError(f"canonical artifact inventory mismatch: {directory}")

    try:
        formatted_result = result_relative_path.format(run_id=str(run["run_id"]))
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"invalid result path template: {result_relative_path}"
        ) from exc
    if not (directory / formatted_result).is_file():
        raise ValueError(f"canonical result is missing: {directory / formatted_result}")
    return dict(qc)


def validate_pairing_audit(
    pairing_path: Path,
    manifest: Mapping[str, Any],
    canonical_root: Path,
) -> dict[str, Any]:
    """Require a passing pairing report bound to this manifest and root."""

    if not pairing_path.is_file():
        raise ValueError(f"pairing audit is missing: {pairing_path}")
    report = read_json(pairing_path)
    if not isinstance(report, Mapping) or report.get("schema") != PAIRING_AUDIT_SCHEMA:
        raise ValueError("pairing audit has an unsupported schema")
    if report.get("passed") is not True or report.get("failures"):
        raise ValueError("pairing audit did not pass")
    if report.get("protocol_manifest_sha256") != manifest.get("manifest_hash"):
        raise ValueError("pairing audit is bound to a different manifest")
    reported_root = report.get("canonical_root")
    if (
        not isinstance(reported_root, str)
        or Path(reported_root).resolve() != canonical_root.resolve()
    ):
        raise ValueError("pairing audit is bound to a different canonical root")
    runs = manifest.get("runs")
    if not isinstance(runs, list) or report.get("run_count") != len(runs):
        raise ValueError("pairing audit run count does not match the manifest")
    expected_ids = {str(run.get("run_id")) for run in runs if isinstance(run, Mapping)}
    observed_id_list = [
        str(item.get("run_id"))
        for group in report.get("groups", [])
        if isinstance(group, Mapping)
        for item in group.get("runs", [])
        if isinstance(item, Mapping)
    ]
    observed_ids = set(observed_id_list)
    if len(observed_id_list) != len(observed_ids):
        raise ValueError("pairing audit contains duplicate run evidence")
    if observed_ids != expected_ids:
        raise ValueError("pairing audit run IDs do not match the manifest")
    if manifest.get("formal_results_eligible") is True:
        # Formal reports must carry the runtime consensus introduced by the
        # current pairing protocol.  This deliberately rejects reports made
        # by older tooling instead of silently treating their provenance as
        # equivalent.
        groups = report.get("groups")
        if not isinstance(groups, list):
            raise ValueError("formal pairing audit has no group reports")
        for group in groups:
            if not isinstance(group, Mapping):
                raise ValueError("formal pairing audit contains a malformed group")
            consensus = group.get("consensus")
            if not isinstance(consensus, Mapping):
                raise ValueError("formal pairing audit group lacks runtime consensus")
            for field in RUNTIME_CONSENSUS_FIELDS:
                value = consensus.get(field)
                pattern = _COMMIT_RE if field == "runtime_git_commit" else _SHA256_RE
                if not isinstance(value, str) or pattern.fullmatch(value) is None:
                    raise ValueError(
                        "formal pairing audit lacks current runtime consensus "
                        f"field {field}"
                    )
            members = group.get("runs")
            if not isinstance(members, list):
                raise ValueError("formal pairing audit group lacks run evidence")
            for member in members:
                if not isinstance(member, Mapping):
                    raise ValueError("formal pairing audit run evidence is malformed")
                for field in RUNTIME_CONSENSUS_FIELDS:
                    if member.get(field) != consensus.get(field):
                        raise ValueError(
                            "formal pairing audit runtime evidence disagrees with "
                            f"consensus for {field}"
                        )
    return dict(report)
