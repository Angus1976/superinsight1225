"""
Ragas Integration API Endpoints.

Provides REST API endpoints for Ragas evaluation, trend analysis,
and quality monitoring functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from src.ragas_integration import (
    RagasEvaluator, 
    QualityTrendAnalyzer, 
    QualityMonitor,
    MonitoringConfig
)
from src.models.annotation import Annotation
from src.database.connection import get_db_session
from src.api.ragas_repository import EvaluationResultRepository, SyncEvaluationResultRepository
from src.i18n import get_translation
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ragas", tags=["ragas"])

# Global instances (in production, these should be dependency-injected)
ragas_evaluator = RagasEvaluator()
trend_analyzer = QualityTrendAnalyzer()
quality_monitor = QualityMonitor()


def get_repository(db: Session = Depends(get_db_session)) -> SyncEvaluationResultRepository:
    """Dependency to get evaluation result repository."""
    return SyncEvaluationResultRepository(db)


# =============================================================================
# Request/Response Models
# =============================================================================


class EvaluationRequest(BaseModel):
    """Request model for Ragas evaluation."""
    
    annotation_ids: List[str] = Field(..., description="List of annotation IDs to evaluate")
    metrics: Optional[List[str]] = Field(None, description="Specific metrics to evaluate")
    task_id: Optional[str] = Field(None, description="Optional task ID for tracking")


class TrendAnalysisRequest(BaseModel):
    """Request model for trend analysis."""
    
    metric_name: str = Field(..., description="Name of the metric to analyze")
    analysis_period_days: Optional[int] = Field(7, description="Analysis period in days")


class ForecastRequest(BaseModel):
    """Request model for quality forecasting."""
    
    metric_name: str = Field(..., description="Name of the metric to forecast")
    forecast_days: int = Field(7, description="Number of days to forecast")


class MonitoringConfigRequest(BaseModel):
    """Request model for monitoring configuration."""
    
    evaluation_interval: Optional[int] = Field(300, description="Evaluation interval in seconds")
    min_overall_quality: Optional[float] = Field(0.7, description="Minimum overall quality threshold")
    min_faithfulness: Optional[float] = Field(0.7, description="Minimum faithfulness threshold")
    min_relevancy: Optional[float] = Field(0.7, description="Minimum relevancy threshold")
    enable_auto_retraining: Optional[bool] = Field(True, description="Enable automatic retraining")
    enable_notifications: Optional[bool] = Field(True, description="Enable notifications")


class AlertAcknowledgeRequest(BaseModel):
    """Request model for acknowledging alerts."""
    
    alert_id: str = Field(..., description="ID of the alert to acknowledge")


class EvaluationListResponse(BaseModel):
    """Response model for listing evaluation results."""
    
    success: bool = Field(default=True, description="Whether the request was successful")
    evaluations: List[Dict[str, Any]] = Field(default_factory=list, description="List of evaluation results")
    total_count: int = Field(default=0, description="Total number of matching results")
    skip: int = Field(default=0, description="Number of records skipped")
    limit: int = Field(default=100, description="Maximum number of records returned")


# =============================================================================
# Evaluation Endpoints
# =============================================================================


@router.post("/evaluate")
async def evaluate_annotations(
    request: EvaluationRequest,
    repository: SyncEvaluationResultRepository = Depends(get_repository)
) -> JSONResponse:
    """
    Evaluate annotations using Ragas metrics.
    
    Args:
        request: Evaluation request containing annotation IDs and options
        repository: Evaluation result repository for persistence
        
    Returns:
        Ragas evaluation results with evaluation_id for retrieval
    """
    try:
        # TODO: In production, fetch annotations from database
        # For now, create mock annotations
        annotations = []
        for ann_id in request.annotation_ids:
            mock_annotation = Annotation(
                id=ann_id,
                annotation_data={
                    "question": f"Sample question for {ann_id}",
                    "answer": f"Sample answer for {ann_id}",
                    "context": f"Sample context for {ann_id}"
                },
                confidence=0.85
            )
            annotations.append(mock_annotation)
        
        # Perform evaluation
        result = await ragas_evaluator.evaluate_annotations(
            annotations=annotations,
            metrics=request.metrics,
            task_id=request.task_id
        )
        
        # Add result to trend analyzer
        trend_analyzer.add_evaluation_result(result)
        quality_monitor.add_evaluation_result(result)
        
        # Save result to database
        try:
            result_dict = result.to_dict()
            result_dict['annotation_ids'] = request.annotation_ids
            evaluation_id = repository.save(result_dict)
            
            logger.info(
                get_translation("ragas.api.evaluate_saved", default="Evaluation result saved"),
                extra={"evaluation_id": evaluation_id}
            )
        except Exception as save_error:
            # Log error but don't fail the request - evaluation was successful
            logger.error(
                get_translation("ragas.api.save_failed", default="Failed to save evaluation result"),
                extra={"error": str(save_error)}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "evaluation_result": result.to_dict(),
                "message": get_translation("ragas.api.evaluate_success", default="Evaluation completed successfully")
            }
        )
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=get_translation("ragas.api.evaluate_error", default=f"Evaluation failed: {str(e)}")
        )


@router.get("/evaluate/{evaluation_id}")
async def get_evaluation_result(
    evaluation_id: str,
    repository: SyncEvaluationResultRepository = Depends(get_repository)
) -> JSONResponse:
    """
    Get evaluation result by ID.
    
    Args:
        evaluation_id: ID of the evaluation result
        repository: Evaluation result repository for retrieval
        
    Returns:
        Evaluation result details
    """
    try:
        result = repository.get_by_id(evaluation_id)
        
        if result:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "evaluation_result": result,
                    "message": get_translation("ragas.api.get_success", default="Evaluation result retrieved successfully")
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": get_translation("ragas.api.not_found", default="Evaluation result not found")
                }
            )
        
    except Exception as e:
        logger.error(f"Failed to get evaluation result: {e}")
        raise HTTPException(
            status_code=500, 
            detail=get_translation("ragas.api.get_error", default=f"Failed to get evaluation result: {str(e)}")
        )


@router.get("/evaluations")
async def list_evaluation_results(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records to return"),
    start_date: Optional[datetime] = Query(default=None, description="Start date for filtering (ISO format)"),
    end_date: Optional[datetime] = Query(default=None, description="End date for filtering (ISO format)"),
    task_id: Optional[str] = Query(default=None, description="Filter by task ID"),
    repository: SyncEvaluationResultRepository = Depends(get_repository)
) -> JSONResponse:
    """
    List evaluation results with pagination and optional date filtering.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        start_date: Optional start date for filtering (inclusive)
        end_date: Optional end date for filtering (inclusive)
        task_id: Optional task ID for filtering
        repository: Evaluation result repository
        
    Returns:
        List of evaluation results with pagination info
    """
    try:
        results = repository.list(
            skip=skip,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            task_id=task_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "evaluations": results,
                "total_count": len(results),
                "skip": skip,
                "limit": limit,
                "message": get_translation("ragas.api.list_success", default="Evaluation results retrieved successfully")
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to list evaluation results: {e}")
        raise HTTPException(
            status_code=500, 
            detail=get_translation("ragas.api.list_error", default=f"Failed to list evaluation results: {str(e)}")
        )


@router.get("/metrics/available")
async def get_available_metrics() -> JSONResponse:
    """
    Get list of available Ragas metrics.
    
    Returns:
        List of available metrics with descriptions
    """
    try:
        metrics = ragas_evaluator.get_metric_descriptions()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "metrics": metrics,
                "ragas_available": ragas_evaluator.is_available()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get available metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available metrics: {str(e)}")


# =============================================================================
# Trend Analysis Endpoints
# =============================================================================


@router.post("/trends/analyze")
async def analyze_trend(request: TrendAnalysisRequest) -> JSONResponse:
    """
    Analyze quality trend for a specific metric.
    
    Args:
        request: Trend analysis request
        
    Returns:
        Trend analysis results
    """
    try:
        analysis_period = timedelta(days=request.analysis_period_days) if request.analysis_period_days else None
        trend = trend_analyzer.analyze_metric_trend(request.metric_name, analysis_period)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "trend": trend.to_dict(),
                "message": "Trend analysis completed successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {str(e)}")


@router.get("/trends/all")
async def get_all_trends(analysis_period_days: Optional[int] = 7) -> JSONResponse:
    """
    Get trend analysis for all available metrics.
    
    Args:
        analysis_period_days: Analysis period in days
        
    Returns:
        Trend analysis for all metrics
    """
    try:
        analysis_period = timedelta(days=analysis_period_days) if analysis_period_days else None
        trends = trend_analyzer.analyze_all_metrics(analysis_period)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "trends": {name: trend.to_dict() for name, trend in trends.items()},
                "analysis_period_days": analysis_period_days
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get all trends: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get all trends: {str(e)}")


@router.post("/forecast")
async def forecast_quality(request: ForecastRequest) -> JSONResponse:
    """
    Forecast quality metric values.
    
    Args:
        request: Forecast request
        
    Returns:
        Quality forecast results
    """
    try:
        forecast = trend_analyzer.forecast_quality(
            metric_name=request.metric_name,
            forecast_days=request.forecast_days
        )
        
        if forecast is None:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Insufficient data for forecasting"
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "forecast": forecast.to_dict(),
                "message": "Forecast generated successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Forecasting failed: {e}")
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")


@router.get("/summary")
async def get_quality_summary(period_days: Optional[int] = 7) -> JSONResponse:
    """
    Get comprehensive quality summary.
    
    Args:
        period_days: Analysis period in days
        
    Returns:
        Quality summary with trends and alerts
    """
    try:
        period = timedelta(days=period_days) if period_days else None
        summary = trend_analyzer.get_quality_summary(period)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "summary": summary
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get quality summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quality summary: {str(e)}")


# =============================================================================
# Alert Management Endpoints
# =============================================================================


@router.get("/alerts")
async def get_alerts(severity: Optional[str] = None) -> JSONResponse:
    """
    Get active quality alerts.
    
    Args:
        severity: Optional severity filter (critical, high, medium, low)
        
    Returns:
        List of active alerts
    """
    try:
        from src.ragas_integration.trend_analyzer import AlertSeverity
        
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        alerts = trend_analyzer.get_active_alerts(severity_filter)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "alerts": [alert.to_dict() for alert in alerts],
                "total_count": len(alerts)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.post("/alerts/acknowledge")
async def acknowledge_alert(request: AlertAcknowledgeRequest) -> JSONResponse:
    """
    Acknowledge a quality alert.
    
    Args:
        request: Alert acknowledgment request
        
    Returns:
        Acknowledgment result
    """
    try:
        success = trend_analyzer.acknowledge_alert(request.alert_id)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Alert acknowledged successfully"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "Alert not found"
                }
            )
        
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.delete("/alerts/acknowledged")
async def clear_acknowledged_alerts() -> JSONResponse:
    """
    Clear all acknowledged alerts.
    
    Returns:
        Number of cleared alerts
    """
    try:
        cleared_count = trend_analyzer.clear_acknowledged_alerts()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "cleared_count": cleared_count,
                "message": f"Cleared {cleared_count} acknowledged alerts"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to clear acknowledged alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear acknowledged alerts: {str(e)}")


# =============================================================================
# Quality Monitoring Endpoints
# =============================================================================


@router.post("/monitoring/start")
async def start_monitoring() -> JSONResponse:
    """
    Start quality monitoring.
    
    Returns:
        Monitoring start result
    """
    try:
        await quality_monitor.start_monitoring()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Quality monitoring started successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/monitoring/stop")
async def stop_monitoring() -> JSONResponse:
    """
    Stop quality monitoring.
    
    Returns:
        Monitoring stop result
    """
    try:
        await quality_monitor.stop_monitoring()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Quality monitoring stopped successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")


@router.get("/monitoring/status")
async def get_monitoring_status() -> JSONResponse:
    """
    Get current monitoring status.
    
    Returns:
        Monitoring status and statistics
    """
    try:
        status = quality_monitor.get_monitoring_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "status": status
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")


@router.put("/monitoring/config")
async def update_monitoring_config(request: MonitoringConfigRequest) -> JSONResponse:
    """
    Update monitoring configuration.
    
    Args:
        request: New monitoring configuration
        
    Returns:
        Configuration update result
    """
    try:
        # Create new config from request
        new_config = MonitoringConfig(
            evaluation_interval=request.evaluation_interval,
            min_overall_quality=request.min_overall_quality,
            min_faithfulness=request.min_faithfulness,
            min_relevancy=request.min_relevancy,
            enable_auto_retraining=request.enable_auto_retraining,
            enable_notifications=request.enable_notifications
        )
        
        quality_monitor.update_config(new_config)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Monitoring configuration updated successfully",
                "config": new_config.to_dict()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to update monitoring config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update monitoring config: {str(e)}")


@router.post("/monitoring/retraining/manual")
async def trigger_manual_retraining(reason: Optional[str] = "Manual trigger") -> JSONResponse:
    """
    Manually trigger model retraining.
    
    Args:
        reason: Reason for manual retraining
        
    Returns:
        Retraining trigger result
    """
    try:
        await quality_monitor.manual_retraining(reason)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Manual retraining triggered successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger manual retraining: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger manual retraining: {str(e)}")


@router.get("/monitoring/retraining/history")
async def get_retraining_history(limit: Optional[int] = 10) -> JSONResponse:
    """
    Get retraining history.
    
    Args:
        limit: Maximum number of events to return
        
    Returns:
        Retraining history
    """
    try:
        history = quality_monitor.get_retraining_history(limit)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "history": [event.to_dict() for event in history],
                "total_count": len(history)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get retraining history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get retraining history: {str(e)}")


@router.get("/monitoring/report")
async def generate_monitoring_report(period_days: Optional[int] = 7) -> JSONResponse:
    """
    Generate comprehensive monitoring report.
    
    Args:
        period_days: Report period in days
        
    Returns:
        Comprehensive monitoring report
    """
    try:
        period = timedelta(days=period_days) if period_days else None
        report = await quality_monitor.generate_monitoring_report(period)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "report": report
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate monitoring report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate monitoring report: {str(e)}")


# =============================================================================
# Data Export Endpoints
# =============================================================================


@router.get("/export/trends/{metric_name}")
async def export_trend_data(metric_name: str, period_days: Optional[int] = 30) -> JSONResponse:
    """
    Export trend data for external analysis.
    
    Args:
        metric_name: Name of the metric to export
        period_days: Export period in days
        
    Returns:
        Exported trend data
    """
    try:
        period = timedelta(days=period_days) if period_days else None
        data = trend_analyzer.export_trend_data(metric_name, period)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "export_data": data
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export trend data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export trend data: {str(e)}")


# =============================================================================
# Health Check Endpoint
# =============================================================================


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check for Ragas integration service.
    
    Returns:
        Service health status
    """
    try:
        health_status = {
            "service": "ragas_integration",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "ragas_evaluator": {
                    "available": ragas_evaluator.is_available(),
                    "status": "healthy" if ragas_evaluator.is_available() else "degraded"
                },
                "trend_analyzer": {
                    "evaluation_count": len(trend_analyzer.evaluation_history),
                    "status": "healthy"
                },
                "quality_monitor": {
                    "status": quality_monitor.status.value,
                    "monitoring_active": quality_monitor.status.value == "active"
                }
            }
        }
        
        # Determine overall status
        if not ragas_evaluator.is_available():
            health_status["status"] = "degraded"
            health_status["message"] = "Ragas library not available - using basic evaluation"
        
        return JSONResponse(
            status_code=200,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "service": "ragas_integration",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )