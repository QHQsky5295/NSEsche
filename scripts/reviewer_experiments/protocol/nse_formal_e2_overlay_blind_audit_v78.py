"""Result-blind integrity audit for the V78 formal E2 NSESche overlay."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.analysis.formal_inputs import (
    validate_canonical_run,
    validate_pairing_audit,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


ROOT = Path("tmp/nse_formal_e2_low_n100_overlay_20260826_v78")
MANIFEST_PATH = ROOT / "manifest.ready.json"
WORKSPACE = ROOT / "formal-runs"
PAIRING_PATH = ROOT / "pairing-audit.json"
OUTPUT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_formal_e2_low_n100_overlay_blind_audit_v78.json"
)
MARKER = "formal_e2_nsesche_profile_overlay"
EXPECTED_SEEDS = {f"E{index:02d}" for index in range(1, 21)}
EXPECTED_BASELINES = {
    "greedy",
    "random",
    "hash",
    "load_least",
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def runtime_identity(directory: Path) -> dict[str, Any]:
    adapter = read_json(directory / "adapter_observation.json")
    audit = read_json(directory / "manifest.json")
    software = audit.get("software_environment", {})
    return {
        "binary_sha256": adapter.get("server_executable_sha256"),
        "python_sha256": adapter.get("python_helper_interpreter_sha256"),
        "git_commit": software.get("git", {}).get("commit"),
        "cargo_lock_sha256": software.get("cargo_lock", {}).get("sha256"),
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"blind audit already exists: {OUTPUT}")

    errors: list[str] = []
    manifest = read_json(MANIFEST_PATH)
    validate_manifest(manifest)
    overlay = manifest.get(MARKER)
    if not isinstance(overlay, dict):
        raise RuntimeError("formal overlay marker is missing")
    require(
        overlay.get("performance_results_consulted") is False,
        "overlay was not derived result-blind",
        errors,
    )

    runs = manifest.get("runs", [])
    expected_ids = {run["run_id"] for run in runs}
    expected_by_seed = {run["seed"]: run for run in runs}
    require(len(runs) == 20, "candidate manifest does not contain 20 runs", errors)
    require(
        set(expected_by_seed) == EXPECTED_SEEDS,
        "candidate seed set is not E01--E20",
        errors,
    )
    require(
        all(run.get("method") == "sche_nash" for run in runs),
        "candidate manifest contains a non-NSESche run",
        errors,
    )

    canonical_root = WORKSPACE / "canonical"
    quarantine_root = WORKSPACE / "quarantine"
    actual_ids = {path.name for path in canonical_root.iterdir() if path.is_dir()}
    quarantine_ids = (
        {path.name for path in quarantine_root.iterdir() if path.is_dir()}
        if quarantine_root.exists()
        else set()
    )
    require(actual_ids == expected_ids, "candidate canonical set mismatch", errors)
    require(not quarantine_ids, "candidate quarantine is non-empty", errors)

    candidate_runtime_values: dict[str, set[Any]] = {
        "binary_sha256": set(),
        "python_sha256": set(),
        "git_commit": set(),
        "cargo_lock_sha256": set(),
    }
    candidate_attempt_one = 0
    candidate_qc_pass = 0
    result_relative = manifest["execution"]["result_relative_path"]
    for run in runs:
        directory = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            directory,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path=result_relative,
        )
        attempt = read_json(directory / "attempt.json")
        qc = read_json(directory / "qc_report.json")
        if (
            attempt.get("run_id") == run["run_id"]
            and attempt.get("attempt") == 1
            and attempt.get("status") == "qc_pass"
            and attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and attempt.get("exit_code") == 0
        ):
            candidate_attempt_one += 1
        if qc.get("passed") is True and qc.get("classification") == "qc_pass":
            candidate_qc_pass += 1
        identity = runtime_identity(directory)
        for key, value in identity.items():
            candidate_runtime_values[key].add(value)

    require(candidate_attempt_one == 20, "candidate attempt-one count mismatch", errors)
    require(candidate_qc_pass == 20, "candidate QC-pass count mismatch", errors)
    expected_candidate_binary = overlay["selected_profile"]["binary_sha256"]
    require(
        candidate_runtime_values["binary_sha256"] == {expected_candidate_binary},
        "candidate binary identity mismatch",
        errors,
    )
    for field, values in candidate_runtime_values.items():
        require(
            len(values) == 1 and None not in values,
            f"candidate {field} differs",
            errors,
        )

    ledger_path = WORKSPACE / "ledger.jsonl"
    ledger_events, ledger_last_hash = verify_ledger(ledger_path)
    ledger_rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_counts: dict[str, int] = {}
    for event in ledger_rows:
        name = str(event.get("event_type"))
        event_counts[name] = event_counts.get(name, 0) + 1
    require(
        event_counts.get("batch_started") == 1, "batch start count mismatch", errors
    )
    require(
        event_counts.get("attempt_started") == 20,
        "attempt start count mismatch",
        errors,
    )
    require(
        event_counts.get("attempt_canonicalized") == 20,
        "canonicalization count mismatch",
        errors,
    )
    require(
        event_counts.get("batch_finished") == 1, "batch finish count mismatch", errors
    )
    require(
        not any(
            any(token in name for token in ("failed", "quarantined", "blocked"))
            for name in event_counts
        ),
        "candidate ledger contains a failure-class event",
        errors,
    )

    pairing = validate_pairing_audit(PAIRING_PATH, manifest, canonical_root)
    require(
        pairing.get("group_count") == 20, "candidate pairing count mismatch", errors
    )

    source_cache: dict[str, tuple[dict[str, Any], dict[str, dict[str, Any]]]] = {}

    def source_run(lineage: dict[str, Any]) -> dict[str, Any]:
        path = str(Path(lineage["source_manifest_path"]).resolve())
        if path not in source_cache:
            source_path = Path(path)
            require(source_path.is_file(), f"missing source manifest {path}", errors)
            require(
                file_hash(source_path) == lineage["source_manifest_file_sha256"],
                f"source manifest file changed: {path}",
                errors,
            )
            source = read_json(source_path)
            validate_manifest(source)
            require(
                source.get("manifest_hash") == lineage["source_manifest_hash"],
                f"source manifest identity changed: {path}",
                errors,
            )
            source_cache[path] = (
                source,
                {run["run_id"]: run for run in source.get("runs", [])},
            )
        return source_cache[path][1][lineage["source_run_id"]]

    baseline_entries = overlay.get("frozen_baseline_runs", [])
    baseline_keys = {
        (entry.get("source_method"), entry.get("source_seed"))
        for entry in baseline_entries
    }
    require(len(baseline_entries) == 180, "baseline lineage count mismatch", errors)
    require(
        baseline_keys
        == {(method, seed) for method in EXPECTED_BASELINES for seed in EXPECTED_SEEDS},
        "baseline method/seed product mismatch",
        errors,
    )

    cross_version_pairs = 0
    baseline_runtime_values: dict[str, set[Any]] = {
        "binary_sha256": set(),
        "python_sha256": set(),
        "git_commit": set(),
        "cargo_lock_sha256": set(),
    }
    for entry in baseline_entries:
        run = source_run(entry)
        directory = Path(entry["source_canonical_directory"])
        source_manifest = source_cache[
            str(Path(entry["source_manifest_path"]).resolve())
        ][0]
        validate_canonical_run(
            run,
            directory,
            expected_manifest_hash=entry["source_manifest_hash"],
            result_relative_path=source_manifest["execution"]["result_relative_path"],
        )
        require(
            run["run_spec_hash"] == entry["source_run_spec_hash"],
            "baseline run spec changed",
            errors,
        )
        require(
            file_hash(directory / "manifest.json")
            == entry["source_audit_manifest_sha256"],
            "baseline audit hash changed",
            errors,
        )
        require(
            file_hash(directory / "qc_report.json") == entry["source_qc_report_sha256"],
            "baseline QC hash changed",
            errors,
        )
        summary_relative = source_manifest["execution"]["result_relative_path"].format(
            run_id=run["run_id"]
        )
        require(
            file_hash(directory / summary_relative) == entry["source_summary_sha256"],
            "baseline summary hash changed",
            errors,
        )
        identity = runtime_identity(directory)
        require(
            identity == entry["source_runtime_identity"],
            "baseline runtime identity changed",
            errors,
        )
        for key, value in identity.items():
            baseline_runtime_values[key].add(value)

        candidate = expected_by_seed[entry["source_seed"]]
        equalities = {
            "workload_spec_hash": (
                candidate["workload_spec_hash"],
                run["workload_spec_hash"],
            ),
            "workload_tape_sha256": (
                candidate["workload_tape"]["sha256"],
                run["workload_tape"]["sha256"],
            ),
            "common_hpa_hash": (candidate["common_hpa_hash"], run["common_hpa_hash"]),
            "cluster_sha256": (
                object_hash(candidate["cluster"]),
                object_hash(run["cluster"]),
            ),
            "simulation_sha256": (
                object_hash(candidate["simulation"]),
                object_hash(run["simulation"]),
            ),
            "workload_profile_sha256": (
                candidate["workload_profile"]["sha256"],
                run["workload_profile"]["sha256"],
            ),
        }
        if run["method"] == "sche_FaaSRank":
            equalities["faasrank_model_sha256"] = (
                candidate["simulator_experiment"]["faasrank_model"]["model_sha256"],
                run["simulator_experiment"]["faasrank_model"]["model_sha256"],
            )
        for field, (candidate_value, baseline_value) in equalities.items():
            require(
                candidate_value == baseline_value,
                f"cross-version pair mismatch {entry['source_seed']}/{entry['source_method']}/{field}",
                errors,
            )
        cross_version_pairs += 1

    require(
        {run["simulator_experiment"]["faasrank_model"]["model_sha256"] for run in runs}
        == {overlay["selected_profile"]["faasrank_model_sha256"]},
        "candidate frozen FaaSRank model binding mismatch",
        errors,
    )
    frozen_runtime = overlay["frozen_baseline_runtime"]
    for field in ("binary_sha256", "python_sha256", "cargo_lock_sha256"):
        require(
            baseline_runtime_values[field] == {frozen_runtime[field]},
            f"frozen baseline {field} mismatch",
            errors,
        )

    historical_entries = overlay.get("historical_nsesche_runs", [])
    require(len(historical_entries) == 20, "historical NSESche count mismatch", errors)
    require(
        {entry.get("source_seed") for entry in historical_entries} == EXPECTED_SEEDS,
        "historical NSESche seed set mismatch",
        errors,
    )
    require(
        not ({entry["source_run_id"] for entry in historical_entries} & expected_ids),
        "historical NSESche run leaked into the candidate run set",
        errors,
    )

    payload = {
        "schema_version": "NSE_FORMAL_E2_NSESCHE_OVERLAY_BLIND_AUDIT_V78",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed",
        "metrics_consulted": False,
        "scientific_result_files_parsed": 0,
        "manifest_path": str(MANIFEST_PATH),
        "manifest_hash": manifest["manifest_hash"],
        "manifest_file_sha256": file_hash(MANIFEST_PATH),
        "canonical_count": len(actual_ids),
        "quarantine_count": len(quarantine_ids),
        "attempt_one_qc_pass_count": candidate_attempt_one,
        "ledger_path": str(ledger_path),
        "ledger_file_sha256": file_hash(ledger_path),
        "ledger_events": ledger_events,
        "ledger_last_hash": ledger_last_hash,
        "ledger_event_counts": event_counts,
        "pairing_path": str(PAIRING_PATH),
        "pairing_file_sha256": file_hash(PAIRING_PATH),
        "pairing_groups": pairing.get("group_count"),
        "candidate_runtime_consensus": {
            key: next(iter(values)) for key, values in candidate_runtime_values.items()
        },
        "baseline_runtime_values": {
            key: sorted(values) for key, values in baseline_runtime_values.items()
        },
        "frozen_baseline_count": len(baseline_entries),
        "historical_nsesche_excluded_count": len(historical_entries),
        "cross_version_pair_equalities_checked": cross_version_pairs,
        "cross_version_contract": overlay["versioned_runtime_contract"],
        "errors": errors,
    }
    payload["audit_hash"] = object_hash(payload)
    write_json_atomic(OUTPUT, payload)
    print(
        {
            "status": payload["status"],
            "metrics_consulted": False,
            "candidate_runs": len(actual_ids),
            "baseline_runs": len(baseline_entries),
            "cross_version_pairs": cross_version_pairs,
            "errors": errors,
            "output": str(OUTPUT),
            "file_sha256": file_hash(OUTPUT),
            "audit_hash": payload["audit_hash"],
        }
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
