"""
Approval Workflow Engine for SuperInsight Platform.

Implements data access approval workflows:
- Multi-level approval configuration
- Sensitivity-based routing
- Timeout handling
- Delegation support
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.data_permission import (
    ApprovalWorkflowModel, ApprovalRequestModel, ApprovalActionModel,
    ApprovalDelegationModel, ApprovalStatus, SensitivityLevel,
    DataClassificationModel
)
from src.schemas.data_permission import (
    CreateApprovalRequest, ApprovalDecision, ApprovalResult,
    ApprovalRequestResponse, ApprovalActionResponse, DelegationResponse,
    ApprovalWorkflowConfig
)

logger = logging.getLogger(__name__)


class ApprovalWorkflowEngine:
    """
    Approval Workflow Engine.
    
    Manages data access approval workflows:
    - Multi-level approval processes
    - Automatic routing based on sensitivity
    - Timeout handling
    - Delegation support
    """
    
    def __init__(self, notification_service=None):
        self.logger = logging.getLogger(__name__)
        self._notification_service = notification_service
    
    # ========================================================================
    # Workflow Configuration
    # ========================================================================
    
    async def create_workflow(
        self,
        config: ApprovalWorkflowConfig,
        tenant_id: str,
        created_by: UUID,
        db: Session
    ) -> ApprovalWorkflowModel:
        """
        Create an approval workflow configuration.
        
        Args:
            config: Workflow configuration
            tenant_id: Tenant context
            created_by: User creating the workflow
            db: Database session
            
        Returns:
            Created ApprovalWorkflowModel
        """
        workflow = ApprovalWorkflowModel(
            tenant_id=tenant_id,
            name=config.name,
            description=config.description,
            sensitivity_levels=[level.value for level in config.sensitivity_levels],
            approval_levels=config.approval_levels,
            timeout_hours=config.timeout_hours,
            auto_approve_conditions=config.auto_approve_conditions,
            created_by=created_by
        )
        
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        self.logger.info(f"Created approval workflow: {config.name}")
        return workflow
    
    async def get_workflow(
        self,
        workflow_id: UUID,
        tenant_id: str,
        db: Session
    ) -> Optional[ApprovalWorkflowModel]:
        """Get workflow by ID."""
        return db.query(ApprovalWorkflowModel).filter(
            and_(
                ApprovalWorkflowModel.id == workflow_id,
                ApprovalWorkflowModel.tenant_id == tenant_id,
                ApprovalWorkflowModel.is_active == True
            )
        ).first()
    
    async def get_workflow_for_sensitivity(
        self,
        sensitivity_level: SensitivityLevel,
        tenant_id: str,
        db: Session
    ) -> Optional[ApprovalWorkflowModel]:
        """Get workflow that handles a specific sensitivity level."""
        workflows = db.query(ApprovalWorkflowModel).filter(
            and_(
                ApprovalWorkflowModel.tenant_id == tenant_id,
                ApprovalWorkflowModel.is_active == True
            )
        ).all()
        
        for workflow in workflows:
            if sensitivity_level.value in workflow.sensitivity_levels:
                return workflow
        
        return None
    
    # ========================================================================
    # Approval Request Management
    # ========================================================================
    
    async def create_approval_request(
        self,
        requester_id: UUID,
        resource: str,
        resource_type: str,
        action: str,
        reason: str,
        tenant_id: str,
        db: Session,
        sensitivity_level: Optional[SensitivityLevel] = None
    ) -> ApprovalRequestModel:
        """
        Create an approval request.
        
        Args:
            requester_id: User requesting access
            resource: Resource identifier
            resource_type: Type of resource
            action: Requested action
            reason: Reason for request
            tenant_id: Tenant context
            db: Database session
            sensitivity_level: Optional sensitivity level override
            
        Returns:
            Created ApprovalRequestModel
        """
        # Determine sensitivity level if not provided
        if not sensitivity_level:
            sensitivity_level = await self._get_resource_sensitivity(
                resource=resource,
                resource_type=resource_type,
                tenant_id=tenant_id,
                db=db
            )
        
        # Find appropriate workflow
        workflow = await self.get_workflow_for_sensitivity(
            sensitivity_level=sensitivity_level,
            tenant_id=tenant_id,
            db=db
        )
        
        if not workflow:
            # Create default workflow if none exists
            workflow = await self._create_default_workflow(tenant_id, db)
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=workflow.timeout_hours)
        
        # Check auto-approve conditions
        if await self._check_auto_approve(
            requester_id=requester_id,
            resource=resource,
            action=action,
            workflow=workflow,
            tenant_id=tenant_id,
            db=db
        ):
            # Auto-approve
            request = ApprovalRequestModel(
                tenant_id=tenant_id,
                requester_id=requester_id,
                resource=resource,
                resource_type=resource_type,
                action=action,
                reason=reason,
                sensitivity_level=sensitivity_level,
                workflow_id=workflow.id,
                status=ApprovalStatus.APPROVED,
                expires_at=expires_at,
                resolved_at=datetime.utcnow()
            )
            db.add(request)
            db.commit()
            db.refresh(request)
            
            self.logger.info(f"Auto-approved request for {resource}")
            return request
        
        # Create pending request
        request = ApprovalRequestModel(
            tenant_id=tenant_id,
            requester_id=requester_id,
            resource=resource,
            resource_type=resource_type,
            action=action,
            reason=reason,
            sensitivity_level=sensitivity_level,
            workflow_id=workflow.id,
            status=ApprovalStatus.PENDING,
            current_level=0,
            expires_at=expires_at
        )
        
        db.add(request)
        db.commit()
        db.refresh(request)
        
        # Route to approvers
        approvers = await self.route_approval(request, db)
        
        # Send notifications
        await self._notify_approvers(request, approvers)
        
        self.logger.info(f"Created approval request {request.id} for {resource}")
        return request
    
    async def route_approval(
        self,
        request: ApprovalRequestModel,
        db: Session
    ) -> List[UUID]:
        """
        Route approval request to appropriate approvers.
        
        Args:
            request: Approval request
            db: Database session
            
        Returns:
            List of approver user IDs
        """
        workflow = await self.get_workflow(
            workflow_id=request.workflow_id,
            tenant_id=request.tenant_id,
            db=db
        )
        
        if not workflow or not workflow.approval_levels:
            return []
        
        # Get current level configuration
        current_level = request.current_level
        if current_level >= len(workflow.approval_levels):
            return []
        
        level_config = workflow.approval_levels[current_level]
        approvers = []
        
        # Get approvers based on level configuration
        if "approvers" in level_config:
            approvers = [UUID(a) for a in level_config["approvers"]]
        elif "role" in level_config:
            # Get users with specified role
            # In production, query user-role assignments
            pass
        
        # Check for delegations
        approvers = await self._apply_delegations(approvers, request.tenant_id, db)
        
        return approvers
    
    # ========================================================================
    # Approval Decision
    # ========================================================================
    
    async def approve(
        self,
        request_id: UUID,
        approver_id: UUID,
        decision: str,
        tenant_id: str,
        db: Session,
        comments: Optional[str] = None
    ) -> ApprovalResult:
        """
        Process an approval decision.
        
        Args:
            request_id: Request ID
            approver_id: Approver user ID
            decision: Decision (approved/rejected)
            tenant_id: Tenant context
            db: Database session
            comments: Optional comments
            
        Returns:
            ApprovalResult with decision details
        """
        request = db.query(ApprovalRequestModel).filter(
            and_(
                ApprovalRequestModel.id == request_id,
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatus.PENDING
            )
        ).first()
        
        if not request:
            return ApprovalResult(
                request_id=request_id,
                status=ApprovalStatus.PENDING,
                decision=None
            )
        
        # Check if request has expired
        if request.expires_at < datetime.utcnow():
            request.status = ApprovalStatus.EXPIRED
            db.commit()
            return ApprovalResult(
                request_id=request_id,
                status=ApprovalStatus.EXPIRED,
                decision=None
            )
        
        # Check for delegation
        actual_approver = approver_id
        delegated_from = None
        delegation = await self._get_active_delegation(approver_id, tenant_id, db)
        if delegation:
            delegated_from = delegation.delegator_id
        
        # Record action
        action = ApprovalActionModel(
            request_id=request_id,
            approver_id=actual_approver,
            approval_level=request.current_level,
            decision=decision,
            comments=comments,
            delegated_from=delegated_from
        )
        db.add(action)
        
        # Process decision
        if decision == "rejected":
            request.status = ApprovalStatus.REJECTED
            request.resolved_at = datetime.utcnow()
            db.commit()
            
            # Notify requester
            await self._notify_requester(request, "rejected")
            
            return ApprovalResult(
                request_id=request_id,
                status=ApprovalStatus.REJECTED,
                decision="rejected",
                decided_by=actual_approver,
                decided_at=datetime.utcnow(),
                comments=comments
            )
        
        # Approved - check if more levels needed
        workflow = await self.get_workflow(request.workflow_id, tenant_id, db)
        
        if workflow and request.current_level + 1 < len(workflow.approval_levels):
            # Move to next level
            request.current_level += 1
            db.commit()
            
            # Route to next level approvers
            next_approvers = await self.route_approval(request, db)
            await self._notify_approvers(request, next_approvers)
            
            return ApprovalResult(
                request_id=request_id,
                status=ApprovalStatus.PENDING,
                decision="approved",
                decided_by=actual_approver,
                decided_at=datetime.utcnow(),
                comments=comments,
                next_approver=next_approvers[0] if next_approvers else None
            )
        
        # Final approval
        request.status = ApprovalStatus.APPROVED
        request.resolved_at = datetime.utcnow()
        db.commit()
        
        # Notify requester
        await self._notify_requester(request, "approved")
        
        # Grant permission
        await self._grant_approved_permission(request, db)
        
        return ApprovalResult(
            request_id=request_id,
            status=ApprovalStatus.APPROVED,
            decision="approved",
            decided_by=actual_approver,
            decided_at=datetime.utcnow(),
            comments=comments
        )
    
    # ========================================================================
    # Timeout Handling
    # ========================================================================
    
    async def handle_timeout(
        self,
        request_id: UUID,
        tenant_id: str,
        db: Session
    ) -> ApprovalResult:
        """
        Handle approval request timeout.
        
        Args:
            request_id: Request ID
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            ApprovalResult with timeout status
        """
        request = db.query(ApprovalRequestModel).filter(
            and_(
                ApprovalRequestModel.id == request_id,
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatus.PENDING
            )
        ).first()
        
        if not request:
            return ApprovalResult(
                request_id=request_id,
                status=ApprovalStatus.EXPIRED,
                decision=None
            )
        
        request.status = ApprovalStatus.EXPIRED
        request.resolved_at = datetime.utcnow()
        db.commit()
        
        # Notify requester
        await self._notify_requester(request, "expired")
        
        self.logger.info(f"Request {request_id} expired due to timeout")
        
        return ApprovalResult(
            request_id=request_id,
            status=ApprovalStatus.EXPIRED,
            decision=None
        )
    
    async def process_expired_requests(
        self,
        tenant_id: str,
        db: Session
    ) -> int:
        """
        Process all expired requests for a tenant.
        
        Args:
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            Number of requests expired
        """
        now = datetime.utcnow()
        
        expired_requests = db.query(ApprovalRequestModel).filter(
            and_(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatus.PENDING,
                ApprovalRequestModel.expires_at < now
            )
        ).all()
        
        count = 0
        for request in expired_requests:
            await self.handle_timeout(request.id, tenant_id, db)
            count += 1
        
        return count
    
    # ========================================================================
    # Delegation
    # ========================================================================
    
    async def delegate_approval(
        self,
        delegator_id: UUID,
        delegate_to: UUID,
        start_date: datetime,
        end_date: datetime,
        tenant_id: str,
        db: Session
    ) -> ApprovalDelegationModel:
        """
        Create an approval delegation.
        
        Args:
            delegator_id: User delegating approval authority
            delegate_to: User receiving delegation
            start_date: Delegation start date
            end_date: Delegation end date
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            Created ApprovalDelegationModel
        """
        # Deactivate any existing delegations
        existing = db.query(ApprovalDelegationModel).filter(
            and_(
                ApprovalDelegationModel.tenant_id == tenant_id,
                ApprovalDelegationModel.delegator_id == delegator_id,
                ApprovalDelegationModel.is_active == True
            )
        ).all()
        
        for d in existing:
            d.is_active = False
        
        # Create new delegation
        delegation = ApprovalDelegationModel(
            tenant_id=tenant_id,
            delegator_id=delegator_id,
            delegate_id=delegate_to,
            start_date=start_date,
            end_date=end_date
        )
        
        db.add(delegation)
        db.commit()
        db.refresh(delegation)
        
        self.logger.info(f"Created delegation from {delegator_id} to {delegate_to}")
        return delegation
    
    async def revoke_delegation(
        self,
        delegation_id: UUID,
        tenant_id: str,
        db: Session
    ) -> bool:
        """Revoke an approval delegation."""
        delegation = db.query(ApprovalDelegationModel).filter(
            and_(
                ApprovalDelegationModel.id == delegation_id,
                ApprovalDelegationModel.tenant_id == tenant_id
            )
        ).first()
        
        if not delegation:
            return False
        
        delegation.is_active = False
        db.commit()
        
        return True
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    async def get_pending_approvals(
        self,
        approver_id: UUID,
        tenant_id: str,
        db: Session
    ) -> List[ApprovalRequestModel]:
        """Get pending approvals for an approver."""
        # Get direct pending requests
        # In production, this would check workflow configurations
        # to determine which requests the approver can handle
        
        requests = db.query(ApprovalRequestModel).filter(
            and_(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatus.PENDING,
                ApprovalRequestModel.expires_at > datetime.utcnow()
            )
        ).all()
        
        # Filter by approver (simplified - in production check workflow levels)
        return requests
    
    async def get_approval_history(
        self,
        request_id: UUID,
        tenant_id: str,
        db: Session
    ) -> List[ApprovalActionModel]:
        """Get approval history for a request."""
        request = db.query(ApprovalRequestModel).filter(
            and_(
                ApprovalRequestModel.id == request_id,
                ApprovalRequestModel.tenant_id == tenant_id
            )
        ).first()
        
        if not request:
            return []
        
        return db.query(ApprovalActionModel).filter(
            ApprovalActionModel.request_id == request_id
        ).order_by(ApprovalActionModel.action_at).all()
    
    async def get_user_requests(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Session,
        status: Optional[ApprovalStatus] = None
    ) -> List[ApprovalRequestModel]:
        """Get approval requests submitted by a user."""
        query = db.query(ApprovalRequestModel).filter(
            and_(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.requester_id == user_id
            )
        )
        
        if status:
            query = query.filter(ApprovalRequestModel.status == status)
        
        return query.order_by(ApprovalRequestModel.created_at.desc()).all()
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    async def _get_resource_sensitivity(
        self,
        resource: str,
        resource_type: str,
        tenant_id: str,
        db: Session
    ) -> SensitivityLevel:
        """Get sensitivity level for a resource."""
        classification = db.query(DataClassificationModel).filter(
            and_(
                DataClassificationModel.tenant_id == tenant_id,
                DataClassificationModel.dataset_id == resource
            )
        ).first()
        
        if classification:
            return classification.sensitivity_level
        
        # Default to internal
        return SensitivityLevel.INTERNAL
    
    async def _create_default_workflow(
        self,
        tenant_id: str,
        db: Session
    ) -> ApprovalWorkflowModel:
        """Create a default approval workflow."""
        workflow = ApprovalWorkflowModel(
            tenant_id=tenant_id,
            name="Default Workflow",
            description="Default approval workflow",
            sensitivity_levels=[
                SensitivityLevel.INTERNAL.value,
                SensitivityLevel.CONFIDENTIAL.value,
                SensitivityLevel.TOP_SECRET.value
            ],
            approval_levels=[
                {"level": 0, "name": "Manager Approval", "approvers": []}
            ],
            timeout_hours=72,
            created_by=UUID("00000000-0000-0000-0000-000000000000")
        )
        
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        return workflow
    
    async def _check_auto_approve(
        self,
        requester_id: UUID,
        resource: str,
        action: str,
        workflow: ApprovalWorkflowModel,
        tenant_id: str,
        db: Session
    ) -> bool:
        """Check if request should be auto-approved."""
        if not workflow.auto_approve_conditions:
            return False
        
        for condition in workflow.auto_approve_conditions:
            # Check condition type
            if condition.get("type") == "user_role":
                # Check if user has specified role
                required_role = condition.get("role")
                # In production, check user roles
                pass
            elif condition.get("type") == "resource_pattern":
                # Check if resource matches pattern
                import fnmatch
                pattern = condition.get("pattern", "*")
                if fnmatch.fnmatch(resource, pattern):
                    return True
            elif condition.get("type") == "action":
                # Check if action matches
                if action == condition.get("action"):
                    return True
        
        return False
    
    async def _apply_delegations(
        self,
        approvers: List[UUID],
        tenant_id: str,
        db: Session
    ) -> List[UUID]:
        """Apply active delegations to approver list."""
        now = datetime.utcnow()
        result = []
        
        for approver in approvers:
            delegation = db.query(ApprovalDelegationModel).filter(
                and_(
                    ApprovalDelegationModel.tenant_id == tenant_id,
                    ApprovalDelegationModel.delegator_id == approver,
                    ApprovalDelegationModel.is_active == True,
                    ApprovalDelegationModel.start_date <= now,
                    ApprovalDelegationModel.end_date >= now
                )
            ).first()
            
            if delegation:
                result.append(delegation.delegate_id)
            else:
                result.append(approver)
        
        return result
    
    async def _get_active_delegation(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Session
    ) -> Optional[ApprovalDelegationModel]:
        """Get active delegation where user is the delegate."""
        now = datetime.utcnow()
        
        return db.query(ApprovalDelegationModel).filter(
            and_(
                ApprovalDelegationModel.tenant_id == tenant_id,
                ApprovalDelegationModel.delegate_id == user_id,
                ApprovalDelegationModel.is_active == True,
                ApprovalDelegationModel.start_date <= now,
                ApprovalDelegationModel.end_date >= now
            )
        ).first()
    
    async def _notify_approvers(
        self,
        request: ApprovalRequestModel,
        approvers: List[UUID]
    ) -> None:
        """Send notifications to approvers."""
        if self._notification_service:
            for approver in approvers:
                await self._notification_service.send(
                    user_id=approver,
                    title="New Approval Request",
                    message=f"Approval request for {request.resource}",
                    data={"request_id": str(request.id)}
                )
    
    async def _notify_requester(
        self,
        request: ApprovalRequestModel,
        status: str
    ) -> None:
        """Send notification to requester."""
        if self._notification_service:
            await self._notification_service.send(
                user_id=request.requester_id,
                title=f"Approval Request {status.title()}",
                message=f"Your request for {request.resource} has been {status}",
                data={"request_id": str(request.id)}
            )
    
    async def _grant_approved_permission(
        self,
        request: ApprovalRequestModel,
        db: Session
    ) -> None:
        """Grant permission after approval."""
        from src.security.data_permission_engine import get_data_permission_engine
        from src.schemas.data_permission import GrantPermissionRequest, ResourceLevel, DataPermissionAction
        
        engine = get_data_permission_engine()
        
        # Create temporary permission (24 hours by default)
        await engine.grant_temporary_permission(
            user_id=str(request.requester_id),
            resource=f"{request.resource_type}:{request.resource}",
            action=request.action,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            tenant_id=request.tenant_id,
            granted_by=UUID("00000000-0000-0000-0000-000000000000"),  # System
            db=db
        )


# Global instance
_approval_workflow_engine: Optional[ApprovalWorkflowEngine] = None


def get_approval_workflow_engine() -> ApprovalWorkflowEngine:
    """Get or create the global approval workflow engine instance."""
    global _approval_workflow_engine
    if _approval_workflow_engine is None:
        _approval_workflow_engine = ApprovalWorkflowEngine()
    return _approval_workflow_engine
