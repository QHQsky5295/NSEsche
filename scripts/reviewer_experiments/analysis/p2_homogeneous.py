"""Close the preregistered P2 homogeneous-middle result without tuning.

The integrity report supplies the 200 first canonical QC-valid run rows.  This
module retains all of them, computes run-level summaries and paired statistics,
and applies the claim-reframed V4 continuation rule.  The submitted Fig. 6
readings are used only as an explicitly approximate provenance diagnostic.
"""

from __future__ import annotations

import argparse
import copy
import csv
import math
from pathlib import Path
from statistics import fmean, median, stdev
from typing import Any, Mapping, Sequence

from ..protocol.p2_homogeneous import (
    P2_MIDDLE_LOAD,
    P2_MIDDLE_RUN_COUNT,
    P2_MIDDLE_TOPOLOGY,
    validate_middle_selection,
)
from ..protocol.schema import (
    FORMAL_E1_METHODS,
    G1_FORMAL_QUALIFICATION_SEEDS,
    ProtocolValidationError,
)
from ..protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)
from .stats import (
    bca_interval,
    holm_adjust,
    paired_effect_sizes,
    paired_permutation_test,
)


P2_RESULT_SCHEMA = "NSE_P2_HOMOGENEOUS_MIDDLE_RESULT_V1"
OLD_ALIGNMENT_SCHEMA = "NSE_OLD_FIG6_HOMOGENEOUS_MIDDLE_ALIGNMENT_V1"
NASH_METHOD = "sche_nash"
METHOD_LABELS = {
    "greedy": "Greedy",
    "random": "Random",
    "hash": "Hash",
    "load_least": "Load Balance",
    "sche_FaaSRank": "FaaSRank",
    "sche_OCS": "OCS",
    "sche_Hiku": "Hiku",
    "sche_jiagu": "Jiagu",
    "sche_orion": "Orion",
    "sche_nash": "NSESche",
}
METRICS = (
    "throughput_requests_per_ms",
    "qpr",
    "completion_ratio",
    "latency_mean_ms",
    "cost_per_completed_request",
)
PRIMARY_METRICS = ("throughput_requests_per_ms", "qpr")
HIGHER_IS_BETTER = {
    "throughput_requests_per_ms": True,
    "qpr": True,
    "completion_ratio": True,
    "latency_mean_ms": False,
    "cost_per_completed_request": False,
}
OUTPUT_NAMES = {
    "run_rows": "p2_run_rows.csv",
    "method_summaries": "p2_method_summaries.csv",
    "paired_comparisons": "p2_paired_comparisons.csv",
    "old_pdf_alignment": "p2_old_pdf_alignment.csv",
    "result": "p2_result.json",
}


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _interval(
    values: Sequence[float], *, n_resamples: int, seed: int
) -> dict[str, Any] | None:
    if len(values) < 3:
        return None
    return bca_interval(values, n_resamples=n_resamples, seed=seed)


def _rank_methods(
    summaries: Sequence[Mapping[str, Any]], metric: str
) -> dict[str, int]:
    rows = [
        row
        for row in summaries
        if row["metric"] == metric and row.get("mean") is not None
    ]
    rows.sort(
        key=lambda row: (
            -float(row["mean"]),
            FORMAL_E1_METHODS.index(str(row["method"])),
        )
    )
    return {str(row["method"]): index for index, row in enumerate(rows, start=1)}


def _validate_row_product(rows: Sequence[Mapping[str, Any]]) -> None:
    if len(rows) != P2_MIDDLE_RUN_COUNT:
        raise ProtocolValidationError("P2 analysis requires exactly 200 run rows")
    expected = {
        (method, seed)
        for method in FORMAL_E1_METHODS
        for seed in G1_FORMAL_QUALIFICATION_SEEDS
    }
    observed = [(str(row.get("method")), str(row.get("seed"))) for row in rows]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ProtocolValidationError("P2 run rows are not the frozen paired product")
    if len({str(row.get("run_id")) for row in rows}) != P2_MIDDLE_RUN_COUNT:
        raise ProtocolValidationError("P2 run rows do not contain unique run IDs")
    for row in rows:
        if (
            row.get("topology") != P2_MIDDLE_TOPOLOGY
            or row.get("load") != P2_MIDDLE_LOAD
        ):
            raise ProtocolValidationError("P2 run row escaped the registered cell")
        throughput = _finite(row.get("throughput_requests_per_ms"))
        completion = _finite(row.get("completion_ratio"))
        latency = _finite(row.get("latency_mean_ms"))
        cost = _finite(row.get("cost_per_completed_request"))
        qpr = _finite(row.get("qpr"))
        if throughput is None or throughput < 0.0:
            raise ProtocolValidationError("P2 row has invalid throughput")
        if completion is None or not 0.0 <= completion <= 1.0:
            raise ProtocolValidationError("P2 row has invalid completion ratio")
        applicable = (
            throughput > 0.0
            and latency is not None
            and latency > 0.0
            and cost is not None
            and cost > 0.0
        )
        if applicable:
            recomputed = throughput / (latency * cost)
            if qpr is None or not math.isclose(
                qpr, recomputed, rel_tol=1e-12, abs_tol=1e-15
            ):
                raise ProtocolValidationError(
                    "P2 run-level QPR was not recomputed exactly"
                )
            if row.get("qpr_applicable") is not True:
                raise ProtocolValidationError(
                    "P2 applicable QPR lacks its applicability flag"
                )
        elif qpr is not None or row.get("qpr_applicable") is not False:
            raise ProtocolValidationError(
                "P2 non-applicable QPR was not retained as missing"
            )


def _summarize_rows(
    rows: Sequence[Mapping[str, Any]], *, bca_resamples: int
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for method_index, method in enumerate(FORMAL_E1_METHODS):
        group = [row for row in rows if row["method"] == method]
        for metric_index, metric in enumerate(METRICS):
            values = [
                value
                for value in (_finite(row.get(metric)) for row in group)
                if value is not None
            ]
            ci = _interval(
                values,
                n_resamples=bca_resamples,
                seed=2026090400 + method_index * 100 + metric_index,
            )
            summaries.append(
                {
                    "method": method,
                    "method_label": METHOD_LABELS[method],
                    "metric": metric,
                    "higher_is_better": HIGHER_IS_BETTER[metric],
                    "n_total": len(group),
                    "n_finite": len(values),
                    "mean": fmean(values) if values else None,
                    "sample_sd": stdev(values) if len(values) >= 2 else None,
                    "median": median(values) if values else None,
                    "bca_low": ci["low"] if ci else None,
                    "bca_high": ci["high"] if ci else None,
                    "bca_confidence": ci["confidence"] if ci else None,
                    "bca_resamples": ci["resamples"] if ci else None,
                    "rank": None,
                }
            )
    for metric in PRIMARY_METRICS:
        ranks = _rank_methods(summaries, metric)
        for row in summaries:
            if row["metric"] == metric and row["method"] in ranks:
                row["rank"] = ranks[row["method"]]
    return summaries


def _paired_comparisons(
    rows: Sequence[Mapping[str, Any]],
    *,
    bca_resamples: int,
    permutation_resamples: int,
) -> list[dict[str, Any]]:
    by_method_seed = {(str(row["method"]), str(row["seed"])): row for row in rows}
    comparisons: list[dict[str, Any]] = []
    for metric_index, metric in enumerate(PRIMARY_METRICS):
        for method_index, comparator in enumerate(FORMAL_E1_METHODS[:-1]):
            pairs: list[tuple[float, float]] = []
            for seed in G1_FORMAL_QUALIFICATION_SEEDS:
                nash = _finite(by_method_seed[(NASH_METHOD, seed)].get(metric))
                base = _finite(by_method_seed[(comparator, seed)].get(metric))
                if nash is not None and base is not None:
                    pairs.append((nash, base))
            left = [pair[0] for pair in pairs]
            right = [pair[1] for pair in pairs]
            differences = [x - y for x, y in pairs]
            ci = _interval(
                differences,
                n_resamples=bca_resamples,
                seed=2026091400 + metric_index * 100 + method_index,
            )
            permutation = (
                paired_permutation_test(
                    left,
                    right,
                    alternative="two-sided",
                    n_resamples=permutation_resamples,
                    seed=2026092400 + metric_index * 100 + method_index,
                )
                if pairs
                else None
            )
            effects = paired_effect_sizes(left, right) if pairs else None
            relative = [(x - y) / y for x, y in pairs if y > 0.0]
            relative_complete = len(relative) == len(G1_FORMAL_QUALIFICATION_SEEDS)
            relative_ci = (
                _interval(
                    relative,
                    n_resamples=bca_resamples,
                    seed=2026093400 + metric_index * 100 + method_index,
                )
                if relative_complete
                else None
            )
            comparisons.append(
                {
                    "metric": metric,
                    "nash_method": NASH_METHOD,
                    "nash_label": METHOD_LABELS[NASH_METHOD],
                    "comparator_method": comparator,
                    "comparator_label": METHOD_LABELS[comparator],
                    "n_pairs": len(pairs),
                    "mean_difference": effects["mean_difference"] if effects else None,
                    "median_difference": effects["median_difference"]
                    if effects
                    else None,
                    "difference_bca_low": ci["low"] if ci else None,
                    "difference_bca_high": ci["high"] if ci else None,
                    "difference_bca_confidence": ci["confidence"] if ci else None,
                    "difference_bca_resamples": ci["resamples"] if ci else None,
                    "permutation_p_raw": permutation["p_value"]
                    if permutation
                    else None,
                    "permutation_exact": permutation["exact"] if permutation else None,
                    "permutation_resamples": permutation["resamples"]
                    if permutation
                    else None,
                    "permutation_p_holm": None,
                    "holm_reject_0_05": None,
                    "cohen_dz": effects["cohen_dz"] if effects else None,
                    "rank_biserial": effects["rank_biserial"] if effects else None,
                    "paired_wins": sum(value > 0.0 for value in differences),
                    "paired_ties": sum(value == 0.0 for value in differences),
                    "paired_losses": sum(value < 0.0 for value in differences),
                    "relative_change_n": len(relative),
                    "mean_relative_change": fmean(relative)
                    if relative_complete
                    else None,
                    "relative_change_bca_low": relative_ci["low"]
                    if relative_ci
                    else None,
                    "relative_change_bca_high": relative_ci["high"]
                    if relative_ci
                    else None,
                    "is_fifth_rank_comparator": False,
                }
            )
    p_values = [row["permutation_p_raw"] for row in comparisons]
    holm_complete = len(p_values) == 18 and all(value is not None for value in p_values)
    if holm_complete:
        adjusted, rejected = holm_adjust([float(value) for value in p_values])
        for row, value, reject in zip(comparisons, adjusted, rejected):
            row["permutation_p_holm"] = value
            row["holm_reject_0_05"] = reject
    return comparisons


def _old_alignment(
    summaries: Sequence[Mapping[str, Any]], old_spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if old_spec.get("schema_version") != OLD_ALIGNMENT_SCHEMA:
        raise ProtocolValidationError("unknown old Fig. 6 alignment specification")
    methods = old_spec.get("coordinate_system", {}).get("method_order")
    if methods != [METHOD_LABELS[method] for method in FORMAL_E1_METHODS]:
        raise ProtocolValidationError("old Fig. 6 method order changed")
    trigger = float(old_spec.get("relative_difference_trigger"))
    output: list[dict[str, Any]] = []
    summary_index = {(row["metric"], row["method_label"]): row for row in summaries}
    for metric, panel in old_spec.get("panels", {}).items():
        old_values = panel.get("approximate_values", [])
        bar_tops = panel.get("bar_top_y_px", [])
        if len(old_values) != 10 or len(bar_tops) != 10:
            raise ProtocolValidationError("old Fig. 6 alignment panel is incomplete")
        baseline = float(panel["baseline_y_px"])
        axis_top = float(panel["axis_top_y_px"])
        axis_max = float(panel["axis_max"])
        recomputed = [
            (baseline - float(y)) / (baseline - axis_top) * axis_max for y in bar_tops
        ]
        resolution_limited = set(panel.get("resolution_limited_methods", []))
        for index, method_label in enumerate(methods):
            declared = float(old_values[index])
            if not math.isclose(
                declared, recomputed[index], rel_tol=2e-4, abs_tol=2e-6
            ):
                raise ProtocolValidationError("old Fig. 6 pixel conversion changed")
            current = summary_index[(metric, method_label)]["mean"]
            relative = (
                (float(current) - declared) / declared
                if current is not None and declared > 0.0
                else None
            )
            output.append(
                {
                    "metric": metric,
                    "method_label": method_label,
                    "old_approximate_value": declared,
                    "new_run_level_mean": current,
                    "relative_difference": relative,
                    "absolute_relative_difference_ge_15pct": (
                        abs(relative) >= trigger if relative is not None else None
                    ),
                    "old_reading_resolution_limited": method_label
                    in resolution_limited,
                    "interpretation": "whole_scene_provenance_diagnostic_only",
                }
            )
    return output


def analyze_middle_rows(
    rows: Sequence[Mapping[str, Any]],
    old_spec: Mapping[str, Any],
    *,
    bca_resamples: int = 10_000,
    permutation_resamples: int = 100_000,
) -> dict[str, Any]:
    """Analyze an already integrity-validated 200-row middle cell."""

    normalized = [copy.deepcopy(dict(row)) for row in rows]
    _validate_row_product(normalized)
    summaries = _summarize_rows(normalized, bca_resamples=bca_resamples)
    comparisons = _paired_comparisons(
        normalized,
        bca_resamples=bca_resamples,
        permutation_resamples=permutation_resamples,
    )
    full_qpr = all(_finite(row.get("qpr")) is not None for row in normalized)
    ranks = {metric: _rank_methods(summaries, metric) for metric in PRIMARY_METRICS}
    nash_ranks = {metric: ranks[metric].get(NASH_METHOD) for metric in PRIMARY_METRICS}
    fifth_methods = {
        metric: next(
            (method for method, rank in ranks[metric].items() if rank == 5), None
        )
        for metric in PRIMARY_METRICS
    }
    fifth_comparisons: dict[str, dict[str, Any] | None] = {}
    for metric in PRIMARY_METRICS:
        comparator = fifth_methods[metric]
        match = next(
            (
                row
                for row in comparisons
                if row["metric"] == metric and row["comparator_method"] == comparator
            ),
            None,
        )
        if match is not None:
            match["is_fifth_rank_comparator"] = True
        fifth_comparisons[metric] = copy.deepcopy(match)

    possible_stop = full_qpr and all(
        rank is not None and 6 <= rank <= 10 for rank in nash_ranks.values()
    )
    confirmed_stop = possible_stop and all(
        fifth_comparisons[metric] is not None
        and fifth_comparisons[metric]["difference_bca_high"] is not None
        and float(fifth_comparisons[metric]["difference_bca_high"]) < 0.0
        for metric in PRIMARY_METRICS
    )
    if not full_qpr:
        disposition = "blocked_incomplete_full_qpr_gate"
    elif confirmed_stop:
        disposition = "pause_for_resubmission_value_review"
    else:
        disposition = (
            "eligible_for_separate_homogeneous_high_preregistration_after_result_audit"
        )
    alignment = _old_alignment(summaries, old_spec)
    return {
        "run_rows": normalized,
        "method_summaries": summaries,
        "paired_comparisons": comparisons,
        "old_pdf_alignment": alignment,
        "analysis_gate": {
            "run_count": len(normalized),
            "paired_seed_count": len(G1_FORMAL_QUALIFICATION_SEEDS),
            "all_methods_full_qpr_coverage": full_qpr,
            "holm_family_size": len(comparisons),
            "holm_family_complete": all(
                row["permutation_p_holm"] is not None for row in comparisons
            ),
        },
        "v4_continuation": {
            "nash_ranks": nash_ranks,
            "fifth_rank_methods": fifth_methods,
            "fifth_rank_comparisons": fifth_comparisons,
            "possible_stop_branch_entered": possible_stop,
            "both_fifth_place_bca_high_strictly_below_zero": confirmed_stop,
            "disposition": disposition,
            "high_load_directly_authorized": False,
        },
        "old_pdf_scene_diagnostic": {
            "comparison_count": len(alignment),
            "triggered_count": sum(
                row["absolute_relative_difference_ge_15pct"] is True
                for row in alignment
            ),
            "used_for_run_retention_retry_or_tuning": False,
        },
    }


def _validate_integrity_report(
    report_path: Path, selection: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = read_json(report_path)
    if not isinstance(report, dict):
        raise ProtocolValidationError("P2 integrity report is not a JSON object")
    payload = copy.deepcopy(report)
    claimed = payload.pop("document_sha256", None)
    if (
        report.get("schema_version") != "NSE_G1_FORMAL_CELL_REPORT_V1"
        or claimed != object_hash(payload)
        or report.get("formal_results_eligible") is not True
        or report.get("topology") != P2_MIDDLE_TOPOLOGY
        or report.get("load") != P2_MIDDLE_LOAD
        or report.get("run_count") != P2_MIDDLE_RUN_COUNT
        or report.get("fixed_seed_count") != 20
        or report.get("all_valid_rows_retained") is not True
        or report.get("result_conditioned_seed_removal_or_replacement") is not False
        or report.get("pairing", {}).get("passed") is not True
        or report.get("pairing", {}).get("runtime_identity_count") != 1
    ):
        raise ProtocolValidationError("P2 integrity report failed its frozen gates")
    source = selection["source_manifest"]
    protocol = report.get("protocol_manifest", {})
    if (
        protocol.get("manifest_hash") != source["manifest_hash"]
        or protocol.get("file_sha256") != source["file_sha256"]
        or Path(str(report.get("canonical_root", ""))).resolve()
        != (Path(str(selection["workspace"])) / "canonical").resolve()
    ):
        raise ProtocolValidationError(
            "P2 integrity report is not bound to this selection"
        )
    rows = report.get("run_metrics")
    artifacts = report.get("artifact_receipts")
    if not isinstance(rows, list) or not isinstance(artifacts, list):
        raise ProtocolValidationError("P2 integrity report lacks row receipts")
    selected = {
        row["run_id"]: row["run_spec_hash"] for row in selection["selection"]["runs"]
    }
    if {
        str(row.get("run_id")): str(row.get("run_spec_hash")) for row in rows
    } != selected or {str(row.get("run_id")) for row in artifacts} != set(selected):
        raise ProtocolValidationError(
            "P2 integrity rows differ from the frozen allowlist"
        )
    return report, [copy.deepcopy(dict(row)) for row in rows]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists():
        raise ProtocolValidationError(f"refusing to overwrite P2 artifact: {path}")
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_middle_analysis(
    selection_path: Path,
    integrity_report_path: Path,
    old_spec_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise ProtocolValidationError("P2 analysis output directory must be absent")
    selection = validate_middle_selection(selection_path)
    report, rows = _validate_integrity_report(integrity_report_path, selection)
    old_spec = read_json(old_spec_path)
    if not isinstance(old_spec, dict):
        raise ProtocolValidationError("old Fig. 6 specification is invalid")
    source_pdf = Path(str(old_spec.get("source_pdf", {}).get("path", ""))).resolve()
    if not source_pdf.is_file() or file_hash(source_pdf) != old_spec.get(
        "source_pdf", {}
    ).get("sha256"):
        raise ProtocolValidationError("submitted source PDF is missing or changed")
    analysis = analyze_middle_rows(rows, old_spec)
    output_dir.mkdir(parents=True)
    for key in (
        "run_rows",
        "method_summaries",
        "paired_comparisons",
        "old_pdf_alignment",
    ):
        _write_csv(output_dir / OUTPUT_NAMES[key], analysis[key])
    artifact_receipts = {
        key: {
            "path": str((output_dir / OUTPUT_NAMES[key]).resolve()),
            "bytes": (output_dir / OUTPUT_NAMES[key]).stat().st_size,
            "sha256": file_hash(output_dir / OUTPUT_NAMES[key]),
        }
        for key in (
            "run_rows",
            "method_summaries",
            "paired_comparisons",
            "old_pdf_alignment",
        )
    }
    result: dict[str, Any] = {
        "schema_version": P2_RESULT_SCHEMA,
        "created_at": utc_now(),
        "status": "complete_claim_reframed_middle_cell",
        "formal_results_eligible": True,
        "paper_ready_closed": False,
        "all_first_qc_valid_rows_retained": True,
        "result_conditioned_seed_or_run_selection": False,
        "parameter_or_mechanism_change_after_preregistration": False,
        "selection_receipt": {
            "path": str(selection_path.resolve()),
            "file_sha256": file_hash(selection_path),
            "document_sha256": selection["document_sha256"],
        },
        "integrity_report": {
            "path": str(integrity_report_path.resolve()),
            "file_sha256": file_hash(integrity_report_path),
            "document_sha256": report["document_sha256"],
            "old_dual_first_decision_diagnostic_only": report["cell_decision"],
        },
        "old_pdf_alignment_spec": {
            "path": str(old_spec_path.resolve()),
            "file_sha256": file_hash(old_spec_path),
            "source_pdf_sha256": old_spec["source_pdf"]["sha256"],
            "used_for_acceptance_retry_selection_or_tuning": False,
        },
        "statistics_contract": {
            "independent_unit": "one complete run/seed",
            "paired_seeds": list(G1_FORMAL_QUALIFICATION_SEEDS),
            "bca_resamples": 10_000,
            "paired_permutation_sign_flips": 100_000,
            "holm_family_size": 18,
            "qpr_definition": "throughput_requests_per_ms/(latency_mean_ms*cost_per_completed_request)",
        },
        "analysis_gate": analysis["analysis_gate"],
        "v4_continuation": analysis["v4_continuation"],
        "old_pdf_scene_diagnostic": analysis["old_pdf_scene_diagnostic"],
        "artifact_receipts": artifact_receipts,
    }
    result["document_sha256"] = object_hash(result)
    write_json_atomic(output_dir / OUTPUT_NAMES["result"], result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("integrity_report", type=Path)
    parser.add_argument("old_alignment_spec", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    result = write_middle_analysis(
        args.selection,
        args.integrity_report,
        args.old_alignment_spec,
        args.output_dir,
    )
    import json

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
