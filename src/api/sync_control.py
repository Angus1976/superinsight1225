"""
Sync Control Panel API.

Provides RESTful endpoints for sync management and control:
- Job management (start, stop, pause, resume)
- Monitoring and health checks
- Alert management
- Configuration management
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

from src.sync.monitoring.comprehensive_monitor import (
    comprehensive_sync_monitor,
    SyncJobStatus,
    AlertSeverity
)
from src.sync.monitoring.sync_metrics import sync_metrics
from src.sync.quality.data_validator import data_sync_quality_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync-control"])


# Request/Response Models
class StartSyncJobRequest(BaseModel):
    """Request to start a sync job."""
    source_id: str = Field(..., description="Source data source ID")
    target_id: str = Field(..., description="Target data source ID")
    sync_type: str = Field(default="incremental", description="Sync type: full, incremental, realtime")
    config: Dict[str, Any] = Field(default_factory=dict, description="Sync configuration")
    schedule: Optional[str] = Field(None, description="Cron schedule for recurring sync")


class SyncJobResponse(BaseModel):
    """Response for sync job operations."""
    job_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class AlertAcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""
    alert_id: str
    user: str
    notes: Optional[str] = None


class UpdateThresholdsRequest(BaseModel):
    """Request to update health thresholds."""
    max_latency_ms: Optional[float] = None
    min_throughput: Optional[float] = None
    max_error_rate: Optional[float] = None
    max_queue_depth: Optional[int] = None
    max_active_jobs: Optional[int] = None


class QualityThresholdsRequest(BaseModel):
    """Request to update quality thresholds."""
    minimum_score: Optional[float] = None
    warning_score: Optional[float] = None
    critical_error_count: Optional[int] = None


# Job Management Endpoints
@router.post("/jobs/start", response_model=SyncJobResponse)
async def start_sync_job(
    request: StartSyncJobRequest,
    background_tasks: BackgroundTasks
):
    """Start a new sync job."""
    try:
        import uuid
        job_id = str(uuid.uuid4())
        
        # Start job tracking
        job = comprehensive_sync_monitor.start_job(
            job_id=job_id,
            source_id=request.source_id,
            target_id=request.target_id,
            metadata={"sync_type": request.sync_type, "config": request.config}
        )
        
        # In a real implementation, this would trigger the actual sync
        # background_tasks.add_task(run_sync_job, job_id, request)
        
        return SyncJobResponse(
            job_id=job_id,
            status="started",
            message=f"Sync job started: {request.source_id} -> {request.target_id}",
            data=job.to_dict()
        )
    except Exception as e:
        logger.error(f"Failed to start sync job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/stop", response_model=SyncJobResponse)
async def stop_sync_job(job_id: str):
    """Stop a running sync job."""
    try:
        job = comprehensive_sync_monitor.complete_job(job_id, SyncJobStatus.CANCELLED)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return SyncJobResponse(
            job_id=job_id,
            status="stopped",
            message="Sync job stopped",
            data=job.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop sync job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/pause", response_model=SyncJobResponse)
async def pause_sync_job(job_id: str):
    """Pause a running sync job."""
    try:
        # Update job status
        job_status = comprehensive_sync_monitor.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # In real implementation, this would pause the actual sync process
        comprehensive_sync_monitor.add_job_checkpoint(
            job_id, "paused", {"paused_at": datetime.now().isoformat()}
        )
        
        return SyncJobResponse(
            job_id=job_id,
            status="paused",
            message="Sync job paused",
            data=job_status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause sync job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/resume", response_model=SyncJobResponse)
async def resume_sync_job(job_id: str):
    """Resume a paused sync job."""
    try:
        job_status = comprehensive_sync_monitor.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        comprehensive_sync_monitor.add_job_checkpoint(
            job_id, "resumed", {"resumed_at": datetime.now().isoformat()}
        )
        
        return SyncJobResponse(
            job_id=job_id,
            status="running",
            message="Sync job resumed",
            data=job_status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume sync job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_sync_job(job_id: str) -> Dict[str, Any]:
    """Get details of a specific sync job."""
    job_status = comprehensive_sync_monitor.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return job_status


@router.get("/jobs")
async def list_sync_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    source_id: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """List sync jobs."""
    active_jobs = comprehensive_sync_monitor.get_active_jobs()
    recent_jobs = comprehensive_sync_monitor.get_recent_jobs(limit)
    
    # Apply filters
    if status:
        active_jobs = [j for j in active_jobs if j.get("status") == status]
        recent_jobs = [j for j in recent_jobs if j.get("status") == status]
    
    if source_id:
        active_jobs = [j for j in active_jobs if j.get("source_id") == source_id]
        recent_jobs = [j for j in recent_jobs if j.get("source_id") == source_id]
    
    return {
        "active_jobs": active_jobs,
        "recent_jobs": recent_jobs,
        "total_active": len(active_jobs),
        "total_recent": len(recent_jobs)
    }


# Monitoring Endpoints
@router.get("/health")
async def get_sync_health() -> Dict[str, Any]:
    """Get sync system health status."""
    return comprehensive_sync_monitor.get_health_status()


@router.get("/dashboard")
async def get_dashboard_data() -> Dict[str, Any]:
    """Get data for sync monitoring dashboard."""
    return comprehensive_sync_monitor.get_dashboard_data()


@router.get("/metrics")
async def get_sync_metrics() -> Dict[str, Any]:
    """Get sync system metrics."""
    return {
        "all_metrics": sync_metrics.get_all_metrics(),
        "throughput": sync_metrics.get_throughput_stats(),
        "latency_percentiles": sync_metrics.get_latency_percentiles()
    }


@router.get("/metrics/prometheus")
async def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus format."""
    return sync_metrics.export_prometheus()


# Alert Management Endpoints
@router.get("/alerts")
async def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(100, ge=1, le=500)
) -> Dict[str, Any]:
    """List sync alerts."""
    severity_enum = AlertSeverity(severity) if severity else None
    
    alerts = comprehensive_sync_monitor.get_alerts(
        severity=severity_enum,
        acknowledged=acknowledged,
        limit=limit
    )
    
    return {
        "alerts": alerts,
        "total": len(alerts)
    }


@router.post("/alerts/acknowledge")
async def acknowledge_alert(request: AlertAcknowledgeRequest) -> Dict[str, Any]:
    """Acknowledge an alert."""
    success = comprehensive_sync_monitor.acknowledge_alert(
        alert_id=request.alert_id,
        user=request.user
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {request.alert_id} not found")
    
    return {
        "success": True,
        "message": f"Alert {request.alert_id} acknowledged by {request.user}"
    }


@router.post("/alerts/create")
async def create_alert(
    severity: str,
    title: str,
    message: str,
    job_id: Optional[str] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a manual alert."""
    alert = comprehensive_sync_monitor.create_alert(
        severity=AlertSeverity(severity),
        title=title,
        message=message,
        job_id=job_id,
        source_id=source_id
    )
    
    return alert.to_dict()


# Configuration Endpoints
@router.get("/config/thresholds")
async def get_thresholds() -> Dict[str, Any]:
    """Get current health thresholds."""
    return {
        "health_thresholds": comprehensive_sync_monitor.health_thresholds,
        "quality_thresholds": data_sync_quality_manager.quality_thresholds
    }


@router.put("/config/thresholds/health")
async def update_health_thresholds(request: UpdateThresholdsRequest) -> Dict[str, Any]:
    """Update health thresholds."""
    updates = request.dict(exclude_none=True)
    
    for key, value in updates.items():
        if key in comprehensive_sync_monitor.health_thresholds:
            comprehensive_sync_monitor.health_thresholds[key] = value
    
    return {
        "success": True,
        "thresholds": comprehensive_sync_monitor.health_thresholds
    }


@router.put("/config/thresholds/quality")
async def update_quality_thresholds(request: QualityThresholdsRequest) -> Dict[str, Any]:
    """Update quality thresholds."""
    updates = request.dict(exclude_none=True)
    data_sync_quality_manager.set_thresholds(updates)
    
    return {
        "success": True,
        "thresholds": data_sync_quality_manager.quality_thresholds
    }


# Quality Endpoints
@router.get("/quality/report")
async def get_quality_report(
    sync_job_id: Optional[str] = None,
    source_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Get quality report for sync operations."""
    return await data_sync_quality_manager.get_quality_report(
        sync_job_id=sync_job_id,
        source_id=source_id,
        limit=limit
    )


# Lineage Endpoints
@router.get("/lineage/visualization")
async def get_lineage_visualization(
    job_id: Optional[str] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get lineage data for visualization."""
    from src.sync.lineage.lineage_tracker import lineage_tracker
    
    return lineage_tracker.get_visualization_data(
        filter_job_id=job_id,
        filter_source_id=source_id
    )


@router.get("/lineage/impact/{node_id}")
async def get_downstream_impact(node_id: str) -> Dict[str, Any]:
    """Get downstream impact analysis for a node."""
    from src.sync.lineage.lineage_tracker import lineage_tracker
    
    return lineage_tracker.get_downstream_impact(node_id)


@router.get("/lineage/sources/{node_id}")
async def get_upstream_sources(node_id: str) -> Dict[str, Any]:
    """Get upstream sources for a node."""
    from src.sync.lineage.lineage_tracker import lineage_tracker
    
    return lineage_tracker.get_upstream_sources(node_id)


@router.get("/lineage/path")
async def get_data_flow_path(
    source_id: str,
    target_id: str
) -> Dict[str, Any]:
    """Get data flow path between source and target."""
    from src.sync.lineage.lineage_tracker import lineage_tracker
    
    return lineage_tracker.get_data_flow_path(source_id, target_id)


@router.get("/lineage/report")
async def get_lineage_report(
    sync_job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Generate lineage report."""
    from src.sync.lineage.lineage_tracker import lineage_tracker
    
    return lineage_tracker.generate_lineage_report(sync_job_id)
