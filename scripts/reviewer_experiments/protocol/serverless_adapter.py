from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .util import file_hash, read_json, replace_atomic, utc_now, write_json_atomic
from .workload_profile import load_frozen_workload_profile


class AdapterError(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_executable() -> Path:
    name = "serverless_sim.exe" if os.name == "nt" else "serverless_sim"
    return _repo_root() / "serverless_sim" / "target" / "release" / name


def _snapshot_module_inventory(server_directory: Path) -> tuple[Path, bytes, str]:
    """Preserve the tracked module inventory before the Rust server rewrites it."""

    module_path = server_directory / "module_conf_es.json"
    try:
        original = module_path.read_bytes()
    except OSError as exc:
        raise AdapterError(
            f"cannot preserve Rust module inventory {module_path}: {exc}"
        ) from exc
    return module_path, original, hashlib.sha256(original).hexdigest()


def _restore_module_inventory(module_path: Path, original: bytes) -> None:
    """Atomically restore the exact pre-run inventory bytes."""

    temporary = module_path.with_name(f".{module_path.name}.{os.getpid()}.restore.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        replace_atomic(temporary, module_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _server_environment() -> tuple[dict[str, str], Path]:
    """Pin Rust's Python helpers to the interpreter running this adapter."""

    interpreter = Path(sys.executable).resolve()
    if not interpreter.is_file():
        raise AdapterError(
            f"adapter Python interpreter is not a regular file: {interpreter}"
        )
    environment = os.environ.copy()
    environment["SERVERLESS_SIM_PYTHON"] = str(interpreter)
    # Formal runs persist authoritative structured JSONL observations.  Keep
    # stderr for actionable warnings/errors without duplicating every window's
    # structured event and every normal simulator frame at INFO level.
    environment["SERVERLESS_SIM_LOG_LEVEL"] = "warn"
    return environment, interpreter


def _port_is_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_server(
    process: subprocess.Popen[Any], host: str, port: int, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise AdapterError(f"serverless_sim exited during startup with code {code}")
        if _port_is_open(host, port):
            return
        time.sleep(0.05)
    raise AdapterError(
        f"serverless_sim did not listen on {host}:{port} within {timeout:g}s"
    )


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, allow_nan=False, separators=(",", ":")).encode(
            "utf-8"
        ),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if response.status != 200:
                raise AdapterError(f"HTTP {response.status} from {url}")
    except (OSError, urllib.error.URLError) as exc:
        raise AdapterError(f"request to {url} failed: {exc}") from exc
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"response from {url} is not JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError(f"response from {url} is not a JSON object")
    return value


def _select_module(
    module: dict[str, Any], category: str, selected: str, argument: str = ""
) -> None:
    choices = module.get(category)
    if not isinstance(choices, dict) or selected not in choices:
        raise AdapterError(f"Rust module configuration has no {category}.{selected}")
    for key in choices:
        choices[key] = argument if key == selected else None


def _scheduler_name(method: str) -> str:
    return method


def _build_mechanism(run: dict[str, Any], server_directory: Path) -> dict[str, Any]:
    module_path = server_directory / "module_conf_es.json"
    deadline = time.monotonic() + 5.0
    while not module_path.is_file() and time.monotonic() < deadline:
        time.sleep(0.05)
    try:
        module = read_json(module_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterError(
            f"cannot read Rust module inventory {module_path}: {exc}"
        ) from exc
    if not isinstance(module, dict):
        raise AdapterError("Rust module inventory root is not an object")
    hpa = run["common_hpa"]
    _select_module(module, "mech_type", hpa["mech_type"])
    _select_module(module, "scale_num", hpa["scale_num"])
    _select_module(module, "scale_down_exec", hpa["scale_down_exec"])
    _select_module(module, "scale_up_exec", hpa["scale_up_exec"])
    _select_module(module, "sche", _scheduler_name(run["method"]))
    _select_module(module, "instance_cache_policy", hpa["instance_cache_policy"])
    filters = module.get("filter")
    if not isinstance(filters, dict):
        raise AdapterError("Rust module inventory has no filter map")
    selected_filters = set(hpa.get("filters", []))
    missing_filters = selected_filters - filters.keys()
    if missing_filters:
        raise AdapterError(
            f"Rust module inventory lacks filters: {sorted(missing_filters)}"
        )
    for key in filters:
        filters[key] = "" if key in selected_filters else None
    return module


def _full_config(run: dict[str, Any], mechanism: dict[str, Any]) -> dict[str, Any]:
    simulation = run["simulation"]
    return {
        "rand_seed": run["seed"],
        "total_frame": int(simulation["total_frame"]),
        "request_freq": run["workload"]["request_freq"],
        "dag_type": simulation["dag_type"],
        "cold_start": simulation["cold_start"],
        "fn_type": simulation["fn_type"],
        "no_mech_latency": bool(run["common_hpa"]["no_mech_latency"]),
        "mech": mechanism,
        "no_log": True,
        "experiment": run["simulator_experiment"],
    }


def _verify_workload_frequency_profile(run: dict[str, Any]) -> dict[str, Any]:
    experiment = run.get("simulator_experiment")
    binding = run.get("workload_profile")
    if not isinstance(experiment, dict) or experiment.get("protocol_version") not in {
        "reviewer-v3",
        "reviewer-v4",
    }:
        raise AdapterError(
            "formal adapter requires simulator protocol_version=reviewer-v3 or reviewer-v4"
        )
    if not isinstance(binding, dict):
        raise AdapterError("formal run has no workload profile binding")
    experiment_binding = experiment.get("workload", {}).get("frequency_profile")
    if experiment_binding != binding:
        raise AdapterError("simulator workload profile differs from run binding")
    if run.get("workload", {}).get("request_freq") != binding.get("load"):
        raise AdapterError("workload profile load differs from the run load")
    try:
        loaded = load_frozen_workload_profile(
            Path(binding["path"]),
            expected_sha256=binding["sha256"],
            expected_load=binding["load"],
            expected_profile_id=binding["profile_id"],
            expected_profile_set_id=binding["profile_set_id"],
            expected_frequency_sha256=binding["dag_call_frequency_sha256"],
        )
    except (KeyError, OSError, ValueError) as exc:
        raise AdapterError(f"workload profile verification failed: {exc}") from exc
    if loaded.to_binding() != binding:
        raise AdapterError("workload profile artifact differs from the frozen binding")
    return binding


def _kernel(response: dict[str, Any], operation: str) -> dict[str, Any]:
    if response.get("id") != 1:
        raise AdapterError(f"{operation} was rejected: {response.get('kernel')!r}")
    kernel = response.get("kernel")
    if not isinstance(kernel, dict):
        raise AdapterError(f"{operation} response has no kernel object")
    return kernel


def _stop_server(
    process: subprocess.Popen[Any], grace_seconds: float = 5.0
) -> dict[str, Any]:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return {
                "method": "kill_after_terminate_timeout",
                "exit_code": process.returncode,
            }
        return {"method": "terminate", "exit_code": process.returncode}
    return {"method": "already_exited", "exit_code": process.returncode}


def _wait_for_completed_artifacts(
    run: dict[str, Any],
    result_path: Path,
    process: subprocess.Popen[Any],
    timeout: float,
) -> None:
    required = [
        result_path,
        result_path.parent / "frames.jsonl",
        result_path.parent / "requests.jsonl",
        result_path.parent / "scheduler_windows.jsonl",
    ]
    if run.get("method") == "sche_nash":
        observation_path = result_path.parent / "nash_metrics.jsonl"
        required.append(observation_path)
    else:
        observation_path = result_path.parent / "welfare_metrics.jsonl"
        required.append(observation_path)
    reference = run.get("simulator_experiment", {}).get("reference", {})
    if reference.get("mode") == "build":
        required.append(Path(reference["build_output_path"]))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AdapterError(
                f"serverless_sim exited before publishing artifacts (code {process.returncode})"
            )
        partials = [path.with_name(path.name + ".partial") for path in required]
        if (
            all(path.is_file() for path in required)
            and not any(path.exists() for path in partials)
            and _observation_stream_complete(observation_path, run)
        ):
            return
        time.sleep(0.05)
    missing = [str(path) for path in required if not path.is_file()]
    partial = [
        str(path.with_name(path.name + ".partial"))
        for path in required
        if path.with_name(path.name + ".partial").exists()
    ]
    raise AdapterError(
        f"completed artifacts were not atomically published within {timeout:g}s; "
        f"missing={missing}, partial={partial}"
    )


def _observation_stream_complete(path: Path, run: dict[str, Any]) -> bool:
    """Require the scheduler's terminal summary before stopping its process.

    The simulator writes window events while the mechanism thread is still
    draining.  Checking only for the JSONL path lets QC read a valid prefix.
    The terminal summary is emitted after that writer has consumed every
    scheduling window and is therefore the synchronization marker.
    """

    expected_kind = (
        "run_summary" if run.get("method") == "sche_nash" else "welfare_run_summary"
    )
    window_kind = "window" if run.get("method") == "sche_nash" else "welfare_window"
    last: dict[str, Any] | None = None
    window_count = 0
    summary_count = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    continue
                event = json.loads(raw_line)
                if not isinstance(event, dict):
                    return False
                if event.get("kind") == window_kind:
                    window_count += 1
                elif event.get("kind") == expected_kind:
                    summary_count += 1
                last = event
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if (
        last is None
        or last.get("kind") != expected_kind
        or summary_count != 1
        or last.get("observation_writer_error") is not None
    ):
        return False
    if run.get("method") == "sche_nash":
        if (
            last.get("v") != 2
            or last.get("schema") is not None
            or last.get("scheduler") != "sche_nash"
        ):
            return False
    else:
        if (
            last.get("v") != 1
            or last.get("schema") != "NSE_POSTHOC_WELFARE_RUN_V1"
            or last.get("scheduler") != run.get("method")
        ):
            return False
    if last.get("windows") != window_count:
        return False
    windows = last.get("windows")
    if not isinstance(windows, int) or isinstance(windows, bool) or windows < 0:
        return False
    expected_windows = run.get("simulation", {}).get("expected_final_frame")
    if (
        isinstance(expected_windows, int)
        and not isinstance(expected_windows, bool)
        and windows != expected_windows
    ):
        return False
    return True


def run_adapter(
    run_config_path: Path,
    executable: Path,
    *,
    host: str,
    port: int,
    startup_timeout: float,
    request_timeout: float,
    artifact_timeout: float,
) -> dict[str, Any]:
    run = read_json(run_config_path)
    if not isinstance(run, dict):
        raise AdapterError("materialized run config root must be an object")
    workload_profile = _verify_workload_frequency_profile(run)
    if not executable.is_file():
        raise AdapterError(
            f"release executable is missing: {executable}; run `cargo build --release` before formal runs"
        )
    if _port_is_open(host, port):
        raise AdapterError(
            f"{host}:{port} is already occupied; refusing to use an unmeasured external simulator"
        )
    server_directory = executable.resolve().parents[2]
    (
        module_path,
        original_module_inventory,
        original_module_sha256,
    ) = _snapshot_module_inventory(server_directory)
    server_environment, helper_interpreter = _server_environment()
    helper_interpreter_sha256 = file_hash(helper_interpreter)
    started_at = utc_now()
    process = subprocess.Popen(
        [str(executable.resolve())],
        cwd=server_directory,
        stdin=subprocess.DEVNULL,
        stdout=None,
        stderr=None,
        env=server_environment,
    )
    shutdown: dict[str, Any] | None = None
    status = "failed"
    reset_response: dict[str, Any] | None = None
    step_response: dict[str, Any] | None = None
    module_restore_error: str | None = None
    restored_module_sha256: str | None = None
    try:
        _wait_for_server(process, host, port, startup_timeout)
        mechanism = _build_mechanism(run, server_directory)
        config = _full_config(run, mechanism)
        reset_response = _post_json(
            f"http://{host}:{port}/reset", {"config": config}, request_timeout
        )
        reset_kernel = _kernel(reset_response, "reset")
        env_id = reset_kernel.get("env_id")
        if not isinstance(env_id, str) or not env_id:
            raise AdapterError("reset response has no non-empty env_id")
        step_response = _post_json(
            f"http://{host}:{port}/step",
            {"env_id": env_id, "action": 1},
            request_timeout,
        )
        step_kernel = _kernel(step_response, "step")
        if step_kernel.get("stop") is not True:
            raise AdapterError("step completed without stop=true")
        result_path = Path(os.environ.get("PROTOCOL_RESULT_PATH", ""))
        _wait_for_completed_artifacts(run, result_path, process, artifact_timeout)
        summary = read_json(result_path)
        if not isinstance(summary, dict) or summary.get("schema") != "NSE_SUMMARY_V1":
            raise AdapterError("simulator summary schema is not NSE_SUMMARY_V1")
        if (
            summary.get("run_id") != run.get("run_id")
            or summary.get("run_complete") is not True
        ):
            raise AdapterError(
                "simulator summary provenance/completion marker is invalid"
            )
        status = "completed"
        return {
            "schema_version": "NSE_SERVERLESS_ADAPTER_V1",
            "status": status,
            "run_id": run["run_id"],
            "server_pid": process.pid,
            "server_executable": str(executable.resolve()),
            "server_executable_sha256": file_hash(executable),
            "python_helper_interpreter": str(helper_interpreter),
            "python_helper_interpreter_sha256": helper_interpreter_sha256,
            "python_helper_version": sys.version,
            "server_log_level": server_environment["SERVERLESS_SIM_LOG_LEVEL"],
            "workload_profile_id": workload_profile["profile_id"],
            "workload_profile_sha256": workload_profile["sha256"],
            "started_at": started_at,
            "ended_at": utc_now(),
            "reset_response_id": reset_response.get("id"),
            "step_response_id": step_response.get("id"),
            "summary_sha256": file_hash(result_path),
        }
    finally:
        shutdown = _stop_server(process)
        try:
            _restore_module_inventory(module_path, original_module_inventory)
            restored_module_sha256 = file_hash(module_path)
            if restored_module_sha256 != original_module_sha256:
                raise AdapterError(
                    "restored Rust module inventory does not match its pre-run hash"
                )
        except (OSError, AdapterError) as exc:
            status = "failed"
            module_restore_error = f"{type(exc).__name__}: {exc}"
        observation_path = (
            Path(os.environ.get("PROTOCOL_PARTIAL_DIR", run_config_path.parent))
            / "adapter_observation.json"
        )
        observation = {
            "schema_version": "NSE_SERVERLESS_ADAPTER_LIFECYCLE_V1",
            "status": status,
            "run_id": run.get("run_id"),
            "server_pid": process.pid,
            "server_executable": str(executable.resolve()),
            "server_executable_sha256": file_hash(executable),
            "python_helper_interpreter": str(helper_interpreter),
            "python_helper_interpreter_sha256": helper_interpreter_sha256,
            "python_helper_version": sys.version,
            "server_log_level": server_environment["SERVERLESS_SIM_LOG_LEVEL"],
            "workload_profile_id": workload_profile["profile_id"],
            "workload_profile_sha256": workload_profile["sha256"],
            "started_at": started_at,
            "ended_at": utc_now(),
            "shutdown": shutdown,
            "module_inventory_preservation": {
                "path": str(module_path.resolve()),
                "pre_run_sha256": original_module_sha256,
                "post_restore_sha256": restored_module_sha256,
                "restored_exactly": (
                    restored_module_sha256 == original_module_sha256
                    and module_restore_error is None
                ),
                "error": module_restore_error,
            },
            "reset_response_id": reset_response.get("id") if reset_response else None,
            "step_response_id": step_response.get("id") if step_response else None,
        }
        write_json_atomic(observation_path, observation)
        if module_restore_error is not None:
            raise AdapterError(
                f"failed to restore Rust module inventory: {module_restore_error}"
            )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch and drive one measured serverless_sim process"
    )
    parser.add_argument("--run-config", type=Path, required=True)
    parser.add_argument("--simulator-exe", type=Path, default=_default_executable())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    parser.add_argument("--request-timeout", type=float, default=1790.0)
    parser.add_argument("--artifact-timeout", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_adapter(
            args.run_config,
            args.simulator_exe,
            host=args.host,
            port=args.port,
            startup_timeout=args.startup_timeout,
            request_timeout=args.request_timeout,
            artifact_timeout=args.artifact_timeout,
        )
    except (OSError, ValueError, AdapterError, json.JSONDecodeError) as exc:
        print(f"serverless adapter error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
