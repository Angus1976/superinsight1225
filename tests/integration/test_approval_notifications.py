"""
Integration tests for approval notification system.

Tests the complete notification flow including:
- Notification triggering on approval creation
- Notification triggering on approval decision
- Database integration
- Email integration (mocked)
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import text

from src.services.approval_service import ApprovalService
from src.services.notification_service import NotificationService
from src.models.data_transfer import DataTransferRequest, DataAttributes, TransferRecord
from src.services.permission_service import UserRole


@pytest.fixture
def approval_service_with_notifications(db_session):
    """Create ApprovalService with notification system."""
    service = ApprovalService(db_session)
    # Mock email sender to avoid actual email sending
    service.notification_service.email_sender.send_report = AsyncMock(
        return_value=Mock(success=True)
    )
    return service


@pytest.fixture
def setup_test_users(db_session):
    """Create test users in database."""
    # Create approver (data_manager)
    approver_id = str(uuid4())
    insert_approver = text("""
        INSERT INTO users (id, username, email, password_hash, role, tenant_id, is_active)
        VALUES (:id, :username, :email, :password_hash, :role, :tenant_id, :is_active)
    """)
    db_session.execute(insert_approver, {
        "id": approver_id,
        "username": "approver1",
        "email": "approver@example.com",
        "password_hash": "hashed_password",
        "role": "data_manager",
        "tenant_id": "tenant-1",
        "is_active": True
    })
    
    # Create requester (data_analyst)
    requester_id = str(uuid4())
    insert_requester = text("""
        INSERT INTO users (id, username, email, password_hash, role, tenant_id, is_active)
        VALUES (:id, :username, :email, :password_hash, :role, :tenant_id, :is_active)
    """)
    db_session.execute(insert_requester, {
        "id": requester_id,
        "username": "requester1",
        "email": "requester@example.com",
        "password_hash": "hashed_password",
        "role": "data_analyst",
        "tenant_id": "tenant-1",
        "is_active": True
    })
    
    db_session.commit()
    
    return {
        "approver_id": approver_id,
        "requester_id": requester_id
    }


@pytest.fixture
def valid_transfer_request():
    """Create valid transfer request."""
    return DataTransferRequest(
        source_type="structuring",
        source_id="source-123",
        target_state="in_sample_library",
        data_attributes=DataAttributes(
            category="test_data",
            tags=["test"],
            quality_score=0.9
        ),
        records=[
            TransferRecord(
                id="record-1",
                content={"field": "value"}
            )
        ]
    )


class TestApprovalCreationNotifications:
    """Test notifications sent when approval request is created."""
    
    @pytest.mark.asyncio
    async def test_create_approval_sends_notifications_to_approvers(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request,
        db_session
    ):
        """Test that creating approval sends notifications to all eligible approvers."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        
        # Act
        approval = await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert - Check internal messages were created
        query = text("""
            SELECT COUNT(*) FROM internal_messages
            WHERE related_approval_id = :approval_id
              AND message_type = 'approval_new_request'
        """)
        result = db_session.execute(query, {"approval_id": approval.id}).scalar()
        assert result > 0, "No internal messages created for approvers"
    
    @pytest.mark.asyncio
    async def test_create_approval_sends_email_to_approvers(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request
    ):
        """Test that creating approval triggers email sending."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        email_sender = approval_service_with_notifications.notification_service.email_sender
        
        # Act
        await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert
        assert email_sender.send_report.called, "Email was not sent"
        call_args = email_sender.send_report.call_args
        assert "approver@example.com" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_notification_contains_approval_details(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request,
        db_session
    ):
        """Test that notification contains relevant approval details."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        
        # Act
        approval = await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert - Check message content
        query = text("""
            SELECT content FROM internal_messages
            WHERE related_approval_id = :approval_id
            LIMIT 1
        """)
        result = db_session.execute(query, {"approval_id": approval.id}).scalar()
        
        assert approval.id in result
        assert "structuring" in result
        assert "in_sample_library" in result


class TestApprovalDecisionNotifications:
    """Test notifications sent when approval decision is made."""
    
    @pytest.mark.asyncio
    async def test_approve_request_sends_notification_to_requester(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request,
        db_session
    ):
        """Test that approving request sends notification to requester."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        approver_id = setup_test_users["approver_id"]
        
        # Create approval
        approval = await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Clear previous messages
        db_session.execute(text("DELETE FROM internal_messages"))
        db_session.commit()
        
        # Act - Approve the request
        await approval_service_with_notifications.approve_request(
            approval_id=approval.id,
            approver_id=approver_id,
            approver_role=UserRole.DATA_MANAGER,
            approved=True,
            comment="Approved for testing"
        )
        
        # Assert - Check notification was sent to requester
        query = text("""
            SELECT COUNT(*) FROM internal_messages
            WHERE recipient_id = :requester_id
              AND message_type = 'approval_approved'
        """)
        result = db_session.execute(query, {"requester_id": requester_id}).scalar()
        assert result > 0, "No approval notification sent to requester"
    
    @pytest.mark.asyncio
    async def test_reject_request_sends_notification_to_requester(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request,
        db_session
    ):
        """Test that rejecting request sends notification to requester."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        approver_id = setup_test_users["approver_id"]
        
        # Create approval
        approval = await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Clear previous messages
        db_session.execute(text("DELETE FROM internal_messages"))
        db_session.commit()
        
        # Act - Reject the request
        await approval_service_with_notifications.approve_request(
            approval_id=approval.id,
            approver_id=approver_id,
            approver_role=UserRole.DATA_MANAGER,
            approved=False,
            comment="Insufficient data quality"
        )
        
        # Assert - Check notification was sent to requester
        query = text("""
            SELECT content FROM internal_messages
            WHERE recipient_id = :requester_id
              AND message_type = 'approval_rejected'
        """)
        result = db_session.execute(query, {"requester_id": requester_id}).scalar()
        
        assert result is not None
        assert "拒绝" in result or "rejected" in result.lower()
        assert "Insufficient data quality" in result
    
    @pytest.mark.asyncio
    async def test_decision_notification_includes_comment(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request,
        db_session
    ):
        """Test that decision notification includes approver's comment."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        approver_id = setup_test_users["approver_id"]
        comment = "Data quality meets requirements"
        
        # Create and approve
        approval = await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        db_session.execute(text("DELETE FROM internal_messages"))
        db_session.commit()
        
        # Act
        await approval_service_with_notifications.approve_request(
            approval_id=approval.id,
            approver_id=approver_id,
            approver_role=UserRole.DATA_MANAGER,
            approved=True,
            comment=comment
        )
        
        # Assert
        query = text("""
            SELECT content FROM internal_messages
            WHERE recipient_id = :requester_id
        """)
        result = db_session.execute(query, {"requester_id": requester_id}).scalar()
        
        assert comment in result


class TestNotificationBilingualSupport:
    """Test bilingual notification support."""
    
    @pytest.mark.asyncio
    async def test_chinese_notification_content(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request,
        db_session
    ):
        """Test Chinese language notification content."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        
        # Act
        approval = await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert
        query = text("""
            SELECT subject, content FROM internal_messages
            WHERE related_approval_id = :approval_id
            LIMIT 1
        """)
        result = db_session.execute(query, {"approval_id": approval.id}).fetchone()
        
        subject, content = result
        assert "审批" in subject or "请求" in subject
        assert "审批ID" in content or "申请人" in content
    
    @pytest.mark.asyncio
    async def test_email_html_formatting(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request
    ):
        """Test that email is sent with HTML formatting."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        email_sender = approval_service_with_notifications.notification_service.email_sender
        
        # Act
        await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert
        call_kwargs = email_sender.send_report.call_args[1]
        assert call_kwargs["format"] == "html"
        assert "<html>" in call_kwargs["content"]
        assert "<body>" in call_kwargs["content"]


class TestNotificationErrorHandling:
    """Test error handling in notification system."""
    
    @pytest.mark.asyncio
    async def test_approval_creation_succeeds_despite_notification_failure(
        self,
        approval_service_with_notifications,
        setup_test_users,
        valid_transfer_request,
        db_session
    ):
        """Test that approval creation succeeds even if notifications fail."""
        # Arrange
        requester_id = setup_test_users["requester_id"]
        
        # Make email sending fail
        approval_service_with_notifications.notification_service.email_sender.send_report = AsyncMock(
            return_value=Mock(success=False, error_message="SMTP error")
        )
        
        # Act - Should not raise exception
        approval = await approval_service_with_notifications.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert - Approval should still be created
        assert approval.id is not None
        
        query = text("""
            SELECT COUNT(*) FROM approval_requests
            WHERE id = :approval_id
        """)
        result = db_session.execute(query, {"approval_id": approval.id}).scalar()
        assert result == 1
