"""Property-based tests for Text-to-SQL Quality Assessment and Monitoring.

This module tests the following properties:
- Property 46: Quality Assessment Completeness
- Property 47: Quality Threshold Enforcement
- Property 48: Quality Trend Detection
- Property 49: Alert Generation
- Property 50: Execution Correctness Validation

Requirements:
- All generated SQL should be assessed for quality
- Quality metrics should trigger alerts when thresholds are breached
- Quality degradation should be detected
- Alerts should be generated and tracked
- Execution correctness should be validated
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import List
from uuid import uuid4
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.text_to_sql.quality_assessment import (
    RagasQualityAssessor,
    QualityAssessmentService,
    QualityConfig,
    FeedbackRating,
)
from src.text_to_sql.quality_monitoring import (
    QualityMonitoringService,
    MetricType,
    AlertSeverity,
    AlertType,
    reset_quality_monitoring_service,
)


# ============================================================================
# Property 46: Quality Assessment Completeness
# ============================================================================

class TestQualityAssessmentCompleteness:
    """Property 46: All generated SQL should be assessed for quality."""

    @pytest.mark.asyncio
    @given(
        num_queries=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100, deadline=None)
    async def test_all_generations_assessed(self, num_queries: int):
        """Test that all SQL generations receive quality assessment."""
        service = QualityAssessmentService()
        assessor = RagasQualityAssessor()

        # Generate and assess SQL
        for i in range(num_queries):
            query = f"Show all users from table_{i}"
            sql = f"SELECT * FROM table_{i};"

            assessment = await service.assess_quality(
                query=query,
                generated_sql=sql,
                database_type="postgresql",
                method_used="template",
            )

            # Verify assessment was created
            assert assessment is not None
            assert assessment.query == query
            assert assessment.generated_sql == sql
            assert len(assessment.scores) > 0
            assert 0.0 <= assessment.overall_score <= 1.0

        # Verify all assessments are stored
        assessments = await service.get_assessments(limit=num_queries)
        assert len(assessments) == num_queries

    @pytest.mark.asyncio
    @given(
        score=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100, deadline=None)
    async def test_assessment_score_bounds(self, score: float):
        """Test that quality scores are always within valid bounds [0, 1]."""
        service = QualityAssessmentService()

        assessment = await service.assess_quality(
            query="Test query",
            generated_sql="SELECT 1;",
            database_type="postgresql",
        )

        # Verify all scores are in valid range
        assert 0.0 <= assessment.overall_score <= 1.0
        for score_obj in assessment.scores:
            assert 0.0 <= score_obj.score <= 1.0
            assert 0.0 <= score_obj.confidence <= 1.0

    @pytest.mark.asyncio
    @given(
        num_dimensions=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    async def test_assessment_has_required_dimensions(self, num_dimensions: int):
        """Test that assessments include required quality dimensions."""
        assessor = RagasQualityAssessor()

        assessment = await assessor.assess(
            query="Get all products",
            generated_sql="SELECT * FROM products;",
            database_type="postgresql",
        )

        # Should have at least syntax, faithfulness, relevance
        assert len(assessment.scores) >= 3

        dimensions = {score.dimension for score in assessment.scores}
        from src.text_to_sql.quality_assessment import QualityDimension

        # Required dimensions
        assert QualityDimension.SYNTAX in dimensions
        assert QualityDimension.FAITHFULNESS in dimensions
        assert QualityDimension.RELEVANCE in dimensions


# ============================================================================
# Property 47: Quality Threshold Enforcement
# ============================================================================

class TestQualityThresholdEnforcement:
    """Property 47: Quality metrics trigger alerts when thresholds breached."""

    @pytest.mark.asyncio
    @given(
        score=st.floats(min_value=0.0, max_value=0.45),  # Below critical threshold
        num_violations=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_critical_threshold_triggers_alert(
        self,
        score: float,
        num_violations: int
    ):
        """Test that critical threshold violations generate alerts."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Record low quality metrics
        for i in range(num_violations):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=score,
                metadata={"query": f"query_{i}"}
            )

        # Check for alerts
        alerts = await service.get_active_alerts(severity=AlertSeverity.CRITICAL)

        # Should have critical alerts
        assert len(alerts) > 0, f"Expected critical alerts for score {score}"

        # Verify alert details
        for alert in alerts:
            assert alert.alert_type == AlertType.THRESHOLD_BREACH
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.current_value is not None
            assert alert.current_value <= 0.50  # Critical threshold

    @pytest.mark.asyncio
    @given(
        score=st.floats(min_value=0.51, max_value=0.69),  # Between warning and critical
        num_violations=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_warning_threshold_triggers_alert(
        self,
        score: float,
        num_violations: int
    ):
        """Test that warning threshold violations generate warnings."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Record medium quality metrics
        for i in range(num_violations):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=score,
                metadata={"query": f"query_{i}"}
            )

        # Check for warnings
        alerts = await service.get_active_alerts(severity=AlertSeverity.WARNING)

        # Should have warning alerts
        assert len(alerts) > 0, f"Expected warning alerts for score {score}"

    @pytest.mark.asyncio
    @given(
        good_score=st.floats(min_value=0.80, max_value=1.0)
    )
    @settings(max_examples=100, deadline=None)
    async def test_good_scores_no_alerts(self, good_score: float):
        """Test that good quality scores don't trigger alerts."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Record good quality metrics
        await service.record_metric(
            metric_type=MetricType.OVERALL_SCORE,
            value=good_score,
        )

        # Should not have threshold breach alerts
        alerts = await service.get_active_alerts(alert_type=AlertType.THRESHOLD_BREACH)
        assert len(alerts) == 0, f"Good score {good_score} should not trigger alerts"


# ============================================================================
# Property 48: Quality Trend Detection
# ============================================================================

class TestQualityTrendDetection:
    """Property 48: Quality degradation should be detected."""

    @pytest.mark.asyncio
    @given(
        degradation_amount=st.floats(min_value=0.15, max_value=0.30)
    )
    @settings(max_examples=100, deadline=None)
    async def test_degradation_detected(self, degradation_amount: float):
        """Test that quality degradation is detected."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Record high quality period
        for i in range(20):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=0.90,
            )

        # Record degraded quality period
        degraded_score = 0.90 - degradation_amount
        for i in range(20):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=degraded_score,
            )

        # Analyze trend
        trend = await service.analyze_trend(
            metric_type=MetricType.OVERALL_SCORE,
            period_minutes=60,
            comparison_period_minutes=60,
        )

        # Should detect degradation
        assert trend.trend_direction == "degrading"
        assert trend.change_percent < -5.0  # At least 5% degradation

    @pytest.mark.asyncio
    @given(
        improvement_amount=st.floats(min_value=0.05, max_value=0.20)
    )
    @settings(max_examples=100, deadline=None)
    async def test_improvement_detected(self, improvement_amount: float):
        """Test that quality improvement is detected."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Record low quality period
        for i in range(20):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=0.70,
            )

        # Record improved quality period
        improved_score = 0.70 + improvement_amount
        for i in range(20):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=improved_score,
            )

        # Analyze trend
        trend = await service.analyze_trend(
            metric_type=MetricType.OVERALL_SCORE,
            period_minutes=60,
            comparison_period_minutes=60,
        )

        # Should detect improvement
        assert trend.trend_direction == "improving"
        assert trend.change_percent > 0.0

    @pytest.mark.asyncio
    async def test_stable_quality_detected(self):
        """Test that stable quality is detected."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Record stable quality
        for i in range(40):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=0.85,
            )

        # Analyze trend
        trend = await service.analyze_trend(
            metric_type=MetricType.OVERALL_SCORE,
            period_minutes=60,
            comparison_period_minutes=60,
        )

        # Should detect stable trend
        assert trend.trend_direction == "stable"
        assert abs(trend.change_percent) < 2.0


# ============================================================================
# Property 49: Alert Generation
# ============================================================================

class TestAlertGeneration:
    """Property 49: Alerts are generated and tracked correctly."""

    @pytest.mark.asyncio
    @given(
        num_alerts=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    async def test_alerts_tracked(self, num_alerts: int):
        """Test that all alerts are tracked."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Generate alerts by recording low scores
        for i in range(num_alerts):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=0.30,  # Critical score
                metadata={"query": f"query_{i}"}
            )

        # Check alert count
        alert_summary = await service.get_alert_summary()
        assert alert_summary["total_alerts"] >= num_alerts

    @pytest.mark.asyncio
    @given(
        num_alerts=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_alert_resolution(self, num_alerts: int):
        """Test that alerts can be resolved."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Generate alerts
        alert_ids = []
        for i in range(num_alerts):
            await service.record_metric(
                metric_type=MetricType.OVERALL_SCORE,
                value=0.40,
            )

        # Get active alerts
        alerts = await service.get_active_alerts()
        initial_count = len(alerts)
        assert initial_count >= num_alerts

        # Resolve some alerts
        for alert in alerts[:min(3, len(alerts))]:
            await service.resolve_alert(alert.id)

        # Check active alerts reduced
        remaining_alerts = await service.get_active_alerts()
        assert len(remaining_alerts) < initial_count

    @pytest.mark.asyncio
    async def test_alert_severity_classification(self):
        """Test that alerts are classified by severity correctly."""
        await reset_quality_monitoring_service()
        service = QualityMonitoringService()

        # Generate critical alert
        await service.record_metric(
            metric_type=MetricType.OVERALL_SCORE,
            value=0.30,  # Critical
        )

        # Generate warning alert
        await service.record_metric(
            metric_type=MetricType.OVERALL_SCORE,
            value=0.65,  # Warning
        )

        # Check severity classification
        critical_alerts = await service.get_active_alerts(severity=AlertSeverity.CRITICAL)
        warning_alerts = await service.get_active_alerts(severity=AlertSeverity.WARNING)

        assert len(critical_alerts) > 0
        assert len(warning_alerts) > 0


# ============================================================================
# Property 50: Execution Correctness Validation
# ============================================================================

class TestExecutionCorrectnessValidation:
    """Property 50: SQL execution correctness is validated."""

    @pytest.mark.asyncio
    async def test_successful_execution_scored_higher(self):
        """Test that successfully executing SQL gets higher score."""
        service = QualityMonitoringService()

        # Mock successful execution
        async def successful_executor(sql):
            from src.text_to_sql.quality_monitoring import ExecutionResult
            return ExecutionResult(
                success=True,
                row_count=10,
                columns=["id", "name"],
                execution_time_ms=100.0,
            )

        assessment = await service.validate_execution(
            generated_sql="SELECT id, name FROM users;",
            database_executor=successful_executor,
        )

        assert assessment.execution_successful
        assert assessment.score >= 0.5

    @pytest.mark.asyncio
    async def test_failed_execution_scored_low(self):
        """Test that failed SQL execution gets low score."""
        service = QualityMonitoringService()

        # Mock failed execution
        async def failed_executor(sql):
            from src.text_to_sql.quality_monitoring import ExecutionResult
            return ExecutionResult(
                success=False,
                error="Table not found",
            )

        assessment = await service.validate_execution(
            generated_sql="SELECT * FROM nonexistent;",
            database_executor=failed_executor,
        )

        assert not assessment.execution_successful
        assert assessment.score == 0.0

    @pytest.mark.asyncio
    async def test_matching_results_perfect_score(self):
        """Test that matching execution results get perfect score."""
        service = QualityMonitoringService()

        # Mock executor with consistent results
        async def consistent_executor(sql):
            from src.text_to_sql.quality_monitoring import ExecutionResult
            return ExecutionResult(
                success=True,
                row_count=5,
                columns=["id", "name"],
                result_hash="abc123",
            )

        assessment = await service.validate_execution(
            generated_sql="SELECT id, name FROM users LIMIT 5;",
            expected_sql="SELECT id, name FROM users LIMIT 5;",
            database_executor=consistent_executor,
        )

        assert assessment.execution_successful
        assert assessment.result_matches_expected
        assert assessment.score == 1.0


# ============================================================================
# Helper functions for running async tests
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
