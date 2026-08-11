"""Shared visual constants matching the submitted paper's figures."""

from __future__ import annotations

from matplotlib import colors as mcolors
from matplotlib import rcParams


ALGORITHM_ORDER = [
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
]

# Tableau ordering used by the submitted Fig. 6/9.  NSESche deliberately keeps
# the submitted green rather than being recolored during the revision.
ALGORITHM_COLORS = {
    "Greedy": "#1f77b4",
    "Random": "#ff7f0e",
    "Hash": "#2ca02c",
    "Load Balance": "#d62728",
    "FaaSRank": "#9467bd",
    "OCS": "#8c564b",
    "Hiku": "#e377c2",
    "Jiagu": "#7f7f7f",
    "Orion": "#bcbd22",
    "NSESche": "#2ca02c",
}

LOAD_ORDER = ["low", "middle", "high"]
LOAD_LABELS = {"low": "Low", "middle": "Middle", "high": "High"}

ABLATION_ORDER = [
    "w/o Heterogeneity Modeling",
    "w/o Externality Modeling",
    "w/o Congestion Pricing",
    "w/o Nash–Social Coordination",
    "NSESche",
]

# These are the four samples selected by ``Set3(i/4)`` in the submitted script.
ABLATION_COLORS = {
    "w/o Heterogeneity Modeling": "#8dd3c7",
    "w/o Externality Modeling": "#80b1d3",
    "w/o Congestion Pricing": "#fb8072",
    "w/o Nash–Social Coordination": "#b3de69",
    "NSESche": "#bc80bd",
}


def configure_style() -> None:
    rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 12,
            "axes.labelsize": 15,
            "axes.titlesize": 15,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "legend.fontsize": 11,
            "figure.titlesize": 16,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def ordered_present(values: set[str], preferred: list[str]) -> list[str]:
    return [value for value in preferred if value in values] + sorted(
        values - set(preferred)
    )


def algorithm_color(algorithm: str) -> str:
    return ALGORITHM_COLORS.get(algorithm, "#666666")


def shaded(color: str, amount: float) -> tuple[float, float, float]:
    """Blend a color toward white (positive) or black (negative)."""

    rgb = mcolors.to_rgb(color)
    if amount >= 0.0:
        return tuple(channel + (1.0 - channel) * min(amount, 1.0) for channel in rgb)
    factor = max(0.0, 1.0 + amount)
    return tuple(channel * factor for channel in rgb)
