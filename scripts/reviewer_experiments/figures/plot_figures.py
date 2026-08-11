"""Draw Fig. 5--10 from run-level BCa summary CSVs.

All templates preserve the submitted panel layout and algorithm colors, while
adding asymmetric 95% BCa error bars.  If a comparisons CSV is supplied, a star
above a comparator bar denotes its Holm-adjusted paired test versus NSESche.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

try:
    from .style import (
        ABLATION_COLORS,
        ABLATION_ORDER,
        ALGORITHM_ORDER,
        LOAD_LABELS,
        LOAD_ORDER,
        algorithm_color,
        configure_style,
        ordered_present,
        shaded,
    )
except ImportError:
    from style import (  # type: ignore
        ABLATION_COLORS,
        ABLATION_ORDER,
        ALGORITHM_ORDER,
        LOAD_LABELS,
        LOAD_ORDER,
        algorithm_color,
        configure_style,
        ordered_present,
        shaded,
    )


METRIC_LABELS = {
    "cost": "Average Cost",
    "latency": "Latency (ms)",
    "throughput": "Throughput ($10^3$ requests/s)",
    "qpr": "Quality-Price Ratio",
    "scheduler_latency": "Placement Decision Time (ms)",
    "cpu_utilization": "CPU Utilization",
    "memory_utilization": "Memory Utilization",
}


def read_rows(path: str | Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: Any, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _filtered(
    rows: Iterable[Mapping[str, Any]], filters: Mapping[str, Any] | None
) -> list[Mapping[str, Any]]:
    filters = {
        key: str(value) for key, value in (filters or {}).items() if value is not None
    }
    return [
        row
        for row in rows
        if all(str(row.get(key, "")) == expected for key, expected in filters.items())
    ]


def _unique_order(
    rows: Sequence[Mapping[str, Any]], column: str, preferred: list[str]
) -> list[str]:
    present = {str(row.get(column, "")) for row in rows if str(row.get(column, ""))}
    return ordered_present(present, preferred)


def _lookup(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric: str,
    selectors: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    matches = [
        row
        for row in rows
        if str(row.get("metric", "")) == metric
        and all(str(row.get(key, "")) == str(value) for key, value in selectors.items())
    ]
    if len(matches) > 1:
        details = ", ".join(f"{key}={value}" for key, value in selectors.items())
        raise ValueError(
            f"summary is not unique for metric={metric}, {details}; add a scenario/QoS filter"
        )
    return matches[0] if matches else None


def _estimate_ci(row: Mapping[str, Any] | None) -> tuple[float, float, float]:
    if row is None:
        return math.nan, 0.0, 0.0
    estimate = _number(row.get("mean"))
    low = _number(row.get("bca_low"))
    high = _number(row.get("bca_high"))
    if not math.isfinite(estimate):
        return math.nan, 0.0, 0.0
    lower_error = estimate - low if math.isfinite(low) else 0.0
    upper_error = high - estimate if math.isfinite(high) else 0.0
    return estimate, max(0.0, lower_error), max(0.0, upper_error)


def _star(p_value: float) -> str:
    if not math.isfinite(p_value) or p_value > 0.05:
        return ""
    if p_value <= 0.001:
        return "***"
    if p_value <= 0.01:
        return "**"
    return "*"


def _comparison_star(
    comparisons: Sequence[Mapping[str, Any]],
    *,
    metric: str,
    comparator: str,
    selectors: Mapping[str, Any],
) -> str:
    matches = [
        row
        for row in comparisons
        if str(row.get("metric", "")) == metric
        and str(row.get("comparator", "")) == comparator
        and str(row.get("reference", "")) == "NSESche"
        and all(str(row.get(key, "")) == str(value) for key, value in selectors.items())
    ]
    if len(matches) != 1 or not _truthy(matches[0].get("reject_holm")):
        return ""
    return _star(_number(matches[0].get("p_holm")))


def _finish_axis(ax: plt.Axes, *, xlabel: str, ylabel: str, panel: str) -> None:
    ax.set_xlabel(xlabel, labelpad=8, fontweight="bold")
    ax.set_ylabel(ylabel, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.5,
        -0.20,
        panel,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=14,
        fontweight="bold",
    )


def _save(fig: plt.Figure, output_prefix: str | Path) -> tuple[Path, Path]:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    png = prefix.with_suffix(".png")
    pdf = prefix.with_suffix(".pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    return png, pdf


def _grouped_algorithm_bars(
    ax: plt.Axes,
    rows: Sequence[Mapping[str, Any]],
    *,
    metric: str,
    categories: Sequence[str],
    category_column: str,
    algorithms: Sequence[str],
    comparisons: Sequence[Mapping[str, Any]],
    base_selectors: Mapping[str, Any] | None = None,
) -> None:
    x = np.arange(len(categories), dtype=float)
    width = 0.80 / max(1, len(algorithms))
    top = 0.0
    for index, algorithm in enumerate(algorithms):
        positions = x + (index - len(algorithms) / 2.0 + 0.5) * width
        values: list[float] = []
        lower: list[float] = []
        upper: list[float] = []
        for category in categories:
            selectors = {
                **(base_selectors or {}),
                category_column: category,
                "algorithm": algorithm,
            }
            estimate, low_error, high_error = _estimate_ci(
                _lookup(rows, metric=metric, selectors=selectors)
            )
            values.append(estimate)
            lower.append(low_error)
            upper.append(high_error)
            if math.isfinite(estimate):
                top = max(top, estimate + high_error)
        ax.bar(
            positions,
            values,
            width,
            color=algorithm_color(algorithm),
            alpha=0.90,
            label=algorithm,
            yerr=np.asarray([lower, upper]),
            capsize=2.2,
            error_kw={"elinewidth": 0.8, "ecolor": "#222222", "capthick": 0.8},
        )
        for position, category, value, high_error in zip(
            positions, categories, values, upper
        ):
            if not math.isfinite(value):
                continue
            selectors = {**(base_selectors or {}), category_column: category}
            marker = _comparison_star(
                comparisons,
                metric=metric,
                comparator=algorithm,
                selectors=selectors,
            )
            if marker:
                ax.text(
                    position,
                    value + high_error + max(top, 1.0) * 0.015,
                    marker,
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )
    ax.set_xticks(x)


def _latency_panel(
    ax: plt.Axes,
    rows: Sequence[Mapping[str, Any]],
    *,
    loads: Sequence[str],
    algorithms: Sequence[str],
    comparisons: Sequence[Mapping[str, Any]],
) -> None:
    components = ["cold_start_latency", "queue_latency", "execution_latency"]
    has_components = any(str(row.get("metric", "")) in components for row in rows)
    if not has_components:
        _grouped_algorithm_bars(
            ax,
            rows,
            metric="latency",
            categories=loads,
            category_column="load",
            algorithms=algorithms,
            comparisons=comparisons,
        )
        return

    x = np.arange(len(loads), dtype=float)
    width = 0.80 / max(1, len(algorithms))
    top = 0.0
    shades = (-0.18, 0.18, 0.40)
    for index, algorithm in enumerate(algorithms):
        positions = x + (index - len(algorithms) / 2.0 + 0.5) * width
        bottoms = np.zeros(len(loads), dtype=float)
        for component, shade_amount in zip(components, shades):
            values = []
            for load in loads:
                estimate, _, _ = _estimate_ci(
                    _lookup(
                        rows,
                        metric=component,
                        selectors={"load": load, "algorithm": algorithm},
                    )
                )
                values.append(0.0 if not math.isfinite(estimate) else estimate)
            ax.bar(
                positions,
                values,
                width,
                bottom=bottoms,
                color=shaded(algorithm_color(algorithm), shade_amount),
                alpha=0.82,
            )
            bottoms += np.asarray(values)

        for position, load, stacked_total in zip(positions, loads, bottoms):
            total, low_error, high_error = _estimate_ci(
                _lookup(
                    rows,
                    metric="latency",
                    selectors={"load": load, "algorithm": algorithm},
                )
            )
            plotted_total = total if math.isfinite(total) else stacked_total
            ax.errorbar(
                position,
                plotted_total,
                yerr=np.asarray([[low_error], [high_error]]),
                fmt="none",
                capsize=2.2,
                elinewidth=0.8,
                capthick=0.8,
                ecolor="#222222",
            )
            top = max(top, plotted_total + high_error)
            marker = _comparison_star(
                comparisons,
                metric="latency",
                comparator=algorithm,
                selectors={"load": load},
            )
            if marker:
                ax.text(
                    position,
                    plotted_total + high_error + max(top, 1.0) * 0.015,
                    marker,
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )
    ax.set_xticks(x)
    legend = [
        Patch(facecolor=algorithm_color(name), alpha=0.9, label=name)
        for name in algorithms
    ]
    ax.legend(handles=legend, loc="upper left", ncol=2, frameon=True)


def plot_fig5(
    summary_rows: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    filters: Mapping[str, Any] | None = None,
) -> tuple[plt.Figure, tuple[Path, Path]]:
    configure_style()
    rows = _filtered(summary_rows, filters)
    loads = _unique_order(rows, "load", LOAD_ORDER)
    variants = _unique_order(rows, "variant", ABLATION_ORDER)
    metrics = ["cost", "latency", "throughput", "qpr"]
    labels = [
        "Cost",
        "Latency (ms)",
        "Throughput ($10^3$ requests/s)",
        "Quality-Price Ratio",
    ]
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    x = np.arange(len(loads), dtype=float)
    width = 0.70 / max(1, len(variants))
    for panel_index, (ax, metric, ylabel) in enumerate(zip(axes, metrics, labels)):
        top = 0.0
        for index, variant in enumerate(variants):
            positions = x + (index - len(variants) / 2.0 + 0.5) * width
            values, lower, upper = [], [], []
            for load in loads:
                estimate, low_error, high_error = _estimate_ci(
                    _lookup(
                        rows,
                        metric=metric,
                        selectors={"load": load, "variant": variant},
                    )
                )
                values.append(estimate)
                lower.append(low_error)
                upper.append(high_error)
                if math.isfinite(estimate):
                    top = max(top, estimate + high_error)
            ax.bar(
                positions,
                values,
                width,
                color=ABLATION_COLORS.get(variant, "#cccccc"),
                alpha=0.82,
                edgecolor="#555555",
                linewidth=0.5,
                label=variant,
                yerr=np.asarray([lower, upper]),
                capsize=2.5,
                error_kw={"elinewidth": 0.8, "ecolor": "#222222", "capthick": 0.8},
            )
            for position, load, value, high_error in zip(
                positions, loads, values, upper
            ):
                if not math.isfinite(value) or variant == "NSESche":
                    continue
                marker = _comparison_star(
                    comparisons,
                    metric=metric,
                    comparator=variant,
                    selectors={"load": load},
                )
                if marker:
                    ax.text(
                        position,
                        value + high_error + max(top, 1.0) * 0.015,
                        marker,
                        ha="center",
                        va="bottom",
                        fontsize=9,
                    )
        ax.set_xticks(x)
        ax.set_xticklabels([LOAD_LABELS.get(load, load.title()) for load in loads])
        _finish_axis(
            ax,
            xlabel="Workload Intensity",
            ylabel=ylabel,
            panel=f"({chr(97 + panel_index)})",
        )
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.01),
        ncol=max(1, len(legend_labels)),
        frameon=False,
        fontsize=14,
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.25, wspace=0.30)
    return fig, _save(fig, output_prefix)


def _performance_figure(
    summary_rows: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    filters: Mapping[str, Any] | None = None,
) -> tuple[plt.Figure, tuple[Path, Path]]:
    configure_style()
    rows = _filtered(summary_rows, filters)
    comparison_rows = _filtered(comparisons, filters)
    loads = _unique_order(rows, "load", LOAD_ORDER)
    algorithms = _unique_order(rows, "algorithm", ALGORITHM_ORDER)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    panels = [
        (axes[0, 0], "latency", "Latency (ms)", "(a) Average Latency"),
        (axes[0, 1], "cost", "Average Cost", "(b) Average Cost"),
        (
            axes[1, 0],
            "throughput",
            "Throughput ($10^3$ requests/s)",
            "(c) Throughput",
        ),
        (axes[1, 1], "qpr", "Quality-Price Ratio", "(d) Quality-Price Ratio"),
    ]
    for ax, metric, ylabel, panel in panels:
        if metric == "latency":
            _latency_panel(
                ax,
                rows,
                loads=loads,
                algorithms=algorithms,
                comparisons=comparison_rows,
            )
        else:
            _grouped_algorithm_bars(
                ax,
                rows,
                metric=metric,
                categories=loads,
                category_column="load",
                algorithms=algorithms,
                comparisons=comparison_rows,
            )
        ax.set_xticklabels([LOAD_LABELS.get(load, load.title()) for load in loads])
        if metric != "latency":
            ax.legend(loc="upper right", ncol=2, frameon=True)
        _finish_axis(ax, xlabel="Load Types", ylabel=ylabel, panel=panel)
    fig.tight_layout(pad=2.5)
    fig.subplots_adjust(hspace=0.30, wspace=0.15, left=0.08, right=0.95)
    return fig, _save(fig, output_prefix)


def plot_fig6(
    summary_rows: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    filters: Mapping[str, Any] | None = None,
) -> tuple[plt.Figure, tuple[Path, Path]]:
    return _performance_figure(
        summary_rows,
        output_prefix,
        comparisons=comparisons,
        filters=filters,
    )


def build_fig7_ci_table(
    summary_rows: Sequence[Mapping[str, Any]],
    *,
    filters: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build the auditable per-cell table underlying the CPU/memory heatmaps.

    Missing cells are emitted explicitly with ``coverage_status=unavailable``;
    they are never replaced with zero.  The BCa bounds originate from
    independent run/seed values in ``summary.csv``.
    """

    rows = _filtered(summary_rows, filters)
    if not rows:
        raise ValueError("Fig. 7 has no algorithm/load cells after filtering")
    # Fig. 7 is a frozen 10 methods x 3 loads design.  Preserve all 30 cells in
    # each heatmap even when a formal run is unavailable; absent cells are NA,
    # never silently dropped or interpreted as zero.
    algorithms = list(ALGORITHM_ORDER)
    loads = list(LOAD_ORDER)
    output: list[dict[str, Any]] = []
    for metric in ("cpu_utilization", "memory_utilization"):
        for algorithm in algorithms:
            for load in loads:
                source = _lookup(
                    rows,
                    metric=metric,
                    selectors={"algorithm": algorithm, "load": load},
                )
                mean = _number(source.get("mean")) if source is not None else math.nan
                low = _number(source.get("bca_low")) if source is not None else math.nan
                high = (
                    _number(source.get("bca_high")) if source is not None else math.nan
                )
                finite_mean = math.isfinite(mean)
                finite_ci = math.isfinite(low) and math.isfinite(high)
                n_runs = int(_number(source.get("n_finite"), 0.0)) if source else 0
                total_runs = int(_number(source.get("n_total"), 0.0)) if source else 0
                missing_runs = total_runs - n_runs
                output.append(
                    {
                        "metric": metric,
                        "algorithm": algorithm,
                        "load": load,
                        "mean": mean,
                        "bca_low": low,
                        "bca_high": high,
                        "n_runs": n_runs,
                        "total_runs": total_runs,
                        "missing_runs": missing_runs,
                        "ci_method": ("BCa bootstrap 95%" if finite_ci else "NA"),
                        "unit": "dimensionless_normalized_utilization",
                        "metric_definition": (
                            "mean_over_node_frame_samples_of_node_cpu_over_cpu_limit"
                            if metric == "cpu_utilization"
                            else "mean_over_node_frame_samples_of_unready_memory_over_memory_limit"
                        ),
                        "inference_unit": "run_seed",
                        "coverage_status": (
                            "ok"
                            if finite_mean and finite_ci and n_runs == total_runs
                            else ("partial" if finite_mean else "unavailable")
                        ),
                        "ci_status": "ok" if finite_ci else "unavailable",
                    }
                )
    return output


def write_fig7_ci_table(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "metric",
        "algorithm",
        "load",
        "mean",
        "bca_low",
        "bca_high",
        "n_runs",
        "total_runs",
        "missing_runs",
        "ci_method",
        "unit",
        "metric_definition",
        "inference_unit",
        "coverage_status",
        "ci_status",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def plot_fig7(
    summary_rows: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    filters: Mapping[str, Any] | None = None,
) -> tuple[plt.Figure, tuple[Path, Path], list[dict[str, Any]]]:
    """Draw paired 10-by-3 CPU and memory utilization heatmaps."""

    configure_style()
    table = build_fig7_ci_table(summary_rows, filters=filters)
    algorithms = list(ALGORITHM_ORDER)
    loads = list(LOAD_ORDER)
    fig, axes = plt.subplots(1, 2, figsize=(12, 10), constrained_layout=True)
    panels = (
        (
            "cpu_utilization",
            "Normalized CPU Utilization",
            "(a) CPU Utilization",
        ),
        (
            "memory_utilization",
            "Normalized Memory Utilization",
            "(b) Memory Utilization",
        ),
    )
    for ax, (metric, colorbar_label, title) in zip(axes, panels):
        matrix = np.full((len(algorithms), len(loads)), np.nan, dtype=float)
        for row in table:
            if row["metric"] != metric:
                continue
            value = _number(row.get("mean"))
            if math.isfinite(value):
                matrix[
                    algorithms.index(str(row["algorithm"])),
                    loads.index(str(row["load"])),
                ] = value
        finite = matrix[np.isfinite(matrix)]
        if finite.size:
            lower = min(0.0, float(np.min(finite)))
            upper = float(np.max(finite))
            if math.isclose(lower, upper):
                upper = lower + 1.0
            image = ax.imshow(
                matrix, aspect="auto", cmap="YlGnBu", vmin=lower, vmax=upper
            )
            colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
            colorbar.set_label(colorbar_label)
        else:
            ax.imshow(
                np.zeros_like(matrix), aspect="auto", cmap="Greys", vmin=0, vmax=1
            )
        for row_index in range(len(algorithms)):
            for column_index in range(len(loads)):
                value = matrix[row_index, column_index]
                text_color = "black"
                if finite.size and math.isfinite(value):
                    normalized = (value - lower) / max(upper - lower, 1e-12)
                    text_color = "white" if normalized >= 0.58 else "black"
                ax.text(
                    column_index,
                    row_index,
                    f"{value:.3f}" if math.isfinite(value) else "NA",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color,
                )
        ax.set_xticks(np.arange(len(loads)))
        ax.set_xticklabels([LOAD_LABELS.get(load, load.title()) for load in loads])
        ax.set_yticks(np.arange(len(algorithms)))
        ax.set_yticklabels(algorithms)
        ax.set_xlabel("Workload Intensity", fontweight="bold")
        ax.set_ylabel("Scheduling Method", fontweight="bold")
        ax.set_title(title, fontweight="bold")
    return fig, _save(fig, output_prefix), table


def plot_fig9(
    summary_rows: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    filters: Mapping[str, Any] | None = None,
) -> tuple[plt.Figure, tuple[Path, Path]]:
    return _performance_figure(
        summary_rows,
        output_prefix,
        comparisons=comparisons,
        filters=filters,
    )


def plot_fig8(
    summary_rows: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    filters: Mapping[str, Any] | None = None,
    metric: str = "scheduler_latency",
) -> tuple[plt.Figure, tuple[Path, Path]]:
    configure_style()
    rows = _filtered(summary_rows, filters)
    comparison_rows = _filtered(comparisons, filters)
    loads = _unique_order(rows, "load", LOAD_ORDER)
    algorithms = _unique_order(rows, "algorithm", ALGORITHM_ORDER)
    fig, ax = plt.subplots(figsize=(14, 6.5))
    _grouped_algorithm_bars(
        ax,
        rows,
        metric=metric,
        categories=loads,
        category_column="load",
        algorithms=algorithms,
        comparisons=comparison_rows,
    )
    ax.set_xticklabels([LOAD_LABELS.get(load, load.title()) for load in loads])
    _finish_axis(
        ax,
        xlabel="Workload Intensity",
        ylabel=METRIC_LABELS.get(metric, metric.replace("_", " ").title()),
        panel="(a) Placement-policy Decision Overhead",
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=5, frameon=False)
    fig.tight_layout()
    fig.subplots_adjust(top=0.82, bottom=0.20)
    return fig, _save(fig, output_prefix)


def plot_fig10(
    summary_rows: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    filters: Mapping[str, Any] | None = None,
) -> tuple[plt.Figure, tuple[Path, Path]]:
    configure_style()
    rows = _filtered(summary_rows, filters)
    comparison_rows = _filtered(comparisons, filters)
    node_values = {
        str(row.get("node_count", "")) for row in rows if str(row.get("node_count", ""))
    }

    def node_key(value: str) -> tuple[int, float | str]:
        try:
            return (0, float(value))
        except ValueError:
            return (1, value)

    nodes = sorted(node_values, key=node_key)
    algorithms = _unique_order(rows, "algorithm", ALGORITHM_ORDER)
    metrics = [
        "cost",
        "latency",
        "throughput",
        "qpr",
        "cpu_utilization",
        "memory_utilization",
    ]
    panels = [
        "(a) Average Cost",
        "(b) Average Latency",
        "(c) Throughput",
        "(d) Quality-Price Ratio",
        "(e) CPU Utilization",
        "(f) Memory Utilization",
    ]
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    for ax, metric, panel in zip(axes.flatten(), metrics, panels):
        _grouped_algorithm_bars(
            ax,
            rows,
            metric=metric,
            categories=nodes,
            category_column="node_count",
            algorithms=algorithms,
            comparisons=comparison_rows,
        )
        ax.set_xticklabels(nodes)
        _finish_axis(
            ax,
            xlabel="Number of Nodes",
            ylabel=METRIC_LABELS.get(metric, metric.replace("_", " ").title()),
            panel=panel,
        )
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.005),
            ncol=min(5, len(labels)),
            frameon=False,
        )
    fig.tight_layout(pad=2.0)
    fig.subplots_adjust(bottom=0.14, hspace=0.38, wspace=0.25)
    return fig, _save(fig, output_prefix)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--comparisons")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--figure", choices=["5", "6", "7", "8", "9", "10", "all"], default="all"
    )
    parser.add_argument("--fig5-scenario", default="ablation")
    parser.add_argument("--fig6-scenario", default="homogeneous")
    parser.add_argument("--fig7-scenario", default="homogeneous")
    parser.add_argument("--fig8-scenario", default="homogeneous")
    parser.add_argument("--fig9-scenario", default="heterogeneous")
    parser.add_argument("--fig10-scenario", default="weak_scaling")
    parser.add_argument(
        "--fig10-load",
        default="high",
        help="one pressure level per six-panel weak-scaling figure",
    )
    parser.add_argument("--scheduler-metric", default="scheduler_latency")
    args = parser.parse_args(argv)

    summary = read_rows(args.summary)
    comparisons = read_rows(args.comparisons)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    requested = (
        {"5", "6", "7", "8", "9", "10"} if args.figure == "all" else {args.figure}
    )
    generated: list[Path] = []
    if "5" in requested:
        fig, paths = plot_fig5(
            summary,
            output / "fig5_ablation",
            comparisons=comparisons,
            filters={"scenario": args.fig5_scenario},
        )
        generated.extend(paths)
        plt.close(fig)
    if "6" in requested:
        fig, paths = plot_fig6(
            summary,
            output / "fig6_homogeneous",
            comparisons=comparisons,
            filters={"scenario": args.fig6_scenario},
        )
        generated.extend(paths)
        plt.close(fig)
    if "7" in requested:
        fig, paths, table = plot_fig7(
            summary,
            output / "fig7_resource_heatmap",
            filters={"scenario": args.fig7_scenario},
        )
        generated.extend(paths)
        generated.append(
            write_fig7_ci_table(output / "fig7_resource_heatmap_ci.csv", table)
        )
        plt.close(fig)
    if "8" in requested:
        fig, paths = plot_fig8(
            summary,
            output / "fig8_scheduler_overhead",
            comparisons=comparisons,
            filters={"scenario": args.fig8_scenario},
            metric=args.scheduler_metric,
        )
        generated.extend(paths)
        plt.close(fig)
    if "9" in requested:
        fig, paths = plot_fig9(
            summary,
            output / "fig9_heterogeneous",
            comparisons=comparisons,
            filters={"scenario": args.fig9_scenario},
        )
        generated.extend(paths)
        plt.close(fig)
    if "10" in requested:
        fig, paths = plot_fig10(
            summary,
            output / "fig10_weak_scaling",
            comparisons=comparisons,
            filters={"scenario": args.fig10_scenario, "load": args.fig10_load},
        )
        generated.extend(paths)
        plt.close(fig)
    for path in generated:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
