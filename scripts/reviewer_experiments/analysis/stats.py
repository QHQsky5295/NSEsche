"""Small, dependency-light statistical routines used by the experiment pipeline.

The functions in this module operate on independent run-level observations.  They
never select or discard a run according to the observed performance.  Non-finite
pairs are removed only where a numerical test is undefined; callers are expected
to report those counts (the CSV pipeline does so explicitly).
"""

from __future__ import annotations

import itertools
import math
from statistics import NormalDist
from typing import Callable, Iterable, Sequence

import numpy as np


ArrayStatistic = Callable[[np.ndarray], float]
_NORMAL = NormalDist()


def _finite_1d(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float).reshape(-1)
    return array[np.isfinite(array)]


def _paired_finite(
    x: Iterable[float], y: Iterable[float]
) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(list(x), dtype=float).reshape(-1)
    right = np.asarray(list(y), dtype=float).reshape(-1)
    if left.shape != right.shape:
        raise ValueError("paired samples must have the same length")
    keep = np.isfinite(left) & np.isfinite(right)
    return left[keep], right[keep]


def bca_interval(
    values: Iterable[float],
    *,
    statistic: ArrayStatistic = np.mean,
    confidence: float = 0.95,
    n_resamples: int = 10_000,
    seed: int = 20260809,
) -> dict[str, float | int | str]:
    """Return a bias-corrected and accelerated (BCa) bootstrap interval.

    The point estimate and interval are based only on finite values.  At least
    three observations are required because the acceleration term is estimated
    with a delete-one jackknife.
    """

    sample = _finite_1d(values)
    n = int(sample.size)
    if n < 3:
        raise ValueError(
            "BCa confidence intervals require at least three finite observations"
        )
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if n_resamples < 100:
        raise ValueError("n_resamples must be at least 100")

    estimate = float(statistic(sample))
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n), endpoint=False)
    if statistic is np.mean:
        bootstrap = np.mean(sample[indices], axis=1)
    else:
        bootstrap = np.asarray([statistic(sample[idx]) for idx in indices], dtype=float)
    bootstrap = bootstrap[np.isfinite(bootstrap)]
    if bootstrap.size < 100:
        raise ValueError("fewer than 100 finite bootstrap estimates were produced")

    # Mid-rank treatment of ties avoids an artificial extreme bias correction
    # for constant or heavily quantized simulator metrics.
    less = float(np.count_nonzero(bootstrap < estimate))
    equal = float(np.count_nonzero(bootstrap == estimate))
    proportion = (less + 0.5 * equal) / float(bootstrap.size)
    guard = 0.5 / float(bootstrap.size)
    proportion = min(max(proportion, guard), 1.0 - guard)
    z0 = _NORMAL.inv_cdf(proportion)

    if statistic is np.mean:
        jackknife = (float(np.sum(sample)) - sample) / float(n - 1)
    else:
        jackknife = np.asarray(
            [statistic(np.delete(sample, idx)) for idx in range(n)], dtype=float
        )
    jackknife_mean = float(np.mean(jackknife))
    centered = jackknife_mean - jackknife
    denominator = 6.0 * float(np.sum(centered**2)) ** 1.5
    acceleration = (
        0.0 if denominator == 0.0 else float(np.sum(centered**3)) / denominator
    )

    alpha = (1.0 - confidence) / 2.0
    requested = (alpha, 1.0 - alpha)
    adjusted: list[float] = []
    for probability in requested:
        z_alpha = _NORMAL.inv_cdf(probability)
        inner = z0 + z_alpha
        denom = 1.0 - acceleration * inner
        if abs(denom) < 1e-12:
            transformed = 0.0 if inner < 0.0 else 1.0
        else:
            transformed = _NORMAL.cdf(z0 + inner / denom)
        adjusted.append(min(max(transformed, 0.0), 1.0))

    low, high = np.quantile(bootstrap, adjusted, method="linear")
    return {
        "estimate": estimate,
        "low": float(low),
        "high": float(high),
        "confidence": float(confidence),
        "n": n,
        "resamples": int(bootstrap.size),
        "method": "BCa",
        "bias_correction": float(z0),
        "acceleration": float(acceleration),
    }


def paired_permutation_test(
    x: Iterable[float],
    y: Iterable[float],
    *,
    alternative: str = "two-sided",
    n_resamples: int = 100_000,
    exact_threshold: int = 16,
    seed: int = 20260809,
) -> dict[str, float | int | bool | str]:
    """Paired randomization test of a zero mean paired difference.

    All ``2**n`` sign flips are enumerated through ``exact_threshold`` pairs.
    Larger samples use Monte Carlo sign flips and the Phipson-Smyth ``+1``
    correction, so a simulated p-value is never reported as zero.
    """

    if alternative not in {"two-sided", "greater", "less"}:
        raise ValueError("alternative must be two-sided, greater, or less")
    left, right = _paired_finite(x, y)
    differences = left - right
    n = int(differences.size)
    if n == 0:
        raise ValueError("paired permutation test requires at least one finite pair")
    observed = float(np.mean(differences))
    tolerance = np.finfo(float).eps * max(1.0, abs(observed)) * 8.0

    def is_extreme(candidate: np.ndarray | float) -> np.ndarray | bool:
        if alternative == "two-sided":
            return np.abs(candidate) >= abs(observed) - tolerance
        if alternative == "greater":
            return candidate >= observed - tolerance
        return candidate <= observed + tolerance

    if n <= exact_threshold:
        extreme = 0
        total = 0
        for signs in itertools.product((-1.0, 1.0), repeat=n):
            candidate = float(np.mean(differences * np.asarray(signs)))
            total += 1
            extreme += int(bool(is_extreme(candidate)))
        p_value = extreme / total
        exact = True
    else:
        if n_resamples < 1_000:
            raise ValueError(
                "Monte Carlo permutation tests require at least 1,000 resamples"
            )
        rng = np.random.default_rng(seed)
        extreme = 0
        generated = 0
        batch_size = min(10_000, n_resamples)
        while generated < n_resamples:
            current = min(batch_size, n_resamples - generated)
            signs = rng.choice(np.asarray((-1.0, 1.0)), size=(current, n))
            candidates = np.mean(signs * differences, axis=1)
            extreme += int(np.count_nonzero(is_extreme(candidates)))
            generated += current
        total = n_resamples
        p_value = (extreme + 1.0) / (total + 1.0)
        exact = False

    return {
        "mean_difference": observed,
        "p_value": float(p_value),
        "n_pairs": n,
        "alternative": alternative,
        "exact": exact,
        "resamples": int(total),
    }


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=float)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        # Ranks are one-based; tied observations receive their average rank.
        average = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average
        start = end
    return ranks


def spearman_correlation(
    x: Iterable[float], y: Iterable[float]
) -> dict[str, float | int | str]:
    """Return Spearman's rank correlation with explicit undefined reasons.

    The routine is intentionally dependency-light (SciPy is not required) and
    uses average ranks for ties.  It is a *descriptive within-run* statistic in
    the reviewer pipeline: confidence intervals are subsequently formed across
    independent run/seed correlations, never across functions or requests.
    """

    left = np.asarray(list(x), dtype=float).reshape(-1)
    right = np.asarray(list(y), dtype=float).reshape(-1)
    if left.shape != right.shape:
        raise ValueError("Spearman samples must have the same length")
    keep = np.isfinite(left) & np.isfinite(right)
    left = left[keep]
    right = right[keep]
    n = int(left.size)
    if n < 3:
        return {"rho": math.nan, "n": n, "status": "insufficient_pairs"}
    if np.all(left == left[0]):
        return {"rho": math.nan, "n": n, "status": "constant_feature"}
    if np.all(right == right[0]):
        return {"rho": math.nan, "n": n, "status": "constant_outcome"}
    left_rank = _average_ranks(left)
    right_rank = _average_ranks(right)
    rho = float(np.corrcoef(left_rank, right_rank)[0, 1])
    return {
        "rho": max(-1.0, min(1.0, rho)),
        "n": n,
        "status": "ok",
    }


def paired_effect_sizes(
    x: Iterable[float], y: Iterable[float]
) -> dict[str, float | int]:
    """Return Cohen's dz and matched-pairs rank-biserial correlation for x-y."""

    left, right = _paired_finite(x, y)
    differences = left - right
    n = int(differences.size)
    if n == 0:
        raise ValueError("paired effect sizes require at least one finite pair")

    mean_difference = float(np.mean(differences))
    if n < 2:
        cohen_dz = math.nan
    else:
        sd_difference = float(np.std(differences, ddof=1))
        if sd_difference == 0.0:
            cohen_dz = (
                0.0
                if mean_difference == 0.0
                else math.copysign(math.inf, mean_difference)
            )
        else:
            cohen_dz = mean_difference / sd_difference

    nonzero = differences[differences != 0.0]
    if nonzero.size == 0:
        rank_biserial = 0.0
    else:
        ranks = _average_ranks(np.abs(nonzero))
        positive = float(np.sum(ranks[nonzero > 0.0]))
        negative = float(np.sum(ranks[nonzero < 0.0]))
        rank_biserial = (positive - negative) / float(np.sum(ranks))

    return {
        "mean_difference": mean_difference,
        "median_difference": float(np.median(differences)),
        "cohen_dz": float(cohen_dz),
        "rank_biserial": float(rank_biserial),
        "n_pairs": n,
    }


def holm_adjust(
    p_values: Sequence[float], *, alpha: float = 0.05
) -> tuple[list[float], list[bool]]:
    """Holm step-down family-wise error correction in original input order."""

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")
    p_array = np.asarray(p_values, dtype=float)
    if p_array.ndim != 1:
        raise ValueError("p_values must be one-dimensional")
    if np.any(~np.isfinite(p_array)) or np.any((p_array < 0.0) | (p_array > 1.0)):
        raise ValueError("all p-values must be finite and between 0 and 1")
    m = int(p_array.size)
    if m == 0:
        return [], []

    order = np.argsort(p_array, kind="mergesort")
    adjusted_sorted = np.empty(m, dtype=float)
    running_max = 0.0
    for rank, original_index in enumerate(order):
        candidate = (m - rank) * float(p_array[original_index])
        running_max = max(running_max, candidate)
        adjusted_sorted[rank] = min(running_max, 1.0)

    adjusted = np.empty(m, dtype=float)
    for rank, original_index in enumerate(order):
        adjusted[original_index] = adjusted_sorted[rank]
    rejected = adjusted <= alpha
    return adjusted.tolist(), rejected.tolist()


def precision_assessment(
    ordered_values: Iterable[float],
    *,
    first_n: int = 10,
    max_n: int = 20,
    target_relative_half_width: float = 0.10,
    target_absolute_half_width: float | None = None,
    confidence: float = 0.95,
    n_resamples: int = 10_000,
    seed: int = 20260809,
) -> dict[str, float | int | bool | str | None]:
    """Apply a pre-declared CI precision rule at n=10, then (if needed) n=20.

    Values must already be in the protocol's fixed run order, normally ascending
    seed.  The stopping recommendation depends only on interval width, never on
    whether a method wins or whether a p-value is significant.
    """

    if first_n < 3 or max_n < first_n:
        raise ValueError("require 3 <= first_n <= max_n")
    if target_relative_half_width <= 0.0:
        raise ValueError("target_relative_half_width must be positive")
    values = _finite_1d(ordered_values)
    available = int(values.size)

    result: dict[str, float | int | bool | str | None] = {
        "available_n": available,
        "first_n": first_n,
        "max_n": max_n,
        "target_relative_half_width": target_relative_half_width,
        "target_absolute_half_width": target_absolute_half_width,
        "estimate_n10": None,
        "ci_low_n10": None,
        "ci_high_n10": None,
        "relative_half_width_n10": None,
        "precision_met_n10": False,
        "estimate_n20": None,
        "ci_low_n20": None,
        "ci_high_n20": None,
        "relative_half_width_n20": None,
        "precision_met_n20": False,
        "precision_gain_10_to_20": None,
        "recommended_n": None,
        "decision": "insufficient_for_n10",
    }
    if available < first_n:
        return result

    def interval_snapshot(
        sample: np.ndarray, local_seed: int
    ) -> dict[str, float | bool]:
        ci = bca_interval(
            sample,
            confidence=confidence,
            n_resamples=n_resamples,
            seed=local_seed,
        )
        half_width = (float(ci["high"]) - float(ci["low"])) / 2.0
        estimate = float(ci["estimate"])
        if abs(estimate) > 1e-12:
            relative = half_width / abs(estimate)
            met = relative <= target_relative_half_width
        else:
            relative = math.inf
            met = (
                target_absolute_half_width is not None
                and half_width <= target_absolute_half_width
            )
        return {
            "estimate": estimate,
            "low": float(ci["low"]),
            "high": float(ci["high"]),
            "relative": float(relative),
            "met": bool(met),
        }

    first = interval_snapshot(values[:first_n], seed)
    result.update(
        {
            "estimate_n10": first["estimate"],
            "ci_low_n10": first["low"],
            "ci_high_n10": first["high"],
            "relative_half_width_n10": first["relative"],
            "precision_met_n10": first["met"],
        }
    )
    if bool(first["met"]):
        result["recommended_n"] = first_n
        result["decision"] = "stop_at_n10"
    else:
        result["recommended_n"] = max_n
        result["decision"] = "extend_to_n20" if available < max_n else "evaluate_n20"

    if available >= max_n:
        final = interval_snapshot(values[:max_n], seed + 1)
        result.update(
            {
                "estimate_n20": final["estimate"],
                "ci_low_n20": final["low"],
                "ci_high_n20": final["high"],
                "relative_half_width_n20": final["relative"],
                "precision_met_n20": final["met"],
            }
        )
        first_relative = float(first["relative"])
        final_relative = float(final["relative"])
        if (
            math.isfinite(first_relative)
            and first_relative > 0.0
            and math.isfinite(final_relative)
        ):
            result["precision_gain_10_to_20"] = 1.0 - final_relative / first_relative
        if not bool(first["met"]):
            result["decision"] = (
                "precision_met_at_n20"
                if bool(final["met"])
                else "precision_not_met_at_n20"
            )
    return result
