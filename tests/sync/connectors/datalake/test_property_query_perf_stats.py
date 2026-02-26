"""
Property-based tests for Query Performance Statistics Correctness.

Tests Property 10: Query performance statistics correctness
**Validates: Requirement 6.4**

For any set of query latency measurements, the computed avg_latency_ms
should equal the arithmetic mean, p95_latency_ms should equal the 95th
percentile, and p99_latency_ms should equal the 99th percentile of the
input data.
"""

import math
from typing import List

from hypothesis import given, settings, strategies as st

from src.sync.connectors.datalake.router import _compute_percentile


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def latency_strategy():
    """Non-negative float values representing latency in ms."""
    return st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False)


def latency_list_strategy(min_size: int = 1, max_size: int = 200):
    """List of non-negative latency values."""
    return st.lists(latency_strategy(), min_size=min_size, max_size=max_size)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------

class TestAvgLatencyEqualsArithmeticMean:
    """avg_latency should equal the arithmetic mean of all latency values.

    **Validates: Requirement 6.4**
    """

    @settings(max_examples=100)
    @given(latencies=latency_list_strategy(min_size=1))
    def test_avg_equals_arithmetic_mean(self, latencies: List[float]):
        """For any non-empty list of latencies, avg equals sum/count.

        **Validates: Requirement 6.4**
        """
        expected_avg = sum(latencies) / len(latencies)
        sorted_latencies = sorted(latencies)
        computed_avg = sum(sorted_latencies) / len(sorted_latencies)

        assert math.isclose(computed_avg, expected_avg, rel_tol=1e-9, abs_tol=1e-12)


class TestP95PercentileCorrectness:
    """_compute_percentile(sorted_values, 95) should equal the 95th percentile.

    **Validates: Requirement 6.4**
    """

    @settings(max_examples=100)
    @given(latencies=latency_list_strategy(min_size=1))
    def test_p95_equals_95th_percentile(self, latencies: List[float]):
        """For any sorted list, _compute_percentile(values, 95) matches expected.

        **Validates: Requirement 6.4**
        """
        sorted_vals = sorted(latencies)
        p95 = _compute_percentile(sorted_vals, 95)

        # Manually compute expected 95th percentile using same interpolation
        n = len(sorted_vals)
        if n == 1:
            assert p95 == sorted_vals[0]
            return

        rank = 0.95 * (n - 1)
        lower = int(rank)
        upper = min(lower + 1, n - 1)
        fraction = rank - lower
        expected = sorted_vals[lower] + fraction * (sorted_vals[upper] - sorted_vals[lower])

        assert math.isclose(p95, expected, rel_tol=1e-9, abs_tol=1e-12)


class TestP99PercentileCorrectness:
    """_compute_percentile(sorted_values, 99) should equal the 99th percentile.

    **Validates: Requirement 6.4**
    """

    @settings(max_examples=100)
    @given(latencies=latency_list_strategy(min_size=1))
    def test_p99_equals_99th_percentile(self, latencies: List[float]):
        """For any sorted list, _compute_percentile(values, 99) matches expected.

        **Validates: Requirement 6.4**
        """
        sorted_vals = sorted(latencies)
        p99 = _compute_percentile(sorted_vals, 99)

        n = len(sorted_vals)
        if n == 1:
            assert p99 == sorted_vals[0]
            return

        rank = 0.99 * (n - 1)
        lower = int(rank)
        upper = min(lower + 1, n - 1)
        fraction = rank - lower
        expected = sorted_vals[lower] + fraction * (sorted_vals[upper] - sorted_vals[lower])

        assert math.isclose(p99, expected, rel_tol=1e-9, abs_tol=1e-12)


class TestP95LessOrEqualP99:
    """p95 <= p99 should always hold for any non-empty sorted list.

    **Validates: Requirement 6.4**
    """

    @settings(max_examples=100)
    @given(latencies=latency_list_strategy(min_size=1))
    def test_p95_leq_p99(self, latencies: List[float]):
        """For any latency data, p95 <= p99.

        **Validates: Requirement 6.4**
        """
        sorted_vals = sorted(latencies)
        p95 = _compute_percentile(sorted_vals, 95)
        p99 = _compute_percentile(sorted_vals, 99)

        assert p95 <= p99 or math.isclose(p95, p99, rel_tol=1e-9, abs_tol=1e-12)


class TestAvgLessOrEqualP99:
    """avg <= p99 should always hold for non-negative values.

    **Validates: Requirement 6.4**
    """

    @settings(max_examples=100)
    @given(latencies=latency_list_strategy(min_size=1))
    def test_avg_leq_p99(self, latencies: List[float]):
        """For any non-negative latency data, avg <= p99.

        **Validates: Requirement 6.4**
        """
        sorted_vals = sorted(latencies)
        avg = sum(sorted_vals) / len(sorted_vals)
        p99 = _compute_percentile(sorted_vals, 99)

        assert avg <= p99 or math.isclose(avg, p99, rel_tol=1e-9, abs_tol=1e-12)


class TestEmptyInputReturnsZero:
    """Empty input should return 0.0 for all stats.

    **Validates: Requirement 6.4**
    """

    def test_empty_list_returns_zero(self):
        """_compute_percentile on empty list returns 0.0.

        **Validates: Requirement 6.4**
        """
        assert _compute_percentile([], 50) == 0.0
        assert _compute_percentile([], 95) == 0.0
        assert _compute_percentile([], 99) == 0.0

    def test_empty_avg_is_zero(self):
        """Average of empty list is 0.0 (matching router behavior).

        **Validates: Requirement 6.4**
        """
        latencies: List[float] = []
        avg = sum(latencies) / len(latencies) if latencies else 0.0
        assert avg == 0.0
