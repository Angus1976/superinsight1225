"""
Integration test for complete approval processing workflow.

Tests the end-to-end approval processing including:
- Permission checks
- Status updates
- Notifications
- Transfer execution
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.approval_service import ApprovalService
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.models.data_transfer import DataTransferRequest, DataAttributes, TransferRecord
from src.services.permission_service import UserRole


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock()
    session.execute = Mock()
    session.commit = Mock()
    return session


@pytest.fixture
def approval_service(mock_db_session):
    """Create ApprovalService with mocked dependencies."""
    service = ApprovalService(mock_db_session)
    # Mock notification service to avoid external dependencies
    service.notification_service = Mock()
    service.notification_service.send_internal_message = AsyncMock()
    service.notification_service.send_email_notification = AsyncMock()
    return service


@pytest.fixture
def sample_transfer_request():
    """Create a sample transfer request."""
    return DataTransferRequest(
        source_type="structuring",
        source_id="test-source-123",
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


class TestApprovalProcessingWorkflow:
    """Test complete approval processing workflow."""
    
    @pytest.mark.asyncio
    async def test_approve_workflow_complete(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test complete approval workflow from creation to execution."""
        # Step 1: Create approval request
        approval_id = str(uuid4())
        requester_id = "user-123"
        approver_id = "approver-456"
        
        # Mock approval retrieval
        pending_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=pending_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Step 2: Approve the request
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id=approver_id,
            approver_role=UserRole.DATA_MANAGER,
            approved=True,
            comment="Approved for testing"
        )
        
        # Step 3: Verify workflow steps
        # 3.1 Permission check passed (DATA_MANAGER can approve)
        assert result is not None
        
        # 3.2 Status updated to APPROVED
        assert result.status == ApprovalStatus.APPROVED
        assert result.approver_id == approver_id
        assert result.comment == "Approved for testing"
        
        # 3.3 Status update was called
        approval_service._update_approval_status.assert_called_once_with(
            approval_id,
            ApprovalStatus.APPROVED,
            approver_id,
            "Approved for testing"
        )
        
        # 3.4 Requester was notified
        approval_service._notify_requester.assert_called_once()
        
        # 3.5 Transfer was executed
        approval_service._execute_transfer.assert_called_once_with(
            sample_transfer_request
        )
    
    @pytest.mark.asyncio
    async def test_reject_workflow_complete(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test complete rejection workflow."""
        # Setup
        approval_id = str(uuid4())
        requester_id = "user-123"
        approver_id = "approver-456"
        
        pending_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id=requester_id,
            requester_role=UserRole.USER.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=pending_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Execute rejection
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id=approver_id,
            approver_role=UserRole.ADMIN,
            approved=False,
            comment="Insufficient data quality"
        )
        
        # Verify rejection workflow
        assert result.status == ApprovalStatus.REJECTED
        assert result.approver_id == approver_id
        assert result.comment == "Insufficient data quality"
        
        # Status updated to REJECTED
        approval_service._update_approval_status.assert_called_once_with(
            approval_id,
            ApprovalStatus.REJECTED,
            approver_id,
            "Insufficient data quality"
        )
        
        # Requester was notified
        approval_service._notify_requester.assert_called_once()
        
        # Transfer was NOT executed
        approval_service._execute_transfer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_permission_check_enforcement(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that permission checks are enforced."""
        approval_id = str(uuid4())
        
        # Test DATA_ANALYST cannot approve
        with pytest.raises(PermissionError, match="cannot approve requests"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="analyst-123",
                approver_role=UserRole.DATA_ANALYST,
                approved=True
            )
        
        # Test USER cannot approve
        with pytest.raises(PermissionError, match="cannot approve requests"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="user-123",
                approver_role=UserRole.USER,
                approved=True
            )
    
    @pytest.mark.asyncio
    async def test_expired_approval_handling(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test handling of expired approval requests."""
        approval_id = str(uuid4())
        
        # Create expired approval
        expired_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=3)  # Expired 3 days ago
        )
        
        approval_service._get_approval_by_id = Mock(return_value=expired_approval)
        approval_service._update_approval_status = Mock()
        
        # Attempt to approve expired request
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
    
    @pytest.mark.asyncio
    async def test_already_processed_approval(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that already processed approvals cannot be re-processed."""
        approval_id = str(uuid4())
        
        # Create already approved request
        approved_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.APPROVED,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            approver_id="previous-approver",
            approved_at=datetime.utcnow()
        )
        
        approval_service._get_approval_by_id = Mock(return_value=approved_approval)
        
        # Attempt to re-approve
        with pytest.raises(ValueError, match="already approved"):
            await approval_service.approve_request(
                approval_id=approval_id,
                approver_id="approver-123",
                approver_role=UserRole.ADMIN,
                approved=True
            )
    
    @pytest.mark.asyncio
    async def test_approval_not_found(
        self,
        approval_service
    ):
        """Test handling of non-existent approval requests."""
        approval_service._get_approval_by_id = Mock(return_value=None)
        
        with pytest.raises(ValueError, match="not found"):
            await approval_service.approve_request(
                approval_id="nonexistent-id",
                approver_id="approver-123",
                approver_role=UserRole.ADMIN,
                approved=True
            )
    
    @pytest.mark.asyncio
    async def test_approval_with_admin_role(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that ADMIN role can approve requests."""
        approval_id = str(uuid4())
        
        pending_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=pending_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Admin approves
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="admin-123",
            approver_role=UserRole.ADMIN,
            approved=True,
            comment="Admin approval"
        )
        
        # Verify success
        assert result.status == ApprovalStatus.APPROVED
        assert result.approver_id == "admin-123"
        approval_service._execute_transfer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approval_with_data_manager_role(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test that DATA_MANAGER role can approve requests."""
        approval_id = str(uuid4())
        
        pending_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=pending_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Data Manager approves
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="manager-123",
            approver_role=UserRole.DATA_MANAGER,
            approved=True,
            comment="Manager approval"
        )
        
        # Verify success
        assert result.status == ApprovalStatus.APPROVED
        assert result.approver_id == "manager-123"
        approval_service._execute_transfer.assert_called_once()


class TestApprovalProcessingEdgeCases:
    """Test edge cases in approval processing."""
    
    @pytest.mark.asyncio
    async def test_approval_without_comment(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test approval without providing a comment."""
        approval_id = str(uuid4())
        
        pending_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=pending_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        # Approve without comment
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="approver-123",
            approver_role=UserRole.ADMIN,
            approved=True,
            comment=None
        )
        
        # Verify approval succeeded
        assert result.status == ApprovalStatus.APPROVED
        assert result.comment is None
        approval_service._execute_transfer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rejection_with_detailed_comment(
        self,
        approval_service,
        sample_transfer_request
    ):
        """Test rejection with detailed comment."""
        approval_id = str(uuid4())
        
        pending_approval = ApprovalRequest(
            id=approval_id,
            transfer_request=sample_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER.value,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        approval_service._get_approval_by_id = Mock(return_value=pending_approval)
        approval_service._update_approval_status = Mock()
        approval_service._notify_requester = AsyncMock()
        approval_service._execute_transfer = AsyncMock()
        
        detailed_comment = """
        Rejection reasons:
        1. Data quality score below threshold (0.9 < 0.95)
        2. Missing required fields: field_x, field_y
        3. Inconsistent data format in 15% of records
        Please address these issues and resubmit.
        """
        
        # Reject with detailed comment
        result = await approval_service.approve_request(
            approval_id=approval_id,
            approver_id="approver-123",
            approver_role=UserRole.DATA_MANAGER,
            approved=False,
            comment=detailed_comment
        )
        
        # Verify rejection with comment
        assert result.status == ApprovalStatus.REJECTED
        assert result.comment == detailed_comment
        approval_service._execute_transfer.assert_not_called()
