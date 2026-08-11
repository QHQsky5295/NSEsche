from __future__ import annotations

import bisect
import copy
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from .schema import ProtocolValidationError
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


SMALL_TAPE_BYTES = 64 * 1024 * 1024
TAPE_CATALOG_SCHEMA = "NSE_TAPE_CATALOG_V2"
BURST_TRANSFORMS: dict[str, dict[str, Any]] = {
    "spike5x50ms": {"multiplier": 5.0, "intervals": [[475, 525]]},
    "sustained3x200ms": {"multiplier": 3.0, "intervals": [[400, 600]]},
    "pulse4x4x50ms": {
        "multiplier": 4.0,
        "intervals": [[200, 250], [400, 450], [600, 650], [800, 850]],
    },
}


@dataclass(frozen=True)
class TapeInfo:
    path: str
    sha256: str
    version: int
    workload_seed: str
    event_count: int
    dag_order_sha256: str
    first_frame: int | None
    last_frame: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "version": self.version,
            "workload_seed": self.workload_seed,
            "event_count": self.event_count,
            "dag_order_sha256": self.dag_order_sha256,
            "first_frame": self.first_frame,
            "last_frame": self.last_frame,
        }


class TapeFormatError(ValueError):
    pass


def _validate_event(event: Any, index: int) -> dict[str, int]:
    if not isinstance(event, dict):
        raise TapeFormatError(f"event {index} is not an object")
    frame = event.get("frame")
    dag_id = event.get("dag_id")
    if isinstance(frame, bool) or not isinstance(frame, int) or frame < 0:
        raise TapeFormatError(f"event {index} has invalid frame")
    if isinstance(dag_id, bool) or not isinstance(dag_id, int) or dag_id < 0:
        raise TapeFormatError(f"event {index} has invalid dag_id")
    return {"frame": frame, "dag_id": dag_id}


def _read_small_tape(path: Path) -> tuple[int, str, list[dict[str, int]]]:
    try:
        tape = read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TapeFormatError(f"cannot parse tape {path}: {exc}") from exc
    if not isinstance(tape, dict) or tape.get("version") != 1:
        raise TapeFormatError("tape version must equal 1")
    seed = tape.get("workload_seed")
    if not isinstance(seed, str) or not seed:
        raise TapeFormatError("tape workload_seed must be non-empty")
    events = tape.get("events")
    if not isinstance(events, list):
        raise TapeFormatError("tape events must be an array")
    return (
        1,
        seed,
        [_validate_event(event, index) for index, event in enumerate(events)],
    )


def _stream_header_and_events(path: Path) -> tuple[int, str, Iterator[dict[str, int]]]:
    handle = path.open("r", encoding="utf-8", errors="strict")
    buffer = ""
    pattern = re.compile(r'"events"\s*:\s*\[')
    try:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                raise TapeFormatError("events array header was not found")
            buffer += chunk
            match = pattern.search(buffer)
            if match:
                header = buffer[: match.start()]
                buffer = buffer[match.end() :]
                break
            if len(buffer) > 16 * 1024 * 1024:
                raise TapeFormatError("tape header exceeds 16 MiB")
        version_match = re.search(r'"version"\s*:\s*(\d+)', header)
        seed_match = re.search(r'"workload_seed"\s*:\s*("(?:\\.|[^"\\])*")', header)
        if version_match is None or int(version_match.group(1)) != 1:
            raise TapeFormatError("tape version must equal 1")
        if seed_match is None:
            raise TapeFormatError("tape workload_seed is missing")
        seed = json.loads(seed_match.group(1))
        if not isinstance(seed, str) or not seed:
            raise TapeFormatError("tape workload_seed must be non-empty")
    except Exception:
        handle.close()
        raise

    def iterator() -> Iterator[dict[str, int]]:
        nonlocal buffer
        decoder = json.JSONDecoder()
        index = 0
        eof = False
        try:
            while True:
                buffer = buffer.lstrip()
                while buffer.startswith(","):
                    buffer = buffer[1:].lstrip()
                if buffer.startswith("]"):
                    remainder = buffer[1:] + handle.read()
                    if re.fullmatch(r"\s*}\s*", remainder) is None:
                        raise TapeFormatError("tape has no closing ]}")
                    return
                try:
                    value, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError as exc:
                    if eof:
                        raise TapeFormatError(
                            f"truncated event {index}: {exc}"
                        ) from exc
                    if len(buffer) > 32 * 1024 * 1024:
                        raise TapeFormatError("one tape event exceeds 32 MiB")
                    chunk = handle.read(1024 * 1024)
                    if chunk:
                        buffer += chunk
                    else:
                        eof = True
                    continue
                yield _validate_event(value, index)
                index += 1
                buffer = buffer[end:]
        finally:
            handle.close()

    return 1, seed, iterator()


def _event_source(path: Path, mode: str) -> tuple[int, str, Iterable[dict[str, int]]]:
    if mode not in {"auto", "small", "stream"}:
        raise ValueError("mode must be auto, small, or stream")
    selected = (
        "small"
        if mode == "small"
        or (mode == "auto" and path.stat().st_size <= SMALL_TAPE_BYTES)
        else "stream"
    )
    if selected == "small":
        return _read_small_tape(path)
    return _stream_header_and_events(path)


def inspect_tape(path: Path, mode: str = "auto") -> TapeInfo:
    path = path.resolve()
    version, seed, events = _event_source(path, mode)
    import hashlib

    dag_digest = hashlib.sha256()
    count = 0
    first_frame: int | None = None
    last_frame: int | None = None
    previous_frame = -1
    for event in events:
        if event["frame"] < previous_frame:
            raise TapeFormatError(f"event {count} frame order decreases")
        previous_frame = event["frame"]
        first_frame = event["frame"] if first_frame is None else first_frame
        last_frame = event["frame"]
        dag_digest.update(f"{event['dag_id']}\n".encode("ascii"))
        count += 1
    return TapeInfo(
        path=str(path),
        sha256=file_hash(path),
        version=version,
        workload_seed=seed,
        event_count=count,
        dag_order_sha256=dag_digest.hexdigest(),
        first_frame=first_frame,
        last_frame=last_frame,
    )


def _write_tape(
    output: Path,
    seed: str,
    events: Iterable[dict[str, int]],
    derivation: dict[str, Any],
) -> None:
    if output.exists():
        raise FileExistsError(f"immutable tape already exists: {output}")
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"partial tape already exists: {partial}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with partial.open("xb") as handle:
            header = {
                "version": 1,
                "workload_seed": seed,
                "derivation": derivation,
            }
            encoded_header = json.dumps(
                header, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            handle.write(encoded_header[:-1].encode("utf-8"))
            handle.write(b',"events":[')
            first = True
            for sequence, event in enumerate(events):
                if not first:
                    handle.write(b",")
                first = False
                output_event = {
                    "frame": event["frame"],
                    "dag_id": event["dag_id"],
                    "sequence": sequence,
                }
                handle.write(
                    json.dumps(
                        output_event, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                )
            handle.write(b"]}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(partial, output)
    finally:
        if partial.exists():
            partial.unlink()


def derive_burst_tape(
    parent: Path,
    output: Path,
    scenario: str,
    *,
    horizon_frames: int = 1000,
    mode: str = "auto",
) -> dict[str, Any]:
    if scenario not in BURST_TRANSFORMS:
        raise ValueError(f"unknown burst scenario {scenario!r}")
    if horizon_frames <= 0:
        raise ValueError("horizon_frames must be positive")
    parent_info = inspect_tape(parent, mode)
    transform = BURST_TRANSFORMS[scenario]
    weights = [1.0] * horizon_frames
    for start, end in transform["intervals"]:
        for frame in range(max(0, start), min(horizon_frames, end)):
            weights[frame] = float(transform["multiplier"])
    cumulative: list[float] = []
    total_weight = 0.0
    for weight in weights:
        total_weight += weight
        cumulative.append(total_weight)

    _, seed, parent_events = _event_source(parent, mode)
    event_count = parent_info.event_count

    def remapped() -> Iterator[dict[str, int]]:
        for rank, event in enumerate(parent_events):
            target = (rank + 0.5) * total_weight / max(event_count, 1)
            frame = min(bisect.bisect_left(cumulative, target), horizon_frames - 1)
            yield {"frame": frame, "dag_id": event["dag_id"]}

    derivation = {
        "schema": "NSE_TAPE_DERIVATION_V1",
        "kind": "cdf_burst_remap",
        "scenario": scenario,
        "horizon_frames": horizon_frames,
        "multiplier": transform["multiplier"],
        "intervals": transform["intervals"],
        "parent_sha256": parent_info.sha256,
        "parent_event_count": parent_info.event_count,
        "event_count_invariant": "exact",
        "dag_order_invariant": "exact",
    }
    _write_tape(output, seed, remapped(), derivation)
    derived = inspect_tape(output, mode)
    if derived.event_count != parent_info.event_count:
        raise ProtocolValidationError("burst derivation changed the event count")
    if derived.dag_order_sha256 != parent_info.dag_order_sha256:
        raise ProtocolValidationError("burst derivation changed DAG/event order")
    return {
        **derived.to_dict(),
        "measured_arrival_rate_rps": derived.event_count / (horizon_frames * 0.001),
        "kind": "derived_burst",
        "parent_path": str(parent),
        "parent_sha256": parent_info.sha256,
        "transform": derivation,
    }


def derive_scaled_tape(
    parent: Path,
    output: Path,
    factor: int,
    *,
    horizon_frames: int = 1000,
    mode: str = "auto",
) -> dict[str, Any]:
    if factor not in {5, 25}:
        raise ValueError("weak-scaling factor must be exactly 5 or 25")
    parent_info = inspect_tape(parent, mode)
    _, seed, parent_events = _event_source(parent, mode)

    def replicated() -> Iterator[dict[str, int]]:
        for event in parent_events:
            for _ in range(factor):
                yield {"frame": event["frame"], "dag_id": event["dag_id"]}

    derivation = {
        "schema": "NSE_TAPE_DERIVATION_V1",
        "kind": "same_frame_replication",
        "factor": factor,
        "parent_sha256": parent_info.sha256,
        "parent_event_count": parent_info.event_count,
        "expected_event_count": parent_info.event_count * factor,
        "arrival_frame_invariant": "exact_per_parent_event",
    }
    _write_tape(output, seed, replicated(), derivation)
    derived = inspect_tape(output, mode)
    if derived.event_count != parent_info.event_count * factor:
        raise ProtocolValidationError(
            "weak-scaling derivation does not have the exact factor"
        )
    return {
        **derived.to_dict(),
        "measured_arrival_rate_rps": derived.event_count / (horizon_frames * 0.001),
        "kind": "derived_scale",
        "parent_path": str(parent),
        "parent_sha256": parent_info.sha256,
        "transform": derivation,
    }


def derive_capacity_tape(
    parent: Path,
    output: Path,
    factor: int,
    *,
    horizon_frames: int = 1000,
    mode: str = "auto",
) -> dict[str, Any]:
    """Create a predeclared integer-rate tape for an isolated capacity pilot.

    This is deliberately separate from E2 weak scaling: the resulting tape is
    calibration-only and must never be registered as an E1--E9 evaluation tape.
    """

    if isinstance(factor, bool) or not isinstance(factor, int) or factor < 1:
        raise ValueError("capacity-pilot replication factor must be a positive integer")
    if horizon_frames <= 0:
        raise ValueError("capacity-pilot arrival horizon must be positive")
    parent_info = inspect_tape(parent, mode)
    _, seed, parent_events = _event_source(parent, mode)

    def replicated() -> Iterator[dict[str, int]]:
        for event in parent_events:
            for _ in range(factor):
                yield {"frame": event["frame"], "dag_id": event["dag_id"]}

    derivation = {
        "schema": "NSE_TAPE_DERIVATION_V1",
        "kind": "isolated_capacity_same_frame_replication",
        "factor": factor,
        "parent_sha256": parent_info.sha256,
        "parent_event_count": parent_info.event_count,
        "expected_event_count": parent_info.event_count * factor,
        "arrival_frame_invariant": "exact_per_parent_event",
        "scope": "sla_pilot_only",
    }
    _write_tape(output, seed, replicated(), derivation)
    derived = inspect_tape(output, mode)
    if derived.event_count != parent_info.event_count * factor:
        raise ProtocolValidationError(
            "capacity-pilot derivation does not have the exact factor"
        )
    return {
        **derived.to_dict(),
        "measured_arrival_rate_rps": derived.event_count / (horizon_frames * 0.001),
        "kind": "isolated_capacity_tape",
        "parent_path": str(parent.resolve()),
        "parent_sha256": parent_info.sha256,
        "transform": derivation,
    }


def register_catalog_entry(
    catalog_path: Path, key: str, entry: dict[str, Any]
) -> dict[str, Any]:
    if catalog_path.exists():
        catalog = read_json(catalog_path)
    else:
        catalog = {
            "schema_version": TAPE_CATALOG_SCHEMA,
            "created_at": utc_now(),
            "entries": {},
        }
    if (
        not isinstance(catalog, dict)
        or catalog.get("schema_version") != TAPE_CATALOG_SCHEMA
    ):
        raise ProtocolValidationError("invalid tape catalog schema")
    entries = catalog.setdefault("entries", {})
    if key in entries and entries[key] != entry:
        raise ProtocolValidationError(
            f"refusing to replace immutable tape catalog key {key!r}"
        )
    entries[key] = entry
    catalog["updated_at"] = utc_now()
    payload = dict(catalog)
    payload.pop("catalog_hash", None)
    catalog["catalog_hash"] = object_hash(payload)
    write_json_atomic(catalog_path, catalog)
    return catalog


def register_base_tape(
    catalog_path: Path,
    key: str,
    path: Path,
    mode: str = "auto",
    *,
    horizon_frames: int = 1000,
    frame_duration_seconds: float = 0.001,
) -> dict[str, Any]:
    if horizon_frames <= 0 or frame_duration_seconds <= 0:
        raise ValueError("tape observation horizon must be positive")
    info = inspect_tape(path, mode)
    entry = {
        **info.to_dict(),
        "kind": "base_steady",
        "parent_sha256": None,
        "transform": {"kind": "identity"},
        "measured_arrival_rate_rps": info.event_count
        / (horizon_frames * frame_duration_seconds),
    }
    register_catalog_entry(catalog_path, key, entry)
    return entry


def derive_required_tapes(
    manifest: dict[str, Any],
    catalog_path: Path,
    output_root: Path,
    *,
    mode: str = "auto",
) -> list[dict[str, Any]]:
    """Create every missing E2/E3 derived tape declared by a manifest.

    Base tapes are never generated here: they must first be captured from the
    simulator and registered under their manifest key.
    """
    if catalog_path.exists():
        catalog = read_json(catalog_path)
    else:
        raise ProtocolValidationError("tape catalog does not exist")
    if (
        not isinstance(catalog, dict)
        or catalog.get("schema_version") != TAPE_CATALOG_SCHEMA
    ):
        raise ProtocolValidationError("invalid tape catalog schema")
    entries = catalog.get("entries")
    if not isinstance(entries, dict):
        raise ProtocolValidationError("tape catalog entries must be an object")
    plans: dict[str, dict[str, Any]] = {}
    for run in manifest.get("runs", []):
        plan = run.get("workload_tape")
        if isinstance(plan, dict):
            plans.setdefault(str(plan.get("key")), plan)
    created: list[dict[str, Any]] = []
    for key in sorted(plans):
        plan = plans[key]
        if plan.get("kind") not in {"derived_scale", "derived_burst"} or key in entries:
            continue
        parent_key = plan.get("parent_key")
        parent_entry = entries.get(parent_key)
        if not isinstance(parent_entry, dict):
            raise ProtocolValidationError(
                f"cannot derive {key!r}: parent base tape {parent_key!r} is not registered"
            )
        parent_path = Path(parent_entry["path"])
        if not parent_path.is_absolute():
            parent_path = (catalog_path.resolve().parent / parent_path).resolve()
        if file_hash(parent_path) != parent_entry.get("sha256"):
            raise ProtocolValidationError(
                f"parent tape hash mismatch for {parent_key!r}"
            )
        output = Path(plan["path"])
        if not output.is_absolute():
            output = (output_root.resolve() / output).resolve()
        if plan["kind"] == "derived_scale":
            entry = derive_scaled_tape(
                parent_path,
                output,
                int(plan["transform"]["factor"]),
                horizon_frames=int(manifest["simulation"]["expected_final_frame"]),
                mode=mode,
            )
        else:
            entry = derive_burst_tape(
                parent_path,
                output,
                str(plan["transform"]["scenario"]),
                horizon_frames=int(manifest["simulation"]["expected_final_frame"]),
                mode=mode,
            )
        entry["capture_environment"] = parent_entry.get("capture_environment")
        entry["capture_receipt_path"] = parent_entry.get("capture_receipt_path")
        entry["capture_receipt_sha256"] = parent_entry.get("capture_receipt_sha256")
        entry["workload_profile"] = copy.deepcopy(plan["workload_profile"])
        entry["provenance"] = dict(parent_entry.get("provenance", {}))
        entry["provenance"]["measured_arrival_rate_rps"] = entry[
            "measured_arrival_rate_rps"
        ]
        register_catalog_entry(catalog_path, key, entry)
        entries[key] = entry
        created.append({"key": key, **entry})
    return created
