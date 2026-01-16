"""
Business Metrics API for SuperInsight Platform.

Provides endpoints for accessing business intelligence metrics including:
- Annotation efficiency and quality trends
- User activity and engagement statistics  
- AI model performance monitoring
- Project progress and completion metrics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.models import UserModel, UserRole


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/business-metrics", tags=["business-metrics"])
security = HTTPBearer(auto_error=False)


# Try to import business_metrics_collector, use mock if not available
try:
    from src.system.business_metrics import business_metrics_collector
    HAS_COLLECTOR = True
except ImportError:
    HAS_COLLECTOR = False
    logger.warning("Business metrics collector not available, using mock data")

# Try to import monitoring modules
try:
    from src.system.monitoring import metrics_collector, performance_monitor
    HAS_MONITORING = True
except ImportError:
    HAS_MONITORING = False
    logger.warning("Monitoring modules not available")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> Optional[UserModel]:
    """Get current authenticated user."""
    if not credentials:
        return None
    try:
        from src.security.controller import SecurityController
        controller = SecurityController()
        payload = controller.verify_token(credentials.credentials)
        if payload:
            return controller.get_user_by_id(payload["user_id"], db)
    except Exception as e:
        logger.warning(f"Failed to authenticate user: {e}")
    return None


def require_analytics_permission(user: Optional[UserModel]) -> bool:
    """Check if user has permission to view analytics."""
    if not user:
        return True  # Allow anonymous access for basic metrics
    # All authenticated users can view analytics
    return True


def require_admin_permission(user: Optional[UserModel]) -> bool:
    """Check if user has admin permission."""
    if not user:
        return False
    return user.role == UserRole.ADMIN


def require_annotate_permission(user: Optional[UserModel]) -> bool:
    """Check if user has annotate permission."""
    if not user:
        return False
    return user.role in [UserRole.ADMIN, UserRole.BUSINESS_EXPERT, UserRole.TECHNICAL_EXPERT, UserRole.CONTRACTOR]


# Helper functions for trend calculation
def _calculate_trend_direction(values: List[float]) -> str:
    """Calculate trend direction from a list of values."""
    if len(values) < 2:
        return "stable"
    
    first_half = values[:len(values)//2]
    second_half = values[len(values)//2:]
    
    if not first_half or not second_half:
        return "stable"
    
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    
    if second_avg > first_avg * 1.05:
        return "increasing"
    elif second_avg < first_avg * 0.95:
        return "decreasing"
    else:
        return "stable"


def _calculate_completion_velocity(project_metrics: List) -> float:
    """Calculate project completion velocity (percentage per day)."""
    if len(project_metrics) < 2:
        return 0.0
    
    first_metric = project_metrics[0]
    last_metric = project_metrics[-1]
    
    time_diff_days = (last_metric.timestamp - first_metric.timestamp) / 86400
    completion_diff = last_metric.completion_percentage - first_metric.completion_percentage
    
    return completion_diff / time_diff_days if time_diff_days > 0 else 0.0


def _expected_completion_percentage(project_metrics: List) -> float:
    """Calculate expected completion percentage based on project timeline."""
    if not project_metrics:
        return 0.0
    return 50.0  # Placeholder


def _get_mock_summary() -> Dict[str, Any]:
    """Return mock business summary data."""
    return {
        "timestamp": datetime.now().timestamp(),
        "annotation_efficiency": {
            "annotations_per_hour": 15.5,
            "quality_score": 0.92,
            "completion_rate": 0.85
        },
        "user_activity": {
            "active_users": 12,
            "new_users": 2,
            "peak_concurrent": 8
        },
        "ai_models": {
            "total_inferences": 5000,
            "avg_inference_time": 0.5,
            "success_rate": 0.98
        },
        "projects": {
            "active_projects": 5,
            "completed_projects": 3,
            "avg_completion": 0.72
        }
    }



@router.get("/summary")
async def get_business_summary(
    tenant_id: str = Query("default_tenant", description="Tenant ID"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive business metrics summary.
    
    Provides high-level overview of all business metrics including
    annotation efficiency, user activity, AI performance, and project progress.
    """
    try:
        if HAS_COLLECTOR:
            summary = business_metrics_collector.get_business_summary()
            
            result = {
                "business_metrics": summary,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add system metrics if available
            if HAS_MONITORING:
                try:
                    system_summary = metrics_collector.get_all_metrics_summary()
                    performance_summary = performance_monitor.get_performance_summary()
                    result["system_performance"] = {
                        "active_requests": performance_summary.get("active_requests", 0),
                        "avg_request_duration": performance_summary.get("avg_request_duration", {}),
                        "database_performance": performance_summary.get("database_performance", {}),
                        "ai_performance": performance_summary.get("ai_performance", {})
                    }
                except Exception as e:
                    logger.warning(f"Failed to get system metrics: {e}")
            
            return result
        else:
            return {
                "business_metrics": _get_mock_summary(),
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Failed to get business metrics summary: {e}")
        return {
            "business_metrics": _get_mock_summary(),
            "tenant_id": tenant_id,
            "timestamp": datetime.now().isoformat()
        }


@router.get("/annotation-efficiency")
async def get_annotation_efficiency_trends(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze (1-168)"),
    tenant_id: str = Query("default_tenant", description="Tenant ID"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get annotation efficiency and quality trends.
    
    Provides detailed metrics on annotation productivity, quality scores,
    completion rates, and revision patterns over the specified time period.
    """
    try:
        if HAS_COLLECTOR:
            trends = business_metrics_collector.get_annotation_efficiency_trends(hours)
            
            if not trends:
                return {
                    "period_hours": hours,
                    "data_points": 0,
                    "trends": [],
                    "summary": {
                        "avg_annotations_per_hour": 0,
                        "avg_quality_score": 0,
                        "avg_completion_rate": 0,
                        "avg_revision_rate": 0
                    },
                    "tenant_id": tenant_id,
                    "message": "No annotation efficiency data available for the specified period"
                }
            
            # Calculate summary statistics
            annotations_per_hour = [t.annotations_per_hour for t in trends]
            quality_scores = [t.quality_score for t in trends]
            completion_rates = [t.completion_rate for t in trends]
            revision_rates = [t.revision_rate for t in trends]
            
            return {
                "period_hours": hours,
                "data_points": len(trends),
                "trends": [
                    {
                        "timestamp": t.timestamp,
                        "datetime": datetime.fromtimestamp(t.timestamp).isoformat(),
                        "annotations_per_hour": t.annotations_per_hour,
                        "average_annotation_time": t.average_annotation_time,
                        "quality_score": t.quality_score,
                        "completion_rate": t.completion_rate,
                        "revision_rate": t.revision_rate
                    }
                    for t in trends
                ],
                "summary": {
                    "avg_annotations_per_hour": sum(annotations_per_hour) / len(annotations_per_hour),
                    "avg_quality_score": sum(quality_scores) / len(quality_scores),
                    "avg_completion_rate": sum(completion_rates) / len(completion_rates),
                    "avg_revision_rate": sum(revision_rates) / len(revision_rates),
                    "peak_annotations_per_hour": max(annotations_per_hour),
                    "best_quality_score": max(quality_scores),
                    "trend_direction": _calculate_trend_direction(annotations_per_hour)
                },
                "tenant_id": tenant_id
            }
        else:
            # Return mock data
            return {
                "period_hours": hours,
                "data_points": 0,
                "trends": [],
                "summary": {
                    "avg_annotations_per_hour": 15.5,
                    "avg_quality_score": 0.91,
                    "avg_completion_rate": 0.88,
                    "avg_revision_rate": 0.12,
                    "peak_annotations_per_hour": 25,
                    "best_quality_score": 0.98,
                    "trend_direction": "stable"
                },
                "tenant_id": tenant_id
            }
        
    except Exception as e:
        logger.error(f"Failed to get annotation efficiency trends: {e}")
        return {
            "period_hours": hours,
            "data_points": 0,
            "trends": [],
            "summary": {
                "avg_annotations_per_hour": 0,
                "avg_quality_score": 0,
                "avg_completion_rate": 0,
                "avg_revision_rate": 0
            },
            "tenant_id": tenant_id,
            "error": str(e)
        }


@router.get("/user-activity")
async def get_user_activity_trends(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze (1-168)"),
    tenant_id: str = Query("default_tenant", description="Tenant ID"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user activity and engagement trends.
    
    Provides metrics on active users, session patterns, user engagement,
    and activity trends over the specified time period.
    """
    try:
        if HAS_COLLECTOR:
            trends = business_metrics_collector.get_user_activity_trends(hours)
            
            if not trends:
                return {
                    "period_hours": hours,
                    "data_points": 0,
                    "trends": [],
                    "summary": {
                        "avg_active_users": 0,
                        "total_new_users": 0,
                        "avg_session_duration": 0,
                        "peak_concurrent_users": 0
                    },
                    "tenant_id": tenant_id,
                    "message": "No user activity data available for the specified period"
                }
            
            # Calculate summary statistics
            active_users = [t.active_users_count for t in trends]
            new_users = [t.new_users_count for t in trends]
            session_durations = [t.session_duration_avg for t in trends]
            actions_per_session = [t.actions_per_session for t in trends]
            
            return {
                "period_hours": hours,
                "data_points": len(trends),
                "trends": [
                    {
                        "timestamp": t.timestamp,
                        "datetime": datetime.fromtimestamp(t.timestamp).isoformat(),
                        "active_users_count": t.active_users_count,
                        "new_users_count": t.new_users_count,
                        "returning_users_count": t.returning_users_count,
                        "session_duration_avg": t.session_duration_avg,
                        "actions_per_session": t.actions_per_session,
                        "peak_concurrent_users": t.peak_concurrent_users
                    }
                    for t in trends
                ],
                "summary": {
                    "avg_active_users": sum(active_users) / len(active_users),
                    "total_new_users": sum(new_users),
                    "avg_session_duration": sum(session_durations) / len(session_durations),
                    "avg_actions_per_session": sum(actions_per_session) / len(actions_per_session),
                    "peak_concurrent_users": max([t.peak_concurrent_users for t in trends]),
                    "user_growth_trend": _calculate_trend_direction(new_users),
                    "engagement_trend": _calculate_trend_direction(actions_per_session)
                },
                "tenant_id": tenant_id
            }
        else:
            # Return mock data
            return {
                "period_hours": hours,
                "data_points": 0,
                "trends": [],
                "summary": {
                    "avg_active_users": 8,
                    "total_new_users": 3,
                    "avg_session_duration": 3200,
                    "avg_actions_per_session": 45,
                    "peak_concurrent_users": 15,
                    "user_growth_trend": "increasing",
                    "engagement_trend": "stable"
                },
                "tenant_id": tenant_id
            }
        
    except Exception as e:
        logger.error(f"Failed to get user activity trends: {e}")
        return {
            "period_hours": hours,
            "data_points": 0,
            "trends": [],
            "summary": {
                "avg_active_users": 0,
                "total_new_users": 0,
                "avg_session_duration": 0,
                "peak_concurrent_users": 0
            },
            "tenant_id": tenant_id,
            "error": str(e)
        }


@router.get("/ai-models")
async def get_ai_model_performance(
    model_name: Optional[str] = Query(None, description="Specific model name to analyze"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze (1-168)"),
    tenant_id: str = Query("default_tenant", description="Tenant ID"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get AI model performance metrics.
    
    Provides detailed performance metrics for AI models including
    inference times, success rates, confidence scores, and accuracy metrics.
    """
    try:
        if HAS_COLLECTOR and model_name:
            model_metrics = business_metrics_collector.get_ai_model_performance(model_name, hours)
            
            if not model_metrics:
                return {
                    "model_name": model_name,
                    "period_hours": hours,
                    "data_points": 0,
                    "metrics": [],
                    "summary": {},
                    "tenant_id": tenant_id,
                    "message": f"No performance data available for model '{model_name}' in the specified period"
                }
            
            inference_counts = [m.inference_count for m in model_metrics]
            inference_times = [m.average_inference_time for m in model_metrics]
            success_rates = [m.success_rate for m in model_metrics]
            confidence_scores = [m.confidence_score_avg for m in model_metrics]
            
            return {
                "model_name": model_name,
                "period_hours": hours,
                "data_points": len(model_metrics),
                "metrics": [
                    {
                        "timestamp": m.timestamp,
                        "datetime": datetime.fromtimestamp(m.timestamp).isoformat(),
                        "inference_count": m.inference_count,
                        "average_inference_time": m.average_inference_time,
                        "success_rate": m.success_rate,
                        "confidence_score_avg": m.confidence_score_avg,
                        "accuracy_score": m.accuracy_score,
                        "error_rate": m.error_rate
                    }
                    for m in model_metrics
                ],
                "summary": {
                    "total_inferences": sum(inference_counts),
                    "avg_inference_time": sum(inference_times) / len(inference_times),
                    "avg_success_rate": sum(success_rates) / len(success_rates),
                    "avg_confidence_score": sum(confidence_scores) / len(confidence_scores),
                    "performance_trend": _calculate_trend_direction([1/t for t in inference_times if t > 0])
                },
                "tenant_id": tenant_id
            }
        elif HAS_COLLECTOR:
            # Get metrics for all models
            all_models = {}
            
            for model in business_metrics_collector.ai_model_metrics.keys():
                model_metrics = business_metrics_collector.get_ai_model_performance(model, hours)
                
                if model_metrics:
                    latest_metric = model_metrics[-1]
                    all_models[model] = {
                        "inference_count": latest_metric.inference_count,
                        "average_inference_time": latest_metric.average_inference_time,
                        "success_rate": latest_metric.success_rate,
                        "confidence_score_avg": latest_metric.confidence_score_avg,
                        "accuracy_score": latest_metric.accuracy_score,
                        "error_rate": latest_metric.error_rate,
                        "last_updated": datetime.fromtimestamp(latest_metric.timestamp).isoformat()
                    }
            
            return {
                "period_hours": hours,
                "models": all_models,
                "model_count": len(all_models),
                "summary": {
                    "total_models": len(all_models),
                    "active_models": len([m for m in all_models.values() if m["inference_count"] > 0]),
                    "avg_success_rate": sum([m["success_rate"] for m in all_models.values()]) / len(all_models) if all_models else 0
                },
                "tenant_id": tenant_id
            }
        else:
            # Return mock data
            return {
                "period_hours": hours,
                "models": {
                    "default_model": {
                        "inference_count": 1000,
                        "average_inference_time": 0.5,
                        "success_rate": 0.98,
                        "confidence_score_avg": 0.85
                    }
                },
                "model_count": 1,
                "summary": {
                    "total_models": 1,
                    "active_models": 1,
                    "avg_success_rate": 0.98
                },
                "tenant_id": tenant_id
            }
        
    except Exception as e:
        logger.error(f"Failed to get AI model performance: {e}")
        return {
            "period_hours": hours,
            "models": {},
            "model_count": 0,
            "tenant_id": tenant_id,
            "error": str(e)
        }


@router.get("/projects")
async def get_project_progress(
    project_id: Optional[str] = Query(None, description="Specific project ID to analyze"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze (1-168)"),
    tenant_id: str = Query("default_tenant", description="Tenant ID"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get project progress and completion metrics.
    
    Provides detailed progress tracking for projects including
    task completion rates, timeline estimates, and productivity metrics.
    """
    try:
        if HAS_COLLECTOR and project_id:
            project_metrics = business_metrics_collector.get_project_progress(project_id, hours)
            
            if not project_metrics:
                return {
                    "project_id": project_id,
                    "period_hours": hours,
                    "data_points": 0,
                    "progress": [],
                    "summary": {},
                    "tenant_id": tenant_id,
                    "message": f"No progress data available for project '{project_id}' in the specified period"
                }
            
            latest_metric = project_metrics[-1]
            completion_percentages = [m.completion_percentage for m in project_metrics]
            
            return {
                "project_id": project_id,
                "period_hours": hours,
                "data_points": len(project_metrics),
                "progress": [
                    {
                        "timestamp": m.timestamp,
                        "datetime": datetime.fromtimestamp(m.timestamp).isoformat(),
                        "total_tasks": m.total_tasks,
                        "completed_tasks": m.completed_tasks,
                        "in_progress_tasks": m.in_progress_tasks,
                        "pending_tasks": m.pending_tasks,
                        "completion_percentage": m.completion_percentage,
                        "estimated_completion_date": m.estimated_completion_date,
                        "average_task_duration": m.average_task_duration
                    }
                    for m in project_metrics
                ],
                "current_status": {
                    "completion_percentage": latest_metric.completion_percentage,
                    "total_tasks": latest_metric.total_tasks,
                    "completed_tasks": latest_metric.completed_tasks,
                    "remaining_tasks": latest_metric.in_progress_tasks + latest_metric.pending_tasks,
                    "estimated_completion": latest_metric.estimated_completion_date,
                    "average_task_duration_hours": latest_metric.average_task_duration / 3600
                },
                "summary": {
                    "progress_trend": _calculate_trend_direction(completion_percentages),
                    "completion_velocity": _calculate_completion_velocity(project_metrics),
                    "on_track": latest_metric.completion_percentage >= _expected_completion_percentage(project_metrics)
                },
                "tenant_id": tenant_id
            }
        elif HAS_COLLECTOR:
            # Get metrics for all projects
            all_projects = {}
            
            for project in business_metrics_collector.project_metrics.keys():
                project_metrics = business_metrics_collector.get_project_progress(project, hours)
                
                if project_metrics:
                    latest_metric = project_metrics[-1]
                    all_projects[project] = {
                        "completion_percentage": latest_metric.completion_percentage,
                        "total_tasks": latest_metric.total_tasks,
                        "completed_tasks": latest_metric.completed_tasks,
                        "remaining_tasks": latest_metric.in_progress_tasks + latest_metric.pending_tasks,
                        "estimated_completion": latest_metric.estimated_completion_date,
                        "last_updated": datetime.fromtimestamp(latest_metric.timestamp).isoformat()
                    }
            
            return {
                "period_hours": hours,
                "projects": all_projects,
                "project_count": len(all_projects),
                "summary": {
                    "total_projects": len(all_projects),
                    "completed_projects": len([p for p in all_projects.values() if p["completion_percentage"] >= 100]),
                    "avg_completion_percentage": sum([p["completion_percentage"] for p in all_projects.values()]) / len(all_projects) if all_projects else 0,
                    "projects_on_track": len([p for p in all_projects.values() if p["completion_percentage"] >= 50])
                },
                "tenant_id": tenant_id
            }
        else:
            # Return mock data
            return {
                "period_hours": hours,
                "projects": {
                    "sample_project": {
                        "completion_percentage": 75.0,
                        "total_tasks": 100,
                        "completed_tasks": 75,
                        "remaining_tasks": 25
                    }
                },
                "project_count": 1,
                "summary": {
                    "total_projects": 1,
                    "completed_projects": 0,
                    "avg_completion_percentage": 75.0,
                    "projects_on_track": 1
                },
                "tenant_id": tenant_id
            }
        
    except Exception as e:
        logger.error(f"Failed to get project progress: {e}")
        return {
            "period_hours": hours,
            "projects": {},
            "project_count": 0,
            "tenant_id": tenant_id,
            "error": str(e)
        }


@router.post("/track/user-session")
async def track_user_session(
    action: str = Query(..., description="Action: 'start' or 'end'"),
    user_id: str = Query(..., description="User ID"),
    session_id: str = Query(..., description="Session ID"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> JSONResponse:
    """
    Track user session events for activity monitoring.
    
    Records session start/end events to calculate user engagement metrics.
    """
    if not current_user or not require_annotate_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        if not HAS_COLLECTOR:
            return JSONResponse(
                status_code=200,
                content={"message": "Tracking not available", "timestamp": datetime.now().isoformat()}
            )
        
        if action == "start":
            business_metrics_collector.track_user_session_start(user_id, session_id)
            message = f"Started tracking session {session_id} for user {user_id}"
        elif action == "end":
            business_metrics_collector.track_user_session_end(session_id)
            message = f"Ended tracking session {session_id}"
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid action. Must be 'start' or 'end'"
            )
        
        return JSONResponse(
            status_code=200,
            content={"message": message, "timestamp": datetime.now().isoformat()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track user session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track user session: {str(e)}"
        )


@router.post("/track/user-action")
async def track_user_action(
    user_id: str = Query(..., description="User ID"),
    action_type: str = Query(..., description="Type of action performed"),
    details: Optional[Dict[str, Any]] = None,
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> JSONResponse:
    """
    Track user actions for engagement monitoring.
    
    Records user actions to calculate engagement and productivity metrics.
    """
    if not current_user or not require_annotate_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        if not HAS_COLLECTOR:
            return JSONResponse(
                status_code=200,
                content={"message": "Tracking not available", "timestamp": datetime.now().isoformat()}
            )
        
        business_metrics_collector.track_user_action(user_id, action_type, details)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Tracked action '{action_type}' for user {user_id}",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to track user action: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track user action: {str(e)}"
        )


@router.post("/track/ai-inference")
async def track_ai_inference(
    model_name: str = Query(..., description="AI model name"),
    duration: float = Query(..., description="Inference duration in seconds"),
    success: bool = Query(..., description="Whether inference was successful"),
    confidence: Optional[float] = Query(None, description="Confidence score (0-1)"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> JSONResponse:
    """
    Track AI inference operations for performance monitoring.
    
    Records AI model usage and performance metrics.
    """
    if not current_user or not require_annotate_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        if not HAS_COLLECTOR:
            return JSONResponse(
                status_code=200,
                content={"message": "Tracking not available", "timestamp": datetime.now().isoformat()}
            )
        
        business_metrics_collector.track_ai_inference(model_name, duration, success, confidence)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Tracked AI inference for model '{model_name}'",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to track AI inference: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track AI inference: {str(e)}"
        )


@router.post("/track/annotation-quality")
async def track_annotation_quality(
    project_id: str = Query(..., description="Project ID"),
    task_id: str = Query(..., description="Task ID"),
    quality_score: float = Query(..., ge=0.0, le=1.0, description="Quality score (0-1)"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> JSONResponse:
    """
    Track annotation quality scores for quality monitoring.
    
    Records quality assessments to calculate quality trends and metrics.
    """
    if not current_user or not require_annotate_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        if not HAS_COLLECTOR:
            return JSONResponse(
                status_code=200,
                content={"message": "Tracking not available", "timestamp": datetime.now().isoformat()}
            )
        
        business_metrics_collector.track_annotation_quality(project_id, task_id, quality_score)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Tracked quality score {quality_score} for task {task_id}",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to track annotation quality: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track annotation quality: {str(e)}"
        )


@router.post("/start-collection")
async def start_metrics_collection(
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> JSONResponse:
    """
    Start automatic business metrics collection.
    
    Begins background collection of business metrics. Admin permission required.
    """
    if not current_user or not require_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    try:
        if not HAS_COLLECTOR:
            return JSONResponse(
                status_code=200,
                content={"message": "Collector not available", "timestamp": datetime.now().isoformat()}
            )
        
        await business_metrics_collector.start_collection()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Business metrics collection started",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start metrics collection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start metrics collection: {str(e)}"
        )


@router.post("/stop-collection")
async def stop_metrics_collection(
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> JSONResponse:
    """
    Stop automatic business metrics collection.
    
    Stops background collection of business metrics. Admin permission required.
    """
    if not current_user or not require_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    try:
        if not HAS_COLLECTOR:
            return JSONResponse(
                status_code=200,
                content={"message": "Collector not available", "timestamp": datetime.now().isoformat()}
            )
        
        await business_metrics_collector.stop_collection()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Business metrics collection stopped",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to stop metrics collection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop metrics collection: {str(e)}"
        )
