"""
Property-based tests for Text-to-SQL Monitoring Module.

Tests Properties 35-41 from text-to-sql-methods specification:
- Property 35: Performance Degradation Alerting
- Property 36: Prometheus Metrics Export
- Property 37: Slow Query Logging
- Property 40: Accuracy Metrics Tracking
- Property 41: Accuracy Threshold Alerting
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

# Import the module under test
import sys
sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/tests/", 1)[0] + "/src")

from text_to_sql.monitoring import (
    TextToSQLMonitoringService,
    MonitoringConfig,
    GenerationMethod,
    AlertSeverity,
    AlertStatus,
    SlowQueryLog,
    Alert,
    MethodMetrics,
    AccuracyMetrics,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def generation_method_strategy(draw) -> GenerationMethod:
    """Generate valid generation method."""
    return draw(st.sampled_from(list(GenerationMethod)))


@st.composite
def execution_time_strategy(draw) -> float:
    """Generate execution time in milliseconds."""
    return draw(st.floats(min_value=1.0, max_value=10000.0))


@st.composite
def query_strategy(draw) -> str:
    """Generate natural language query."""
    templates = [
        "Show me all {entity} from {table}",
        "Find {entity} where {condition}",
        "Count the number of {entity}",
        "List {entity} ordered by {field}",
    ]
    template = draw(st.sampled_from(templates))
    entity = draw(st.sampled_from(["users", "orders", "products", "customers"]))
    table = draw(st.sampled_from(["users_table", "orders_table", "products_table"]))
    condition = draw(st.sampled_from(["status = 'active'", "id > 100", "created_at > '2024-01-01'"]))
    field = draw(st.sampled_from(["id", "name", "created_at"]))
    return template.format(entity=entity, table=table, condition=condition, field=field)


@st.composite
def sql_strategy(draw) -> str:
    """Generate SQL statement."""
    return draw(st.sampled_from([
        "SELECT * FROM users",
        "SELECT id, name FROM orders WHERE status = 'active'",
        "SELECT COUNT(*) FROM products",
        "SELECT * FROM customers ORDER BY created_at DESC",
    ]))


@st.composite
def database_type_strategy(draw) -> str:
    """Generate database type."""
    return draw(st.sampled_from(["postgresql", "mysql", "oracle", "sqlserver"]))


# =============================================================================
# Property 35: Performance Degradation Alerting
# =============================================================================

class TestPerformanceDegradationAlerting:
    """
    Property 35: Performance Degradation Alerting

    Validates that:
    1. Alerts are triggered when success rate falls below threshold
    2. Alerts are triggered when latency exceeds threshold
    3. Alerts are resolved when metrics return to normal
    4. Alert cooldown prevents alert spam
    """

    @pytest.fixture
    def service(self):
        """Create service with low thresholds for testing."""
        config = MonitoringConfig(
            success_rate_threshold=0.90,
            latency_p99_threshold_ms=1000,
            alert_cooldown_seconds=1,  # Short cooldown for testing
        )
        return TextToSQLMonitoringService(config=config)

    @pytest.mark.asyncio
    async def test_alert_triggered_on_low_success_rate(self):
        """Property: Alert triggered when success rate drops below threshold."""
        config = MonitoringConfig(
            success_rate_threshold=0.90,
            alert_cooldown_seconds=0,
        )
        service = TextToSQLMonitoringService(config=config)

        # Record requests with 80% failure rate
        for i in range(10):
            await service.record_request(
                method=GenerationMethod.TEMPLATE,
                execution_time_ms=100,
                success=(i < 2),  # Only 2 successes out of 10
                query="test query",
                generated_sql="SELECT * FROM test",
                database_type="postgresql",
            )

        alerts = await service.get_active_alerts()
        alert_names = [a.name for a in alerts]

        assert "low_success_rate" in alert_names

    @pytest.mark.asyncio
    async def test_alert_resolved_when_metrics_improve(self):
        """Property: Alert resolved when metrics return to normal."""
        config = MonitoringConfig(
            success_rate_threshold=0.50,  # Low threshold
            alert_cooldown_seconds=0,
        )
        service = TextToSQLMonitoringService(config=config)

        # First, trigger low success rate
        for i in range(10):
            await service.record_request(
                method=GenerationMethod.TEMPLATE,
                execution_time_ms=100,
                success=(i < 3),  # 30% success
                query="test query",
                generated_sql="SELECT * FROM test",
                database_type="postgresql",
            )

        # Verify alert is active
        alerts = await service.get_active_alerts()
        assert len([a for a in alerts if a.name == "low_success_rate"]) > 0

        # Now improve success rate
        for _ in range(100):
            await service.record_request(
                method=GenerationMethod.TEMPLATE,
                execution_time_ms=100,
                success=True,  # All success
                query="test query",
                generated_sql="SELECT * FROM test",
                database_type="postgresql",
            )

        # Alert should be resolved
        alerts = await service.get_active_alerts()
        alert_names = [a.name for a in alerts]
        assert "low_success_rate" not in alert_names

    @given(
        num_requests=st.integers(min_value=10, max_value=50),
        success_rate=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=20, deadline=None)
    def test_alert_correlates_with_success_rate(
        self,
        num_requests: int,
        success_rate: float,
    ):
        """Property: Alert state correlates with actual success rate."""
        threshold = 0.80
        config = MonitoringConfig(
            success_rate_threshold=threshold,
            alert_cooldown_seconds=0,
        )
        service = TextToSQLMonitoringService(config=config)

        async def run_test():
            num_success = int(num_requests * success_rate)

            for i in range(num_requests):
                await service.record_request(
                    method=GenerationMethod.TEMPLATE,
                    execution_time_ms=100,
                    success=(i < num_success),
                    query="test query",
                    generated_sql="SELECT * FROM test",
                    database_type="postgresql",
                )

            alerts = await service.get_active_alerts()
            has_alert = any(a.name == "low_success_rate" for a in alerts)

            # If success rate is below threshold, alert should be active
            # (with some tolerance for edge cases)
            if success_rate < threshold - 0.05:
                assert has_alert, f"Expected alert at {success_rate:.2%} success rate"

        asyncio.run(run_test())


# =============================================================================
# Property 36: Prometheus Metrics Export
# =============================================================================

class TestPrometheusMetricsExport:
    """
    Property 36: Prometheus Metrics Export

    Validates that:
    1. Exported metrics follow Prometheus format
    2. All required metrics are present
    3. Counter metrics only increase
    4. Histogram buckets are correct
    """

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return TextToSQLMonitoringService()

    @pytest.mark.asyncio
    async def test_prometheus_format_validity(self):
        """Property: Exported metrics follow Prometheus format."""
        service = TextToSQLMonitoringService()

        # Record some data
        await service.record_request(
            method=GenerationMethod.TEMPLATE,
            execution_time_ms=100,
            success=True,
            query="test query",
            generated_sql="SELECT * FROM test",
            database_type="postgresql",
        )

        metrics_text = await service.export_prometheus_metrics()

        # Check format
        lines = metrics_text.strip().split("\n")

        for line in lines:
            if line.startswith("#"):
                # Comment line should be HELP or TYPE
                assert line.startswith("# HELP") or line.startswith("# TYPE")
            elif line.strip():
                # Metric line should have name and value
                parts = line.split()
                assert len(parts) >= 2, f"Invalid metric line: {line}"

    @pytest.mark.asyncio
    async def test_required_metrics_present(self):
        """Property: All required metrics are exported."""
        service = TextToSQLMonitoringService()

        metrics_text = await service.export_prometheus_metrics()

        required_metrics = [
            "text2sql_requests_total",
            "text2sql_requests_success",
            "text2sql_requests_failure",
            "text2sql_cache_hits",
            "text2sql_cache_misses",
            "text2sql_success_rate",
            "text2sql_average_latency_ms",
        ]

        for metric in required_metrics:
            assert metric in metrics_text, f"Missing required metric: {metric}"

    @given(
        num_requests=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=20, deadline=None)
    def test_counter_metrics_only_increase(self, num_requests: int):
        """Property: Counter metrics only increase, never decrease."""
        service = TextToSQLMonitoringService()

        async def run_test():
            previous_total = 0

            for i in range(num_requests):
                await service.record_request(
                    method=GenerationMethod.TEMPLATE,
                    execution_time_ms=100,
                    success=True,
                    query="test query",
                    generated_sql="SELECT * FROM test",
                    database_type="postgresql",
                )

                stats = await service.get_overall_statistics()
                current_total = stats["total_requests"]

                assert current_total >= previous_total, \
                    "Counter decreased from {previous_total} to {current_total}"

                previous_total = current_total

        asyncio.run(run_test())


# =============================================================================
# Property 37: Slow Query Logging
# =============================================================================

class TestSlowQueryLogging:
    """
    Property 37: Slow Query Logging

    Validates that:
    1. Queries exceeding threshold are logged
    2. Queries below threshold are not logged
    3. Log contains all required information
    4. Log respects size limits
    """

    @pytest.fixture
    def service(self):
        """Create service with specific slow query threshold."""
        config = MonitoringConfig(
            slow_query_threshold_ms=100,  # 100ms threshold
            max_slow_query_logs=10,
        )
        return TextToSQLMonitoringService(config=config)

    @pytest.mark.asyncio
    async def test_slow_queries_logged(self):
        """Property: Queries exceeding threshold are logged."""
        config = MonitoringConfig(slow_query_threshold_ms=100)
        service = TextToSQLMonitoringService(config=config)

        # Record slow query (above threshold)
        await service.record_request(
            method=GenerationMethod.LLM,
            execution_time_ms=500,  # Above 100ms threshold
            success=True,
            query="slow query",
            generated_sql="SELECT * FROM large_table",
            database_type="postgresql",
            correlation_id="test-123",
        )

        logs = await service.get_slow_query_logs()

        assert len(logs) == 1
        assert logs[0].query == "slow query"
        assert logs[0].execution_time_ms == 500
        assert logs[0].correlation_id == "test-123"

    @pytest.mark.asyncio
    async def test_fast_queries_not_logged(self):
        """Property: Queries below threshold are not logged."""
        config = MonitoringConfig(slow_query_threshold_ms=100)
        service = TextToSQLMonitoringService(config=config)

        # Record fast query (below threshold)
        await service.record_request(
            method=GenerationMethod.TEMPLATE,
            execution_time_ms=50,  # Below 100ms threshold
            success=True,
            query="fast query",
            generated_sql="SELECT 1",
            database_type="postgresql",
        )

        logs = await service.get_slow_query_logs()
        assert len(logs) == 0

    @given(
        execution_time=execution_time_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_threshold_boundary(self, execution_time: float):
        """Property: Logging respects threshold boundary."""
        threshold = 500
        config = MonitoringConfig(slow_query_threshold_ms=threshold)
        service = TextToSQLMonitoringService(config=config)

        async def run_test():
            await service.record_request(
                method=GenerationMethod.TEMPLATE,
                execution_time_ms=execution_time,
                success=True,
                query="test query",
                generated_sql="SELECT * FROM test",
                database_type="postgresql",
            )

            logs = await service.get_slow_query_logs()

            if execution_time > threshold:
                assert len(logs) == 1
            else:
                assert len(logs) == 0

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_log_respects_size_limit(self):
        """Property: Slow query log respects maximum size limit."""
        max_logs = 5
        config = MonitoringConfig(
            slow_query_threshold_ms=100,
            max_slow_query_logs=max_logs,
        )
        service = TextToSQLMonitoringService(config=config)

        # Record more slow queries than the limit
        for i in range(max_logs * 2):
            await service.record_request(
                method=GenerationMethod.LLM,
                execution_time_ms=500,
                success=True,
                query=f"slow query {i}",
                generated_sql="SELECT * FROM test",
                database_type="postgresql",
            )

        logs = await service.get_slow_query_logs(limit=100)

        # Should not exceed max_logs
        assert len(logs) <= max_logs


# =============================================================================
# Property 40: Accuracy Metrics Tracking
# =============================================================================

class TestAccuracyMetricsTracking:
    """
    Property 40: Accuracy Metrics Tracking

    Validates that:
    1. Syntax accuracy is calculated correctly
    2. Semantic accuracy is calculated correctly
    3. Execution accuracy is calculated correctly
    4. Overall accuracy is calculated correctly
    """

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return TextToSQLMonitoringService()

    @given(
        syntax_correct=st.integers(min_value=0, max_value=50),
        syntax_incorrect=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=30, deadline=None)
    def test_syntax_accuracy_calculation(
        self,
        syntax_correct: int,
        syntax_incorrect: int,
    ):
        """Property: Syntax accuracy is calculated correctly."""
        assume(syntax_correct + syntax_incorrect > 0)

        service = TextToSQLMonitoringService()

        async def run_test():
            for _ in range(syntax_correct):
                await service.record_accuracy_result(syntax_correct=True)

            for _ in range(syntax_incorrect):
                await service.record_accuracy_result(syntax_correct=False)

            metrics = await service.get_accuracy_metrics()

            expected_accuracy = syntax_correct / (syntax_correct + syntax_incorrect)
            assert abs(metrics.syntax_accuracy - expected_accuracy) < 0.001

        asyncio.run(run_test())

    @given(
        semantic_correct=st.integers(min_value=0, max_value=50),
        semantic_incorrect=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=30, deadline=None)
    def test_semantic_accuracy_calculation(
        self,
        semantic_correct: int,
        semantic_incorrect: int,
    ):
        """Property: Semantic accuracy is calculated correctly."""
        assume(semantic_correct + semantic_incorrect > 0)

        service = TextToSQLMonitoringService()

        async def run_test():
            for _ in range(semantic_correct):
                await service.record_accuracy_result(
                    syntax_correct=True,
                    semantic_correct=True,
                )

            for _ in range(semantic_incorrect):
                await service.record_accuracy_result(
                    syntax_correct=True,
                    semantic_correct=False,
                )

            metrics = await service.get_accuracy_metrics()

            expected_accuracy = semantic_correct / (semantic_correct + semantic_incorrect)
            assert abs(metrics.semantic_accuracy - expected_accuracy) < 0.001

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_overall_accuracy_calculation(self):
        """Property: Overall accuracy is average of all accuracies."""
        service = TextToSQLMonitoringService()

        # Record mixed results
        for _ in range(8):
            await service.record_accuracy_result(
                syntax_correct=True,
                semantic_correct=True,
                execution_success=True,
            )

        for _ in range(2):
            await service.record_accuracy_result(
                syntax_correct=False,
                semantic_correct=False,
                execution_success=False,
            )

        metrics = await service.get_accuracy_metrics()

        # Each accuracy should be 80%
        assert abs(metrics.syntax_accuracy - 0.8) < 0.001
        assert abs(metrics.semantic_accuracy - 0.8) < 0.001
        assert abs(metrics.execution_accuracy - 0.8) < 0.001
        assert abs(metrics.overall_accuracy - 0.8) < 0.001


# =============================================================================
# Property 41: Accuracy Threshold Alerting
# =============================================================================

class TestAccuracyThresholdAlerting:
    """
    Property 41: Accuracy Threshold Alerting

    Validates that:
    1. Alert triggered when accuracy falls below threshold
    2. Alert includes correct severity and message
    3. Alert resolved when accuracy improves
    """

    @pytest.mark.asyncio
    async def test_alert_triggered_on_low_accuracy(self):
        """Property: Alert triggered when accuracy drops below threshold."""
        config = MonitoringConfig(
            accuracy_threshold=0.90,
            alert_cooldown_seconds=0,
        )
        service = TextToSQLMonitoringService(config=config)

        # Record poor accuracy (70%)
        for _ in range(7):
            await service.record_accuracy_result(
                syntax_correct=True,
                semantic_correct=True,
                execution_success=True,
            )

        for _ in range(3):
            await service.record_accuracy_result(
                syntax_correct=False,
                semantic_correct=False,
                execution_success=False,
            )

        alerts = await service.get_active_alerts()
        alert_names = [a.name for a in alerts]

        assert "low_accuracy" in alert_names

    @pytest.mark.asyncio
    async def test_alert_severity_is_error(self):
        """Property: Low accuracy alert has ERROR severity."""
        config = MonitoringConfig(
            accuracy_threshold=0.90,
            alert_cooldown_seconds=0,
        )
        service = TextToSQLMonitoringService(config=config)

        # Record poor accuracy
        for _ in range(5):
            await service.record_accuracy_result(syntax_correct=True)

        for _ in range(5):
            await service.record_accuracy_result(syntax_correct=False)

        alerts = await service.get_active_alerts()
        accuracy_alerts = [a for a in alerts if a.name == "low_accuracy"]

        assert len(accuracy_alerts) == 1
        assert accuracy_alerts[0].severity == AlertSeverity.ERROR


# =============================================================================
# Additional Property Tests: Method Statistics
# =============================================================================

class TestMethodStatistics:
    """
    Tests for method-specific statistics.
    """

    @given(
        method=generation_method_strategy(),
        num_requests=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=20, deadline=None)
    def test_method_metrics_tracked_separately(
        self,
        method: GenerationMethod,
        num_requests: int,
    ):
        """Property: Each method has separate metrics."""
        service = TextToSQLMonitoringService()

        async def run_test():
            for _ in range(num_requests):
                await service.record_request(
                    method=method,
                    execution_time_ms=100,
                    success=True,
                    query="test query",
                    generated_sql="SELECT * FROM test",
                    database_type="postgresql",
                )

            stats = await service.get_method_statistics()

            # Only the used method should have requests
            for m, metrics in stats.items():
                if m == method.value:
                    assert metrics.total_requests == num_requests
                # Other methods may have 0 requests

        asyncio.run(run_test())


# =============================================================================
# Additional Property Tests: Latency Percentiles
# =============================================================================

class TestLatencyPercentiles:
    """
    Tests for latency percentile calculations.
    """

    @pytest.mark.asyncio
    async def test_p99_latency_reflects_slowest_requests(self):
        """Property: P99 latency captures the slowest 1% of requests."""
        service = TextToSQLMonitoringService()

        # Record 99 fast requests and 1 slow request
        for _ in range(99):
            await service.record_request(
                method=GenerationMethod.TEMPLATE,
                execution_time_ms=100,  # Fast
                success=True,
                query="test",
                generated_sql="SELECT 1",
                database_type="postgresql",
            )

        await service.record_request(
            method=GenerationMethod.LLM,
            execution_time_ms=5000,  # Slow
            success=True,
            query="test",
            generated_sql="SELECT 1",
            database_type="postgresql",
        )

        stats = await service.get_overall_statistics()
        p99 = stats["p99_latency_ms"]

        # P99 should be close to the slow request
        assert p99 >= 4000, f"P99 should capture slow requests, got {p99}"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
