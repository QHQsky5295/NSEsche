from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

from .schema import ProtocolValidationError
from .util import canonical_json_bytes, object_hash, utc_now


GENESIS_HASH = "0" * 64


class Ledger:
    """Append-only, hash-chained audit ledger."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sequence, self._last_hash = self.verify()

    def iter_events(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ProtocolValidationError(
                        f"ledger line {line_number} is invalid JSON: {exc}"
                    ) from exc
                if not isinstance(event, dict):
                    raise ProtocolValidationError(
                        f"ledger line {line_number} is not an object"
                    )
                yield event

    def verify(self) -> tuple[int, str]:
        expected_sequence = 1
        previous_hash = GENESIS_HASH
        for event in self.iter_events() or ():
            sequence = event.get("sequence")
            if sequence != expected_sequence:
                raise ProtocolValidationError(
                    f"ledger sequence mismatch: expected {expected_sequence}, got {sequence}"
                )
            if event.get("previous_hash") != previous_hash:
                raise ProtocolValidationError(
                    f"ledger previous_hash mismatch at sequence {sequence}"
                )
            actual_hash = event.get("event_hash")
            payload = dict(event)
            payload.pop("event_hash", None)
            expected_hash = object_hash(payload)
            if actual_hash != expected_hash:
                raise ProtocolValidationError(
                    f"ledger event_hash mismatch at sequence {sequence}"
                )
            previous_hash = actual_hash
            expected_sequence += 1
        return expected_sequence - 1, previous_hash

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "ledger_version": "1.0",
            "sequence": self._sequence + 1,
            "timestamp": utc_now(),
            "event_type": event_type,
            "payload": payload,
            "previous_hash": self._last_hash,
        }
        event["event_hash"] = object_hash(event)
        line = canonical_json_bytes(event) + b"\n"
        descriptor = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            os.write(descriptor, line)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self._sequence += 1
        self._last_hash = event["event_hash"]
        return event


def verify_ledger(path: Path) -> tuple[int, str]:
    return Ledger(path).verify()
