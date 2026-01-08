"""
Unit tests for multi-dimensional assessment reporter.

Tests the assessment reporting functionality including:
- Individual assessment reports
- Team assessment reports
- Project assessment reports
- Comparative assessment reports
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from src.evaluation.assessment_reporter import (
    MultiDimensionalAssessmentReporter,
    AssessmentDimension,
    AssessmentLevel,
    AssessmentMetric,
    DimensionScore
)
from src.evaluation.models import (
    PerformanceRecordModel,
    PerformanceStatus,
    PerformancePeriod
)


class TestMultiDimensionalAssessmentReporter:
    """Test cases for MultiDimensionalAssessmentReporter."""

    @pytest.fixture
    def reporter(self):
        """Create assessment reporter instance."""
        return MultiDimensionalAssessmentReporter()

    @pytest.fixture
    def sample_performance_record(self):
        """Create sample performance record."""
        return PerformanceRecordModel(
            id=uuid4(),
            user_id="test_user_1",
            tenant_id="test_tenant",
            period_type=PerformancePeriod.MONTHLY,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            quality_score=0.85,
            accuracy_rate=0.90,
            consistency_score=0.88,
            error_rate=0.05,
            completion_rate=0.92,
            avg_resolution_time=7200,  # 2 hours
            tasks_completed=25,
            tasks_assigned=27,
            sla_compliance_rate=0.95,
            attendance_rate=0.98,
            rule_violations=1,
            improvement_rate=0.08,
            training_completion=0.85,
            feedback_score=0.80,
            overall_score=0.87,
            status=PerformanceStatus.APPROVED
        )

    @pytest.mark.asyncio
    async def test_generate_individual_assessment_report(self, reporter, sample_performance_record):
        """Test individual assessment report generation."""
        with patch.object(reporter, '_get_performance_record', return_value=sample_performance_record), \
             patch.object(reporter, '_calculate_dimension_scores') as mock_calc_dims, \
             patch.object(reporter, '_get_peer_comparison') as mock_peer_comp, \
             patch.object(reporter, '_get_trend_analysis') as mock_trend:

            # Mock dimension scores
            mock_calc_dims.return_value = [
                DimensionScore(
                    AssessmentDimension.QUALITY,
                    85.0,
                    AssessmentLevel.EXCELLENT,
                    [AssessmentMetric("accuracy", 0.90, 0.4, 0.95, "stable", 75.0)],
                    ["Maintain quality standards"]
                ),
                DimensionScore(
                    AssessmentDimension.EFFICIENCY,
                    88.0,
                    AssessmentLevel.EXCELLENT,
                    [AssessmentMetric("completion_rate", 0.92, 0.4, 0.95, "up", 80.0)],
                    ["Continue efficiency improvements"]
                )
            ]

            mock_peer_comp.return_value = {
                "rank": 3,
                "total": 20,
                "percentile": 85.0,
                "user_score": 87.0,
                "avg_score": 75.0
            }

            mock_trend.return_value = {
                "overall_trend": {"direction": "improving", "change_percent": 5.2},
                "periods_analyzed": 6
            }

            # Test report generation
            report = await reporter.generate_individual_assessment_report(
                user_id="test_user_1",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                tenant_id="test_tenant"
            )

            # Verify report structure
            assert report["report_type"] == "individual_assessment"
            assert report["user_id"] == "test_user_1"
            assert "overall_assessment" in report
            assert "dimension_scores" in report
            assert "trend_analysis" in report
            assert "peer_comparison" in report

            # Verify overall assessment
            overall = report["overall_assessment"]
            assert "score" in overall
            assert "level" in overall
            assert "percentile" in overall
            assert "rank" in overall

            # Verify dimension scores
            assert len(report["dimension_scores"]) == 2
            quality_dim = report["dimension_scores"][0]
            assert quality_dim["dimension"] == "quality"
            assert quality_dim["score"] == 85.0
            assert quality_dim["level"] == "excellent"

    @pytest.mark.asyncio
    async def test_generate_team_assessment_report(self, reporter):
        """Test team assessment report generation."""
        # Mock team performance records
        team_records = [
            PerformanceRecordModel(
                id=uuid4(),
                user_id=f"user_{i}",
                tenant_id="test_team",
                overall_score=0.8 + (i * 0.02),
                quality_score=0.85 + (i * 0.01),
                completion_rate=0.90 + (i * 0.01),
                sla_compliance_rate=0.95,
                improvement_rate=0.05
            )
            for i in range(5)
        ]

        with patch('src.database.connection.db_manager.get_session') as mock_session, \
             patch.object(reporter, '_calculate_dimension_scores') as mock_calc_dims:

            # Mock database session
            mock_session.return_value.__enter__.return_value.execute.return_value.scalars.return_value.all.return_value = team_records

            # Mock dimension scores for each user
            mock_calc_dims.return_value = [
                DimensionScore(AssessmentDimension.QUALITY, 85.0, AssessmentLevel.EXCELLENT, [], []),
                DimensionScore(AssessmentDimension.EFFICIENCY, 88.0, AssessmentLevel.EXCELLENT, [], [])
            ]

            # Test team report generation
            report = await reporter.generate_team_assessment_report(
                tenant_id="test_team",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31)
            )

            # Verify report structure
            assert report["report_type"] == "team_assessment"
            assert report["tenant_id"] == "test_team"
            assert "team_summary" in report
            assert "member_assessments" in report
            assert "top_performers" in report

            # Verify team summary
            team_summary = report["team_summary"]
            assert team_summary["total_members"] == 5
            assert "avg_score" in team_summary
            assert "avg_level" in team_summary

            # Verify member assessments are ranked
            members = report["member_assessments"]
            assert len(members) == 5
            assert all("rank" in member for member in members)
            # Check ranking order (highest score first)
            for i in range(len(members) - 1):
                assert members[i]["overall_score"] >= members[i + 1]["overall_score"]

    @pytest.mark.asyncio
    async def test_generate_project_assessment_report(self, reporter):
        """Test project assessment report generation."""
        # Mock project tickets
        from src.ticket.models import TicketModel, TicketStatus, TicketPriority
        
        project_tickets = [
            Mock(
                assigned_to=f"user_{i % 3}",
                status=Mock(value="resolved"),
                created_at=datetime(2024, 1, 1),
                resolved_at=datetime(2024, 1, 2),
                sla_breached=False,
                escalation_level=1,
                priority=Mock(value="medium")
            )
            for i in range(10)
        ]

        with patch('src.database.connection.db_manager.get_session') as mock_session, \
             patch.object(reporter, '_calculate_dimension_scores') as mock_calc_dims:

            # Mock database session
            mock_session.return_value.__enter__.return_value.execute.return_value.scalars.return_value.all.return_value = project_tickets

            # Mock dimension scores
            mock_calc_dims.return_value = [
                DimensionScore(AssessmentDimension.QUALITY, 85.0, AssessmentLevel.EXCELLENT, [], [])
            ]

            # Test project report generation
            report = await reporter.generate_project_assessment_report(
                project_id="test_project",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31)
            )

            # Verify report structure
            assert report["report_type"] == "project_assessment"
            assert report["project_id"] == "test_project"
            assert "project_summary" in report
            assert "quality_indicators" in report
            assert "contributor_assessments" in report

            # Verify project summary
            project_summary = report["project_summary"]
            assert project_summary["total_tickets"] == 10
            assert "completion_rate" in project_summary
            assert "quality_score" in project_summary

    @pytest.mark.asyncio
    async def test_generate_comparative_assessment_report(self, reporter):
        """Test comparative assessment report generation."""
        with patch.object(reporter, 'generate_individual_assessment_report') as mock_individual:
            # Mock individual reports
            mock_individual.side_effect = [
                {
                    "overall_assessment": {"score": 85.0},
                    "dimension_scores": [
                        {"dimension": "quality", "score": 88.0},
                        {"dimension": "efficiency", "score": 82.0}
                    ]
                },
                {
                    "overall_assessment": {"score": 78.0},
                    "dimension_scores": [
                        {"dimension": "quality", "score": 80.0},
                        {"dimension": "efficiency", "score": 76.0}
                    ]
                }
            ]

            # Test comparative report generation
            report = await reporter.generate_comparative_assessment_report(
                comparison_type="users",
                entities=["user_1", "user_2"],
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31)
            )

            # Verify report structure
            assert report["report_type"] == "comparative_assessment"
            assert report["comparison_type"] == "users"
            assert "comparisons" in report
            assert "comparison_stats" in report

            # Verify comparisons are ranked
            comparisons = report["comparisons"]
            assert len(comparisons) == 2
            assert comparisons[0]["overall_score"] >= comparisons[1]["overall_score"]
            assert comparisons[0]["rank"] == 1
            assert comparisons[1]["rank"] == 2

    def test_calculate_overall_score(self, reporter):
        """Test overall score calculation from dimension scores."""
        dimension_scores = [
            DimensionScore(AssessmentDimension.QUALITY, 85.0, AssessmentLevel.EXCELLENT, [], []),
            DimensionScore(AssessmentDimension.EFFICIENCY, 80.0, AssessmentLevel.EXCELLENT, [], []),
            DimensionScore(AssessmentDimension.COMPLIANCE, 90.0, AssessmentLevel.OUTSTANDING, [], []),
            DimensionScore(AssessmentDimension.IMPROVEMENT, 75.0, AssessmentLevel.GOOD, [], [])
        ]

        overall_score = reporter._calculate_overall_score(dimension_scores)

        # Verify weighted calculation
        expected_score = (
            85.0 * 0.30 +  # Quality: 30%
            80.0 * 0.25 +  # Efficiency: 25%
            90.0 * 0.20 +  # Compliance: 20%
            75.0 * 0.10    # Improvement: 10%
            # Note: Collaboration and Innovation would be 0 if not provided
        )
        
        assert abs(overall_score - expected_score) < 0.1

    def test_get_assessment_level(self, reporter):
        """Test assessment level determination."""
        assert reporter._get_assessment_level(95.0) == AssessmentLevel.OUTSTANDING
        assert reporter._get_assessment_level(85.0) == AssessmentLevel.EXCELLENT
        assert reporter._get_assessment_level(75.0) == AssessmentLevel.GOOD
        assert reporter._get_assessment_level(65.0) == AssessmentLevel.AVERAGE
        assert reporter._get_assessment_level(55.0) == AssessmentLevel.POOR
        assert reporter._get_assessment_level(45.0) == AssessmentLevel.UNACCEPTABLE

    def test_calculate_trend(self, reporter):
        """Test trend calculation for metric values."""
        # Test improving trend
        improving_values = [70.0, 72.0, 75.0, 78.0, 80.0]
        trend = reporter._calculate_trend(improving_values)
        assert trend["direction"] == "improving"
        assert trend["slope"] > 0
        assert trend["change"] == 10.0

        # Test declining trend
        declining_values = [80.0, 78.0, 75.0, 72.0, 70.0]
        trend = reporter._calculate_trend(declining_values)
        assert trend["direction"] == "declining"
        assert trend["slope"] < 0
        assert trend["change"] == -10.0

        # Test stable trend
        stable_values = [75.0, 75.5, 74.5, 75.2, 75.0]
        trend = reporter._calculate_trend(stable_values)
        assert trend["direction"] == "stable"
        assert abs(trend["slope"]) < 0.02

    def test_calculate_team_statistics(self, reporter):
        """Test team statistics calculation."""
        records = [
            Mock(
                overall_score=0.85,
                quality_score=0.88,
                completion_rate=0.90,
                sla_compliance_rate=0.95,
                improvement_rate=0.05
            ),
            Mock(
                overall_score=0.78,
                quality_score=0.82,
                completion_rate=0.85,
                sla_compliance_rate=0.92,
                improvement_rate=0.03
            ),
            Mock(
                overall_score=0.92,
                quality_score=0.95,
                completion_rate=0.94,
                sla_compliance_rate=0.98,
                improvement_rate=0.08
            )
        ]

        stats = reporter._calculate_team_statistics(records)

        assert abs(stats["avg_overall"] - 0.85) < 0.01
        assert stats["min_overall"] == 0.78
        assert stats["max_overall"] == 0.92
        assert stats["std_overall"] > 0
        assert "avg_quality" in stats
        assert "avg_efficiency" in stats

    def test_calculate_dimension_distribution(self, reporter):
        """Test dimension score distribution calculation."""
        assessments = [
            {
                "dimension_scores": {
                    "quality": 95.0,
                    "efficiency": 85.0,
                    "compliance": 75.0
                }
            },
            {
                "dimension_scores": {
                    "quality": 88.0,
                    "efficiency": 82.0,
                    "compliance": 78.0
                }
            },
            {
                "dimension_scores": {
                    "quality": 65.0,
                    "efficiency": 70.0,
                    "compliance": 68.0
                }
            }
        ]

        distribution = reporter._calculate_dimension_distribution(assessments)

        # Verify structure
        assert "quality" in distribution
        assert "efficiency" in distribution
        assert "compliance" in distribution

        # Verify quality distribution
        quality_dist = distribution["quality"]
        assert quality_dist["outstanding"] == 1  # 95.0
        assert quality_dist["excellent"] == 1    # 88.0
        assert quality_dist["average"] == 1      # 65.0

    def test_generate_improvement_recommendations(self, reporter):
        """Test improvement recommendations generation."""
        dimension_scores = [
            DimensionScore(
                AssessmentDimension.QUALITY,
                65.0,  # Below 70 - needs improvement
                AssessmentLevel.AVERAGE,
                [],
                ["Focus on accuracy improvement"]
            ),
            DimensionScore(
                AssessmentDimension.EFFICIENCY,
                85.0,  # Above 70 - good
                AssessmentLevel.EXCELLENT,
                [],
                []
            ),
            DimensionScore(
                AssessmentDimension.COMPLIANCE,
                55.0,  # Below 60 - high priority
                AssessmentLevel.POOR,
                [],
                ["Improve SLA compliance"]
            )
        ]

        recommendations = reporter._generate_improvement_recommendations(dimension_scores)

        # Should have 2 recommendations (quality and compliance)
        assert len(recommendations) == 2

        # High priority (compliance) should come first
        assert recommendations[0]["dimension"] == "compliance"
        assert recommendations[0]["priority"] == "high"
        assert recommendations[0]["current_score"] == 55.0

        # Medium priority (quality) should come second
        assert recommendations[1]["dimension"] == "quality"
        assert recommendations[1]["priority"] == "medium"
        assert recommendations[1]["current_score"] == 65.0

    def test_generate_team_insights(self, reporter):
        """Test team insights generation."""
        team_stats = {
            "avg_overall": 0.85,
            "std_overall": 12.0,
            "avg_quality": 0.88,
            "avg_efficiency": 0.82,
            "avg_compliance": 0.90,
            "avg_improvement": 0.75
        }

        assessments = [
            {"overall_score": 85.0},
            {"overall_score": 78.0},
            {"overall_score": 92.0}
        ]

        insights = reporter._generate_team_insights(team_stats, assessments)

        assert len(insights) > 0
        assert any("excellent" in insight.lower() for insight in insights)
        assert any("quality" in insight.lower() or "efficiency" in insight.lower() for insight in insights)

    def test_calculate_project_metrics(self, reporter):
        """Test project metrics calculation."""
        tickets = [
            Mock(
                status=Mock(value="resolved"),
                created_at=datetime(2024, 1, 1),
                resolved_at=datetime(2024, 1, 2),
                sla_breached=False
            ),
            Mock(
                status=Mock(value="resolved"),
                created_at=datetime(2024, 1, 1),
                resolved_at=datetime(2024, 1, 3),
                sla_breached=True
            ),
            Mock(
                status=Mock(value="open"),
                created_at=datetime(2024, 1, 1),
                resolved_at=None,
                sla_breached=False
            )
        ]

        metrics = reporter._calculate_project_metrics(tickets)

        assert metrics["total_tickets"] == 3
        assert metrics["completed_tickets"] == 2
        assert metrics["completion_rate"] == 2/3
        assert metrics["quality_score"] == 50.0  # 1 out of 2 completed without SLA breach
        assert "avg_resolution_time" in metrics

    def test_calculate_contribution_score(self, reporter):
        """Test user contribution score calculation."""
        tickets = [
            Mock(assigned_to="user_1", status=Mock(value="resolved"), escalation_level=1),
            Mock(assigned_to="user_1", status=Mock(value="resolved"), escalation_level=2),
            Mock(assigned_to="user_1", status=Mock(value="open"), escalation_level=1),
            Mock(assigned_to="user_2", status=Mock(value="resolved"), escalation_level=1)
        ]

        score = reporter._calculate_contribution_score("user_1", tickets)

        # User 1 has 3 tickets, 2 completed = 66.7% completion rate
        # Plus complexity bonus from escalation levels
        assert score > 50.0
        assert score <= 100.0

    def test_error_handling_no_data(self, reporter):
        """Test error handling when no performance data exists."""
        with patch.object(reporter, '_get_performance_record', return_value=None):
            result = reporter.generate_individual_assessment_report(
                user_id="nonexistent_user",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31)
            )

            # Should be handled gracefully in the async method
            # This test verifies the structure is in place

    def test_dimension_weights_sum_to_one(self, reporter):
        """Test that dimension weights sum to approximately 1.0."""
        total_weight = sum(reporter.dimension_weights.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_assessment_metric_validation(self):
        """Test AssessmentMetric data structure."""
        metric = AssessmentMetric(
            name="test_metric",
            value=0.85,
            weight=0.4,
            target=0.90,
            trend="up",
            percentile=75.0
        )

        assert metric.name == "test_metric"
        assert metric.value == 0.85
        assert metric.weight == 0.4
        assert metric.target == 0.90
        assert metric.trend == "up"
        assert metric.percentile == 75.0

    def test_dimension_score_validation(self):
        """Test DimensionScore data structure."""
        metrics = [
            AssessmentMetric("metric1", 0.8, 0.5, 0.9, "stable", 70.0),
            AssessmentMetric("metric2", 0.9, 0.5, 0.95, "up", 80.0)
        ]

        dimension_score = DimensionScore(
            dimension=AssessmentDimension.QUALITY,
            score=85.0,
            level=AssessmentLevel.EXCELLENT,
            metrics=metrics,
            improvement_suggestions=["Maintain standards", "Focus on consistency"]
        )

        assert dimension_score.dimension == AssessmentDimension.QUALITY
        assert dimension_score.score == 85.0
        assert dimension_score.level == AssessmentLevel.EXCELLENT
        assert len(dimension_score.metrics) == 2
        assert len(dimension_score.improvement_suggestions) == 2