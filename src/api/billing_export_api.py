"""
API endpoints for billing export functionality.

Provides REST API for exporting billing data in various formats
with permission controls and batch processing.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from uuid import UUID
import os
import io
from pathlib import Path

from src.billing.excel_exporter import (
    BillingExcelExporter, ExportFormat, ExportTemplate, 
    ExportPermission, ExportScheduler
)
from src.billing.models import BillingRecord, Bill, BillingReport
from src.billing.invoice_generator import DetailedInvoiceGenerator


router = APIRouter(prefix="/api/billing/export", tags=["billing-export"])


class ExportRequest(BaseModel):
    """Export request model."""
    export_type: str = Field(..., description="Type of data to export")
    format_type: ExportFormat = Field(default=ExportFormat.EXCEL, description="Export format")
    template: ExportTemplate = Field(default=ExportTemplate.STANDARD, description="Export template")
    tenant_id: str = Field(..., description="Tenant identifier")
    start_date: Optional[date] = Field(None, description="Start date for data range")
    end_date: Optional[date] = Field(None, description="End date for data range")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")
    custom_filename: Optional[str] = Field(None, description="Custom filename")


class BatchExportRequest(BaseModel):
    """Batch export request model."""
    exports: List[ExportRequest] = Field(..., description="List of export requests")
    user_id: str = Field(..., description="User requesting exports")


class ScheduleExportRequest(BaseModel):
    """Schedule export request model."""
    tenant_id: str = Field(..., description="Tenant identifier")
    schedule_type: str = Field(..., description="Schedule type (daily/weekly/monthly)")
    export_config: Dict[str, Any] = Field(..., description="Export configuration")
    start_time: Optional[datetime] = Field(None, description="Schedule start time")


class ExportResponse(BaseModel):
    """Export response model."""
    job_id: str = Field(..., description="Export job identifier")
    status: str = Field(..., description="Export status")
    message: str = Field(..., description="Status message")
    download_url: Optional[str] = Field(None, description="Download URL when completed")


class ExportStatusResponse(BaseModel):
    """Export status response model."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current status")
    progress: int = Field(..., description="Progress percentage")
    created_at: datetime = Field(..., description="Job creation time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    file_path: Optional[str] = Field(None, description="Generated file path")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# Initialize exporter and scheduler
exporter = BillingExcelExporter()
scheduler = ExportScheduler(exporter)


def get_user_permission(user_id: str) -> ExportPermission:
    """
    Get user's export permission level.
    
    Args:
        user_id: User identifier
        
    Returns:
        User's permission level
    """
    # This would typically check user roles/permissions from database
    # For now, return full access for demonstration
    return ExportPermission.FULL_ACCESS


def get_billing_records(tenant_id: str, start_date: Optional[date] = None, 
                       end_date: Optional[date] = None,
                       filters: Optional[Dict[str, Any]] = None) -> List[BillingRecord]:
    """
    Fetch billing records for export.
    
    Args:
        tenant_id: Tenant identifier
        start_date: Start date filter
        end_date: End date filter
        filters: Additional filters
        
    Returns:
        List of billing records
    """
    # This would typically fetch from database
    # For demonstration, return sample data
    from decimal import Decimal
    from uuid import uuid4
    
    sample_records = []
    for i in range(10):
        record = BillingRecord(
            tenant_id=tenant_id,
            user_id=f"user_{i}",
            task_id=uuid4(),
            annotation_count=100 + i * 10,
            time_spent=3600 + i * 300,
            cost=Decimal(str(50.0 + i * 5)),
            billing_date=date.today(),
            created_at=datetime.now()
        )
        sample_records.append(record)
    
    return sample_records


@router.post("/request", response_model=ExportResponse)
async def request_export(
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Query(..., description="User requesting export")
):
    """
    Request a new export job.
    
    Args:
        export_request: Export configuration
        background_tasks: FastAPI background tasks
        user_id: User identifier
        
    Returns:
        Export job information
    """
    try:
        # Get user permissions
        permission = get_user_permission(user_id)
        
        # Create export job
        job_id = exporter.create_export_job(
            user_id=user_id,
            export_type=export_request.export_type,
            format_type=export_request.format_type,
            template=export_request.template,
            permission=permission
        )
        
        if not job_id:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions for this export type"
            )
        
        # Fetch data for export
        if export_request.export_type == "billing_records":
            data = get_billing_records(
                tenant_id=export_request.tenant_id,
                start_date=export_request.start_date,
                end_date=export_request.end_date,
                filters=export_request.filters
            )
        elif export_request.export_type == "invoices":
            # Generate sample invoice data
            invoice_generator = DetailedInvoiceGenerator()
            billing_records = get_billing_records(export_request.tenant_id)
            data = invoice_generator.generate_detailed_invoice(
                tenant_id=export_request.tenant_id,
                billing_period=datetime.now().strftime("%Y-%m"),
                billing_records=billing_records
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export type: {export_request.export_type}"
            )
        
        # Schedule export processing
        background_tasks.add_task(exporter.schedule_export, job_id, data)
        
        return ExportResponse(
            job_id=job_id,
            status="pending",
            message="Export job created successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[ExportResponse])
async def request_batch_export(
    batch_request: BatchExportRequest,
    background_tasks: BackgroundTasks
):
    """
    Request multiple exports in batch.
    
    Args:
        batch_request: Batch export configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        List of export job information
    """
    try:
        permission = get_user_permission(batch_request.user_id)
        responses = []
        
        for export_req in batch_request.exports:
            # Create individual export job
            job_id = exporter.create_export_job(
                user_id=batch_request.user_id,
                export_type=export_req.export_type,
                format_type=export_req.format_type,
                template=export_req.template,
                permission=permission
            )
            
            if job_id:
                # Fetch data and schedule processing
                if export_req.export_type == "billing_records":
                    data = get_billing_records(
                        tenant_id=export_req.tenant_id,
                        start_date=export_req.start_date,
                        end_date=export_req.end_date,
                        filters=export_req.filters
                    )
                elif export_req.export_type == "invoices":
                    invoice_generator = DetailedInvoiceGenerator()
                    billing_records = get_billing_records(export_req.tenant_id)
                    data = invoice_generator.generate_detailed_invoice(
                        tenant_id=export_req.tenant_id,
                        billing_period=datetime.now().strftime("%Y-%m"),
                        billing_records=billing_records
                    )
                else:
                    continue
                
                background_tasks.add_task(exporter.schedule_export, job_id, data)
                
                responses.append(ExportResponse(
                    job_id=job_id,
                    status="pending",
                    message="Export job created successfully"
                ))
            else:
                responses.append(ExportResponse(
                    job_id="",
                    status="failed",
                    message="Insufficient permissions"
                ))
        
        return responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=ExportStatusResponse)
async def get_export_status(job_id: str):
    """
    Get export job status.
    
    Args:
        job_id: Export job identifier
        
    Returns:
        Export job status information
    """
    try:
        status_info = exporter.get_export_job_status(job_id)
        
        if not status_info:
            raise HTTPException(status_code=404, detail="Export job not found")
        
        return ExportStatusResponse(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{job_id}")
async def download_export(job_id: str):
    """
    Download completed export file.
    
    Args:
        job_id: Export job identifier
        
    Returns:
        File download response
    """
    try:
        status_info = exporter.get_export_job_status(job_id)
        
        if not status_info:
            raise HTTPException(status_code=404, detail="Export job not found")
        
        if status_info["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Export not completed. Current status: {status_info['status']}"
            )
        
        file_path = status_info["file_path"]
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        # Determine media type based on file extension
        file_ext = Path(file_path).suffix.lower()
        media_type_map = {
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.json': 'application/json'
        }
        media_type = media_type_map.get(file_ext, 'application/octet-stream')
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=os.path.basename(file_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_export_templates():
    """
    Get available export templates.
    
    Returns:
        List of available templates
    """
    try:
        templates = {}
        for template in ExportTemplate:
            templates[template.value] = {
                "name": template.value,
                "description": f"{template.value.title()} template"
            }
        
        return {
            "templates": templates,
            "formats": [format_type.value for format_type in ExportFormat]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule", response_model=Dict[str, str])
async def schedule_export(schedule_request: ScheduleExportRequest):
    """
    Schedule recurring exports.
    
    Args:
        schedule_request: Schedule configuration
        
    Returns:
        Schedule information
    """
    try:
        if schedule_request.schedule_type == "daily":
            schedule_id = scheduler.schedule_daily_export(
                tenant_id=schedule_request.tenant_id,
                export_config=schedule_request.export_config
            )
        elif schedule_request.schedule_type == "weekly":
            schedule_id = scheduler.schedule_weekly_export(
                tenant_id=schedule_request.tenant_id,
                export_config=schedule_request.export_config
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported schedule type: {schedule_request.schedule_type}"
            )
        
        return {
            "schedule_id": schedule_id,
            "message": f"{schedule_request.schedule_type.title()} export scheduled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedules/{tenant_id}")
async def get_scheduled_exports(tenant_id: str):
    """
    Get scheduled exports for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        List of scheduled exports
    """
    try:
        schedules = []
        for schedule_id, job_info in scheduler.scheduled_jobs.items():
            if job_info["tenant_id"] == tenant_id:
                schedules.append({
                    "schedule_id": schedule_id,
                    "schedule_type": job_info["schedule_type"],
                    "created_at": job_info["created_at"].isoformat(),
                    "next_run": job_info["next_run"].isoformat(),
                    "config": job_info["config"]
                })
        
        return {"schedules": schedules}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedule/{schedule_id}")
async def cancel_scheduled_export(schedule_id: str):
    """
    Cancel a scheduled export.
    
    Args:
        schedule_id: Schedule identifier
        
    Returns:
        Cancellation confirmation
    """
    try:
        if schedule_id in scheduler.scheduled_jobs:
            del scheduler.scheduled_jobs[schedule_id]
            return {"message": "Scheduled export cancelled successfully"}
        else:
            raise HTTPException(status_code=404, detail="Scheduled export not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom-template")
async def upload_custom_template(
    template_name: str = Query(..., description="Template name"),
    template_file: UploadFile = File(..., description="Template file")
):
    """
    Upload custom export template.
    
    Args:
        template_name: Name for the template
        template_file: Template file upload
        
    Returns:
        Upload confirmation
    """
    try:
        # Validate file type
        if not template_file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only Excel files (.xlsx, .xls) are supported for templates"
            )
        
        # Save template file
        template_dir = Path("templates")
        template_dir.mkdir(exist_ok=True)
        
        template_path = template_dir / f"{template_name}.xlsx"
        
        with open(template_path, "wb") as f:
            content = await template_file.read()
            f.write(content)
        
        return {
            "message": "Custom template uploaded successfully",
            "template_name": template_name,
            "template_path": str(template_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-log")
async def get_export_audit_log(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(100, description="Maximum number of records")
):
    """
    Get export audit log.
    
    Args:
        tenant_id: Optional tenant filter
        user_id: Optional user filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of records
        
    Returns:
        Export audit log entries
    """
    try:
        # Filter export jobs based on criteria
        audit_entries = []
        
        for job_id, job in exporter.export_jobs.items():
            # Apply filters
            if tenant_id and job_id.find(tenant_id) == -1:
                continue
            if user_id and job.user_id != user_id:
                continue
            if start_date and job.created_at.date() < start_date:
                continue
            if end_date and job.created_at.date() > end_date:
                continue
            
            audit_entries.append({
                "job_id": job.job_id,
                "user_id": job.user_id,
                "export_type": job.export_type,
                "format_type": job.format_type.value,
                "template": job.template.value,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "file_path": job.file_path,
                "error_message": job.error_message
            })
        
        # Sort by creation time (newest first) and limit
        audit_entries.sort(key=lambda x: x["created_at"], reverse=True)
        audit_entries = audit_entries[:limit]
        
        return {
            "audit_entries": audit_entries,
            "total_count": len(audit_entries)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_export_statistics(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get export usage statistics.
    
    Args:
        tenant_id: Optional tenant filter
        days: Number of days to analyze
        
    Returns:
        Export usage statistics
    """
    try:
        from collections import defaultdict
        
        # Analyze export jobs
        stats = {
            "total_exports": 0,
            "successful_exports": 0,
            "failed_exports": 0,
            "by_format": defaultdict(int),
            "by_template": defaultdict(int),
            "by_user": defaultdict(int),
            "by_day": defaultdict(int)
        }
        
        cutoff_date = datetime.now() - pd.Timedelta(days=days)
        
        for job in exporter.export_jobs.values():
            if job.created_at < cutoff_date:
                continue
            
            # Apply tenant filter
            if tenant_id and job_id.find(tenant_id) == -1:
                continue
            
            stats["total_exports"] += 1
            
            if job.status.value == "completed":
                stats["successful_exports"] += 1
            elif job.status.value == "failed":
                stats["failed_exports"] += 1
            
            stats["by_format"][job.format_type.value] += 1
            stats["by_template"][job.template.value] += 1
            stats["by_user"][job.user_id] += 1
            stats["by_day"][job.created_at.date().isoformat()] += 1
        
        # Convert defaultdicts to regular dicts
        stats["by_format"] = dict(stats["by_format"])
        stats["by_template"] = dict(stats["by_template"])
        stats["by_user"] = dict(stats["by_user"])
        stats["by_day"] = dict(stats["by_day"])
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))