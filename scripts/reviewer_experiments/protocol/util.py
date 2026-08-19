from __future__ import annotations

import hashlib
import json
import os
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
