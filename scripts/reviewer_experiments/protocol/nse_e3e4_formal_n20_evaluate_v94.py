from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


INITIAL_ROOT = Path("tmp/nse_e3e4_formal_initial_v94_20260828")
EXTENSION_ROOT = Path("tmp/nse_e3e4_formal_extension_v94_20260828")
N20_ROOT = Path("tmp/nse_e3e4_formal_n20_v94_20260828")
INITIAL_MANIFEST = INITIAL_ROOT / "manifest.v94-formal.ready.v2.json"
EXTENSION_MANIFEST = EXTENSION_ROOT / "manifest.v94-formal.ready.json"
INITIAL_PAIRING = INITIAL_ROOT / "pairing-audit.v2.repaired.json"
EXTENSION_PAIRING = EXTENSION_ROOT / "pairing-audit.v94-extension.json"
INITIAL_RUNS = INITIAL_ROOT / "analysis-v2/runs.csv"
EXTENSION_RUNS = EXTENSION_ROOT / "analysis-v2/runs.csv"
COMBINED_RUNS = N20_ROOT / "analysis/runs.csv"
SUMMARY = N20_ROOT / "analysis/stats/summary.csv"
COMPARISONS = N20_ROOT / "analysis/stats/comparisons.csv"
ANALYSIS_MANIFEST = N20_ROOT / "analysis/stats/analysis_manifest.json"
OUTPUT = Path(
    "scripts/reviewer_experiments/protocol/" "nse_e3e4_formal_n20_result_v94.json"
)

EXPECTED_HASHES = {
    INITIAL_MANIFEST: "81f6efc32a31567aec79bce38bccb9fa6bd7c16d72d388a3cc2ef6671afc8a54",
    EXTENSION_MANIFEST: "65ff435b24ab2a9248fc3166dac998be17822679044f8deef6e894af8a59bc34",
    INITIAL_PAIRING: "1f259b4703f7e1e7fdd60906300f319edab845cfccfc737aa0e82877e620cfa8",
    EXTENSION_PAIRING: "0e93d79fdbade972d518532188c682be9cffcfc16a676a845c9eb5b70e4b4141",
    INITIAL_RUNS: "d1bc67b8198e3a826840679629bd60a07dc5dcae766079afe24de257118a2f15",
    EXTENSION_RUNS: "258ba88828856c9e936ea77c8e68056c567ea7158228705f37c2b8182ed66f1d",
    COMBINED_RUNS: "65c4ec04155a33ae81bd2b998719184a490d1a3b5c9172e20f238945b9bf10ad",
    SUMMARY: "08e137f07fe87fc2dff34738595afc3eb863e2253009c693c387a992dc489058",
    COMPARISONS: "237ccaf4fcd7cb7250f707ec5f2a6c3b5839b40d380b43b60d393ac4fe605824",
    ANALYSIS_MANIFEST: "328ecc9336ac0d67cc6a6c4c92d8ab83c078a73a0b3e2ce0e7bfc504f3c0cb36",
}
EXPECTED_MANIFEST_HASHES = {
    "initial": "3aa8762ae6a289d143b3c35cc4c328b06bfab333c8aab0ad2884c6b12d4d1801",
    "extension": "5feb3e397d055dbcd9c40dc41d50f1151e4285d31842089ce948ac899bd286ec",
}
EXPECTED_SCENARIOS = (
    "E3.spike5x50ms",
    "E3.sustained3x200ms",
    "E3.pulse4x4x50ms",
    "E4.steady",
)
EXPECTED_METHODS = (
    "Greedy",
    "Random",
    "Hash",
    "Load Balance",
    "FaaSRank",
    "OCS",
    "Hiku",
    "Jiagu",
    "Orion",
    "NSESche",
)
EXPECTED_SEEDS = tuple(f"E{value:02d}" for value in range(1, 21))
METRICS = (
    "throughput_requests_per_ms",
    "qpr_finite_only",
    "qpr_zero_completed_as_zero",
)


def _finite(value: object) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _number(row: Mapping[str, str], field: str) -> float | None:
    value = row.get(field)
    return float(value) if _finite(value) else None


def _scenario(row: Mapping[str, str]) -> str:
    if row.get("experiment_id") == "E3":
        return f"E3.{row.get('burst_pattern')}"
    if row.get("experiment_id") == "E4":
        return "E4.steady"
    raise ValueError(f"unexpected experiment_id: {row.get('experiment_id')}")


def _run_metrics(row: Mapping[str, str]) -> dict[str, float | None]:
    throughput = _number(row, "throughput")
    completed = _number(row, "completed")
    cost = _number(row, "cost")
    latency = _number(row, "latency")
    if throughput is None or throughput < 0.0:
        raise ValueError(f"invalid throughput: {row.get('run_id')}")
    if completed is None or completed < 0.0 or not completed.is_integer():
        raise ValueError(f"invalid completed count: {row.get('run_id')}")
    qpr = None
    if completed > 0.0:
        if cost is None or cost <= 0.0 or latency is None or latency <= 0.0:
            raise ValueError(
                f"positive-completion run lacks a finite QPR denominator: {row.get('run_id')}"
            )
        qpr = throughput / (cost * latency)
        if not math.isfinite(qpr):
            raise ValueError(f"non-finite recomputed QPR: {row.get('run_id')}")
    return {
        "throughput_requests_per_ms": throughput,
        "qpr_finite_only": qpr,
        "qpr_zero_completed_as_zero": 0.0 if completed == 0.0 else qpr,
    }


def _aggregate(rows: Sequence[Mapping[str, str]], metric: str) -> dict[str, object]:
    values = [_run_metrics(row)[metric] for row in rows]
    finite_values = [float(value) for value in values if _finite(value)]
    return {
        "n_total": len(rows),
        "n_finite": len(finite_values),
        "n_zero_completed": sum(float(row["completed"]) == 0.0 for row in rows),
        "mean": statistics.fmean(finite_values) if finite_values else None,
        "sample_std": (
            statistics.stdev(finite_values) if len(finite_values) >= 2 else None
        ),
        "values_by_seed": {str(row["seed"]): value for row, value in zip(rows, values)},
    }


def _rank(method: str, means: Mapping[str, float]) -> int:
    return 1 + sum(value > means[method] for value in means.values())


def evaluate_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    expected_scenarios: Sequence[str] = EXPECTED_SCENARIOS,
    expected_methods: Sequence[str] = EXPECTED_METHODS,
    expected_seeds: Sequence[str] = EXPECTED_SEEDS,
) -> dict[str, object]:
    grouped: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    run_ids: set[str] = set()
    for row in rows:
        run_id = str(row.get("run_id"))
        if run_id in run_ids:
            raise ValueError(f"duplicate run_id: {run_id}")
        run_ids.add(run_id)
        grouped[(_scenario(row), str(row.get("algorithm")))].append(row)

    expected_keys = {
        (scenario, method)
        for scenario in expected_scenarios
        for method in expected_methods
    }
    if set(grouped) != expected_keys:
        raise ValueError(
            f"scenario/method product mismatch: missing={sorted(expected_keys-set(grouped))}, "
            f"extra={sorted(set(grouped)-expected_keys)}"
        )

    scenario_results: dict[str, object] = {}
    for scenario in expected_scenarios:
        methods: dict[str, dict[str, object]] = {}
        for method in expected_methods:
            selected = sorted(grouped[(scenario, method)], key=lambda row: row["seed"])
            if [row["seed"] for row in selected] != sorted(expected_seeds):
                raise ValueError(f"seed set mismatch: {scenario}/{method}")
            methods[method] = {
                metric: _aggregate(selected, metric) for metric in METRICS
            }

        gates: dict[str, object] = {}
        for metric in METRICS:
            means = {
                method: float(methods[method][metric]["mean"])
                for method in expected_methods
                if _finite(methods[method][metric]["mean"])
            }
            if set(means) != set(expected_methods):
                raise ValueError(f"missing aggregate mean: {scenario}/{metric}")
            baseline_mean = max(
                value for method, value in means.items() if method != "NSESche"
            )
            baseline_methods = sorted(
                method
                for method, value in means.items()
                if method != "NSESche" and value == baseline_mean
            )
            candidate_mean = means["NSESche"]
            gates[metric] = {
                "candidate_mean": candidate_mean,
                "candidate_rank": _rank("NSESche", means),
                "maximum_baseline_mean": baseline_mean,
                "maximum_baseline_methods": baseline_methods,
                "candidate_minus_maximum_baseline": candidate_mean - baseline_mean,
                "relative_margin": (
                    (candidate_mean - baseline_mean) / baseline_mean
                    if baseline_mean > 0.0
                    else None
                ),
                "strictly_greater": candidate_mean > baseline_mean,
            }
        scenario_results[scenario] = {
            "methods": methods,
            "gates": gates,
            "all_three_operational_gates_pass": all(
                gates[metric]["strictly_greater"] for metric in METRICS
            ),
        }

    return {
        "scenario_results": scenario_results,
        "passing_scenarios": [
            scenario
            for scenario in expected_scenarios
            if scenario_results[scenario]["all_three_operational_gates_pass"]
        ],
        "all_four_scenarios_pass": all(
            scenario_results[scenario]["all_three_operational_gates_pass"]
            for scenario in expected_scenarios
        ),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _validate_pairing(path: Path, expected_manifest_hash: str) -> dict:
    report = read_json(path)
    if (
        report.get("passed") is not True
        or report.get("failed_group_count") != 0
        or report.get("run_count") != 400
        or report.get("group_count") != 40
        or report.get("protocol_manifest_sha256") != expected_manifest_hash
    ):
        raise RuntimeError(f"pairing audit is not an admitted 400-run block: {path}")
    return report


def _runtime_identity(report: Mapping[str, object]) -> dict[str, object]:
    fields = (
        "runtime_binary_sha256",
        "runtime_cargo_lock_sha256",
        "runtime_python_executable_sha256",
        "common_hpa_sha256",
        "runtime_git_commit",
    )
    values = {
        field: sorted(
            {
                str(group["consensus"][field])
                for group in report["groups"]
                if isinstance(group, Mapping)
            }
        )
        for field in fields
    }
    if any(len(value) != 1 for value in values.values()):
        raise RuntimeError("pairing audit lacks one runtime identity per block")
    return {field: value[0] for field, value in values.items()}


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"formal n=20 result already exists: {OUTPUT}")
    for path, expected_hash in EXPECTED_HASHES.items():
        if not path.is_file() or file_hash(path) != expected_hash:
            raise RuntimeError(f"frozen n=20 input changed: {path}")

    initial_manifest = read_json(INITIAL_MANIFEST)
    extension_manifest = read_json(EXTENSION_MANIFEST)
    if (
        initial_manifest.get("manifest_hash") != EXPECTED_MANIFEST_HASHES["initial"]
        or extension_manifest.get("manifest_hash")
        != EXPECTED_MANIFEST_HASHES["extension"]
    ):
        raise RuntimeError("formal manifest content hash changed")
    initial_pairing = _validate_pairing(
        INITIAL_PAIRING, EXPECTED_MANIFEST_HASHES["initial"]
    )
    extension_pairing = _validate_pairing(
        EXTENSION_PAIRING, EXPECTED_MANIFEST_HASHES["extension"]
    )
    initial_identity = _runtime_identity(initial_pairing)
    extension_identity = _runtime_identity(extension_pairing)
    for field in (
        "runtime_binary_sha256",
        "runtime_cargo_lock_sha256",
        "runtime_python_executable_sha256",
        "common_hpa_sha256",
    ):
        if initial_identity[field] != extension_identity[field]:
            raise RuntimeError(f"cross-block runtime identity mismatch: {field}")

    initial_rows = _read_csv(INITIAL_RUNS)
    extension_rows = _read_csv(EXTENSION_RUNS)
    combined_rows = _read_csv(COMBINED_RUNS)
    if (
        len(initial_rows) != 400
        or len(extension_rows) != 400
        or len(combined_rows) != 800
    ):
        raise RuntimeError("formal block row count mismatch")
    source_by_id = {row["run_id"]: row for row in [*initial_rows, *extension_rows]}
    combined_by_id = {row["run_id"]: row for row in combined_rows}
    if len(source_by_id) != 800 or combined_by_id != source_by_id:
        raise RuntimeError("combined n=20 CSV is not the exact union of both blocks")
    if {row["seed"] for row in initial_rows} & {row["seed"] for row in extension_rows}:
        raise RuntimeError("initial and extension seed sets overlap")

    evaluation = evaluate_rows(combined_rows)
    result = {
        "schema_version": "NSE_E3E4_FORMAL_N20_RESULT_V94_V1",
        "created_at": utc_now(),
        "status": (
            "formal_n20_operational_gate_pass"
            if evaluation["all_four_scenarios_pass"]
            else "formal_n20_operational_gate_fail"
        ),
        "formal_results_eligible": True,
        "selection_or_selective_rerun_used": False,
        "initial_seeds": [f"E{value:02d}" for value in range(1, 11)],
        "extension_seeds": [f"E{value:02d}" for value in range(11, 21)],
        "all_methods_extended_together": True,
        "run_count": len(combined_rows),
        "input_artifacts": [
            {"path": str(path), "file_sha256": expected_hash}
            for path, expected_hash in EXPECTED_HASHES.items()
        ],
        "manifest_hashes": EXPECTED_MANIFEST_HASHES,
        "runtime_identity": {
            "initial": initial_identity,
            "extension": extension_identity,
            "cross_block_equal_fields": [
                "runtime_binary_sha256",
                "runtime_cargo_lock_sha256",
                "runtime_python_executable_sha256",
                "common_hpa_sha256",
            ],
            "git_commit_difference_is_control_plane_only": True,
            "git_diff_name_status": [
                "A scripts/reviewer_experiments/protocol/nse_e3e4_formal_extension_v94_plan.json",
                "A scripts/reviewer_experiments/protocol/nse_e3e4_formal_extension_v94_prepare.py",
                "M scripts/reviewer_experiments/protocol/schema.py",
                "A scripts/reviewer_experiments/protocol/tests/test_nse_e3e4_formal_extension_v94_prepare.py",
            ],
        },
        "metric_definitions": {
            "throughput_requests_per_ms": (
                "per-run fixed-observation-window completed requests divided by 1000 ms"
            ),
            "qpr_finite_only": (
                "mean over runs with completed>0 and finite positive cost and latency; "
                "QPR_i=throughput_i/(cost_i*latency_i)"
            ),
            "qpr_zero_completed_as_zero": (
                "same per-run QPR, but an exactly zero-completion run contributes 0; "
                "positive-completion runs with an invalid denominator fail closed"
            ),
            "gate": (
                "NSESche finite complete mean must be strictly greater than every "
                "baseline mean in each scenario; ties fail"
            ),
        },
        **evaluation,
        "decision": {
            "freeze_E01_E20_without_deletion_or_replacement": True,
            "baseline_rerun": False,
            "selective_seed_rerun": False,
            "proceed_to_E5_E6_E7": evaluation["all_four_scenarios_pass"],
            "next_action": (
                "proceed to frozen E5/E6/E7 matrix"
                if evaluation["all_four_scenarios_pass"]
                else (
                    "freeze this complete failed n=20 cohort and preregister a new "
                    "bounded NSESche-only development cohort on untouched seeds; keep "
                    "all E01-E20 baselines frozen"
                )
            ),
        },
    }
    result["result_hash"] = object_hash(result)
    write_json_atomic(OUTPUT, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(OUTPUT),
                "file_sha256": file_hash(OUTPUT),
                "result_hash": result["result_hash"],
                "passing_scenarios": result["passing_scenarios"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
