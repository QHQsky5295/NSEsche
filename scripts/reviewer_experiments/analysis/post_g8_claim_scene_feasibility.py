"""Audit retained post-G8 evidence for candidate and manuscript feasibility."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Mapping, Sequence

from scipy import stats as scipy_stats

from ..protocol.schema import ProtocolValidationError
from ..protocol.util import file_hash, object_hash, read_json, utc_now


SCHEMA_VERSION = "NSE_POST_G8_CLAIM_SCENE_FEASIBILITY_V1"
OUTPUT_NAMES = (
    "post_g8_claim_scene_feasibility.json",
    "post_g8_candidate_cells.csv",
    "post_g8_hom_low_baseline_pairs.csv",
    "post_g8_formal_hom_low.csv",
)
JSON_INPUTS: dict[str, dict[str, Any]] = {
    "formal_q61_q80": {
        "path": "runs/tscv1_g1_formal_q61_q80_98f822c_20260903/online/homogeneous-low/homogeneous-low.cell-report.json",
        "file_sha256": "98558269dc6303f9245479f1a4aaa02d40ad0f727c3db491780558a0802f8073",
        "document_sha256": "10dada54be25f19efa647d5c46bf5f7bf6528f12a6f55f33e02349d2ffa7f709",
        "status": "complete_formal_cell_failed_gate",
        "run_count": 200,
    },
    "g2": {
        "path": "runs/tscv1_g2_init_d66_d70_3ae7792_20260903/g2.initialization.analysis.json",
        "file_sha256": "414f42b286358277c6dd30dd3943074067cefa590f3a0ff45ed74b6c809f18db",
        "document_sha256": "e1c756041e7155b36c87fb9a15a2c184f6967b1356b2563038e2805b96a57d79",
        "status": "complete_g2_development_failed_baseline_gate",
        "run_count": 135,
    },
    "g3": {
        "path": "runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.selection.json",
        "file_sha256": "22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7",
        "document_sha256": "4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34",
        "status": "complete_g3_e0_development_gate_failed",
        "run_count": 135,
    },
    "g8": {
        "path": "runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/frontier_only_attribution/g8_frontier_only_attribution.json",
        "file_sha256": "a95860a5e4ca3ee3a087bd0067c160ff1e955ac76af9065b6a23548aa44905c7",
        "document_sha256": "d43bf3e4ce1e603211a20ddd94a38850258a87d69a2e1100e0809b84e67180fb",
        "status": "complete_no_g8_authorized",
        "run_count": 25,
    },
}
TEXT_INPUTS = {
    "g1_result_audit": (
        "refine-logs/G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md",
        "9376c7202a01de1b3706ed92d68f90580ef576ab7b780c8e74cad5028e9b5c16",
    ),
    "g8_result_audit": (
        "refine-logs/G8_FRONTIER_ONLY_ATTRIBUTION_RESULT_AUDIT.md",
        "9a411c6186cb60e3c52f21358d3e4d42a01639bc8e7f4f01a13607df2cfa66fa",
    ),
    "b0_scene_audit": (
        "refine-logs/B0_SCENE_PROTOCOL_DIFFERENCE_AUDIT.md",
        "c4a528e0a9347d59c98531c8c89556cabe0b4874b3c547a94eb1256e232c95bc",
    ),
    "legacy_provenance": (
        "refine-logs/LEGACY_RESULT_PROVENANCE_AUDIT.md",
        "71619733d1b2eac94e66b84e5bf33396e745d876fe88d8e010b8e417d83f42f9",
    ),
}
FAMILIES = {
    "g2": {
        "control": "ready_order",
        "candidates": ("ready_order", "ready_warm_init", "ready_finish_init"),
        "seeds": tuple(f"D{i}" for i in range(66, 71)),
    },
    "g3": {
        "control": "ready_order",
        "candidates": (
            "ready_order",
            "ready_pne_envelope_first",
            "ready_pne_envelope_each",
        ),
        "seeds": tuple(f"D{i}" for i in range(71, 76)),
    },
}
CELLS = tuple(
    (load, topology)
    for load in ("low", "middle", "high")
    for topology in ("homogeneous", "heterogeneous")
)
METRICS = {
    "throughput": "throughput_requests_per_ms",
    "qpr": "qpr",
    "latency": "latency_mean_ms",
    "completion": "completion_ratio",
    "cost": "cost_per_completed_request",
}
EPSILON = 1e-15
COMPLEXITY_ORDER = {
    ("g2", "ready_warm_init"): 1,
    ("g2", "ready_finish_init"): 2,
    ("g3", "ready_pne_envelope_first"): 3,
    ("g3", "ready_pne_envelope_each"): 4,
}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ProtocolValidationError(f"{label} is not finite")
    return result


def summarize(values: Sequence[float]) -> dict[str, Any]:
    sample = [_number(value, "summary value") for value in values]
    if len(sample) < 2:
        raise ProtocolValidationError("summary requires at least two values")
    mean = fmean(sample)
    sd = stdev(sample)
    half_width = (
        float(scipy_stats.t.ppf(0.975, len(sample) - 1)) * sd / math.sqrt(len(sample))
    )
    return {
        "n": len(sample),
        "mean": mean,
        "sample_sd": sd,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "positive": sum(value > EPSILON for value in sample),
        "zero": sum(abs(value) <= EPSILON for value in sample),
        "negative": sum(value < -EPSILON for value in sample),
        "values": sample,
        "leave_one_seed_out_means": [
            fmean(sample[:index] + sample[index + 1 :]) for index in range(len(sample))
        ],
    }


def _validate_json(path: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    if file_hash(path) != spec["file_sha256"]:
        raise ProtocolValidationError(f"frozen JSON file hash mismatch: {path}")
    value = read_json(path)
    if not isinstance(value, dict):
        raise ProtocolValidationError(f"frozen JSON is not an object: {path}")
    stored = value.get("document_sha256")
    payload = dict(value)
    payload.pop("document_sha256", None)
    if stored != spec["document_sha256"] or object_hash(payload) != stored:
        raise ProtocolValidationError(f"frozen JSON document hash mismatch: {path}")
    if (
        value.get("status") != spec["status"]
        or value.get("run_count") != spec["run_count"]
    ):
        raise ProtocolValidationError(f"frozen JSON status/count mismatch: {path}")
    return value


def validate_inputs(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    repo_root = repo_root.resolve()
    products: dict[str, Any] = {}
    receipts: list[dict[str, Any]] = []
    for name, spec in JSON_INPUTS.items():
        path = repo_root / spec["path"]
        products[name] = _validate_json(path, spec)
        receipts.append(
            {
                "input": name,
                "path": spec["path"],
                "file_sha256": spec["file_sha256"],
                "document_sha256": spec["document_sha256"],
            }
        )
    for name, (relative, expected) in TEXT_INPUTS.items():
        actual = file_hash(repo_root / relative)
        if actual != expected:
            raise ProtocolValidationError(f"frozen text input hash mismatch: {name}")
        receipts.append({"input": name, "path": relative, "file_sha256": actual})
    return products, receipts


def _validated_development_rows(
    report: Mapping[str, Any], family: str
) -> list[dict[str, Any]]:
    rows = report.get("run_metrics")
    config = FAMILIES[family]
    if not isinstance(rows, list) or len(rows) != 135:
        raise ProtocolValidationError(f"{family} does not contain 135 run rows")
    identifiers = set()
    nash_counts: dict[tuple[str, str, str], int] = {}
    baseline_counts: dict[tuple[str, str], int] = {}
    result = []
    for item in rows:
        if not isinstance(item, Mapping):
            raise ProtocolValidationError(f"{family} has a malformed run row")
        row = dict(item)
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or run_id in identifiers:
            raise ProtocolValidationError(f"{family} run IDs are not unique")
        identifiers.add(run_id)
        seed = row.get("seed")
        load = row.get("load")
        topology = row.get("topology")
        if seed not in config["seeds"] or (load, topology) not in CELLS:
            raise ProtocolValidationError(f"{family} row is outside the frozen matrix")
        for source in METRICS.values():
            _number(row.get(source), f"{family}.{source}")
        if row.get("method") == "sche_nash":
            candidate = row.get("candidate")
            if candidate not in config["candidates"]:
                raise ProtocolValidationError(f"{family} has an unknown candidate")
            key = (str(candidate), str(load), str(topology))
            nash_counts[key] = nash_counts.get(key, 0) + 1
        else:
            if row.get("candidate") is not None or (load, topology) != (
                "low",
                "homogeneous",
            ):
                raise ProtocolValidationError(f"{family} baseline scope changed")
            method = str(row.get("method"))
            baseline_counts[(method, str(seed))] = (
                baseline_counts.get((method, str(seed)), 0) + 1
            )
        result.append(row)
    expected_nash = {
        (candidate, load, topology)
        for candidate in config["candidates"]
        for load, topology in CELLS
    }
    if set(nash_counts) != expected_nash or any(
        count != 5 for count in nash_counts.values()
    ):
        raise ProtocolValidationError(f"{family} candidate matrix is incomplete")
    baseline_methods = {key[0] for key in baseline_counts}
    if len(baseline_methods) != 9 or any(
        count != 1 for count in baseline_counts.values()
    ):
        raise ProtocolValidationError(f"{family} baseline matrix is incomplete")
    if {key[1] for key in baseline_counts} != set(config["seeds"]):
        raise ProtocolValidationError(f"{family} baseline seeds are incomplete")
    receipts = report.get("artifact_receipts")
    if not isinstance(receipts, list) or len(receipts) != 135:
        raise ProtocolValidationError(f"{family} artifact receipt set is incomplete")
    return result


def _cell_rows(family: str, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    config = FAMILIES[family]
    output = []
    for candidate in config["candidates"]:
        for load, topology in CELLS:
            current = sorted(
                [
                    row
                    for row in rows
                    if row.get("candidate") == candidate
                    and row.get("load") == load
                    and row.get("topology") == topology
                ],
                key=lambda row: str(row["seed"]),
            )
            control = sorted(
                [
                    row
                    for row in rows
                    if row.get("candidate") == config["control"]
                    and row.get("load") == load
                    and row.get("topology") == topology
                ],
                key=lambda row: str(row["seed"]),
            )
            if (
                len(current) != 5
                or len(control) != 5
                or [row["seed"] for row in current] != [row["seed"] for row in control]
            ):
                raise ProtocolValidationError(f"{family}/{candidate} cell pair failed")
            result: dict[str, Any] = {
                "family": family,
                "candidate": candidate,
                "is_control": candidate == config["control"],
                "load": load,
                "topology": topology,
                "seeds": [row["seed"] for row in current],
            }
            for metric, source in METRICS.items():
                raw = [_number(row[source], source) for row in current]
                deltas = [
                    _number(left[source], source) - _number(right[source], source)
                    for left, right in zip(current, control)
                ]
                raw_summary = summarize(raw)
                delta_summary = summarize(deltas)
                for key, value in raw_summary.items():
                    result[f"{metric}_{key}"] = value
                for key, value in delta_summary.items():
                    result[f"delta_{metric}_{key}"] = value
                control_mean = fmean(_number(row[source], source) for row in control)
                if control_mean <= 0.0:
                    raise ProtocolValidationError("control metric is not positive")
                result[f"{metric}_control_ratio"] = raw_summary["mean"] / control_mean
            output.append(result)
    return output


def _development_baseline_pairs(
    family: str, rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    config = FAMILIES[family]
    baselines = sorted(
        {str(row["method"]) for row in rows if row.get("method") != "sche_nash"}
    )
    baseline_means = {
        method: {
            metric: fmean(
                _number(row[source], source)
                for row in rows
                if row.get("method") == method
            )
            for metric, source in (
                ("throughput", METRICS["throughput"]),
                ("qpr", METRICS["qpr"]),
            )
        }
        for method in baselines
    }
    leaders = {
        metric: max(values[metric] for values in baseline_means.values())
        for metric in ("throughput", "qpr")
    }
    output = []
    for candidate in config["candidates"]:
        if candidate == config["control"]:
            continue
        current = sorted(
            [
                row
                for row in rows
                if row.get("candidate") == candidate
                and row.get("load") == "low"
                and row.get("topology") == "homogeneous"
            ],
            key=lambda row: str(row["seed"]),
        )
        for baseline in baselines:
            other = sorted(
                [row for row in rows if row.get("method") == baseline],
                key=lambda row: str(row["seed"]),
            )
            if [row["seed"] for row in current] != [row["seed"] for row in other]:
                raise ProtocolValidationError(
                    f"{family}/{candidate}/{baseline} pairing failed"
                )
            result: dict[str, Any] = {
                "family": family,
                "candidate": candidate,
                "baseline": baseline,
                "seeds": [row["seed"] for row in current],
                "baseline_within_five_percent_of_either_leader": (
                    baseline_means[baseline]["throughput"]
                    >= 0.95 * leaders["throughput"]
                    or baseline_means[baseline]["qpr"] >= 0.95 * leaders["qpr"]
                ),
            }
            joint_wins = 0
            for metric, source in (
                ("throughput", METRICS["throughput"]),
                ("qpr", METRICS["qpr"]),
            ):
                left = [_number(row[source], source) for row in current]
                right = [_number(row[source], source) for row in other]
                deltas = [a - b for a, b in zip(left, right)]
                summary = summarize(deltas)
                result[f"candidate_mean_{metric}"] = fmean(left)
                result[f"baseline_mean_{metric}"] = fmean(right)
                for key, value in summary.items():
                    result[f"delta_{metric}_{key}"] = value
            for left, right in zip(current, other):
                joint_wins += int(
                    _number(left[METRICS["throughput"]], "throughput")
                    > _number(right[METRICS["throughput"]], "throughput")
                    and _number(left[METRICS["qpr"]], "qpr")
                    > _number(right[METRICS["qpr"]], "qpr")
                )
            result["joint_win_count"] = joint_wins
            result["dual_mean_above"] = (
                result["delta_throughput_mean"] > 0 and result["delta_qpr_mean"] > 0
            )
            output.append(result)
    return output


def _formal_rows(
    report: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = report.get("run_metrics")
    if not isinstance(raw, list) or len(raw) != 200:
        raise ProtocolValidationError("formal product does not contain 200 rows")
    methods = sorted({str(row.get("method")) for row in raw})
    if len(methods) != 10:
        raise ProtocolValidationError("formal product does not contain ten methods")
    by_method: dict[str, list[Mapping[str, Any]]] = {}
    output = []
    for method in methods:
        rows = sorted(
            [row for row in raw if row.get("method") == method],
            key=lambda row: str(row["seed"]),
        )
        if len(rows) != 20 or len({row["seed"] for row in rows}) != 20:
            raise ProtocolValidationError(f"formal method is incomplete: {method}")
        by_method[method] = rows
        result: dict[str, Any] = {
            "method": method,
            "seeds": [row["seed"] for row in rows],
        }
        for metric, source in METRICS.items():
            summary = summarize([_number(row[source], source) for row in rows])
            for key, value in summary.items():
                result[f"{metric}_{key}"] = value
        output.append(result)
    for metric in ("throughput", "qpr"):
        ranked = sorted(output, key=lambda row: (-row[f"{metric}_mean"], row["method"]))
        for rank, row in enumerate(ranked, start=1):
            row[f"{metric}_rank"] = rank
    nash = next((row for row in output if row["method"] == "sche_nash"), None)
    if nash is None:
        raise ProtocolValidationError("formal product lacks sche_nash")
    leader_methods = {
        metric: min(output, key=lambda row: (-row[f"{metric}_mean"], row["method"]))[
            "method"
        ]
        for metric in ("throughput", "qpr")
    }
    leader_differences = {}
    for metric, leader in leader_methods.items():
        source = METRICS[metric]
        left = by_method["sche_nash"]
        right = by_method[str(leader)]
        if [row["seed"] for row in left] != [row["seed"] for row in right]:
            raise ProtocolValidationError(f"formal {metric} leader pairing failed")
        leader_differences[metric] = {
            "leader": leader,
            "nash_rank": nash[f"{metric}_rank"],
            "absolute_margin": nash[f"{metric}_mean"]
            - next(row[f"{metric}_mean"] for row in output if row["method"] == leader),
            "relative_margin": nash[f"{metric}_mean"]
            / next(row[f"{metric}_mean"] for row in output if row["method"] == leader)
            - 1.0,
            "paired_difference": summarize(
                [
                    _number(a[source], source) - _number(b[source], source)
                    for a, b in zip(left, right)
                ]
            ),
        }
    if nash["throughput_rank"] == nash["qpr_rank"] == 1:
        label = "dual_metric_superiority"
    elif (nash["throughput_rank"] == 1) != (nash["qpr_rank"] == 1):
        label = "single_metric_leading"
    elif all(
        evidence["paired_difference"]["ci95_low"]
        <= 0.0
        <= evidence["paired_difference"]["ci95_high"]
        for evidence in leader_differences.values()
    ):
        label = "not_leading_interval_compatible"
    else:
        label = "not_leading"
    return output, {
        "formal_homogeneous_low_label": label,
        "leader_differences": leader_differences,
        "unopened_scene_label": "unmeasured_against_all_baselines",
        "unopened_scenes": [
            {"load": load, "topology": topology}
            for load, topology in CELLS
            if (load, topology) != ("low", "homogeneous")
        ],
    }


def evaluate_candidates(
    cell_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    integrity: Mapping[str, bool],
) -> dict[str, Any]:
    evaluations = []
    for family, config in FAMILIES.items():
        for candidate in config["candidates"]:
            if candidate == config["control"]:
                continue
            cells = [
                row
                for row in cell_rows
                if row["family"] == family and row["candidate"] == candidate
            ]
            baselines = [
                row
                for row in baseline_rows
                if row["family"] == family and row["candidate"] == candidate
            ]
            if len(cells) != 6 or len(baselines) != 9:
                raise ProtocolValidationError(
                    f"candidate evidence incomplete: {family}/{candidate}"
                )
            dual_improvement_cells = sum(
                row["delta_throughput_mean"] > 0 and row["delta_qpr_mean"] > 0
                for row in cells
            )
            floors_passed = all(
                row["throughput_control_ratio"] >= 0.9
                and row["qpr_control_ratio"] >= 0.9
                for row in cells
            )
            dual_above_all = all(row["dual_mean_above"] for row in baselines)
            near_leaders = [
                row
                for row in baselines
                if row["baseline_within_five_percent_of_either_leader"]
            ]
            near_leader_pairs_passed = bool(near_leaders) and all(
                row["delta_throughput_positive"] >= 3
                and row["delta_qpr_positive"] >= 4
                and row["joint_win_count"] >= 3
                for row in near_leaders
            )
            best_t = max(baselines, key=lambda row: row["baseline_mean_throughput"])
            best_q = max(baselines, key=lambda row: row["baseline_mean_qpr"])
            loo_positive = all(
                value > 0
                for value in best_t["delta_throughput_leave_one_seed_out_means"]
            ) and all(
                value > 0 for value in best_q["delta_qpr_leave_one_seed_out_means"]
            )
            conditions = {
                "hom_low_dual_mean_above_all_nine_baselines": dual_above_all,
                "dual_improvement_at_least_five_of_six_cells": dual_improvement_cells
                >= 5,
                "near_leader_pair_wins_pass": near_leader_pairs_passed,
                "all_cell_ninety_percent_floors_pass": floors_passed,
                "all_hom_low_leave_one_out_leader_margins_positive": loo_positive,
                "retained_product_integrity_passed": integrity[family],
            }
            primary_ratios = [
                ratio
                for row in cells
                for ratio in (
                    row["throughput_control_ratio"],
                    row["qpr_control_ratio"],
                )
            ]
            evaluations.append(
                {
                    "family": family,
                    "candidate": candidate,
                    "dual_improvement_cell_count": dual_improvement_cells,
                    "mean_control_relative_ratio": fmean(primary_ratios),
                    "worst_control_relative_ratio": min(primary_ratios),
                    "complexity_order": COMPLEXITY_ORDER[(family, candidate)],
                    "near_leader_baseline_count": len(near_leaders),
                    "conditions": conditions,
                    "passed": all(conditions.values()),
                }
            )
    passing = [row for row in evaluations if row["passed"]]
    selected = (
        min(
            passing,
            key=lambda row: (
                -row["dual_improvement_cell_count"],
                -row["mean_control_relative_ratio"],
                -row["worst_control_relative_ratio"],
                row["complexity_order"],
                row["family"],
                row["candidate"],
            ),
        )
        if passing
        else None
    )
    return {
        "candidate_evaluations": evaluations,
        "existing_candidate_confirmation_preregistration_supported": selected
        is not None,
        "selected_existing_candidate": (
            None
            if selected is None
            else {"family": selected["family"], "candidate": selected["candidate"]}
        ),
    }


def analyze(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    products, input_receipts = validate_inputs(repo_root)
    development = {
        family: _validated_development_rows(products[family], family)
        for family in FAMILIES
    }
    cell_rows = [
        row for family, rows in development.items() for row in _cell_rows(family, rows)
    ]
    baseline_rows = [
        row
        for family, rows in development.items()
        for row in _development_baseline_pairs(family, rows)
    ]
    formal_rows, claim_labels = _formal_rows(products["formal_q61_q80"])
    integrity = {
        family: (
            products[family]["paper_equations_changed"] is False
            and products[family]["formal_results_eligible"] is False
            and products[family]["run_count"] == 135
            and len(products[family]["artifact_receipts"]) == 135
        )
        for family in FAMILIES
    }
    decision = evaluate_candidates(cell_rows, baseline_rows, integrity)
    source_path = Path(__file__).resolve()
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": (
            "complete_existing_candidate_confirmation_supported"
            if decision["existing_candidate_confirmation_preregistration_supported"]
            else "complete_no_existing_candidate_confirmation_supported"
        ),
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "definitions": {
            "independent_unit": "complete run/seed",
            "development_banks_remain_separate": True,
            "candidate_pair_difference": "candidate minus same-family ready_order C0",
            "baseline_pair_difference": "candidate minus same-family baseline",
            "intervals": "descriptive paired t intervals; no confirmatory p-value",
            "five_unopened_scenes": "candidate-versus-control only; not measured against all baselines",
            "old_pdf_values_are_selection_inputs": False,
        },
        "input_receipts": input_receipts,
        "source_receipts": [
            {
                "path": source_path.relative_to(repo_root).as_posix(),
                "file_sha256": file_hash(source_path),
            }
        ],
        "candidate_cell_metrics": cell_rows,
        "homogeneous_low_baseline_pairs": baseline_rows,
        "formal_homogeneous_low_metrics": formal_rows,
        "claim_scene_labels": claim_labels,
        "candidate_decision": decision,
        "candidate_cell_row_count": len(cell_rows),
        "baseline_pair_row_count": len(baseline_rows),
        "formal_method_row_count": len(formal_rows),
        "existing_candidate_confirmation_preregistration_supported": decision[
            "existing_candidate_confirmation_preregistration_supported"
        ],
        "new_candidate_implementation_authorized": False,
        "new_sampling_authorized": False,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
    }


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ProtocolValidationError(f"empty CSV product: {path.name}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def write_outputs(report: Mapping[str, Any], output_dir: Path) -> list[Path]:
    output_dir = output_dir.resolve()
    paths = [output_dir / name for name in OUTPUT_NAMES]
    if output_dir.exists():
        raise FileExistsError("post-G8 claim/scene output directory already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    temporary = [path.with_suffix(path.suffix + ".tmp") for path in paths]
    try:
        table_keys = (
            "candidate_cell_metrics",
            "homogeneous_low_baseline_pairs",
            "formal_homogeneous_low_metrics",
        )
        for index, key in enumerate(table_keys, start=1):
            _write_csv(temporary[index], report[key])
            temporary[index].replace(paths[index])
        final_report = dict(report)
        final_report["output_receipts"] = {
            paths[index].name: {
                "row_count": len(report[key]),
                "file_sha256": file_hash(paths[index]),
            }
            for index, key in enumerate(table_keys, start=1)
        }
        final_report["document_sha256"] = object_hash(final_report)
        with temporary[0].open("x", encoding="utf-8") as handle:
            json.dump(
                final_report,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")
        temporary[0].replace(paths[0])
    except Exception:
        for path in (*temporary, *paths):
            if path.exists():
                path.unlink()
        if output_dir.exists():
            output_dir.rmdir()
        raise
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if args.validate_only:
        products, receipts = validate_inputs(args.repo_root)
        for family in FAMILIES:
            _validated_development_rows(products[family], family)
        _formal_rows(products["formal_q61_q80"])
        print(
            json.dumps(
                {
                    "status": "post_g8_claim_scene_contract_validated",
                    "input_receipt_count": len(receipts),
                    "development_run_count": 270,
                    "formal_run_count": 200,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required unless --validate-only is used")
    report = analyze(args.repo_root)
    outputs = write_outputs(report, args.output_dir)
    print(
        json.dumps(
            {
                "status": report["status"],
                "existing_candidate_confirmation_preregistration_supported": report[
                    "existing_candidate_confirmation_preregistration_supported"
                ],
                "outputs": [str(path) for path in outputs],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
