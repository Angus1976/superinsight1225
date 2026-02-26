"""
Property-based tests for Query Timeout Protection.

Tests Property 8: Query timeout protection
**Validates: Requirement 5.2**

For any query where execution time exceeds the configured query_timeout value,
the connector should cancel the query and return a timeout error.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.sync.connectors.datalake.clickhouse import (
    ClickHouseConfig,
    ClickHouseConnector,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_connector(query_timeout: int) -> ClickHouseConnector:
    """Create a ClickHouseConnector with the given query_timeout."""
    config = ClickHouseConfig(
        name="test-clickhouse",
        host="localhost",
        port=9000,
        database="test",
        username="user",
        password="pass",
        query_timeout=query_timeout,
    )
    return ClickHouseConnector(config)


# ============================================================================
# Strategies
# ============================================================================


def small_timeout_strategy():
    """Strategy for small timeout values (seconds) to keep tests fast."""
    return st.integers(min_value=1, max_value=5)


def query_timeout_strategy():
    """Strategy for valid query_timeout config values."""
    return st.integers(min_value=1, max_value=300)


# ============================================================================
# Property 8: Query timeout protection
# **Validates: Requirement 5.2**
# ============================================================================


class TestQueryTimeoutProtection:
    """Property 8: Query timeout protection."""

    @settings(max_examples=20, deadline=30000)
    @given(query_timeout=small_timeout_strategy())
    def test_slow_query_raises_timeout_error(self, query_timeout):
        """Queries exceeding query_timeout raise TimeoutError.

        **Validates: Requirement 5.2**
        """
        connector = _make_connector(query_timeout)

        async def slow_run_query(sql):
            await asyncio.sleep(query_timeout + 1)
            return []

        with patch.object(connector, "_run_query", side_effect=slow_run_query):
            with pytest.raises(TimeoutError):
                asyncio.get_event_loop().run_until_complete(
                    connector.execute_query("SELECT 1")
                )

    @settings(max_examples=20, deadline=30000)
    @given(query_timeout=small_timeout_strategy())
    def test_timeout_records_failed_metric(self, query_timeout):
        """When a query times out, failed_queries metric is incremented.

        **Validates: Requirement 5.2**
        """
        connector = _make_connector(query_timeout)
        initial_failed = connector._query_metrics["failed_queries"]
        initial_total = connector._query_metrics["total_queries"]

        async def slow_run_query(sql):
            await asyncio.sleep(query_timeout + 1)
            return []

        with patch.object(connector, "_run_query", side_effect=slow_run_query):
            with pytest.raises(TimeoutError):
                asyncio.get_event_loop().run_until_complete(
                    connector.execute_query("SELECT 1")
                )

        assert connector._query_metrics["failed_queries"] == initial_failed + 1
        assert connector._query_metrics["total_queries"] == initial_total + 1

    @settings(max_examples=50, deadline=30000)
    @given(query_timeout=query_timeout_strategy())
    def test_timeout_value_from_config_is_respected(self, query_timeout):
        """The timeout error message references the configured query_timeout.

        **Validates: Requirement 5.2**
        """
        connector = _make_connector(query_timeout)

        async def immediate_timeout(sql):
            raise asyncio.TimeoutError()

        with patch.object(
            connector, "_run_query", side_effect=immediate_timeout
        ):
            with pytest.raises(TimeoutError, match=str(query_timeout)):
                asyncio.get_event_loop().run_until_complete(
                    connector.execute_query("SELECT 1")
                )

    @settings(max_examples=20, deadline=30000)
    @given(query_timeout=small_timeout_strategy())
    def test_fast_query_succeeds_within_timeout(self, query_timeout):
        """Queries completing before query_timeout return results normally.

        **Validates: Requirement 5.2**
        """
        connector = _make_connector(query_timeout)

        async def fast_run_query(sql):
            await asyncio.sleep(0.01)
            return [{"col": "value"}]

        with patch.object(connector, "_run_query", side_effect=fast_run_query):
            batch = asyncio.get_event_loop().run_until_complete(
                connector.execute_query("SELECT 1")
            )

        assert len(batch.records) == 1
        assert connector._query_metrics["failed_queries"] == 0
        assert connector._query_metrics["total_queries"] == 1
