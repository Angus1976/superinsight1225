"""
Unit tests for NotificationService.

Tests internal message and email notification functionality
for the approval workflow system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.notification_service import NotificationService
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.models.data_transfer import DataTransferRequest, DataAttributes, TransferRecord
from src.services.permission_service import UserRole


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_email_sender():
    """Create mock email sender."""
    sender = Mock()
    sender.send_report = AsyncMock()
    return sender


@pytest.fixture
def notification_service(mock_db, mock_email_sender):
    """Create NotificationService instance with mocked dependencies."""
    service = NotificationService(mock_db)
    service.email_sender = mock_email_sender
    return service


@pytest.fixture
def sample_approver():
    """Create sample approver user data."""
    return {
        "id": str(uuid4()),
        "email": "approver@example.com",
        "username": "approver1",
        "full_name": "Test Approver",
        "role": "data_manager"
    }


@pytest.fixture
def sample_requester():
    """Create sample requester user data."""
    return {
        "id": str(uuid4()),
        "email": "requester@example.com",
        "username": "requester1",
        "full_name": "Test Requester",
        "role": "data_analyst"
    }


@pytest.fixture
def sample_approval():
    """Create sample approval request."""
    transfer_request = DataTransferRequest(
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
    
    return ApprovalRequest(
        id=str(uuid4()),
        transfer_request=transfer_request,
        requester_id=str(uuid4()),
        requester_role=UserRole.DATA_ANALYST.value,
        status=ApprovalStatus.PENDING,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )


class TestInternalMessageNotifications:
    """Test internal message notification functionality."""
    
    @pytest.mark.asyncio
    async def test_send_internal_message_success(
        self,
        notification_service,
        mock_db,
        sample_approver,
        sample_approval
    ):
        """Test successful internal message sending."""
        # Act
        result = await notification_service._send_internal_message(
            recipient=sample_approver,
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_internal_message_chinese_content(
        self,
        notification_service,
        mock_db,
        sample_approver,
        sample_approval
    ):
        """Test Chinese language message content generation."""
        # Act
        await notification_service._send_internal_message(
            recipient=sample_approver,
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        call_args = mock_db.execute.call_args[0][1]
        assert "新的数据转存审批请求" in call_args["subject"]
        assert "审批ID" in call_args["content"]
    
    @pytest.mark.asyncio
    async def test_send_internal_message_english_content(
        self,
        notification_service,
        mock_db,
        sample_approver,
        sample_approval
    ):
        """Test English language message content generation."""
        # Act
        await notification_service._send_internal_message(
            recipient=sample_approver,
            approval=sample_approval,
            notification_type="new_request",
            language="en"
        )
        
        # Assert
        call_args = mock_db.execute.call_args[0][1]
        assert "New Data Transfer Approval Request" in call_args["subject"]
        assert "Approval ID" in call_args["content"]
    
    @pytest.mark.asyncio
    async def test_send_internal_message_approved_notification(
        self,
        notification_service,
        mock_db,
        sample_requester,
        sample_approval
    ):
        """Test approved decision notification content."""
        # Arrange
        sample_approval.status = ApprovalStatus.APPROVED
        sample_approval.approver_id = str(uuid4())
        sample_approval.approved_at = datetime.utcnow()
        sample_approval.comment = "Looks good"
        
        # Act
        await notification_service._send_internal_message(
            recipient=sample_requester,
            approval=sample_approval,
            notification_type="approved",
            language="zh"
        )
        
        # Assert
        call_args = mock_db.execute.call_args[0][1]
        assert "已批准" in call_args["subject"]
        assert "Looks good" in call_args["content"]
    
    @pytest.mark.asyncio
    async def test_send_internal_message_rejected_notification(
        self,
        notification_service,
        mock_db,
        sample_requester,
        sample_approval
    ):
        """Test rejected decision notification content."""
        # Arrange
        sample_approval.status = ApprovalStatus.REJECTED
        sample_approval.approver_id = str(uuid4())
        sample_approval.approved_at = datetime.utcnow()
        sample_approval.comment = "Insufficient data quality"
        
        # Act
        await notification_service._send_internal_message(
            recipient=sample_requester,
            approval=sample_approval,
            notification_type="rejected",
            language="zh"
        )
        
        # Assert
        call_args = mock_db.execute.call_args[0][1]
        assert "已被拒绝" in call_args["subject"]
        assert "Insufficient data quality" in call_args["content"]
    
    @pytest.mark.asyncio
    async def test_send_internal_message_database_error(
        self,
        notification_service,
        mock_db,
        sample_approver,
        sample_approval
    ):
        """Test handling of database errors."""
        # Arrange
        mock_db.execute.side_effect = Exception("Database error")
        
        # Act
        result = await notification_service._send_internal_message(
            recipient=sample_approver,
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        assert result is False
        mock_db.rollback.assert_called_once()


class TestEmailNotifications:
    """Test email notification functionality."""
    
    @pytest.mark.asyncio
    async def test_send_email_notification_success(
        self,
        notification_service,
        mock_email_sender,
        sample_approver,
        sample_approval
    ):
        """Test successful email sending."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_email_sender.send_report.return_value = mock_result
        
        # Act
        result = await notification_service._send_email_notification(
            recipient=sample_approver,
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        assert result is True
        mock_email_sender.send_report.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_notification_html_format(
        self,
        notification_service,
        mock_email_sender,
        sample_approver,
        sample_approval
    ):
        """Test email is sent in HTML format."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_email_sender.send_report.return_value = mock_result
        
        # Act
        await notification_service._send_email_notification(
            recipient=sample_approver,
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        call_kwargs = mock_email_sender.send_report.call_args[1]
        assert call_kwargs["format"] == "html"
        assert "<html>" in call_kwargs["content"]
    
    @pytest.mark.asyncio
    async def test_send_email_notification_no_email_address(
        self,
        notification_service,
        mock_email_sender,
        sample_approval
    ):
        """Test handling of missing email address."""
        # Arrange
        recipient_no_email = {
            "id": str(uuid4()),
            "username": "user1"
            # No email field
        }
        
        # Act
        result = await notification_service._send_email_notification(
            recipient=recipient_no_email,
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        assert result is False
        mock_email_sender.send_report.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_email_notification_send_failure(
        self,
        notification_service,
        mock_email_sender,
        sample_approver,
        sample_approval
    ):
        """Test handling of email send failure."""
        # Arrange
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "SMTP connection failed"
        mock_email_sender.send_report.return_value = mock_result
        
        # Act
        result = await notification_service._send_email_notification(
            recipient=sample_approver,
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        assert result is False


class TestApprovalNotifications:
    """Test high-level approval notification methods."""
    
    @pytest.mark.asyncio
    async def test_send_approval_request_notification(
        self,
        notification_service,
        mock_db,
        mock_email_sender,
        sample_approver,
        sample_approval
    ):
        """Test sending approval request notification."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_email_sender.send_report.return_value = mock_result
        
        # Act
        result = await notification_service.send_approval_request_notification(
            approver=sample_approver,
            approval=sample_approval,
            language="zh"
        )
        
        # Assert
        assert result is True
        mock_db.execute.assert_called_once()  # Internal message
        mock_email_sender.send_report.assert_called_once()  # Email
    
    @pytest.mark.asyncio
    async def test_send_approval_decision_notification_approved(
        self,
        notification_service,
        mock_db,
        mock_email_sender,
        sample_requester,
        sample_approval
    ):
        """Test sending approval decision notification for approved request."""
        # Arrange
        sample_approval.status = ApprovalStatus.APPROVED
        mock_result = Mock()
        mock_result.success = True
        mock_email_sender.send_report.return_value = mock_result
        
        # Act
        result = await notification_service.send_approval_decision_notification(
            requester=sample_requester,
            approval=sample_approval,
            approved=True,
            language="zh"
        )
        
        # Assert
        assert result is True
        mock_db.execute.assert_called_once()
        mock_email_sender.send_report.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_approval_decision_notification_rejected(
        self,
        notification_service,
        mock_db,
        mock_email_sender,
        sample_requester,
        sample_approval
    ):
        """Test sending approval decision notification for rejected request."""
        # Arrange
        sample_approval.status = ApprovalStatus.REJECTED
        mock_result = Mock()
        mock_result.success = True
        mock_email_sender.send_report.return_value = mock_result
        
        # Act
        result = await notification_service.send_approval_decision_notification(
            requester=sample_requester,
            approval=sample_approval,
            approved=False,
            language="en"
        )
        
        # Assert
        assert result is True
        mock_db.execute.assert_called_once()
        mock_email_sender.send_report.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_notification_partial_failure(
        self,
        notification_service,
        mock_db,
        mock_email_sender,
        sample_approver,
        sample_approval
    ):
        """Test notification succeeds if at least one channel works."""
        # Arrange - email fails but internal message succeeds
        mock_result = Mock()
        mock_result.success = False
        mock_email_sender.send_report.return_value = mock_result
        
        # Act
        result = await notification_service.send_approval_request_notification(
            approver=sample_approver,
            approval=sample_approval,
            language="zh"
        )
        
        # Assert - should still return True because internal message succeeded
        assert result is True


class TestMessageContentGeneration:
    """Test message content generation for different scenarios."""
    
    def test_generate_chinese_new_request_message(
        self,
        notification_service,
        sample_approval
    ):
        """Test Chinese new request message generation."""
        # Act
        subject, content = notification_service._generate_message_content(
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        assert "新的数据转存审批请求" in subject
        assert sample_approval.id in content
        assert "structuring" in content
        assert "in_sample_library" in content
    
    def test_generate_english_new_request_message(
        self,
        notification_service,
        sample_approval
    ):
        """Test English new request message generation."""
        # Act
        subject, content = notification_service._generate_message_content(
            approval=sample_approval,
            notification_type="new_request",
            language="en"
        )
        
        # Assert
        assert "New Data Transfer Approval Request" in subject
        assert sample_approval.id in content
        assert "structuring" in content
    
    def test_generate_email_html_content(
        self,
        notification_service,
        sample_approval
    ):
        """Test HTML email content generation."""
        # Act
        subject, html_content = notification_service._generate_email_content(
            approval=sample_approval,
            notification_type="new_request",
            language="zh"
        )
        
        # Assert
        assert "<html>" in html_content
        assert "<body>" in html_content
        assert sample_approval.id in html_content
        assert "structuring" in html_content
