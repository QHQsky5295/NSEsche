"""Reproducible run-level analysis for the reviewer experiments."""

from .stats import (
    bca_interval,
    holm_adjust,
    paired_effect_sizes,
    paired_permutation_test,
    precision_assessment,
    spearman_correlation,
)
from .protocol_results import load_canonical_protocol_results

__all__ = [
    "bca_interval",
    "holm_adjust",
    "paired_effect_sizes",
    "paired_permutation_test",
    "precision_assessment",
    "spearman_correlation",
    "load_canonical_protocol_results",
]
