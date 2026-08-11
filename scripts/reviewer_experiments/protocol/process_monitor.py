from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int | None
    timed_out: bool
    launch_error: str | None
    duration_seconds: float
    samples: int
    peak_process_tree_rss_bytes: int
    peak_process_tree_vms_bytes: int
    peak_process_tree_count: int
    process_tree_cpu_seconds: float

    def to_observation(self) -> dict[str, Any]:
        return {
            "schema_version": "NSE_PROCESS_OBSERVATION_V1",
            "duration_seconds": self.duration_seconds,
            "sample_interval_seconds": 0.05,
            "samples": self.samples,
            "peak_process_tree_rss_bytes": self.peak_process_tree_rss_bytes,
            "peak_process_tree_vms_bytes": self.peak_process_tree_vms_bytes,
            "peak_process_tree_count": self.peak_process_tree_count,
            "process_tree_cpu_seconds": self.process_tree_cpu_seconds,
            "timed_out": self.timed_out,
            "exit_code": self.exit_code,
            "launch_error": self.launch_error,
        }


def available() -> bool:
    return psutil is not None


def run_monitored(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
) -> ProcessResult:
    if psutil is None:
        raise RuntimeError("psutil is required for process-tree monitoring")
    peak_rss = 0
    peak_vms = 0
    peak_count = 0
    samples = 0
    cpu_max_by_pid: dict[int, float] = {}
    exit_code: int | None = None
    timed_out = False
    launch_error: str | None = None
    start = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdout=stdout,
                stderr=stderr,
            )
            root = psutil.Process(process.pid)
            while True:
                members = [root]
                try:
                    members.extend(root.children(recursive=True))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                rss = 0
                vms = 0
                count = 0
                for member in members:
                    try:
                        memory = member.memory_info()
                        cpu = member.cpu_times()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                    rss += int(memory.rss)
                    vms += int(memory.vms)
                    count += 1
                    cpu_max_by_pid[member.pid] = max(
                        cpu_max_by_pid.get(member.pid, 0.0),
                        float(cpu.user + cpu.system),
                    )
                peak_rss = max(peak_rss, rss)
                peak_vms = max(peak_vms, vms)
                peak_count = max(peak_count, count)
                samples += 1
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
    return ProcessResult(
        exit_code=exit_code,
        timed_out=timed_out,
        launch_error=launch_error,
        duration_seconds=time.monotonic() - start,
        samples=samples,
        peak_process_tree_rss_bytes=peak_rss,
        peak_process_tree_vms_bytes=peak_vms,
        peak_process_tree_count=peak_count,
        process_tree_cpu_seconds=sum(cpu_max_by_pid.values()),
    )
