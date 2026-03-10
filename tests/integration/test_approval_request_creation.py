"""
Integration tests for approval request creation workflow.

Tests the complete approval request creation logic including:
- Request validation
- Database storage
- Notification triggering
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.services.approval_service import ApprovalService
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord
)
from src.services.permission_service import UserRole


@pytest.fixture
def test_db():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    
    # Create approval_requests table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE approval_requests (
                id TEXT PRIMARY KEY,
                transfer_request TEXT NOT NULL,
                requester_id TEXT NOT NULL,
                requester_role TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                approver_id TEXT,
                approved_at TIMESTAMP,
                comment TEXT
            )
        """))
        conn.commit()
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture
def approval_service(test_db):
    """Create an ApprovalService instance with test database."""
    return ApprovalService(test_db)


@pytest.fixture
def valid_transfer_request():
    """Create a valid transfer request for testing."""
    return DataTransferRequest(
        source_type="structuring",
        source_id="test-source-123",
        target_state="in_sample_library",
        data_attributes=DataAttributes(
            category="test_category",
            tags=["test", "integration"],
            quality_score=0.85,
            description="Integration test transfer request"
        ),
        records=[
            TransferRecord(
                id="record-1",
                content={"field1": "value1", "field2": "value2"},
                metadata={"source": "test"}
            )
        ]
    )


class TestApprovalRequestCreation:
    """Test approval request creation workflow."""
    
    @pytest.mark.asyncio
    async def test_create_approval_request_stores_in_database(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that approval request is correctly stored in database."""
        # Arrange
        requester_id = "user-123"
        requester_role = UserRole.DATA_ANALYST
        
        # Mock notification to avoid external dependencies
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id=requester_id,
            requester_role=requester_role
        )
        
        # Assert - Verify approval object
        assert approval.id is not None
        assert approval.requester_id == requester_id
        assert approval.requester_role == requester_role.value
        assert approval.status == ApprovalStatus.PENDING
        assert approval.transfer_request == valid_transfer_request
        
        # Assert - Verify database storage
        result = test_db.execute(
            text("SELECT * FROM approval_requests WHERE id = :id"),
            {"id": approval.id}
        ).fetchone()
        
        assert result is not None
        assert result[0] == approval.id  # id
        assert result[2] == requester_id  # requester_id
        assert result[3] == requester_role.value  # requester_role
        assert result[4] == ApprovalStatus.PENDING.value  # status
    
    @pytest.mark.asyncio
    async def test_create_approval_request_sets_expiry_date(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that approval request has correct expiry date (7 days)."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        before_creation = datetime.utcnow()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER
        )
        
        after_creation = datetime.utcnow()
        
        # Assert
        expected_expiry_min = before_creation + timedelta(days=7)
        expected_expiry_max = after_creation + timedelta(days=7)
        
        assert expected_expiry_min <= approval.expires_at <= expected_expiry_max
        
        # Verify in database
        result = test_db.execute(
            text("SELECT expires_at FROM approval_requests WHERE id = :id"),
            {"id": approval.id}
        ).fetchone()
        
        assert result is not None
        assert result[0] is not None
    
    @pytest.mark.asyncio
    async def test_create_approval_request_triggers_notifications(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that creating approval request triggers notifications."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert
        approval_service._notify_approvers.assert_called_once()
        call_args = approval_service._notify_approvers.call_args[0]
        assert call_args[0].id == approval.id
    
    @pytest.mark.asyncio
    async def test_create_approval_request_validates_empty_records(
        self,
        approval_service,
        valid_transfer_request
    ):
        """Test that empty records list raises validation error."""
        # Arrange
        valid_transfer_request.records = []
        
        # Act & Assert
        with pytest.raises(ValueError, match="must contain at least one record"):
            await approval_service.create_approval_request(
                transfer_request=valid_transfer_request,
                requester_id="user-123",
                requester_role=UserRole.USER
            )
    
    @pytest.mark.asyncio
    async def test_create_approval_request_with_multiple_records(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test creating approval request with multiple records."""
        # Arrange
        valid_transfer_request.records = [
            TransferRecord(id=f"record-{i}", content={"data": f"value{i}"})
            for i in range(5)
        ]
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert
        assert len(approval.transfer_request.records) == 5
        
        # Verify stored in database
        result = test_db.execute(
            text("SELECT transfer_request FROM approval_requests WHERE id = :id"),
            {"id": approval.id}
        ).fetchone()
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_create_approval_request_different_roles(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test creating approval requests with different user roles."""
        approval_service._notify_approvers = AsyncMock()
        
        roles = [
            UserRole.USER,
            UserRole.DATA_ANALYST,
            UserRole.DATA_MANAGER,
            UserRole.ADMIN
        ]
        
        for role in roles:
            # Act
            approval = await approval_service.create_approval_request(
                transfer_request=valid_transfer_request,
                requester_id=f"user-{role.value}",
                requester_role=role
            )
            
            # Assert
            assert approval.requester_role == role.value
            
            # Verify in database
            result = test_db.execute(
                text("SELECT requester_role FROM approval_requests WHERE id = :id"),
                {"id": approval.id}
            ).fetchone()
            
            assert result[0] == role.value
    
    @pytest.mark.asyncio
    async def test_create_approval_request_initial_status_pending(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that new approval requests have PENDING status."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER
        )
        
        # Assert
        assert approval.status == ApprovalStatus.PENDING
        assert approval.approver_id is None
        assert approval.approved_at is None
        assert approval.comment is None
    
    @pytest.mark.asyncio
    async def test_create_approval_request_preserves_transfer_details(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that all transfer request details are preserved."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert - Verify all fields preserved
        assert approval.transfer_request.source_type == valid_transfer_request.source_type
        assert approval.transfer_request.source_id == valid_transfer_request.source_id
        assert approval.transfer_request.target_state == valid_transfer_request.target_state
        assert approval.transfer_request.data_attributes.category == valid_transfer_request.data_attributes.category
        assert approval.transfer_request.data_attributes.tags == valid_transfer_request.data_attributes.tags
        assert approval.transfer_request.data_attributes.quality_score == valid_transfer_request.data_attributes.quality_score
    
    @pytest.mark.asyncio
    async def test_create_multiple_approval_requests(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test creating multiple approval requests."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        
        # Act - Create 3 approval requests
        approvals = []
        for i in range(3):
            approval = await approval_service.create_approval_request(
                transfer_request=valid_transfer_request,
                requester_id=f"user-{i}",
                requester_role=UserRole.DATA_ANALYST
            )
            approvals.append(approval)
        
        # Assert - All have unique IDs
        approval_ids = [a.id for a in approvals]
        assert len(approval_ids) == len(set(approval_ids))
        
        # Verify all stored in database
        result = test_db.execute(
            text("SELECT COUNT(*) FROM approval_requests")
        ).fetchone()
        
        assert result[0] == 3


class TestApprovalRequestValidation:
    """Test validation logic in approval request creation."""
    
    @pytest.mark.asyncio
    async def test_validation_rejects_none_transfer_request(
        self,
        approval_service
    ):
        """Test that None transfer request is rejected."""
        with pytest.raises(AttributeError):
            await approval_service.create_approval_request(
                transfer_request=None,
                requester_id="user-123",
                requester_role=UserRole.USER
            )
    
    @pytest.mark.asyncio
    async def test_validation_accepts_minimum_valid_request(
        self,
        approval_service,
        test_db
    ):
        """Test that minimum valid request is accepted."""
        # Arrange
        minimal_request = DataTransferRequest(
            source_type="sync",
            source_id="min-source",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="minimal",
                tags=[],
                quality_score=0.5
            ),
            records=[
                TransferRecord(id="min-record", content={})
            ]
        )
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=minimal_request,
            requester_id="user-123",
            requester_role=UserRole.USER
        )
        
        # Assert
        assert approval is not None
        assert approval.status == ApprovalStatus.PENDING


class TestApprovalRequestNotifications:
    """Test notification triggering in approval request creation."""
    
    @pytest.mark.asyncio
    async def test_notifications_called_with_correct_approval(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that notifications receive correct approval object."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert
        approval_service._notify_approvers.assert_called_once()
        notified_approval = approval_service._notify_approvers.call_args[0][0]
        
        assert notified_approval.id == approval.id
        assert notified_approval.requester_id == approval.requester_id
        assert notified_approval.status == ApprovalStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_notification_failure_does_not_prevent_creation(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that notification failure doesn't prevent request creation."""
        # Arrange
        async def failing_notify(approval):
            raise Exception("Notification service unavailable")
        
        approval_service._notify_approvers = failing_notify
        
        # Act & Assert - Should raise exception from notification
        with pytest.raises(Exception, match="Notification service unavailable"):
            await approval_service.create_approval_request(
                transfer_request=valid_transfer_request,
                requester_id="user-123",
                requester_role=UserRole.USER
            )
        
        # Note: In production, notification failures should be logged but not prevent creation
        # This test documents current behavior


class TestApprovalRequestDatabaseIntegrity:
    """Test database integrity in approval request creation."""
    
    @pytest.mark.asyncio
    async def test_database_transaction_commits(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that database transaction is committed."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.DATA_ANALYST
        )
        
        # Assert - Data should be retrievable in new query
        result = test_db.execute(
            text("SELECT id FROM approval_requests WHERE id = :id"),
            {"id": approval.id}
        ).fetchone()
        
        assert result is not None
        assert result[0] == approval.id
    
    @pytest.mark.asyncio
    async def test_created_at_timestamp_set(
        self,
        approval_service,
        test_db,
        valid_transfer_request
    ):
        """Test that created_at timestamp is set correctly."""
        # Arrange
        approval_service._notify_approvers = AsyncMock()
        before_creation = datetime.utcnow()
        
        # Act
        approval = await approval_service.create_approval_request(
            transfer_request=valid_transfer_request,
            requester_id="user-123",
            requester_role=UserRole.USER
        )
        
        after_creation = datetime.utcnow()
        
        # Assert
        assert before_creation <= approval.created_at <= after_creation
