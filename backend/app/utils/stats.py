"""Pure-python statistical helpers used by analytics_service.

These are intentionally free of any MongoDB/FastAPI dependency so they can
be unit-tested directly against hand-computable fixtures.
"""
from typing import List, Optional, Sequence, Tuple

import numpy as np


def coefficient_of_variation(mean: float, std: float) -> float:
    """CV = std / mean. Guards divide-by-zero (returns 0.0, so a caller
    computing consistency = 1/(1+CV) correctly gets 1.0 for a zero-mean
    degenerate case -- this shouldn't happen with real data but is guarded
    anyway).
    """
    if mean == 0:
        return 0.0
    return std / mean


def min_max_normalize(
    values: Sequence[float],
    invert: bool = False,
    clip_percentiles: Optional[Tuple[float, float]] = None,
) -> List[float]:
    """Min-max normalize `values` to [0, 1].

    If `clip_percentiles=(low_pct, high_pct)` is given, each value is first
    clipped into the [P_low, P_high] range computed over `values` (used to
    keep a handful of extreme outliers from squashing everyone else's score
    to near-0 or near-1).

    If `invert` is True, the smallest (clipped) value maps to 1.0 and the
    largest to 0.0 -- used for "lower is better" metrics like response time
    turned into a speed score.

    Degenerate case (max == min, e.g. a tiny or fully-uniform cohort):
    returns 0.5 for every value rather than dividing by zero.
    """
    arr = np.array(values, dtype=float)
    if arr.size == 0:
        return []

    if clip_percentiles is not None:
        low_pct, high_pct = clip_percentiles
        lo = np.percentile(arr, low_pct)
        hi = np.percentile(arr, high_pct)
        arr = np.clip(arr, lo, hi)

    vmin = float(arr.min())
    vmax = float(arr.max())

    if vmax == vmin:
        return [0.5] * len(arr)

    if invert:
        normalized = (vmax - arr) / (vmax - vmin)
    else:
        normalized = (arr - vmin) / (vmax - vmin)

    return [float(v) for v in normalized]


def bayesian_shrink(observed_sum: float, observed_count: float, prior_mean: float, k: float) -> float:
    """Generic Bayesian (empirical-Bayes) shrinkage toward a prior mean.

    shrunk = (observed_sum + k * prior_mean) / (observed_count + k)

    For accuracy: observed_sum=correct_count, observed_count=total_attempts,
    prior_mean=global (or chapter) mean accuracy.
    For time: observed_sum=total_attempts*avg_time (i.e. sum of durations),
    observed_count=total_attempts, prior_mean=chapter mean time.
    """
    return (observed_sum + k * prior_mean) / (observed_count + k)


def linear_regression_slope(x: Sequence[float], y: Sequence[float]) -> float:
    """Slope of the best-fit line for y over x, via numpy.polyfit degree 1.

    Returns 0.0 if there are fewer than 2 points (slope is undefined).
    """
    if len(x) < 2 or len(y) < 2:
        return 0.0
    slope, _intercept = np.polyfit(np.array(x, dtype=float), np.array(y, dtype=float), 1)
    return float(slope)
