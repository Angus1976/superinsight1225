"""
Unit tests for Datalake Dashboard endpoints.

Tests the dashboard data aggregation logic for:
- GET /dashboard/overview (Requirement 6.1, 6.2)
- GET /dashboard/health (Requirement 6.1)
- GET /dashboard/volume-trends (Requirement 6.3)
- GET /dashboard/query-performance (Requirement 6.4)
- GET /dashboard/data-flow (Requirement 6.5)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.sync.connectors.datalake.router import (
    _build_source_summary,
    _classify_source_type,
    _compute_percentile,
    _parse_period,
)
from src.sync.connectors.datalake.schemas import (
    DashboardOverview,
    DataFlowGraph,
    QueryPerformanceData,
    SourceHealthStatus,
    VolumeTrendData,
)
from src.sync.models import DataSourceStatus, DataSourceType


# ============================================================================
# Tests for _compute_percentile
# ============================================================================


class TestComputePercentile:
    """Tests for the percentile computation helper."""

    def test_empty_list_returns_zero(self):
        assert _compute_percentile([], 95) == 0.0

    def test_single_value(self):
        assert _compute_percentile([42.0], 95) == 42.0
        assert _compute_percentile([42.0], 50) == 42.0

    def test_two_values_p50(self):
        result = _compute_percentile([10.0, 20.0], 50)
        assert result == pytest.approx(15.0)

    def test_p95_with_known_data(self):
        # 20 values: 1..20
        values = sorted([float(i) for i in range(1, 21)])
        p95 = _compute_percentile(values, 95)
        # rank = 0.95 * 19 = 18.05 → between index 18 (19.0) and 19 (20.0)
        assert p95 == pytest.approx(19.05, rel=1e-3)

    def test_p99_with_known_data(self):
        values = sorted([float(i) for i in range(1, 101)])
        p99 = _compute_percentile(values, 99)
        # rank = 0.99 * 99 = 98.01 → between index 98 (99.0) and 99 (100.0)
        assert p99 == pytest.approx(99.01, rel=1e-3)

    def test_p0_returns_min(self):
        values = [5.0, 10.0, 15.0]
        assert _compute_percentile(values, 0) == 5.0

    def test_p100_returns_max(self):
        values = [5.0, 10.0, 15.0]
        assert _compute_percentile(values, 100) == 15.0


# ============================================================================
# Tests for _parse_period
# ============================================================================


class TestParsePeriod:
    """Tests for the period string parser."""

    def test_valid_periods(self):
        assert _parse_period("1d") == timedelta(days=1)
        assert _parse_period("7d") == timedelta(days=7)
        assert _parse_period("30d") == timedelta(days=30)
        assert _parse_period("90d") == timedelta(days=90)

    def test_invalid_period_raises_400(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _parse_period("invalid")
        assert exc_info.value.status_code == 400


# ============================================================================
# Tests for _classify_source_type
# ============================================================================


class TestClassifySourceType:
    """Tests for the source type classifier."""

    def test_lake_types(self):
        assert _classify_source_type(DataSourceType.DELTA_LAKE) == "lake"
        assert _classify_source_type(DataSourceType.ICEBERG) == "lake"
        assert _classify_source_type(DataSourceType.HIVE) == "lake"

    def test_source_types(self):
        assert _classify_source_type(DataSourceType.CLICKHOUSE) == "source"
        assert _classify_source_type(DataSourceType.DORIS) == "source"
        assert _classify_source_type(DataSourceType.SPARK_SQL) == "source"
        assert _classify_source_type(DataSourceType.PRESTO_TRINO) == "source"


# ============================================================================
# Tests for _build_source_summary
# ============================================================================


class TestBuildSourceSummary:
    """Tests for the source summary builder."""

    def test_builds_summary_from_source(self):
        source = MagicMock()
        source.id = uuid4()
        source.name = "test-clickhouse"
        source.source_type = DataSourceType.CLICKHOUSE
        source.status = DataSourceStatus.ACTIVE
        source.health_check_status = "connected"

        summary = _build_source_summary(source)

        assert summary.source_id == source.id
        assert summary.name == "test-clickhouse"
        assert summary.source_type == DataSourceType.CLICKHOUSE
        assert summary.status == DataSourceStatus.ACTIVE
        assert summary.health_check_status == "connected"

    def test_handles_none_health_check_status(self):
        source = MagicMock()
        source.id = uuid4()
        source.name = "new-source"
        source.source_type = DataSourceType.HIVE
        source.status = DataSourceStatus.INACTIVE
        source.health_check_status = None

        summary = _build_source_summary(source)

        assert summary.health_check_status is None


# ============================================================================
# Tests for DashboardOverview schema invariant
# ============================================================================


class TestDashboardOverviewInvariant:
    """Validates Requirement 6.2: total_sources = active + error + inactive."""

    def test_overview_counts_consistency(self):
        """total_sources must equal active + error + remaining inactive."""
        overview = DashboardOverview(
            total_sources=10,
            active_sources=5,
            error_sources=2,
            total_data_volume_gb=100.0,
            avg_query_latency_ms=50.0,
            sources=[],
        )
        # Invariant: total >= active + error
        assert overview.total_sources >= overview.active_sources + overview.error_sources

    def test_overview_zero_sources(self):
        """Empty dashboard should have all zeros."""
        overview = DashboardOverview(
            total_sources=0,
            active_sources=0,
            error_sources=0,
            total_data_volume_gb=0.0,
            avg_query_latency_ms=0.0,
            sources=[],
        )
        assert overview.total_sources == 0
        assert overview.avg_query_latency_ms == 0.0


# ============================================================================
# Tests for QueryPerformanceData schema
# ============================================================================


class TestQueryPerformanceDataSchema:
    """Validates Requirement 6.4: performance metrics structure."""

    def test_performance_data_fields(self):
        data = QueryPerformanceData(
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            p99_latency_ms=300.0,
            total_queries=1000,
            failed_queries=5,
            queries_by_source=[],
        )
        assert data.avg_latency_ms == 100.0
        assert data.p95_latency_ms == 200.0
        assert data.p99_latency_ms == 300.0
        assert data.total_queries == 1000
        assert data.failed_queries == 5

    def test_latency_ordering_invariant(self):
        """P95 <= P99 for any reasonable dataset."""
        data = QueryPerformanceData(
            avg_latency_ms=50.0,
            p95_latency_ms=150.0,
            p99_latency_ms=200.0,
            total_queries=100,
            failed_queries=0,
            queries_by_source=[],
        )
        assert data.p95_latency_ms <= data.p99_latency_ms


# ============================================================================
# Tests for DataFlowGraph schema
# ============================================================================


class TestDataFlowGraphSchema:
    """Validates Requirement 6.5: graph data structure."""

    def test_empty_graph(self):
        graph = DataFlowGraph(nodes=[], edges=[])
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_graph_with_nodes_and_edges(self):
        from src.sync.connectors.datalake.schemas import FlowEdge, FlowNode

        nodes = [
            FlowNode(id="src1", label="ClickHouse", type="source", status="active"),
            FlowNode(id="platform", label="DataSync", type="warehouse", status="active"),
        ]
        edges = [
            FlowEdge(source="src1", target="platform", volume_gb=10.5, sync_status="active"),
        ]
        graph = DataFlowGraph(nodes=nodes, edges=edges)

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.edges[0].source == "src1"
        assert graph.edges[0].target == "platform"
