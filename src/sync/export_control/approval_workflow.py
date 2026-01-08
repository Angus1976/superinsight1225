"""
Approval Workflow Service for data export requests.

Provides comprehensive approval workflow management with multi-level approvals,
escalation, notifications, and automated decision making.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from dataclasses import dataclass
from enum import Enum

from src.database.connection import get_db_session
from .models import (
    ExportRequestModel, ExportApprovalModel, ExportRequestStatus,
    ApprovalStatus
)

logger = logging.getLogger(__name__)


class ApprovalDecision(str, Enum):
    """Approval decision enumeration."""
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    REQUEST_INFO = "request_info"


@dataclass
class ApprovalRequest:
    """Approval request data."""
    export_request_id: UUID
    approver_id: UUID
    decision: ApprovalDecision
    reason: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    escalate_to: Optional[UUID] = None


@dataclass
class ApprovalWorkflowConfig:
    """Approval workflow configuration."""
    tenant_id: str
    approval_levels: List[Dict[str, Any]]
    escalation_rules: Dict[str, Any]
    notification_settings: Dict[str, Any]
    auto_approval_rules: Optional[Dict[str, Any]] = None


class ApprovalWorkflowService:
    """
    Approval workflow service for data export requests.
    
    Manages multi-level approval processes with escalation, notifications,
    and automated decision making.
    """
    
    def __init__(self):
        self.default_approval_timeout = timedelta(hours=24)
        self.escalation_timeout = timedelta(hours=48)
    
    def initiate_approval_workflow(
        self,
        export_request: ExportRequestModel,
        workflow_config: Optional[ApprovalWorkflowConfig] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Initiate approval workflow for export request.
        
        Args:
            export_request: Export request to approve
            workflow_config: Workflow configuration
            db: Database session
            
        Returns:
            True if workflow initiated successfully
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Check if approval is required
            if not export_request.requires_approval:
                # Auto-approve
                export_request.status = ExportRequestStatus.APPROVED
                db.commit()
                logger.info(f"Export request {export_request.id} auto-approved")
                return True
            
            # Get workflow configuration
            if not workflow_config:
                workflow_config = self._get_default_workflow_config(export_request.tenant_id)
            
            # Create approval records for each level
            approval_levels = workflow_config.approval_levels[:export_request.approval_level]
            
            for level_config in approval_levels:
                approval = ExportApprovalModel(
                    export_request_id=export_request.id,
                    tenant_id=export_request.tenant_id,
                    approval_level=level_config["level"],
                    approver_role=level_config["role"],
                    due_at=datetime.utcnow() + timedelta(hours=level_config.get("timeout_hours", 24))
                )
                
                # Assign specific approver if configured
                if "approver_id" in level_config:
                    approval.approver_id = level_config["approver_id"]
                
                db.add(approval)
            
            # Update export request status
            export_request.status = ExportRequestStatus.PENDING
            
            db.commit()
            
            # Send notifications for first level
            self._send_approval_notifications(export_request, 1, workflow_config)
            
            logger.info(f"Approval workflow initiated for export request {export_request.id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error initiating approval workflow: {e}")
            return False
    
    def process_approval_decision(
        self,
        approval_request: ApprovalRequest,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Process approval decision.
        
        Args:
            approval_request: Approval decision request
            db: Database session
            
        Returns:
            Processing result dictionary
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Get export request
            export_request = db.query(ExportRequestModel).filter(
                ExportRequestModel.id == approval_request.export_request_id
            ).first()
            
            if not export_request:
                return {
                    "success": False,
                    "error": "Export request not found"
                }
            
            # Get pending approval for this approver
            approval = self._get_pending_approval(
                approval_request.export_request_id,
                approval_request.approver_id,
                db
            )
            
            if not approval:
                return {
                    "success": False,
                    "error": "No pending approval found for this approver"
                }
            
            # Process decision
            if approval_request.decision == ApprovalDecision.APPROVE:
                result = self._process_approval(approval, approval_request, export_request, db)
            elif approval_request.decision == ApprovalDecision.REJECT:
                result = self._process_rejection(approval, approval_request, export_request, db)
            elif approval_request.decision == ApprovalDecision.ESCALATE:
                result = self._process_escalation(approval, approval_request, export_request, db)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported decision: {approval_request.decision}"
                }
            
            db.commit()
            return result
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing approval decision: {e}")
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}"
            }
    
    def get_pending_approvals(
        self,
        approver_id: UUID,
        tenant_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending approvals for approver.
        
        Args:
            approver_id: Approver user ID
            tenant_id: Tenant ID (optional filter)
            db: Database session
            
        Returns:
            List of pending approval dictionaries
        """
        if db is None:
            db = next(get_db_session())
        
        query = db.query(ExportApprovalModel).join(ExportRequestModel).filter(
            and_(
                ExportApprovalModel.approver_id == approver_id,
                ExportApprovalModel.status == ApprovalStatus.PENDING
            )
        )
        
        if tenant_id:
            query = query.filter(ExportApprovalModel.tenant_id == tenant_id)
        
        approvals = query.all()
        
        result = []
        for approval in approvals:
            export_request = approval.export_request
            result.append({
                "approval_id": str(approval.id),
                "export_request_id": str(export_request.id),
                "request_title": export_request.request_title,
                "requester_id": str(export_request.requester_id),
                "approval_level": approval.approval_level,
                "assigned_at": approval.assigned_at.isoformat(),
                "due_at": approval.due_at.isoformat() if approval.due_at else None,
                "business_justification": export_request.business_justification,
                "table_names": export_request.table_names,
                "estimated_records": export_request.estimated_records,
                "export_format": export_request.export_format.value,
                "priority": export_request.priority
            })
        
        return result
    
    def get_approval_history(
        self,
        export_request_id: UUID,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Get approval history for export request.
        
        Args:
            export_request_id: Export request ID
            db: Database session
            
        Returns:
            List of approval history entries
        """
        if db is None:
            db = next(get_db_session())
        
        approvals = db.query(ExportApprovalModel).filter(
            ExportApprovalModel.export_request_id == export_request_id
        ).order_by(ExportApprovalModel.approval_level).all()
        
        history = []
        for approval in approvals:
            history.append({
                "approval_level": approval.approval_level,
                "approver_id": str(approval.approver_id) if approval.approver_id else None,
                "approver_role": approval.approver_role,
                "status": approval.status.value,
                "decision_reason": approval.decision_reason,
                "assigned_at": approval.assigned_at.isoformat(),
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                "due_at": approval.due_at.isoformat() if approval.due_at else None,
                "conditions": approval.conditions,
                "escalated_to": str(approval.escalated_to) if approval.escalated_to else None,
                "escalation_reason": approval.escalation_reason
            })
        
        return history
    
    def check_overdue_approvals(
        self,
        tenant_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for overdue approvals and handle escalation.
        
        Args:
            tenant_id: Tenant ID (optional filter)
            db: Database session
            
        Returns:
            List of overdue approval actions taken
        """
        if db is None:
            db = next(get_db_session())
        
        # Find overdue approvals
        query = db.query(ExportApprovalModel).filter(
            and_(
                ExportApprovalModel.status == ApprovalStatus.PENDING,
                ExportApprovalModel.due_at < datetime.utcnow()
            )
        )
        
        if tenant_id:
            query = query.filter(ExportApprovalModel.tenant_id == tenant_id)
        
        overdue_approvals = query.all()
        
        actions_taken = []
        
        for approval in overdue_approvals:
            try:
                # Auto-escalate overdue approvals
                escalation_result = self._auto_escalate_approval(approval, db)
                actions_taken.append({
                    "approval_id": str(approval.id),
                    "export_request_id": str(approval.export_request_id),
                    "action": "escalated",
                    "details": escalation_result
                })
                
            except Exception as e:
                logger.error(f"Error handling overdue approval {approval.id}: {e}")
                actions_taken.append({
                    "approval_id": str(approval.id),
                    "export_request_id": str(approval.export_request_id),
                    "action": "error",
                    "details": str(e)
                })
        
        if actions_taken:
            db.commit()
        
        return actions_taken
    
    def _process_approval(
        self,
        approval: ExportApprovalModel,
        approval_request: ApprovalRequest,
        export_request: ExportRequestModel,
        db: Session
    ) -> Dict[str, Any]:
        """Process approval decision."""
        
        # Update approval record
        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = approval_request.approver_id
        approval.decision_reason = approval_request.reason
        approval.conditions = approval_request.conditions or {}
        approval.decided_at = datetime.utcnow()
        
        # Check if this was the final approval level
        max_level = db.query(func.max(ExportApprovalModel.approval_level)).filter(
            ExportApprovalModel.export_request_id == export_request.id
        ).scalar()
        
        if approval.approval_level >= max_level:
            # All approvals complete
            export_request.status = ExportRequestStatus.APPROVED
            
            # Send approval notification
            self._send_approval_complete_notification(export_request)
            
            return {
                "success": True,
                "message": "Export request fully approved",
                "next_action": "processing"
            }
        else:
            # Move to next approval level
            next_level = approval.approval_level + 1
            next_approval = db.query(ExportApprovalModel).filter(
                and_(
                    ExportApprovalModel.export_request_id == export_request.id,
                    ExportApprovalModel.approval_level == next_level
                )
            ).first()
            
            if next_approval:
                # Send notification for next level
                workflow_config = self._get_default_workflow_config(export_request.tenant_id)
                self._send_approval_notifications(export_request, next_level, workflow_config)
            
            return {
                "success": True,
                "message": f"Approval level {approval.approval_level} approved, proceeding to level {next_level}",
                "next_action": f"approval_level_{next_level}"
            }
    
    def _process_rejection(
        self,
        approval: ExportApprovalModel,
        approval_request: ApprovalRequest,
        export_request: ExportRequestModel,
        db: Session
    ) -> Dict[str, Any]:
        """Process rejection decision."""
        
        # Update approval record
        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = approval_request.approver_id
        approval.decision_reason = approval_request.reason
        approval.decided_at = datetime.utcnow()
        
        # Reject the entire export request
        export_request.status = ExportRequestStatus.REJECTED
        
        # Send rejection notification
        self._send_rejection_notification(export_request, approval_request.reason)
        
        return {
            "success": True,
            "message": "Export request rejected",
            "next_action": "none"
        }
    
    def _process_escalation(
        self,
        approval: ExportApprovalModel,
        approval_request: ApprovalRequest,
        export_request: ExportRequestModel,
        db: Session
    ) -> Dict[str, Any]:
        """Process escalation decision."""
        
        # Update approval record
        approval.status = ApprovalStatus.ESCALATED
        approval.approver_id = approval_request.approver_id
        approval.decision_reason = approval_request.reason
        approval.escalated_to = approval_request.escalate_to
        approval.escalated_at = datetime.utcnow()
        approval.escalation_reason = approval_request.reason
        
        # Create new approval for escalated approver
        escalated_approval = ExportApprovalModel(
            export_request_id=export_request.id,
            tenant_id=export_request.tenant_id,
            approval_level=approval.approval_level,  # Same level, different approver
            approver_id=approval_request.escalate_to,
            approver_role=approval.approver_role + "_escalated",
            due_at=datetime.utcnow() + self.escalation_timeout
        )
        
        db.add(escalated_approval)
        
        # Send escalation notification
        self._send_escalation_notification(export_request, approval_request)
        
        return {
            "success": True,
            "message": f"Approval escalated to {approval_request.escalate_to}",
            "next_action": "escalated_approval"
        }
    
    def _get_pending_approval(
        self,
        export_request_id: UUID,
        approver_id: UUID,
        db: Session
    ) -> Optional[ExportApprovalModel]:
        """Get pending approval for approver."""
        
        return db.query(ExportApprovalModel).filter(
            and_(
                ExportApprovalModel.export_request_id == export_request_id,
                or_(
                    ExportApprovalModel.approver_id == approver_id,
                    ExportApprovalModel.approver_id.is_(None)  # Unassigned approval
                ),
                ExportApprovalModel.status == ApprovalStatus.PENDING
            )
        ).first()
    
    def _auto_escalate_approval(
        self,
        approval: ExportApprovalModel,
        db: Session
    ) -> Dict[str, Any]:
        """Auto-escalate overdue approval."""
        
        # Mark as escalated
        approval.status = ApprovalStatus.ESCALATED
        approval.escalated_at = datetime.utcnow()
        approval.escalation_reason = "Automatic escalation due to timeout"
        
        # Create escalated approval (simplified - would need proper escalation logic)
        escalated_approval = ExportApprovalModel(
            export_request_id=approval.export_request_id,
            tenant_id=approval.tenant_id,
            approval_level=approval.approval_level + 1,  # Escalate to next level
            approver_role=approval.approver_role + "_manager",
            due_at=datetime.utcnow() + self.escalation_timeout
        )
        
        db.add(escalated_approval)
        
        return {
            "escalated_to_level": approval.approval_level + 1,
            "reason": "timeout"
        }
    
    def _get_default_workflow_config(self, tenant_id: str) -> ApprovalWorkflowConfig:
        """Get default workflow configuration for tenant."""
        
        return ApprovalWorkflowConfig(
            tenant_id=tenant_id,
            approval_levels=[
                {
                    "level": 1,
                    "role": "manager",
                    "timeout_hours": 24
                },
                {
                    "level": 2,
                    "role": "senior_manager",
                    "timeout_hours": 48
                },
                {
                    "level": 3,
                    "role": "executive",
                    "timeout_hours": 72
                }
            ],
            escalation_rules={
                "timeout_escalation": True,
                "escalation_timeout_hours": 48
            },
            notification_settings={
                "email_notifications": True,
                "slack_notifications": False,
                "reminder_hours": [12, 2]  # Send reminders 12h and 2h before due
            }
        )
    
    def _send_approval_notifications(
        self,
        export_request: ExportRequestModel,
        approval_level: int,
        workflow_config: ApprovalWorkflowConfig
    ) -> None:
        """Send approval notifications."""
        
        # This would integrate with notification service
        logger.info(
            f"Sending approval notification for export request {export_request.id}, "
            f"level {approval_level}"
        )
        
        # In production, this would send actual notifications via email, Slack, etc.
    
    def _send_approval_complete_notification(self, export_request: ExportRequestModel) -> None:
        """Send notification when approval is complete."""
        
        logger.info(f"Export request {export_request.id} fully approved")
        
        # In production, notify requester that export is approved and processing
    
    def _send_rejection_notification(
        self,
        export_request: ExportRequestModel,
        reason: Optional[str]
    ) -> None:
        """Send rejection notification."""
        
        logger.info(f"Export request {export_request.id} rejected: {reason}")
        
        # In production, notify requester of rejection with reason
    
    def _send_escalation_notification(
        self,
        export_request: ExportRequestModel,
        approval_request: ApprovalRequest
    ) -> None:
        """Send escalation notification."""
        
        logger.info(
            f"Export request {export_request.id} escalated to {approval_request.escalate_to}"
        )
        
        # In production, notify escalated approver