from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, BinaryIO, Iterable


SOURCE_ROOT = Path(r"C:\Users\99349\Desktop\serverless_sim_game_nse_dev")
ARCHIVE_DIR = Path(
    r"E:\NSEsche_experiment_archives\nse_dev_recreated_20260902"
)
ARCHIVE_PATH = ARCHIVE_DIR / "nse_dev_recreated_nonbuild_20260902.zip"
PARTIAL_PATH = ARCHIVE_PATH.with_suffix(".zip.partial")
RECEIPT_PATH = ARCHIVE_DIR / "nse_dev_recreated_nonbuild_20260902.receipt.json"
INTERNAL_MANIFEST = "__nse_redundant_copy_inventory.json"
REPARSE_POINT = 0x400
BUFFER_BYTES = 8 * 1024 * 1024
PROGRESS_INTERVAL = 500
MIN_SOURCE_FILES = 1000

EXCLUDED_DIRECTORY_NAMES = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}
STORE_SUFFIXES = {
    ".7z",
    ".bz2",
    ".dll",
    ".exe",
    ".gz",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".pyd",
    ".tar",
    ".whl",
    ".xz",
    ".zip",
    ".zst",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def object_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(BUFFER_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def copy_and_hash(source: BinaryIO, target: BinaryIO) -> tuple[int, str]:
    digest = hashlib.sha256()
    copied = 0
    while chunk := source.read(BUFFER_BYTES):
        target.write(chunk)
        digest.update(chunk)
        copied += len(chunk)
    return copied, digest.hexdigest()


def write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))
        stream.write(b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def is_excluded_directory(name: str) -> bool:
    lowered = name.lower()
    return lowered in EXCLUDED_DIRECTORY_NAMES or lowered == "target" or lowered.startswith(
        "target_"
    )


def assert_frozen_paths() -> None:
    expected_source = Path(
        r"C:\Users\99349\Desktop\serverless_sim_game_nse_dev"
    ).resolve()
    expected_archive_dir = Path(
        r"E:\NSEsche_experiment_archives\nse_dev_recreated_20260902"
    ).resolve()
    if SOURCE_ROOT.resolve() != expected_source:
        raise RuntimeError("source path is not the frozen redundant-copy target")
    if ARCHIVE_DIR.resolve() != expected_archive_dir:
        raise RuntimeError("archive directory is not the frozen E-drive target")
    if SOURCE_ROOT.parent.resolve() != Path(r"C:\Users\99349\Desktop").resolve():
        raise RuntimeError("source target escaped the Desktop parent")
    if not SOURCE_ROOT.is_dir():
        raise RuntimeError(f"source directory is missing: {SOURCE_ROOT}")
    if (SOURCE_ROOT / ".git").exists():
        raise RuntimeError("refusing to archive/delete a Git worktree")


def lstat_is_reparse(path: Path) -> bool:
    stat = path.lstat()
    return path.is_symlink() or bool(
        getattr(stat, "st_file_attributes", 0) & REPARSE_POINT
    )


def scan_source() -> tuple[list[Path], list[Path], list[str]]:
    directories: list[Path] = []
    files: list[Path] = []
    excluded: list[str] = []
    for current, directory_names, file_names in os.walk(
        SOURCE_ROOT, topdown=True, followlinks=False
    ):
        directory_names.sort()
        file_names.sort()
        current_path = Path(current)
        for name in list(directory_names):
            path = current_path / name
            if lstat_is_reparse(path):
                raise RuntimeError(f"refusing directory reparse point: {path}")
            if is_excluded_directory(name):
                directory_names.remove(name)
                excluded.append(path.relative_to(SOURCE_ROOT).as_posix())
            else:
                directories.append(path)
        for name in file_names:
            path = current_path / name
            if lstat_is_reparse(path):
                raise RuntimeError(f"refusing file reparse point: {path}")
            files.append(path)
    return directories, files, excluded


def scan_all_reparse_points() -> list[str]:
    found: list[str] = []
    for current, directory_names, file_names in os.walk(
        SOURCE_ROOT, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        for name in directory_names:
            path = current_path / name
            if lstat_is_reparse(path):
                found.append(path.relative_to(SOURCE_ROOT).as_posix())
        for name in file_names:
            path = current_path / name
            if lstat_is_reparse(path):
                found.append(path.relative_to(SOURCE_ROOT).as_posix())
    return sorted(found)


def progress(phase: str, ordinal: int, total: int, source_bytes: int = 0) -> None:
    if ordinal % PROGRESS_INTERVAL == 0 or ordinal == total:
        print(
            json.dumps(
                {
                    "phase": phase,
                    "ordinal": ordinal,
                    "file_count": total,
                    "source_gib": round(source_bytes / (1024**3), 3),
                }
            ),
            flush=True,
        )


def manifest_without_hash(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "inventory_hash"}


def create_archive(goal_path: Path, plan_path: Path) -> dict[str, Any]:
    assert_frozen_paths()
    if ARCHIVE_PATH.exists() or PARTIAL_PATH.exists() or RECEIPT_PATH.exists():
        raise RuntimeError("archive output already exists")
    if not goal_path.is_file() or not plan_path.is_file():
        raise RuntimeError("goal or plan input is missing")

    directories, files, excluded = scan_source()
    if len(files) < MIN_SOURCE_FILES:
        raise RuntimeError("source snapshot is implausibly small")
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    print(
        json.dumps(
            {
                "phase": "archive_start",
                "source": str(SOURCE_ROOT),
                "files": len(files),
                "directories": len(directories),
                "excluded_directories": len(excluded),
            }
        ),
        flush=True,
    )
    with zipfile.ZipFile(
        PARTIAL_PATH,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=1,
        allowZip64=True,
        strict_timestamps=False,
    ) as archive:
        for directory in directories:
            relative = directory.relative_to(SOURCE_ROOT).as_posix().rstrip("/") + "/"
            info = zipfile.ZipInfo.from_file(
                directory, arcname=relative, strict_timestamps=False
            )
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, b"")

        for ordinal, path in enumerate(files, start=1):
            relative = path.relative_to(SOURCE_ROOT).as_posix()
            before = path.stat()
            info = zipfile.ZipInfo.from_file(
                path, arcname=relative, strict_timestamps=False
            )
            info.compress_type = (
                zipfile.ZIP_STORED
                if path.suffix.lower() in STORE_SUFFIXES
                else zipfile.ZIP_DEFLATED
            )
            with path.open("rb") as source, archive.open(
                info, mode="w", force_zip64=True
            ) as target:
                copied, sha256 = copy_and_hash(source, target)
            after = path.stat()
            if (
                copied != before.st_size
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
            ):
                raise RuntimeError(f"source changed during archival: {path}")
            total_bytes += copied
            entries.append(
                {
                    "relative_path": relative,
                    "bytes": copied,
                    "mtime_ns": before.st_mtime_ns,
                    "sha256": sha256,
                }
            )
            progress("archive", ordinal, len(files), total_bytes)

        manifest = {
            "schema_version": "NSE_REDUNDANT_COPY_ARCHIVE_V1",
            "source_root": str(SOURCE_ROOT),
            "goal_path": str(goal_path),
            "goal_sha256": file_hash(goal_path),
            "plan_path": str(plan_path),
            "plan_sha256": file_hash(plan_path),
            "file_count": len(files),
            "directory_count": len(directories),
            "total_source_bytes": total_bytes,
            "excluded_directories": excluded,
            "entries": entries,
        }
        manifest["inventory_hash"] = object_hash(manifest)
        archive.writestr(
            INTERNAL_MANIFEST,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
            + b"\n",
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=1,
        )

    verification = verify_archive(PARTIAL_PATH)
    os.replace(PARTIAL_PATH, ARCHIVE_PATH)
    receipt = {
        "schema_version": "NSE_REDUNDANT_COPY_ARCHIVE_RECEIPT_V1",
        "created_at_unix": time.time(),
        "source_root": str(SOURCE_ROOT),
        "archive_path": str(ARCHIVE_PATH),
        "archive_sha256": file_hash(ARCHIVE_PATH),
        "archive_bytes": ARCHIVE_PATH.stat().st_size,
        "file_count": manifest["file_count"],
        "directory_count": manifest["directory_count"],
        "total_source_bytes": manifest["total_source_bytes"],
        "excluded_directories": manifest["excluded_directories"],
        "inventory_hash": manifest["inventory_hash"],
        "zip_crc_verified": verification["zip_crc_verified"],
        "all_restored_file_sha256_verified": verification[
            "all_restored_file_sha256_verified"
        ],
        "source_deleted": False,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(RECEIPT_PATH, receipt)
    print(json.dumps({"phase": "archive_complete", **receipt}), flush=True)
    return receipt


def verify_archive(path: Path = ARCHIVE_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"archive is missing: {path}")
    with zipfile.ZipFile(path, mode="r", allowZip64=True) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"ZIP CRC validation failed: {bad_member}")
        manifest = json.loads(archive.read(INTERNAL_MANIFEST).decode("utf-8"))
        if manifest.get("inventory_hash") != object_hash(manifest_without_hash(manifest)):
            raise RuntimeError("internal inventory hash mismatch")
        entries = manifest.get("entries")
        if not isinstance(entries, list) or len(entries) != manifest.get("file_count"):
            raise RuntimeError("archive inventory membership is incomplete")
        expected_names = {entry["relative_path"] for entry in entries}
        actual_names = {
            item.filename
            for item in archive.infolist()
            if not item.is_dir() and item.filename != INTERNAL_MANIFEST
        }
        if expected_names != actual_names:
            raise RuntimeError("archive file product differs from inventory")
        restored_bytes = 0
        for ordinal, entry in enumerate(entries, start=1):
            digest = hashlib.sha256()
            restored = 0
            with archive.open(entry["relative_path"], mode="r") as stream:
                while chunk := stream.read(BUFFER_BYTES):
                    digest.update(chunk)
                    restored += len(chunk)
            if restored != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
                raise RuntimeError(
                    f"restored stream differs from source: {entry['relative_path']}"
                )
            restored_bytes += restored
            progress("verify", ordinal, len(entries), restored_bytes)
    return {
        "manifest": manifest,
        "zip_crc_verified": True,
        "all_restored_file_sha256_verified": True,
        "restored_bytes": restored_bytes,
    }


def current_entries() -> Iterable[dict[str, Any]]:
    _, files, _ = scan_source()
    for ordinal, path in enumerate(files, start=1):
        stat = path.stat()
        yield {
            "relative_path": path.relative_to(SOURCE_ROOT).as_posix(),
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": file_hash(path),
        }
        progress("source_reverify", ordinal, len(files))


def delete_verified_source() -> dict[str, Any]:
    assert_frozen_paths()
    if scan_all_reparse_points():
        raise RuntimeError("source gained a reparse point after archival")
    verification = verify_archive(ARCHIVE_PATH)
    manifest = verification["manifest"]
    expected = {
        item["relative_path"]: item
        for item in manifest["entries"]
    }
    observed = {item["relative_path"]: item for item in current_entries()}
    if expected != observed:
        missing = sorted(set(expected) - set(observed))[:10]
        added = sorted(set(observed) - set(expected))[:10]
        changed = sorted(
            key for key in set(expected) & set(observed) if expected[key] != observed[key]
        )[:10]
        raise RuntimeError(
            f"source changed after archive: missing={missing}, added={added}, changed={changed}"
        )
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    if receipt.get("archive_sha256") != file_hash(ARCHIVE_PATH):
        raise RuntimeError("archive hash differs from receipt")
    if SOURCE_ROOT.resolve() != Path(
        r"C:\Users\99349\Desktop\serverless_sim_game_nse_dev"
    ).resolve():
        raise RuntimeError("delete target changed")
    shutil.rmtree(SOURCE_ROOT)
    if SOURCE_ROOT.exists():
        raise RuntimeError("source directory remains after deletion")
    receipt["source_deleted"] = True
    receipt["deleted_at_unix"] = time.time()
    receipt["receipt_hash"] = object_hash(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )
    write_json_atomic(RECEIPT_PATH, receipt)
    print(json.dumps({"phase": "delete_complete", **receipt}), flush=True)
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("archive", "verify", "delete"))
    parser.add_argument("--goal-path", type=Path)
    parser.add_argument("--plan-path", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "archive":
        if args.goal_path is None or args.plan_path is None:
            raise RuntimeError("archive requires --goal-path and --plan-path")
        create_archive(args.goal_path, args.plan_path)
    elif args.action == "verify":
        result = verify_archive()
        print(
            json.dumps(
                {
                    "phase": "verify_complete",
                    "archive": str(ARCHIVE_PATH),
                    "archive_sha256": file_hash(ARCHIVE_PATH),
                    "file_count": result["manifest"]["file_count"],
                    "restored_bytes": result["restored_bytes"],
                }
            ),
            flush=True,
        )
    else:
        delete_verified_source()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"REDUNDANT_COPY_ARCHIVE_FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise
