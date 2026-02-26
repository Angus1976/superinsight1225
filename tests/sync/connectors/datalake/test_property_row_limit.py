"""
Property-based tests for Row Limit Enforcement.

Tests Property 7: Row limit enforcement
**Validates: Requirements 4.3, 5.3**

For any query result or table preview request, the number of returned rows
should not exceed min(requested_limit, max_query_rows) and the preview limit
should not exceed 1000.
"""

from hypothesis import given, settings, strategies as st

from src.sync.connectors.datalake.base import (
    DEFAULT_PREVIEW_LIMIT,
    MAX_PREVIEW_LIMIT,
    DatalakeBaseConnector,
)
from src.sync.connectors.datalake.clickhouse import (
    ClickHouseConfig,
    ClickHouseConnector,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_connector(max_query_rows: int) -> DatalakeBaseConnector:
    """Create a ClickHouseConnector with the given max_query_rows."""
    config = ClickHouseConfig(
        name="test-clickhouse",
        host="localhost",
        port=9000,
        database="test",
        username="user",
        password="pass",
        max_query_rows=max_query_rows,
    )
    return ClickHouseConnector(config)


# ============================================================================
# Strategies
# ============================================================================

def positive_limit_strategy():
    """Strategy for positive requested limits."""
    return st.integers(min_value=1, max_value=10_000_000)


def non_positive_limit_strategy():
    """Strategy for zero and negative requested limits."""
    return st.integers(min_value=-10_000_000, max_value=0)


def max_query_rows_strategy():
    """Strategy for valid max_query_rows config values (>= 1)."""
    return st.integers(min_value=1, max_value=10_000_000)


# ============================================================================
# Property 7: Row limit enforcement
# **Validates: Requirements 4.3, 5.3**
# ============================================================================

class TestRowLimitEnforcement:
    """Property 7: Row limit enforcement."""

    @settings(max_examples=200)
    @given(
        requested_limit=positive_limit_strategy(),
        max_query_rows=max_query_rows_strategy(),
    )
    def test_never_exceeds_max_preview_limit(
        self, requested_limit, max_query_rows
    ):
        """Clamped limit never exceeds MAX_PREVIEW_LIMIT (1000).

        **Validates: Requirements 4.3**
        """
        connector = _make_connector(max_query_rows)
        result = connector._clamp_preview_limit(requested_limit)
        assert result <= MAX_PREVIEW_LIMIT, (
            f"Clamped limit {result} exceeds MAX_PREVIEW_LIMIT "
            f"({MAX_PREVIEW_LIMIT}) for requested={requested_limit}, "
            f"max_query_rows={max_query_rows}"
        )

    @settings(max_examples=200)
    @given(
        requested_limit=positive_limit_strategy(),
        max_query_rows=max_query_rows_strategy(),
    )
    def test_never_exceeds_max_query_rows(
        self, requested_limit, max_query_rows
    ):
        """Clamped limit never exceeds max_query_rows from config.

        **Validates: Requirements 5.3**
        """
        connector = _make_connector(max_query_rows)
        result = connector._clamp_preview_limit(requested_limit)
        assert result <= max_query_rows, (
            f"Clamped limit {result} exceeds max_query_rows "
            f"({max_query_rows}) for requested={requested_limit}"
        )

    @settings(max_examples=200)
    @given(
        requested_limit=positive_limit_strategy(),
        max_query_rows=max_query_rows_strategy(),
    )
    def test_effective_limit_equals_min(self, requested_limit, max_query_rows):
        """Effective limit equals min(requested, max_query_rows, MAX_PREVIEW_LIMIT).

        **Validates: Requirements 4.3, 5.3**
        """
        connector = _make_connector(max_query_rows)
        result = connector._clamp_preview_limit(requested_limit)
        expected = min(requested_limit, max_query_rows, MAX_PREVIEW_LIMIT)
        assert result == expected, (
            f"Expected {expected}, got {result} for "
            f"requested={requested_limit}, max_query_rows={max_query_rows}"
        )

    @settings(max_examples=200)
    @given(
        requested_limit=non_positive_limit_strategy(),
        max_query_rows=max_query_rows_strategy(),
    )
    def test_non_positive_returns_default(
        self, requested_limit, max_query_rows
    ):
        """Non-positive requested limits fall back to DEFAULT_PREVIEW_LIMIT.

        **Validates: Requirements 4.3**
        """
        connector = _make_connector(max_query_rows)
        result = connector._clamp_preview_limit(requested_limit)
        assert result == DEFAULT_PREVIEW_LIMIT, (
            f"Expected DEFAULT_PREVIEW_LIMIT ({DEFAULT_PREVIEW_LIMIT}), "
            f"got {result} for non-positive limit={requested_limit}"
        )

    @settings(max_examples=100)
    @given(max_query_rows=max_query_rows_strategy())
    def test_result_always_positive(self, max_query_rows):
        """Clamped limit is always a positive integer regardless of input.

        **Validates: Requirements 4.3, 5.3**
        """
        connector = _make_connector(max_query_rows)
        # Test with a range of limits including edge cases
        for limit in [-1, 0, 1, 500, 1000, 1001, 999999]:
            result = connector._clamp_preview_limit(limit)
            assert result > 0, (
                f"Clamped limit should be positive, got {result} "
                f"for limit={limit}, max_query_rows={max_query_rows}"
            )
