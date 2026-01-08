"""
Ticket Management API for SuperInsight Platform.

Provides REST API endpoints for ticket creation, dispatch, tracking,
and SLA monitoring operations.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.ticket.models import (
    TicketStatus,
    TicketPriority,
    TicketType,
)
from src.ticket.tracker import TicketTracker
from src.ticket.dispatcher import TicketDispatcher
from src.ticket.sla_monitor import SLAMonitor
from src.ticket.intelligent_creator import IntelligentTicketCreator, TicketTemplate
from src.ticket.classification_manager import TicketClassificationManager


router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])

# Global instances - use lazy initialization
_ticket_tracker: Optional[TicketTracker] = None
_ticket_dispatcher: Optional[TicketDispatcher] = None
_sla_monitor: Optional[SLAMonitor] = None
_intelligent_creator: Optional[IntelligentTicketCreator] = None
_classification_manager: Optional[TicketClassificationManager] = None


def get_ticket_tracker() -> TicketTracker:
    """Get or create ticket tracker instance."""
    global _ticket_tracker
    if _ticket_tracker is None:
        _ticket_tracker = TicketTracker()
    return _ticket_tracker


def get_ticket_dispatcher() -> TicketDispatcher:
    """Get or create ticket dispatcher instance."""
    global _ticket_dispatcher
    if _ticket_dispatcher is None:
        _ticket_dispatcher = TicketDispatcher()
    return _ticket_dispatcher


def get_sla_monitor() -> SLAMonitor:
    """Get or create SLA monitor instance."""
    global _sla_monitor
    if _sla_monitor is None:
        _sla_monitor = SLAMonitor()
    return _sla_monitor


def get_intelligent_creator() -> IntelligentTicketCreator:
    """Get or create intelligent creator instance."""
    global _intelligent_creator
    if _intelligent_creator is None:
        _intelligent_creator = IntelligentTicketCreator()
    return _intelligent_creator


def get_classification_manager() -> TicketClassificationManager:
    """Get or create classification manager instance."""
    global _classification_manager
    if _classification_manager is None:
        _classification_manager = TicketClassificationManager()
    return _classification_manager


# ==================== Request/Response Models ====================

class CreateTicketRequest(BaseModel):
    """Request model for creating a ticket."""
    ticket_type: str = Field(..., description="Type of ticket (quality_issue, annotation_error, etc.)")
    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    description: Optional[str] = Field(None, description="Detailed description")
    priority: str = Field("medium", description="Priority level (critical, high, medium, low)")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    created_by: Optional[str] = Field(None, description="User creating the ticket")
    quality_issue_id: Optional[UUID] = Field(None, description="Related quality issue ID")
    task_id: Optional[UUID] = Field(None, description="Related task ID")
    skill_requirements: Optional[Dict[str, Any]] = Field(None, description="Required skills for dispatch")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UpdateTicketRequest(BaseModel):
    """Request model for updating a ticket."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = None
    skill_requirements: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    updated_by: str = Field(..., description="User making the update")


class AssignTicketRequest(BaseModel):
    """Request model for assigning a ticket."""
    assignee_id: str = Field(..., description="User to assign to")
    assigned_by: str = Field(..., description="User making the assignment")


class ChangeStatusRequest(BaseModel):
    """Request model for changing ticket status."""
    status: str = Field(..., description="New status")
    changed_by: str = Field(..., description="User making the change")
    notes: Optional[str] = Field(None, description="Optional notes")


class ResolveTicketRequest(BaseModel):
    """Request model for resolving a ticket."""
    resolved_by: str = Field(..., description="User resolving the ticket")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class DispatchTicketRequest(BaseModel):
    """Request model for dispatching a ticket."""
    auto_assign: bool = Field(True, description="Whether to auto-assign")
    preferred_user: Optional[str] = Field(None, description="Preferred user to assign")
    policy_name: str = Field("default", description="Dispatch policy to use")


class UpdateDispatchPolicyRequest(BaseModel):
    """Request model for updating dispatch policy."""
    skill_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Skill weight")
    capacity_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Capacity weight")
    performance_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Performance weight")
    min_skill_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Min skill threshold")
    max_workload_ratio: Optional[float] = Field(None, ge=0.0, le=1.0, description="Max workload ratio")
    enabled: Optional[bool] = Field(None, description="Whether policy is enabled")


class EscalateTicketRequest(BaseModel):
    """Request model for escalating a ticket."""
    reason: str = Field("Manual escalation", description="Reason for escalation")
    escalated_by: str = Field(..., description="User escalating the ticket")


class CreateFromQualityIssueRequest(BaseModel):
    """Request model for creating ticket from quality issue."""
    quality_issue_id: UUID = Field(..., description="Quality issue ID")
    task_id: Optional[UUID] = Field(None, description="Related task ID")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    created_by: Optional[str] = Field(None, description="User creating the ticket")
    auto_classify: bool = Field(True, description="Whether to auto-classify")
    template: Optional[str] = Field(None, description="Specific template to use")


class CreateFromTemplateRequest(BaseModel):
    """Request model for creating ticket from template."""
    template: str = Field(..., description="Template name")
    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    description: Optional[str] = Field(None, description="Custom description")
    priority: Optional[str] = Field(None, description="Custom priority")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    created_by: Optional[str] = Field(None, description="User creating the ticket")
    custom_variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")


class ApplyTagsRequest(BaseModel):
    """Request model for applying tags."""
    tags: List[str] = Field(..., description="Tags to apply")
    applied_by: str = Field(..., description="User applying tags")
    replace_existing: bool = Field(False, description="Replace existing tags")


class RemoveTagsRequest(BaseModel):
    """Request model for removing tags."""
    tags: List[str] = Field(..., description="Tags to remove")
    removed_by: str = Field(..., description="User removing tags")


class TicketResponse(BaseModel):
    """Response model for ticket data."""
    id: str
    ticket_type: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    assigned_to: Optional[str]
    sla_deadline: Optional[str]
    sla_breached: bool
    created_at: str
    updated_at: str


class TicketListResponse(BaseModel):
    """Response model for ticket list."""
    tickets: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


# ==================== Ticket CRUD Endpoints ====================

@router.post("", response_model=Dict[str, Any])
async def create_ticket(request: CreateTicketRequest) -> Dict[str, Any]:
    """
    Create a new ticket.

    Creates a ticket with automatic SLA deadline calculation.
    """
    try:
        tracker = get_ticket_tracker()

        # Convert string enums
        ticket_type = TicketType(request.ticket_type)
        priority = TicketPriority(request.priority)

        ticket = await tracker.create_ticket(
            ticket_type=ticket_type,
            title=request.title,
            description=request.description,
            priority=priority,
            tenant_id=request.tenant_id,
            created_by=request.created_by,
            quality_issue_id=request.quality_issue_id,
            task_id=request.task_id,
            skill_requirements=request.skill_requirements,
            metadata=request.metadata,
        )

        return {
            "status": "success",
            "ticket": ticket.to_dict(),
            "message": f"Ticket created: {ticket.id}"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    ticket_type: Optional[str] = Query(None, description="Filter by type"),
    sla_breached: Optional[bool] = Query(None, description="Filter by SLA breach"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> TicketListResponse:
    """
    List tickets with optional filters.

    Supports filtering by tenant, status, priority, assignee, type, and SLA breach.
    """
    try:
        tracker = get_ticket_tracker()

        # Convert string enums if provided
        status_enum = TicketStatus(status) if status else None
        priority_enum = TicketPriority(priority) if priority else None
        type_enum = TicketType(ticket_type) if ticket_type else None

        tickets, total = await tracker.list_tickets(
            tenant_id=tenant_id,
            status=status_enum,
            priority=priority_enum,
            assigned_to=assigned_to,
            ticket_type=type_enum,
            sla_breached=sla_breached,
            limit=limit,
            offset=offset,
        )

        return TicketListResponse(
            tickets=[t.to_dict() for t in tickets],
            total=total,
            limit=limit,
            offset=offset,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid filter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tickets: {str(e)}")


@router.get("/{ticket_id}", response_model=Dict[str, Any])
async def get_ticket(ticket_id: UUID) -> Dict[str, Any]:
    """
    Get a ticket by ID.

    Returns full ticket details including SLA status.
    """
    try:
        tracker = get_ticket_tracker()
        ticket = await tracker.get_ticket(ticket_id)

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return {
            "status": "success",
            "ticket": ticket.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ticket: {str(e)}")


@router.put("/{ticket_id}", response_model=Dict[str, Any])
async def update_ticket(
    ticket_id: UUID,
    request: UpdateTicketRequest
) -> Dict[str, Any]:
    """
    Update ticket fields.

    Updates the specified fields and records history.
    """
    try:
        tracker = get_ticket_tracker()

        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.description is not None:
            updates["description"] = request.description
        if request.priority is not None:
            updates["priority"] = TicketPriority(request.priority)
        if request.skill_requirements is not None:
            updates["skill_requirements"] = request.skill_requirements
        if request.metadata is not None:
            updates["metadata"] = request.metadata

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        ticket = await tracker.update_ticket(
            ticket_id,
            request.updated_by,
            **updates
        )

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return {
            "status": "success",
            "ticket": ticket.to_dict(),
            "message": "Ticket updated"
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ticket: {str(e)}")


# ==================== Assignment Endpoints ====================

@router.put("/{ticket_id}/assign", response_model=Dict[str, Any])
async def assign_ticket(
    ticket_id: UUID,
    request: AssignTicketRequest
) -> Dict[str, Any]:
    """
    Manually assign a ticket to a user.

    Updates the ticket assignment and annotator workload.
    """
    try:
        tracker = get_ticket_tracker()

        success = await tracker.assign_ticket(
            ticket_id,
            request.assignee_id,
            request.assigned_by
        )

        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found or assignment failed")

        return {
            "status": "success",
            "message": f"Ticket {ticket_id} assigned to {request.assignee_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign ticket: {str(e)}")


@router.post("/{ticket_id}/dispatch", response_model=Dict[str, Any])
async def dispatch_ticket(
    ticket_id: UUID,
    request: DispatchTicketRequest
) -> Dict[str, Any]:
    """
    Dispatch a ticket using intelligent assignment.

    Uses skill matching, workload balancing, and performance history.
    """
    try:
        dispatcher = get_ticket_dispatcher()

        assigned_to = await dispatcher.dispatch_ticket_optimized(
            ticket_id,
            policy_name=request.policy_name,
            auto_assign=request.auto_assign,
            preferred_user=request.preferred_user
        )

        if not assigned_to:
            return {
                "status": "no_match",
                "message": "No suitable annotator found for this ticket"
            }

        return {
            "status": "success",
            "assigned_to": assigned_to,
            "policy_used": request.policy_name,
            "message": f"Ticket dispatched to {assigned_to} using {request.policy_name} policy"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch ticket: {str(e)}")


@router.get("/{ticket_id}/recommendations", response_model=Dict[str, Any])
async def get_dispatch_recommendations(
    ticket_id: UUID,
    policy_name: str = Query("default", description="Dispatch policy to use"),
    include_scores: bool = Query(True, description="Include detailed scores")
) -> Dict[str, Any]:
    """
    Get dispatch recommendations for a ticket.

    Returns ranked list of suitable annotators without assigning.
    """
    try:
        dispatcher = get_ticket_dispatcher()

        recommendations = await dispatcher.get_dispatch_recommendations_advanced(
            ticket_id,
            policy_name=policy_name,
            include_scores=include_scores
        )

        return {
            "status": "success",
            "ticket_id": str(ticket_id),
            "policy_used": policy_name,
            "recommendations": recommendations
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


# ==================== Enhanced Dispatch Management Endpoints ====================

@router.get("/dispatch/policies", response_model=Dict[str, Any])
async def get_dispatch_policies() -> Dict[str, Any]:
    """
    Get available dispatch policies.
    
    Returns all configured dispatch policies with their settings.
    """
    try:
        dispatcher = get_ticket_dispatcher()
        policies = await dispatcher.get_dispatch_policies()
        
        return {
            "status": "success",
            "policies": policies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get policies: {str(e)}")


@router.put("/dispatch/policies/{policy_name}", response_model=Dict[str, Any])
async def update_dispatch_policy(
    policy_name: str,
    request: UpdateDispatchPolicyRequest
) -> Dict[str, Any]:
    """
    Update a dispatch policy configuration.
    
    Modifies the specified policy with new settings.
    """
    try:
        dispatcher = get_ticket_dispatcher()
        
        # Filter out None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await dispatcher.update_dispatch_policy(policy_name, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        return {
            "status": "success",
            "message": f"Policy {policy_name} updated successfully",
            "updates": updates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {str(e)}")


@router.get("/dispatch/rules", response_model=Dict[str, Any])
async def get_dispatch_rules() -> Dict[str, Any]:
    """
    Get dispatch rules configuration.
    
    Returns all configured dispatch rules and their settings.
    """
    try:
        dispatcher = get_ticket_dispatcher()
        rules = await dispatcher.get_dispatch_rules()
        
        return {
            "status": "success",
            "rules": rules
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")


@router.get("/dispatch/effectiveness", response_model=Dict[str, Any])
async def evaluate_dispatch_effectiveness(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    days: int = Query(30, ge=1, le=365, description="Analysis period in days")
) -> Dict[str, Any]:
    """
    Evaluate dispatch effectiveness and get optimization suggestions.
    
    Analyzes dispatch performance and provides actionable insights.
    """
    try:
        dispatcher = get_ticket_dispatcher()
        
        evaluation = await dispatcher.evaluate_dispatch_effectiveness(tenant_id, days)
        
        return {
            "status": "success",
            "evaluation": evaluation
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate effectiveness: {str(e)}")


# ==================== Status Management Endpoints ====================

@router.put("/{ticket_id}/status", response_model=Dict[str, Any])
async def change_ticket_status(
    ticket_id: UUID,
    request: ChangeStatusRequest
) -> Dict[str, Any]:
    """
    Change ticket status.

    Validates status transition and records history.
    """
    try:
        tracker = get_ticket_tracker()

        new_status = TicketStatus(request.status)

        success = await tracker.change_status(
            ticket_id,
            new_status,
            request.changed_by,
            request.notes
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Invalid status transition or ticket not found"
            )

        return {
            "status": "success",
            "message": f"Ticket status changed to {request.status}"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change status: {str(e)}")


@router.post("/{ticket_id}/resolve", response_model=Dict[str, Any])
async def resolve_ticket(
    ticket_id: UUID,
    request: ResolveTicketRequest
) -> Dict[str, Any]:
    """
    Resolve a ticket.

    Marks the ticket as resolved with optional resolution notes.
    """
    try:
        tracker = get_ticket_tracker()

        success = await tracker.resolve_ticket(
            ticket_id,
            request.resolved_by,
            request.resolution_notes
        )

        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found or cannot be resolved")

        return {
            "status": "success",
            "message": f"Ticket {ticket_id} resolved"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve ticket: {str(e)}")


@router.post("/{ticket_id}/escalate", response_model=Dict[str, Any])
async def escalate_ticket(
    ticket_id: UUID,
    request: EscalateTicketRequest
) -> Dict[str, Any]:
    """
    Escalate a ticket.

    Increases escalation level and marks ticket as escalated.
    """
    try:
        monitor = get_sla_monitor()

        success = await monitor.escalate_ticket(
            ticket_id,
            request.reason,
            request.escalated_by
        )

        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found or escalation failed")

        return {
            "status": "success",
            "message": f"Ticket {ticket_id} escalated"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to escalate ticket: {str(e)}")


# ==================== History Endpoints ====================

@router.get("/{ticket_id}/history", response_model=Dict[str, Any])
async def get_ticket_history(ticket_id: UUID) -> Dict[str, Any]:
    """
    Get ticket history.

    Returns all status changes and actions on the ticket.
    """
    try:
        tracker = get_ticket_tracker()

        history = await tracker.get_ticket_history(ticket_id)

        return {
            "status": "success",
            "ticket_id": str(ticket_id),
            "history": [h.to_dict() for h in history]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


# ==================== SLA Monitoring Endpoints ====================

@router.get("/sla/violations", response_model=Dict[str, Any])
async def get_sla_violations(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant")
) -> Dict[str, Any]:
    """
    Get tickets with SLA violations.

    Checks all active tickets for SLA breaches.
    """
    try:
        monitor = get_sla_monitor()

        violations = await monitor.check_sla_violations(tenant_id)

        return {
            "status": "success",
            "violations_count": len(violations),
            "violations": [
                {
                    "ticket_id": str(v.id),
                    "title": v.title,
                    "priority": v.priority.value,
                    "sla_deadline": v.sla_deadline.isoformat() if v.sla_deadline else None,
                    "assigned_to": v.assigned_to,
                }
                for v in violations
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check SLA violations: {str(e)}")


@router.get("/sla/warnings", response_model=Dict[str, Any])
async def get_sla_warnings(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant")
) -> Dict[str, Any]:
    """
    Get tickets approaching SLA deadline.

    Returns tickets within warning threshold of their SLA.
    """
    try:
        monitor = get_sla_monitor()

        warnings = await monitor.check_sla_warnings(tenant_id)

        return {
            "status": "success",
            "warnings_count": len(warnings),
            "warnings": [
                {
                    "ticket_id": str(w.id),
                    "title": w.title,
                    "priority": w.priority.value,
                    "sla_deadline": w.sla_deadline.isoformat() if w.sla_deadline else None,
                    "assigned_to": w.assigned_to,
                }
                for w in warnings
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check SLA warnings: {str(e)}")


@router.get("/sla/compliance", response_model=Dict[str, Any])
async def get_sla_compliance_report(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    days: int = Query(30, ge=1, le=365, description="Analysis period in days")
) -> Dict[str, Any]:
    """
    Get SLA compliance report.

    Returns SLA compliance statistics for the specified period.
    """
    try:
        monitor = get_sla_monitor()

        report = await monitor.get_sla_compliance_report(tenant_id, days)

        return {
            "status": "success",
            "report": report
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


# ==================== Workload Endpoints ====================

@router.get("/workload", response_model=Dict[str, Any])
async def get_workload_distribution(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant")
) -> Dict[str, Any]:
    """
    Get workload distribution across annotators.

    Shows current workload and capacity for each annotator.
    """
    try:
        dispatcher = get_ticket_dispatcher()

        distribution = await dispatcher.get_workload_distribution(tenant_id)

        return {
            "status": "success",
            "workload": distribution
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workload: {str(e)}")


@router.post("/workload/rebalance", response_model=Dict[str, Any])
async def rebalance_workload(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant")
) -> Dict[str, Any]:
    """
    Rebalance workload across annotators.

    Reassigns tickets from overloaded annotators to underutilized ones.
    """
    try:
        dispatcher = get_ticket_dispatcher()

        actions = await dispatcher.rebalance_workload(tenant_id)

        return {
            "status": "success",
            "actions_taken": len(actions),
            "actions": actions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebalance: {str(e)}")


# ==================== Statistics Endpoints ====================

@router.get("/statistics", response_model=Dict[str, Any])
async def get_ticket_statistics(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    days: int = Query(30, ge=1, le=365, description="Analysis period in days")
) -> Dict[str, Any]:
    """
    Get ticket statistics.

    Returns aggregate statistics for tickets in the specified period.
    """
    try:
        tracker = get_ticket_tracker()

        stats = await tracker.get_statistics(tenant_id, days)

        return {
            "status": "success",
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# ==================== Alerts Endpoints ====================

@router.get("/alerts", response_model=Dict[str, Any])
async def get_active_alerts(
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgement status")
) -> Dict[str, Any]:
    """
    Get active SLA alerts.

    Returns alerts for SLA violations, warnings, and escalations.
    """
    try:
        monitor = get_sla_monitor()

        alerts = await monitor.get_active_alerts(acknowledged)

        return {
            "status": "success",
            "alerts_count": len(alerts),
            "alerts": alerts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.post("/monitoring/cycle", response_model=Dict[str, Any])
async def run_monitoring_cycle(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant")
) -> Dict[str, Any]:
    """
    Run a complete SLA monitoring cycle.

    Checks violations, warnings, unassigned tickets, and auto-escalates.
    """
    try:
        monitor = get_sla_monitor()

        summary = await monitor.run_monitoring_cycle(tenant_id)

        return {
            "status": "success",
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run monitoring: {str(e)}")


# ==================== Intelligent Creation Endpoints ====================

@router.post("/create-from-quality-issue", response_model=Dict[str, Any])
async def create_ticket_from_quality_issue(
    request: CreateFromQualityIssueRequest
) -> Dict[str, Any]:
    """
    Create a ticket automatically from a quality issue.
    
    Uses intelligent classification and template selection.
    """
    try:
        creator = get_intelligent_creator()
        
        # Mock quality issue for demonstration (in real implementation, fetch from database)
        from src.models.quality_issue import QualityIssue, IssueSeverity
        quality_issue = QualityIssue(
            id=request.quality_issue_id,
            task_id=request.task_id or request.quality_issue_id,
            issue_type="annotation_error",
            description="Sample quality issue for ticket creation",
            severity=IssueSeverity.MEDIUM
        )
        
        template = TicketTemplate(request.template) if request.template else None
        
        ticket_id = await creator.create_ticket_from_quality_issue(
            quality_issue=quality_issue,
            tenant_id=request.tenant_id,
            created_by=request.created_by,
            auto_classify=request.auto_classify,
            template=template
        )
        
        if not ticket_id:
            raise HTTPException(status_code=500, detail="Failed to create ticket")
        
        return {
            "status": "success",
            "ticket_id": str(ticket_id),
            "message": "Ticket created from quality issue"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")


@router.post("/create-from-template", response_model=Dict[str, Any])
async def create_ticket_from_template(
    request: CreateFromTemplateRequest
) -> Dict[str, Any]:
    """
    Create a ticket using a specific template.
    
    Applies template configuration and variables.
    """
    try:
        creator = get_intelligent_creator()
        
        template = TicketTemplate(request.template)
        priority = TicketPriority(request.priority) if request.priority else None
        
        ticket_id = await creator.create_ticket_from_template(
            template=template,
            title=request.title,
            description=request.description,
            priority=priority,
            tenant_id=request.tenant_id,
            created_by=request.created_by,
            custom_variables=request.custom_variables
        )
        
        if not ticket_id:
            raise HTTPException(status_code=500, detail="Failed to create ticket")
        
        return {
            "status": "success",
            "ticket_id": str(ticket_id),
            "message": f"Ticket created using {request.template} template"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid template or priority: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")


@router.get("/templates", response_model=Dict[str, Any])
async def get_available_templates() -> Dict[str, Any]:
    """
    Get available ticket templates.
    
    Returns template configurations and usage information.
    """
    try:
        creator = get_intelligent_creator()
        templates = await creator.get_available_templates()
        
        return {
            "status": "success",
            "templates": templates
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")


# ==================== Classification and Tagging Endpoints ====================

@router.post("/{ticket_id}/classify", response_model=Dict[str, Any])
async def classify_ticket(
    ticket_id: UUID,
    auto_apply: bool = Query(True, description="Auto-apply suggested tags")
) -> Dict[str, Any]:
    """
    Classify a ticket and suggest tags.
    
    Uses intelligent classification rules to suggest appropriate tags.
    """
    try:
        # Get ticket details
        tracker = get_ticket_tracker()
        ticket = await tracker.get_ticket(ticket_id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Classify ticket
        classifier = get_classification_manager()
        suggested_tags = await classifier.classify_ticket(
            ticket_id=ticket_id,
            title=ticket.title,
            description=ticket.description,
            ticket_type=ticket.ticket_type,
            priority=ticket.priority,
            auto_apply=auto_apply
        )
        
        return {
            "status": "success",
            "ticket_id": str(ticket_id),
            "suggested_tags": suggested_tags,
            "auto_applied": auto_apply
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to classify ticket: {str(e)}")


@router.post("/{ticket_id}/tags", response_model=Dict[str, Any])
async def apply_tags(
    ticket_id: UUID,
    request: ApplyTagsRequest
) -> Dict[str, Any]:
    """
    Apply tags to a ticket.
    
    Adds or replaces tags on the specified ticket.
    """
    try:
        classifier = get_classification_manager()
        
        success = await classifier.apply_tags(
            ticket_id=ticket_id,
            tags=request.tags,
            applied_by=request.applied_by,
            replace_existing=request.replace_existing
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found or tagging failed")
        
        return {
            "status": "success",
            "message": f"Applied {len(request.tags)} tags to ticket"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply tags: {str(e)}")


@router.delete("/{ticket_id}/tags", response_model=Dict[str, Any])
async def remove_tags(
    ticket_id: UUID,
    request: RemoveTagsRequest
) -> Dict[str, Any]:
    """
    Remove tags from a ticket.
    
    Removes specified tags from the ticket.
    """
    try:
        classifier = get_classification_manager()
        
        success = await classifier.remove_tags(
            ticket_id=ticket_id,
            tags=request.tags,
            removed_by=request.removed_by
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found or tag removal failed")
        
        return {
            "status": "success",
            "message": f"Removed {len(request.tags)} tags from ticket"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove tags: {str(e)}")


@router.get("/{ticket_id}/tags", response_model=Dict[str, Any])
async def get_ticket_tags(ticket_id: UUID) -> Dict[str, Any]:
    """
    Get tags for a ticket.
    
    Returns all tags currently applied to the ticket.
    """
    try:
        classifier = get_classification_manager()
        tags = await classifier.get_ticket_tags(ticket_id)
        
        return {
            "status": "success",
            "ticket_id": str(ticket_id),
            "tags": tags
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tags: {str(e)}")


@router.get("/search/by-tags", response_model=Dict[str, Any])
async def search_tickets_by_tags(
    tags: List[str] = Query(..., description="Tags to search for"),
    match_all: bool = Query(False, description="Match all tags (AND) vs any tag (OR)"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
) -> Dict[str, Any]:
    """
    Search tickets by tags.
    
    Finds tickets that match the specified tag criteria.
    """
    try:
        classifier = get_classification_manager()
        
        ticket_ids, total = await classifier.search_tickets_by_tags(
            tags=tags,
            match_all=match_all,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "ticket_ids": [str(tid) for tid in ticket_ids],
            "total": total,
            "search_criteria": {
                "tags": tags,
                "match_all": match_all,
                "tenant_id": tenant_id
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search by tags: {str(e)}")


@router.get("/tags/statistics", response_model=Dict[str, Any])
async def get_tag_statistics(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant")
) -> Dict[str, Any]:
    """
    Get tag usage statistics.
    
    Returns statistics about tag usage across tickets.
    """
    try:
        classifier = get_classification_manager()
        stats = await classifier.get_tag_statistics(tenant_id)
        
        return {
            "status": "success",
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/tags/hierarchy", response_model=Dict[str, Any])
async def get_tag_hierarchy() -> Dict[str, Any]:
    """
    Get tag hierarchy and metadata.
    
    Returns the complete tag hierarchy with categories and descriptions.
    """
    try:
        classifier = get_classification_manager()
        hierarchy = await classifier.get_tag_hierarchy()
        
        return {
            "status": "success",
            "hierarchy": hierarchy
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hierarchy: {str(e)}")


# ==================== Health Check ====================

@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check for ticket management service.
    """
    return {
        "status": "healthy",
        "service": "ticket-management",
        "timestamp": datetime.now().isoformat()
    }
