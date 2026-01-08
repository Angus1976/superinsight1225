"""
Intelligent Operations API for SuperInsight Platform.

Provides REST API endpoints for intelligent operations capabilities including:
- AI-driven anomaly detection and prediction
- Automated operations management
- Operations knowledge base access
- Decision support system
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from src.system.intelligent_operations import get_intelligent_operations, PredictionType, RecommendationType
from src.system.automated_operations import get_automated_operations, AutomationLevel, OperationType
from src.system.operations_knowledge_base import get_operations_knowledge, CaseType, CaseSeverity, DecisionContext
from src.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligent-operations", tags=["Intelligent Operations"])


# Pydantic models for API
class PredictionRequest(BaseModel):
    metric_name: str
    prediction_horizon_hours: int = Field(default=1, ge=1, le=168)  # 1 hour to 1 week
    features: Optional[Dict[str, float]] = None


class RecommendationFilter(BaseModel):
    priority: Optional[str] = None
    recommendation_type: Optional[str] = None
    timeline: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)


class AutomationRuleRequest(BaseModel):
    rule_id: str
    operation_type: str
    automation_level: str
    trigger_conditions: Dict[str, Any]
    action_parameters: Dict[str, Any]
    cooldown_seconds: int = Field(default=300, ge=60)
    max_executions_per_hour: int = Field(default=5, ge=1, le=20)
    enabled: bool = True


class CaseSearchRequest(BaseModel):
    query: Optional[str] = None
    case_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=50)


class DecisionRequest(BaseModel):
    situation_id: str
    description: str
    current_metrics: Dict[str, float]
    symptoms: List[str]
    constraints: Optional[Dict[str, Any]] = None
    objectives: List[str]
    time_pressure: str = Field(default="medium")
    risk_tolerance: str = Field(default="medium")


# Intelligent Operations Endpoints
@router.get("/status")
async def get_intelligent_operations_status(current_user: dict = Depends(get_current_user)):
    """Get the status of intelligent operations system."""
    try:
        intelligent_ops = get_intelligent_operations()
        automated_ops = get_automated_operations()
        knowledge_system = get_operations_knowledge()
        
        return {
            "intelligent_operations": {
                "is_running": intelligent_ops.is_running,
                "analysis_interval": intelligent_ops.analysis_interval,
                "predictions_count": len(intelligent_ops.predictions),
                "recommendations_count": len(intelligent_ops.recommendations)
            },
            "automated_operations": automated_ops.get_automation_status(),
            "knowledge_system": knowledge_system.get_system_insights()
        }
        
    except Exception as e:
        logger.error(f"Error getting intelligent operations status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_system_insights(current_user: dict = Depends(get_current_user)):
    """Get comprehensive system insights from intelligent operations."""
    try:
        intelligent_ops = get_intelligent_operations()
        insights = intelligent_ops.get_system_insights()
        
        return {
            "status": "success",
            "data": insights,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions")
async def get_predictions(
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    current_user: dict = Depends(get_current_user)
):
    """Get current predictions from the intelligent operations system."""
    try:
        intelligent_ops = get_intelligent_operations()
        
        predictions = {}
        for name, prediction in intelligent_ops.predictions.items():
            if metric_name is None or metric_name in name:
                predictions[name] = {
                    "prediction_id": prediction.prediction_id,
                    "prediction_type": prediction.prediction_type.value,
                    "target_metric": prediction.target_metric,
                    "predicted_value": prediction.predicted_value,
                    "confidence": prediction.confidence,
                    "prediction_horizon": prediction.prediction_horizon,
                    "created_at": prediction.created_at.isoformat(),
                    "model_accuracy": prediction.model_accuracy
                }
        
        return {
            "status": "success",
            "data": predictions,
            "count": len(predictions)
        }
        
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/request")
async def request_prediction(
    request: PredictionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Request a specific prediction from the ML models."""
    try:
        intelligent_ops = get_intelligent_operations()
        
        # Get current metrics if features not provided
        if request.features is None:
            current_metrics = intelligent_ops.metrics_collector.get_all_metrics_summary()
            features = intelligent_ops._flatten_metrics(current_metrics)
        else:
            features = request.features
        
        # Add time-based features
        features['hour_of_day'] = (datetime.utcnow().hour + request.prediction_horizon_hours) % 24
        features['day_of_week'] = datetime.utcnow().weekday()
        
        # Get prediction
        prediction_result = await intelligent_ops.ml_predictor.predict(request.metric_name, features)
        
        if prediction_result is None:
            raise HTTPException(status_code=404, detail=f"No model available for metric: {request.metric_name}")
        
        predicted_value, confidence = prediction_result
        
        return {
            "status": "success",
            "data": {
                "metric_name": request.metric_name,
                "predicted_value": predicted_value,
                "confidence": confidence,
                "prediction_horizon_hours": request.prediction_horizon_hours,
                "features_used": list(features.keys()),
                "model_accuracy": intelligent_ops.ml_predictor.model_accuracy.get(request.metric_name, 0.0),
                "created_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations(
    priority: Optional[str] = Query(None, description="Filter by priority"),
    recommendation_type: Optional[str] = Query(None, description="Filter by type"),
    timeline: Optional[str] = Query(None, description="Filter by timeline"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Get current operational recommendations."""
    try:
        intelligent_ops = get_intelligent_operations()
        
        recommendations = intelligent_ops.recommendations
        
        # Apply filters
        if priority:
            recommendations = [r for r in recommendations if r.priority == priority]
        
        if recommendation_type:
            recommendations = [r for r in recommendations if r.recommendation_type.value == recommendation_type]
        
        if timeline:
            recommendations = [r for r in recommendations if r.timeline == timeline]
        
        # Limit results
        recommendations = recommendations[:limit]
        
        # Convert to response format
        result = []
        for rec in recommendations:
            result.append({
                "recommendation_id": rec.recommendation_id,
                "recommendation_type": rec.recommendation_type.value,
                "title": rec.title,
                "description": rec.description,
                "priority": rec.priority,
                "estimated_impact": rec.estimated_impact,
                "implementation_effort": rec.implementation_effort,
                "timeline": rec.timeline,
                "prerequisites": rec.prerequisites,
                "risks": rec.risks,
                "created_at": rec.created_at.isoformat(),
                "expires_at": rec.expires_at.isoformat() if rec.expires_at else None
            })
        
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity-forecasts")
async def get_capacity_forecasts(current_user: dict = Depends(get_current_user)):
    """Get current capacity forecasts."""
    try:
        intelligent_ops = get_intelligent_operations()
        
        forecasts = {}
        for resource_type, forecast in intelligent_ops.capacity_forecasts.items():
            forecasts[resource_type] = {
                "resource_type": forecast.resource_type,
                "current_usage": forecast.current_usage,
                "predicted_usage": forecast.predicted_usage,
                "capacity_limit": forecast.capacity_limit,
                "time_to_exhaustion": forecast.time_to_exhaustion,
                "recommended_action": forecast.recommended_action,
                "confidence": forecast.confidence,
                "created_at": forecast.created_at.isoformat()
            }
        
        return {
            "status": "success",
            "data": forecasts,
            "count": len(forecasts)
        }
        
    except Exception as e:
        logger.error(f"Error getting capacity forecasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Automated Operations Endpoints
@router.get("/automation/status")
async def get_automation_status(current_user: dict = Depends(get_current_user)):
    """Get automation system status."""
    try:
        automated_ops = get_automated_operations()
        return {
            "status": "success",
            "data": automated_ops.get_automation_status()
        }
        
    except Exception as e:
        logger.error(f"Error getting automation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/rules")
async def add_automation_rule(
    rule_request: AutomationRuleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a new automation rule."""
    try:
        from src.system.automated_operations import AutomationRule
        
        automated_ops = get_automated_operations()
        
        # Validate enums
        try:
            operation_type = OperationType(rule_request.operation_type)
            automation_level = AutomationLevel(rule_request.automation_level)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
        
        # Create automation rule
        rule = AutomationRule(
            rule_id=rule_request.rule_id,
            operation_type=operation_type,
            automation_level=automation_level,
            trigger_conditions=rule_request.trigger_conditions,
            action_parameters=rule_request.action_parameters,
            cooldown_seconds=rule_request.cooldown_seconds,
            max_executions_per_hour=rule_request.max_executions_per_hour,
            enabled=rule_request.enabled
        )
        
        automated_ops.add_automation_rule(rule)
        
        return {
            "status": "success",
            "message": f"Automation rule '{rule_request.rule_id}' added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding automation rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/history")
async def get_automation_history(
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get automation execution history."""
    try:
        automated_ops = get_automated_operations()
        
        # Get recent executions
        executions = list(automated_ops.execution_history)
        
        # Apply filters
        if operation_type:
            executions = [e for e in executions if e.operation_type.value == operation_type]
        
        if success is not None:
            executions = [e for e in executions if e.success == success]
        
        # Limit and sort by most recent
        executions = sorted(executions, key=lambda e: e.started_at, reverse=True)[:limit]
        
        # Convert to response format
        result = []
        for exec in executions:
            result.append({
                "execution_id": exec.execution_id,
                "rule_id": exec.rule_id,
                "operation_type": exec.operation_type.value,
                "action_taken": exec.action_taken,
                "trigger_reason": exec.trigger_reason,
                "success": exec.success,
                "result": exec.result,
                "error_message": exec.error_message,
                "started_at": exec.started_at.isoformat(),
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "metrics_before": exec.metrics_before,
                "metrics_after": exec.metrics_after
            })
        
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting automation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Knowledge Base Endpoints
@router.get("/knowledge/cases")
async def search_cases(
    query: Optional[str] = Query(None, description="Search query"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Search operational cases in the knowledge base."""
    try:
        knowledge_system = get_operations_knowledge()
        
        # Parse parameters
        case_type_enum = None
        if case_type:
            try:
                case_type_enum = CaseType(case_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid case type: {case_type}")
        
        severity_enum = None
        if severity:
            try:
                severity_enum = CaseSeverity(severity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        status_enum = None
        if status:
            try:
                from src.system.operations_knowledge_base import CaseStatus
                status_enum = CaseStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        tags_list = None
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]
        
        # Search cases
        cases = knowledge_system.case_library.search_cases(
            query=query,
            case_type=case_type_enum,
            severity=severity_enum,
            status=status_enum,
            tags=tags_list,
            limit=limit
        )
        
        # Convert to response format
        result = []
        for case in cases:
            result.append({
                "case_id": case.case_id,
                "case_type": case.case_type.value,
                "severity": case.severity.value,
                "status": case.status.value,
                "title": case.title,
                "description": case.description,
                "symptoms": case.symptoms,
                "root_cause": case.root_cause,
                "resolution_steps": case.resolution_steps,
                "resolution_time_minutes": case.resolution_time_minutes,
                "tags": list(case.tags),
                "effectiveness_score": case.effectiveness_score,
                "created_at": case.created_at.isoformat(),
                "updated_at": case.updated_at.isoformat(),
                "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None
            })
        
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/cases/{case_id}")
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific case by ID."""
    try:
        knowledge_system = get_operations_knowledge()
        
        if case_id not in knowledge_system.case_library.cases:
            raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
        
        case = knowledge_system.case_library.cases[case_id]
        
        return {
            "status": "success",
            "data": {
                "case_id": case.case_id,
                "case_type": case.case_type.value,
                "severity": case.severity.value,
                "status": case.status.value,
                "title": case.title,
                "description": case.description,
                "symptoms": case.symptoms,
                "root_cause": case.root_cause,
                "resolution_steps": case.resolution_steps,
                "resolution_time_minutes": case.resolution_time_minutes,
                "tags": list(case.tags),
                "related_metrics": case.related_metrics,
                "effectiveness_score": case.effectiveness_score,
                "reoccurrence_count": case.reoccurrence_count,
                "created_at": case.created_at.isoformat(),
                "updated_at": case.updated_at.isoformat(),
                "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
                "created_by": case.created_by,
                "assigned_to": case.assigned_to
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/articles")
async def search_articles(
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Search knowledge base articles."""
    try:
        knowledge_system = get_operations_knowledge()
        
        tags_list = None
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]
        
        articles = knowledge_system.knowledge_base.search_articles(
            query=query,
            category=category,
            tags=tags_list,
            limit=limit
        )
        
        # Convert to response format
        result = []
        for article in articles:
            result.append({
                "article_id": article.article_id,
                "title": article.title,
                "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
                "category": article.category,
                "tags": list(article.tags),
                "author": article.author,
                "view_count": article.view_count,
                "rating": article.rating,
                "created_at": article.created_at.isoformat(),
                "updated_at": article.updated_at.isoformat()
            })
        
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error searching articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decision-support")
async def get_decision_recommendations(
    request: DecisionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get decision support recommendations for a given context."""
    try:
        knowledge_system = get_operations_knowledge()
        
        # Create decision context
        context = DecisionContext(
            situation_id=request.situation_id,
            description=request.description,
            current_metrics=request.current_metrics,
            symptoms=request.symptoms,
            constraints=request.constraints or {},
            objectives=request.objectives,
            time_pressure=request.time_pressure,
            risk_tolerance=request.risk_tolerance
        )
        
        # Get recommendations
        recommendations = await knowledge_system.decision_support.get_decision_recommendations(context)
        
        # Convert to response format
        result = []
        for rec in recommendations:
            result.append({
                "recommendation_id": rec.recommendation_id,
                "recommended_action": rec.recommended_action,
                "rationale": rec.rationale,
                "confidence": rec.confidence,
                "expected_outcome": rec.expected_outcome,
                "risks": rec.risks,
                "prerequisites": rec.prerequisites,
                "estimated_effort": rec.estimated_effort,
                "similar_cases": rec.similar_cases,
                "success_probability": rec.success_probability
            })
        
        return {
            "status": "success",
            "data": {
                "context_id": request.situation_id,
                "recommendations": result,
                "recommendation_count": len(result)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting decision recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/statistics")
async def get_knowledge_statistics(current_user: dict = Depends(get_current_user)):
    """Get statistics about the knowledge system."""
    try:
        knowledge_system = get_operations_knowledge()
        
        case_stats = knowledge_system.case_library.get_case_statistics()
        system_insights = knowledge_system.get_system_insights()
        
        return {
            "status": "success",
            "data": {
                "case_library": case_stats,
                "knowledge_base": system_insights.get("knowledge_base", {}),
                "decision_support": system_insights.get("decision_support", {}),
                "learning_status": system_insights.get("learning_status", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting knowledge statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Control Endpoints
@router.post("/start")
async def start_intelligent_operations(current_user: dict = Depends(get_current_user)):
    """Start the intelligent operations system."""
    try:
        intelligent_ops = get_intelligent_operations()
        automated_ops = get_automated_operations()
        
        await intelligent_ops.start()
        await automated_ops.start()
        
        return {
            "status": "success",
            "message": "Intelligent operations system started successfully"
        }
        
    except Exception as e:
        logger.error(f"Error starting intelligent operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_intelligent_operations(current_user: dict = Depends(get_current_user)):
    """Stop the intelligent operations system."""
    try:
        intelligent_ops = get_intelligent_operations()
        automated_ops = get_automated_operations()
        
        await intelligent_ops.stop()
        await automated_ops.stop()
        
        return {
            "status": "success",
            "message": "Intelligent operations system stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Error stopping intelligent operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))