"""Plot the frozen NSESche-only homogeneous low-load scaling bundle."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


DEFAULT_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_homogeneous_low_resource_scaling_result_v1.json"
)
DEFAULT_OUTPUT = Path("tmp/nse_homogeneous_low_resource_scaling_freeze_v1")
NODE_COUNTS = (20, 100, 500)
PANELS = (
    ("throughput_requests_per_ms", "Throughput (10³ requests/s)", "a"),
    ("qpr", "QPR", "b"),
    ("drained_cohort_mean_latency_ms", "Mean latency (ms)", "c"),
    ("cost_per_completed_request", "Cost / completed request (sim. units)", "d"),
)
BLUE = "#0072B2"
GRAY = "#6C757D"
FIGURE_CREATOR = "NSE reviewer-v3 resource-scaling pipeline"


def finite(value: object) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def validate_result(path: Path) -> dict[str, Any]:
    result = read_json(path)
    claimed = result.get("result_hash")
    unhashed = dict(result)
    unhashed.pop("result_hash", None)
    if claimed != object_hash(unhashed):
        raise RuntimeError("resource-scaling result self-hash mismatch")
    if (
        result.get("status") != "formal_nse_resource_scaling_freeze_pass"
        or result.get("resource_scaling_gate_passed") is not True
        or result.get("run_count") != 60
        or result.get("seed_count_per_cell") != 20
    ):
        raise RuntimeError("resource-scaling result is not frozen/publishable")
    raw_path = Path(result["raw_run_table_path"])
    if file_hash(raw_path) != result["raw_run_table_file_sha256"]:
        raise RuntimeError("raw scaling table hash mismatch")
    return result


def read_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    with Path(result["raw_run_table_path"]).open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 60:
        raise RuntimeError("raw scaling table does not contain 60 rows")
    return rows


def main() -> None:
    args = parse_args()
    result = validate_result(args.result)
    rows = read_rows(result)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_dir / "fig10_nse_resource_scaling"
    outputs = [stem.with_suffix(suffix) for suffix in (".pdf", ".png", ".svg")]
    manifest_path = args.output_dir / "figure_manifest.json"
    alt_path = args.output_dir / "alt_text.md"
    existing = [path for path in [*outputs, manifest_path, alt_path] if path.exists()]
    if existing and not args.force:
        raise RuntimeError(f"refusing to overwrite existing outputs: {existing}")

    grouped: dict[int, list[dict[str, Any]]] = {
        node_count: [row for row in rows if int(row["node_count"]) == node_count]
        for node_count in NODE_COUNTS
    }
    if any(len(grouped[node_count]) != 20 for node_count in NODE_COUNTS):
        raise RuntimeError("each node-count cell must contain exactly 20 runs")

    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "axes.titlesize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.4,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(178 / 25.4, 126 / 25.4),
    )
    fig.subplots_adjust(
        left=0.11, right=0.985, bottom=0.14, top=0.84, wspace=0.30, hspace=0.38
    )
    x = np.arange(len(NODE_COUNTS), dtype=float)
    offsets = np.linspace(-0.075, 0.075, 20)
    cell_summaries = result["cell_summaries"]

    for panel_index, (axis, (metric, ylabel, panel_label)) in enumerate(
        zip(axes.flat, PANELS)
    ):
        for node_index, node_count in enumerate(NODE_COUNTS):
            raw = np.array(
                [float(row[metric]) for row in grouped[node_count]], dtype=float
            )
            if not np.isfinite(raw).all():
                raise RuntimeError(f"nonfinite raw values for {metric}/n{node_count}")
            axis.scatter(
                node_index + offsets,
                raw,
                s=10,
                marker="o",
                facecolors="none",
                edgecolors=GRAY,
                linewidths=0.55,
                alpha=0.55,
                zorder=2,
            )
        means = np.array(
            [
                cell_summaries[str(node)]["metrics"][metric]["mean"]
                for node in NODE_COUNTS
            ],
            dtype=float,
        )
        lows = np.array(
            [
                cell_summaries[str(node)]["metrics"][metric]["bca_95_ci"]["low"]
                for node in NODE_COUNTS
            ],
            dtype=float,
        )
        highs = np.array(
            [
                cell_summaries[str(node)]["metrics"][metric]["bca_95_ci"]["high"]
                for node in NODE_COUNTS
            ],
            dtype=float,
        )
        axis.errorbar(
            x,
            means,
            yerr=np.vstack((means - lows, highs - means)),
            color=BLUE,
            marker="D",
            markersize=5.2,
            markerfacecolor="white",
            markeredgewidth=1.2,
            capsize=3,
            label="Mean ± BCa 95% CI",
            zorder=4,
        )
        axis.set(
            xticks=x,
            xticklabels=[str(node) for node in NODE_COUNTS],
            ylabel=ylabel,
        )
        if panel_index >= 2:
            axis.set_xlabel("Homogeneous nodes")
        axis.set_ylim(bottom=0.0)
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.55, alpha=0.8)
        axis.grid(axis="x", visible=False)
        axis.spines[["top", "right"]].set_visible(False)
        axis.text(
            0.015,
            0.965,
            panel_label,
            transform=axis.transAxes,
            fontweight="bold",
            fontsize=9.5,
            va="top",
        )

    throughput_axis = axes[0, 0]
    comparisons = result["paired_scaling_comparisons"]
    for center, key in ((0.5, "n20_to_n100"), (1.5, "n100_to_n500")):
        efficiency = comparisons[key]["weak_scaling_efficiency_from_ratio_of_means"]
        throughput_axis.text(
            center,
            0.91,
            f"Efficiency {efficiency:.1%}",
            transform=throughput_axis.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=7.2,
            color="#333333",
        )

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor="none",
            markeredgecolor=GRAY,
            markersize=4.5,
            label="All E01–E20 runs",
        ),
        Line2D(
            [0],
            [0],
            color=BLUE,
            marker="D",
            markerfacecolor="white",
            markersize=4.5,
            label="Mean ± BCa 95% CI",
        ),
    ]
    labels = [handle.get_label() for handle in handles]
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.91),
        ncol=2,
        frameon=False,
    )
    fig.suptitle(
        "NSESche proportional-load resource scaling",
        fontsize=10,
        fontweight="semibold",
        y=0.975,
    )
    fig.text(
        0.5,
        0.025,
        "n = 20 paired environment seeds per node count; error bars are deterministic 10,000-resample BCa 95% CIs.",
        ha="center",
        va="bottom",
        fontsize=6.8,
    )
    mpl.rcParams["svg.hashsalt"] = "nse-resource-scaling-v1"
    for output in outputs:
        if output.suffix == ".png":
            fig.savefig(
                output,
                dpi=600,
                bbox_inches=None,
                transparent=False,
                metadata={"Software": FIGURE_CREATOR},
            )
        elif output.suffix == ".pdf":
            fig.savefig(
                output,
                bbox_inches=None,
                transparent=False,
                metadata={
                    "Creator": FIGURE_CREATOR,
                    "Producer": FIGURE_CREATOR,
                    "CreationDate": None,
                    "ModDate": None,
                },
            )
        else:
            fig.savefig(
                output,
                bbox_inches=None,
                transparent=False,
                metadata={"Creator": FIGURE_CREATOR, "Date": None},
            )
    plt.close(fig)

    alt_text = (
        "Four-panel line-and-point figure showing NSESche at 20, 100, and 500 "
        "homogeneous nodes under proportional 1x, 5x, and 25x low-load "
        "replication. Throughput rises from 1.439 to 5.887 and 21.114 thousand "
        "requests per second, while QPR rises from 0.0410 to 0.1261 and 0.3533. "
        "Mean latency increases from 125.5 to 172.6 and 199.1 milliseconds, and "
        "cost per completed request is approximately stable from 20 to 100 nodes "
        "before increasing at 500 nodes. Open gray circles show all 20 paired "
        "seed observations per cell; blue diamonds and error bars show means and "
        "BCa 95 percent confidence intervals."
    )
    with alt_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(alt_text + "\n")
    manifest: dict[str, Any] = {
        "schema_version": "NSE_RESOURCE_SCALING_FIGURE_MANIFEST_V1",
        "created_from_result": str(args.result),
        "result_file_sha256": file_hash(args.result),
        "result_hash": result["result_hash"],
        "raw_data": result["raw_run_table_path"],
        "raw_data_file_sha256": result["raw_run_table_file_sha256"],
        "transformations": [
            "no run filtering",
            "arithmetic mean per node-count cell",
            "deterministic 10000-resample BCa 95% confidence intervals",
            "fixed symmetric horizontal offsets for raw points",
        ],
        "replicate_unit": "paired environment seed E01-E20",
        "sample_size_per_cell": 20,
        "missing_values": 0,
        "excluded_values": 0,
        "publisher_profile": "provisional general manuscript figure; exact journal requirements pending",
        "physical_size_mm": {"width": 178, "height": 126},
        "outputs": [
            {
                "path": str(path),
                "file_sha256": file_hash(path),
                "bytes": path.stat().st_size,
            }
            for path in outputs
        ],
        "alt_text_path": str(alt_path),
        "alt_text_file_sha256": file_hash(alt_path),
    }
    manifest["manifest_hash"] = object_hash(manifest)
    write_json_atomic(manifest_path, manifest)
    print(
        json.dumps(
            {
                "outputs": [str(path) for path in outputs],
                "figure_manifest": str(manifest_path),
                "manifest_hash": manifest["manifest_hash"],
                "alt_text": str(alt_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
