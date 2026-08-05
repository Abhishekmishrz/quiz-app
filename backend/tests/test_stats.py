"""Unit tests for app/utils/stats.py using hand-computable fixtures."""
import math

import pytest

from app.utils.stats import (
    bayesian_shrink,
    coefficient_of_variation,
    linear_regression_slope,
    min_max_normalize,
)


class TestCoefficientOfVariation:
    def test_basic(self):
        # CV = std/mean = 6000/18000 = 0.3333...
        cv = coefficient_of_variation(mean=18000, std=6000)
        assert cv == pytest.approx(0.3333, abs=1e-3)

    def test_zero_mean_guarded(self):
        assert coefficient_of_variation(mean=0, std=100) == 0.0

    def test_zero_std(self):
        assert coefficient_of_variation(mean=100, std=0) == 0.0


class TestMinMaxNormalize:
    def test_plain_normalize(self):
        result = min_max_normalize([10000, 20000, 30000])
        assert result == pytest.approx([0.0, 0.5, 1.0])

    def test_inverted_normalize_matches_lvi_worked_example(self):
        # cohort clipped range [10000, 30000], user value 18000
        # speed_score = (30000-18000)/(30000-10000) = 0.60
        result = min_max_normalize([10000, 18000, 30000], invert=True)
        assert result[1] == pytest.approx(0.60)

    def test_degenerate_all_equal_returns_half(self):
        result = min_max_normalize([5000, 5000, 5000])
        assert result == [0.5, 0.5, 0.5]

    def test_empty_returns_empty(self):
        assert min_max_normalize([]) == []

    def test_percentile_clipping_limits_outlier_influence(self):
        # A single huge outlier shouldn't get to squash everyone else's
        # normalized spread down near 0.
        values = [10000, 11000, 12000, 13000, 14000, 100000]
        clipped = min_max_normalize(values, clip_percentiles=(5, 95))
        unclipped = min_max_normalize(values)

        # The outlier is still the max after clipping -> normalizes to 1.0.
        assert clipped[-1] == 1.0
        # A mid-range value (12000) should carry noticeably more of the [0,1]
        # spread once the 100000 outlier's influence on the range is capped.
        assert clipped[2] > unclipped[2]


class TestBayesianShrink:
    def test_qdi_accuracy_worked_example(self):
        # 3 attempts, 1 correct -> shrunk_accuracy = (1 + 10*0.65)/13 = 0.5769
        shrunk = bayesian_shrink(observed_sum=1, observed_count=3, prior_mean=0.65, k=10)
        assert shrunk == pytest.approx(0.5769, abs=1e-3)

    def test_qdi_time_worked_example(self):
        # 3 attempts, raw avg 25000ms (sum=75000), chapter_mean=18000, k=10
        # shrunk_time = (75000 + 10*18000)/13 = 19615.38
        shrunk = bayesian_shrink(observed_sum=75000, observed_count=3, prior_mean=18000, k=10)
        assert shrunk == pytest.approx(19615.38, abs=0.5)

    def test_shrinks_toward_prior_when_no_observations(self):
        shrunk = bayesian_shrink(observed_sum=0, observed_count=0, prior_mean=0.5, k=10)
        assert shrunk == pytest.approx(0.5)

    def test_large_sample_barely_shrinks(self):
        # 1000 attempts, 800 correct -> raw 0.8, shrinkage should barely move it
        shrunk = bayesian_shrink(observed_sum=800, observed_count=1000, prior_mean=0.5, k=10)
        assert shrunk == pytest.approx(0.8, abs=0.01)


class TestLinearRegressionSlope:
    def test_accuracy_slope_worked_example(self):
        # buckets accuracy [0.90, 0.80, 0.70, 0.60] at indices [0,1,2,3]
        # perfectly linear -> slope = -0.10 exactly
        slope = linear_regression_slope([0, 1, 2, 3], [0.90, 0.80, 0.70, 0.60])
        assert slope == pytest.approx(-0.10, abs=1e-9)

    def test_time_slope_worked_example(self):
        # time [15000, 17000, 20000, 25000]ms at indices [0,1,2,3]
        # least-squares slope = 3300 (not perfectly linear, computed via polyfit)
        slope = linear_regression_slope([0, 1, 2, 3], [15000, 17000, 20000, 25000])
        assert slope == pytest.approx(3300.0, abs=1.0)

    def test_fewer_than_two_points_returns_zero(self):
        assert linear_regression_slope([0], [1.0]) == 0.0
        assert linear_regression_slope([], []) == 0.0
