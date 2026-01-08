"""
Unit tests for assessment results application system.

Tests the application of assessment results to:
- Billing adjustments
- Training recommendations
- Performance rewards
- Improvement plans
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from src.evaluation.assessment_application import (
    AssessmentResultsApplication,
    ApplicationType,
    ActionPriority,
    BillingAdjustment,
    TrainingRecommendation,
    RewardCalculation,
    ImprovementPlan
)


class TestAssessmentResultsApplication:
    """Test cases for AssessmentResultsApplication."""

    @pytest.fixture
    def application_system(self):
        """Create assessment application system instance."""
        return AssessmentResultsApplication()

    @pytest.fixture
    def sample_assessment_report(self):
        """Create sample assessment report."""
        return {
            "report_type": "individual_assessment",
            "user_id": "test_user_1",
            "overall_assessment": {
                "score": 85.0,
                "level": "excellent",
                "percentile": 80.0,
                "rank": 5
            },
            "dimension_scores": [
                {
                    "dimension": "quality",
                    "score": 88.0,
                    "level": "excellent",
                    "metrics": []
                },
                {
                    "dimension": "efficiency",
                    "score": 82.0,
                    "level": "excellent",
                    "metrics": []
                },
                {
                    "dimension": "compliance",
                    "score": 90.0,
                    "level": "outstanding",
                    "metrics": []
                },
                {
                    "dimension": "improvement",
                    "score": 75.0,
                    "level": "good",
                    "metrics": []
                }
            ],
            "trend_analysis": {
                "overall_trend": {
                    "direction": "improving",
                    "change_percent": 8.5
                }
            },
            "recommendations": [
                {
                    "dimension": "improvement",
                    "current_score": 75.0,
                    "target_score": 85.0,
                    "priority": "medium"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_apply_assessment_to_billing(self, application_system, sample_assessment_report):
        """Test billing adjustment application."""
        with patch.object(application_system.reporter, 'generate_individual_assessment_report', 
                         return_value=sample_assessment_report):
            
            adjustment = await application_system.apply_assessment_to_billing(
                user_id="test_user_1",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                base_amount=5000.0,
                tenant_id="test_tenant"
            )

            # Verify adjustment structure
            assert isinstance(adjustment, BillingAdjustment)
            assert adjustment.user_id == "test_user_1"
            assert adjustment.base_amount == 5000.0
            assert adjustment.final_amount > 0

            # Verify multipliers are calculated
            assert 0.7 <= adjustment.quality_multiplier <= 1.3
            assert 0.7 <= adjustment.efficiency_multiplier <= 1.3
            assert 0.7 <= adjustment.compliance_multiplier <= 1.3

            # Verify final amount reflects performance
            # With good scores, should be at or above base amount
            assert adjustment.final_amount >= adjustment.base_amount * 0.95

    @pytest.mark.asyncio
    async def test_apply_billing_no_assessment_data(self, application_system):
        """Test billing adjustment when no assessment data exists."""
        with patch.object(application_system.reporter, 'generate_individual_assessment_report',
                         return_value={"error": "No data found"}):
            
            adjustment = await application_system.apply_assessment_to_billing(
                user_id="nonexistent_user",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                base_amount=5000.0
            )

            # Should return default adjustment
            assert adjustment.final_amount == adjustment.base_amount
            assert adjustment.quality_multiplier == 1.0
            assert adjustment.efficiency_multiplier == 1.0
            assert adjustment.compliance_multiplier == 1.0
            assert "No assessment data" in adjustment.adjustment_reason

    @pytest.mark.asyncio
    async def test_generate_training_recommendations(self, application_system, sample_assessment_report):
        """Test training recommendations generation."""
        with patch.object(application_system.reporter, 'generate_individual_assessment_report',
                         return_value=sample_assessment_report):
            
            recommendations = await application_system.generate_training_recommendations(
                user_id="test_user_1",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                tenant_id="test_tenant"
            )

            # Should generate recommendations for dimensions below 80
            assert len(recommendations) > 0
            
            # Check recommendation structure
            for rec in recommendations:
                assert isinstance(rec, TrainingRecommendation)
                assert rec.user_id == "test_user_1"
                assert rec.skill_gap
                assert rec.recommended_training
                assert rec.priority in ActionPriority
                assert rec.estimated_duration > 0
                assert rec.expected_improvement > 0

            # Should be sorted by priority
            priorities = [rec.priority for rec in recommendations]
            priority_values = {
                ActionPriority.CRITICAL: 0,
                ActionPriority.HIGH: 1,
                ActionPriority.MEDIUM: 2,
                ActionPriority.LOW: 3
            }
            for i in range(len(priorities) - 1):
                assert priority_values[priorities[i]] <= priority_values[priorities[i + 1]]

    @pytest.mark.asyncio
    async def test_calculate_performance_rewards(self, application_system, sample_assessment_report):
        """Test performance reward calculation."""
        with patch.object(application_system.reporter, 'generate_individual_assessment_report',
                         return_value=sample_assessment_report):
            
            reward = await application_system.calculate_performance_rewards(
                user_id="test_user_1",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                tenant_id="test_tenant"
            )

            # Verify reward structure
            assert isinstance(reward, RewardCalculation)
            assert reward.user_id == "test_user_1"
            assert reward.base_reward > 0
            assert reward.total_reward >= reward.base_reward

            # With improving trend, should have improvement bonus
            assert reward.improvement_bonus > 0
            assert reward.total_reward == reward.base_reward + reward.performance_bonus + reward.improvement_bonus

    @pytest.mark.asyncio
    async def test_calculate_rewards_no_bonuses(self, application_system):
        """Test reward calculation with no bonuses."""
        # Create assessment report with average performance
        average_report = {
            "overall_assessment": {"score": 75.0},
            "trend_analysis": {
                "overall_trend": {"direction": "stable", "change_percent": 1.0}
            }
        }

        with patch.object(application_system.reporter, 'generate_individual_assessment_report',
                         return_value=average_report):
            
            reward = await application_system.calculate_performance_rewards(
                user_id="test_user_1",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31)
            )

            # Should only have base reward
            assert reward.performance_bonus == 0.0
            assert reward.improvement_bonus == 0.0
            assert reward.total_reward == reward.base_reward

    @pytest.mark.asyncio
    async def test_generate_improvement_plan(self, application_system, sample_assessment_report):
        """Test improvement plan generation."""
        with patch.object(application_system.reporter, 'generate_individual_assessment_report',
                         return_value=sample_assessment_report):
            
            plans = await application_system.generate_improvement_plan(
                user_id="test_user_1",
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                tenant_id="test_tenant"
            )

            # Should generate plans for dimensions needing improvement
            assert len(plans) > 0

            # Check plan structure
            for plan in plans:
                assert isinstance(plan, ImprovementPlan)
                assert plan.user_id == "test_user_1"
                assert plan.target_dimension
                assert plan.current_score < plan.target_score
                assert len(plan.action_items) > 0
                assert len(plan.success_metrics) > 0
                assert plan.timeline > 0

    @pytest.mark.asyncio
    async def test_batch_application(self, application_system, sample_assessment_report):
        """Test batch application processing."""
        user_ids = ["user_1", "user_2", "user_3"]
        
        with patch.object(application_system.reporter, 'generate_individual_assessment_report',
                         return_value=sample_assessment_report):
            
            results = await application_system.apply_assessment_results_batch(
                user_ids=user_ids,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                application_types=[
                    ApplicationType.BILLING_ADJUSTMENT,
                    ApplicationType.TRAINING_RECOMMENDATION,
                    ApplicationType.REWARD_CALCULATION
                ]
            )

            # Verify batch results
            assert results["processed_users"] == 3
            assert results["successful_applications"] == 3
            assert results["failed_applications"] == 0

            # Verify application counts
            assert len(results["billing_adjustments"]) == 3
            assert len(results["training_recommendations"]) >= 0  # May vary based on assessment
            assert len(results["reward_calculations"]) == 3

    @pytest.mark.asyncio
    async def test_batch_application_with_errors(self, application_system):
        """Test batch application with some failures."""
        user_ids = ["user_1", "user_2", "user_3"]
        
        # Mock to simulate error for one user
        def mock_assessment(user_id, *args, **kwargs):
            if user_id == "user_2":
                raise Exception("Assessment error")
            return {
                "overall_assessment": {"score": 80.0},
                "dimension_scores": [],
                "trend_analysis": {"overall_trend": {"direction": "stable"}}
            }

        with patch.object(application_system.reporter, 'generate_individual_assessment_report',
                         side_effect=mock_assessment):
            
            results = await application_system.apply_assessment_results_batch(
                user_ids=user_ids,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                application_types=[ApplicationType.BILLING_ADJUSTMENT]
            )

            # Should process all users but have one failure
            assert results["processed_users"] == 3
            assert results["successful_applications"] == 2
            assert results["failed_applications"] == 1
            assert len(results["errors"]) == 1
            assert results["errors"][0]["user_id"] == "user_2"

    def test_calculate_billing_multiplier(self, application_system):
        """Test billing multiplier calculation."""
        # Test above baseline (75)
        multiplier = application_system._calculate_billing_multiplier(90.0)
        assert multiplier > 1.0
        assert multiplier <= 1.3

        # Test at baseline
        multiplier = application_system._calculate_billing_multiplier(75.0)
        assert multiplier == 1.0

        # Test below baseline
        multiplier = application_system._calculate_billing_multiplier(60.0)
        assert multiplier < 1.0
        assert multiplier >= 0.7

        # Test extreme values
        multiplier = application_system._calculate_billing_multiplier(100.0)
        assert multiplier == 1.3

        multiplier = application_system._calculate_billing_multiplier(0.0)
        assert multiplier == 0.7

    def test_generate_dimension_training(self, application_system):
        """Test dimension-specific training generation."""
        # Test quality dimension
        training = application_system._generate_dimension_training(
            "test_user", "quality", 65.0, "average"
        )
        
        assert training is not None
        assert training.skill_gap == "Quality assurance and accuracy"
        assert training.recommended_training == "Advanced Quality Control Training"
        assert training.priority == ActionPriority.MEDIUM  # 65 score = medium priority

        # Test critical priority (score < 60)
        training = application_system._generate_dimension_training(
            "test_user", "efficiency", 55.0, "poor"
        )
        
        assert training.priority == ActionPriority.CRITICAL
        assert training.deadline == date.today() + timedelta(days=14)

        # Test unknown dimension
        training = application_system._generate_dimension_training(
            "test_user", "unknown_dimension", 70.0, "good"
        )
        
        assert training is None

    def test_create_dimension_improvement_plan(self, application_system):
        """Test dimension improvement plan creation."""
        plan = application_system._create_dimension_improvement_plan(
            "test_user", "quality", 70.0, {}
        )

        assert isinstance(plan, ImprovementPlan)
        assert plan.user_id == "test_user"
        assert plan.target_dimension == "quality"
        assert plan.current_score == 70.0
        assert plan.target_score == 85.0  # 70 + 15
        assert len(plan.action_items) > 0
        assert len(plan.success_metrics) > 0
        assert plan.timeline > 0

        # Timeline should be based on improvement needed
        expected_timeline = max(30, min(90, int(15 * 3)))  # 15 points * 3 days
        assert plan.timeline == expected_timeline

    @pytest.mark.asyncio
    async def test_get_application_history(self, application_system):
        """Test application history retrieval."""
        history = await application_system.get_application_history(
            user_id="test_user",
            application_type=ApplicationType.BILLING_ADJUSTMENT,
            limit=5
        )

        # Should return historical data structure
        assert isinstance(history, list)
        assert len(history) <= 5

        # Check history item structure
        if history:
            item = history[0]
            assert "id" in item
            assert "user_id" in item
            assert "application_type" in item
            assert "details" in item
            assert "applied_at" in item

    @pytest.mark.asyncio
    async def test_get_application_summary(self, application_system):
        """Test application summary retrieval."""
        summary = await application_system.get_application_summary(
            tenant_id="test_tenant",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31)
        )

        # Should return summary structure
        assert "totals" in summary
        assert "billing_impact" in summary
        assert "training_stats" in summary
        assert "reward_stats" in summary

        # Check totals structure
        totals = summary["totals"]
        assert "users_processed" in totals
        assert "billing_adjustments" in totals
        assert "training_recommendations" in totals
        assert "reward_calculations" in totals

    def test_billing_config_validation(self, application_system):
        """Test billing configuration validation."""
        config = application_system.billing_config
        
        # Weights should sum to 1.0
        total_weight = (
            config["quality_weight"] +
            config["efficiency_weight"] +
            config["compliance_weight"]
        )
        assert abs(total_weight - 1.0) < 0.01

        # Multiplier bounds should be reasonable
        assert 0 < config["min_multiplier"] < 1.0
        assert 1.0 < config["max_multiplier"] < 2.0
        assert config["min_multiplier"] < config["max_multiplier"]

    def test_reward_config_validation(self, application_system):
        """Test reward configuration validation."""
        config = application_system.reward_config
        
        # Base reward should be positive
        assert config["base_reward_amount"] > 0

        # Bonus rates should be reasonable
        assert 0 < config["performance_bonus_rate"] < 0.1  # Less than 10%
        assert 0 < config["improvement_bonus_rate"] < 0.2  # Less than 20%

        # Thresholds should be reasonable
        assert 80 <= config["excellence_threshold"] <= 100
        assert 0 < config["improvement_threshold"] <= 10

    def test_application_type_enum(self):
        """Test ApplicationType enum values."""
        expected_types = {
            "billing_adjustment",
            "training_recommendation", 
            "reward_calculation",
            "penalty_application",
            "improvement_plan"
        }
        
        actual_types = {t.value for t in ApplicationType}
        assert actual_types == expected_types

    def test_action_priority_enum(self):
        """Test ActionPriority enum values."""
        expected_priorities = {"critical", "high", "medium", "low"}
        actual_priorities = {p.value for p in ActionPriority}
        assert actual_priorities == expected_priorities

    def test_billing_adjustment_dataclass(self):
        """Test BillingAdjustment dataclass."""
        adjustment = BillingAdjustment(
            user_id="test_user",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            base_amount=5000.0,
            quality_multiplier=1.1,
            efficiency_multiplier=1.05,
            compliance_multiplier=1.15,
            final_amount=5500.0,
            adjustment_reason="Good performance",
            created_at=datetime.now()
        )

        assert adjustment.user_id == "test_user"
        assert adjustment.base_amount == 5000.0
        assert adjustment.final_amount == 5500.0
        assert adjustment.adjustment_reason == "Good performance"

    def test_training_recommendation_dataclass(self):
        """Test TrainingRecommendation dataclass."""
        recommendation = TrainingRecommendation(
            user_id="test_user",
            skill_gap="Quality improvement",
            recommended_training="Quality Training Course",
            priority=ActionPriority.HIGH,
            estimated_duration=16,
            expected_improvement=10.0,
            deadline=date.today() + timedelta(days=30),
            created_at=datetime.now()
        )

        assert recommendation.user_id == "test_user"
        assert recommendation.skill_gap == "Quality improvement"
        assert recommendation.priority == ActionPriority.HIGH
        assert recommendation.estimated_duration == 16
        assert recommendation.expected_improvement == 10.0

    def test_reward_calculation_dataclass(self):
        """Test RewardCalculation dataclass."""
        reward = RewardCalculation(
            user_id="test_user",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            base_reward=1000.0,
            performance_bonus=200.0,
            improvement_bonus=100.0,
            total_reward=1300.0,
            reward_reason="Excellence and improvement",
            created_at=datetime.now()
        )

        assert reward.user_id == "test_user"
        assert reward.base_reward == 1000.0
        assert reward.performance_bonus == 200.0
        assert reward.improvement_bonus == 100.0
        assert reward.total_reward == 1300.0

    def test_improvement_plan_dataclass(self):
        """Test ImprovementPlan dataclass."""
        plan = ImprovementPlan(
            user_id="test_user",
            target_dimension="quality",
            current_score=70.0,
            target_score=85.0,
            action_items=["Complete training", "Practice exercises"],
            timeline=60,
            success_metrics=["Achieve target score", "Complete all actions"],
            created_at=datetime.now()
        )

        assert plan.user_id == "test_user"
        assert plan.target_dimension == "quality"
        assert plan.current_score == 70.0
        assert plan.target_score == 85.0
        assert len(plan.action_items) == 2
        assert plan.timeline == 60