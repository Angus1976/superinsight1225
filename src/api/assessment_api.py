"""
Assessment reporting API endpoints for SuperInsight platform.

Provides REST API endpoints for:
- Individual assessment reports
- Team assessment reports  
- Project assessment reports
- Comparative assessment reports
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.evaluation.assessment_reporter import MultiDimensionalAssessmentReporter
from src.evaluation.models import PerformancePeriod

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assessment", tags=["Assessment Reports"])


# ==================== Request Models ====================

class AssessmentPeriodRequest(BaseModel):
    """Assessment period request model."""
    start_date: date = Field(..., description="Period start date")
    end_date: date = Field(..., description="Period end date")
    tenant_id: Optional[str] = Field(None, description="Tenant filter")


class IndividualAssessmentRequest(AssessmentPeriodRequest):
    """Individual assessment request model."""
    user_id: str = Field(..., description="User identifier")


class TeamAssessmentRequest(BaseModel):
    """Team assessment request model."""
    tenant_id: str = Field(..., description="Team/tenant identifier")
    start_date: date = Field(..., description="Period start date")
    end_date: date = Field(..., description="Period end date")


class ProjectAssessmentRequest(BaseModel):
    """Project assessment request model."""
    project_id: str = Field(..., description="Project identifier")
    start_date: date = Field(..., description="Period start date")
    end_date: date = Field(..., description="Period end date")


class ComparativeAssessmentRequest(AssessmentPeriodRequest):
    """Comparative assessment request model."""
    comparison_type: str = Field(..., description="Type of comparison (users/teams/periods)")
    entities: List[str] = Field(..., description="List of entities to compare")


# ==================== Response Models ====================

class AssessmentResponse(BaseModel):
    """Base assessment response model."""
    success: bool = Field(default=True)
    message: str = Field(default="Assessment report generated successfully")
    data: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== API Endpoints ====================

@router.post("/individual", response_model=AssessmentResponse)
async def generate_individual_assessment(
    request: IndividualAssessmentRequest
) -> AssessmentResponse:
    """
    Generate individual multi-dimensional assessment report.
    
    Provides comprehensive assessment across multiple dimensions:
    - Quality (accuracy, consistency, error rate)
    - Efficiency (completion rate, resolution time, throughput)
    - Compliance (SLA adherence, attendance, rule violations)
    - Improvement (improvement rate, training, feedback)
    - Collaboration (team contribution, knowledge sharing)
    - Innovation (process improvement, creative solutions)
    """
    try:
        reporter = MultiDimensionalAssessmentReporter()
        
        report = await reporter.generate_individual_assessment_report(
            user_id=request.user_id,
            period_start=request.start_date,
            period_end=request.end_date,
            tenant_id=request.tenant_id
        )
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return AssessmentResponse(
            data=report,
            message=f"Individual assessment report generated for user {request.user_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating individual assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team", response_model=AssessmentResponse)
async def generate_team_assessment(
    request: TeamAssessmentRequest
) -> AssessmentResponse:
    """
    Generate team multi-dimensional assessment report.
    
    Provides team-level assessment including:
    - Team summary statistics
    - Individual member assessments
    - Top performers identification
    - Members needing improvement
    - Dimension distribution analysis
    - Team insights and recommendations
    """
    try:
        reporter = MultiDimensionalAssessmentReporter()
        
        report = await reporter.generate_team_assessment_report(
            tenant_id=request.tenant_id,
            period_start=request.start_date,
            period_end=request.end_date
        )
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return AssessmentResponse(
            data=report,
            message=f"Team assessment report generated for tenant {request.tenant_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating team assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/project", response_model=AssessmentResponse)
async def generate_project_assessment(
    request: ProjectAssessmentRequest
) -> AssessmentResponse:
    """
    Generate project-level assessment report.
    
    Provides project assessment including:
    - Project summary metrics
    - Quality indicators
    - Contributor assessments
    - Project insights and recommendations
    """
    try:
        reporter = MultiDimensionalAssessmentReporter()
        
        report = await reporter.generate_project_assessment_report(
            project_id=request.project_id,
            period_start=request.start_date,
            period_end=request.end_date
        )
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return AssessmentResponse(
            data=report,
            message=f"Project assessment report generated for project {request.project_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating project assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comparative", response_model=AssessmentResponse)
async def generate_comparative_assessment(
    request: ComparativeAssessmentRequest
) -> AssessmentResponse:
    """
    Generate comparative assessment report.
    
    Supports comparison of:
    - Multiple users
    - Multiple teams
    - Multiple time periods
    
    Provides ranking, statistics, and insights.
    """
    try:
        if request.comparison_type not in ["users", "teams", "periods"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid comparison_type. Must be 'users', 'teams', or 'periods'"
            )
        
        if len(request.entities) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 entities required for comparison"
            )
        
        reporter = MultiDimensionalAssessmentReporter()
        
        report = await reporter.generate_comparative_assessment_report(
            comparison_type=request.comparison_type,
            entities=request.entities,
            period_start=request.start_date,
            period_end=request.end_date,
            tenant_id=request.tenant_id
        )
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return AssessmentResponse(
            data=report,
            message=f"Comparative assessment report generated for {len(request.entities)} {request.comparison_type}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating comparative assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/individual/{user_id}", response_model=AssessmentResponse)
async def get_individual_assessment(
    user_id: str,
    start_date: date = Query(..., description="Period start date"),
    end_date: date = Query(..., description="Period end date"),
    tenant_id: Optional[str] = Query(None, description="Tenant filter")
) -> AssessmentResponse:
    """
    Get individual assessment report via GET request.
    
    Convenience endpoint for retrieving individual assessments
    with query parameters.
    """
    try:
        reporter = MultiDimensionalAssessmentReporter()
        
        report = await reporter.generate_individual_assessment_report(
            user_id=user_id,
            period_start=start_date,
            period_end=end_date,
            tenant_id=tenant_id
        )
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return AssessmentResponse(
            data=report,
            message=f"Individual assessment retrieved for user {user_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving individual assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/{tenant_id}", response_model=AssessmentResponse)
async def get_team_assessment(
    tenant_id: str,
    start_date: date = Query(..., description="Period start date"),
    end_date: date = Query(..., description="Period end date")
) -> AssessmentResponse:
    """
    Get team assessment report via GET request.
    
    Convenience endpoint for retrieving team assessments
    with query parameters.
    """
    try:
        reporter = MultiDimensionalAssessmentReporter()
        
        report = await reporter.generate_team_assessment_report(
            tenant_id=tenant_id,
            period_start=start_date,
            period_end=end_date
        )
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return AssessmentResponse(
            data=report,
            message=f"Team assessment retrieved for tenant {tenant_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving team assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dimensions", response_model=AssessmentResponse)
async def get_assessment_dimensions() -> AssessmentResponse:
    """
    Get available assessment dimensions and their descriptions.
    
    Returns information about all assessment dimensions,
    their weights, and what they measure.
    """
    try:
        reporter = MultiDimensionalAssessmentReporter()
        
        dimensions_info = {
            "quality": {
                "weight": reporter.dimension_weights.get("quality", 0.30),
                "description": "Accuracy, consistency, and error rates",
                "metrics": ["accuracy_rate", "consistency_score", "error_rate"]
            },
            "efficiency": {
                "weight": reporter.dimension_weights.get("efficiency", 0.25),
                "description": "Completion rate, resolution time, and throughput",
                "metrics": ["completion_rate", "resolution_speed", "throughput"]
            },
            "compliance": {
                "weight": reporter.dimension_weights.get("compliance", 0.20),
                "description": "SLA adherence, attendance, and rule compliance",
                "metrics": ["sla_compliance", "attendance", "rule_adherence"]
            },
            "improvement": {
                "weight": reporter.dimension_weights.get("improvement", 0.10),
                "description": "Improvement rate, training completion, and feedback",
                "metrics": ["improvement_rate", "training_completion", "feedback_score"]
            },
            "collaboration": {
                "weight": reporter.dimension_weights.get("collaboration", 0.10),
                "description": "Team contribution, knowledge sharing, and peer feedback",
                "metrics": ["team_contribution", "knowledge_sharing", "peer_feedback"]
            },
            "innovation": {
                "weight": reporter.dimension_weights.get("innovation", 0.05),
                "description": "Process improvement and creative solutions",
                "metrics": ["process_improvement", "creative_solutions"]
            }
        }
        
        return AssessmentResponse(
            data={
                "dimensions": dimensions_info,
                "total_weight": sum(d["weight"] for d in dimensions_info.values()),
                "assessment_levels": {
                    "outstanding": "90-100 points",
                    "excellent": "80-89 points", 
                    "good": "70-79 points",
                    "average": "60-69 points",
                    "poor": "50-59 points",
                    "unacceptable": "Below 50 points"
                }
            },
            message="Assessment dimensions information retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving dimensions info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rankings", response_model=AssessmentResponse)
async def get_assessment_rankings(
    start_date: date = Query(..., description="Period start date"),
    end_date: date = Query(..., description="Period end date"),
    tenant_id: Optional[str] = Query(None, description="Tenant filter"),
    dimension: Optional[str] = Query(None, description="Specific dimension to rank by"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results")
) -> AssessmentResponse:
    """
    Get assessment rankings for a period.
    
    Returns top performers ranked by overall score or specific dimension.
    Useful for leaderboards and performance comparisons.
    """
    try:
        # This would integrate with the existing performance ranking system
        # For now, return a placeholder structure
        
        rankings = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "ranking_criteria": dimension or "overall_score",
            "tenant_filter": tenant_id,
            "rankings": [
                {
                    "rank": i + 1,
                    "user_id": f"user_{i+1}",
                    "score": 95.0 - (i * 2.5),
                    "level": "excellent" if i < 3 else "good",
                    "dimension_scores": {
                        "quality": 90.0 - (i * 2),
                        "efficiency": 88.0 - (i * 1.5),
                        "compliance": 92.0 - (i * 1),
                        "improvement": 85.0 - (i * 3)
                    }
                }
                for i in range(min(limit, 10))
            ],
            "statistics": {
                "total_ranked": min(limit, 10),
                "avg_score": 85.5,
                "top_score": 95.0,
                "score_range": 25.0
            }
        }
        
        return AssessmentResponse(
            data=rankings,
            message=f"Assessment rankings retrieved for {dimension or 'overall'} dimension"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{user_id}", response_model=AssessmentResponse)
async def get_assessment_trends(
    user_id: str,
    periods: int = Query(6, ge=2, le=24, description="Number of periods to analyze"),
    tenant_id: Optional[str] = Query(None, description="Tenant filter")
) -> AssessmentResponse:
    """
    Get assessment trend analysis for a user.
    
    Returns historical performance trends across all dimensions
    with trend direction and insights.
    """
    try:
        reporter = MultiDimensionalAssessmentReporter()
        
        # This would use the existing trend analysis functionality
        # For now, return a structured response
        
        trends = {
            "user_id": user_id,
            "periods_analyzed": periods,
            "overall_trend": {
                "direction": "improving",
                "slope": 0.025,
                "change_percent": 8.5
            },
            "dimension_trends": {
                "quality": {"direction": "stable", "change": 2.1},
                "efficiency": {"direction": "improving", "change": 12.3},
                "compliance": {"direction": "stable", "change": -1.2},
                "improvement": {"direction": "improving", "change": 15.7}
            },
            "insights": [
                "Overall performance showing steady improvement",
                "Efficiency gains are the primary driver of improvement",
                "Quality metrics remain consistently high",
                "Compliance slightly declined but within acceptable range"
            ],
            "recommendations": [
                "Continue focus on efficiency improvements",
                "Monitor compliance metrics more closely",
                "Maintain current quality standards"
            ]
        }
        
        return AssessmentResponse(
            data=trends,
            message=f"Assessment trends retrieved for user {user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check ====================

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for assessment API."""
    return {
        "status": "healthy",
        "service": "assessment_api",
        "timestamp": datetime.now().isoformat()
    }