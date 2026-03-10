"""
Unit tests for ApprovalService.

Tests approval workflow including:
- Creating approval requests
- Processing approvals/rejections
- Permission validation
- Expiry handling
- Query operations
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from src.services.approval_service import ApprovalService
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord
)
from src.services.permission_service import UserRole


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    db.fetchone = Mock()
    db.fetchall = Mock()
    return db


@pytest.fixture
def approval_service(mock_db):
    """Create an ApprovalService instance with mock database."""
    return ApprovalService(mock_db)


@pytest.fixture
def sample_transfer_request():
    """Create a sample transfer request for testing."""
    return DataTransferRequest(
        source_type="structuring",
        source_id="test-source-123",
        target_state="in_sample_library",
        data_attributes=DataAttributes(
            category="test_category",
            tags=["test", "sample"],
            quality_score=0.9,
            description="Test transfer request"
        ),
        records=[
            TransferRecord(
                id="record-1",
                content={"field1": "value1", "field2": "value2"},
                metadata={"source": "test"}
            ),
            TransferRecord(
                id="record-2",
                content={"field1": "value3", "field2": "value4"},
                metadata={"source": "test"}
            )
        ]
    )


class TestCreateApprovalRequest:
    """Tests for creating approval requests."""
    
    @pytest.mark.asyncio
    async def test_create_approval_request_success(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test successful creation of approval request."""
        # Arrange
        requester_id = "user-123"
        requester_role = UserRole.DATA_ANALYST
        
        # Mock database execute
        mock_db.execute.return_value = None
        
        # Mock notification methods
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=sample_transfer_request,
            requester_id=requester_id,
            requester_role=requester_role
        )
        
        # Assert
        assert approval.requester_id == requester_id
        assert approval.requester_role == requester_role.value
        assert approval.status == ApprovalStatus.PENDING
        assert approval.transfer_request == sample_transfer_request
        assert approval.expires_at > datetime.utcnow()
        assert approval.approver_id is None
        assert approval.approved_at is None
        
        # Verify database insert was called
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify notifications were sent
        approval_service._notify_approvers.assert_called_once_with(approval)
    
    @pytest.mark.asyncio
    async def test_create_approval_request_empty_records(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that creating approval with empty records raises error."""
        # Arrange
        sample_transfer_request.records = []
        
        # Act & Assert
        with pytest.raises(ValueError, match="must contain at least one record"):
            await approval_service.create_approval_request(
                transfer_request=sample_transfer_request,
                requester_id="user-123",
                requester_role=UserRole.DATA_ANALYST
            )
    
    @pytest.mark.asyncio
    async def test_create_approval_request_sets_expiry(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test that approval request has correct expiry date."""
        # Arrange
        mock_db.execute.return_value = None
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER
        )
        
        # Assert
        expected_expiry = datetime.utcnow() + timedelta(days=7)
        time_diff = abs((approval.expires_at - expected_expiry).total_seconds())
        assert time_diff < 5  # Within 5 seconds tolerance


class TestApproveRequest:
    """Tests for approving/rejecting requests."""
    
    @pytest.mark.asyncio
    async def test_approve_request_success(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test successful approval of request."""
        # Arrange
        approval_id = str(uuid4())
        approver_id = "approver-123"
        approver_role = UserRole.DATA_MANAGER
        
        # Mock existing approval
        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Act
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id=approver_id,
            approver_role=approver_role,
            approved=True,
            comment="Looks good"
        )
        
        # Assert
        assert result.status == ApprovalStatus.APPROVED
        assert result.approver_id == approver_id
        assert result.comment == "Looks good"
        
        # Verify status update was called
        approval_service._update_approval_status.assert_called_once_with(
            approval_id,
            ApprovalStatus.APPROVED,
            approver_id,
            "Looks good"
        )
        
        # Verify requester was notified
        approval_service._notify_requester.assert_called_once()
        
        # Verify transfer was executed
        approval_service._execute_transfer.assert_called_once_with(
            sample_transfer_request
        )
    
    @pytest.mark.asyncio
    async def test_reject_request_success(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test successful rejection of request."""
        # Arrange
        approval_id = str(uuid4())
        approver_id = "approver-123"
        approver_role = UserRole.ADMIN
        
        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Act
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id=approver_id,
            approver_role=approver_role,
            approved=False,
            comment="Insufficient quality"
        )
        
        # Assert
        assert result.status == ApprovalStatus.REJECTED
        assert result.approver_id == approver_id
        assert result.comment == "Insufficient quality"
        
        # Verify requester was notified of rejection
        approval_service._notify_requester.assert_called_once()
        
        # Verify transfer was NOT executed
        approval_service._execute_transfer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_approve_request_insufficient_permission(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that non-authorized users cannot approve."""
        # Arrange
        approval_id = str(uuid4())
        
        # Act & Assert - DATA_ANALYST cannot approve
        with pytest.raises(PermissionError, match="cannot approve requests"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="user-123",
                approver_role=UserRole.DATA_ANALYST,
                approved=True
            )
        
        # Act & Assert - USER cannot approve
        with pytest.raises(PermissionError, match="cannot approve requests"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="user-456",
                approver_role=UserRole.USER,
                approved=True
            )
    
    @pytest.mark.asyncio
    async def test_approve_request_not_found(
        self,
        approval_service
    ):
        """Test approving non-existent request raises error."""
        # Arrange
        approval_service._get_approval_by_id = Mock(return_value=None)
        
        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await approval_service.approve_request(
                approval_id="nonexistent-id",
                approver_id="approver-123",
                approver_role=UserRole.ADMIN,
                approved=True
            )
    
    @pytest.mark.asyncio
    async def test_approve_request_already_processed(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that already processed requests cannot be re-approved."""
        # Arrange
        approval_id = str(uuid4())
        
        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.APPROVED,  # Already approved
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            approver_id="previous-approver",
            approved_at=datetime.utcnow()
        )
        
        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        
        # Act & Assert
        with pytest.raises(ValueError, match="already approved"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="approver-123",
                approver_role=UserRole.ADMIN,
                approved=True
            )
    @pytest.mark.asyncio
    async def test_reject_already_rejected_request(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that already rejected requests cannot be re-processed."""
        approval_id = str(uuid4())

        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.REJECTED,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            approver_id="previous-approver",
            approved_at=datetime.utcnow(),
            comment="Previously rejected"
        )

        approval_service._get_approval_by_id = Mock(return_value=existing_approval)

        with pytest.raises(ValueError, match="already rejected"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="approver-123",
                approver_role=UserRole.ADMIN,
                approved=True
            )

    @pytest.mark.asyncio
    async def test_approve_expired_request_cannot_be_rejected(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that expired requests cannot be rejected either."""
        approval_id = str(uuid4())

        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=3)
        )

        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()

        with pytest.raises(ValueError, match="expired"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="approver-123",
                approver_role=UserRole.DATA_MANAGER,
                approved=False
            )

    @pytest.mark.asyncio
    async def test_approve_request_sets_approved_at_timestamp(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that approved_at timestamp is set on approval."""
        approval_id = str(uuid4())
        before_approve = datetime.utcnow()

        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()

        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="approver-123",
            approver_role=UserRole.ADMIN,
            approved=True
        )

        assert result.approved_at is not None
        assert result.approved_at >= before_approve
    
    @pytest.mark.asyncio
    async def test_approve_request_expired(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that expired requests cannot be approved."""
        # Arrange
        approval_id = str(uuid4())
        
        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=3)  # Expired 3 days ago
        )
        
        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()
        
        # Act & Assert
        with pytest.raises(ValueError, match="expired"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="approver-123",
                approver_role=UserRole.ADMIN,
                approved=True
            )
        
        # Verify status was updated to EXPIRED
        approval_service._update_approval_status.assert_called_once_with(
            approval_id,
            ApprovalStatus.EXPIRED,
            "approver-123",
            "Approval request expired"
        )


class TestGetPendingApprovals:
    """Tests for querying pending approvals."""
    
    def test_get_pending_approvals_success(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test retrieving pending approvals."""
        # Arrange
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (
                "approval-1",
                sample_transfer_request.model_dump_json(),
                "user-123",
                UserRole.DATA_ANALYST.value,
                ApprovalStatus.PENDING.value,
                datetime.utcnow(),
                datetime.utcnow() + timedelta(days=7),
                None,
                None,
                None
            )
        ]
        mock_db.execute.return_value = mock_result
        
        # Act
        approvals = approval_service.get_pending_approvals(limit=10, offset=0)
        
        # Assert
        assert len(approvals) == 1
        assert approvals[0].id == "approval-1"
        assert approvals[0].status == ApprovalStatus.PENDING
        assert approvals[0].requester_id == "user-123"
    
    def test_get_pending_approvals_empty(
        self,
        approval_service,
        mock_db
    ):
        """Test retrieving pending approvals when none exist."""
        # Arrange
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Act
        approvals = approval_service.get_pending_approvals()
        
        # Assert
        assert len(approvals) == 0


class TestGetUserApprovalRequests:
    """Tests for querying user's approval requests."""
    
    def test_get_user_approval_requests_all_statuses(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test retrieving all approval requests for a user."""
        # Arrange
        user_id = "user-123"
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (
                "approval-1",
                sample_transfer_request.model_dump_json(),
                user_id,
                UserRole.DATA_ANALYST.value,
                ApprovalStatus.PENDING.value,
                datetime.utcnow(),
                datetime.utcnow() + timedelta(days=7),
                None,
                None,
                None
            ),
            (
                "approval-2",
                sample_transfer_request.model_dump_json(),
                user_id,
                UserRole.DATA_ANALYST.value,
                ApprovalStatus.APPROVED.value,
                datetime.utcnow() - timedelta(days=2),
                datetime.utcnow() + timedelta(days=5),
                "approver-456",
                datetime.utcnow() - timedelta(days=1),
                "Approved"
            )
        ]
        mock_db.execute.return_value = mock_result
        
        # Act
        approvals = approval_service.get_user_approval_requests(
            user_id=user_id,
            limit=10,
            offset=0
        )
        
        # Assert
        assert len(approvals) == 2
        assert approvals[0].requester_id == user_id
        assert approvals[1].requester_id == user_id
    
    def test_get_user_approval_requests_filtered_by_status(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test retrieving user's approval requests filtered by status."""
        # Arrange
        user_id = "user-123"
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (
                "approval-1",
                sample_transfer_request.model_dump_json(),
                user_id,
                UserRole.DATA_ANALYST.value,
                ApprovalStatus.PENDING.value,
                datetime.utcnow(),
                datetime.utcnow() + timedelta(days=7),
                None,
                None,
                None
            )
        ]
        mock_db.execute.return_value = mock_result
        
        # Act
        approvals = approval_service.get_user_approval_requests(
            user_id=user_id,
            status=ApprovalStatus.PENDING,
            limit=10,
            offset=0
        )
        
        # Assert
        assert len(approvals) == 1
        assert approvals[0].status == ApprovalStatus.PENDING


class TestExpireOldApprovals:
    """Tests for expiring old approval requests."""
    
    def test_expire_old_approvals_success(
        self,
        approval_service,
        mock_db
    ):
        """Test expiring old pending approvals."""
        # Arrange
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_db.execute.return_value = mock_result
        
        # Act
        expired_count = approval_service.expire_old_approvals()
        
        # Assert
        assert expired_count == 3
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_expire_old_approvals_none_expired(
        self,
        approval_service,
        mock_db
    ):
        """Test expiring when no approvals are expired."""
        # Arrange
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        
        # Act
        expired_count = approval_service.expire_old_approvals()
        
        # Assert
        assert expired_count == 0


class TestNotificationMethods:
    """Tests for notification helper methods."""

    @pytest.mark.asyncio
    async def test_notify_approvers_called_on_creation(
        self,
        approval_service,
        mock_db,
        sample_transfer_request
    ):
        """Test that approvers are notified when approval request is created."""
        mock_db.execute.return_value = None
        approval_service._notify_approvers = AsyncMock()

        await approval_service.create_approval_request(
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST
        )

        approval_service._notify_approvers.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_approvers_sends_to_all_eligible(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that both internal message and email are sent to each approver."""
        approvers = [
            {"id": "admin-1", "email": "admin@test.com", "username": "admin1",
             "full_name": "Admin One", "role": "admin"},
            {"id": "manager-1", "email": "manager@test.com", "username": "mgr1",
             "full_name": "Manager One", "role": "data_manager"},
        ]
        approval_service._get_eligible_approvers = Mock(return_value=approvers)
        approval_service._send_internal_message = AsyncMock()
        approval_service._send_email_notification = AsyncMock()

        approval = ApprovalRequest(
            id=str(uuid4()),
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        await approval_service._notify_approvers(approval)

        assert approval_service._send_internal_message.call_count == 2
        assert approval_service._send_email_notification.call_count == 2

    @pytest.mark.asyncio
    async def test_notify_approvers_no_eligible_approvers(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test notification when no eligible approvers exist."""
        approval_service._get_eligible_approvers = Mock(return_value=[])
        approval_service._send_internal_message = AsyncMock()
        approval_service._send_email_notification = AsyncMock()

        approval = ApprovalRequest(
            id=str(uuid4()),
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        await approval_service._notify_approvers(approval)

        approval_service._send_internal_message.assert_not_called()
        approval_service._send_email_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_requester_notified_on_approval(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that requester is notified when request is approved."""
        approval_id = str(uuid4())

        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()

        await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="approver-123",
            approver_role=UserRole.ADMIN,
            approved=True
        )

        approval_service._notify_requester.assert_called_once()
        notified_approval = approval_service._notify_requester.call_args[0][0]
        assert notified_approval.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_requester_notified_on_rejection(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that requester is notified when request is rejected."""
        approval_id = str(uuid4())

        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()

        await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="approver-123",
            approver_role=UserRole.DATA_MANAGER,
            approved=False,
            comment="Data quality insufficient"
        )

        approval_service._notify_requester.assert_called_once()
        notified_approval = approval_service._notify_requester.call_args[0][0]
        assert notified_approval.status == ApprovalStatus.REJECTED
        assert notified_approval.comment == "Data quality insufficient"

    def test_get_eligible_approvers_returns_list(
        self,
        approval_service,
        mock_db
    ):
        """Test that get_eligible_approvers returns a list."""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("admin-1", "admin@test.com", "admin1", "Admin One", "admin")
        ]
        mock_db.execute.return_value = mock_result

        approvers = approval_service._get_eligible_approvers()

        assert isinstance(approvers, list)
        assert len(approvers) == 1
        assert approvers[0]["id"] == "admin-1"
        assert approvers[0]["role"] == "admin"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_approve_with_empty_comment(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test approving without a comment."""
        # Arrange
        approval_id = str(uuid4())
        
        existing_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=existing_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Act
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="approver-123",
            approver_role=UserRole.ADMIN,
            approved=True,
            comment=None  # No comment
        )
        
        # Assert
        assert result.comment is None
    
    @pytest.mark.asyncio
    async def test_create_approval_with_single_record(
        self,
        approval_service,
        mock_db
    ):
        """Test creating approval with minimum (1) record."""
        # Arrange
        transfer_request = DataTransferRequest(
            source_type="augmentation",
            source_id="source-1",
            target_state="annotation_pending",
            data_attributes=DataAttributes(
                category="test",
                tags=[],
                quality_score=0.5
            ),
            records=[
                TransferRecord(
                    id="single-record",
                    content={"data": "value"}
                )
            ]
        )
        
        mock_db.execute.return_value = None
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER
        )
        
        # Assert
        assert len(approval.transfer_request.records) == 1
        assert approval.status == ApprovalStatus.PENDING
