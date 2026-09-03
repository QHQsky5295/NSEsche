from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_WINDOWS_RETRYABLE_REPLACE_ERRORS = frozenset({5, 32, 33})
_ATOMIC_REPLACE_BACKOFF_SECONDS = (0.01, 0.02, 0.05, 0.1, 0.2)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def object_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _retryable_atomic_replace_error(exc: OSError) -> bool:
    """Return whether Windows reports a transient file-sharing failure.

    Antivirus scanners and indexers can briefly hold a just-fsynced file open
    on Windows.  Only the documented access/sharing/lock violations are
    retried; every other error remains an immediate, fail-closed exception.
    """

    return os.name == "nt" and getattr(exc, "winerror", None) in (
        _WINDOWS_RETRYABLE_REPLACE_ERRORS
    )


def replace_atomic(source: Path, destination: Path) -> None:
    """Atomically replace ``destination`` with bounded Windows-only retries."""

    for retry, delay in enumerate((*_ATOMIC_REPLACE_BACKOFF_SECONDS, None)):
        try:
            os.replace(source, destination)
            return
        except OSError as exc:
            if delay is None or not _retryable_atomic_replace_error(exc):
                raise
            time.sleep(delay)
    raise AssertionError(f"unreachable atomic replace retry state: {retry}")


def directory_tree_inventory(path: Path) -> list[dict[str, Any]]:
    """Return a path-independent, content-addressed directory inventory."""

    if not path.is_dir():
        raise OSError(f"directory tree is missing: {path}")
    inventory: list[dict[str, Any]] = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise OSError(f"directory promotion forbids symbolic links: {item}")
        if not item.is_file():
            continue
        inventory.append(
            {
                "relative_path": item.relative_to(path).as_posix(),
                "sha256": file_hash(item),
                "bytes": item.stat().st_size,
            }
        )
    return inventory


def promote_directory_exact(source: Path, destination: Path) -> dict[str, Any]:
    """Publish a directory at one exact path and verify every copied byte.

    Windows directory replacement was observed to preserve the source basename
    intermittently under the destination parent.  On Windows, copy the complete
    tree to the exact destination, compare content-addressed inventories, and
    remove the source only after verification.  Other platforms retain the
    atomic rename path.
    """

    source = source.resolve()
    destination = destination.resolve()
    if not source.is_dir():
        raise OSError(f"directory promotion source is missing: {source}")
    if destination.exists():
        raise OSError(f"directory promotion destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_inventory = directory_tree_inventory(source)
    source_tree_sha256 = object_hash(source_inventory)

    if os.name != "nt":
        replace_atomic(source, destination)
        mode = "atomic_directory_replace"
    else:
        shutil.copytree(source, destination)
        destination_inventory = directory_tree_inventory(destination)
        if destination_inventory != source_inventory:
            raise OSError(
                "verified Windows directory copy differs from the promotion source"
            )
        mode = "verified_exact_copy"

    if not destination.is_dir():
        raise OSError(
            f"directory promotion did not create the exact destination: {destination}"
        )
    destination_inventory = directory_tree_inventory(destination)
    if destination_inventory != source_inventory:
        raise OSError("promoted directory tree differs from the source inventory")

    source_retained = source.exists()
    cleanup_error: str | None = None
    if source_retained and mode == "verified_exact_copy":
        try:
            shutil.rmtree(source)
        except OSError as exc:  # The verified canonical copy remains authoritative.
            cleanup_error = str(exc)
        source_retained = source.exists()
    return {
        "mode": mode,
        "source_tree_sha256": source_tree_sha256,
        "file_count": len(source_inventory),
        "bytes": sum(item["bytes"] for item in source_inventory),
        "source_retained": source_retained,
        "source_path": str(source) if source_retained else None,
        "cleanup_error": cleanup_error,
    }


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    replace_atomic(temporary, path)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
