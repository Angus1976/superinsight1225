"""
Assessment results application API endpoints for SuperInsight platform.

Provides REST API endpoints for:
- Billing adjustments based on assessments
- Training recommendations from assessment gaps
- Performance reward calculations
- Improvement plan generation
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.evaluation.assessment_application import (
    AssessmentResultsApplication,
    ApplicationType,
    ActionPriority
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assessment/application", tags=["Assessment Application"])


# ==================== Request Models ====================

class BillingAdjustmentRequest(BaseModel):
    """Billing adjustment request model."""
    user_id: str = Field(..., description="User identifier")
    period_start: date = Field(..., description="Billing period start")
    period_end: date = Field(..., description="Billing period end")
    base_amount: float = Field(..., gt=0, description="Base billing amount")
    tenant_id: Optional[str] = Field(None, description="Tenant filter")


class TrainingRecommendationRequest(BaseModel):
    """Training recommendation request model."""
    user_id: str = Field(..., description="User identifier")
    period_start: date = Field(..., description="Assessment period start")
    period_end: date = Field(..., description="Assessment period end")
    tenant_id: Optional[str] = Field(None, description="Tenant filter")


class RewardCalculationRequest(BaseModel):
    """Reward calculation request model."""
    user_id: str = Field(..., description="User identifier")
    period_start: date = Field(..., description="Reward period start")
    period_end: date = Field(..., description="Reward period end")
    tenant_id: Optional[str] = Field(None, description="Tenant filter")


class ImprovementPlanRequest(BaseModel):
    """Improvement plan request model."""
    user_id: str = Field(..., description="User identifier")
    period_start: date = Field(..., description="Assessment period start")
    period_end: date = Field(..., description="Assessment period end")
    tenant_id: Optional[str] = Field(None, description="Tenant filter")


class BatchApplicationRequest(BaseModel):
    """Batch application request model."""
    user_ids: List[str] = Field(..., min_items=1, description="List of user identifiers")
    period_start: date = Field(..., description="Period start date")
    period_end: date = Field(..., description="Period end date")
    application_types: List[ApplicationType] = Field(..., min_items=1, description="Types of applications")
    tenant_id: Optional[str] = Field(None, description="Tenant filter")


# ==================== Response Models ====================

class ApplicationResponse(BaseModel):
    """Base application response model."""
    success: bool = Field(default=True)
    message: str = Field(default="Application completed successfully")
    data: Dict[str, Any] = Field(default_factory=dict)
    applied_at: datetime = Field(default_factory=datetime.now)


# ==================== API Endpoints ====================

@router.post("/billing-adjustment", response_model=ApplicationResponse)
async def apply_billing_adjustment(
    request: BillingAdjustmentRequest
) -> ApplicationResponse:
    """
    Apply assessment results to billing calculations.
    
    Calculates billing adjustments based on:
    - Quality performance (40% weight)
    - Efficiency performance (30% weight)  
    - Compliance performance (30% weight)
    
    Returns adjusted billing amount with detailed breakdown.
    """
    try:
        application_system = AssessmentResultsApplication()
        
        adjustment = await application_system.apply_assessment_to_billing(
            user_id=request.user_id,
            period_start=request.period_start,
            period_end=request.period_end,
            base_amount=request.base_amount,
            tenant_id=request.tenant_id
        )
        
        return ApplicationResponse(
            data={
                "user_id": adjustment.user_id,
                "period": {
                    "start": adjustment.period_start.isoformat(),
                    "end": adjustment.period_end.isoformat()
                },
                "billing_details": {
                    "base_amount": adjustment.base_amount,
                    "final_amount": adjustment.final_amount,
                    "adjustment_amount": adjustment.final_amount - adjustment.base_amount,
                    "adjustment_percentage": ((adjustment.final_amount / adjustment.base_amount) - 1) * 100
                },
                "multipliers": {
                    "quality": adjustment.quality_multiplier,
                    "efficiency": adjustment.efficiency_multiplier,
                    "compliance": adjustment.compliance_multiplier,
                    "final": adjustment.final_amount / adjustment.base_amount
                },
                "reason": adjustment.adjustment_reason
            },
            message=f"Billing adjustment applied for user {request.user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error applying billing adjustment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training-recommendations", response_model=ApplicationResponse)
async def generate_training_recommendations(
    request: TrainingRecommendationRequest
) -> ApplicationResponse:
    """
    Generate training recommendations based on assessment gaps.
    
    Analyzes assessment results to identify:
    - Skill gaps in specific dimensions
    - Recommended training programs
    - Priority levels and timelines
    - Expected improvement outcomes
    """
    try:
        application_system = AssessmentResultsApplication()
        
        recommendations = await application_system.generate_training_recommendations(
            user_id=request.user_id,
            period_start=request.period_start,
            period_end=request.period_end,
            tenant_id=request.tenant_id
        )
        
        return ApplicationResponse(
            data={
                "user_id": request.user_id,
                "period": {
                    "start": request.period_start.isoformat(),
                    "end": request.period_end.isoformat()
                },
                "recommendations_count": len(recommendations),
                "recommendations": [
                    {
                        "skill_gap": rec.skill_gap,
                        "recommended_training": rec.recommended_training,
                        "priority": rec.priority.value,
                        "estimated_duration_hours": rec.estimated_duration,
                        "expected_improvement": rec.expected_improvement,
                        "deadline": rec.deadline.isoformat(),
                        "created_at": rec.created_at.isoformat()
                    }
                    for rec in recommendations
                ],
                "priority_summary": {
                    "critical": sum(1 for r in recommendations if r.priority == ActionPriority.CRITICAL),
                    "high": sum(1 for r in recommendations if r.priority == ActionPriority.HIGH),
                    "medium": sum(1 for r in recommendations if r.priority == ActionPriority.MEDIUM),
                    "low": sum(1 for r in recommendations if r.priority == ActionPriority.LOW)
                }
            },
            message=f"Generated {len(recommendations)} training recommendations for user {request.user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error generating training recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reward-calculation", response_model=ApplicationResponse)
async def calculate_performance_rewards(
    request: RewardCalculationRequest
) -> ApplicationResponse:
    """
    Calculate performance-based rewards from assessment results.
    
    Calculates rewards based on:
    - Base reward amount
    - Performance bonus for excellence (>90 score)
    - Improvement bonus for significant progress
    - Total reward with detailed breakdown
    """
    try:
        application_system = AssessmentResultsApplication()
        
        reward = await application_system.calculate_performance_rewards(
            user_id=request.user_id,
            period_start=request.period_start,
            period_end=request.period_end,
            tenant_id=request.tenant_id
        )
        
        return ApplicationResponse(
            data={
                "user_id": reward.user_id,
                "period": {
                    "start": reward.period_start.isoformat(),
                    "end": reward.period_end.isoformat()
                },
                "reward_details": {
                    "base_reward": reward.base_reward,
                    "performance_bonus": reward.performance_bonus,
                    "improvement_bonus": reward.improvement_bonus,
                    "total_reward": reward.total_reward,
                    "bonus_percentage": ((reward.total_reward / reward.base_reward) - 1) * 100 if reward.base_reward > 0 else 0
                },
                "reason": reward.reward_reason,
                "calculated_at": reward.created_at.isoformat()
            },
            message=f"Calculated performance reward for user {request.user_id}: ${reward.total_reward:.2f}"
        )
        
    except Exception as e:
        logger.error(f"Error calculating performance rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/improvement-plan", response_model=ApplicationResponse)
async def generate_improvement_plan(
    request: ImprovementPlanRequest
) -> ApplicationResponse:
    """
    Generate improvement plans based on assessment results.
    
    Creates targeted improvement plans including:
    - Specific dimensions needing improvement
    - Current vs target scores
    - Actionable improvement items
    - Success metrics and timelines
    """
    try:
        application_system = AssessmentResultsApplication()
        
        plans = await application_system.generate_improvement_plan(
            user_id=request.user_id,
            period_start=request.period_start,
            period_end=request.period_end,
            tenant_id=request.tenant_id
        )
        
        return ApplicationResponse(
            data={
                "user_id": request.user_id,
                "period": {
                    "start": request.period_start.isoformat(),
                    "end": request.period_end.isoformat()
                },
                "plans_count": len(plans),
                "improvement_plans": [
                    {
                        "target_dimension": plan.target_dimension,
                        "current_score": plan.current_score,
                        "target_score": plan.target_score,
                        "improvement_needed": plan.target_score - plan.current_score,
                        "action_items": plan.action_items,
                        "timeline_days": plan.timeline,
                        "success_metrics": plan.success_metrics,
                        "created_at": plan.created_at.isoformat()
                    }
                    for plan in plans
                ],
                "summary": {
                    "total_improvement_points": sum(plan.target_score - plan.current_score for plan in plans),
                    "avg_timeline_days": sum(plan.timeline for plan in plans) / len(plans) if plans else 0,
                    "dimensions_targeted": list(set(plan.target_dimension for plan in plans))
                }
            },
            message=f"Generated {len(plans)} improvement plans for user {request.user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error generating improvement plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-application", response_model=ApplicationResponse)
async def apply_batch_assessment_results(
    request: BatchApplicationRequest
) -> ApplicationResponse:
    """
    Apply assessment results to multiple users in batch.
    
    Performs batch processing for:
    - Multiple users simultaneously
    - Multiple application types
    - Comprehensive results summary
    - Error handling and reporting
    """
    try:
        if len(request.user_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Batch size limited to 100 users maximum"
            )
        
        application_system = AssessmentResultsApplication()
        
        results = await application_system.apply_assessment_results_batch(
            user_ids=request.user_ids,
            period_start=request.period_start,
            period_end=request.period_end,
            application_types=request.application_types,
            tenant_id=request.tenant_id
        )
        
        return ApplicationResponse(
            data={
                "batch_summary": {
                    "total_users": len(request.user_ids),
                    "processed_users": results["processed_users"],
                    "successful_applications": results["successful_applications"],
                    "failed_applications": results["failed_applications"],
                    "success_rate": (results["successful_applications"] / results["processed_users"]) * 100 if results["processed_users"] > 0 else 0
                },
                "application_counts": {
                    "billing_adjustments": len(results["billing_adjustments"]),
                    "training_recommendations": len(results["training_recommendations"]),
                    "reward_calculations": len(results["reward_calculations"]),
                    "improvement_plans": len(results["improvement_plans"])
                },
                "billing_summary": {
                    "total_adjustments": len(results["billing_adjustments"]),
                    "total_base_amount": sum(adj.base_amount for adj in results["billing_adjustments"]),
                    "total_final_amount": sum(adj.final_amount for adj in results["billing_adjustments"]),
                    "avg_multiplier": sum(adj.final_amount / adj.base_amount for adj in results["billing_adjustments"]) / len(results["billing_adjustments"]) if results["billing_adjustments"] else 1.0
                } if ApplicationType.BILLING_ADJUSTMENT in request.application_types else None,
                "reward_summary": {
                    "total_rewards": len(results["reward_calculations"]),
                    "total_amount": sum(reward.total_reward for reward in results["reward_calculations"]),
                    "total_bonuses": sum(reward.performance_bonus + reward.improvement_bonus for reward in results["reward_calculations"])
                } if ApplicationType.REWARD_CALCULATION in request.application_types else None,
                "errors": results["errors"]
            },
            message=f"Batch processing completed: {results['successful_applications']}/{results['processed_users']} users processed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}", response_model=ApplicationResponse)
async def get_application_history(
    user_id: str,
    application_type: Optional[ApplicationType] = Query(None, description="Filter by application type"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
) -> ApplicationResponse:
    """
    Get history of assessment result applications for a user.
    
    Returns historical data including:
    - Previous billing adjustments
    - Training recommendations
    - Reward calculations
    - Improvement plans
    """
    try:
        application_system = AssessmentResultsApplication()
        
        history = await application_system.get_application_history(
            user_id=user_id,
            application_type=application_type,
            limit=limit
        )
        
        return ApplicationResponse(
            data={
                "user_id": user_id,
                "filter": {
                    "application_type": application_type.value if application_type else None,
                    "limit": limit
                },
                "history_count": len(history),
                "history": history
            },
            message=f"Retrieved {len(history)} historical applications for user {user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error getting application history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=ApplicationResponse)
async def get_application_summary(
    tenant_id: Optional[str] = Query(None, description="Tenant filter"),
    period_start: Optional[date] = Query(None, description="Period start filter"),
    period_end: Optional[date] = Query(None, description="Period end filter")
) -> ApplicationResponse:
    """
    Get summary of assessment result applications.
    
    Provides aggregate statistics including:
    - Total applications by type
    - Billing impact analysis
    - Training statistics
    - Reward distributions
    """
    try:
        application_system = AssessmentResultsApplication()
        
        summary = await application_system.get_application_summary(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end
        )
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        return ApplicationResponse(
            data=summary,
            message="Application summary retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=ApplicationResponse)
async def get_application_config() -> ApplicationResponse:
    """
    Get assessment application configuration.
    
    Returns current configuration for:
    - Billing adjustment parameters
    - Reward calculation settings
    - Training recommendation criteria
    - Improvement plan templates
    """
    try:
        application_system = AssessmentResultsApplication()
        
        config = {
            "billing_config": application_system.billing_config,
            "reward_config": application_system.reward_config,
            "application_types": [t.value for t in ApplicationType],
            "action_priorities": [p.value for p in ActionPriority],
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat()
        }
        
        return ApplicationResponse(
            data=config,
            message="Application configuration retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting application config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check ====================

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for assessment application API."""
    return {
        "status": "healthy",
        "service": "assessment_application_api",
        "timestamp": datetime.now().isoformat()
    }