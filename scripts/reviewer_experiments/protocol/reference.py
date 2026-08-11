from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import HASH_RE, ProtocolValidationError, validate_manifest
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


@dataclass(frozen=True)
class ReferenceTableInfo:
    path: str
    sha256: str
    bytes: int
    line_count: int
    state_pair_sequence_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "line_count": self.line_count,
            "state_pair_sequence_sha256": self.state_pair_sequence_sha256,
        }


def _state_key(event: dict[str, Any], line_number: int) -> int:
    value = event.get("state_key_u64")
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    text = event.get("state_key")
    if isinstance(text, str):
        try:
            value = int(text, 0)
        except ValueError:
            pass
        else:
            if value >= 0:
                return value
    raise ProtocolValidationError(
        f"reference line {line_number} has no valid state key"
    )


def inspect_reference_table(path: Path) -> ReferenceTableInfo:
    path = path.resolve()
    digest = hashlib.sha256()
    keys: set[int] = set()
    line_count = 0
    with path.open("rb") as handle:
        for line_count, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                raise ProtocolValidationError(f"reference line {line_count} is blank")
            try:
                event = json.loads(raw_line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProtocolValidationError(
                    f"reference line {line_count} is invalid JSON: {exc}"
                ) from exc
            if (
                not isinstance(event, dict)
                or event.get("kind") != "offline_social_reference_build"
            ):
                raise ProtocolValidationError(
                    f"reference line {line_count} has the wrong kind"
                )
            key = _state_key(event, line_count)
            if key in keys:
                raise ProtocolValidationError(
                    f"reference line {line_count} repeats state key {key}"
                )
            keys.add(key)
            initial_hash = event.get("initial_assignment_hash")
            if (
                isinstance(initial_hash, bool)
                or not isinstance(initial_hash, int)
                or initial_hash < 0
            ):
                raise ProtocolValidationError(
                    f"reference line {line_count} has no valid initial_assignment_hash"
                )
            reference = event.get("reference")
            if reference is not None and (
                isinstance(reference, bool)
                or not isinstance(reference, (int, float))
                or not math.isfinite(float(reference))
            ):
                raise ProtocolValidationError(
                    f"reference line {line_count} has a nonfinite reference"
                )
            digest.update(f"{key}:{initial_hash}\n".encode("ascii"))
    return ReferenceTableInfo(
        path=str(path),
        sha256=file_hash(path),
        bytes=path.stat().st_size,
        line_count=line_count,
        state_pair_sequence_sha256=digest.hexdigest(),
    )


def register_reference_build(
    catalog_path: Path,
    key: str,
    table_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    table = inspect_reference_table(table_path)
    receipt = read_json(receipt_path)
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version") != "NSE_REFERENCE_BUILD_RECEIPT_V1"
    ):
        raise ProtocolValidationError("reference build receipt schema is invalid")
    expected = {
        "reference_key": key,
        "table_sha256": table.sha256,
        "table_bytes": table.bytes,
        "table_line_count": table.line_count,
        "state_pair_sequence_sha256": table.state_pair_sequence_sha256,
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise ProtocolValidationError(
                f"reference receipt {field} does not match the table"
            )
    for field in (
        "build_spec_hash",
        "workload_tape_sha256",
        "process_observation_sha256",
        "assignment_sequence_sha256",
    ):
        if HASH_RE.fullmatch(str(receipt.get(field))) is None:
            raise ProtocolValidationError(f"reference receipt {field} is invalid")
    completed = receipt.get("completed")
    if isinstance(completed, bool) or not isinstance(completed, int) or completed < 0:
        raise ProtocolValidationError("reference receipt completed counter is invalid")
    process_observation_path = (
        receipt_path.resolve().parent / "process_observation.json"
    )
    if (
        not process_observation_path.is_file()
        or file_hash(process_observation_path) != receipt["process_observation_sha256"]
    ):
        raise ProtocolValidationError(
            "reference build process observation is missing or changed"
        )
    entry = {
        "key": key,
        **table.to_dict(),
        "receipt_path": str(receipt_path.resolve()),
        "receipt_sha256": file_hash(receipt_path),
        "build_spec_hash": receipt["build_spec_hash"],
        "workload_tape_sha256": receipt["workload_tape_sha256"],
        "build_completed": completed,
        "assignment_sequence_sha256": receipt["assignment_sequence_sha256"],
        "build_process_observation_path": str(process_observation_path),
        "build_process_observation_sha256": receipt["process_observation_sha256"],
    }
    if catalog_path.exists():
        catalog = read_json(catalog_path)
    else:
        catalog = {
            "schema_version": "NSE_REFERENCE_CATALOG_V1",
            "created_at": utc_now(),
            "entries": {},
        }
    if (
        not isinstance(catalog, dict)
        or catalog.get("schema_version") != "NSE_REFERENCE_CATALOG_V1"
    ):
        raise ProtocolValidationError("reference catalog schema is invalid")
    entries = catalog.setdefault("entries", {})
    if key in entries and entries[key] != entry:
        raise ProtocolValidationError(
            f"refusing to replace immutable reference key {key!r}"
        )
    entries[key] = entry
    catalog["updated_at"] = utc_now()
    payload = copy.deepcopy(catalog)
    payload.pop("catalog_hash", None)
    catalog["catalog_hash"] = object_hash(payload)
    write_json_atomic(catalog_path, catalog)
    return entry


def bind_reference_catalog(
    manifest: dict[str, Any], catalog: dict[str, Any]
) -> dict[str, Any]:
    from .matrix import _assign_run_identity, _reference_build_dependencies

    validate_manifest(manifest)
    if (
        not isinstance(catalog, dict)
        or catalog.get("schema_version") != "NSE_REFERENCE_CATALOG_V1"
    ):
        raise ProtocolValidationError("reference catalog schema is invalid")
    payload = copy.deepcopy(catalog)
    catalog_hash = payload.pop("catalog_hash", None)
    if not isinstance(catalog_hash, str) or object_hash(payload) != catalog_hash:
        raise ProtocolValidationError(
            "reference catalog hash does not match its content"
        )
    entries = catalog.get("entries")
    if not isinstance(entries, dict):
        raise ProtocolValidationError("reference catalog entries must be an object")
    bound = copy.deepcopy(manifest)
    for run in bound["runs"]:
        dependency = run.get("reference_dependency")
        if dependency is None:
            continue
        entry = entries.get(dependency["key"])
        if not isinstance(entry, dict):
            raise ProtocolValidationError(
                f"reference catalog is missing {dependency['key']!r}"
            )
        if entry.get("build_spec_hash") != dependency["build_spec_hash"]:
            raise ProtocolValidationError(
                f"reference build spec mismatch for {dependency['key']!r}"
            )
        if entry.get("workload_tape_sha256") != run["workload_tape"]["sha256"]:
            raise ProtocolValidationError(
                f"reference workload tape mismatch for {dependency['key']!r}"
            )
        table_path = Path(entry["path"])
        receipt_path = Path(entry["receipt_path"])
        if not table_path.is_file() or file_hash(table_path) != entry.get("sha256"):
            raise ProtocolValidationError(
                f"reference table is missing or changed for {dependency['key']!r}"
            )
        if not receipt_path.is_file() or file_hash(receipt_path) != entry.get(
            "receipt_sha256"
        ):
            raise ProtocolValidationError(
                f"reference receipt is missing or changed for {dependency['key']!r}"
            )
        process_path = Path(entry["build_process_observation_path"])
        if not process_path.is_file() or file_hash(process_path) != entry.get(
            "build_process_observation_sha256"
        ):
            raise ProtocolValidationError(
                f"reference process observation is missing or changed for {dependency['key']!r}"
            )
        dependency.update(
            {
                "path": entry["path"],
                "sha256": entry["sha256"],
                "bytes": entry["bytes"],
                "line_count": entry["line_count"],
                "receipt_path": entry["receipt_path"],
                "receipt_sha256": entry["receipt_sha256"],
                "build_completed": entry["build_completed"],
                "state_pair_sequence_sha256": entry["state_pair_sequence_sha256"],
                "assignment_sequence_sha256": entry["assignment_sequence_sha256"],
                "build_process_observation_path": entry[
                    "build_process_observation_path"
                ],
                "build_process_observation_sha256": entry[
                    "build_process_observation_sha256"
                ],
                "build_required": False,
            }
        )
        run["simulator_experiment"]["reference"]["table_path"] = entry["path"]
        _assign_run_identity(run)
    bound["reference_build_dependencies"] = _reference_build_dependencies(bound["runs"])
    bound["reference_catalog_hash"] = catalog_hash
    bound["all_references_bound"] = True
    bound.pop("manifest_hash", None)
    bound["manifest_hash"] = object_hash(bound)
    validate_manifest(bound)
    return bound
