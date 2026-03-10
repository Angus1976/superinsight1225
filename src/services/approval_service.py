"""
Approval Service for Data Transfer Integration.

Manages approval workflow for data transfer operations that require authorization.
Handles approval request creation, notification, processing, and timeout management.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.approval import ApprovalRequest, ApprovalStatus
from src.models.data_transfer import DataTransferRequest
from src.services.permission_service import UserRole
from src.services.notification_service import NotificationService
from src.config.approval_defaults import get_approval_settings


class ApprovalService:
    """
    Approval service for data transfer operations.
    
    Manages the complete approval workflow including:
    - Creating approval requests
    - Notifying approvers
    - Processing approvals/rejections
    - Handling approval timeouts
    - Tracking approval history
    """
    
    def __init__(self, db: Session):
        """
        Initialize the Approval Service.
        
        Args:
            db: Database session
        """
        self.db = db
        approval_settings = get_approval_settings()
        self.default_expiry_days = approval_settings.timeout_days
        self.notification_service = NotificationService(db)
    
    async def create_approval_request(
        self,
        transfer_request: DataTransferRequest,
        requester_id: str,
        requester_role: UserRole
    ) -> ApprovalRequest:
        """
        Create a new approval request for a data transfer operation.
        
        Args:
            transfer_request: The data transfer request requiring approval
            requester_id: ID of the user requesting the transfer
            requester_role: Role of the requesting user
            
        Returns:
            Created approval request
            
        Raises:
            ValueError: If transfer request is invalid
        """
        # Validate transfer request
        if not transfer_request.records:
            raise ValueError("Transfer request must contain at least one record")
        
        # Create approval request
        approval_id = str(uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=self.default_expiry_days)
        
        approval = ApprovalRequest(
            id=approval_id,
            transfer_request=transfer_request,
            requester_id=requester_id,
            requester_role=requester_role.value,
            status=ApprovalStatus.PENDING,
            created_at=created_at,
            expires_at=expires_at
        )
        
        # Store approval request in database
        # Note: In a real implementation, this would use SQLAlchemy models
        # For now, we'll store the approval data as JSONB
        from sqlalchemy import text
        
        insert_query = text("""
            INSERT INTO approval_requests (
                id, transfer_request, requester_id, requester_role,
                status, created_at, expires_at
            ) VALUES (
                :id, :transfer_request, :requester_id, :requester_role,
                :status, :created_at, :expires_at
            )
        """)
        
        self.db.execute(insert_query, {
            "id": approval.id,
            "transfer_request": transfer_request.model_dump_json(),
            "requester_id": approval.requester_id,
            "requester_role": approval.requester_role,
            "status": approval.status.value,
            "created_at": approval.created_at,
            "expires_at": approval.expires_at
        })
        self.db.commit()
        
        # Send notifications to approvers
        await self._notify_approvers(approval)
        
        return approval
    
    async def _notify_approvers(self, approval: ApprovalRequest) -> None:
        """
        Send notifications to eligible approvers.
        
        Args:
            approval: The approval request to notify about
            
        Note: In a real implementation, this would:
        - Query users with data_manager or admin roles
        - Send internal messages via notification service
        - Send email notifications
        - Log notification attempts
        """
        # Find eligible approvers (data_manager or admin roles)
        # This is a placeholder - actual implementation would query user table
        approvers = self._get_eligible_approvers()
        
        for approver in approvers:
            # Send internal message
            await self._send_internal_message(approver, approval)
            
            # Send email notification
            await self._send_email_notification(approver, approval)
    
    def _get_eligible_approvers(self) -> List[Dict[str, Any]]:
        """
        Get list of users eligible to approve requests.
        
        Returns:
            List of approver user dictionaries with 'id', 'email', 'role', etc.
            
        Queries users table for active users with data_manager or admin roles.
        """
        from sqlalchemy import text
        
        query = text("""
            SELECT id, email, username, full_name, role
            FROM users
            WHERE role IN ('admin', 'data_manager')
              AND is_active = true
        """)
        
        results = self.db.execute(query).fetchall()
        
        approvers = []
        for row in results:
            approvers.append({
                "id": str(row[0]),
                "email": row[1],
                "username": row[2],
                "full_name": row[3],
                "role": row[4]
            })
        
        return approvers
    
    async def _send_internal_message(
        self,
        approver: Dict[str, Any],
        approval: ApprovalRequest
    ) -> None:
        """
        Send internal notification message to approver.
        
        Args:
            approver: Approver user information (dict with 'id', 'email', etc.)
            approval: Approval request details
            
        Uses NotificationService to send internal message notification.
        """
        try:
            # Determine language based on user preference (default to Chinese)
            # In a real implementation, this would check user preferences
            language = "zh"
            
            await self.notification_service.send_approval_request_notification(
                approver=approver,
                approval=approval,
                language=language
            )
        except Exception as e:
            # Log error but don't fail the approval creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send internal message to {approver.get('id')}: {e}")
    
    async def _send_email_notification(
        self,
        approver: Dict[str, Any],
        approval: ApprovalRequest
    ) -> None:
        """
        Send email notification to approver.
        
        Args:
            approver: Approver user information (dict with 'id', 'email', etc.)
            approval: Approval request details
            
        Uses NotificationService to send email notification.
        """
        try:
            # Determine language based on user preference (default to Chinese)
            # In a real implementation, this would check user preferences
            language = "zh"
            
            await self.notification_service.send_approval_request_notification(
                approver=approver,
                approval=approval,
                language=language
            )
        except Exception as e:
            # Log error but don't fail the approval creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email to {approver.get('email')}: {e}")
    
    async def approve_request(
        self,
        approval_id: str,
        approver_id: str,
        approver_role: UserRole,
        approved: bool,
        comment: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Process an approval request (approve or reject).
        
        Args:
            approval_id: ID of the approval request
            approver_id: ID of the user processing the approval
            approver_role: Role of the approver
            approved: True to approve, False to reject
            comment: Optional comment explaining the decision
            
        Returns:
            Updated approval request
            
        Raises:
            ValueError: If approval not found or invalid state
            PermissionError: If user lacks approval permissions
        """
        # Verify approver has permission
        if approver_role not in [UserRole.ADMIN, UserRole.DATA_MANAGER]:
            raise PermissionError(
                f"User with role {approver_role.value} cannot approve requests"
            )
        
        # Fetch approval request
        approval = self._get_approval_by_id(approval_id)
        
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found")
        
        # Verify approval is still pending
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Approval request is already {approval.status.value}"
            )
        
        # Check if expired
        if datetime.utcnow() > approval.expires_at:
            # Mark as expired
            self._update_approval_status(
                approval_id,
                ApprovalStatus.EXPIRED,
                approver_id,
                "Approval request expired"
            )
            raise ValueError("Approval request has expired")
        
        # Update approval status
        new_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        self._update_approval_status(
            approval_id,
            new_status,
            approver_id,
            comment
        )
        
        # Update approval object
        approval.status = new_status
        approval.approver_id = approver_id
        approval.approved_at = datetime.utcnow()
        approval.comment = comment
        
        # Notify requester of decision
        await self._notify_requester(approval)
        
        # If approved, execute the transfer
        if approved:
            await self._execute_transfer(approval.transfer_request)
        
        return approval
    
    def _get_approval_by_id(self, approval_id: str) -> Optional[ApprovalRequest]:
        """
        Retrieve an approval request by ID.
        
        Args:
            approval_id: ID of the approval request
            
        Returns:
            Approval request if found, None otherwise
        """
        from sqlalchemy import text
        import json
        
        query = text("""
            SELECT id, transfer_request, requester_id, requester_role,
                   status, created_at, expires_at, approver_id, approved_at, comment
            FROM approval_requests
            WHERE id = :approval_id
        """)
        
        result = self.db.execute(query, {"approval_id": approval_id}).fetchone()
        
        if not result:
            return None
        
        # Parse transfer_request JSON
        transfer_request_data = json.loads(result[1]) if isinstance(result[1], str) else result[1]
        transfer_request = DataTransferRequest(**transfer_request_data)
        
        return ApprovalRequest(
            id=result[0],
            transfer_request=transfer_request,
            requester_id=result[2],
            requester_role=result[3],
            status=ApprovalStatus(result[4]),
            created_at=result[5],
            expires_at=result[6],
            approver_id=result[7],
            approved_at=result[8],
            comment=result[9]
        )
    
    def _update_approval_status(
        self,
        approval_id: str,
        status: ApprovalStatus,
        approver_id: str,
        comment: Optional[str] = None
    ) -> None:
        """
        Update the status of an approval request.
        
        Args:
            approval_id: ID of the approval request
            status: New status
            approver_id: ID of the approver
            comment: Optional comment
        """
        from sqlalchemy import text
        
        update_query = text("""
            UPDATE approval_requests
            SET status = :status,
                approver_id = :approver_id,
                approved_at = :approved_at,
                comment = :comment
            WHERE id = :approval_id
        """)
        
        self.db.execute(update_query, {
            "approval_id": approval_id,
            "status": status.value,
            "approver_id": approver_id,
            "approved_at": datetime.utcnow(),
            "comment": comment
        })
        self.db.commit()
    
    async def _notify_requester(self, approval: ApprovalRequest) -> None:
        """
        Notify the requester of the approval decision.
        
        Args:
            approval: The processed approval request
            
        Uses NotificationService to send decision notification to requester.
        """
        try:
            # Get requester information
            from sqlalchemy import text
            
            query = text("""
                SELECT id, email, username, full_name, role
                FROM users
                WHERE id = :user_id
            """)
            
            result = self.db.execute(query, {"user_id": approval.requester_id}).fetchone()
            
            if not result:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Requester {approval.requester_id} not found")
                return
            
            requester = {
                "id": str(result[0]),
                "email": result[1],
                "username": result[2],
                "full_name": result[3],
                "role": result[4]
            }
            
            # Determine language based on user preference (default to Chinese)
            language = "zh"
            
            # Determine if approved or rejected
            approved = approval.status == ApprovalStatus.APPROVED
            
            await self.notification_service.send_approval_decision_notification(
                requester=requester,
                approval=approval,
                approved=approved,
                language=language
            )
        except Exception as e:
            # Log error but don't fail the approval process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to notify requester {approval.requester_id}: {e}")
    
    async def _execute_transfer(self, transfer_request: DataTransferRequest) -> None:
        """
        Execute the approved data transfer.
        
        Args:
            transfer_request: The transfer request to execute
            
        Note: This would integrate with DataTransferService
        """
        # Placeholder - would call DataTransferService._execute_transfer
        pass
    
    def get_pending_approvals(
        self,
        approver_role: Optional[UserRole] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """
        Get list of pending approval requests.
        
        Args:
            approver_role: Optional filter by approver role eligibility
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of pending approval requests
        """
        from sqlalchemy import text
        import json
        
        query = text("""
            SELECT id, transfer_request, requester_id, requester_role,
                   status, created_at, expires_at, approver_id, approved_at, comment
            FROM approval_requests
            WHERE status = :status
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        results = self.db.execute(query, {
            "status": ApprovalStatus.PENDING.value,
            "limit": limit,
            "offset": offset
        }).fetchall()
        
        approvals = []
        for result in results:
            transfer_request_data = json.loads(result[1]) if isinstance(result[1], str) else result[1]
            transfer_request = DataTransferRequest(**transfer_request_data)
            
            approval = ApprovalRequest(
                id=result[0],
                transfer_request=transfer_request,
                requester_id=result[2],
                requester_role=result[3],
                status=ApprovalStatus(result[4]),
                created_at=result[5],
                expires_at=result[6],
                approver_id=result[7],
                approved_at=result[8],
                comment=result[9]
            )
            approvals.append(approval)
        
        return approvals
    
    def get_user_approval_requests(
        self,
        user_id: str,
        status: Optional[ApprovalStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """
        Get approval requests for a specific user.
        
        Args:
            user_id: ID of the user (requester)
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of approval requests for the user
        """
        from sqlalchemy import text
        import json
        
        if status:
            query = text("""
                SELECT id, transfer_request, requester_id, requester_role,
                       status, created_at, expires_at, approver_id, approved_at, comment
                FROM approval_requests
                WHERE requester_id = :user_id AND status = :status
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {
                "user_id": user_id,
                "status": status.value,
                "limit": limit,
                "offset": offset
            }
        else:
            query = text("""
                SELECT id, transfer_request, requester_id, requester_role,
                       status, created_at, expires_at, approver_id, approved_at, comment
                FROM approval_requests
                WHERE requester_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }
        
        results = self.db.execute(query, params).fetchall()
        
        approvals = []
        for result in results:
            transfer_request_data = json.loads(result[1]) if isinstance(result[1], str) else result[1]
            transfer_request = DataTransferRequest(**transfer_request_data)
            
            approval = ApprovalRequest(
                id=result[0],
                transfer_request=transfer_request,
                requester_id=result[2],
                requester_role=result[3],
                status=ApprovalStatus(result[4]),
                created_at=result[5],
                expires_at=result[6],
                approver_id=result[7],
                approved_at=result[8],
                comment=result[9]
            )
            approvals.append(approval)
        
        return approvals
    
    def expire_old_approvals(self) -> int:
        """
        Mark expired approval requests as EXPIRED.
        
        This should be called periodically (e.g., via cron job)
        to clean up old pending approvals.
        
        Returns:
            Number of approvals marked as expired
        """
        from sqlalchemy import text
        
        update_query = text("""
            UPDATE approval_requests
            SET status = :expired_status
            WHERE status = :pending_status
              AND expires_at < :current_time
        """)
        
        result = self.db.execute(update_query, {
            "expired_status": ApprovalStatus.EXPIRED.value,
            "pending_status": ApprovalStatus.PENDING.value,
            "current_time": datetime.utcnow()
        })
        self.db.commit()
        
        return result.rowcount
