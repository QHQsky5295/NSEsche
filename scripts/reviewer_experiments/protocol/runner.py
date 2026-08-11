from __future__ import annotations

import gzip
import hashlib
import importlib.metadata
import copy
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

try:
    import psutil
except ImportError:  # pragma: no cover - the formal requirements install it.
    psutil = None

from .ledger import Ledger
from .faasrank_model import FaaSRankModelError, verify_frozen_faasrank_model
from .qc import (
    QCIssue,
    QCReport,
    evaluate_attempt,
    technical_failure_signature,
)
from .schema import ProtocolValidationError, load_and_validate_manifest
from .sla import SlaFreezeError, load_frozen_sla_targets
from .tape import TapeFormatError, inspect_tape
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


class ProtocolRunError(RuntimeError):
    pass


class _WorkspaceLock:
    """Cross-platform advisory lock released automatically when the process exits."""

    def __init__(self, path: Path):
        self.path = path
        self.handle: Any = None

    def __enter__(self) -> "_WorkspaceLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0)
        if self.handle.read(1) == b"":
            self.handle.seek(0)
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            self.handle = None
            raise ProtocolRunError(
                f"another protocol runner holds {self.path}"
            ) from exc
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.handle is None:
            return
        self.handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
        self.handle = None


def _attempt_number(path: Path) -> int | None:
    name = path.name
    if not name.startswith("attempt-"):
        return None
    try:
        return int(name.removeprefix("attempt-"))
    except ValueError:
        return None


class ProtocolRunner:
    def __init__(self, manifest_path: Path, workspace: Path):
        self.manifest_path = manifest_path.resolve()
        self.manifest = load_and_validate_manifest(self.manifest_path)
        self.workspace = workspace.resolve()
        # Capture the software environment before the runner creates experiment
        # outputs.  A dirty worktree is evidence, not a reason to reject a run.
        self._adapter_binary_hash_cache: dict[tuple[str, int, int], str] = {}
        self._static_runtime_provenance = self._collect_static_runtime_provenance()
        self.partial_root = self.workspace / "partial"
        self.quarantine_root = self.workspace / "quarantine"
        self.canonical_root = self.workspace / "canonical"
        for directory in (self.partial_root, self.quarantine_root, self.canonical_root):
            directory.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.workspace / "ledger.jsonl")
        self._verified_tapes: dict[tuple[str, str], dict[str, Any]] = {}
        self._verified_workload_packages: dict[
            tuple[str, str, str, str], dict[str, Any]
        ] = {}

    def _assert_ready(self, command_override: list[str] | None) -> None:
        command = command_override or self.manifest["execution"].get(
            "command_template", []
        )
        if not command:
            raise ProtocolRunError(
                "no execution command is frozen; set execution.command_template in the protocol config "
                "or pass a command override"
            )
        if psutil is None:
            raise ProtocolRunError(
                "psutil is required for formal process CPU/peak-RSS observation; "
                "install protocol/requirements.txt"
            )
        hpa = self.manifest["common_hpa"]
        unset = [
            name
            for name in (
                "target_mem_use_rate",
                "tolerance",
                "check_period_frames",
                "careful_down_history",
                "min_instances_when_pending",
                "allow_scale_to_zero",
                "scale_up_placement",
            )
            if hpa.get(name) is None
        ]
        if unset:
            raise ProtocolRunError(
                "formal common-HPA fields are not frozen: " + ", ".join(unset)
            )

    def _resolve_manifest_input(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.manifest_path.parent / path
        return path.resolve()

    def _execution_cwd(self) -> Path:
        setting = Path(self.manifest.get("execution", {}).get("cwd", "."))
        return (
            setting.resolve()
            if setting.is_absolute()
            else (Path.cwd() / setting).resolve()
        )

    @staticmethod
    def _run_read_only_command(
        command: list[str], cwd: Path
    ) -> tuple[int | None, str, str]:
        """Run a bounded provenance query without making it a run precondition."""

        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
            return (
                completed.returncode,
                completed.stdout.strip(),
                completed.stderr.strip(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return None, "", repr(exc)

    def _collect_git_provenance(self, cwd: Path) -> dict[str, Any]:
        code, root_text, error = self._run_read_only_command(
            ["git", "rev-parse", "--show-toplevel"], cwd
        )
        if code != 0 or not root_text:
            return {
                "available": False,
                "commit": None,
                "dirty": None,
                "repository_root": None,
                "error": error or root_text or f"git exited with {code}",
            }
        root = Path(root_text).resolve()
        commit_code, commit, commit_error = self._run_read_only_command(
            ["git", "rev-parse", "HEAD"], root
        )
        status_code, status, status_error = self._run_read_only_command(
            ["git", "status", "--porcelain=v1", "--untracked-files=normal"], root
        )
        status_lines = status.splitlines() if status else []
        return {
            "available": commit_code == 0 and status_code == 0,
            "commit": commit if commit_code == 0 and commit else None,
            "dirty": bool(status_lines) if status_code == 0 else None,
            "dirty_entry_count": len(status_lines) if status_code == 0 else None,
            "dirty_listing_sha256": (
                hashlib.sha256(status.encode("utf-8")).hexdigest()
                if status_code == 0
                else None
            ),
            "repository_root": str(root),
            "error": commit_error or status_error or None,
        }

    @staticmethod
    def _file_evidence(
        path: Path, *, relative_to: Path | None = None
    ) -> dict[str, Any]:
        resolved = path.resolve()
        evidence: dict[str, Any] = {
            "path": str(resolved),
            "exists": resolved.is_file(),
            "sha256": None,
            "bytes": None,
        }
        if relative_to is not None:
            try:
                relative_path = resolved.relative_to(relative_to.resolve()).as_posix()
                # Attempts are atomically moved from partial/ to quarantine/ or
                # canonical/.  Keep in-attempt evidence relocation invariant.
                evidence["path"] = relative_path
                evidence["relative_path"] = relative_path
            except ValueError:
                evidence["relative_path"] = None
        if resolved.is_file():
            evidence["sha256"] = file_hash(resolved)
            evidence["bytes"] = resolved.stat().st_size
        return evidence

    def _collect_static_runtime_provenance(self) -> dict[str, Any]:
        cwd = self._execution_cwd()
        git = self._collect_git_provenance(cwd)
        candidate_roots: list[Path] = [cwd]
        if git.get("repository_root"):
            candidate_roots.insert(0, Path(str(git["repository_root"])))
        candidate_roots.extend(
            (self.manifest_path.parent, self.manifest_path.parent.parent)
        )
        cargo_candidates: list[Path] = []
        seen: set[Path] = set()
        for root in candidate_roots:
            for candidate in (
                root / "Cargo.lock",
                root / "serverless_sim" / "Cargo.lock",
            ):
                candidate = candidate.resolve()
                if candidate not in seen:
                    seen.add(candidate)
                    if candidate.is_file():
                        cargo_candidates.append(candidate)
        cargo_locks = [self._file_evidence(path) for path in cargo_candidates]
        packages = sorted(
            {
                (
                    str(
                        distribution.metadata.get(
                            "Name", distribution.metadata.get("Summary", "unknown")
                        )
                    ),
                    str(distribution.version),
                )
                for distribution in importlib.metadata.distributions()
            },
            key=lambda item: (item[0].casefold(), item[1]),
        )
        package_records = [
            {"name": name, "version": version} for name, version in packages
        ]
        rust_tools: dict[str, Any] = {}
        for tool, command in (
            ("rustc", ["rustc", "--version", "--verbose"]),
            ("cargo", ["cargo", "--version", "--verbose"]),
        ):
            code, stdout, stderr = self._run_read_only_command(command, cwd)
            rust_tools[tool] = {
                "available": code == 0,
                "exit_code": code,
                "version_output": stdout if code == 0 else None,
                "error": stderr or None,
            }
        return {
            "captured_at": utc_now(),
            "git": git,
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "full_version": sys.version,
                "executable": str(Path(sys.executable).resolve()),
                "executable_sha256": file_hash(Path(sys.executable).resolve()),
                "packages": package_records,
                "packages_sha256": object_hash(package_records),
            },
            "rust": rust_tools,
            "cargo_lock": cargo_locks[0] if cargo_locks else None,
            "cargo_locks": cargo_locks,
        }

    def _runtime_provenance(self) -> dict[str, Any]:
        # A few unit-level callers construct the runner without __init__.
        provenance = getattr(self, "_static_runtime_provenance", None)
        if provenance is None:
            self._adapter_binary_hash_cache = {}
            provenance = self._collect_static_runtime_provenance()
            self._static_runtime_provenance = provenance
        return copy.deepcopy(provenance)

    @staticmethod
    def _read_optional_json(path: Path) -> tuple[Any | None, str | None]:
        if not path.is_file():
            return None, None
        try:
            return read_json(path), None
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return None, repr(exc)

    def _adapter_binary_evidence(self, attempt_dir: Path) -> dict[str, Any] | None:
        observation_path = attempt_dir / "adapter_observation.json"
        observation, parse_error = self._read_optional_json(observation_path)
        if observation is None and parse_error is None:
            return None
        evidence: dict[str, Any] = {
            "observation": self._file_evidence(
                observation_path, relative_to=attempt_dir
            ),
            "observation_parse_error": parse_error,
            "path": None,
            "observed_sha256": None,
            "verified_sha256": None,
            "observed_hash_matches_file": None,
        }
        if not isinstance(observation, dict):
            return evidence
        executable_value = observation.get("server_executable")
        observed_hash = observation.get("server_executable_sha256")
        evidence["path"] = (
            executable_value if isinstance(executable_value, str) else None
        )
        evidence["observed_sha256"] = (
            observed_hash if isinstance(observed_hash, str) else None
        )
        if not isinstance(executable_value, str) or not executable_value:
            return evidence
        executable = Path(executable_value).resolve()
        if not executable.is_file():
            evidence["file_present_when_manifest_written"] = False
            return evidence
        stat = executable.stat()
        cache_key = (str(executable), stat.st_size, stat.st_mtime_ns)
        cache = getattr(self, "_adapter_binary_hash_cache", None)
        if cache is None:
            cache = {}
            self._adapter_binary_hash_cache = cache
        verified_hash = cache.get(cache_key)
        if verified_hash is None:
            verified_hash = file_hash(executable)
            cache[cache_key] = verified_hash
        evidence.update(
            {
                "file_present_when_manifest_written": True,
                "bytes": stat.st_size,
                "verified_sha256": verified_hash,
                "observed_hash_matches_file": observed_hash == verified_hash,
            }
        )
        return evidence

    @staticmethod
    def _selected_process_observation(observation: Any) -> dict[str, Any] | None:
        if not isinstance(observation, dict):
            return None
        keys = (
            "duration_seconds",
            "sample_interval_seconds",
            "samples",
            "peak_process_tree_rss_bytes",
            "peak_process_tree_vms_bytes",
            "peak_process_tree_count",
            "process_tree_cpu_seconds",
            "timed_out",
            "exit_code",
        )
        return {key: observation.get(key) for key in keys}

    @staticmethod
    def _artifact_inventory(attempt_dir: Path) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for path in sorted(attempt_dir.rglob("*")):
            if not path.is_file() or path.name == "manifest.json":
                continue
            artifacts.append(
                {
                    "relative_path": path.relative_to(attempt_dir).as_posix(),
                    "sha256": file_hash(path),
                    "bytes": path.stat().st_size,
                }
            )
        return artifacts

    def _jsonl_archive_evidence(self, attempt_dir: Path) -> dict[str, Any]:
        summary_path = attempt_dir / "jsonl_archive_summary.json"
        summary, parse_error = self._read_optional_json(summary_path)
        files: list[dict[str, Any]] = []
        if isinstance(summary, dict):
            for item in summary.get("artifacts", []):
                if not isinstance(item, dict):
                    continue
                relative = item.get("gzip_relative_path")
                if not isinstance(relative, str):
                    continue
                path = attempt_dir / relative
                files.append(
                    {
                        "relative_path": Path(relative).as_posix(),
                        "directory": Path(relative).parent.as_posix(),
                        "sha256": file_hash(path) if path.is_file() else None,
                        "bytes": path.stat().st_size if path.is_file() else None,
                        "raw_sha256": item.get("raw_sha256"),
                        "raw_bytes": item.get("raw_bytes"),
                        "raw_lines": item.get("raw_lines"),
                        "lossless_verified": item.get("lossless_verified"),
                    }
                )
        return {
            "summary": (
                self._file_evidence(summary_path, relative_to=attempt_dir)
                if summary_path.is_file()
                else None
            ),
            "summary_parse_error": parse_error,
            "directories": sorted({item["directory"] for item in files}),
            "files": files,
        }

    def _audit_manifest_payload(
        self,
        run: dict[str, Any],
        attempt: int,
        attempt_dir: Path,
        *,
        status: str,
        report: QCReport | None,
    ) -> dict[str, Any]:
        run_config_path = attempt_dir / "run_config.json"
        process_path = attempt_dir / "process_observation.json"
        process_observation, process_parse_error = self._read_optional_json(
            process_path
        )
        experiment = run.get("simulator_experiment", {})
        reference = run.get("reference_dependency")
        tape_path = self._resolve_manifest_input(run["workload_tape"]["path"])
        capture_receipt_path = self._resolve_manifest_input(
            run["workload_tape"]["capture_receipt_path"]
        )
        workload_package_key = self._workload_package_cache_key(
            tape_path,
            run["workload_tape"]["sha256"],
            capture_receipt_path,
            run["workload_tape"]["capture_receipt_sha256"],
        )
        workload_package = self._verified_workload_packages.get(workload_package_key)
        if workload_package is None:
            raise ProtocolRunError(
                f"workload package was not verified before auditing {run['run_id']}"
            )
        environment_hashes = (
            report.observations.get("environment_semantic_hashes", {})
            if report is not None
            else {}
        )
        payload: dict[str, Any] = {
            "schema_version": "NSE_RUN_AUDIT_MANIFEST_V1",
            "created_at": utc_now(),
            "status": status,
            "protocol_manifest": {
                "path": str(self.manifest_path),
                "protocol_id": self.manifest.get("protocol_id"),
                "schema_version": self.manifest.get("schema_version"),
                "manifest_hash": self.manifest.get("manifest_hash"),
                "file_sha256": file_hash(self.manifest_path),
            },
            "run": {
                "run_id": run.get("run_id"),
                "run_spec_hash": run.get("run_spec_hash"),
                "experiment_id": run.get("experiment_id"),
                "cell_id": run.get("cell_id"),
                "method": run.get("method"),
                "variant": run.get("variant"),
                "attempt": attempt,
                "frozen_spec": copy.deepcopy(run),
            },
            "seeds": {
                "workload_seed": experiment.get("workload_seed"),
                "topology_seed": experiment.get("topology_seed"),
                "algorithm_seed": experiment.get("algorithm_seed"),
            },
            "immutable_inputs": {
                "workload_tape": {
                    "path": str(tape_path),
                    "sha256": run["workload_tape"].get("sha256"),
                    "event_count": run["workload_tape"].get("event_count"),
                    "capture_receipt_sha256": run["workload_tape"].get(
                        "capture_receipt_sha256"
                    ),
                },
                "workload_package": copy.deepcopy(workload_package),
                "offline_reference": (
                    {
                        "path": str(self._resolve_manifest_input(reference["path"])),
                        "sha256": reference.get("sha256"),
                        "bytes": reference.get("bytes"),
                        "receipt_sha256": reference.get("receipt_sha256"),
                        "build_spec_hash": reference.get("build_spec_hash"),
                        "state_pair_sequence_sha256": reference.get(
                            "state_pair_sequence_sha256"
                        ),
                        "assignment_sequence_sha256": reference.get(
                            "assignment_sequence_sha256"
                        ),
                    }
                    if isinstance(reference, dict)
                    else None
                ),
                "sla_targets": (
                    {
                        "path": str(
                            self._resolve_manifest_input(
                                run["sla_targets"]["artifact_path"]
                            )
                        ),
                        **{
                            key: run["sla_targets"].get(key)
                            for key in (
                                "artifact_sha256",
                                "artifact_bytes",
                                "document_sha256",
                                "targets_sha256",
                                "source_bundle_sha256",
                            )
                        },
                    }
                    if isinstance(run.get("sla_targets"), dict)
                    else None
                ),
                "faasrank_model": (
                    {
                        "path": str(
                            self._resolve_manifest_input(
                                run["baseline_model"]["artifact_path"]
                            )
                        ),
                        **{
                            key: run["baseline_model"].get(key)
                            for key in (
                                "artifact_sha256",
                                "artifact_bytes",
                                "training_tape_sha256",
                            )
                        },
                    }
                    if run.get("baseline_model", {}).get("state") == "frozen"
                    else None
                ),
            },
            "configuration": {
                "common_hpa_hash": run.get("common_hpa_hash"),
                "common_hpa": copy.deepcopy(run.get("common_hpa")),
                "cluster": copy.deepcopy(run.get("cluster")),
                "node_count": experiment.get("node_count"),
                "node_profile": copy.deepcopy(experiment.get("node_profile")),
                "qos": copy.deepcopy(experiment.get("qos")),
                "ablation": copy.deepcopy(experiment.get("ablation")),
                "faasrank_model": copy.deepcopy(experiment.get("faasrank_model")),
            },
            "run_config": self._file_evidence(run_config_path, relative_to=attempt_dir),
            "software_environment": self._runtime_provenance(),
            "adapter_binary": self._adapter_binary_evidence(attempt_dir),
            "process_observation": {
                "artifact": (
                    self._file_evidence(process_path, relative_to=attempt_dir)
                    if process_path.is_file()
                    else None
                ),
                "parse_error": process_parse_error,
                "measurements": self._selected_process_observation(process_observation),
            },
            "qc": {
                "passed": report.passed if report is not None else None,
                "classification": report.classification if report is not None else None,
                "failure_signature": (
                    technical_failure_signature(report) if report is not None else None
                ),
                "environment_semantic_hashes": copy.deepcopy(environment_hashes),
            },
            "compressed_jsonl": self._jsonl_archive_evidence(attempt_dir),
            "final_artifacts": self._artifact_inventory(attempt_dir),
        }
        payload["audit_manifest_hash"] = object_hash(payload)
        return payload

    def _write_audit_manifest(
        self,
        run: dict[str, Any],
        attempt: int,
        attempt_dir: Path,
        *,
        status: str,
        report: QCReport | None,
    ) -> dict[str, Any]:
        payload = self._audit_manifest_payload(
            run, attempt, attempt_dir, status=status, report=report
        )
        write_json_atomic(attempt_dir / "manifest.json", payload)
        return payload

    @staticmethod
    def _workload_package_cache_key(
        tape_path: Path,
        tape_sha256: str,
        receipt_path: Path,
        receipt_sha256: str,
    ) -> tuple[str, str, str, str]:
        return (
            str(tape_path.resolve()),
            tape_sha256,
            str(receipt_path.resolve()),
            receipt_sha256,
        )

    def _validate_workload_package(
        self,
        run: dict[str, Any],
        tape_path: Path,
        receipt_path: Path,
    ) -> dict[str, Any]:
        """Verify the replay tape, its capture receipt, and frozen environment snapshot."""
        tape = run["workload_tape"]
        capture = tape.get("capture_environment")
        if not isinstance(capture, dict):
            raise ProtocolRunError(
                f"workload package lacks a capture environment binding for {run['run_id']}"
            )
        try:
            receipt = read_json(receipt_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolRunError(
                f"workload capture receipt cannot be parsed: {receipt_path}: {exc}"
            ) from exc
        if (
            not isinstance(receipt, dict)
            or receipt.get("schema_version") != "NSE_BASE_TAPE_CAPTURE_RECEIPT_V1"
        ):
            raise ProtocolRunError(
                f"workload capture receipt schema is invalid: {receipt_path}"
            )

        is_base = tape.get("kind") == "base_steady"
        capture_tape_key = tape.get("key") if is_base else tape.get("parent_key")
        capture_tape_sha256 = (
            tape.get("sha256") if is_base else tape.get("parent_sha256")
        )
        if (
            receipt.get("key") != capture_tape_key
            or receipt.get("seed") != run.get("seed")
            or receipt.get("tape_sha256") != capture_tape_sha256
        ):
            raise ProtocolRunError(
                f"workload capture receipt does not bind the replay tape lineage for {run['run_id']}"
            )
        if is_base and receipt.get("tape_event_count") != tape.get("event_count"):
            raise ProtocolRunError(
                f"workload capture receipt event count differs from the base tape for {run['run_id']}"
            )
        if (
            receipt.get("source_kind") != "azure_trace_derived_empirical_cdf"
            or receipt.get("source_is_direct_raw_trace") is not False
        ):
            raise ProtocolRunError(
                f"workload capture receipt source declaration is invalid for {run['run_id']}"
            )

        capture_fields = (
            "function_dag_qos_sha256",
            "node_network_sha256",
            "capture_environment_sha256",
            "function_count",
            "node_count",
            "semantic_bundle_sha256",
        )
        if any(receipt.get(field) != capture.get(field) for field in capture_fields):
            raise ProtocolRunError(
                f"workload capture receipt environment binding differs from the manifest for {run['run_id']}"
            )
        semantic_payload = {
            field: capture.get(field)
            for field in (
                "function_dag_qos_sha256",
                "node_network_sha256",
                "capture_environment_sha256",
                "function_count",
                "node_count",
            )
        }
        if object_hash(semantic_payload) != capture.get("semantic_bundle_sha256"):
            raise ProtocolRunError(
                f"workload capture semantic bundle hash is invalid for {run['run_id']}"
            )

        expected_environment_hash = capture["capture_environment_sha256"]
        matching_snapshots = [
            candidate.resolve()
            for candidate in receipt_path.parent.rglob("environment.json")
            if candidate.is_file() and file_hash(candidate) == expected_environment_hash
        ]
        if len(matching_snapshots) != 1:
            raise ProtocolRunError(
                "workload package must contain exactly one immutable environment snapshot "
                f"with hash {expected_environment_hash}; found {len(matching_snapshots)} "
                f"under {receipt_path.parent}"
            )
        environment_path = matching_snapshots[0]
        try:
            environment = read_json(environment_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolRunError(
                f"workload environment snapshot cannot be parsed: {environment_path}: {exc}"
            ) from exc
        if (
            not isinstance(environment, dict)
            or environment.get("schema") != "NSE_ENVIRONMENT_V1"
        ):
            raise ProtocolRunError(
                f"workload environment snapshot schema is invalid: {environment_path}"
            )
        functions = environment.get("functions")
        nodes = environment.get("nodes")
        network = environment.get("network_mb_per_second")
        if (
            not isinstance(functions, list)
            or not isinstance(nodes, list)
            or not isinstance(network, list)
        ):
            raise ProtocolRunError(
                f"workload environment snapshot lacks functions/nodes/network: {environment_path}"
            )
        observed = {
            "function_dag_qos_sha256": object_hash(functions),
            "node_network_sha256": object_hash(
                {"nodes": nodes, "network_mb_per_second": network}
            ),
            "capture_environment_sha256": file_hash(environment_path),
            "function_count": len(functions),
            "node_count": len(nodes),
        }
        observed["semantic_bundle_sha256"] = object_hash(observed)
        if any(observed.get(field) != capture.get(field) for field in capture_fields):
            raise ProtocolRunError(
                f"workload environment snapshot content differs from its manifest binding: {environment_path}"
            )

        return {
            "schema_version": "NSE_WORKLOAD_PACKAGE_V1",
            "definition": "arrival_tape_plus_capture_receipt_plus_immutable_environment_snapshot",
            "arrival_tape": {
                "path": str(tape_path.resolve()),
                "sha256": tape["sha256"],
                "event_count": tape["event_count"],
                "kind": tape["kind"],
                "parent_sha256": tape.get("parent_sha256"),
            },
            "capture_receipt": {
                "path": str(receipt_path.resolve()),
                "sha256": tape["capture_receipt_sha256"],
                "schema_version": receipt["schema_version"],
                "capture_tape_key": capture_tape_key,
                "capture_tape_sha256": capture_tape_sha256,
            },
            "immutable_environment_snapshot": {
                "path": str(environment_path),
                **observed,
            },
        }

    def _assert_run_ready(self, run: dict[str, Any]) -> tuple[Path, Path | None]:
        """Check immutable inputs before an attempt number is consumed."""
        tape = run["workload_tape"]
        tape_hash = tape.get("sha256")
        if not isinstance(tape_hash, str) or len(tape_hash) != 64:
            raise ProtocolRunError(
                f"run {run['run_id']} has no hash-bound workload tape; use bind-tapes first"
            )
        tape_path = self._resolve_manifest_input(tape["path"])
        cache_key = (str(tape_path), tape_hash)
        if not tape_path.is_file():
            raise ProtocolRunError(f"workload tape is missing: {tape_path}")
        if file_hash(tape_path) != tape_hash:
            raise ProtocolRunError(f"workload tape hash mismatch: {tape_path}")
        info = self._verified_tapes.get(cache_key)
        if info is None:
            try:
                inspected = inspect_tape(tape_path)
            except (OSError, TapeFormatError) as exc:
                raise ProtocolRunError(
                    f"workload tape is invalid: {tape_path}: {exc}"
                ) from exc
            info = inspected.to_dict()
            if info["sha256"] != tape_hash:
                raise ProtocolRunError(f"workload tape hash mismatch: {tape_path}")
            if info["workload_seed"] != run["seed"]:
                raise ProtocolRunError(f"workload tape seed mismatch: {tape_path}")
            if info["event_count"] != tape.get("event_count"):
                raise ProtocolRunError(
                    f"workload tape event count mismatch: {tape_path}"
                )
            self._verified_tapes[cache_key] = info
        capture_receipt_hash = tape.get("capture_receipt_sha256")
        capture_receipt_path = self._resolve_manifest_input(
            str(tape.get("capture_receipt_path", ""))
        )
        if (
            not isinstance(capture_receipt_hash, str)
            or len(capture_receipt_hash) != 64
            or not capture_receipt_path.is_file()
            or file_hash(capture_receipt_path) != capture_receipt_hash
        ):
            raise ProtocolRunError(
                f"workload capture provenance receipt is missing or changed: {capture_receipt_path}"
            )
        package_key = self._workload_package_cache_key(
            tape_path,
            tape_hash,
            capture_receipt_path,
            capture_receipt_hash,
        )
        # Re-hash the capture environment for every run preflight.  A shared
        # tape package is often reused by many paired methods; a process-local
        # cache must not allow a snapshot changed after the first method to be
        # launched under the old provenance binding.
        self._verified_workload_packages[package_key] = self._validate_workload_package(
            run, tape_path, capture_receipt_path
        )

        qos = run["simulator_experiment"]["qos"]
        if qos.get("enabled") and any(
            qos.get(field) is None
            for field in (
                "latency_deadline_ms",
                "throughput_target_rps",
                "cost_budget_per_request",
            )
        ):
            raise ProtocolRunError(
                f"formal balanced-QoS run {run['run_id']} is blocked until all three SLA thresholds are frozen"
            )
        if run["workload"].get("qos_profile") == "balanced":
            if self.manifest.get("all_sla_targets_bound") is not True:
                raise ProtocolRunError(
                    f"formal balanced-QoS run {run['run_id']} is blocked until the three-pilot SLA artifact is bound"
                )
            binding = run.get("sla_targets", {})
            sla_path = self._resolve_manifest_input(
                str(binding.get("artifact_path", ""))
            )
            try:
                frozen_sla = load_frozen_sla_targets(sla_path)
            except (OSError, SlaFreezeError) as exc:
                raise ProtocolRunError(
                    f"frozen SLA artifact is missing or invalid: {exc}"
                ) from exc
            expected_binding = {
                "artifact_sha256": frozen_sla.artifact_sha256,
                "artifact_bytes": frozen_sla.artifact_bytes,
                "document_sha256": frozen_sla.document_sha256,
                "targets_sha256": frozen_sla.targets_sha256,
                "source_bundle_sha256": frozen_sla.source_bundle_sha256,
            }
            for field, expected in expected_binding.items():
                if binding.get(field) != expected:
                    raise ProtocolRunError(
                        f"frozen SLA artifact {field} differs from its manifest binding"
                    )
            if any(
                qos.get(field) != value for field, value in frozen_sla.targets.items()
            ):
                raise ProtocolRunError(
                    "formal QoS thresholds differ from the bound three-pilot SLA artifact"
                )

        if run["method"] == "sche_FaaSRank":
            if self.manifest.get("all_faasrank_models_bound") is not True:
                raise ProtocolRunError(
                    f"formal FaaSRank-P run {run['run_id']} is blocked until an immutable frozen model is bound"
                )
            binding = run.get("baseline_model", {})
            model_path = self._resolve_manifest_input(
                str(binding.get("artifact_path", ""))
            )
            try:
                model = verify_frozen_faasrank_model(
                    model_path,
                    expected_artifact_sha256=binding.get("artifact_sha256"),
                    expected_training_tape_sha256=binding.get("training_tape_sha256"),
                    test_tape_sha256=tape_hash,
                )
            except (OSError, FaaSRankModelError) as exc:
                raise ProtocolRunError(
                    f"frozen FaaSRank-P model is missing, changed, or not training/test-disjoint: {exc}"
                ) from exc
            if model.artifact_bytes != binding.get("artifact_bytes"):
                raise ProtocolRunError(
                    f"frozen FaaSRank-P model size differs from its binding: {model_path}"
                )

        reference_path: Path | None = None
        if run["method"] == "sche_nash" and run.get("variant") == "no_coordination":
            if run["simulator_experiment"]["reference"]["mode"] != "not_required":
                raise ProtocolRunError(
                    "no_coordination must use reference.mode=not_required"
                )
        dependency = run.get("reference_dependency")
        if isinstance(dependency, dict):
            reference_hash = dependency.get("sha256")
            if not isinstance(reference_hash, str) or len(reference_hash) != 64:
                raise ProtocolRunError(
                    f"formal welfare run {run['run_id']} is blocked on offline reference build {dependency['key']}"
                )
            reference_path = self._resolve_manifest_input(dependency["path"])
            if (
                not reference_path.is_file()
                or file_hash(reference_path) != reference_hash
            ):
                raise ProtocolRunError(
                    f"offline reference table is missing or changed: {reference_path}"
                )
            if reference_path.stat().st_size != dependency.get("bytes"):
                raise ProtocolRunError(
                    f"offline reference table size differs from its receipt: {reference_path}"
                )
            receipt_hash = dependency.get("receipt_sha256")
            receipt_path = self._resolve_manifest_input(
                dependency.get("receipt_path", "")
            )
            if (
                not isinstance(receipt_hash, str)
                or len(receipt_hash) != 64
                or not receipt_path.is_file()
                or file_hash(receipt_path) != receipt_hash
            ):
                raise ProtocolRunError(
                    f"offline reference build receipt is missing or changed: {receipt_path}"
                )
        return tape_path, reference_path

    def _materialize_run_config(
        self,
        run: dict[str, Any],
        attempt_dir: Path,
        tape_path: Path,
        reference_path: Path | None,
    ) -> dict[str, Any]:
        materialized = copy.deepcopy(run)
        experiment = materialized["simulator_experiment"]
        experiment["workload"]["tape_path"] = str(tape_path)
        experiment["output"]["root"] = str((attempt_dir / "reviewer_records").resolve())
        if reference_path is not None:
            experiment["reference"]["table_path"] = str(reference_path)
        materialized["materialization"] = {
            "schema_version": "NSE_RUN_MATERIALIZATION_V1",
            "semantic_run_spec_hash": run["run_spec_hash"],
            "workload_tape_sha256": run["workload_tape"]["sha256"],
            "offline_reference_sha256": (
                run.get("reference_dependency", {}).get("sha256")
            ),
            "sla_targets_sha256": run.get("sla_targets", {}).get("artifact_sha256"),
            "faasrank_model_sha256": run.get("baseline_model", {}).get(
                "artifact_sha256"
            ),
        }
        return materialized

    def _select_runs(
        self,
        run_ids: set[str] | None,
        experiment_ids: set[str] | None,
    ) -> list[dict[str, Any]]:
        runs = []
        for run in self.manifest["runs"]:
            if run_ids is not None and run["run_id"] not in run_ids:
                continue
            if (
                experiment_ids is not None
                and run["experiment_id"] not in experiment_ids
            ):
                continue
            runs.append(run)
        if run_ids is not None:
            found = {run["run_id"] for run in runs}
            missing = sorted(run_ids - found)
            if missing:
                raise ProtocolRunError(
                    f"run IDs are absent from manifest: {', '.join(missing)}"
                )
        return runs

    def _used_attempts(self, run_id: str) -> set[int]:
        used: set[int] = set()
        for root in (self.partial_root, self.quarantine_root):
            directory = root / run_id
            if directory.exists():
                for path in directory.iterdir():
                    number = _attempt_number(path)
                    if number is not None:
                        used.add(number)
        canonical = self.canonical_root / run_id / "attempt.json"
        if canonical.exists():
            try:
                used.add(int(read_json(canonical)["attempt"]))
            except (OSError, ValueError, KeyError, json.JSONDecodeError, TypeError):
                raise ProtocolRunError(
                    f"canonical attempt metadata is invalid: {canonical}"
                )
        return used

    def _failure_history(self, run_id: str) -> list[tuple[int, str]]:
        """Read stable failure identities from finalized quarantine evidence."""

        history: list[tuple[int, str]] = []
        directory = self.quarantine_root / run_id
        if not directory.exists():
            return history
        for attempt_dir in sorted(directory.iterdir()):
            attempt = _attempt_number(attempt_dir)
            report_path = attempt_dir / "qc_report.json"
            if attempt is None or not report_path.is_file():
                continue
            try:
                report = read_json(report_path)
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(report, dict):
                continue
            # Recompute from the retained evidence rather than trusting a
            # stored control field in a mutable quarantine directory.
            signature = technical_failure_signature(report)
            if isinstance(signature, str):
                history.append((attempt, signature))
        return sorted(history)

    @staticmethod
    def _repeated_failure_signature(
        history: list[tuple[int, str]],
    ) -> str | None:
        if len(history) < 2:
            return None
        previous, latest = history[-2:]
        if latest[0] == previous[0] + 1 and latest[1] == previous[1]:
            return latest[1]
        return None

    def _block_repeated_failure(
        self,
        run: dict[str, Any],
        used: set[int],
        signature: str,
    ) -> dict[str, Any]:
        reason = "repeated_technical_failure_signature"
        self.ledger.append(
            "run_blocked",
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "seed": run["seed"],
                "attempts_used": sorted(used),
                "reason": reason,
                "failure_signature": signature,
            },
        )
        return {
            "run_id": run["run_id"],
            "status": "blocked",
            "attempts_used": sorted(used),
            "reason": reason,
            "failure_signature": signature,
        }

    def _validate_audit_manifest(self, run: dict[str, Any], canonical: Path) -> None:
        path = canonical / "manifest.json"
        try:
            audit = read_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolRunError(
                f"canonical audit manifest cannot be read for {run['run_id']}: {exc}"
            ) from exc
        if (
            not isinstance(audit, dict)
            or audit.get("schema_version") != "NSE_RUN_AUDIT_MANIFEST_V1"
        ):
            raise ProtocolRunError(
                f"canonical audit manifest schema is invalid for {run['run_id']}"
            )
        if audit.get("status") != "canonical":
            raise ProtocolRunError(
                f"canonical audit disposition is invalid for {run['run_id']}"
            )
        claimed_hash = audit.get("audit_manifest_hash")
        unhashed = copy.deepcopy(audit)
        unhashed.pop("audit_manifest_hash", None)
        if not isinstance(claimed_hash, str) or object_hash(unhashed) != claimed_hash:
            raise ProtocolRunError(
                f"canonical audit manifest hash mismatch for {run['run_id']}"
            )

        protocol = audit.get("protocol_manifest")
        if not isinstance(protocol, dict):
            raise ProtocolRunError(
                f"canonical protocol provenance is missing for {run['run_id']}"
            )
        protocol_expected = {
            "path": str(self.manifest_path),
            "protocol_id": self.manifest.get("protocol_id"),
            "schema_version": self.manifest.get("schema_version"),
            "manifest_hash": self.manifest.get("manifest_hash"),
            "file_sha256": file_hash(self.manifest_path),
        }
        for key, expected in protocol_expected.items():
            if protocol.get(key) != expected:
                raise ProtocolRunError(
                    f"canonical audit protocol {key} mismatch for {run['run_id']}"
                )

        identity = audit.get("run")
        expected_identity = {
            "run_id": run.get("run_id"),
            "run_spec_hash": run.get("run_spec_hash"),
            "experiment_id": run.get("experiment_id"),
            "cell_id": run.get("cell_id"),
            "method": run.get("method"),
            "variant": run.get("variant"),
        }
        if not isinstance(identity, dict):
            raise ProtocolRunError(
                f"canonical audit run identity is missing for {run['run_id']}"
            )
        for key, expected in expected_identity.items():
            if identity.get(key) != expected:
                raise ProtocolRunError(
                    f"canonical audit run {key} mismatch for {run['run_id']}"
                )
        if identity.get("frozen_spec") != run:
            raise ProtocolRunError(
                f"canonical frozen run spec mismatch for {run['run_id']}"
            )
        try:
            attempt_metadata = read_json(canonical / "attempt.json")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolRunError(
                f"canonical attempt metadata cannot be audited: {exc}"
            ) from exc
        if identity.get("attempt") != attempt_metadata.get("attempt"):
            raise ProtocolRunError(
                f"canonical audit attempt number mismatch for {run['run_id']}"
            )

        experiment = run["simulator_experiment"]
        expected_seeds = {
            "workload_seed": experiment.get("workload_seed"),
            "topology_seed": experiment.get("topology_seed"),
            "algorithm_seed": experiment.get("algorithm_seed"),
        }
        if audit.get("seeds") != expected_seeds:
            raise ProtocolRunError(
                f"canonical three-seed provenance mismatch for {run['run_id']}"
            )

        immutable_inputs = audit.get("immutable_inputs")
        if not isinstance(immutable_inputs, dict):
            raise ProtocolRunError(
                f"canonical immutable inputs are missing for {run['run_id']}"
            )
        tape = immutable_inputs.get("workload_tape")
        if not isinstance(tape, dict) or tape.get("sha256") != run["workload_tape"].get(
            "sha256"
        ):
            raise ProtocolRunError(
                f"canonical workload tape hash mismatch for {run['run_id']}"
            )
        run_tape = run["workload_tape"]
        tape_path = self._resolve_manifest_input(run_tape["path"])
        receipt_path = self._resolve_manifest_input(run_tape["capture_receipt_path"])
        expected_workload_package = self._validate_workload_package(
            run, tape_path, receipt_path
        )
        if immutable_inputs.get("workload_package") != expected_workload_package:
            raise ProtocolRunError(
                f"canonical workload-package provenance mismatch for {run['run_id']}"
            )
        reference = run.get("reference_dependency")
        recorded_reference = immutable_inputs.get("offline_reference")
        if isinstance(reference, dict):
            if not isinstance(recorded_reference, dict) or any(
                recorded_reference.get(key) != reference.get(key)
                for key in (
                    "sha256",
                    "bytes",
                    "receipt_sha256",
                    "build_spec_hash",
                    "state_pair_sequence_sha256",
                    "assignment_sequence_sha256",
                )
            ):
                raise ProtocolRunError(
                    f"canonical offline-reference provenance mismatch for {run['run_id']}"
                )
        elif recorded_reference is not None:
            raise ProtocolRunError(
                f"canonical has an unexpected offline reference for {run['run_id']}"
            )

        for run_field, audit_field, keys in (
            (
                "sla_targets",
                "sla_targets",
                (
                    "artifact_sha256",
                    "artifact_bytes",
                    "document_sha256",
                    "targets_sha256",
                    "source_bundle_sha256",
                ),
            ),
            (
                "baseline_model",
                "faasrank_model",
                ("artifact_sha256", "artifact_bytes", "training_tape_sha256"),
            ),
        ):
            declared = run.get(run_field)
            recorded = immutable_inputs.get(audit_field)
            is_bound = isinstance(declared, dict) and declared.get("state") == "frozen"
            if is_bound:
                if not isinstance(recorded, dict) or any(
                    recorded.get(key) != declared.get(key) for key in keys
                ):
                    raise ProtocolRunError(
                        f"canonical {audit_field} binding mismatch for {run['run_id']}"
                    )
            elif recorded is not None:
                raise ProtocolRunError(
                    f"canonical has an unexpected {audit_field} binding for {run['run_id']}"
                )

        expected_configuration = {
            "common_hpa_hash": run.get("common_hpa_hash"),
            "common_hpa": run.get("common_hpa"),
            "cluster": run.get("cluster"),
            "node_count": experiment.get("node_count"),
            "node_profile": experiment.get("node_profile"),
            "qos": experiment.get("qos"),
            "ablation": experiment.get("ablation"),
            "faasrank_model": experiment.get("faasrank_model"),
        }
        if audit.get("configuration") != expected_configuration:
            raise ProtocolRunError(
                f"canonical frozen configuration mismatch for {run['run_id']}"
            )

        run_config_path = canonical / "run_config.json"
        run_config = audit.get("run_config")
        if (
            not isinstance(run_config, dict)
            or not run_config_path.is_file()
            or run_config.get("sha256") != file_hash(run_config_path)
            or run_config.get("sha256") != attempt_metadata.get("run_config_sha256")
        ):
            raise ProtocolRunError(
                f"canonical run_config hash mismatch for {run['run_id']}"
            )

        try:
            report = read_json(canonical / "qc_report.json")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolRunError(
                f"canonical QC report cannot be audited: {exc}"
            ) from exc
        qc_audit = audit.get("qc")
        expected_environment_hashes = report.get("observations", {}).get(
            "environment_semantic_hashes", {}
        )
        if (
            not isinstance(qc_audit, dict)
            or qc_audit.get("passed") != report.get("passed")
            or qc_audit.get("classification") != report.get("classification")
            or qc_audit.get("environment_semantic_hashes")
            != expected_environment_hashes
        ):
            raise ProtocolRunError(
                f"canonical QC/environment hash provenance mismatch for {run['run_id']}"
            )

        process_path = canonical / "process_observation.json"
        process, process_error = self._read_optional_json(process_path)
        process_audit = audit.get("process_observation")
        process_artifact = (
            process_audit.get("artifact") if isinstance(process_audit, dict) else None
        )
        if (
            process_error is not None
            or not isinstance(process_audit, dict)
            or not isinstance(process_artifact, dict)
            or process_audit.get("measurements")
            != self._selected_process_observation(process)
            or process_artifact.get("sha256") != file_hash(process_path)
        ):
            raise ProtocolRunError(
                f"canonical process CPU/RSS provenance mismatch for {run['run_id']}"
            )

        adapter_path = canonical / "adapter_observation.json"
        adapter_audit = audit.get("adapter_binary")
        if adapter_path.is_file():
            adapter, adapter_error = self._read_optional_json(adapter_path)
            if (
                adapter_error is not None
                or not isinstance(adapter, dict)
                or not isinstance(adapter_audit, dict)
            ):
                raise ProtocolRunError(
                    f"canonical adapter provenance is invalid for {run['run_id']}"
                )
            adapter_artifact = adapter_audit.get("observation")
            if (
                not isinstance(adapter_artifact, dict)
                or adapter_artifact.get("sha256") != file_hash(adapter_path)
                or adapter_audit.get("path") != adapter.get("server_executable")
                or adapter_audit.get("observed_sha256")
                != adapter.get("server_executable_sha256")
            ):
                raise ProtocolRunError(
                    f"canonical adapter binary hash mismatch for {run['run_id']}"
                )
        elif adapter_audit is not None:
            raise ProtocolRunError(
                f"canonical records a missing adapter observation for {run['run_id']}"
            )

        if audit.get("compressed_jsonl") != self._jsonl_archive_evidence(canonical):
            raise ProtocolRunError(
                f"canonical compressed JSONL directory mismatch for {run['run_id']}"
            )
        if audit.get("final_artifacts") != self._artifact_inventory(canonical):
            raise ProtocolRunError(
                f"canonical final-artifact inventory mismatch for {run['run_id']}"
            )

    def _validate_existing_canonical(
        self, run: dict[str, Any], canonical: Path
    ) -> None:
        self._validate_audit_manifest(run, canonical)
        metadata_path = canonical / "attempt.json"
        report_path = canonical / "qc_report.json"
        result_path = canonical / self.manifest["execution"][
            "result_relative_path"
        ].format(run_id=run["run_id"])
        try:
            metadata = read_json(metadata_path)
            report = read_json(report_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolRunError(
                f"canonical metadata cannot be read for {run['run_id']}: {exc}"
            ) from exc
        expected = {
            "run_id": run["run_id"],
            "run_spec_hash": run["run_spec_hash"],
            "seed": run["seed"],
            "workload_spec_hash": run["workload_spec_hash"],
            "common_hpa_hash": run["common_hpa_hash"],
            "workload_tape_sha256": run["workload_tape"]["sha256"],
            "offline_reference_sha256": run.get("reference_dependency", {}).get(
                "sha256"
            ),
        }
        for key, expected_value in expected.items():
            if metadata.get(key) != expected_value:
                raise ProtocolRunError(f"canonical {key} mismatch for {run['run_id']}")
        if report.get("passed") is not True:
            raise ProtocolRunError(
                f"canonical QC report is not a pass for {run['run_id']}"
            )
        if not result_path.is_file():
            raise ProtocolRunError(f"canonical result is missing for {run['run_id']}")
        if metadata.get("result_sha256") != file_hash(result_path):
            raise ProtocolRunError(
                f"canonical result hash mismatch for {run['run_id']}"
            )
        archive_summary_path = canonical / "jsonl_archive_summary.json"
        if not archive_summary_path.is_file():
            raise ProtocolRunError(
                f"canonical JSONL archive summary is missing for {run['run_id']}"
            )
        if metadata.get("jsonl_archive_summary_sha256") != file_hash(
            archive_summary_path
        ):
            raise ProtocolRunError(
                f"canonical JSONL archive summary hash mismatch for {run['run_id']}"
            )
        process_observation_path = canonical / "process_observation.json"
        if not process_observation_path.is_file():
            raise ProtocolRunError(
                f"canonical process observation is missing for {run['run_id']}"
            )
        if metadata.get("process_observation_sha256") != file_hash(
            process_observation_path
        ):
            raise ProtocolRunError(
                f"canonical process observation hash mismatch for {run['run_id']}"
            )
        try:
            archive_summary = read_json(archive_summary_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolRunError(
                f"canonical JSONL archive summary is invalid: {exc}"
            ) from exc
        for artifact in archive_summary.get("artifacts", []):
            gzip_path = canonical / artifact["gzip_relative_path"]
            if not gzip_path.is_file() or file_hash(gzip_path) != artifact.get(
                "gzip_sha256"
            ):
                raise ProtocolRunError(f"canonical gzip hash mismatch: {gzip_path}")
        if list(canonical.rglob("*.jsonl")) or list(canonical.rglob("*.jsonl.partial")):
            raise ProtocolRunError(
                f"canonical directory contains unarchived JSONL for {run['run_id']}"
            )

    def _recover_partials(self, run: dict[str, Any]) -> None:
        run_partial = self.partial_root / run["run_id"]
        if not run_partial.exists():
            return
        for attempt_dir in sorted(run_partial.iterdir()):
            attempt = _attempt_number(attempt_dir)
            if attempt is None or not attempt_dir.is_dir():
                continue
            report = QCReport(
                passed=False,
                classification="abandoned_partial",
                checked_at=utc_now(),
                result_path=None,
                result_sha256=None,
                result_bytes=None,
                issues=[
                    QCIssue(
                        "abandoned_partial", "runner found an unfinished prior attempt"
                    )
                ],
                observations={},
            )
            write_json_atomic(attempt_dir / "qc_report.json", report.to_dict())
            metadata_path = attempt_dir / "attempt.json"
            if metadata_path.exists():
                try:
                    metadata = read_json(metadata_path)
                except (OSError, json.JSONDecodeError):
                    metadata = {}
            else:
                metadata = {}
            metadata.update(
                {
                    "run_id": run["run_id"],
                    "run_spec_hash": run["run_spec_hash"],
                    "seed": run["seed"],
                    "attempt": attempt,
                    "status": "abandoned_partial",
                    "ended_at": utc_now(),
                }
            )
            write_json_atomic(metadata_path, metadata)
            self._write_audit_manifest(
                run,
                attempt,
                attempt_dir,
                status="quarantined_abandoned_partial",
                report=report,
            )
            target = self.quarantine_root / run["run_id"] / attempt_dir.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ProtocolRunError(
                    f"cannot recover partial because quarantine target exists: {target}"
                )
            os.replace(attempt_dir, target)
            self.ledger.append(
                "attempt_quarantined",
                {
                    "run_id": run["run_id"],
                    "run_spec_hash": run["run_spec_hash"],
                    "seed": run["seed"],
                    "attempt": attempt,
                    "classification": "abandoned_partial",
                    "path": str(target),
                },
            )

    def _format_command(
        self,
        template: list[str],
        run: dict[str, Any],
        attempt: int,
        attempt_dir: Path,
        run_config_path: Path,
        result_path: Path,
    ) -> list[str]:
        variables = {
            "python": sys.executable,
            "run_id": run["run_id"],
            "attempt": str(attempt),
            "partial_dir": str(attempt_dir),
            "run_config": str(run_config_path),
            "result_path": str(result_path),
            "seed": run["seed"],
            "experiment_id": run["experiment_id"],
            "method": run["method"],
        }
        try:
            return [part.format_map(variables) for part in template]
        except KeyError as exc:
            raise ProtocolRunError(f"unknown command template variable: {exc}") from exc

    def _execute_attempt(
        self,
        run: dict[str, Any],
        attempt: int,
        command_template: list[str],
        tape_path: Path,
        reference_path: Path | None,
    ) -> tuple[QCReport, Path]:
        attempt_dir = self.partial_root / run["run_id"] / f"attempt-{attempt:02d}"
        if attempt_dir.exists():
            raise ProtocolRunError(
                f"partial attempt directory already exists: {attempt_dir}"
            )
        attempt_dir.mkdir(parents=True)
        run_config_path = attempt_dir / "run_config.json"
        result_relative_path = self.manifest["execution"][
            "result_relative_path"
        ].format(run_id=run["run_id"])
        result_path = (attempt_dir / result_relative_path).resolve()
        if not result_path.is_relative_to(attempt_dir.resolve()):
            raise ProtocolRunError(
                "result_relative_path escapes the partial attempt directory"
            )
        result_path.parent.mkdir(parents=True, exist_ok=True)
        materialized_run = self._materialize_run_config(
            run, attempt_dir, tape_path, reference_path
        )
        write_json_atomic(run_config_path, materialized_run)
        command = self._format_command(
            command_template,
            run,
            attempt,
            attempt_dir,
            run_config_path,
            result_path,
        )
        stdout_path = attempt_dir / "stdout.log"
        stderr_path = attempt_dir / "stderr.log"
        started_at = utc_now()
        metadata = {
            "run_id": run["run_id"],
            "run_spec_hash": run["run_spec_hash"],
            "seed": run["seed"],
            "workload_spec_hash": run["workload_spec_hash"],
            "common_hpa_hash": run["common_hpa_hash"],
            "workload_tape_sha256": run["workload_tape"]["sha256"],
            "offline_reference_sha256": run.get("reference_dependency", {}).get(
                "sha256"
            ),
            "attempt": attempt,
            "status": "running",
            "started_at": started_at,
            "command": command,
            "run_config_sha256": file_hash(run_config_path),
        }
        write_json_atomic(attempt_dir / "attempt.json", metadata)
        self._write_audit_manifest(
            run,
            attempt,
            attempt_dir,
            status="running",
            report=None,
        )
        self.ledger.append(
            "attempt_started",
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "seed": run["seed"],
                "attempt": attempt,
                "partial_path": str(attempt_dir),
            },
        )

        environment = os.environ.copy()
        environment.update(run.get("environment", {}))
        environment.update(
            {
                "PROTOCOL_RUN_ID": run["run_id"],
                "PROTOCOL_RUN_SPEC_HASH": run["run_spec_hash"],
                "PROTOCOL_SEED": run["seed"],
                "PROTOCOL_WORKLOAD_SPEC_HASH": run["workload_spec_hash"],
                "PROTOCOL_COMMON_HPA_HASH": run["common_hpa_hash"],
                "PROTOCOL_ATTEMPT": str(attempt),
                "PROTOCOL_RUN_CONFIG": str(run_config_path),
                "PROTOCOL_PARTIAL_DIR": str(attempt_dir),
                "PROTOCOL_RESULT_PATH": str(result_path),
                "PROTOCOL_REVIEWER_RECORD_ROOT": str(attempt_dir / "reviewer_records"),
                "PROTOCOL_WORKLOAD_TAPE": str(tape_path),
            }
        )
        if reference_path is not None:
            environment["PROTOCOL_OFFLINE_REFERENCE_TABLE"] = str(reference_path)
        cwd_setting = Path(self.manifest["execution"].get("cwd", "."))
        cwd = (
            cwd_setting
            if cwd_setting.is_absolute()
            else (Path.cwd() / cwd_setting).resolve()
        )
        timeout_seconds = float(self.manifest["execution"]["timeout_seconds"])
        exit_code: int | None = None
        timed_out = False
        launch_error: str | None = None
        peak_rss_bytes = 0
        peak_vms_bytes = 0
        peak_process_count = 0
        resource_samples = 0
        cpu_max_by_pid: dict[int, float] = {}
        start = time.monotonic()
        with stdout_path.open("wb") as stdout_handle, stderr_path.open(
            "wb"
        ) as stderr_handle:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=environment,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                )
                root_process = psutil.Process(process.pid)
                while True:
                    members = [root_process]
                    try:
                        members.extend(root_process.children(recursive=True))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    rss = 0
                    vms = 0
                    live_count = 0
                    for member in members:
                        try:
                            memory = member.memory_info()
                            cpu = member.cpu_times()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                        rss += int(memory.rss)
                        vms += int(memory.vms)
                        live_count += 1
                        cpu_max_by_pid[member.pid] = max(
                            cpu_max_by_pid.get(member.pid, 0.0),
                            float(cpu.user + cpu.system),
                        )
                    peak_rss_bytes = max(peak_rss_bytes, rss)
                    peak_vms_bytes = max(peak_vms_bytes, vms)
                    peak_process_count = max(peak_process_count, live_count)
                    resource_samples += 1
                    exit_code = process.poll()
                    if exit_code is not None:
                        break
                    if time.monotonic() - start >= timeout_seconds:
                        timed_out = True
                        for member in reversed(members):
                            try:
                                member.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        exit_code = process.returncode
                        break
                    time.sleep(0.05)
            except OSError as exc:
                launch_error = str(exc)
        duration_seconds = time.monotonic() - start
        process_observation = {
            "schema_version": "NSE_PROCESS_OBSERVATION_V1",
            "duration_seconds": duration_seconds,
            "sample_interval_seconds": 0.05,
            "samples": resource_samples,
            "peak_process_tree_rss_bytes": peak_rss_bytes,
            "peak_process_tree_vms_bytes": peak_vms_bytes,
            "peak_process_tree_count": peak_process_count,
            "process_tree_cpu_seconds": sum(cpu_max_by_pid.values()),
            "timed_out": timed_out,
            "exit_code": exit_code,
        }
        write_json_atomic(attempt_dir / "process_observation.json", process_observation)
        report = evaluate_attempt(
            run,
            self.manifest["qc"],
            result_path,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            artifact_root=attempt_dir,
        )
        if launch_error is not None:
            report.issues.insert(
                0,
                QCIssue(
                    "launch_error",
                    "attempt process could not be launched",
                    {"error": launch_error},
                ),
            )
            report.passed = False
            report.classification = "launch_error"
        write_json_atomic(attempt_dir / "qc_report.json", report.to_dict())
        metadata.update(
            {
                "status": "qc_pass" if report.passed else "qc_fail",
                "ended_at": utc_now(),
                "duration_seconds": duration_seconds,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "classification": report.classification,
                "result_sha256": report.result_sha256,
                "process_observation_sha256": file_hash(
                    attempt_dir / "process_observation.json"
                ),
                "peak_process_tree_rss_bytes": peak_rss_bytes,
                "process_tree_cpu_seconds": sum(cpu_max_by_pid.values()),
            }
        )
        write_json_atomic(attempt_dir / "attempt.json", metadata)
        return report, attempt_dir

    def _gzip_one_jsonl(self, source: Path, attempt_dir: Path) -> dict[str, Any]:
        destination = source.with_suffix(source.suffix + ".gz")
        temporary = destination.with_suffix(destination.suffix + ".partial")
        if destination.exists() or temporary.exists():
            raise ProtocolRunError(
                f"refusing to overwrite JSONL archive: {destination}"
            )
        raw_digest = hashlib.sha256()
        raw_bytes = 0
        raw_newlines = 0
        last_byte = b""
        try:
            with source.open("rb") as input_handle, temporary.open("xb") as raw_output:
                with gzip.GzipFile(
                    filename="", mode="wb", fileobj=raw_output, mtime=0
                ) as gzip_output:
                    while chunk := input_handle.read(1024 * 1024):
                        raw_digest.update(chunk)
                        raw_bytes += len(chunk)
                        raw_newlines += chunk.count(b"\n")
                        last_byte = chunk[-1:]
                        gzip_output.write(chunk)
                raw_output.flush()
                os.fsync(raw_output.fileno())
            os.replace(temporary, destination)

            restored_digest = hashlib.sha256()
            restored_bytes = 0
            restored_newlines = 0
            restored_last_byte = b""
            with gzip.open(destination, "rb") as restored:
                while chunk := restored.read(1024 * 1024):
                    restored_digest.update(chunk)
                    restored_bytes += len(chunk)
                    restored_newlines += chunk.count(b"\n")
                    restored_last_byte = chunk[-1:]
            raw_lines = raw_newlines + (1 if raw_bytes and last_byte != b"\n" else 0)
            restored_lines = restored_newlines + (
                1 if restored_bytes and restored_last_byte != b"\n" else 0
            )
            if (
                restored_digest.hexdigest() != raw_digest.hexdigest()
                or restored_bytes != raw_bytes
                or restored_lines != raw_lines
            ):
                raise ProtocolRunError(f"lossless verification failed for {source}")
            archive = {
                "source_relative_path": str(source.relative_to(attempt_dir)),
                "gzip_relative_path": str(destination.relative_to(attempt_dir)),
                "raw_sha256": raw_digest.hexdigest(),
                "raw_bytes": raw_bytes,
                "raw_lines": raw_lines,
                "gzip_sha256": file_hash(destination),
                "gzip_bytes": destination.stat().st_size,
                "gzip_mtime": 0,
                "lossless_verified": True,
            }
            source.unlink()
            return archive
        finally:
            if temporary.exists():
                temporary.unlink()

    def _archive_jsonl(self, attempt_dir: Path) -> dict[str, Any]:
        partials = sorted(attempt_dir.rglob("*.jsonl.partial"))
        if partials:
            raise ProtocolRunError(
                "cannot canonicalize while JSONL partials remain: "
                + ", ".join(str(path.relative_to(attempt_dir)) for path in partials)
            )
        sources = sorted(attempt_dir.rglob("*.jsonl"))
        if (
            self.manifest["qc"].get("jsonl_artifacts", {}).get("required", False)
            and not sources
        ):
            raise ProtocolRunError(
                "cannot canonicalize without completed JSONL artifacts"
            )
        archives = [self._gzip_one_jsonl(source, attempt_dir) for source in sources]
        summary = {
            "schema_version": "jsonl_archive_summary_v1",
            "created_at": utc_now(),
            "archive_count": len(archives),
            "total_raw_bytes": sum(item["raw_bytes"] for item in archives),
            "total_raw_lines": sum(item["raw_lines"] for item in archives),
            "total_gzip_bytes": sum(item["gzip_bytes"] for item in archives),
            "artifacts": archives,
        }
        summary_path = attempt_dir / "jsonl_archive_summary.json"
        write_json_atomic(summary_path, summary)
        return {
            "summary_relative_path": str(summary_path.relative_to(attempt_dir)),
            "summary_sha256": file_hash(summary_path),
            **summary,
        }

    def _finalize_attempt(
        self,
        run: dict[str, Any],
        attempt: int,
        report: QCReport,
        attempt_dir: Path,
    ) -> Path:
        archive_summary: dict[str, Any] | None = None
        if report.passed:
            try:
                archive_summary = self._archive_jsonl(attempt_dir)
                report.observations["jsonl_archive"] = archive_summary
            except (OSError, ProtocolRunError) as exc:
                report.passed = False
                report.classification = "jsonl_archive_failure"
                report.issues.append(
                    QCIssue(
                        "jsonl_archive_failure",
                        "completed JSONL artifacts could not be losslessly archived",
                        {"error": str(exc)},
                    )
                )
        metadata_path = attempt_dir / "attempt.json"
        metadata = read_json(metadata_path) if metadata_path.exists() else {}
        metadata.update(
            {
                "status": "qc_pass" if report.passed else "qc_fail",
                "classification": report.classification,
                "failure_signature": technical_failure_signature(report),
                "result_sha256": report.result_sha256,
                "jsonl_archive_summary_sha256": (
                    archive_summary["summary_sha256"] if archive_summary else None
                ),
            }
        )
        write_json_atomic(metadata_path, metadata)
        write_json_atomic(attempt_dir / "qc_report.json", report.to_dict())
        self._write_audit_manifest(
            run,
            attempt,
            attempt_dir,
            status="canonical" if report.passed else "quarantined",
            report=report,
        )

        if report.passed:
            target = self.canonical_root / run["run_id"]
            event_type = "attempt_canonicalized"
        else:
            target = self.quarantine_root / run["run_id"] / f"attempt-{attempt:02d}"
            event_type = "attempt_quarantined"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ProtocolRunError(
                f"refusing to overwrite existing finalized attempt: {target}"
            )
        os.replace(attempt_dir, target)
        self.ledger.append(
            event_type,
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "seed": run["seed"],
                "attempt": attempt,
                "classification": report.classification,
                "qc_passed": report.passed,
                "failure_signature": technical_failure_signature(report),
                "result_sha256": report.result_sha256,
                "jsonl_archive_summary_sha256": (
                    archive_summary["summary_sha256"] if archive_summary else None
                ),
                "audit_manifest_sha256": file_hash(target / "manifest.json"),
                "path": str(target),
            },
        )
        return target

    def run_one(
        self, run: dict[str, Any], command_override: list[str] | None = None
    ) -> dict[str, Any]:
        self._assert_ready(command_override)
        try:
            tape_path, reference_path = self._assert_run_ready(run)
        except ProtocolRunError as exc:
            self.ledger.append(
                "run_preflight_blocked",
                {
                    "run_id": run["run_id"],
                    "run_spec_hash": run["run_spec_hash"],
                    "seed": run["seed"],
                    "reason": str(exc),
                    "attempts_consumed": 0,
                },
            )
            return {
                "run_id": run["run_id"],
                "status": "preflight_blocked",
                "attempts_used": [],
                "reason": str(exc),
            }
        canonical = self.canonical_root / run["run_id"]
        if canonical.exists():
            self._validate_existing_canonical(run, canonical)
            self.ledger.append(
                "run_skipped_canonical",
                {
                    "run_id": run["run_id"],
                    "run_spec_hash": run["run_spec_hash"],
                    "path": str(canonical),
                },
            )
            return {
                "run_id": run["run_id"],
                "status": "canonical_exists",
                "path": str(canonical),
            }

        self._recover_partials(run)
        maximum = int(self.manifest["execution"]["max_attempts"])
        used = {
            attempt
            for attempt in self._used_attempts(run["run_id"])
            if 1 <= attempt <= maximum
        }
        failure_history = [
            item
            for item in self._failure_history(run["run_id"])
            if 1 <= item[0] <= maximum
        ]
        repeated_signature = self._repeated_failure_signature(failure_history)
        if repeated_signature is not None:
            return self._block_repeated_failure(run, used, repeated_signature)
        template = command_override or self.manifest["execution"]["command_template"]
        while len(used) < maximum:
            attempt = min(set(range(1, maximum + 1)) - used)
            try:
                # Revalidate every immutable workload-package hash immediately
                # before each process launch. This consumes no attempt if an
                # input changed between paired runs or retries.
                tape_path, reference_path = self._assert_run_ready(run)
            except ProtocolRunError as exc:
                self.ledger.append(
                    "run_preflight_blocked",
                    {
                        "run_id": run["run_id"],
                        "run_spec_hash": run["run_spec_hash"],
                        "seed": run["seed"],
                        "reason": str(exc),
                        "attempts_consumed": len(used),
                    },
                )
                return {
                    "run_id": run["run_id"],
                    "status": "preflight_blocked",
                    "attempts_used": sorted(used),
                    "reason": str(exc),
                }
            try:
                report, partial_dir = self._execute_attempt(
                    run, attempt, template, tape_path, reference_path
                )
            except Exception as exc:
                partial_dir = (
                    self.partial_root / run["run_id"] / f"attempt-{attempt:02d}"
                )
                partial_dir.mkdir(parents=True, exist_ok=True)
                report = QCReport(
                    passed=False,
                    classification="runner_exception",
                    checked_at=utc_now(),
                    result_path=None,
                    result_sha256=None,
                    result_bytes=None,
                    issues=[
                        QCIssue(
                            "runner_exception",
                            "attempt raised a technical runner exception",
                            {"error": repr(exc)},
                        )
                    ],
                    observations={},
                )
                write_json_atomic(partial_dir / "qc_report.json", report.to_dict())
                metadata_path = partial_dir / "attempt.json"
                metadata = read_json(metadata_path) if metadata_path.exists() else {}
                metadata.update(
                    {
                        "run_id": run["run_id"],
                        "run_spec_hash": run["run_spec_hash"],
                        "seed": run["seed"],
                        "workload_spec_hash": run["workload_spec_hash"],
                        "common_hpa_hash": run["common_hpa_hash"],
                        "workload_tape_sha256": run["workload_tape"].get("sha256"),
                        "offline_reference_sha256": run.get(
                            "reference_dependency", {}
                        ).get("sha256"),
                        "attempt": attempt,
                        "status": "qc_fail",
                        "ended_at": utc_now(),
                        "classification": report.classification,
                    }
                )
                write_json_atomic(metadata_path, metadata)
            final_path = self._finalize_attempt(run, attempt, report, partial_dir)
            used.add(attempt)
            if report.passed:
                return {
                    "run_id": run["run_id"],
                    "status": "canonicalized",
                    "attempt": attempt,
                    "path": str(final_path),
                }
            signature = technical_failure_signature(report)
            if signature is not None:
                failure_history.append((attempt, signature))
                repeated_signature = self._repeated_failure_signature(failure_history)
                if repeated_signature is not None:
                    return self._block_repeated_failure(run, used, repeated_signature)

        self.ledger.append(
            "run_blocked",
            {
                "run_id": run["run_id"],
                "run_spec_hash": run["run_spec_hash"],
                "seed": run["seed"],
                "attempts_used": sorted(used),
                "reason": "maximum_result_blind_attempts_exhausted",
            },
        )
        return {
            "run_id": run["run_id"],
            "status": "blocked",
            "attempts_used": sorted(used),
        }

    def run(
        self,
        *,
        run_ids: Iterable[str] | None = None,
        experiment_ids: Iterable[str] | None = None,
        command_override: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        selected = self._select_runs(
            set(run_ids) if run_ids is not None else None,
            set(experiment_ids) if experiment_ids is not None else None,
        )
        with _WorkspaceLock(self.workspace / ".protocol.lock"):
            self.ledger.append(
                "batch_started",
                {
                    "manifest_path": str(self.manifest_path),
                    "manifest_hash": self.manifest["manifest_hash"],
                    "selected_run_count": len(selected),
                },
            )
            results = [self.run_one(run, command_override) for run in selected]
            self.ledger.append(
                "batch_finished",
                {
                    "manifest_hash": self.manifest["manifest_hash"],
                    "selected_run_count": len(selected),
                    "canonicalized": sum(
                        result["status"] in {"canonicalized", "canonical_exists"}
                        for result in results
                    ),
                    "blocked": sum(result["status"] == "blocked" for result in results),
                    "preflight_blocked": sum(
                        result["status"] == "preflight_blocked" for result in results
                    ),
                },
            )
        return results
