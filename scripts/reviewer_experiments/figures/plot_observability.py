"""Publication templates for reviewer Fig. 11--13 (E3/E4/E8/E9)."""

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

try:
    from .style import (
        ALGORITHM_ORDER,
        algorithm_color,
        configure_style,
        ordered_present,
        shaded,
    )
except ImportError:
    from style import (  # type: ignore
        ALGORITHM_ORDER,
        algorithm_color,
        configure_style,
        ordered_present,
        shaded,
    )


QOS_ORDER = ["latency", "throughput", "cost"]
QOS_LABELS = {
    "latency": "Latency-\nsensitive",
    "throughput": "Throughput-\nsensitive",
    "cost": "Cost-\nsensitive",
}
FEATURE_LABELS = {
    "h_ri": "$H_{RI}$",
    "h_fc": "$H_{FC}$",
    "h_nd": "$H_{ND}$",
    "h_pi": "$H_{PI}$",
    "impact": "Impact",
    "active_differentiation_mean": r"Active $H_{PI}$ mean",
}
OUTCOME_LABELS = {
    "queue_pressure_mean": "queue pressure",
    "execution_mean_ms": "execution time",
    "communication_wait_mean_ms": "communication wait",
    "throughput_shortfall_vs_run_max": "throughput shortfall",
    "stage_latency_p95_ms": "stage-latency p95",
    "placement_dispersion_normalized": "placement dispersion",
    "co_location_conflict_pair_ratio_proxy": "co-location conflict",
    "near_tie_player_ratio": "near-tie decisions",
    "differentiation_changed_top_choice_ratio": "changed top choice",
}
BURST_LABELS = {
    "spike5x50ms": "5x 50-ms spike",
    "sustained3x200ms": "3x 200-ms sustained",
    "pulse4x4x50ms": "four 4x 50-ms pulses",
}


def read_rows(path: str | Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _star(value: Any) -> str:
    probability = _number(value)
    if not math.isfinite(probability) or probability > 0.05:
        return ""
    if probability <= 0.001:
        return "***"
    if probability <= 0.01:
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
    return _star(matches[0].get("p_holm"))


def _filter(
    rows: Iterable[Mapping[str, Any]], filters: Mapping[str, Any] | None
) -> list[Mapping[str, Any]]:
    selected = {
        key: str(value) for key, value in (filters or {}).items() if value is not None
    }
    return [
        row
        for row in rows
        if all(str(row.get(key, "")) == value for key, value in selected.items())
    ]


def _algorithms(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    present = {str(row.get("algorithm", "")) for row in rows if row.get("algorithm")}
    return ordered_present(present, ALGORITHM_ORDER)


def _save(fig: plt.Figure, output_prefix: str | Path) -> tuple[Path, Path]:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    png = prefix.with_suffix(".png")
    pdf = prefix.with_suffix(".pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    return png, pdf


def _panel_label(ax: plt.Axes, text: str, *, y: float = -0.20) -> None:
    ax.text(
        0.5,
        y,
        text,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=13,
        fontweight="bold",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", alpha=0.28, linewidth=0.8)
    ax.set_axisbelow(True)


def _active_spans(rows: Sequence[Mapping[str, Any]]) -> list[tuple[float, float]]:
    points = sorted(
        {
            (_number(row.get("time_relative_ms")), _truthy(row.get("burst_active")))
            for row in rows
            if math.isfinite(_number(row.get("time_relative_ms")))
        }
    )
    spans: list[tuple[float, float]] = []
    start: float | None = None
    previous = math.nan
    step = 1.0
    for time_ms, active in points:
        if math.isfinite(previous):
            step = max(1e-9, time_ms - previous)
        if active and start is None:
            start = time_ms
        if not active and start is not None:
            spans.append((start, time_ms))
            start = None
        previous = time_ms
    if start is not None and math.isfinite(previous):
        spans.append((start, previous + step))
    return spans


def plot_fig11(
    timeseries_summary: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    filters: Mapping[str, Any] | None = None,
    run_metrics: Sequence[Mapping[str, Any]] = (),
) -> tuple[plt.Figure, tuple[Path, Path]]:
    """Draw arrival/queue/throughput/rolling-p95 burst dynamics."""

    configure_style()
    rows = _filter(timeseries_summary, filters)
    if not rows:
        raise ValueError("Fig. 11 has no rows after filtering")
    patterns = {str(row.get("burst_pattern", "")) for row in rows}
    if len(patterns) != 1:
        raise ValueError("Fig. 11 requires exactly one burst pattern per figure")
    algorithms = _algorithms(rows)
    panels = [
        ("arrival_rps", "Arrival Rate (requests/s)", "(a) Request Arrivals"),
        ("queue_total", "Queued + Running Tasks", "(b) Queue Backlog"),
        ("throughput_rps", "Throughput (requests/s)", "(c) Completions"),
        ("rolling_p95_ms", "Rolling p95 Latency (ms)", "(d) Tail Latency"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True)
    spans = _active_spans(rows)
    for ax, (metric, ylabel, panel) in zip(axes.flatten(), panels):
        for start, end in spans:
            ax.axvspan(start, end, color="#bdbdbd", alpha=0.20, linewidth=0)
        for algorithm in algorithms:
            selected = sorted(
                (
                    row
                    for row in rows
                    if str(row.get("metric", "")) == metric
                    and str(row.get("algorithm", "")) == algorithm
                ),
                key=lambda row: _number(row.get("time_relative_ms")),
            )
            if not selected:
                continue
            x = np.asarray([_number(row.get("time_relative_ms")) for row in selected])
            y = np.asarray([_number(row.get("mean")) for row in selected])
            low = np.asarray([_number(row.get("ci_low")) for row in selected])
            high = np.asarray([_number(row.get("ci_high")) for row in selected])
            color = algorithm_color(algorithm)
            ax.plot(x, y, color=color, linewidth=1.6, label=algorithm)
            band = np.isfinite(x) & np.isfinite(low) & np.isfinite(high)
            if np.any(band):
                ax.fill_between(
                    x[band], low[band], high[band], color=color, alpha=0.10, linewidth=0
                )
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_xlabel("Time Relative to First Burst (ms)", fontweight="bold")
        _panel_label(ax, panel)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    recovery_rows = _filter(run_metrics, filters)
    if recovery_rows:
        statuses = [str(row.get("recovery_status", "")) for row in recovery_rows]
        recovered = sum(status == "recovered" for status in statuses)
        censored = sum(status == "right_censored" for status in statuses)
        unavailable = len(statuses) - recovered - censored
        axes[0, 1].text(
            0.98,
            0.96,
            f"joint queue+p95 recovery: {recovered}/{len(statuses)}\n"
            f"right-censored: {censored}; NA: {unavailable}",
            transform=axes[0, 1].transAxes,
            ha="right",
            va="top",
            fontsize=10,
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
        )
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
    fig.subplots_adjust(bottom=0.14, hspace=0.32, wspace=0.20)
    return fig, _save(fig, output_prefix)


def _summary_lookup(
    rows: Sequence[Mapping[str, Any]],
    metric: str,
    selectors: Mapping[str, Any],
) -> tuple[float, float, float]:
    matches = [
        row
        for row in rows
        if str(row.get("metric", "")) == metric
        and all(str(row.get(key, "")) == str(value) for key, value in selectors.items())
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate summary cells for {metric}, {dict(selectors)}")
    if not matches:
        return math.nan, 0.0, 0.0
    mean = _number(matches[0].get("mean"))
    low = _number(matches[0].get("bca_low"))
    high = _number(matches[0].get("bca_high"))
    return (
        mean,
        max(0.0, mean - low) if math.isfinite(low) else 0.0,
        max(0.0, high - mean) if math.isfinite(high) else 0.0,
    )


def _grouped_bars(
    ax: plt.Axes,
    rows: Sequence[Mapping[str, Any]],
    *,
    metric: str,
    categories: Sequence[str],
    category_column: str,
    algorithms: Sequence[str],
    comparisons: Sequence[Mapping[str, Any]] = (),
    base_selectors: Mapping[str, Any] | None = None,
) -> None:
    x = np.arange(len(categories), dtype=float)
    width = 0.82 / max(1, len(algorithms))
    for index, algorithm in enumerate(algorithms):
        positions = x + (index - len(algorithms) / 2.0 + 0.5) * width
        values: list[float] = []
        lower: list[float] = []
        upper: list[float] = []
        for category in categories:
            value, down, up = _summary_lookup(
                rows,
                metric,
                {"algorithm": algorithm, category_column: category},
            )
            values.append(value)
            lower.append(down)
            upper.append(up)
        ax.bar(
            positions,
            values,
            width,
            color=algorithm_color(algorithm),
            alpha=0.88,
            label=algorithm,
            yerr=np.asarray([lower, upper]),
            capsize=2.0,
            error_kw={"elinewidth": 0.8, "ecolor": "#222222", "capthick": 0.8},
        )
        for position, category, value, up in zip(positions, categories, values, upper):
            if not math.isfinite(value):
                ax.text(
                    position,
                    0.02,
                    "NA",
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="bottom",
                    rotation=90,
                    fontsize=7,
                    color="#666666",
                )
                continue
            marker = _comparison_star(
                comparisons,
                metric=metric,
                comparator=algorithm,
                selectors={
                    **(base_selectors or {}),
                    category_column: category,
                },
            )
            if marker:
                ax.text(
                    position,
                    value + up + max(abs(value), 1.0) * 0.025,
                    marker,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    clip_on=True,
                )
    ax.set_xticks(x)
    ax.margins(y=0.12)


def plot_fig12_burst(
    burst_summary: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    filters: Mapping[str, Any] | None = None,
) -> tuple[plt.Figure, tuple[Path, Path]]:
    """Draw all predeclared E3 burst-resilience bar endpoints."""

    configure_style()
    rows = _filter(burst_summary, filters)
    comparison_rows = _filter(comparisons, filters)
    if not rows:
        raise ValueError("Fig. 12 burst panel has no E3 summary rows after filtering")
    patterns = sorted({str(row.get("burst_pattern", "")) for row in rows})
    if len(patterns) != 1:
        raise ValueError("Fig. 12 burst panel requires exactly one burst pattern")
    algorithms = _algorithms(rows)
    panels = (
        ("peak_queue", "Peak Queue (tasks)", "(a) Peak Queue"),
        (
            "restricted_recovery_time_ms",
            "Time (ms)",
            "(b) Joint Queue+p95 Recovery/Censor Time",
        ),
        ("recovery_observed", "Fraction of Runs", "(c) Recovered by 4000 ms"),
        ("admission_drop", "Requests", "(d) Admission Drops"),
        ("admission_reject", "Requests", "(e) Admission Rejections"),
        ("timeout", "Requests", "(f) Timeouts"),
        ("latency_p95_ms", "Latency (ms)", "(g) Request p95"),
        ("latency_p99_ms", "Latency (ms)", "(h) Request p99"),
    )
    fig, axes = plt.subplots(2, 4, figsize=(22, 10))
    for ax, (metric, ylabel, panel) in zip(axes.flatten(), panels):
        _grouped_bars(
            ax,
            rows,
            metric=metric,
            categories=patterns,
            category_column="burst_pattern",
            algorithms=algorithms,
            comparisons=comparison_rows,
        )
        ax.set_xticklabels(
            [BURST_LABELS.get(patterns[0], patterns[0].replace("_", "\n"))],
            fontsize=9,
        )
        ax.set_ylabel(ylabel, fontweight="bold")
        if metric == "recovery_observed":
            ax.set_ylim(0.0, 1.05)
        elif metric in {"admission_drop", "admission_reject", "timeout"}:
            ax.set_ylim(bottom=0.0)
        _panel_label(ax, panel, y=-0.28)
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
    fig.subplots_adjust(bottom=0.15, hspace=0.48, wspace=0.28)
    return fig, _save(fig, output_prefix)


def plot_fig12(
    qos_summary: Sequence[Mapping[str, Any]],
    fairness_summary: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    filters: Mapping[str, Any] | None = None,
    qos_comparisons: Sequence[Mapping[str, Any]] = (),
    fairness_comparisons: Sequence[Mapping[str, Any]] = (),
) -> tuple[plt.Figure, tuple[Path, Path]]:
    """Draw three-class QoS performance, violations, and fairness."""

    configure_style()
    qos_rows = _filter(qos_summary, filters)
    fairness_rows = _filter(fairness_summary, filters)
    if not qos_rows:
        raise ValueError("Fig. 12 has no QoS rows after filtering")
    algorithms = _algorithms([*qos_rows, *fairness_rows])
    classes = [
        qos
        for qos in QOS_ORDER
        if any(str(row.get("qos_class", "")) == qos for row in qos_rows)
    ]
    fig, axes = plt.subplots(2, 3, figsize=(20, 10))
    panels = [
        (
            axes[0, 0],
            "stage_latency_p95_ms",
            "Function-stage p95 Latency (ms)",
            "(a) Tail Latency by QoS Class",
        ),
        (
            axes[0, 1],
            "throughput_rps",
            "Completed Invocations/s",
            "(b) Throughput by QoS Class",
        ),
        (
            axes[0, 2],
            "direct_cost_mean",
            "Simulator Cost / Completed Function",
            "(c) Cost by QoS Class",
        ),
        (
            axes[1, 0],
            "completion_ratio",
            "Completed / Arrived Functions",
            "(d) Completion Ratio",
        ),
        (
            axes[1, 1],
            "sla_violation_rate",
            "SLA Violation Rate",
            "(e) SLA Violations",
        ),
    ]
    for ax, metric, ylabel, panel in panels:
        _grouped_bars(
            ax,
            qos_rows,
            metric=metric,
            categories=classes,
            category_column="qos_class",
            algorithms=algorithms,
            comparisons=qos_comparisons,
        )
        ax.set_xticklabels([QOS_LABELS.get(value, value.title()) for value in classes])
        ax.tick_params(axis="x", rotation=8)
        ax.set_ylabel(ylabel, fontweight="bold")
        _panel_label(ax, panel, y=-0.32)
        if metric in {"sla_violation_rate", "completion_ratio"}:
            ax.set_ylim(0.0, 1.05)

    fairness_categories = ["jain_satisfaction", "worst10_satisfaction"]
    # Fairness uses metric names as categories rather than a metric column shared
    # across categories, so draw the same grouped layout explicitly.
    ax = axes[1, 2]
    x = np.arange(2, dtype=float)
    width = 0.82 / max(1, len(algorithms))
    for index, algorithm in enumerate(algorithms):
        positions = x + (index - len(algorithms) / 2.0 + 0.5) * width
        values, lower, upper = [], [], []
        for metric in fairness_categories:
            value, down, up = _summary_lookup(
                fairness_rows, metric, {"algorithm": algorithm}
            )
            values.append(value)
            lower.append(down)
            upper.append(up)
        ax.bar(
            positions,
            values,
            width,
            color=algorithm_color(algorithm),
            alpha=0.88,
            label=algorithm,
            yerr=np.asarray([lower, upper]),
            capsize=2.0,
            error_kw={"elinewidth": 0.8, "ecolor": "#222222", "capthick": 0.8},
        )
        for position, value in zip(positions, values):
            if not math.isfinite(value):
                ax.text(
                    position,
                    0.02,
                    "NA",
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="bottom",
                    rotation=90,
                    fontsize=7,
                    color="#666666",
                )
        for position, metric, value, up in zip(
            positions, fairness_categories, values, upper
        ):
            if not math.isfinite(value):
                continue
            marker = _comparison_star(
                fairness_comparisons,
                metric=metric,
                comparator=algorithm,
                selectors={},
            )
            if marker:
                ax.text(
                    position,
                    value + up + 0.02,
                    marker,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    clip_on=True,
                )
    ax.set_xticks(x)
    ax.set_xticklabels(["Jain Index", "Worst 10% Satisfaction"])
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Normalized Satisfaction", fontweight="bold")
    _panel_label(ax, "(f) Cross-class Fairness", y=-0.22)

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
    fig.subplots_adjust(bottom=0.16, hspace=0.56, wspace=0.24)
    return fig, _save(fig, output_prefix)


def _diagnostic_bars(
    ax: plt.Axes,
    rows: Sequence[Mapping[str, Any]],
    metrics: Sequence[tuple[str, str]],
    algorithms: Sequence[str],
    *,
    comparisons: Sequence[Mapping[str, Any]] = (),
    selectors: Mapping[str, Any] | None = None,
) -> None:
    x = np.arange(len(metrics), dtype=float)
    width = 0.82 / max(1, len(algorithms))
    for index, algorithm in enumerate(algorithms):
        positions = x + (index - len(algorithms) / 2.0 + 0.5) * width
        values, lower, upper = [], [], []
        for metric, _ in metrics:
            value, down, up = _summary_lookup(rows, metric, {"algorithm": algorithm})
            values.append(value)
            lower.append(down)
            upper.append(up)
        ax.bar(
            positions,
            values,
            width,
            color=algorithm_color(algorithm),
            alpha=0.88,
            label=algorithm,
            yerr=np.asarray([lower, upper]),
            capsize=2.0,
            error_kw={"elinewidth": 0.8, "ecolor": "#222222", "capthick": 0.8},
        )
        for position, (metric, _), value, up in zip(positions, metrics, values, upper):
            if not math.isfinite(value):
                ax.text(
                    position,
                    0.02,
                    "NA",
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="bottom",
                    rotation=90,
                    fontsize=7,
                    color="#666666",
                )
                continue
            marker = _comparison_star(
                comparisons,
                metric=metric,
                comparator=algorithm,
                selectors=selectors or {},
            )
            if marker:
                ax.text(
                    position,
                    value + up + max(abs(value), 1.0) * 0.025,
                    marker,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    clip_on=True,
                )
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in metrics], rotation=8)
    ax.margins(y=0.12)


def plot_fig13(
    feature_summary: Sequence[Mapping[str, Any]],
    diagnostic_summary: Sequence[Mapping[str, Any]],
    output_prefix: str | Path,
    *,
    differentiation_summary: Sequence[Mapping[str, Any]] = (),
    feature_filters: Mapping[str, Any] | None = None,
    diagnostic_filters: Mapping[str, Any] | None = None,
    diagnostic_comparisons: Sequence[Mapping[str, Any]] = (),
    exact_poa_summary: Sequence[Mapping[str, Any]] = (),
) -> tuple[plt.Figure, tuple[Path, Path]]:
    """Draw validation diagnostics and, optionally, constructed exact PoA.

    The exact pure-PoA panels use constructed states as their sampling unit and
    are intentionally separate from the large-scale empirical welfare-gap panel.
    """

    configure_style()
    feature_rows = [
        row
        for row in _filter(
            [*feature_summary, *differentiation_summary], feature_filters
        )
        if _truthy(row.get("primary_pair"))
    ]
    diagnostics = _filter(diagnostic_summary, diagnostic_filters)
    comparison_rows = _filter(diagnostic_comparisons, diagnostic_filters)
    if not feature_rows:
        raise ValueError("Fig. 13 requires primary feature-correlation rows")
    if not diagnostics:
        raise ValueError("Fig. 13 has no diagnostic rows after filtering")
    algorithms = _algorithms(diagnostics)
    exact_rows = sorted(
        exact_poa_summary,
        key=lambda row: _number(row.get("players")),
    )
    if exact_rows:
        # Twelve populated panels fit naturally in a compact 3 x 4 grid.
        fig, axes = plt.subplots(3, 4, figsize=(22, 15))
        flat_axes = list(axes.flatten())
    else:
        # E1/E8/E9 validation has ten panels.  Let the two bottom panels span
        # two columns apiece instead of reserving two empty subplot cells.
        fig = plt.figure(figsize=(22, 15))
        grid = fig.add_gridspec(3, 4)
        flat_axes = [
            fig.add_subplot(grid[row, column])
            for row in range(2)
            for column in range(4)
        ]
        flat_axes.extend(
            [
                fig.add_subplot(grid[2, :2]),
                fig.add_subplot(grid[2, 2:]),
            ]
        )

    # (a) Run-level Spearman forest plot.
    ax = flat_axes[0]
    labels: list[str] = []
    y = np.arange(len(feature_rows), dtype=float)
    for index, row in enumerate(feature_rows):
        estimate = _number(row.get("mean_rho"))
        low = _number(row.get("bca_low"))
        high = _number(row.get("bca_high"))
        down = max(0.0, estimate - low) if math.isfinite(low) else 0.0
        up = max(0.0, high - estimate) if math.isfinite(high) else 0.0
        if math.isfinite(estimate):
            ax.errorbar(
                estimate,
                index,
                xerr=np.asarray([[down], [up]]),
                fmt="o",
                color="#2ca02c",
                ecolor="#333333",
                capsize=3,
            )
            marker = "*" if _truthy(row.get("reject_holm")) else ""
            if marker:
                ax.text(estimate + 0.04 * (1 if estimate >= 0 else -1), index, marker)
        else:
            ax.text(0.0, index, "NA", ha="center", va="center", fontsize=8)
        feature = str(row.get("feature", ""))
        outcome = str(row.get("outcome", ""))
        labels.append(
            f"{FEATURE_LABELS.get(feature, feature)} to "
            f"{OUTCOME_LABELS.get(outcome, outcome)}"
        )
    ax.axvline(0.0, color="#777777", linewidth=1.0, linestyle="--")
    ax.set_xlim(-1.05, 1.05)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel(r"Mean Within-run Spearman $\rho$", fontweight="bold")
    _panel_label(ax, "(a) Feature Identifiability")

    selectors = {
        key: value
        for key, value in (diagnostic_filters or {}).items()
        if value is not None
    }

    # (b)--(j) solver behavior, process cost, and offline-reference evidence.
    panel_specs = (
        (
            1,
            [("inner_rounds_mean", "Inner"), ("outer_rounds_mean", "Outer")],
            "Rounds per Scheduling Window",
            "(b) Convergence Rounds",
            None,
        ),
        (
            2,
            [
                ("inner_limit_hit_rate", "Inner limit"),
                ("outer_limit_hit_rate", "Outer limit"),
                ("oscillation_window_rate", "Oscillation"),
                ("nonconvergence_rate", "Non-converged"),
            ],
            "Fraction of Solver Windows",
            "(c) Stability Diagnostics",
            (0.0, 1.05),
        ),
        (
            3,
            [
                ("placement_policy_wall_mean_us", "Placement wall"),
                ("placement_policy_cpu_mean_us", "Placement CPU"),
                ("solve_mean_us", "NSE solve"),
            ],
            r"Time ($\mu$s)",
            "(d) Online Scheduling Cost",
            (0.0, None),
        ),
        (
            4,
            [
                ("process_peak_rss_mib", "Online process"),
                ("offline_build_peak_rss_mib", "Offline build"),
            ],
            "Peak Process-tree RSS (MiB)",
            "(e) Online/Offline Peak Memory",
            (0.0, None),
        ),
        (
            5,
            [
                ("offline_build_wall_ms", "Wall"),
                ("offline_build_cpu_ms", "CPU"),
            ],
            "Offline Build Time (ms)",
            "(f) Offline Reference Build",
            (0.0, None),
        ),
        (
            6,
            [("reference_table_bytes", "Table")],
            "Reference Table Size (bytes)",
            "(g) Offline Table Footprint",
            (0.0, None),
        ),
        (
            7,
            [
                ("reference_table_load_us", "Load wall"),
                ("reference_table_load_thread_cpu_us", "Load CPU"),
                ("reference_lookup_mean_us", "Lookup/window"),
            ],
            r"Replay Time ($\mu$s)",
            "(h) Online Reference Access",
            (0.0, None),
        ),
        (
            8,
            [
                ("reference_missing_ratio", "Missing"),
                ("reference_zero_ratio", "Zero"),
                ("reference_negative_ratio", "Negative"),
                ("reference_unavailable_ratio", "Unavailable"),
                ("reference_persist_failure_ratio", "Persist\nfailure"),
                ("reference_offline_required_ok", "Offline-required\nOK"),
            ],
            "Fraction / Run Indicator",
            "(i) Reference Status",
            (0.0, 1.05),
        ),
        (
            9,
            [
                ("welfare_gap_mean", "Gap mean"),
                ("welfare_gap_p95", "Gap p95"),
                ("welfare_gap_applicability", "Applicable"),
                ("reference_cache_hit_rate", "Cache hit"),
            ],
            "Fraction",
            "(j) Welfare/Reference Coverage",
            (0.0, 1.05),
        ),
    )
    nse_only_panels = {1, 2, 5, 6, 7, 8, 9}
    for axis_index, metrics, ylabel, panel, limits in panel_specs:
        axis = flat_axes[axis_index]
        panel_algorithms = (
            ["NSESche"]
            if axis_index in nse_only_panels and "NSESche" in algorithms
            else algorithms
        )
        _diagnostic_bars(
            axis,
            diagnostics,
            metrics,
            panel_algorithms,
            comparisons=comparison_rows,
            selectors=selectors,
        )
        axis.set_ylabel(ylabel, fontweight="bold")
        if limits is not None:
            axis.set_ylim(bottom=limits[0], top=limits[1])
        if axis_index == 6:
            axis.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        _panel_label(axis, panel)

    if exact_rows:
        player_counts = [_number(row.get("players")) for row in exact_rows]
        if any(not math.isfinite(value) for value in player_counts):
            raise ValueError("exact PoA summary contains an invalid player count")
        if len(set(player_counts)) != len(player_counts):
            raise ValueError("exact PoA summary contains duplicate player counts")

        # (k) is the exact pure-strategy ratio from complete enumeration of each
        # constructed state.  It is not a trace-run CI and is never overlaid on
        # the empirical simulated-annealing gap in panel (j).
        ax = flat_axes[10]
        for index, row in enumerate(exact_rows):
            estimate = _number(row.get("exact_poa_median"))
            low = _number(row.get("exact_poa_bca_low"))
            high = _number(row.get("exact_poa_bca_high"))
            if not math.isfinite(estimate):
                ax.text(index, 1.0, "NA", ha="center", va="bottom", fontweight="bold")
                continue
            down = max(0.0, estimate - low) if math.isfinite(low) else 0.0
            up = max(0.0, high - estimate) if math.isfinite(high) else 0.0
            ax.errorbar(
                index,
                estimate,
                yerr=np.asarray([[down], [up]]),
                fmt="o",
                markersize=7,
                color="#2ca02c",
                ecolor="#222222",
                capsize=4,
                linewidth=1.2,
            )
        ax.axhline(1.0, color="#777777", linewidth=1.0, linestyle="--")
        ax.set_xticks(np.arange(len(exact_rows)))
        ax.set_xticklabels([f"{int(value)}" for value in player_counts])
        ax.set_xlabel("Players per Constructed Game", fontweight="bold")
        ax.set_ylabel(r"Exact Pure PoA  $W^*/W_{NE}^{worst}$", fontweight="bold")
        ax.set_ylim(bottom=min(0.95, ax.get_ylim()[0]))
        _panel_label(ax, "(k) Constructed-state Exact Pure PoA")

        ax = flat_axes[11]
        ratios = [_number(row.get("poa_applicable_ratio")) for row in exact_rows]
        positions = np.arange(len(exact_rows))
        bars = ax.bar(
            positions,
            [value if math.isfinite(value) else 0.0 for value in ratios],
            width=0.62,
            color=shaded("#2ca02c", 0.20),
            edgecolor="#2ca02c",
        )
        for bar, row, ratio in zip(bars, exact_rows, ratios):
            applicable = _number(row.get("poa_applicable_states"))
            total = _number(row.get("total_states"))
            if math.isfinite(ratio):
                count = (
                    f"{int(applicable)}/{int(total)}"
                    if math.isfinite(applicable) and math.isfinite(total)
                    else f"{ratio:.2f}"
                )
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    min(1.02, ratio + 0.025),
                    count,
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )
            else:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    0.02,
                    "NA",
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                )
        ax.set_xticks(positions)
        ax.set_xticklabels([f"{int(value)}" for value in player_counts])
        ax.set_xlabel("Players per Constructed Game", fontweight="bold")
        ax.set_ylabel("PoA-applicable Fraction of States", fontweight="bold")
        ax.set_ylim(0.0, 1.08)
        _panel_label(ax, "(l) Constructed-state Applicability")
    handles, legend_labels = flat_axes[3].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            legend_labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.995),
            ncol=min(5, len(legend_labels)),
            frameon=False,
        )
    fig.text(
        0.5,
        0.012,
        "Error bars: run-level 95% BCa CI; stars: Holm-adjusted paired permutation test vs NSESche; NA: unavailable/not applicable.",
        ha="center",
        va="bottom",
        fontsize=10,
    )
    fig.tight_layout(rect=(0.0, 0.075, 1.0, 0.91), pad=2.0)
    fig.subplots_adjust(bottom=0.11, top=0.89, hspace=0.48, wspace=0.30)
    return fig, _save(fig, output_prefix)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure", choices=("11", "12", "13", "all"), default="all")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--e3-timeseries-summary")
    parser.add_argument("--e3-run-metrics")
    parser.add_argument("--e3-run-summary")
    parser.add_argument("--e3-comparisons")
    parser.add_argument("--e4-qos-summary")
    parser.add_argument("--e4-fairness-summary")
    parser.add_argument("--e4-qos-comparisons")
    parser.add_argument("--e4-fairness-comparisons")
    parser.add_argument("--e8-feature-summary")
    parser.add_argument("--e8-differentiation-summary")
    parser.add_argument("--e9-diagnostic-summary")
    parser.add_argument("--e9-comparisons")
    parser.add_argument("--e9-exact-poa-summary")
    parser.add_argument("--burst-pattern", default="spike5x50ms")
    parser.add_argument("--diagnostic-experiment", default="E1")
    parser.add_argument("--diagnostic-load", default="high")
    parser.add_argument("--diagnostic-node-count", default="20")
    parser.add_argument("--diagnostic-topology", default="heterogeneous")
    args = parser.parse_args(argv)
    requested = {"11", "12", "13"} if args.figure == "all" else {args.figure}
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    if "11" in requested:
        fig, paths = plot_fig11(
            read_rows(args.e3_timeseries_summary),
            output / "fig11_burst_dynamics",
            filters={"burst_pattern": args.burst_pattern},
            run_metrics=read_rows(args.e3_run_metrics),
        )
        generated.extend(paths)
        plt.close(fig)
    if "12" in requested:
        burst_rows = read_rows(args.e3_run_summary)
        burst_comparisons = read_rows(args.e3_comparisons)
        if not burst_rows:
            raise ValueError("Fig. 12 requires --e3-run-summary")
        if not burst_comparisons:
            raise ValueError("Fig. 12 requires --e3-comparisons")
        patterns = sorted({str(row.get("burst_pattern", "")) for row in burst_rows})
        for pattern in patterns:
            if not pattern:
                continue
            safe_pattern = "".join(
                character if character.isalnum() else "_" for character in pattern
            ).strip("_")
            fig, paths = plot_fig12_burst(
                burst_rows,
                output / f"fig12a_burst_resilience_{safe_pattern}",
                comparisons=burst_comparisons,
                filters={"burst_pattern": pattern},
            )
            generated.extend(paths)
            plt.close(fig)
        qos_rows = read_rows(args.e4_qos_summary)
        fairness_rows = read_rows(args.e4_fairness_summary)
        qos_comparisons = read_rows(args.e4_qos_comparisons)
        fairness_comparisons = read_rows(args.e4_fairness_comparisons)
        if not qos_comparisons or not fairness_comparisons:
            raise ValueError("Fig. 12 requires E4 QoS and fairness comparison tables")
        fig, paths = plot_fig12(
            qos_rows,
            fairness_rows,
            output / "fig12b_qos_sla_fairness",
            qos_comparisons=qos_comparisons,
            fairness_comparisons=fairness_comparisons,
        )
        generated.extend(paths)
        plt.close(fig)
    if "13" in requested:
        diagnostic_comparisons = read_rows(args.e9_comparisons)
        if not diagnostic_comparisons:
            raise ValueError("Fig. 13 requires --e9-comparisons")
        fig, paths = plot_fig13(
            read_rows(args.e8_feature_summary),
            read_rows(args.e9_diagnostic_summary),
            output / "fig13_validation_diagnostics",
            differentiation_summary=read_rows(args.e8_differentiation_summary),
            feature_filters={
                "experiment_id": args.diagnostic_experiment,
                "load": args.diagnostic_load,
                "node_count": args.diagnostic_node_count,
                "topology": args.diagnostic_topology,
            },
            diagnostic_filters={
                "experiment_id": args.diagnostic_experiment,
                "load": args.diagnostic_load,
                "node_count": args.diagnostic_node_count,
                "topology": args.diagnostic_topology,
            },
            diagnostic_comparisons=diagnostic_comparisons,
            exact_poa_summary=read_rows(args.e9_exact_poa_summary),
        )
        generated.extend(paths)
        plt.close(fig)
    for path in generated:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
