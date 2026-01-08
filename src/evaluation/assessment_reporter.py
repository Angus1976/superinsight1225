"""
Multi-dimensional assessment reporting system for SuperInsight platform.

Provides comprehensive assessment reports with:
- Individual, team, and project multi-dimensional assessments
- Assessment indicator comparison analysis
- Assessment trend charts
- Assessment ranking and rating
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.evaluation.models import (
    PerformanceRecordModel,
    PerformanceHistoryModel,
    PerformanceRecord,
    PerformanceWeights,
    PerformancePeriod,
)
from src.ticket.models import TicketModel, AnnotatorSkillModel

logger = logging.getLogger(__name__)


class AssessmentDimension(str, Enum):
    """Assessment dimensions for multi-dimensional analysis."""
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    COMPLIANCE = "compliance"
    IMPROVEMENT = "improvement"
    COLLABORATION = "collaboration"
    INNOVATION = "innovation"


class AssessmentLevel(str, Enum):
    """Assessment performance levels."""
    OUTSTANDING = "outstanding"  # 优秀 (90-100)
    EXCELLENT = "excellent"      # 良好 (80-89)
    GOOD = "good"               # 合格 (70-79)
    AVERAGE = "average"         # 一般 (60-69)
    POOR = "poor"              # 需改进 (50-59)
    UNACCEPTABLE = "unacceptable"  # 不合格 (<50)


@dataclass
class AssessmentMetric:
    """Assessment metric data structure."""
    name: str
    value: float
    weight: float
    target: float
    trend: str  # "up", "down", "stable"
    percentile: float


@dataclass
class DimensionScore:
    """Dimension score with detailed breakdown."""
    dimension: AssessmentDimension
    score: float
    level: AssessmentLevel
    metrics: List[AssessmentMetric]
    improvement_suggestions: List[str]


class MultiDimensionalAssessmentReporter:
    """
    Multi-dimensional assessment reporter.
    
    Generates comprehensive assessment reports across multiple dimensions
    with detailed analysis, comparisons, and improvement recommendations.
    """

    def __init__(self):
        """Initialize the assessment reporter."""
        self.weights = PerformanceWeights()
        
        # Extended dimension weights for comprehensive assessment
        self.dimension_weights = {
            AssessmentDimension.QUALITY: 0.30,
            AssessmentDimension.EFFICIENCY: 0.25,
            AssessmentDimension.COMPLIANCE: 0.20,
            AssessmentDimension.IMPROVEMENT: 0.10,
            AssessmentDimension.COLLABORATION: 0.10,
            AssessmentDimension.INNOVATION: 0.05,
        }

    async def generate_individual_assessment_report(
        self,
        user_id: str,
        period_start: date,
        period_end: date,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate individual multi-dimensional assessment report.

        Args:
            user_id: User identifier
            period_start: Assessment period start
            period_end: Assessment period end
            tenant_id: Optional tenant filter

        Returns:
            Comprehensive individual assessment report
        """
        try:
            with db_manager.get_session() as session:
                # Get performance record
                record = await self._get_performance_record(
                    session, user_id, period_start, period_end, tenant_id
                )
                
                if not record:
                    return {"error": "No performance data found for this period"}

                # Calculate dimension scores
                dimension_scores = await self._calculate_dimension_scores(
                    session, user_id, period_start, period_end, tenant_id
                )

                # Get comparison data
                peer_comparison = await self._get_peer_comparison(
                    session, user_id, period_start, period_end, tenant_id
                )

                # Get trend analysis
                trend_analysis = await self._get_trend_analysis(
                    session, user_id, periods=6
                )

                # Calculate overall assessment
                overall_score = self._calculate_overall_score(dimension_scores)
                overall_level = self._get_assessment_level(overall_score)

                # Generate recommendations
                recommendations = self._generate_improvement_recommendations(dimension_scores)

                report = {
                    "report_type": "individual_assessment",
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "period": {
                        "start": period_start.isoformat(),
                        "end": period_end.isoformat(),
                        "type": "monthly"
                    },
                    "overall_assessment": {
                        "score": round(overall_score, 2),
                        "level": overall_level.value,
                        "percentile": peer_comparison.get("percentile", 0),
                        "rank": peer_comparison.get("rank", 0),
                        "total_assessed": peer_comparison.get("total", 0)
                    },
                    "dimension_scores": [
                        {
                            "dimension": ds.dimension.value,
                            "score": round(ds.score, 2),
                            "level": ds.level.value,
                            "weight": self.dimension_weights[ds.dimension],
                            "metrics": [
                                {
                                    "name": m.name,
                                    "value": round(m.value, 3),
                                    "weight": m.weight,
                                    "target": m.target,
                                    "trend": m.trend,
                                    "percentile": round(m.percentile, 1)
                                }
                                for m in ds.metrics
                            ],
                            "suggestions": ds.improvement_suggestions
                        }
                        for ds in dimension_scores
                    ],
                    "trend_analysis": trend_analysis,
                    "peer_comparison": peer_comparison,
                    "recommendations": recommendations,
                    "generated_at": datetime.now().isoformat()
                }

                logger.info(f"Generated individual assessment report for {user_id}")
                return report

        except Exception as e:
            logger.error(f"Error generating individual assessment report: {e}")
            return {"error": str(e)}

    async def generate_team_assessment_report(
        self,
        tenant_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """
        Generate team multi-dimensional assessment report.

        Args:
            tenant_id: Team/tenant identifier
            period_start: Assessment period start
            period_end: Assessment period end

        Returns:
            Team assessment report with comparisons
        """
        try:
            with db_manager.get_session() as session:
                # Get all team members' records
                records = session.execute(
                    select(PerformanceRecordModel).where(
                        and_(
                            PerformanceRecordModel.tenant_id == tenant_id,
                            PerformanceRecordModel.period_start >= period_start,
                            PerformanceRecordModel.period_end <= period_end
                        )
                    )
                ).scalars().all()

                if not records:
                    return {"error": "No team performance data found"}

                # Calculate team statistics
                team_stats = self._calculate_team_statistics(records)

                # Get individual assessments for all members
                member_assessments = []
                for record in records:
                    dimension_scores = await self._calculate_dimension_scores(
                        session, record.user_id, period_start, period_end, tenant_id
                    )
                    overall_score = self._calculate_overall_score(dimension_scores)
                    
                    member_assessments.append({
                        "user_id": record.user_id,
                        "overall_score": round(overall_score, 2),
                        "level": self._get_assessment_level(overall_score).value,
                        "dimension_scores": {
                            ds.dimension.value: round(ds.score, 2)
                            for ds in dimension_scores
                        }
                    })

                # Sort by overall score
                member_assessments.sort(key=lambda x: x["overall_score"], reverse=True)

                # Add rankings
                for i, assessment in enumerate(member_assessments, 1):
                    assessment["rank"] = i

                # Identify top performers and improvement needs
                top_performers = member_assessments[:3]
                needs_improvement = [
                    a for a in member_assessments 
                    if a["overall_score"] < 70
                ]

                # Calculate dimension distribution
                dimension_distribution = self._calculate_dimension_distribution(member_assessments)

                report = {
                    "report_type": "team_assessment",
                    "tenant_id": tenant_id,
                    "period": {
                        "start": period_start.isoformat(),
                        "end": period_end.isoformat(),
                    },
                    "team_summary": {
                        "total_members": len(records),
                        "avg_score": round(team_stats["avg_overall"], 2),
                        "avg_level": self._get_assessment_level(team_stats["avg_overall"]).value,
                        "score_range": {
                            "min": round(team_stats["min_overall"], 2),
                            "max": round(team_stats["max_overall"], 2),
                            "std": round(team_stats["std_overall"], 2)
                        }
                    },
                    "dimension_averages": {
                        dim.value: round(team_stats[f"avg_{dim.value}"], 2)
                        for dim in AssessmentDimension
                    },
                    "member_assessments": member_assessments,
                    "top_performers": top_performers,
                    "needs_improvement": needs_improvement,
                    "dimension_distribution": dimension_distribution,
                    "team_insights": self._generate_team_insights(team_stats, member_assessments),
                    "generated_at": datetime.now().isoformat()
                }

                logger.info(f"Generated team assessment report for {tenant_id}")
                return report

        except Exception as e:
            logger.error(f"Error generating team assessment report: {e}")
            return {"error": str(e)}

    async def generate_project_assessment_report(
        self,
        project_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """
        Generate project-level assessment report.

        Args:
            project_id: Project identifier
            period_start: Assessment period start
            period_end: Assessment period end

        Returns:
            Project assessment report
        """
        try:
            with db_manager.get_session() as session:
                # Get project-related tickets and performance data
                # Note: This assumes project_id is stored in ticket metadata
                project_tickets = session.execute(
                    select(TicketModel).where(
                        and_(
                            TicketModel.metadata.contains({"project_id": project_id}),
                            TicketModel.created_at >= datetime.combine(period_start, datetime.min.time()),
                            TicketModel.created_at <= datetime.combine(period_end, datetime.max.time())
                        )
                    )
                ).scalars().all()

                if not project_tickets:
                    return {"error": "No project data found"}

                # Get unique users involved in project
                project_users = list(set(t.assigned_to for t in project_tickets if t.assigned_to))

                # Calculate project metrics
                project_metrics = self._calculate_project_metrics(project_tickets)

                # Get user assessments for project contributors
                contributor_assessments = []
                for user_id in project_users:
                    dimension_scores = await self._calculate_dimension_scores(
                        session, user_id, period_start, period_end
                    )
                    overall_score = self._calculate_overall_score(dimension_scores)
                    
                    contributor_assessments.append({
                        "user_id": user_id,
                        "overall_score": round(overall_score, 2),
                        "contribution_score": self._calculate_contribution_score(
                            user_id, project_tickets
                        )
                    })

                # Calculate project quality indicators
                quality_indicators = self._calculate_project_quality_indicators(project_tickets)

                report = {
                    "report_type": "project_assessment",
                    "project_id": project_id,
                    "period": {
                        "start": period_start.isoformat(),
                        "end": period_end.isoformat(),
                    },
                    "project_summary": {
                        "total_tickets": len(project_tickets),
                        "total_contributors": len(project_users),
                        "completion_rate": project_metrics["completion_rate"],
                        "avg_resolution_time": project_metrics["avg_resolution_time"],
                        "quality_score": project_metrics["quality_score"]
                    },
                    "quality_indicators": quality_indicators,
                    "contributor_assessments": contributor_assessments,
                    "project_insights": self._generate_project_insights(project_metrics),
                    "generated_at": datetime.now().isoformat()
                }

                logger.info(f"Generated project assessment report for {project_id}")
                return report

        except Exception as e:
            logger.error(f"Error generating project assessment report: {e}")
            return {"error": str(e)}

    async def generate_comparative_assessment_report(
        self,
        comparison_type: str,  # "users", "teams", "periods"
        entities: List[str],
        period_start: date,
        period_end: date,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comparative assessment report.

        Args:
            comparison_type: Type of comparison (users/teams/periods)
            entities: List of entities to compare
            period_start: Assessment period start
            period_end: Assessment period end
            tenant_id: Optional tenant filter

        Returns:
            Comparative assessment report
        """
        try:
            comparisons = []
            
            if comparison_type == "users":
                for user_id in entities:
                    individual_report = await self.generate_individual_assessment_report(
                        user_id, period_start, period_end, tenant_id
                    )
                    if "error" not in individual_report:
                        comparisons.append({
                            "entity_id": user_id,
                            "entity_type": "user",
                            "overall_score": individual_report["overall_assessment"]["score"],
                            "dimension_scores": {
                                ds["dimension"]: ds["score"]
                                for ds in individual_report["dimension_scores"]
                            }
                        })

            elif comparison_type == "teams":
                for team_id in entities:
                    team_report = await self.generate_team_assessment_report(
                        team_id, period_start, period_end
                    )
                    if "error" not in team_report:
                        comparisons.append({
                            "entity_id": team_id,
                            "entity_type": "team",
                            "overall_score": team_report["team_summary"]["avg_score"],
                            "dimension_scores": team_report["dimension_averages"]
                        })

            # Sort by overall score
            comparisons.sort(key=lambda x: x["overall_score"], reverse=True)

            # Add rankings
            for i, comp in enumerate(comparisons, 1):
                comp["rank"] = i

            # Calculate comparison statistics
            scores = [c["overall_score"] for c in comparisons]
            comparison_stats = {
                "count": len(comparisons),
                "avg_score": np.mean(scores) if scores else 0,
                "min_score": min(scores) if scores else 0,
                "max_score": max(scores) if scores else 0,
                "std_score": np.std(scores) if scores else 0
            }

            report = {
                "report_type": "comparative_assessment",
                "comparison_type": comparison_type,
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                },
                "comparison_stats": comparison_stats,
                "comparisons": comparisons,
                "insights": self._generate_comparison_insights(comparisons),
                "generated_at": datetime.now().isoformat()
            }

            logger.info(f"Generated comparative assessment report for {comparison_type}")
            return report

        except Exception as e:
            logger.error(f"Error generating comparative assessment report: {e}")
            return {"error": str(e)}

    async def _get_performance_record(
        self,
        session: Session,
        user_id: str,
        period_start: date,
        period_end: date,
        tenant_id: Optional[str]
    ) -> Optional[PerformanceRecordModel]:
        """Get performance record for the specified period."""
        query = select(PerformanceRecordModel).where(
            and_(
                PerformanceRecordModel.user_id == user_id,
                PerformanceRecordModel.period_start >= period_start,
                PerformanceRecordModel.period_end <= period_end
            )
        )
        
        if tenant_id:
            query = query.where(PerformanceRecordModel.tenant_id == tenant_id)
            
        return session.execute(query).scalar_one_or_none()

    async def _calculate_dimension_scores(
        self,
        session: Session,
        user_id: str,
        period_start: date,
        period_end: date,
        tenant_id: Optional[str] = None
    ) -> List[DimensionScore]:
        """Calculate detailed dimension scores."""
        dimension_scores = []

        # Get performance record
        record = await self._get_performance_record(
            session, user_id, period_start, period_end, tenant_id
        )
        
        if not record:
            return []

        # Quality dimension
        quality_metrics = [
            AssessmentMetric("accuracy_rate", record.accuracy_rate, 0.4, 0.95, "stable", 75.0),
            AssessmentMetric("consistency_score", record.consistency_score, 0.3, 0.90, "up", 80.0),
            AssessmentMetric("error_rate", 1.0 - record.error_rate, 0.3, 0.95, "up", 70.0)
        ]
        quality_score = sum(m.value * m.weight for m in quality_metrics) * 100
        quality_suggestions = self._get_quality_suggestions(record)
        
        dimension_scores.append(DimensionScore(
            AssessmentDimension.QUALITY,
            quality_score,
            self._get_assessment_level(quality_score),
            quality_metrics,
            quality_suggestions
        ))

        # Efficiency dimension
        efficiency_metrics = [
            AssessmentMetric("completion_rate", record.completion_rate, 0.4, 0.95, "stable", 85.0),
            AssessmentMetric("resolution_speed", min(1.0, 28800 / max(1, record.avg_resolution_time)), 0.3, 0.80, "up", 60.0),
            AssessmentMetric("throughput", min(1.0, record.tasks_completed / 20), 0.3, 0.75, "stable", 70.0)
        ]
        efficiency_score = sum(m.value * m.weight for m in efficiency_metrics) * 100
        efficiency_suggestions = self._get_efficiency_suggestions(record)
        
        dimension_scores.append(DimensionScore(
            AssessmentDimension.EFFICIENCY,
            efficiency_score,
            self._get_assessment_level(efficiency_score),
            efficiency_metrics,
            efficiency_suggestions
        ))

        # Compliance dimension
        compliance_metrics = [
            AssessmentMetric("sla_compliance", record.sla_compliance_rate, 0.5, 0.95, "stable", 90.0),
            AssessmentMetric("attendance", record.attendance_rate, 0.3, 0.98, "stable", 95.0),
            AssessmentMetric("rule_adherence", max(0, 1.0 - record.rule_violations / 10), 0.2, 0.90, "up", 80.0)
        ]
        compliance_score = sum(m.value * m.weight for m in compliance_metrics) * 100
        compliance_suggestions = self._get_compliance_suggestions(record)
        
        dimension_scores.append(DimensionScore(
            AssessmentDimension.COMPLIANCE,
            compliance_score,
            self._get_assessment_level(compliance_score),
            compliance_metrics,
            compliance_suggestions
        ))

        # Improvement dimension
        improvement_metrics = [
            AssessmentMetric("improvement_rate", max(0, record.improvement_rate), 0.4, 0.10, "up", 60.0),
            AssessmentMetric("training_completion", record.training_completion, 0.3, 0.90, "stable", 75.0),
            AssessmentMetric("feedback_score", record.feedback_score, 0.3, 0.85, "stable", 70.0)
        ]
        improvement_score = sum(m.value * m.weight for m in improvement_metrics) * 100
        improvement_suggestions = self._get_improvement_suggestions(record)
        
        dimension_scores.append(DimensionScore(
            AssessmentDimension.IMPROVEMENT,
            improvement_score,
            self._get_assessment_level(improvement_score),
            improvement_metrics,
            improvement_suggestions
        ))

        # Collaboration dimension (placeholder - would integrate with collaboration metrics)
        collaboration_score = 75.0  # Default
        collaboration_metrics = [
            AssessmentMetric("team_contribution", 0.75, 0.5, 0.80, "stable", 70.0),
            AssessmentMetric("knowledge_sharing", 0.70, 0.3, 0.75, "up", 65.0),
            AssessmentMetric("peer_feedback", 0.80, 0.2, 0.85, "stable", 80.0)
        ]
        
        dimension_scores.append(DimensionScore(
            AssessmentDimension.COLLABORATION,
            collaboration_score,
            self._get_assessment_level(collaboration_score),
            collaboration_metrics,
            ["Increase participation in team discussions", "Share more knowledge with peers"]
        ))

        # Innovation dimension (placeholder)
        innovation_score = 65.0  # Default
        innovation_metrics = [
            AssessmentMetric("process_improvement", 0.60, 0.6, 0.70, "up", 55.0),
            AssessmentMetric("creative_solutions", 0.70, 0.4, 0.75, "stable", 60.0)
        ]
        
        dimension_scores.append(DimensionScore(
            AssessmentDimension.INNOVATION,
            innovation_score,
            self._get_assessment_level(innovation_score),
            innovation_metrics,
            ["Propose more process improvements", "Think creatively about problem solving"]
        ))

        return dimension_scores

    def _calculate_overall_score(self, dimension_scores: List[DimensionScore]) -> float:
        """Calculate weighted overall assessment score."""
        total_score = 0.0
        total_weight = 0.0
        
        for ds in dimension_scores:
            weight = self.dimension_weights.get(ds.dimension, 0.0)
            total_score += ds.score * weight
            total_weight += weight
            
        return total_score / total_weight if total_weight > 0 else 0.0

    def _get_assessment_level(self, score: float) -> AssessmentLevel:
        """Get assessment level based on score."""
        if score >= 90:
            return AssessmentLevel.OUTSTANDING
        elif score >= 80:
            return AssessmentLevel.EXCELLENT
        elif score >= 70:
            return AssessmentLevel.GOOD
        elif score >= 60:
            return AssessmentLevel.AVERAGE
        elif score >= 50:
            return AssessmentLevel.POOR
        else:
            return AssessmentLevel.UNACCEPTABLE

    async def _get_peer_comparison(
        self,
        session: Session,
        user_id: str,
        period_start: date,
        period_end: date,
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get peer comparison data."""
        try:
            # Get all records for the same period
            query = select(PerformanceRecordModel).where(
                and_(
                    PerformanceRecordModel.period_start >= period_start,
                    PerformanceRecordModel.period_end <= period_end
                )
            )
            
            if tenant_id:
                query = query.where(PerformanceRecordModel.tenant_id == tenant_id)
                
            all_records = session.execute(query).scalars().all()
            
            if not all_records:
                return {}

            # Calculate scores for all users
            user_scores = {}
            for record in all_records:
                dimension_scores = await self._calculate_dimension_scores(
                    session, record.user_id, period_start, period_end, tenant_id
                )
                overall_score = self._calculate_overall_score(dimension_scores)
                user_scores[record.user_id] = overall_score

            # Sort by score
            sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Find user's rank
            rank = None
            for i, (uid, score) in enumerate(sorted_users, 1):
                if uid == user_id:
                    rank = i
                    break

            total = len(sorted_users)
            percentile = ((total - rank + 1) / total) * 100 if rank else 0

            return {
                "rank": rank,
                "total": total,
                "percentile": round(percentile, 1),
                "user_score": user_scores.get(user_id, 0),
                "avg_score": sum(user_scores.values()) / len(user_scores),
                "top_score": max(user_scores.values()) if user_scores else 0
            }

        except Exception as e:
            logger.error(f"Error getting peer comparison: {e}")
            return {}

    async def _get_trend_analysis(
        self,
        session: Session,
        user_id: str,
        periods: int = 6
    ) -> Dict[str, Any]:
        """Get trend analysis for the user."""
        try:
            records = session.execute(
                select(PerformanceRecordModel).where(
                    PerformanceRecordModel.user_id == user_id
                ).order_by(PerformanceRecordModel.period_end.desc()).limit(periods)
            ).scalars().all()

            if len(records) < 2:
                return {"trend": "insufficient_data"}

            records = list(reversed(records))
            
            # Calculate trends for each dimension
            overall_scores = [r.overall_score for r in records]
            quality_scores = [r.quality_score for r in records]
            efficiency_scores = [r.completion_rate for r in records]
            compliance_scores = [r.sla_compliance_rate for r in records]

            return {
                "periods_analyzed": len(records),
                "overall_trend": self._calculate_trend(overall_scores),
                "quality_trend": self._calculate_trend(quality_scores),
                "efficiency_trend": self._calculate_trend(efficiency_scores),
                "compliance_trend": self._calculate_trend(compliance_scores),
                "timeline": [
                    {
                        "period_end": r.period_end.isoformat(),
                        "overall_score": r.overall_score,
                        "quality_score": r.quality_score,
                        "efficiency_score": r.completion_rate,
                        "compliance_score": r.sla_compliance_rate
                    }
                    for r in records
                ]
            }

        except Exception as e:
            logger.error(f"Error getting trend analysis: {e}")
            return {"trend": "error"}

    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend for a series of values."""
        if len(values) < 2:
            return {"direction": "stable", "slope": 0}

        # Simple linear regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        if slope > 0.02:
            direction = "improving"
        elif slope < -0.02:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "slope": round(slope, 4),
            "change": values[-1] - values[0],
            "change_percent": ((values[-1] - values[0]) / values[0] * 100) if values[0] > 0 else 0
        }

    def _generate_improvement_recommendations(
        self,
        dimension_scores: List[DimensionScore]
    ) -> List[Dict[str, Any]]:
        """Generate improvement recommendations based on dimension scores."""
        recommendations = []

        for ds in dimension_scores:
            if ds.score < 70:  # Below good level
                recommendations.append({
                    "dimension": ds.dimension.value,
                    "current_score": round(ds.score, 1),
                    "target_score": 80.0,
                    "priority": "high" if ds.score < 60 else "medium",
                    "suggestions": ds.improvement_suggestions,
                    "expected_impact": "significant" if ds.score < 60 else "moderate"
                })

        # Sort by priority and impact
        recommendations.sort(key=lambda x: (x["priority"] == "high", -x["current_score"]), reverse=True)
        
        return recommendations

    def _calculate_team_statistics(
        self,
        records: List[PerformanceRecordModel]
    ) -> Dict[str, float]:
        """Calculate team-level statistics."""
        if not records:
            return {}

        overall_scores = [r.overall_score for r in records]
        quality_scores = [r.quality_score for r in records]
        efficiency_scores = [r.completion_rate for r in records]
        compliance_scores = [r.sla_compliance_rate for r in records]

        return {
            "avg_overall": np.mean(overall_scores),
            "min_overall": min(overall_scores),
            "max_overall": max(overall_scores),
            "std_overall": np.std(overall_scores),
            "avg_quality": np.mean(quality_scores),
            "avg_efficiency": np.mean(efficiency_scores),
            "avg_compliance": np.mean(compliance_scores),
            "avg_improvement": np.mean([r.improvement_rate for r in records]),
            "avg_collaboration": 75.0,  # Placeholder
            "avg_innovation": 65.0,  # Placeholder
        }

    def _calculate_dimension_distribution(
        self,
        assessments: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, int]]:
        """Calculate distribution of scores across dimensions."""
        distribution = {}
        
        for dim in AssessmentDimension:
            dim_scores = [a["dimension_scores"].get(dim.value, 0) for a in assessments]
            distribution[dim.value] = {
                "outstanding": sum(1 for s in dim_scores if s >= 90),
                "excellent": sum(1 for s in dim_scores if 80 <= s < 90),
                "good": sum(1 for s in dim_scores if 70 <= s < 80),
                "average": sum(1 for s in dim_scores if 60 <= s < 70),
                "poor": sum(1 for s in dim_scores if 50 <= s < 60),
                "unacceptable": sum(1 for s in dim_scores if s < 50)
            }
            
        return distribution

    def _generate_team_insights(
        self,
        team_stats: Dict[str, float],
        assessments: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate insights for team performance."""
        insights = []

        avg_score = team_stats["avg_overall"]
        if avg_score >= 80:
            insights.append("Team performance is excellent overall")
        elif avg_score >= 70:
            insights.append("Team performance is good with room for improvement")
        else:
            insights.append("Team performance needs significant improvement")

        # Check score variance
        std_score = team_stats["std_overall"]
        if std_score > 15:
            insights.append("High performance variance - consider targeted training")
        elif std_score < 5:
            insights.append("Consistent team performance across members")

        # Check dimension strengths/weaknesses
        dimensions = ["quality", "efficiency", "compliance", "improvement"]
        dim_scores = {dim: team_stats[f"avg_{dim}"] for dim in dimensions}
        
        strongest = max(dim_scores, key=dim_scores.get)
        weakest = min(dim_scores, key=dim_scores.get)
        
        insights.append(f"Team strength: {strongest} ({dim_scores[strongest]:.1f})")
        insights.append(f"Improvement area: {weakest} ({dim_scores[weakest]:.1f})")

        return insights

    def _calculate_project_metrics(self, tickets: List[TicketModel]) -> Dict[str, Any]:
        """Calculate project-level metrics."""
        if not tickets:
            return {}

        completed = [t for t in tickets if t.status.value in ["resolved", "closed"]]
        completion_rate = len(completed) / len(tickets)

        resolution_times = []
        for t in completed:
            if t.resolved_at and t.created_at:
                resolution_times.append((t.resolved_at - t.created_at).total_seconds())

        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0

        # Calculate quality score based on SLA compliance
        sla_compliant = sum(1 for t in completed if not t.sla_breached)
        quality_score = (sla_compliant / len(completed)) * 100 if completed else 0

        return {
            "completion_rate": completion_rate,
            "avg_resolution_time": int(avg_resolution_time),
            "quality_score": quality_score,
            "total_tickets": len(tickets),
            "completed_tickets": len(completed)
        }

    def _calculate_contribution_score(
        self,
        user_id: str,
        tickets: List[TicketModel]
    ) -> float:
        """Calculate user's contribution score to the project."""
        user_tickets = [t for t in tickets if t.assigned_to == user_id]
        if not user_tickets:
            return 0.0

        completed = [t for t in user_tickets if t.status.value in ["resolved", "closed"]]
        completion_rate = len(completed) / len(user_tickets)

        # Factor in ticket complexity (using escalation level as proxy)
        complexity_bonus = sum(t.escalation_level * 0.1 for t in completed)

        return min(100.0, (completion_rate * 80) + complexity_bonus)

    def _calculate_project_quality_indicators(
        self,
        tickets: List[TicketModel]
    ) -> Dict[str, Any]:
        """Calculate project quality indicators."""
        if not tickets:
            return {}

        completed = [t for t in tickets if t.status.value in ["resolved", "closed"]]
        
        return {
            "sla_compliance_rate": (sum(1 for t in completed if not t.sla_breached) / len(completed)) * 100 if completed else 0,
            "avg_escalation_level": sum(t.escalation_level for t in tickets) / len(tickets),
            "critical_tickets_ratio": (sum(1 for t in tickets if t.priority.value == "urgent") / len(tickets)) * 100,
            "resolution_efficiency": len(completed) / len(tickets) * 100
        }

    def _generate_project_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate insights for project performance."""
        insights = []

        completion_rate = metrics.get("completion_rate", 0)
        if completion_rate >= 0.9:
            insights.append("Excellent project completion rate")
        elif completion_rate >= 0.7:
            insights.append("Good project progress with room for improvement")
        else:
            insights.append("Project completion rate needs attention")

        quality_score = metrics.get("quality_score", 0)
        if quality_score >= 90:
            insights.append("High quality delivery standards maintained")
        elif quality_score < 70:
            insights.append("Quality standards need improvement")

        return insights

    def _generate_comparison_insights(
        self,
        comparisons: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate insights from comparison analysis."""
        insights = []

        if not comparisons:
            return insights

        scores = [c["overall_score"] for c in comparisons]
        avg_score = np.mean(scores)
        std_score = np.std(scores)

        if std_score > 15:
            insights.append("High performance variance across entities")
        elif std_score < 5:
            insights.append("Consistent performance across entities")

        top_performer = comparisons[0]
        insights.append(f"Top performer: {top_performer['entity_id']} ({top_performer['overall_score']:.1f})")

        if len(comparisons) > 1:
            bottom_performer = comparisons[-1]
            gap = top_performer["overall_score"] - bottom_performer["overall_score"]
            insights.append(f"Performance gap: {gap:.1f} points")

        return insights

    def _get_quality_suggestions(self, record: PerformanceRecordModel) -> List[str]:
        """Get quality improvement suggestions."""
        suggestions = []
        
        if record.accuracy_rate < 0.8:
            suggestions.append("Focus on accuracy improvement through additional training")
        if record.error_rate > 0.2:
            suggestions.append("Reduce error rate by reviewing common mistakes")
        if record.consistency_score < 0.7:
            suggestions.append("Improve consistency through standardized processes")
            
        return suggestions or ["Maintain current quality standards"]

    def _get_efficiency_suggestions(self, record: PerformanceRecordModel) -> List[str]:
        """Get efficiency improvement suggestions."""
        suggestions = []
        
        if record.completion_rate < 0.8:
            suggestions.append("Improve task completion rate through better time management")
        if record.avg_resolution_time > 28800:  # > 8 hours
            suggestions.append("Work on reducing resolution time")
        if record.tasks_completed < 10:
            suggestions.append("Increase throughput by optimizing workflow")
            
        return suggestions or ["Maintain current efficiency levels"]

    def _get_compliance_suggestions(self, record: PerformanceRecordModel) -> List[str]:
        """Get compliance improvement suggestions."""
        suggestions = []
        
        if record.sla_compliance_rate < 0.9:
            suggestions.append("Improve SLA compliance by prioritizing urgent tickets")
        if record.rule_violations > 2:
            suggestions.append("Review and follow established procedures")
        if record.attendance_rate < 0.95:
            suggestions.append("Improve attendance and punctuality")
            
        return suggestions or ["Maintain current compliance standards"]

    def _get_improvement_suggestions(self, record: PerformanceRecordModel) -> List[str]:
        """Get improvement suggestions."""
        suggestions = []
        
        if record.improvement_rate < 0:
            suggestions.append("Focus on continuous improvement initiatives")
        if record.training_completion < 0.8:
            suggestions.append("Complete pending training modules")
        if record.feedback_score < 0.7:
            suggestions.append("Actively seek and apply feedback")
            
        return suggestions or ["Continue current improvement efforts"]