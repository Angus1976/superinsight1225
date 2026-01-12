"""
Quality Governance API for SuperInsight Platform.

Provides comprehensive API endpoints for quality governance:
- Quality workflow management
- Anomaly detection and remediation
- Ticket management
- Progress tracking
- Compliance monitoring
- Report generation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/quality-governance", tags=["Quality Governance"])


# ============== Pydantic Models ==============

class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection."""
    entity_id: str
    entity_type: str
    metrics: Dict[str, float]
    context: Optional[Dict[str, Any]] = None


class RemediationRequest(BaseModel):
    """Request for creating remediation."""
    anomaly_id: str
    entity_id: str
    entity_type: str
    anomaly_type: str
    severity: str
    context: Optional[Dict[str, Any]] = None


class QualityTicketRequest(BaseModel):
    """Request for creating quality ticket."""
    ticket_type: str
    title: str
    description: str
    project_id: str
    priority: str = "medium"
    anomaly_id: Optional[str] = None
    task_id: Optional[str] = None
    quality_score: Optional[float] = None


class ReannotationRequest(BaseModel):
    """Request for creating reannotation task."""
    original_task_id: str
    project_id: str
    data_item_id: str
    reason: str
    priority: str = "medium"
    quality_threshold: float = 0.8


class ProgressRecordRequest(BaseModel):
    """Request for creating progress record."""
    entity_id: str
    entity_type: str
    name: str
    description: Optional[str] = None
    target_date: Optional[str] = None
    owner: Optional[str] = None
    milestone_template: Optional[str] = None


class WorkflowInstanceRequest(BaseModel):
    """Request for creating workflow instance."""
    workflow_id: str
    entity_id: str
    entity_type: str
    owner: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ComplianceCheckRequest(BaseModel):
    """Request for compliance check."""
    data: Dict[str, Any]
    categories: Optional[List[str]] = None
    rule_ids: Optional[List[str]] = None


class ReportGenerationRequest(BaseModel):
    """Request for report generation."""
    report_type: str
    title: str
    format: str = "json"
    project_id: Optional[str] = None
    period_days: int = 7


# ============== Dashboard Endpoints ==============

@router.get("/dashboard")
async def get_governance_dashboard(
    project_id: Optional[str] = Query(None, description="Project filter"),
    period_days: int = Query(7, description="Period in days")
) -> Dict[str, Any]:
    """
    Get comprehensive quality governance dashboard.
    
    Returns aggregated data from all quality governance modules.
    """
    try:
        from src.quality.anomaly_detector import quality_anomaly_detector
        from src.quality.auto_remediation import auto_remediation_engine
        from src.ticket.quality_ticket_manager import quality_ticket_manager
        from src.quality.progress_tracker import progress_tracker
        from src.quality.workflow_engine import workflow_engine
        from src.quality.compliance_tracker import compliance_tracker
        
        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "period_days": period_days,
            "project_id": project_id,
            
            # Anomaly statistics
            "anomalies": quality_anomaly_detector.get_anomaly_statistics(period_days),
            
            # Remediation statistics
            "remediation": auto_remediation_engine.get_statistics(),
            
            # Ticket statistics
            "tickets": quality_ticket_manager.get_statistics(project_id, period_days),
            
            # Progress statistics
            "progress": progress_tracker.get_statistics(period_days=period_days),
            
            # Workflow statistics
            "workflows": workflow_engine.get_statistics(),
            
            # Compliance statistics
            "compliance": compliance_tracker.get_statistics(period_days * 24),
            
            # Summary metrics
            "summary": {
                "active_anomalies": len(quality_anomaly_detector.get_active_anomalies()),
                "pending_remediations": len(auto_remediation_engine.get_pending_actions()),
                "open_tickets": len(quality_ticket_manager.list_tickets(status="open")),
                "active_workflows": workflow_engine.get_statistics().get("active_instances", 0),
                "compliance_score": compliance_tracker.get_compliance_score(period_hours=period_days * 24),
                "active_alerts": len(compliance_tracker.get_active_alerts())
            }
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Error getting governance dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Anomaly Detection Endpoints ==============

@router.post("/anomalies/detect")
async def detect_anomalies(request: AnomalyDetectionRequest) -> Dict[str, Any]:
    """Detect anomalies in provided metrics."""
    try:
        from src.quality.anomaly_detector import quality_anomaly_detector
        
        anomalies = quality_anomaly_detector.detect_anomalies(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            metrics=request.metrics,
            context=request.context
        )
        
        return {
            "detected_count": len(anomalies),
            "anomalies": [a.to_dict() for a in anomalies]
        }
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies")
async def list_anomalies(
    entity_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100)
) -> Dict[str, Any]:
    """List active anomalies."""
    try:
        from src.quality.anomaly_detector import quality_anomaly_detector, AnomalySeverity
        
        severity_enum = AnomalySeverity(severity) if severity else None
        anomalies = quality_anomaly_detector.get_active_anomalies(
            entity_type=entity_type,
            severity=severity_enum
        )
        
        return {
            "total": len(anomalies),
            "anomalies": [a.to_dict() for a in anomalies[:limit]]
        }
        
    except Exception as e:
        logger.error(f"Error listing anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/anomalies/{anomaly_id}/status")
async def update_anomaly_status(
    anomaly_id: str,
    status: str = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """Update anomaly status."""
    try:
        from src.quality.anomaly_detector import quality_anomaly_detector, AnomalyStatus
        
        success = quality_anomaly_detector.update_anomaly_status(
            anomaly_id=anomaly_id,
            status=AnomalyStatus(status),
            resolution_notes=notes
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error updating anomaly status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Remediation Endpoints ==============

@router.post("/remediation/create")
async def create_remediation(request: RemediationRequest) -> Dict[str, Any]:
    """Create remediation actions for an anomaly."""
    try:
        from src.quality.auto_remediation import auto_remediation_engine
        
        actions = await auto_remediation_engine.create_remediation(
            anomaly_id=request.anomaly_id,
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            anomaly_type=request.anomaly_type,
            severity=request.severity,
            context=request.context
        )
        
        return {
            "created_count": len(actions),
            "actions": [a.to_dict() for a in actions]
        }
        
    except Exception as e:
        logger.error(f"Error creating remediation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remediation/pending")
async def list_pending_remediations(
    priority: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """List pending remediation actions."""
    try:
        from src.quality.auto_remediation import auto_remediation_engine, RemediationPriority
        
        priority_enum = RemediationPriority(priority) if priority else None
        actions = auto_remediation_engine.get_pending_actions(priority=priority_enum)
        
        return {
            "total": len(actions),
            "actions": [a.to_dict() for a in actions]
        }
        
    except Exception as e:
        logger.error(f"Error listing pending remediations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remediation/{action_id}/execute")
async def execute_remediation(
    action_id: str,
    force: bool = Query(False)
) -> Dict[str, Any]:
    """Execute a remediation action."""
    try:
        from src.quality.auto_remediation import auto_remediation_engine
        
        success, error = await auto_remediation_engine.execute_action(action_id, force=force)
        
        return {
            "success": success,
            "error": error
        }
        
    except Exception as e:
        logger.error(f"Error executing remediation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remediation/{action_id}/approve")
async def approve_remediation(
    action_id: str,
    approved_by: str = Body(..., embed=True)
) -> Dict[str, Any]:
    """Approve a pending remediation action."""
    try:
        from src.quality.auto_remediation import auto_remediation_engine
        
        success = auto_remediation_engine.approve_action(action_id, approved_by)
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error approving remediation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Quality Ticket Endpoints ==============

@router.post("/tickets")
async def create_quality_ticket(request: QualityTicketRequest) -> Dict[str, Any]:
    """Create a quality ticket."""
    try:
        from src.ticket.quality_ticket_manager import (
            quality_ticket_manager,
            QualityTicketType,
            QualityTicketPriority
        )
        
        ticket = await quality_ticket_manager.create_ticket(
            ticket_type=QualityTicketType(request.ticket_type),
            title=request.title,
            description=request.description,
            project_id=request.project_id,
            priority=QualityTicketPriority(request.priority),
            anomaly_id=request.anomaly_id,
            task_id=request.task_id,
            quality_score=request.quality_score
        )
        
        return ticket.to_dict()
        
    except Exception as e:
        logger.error(f"Error creating quality ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets")
async def list_quality_tickets(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    limit: int = Query(100)
) -> Dict[str, Any]:
    """List quality tickets."""
    try:
        from src.ticket.quality_ticket_manager import (
            quality_ticket_manager,
            QualityTicketStatus,
            QualityTicketPriority
        )
        
        status_enum = QualityTicketStatus(status) if status else None
        priority_enum = QualityTicketPriority(priority) if priority else None
        
        tickets = quality_ticket_manager.list_tickets(
            project_id=project_id,
            status=status_enum,
            priority=priority_enum,
            assigned_to=assigned_to,
            limit=limit
        )
        
        return {
            "total": len(tickets),
            "tickets": [t.to_dict() for t in tickets]
        }
        
    except Exception as e:
        logger.error(f"Error listing quality tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/{ticket_id}")
async def get_quality_ticket(ticket_id: str) -> Dict[str, Any]:
    """Get a quality ticket by ID."""
    try:
        from src.ticket.quality_ticket_manager import quality_ticket_manager
        
        ticket = quality_ticket_manager.get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return ticket.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quality ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tickets/{ticket_id}/assign")
async def assign_quality_ticket(
    ticket_id: str,
    expert_id: Optional[str] = Body(None, embed=True),
    assigned_by: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """Assign a quality ticket."""
    try:
        from src.ticket.quality_ticket_manager import quality_ticket_manager
        
        success, assigned_id = await quality_ticket_manager.assign_ticket(
            ticket_id=ticket_id,
            expert_id=expert_id,
            assigned_by=assigned_by
        )
        
        return {
            "success": success,
            "assigned_to": assigned_id
        }
        
    except Exception as e:
        logger.error(f"Error assigning quality ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tickets/{ticket_id}/resolve")
async def resolve_quality_ticket(
    ticket_id: str,
    resolved_by: str = Body(..., embed=True),
    resolution_notes: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """Resolve a quality ticket."""
    try:
        from src.ticket.quality_ticket_manager import quality_ticket_manager
        
        success = await quality_ticket_manager.resolve_ticket(
            ticket_id=ticket_id,
            resolved_by=resolved_by,
            resolution_notes=resolution_notes
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error resolving quality ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Reannotation Endpoints ==============

@router.post("/reannotation/tasks")
async def create_reannotation_task(request: ReannotationRequest) -> Dict[str, Any]:
    """Create a reannotation task."""
    try:
        from src.quality.reannotation_service import (
            reannotation_service,
            ReannotationReason,
            ReannotationPriority
        )
        
        task = await reannotation_service.create_reannotation_task(
            original_task_id=request.original_task_id,
            project_id=request.project_id,
            data_item_id=request.data_item_id,
            reason=ReannotationReason(request.reason),
            priority=ReannotationPriority(request.priority),
            quality_threshold=request.quality_threshold
        )
        
        return task.to_dict()
        
    except Exception as e:
        logger.error(f"Error creating reannotation task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reannotation/tasks")
async def list_reannotation_tasks(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    annotator_id: Optional[str] = Query(None),
    limit: int = Query(100)
) -> Dict[str, Any]:
    """List reannotation tasks."""
    try:
        from src.quality.reannotation_service import (
            reannotation_service,
            ReannotationStatus
        )
        
        status_enum = ReannotationStatus(status) if status else None
        
        tasks = reannotation_service.list_tasks(
            project_id=project_id,
            status=status_enum,
            annotator_id=annotator_id,
            limit=limit
        )
        
        return {
            "total": len(tasks),
            "tasks": [t.to_dict() for t in tasks]
        }
        
    except Exception as e:
        logger.error(f"Error listing reannotation tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reannotation/tasks/{task_id}/complete")
async def complete_reannotation_task(
    task_id: str,
    new_annotation: Dict[str, Any] = Body(...),
    auto_verify: bool = Query(True)
) -> Dict[str, Any]:
    """Complete a reannotation task."""
    try:
        from src.quality.reannotation_service import reannotation_service
        
        success, verification = await reannotation_service.complete_task(
            task_id=task_id,
            new_annotation=new_annotation,
            auto_verify=auto_verify
        )
        
        return {
            "success": success,
            "verification": verification
        }
        
    except Exception as e:
        logger.error(f"Error completing reannotation task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reannotation/statistics")
async def get_reannotation_statistics(
    project_id: Optional[str] = Query(None),
    days: int = Query(30)
) -> Dict[str, Any]:
    """Get reannotation statistics."""
    try:
        from src.quality.reannotation_service import reannotation_service
        
        return reannotation_service.get_statistics(project_id=project_id, days=days)
        
    except Exception as e:
        logger.error(f"Error getting reannotation statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Progress Tracking Endpoints ==============

@router.post("/progress")
async def create_progress_record(request: ProgressRecordRequest) -> Dict[str, Any]:
    """Create a progress tracking record."""
    try:
        from src.quality.progress_tracker import progress_tracker
        
        target_date = None
        if request.target_date:
            target_date = datetime.fromisoformat(request.target_date)
        
        record = progress_tracker.create_progress_record(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            name=request.name,
            description=request.description,
            target_date=target_date,
            owner=request.owner,
            milestone_template=request.milestone_template
        )
        
        return record.to_dict()
        
    except Exception as e:
        logger.error(f"Error creating progress record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress")
async def list_progress_records(
    entity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    limit: int = Query(100)
) -> Dict[str, Any]:
    """List progress records."""
    try:
        from src.quality.progress_tracker import progress_tracker, ProgressStatus
        
        status_enum = ProgressStatus(status) if status else None
        
        records = progress_tracker.list_records(
            entity_type=entity_type,
            status=status_enum,
            owner=owner,
            limit=limit
        )
        
        return {
            "total": len(records),
            "records": [r.to_dict() for r in records]
        }
        
    except Exception as e:
        logger.error(f"Error listing progress records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{record_id}")
async def get_progress_record(record_id: str) -> Dict[str, Any]:
    """Get a progress record by ID."""
    try:
        from src.quality.progress_tracker import progress_tracker
        
        record = progress_tracker.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Progress record not found")
        
        return record.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/progress/{record_id}")
async def update_progress(
    record_id: str,
    progress_percent: float = Body(..., embed=True),
    updated_by: Optional[str] = Body(None, embed=True),
    notes: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """Update progress for a record."""
    try:
        from src.quality.progress_tracker import progress_tracker
        
        update = progress_tracker.update_progress(
            record_id=record_id,
            progress_percent=progress_percent,
            updated_by=updated_by,
            notes=notes
        )
        
        if not update:
            raise HTTPException(status_code=404, detail="Progress record not found")
        
        return update.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{record_id}/timeline")
async def get_progress_timeline(record_id: str) -> Dict[str, Any]:
    """Get timeline data for a progress record."""
    try:
        from src.quality.progress_tracker import progress_tracker
        
        timeline = progress_tracker.get_timeline_data(record_id)
        if not timeline:
            raise HTTPException(status_code=404, detail="Progress record not found")
        
        return timeline
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/progress/{record_id}/milestones/{milestone_id}/complete")
async def complete_milestone(
    record_id: str,
    milestone_id: str,
    completed_by: Optional[str] = Body(None, embed=True),
    notes: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """Complete a milestone."""
    try:
        from src.quality.progress_tracker import progress_tracker
        
        success = progress_tracker.complete_milestone(
            record_id=record_id,
            milestone_id=milestone_id,
            completed_by=completed_by,
            notes=notes
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error completing milestone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Workflow Endpoints ==============

@router.post("/workflows")
async def create_workflow_instance(request: WorkflowInstanceRequest) -> Dict[str, Any]:
    """Create a workflow instance."""
    try:
        from src.quality.workflow_engine import workflow_engine
        
        instance = await workflow_engine.create_instance(
            workflow_id=request.workflow_id,
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            owner=request.owner,
            context=request.context
        )
        
        if not instance:
            raise HTTPException(status_code=400, detail="Failed to create workflow instance")
        
        return instance.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workflow instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def list_workflow_instances(
    workflow_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    limit: int = Query(100)
) -> Dict[str, Any]:
    """List workflow instances."""
    try:
        from src.quality.workflow_engine import workflow_engine, WorkflowState
        
        state_enum = WorkflowState(state) if state else None
        
        instances = workflow_engine.list_instances(
            workflow_id=workflow_id,
            state=state_enum,
            owner=owner,
            limit=limit
        )
        
        return {
            "total": len(instances),
            "instances": [i.to_dict() for i in instances]
        }
        
    except Exception as e:
        logger.error(f"Error listing workflow instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{instance_id}")
async def get_workflow_instance(instance_id: str) -> Dict[str, Any]:
    """Get a workflow instance by ID."""
    try:
        from src.quality.workflow_engine import workflow_engine
        
        instance = workflow_engine.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        
        return instance.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{instance_id}/transition")
async def transition_workflow(
    instance_id: str,
    target_state: str = Body(..., embed=True),
    triggered_by: Optional[str] = Body(None, embed=True),
    comments: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """Execute a workflow state transition."""
    try:
        from src.quality.workflow_engine import workflow_engine, WorkflowState
        
        success = await workflow_engine.transition(
            instance_id=instance_id,
            target_state=WorkflowState(target_state),
            triggered_by=triggered_by,
            comments=comments
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error transitioning workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{instance_id}/transitions")
async def get_available_transitions(instance_id: str) -> Dict[str, Any]:
    """Get available transitions for a workflow instance."""
    try:
        from src.quality.workflow_engine import workflow_engine
        
        transitions = workflow_engine.get_available_transitions(instance_id)
        
        return {
            "transitions": [t.to_dict() for t in transitions]
        }
        
    except Exception as e:
        logger.error(f"Error getting available transitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/definitions")
async def list_workflow_definitions() -> Dict[str, Any]:
    """List available workflow definitions."""
    try:
        from src.quality.workflow_engine import workflow_engine
        
        definitions = list(workflow_engine.definitions.values())
        
        return {
            "total": len(definitions),
            "definitions": [d.to_dict() for d in definitions]
        }
        
    except Exception as e:
        logger.error(f"Error listing workflow definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Compliance Endpoints ==============

@router.post("/compliance/check")
async def run_compliance_check(request: ComplianceCheckRequest) -> Dict[str, Any]:
    """Run compliance checks on provided data."""
    try:
        from src.quality.compliance_tracker import compliance_tracker, ComplianceCategory
        
        categories = None
        if request.categories:
            categories = [ComplianceCategory(c) for c in request.categories]
        
        results = await compliance_tracker.run_compliance_check(
            data=request.data,
            categories=categories,
            rule_ids=request.rule_ids
        )
        
        return {
            "total_checks": len(results),
            "passed": sum(1 for r in results if r.status.value == "passed"),
            "failed": sum(1 for r in results if r.status.value == "failed"),
            "results": [r.to_dict() for r in results]
        }
        
    except Exception as e:
        logger.error(f"Error running compliance check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/score")
async def get_compliance_score(
    category: Optional[str] = Query(None),
    period_hours: int = Query(24)
) -> Dict[str, Any]:
    """Get compliance score."""
    try:
        from src.quality.compliance_tracker import compliance_tracker, ComplianceCategory
        
        category_enum = ComplianceCategory(category) if category else None
        
        score = compliance_tracker.get_compliance_score(
            category=category_enum,
            period_hours=period_hours
        )
        
        return {
            "score": score,
            "category": category,
            "period_hours": period_hours
        }
        
    except Exception as e:
        logger.error(f"Error getting compliance score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/alerts")
async def list_compliance_alerts(
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """List active compliance alerts."""
    try:
        from src.quality.compliance_tracker import (
            compliance_tracker,
            ComplianceCategory,
            ComplianceSeverity
        )
        
        category_enum = ComplianceCategory(category) if category else None
        severity_enum = ComplianceSeverity(severity) if severity else None
        
        alerts = compliance_tracker.get_active_alerts(
            category=category_enum,
            severity=severity_enum
        )
        
        return {
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts]
        }
        
    except Exception as e:
        logger.error(f"Error listing compliance alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance/alerts/{alert_id}/acknowledge")
async def acknowledge_compliance_alert(
    alert_id: str,
    acknowledged_by: str = Body(..., embed=True)
) -> Dict[str, Any]:
    """Acknowledge a compliance alert."""
    try:
        from src.quality.compliance_tracker import compliance_tracker
        
        success = compliance_tracker.acknowledge_alert(alert_id, acknowledged_by)
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error acknowledging compliance alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance/alerts/{alert_id}/resolve")
async def resolve_compliance_alert(
    alert_id: str,
    resolved_by: str = Body(..., embed=True)
) -> Dict[str, Any]:
    """Resolve a compliance alert."""
    try:
        from src.quality.compliance_tracker import compliance_tracker
        
        success = compliance_tracker.resolve_alert(alert_id, resolved_by)
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error resolving compliance alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/rules")
async def list_compliance_rules() -> Dict[str, Any]:
    """List compliance rules."""
    try:
        from src.quality.compliance_tracker import compliance_tracker
        
        rules = list(compliance_tracker.rules.values())
        
        return {
            "total": len(rules),
            "enabled": sum(1 for r in rules if r.enabled),
            "rules": [r.to_dict() for r in rules]
        }
        
    except Exception as e:
        logger.error(f"Error listing compliance rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/trend")
async def get_compliance_trend(days: int = Query(7)) -> Dict[str, Any]:
    """Get compliance trend data."""
    try:
        from src.quality.compliance_tracker import compliance_tracker
        
        trend = compliance_tracker.get_trend_data(days=days)
        
        return {
            "days": days,
            "trend": trend
        }
        
    except Exception as e:
        logger.error(f"Error getting compliance trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance/snapshot")
async def create_compliance_snapshot() -> Dict[str, Any]:
    """Create a compliance status snapshot."""
    try:
        from src.quality.compliance_tracker import compliance_tracker
        
        snapshot = compliance_tracker.create_snapshot()
        
        return snapshot.to_dict()
        
    except Exception as e:
        logger.error(f"Error creating compliance snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Report Endpoints ==============

@router.post("/reports/generate")
async def generate_report(request: ReportGenerationRequest) -> Dict[str, Any]:
    """Generate a quality report."""
    try:
        from src.quality.report_generator import (
            quality_report_generator,
            ReportType,
            ReportFormat
        )
        
        period_end = datetime.now()
        period_start = period_end - timedelta(days=request.period_days)
        
        report = await quality_report_generator.generate_report(
            report_type=ReportType(request.report_type),
            title=request.title,
            format=ReportFormat(request.format),
            project_id=request.project_id,
            period_start=period_start,
            period_end=period_end
        )
        
        return report.to_dict()
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def list_reports(
    report_type: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50)
) -> Dict[str, Any]:
    """List generated reports."""
    try:
        from src.quality.report_generator import (
            quality_report_generator,
            ReportType,
            ReportStatus
        )
        
        type_enum = ReportType(report_type) if report_type else None
        status_enum = ReportStatus(status) if status else None
        
        reports = quality_report_generator.list_reports(
            report_type=type_enum,
            project_id=project_id,
            status=status_enum,
            limit=limit
        )
        
        return {
            "total": len(reports),
            "reports": [r.to_dict() for r in reports]
        }
        
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    """Get a report by ID."""
    try:
        from src.quality.report_generator import quality_report_generator
        
        report = quality_report_generator.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return report.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: str,
    format: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Export a report in specified format."""
    try:
        from src.quality.report_generator import quality_report_generator, ReportFormat
        
        format_enum = ReportFormat(format) if format else None
        
        content = quality_report_generator.export_report(report_id, format=format_enum)
        if not content:
            raise HTTPException(status_code=404, detail="Report not found or not completed")
        
        return {
            "report_id": report_id,
            "format": format or "json",
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/templates")
async def list_report_templates() -> Dict[str, Any]:
    """List available report templates."""
    try:
        from src.quality.report_generator import quality_report_generator
        
        templates = list(quality_report_generator.templates.values())
        
        return {
            "total": len(templates),
            "templates": [t.to_dict() for t in templates]
        }
        
    except Exception as e:
        logger.error(f"Error listing report templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))
