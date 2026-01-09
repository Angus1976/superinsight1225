"""
Business Metrics API endpoints for SuperInsight Platform.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.api.auth import get_current_user
from src.security.models import UserModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/business-metrics", tags=["Business Metrics"])


# Response models
class AnnotationEfficiencyTrend:
    def __init__(self, timestamp: int, datetime: str, annotations_per_hour: float):
        self.timestamp = timestamp
        self.datetime = datetime
        self.annotations_per_hour = annotations_per_hour


class AnnotationEfficiency:
    def __init__(self, average_per_hour: float, total_annotations: int, trends: list):
        self.average_per_hour = average_per_hour
        self.total_annotations = total_annotations
        self.trends = trends


class UserActivityMetrics:
    def __init__(self, active_users: int, total_sessions: int, average_session_duration: float):
        self.active_users = active_users
        self.total_sessions = total_sessions
        self.average_session_duration = average_session_duration


class DashboardSummary:
    def __init__(self, total_tasks: int, completed_tasks: int, pending_tasks: int, 
                 total_annotations: int, average_quality_score: float):
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.pending_tasks = pending_tasks
        self.total_annotations = total_annotations
        self.average_quality_score = average_quality_score


# Metrics endpoints
@router.get("/summary")
async def get_summary(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get dashboard summary metrics."""
    try:
        # Generate mock data for now
        summary = {
            "total_tasks": 150,
            "completed_tasks": 95,
            "pending_tasks": 55,
            "total_annotations": 2850,
            "average_quality_score": 0.87,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return summary
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get summary metrics"
        )


@router.get("/annotation-efficiency")
async def get_annotation_efficiency(
    hours: int = Query(24, ge=1, le=720),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get annotation efficiency metrics."""
    try:
        # Generate mock trend data
        now = datetime.utcnow()
        trends = []
        
        for i in range(hours):
            timestamp = now - timedelta(hours=hours - i - 1)
            trend = {
                "timestamp": int(timestamp.timestamp() * 1000),
                "datetime": timestamp.isoformat(),
                "annotations_per_hour": 15 + (i % 10),
            }
            trends.append(trend)
        
        efficiency = {
            "average_per_hour": 18.5,
            "total_annotations": 444,
            "trends": trends,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return efficiency
    except Exception as e:
        logger.error(f"Error getting annotation efficiency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get annotation efficiency metrics"
        )


@router.get("/user-activity")
async def get_user_activity(
    hours: int = Query(24, ge=1, le=720),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get user activity metrics."""
    try:
        activity = {
            "active_users": 12,
            "total_sessions": 45,
            "average_session_duration": 1850.5,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return activity
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user activity metrics"
        )


@router.get("/ai-models")
async def get_ai_models(
    model_name: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get AI model metrics."""
    try:
        models = {
            "models": [
                {
                    "name": "gpt-4",
                    "usage_count": 150,
                    "average_latency": 1250,
                    "success_rate": 0.98,
                },
                {
                    "name": "claude-3",
                    "usage_count": 120,
                    "average_latency": 980,
                    "success_rate": 0.96,
                },
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
        return models
    except Exception as e:
        logger.error(f"Error getting AI models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get AI model metrics"
        )


@router.get("/projects")
async def get_projects(
    project_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get project metrics."""
    try:
        projects = {
            "projects": [
                {
                    "id": "proj-001",
                    "name": "Project Alpha",
                    "total_tasks": 50,
                    "completed_tasks": 35,
                    "quality_score": 0.89,
                },
                {
                    "id": "proj-002",
                    "name": "Project Beta",
                    "total_tasks": 100,
                    "completed_tasks": 60,
                    "quality_score": 0.85,
                },
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
        return projects
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project metrics"
        )
