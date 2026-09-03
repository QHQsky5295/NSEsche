"""Render the preregistered P2 primary-metric diagnostic figure.

The vector figure shows every run, the run-level mean, and its 95% BCa
interval.  NSESche is distinguished by both color and marker shape, while all
baselines remain legible in grayscale.  The old submitted bars are deliberately
absent because they are provenance diagnostics rather than pooled observations.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib import rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PIL import Image

from ..analysis.p2_homogeneous import METHOD_LABELS, P2_RESULT_SCHEMA
from ..protocol.schema import FORMAL_E1_METHODS, ProtocolValidationError
from ..protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


P2_FIGURE_SCHEMA = "NSE_P2_HOMOGENEOUS_MIDDLE_FIGURE_V1"
FIGURE_STEM = "p2_homogeneous_middle_primary"
WIDTH_MM = 182.0
HEIGHT_MM = 112.0
DEFAULT_DPI = 900
NASH_COLOR = "#0072B2"
BASELINE_COLOR = "#3F3F3F"
RAW_COLOR = "#A8A8A8"
METRIC_PANELS = (
    (
        "throughput_requests_per_ms",
        "Throughput ($10^3$ requests/s)",
        "(a) Throughput",
    ),
    ("qpr", "Quality–Price Ratio", "(b) Quality–Price Ratio"),
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolValidationError(
            f"figure source contains nonnumeric value: {value}"
        ) from exc
    if not math.isfinite(number):
        raise ProtocolValidationError("figure source contains a nonfinite value")
    return number


def _validate_result(result_path: Path) -> tuple[dict[str, Any], Path, Path]:
    result = read_json(result_path)
    if not isinstance(result, dict):
        raise ProtocolValidationError("P2 figure result source is not a JSON object")
    payload = copy.deepcopy(result)
    claimed = payload.pop("document_sha256", None)
    if (
        result.get("schema_version") != P2_RESULT_SCHEMA
        or claimed != object_hash(payload)
        or result.get("status") != "complete_claim_reframed_middle_cell"
        or result.get("all_first_qc_valid_rows_retained") is not True
        or result.get("result_conditioned_seed_or_run_selection") is not False
    ):
        raise ProtocolValidationError("P2 figure result source failed validation")
    receipts = result.get("artifact_receipts", {})
    paths: dict[str, Path] = {}
    for key in ("run_rows", "method_summaries"):
        receipt = receipts.get(key, {})
        path = Path(str(receipt.get("path", ""))).resolve()
        if (
            not path.is_file()
            or path.stat().st_size != receipt.get("bytes")
            or file_hash(path) != receipt.get("sha256")
        ):
            raise ProtocolValidationError(f"P2 figure source receipt changed: {key}")
        paths[key] = path
    return result, paths["run_rows"], paths["method_summaries"]


def _prepare_sources(
    run_rows_path: Path, summaries_path: Path
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    run_rows = _read_csv(run_rows_path)
    summaries = _read_csv(summaries_path)
    if len(run_rows) != 200:
        raise ProtocolValidationError("P2 figure requires all 200 run points")
    expected_labels = [METHOD_LABELS[method] for method in FORMAL_E1_METHODS]
    for metric, _, _ in METRIC_PANELS:
        metric_summaries = [row for row in summaries if row.get("metric") == metric]
        if (
            len(metric_summaries) != 10
            or [row.get("method_label") for row in metric_summaries] != expected_labels
            or any(row.get("n_finite") != "20" for row in metric_summaries)
        ):
            raise ProtocolValidationError(
                f"P2 figure requires ten complete ordered summaries for {metric}"
            )
        metric_runs = [row for row in run_rows if row.get(metric, "") != ""]
        if len(metric_runs) != 200:
            raise ProtocolValidationError(
                f"P2 figure requires 200 finite {metric} points"
            )
    return run_rows, summaries


def _draw_figure(
    run_rows: Sequence[Mapping[str, str]],
    summaries: Sequence[Mapping[str, str]],
) -> Figure:
    style = {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 7.5,
        "axes.labelsize": 8.5,
        "axes.titlesize": 9.0,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.0,
        "axes.linewidth": 0.7,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
    }
    labels = [METHOD_LABELS[method] for method in FORMAL_E1_METHODS]
    y = np.arange(len(labels), dtype=float)
    jitter = np.linspace(-0.17, 0.17, 20)
    with rc_context(style):
        figure = Figure(
            figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4),
            facecolor="white",
            constrained_layout=False,
        )
        FigureCanvasAgg(figure)
        axes = figure.subplots(1, 2, sharey=True)
        for panel_index, (axis, panel) in enumerate(zip(axes, METRIC_PANELS)):
            metric, xlabel, title = panel
            metric_summary = {
                row["method"]: row for row in summaries if row["metric"] == metric
            }
            all_values: list[float] = []
            for method_index, method in enumerate(FORMAL_E1_METHODS):
                points = [
                    _number(row[metric]) for row in run_rows if row["method"] == method
                ]
                if len(points) != 20:
                    raise ProtocolValidationError(
                        f"P2 figure lacks 20 {metric} points for {method}"
                    )
                all_values.extend(points)
                is_nash = method == "sche_nash"
                point_color = NASH_COLOR if is_nash else RAW_COLOR
                axis.scatter(
                    points,
                    method_index + jitter,
                    s=8.0 if is_nash else 6.0,
                    marker="D" if is_nash else "o",
                    facecolors=point_color if is_nash else "none",
                    edgecolors=point_color,
                    linewidths=0.45,
                    alpha=0.42 if is_nash else 0.55,
                    zorder=2,
                    rasterized=False,
                )
                summary = metric_summary[method]
                estimate = _number(summary["mean"])
                low = _number(summary["bca_low"])
                high = _number(summary["bca_high"])
                axis.errorbar(
                    estimate,
                    method_index,
                    xerr=np.asarray([[estimate - low], [high - estimate]]),
                    fmt="D" if is_nash else "o",
                    markersize=5.2 if is_nash else 4.2,
                    markerfacecolor=NASH_COLOR if is_nash else "white",
                    markeredgecolor=NASH_COLOR if is_nash else BASELINE_COLOR,
                    markeredgewidth=0.9,
                    ecolor=NASH_COLOR if is_nash else BASELINE_COLOR,
                    elinewidth=1.1 if is_nash else 0.85,
                    capsize=2.1,
                    capthick=0.8,
                    zorder=4,
                )
            minimum = min(all_values)
            maximum = max(all_values)
            span = maximum - minimum
            padding = 0.07 * span if span > 0.0 else max(abs(maximum) * 0.07, 0.01)
            axis.set_xlim(max(0.0, minimum - padding), maximum + padding)
            axis.set_xlabel(xlabel)
            axis.set_title(title, loc="left", fontweight="bold", pad=5.0)
            axis.grid(axis="x", color="#D8D8D8", linewidth=0.55, linestyle="--")
            axis.set_axisbelow(True)
            axis.spines["top"].set_visible(False)
            axis.spines["right"].set_visible(False)
            axis.tick_params(axis="y", length=0)
            if panel_index == 1:
                axis.spines["left"].set_visible(False)
        axes[0].set_yticks(y, labels=labels)
        axes[0].invert_yaxis()
        figure.subplots_adjust(
            left=0.19, right=0.985, bottom=0.19, top=0.91, wspace=0.17
        )
        handles = [
            Line2D(
                [0],
                [0],
                marker="o",
                color=BASELINE_COLOR,
                markerfacecolor="white",
                linewidth=0.9,
                markersize=4.2,
                label="Baseline mean (95% BCa CI)",
            ),
            Line2D(
                [0],
                [0],
                marker="D",
                color=NASH_COLOR,
                markerfacecolor=NASH_COLOR,
                linewidth=1.1,
                markersize=4.8,
                label="NSESche mean (95% BCa CI)",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markeredgecolor=RAW_COLOR,
                markerfacecolor="none",
                markersize=3.5,
                label="Individual runs (n=20)",
            ),
        ]
        figure.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(0.57, 0.015),
            ncol=3,
            frameon=False,
            handlelength=1.5,
            columnspacing=1.1,
        )
    return figure


def render_p2_figure(
    result_path: Path,
    output_dir: Path,
    *,
    dpi: int = DEFAULT_DPI,
) -> dict[str, Any]:
    if dpi < 100:
        raise ValueError("figure dpi must be at least 100")
    if output_dir.exists():
        raise ProtocolValidationError("P2 figure output directory must be absent")
    result, run_rows_path, summaries_path = _validate_result(result_path.resolve())
    run_rows, summaries = _prepare_sources(run_rows_path, summaries_path)
    output_dir.mkdir(parents=True)
    figure = _draw_figure(run_rows, summaries)
    paths = {
        "pdf": output_dir / f"{FIGURE_STEM}.pdf",
        "svg": output_dir / f"{FIGURE_STEM}.svg",
        "png": output_dir / f"{FIGURE_STEM}.png",
    }
    figure.savefig(
        paths["pdf"],
        format="pdf",
        facecolor="white",
        transparent=False,
        metadata={
            "Title": "NSESche homogeneous middle-load primary metrics",
            "Author": "NSESche revision experiment pipeline",
            "Subject": "Run-level means and 95% BCa confidence intervals",
        },
    )
    figure.savefig(paths["svg"], format="svg", facecolor="white", transparent=False)
    figure.savefig(
        paths["png"],
        format="png",
        dpi=dpi,
        facecolor="white",
        transparent=False,
    )
    figure.clear()
    with Image.open(paths["png"]) as image:
        png_size = {"width_px": image.width, "height_px": image.height}
        if image.mode not in {"RGB", "RGBA"}:
            raise ProtocolValidationError("P2 PNG has an unsupported color mode")
        if image.mode == "RGBA" and image.getextrema()[3] != (255, 255):
            raise ProtocolValidationError("P2 PNG unexpectedly contains transparency")
    artifacts = {
        key: {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": file_hash(path),
        }
        for key, path in paths.items()
    }
    manifest: dict[str, Any] = {
        "schema_version": P2_FIGURE_SCHEMA,
        "created_at": utc_now(),
        "status": "complete_publication_diagnostic_figure",
        "source_result": {
            "path": str(result_path.resolve()),
            "file_sha256": file_hash(result_path),
            "document_sha256": result["document_sha256"],
        },
        "source_tables": {
            "run_rows": {
                "path": str(run_rows_path),
                "sha256": file_hash(run_rows_path),
            },
            "method_summaries": {
                "path": str(summaries_path),
                "sha256": file_hash(summaries_path),
            },
        },
        "figure_contract": {
            "width_mm": WIDTH_MM,
            "height_mm": HEIGHT_MM,
            "png_dpi": dpi,
            "png_dimensions": png_size,
            "opaque_white_background": True,
            "vector_outputs": ["pdf", "svg"],
            "panels": [panel[0] for panel in METRIC_PANELS],
            "all_200_run_points_visible": True,
            "uncertainty": "run-level 95% BCa confidence interval",
            "nash_redundant_encoding": "blue filled diamond",
            "baseline_redundant_encoding": "gray open circle",
            "old_pdf_bars_plotted": False,
        },
        "artifacts": artifacts,
    }
    manifest["document_sha256"] = object_hash(manifest)
    manifest_path = output_dir / "p2_figure_manifest.json"
    write_json_atomic(manifest_path, manifest)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    manifest = render_p2_figure(args.result, args.output_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
