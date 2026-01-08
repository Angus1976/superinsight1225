"""
Assessment results application system for SuperInsight platform.

Provides functionality to apply assessment results to:
- Billing system integration
- Training program recommendations
- Reward and penalty mechanisms
- Improvement plan generation
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.evaluation.models import (
    PerformanceRecordModel,
    PerformanceStatus,
    PerformancePeriod
)
from src.evaluation.assessment_reporter import MultiDimensionalAssessmentReporter

logger = logging.getLogger(__name__)


class ApplicationType(str, Enum):
    """Types of assessment result applications."""
    BILLING_ADJUSTMENT = "billing_adjustment"
    TRAINING_RECOMMENDATION = "training_recommendation"
    REWARD_CALCULATION = "reward_calculation"
    PENALTY_APPLICATION = "penalty_application"
    IMPROVEMENT_PLAN = "improvement_plan"


class ActionPriority(str, Enum):
    """Priority levels for assessment-driven actions."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BillingAdjustment:
    """Billing adjustment based on assessment results."""
    user_id: str
    period_start: date
    period_end: date
    base_amount: float
    quality_multiplier: float
    efficiency_multiplier: float
    compliance_multiplier: float
    final_amount: float
    adjustment_reason: str
    created_at: datetime


@dataclass
class TrainingRecommendation:
    """Training recommendation based on assessment gaps."""
    user_id: str
    skill_gap: str
    recommended_training: str
    priority: ActionPriority
    estimated_duration: int  # hours
    expected_improvement: float
    deadline: date
    created_at: datetime


@dataclass
class RewardCalculation:
    """Reward calculation based on assessment performance."""
    user_id: str
    period_start: date
    period_end: date
    base_reward: float
    performance_bonus: float
    improvement_bonus: float
    total_reward: float
    reward_reason: str
    created_at: datetime


@dataclass
class ImprovementPlan:
    """Improvement plan based on assessment results."""
    user_id: str
    target_dimension: str
    current_score: float
    target_score: float
    action_items: List[str]
    timeline: int  # days
    success_metrics: List[str]
    created_at: datetime


class AssessmentResultsApplication:
    """
    Assessment results application system.
    
    Applies assessment results to various business processes including
    billing adjustments, training recommendations, rewards, and improvement plans.
    """

    def __init__(self):
        """Initialize the assessment application system."""
        self.reporter = MultiDimensionalAssessmentReporter()
        
        # Configuration for billing adjustments
        self.billing_config = {
            "quality_weight": 0.4,
            "efficiency_weight": 0.3,
            "compliance_weight": 0.3,
            "min_multiplier": 0.7,
            "max_multiplier": 1.3,
            "baseline_score": 75.0
        }
        
        # Configuration for rewards
        self.reward_config = {
            "base_reward_amount": 1000.0,
            "performance_bonus_rate": 0.02,  # 2% per point above baseline
            "improvement_bonus_rate": 0.05,  # 5% per improvement point
            "excellence_threshold": 90.0,
            "improvement_threshold": 5.0
        }

    async def apply_assessment_to_billing(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        base_amount: float,
        tenant_id: Optional[str] = None
    ) -> BillingAdjustment:
        """
        Apply assessment results to billing calculations.

        Args:
            user_id: User identifier
            period_start: Billing period start
            period_end: Billing period end
            base_amount: Base billing amount
            tenant_id: Optional tenant filter

        Returns:
            BillingAdjustment with calculated adjustments
        """
        try:
            # Get assessment report
            assessment_report = await self.reporter.generate_individual_assessment_report(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                tenant_id=tenant_id
            )

            if "error" in assessment_report:
                logger.warning(f"No assessment data for billing adjustment: {assessment_report['error']}")
                return BillingAdjustment(
                    user_id=user_id,
                    period_start=period_start,
                    period_end=period_end,
                    base_amount=base_amount,
                    quality_multiplier=1.0,
                    efficiency_multiplier=1.0,
                    compliance_multiplier=1.0,
                    final_amount=base_amount,
                    adjustment_reason="No assessment data available",
                    created_at=datetime.now()
                )

            # Extract dimension scores
            dimension_scores = {
                ds["dimension"]: ds["score"]
                for ds in assessment_report["dimension_scores"]
            }

            # Calculate multipliers based on performance
            quality_multiplier = self._calculate_billing_multiplier(
                dimension_scores.get("quality", 75.0)
            )
            efficiency_multiplier = self._calculate_billing_multiplier(
                dimension_scores.get("efficiency", 75.0)
            )
            compliance_multiplier = self._calculate_billing_multiplier(
                dimension_scores.get("compliance", 75.0)
            )

            # Calculate weighted final multiplier
            final_multiplier = (
                quality_multiplier * self.billing_config["quality_weight"] +
                efficiency_multiplier * self.billing_config["efficiency_weight"] +
                compliance_multiplier * self.billing_config["compliance_weight"]
            )

            final_amount = base_amount * final_multiplier

            # Generate adjustment reason
            overall_score = assessment_report["overall_assessment"]["score"]
            if overall_score >= 90:
                reason = "Excellent performance - premium billing rate applied"
            elif overall_score >= 80:
                reason = "Good performance - standard billing rate maintained"
            elif overall_score >= 70:
                reason = "Satisfactory performance - minor adjustment applied"
            else:
                reason = "Performance below expectations - billing adjustment applied"

            adjustment = BillingAdjustment(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                base_amount=base_amount,
                quality_multiplier=quality_multiplier,
                efficiency_multiplier=efficiency_multiplier,
                compliance_multiplier=compliance_multiplier,
                final_amount=final_amount,
                adjustment_reason=reason,
                created_at=datetime.now()
            )

            logger.info(f"Applied billing adjustment for {user_id}: {final_multiplier:.3f}x")
            return adjustment

        except Exception as e:
            logger.error(f"Error applying assessment to billing: {e}")
            raise

    async def generate_training_recommendations(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        tenant_id: Optional[str] = None
    ) -> List[TrainingRecommendation]:
        """
        Generate training recommendations based on assessment gaps.

        Args:
            user_id: User identifier
            period_start: Assessment period start
            period_end: Assessment period end
            tenant_id: Optional tenant filter

        Returns:
            List of training recommendations
        """
        try:
            # Get assessment report
            assessment_report = await self.reporter.generate_individual_assessment_report(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                tenant_id=tenant_id
            )

            if "error" in assessment_report:
                return []

            recommendations = []

            # Analyze dimension scores for training needs
            for dimension_data in assessment_report["dimension_scores"]:
                dimension = dimension_data["dimension"]
                score = dimension_data["score"]
                level = dimension_data["level"]

                # Generate recommendations for dimensions below good level
                if score < 80.0:
                    training_rec = self._generate_dimension_training(
                        user_id, dimension, score, level
                    )
                    if training_rec:
                        recommendations.append(training_rec)

            # Add improvement recommendations from assessment
            if "recommendations" in assessment_report:
                for rec in assessment_report["recommendations"]:
                    if rec.get("priority") in ["high", "critical"]:
                        training_rec = self._convert_recommendation_to_training(
                            user_id, rec
                        )
                        if training_rec:
                            recommendations.append(training_rec)

            # Sort by priority
            priority_order = {
                ActionPriority.CRITICAL: 0,
                ActionPriority.HIGH: 1,
                ActionPriority.MEDIUM: 2,
                ActionPriority.LOW: 3
            }
            recommendations.sort(key=lambda x: priority_order[x.priority])

            logger.info(f"Generated {len(recommendations)} training recommendations for {user_id}")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating training recommendations: {e}")
            return []

    async def calculate_performance_rewards(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        tenant_id: Optional[str] = None
    ) -> RewardCalculation:
        """
        Calculate performance-based rewards from assessment results.

        Args:
            user_id: User identifier
            period_start: Reward period start
            period_end: Reward period end
            tenant_id: Optional tenant filter

        Returns:
            RewardCalculation with calculated rewards
        """
        try:
            # Get assessment report
            assessment_report = await self.reporter.generate_individual_assessment_report(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                tenant_id=tenant_id
            )

            base_reward = self.reward_config["base_reward_amount"]
            performance_bonus = 0.0
            improvement_bonus = 0.0

            if "error" not in assessment_report:
                overall_score = assessment_report["overall_assessment"]["score"]
                
                # Calculate performance bonus
                if overall_score > self.reward_config["excellence_threshold"]:
                    performance_bonus = (
                        (overall_score - self.reward_config["excellence_threshold"]) *
                        self.reward_config["performance_bonus_rate"] *
                        base_reward
                    )

                # Calculate improvement bonus from trend analysis
                trend_analysis = assessment_report.get("trend_analysis", {})
                overall_trend = trend_analysis.get("overall_trend", {})
                
                if overall_trend.get("direction") == "improving":
                    change_percent = overall_trend.get("change_percent", 0)
                    if change_percent >= self.reward_config["improvement_threshold"]:
                        improvement_bonus = (
                            change_percent *
                            self.reward_config["improvement_bonus_rate"] *
                            base_reward
                        )

            total_reward = base_reward + performance_bonus + improvement_bonus

            # Generate reward reason
            if performance_bonus > 0 and improvement_bonus > 0:
                reason = "Excellence bonus and improvement bonus awarded"
            elif performance_bonus > 0:
                reason = "Excellence bonus awarded for outstanding performance"
            elif improvement_bonus > 0:
                reason = "Improvement bonus awarded for significant progress"
            else:
                reason = "Base reward - standard performance"

            reward = RewardCalculation(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                base_reward=base_reward,
                performance_bonus=performance_bonus,
                improvement_bonus=improvement_bonus,
                total_reward=total_reward,
                reward_reason=reason,
                created_at=datetime.now()
            )

            logger.info(f"Calculated reward for {user_id}: ${total_reward:.2f}")
            return reward

        except Exception as e:
            logger.error(f"Error calculating performance rewards: {e}")
            raise

    async def generate_improvement_plan(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        tenant_id: Optional[str] = None
    ) -> List[ImprovementPlan]:
        """
        Generate improvement plans based on assessment results.

        Args:
            user_id: User identifier
            period_start: Assessment period start
            period_end: Assessment period end
            tenant_id: Optional tenant filter

        Returns:
            List of improvement plans for different dimensions
        """
        try:
            # Get assessment report
            assessment_report = await self.reporter.generate_individual_assessment_report(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                tenant_id=tenant_id
            )

            if "error" in assessment_report:
                return []

            improvement_plans = []

            # Generate plans for dimensions needing improvement
            for dimension_data in assessment_report["dimension_scores"]:
                dimension = dimension_data["dimension"]
                current_score = dimension_data["score"]
                
                # Create improvement plan for scores below 80
                if current_score < 80.0:
                    plan = self._create_dimension_improvement_plan(
                        user_id, dimension, current_score, dimension_data
                    )
                    improvement_plans.append(plan)

            # Add plans based on specific recommendations
            if "recommendations" in assessment_report:
                for rec in assessment_report["recommendations"]:
                    if rec.get("priority") in ["high", "critical"]:
                        plan = self._create_recommendation_improvement_plan(
                            user_id, rec
                        )
                        if plan:
                            improvement_plans.append(plan)

            logger.info(f"Generated {len(improvement_plans)} improvement plans for {user_id}")
            return improvement_plans

        except Exception as e:
            logger.error(f"Error generating improvement plans: {e}")
            return []

    async def apply_assessment_results_batch(
        self,
        user_ids: List[str],
        period_start: date,
        period_end: date,
        application_types: List[ApplicationType],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply assessment results to multiple users in batch.

        Args:
            user_ids: List of user identifiers
            period_start: Period start date
            period_end: Period end date
            application_types: Types of applications to perform
            tenant_id: Optional tenant filter

        Returns:
            Batch processing results
        """
        try:
            results = {
                "processed_users": 0,
                "successful_applications": 0,
                "failed_applications": 0,
                "billing_adjustments": [],
                "training_recommendations": [],
                "reward_calculations": [],
                "improvement_plans": [],
                "errors": []
            }

            for user_id in user_ids:
                try:
                    results["processed_users"] += 1

                    # Apply billing adjustments
                    if ApplicationType.BILLING_ADJUSTMENT in application_types:
                        # Would need base amount from billing system
                        base_amount = 5000.0  # Placeholder
                        adjustment = await self.apply_assessment_to_billing(
                            user_id, period_start, period_end, base_amount, tenant_id
                        )
                        results["billing_adjustments"].append(adjustment)

                    # Generate training recommendations
                    if ApplicationType.TRAINING_RECOMMENDATION in application_types:
                        recommendations = await self.generate_training_recommendations(
                            user_id, period_start, period_end, tenant_id
                        )
                        results["training_recommendations"].extend(recommendations)

                    # Calculate rewards
                    if ApplicationType.REWARD_CALCULATION in application_types:
                        reward = await self.calculate_performance_rewards(
                            user_id, period_start, period_end, tenant_id
                        )
                        results["reward_calculations"].append(reward)

                    # Generate improvement plans
                    if ApplicationType.IMPROVEMENT_PLAN in application_types:
                        plans = await self.generate_improvement_plan(
                            user_id, period_start, period_end, tenant_id
                        )
                        results["improvement_plans"].extend(plans)

                    results["successful_applications"] += 1

                except Exception as e:
                    results["failed_applications"] += 1
                    results["errors"].append({
                        "user_id": user_id,
                        "error": str(e)
                    })
                    logger.error(f"Error processing user {user_id}: {e}")

            logger.info(f"Batch processing completed: {results['successful_applications']}/{results['processed_users']} successful")
            return results

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            raise

    def _calculate_billing_multiplier(self, score: float) -> float:
        """Calculate billing multiplier based on performance score."""
        baseline = self.billing_config["baseline_score"]
        min_mult = self.billing_config["min_multiplier"]
        max_mult = self.billing_config["max_multiplier"]

        if score >= baseline:
            # Above baseline: linear increase to max multiplier
            excess = score - baseline
            max_excess = 100 - baseline
            multiplier = 1.0 + (excess / max_excess) * (max_mult - 1.0)
        else:
            # Below baseline: linear decrease to min multiplier
            deficit = baseline - score
            max_deficit = baseline
            multiplier = 1.0 - (deficit / max_deficit) * (1.0 - min_mult)

        return max(min_mult, min(max_mult, multiplier))

    def _generate_dimension_training(
        self,
        user_id: str,
        dimension: str,
        score: float,
        level: str
    ) -> Optional[TrainingRecommendation]:
        """Generate training recommendation for a specific dimension."""
        training_map = {
            "quality": {
                "skill_gap": "Quality assurance and accuracy",
                "training": "Advanced Quality Control Training",
                "duration": 16,
                "improvement": 10.0
            },
            "efficiency": {
                "skill_gap": "Time management and productivity",
                "training": "Efficiency and Productivity Workshop",
                "duration": 12,
                "improvement": 8.0
            },
            "compliance": {
                "skill_gap": "Policy adherence and SLA management",
                "training": "Compliance and SLA Training",
                "duration": 8,
                "improvement": 12.0
            },
            "improvement": {
                "skill_gap": "Continuous improvement mindset",
                "training": "Continuous Improvement Methodology",
                "duration": 20,
                "improvement": 15.0
            }
        }

        if dimension not in training_map:
            return None

        training_info = training_map[dimension]
        
        # Determine priority based on score
        if score < 60:
            priority = ActionPriority.CRITICAL
            deadline_days = 14
        elif score < 70:
            priority = ActionPriority.HIGH
            deadline_days = 30
        else:
            priority = ActionPriority.MEDIUM
            deadline_days = 60

        return TrainingRecommendation(
            user_id=user_id,
            skill_gap=training_info["skill_gap"],
            recommended_training=training_info["training"],
            priority=priority,
            estimated_duration=training_info["duration"],
            expected_improvement=training_info["improvement"],
            deadline=date.today() + timedelta(days=deadline_days),
            created_at=datetime.now()
        )

    def _convert_recommendation_to_training(
        self,
        user_id: str,
        recommendation: Dict[str, Any]
    ) -> Optional[TrainingRecommendation]:
        """Convert assessment recommendation to training recommendation."""
        dimension = recommendation.get("dimension")
        priority_str = recommendation.get("priority", "medium")
        
        priority_map = {
            "critical": ActionPriority.CRITICAL,
            "high": ActionPriority.HIGH,
            "medium": ActionPriority.MEDIUM,
            "low": ActionPriority.LOW
        }
        
        priority = priority_map.get(priority_str, ActionPriority.MEDIUM)
        
        # Generate generic training based on dimension
        return self._generate_dimension_training(
            user_id, dimension, recommendation.get("current_score", 70), "average"
        )

    def _create_dimension_improvement_plan(
        self,
        user_id: str,
        dimension: str,
        current_score: float,
        dimension_data: Dict[str, Any]
    ) -> ImprovementPlan:
        """Create improvement plan for a specific dimension."""
        target_score = min(90.0, current_score + 15.0)  # Aim for 15-point improvement
        
        # Generate action items based on dimension
        action_items_map = {
            "quality": [
                "Complete quality assurance training",
                "Implement peer review process",
                "Use quality checklists for all tasks",
                "Attend weekly quality improvement meetings"
            ],
            "efficiency": [
                "Adopt time management techniques",
                "Use productivity tools and automation",
                "Optimize workflow processes",
                "Set daily productivity targets"
            ],
            "compliance": [
                "Review and memorize SLA requirements",
                "Implement compliance tracking system",
                "Attend compliance training sessions",
                "Regular compliance self-assessments"
            ],
            "improvement": [
                "Set monthly improvement goals",
                "Participate in continuous improvement initiatives",
                "Seek regular feedback from supervisors",
                "Document and share best practices"
            ]
        }

        action_items = action_items_map.get(dimension, [
            "Identify specific improvement areas",
            "Create targeted development plan",
            "Seek mentoring and guidance",
            "Track progress regularly"
        ])

        success_metrics = [
            f"Achieve {dimension} score of {target_score:.1f} or higher",
            f"Maintain consistent performance above {current_score + 5:.1f}",
            "Complete all assigned training modules",
            "Receive positive feedback from supervisor"
        ]

        # Timeline based on improvement needed
        improvement_needed = target_score - current_score
        timeline = max(30, min(90, int(improvement_needed * 3)))  # 3 days per point

        return ImprovementPlan(
            user_id=user_id,
            target_dimension=dimension,
            current_score=current_score,
            target_score=target_score,
            action_items=action_items,
            timeline=timeline,
            success_metrics=success_metrics,
            created_at=datetime.now()
        )

    def _create_recommendation_improvement_plan(
        self,
        user_id: str,
        recommendation: Dict[str, Any]
    ) -> Optional[ImprovementPlan]:
        """Create improvement plan from assessment recommendation."""
        dimension = recommendation.get("dimension")
        current_score = recommendation.get("current_score", 70.0)
        target_score = recommendation.get("target_score", 80.0)
        
        if not dimension:
            return None

        return self._create_dimension_improvement_plan(
            user_id, dimension, current_score, {}
        )

    async def get_application_history(
        self,
        user_id: str,
        application_type: Optional[ApplicationType] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get history of assessment result applications for a user.

        Args:
            user_id: User identifier
            application_type: Optional filter by application type
            limit: Maximum results to return

        Returns:
            List of historical applications
        """
        try:
            # This would query a dedicated applications history table
            # For now, return a placeholder structure
            
            history = []
            
            # Simulate historical data
            for i in range(min(limit, 5)):
                days_ago = (i + 1) * 30
                application_date = datetime.now() - timedelta(days=days_ago)
                
                history.append({
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "application_type": ApplicationType.BILLING_ADJUSTMENT.value,
                    "period_start": (application_date.date() - timedelta(days=30)).isoformat(),
                    "period_end": application_date.date().isoformat(),
                    "details": {
                        "base_amount": 5000.0,
                        "final_amount": 5000.0 + (i * 200),
                        "multiplier": 1.0 + (i * 0.04),
                        "reason": "Performance-based adjustment"
                    },
                    "applied_at": application_date.isoformat()
                })

            return history

        except Exception as e:
            logger.error(f"Error getting application history: {e}")
            return []

    async def get_application_summary(
        self,
        tenant_id: Optional[str] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get summary of assessment result applications.

        Args:
            tenant_id: Optional tenant filter
            period_start: Optional period start filter
            period_end: Optional period end filter

        Returns:
            Summary of applications
        """
        try:
            # This would aggregate data from applications history
            # For now, return a placeholder summary
            
            summary = {
                "period": {
                    "start": period_start.isoformat() if period_start else None,
                    "end": period_end.isoformat() if period_end else None
                },
                "tenant_id": tenant_id,
                "totals": {
                    "users_processed": 45,
                    "billing_adjustments": 42,
                    "training_recommendations": 38,
                    "reward_calculations": 45,
                    "improvement_plans": 28
                },
                "billing_impact": {
                    "total_base_amount": 225000.0,
                    "total_adjusted_amount": 238500.0,
                    "average_multiplier": 1.06,
                    "adjustment_range": {"min": 0.85, "max": 1.25}
                },
                "training_stats": {
                    "total_recommendations": 38,
                    "critical_priority": 8,
                    "high_priority": 15,
                    "medium_priority": 12,
                    "low_priority": 3
                },
                "reward_stats": {
                    "total_rewards": 52750.0,
                    "base_rewards": 45000.0,
                    "performance_bonuses": 4500.0,
                    "improvement_bonuses": 3250.0
                },
                "generated_at": datetime.now().isoformat()
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting application summary: {e}")
            return {"error": str(e)}